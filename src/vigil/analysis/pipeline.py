"""Inference worker: sampled frames in, one event per tracklet out.

The worker owns the tracker and every piece of tracklet state, so no other
thread reads or writes it. Frames arrive through a bounded queue that drops its
oldest item, so a slow inference pass can never slow capture or display down.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..config.models import CameraConfig, FaceConfig, VigilConfig
from ..core.records import (
    Decision,
    EventRecord,
    EventType,
    Frame,
    OverlayItem,
    Rect,
)
from ..storage.embeddings import to_blob
from .backend import MODEL_ID
from .decisions import (
    ObservationVote,
    TrackletDecision,
    decide_observation,
    decide_tracklet,
)
from .gallery import Gallery
from .quality import assess_quality
from .tracker import IouTracker, Track
from .unknowns import StrangerGrouper

log = logging.getLogger(__name__)

_EVENT_TYPES = {
    Decision.KNOWN: EventType.KNOWN_FACE,
    Decision.UNKNOWN: EventType.STRANGER,
    Decision.UNCERTAIN: EventType.UNCERTAIN_FACE,
}


class OverlayStore:
    """Last overlay set per camera, with a deadline. Read from the GUI thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: Dict[str, Tuple[List[OverlayItem], float]] = {}

    def put(
        self,
        camera_id: str,
        items: List[OverlayItem],
        ttl: Optional[float] = None,
        now: Optional[float] = None,
    ) -> None:
        ttl = 1.0 if ttl is None else float(ttl)
        now = time.monotonic() if now is None else float(now)
        expires_at = now + ttl
        stamped = []
        for item in items:
            item.expires_at = expires_at
            stamped.append(item)
        with self._lock:
            self._items[camera_id] = (stamped, expires_at)

    def get(self, camera_id: str, now: Optional[float] = None) -> List[OverlayItem]:
        now = time.monotonic() if now is None else float(now)
        with self._lock:
            entry = self._items.get(camera_id)
            if entry is None:
                return []
            items, expires_at = entry
            if now >= expires_at:
                del self._items[camera_id]
                return []
            return list(items)

    def clear(self, camera_id: Optional[str] = None) -> None:
        with self._lock:
            if camera_id is None:
                self._items.clear()
            else:
                self._items.pop(camera_id, None)


@dataclass
class _TrackState:
    camera_id: str
    track_id: int
    started_at: float
    last_wall: float
    first_captured: float
    last_captured: float
    rect: Rect
    observations: int = 0
    votes: List[ObservationVote] = field(default_factory=list)
    best_image: Any = None
    best_weight: float = 0.0
    embedding: Optional[np.ndarray] = None
    # Set when the backend can detect faces but cannot embed them. Such a
    # tracklet has no gallery evidence, so it is a stranger, not an ambiguous
    # match.
    detection_only: bool = False


