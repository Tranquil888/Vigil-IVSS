import time

import numpy as np

from vigil.config.models import CameraConfig, CaptureConfig, InferenceConfig, MotionConfig
from vigil.core.queues import DropOldestQueue, LatestFrame
from vigil.video.capture import CameraSupervisor, FrameSampler
from vigil.video.source import FakeSource
from vigil.video.state import CameraState


def camera(camera_id="front"):
    return CameraConfig(id=camera_id, name="Front", source="fake://")


def capture_config(**overrides):
    values = dict(
        stall_timeout_s=0.2,
        backoff_initial_s=0.01,
        backoff_max_s=0.02,
        backoff_jitter=0.0,
        offline_notify_after_s=0.0,
    )
    values.update(overrides)
    return CaptureConfig(**values)


def inference_config():
    return InferenceConfig(analysis_fps=5.0, queue_size=4)


def test_frame_sampler_emits_at_the_configured_rate():
    sampler = FrameSampler(analysis_fps=5)
    timestamps = [index / 30.0 for index in range(60)]
    forwarded = [ts for ts in timestamps if sampler.due(ts)]
    assert len(forwarded) == 10
    assert forwarded[0] == 0.0


def test_sampler_reset_starts_a_fresh_interval():
    sampler = FrameSampler(analysis_fps=5)
    assert sampler.due(0.0) is True
    assert sampler.due(0.1) is False
    sampler.reset()
    assert sampler.due(0.1) is True


def test_display_gets_every_frame_and_inference_is_sampled():
    display = LatestFrame()
    motion = DropOldestQueue(2)
    inference = DropOldestQueue(4)
    source = FakeSource(frame_count=60, read_delay=1 / 30.0)
    supervisor = CameraSupervisor(
        camera=camera(),
        capture_config=capture_config(),
        motion_config=MotionConfig(enabled=False),
        inference_config=inference_config(),
        display=display,
        motion_queue=motion,
        inference_queue=inference,
        source_factory=lambda: source,
        max_frames=60,
    )
    supervisor.start()
    supervisor.join(5.0)

    assert not supervisor.is_alive()
    assert display.generation == 60
    # 60 frames at 30 fps over 2 s, sampled at 5 fps.
    assert 8 <= inference.qsize() + 0 <= 12


def test_supervisor_keeps_trying_after_open_failures():
    display = LatestFrame()
    attempts = {"count": 0}

    def factory():
        attempts["count"] += 1
        if attempts["count"] <= 2:
            return FakeSource(frame_count=1, open_failures=1)
        return FakeSource(frame_count=3)

    supervisor = CameraSupervisor(
        camera=camera(),
        capture_config=capture_config(),
        motion_config=MotionConfig(enabled=False),
        inference_config=inference_config(),
        display=display,
        motion_queue=DropOldestQueue(2),
        inference_queue=DropOldestQueue(4),
        source_factory=factory,
        max_frames=3,
    )
    supervisor.start()
    supervisor.join(5.0)

    assert attempts["count"] >= 3
    assert supervisor.stats()["reconnects"] >= 2
    assert display.generation == 3


def test_a_stalled_stream_is_reopened():
    display = LatestFrame()
    made = {"count": 0}

    def factory():
        made["count"] += 1
        if made["count"] == 1:
            return FakeSource(frame_count=100, stall_after=2)
        return FakeSource(frame_count=2)

    supervisor = CameraSupervisor(
        camera=camera(),
        capture_config=capture_config(stall_timeout_s=0.05),
        motion_config=MotionConfig(enabled=False),
        inference_config=inference_config(),
        display=display,
        motion_queue=DropOldestQueue(2),
        inference_queue=DropOldestQueue(4),
        source_factory=factory,
        max_frames=4,
    )
    supervisor.start()
    supervisor.join(5.0)

    assert CameraState.STALLED in supervisor.state_history
    assert made["count"] >= 2


def test_stop_closes_the_supervisor():
    supervisor = CameraSupervisor(
        camera=camera(),
        capture_config=capture_config(),
        motion_config=MotionConfig(enabled=False),
        inference_config=inference_config(),
        display=LatestFrame(),
        motion_queue=DropOldestQueue(2),
        inference_queue=DropOldestQueue(4),
        source_factory=lambda: FakeSource(frame_count=10_000, read_delay=0.01),
    )
    supervisor.start()
    time.sleep(0.05)
    supervisor.stop(timeout=2.0)
    assert not supervisor.is_alive()
    assert supervisor.state == CameraState.CLOSED
