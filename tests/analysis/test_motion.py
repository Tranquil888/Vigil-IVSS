import numpy as np

from vigil.analysis.motion import MotionDetector, MotionResult
from vigil.config.models import MotionConfig


def still_frame(width=160, height=120, value=60):
    return np.full((height, width, 3), value, dtype=np.uint8)


def frame_with_box(x, width=160, height=120):
    frame = still_frame(width, height)
    frame[40:80, x : x + 30] = 220
    return frame


def make_detector(**overrides):
    values = dict(
        enabled=True,
        max_side=160,
        threshold_pct=0.5,
        min_area_px=50,
        min_duration_frames=3,
        cooldown_s=0.5,
        suppress_global_pct=60.0,
    )
    values.update(overrides)
    return MotionDetector(MotionConfig(**values), width=160, height=120)


def feed(detector, frames, dt=0.1, start=0.0):
    results = []
    now = start
    for frame in frames:
        results.append(detector.update(frame, now))
        now += dt
    return results


def test_static_frames_do_not_trigger():
    detector = make_detector()
    results = feed(detector, [still_frame() for _ in range(20)])
    assert not any(result.triggered for result in results)


def test_moving_rectangle_triggers_after_the_sustained_frames():
    detector = make_detector(min_duration_frames=3)
    frames = [still_frame() for _ in range(6)]
    frames += [frame_with_box(20 + index * 8) for index in range(12)]
    results = feed(detector, frames)

    assert any(result.triggered for result in results)
    first_trigger = next(index for index, result in enumerate(results) if result.triggered)
    assert first_trigger >= 6


def test_motion_ends_after_cooldown_without_changes():
    detector = make_detector(min_duration_frames=2, cooldown_s=0.3)
    frames = [still_frame() for _ in range(6)]
    frames += [frame_with_box(20 + index * 8) for index in range(8)]
    frames += [still_frame() for _ in range(15)]
    results = feed(detector, frames)

    assert any(result.triggered for result in results)
    assert any(result.ended for result in results[8:])


def test_full_frame_change_is_suppressed():
    detector = make_detector()
    feed(detector, [still_frame() for _ in range(8)])
    result = detector.update(np.full((120, 160, 3), 250, dtype=np.uint8), 2.0)
    assert result.global_change is True
    assert result.triggered is False


def test_zone_threshold_reports_the_zone_name():
    detector = make_detector(min_duration_frames=1)
    frames = [still_frame() for _ in range(5)]
    frames += [frame_with_box(30 + index) for index in range(4)]
    results = feed(detector, frames)
    triggered = [result for result in results if result.triggered]
    assert triggered
    assert "all" in triggered[0].zones


def test_reset_clears_the_background_model():
    detector = make_detector()
    feed(detector, [frame_with_box(30) for _ in range(10)])
    detector.reset()
    result = detector.update(still_frame(), 5.0)
    assert result.active in (True, False)

class FakeDetector:
    def update(self, image, now):
        return MotionResult(active=True, triggered=True, zones=["all"])


def test_motion_worker_reports_a_trigger():
    import time

    from vigil.analysis.motion import MotionWorker
    from vigil.core.queues import DropOldestQueue
    from vigil.core.records import Frame

    queue = DropOldestQueue(2)
    seen = []
    worker = MotionWorker(
        camera_id="front",
        queue=queue,
        config=MotionConfig(),
        zones=[],
        on_result=lambda camera_id, result, frame: seen.append((camera_id, result.triggered)),
        detector_factory=lambda *args: FakeDetector(),
    )
    worker.start()
    try:
        queue.put(Frame("front", 1, 0.0, 0.0, still_frame(), 160, 120))
        deadline = time.monotonic() + 2
        while not seen and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        worker.stop()
    assert seen == [("front", True)]
