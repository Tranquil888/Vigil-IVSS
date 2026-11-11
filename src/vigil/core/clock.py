"""Time helpers. Monotonic for pipelines, wall clock for records."""

from __future__ import annotations

import time
from datetime import datetime, timezone


def monotonic() -> float:
    return time.monotonic()


def wall_time() -> float:
    return time.time()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="milliseconds")
