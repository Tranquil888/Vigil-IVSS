import importlib.util
import io
import json
import tarfile
from pathlib import Path

import cv2
import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_chokepoint.py"


def load_script():
    spec = importlib.util.spec_from_file_location("build_chokepoint", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_script()


def pgm_bytes(seed):
    rng = np.random.default_rng(seed)
    image = rng.integers(0, 256, size=(96, 96), dtype=np.uint8)
    return cv2.imencode(".pgm", image)[1].tobytes()


def add(tar, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    tar.addfile(info, io.BytesIO(payload))


def build_tar(path):
    with tarfile.open(path, "w") as tar:
        for sequence, subject, frames in [
            ("P1E_S1_C1", "0001", range(1, 21)),
            ("P1E_S1_C1", "0003", range(21, 41)),
            ("P1L_S1_C1", "0001", range(1, 11)),
            ("P2E_S1_C1", "0001", range(1, 11)),
        ]:
            for frame in frames:
                add(
                    tar,
                    "%s/%s/%08d.pgm" % (sequence, subject, frame),
                    pgm_bytes(frame + len(subject)),
                )
        add(tar, "P1E_S1_C1/.directory", b"not an image")
    return path


def test_parse_member_rejects_noise_and_reads_frames():
    assert builder.parse_member("P1E_S1_C1/0003/00001930.pgm") == (
        "P1E_S1_C1",
        "0003",
        1930,
    )
    assert builder.parse_member("P1E_S1_C1/0003/readme.txt") is None
    assert builder.parse_member("P1E_S1_C1/0003/poster.jpg") is None
    assert builder.parse_member("P1E_S1_C1/0003") is None


def test_portal_labels_keep_portals_apart():
    assert builder.portal_of("P1E_S1_C1") == "P1"
    assert builder.portal_of("P2L_S4_C3") == "P2"
    assert builder.label_of("P1E_S1_C1", "0001") == "P1-0001"
    assert builder.label_of("P1L_S1_C1", "0001") == "P1-0001"
    assert builder.label_of("P2E_S1_C1", "0001") == "P2-0001"


def test_pick_evenly_spreads_across_the_whole_list():
    items = list(range(100))
    chosen = builder.pick_evenly(items, 5)
    assert chosen == [0, 20, 40, 60, 80]
    assert builder.pick_evenly(items, 0) == items
    assert builder.pick_evenly(items[:3], 5) == [0, 1, 2]


def test_contiguous_blocks_drops_sparse_tails():
    assert builder.contiguous_blocks([1, 2, 3, 10, 11, 12], min_length=3) == [
        [1, 2, 3],
        [10, 11, 12],
    ]
    assert builder.contiguous_blocks([1, 2, 3, 10], min_length=3) == [[1, 2, 3]]
    assert builder.contiguous_blocks([1, 5, 9], min_length=2) == []


def test_compose_frame_keeps_canvas_and_moves_the_face():
    face = np.full((96, 96, 3), 200, dtype=np.uint8)
    first = builder.compose_frame(face, 640, 480, 3, index=0)
    later = builder.compose_frame(face, 640, 480, 3, index=11)
    assert first.shape == (480, 640, 3)
    assert first.dtype == np.uint8
    assert not np.array_equal(first, later)


def test_build_writes_gallery_manifest_and_video(tmp_path):
    archive = build_tar(tmp_path / "faces.tar")
    faces = tmp_path / "gallery"
    videos = tmp_path / "videos"
    manifest = tmp_path / "manifest.json"

    code = builder.main(
        [
            "--archive",
            str(archive),
            "--faces-out",
            str(faces),
            "--videos-out",
            str(videos),
            "--manifest",
            str(manifest),
            "--faces-per-person",
            "2",
            "--video-max-frames",
            "40",
            "--video-max-count",
            "1",
            "--quiet",
        ]
    )

    assert code == 0
    assert sorted(path.name for path in faces.iterdir()) == [
        "P1-0001",
        "P1-0003",
        "P2-0001",
    ]
    assert len(list((faces / "P1-0001").glob("*.jpg"))) == 2
    assert len(list((faces / "P1-0003").glob("*.jpg"))) == 2

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["images"] == 6
    assert len(payload["videos"]) == 1
    assert payload["videos"][0]["sequence"] == "P1E_S1_C1"
    assert payload["videos"][0]["subjects"] == ["0001", "0003"]

    video = Path(payload["videos"][0]["path"])
    assert video.is_file()
    capture = cv2.VideoCapture(str(video))
    try:
        assert capture.isOpened()
        assert int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) == 640
        assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 40
    finally:
        capture.release()


def test_missing_archive_returns_a_clear_error(tmp_path):
    assert builder.main(["--archive", str(tmp_path / "absent.tar")]) == 2
