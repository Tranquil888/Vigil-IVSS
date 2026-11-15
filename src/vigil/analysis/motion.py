"""MOG2 motion detection on a small grayscale copy, gated by polygon zones."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import cv2
import numpy as np

from ..config.models import MotionConfig, ZoneConfig
from .zones import ZoneMask, build_zone_masks


@dataclass
class MotionResult:
    active: bool
    zones: List[str] = field(default_factory=list)
    changed_pct: float = 0.0
    triggered: bool = False
    ended: bool = False
    global_change: bool = False


class MotionDetector:
    def __init__(
        self,
        config: MotionConfig,
        width: int,
        height: int,
        zones: Optional[List[ZoneConfig]] = None,
    ) -> None:
        self.config = config
        scale = min(1.0, float(config.max_side) / float(max(1, width)))
        self.width = max(1, int(round(width * scale)))
        self.height = max(1, int(round(height * scale)))
        self.masks: List[ZoneMask] = build_zone_masks(
            zones or [], self.width, self.height, config.threshold_pct
        )
        self._kernel = np.ones((3, 3), dtype=np.uint8)
        self._background = self._new_background()
        self._previous_gray = None
        self._running_average = None
        self._active = False
        self._streak = 0
        self._last_motion_at = 0.0
        self._frames_seen = 0

    def _new_background(self):
        return cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=16, detectShadows=False
        )

    def reset(self) -> None:
        self._background = self._new_background()
        self._previous_gray = None
        self._running_average = None
        self._streak = 0
        self._frames_seen = 0

    def _foreground(self, gray: np.ndarray) -> np.ndarray:
        algorithm = self.config.algorithm
        if algorithm == "frame_diff":
            if self._previous_gray is None:
                self._previous_gray = gray
                return np.zeros_like(gray)
            difference = cv2.absdiff(gray, self._previous_gray)
            self._previous_gray = gray
            return cv2.threshold(difference, 25, 255, cv2.THRESH_BINARY)[1]
        if algorithm == "running_avg":
            if self._running_average is None:
                self._running_average = gray.astype("float32")
                return np.zeros_like(gray)
            difference = cv2.absdiff(gray, cv2.convertScaleAbs(self._running_average))
            cv2.accumulateWeighted(gray, self._running_average, 0.05)
            return cv2.threshold(difference, 25, 255, cv2.THRESH_BINARY)[1]
        return self._background.apply(gray)

    def update(self, frame: np.ndarray, now: float) -> MotionResult:
        small = cv2.resize(
            frame, (self.width, self.height), interpolation=cv2.INTER_AREA
        )
        gray = (
            cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if small.ndim == 3
            else small
        )
        foreground = self._foreground(gray)
        self._frames_seen += 1
        if self._frames_seen <= 2:
            # MOG2 reports the first frame as fully changed while it learns
            # the background. That is warm-up, not motion.
            return MotionResult(active=self._active, zones=[], changed_pct=0.0)
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, self._kernel)
        foreground = cv2.dilate(foreground, self._kernel, iterations=1)

        total = float(self.width * self.height)
        changed_total = float(np.count_nonzero(foreground))
        if total > 0 and changed_total / total * 100.0 >= self.config.suppress_global_pct:
            self.reset()
            self._streak = 0
            self._last_motion_at = now
            return MotionResult(
                active=self._active,
                zones=[],
                changed_pct=changed_total / total * 100.0,
                global_change=True,
            )

        hit_zones: List[str] = []
        best_pct = changed_total / total * 100.0
        largest_area = 0.0
        for zone in self.masks:
            masked = cv2.bitwise_and(foreground, foreground, mask=zone.mask)
            zone_area = float(np.count_nonzero(zone.mask))
            if zone_area <= 0:
                continue
            changed = float(np.count_nonzero(masked))
            pct = changed / zone_area * 100.0
            best_pct = max(best_pct, pct)
            contours, _ = cv2.findContours(
                masked, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            area = max((cv2.contourArea(c) for c in contours), default=0.0)
            largest_area = max(largest_area, area)
            if pct >= zone.threshold_pct and area >= self.config.min_area_px:
                hit_zones.append(zone.name)

        any_hit = bool(hit_zones)
        if any_hit:
            self._streak += 1
            self._last_motion_at = now
        else:
            self._streak = 0

        triggered = False
        if not self._active and self._streak >= self.config.min_duration_frames:
            self._active = True
            triggered = True

        ended = False
        if (
            self._active
            and not any_hit
            and now - self._last_motion_at >= self.config.cooldown_s
        ):
            self._active = False
            ended = True

        return MotionResult(
            active=self._active,
            zones=hit_zones,
            changed_pct=best_pct,
            triggered=triggered,
            ended=ended,
            global_change=False,
        )


class MotionWorker(threading.Thread):
    """One motion detector per camera, on its own thread."""

    def __init__(
        self,
        camera_id: str,
        queue,
        config: MotionConfig,
        zones: Optional[List[ZoneConfig]],
        on_result: Callable[[str, MotionResult, object], None],
        detector_factory: Optional[Callable[..., MotionDetector]] = None,
    ) -> None:
        super().__init__(name="motion-%s" % camera_id, daemon=True)
        self.camera_id = camera_id
        self.queue = queue
        self.config = config
        self.zones = zones or []
        self.on_result = on_result
        self._factory = detector_factory or MotionDetector
        self._stop_event = threading.Event()
        self._reset_event = threading.Event()
        self._detector = None

    def run(self) -> None:
        while not self._stop_event.is_set():
            frame = self.queue.get(timeout=0.2)
            if frame is None:
                continue
            try:
                if self._reset_event.is_set():
                    self._reset_event.clear()
                    if self._detector is not None:
                        self._detector.reset()
                if self._detector is None:
                    self._detector = self._factory(
                        self.config,
                        frame.width or frame.image.shape[1],
                        frame.height or frame.image.shape[0],
                        self.zones,
                    )

                result = self._detector.update(frame.image, frame.captured_at)
                self.on_result(self.camera_id, result, frame)
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "motion update failed",
                    extra={"event": "motion.error", "camera_id": self.camera_id},
                )

    def reset(self) -> None:
        """Rebuild the background model on the worker's next frame."""
        self._reset_event.set()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if not self.is_alive():
            return
        self.join(timeout)
