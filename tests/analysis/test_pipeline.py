import numpy as np

from vigil.analysis.gallery import Gallery
from vigil.analysis.pipeline import InferenceWorker, OverlayStore
from vigil.analysis.unknowns import StrangerGrouper
from vigil.config.models import FaceConfig, VigilConfig
from vigil.core.records import Frame, OverlayItem
from tests.support import FakeBackend, unit


class RecordingBus:
    def __init__(self):
        self.records = []

    def publish(self, record):
        self.records.append(record)


class NoEmbedBackend(FakeBackend):
    can_embed = False

    def embed(self, image, rect):
        raise AssertionError("embed must not be called when recognition is unavailable")


class NoSnapshots:
    def save(self, image, camera_id, when=None):
        return {
            "path": "snapshot.jpg",
            "sha256": "0" * 64,
            "width": 80,
            "height": 80,
            "created_at": when or 0.0,
        }


def make_worker(backend, gallery=None, camera_id="front", **face_overrides):
    face = FaceConfig(**face_overrides)
    config = VigilConfig()
    config.face = face
    bus = RecordingBus()
    worker = InferenceWorker(
        queue=None,
        config=config,
        backend=backend,
        gallery=gallery or Gallery(),
        grouper=StrangerGrouper(
            window_s=face.unknown_merge_window_s,
            threshold=face.unknown_merge_threshold,
        ),
        bus=bus,
        snapshot_store=NoSnapshots(),
        overlays=OverlayStore(),
        names={1: "Ann", 2: "Bob"},
    )
    return worker, bus


def frame(index, captured_at, image=None, camera_id="front"):
    if image is None:
        image = np.random.randint(0, 255, (120, 120, 3), dtype=np.uint8)
    return Frame(camera_id, index, captured_at, captured_at, image, 120, 120)


def test_known_face_produces_one_event_per_tracklet():
    gallery = Gallery()
    gallery.add(1, unit([1, 0, 0]))
    worker, bus = make_worker(FakeBackend(vector=[1, 0, 0]), gallery=gallery)

    events = []
    for index in range(3):
        events += worker.process(frame(index, 0.0 + index * 0.2))
    assert events == []

    # A long gap closes the tracklet and emits its single decision.
    events = worker.process(frame(9, 5.0))
    assert len(events) == 1
    assert events[0].type == "known_face"
    assert events[0].person_id == 1
    assert events[0].detail["tracklet"]["n_obs"] == 3


def test_small_face_is_tracked_but_not_embedded():
    backend = FakeBackend(vector=[1, 0, 0], rects=[(10, 10, 40, 40)])
    worker, bus = make_worker(backend)
    events = []
    for index in range(2):
        events += worker.process(frame(index, 0.0 + index * 0.2))
    events += worker.process(frame(9, 5.0))

    assert backend.embed_calls == 0
    assert len(events) == 1
    assert events[0].type == "uncertain_face"


def test_detection_without_embeddings_is_a_stranger():
    worker, bus = make_worker(NoEmbedBackend())

    assert worker.process(frame(0, 0.0)) == []
    events = worker.process(frame(9, 5.0))

    assert len(events) == 1
    assert events[0].type == "stranger"
    assert events[0].detail["tracklet"]["decision"] == "unknown"


def test_detection_only_overlay_says_unknown():
    worker, _bus = make_worker(NoEmbedBackend())
    worker.process(frame(0, 0.0))

    items = worker.overlays.get("front", now=0.5)
    assert [item.label for item in items] == ["Unknown"]
    assert [item.kind for item in items] == ["unknown"]


def test_empty_gallery_with_working_recognition_is_a_stranger():
    worker, _bus = make_worker(FakeBackend(vector=[0, 1, 0]), gallery=Gallery())

    assert worker.process(frame(0, 0.0)) == []
    events = worker.process(frame(9, 5.0))

    assert len(events) == 1
    assert events[0].type == "stranger"


def test_unknown_visits_group_into_one_cluster():
    backend = FakeBackend(vector=[0, 1, 0])
    worker, bus = make_worker(backend, gallery=Gallery())
    worker.process(frame(0, 0.0))
    first = worker.process(frame(1, 2.0))

    worker.process(frame(2, 3.0))
    second = worker.process(frame(3, 5.0))

    assert first[0].type == "stranger"
    assert second[0].type == "stranger"
    assert first[0].detail["unknown_cluster"]["n_visits"] == 1
    assert first[0].unknown_cluster_id == second[0].unknown_cluster_id


def test_reconfigure_keeps_the_live_grouper():
    worker, _bus = make_worker(FakeBackend())
    grouper = worker._grouper

    worker._config.face.unknown_merge_window_s = 120.0
    worker._config.face.unknown_merge_threshold = 0.5
    worker.reconfigure(worker._config)

    assert worker._grouper is grouper
    assert grouper.window_s == 120.0
    assert grouper.threshold == 0.5


def test_overlay_ttl_expires():
    overlays = OverlayStore()
    overlays.put("front", [OverlayItem("front", (0, 0, 10, 10), "Ann", "known", 0)], ttl=1.0, now=100.0)
    assert overlays.get("front", now=100.5)
    assert overlays.get("front", now=102.0) == []


def test_stop_finalises_open_tracklets():
    gallery = Gallery()
    gallery.add(1, unit([1, 0, 0]))
    worker, bus = make_worker(FakeBackend(vector=[1, 0, 0]), gallery=gallery)
    worker.process(frame(0, 0.0))
    worker.process(frame(1, 0.2))
    worker.stop()
    assert len(bus.records) == 1
    assert bus.records[0].type == "known_face"
