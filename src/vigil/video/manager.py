"""Owns every capture thread and the shared queues they feed."""

from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional

from ..config.models import CameraConfig, VigilConfig
from ..core.queues import DropOldestQueue, LatestFrame
from .capture import CameraSupervisor
from .source import FrameSource, OpenCVSource


class CameraManager:
    def __init__(
        self,
        config: VigilConfig,
        bus=None,
        source_factory: Optional[Callable[[CameraConfig], FrameSource]] = None,
    ) -> None:
        self.config = config
        self.bus = bus
        self.inference_queue = DropOldestQueue(config.inference.queue_size)
        self._display: Dict[str, LatestFrame] = {}
        self._motion_queues: Dict[str, DropOldestQueue] = {}
        self._motion_active: Dict[str, threading.Event] = {}
        self._supervisors: List[CameraSupervisor] = []

        for camera in config.cameras:
            if not camera.enabled:
                continue
            self._display[camera.id] = LatestFrame()
            self._motion_queues[camera.id] = DropOldestQueue(2)
            self._motion_active[camera.id] = threading.Event()
            factory = source_factory or _default_factory(config)
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
                    bus=bus,
                    motion_active=self._motion_active[camera.id],
                )
            )

    @property
    def camera_ids(self) -> List[str]:
        return list(self._display)

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

    def start_all(self) -> None:
        for supervisor in self._supervisors:
            supervisor.start()

    def start_camera(self, camera_id: str) -> None:
        for supervisor in self._supervisors:
            if supervisor.camera.id == camera_id and not supervisor.is_alive():
                supervisor.start()

    def stop_all(self, timeout: float = 5.0) -> None:
        for supervisor in self._supervisors:
            supervisor.stop(timeout=timeout / max(1, len(self._supervisors)))

    def stats(self) -> List[dict]:
        return [supervisor.stats() for supervisor in self._supervisors]

    def state(self, camera_id: str):
        for supervisor in self._supervisors:
            if supervisor.camera.id == camera_id:
                return supervisor.state
        return None


def _default_factory(config: VigilConfig):
    def build(camera: CameraConfig) -> FrameSource:
        return OpenCVSource(
            camera.source,
            open_timeout_ms=config.capture.open_timeout_ms,
            buffer_size=config.capture.buffer_size,
        )

    return build
