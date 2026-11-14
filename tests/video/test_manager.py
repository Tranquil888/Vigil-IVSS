import time

from vigil.config.models import CameraConfig, VigilConfig
from vigil.core.bus import EventBus
from vigil.video.manager import CameraManager
from vigil.video.source import FakeSource


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_manager_runs_each_enabled_camera_and_stops():
    config = VigilConfig(
        cameras=[
            CameraConfig(id="front", name="Front", source="fake://front"),
            CameraConfig(id="back", name="Back", source="fake://back"),
            CameraConfig(id="off", name="Off", source="fake://off", enabled=False),
        ]
    )
    manager = CameraManager(
        config,
        bus=EventBus(),
        source_factory=lambda camera: FakeSource(frame_count=100_000, read_delay=0.01),
    )
    manager.start_all()
    try:
        assert wait_for(
            lambda: all(manager.display_queue(cid).generation > 0 for cid in ("front", "back"))
        )
        assert set(manager.camera_ids) == {"front", "back"}
    finally:
        manager.stop_all(timeout=3)

    assert all(not supervisor.is_alive() for supervisor in manager._supervisors)


def test_start_all_can_be_called_twice():
    config = VigilConfig(
        cameras=[CameraConfig(id="front", name="Front", source="fake://front")]
    )
    manager = CameraManager(
        config,
        bus=EventBus(),
        source_factory=lambda camera: FakeSource(frame_count=100_000, read_delay=0.01),
    )
    manager.start_all()
    try:
        manager.start_all()
        assert wait_for(lambda: manager.display_queue("front").generation > 0)
        assert manager._supervisors[0].is_alive()
    finally:
        manager.stop_all(timeout=3)


def test_reconfigure_starts_a_camera_enabled_after_a_start_with_none():
    config = VigilConfig(
        cameras=[
            CameraConfig(id="front", name="Front", source="fake://front", enabled=False)
        ]
    )
    manager = CameraManager(
        config,
        bus=EventBus(),
        source_factory=lambda camera: FakeSource(frame_count=100_000, read_delay=0.01),
    )
    manager.start_all()
    try:
        assert manager.camera_ids == []
        config.cameras[0].enabled = True
        manager.reconfigure(config)

        assert manager.camera_ids == ["front"]
        assert wait_for(lambda: manager.display_queue("front").generation > 0)
    finally:
        manager.stop_all(timeout=3)


def test_reconfigure_restarts_the_live_workers():
    config = VigilConfig(
        cameras=[CameraConfig(id="front", name="Front", source="fake://front")]
    )
    manager = CameraManager(
        config,
        bus=EventBus(),
        source_factory=lambda camera: FakeSource(frame_count=100_000, read_delay=0.01),
    )
    manager.start_all()
    try:
        assert wait_for(lambda: manager.display_queue("front").generation > 0)

        config.motion.threshold_pct = 5.0
        manager.reconfigure(config)

        assert manager._supervisors[0].is_alive()
        assert wait_for(lambda: manager.display_queue("front").generation > 0)
    finally:
        manager.stop_all(timeout=3)


def test_start_all_starts_the_rest_when_one_worker_raises():
    config = VigilConfig(
        cameras=[
            CameraConfig(id="front", name="Front", source="fake://front"),
            CameraConfig(id="back", name="Back", source="fake://back"),
        ]
    )
    manager = CameraManager(
        config,
        bus=EventBus(),
        source_factory=lambda camera: FakeSource(frame_count=100_000, read_delay=0.01),
    )
    broken = manager._supervisors[0]

    def boom():
        raise RuntimeError("boom")

    broken.start = boom
    manager.start_all()
    try:
        assert wait_for(lambda: manager.display_queue("back").generation > 0)
    finally:
        manager.stop_all(timeout=3)
