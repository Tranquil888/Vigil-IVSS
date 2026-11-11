from enum import Enum


class CameraState(Enum):
    INIT = "init"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    STALLED = "stalled"
    BACKOFF = "backoff"
    CLOSED = "closed"


class BackoffPolicy:
    def __init__(self, initial_s: float = 1.0, max_s: float = 60.0, jitter: float = 0.2):
        self.initial_s = float(initial_s)
        self.max_s = float(max_s)
        self.jitter = float(jitter)

    def delay(self, attempt: int) -> float:
        base = min(self.max_s, self.initial_s * (2.0 ** max(0, attempt)))
        if self.jitter <= 0:
            return base
        import random

        return base * (1.0 + random.uniform(-self.jitter, self.jitter))


class OfflineTracker:
    """Decides when a failing camera becomes an offline event, and when it returns."""

    def __init__(self, notify_after_s: float = 120.0) -> None:
        self.notify_after_s = float(notify_after_s)
        self.since = None
        self.notified = False

    def failure(self, now: float) -> bool:
        if self.since is None:
            self.since = now
        if not self.notified and now - self.since >= self.notify_after_s:
            self.notified = True
            return True
        return False

    def frame(self, now: float) -> bool:
        was_notified = self.notified
        self.since = None
        self.notified = False
        return was_notified
