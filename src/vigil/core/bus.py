"""In-process pub/sub used to keep DB writes and notifications off workers."""

from __future__ import annotations

import threading
from typing import Any, List

from .queues import DropOldestQueue


class EventBus:
    """Fan-out to bounded subscribers. Publishing is always non-blocking."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: List[DropOldestQueue] = []
        self._closed = False

    def subscribe(self, maxsize: int = 256) -> DropOldestQueue:
        queue = DropOldestQueue(maxsize)
        with self._lock:
            if self._closed:
                queue.close()
                return queue
            self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: DropOldestQueue) -> None:
        with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
        queue.close()

    def publish(self, record: Any) -> None:
        with self._lock:
            if self._closed:
                return
            subscribers = list(self._subscribers)
        for queue in subscribers:
            queue.put(record)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            subscribers = list(self._subscribers)
            self._subscribers.clear()
        for queue in subscribers:
            queue.close()
