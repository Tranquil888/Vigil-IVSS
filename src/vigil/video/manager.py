"""Owns every capture thread and the shared queues they feed."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..config.models import CameraConfig, VigilConfig
from ..core.queues import DropOldestQueue, LatestFrame
from ..core.records import EventRecord, EventType
from .capture import CameraSupervisor
from .source import (
    VIDEO_SUFFIXES,
    FrameSource,
    OpenCVSource,
    VideoFileSource,
)
from ..analysis.motion import MotionWorker

log = logging.getLogger(__name__)


class CameraManager:
    def __init__(
        self,
        config: VigilConfig,
        bus=None,
        source_factory: Optional[Callable[[CameraConfig], FrameSource]] = None,
        on_camera_reset: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.config = config
        self.bus = bus
        self._source_factory = source_factory
        self._on_camera_reset = on_camera_reset
        self.inference_queue = DropOldestQueue(config.inference.queue_size)
        self._display: Dict[str, LatestFrame] = {}
        self._motion_queues: Dict[str, DropOldestQueue] = {}
        self._motion_active: Dict[str, threading.Event] = {}
        self._supervisors: List[CameraSupervisor] = []
        self._motion_workers: List[MotionWorker] = []
        # Threads cannot be restarted, so the manager remembers whether the
        # current worker set was ever started. Liveness alone is not enough: a
        # worker that failed to start, or one whose thread already died, is not
        # alive but still needs a start call after a rebuild.
        self._running = False
        self._build()

    def _build(self) -> None:
        config = self.config
        for camera in config.cameras:
            if not camera.enabled:
                continue
            self._display[camera.id] = LatestFrame()
            self._motion_queues[camera.id] = DropOldestQueue(2)
            self._motion_active[camera.id] = threading.Event()
            motion_config = config.motion_for(camera)
            if motion_config.enabled:
                self._motion_workers.append(
                    MotionWorker(
                        camera_id=camera.id,
                        queue=self._motion_queues[camera.id],
                        config=motion_config,
                        zones=camera.zones,
                        on_result=self._on_motion,
                    )
                )
            factory = self._source_factory or _default_factory(config)
            self._supervisors.append(
                CameraSupervisor(
                    camera=camera,
                    capture_config=config.capture,
                    motion_config=config.motion_for(camera),
                    inference_config=config.inference,
                    display=self._display[camera.id],
                    motion_queue=self._motion_queues[camera.id],
                    inference_queue=self.inference_queue,
                    source_factory=lambda camera=camera, factory=factory: factory(camera),
                    bus=self.bus,
                    motion_active=self._motion_active[camera.id],
                    on_reconnect=self._on_reconnect,
                )
            )

    @property
    def camera_ids(self) -> List[str]:
        return list(self._display)

    def runtime_signature(self):
        """Everything that needs a capture or motion worker rebuild."""
        cameras = []
        for camera in self.config.cameras:
            cameras.append(
                (
                    camera.id,
                    camera.enabled,
                    camera.source,
                    camera.analysis_stream,
                    repr(camera.motion.model_dump(mode="json"))
                    if camera.motion is not None
                    else None,
                    repr([zone.model_dump(mode="json") for zone in camera.zones]),
                )
            )
        return (
            tuple(cameras),
            repr(self.config.capture.model_dump(mode="json")),
            repr(self.config.motion.model_dump(mode="json")),
        )

    def reconfigure(self, config: VigilConfig) -> None:
        """Rebuild capture and motion workers in place, keeping the bus."""
        was_running = self._running
        self.stop_all()
        self.config = config
        self.inference_queue.resize(config.inference.queue_size)
        self._display.clear()
        self._motion_queues.clear()
        self._motion_active.clear()
        self._supervisors = []
        self._motion_workers = []
        self._build()
        if was_running:
            self.start_all()

    def display_queue(self, camera_id: str) -> LatestFrame:
        return self._display[camera_id]

    def motion_queue(self, camera_id: str) -> DropOldestQueue:
        return self._motion_queues[camera_id]

    def set_motion_active(self, camera_id: str, active: bool) -> None:
        event = self._motion_active[camera_id]
        if active:
            event.set()
        else:
            event.clear()

    def _on_reconnect(self, camera_id: str) -> None:
        """A reopened stream starts with a fresh motion model and no tracklets."""
        self.set_motion_active(camera_id, False)
        for worker in self._motion_workers:
            if worker.camera_id == camera_id:
                worker.reset()
                break
        if self._on_camera_reset is not None:
            self._on_camera_reset(camera_id)

    def _on_motion(self, camera_id: str, result, frame) -> None:
        self.set_motion_active(camera_id, result.active)
        if result.triggered and self.bus is not None:
            self.bus.publish(
                EventRecord(
                    camera_id=camera_id,
                    type=EventType.MOTION,
                    ts_start=frame.wall_time,
                    ts_end=frame.wall_time,
                    zone=result.zones[0] if result.zones else None,
                    detail={"changed_pct": round(result.changed_pct, 2)},
                )
            )

    def start_all(self) -> None:
        """Start every built worker. One failure never blocks the others."""
        self._running = True
        for worker in list(self._motion_workers):
            self._start_worker(worker)
        for supervisor in list(self._supervisors):
            self._start_worker(supervisor)

    def _start_worker(self, worker) -> None:
        if worker.is_alive():
            return
        if worker.ident is not None:
            log.warning(
                "worker already ran and is no longer alive, rebuild required",
                extra={"event": "manager.restart_rejected", "detail": worker.name},
            )
            return
        try:
            worker.start()
        except Exception:
            log.exception(
                "worker failed to start",
                extra={"event": "manager.start_failed", "detail": worker.name},
            )

    def start_camera(self, camera_id: str) -> None:
        for supervisor in self._supervisors:
            if supervisor.camera.id == camera_id:
                self._start_worker(supervisor)

    def stop_all(self, timeout: float = 5.0) -> None:
        self._running = False
        for supervisor in self._supervisors:
            supervisor.stop(timeout=timeout / max(1, len(self._supervisors)))
        for worker in self._motion_workers:
            worker.stop(timeout=timeout / max(1, len(self._motion_workers)))

    def stats(self) -> List[dict]:
        return [supervisor.stats() for supervisor in self._supervisors]

    def state(self, camera_id: str):
        for supervisor in self._supervisors:
            if supervisor.camera.id == camera_id:
                return supervisor.state
        return None


def _source_lines(camera: CameraConfig) -> List[str]:
    return [line.strip() for line in str(camera.source).splitlines() if line.strip()]


def _is_video_path(text: str) -> bool:
    return Path(text).suffix.lower() in VIDEO_SUFFIXES


def _default_factory(config: VigilConfig):
    def build(camera: CameraConfig) -> FrameSource:
        lines = _source_lines(camera)
        if len(lines) > 1 or (lines and _is_video_path(lines[0])):
            return VideoFileSource(lines)
        return OpenCVSource(
            camera.source,
            open_timeout_ms=config.capture.open_timeout_ms,
            buffer_size=config.capture.buffer_size,
        )

    return build
