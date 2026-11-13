"""Plan step 3: a burned clock, a real capture thread, and a slow model.

The display consumer decodes the clock from the newest frame and compares
it with the source's presentation base. Inference is a separate thread that
sleeps 150 ms per frame, so the queue fills and drops frames. The display
must not notice.
"""

from __future__ import annotations

import threading
import time
from typing import List, Tuple

import pytest

from tools.latency_harness import percentile
from vigil.config.models import (
    CameraConfig,
    CaptureConfig,
    InferenceConfig,
    MotionConfig,
)
from vigil.core.queues import DropOldestQueue, LatestFrame
from vigil.video.capture import CameraSupervisor

from tests.e2e.clock_video import (
    PacedVideoSource,
    read_clock_ms,
    write_clock_video,
)

pytestmark = pytest.mark.e2e

FPS = 30.0
DISPLAY_INTERVAL_S = 0.015


def _run(
    video_path: str,
    seconds: float,
    inference_delay_ms: float,
) -> Tuple[List[float], int, dict]:
    source = PacedVideoSource(video_path, fps=FPS)
    latest = LatestFrame()
    inference = DropOldestQueue(4)
    motion = DropOldestQueue(2)

    supervisor = CameraSupervisor(
        camera=CameraConfig(id="clock", name="Clock", source="video"),
        capture_config=CaptureConfig(
            stall_timeout_s=1.0,
            backoff_initial_s=0.01,
            backoff_max_s=0.02,
            backoff_jitter=0.0,
            offline_notify_after_s=999.0,
        ),
        motion_config=MotionConfig(enabled=False),
        inference_config=InferenceConfig(
            analysis_fps=FPS,
            queue_size=4,
            max_frame_age_s=10.0,
        ),
        display=latest,
        motion_queue=motion,
        inference_queue=inference,
        source_factory=lambda: source,
        clock=time.monotonic,
    )

    stop = threading.Event()
    samples: List[float] = []

    def consume_inference() -> None:
        while not stop.is_set():
            frame = inference.get(timeout=0.02)
            if frame is None:
                continue
            if inference_delay_ms > 0:
                time.sleep(inference_delay_ms / 1000.0)

    supervisor.start()
    deadline = time.monotonic() + 2.0
    while source.base is None and time.monotonic() < deadline:
        time.sleep(0.001)

    consumer = threading.Thread(
        target=consume_inference, name="e2e-inference", daemon=True
    )
    consumer.start()

    started = time.monotonic()
    try:
        while time.monotonic() - started < seconds:
            frame = latest.latest()
            if frame is not None and frame.image is not None:
                burned = read_clock_ms(frame.image)
                if burned is not None and source.base is not None:
                    expected = source.base + burned / 1000.0
                    samples.append(max(0.0, (time.monotonic() - expected) * 1000.0))
            time.sleep(DISPLAY_INTERVAL_S)
    finally:
        stop.set()
        supervisor.stop(timeout=2.0)
        consumer.join(timeout=1.0)

    return samples, inference.dropped, supervisor.stats()


def test_display_latency_survives_a_150_ms_inference_delay(tmp_path):
    video = write_clock_video(
        str(tmp_path / "clock.avi"),
        frame_count=int(FPS * 3.5),
        fps=FPS,
        width=640,
        height=360,
    )

    baseline, _, baseline_stats = _run(video, 2.0, 0.0)
    delayed, dropped, delayed_stats = _run(video, 2.0, 150.0)

    assert len(baseline) >= 50, "the baseline display saw too few decoded frames"
    assert len(delayed) >= 50, "the delayed run saw too few decoded frames"
    assert baseline_stats["reconnects"] == 0
    assert delayed_stats["reconnects"] == 0
    assert delayed_stats["inference_sent"] > 0

    baseline_p95 = percentile(baseline, 0.95)
    delayed_p95 = percentile(delayed, 0.95)
    assert delayed_p95 - baseline_p95 < 50.0, (
        "inference delay reached the display: baseline p95 %.1f ms, "
        "delayed p95 %.1f ms" % (baseline_p95, delayed_p95)
    )
    assert dropped > 0, "the delayed inference queue never filled, so the test proved nothing"
