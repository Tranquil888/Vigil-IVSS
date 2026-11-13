"""Latency harness for the display path.

The number that matters is frame age at the display consumer: the time
between a frame being captured and the moment the newest frame is read.
Inference runs on its own queue, so a slow model must change that number
by less than a scheduling jitter.

Run it with::

    python tools/latency_harness.py --seconds 10 --with-inference-delay 150

``simulated=True`` advances a virtual clock in event order and is used by
the regression tests. The default runs real threads against the real
``LatestFrame`` and ``DropOldestQueue``.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vigil.core.queues import DropOldestQueue, LatestFrame  # noqa: E402
from vigil.core.records import Frame  # noqa: E402

CAMERA_ID = "latency-benchmark"
INFERENCE_QUEUE_SIZE = 4


@dataclass(frozen=True)
class LatencyReport:
    """Frame-age percentiles in milliseconds."""

    p50: float
    p95: float
    p99: float
    max: float
    n: int
    duration_s: float
    fps: float
    display_interval_ms: float
    inference_delay_ms: float

    def as_dict(self) -> dict:
        return asdict(self)


def percentile(values: List[float], fraction: float) -> float:
    if not values:
        raise ValueError("cannot take a percentile of no samples")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = min(max(fraction, 0.0), 1.0) * (len(ordered) - 1)
    low = int(math.floor(rank))
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _report(
    samples: List[float],
    duration_s: float,
    fps: float,
    display_interval_ms: float,
    inference_delay_ms: float,
) -> LatencyReport:
    if not samples:
        raise RuntimeError("no frames reached the display consumer")
    return LatencyReport(
        p50=percentile(samples, 0.50),
        p95=percentile(samples, 0.95),
        p99=percentile(samples, 0.99),
        max=max(samples),
        n=len(samples),
        duration_s=duration_s,
        fps=fps,
        display_interval_ms=display_interval_ms,
        inference_delay_ms=inference_delay_ms,
    )


def _simulated_samples(
    duration_s: float,
    fps: float,
    display_interval_ms: float,
) -> List[float]:
    """Advance virtual time in event order through the real queue objects.

    Frame production and display polling are interleaved exactly as a
    scheduler would: a frame is published just before a poll that lands on
    or after its capture time. Inference is published to a separate queue
    that the display never reads, so its delay cannot enter this timeline.
    """
    latest = LatestFrame()
    inference = DropOldestQueue(maxsize=INFERENCE_QUEUE_SIZE)
    frame_interval = 1.0 / max(1.0, fps)
    poll_interval = max(0.001, display_interval_ms / 1000.0)

    samples: List[float] = []
    next_frame_at = 0.0
    next_poll_at = 0.0
    index = 0

    while next_poll_at < duration_s:
        while next_frame_at <= next_poll_at + 1e-12:
            frame = Frame(
                CAMERA_ID, index, next_frame_at, next_frame_at, None
            )
            latest.put(frame)
            inference.put(frame)
            index += 1
            next_frame_at += frame_interval

        frame = latest.latest()
        if frame is not None:
            samples.append(max(0.0, (next_poll_at - frame.captured_at) * 1000.0))
        next_poll_at += poll_interval

    return samples


def _real_time_samples(
    duration_s: float,
    fps: float,
    display_interval_ms: float,
    inference_delay_ms: float,
    clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> List[float]:
    latest = LatestFrame()
    inference = DropOldestQueue(maxsize=INFERENCE_QUEUE_SIZE)
    stop = threading.Event()
    samples: List[float] = []
    sample_lock = threading.Lock()

    def produce() -> None:
        frame_interval = 1.0 / max(1.0, fps)
        deadline = clock()
        index = 0
        while not stop.is_set():
            captured_at = clock()
            frame = Frame(
                CAMERA_ID, index, captured_at, time.time(), None
            )
            latest.put(frame)
            inference.put(frame)
            index += 1
            deadline += frame_interval
            wait = deadline - clock()
            if wait > 0:
                sleep(wait)

    def consume_inference() -> None:
        while not stop.is_set():
            frame = inference.get(timeout=0.02)
            if frame is None:
                continue
            if inference_delay_ms > 0:
                sleep(inference_delay_ms / 1000.0)

    producer = threading.Thread(target=produce, name="latency-producer", daemon=True)
    consumer = threading.Thread(
        target=consume_inference, name="latency-inference", daemon=True
    )
    producer.start()
    consumer.start()

    poll_interval = max(0.001, display_interval_ms / 1000.0)
    deadline = clock() + duration_s
    next_poll = clock()
    try:
        while clock() < deadline:
            frame = latest.latest()
            if frame is not None:
                age_ms = max(0.0, (clock() - frame.captured_at) * 1000.0)
                with sample_lock:
                    samples.append(age_ms)
            next_poll += poll_interval
            wait = next_poll - clock()
            if wait > 0:
                sleep(wait)
    finally:
        stop.set()
        producer.join(timeout=1.0)
        consumer.join(timeout=1.0)

    return samples


def measure(
    duration_s: float = 10.0,
    fps: float = 30.0,
    inference_delay_ms: float = 0.0,
    display_interval_ms: float = 15.0,
    simulated: bool = False,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> LatencyReport:
    """Return the frame-age distribution seen by the display consumer."""
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    if fps <= 0:
        raise ValueError("fps must be positive")
    display_interval_ms = max(1.0, float(display_interval_ms))

    if simulated:
        samples = _simulated_samples(duration_s, fps, display_interval_ms)
    else:
        samples = _real_time_samples(
            duration_s,
            fps,
            display_interval_ms,
            max(0.0, inference_delay_ms),
            clock,
            sleep,
        )

    return _report(
        samples,
        duration_s,
        fps,
        display_interval_ms,
        max(0.0, inference_delay_ms),
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure frame age at the display consumer."
    )
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--display-interval-ms", type=float, default=15.0)
    parser.add_argument("--with-inference-delay", type=float, default=0.0)
    parser.add_argument(
        "--simulated",
        action="store_true",
        help="advance a virtual clock instead of sleeping in real time",
    )
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    parser.add_argument(
        "--max-p95",
        type=float,
        default=0.0,
        help="exit non-zero when p95 exceeds this many milliseconds",
    )
    args = parser.parse_args(argv)

    report = measure(
        duration_s=args.seconds,
        fps=args.fps,
        inference_delay_ms=args.with_inference_delay,
        display_interval_ms=args.display_interval_ms,
        simulated=args.simulated,
    )

    if args.json:
        print(json.dumps(report.as_dict()))
    else:
        print(
            "mode: %s, %.1f fps, display poll %.1f ms, inference delay %.0f ms"
            % (
                "simulated" if args.simulated else "real time",
                report.fps,
                report.display_interval_ms,
                report.inference_delay_ms,
            )
        )
        print("p50 %.1f ms" % report.p50)
        print("p95 %.1f ms" % report.p95)
        print("p99 %.1f ms" % report.p99)
        print("max %.1f ms" % report.max)
        print("samples %d over %.1f s" % (report.n, report.duration_s))

    if args.max_p95 > 0 and report.p95 > args.max_p95:
        print(
            "p95 %.1f ms exceeds the %.1f ms budget"
            % (report.p95, args.max_p95),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
