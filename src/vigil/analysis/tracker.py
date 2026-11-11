"""Greedy IoU tracker. Tracklets are closed by the pipeline, not by the tracker."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

Rect = Tuple[int, int, int, int]


def iou(a: Rect, b: Rect) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    left = max(ax, bx)
    top = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)
    if right <= left or bottom <= top:
        return 0.0
    intersection = float((right - left) * (bottom - top))
    union = float(aw * ah + bw * bh) - intersection
    if union <= 0:
        return 0.0
    return intersection / union


@dataclass
class Track:
    id: int
    rect: Rect
    first_seen: float
    last_seen: float
    observations: int = 0
    history: List[Rect] = field(default_factory=list)


class IouTracker:
    def __init__(self, iou_threshold: float = 0.3, max_gap_s: float = 1.0) -> None:
        self.iou_threshold = float(iou_threshold)
        self.max_gap_s = float(max_gap_s)
        self._tracks: Dict[int, Track] = {}
        self._next_id = 1

    def update(self, detections: List[Rect], now: float) -> List[Track]:
        candidates = []
        for detection_index, detection in enumerate(detections):
            for track in self._tracks.values():
                overlap = iou(detection, track.rect)
                if overlap >= self.iou_threshold:
                    candidates.append((overlap, detection_index, track.id))
        candidates.sort(reverse=True)

        matched_detections = set()
        matched_tracks = set()
        assignments: Dict[int, Track] = {}
        for overlap, detection_index, track_id in candidates:
            if detection_index in matched_detections or track_id in matched_tracks:
                continue
            track = self._tracks[track_id]
            track.rect = detections[detection_index]
            track.last_seen = now
            track.observations += 1
            track.history.append(track.rect)
            matched_detections.add(detection_index)
            matched_tracks.add(track_id)
            assignments[detection_index] = track

        for detection_index, detection in enumerate(detections):
            if detection_index in assignments:
                continue
            track = Track(
                id=self._next_id,
                rect=detection,
                first_seen=now,
                last_seen=now,
                observations=1,
                history=[detection],
            )
            self._next_id += 1
            self._tracks[track.id] = track
            assignments[detection_index] = track

        return [assignments[index] for index in range(len(detections))]

    def close_stale(self, now: float) -> List[Track]:
        stale = [
            track
            for track in self._tracks.values()
            if now - track.last_seen > self.max_gap_s
        ]
        for track in stale:
            del self._tracks[track.id]
        return stale

    def close_all(self) -> List[Track]:
        closed = list(self._tracks.values())
        self._tracks.clear()
        return closed

    def active_count(self) -> int:
        return len(self._tracks)
