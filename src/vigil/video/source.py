"""Frame sources. The capture thread knows nothing about cameras or protocols."""

from __future__ import annotations

import time
from typing import Callable, List, Optional

import cv2
import numpy as np

VIDEO_SUFFIXES = frozenset(
    {".mp4", ".m4v", ".avi", ".mkv", ".mov", ".webm", ".mpg", ".mpeg", ".wmv"}
)


class FrameSource:
    def open(self) -> bool:
        raise NotImplementedError

    def read(self) -> Optional[np.ndarray]:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def describe(self) -> str:
        return "source"


class OpenCVSource(FrameSource):
    def __init__(
        self,
        source: str,
        open_timeout_ms: int = 5000,
        buffer_size: int = 1,
    ) -> None:
        self.source = source
        self.open_timeout_ms = int(open_timeout_ms)
        self.buffer_size = int(buffer_size)
        self._capture = None

    def _target(self):
        text = str(self.source)
        if text.isdigit():
            return int(text)
        return text

    def _backend(self) -> int:
        text = str(self.source).lower()
        if text.startswith(("rtsp://", "rtsps://", "http://", "https://")):
            return cv2.CAP_FFMPEG
        return cv2.CAP_ANY

    def open(self) -> bool:
        self.close()
        capture = cv2.VideoCapture(self._target(), self._backend())
        try:
            capture.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
            capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.open_timeout_ms)
        except cv2.error:
            pass
        if not capture.isOpened():
            capture.release()
            return False
        self._capture = capture
        return True

    def read(self) -> Optional[np.ndarray]:
        if self._capture is None:
            return None
        ok, frame = self._capture.read()
        if not ok or frame is None:
            return None
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def describe(self) -> str:
        text = str(self.source)
        if "://" in text and "@" in text:
            scheme, rest = text.split("://", 1)
            return scheme + "://" + rest.split("@", 1)[1]
        return text


class VideoFileSource(FrameSource):
    """Plays one or more video files as a looping, real-time camera.

    A camera ``source`` may list several files, one per line. Files play in
    order and the playlist loops, so a recorder dump behaves like a camera that
    never goes offline. Frames are paced to the file's own frame rate instead
    of decoding as fast as the disk allows.
    """

    def __init__(
        self,
        paths: List[str],
        loop: bool = True,
        realtime: bool = True,
    ) -> None:
        self.paths = [str(path).strip() for path in paths if str(path).strip()]
        self.loop = bool(loop)
        self.realtime = bool(realtime)
        self.index = -1
        self._capture = None
        self._fps = 25.0
        self._next_at = 0.0

    def open(self) -> bool:
        self.close()
        if not self.paths:
            return False
        self.index = 0
        return self._open_current()

    def _open_current(self) -> bool:
        while 0 <= self.index < len(self.paths):
            capture = cv2.VideoCapture(self.paths[self.index])
            if capture.isOpened():
                self._capture = capture
                fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
                self._fps = fps if fps > 1.0 else 25.0
                self._next_at = 0.0
                return True
            capture.release()
            self.index += 1
        return False

    def _advance(self) -> bool:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self.index += 1
        if self.index >= len(self.paths):
            if not self.loop:
                return False
            self.index = 0
        return self._open_current()

    def _pace(self) -> None:
        if not self.realtime:
            return
        now = time.monotonic()
        if self._next_at <= 0.0:
            self._next_at = now
        self._next_at += 1.0 / self._fps
        delay = self._next_at - now
        if delay > 0:
            time.sleep(min(delay, 0.25))
        elif delay < -1.0:
            self._next_at = now

    def read(self) -> Optional[np.ndarray]:
        if self._capture is None and not self._open_current():
            return None
        ok, frame = self._capture.read()
        if not ok or frame is None:
            if not self._advance():
                return None
            ok, frame = self._capture.read()
            if not ok or frame is None:
                return None
        self._pace()
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self.index = -1

    def describe(self) -> str:
        if len(self.paths) == 1:
            return self.paths[0]
        return "playlist of %d files" % len(self.paths)


class FakeSource(FrameSource):
    """Deterministic source for tests. No camera, no codec, no GPU."""

    def __init__(
        self,
        frame_count: int = 0,
        width: int = 64,
        height: int = 48,
        read_delay: float = 0.0,
        open_failures: int = 0,
        read_failures: int = 0,
        stall_after: Optional[int] = None,
        frame_factory: Optional[Callable[[int], np.ndarray]] = None,
    ) -> None:
        self.frame_count = int(frame_count)
        self.width = int(width)
        self.height = int(height)
        self.read_delay = float(read_delay)
        self.open_failures = int(open_failures)
        self.read_failures = int(read_failures)
        self.stall_after = stall_after
        self.frame_factory = frame_factory
        self.reads = 0
        self._open_attempts = 0
        self._opened = False
        self._stalled = False
        self._base = np.full((self.height, self.width, 3), 32, dtype=np.uint8)

    def open(self) -> bool:
        self._open_attempts += 1
        if self._open_attempts <= self.open_failures:
            return False
        self._opened = True
        return True

    def read(self) -> Optional[np.ndarray]:
        if not self._opened or self._stalled:
            return None
        if self.stall_after is not None and self.reads >= self.stall_after:
            self._stalled = True
            return None
        if self.read_failures > 0:
            self.read_failures -= 1
            return None
        if self.read_delay:
            time.sleep(self.read_delay)
        if self.frame_factory is not None:
            frame = self.frame_factory(self.reads)
        else:
            frame = self._base.copy()
            frame[0, self.reads % self.width] = 255
        self.reads += 1
        if self.frame_count and self.reads > self.frame_count:
            return None
        return frame

    def close(self) -> None:
        self._opened = False

    def describe(self) -> str:
        return "fake"
