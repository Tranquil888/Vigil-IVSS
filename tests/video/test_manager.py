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