class InferenceWorker(threading.Thread):
    def __init__(
        self,
        queue=None,
        config: Optional[VigilConfig] = None,
        backend=None,
        gallery: Optional[Gallery] = None,
        grouper: Optional[StrangerGrouper] = None,
        bus=None,
        snapshot_store=None,
        overlays: Optional[OverlayStore] = None,
        cameras: Optional[List[CameraConfig]] = None,
        names: Optional[Dict[int, str]] = None,
        clock=time.monotonic,
    ) -> None:
        super().__init__(name="vigil-inference", daemon=True)
        self._queue = queue
        self._config = config or VigilConfig()
        self._face: FaceConfig = self._config.face
        self._backend = backend
        self._gallery = gallery or Gallery()
        self._grouper = grouper or StrangerGrouper(
            self._face.unknown_merge_window_s,
            self._face.unknown_merge_threshold,
        )
        self._bus = bus
        self._snapshots = snapshot_store
        self._overlays = overlays or OverlayStore()
        self._cameras = {camera.id: camera for camera in (cameras or [])}
        # Share the map so a rename from the People page reaches live labels.
        self._names = names if names is not None else {}
        self._clock = clock
        self._trackers: Dict[str, IouTracker] = {}
        self._states: Dict[Tuple[str, int], _TrackState] = {}
        self._stop_event = threading.Event()
        self._finalised = False
        self._lock = threading.Lock()
        self._reset_lock = threading.Lock()
        self._reset_cameras: List[str] = []
        self._counters = {
            "frames": 0,
            "stale_frames": 0,
            "faces": 0,
            "events": 0,
            "errors": 0,
        }

    # -- public --------------------------------------------------------

    @property
    def overlays(self) -> OverlayStore:
        return self._overlays

    def process(self, frame: Frame) -> List[EventRecord]:
        """Handle one sampled frame. Returns the events this frame closed."""
        self._counters["frames"] += 1
        if frame.image is None:
            return []
        tracker = self._tracker(frame.camera_id)
        now = float(frame.captured_at)

        # Close stale tracklets before matching, so a long gap can never be
        # bridged by a detection that happens to sit on the same rectangle.
        events: List[EventRecord] = []
        for track in tracker.close_stale(now):
            state = self._states.pop((frame.camera_id, track.id), None)
            if state is not None:
                self._finalise(state, events)

        detections = self._detect(frame)
        self._counters["faces"] += len(detections)
        tracks = tracker.update(detections, now)

        items: List[OverlayItem] = []
        for track in tracks:
            state = self._state_for(frame, track)
            vote = self._observe(frame, state, track)
            label, kind = self._label(vote, state)
            items.append(
                OverlayItem(
                    camera_id=frame.camera_id,
                    rect=track.rect,
                    label=label,
                    kind=kind,
                    expires_at=0.0,
                )
            )

        self._overlays.put(
            frame.camera_id,
            items,
            ttl=self._config.display.overlay_ttl_s,
            now=now,
        )
        self._publish(events)
        return events

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._queue is not None:
            self._queue.close()
        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout)
        self._finalise_all()

    def set_backend(self, backend) -> None:
        self._backend = backend

    def request_camera_reset(self, camera_id: str) -> None:
        """Close this camera's tracklets on the worker thread.

        A reconnect means the old frames are gone, so a track that happens to
        land on the same pixels afterwards must not inherit the old votes.
        """
        with self._reset_lock:
            if camera_id not in self._reset_cameras:
                self._reset_cameras.append(camera_id)

    def _drain_camera_resets(self) -> None:
        with self._reset_lock:
            pending = list(self._reset_cameras)
            self._reset_cameras = []
        if not pending:
            return
        events: List[EventRecord] = []
        for camera_id in pending:
            for key in [key for key in self._states if key[0] == camera_id]:
                state = self._states.pop(key)
                self._finalise(state, events)
            if self._trackers.pop(camera_id, None) is not None:
                # Dropping the tracker also drops its id counter, so the next
                # tracklet starts fresh instead of reusing an old id.
                log.debug(
                    "tracklets closed after reconnect",
                    extra={"event": "inference.reset", "camera_id": camera_id},
                )
        self._publish(events)

    def reconfigure(self, config: VigilConfig) -> None:
        """Adopt live config edits. Existing tracklets keep their state."""
        self._config = config
        self._face = config.face
        self._cameras = {camera.id: camera for camera in config.cameras}
        # Keep the live clusters. Replacing the grouper would restart its id
        # counter and collide with cluster rows already in the database.
        self._grouper.configure(
            self._face.unknown_merge_window_s,
            self._face.unknown_merge_threshold,
        )
        for tracker in self._trackers.values():
            tracker.iou_threshold = float(self._face.track_iou)
            tracker.max_gap_s = float(self._face.track_max_gap_s)

    def stats(self) -> dict:
        stats = dict(self._counters)
        stats["tracks_active"] = len(self._states)
        stats["queued"] = self._queue.qsize() if self._queue is not None else 0
        stats["dropped"] = (
            getattr(self._queue, "dropped", 0) if self._queue is not None else 0
        )
        stats["backend"] = getattr(
            getattr(self._backend, "status", None), "detector", "none"
        )
        return stats

    def run(self) -> None:
        while True:
            frame = self._queue.get(timeout=0.2) if self._queue is not None else None
            if frame is None:
                # After a stop request, drain whatever is already queued before
                # finalising, so a shutdown does not silently drop a tracklet.
                if self._stop_event.is_set() or self._queue is None:
                    break
                continue
            # A reconnect request must land before the next frame is matched.
            self._drain_camera_resets()
            age = self._clock() - frame.captured_at
            if age > self._config.inference.max_frame_age_s:
                self._counters["stale_frames"] += 1
                continue
            try:
                self.process(frame)
            except Exception:
                self._counters["errors"] += 1
                log.exception("inference failed", extra={"event": "inference.failed"})
        self._finalise_all()

    # -- internals -----------------------------------------------------

    def _tracker(self, camera_id: str) -> IouTracker:
        tracker = self._trackers.get(camera_id)
        if tracker is None:
            tracker = IouTracker(
                iou_threshold=self._face.track_iou,
                max_gap_s=self._face.track_max_gap_s,
            )
            self._trackers[camera_id] = tracker
        return tracker

    def _detect(self, frame: Frame) -> List[Rect]:
        if self._backend is None:
            return []
        if not getattr(getattr(self._backend, "status", None), "available", False):
            return []
        try:
            return list(self._backend.detect(frame.image))
        except Exception:
            self._counters["errors"] += 1
            log.exception("face detection failed", extra={"event": "face.detect_failed"})
            return []

    def _state_for(self, frame: Frame, track: Track) -> _TrackState:
        key = (frame.camera_id, track.id)
        state = self._states.get(key)
        if state is None:
            state = _TrackState(
                camera_id=frame.camera_id,
                track_id=track.id,
                started_at=float(frame.wall_time),
                last_wall=float(frame.wall_time),
                first_captured=float(frame.captured_at),
                last_captured=float(frame.captured_at),
                rect=track.rect,
            )
            self._states[key] = state
        state.rect = track.rect
        state.last_wall = float(frame.wall_time)
        state.last_captured = float(frame.captured_at)
        state.observations += 1
        return state

    def _observe(
        self, frame: Frame, state: _TrackState, track: Track
    ) -> Optional[ObservationVote]:
        quality = assess_quality(frame.image, track.rect, self._face)
        if quality.face_px < self._face.min_face_px_embed:
            return None
        if self._backend is None or not getattr(self._backend, "can_embed", False):
            state.detection_only = True
            return None
        try:
            embedding = self._backend.embed(frame.image, track.rect)
        except Exception:
            self._counters["errors"] += 1
            log.exception("face embedding failed", extra={"event": "face.embed_failed"})
            return None
        if embedding is None:
            return None

        scores = self._gallery.score(embedding, self._face.gallery_score)
        vote = decide_observation(scores, self._face)
        weight = float(quality.face_px * quality.face_px) * max(
            0.0, float(quality.score)
        )
        vote.weight = max(weight, 1e-6)

        state.votes.append(vote)
        state.votes.sort(key=lambda item: item.weight, reverse=True)
        del state.votes[self._face.best_k :]

        if weight > state.best_weight:
            state.best_weight = weight
            state.best_image = frame.image
            state.embedding = np.asarray(embedding, dtype=np.float32)
        return vote

    def _label(
        self, vote: Optional[ObservationVote], state: _TrackState
    ) -> Tuple[str, str]:
        if vote is None:
            if state.detection_only:
                return "Unknown", Decision.UNKNOWN
            return "Face", Decision.UNCERTAIN
        if vote.decision == Decision.KNOWN and vote.person_id is not None:
            name = self._names.get(vote.person_id, "Person %d" % vote.person_id)
            return name, Decision.KNOWN
        if vote.decision == Decision.UNKNOWN:
            return "Unknown", Decision.UNKNOWN
        return "Check", Decision.UNCERTAIN

    def _finalise_all(self) -> None:
        with self._lock:
            if self._finalised:
                return
            self._finalised = True
        events: List[EventRecord] = []
        for state in list(self._states.values()):
            self._finalise(state, events)
        self._states.clear()
        for tracker in self._trackers.values():
            tracker.close_all()
        self._publish(events)

    def _finalise(self, state: _TrackState, events: List[EventRecord]) -> None:
        if state.observations < self._face.min_tracklet_observations:
            return
        if state.detection_only and not state.votes:
            decision = TrackletDecision(Decision.UNKNOWN)
        else:
            decision = decide_tracklet(state.votes, self._face)
        event_type = _EVENT_TYPES.get(decision.decision)
        if event_type is None:
            return

        started_at = state.started_at
        ended_at = max(state.started_at, state.last_wall)
        detail: Dict[str, Any] = {
            "tracklet": {
                "camera_id": state.camera_id,
                "started_at": started_at,
                "ended_at": ended_at,
                "decision": decision.decision,
                "person_id": decision.person_id,
                "agg_score": decision.score,
                "n_obs": state.observations,
            }
        }

        record = EventRecord(
            camera_id=state.camera_id,
            type=event_type,
            ts_start=started_at,
            ts_end=ended_at,
            person_id=decision.person_id,
            score=decision.score,
            dedupe_key="%s:%s:%d:%.3f"
            % (state.camera_id, event_type, state.track_id, started_at),
            detail=detail,
        )

        if decision.decision == Decision.UNKNOWN and state.embedding is not None:
            assignment = self._grouper.assign(
                state.camera_id, state.embedding, ended_at
            )
            record.unknown_cluster_id = assignment.id
            # All tracklets in one visit share a key, so the writer keeps a
            # single event row and extends its end time instead of adding one
            # row per tracklet.
            record.dedupe_key = "stranger:%s:%d:%.3f" % (
                state.camera_id,
                assignment.id,
                assignment.first_seen,
            )
            if assignment.is_new:
                detail["unknown_cluster"] = {
                    "first_seen": assignment.first_seen,
                    "last_seen": assignment.last_seen,
                    "n_visits": assignment.n_visits,
                    "centroid": to_blob(assignment.centroid),
                    "model_id": MODEL_ID,
                }

        if event_type in (EventType.KNOWN_FACE, EventType.STRANGER):
            self._attach_snapshot(record, state)

        self._counters["events"] += 1
        events.append(record)

    def _attach_snapshot(self, record: EventRecord, state: _TrackState) -> None:
        if self._snapshots is None or state.best_image is None:
            return
        camera = self._cameras.get(state.camera_id)
        if camera is not None and not camera.snapshot_enabled:
            return
        try:
            record.detail["snapshot"] = self._snapshots.save(
                state.best_image, state.camera_id, when=state.last_wall
            )
        except Exception:
            self._counters["errors"] += 1
            log.exception(
                "snapshot save failed",
                extra={"event": "snapshot.save_failed", "camera_id": state.camera_id},
            )

    def _publish(self, events: List[EventRecord]) -> None:
        if self._bus is None:
            return
        for record in events:
            self._bus.publish(record)
