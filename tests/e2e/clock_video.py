"""A machine-readable millisecond clock burned into a test frame.

The plan asks for a clock burned into a video so latency can be measured
without trusting the producer's own timestamps. Drawing digits would need
OCR, so the clock is a fixed strip of 32 high-contrast bits plus a four-bit
marker. It survives JPEG and a half-scale paint, and decoding is a handful
of array reads.

The strip sits at the bottom-left so the live tile's camera tag, which is
painted at the top-left, cannot cover it.
"""

from __future__ import annotations

import time
from typing import Optional

import cv2
import numpy as np

BLOCK = 16
MARKER = (1, 0, 1, 0)
VALUE_BITS = 32
STRIP_BITS = len(MARKER) + VALUE_BITS
STRIP_WIDTH = BLOCK * STRIP_BITS
STRIP_HEIGHT = BLOCK
MARGIN = 3


def _bits(value_ms: int) -> list:
    value = int(value_ms) & 0xFFFFFFFF
    bits = list(MARKER)
    bits.extend((value >> shift) & 1 for shift in range(VALUE_BITS - 1, -1, -1))
    return bits


def _paint(frame: np.ndarray, x: int, y: int, white: bool) -> None:
    left = x + MARGIN
    top = y + MARGIN
    right = x + BLOCK - MARGIN
    bottom = y + BLOCK - MARGIN
    if frame.ndim == 2:
        frame[top:bottom, left:right] = 255 if white else 0
    else:
        frame[top:bottom, left:right] = (255, 255, 255) if white else (0, 0, 0)


def burn_clock(frame: np.ndarray, value_ms: int) -> np.ndarray:
    """Draw ``value_ms`` into the bottom-left strip and return the frame."""
    height, width = frame.shape[:2]
    if width < STRIP_WIDTH or height < STRIP_HEIGHT:
        raise ValueError(
            "frame must be at least %dx%d" % (STRIP_WIDTH, STRIP_HEIGHT)
        )
    top = height - STRIP_HEIGHT
    if frame.ndim == 2:
        frame[top:height, 0:STRIP_WIDTH] = 0
    else:
        frame[top:height, 0:STRIP_WIDTH] = (0, 0, 0)
    for index, bit in enumerate(_bits(value_ms)):
        _paint(frame, index * BLOCK, top, bool(bit))
    return frame


def _sample(frame: np.ndarray, x: int, y: int) -> float:
    left = x + MARGIN
    top = y + MARGIN
    patch = frame[top : y + BLOCK - MARGIN, left : x + BLOCK - MARGIN]
    return float(np.mean(patch))


def read_clock_ms(frame: np.ndarray) -> Optional[int]:
    """Return the burned value, or ``None`` when no valid strip is present."""
    if frame is None:
        return None
    height, width = frame.shape[:2]
    if width < STRIP_WIDTH or height < STRIP_HEIGHT:
        return None
    top = height - STRIP_HEIGHT
    bits = []
    for index in range(STRIP_BITS):
        bits.append(1 if _sample(frame, index * BLOCK, top) > 127.0 else 0)
    if tuple(bits[: len(MARKER)]) != MARKER:
        return None
    value = 0
    for bit in bits[len(MARKER) :]:
        value = (value << 1) | bit
    return value


class PacedVideoSource:
    """A video file played at a fixed rate, with a known presentation base.

    OpenCV reads a file as fast as the disk allows. The capture supervisor
    must see a stream that arrives at camera speed, so each read waits for
    its slot. ``base`` is the monotonic time frame zero is due; the burned
    clock in frame N says ``N * 1000 / fps``, so the expected display time
    is ``base + burned_ms / 1000``.
    """

    def __init__(self, path: str, fps: float = 30.0) -> None:
        self.path = str(path)
        self.fps = float(fps)
        self.base: Optional[float] = None
        self.index = 0
        self._capture = None

    def open(self) -> bool:
        self.close()
        capture = cv2.VideoCapture(self.path)
        if not capture.isOpened():
            capture.release()
            return False
        self._capture = capture
        self.index = 0
        self.base = time.monotonic() + 0.05
        return True

    def read(self) -> Optional[np.ndarray]:
        if self._capture is None:
            return None
        if self.base is not None:
            target = self.base + self.index / self.fps
            wait = target - time.monotonic()
            if wait > 0:
                time.sleep(wait)
        ok, frame = self._capture.read()
        if not ok or frame is None:
            return None
        self.index += 1
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def describe(self) -> str:
        return "paced-video"


def write_clock_video(
    path: str,
    frame_count: int,
    fps: float = 30.0,
    width: int = 640,
    height: int = 360,
) -> str:
    """Write a moving test clip with a millisecond clock on every frame."""
    if width < STRIP_WIDTH or height < STRIP_HEIGHT:
        raise ValueError("video must be at least %dx%d" % (STRIP_WIDTH, STRIP_HEIGHT))
    candidates = [
        (str(path), "MJPG"),
        (str(path), "XVID"),
        (str(path).replace(".avi", ".mp4"), "mp4v"),
    ]
    last_error = None
    for target, codec in candidates:
        writer = cv2.VideoWriter(
            target,
            cv2.VideoWriter_fourcc(*codec),
            float(fps),
            (int(width), int(height)),
        )
        if not writer.isOpened():
            writer.release()
            last_error = "codec %s is not available" % codec
            continue
        try:
            for index in range(int(frame_count)):
                frame = np.full((height, width, 3), 24, dtype=np.uint8)
                x = 40 + (index * 8) % max(1, width - 160)
                cv2.rectangle(frame, (x, 120), (x + 96, 216), (210, 210, 210), -1)
                cv2.rectangle(frame, (x + 12, 132), (x + 84, 204), (60, 60, 60), -1)
                burn_clock(frame, int(round(index * 1000.0 / float(fps))))
                writer.write(frame)
        finally:
            writer.release()
        if target != str(path):
            path = target
        return str(path)
    raise RuntimeError(last_error or "no video codec was available")
