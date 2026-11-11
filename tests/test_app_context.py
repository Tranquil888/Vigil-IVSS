import time

import numpy as np
from sqlalchemy import select

from tests.support import FakeBackend
from vigil.config.models import (
    CameraConfig,
    InferenceConfig,
    MotionConfig,
    VigilConfig,
)
from vigil.core.app_context import AppContext
from vigil.storage.schema import camera as camera_table
from vigil.video.source import FakeSource


def build_config():
    return VigilConfig(
        cameras=[
            CameraConfig(id="front", name="Front door", source="fake"),
        ],
        motion=MotionConfig(enabled=False),
        inference=InferenceConfig(analysis_fps=20.0),
    )


def noisy_frame(index):
    rng = np.random.default_rng(index)
    return rng.integers(0, 255, (128, 128, 3), dtype=np.uint8)


def test_start_and_shutdown_join_every_thread(tmp_path):
    context = AppContext(
        build_config(),
        data_path=tmp_path,
        source_factory=lambda camera: FakeSource(
            read_delay=0.01, frame_factory=noisy_frame
        ),
        backend=FakeBackend(),
    )

    context.start()
    time.sleep(0.4)
    context.shutdown(timeout=5.0)

    for thread in context._threads():
        assert not thread.is_alive(), "%s is still running" % thread.name
    assert (tmp_path / "vigil.db").exists()


def test_shutdown_writes_the_final_tracklet(tmp_path):
    context = AppContext(
        build_config(),
        data_path=tmp_path,
        source_factory=lambda camera: FakeSource(
            read_delay=0.01, frame_factory=noisy_frame
        ),
        backend=FakeBackend(),
    )

    context.start()
    time.sleep(0.4)
    context.shutdown(timeout=5.0)

    events = context.reader.events()
    assert events, "the open tracklet should be closed and written on shutdown"
    assert events[0]["camera_id"] == "front"
    assert events[0]["type"] in ("stranger", "uncertain_face", "known_face")


def test_shutdown_is_idempotent(tmp_path):
    context = AppContext(
        build_config(),
        data_path=tmp_path,
        source_factory=lambda camera: FakeSource(
            read_delay=0.01, frame_factory=noisy_frame
        ),
        backend=FakeBackend(),
    )

    context.start()
    context.shutdown(timeout=2.0)
    context.shutdown(timeout=2.0)

    assert not context.db_writer.is_alive()


def test_start_seeds_the_camera_table(tmp_path):
    context = AppContext(
        build_config(),
        data_path=tmp_path,
        backend=FakeBackend(),
    )

    try:
        with context.database.engine.connect() as conn:
            rows = [dict(row._mapping) for row in conn.execute(select(camera_table))]
        assert [row["id"] for row in rows] == ["front"]
        assert rows[0]["name"] == "Front door"
    finally:
        context.shutdown(timeout=1.0)
