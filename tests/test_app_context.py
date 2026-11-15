import time

import cv2
import numpy as np
from sqlalchemy import select

from tests.support import FakeBackend
from vigil.config.loader import save_config
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


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


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


def write_photo(path):
    image = np.full((160, 160, 3), 90, dtype=np.uint8)
    cv2.imwrite(str(path), image)
    return path


def test_photo_import_stores_the_photo_without_recognition_models(tmp_path):
    backend = FakeBackend()
    backend.can_embed = False
    context = AppContext(build_config(), data_path=tmp_path, backend=backend)
    try:
        person_id = context.people_store.add("Ann")
        ok, message = context.add_person_photo(
            person_id, write_photo(tmp_path / "ann.jpg")
        )

        assert ok, message
        assert "saved" in message.lower()
        assert context.people_store.count_images(person_id) == 1
        assert context.embeddings.count() == 0
        assert list((tmp_path / "people").glob("person-*"))
    finally:
        context.shutdown(timeout=1.0)


def test_rebuild_embeddings_fills_vectors_for_stored_photos(tmp_path):
    backend = FakeBackend(vector=[1, 0, 0])
    backend.can_embed = False
    context = AppContext(build_config(), data_path=tmp_path, backend=backend)
    try:
        person_id = context.people_store.add("Ann")
        assert context.add_person_photo(person_id, write_photo(tmp_path / "ann.jpg"))[0]

        backend.can_embed = True
        result = context.rebuild_embeddings()

        assert result["embedded"] == 1
        assert result["failed"] == 0
        assert result["people"] == 1
        assert context.embeddings.count() == 1
        assert context.gallery.person_ids() == [person_id]
    finally:
        context.shutdown(timeout=1.0)


def test_importing_the_same_photo_twice_keeps_one_copy(tmp_path):
    backend = FakeBackend(vector=[1, 0, 0])
    context = AppContext(build_config(), data_path=tmp_path, backend=backend)
    try:
        person_id = context.people_store.add("Ann")
        photo = write_photo(tmp_path / "ann.jpg")

        assert context.add_person_photo(person_id, photo)[0]
        ok, message = context.add_person_photo(person_id, photo)

        assert ok, message
        assert "already" in message.lower()
        assert context.people_store.count_images(person_id) == 1
        assert context.embeddings.count() == 1
    finally:
        context.shutdown(timeout=1.0)


def test_apply_config_adds_a_camera_without_a_restart(tmp_path):
    config = build_config()
    config.cameras.append(
        CameraConfig(id="rear", name="Rear door", source="fake", enabled=False)
    )
    context = AppContext(config, data_path=tmp_path, backend=FakeBackend())
    try:
        assert context.manager.camera_ids == ["front"]

        config.camera("rear").enabled = True
        summary = context.apply_config()

        assert summary["cameras_rebuilt"] is True
        assert summary["cameras"] == 2
        assert context.manager.camera_ids == ["front", "rear"]
    finally:
        context.shutdown(timeout=1.0)


def test_apply_config_starts_the_first_camera_enabled_after_start(tmp_path):
    config = build_config()
    config.cameras[0].enabled = False
    context = AppContext(
        config,
        data_path=tmp_path,
        source_factory=lambda camera: FakeSource(
            read_delay=0.01, frame_factory=noisy_frame
        ),
        backend=FakeBackend(),
    )
    try:
        context.start()
        assert context.manager.camera_ids == []

        config.cameras[0].enabled = True
        summary = context.apply_config()

        assert summary["cameras"] == 1
        assert wait_for(
            lambda: context.manager._supervisors[0].is_alive()
            and context.manager.display_queue("front").generation > 0
        )
    finally:
        context.shutdown(timeout=2.0)


def test_apply_config_rebuilds_when_the_global_motion_section_changes(tmp_path):
    context = AppContext(build_config(), data_path=tmp_path, backend=FakeBackend())
    try:
        context.config.motion.threshold_pct = 4.5
        summary = context.apply_config()

        assert summary["cameras_rebuilt"] is True
        assert context.config.motion.threshold_pct == 4.5
    finally:
        context.shutdown(timeout=1.0)


