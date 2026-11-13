"""The display path must never inherit inference latency."""

from __future__ import annotations

from tools.latency_harness import measure


def test_display_latency_stays_under_fifty_ms():
    report = measure(duration_s=10.0, fps=30.0, simulated=True)

    assert report.n >= 300
    assert report.p95 < 50.0


def test_percentiles_are_ordered():
    report = measure(duration_s=2.0, fps=30.0, simulated=True)

    assert 0.0 <= report.p50 <= report.p95 <= report.p99 <= report.max


def test_inference_backlog_does_not_touch_display_latency():
    baseline = measure(duration_s=10.0, fps=30.0, simulated=True)
    delayed = measure(
        duration_s=10.0, fps=30.0, inference_delay_ms=150.0, simulated=True
    )

    assert delayed.p95 - baseline.p95 < 50.0


def test_real_time_harness_collects_samples():
    report = measure(duration_s=0.4, fps=30.0, display_interval_ms=10.0)

    assert report.n > 0
    assert report.p95 >= report.p50
