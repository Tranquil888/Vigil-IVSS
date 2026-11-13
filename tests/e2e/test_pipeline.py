"""End-to-end event path: source, motion, inference, bus, SQLite.

These tests use the real composition root and the real database. Only the
camera and the face backend are fakes, because a GPU and a webcam do not
belong in a deterministic suite.
"""

from __future__ import annotations

import time

import cv2
import numpy as np
import pytest
from sqlalchemy import select

from tests.support import FakeBackend
from vigil.analysis.backend import BackendStatus
from vigil.config.models import (
    CameraConfig,
    CaptureConfig,
    FaceConfig,
    InferenceConfig,
    MotionConfig,
    VigilConfig,
    ZoneConfig,
)
from vigil.core.app_context import AppContext
from vigil.core.records import EventType
from vigil.storage.schema import camera as camera_table
from vigil.video.source import FakeSource

pytestmark = pytest.mark.e2e


def build_config(offline_notify_after_s: float = 999.0) -> VigilConfig:
    return VigilConfig(
        cameras=[
            CameraConfig(
                id="front",
                name="Front door",
                source="fake://",
                zones=[
                    ZoneConfig(
                        name="yard",
                        points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
                    )
                ],
            )
        ],
        motion=MotionConfig(
            enabled=True,
            sample_every=1,
            max_side=160,
            threshold_pct=0.5,
            min_area_px=20,
            min_duration_frames=2,
            cooldown_s=0.2,
            suppress_global_pct=90.0,
        ),
        inference=InferenceConfig(
            analysis_fps=20.0,
            queue_size=4,
            max_frame_age_s=10.0,
        ),
        face=FaceConfig(
            min_face_px=32,
            min_face_px_embed=32,
            min_votes=2,
            track_max_gap_s=0.2,
            min_tracklet_observations=1,
            best_k=5,
        ),
        capture=CaptureConfig(
            stall_timeout_s=0.3,
            backoff_initial_s=0.01,
            backoff_max_s=0.02,
            backoff_jitter=0.0,
            offline_notify_after_s=offline_notify_after_s,
        ),
    )


FACE_RECT = (70, 60, 70, 70)


def moving_frame(index: int) -> np.ndarray:
    frame = np.full((200, 200, 3), 18, dtype=np.uint8)
    left = 20 + (index * 6) % 90
    cv2.rectangle(frame, (left, 60), (left + 50, 110), (240, 240, 240), -1)
    rng = np.random.default_rng(index)
    noise = rng.integers(0, 255, (FACE_RECT[3], FACE_RECT[2], 3), dtype=np.uint8)
    frame[
        FACE_RECT[1] : FACE_RECT[1] + FACE_RECT[3],
        FACE_RECT[0] : FACE_RECT[0] + FACE_RECT[2],
    ] = noise
    return frame


def camera_factory():
    return FakeSource(read_delay=1.0 / 30.0, frame_factory=moving_frame)


def test_motion_and_stranger_reach_sqlite(tmp_path):
    context = AppContext(
        build_config(),
        data_path=tmp_path,
        source_factory=lambda camera: camera_factory(),
        backend=FakeBackend(rects=[FACE_RECT]),
    )

    try:
        context.start()
        time.sleep(1.5)
        live_events = context.reader.events()
        assert any(row["type"] == EventType.MOTION for row in live_events)
        assert context.manager.display_queue("front").generation > 0
    finally:
        context.shutdown(timeout=5.0)

    events = context.reader.events()
    types = {row["type"] for row in events}
    assert EventType.MOTION in types
    assert EventType.STRANGER in types

    stranger = next(row for row in events if row["type"] == EventType.STRANGER)
    assert stranger["tracklet_id"] is not None
    assert stranger["snapshot_id"] is not None
    assert stranger["unknown_cluster_id"] is not None
    assert context.reader.tracklets()
    assert context.reader.snapshots()
    assert context.reader.unknown_clusters()


class UnavailableBackend:
    status = BackendStatus(False, False, "none", "recognition disabled in this test")
    can_embed = False

    def __init__(self):
        self.detect_calls = 0

    def detect(self, image):
        self.detect_calls += 1
        return []

    def embed(self, image, rect):
        raise AssertionError("an unavailable backend must not embed")


def test_unavailable_backend_keeps_motion_and_display(tmp_path):
    backend = UnavailableBackend()
    context = AppContext(
        build_config(),
        data_path=tmp_path,
        source_factory=lambda camera: camera_factory(),
        backend=backend,
    )

    try:
        context.start()
        time.sleep(1.2)
        assert context.manager.display_queue("front").generation > 0
        events = context.reader.events()
        assert any(row["type"] == EventType.MOTION for row in events)
        assert not any(
            row["type"]
            in (EventType.KNOWN_FACE, EventType.STRANGER, EventType.UNCERTAIN_FACE)
            for row in events
        )
    finally:
        context.shutdown(timeout=5.0)

    assert backend.detect_calls == 0


def test_camera_offline_and_online_reach_the_event_log(tmp_path):
    attempts = {"count": 0}

    def factory(camera):
        attempts["count"] += 1
        if attempts["count"] <= 2:
            return FakeSource(frame_count=5, open_failures=1)
        return FakeSource(frame_count=200, read_delay=1.0 / 30.0)

    context = AppContext(
        build_config(offline_notify_after_s=0.0),
        data_path=tmp_path,
        source_factory=factory,
        backend=UnavailableBackend(),
    )

    try:
        context.start()
        time.sleep(1.0)
    finally:
        context.shutdown(timeout=5.0)

    types = {row["type"] for row in context.reader.events()}
    assert EventType.CAMERA_OFFLINE in types
    assert EventType.CAMERA_ONLINE in types


def test_restart_keeps_the_event_log_and_one_camera_row(tmp_path):
    first = AppContext(
        build_config(),
        data_path=tmp_path,
        source_factory=lambda camera: camera_factory(),
        backend=FakeBackend(rects=[FACE_RECT]),
    )
    try:
        first.start()
        time.sleep(1.2)
    finally:
        first.shutdown(timeout=5.0)
    before = first.reader.count_events()
    assert before > 0

    second = AppContext(
        build_config(),
        data_path=tmp_path,
        source_factory=lambda camera: FakeSource(open_failures=999),
        backend=UnavailableBackend(),
    )
    try:
        second.start()
        time.sleep(0.3)
    finally:
        second.shutdown(timeout=3.0)

    assert second.reader.count_events() >= before
    with second.database.engine.connect() as conn:
        rows = [dict(row._mapping) for row in conn.execute(select(camera_table))]
    assert [row["id"] for row in rows] == ["front"]
