"""One capture thread per camera. It never waits for inference."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import numpy as np

from ..config.models import CameraConfig, CaptureConfig, InferenceConfig, MotionConfig
from ..core.records import EventRecord, EventType, Frame
from ..core.queues import DropOldestQueue, LatestFrame
from .source import FrameSource, OpenCVSource
from .state import BackoffPolicy, CameraState, OfflineTracker

log = logging.getLogger(__name__)


class FrameSampler:
    """Time-based sampler. Independent of how fast frames arrive."""

    def __init__(self, analysis_fps: float) -> None:
        self.interval = 1.0 / float(analysis_fps)
        self._last = None

    def due(self, now: float) -> bool:
        if self._last is None or now - self._last >= self.interval:
            self._last = now
            return True
        return False

    def reset(self) -> None:
        self._last = None


class CameraSupervisor(threading.Thread):
    def __init__(
        self,
        camera: CameraConfig,
        capture_config: CaptureConfig,
        motion_config: MotionConfig,
        inference_config: InferenceConfig,
        display: LatestFrame,
        motion_queue: DropOldestQueue,
        inference_queue: DropOldestQueue,
        source_factory: Callable[[], FrameSource],
        bus=None,
        motion_active: Optional[threading.Event] = None,
        max_frames: Optional[int] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(name="capture-%s" % camera.id, daemon=True)
        self.camera = camera
        self.capture_config = capture_config
        self.motion_config = motion_config
        self.inference_config = inference_config
        self._display = display
        self._motion_queue = motion_queue
        self._inference_queue = inference_queue
        self._source_factory = source_factory
        self._bus = bus
        self._motion_active = motion_active or threading.Event()
        self._max_frames = max_frames
        self._clock = clock
        self._stop_event = threading.Event()
        self._sampler = FrameSampler(inference_config.analysis_fps)
        self._backoff = BackoffPolicy(
            capture_config.backoff_initial_s,
            capture_config.backoff_max_s,
            capture_config.backoff_jitter,
        )
        self._offline = OfflineTracker(capture_config.offline_notify_after_s)

        self.state = CameraState.INIT
        self.state_history = [CameraState.INIT]
        self._index = 0
        self._frames = 0
        self._reconnects = 0
        self._inference_sent = 0
        self._motion_sent = 0
        self._last_frame_at = None

    # -- state ---------------------------------------------------------

    def _set_state(self, state: CameraState) -> None:
        if state == self.state:
            return
        self.state = state
        self.state_history.append(state)
        log.debug(
            "camera state changed",
            extra={"event": "camera.state", "camera_id": self.camera.id, "detail": state.value},
        )

    # -- run loop ------------------------------------------------------

    def run(self) -> None:
        attempt = 0
        while not self._stop_event.is_set():
            self._set_state(CameraState.CONNECTING)
            source = self._source_factory()
            opened = False
            try:
                opened = source.open()
            except Exception:
                log.exception(
                    "camera open raised",
                    extra={"event": "camera.open_error", "camera_id": self.camera.id},
                )

            if not opened:
                if self._offline.failure(self._clock()):
                    self._publish_offline()
                self._set_state(CameraState.BACKOFF)
                self._reconnects += 1
                if self._stop_event.wait(self._backoff.delay(attempt)):
                    break
                attempt += 1
                continue

            self._set_state(CameraState.STREAMING)
            attempt = 0
            last_frame = self._clock()
            try:
                while not self._stop_event.is_set():
                    image = source.read()
                    now = self._clock()
                    if image is None:
                        if now - last_frame >= self.capture_config.stall_timeout_s:
                            self._set_state(CameraState.STALLED)
                            if self._offline.failure(now):
                                self._publish_offline()
                            break
                        if self._stop_event.wait(0.005):
                            break
                        continue
                    last_frame = now
                    if self._offline.frame(now):
                        self._publish_online(now)
                    self._publish(image, now)
                    if self._max_frames is not None and self._frames >= self._max_frames:
                        self._stop_event.set()
                        break
            except Exception:
                log.exception(
                    "camera read raised",
                    extra={"event": "camera.read_error", "camera_id": self.camera.id},
                )
            finally:
                try:
                    source.close()
                except Exception:
                    pass

            if self._stop_event.is_set():
                break
            self._set_state(CameraState.BACKOFF)
            self._reconnects += 1
            if self._stop_event.wait(self._backoff.delay(attempt)):
                break
            attempt += 1

        self._set_state(CameraState.CLOSED)

    # -- publishing ----------------------------------------------------

    def _motion_gate_open(self) -> bool:
        if not self.motion_config.enabled:
            return True
        return self._motion_active.is_set()

    def _publish(self, image: np.ndarray, now: float) -> None:
        self._index += 1
        self._frames += 1
        height, width = image.shape[:2]
        frame = Frame(
            camera_id=self.camera.id,
            index=self._index,
            captured_at=now,
            wall_time=time.time(),
            image=image,
            width=int(width),
            height=int(height),
        )
        self._display.put(frame)
        self._last_frame_at = now

        if self._index % self.motion_config.sample_every == 0:
            self._motion_queue.put(frame)
            self._motion_sent += 1

        if self._motion_gate_open() and self._sampler.due(now):
            self._inference_queue.put(frame)
            self._inference_sent += 1

    def _publish_offline(self) -> None:
        if self._bus is None:
            return
        self._bus.publish(
            EventRecord(
                camera_id=self.camera.id,
                type=EventType.CAMERA_OFFLINE,
                ts_start=time.time(),
                dedupe_key=None,
            )
        )

    def _publish_online(self, now: float) -> None:
        if self._bus is None:
            return
        self._bus.publish(
            EventRecord(
                camera_id=self.camera.id,
                type=EventType.CAMERA_ONLINE,
                ts_start=time.time(),
                dedupe_key=None,
            )
        )

    # -- lifecycle -----------------------------------------------------

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if not self.is_alive():
            return
        self.join(timeout)
        if self.is_alive():
            log.warning(
                "capture thread did not stop in time",
                extra={"event": "camera.stop_timeout", "camera_id": self.camera.id},
            )

    def stats(self) -> dict:
        return {
            "camera_id": self.camera.id,
            "state": self.state.value,
            "frames": self._frames,
            "reconnects": self._reconnects,
            "inference_sent": self._inference_sent,
            "motion_sent": self._motion_sent,
            "last_frame_at": self._last_frame_at,
        }