def test_apply_config_updates_fps_and_queue_size_in_place(tmp_path):
    context = AppContext(build_config(), data_path=tmp_path, backend=FakeBackend())
    try:
        context.config.inference.analysis_fps = 12.0
        context.config.inference.queue_size = 8
        summary = context.apply_config()

        assert summary["cameras_rebuilt"] is False
        assert context.manager.inference_queue.maxsize == 8
        assert context.manager._supervisors[0]._sampler.interval == 1.0 / 12.0
        assert context.inference.stats()["backend"] == "fake"
    finally:
        context.shutdown(timeout=1.0)


def test_apply_config_pushes_face_thresholds_into_the_worker(tmp_path):
    context = AppContext(build_config(), data_path=tmp_path, backend=FakeBackend())
    try:
        context.config.face.track_iou = 0.5
        context.config.face.unknown_threshold = 0.6
        context.config.face.known_threshold = 0.45
        context.apply_config()

        assert context.inference._face.known_threshold == 0.45
        assert context.inference._face.unknown_threshold == 0.6
        assert context.inference._face.track_iou == 0.5
    finally:
        context.shutdown(timeout=1.0)


def test_inference_and_notifier_share_the_live_name_map(tmp_path):
    context = AppContext(build_config(), data_path=tmp_path, backend=FakeBackend())
    try:
        assert context.inference._names is context.names
        assert context.notifier._names is context.names

        context.remember_person(7, "Ann")

        assert context.inference._names[7] == "Ann"
        assert context.notifier._names[7] == "Ann"
    finally:
        context.shutdown(timeout=1.0)


def test_reload_config_reads_the_file_and_applies(tmp_path):
    config = build_config()
    path = tmp_path / "config.toml"
    save_config(path, config)
    context = AppContext(config, data_path=tmp_path, backend=FakeBackend())
    try:
        edited = config.model_copy(deep=True)
        edited.inference.analysis_fps = 9.0
        edited.cameras.append(
            CameraConfig(id="rear", name="Rear door", source="fake")
        )
        save_config(path, edited)

        summary = context.reload_config(path)

        assert summary["cameras_rebuilt"] is True
        assert summary["cameras"] == 2
        assert context.config.inference.analysis_fps == 9.0
        assert context.manager.camera_ids == ["front", "rear"]
        assert context.manager._supervisors[0]._sampler.interval == 1.0 / 9.0
    finally:
        context.shutdown(timeout=1.0)


def test_default_backend_uses_the_context_data_path_for_models(tmp_path):
    context = AppContext(build_config(), data_path=tmp_path)
    try:
        assert context.backend.models_dir == tmp_path / "models"
    finally:
        context.shutdown(timeout=1.0)


def test_explicit_models_dir_wins_over_the_data_path(tmp_path):
    config = build_config()
    config.face.models_dir = str(tmp_path / "custom-models")
    context = AppContext(config, data_path=tmp_path)
    try:
        assert context.backend.models_dir == tmp_path / "custom-models"
    finally:
        context.shutdown(timeout=1.0)


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


def test_context_resolves_a_vault_camera_source(tmp_path):
    from vigil.secrets import VAULT_SOURCE, SecretStore

    rtsp = "rtsp://operator:s3cret@10.0.0.5/stream"
    store = SecretStore(tmp_path)
    store.set("front", rtsp)
    config = build_config()
    config.cameras[0].source = VAULT_SOURCE

    seen = []
    context = AppContext(
        config,
        data_path=tmp_path,
        source_factory=lambda camera: seen.append(camera.source) or FakeSource(),
        backend=FakeBackend(),
    )
    try:
        assert context.config.cameras[0].source == rtsp
        context.start()
        assert seen and seen[0] == rtsp
    finally:
        context.shutdown(timeout=3.0)
