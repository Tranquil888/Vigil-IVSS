"""Queues on the hot path. No put call ever blocks."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Optional


class LatestFrame:
    """One slot. A new frame replaces the old one, and readers never wait."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._frame: Any = None
        self._generation = 0

    def put(self, frame: Any) -> None:
        with self._condition:
            self._frame = frame
            self._generation += 1
            self._condition.notify_all()

    def latest(self) -> Any:
        with self._condition:
            return self._frame

    def get(self, timeout: Optional[float] = None) -> Any:
        with self._condition:
            if timeout is not None and timeout <= 0:
                return self._frame
            start = self._generation
            if timeout is None:
                while self._generation == start:
                    self._condition.wait()
            else:
                deadline = time.monotonic() + timeout
                while self._generation == start:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None
                    self._condition.wait(remaining)
            return self._frame

    @property
    def generation(self) -> int:
        with self._condition:
            return self._generation


class DropOldestQueue:
    """Bounded queue that discards its oldest item instead of blocking."""

    def __init__(self, maxsize: int = 1) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be at least 1")
        self.maxsize = maxsize
        self._items: Deque[Any] = deque()
        self._condition = threading.Condition()
        self._closed = False
        self.dropped = 0

    def put(self, item: Any) -> int:
        dropped = 0
        with self._condition:
            if self._closed:
                return 0
            while len(self._items) >= self.maxsize:
                self._items.popleft()
                dropped += 1
            self._items.append(item)
            self.dropped += dropped
            self._condition.notify_all()
        return dropped

    def get(self, timeout: Optional[float] = None) -> Any:
        with self._condition:
            if timeout is not None and timeout <= 0:
                if not self._items:
                    return None
            elif timeout is None:
                while not self._items and not self._closed:
                    self._condition.wait()
            else:
                deadline = time.monotonic() + timeout
                while not self._items and not self._closed:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None
                    self._condition.wait(remaining)
            if not self._items:
                return None
            return self._items.popleft()

    def qsize(self) -> int:
        with self._condition:
            return len(self._items)

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    @property
    def closed(self) -> bool:
        with self._condition:
            return self._closed

