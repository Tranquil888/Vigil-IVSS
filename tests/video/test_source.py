import cv2
import numpy as np

from vigil.config.models import CameraConfig, VigilConfig
from vigil.video.manager import _default_factory
from vigil.video.source import OpenCVSource, VideoFileSource


def write_video(path, frames=5, value=30):
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        25.0,
        (64, 48),
    )
    assert writer.isOpened(), "the MJPG writer is not available"
    try:
        for index in range(frames):
            frame = np.full((48, 64, 3), value + index * 10, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()
    return str(path)


def test_video_file_source_loops(tmp_path):
    path = write_video(tmp_path / "clip.avi", frames=5)
    source = VideoFileSource([path], realtime=False)
    assert source.open()
    try:
        frames = [source.read() for _ in range(12)]
    finally:
        source.close()

    assert all(frame is not None for frame in frames)


def test_video_file_source_plays_a_playlist_in_order(tmp_path):
    first = write_video(tmp_path / "first.avi", frames=2, value=20)
    second = write_video(tmp_path / "second.avi", frames=2, value=200)
    source = VideoFileSource([first, second], realtime=False)
    assert source.open()
    try:
        means = [float(source.read().mean()) for _ in range(4)]
    finally:
        source.close()

    assert means[0] < 100 and means[1] < 100
    assert means[2] > 150 and means[3] > 150


def test_video_file_source_skips_a_missing_file(tmp_path):
    path = write_video(tmp_path / "clip.avi", frames=3)
    source = VideoFileSource(
        [str(tmp_path / "missing.mp4"), path], realtime=False
    )
    assert source.open()
    try:
        assert source.read() is not None
    finally:
        source.close()


def test_video_file_source_ends_when_not_looping(tmp_path):
    path = write_video(tmp_path / "clip.avi", frames=3)
    source = VideoFileSource([path], loop=False, realtime=False)
    assert source.open()
    try:
        frames = 0
        while source.read() is not None and frames < 10:
            frames += 1
    finally:
        source.close()

    assert frames == 3


def test_default_factory_uses_a_playlist_for_multiple_lines():
    camera = CameraConfig(
        id="clip", name="Clip", source="C:\\clips\\a.mp4\nC:\\clips\\b.mp4"
    )
    source = _default_factory(VigilConfig())(camera)

    assert isinstance(source, VideoFileSource)
    assert source.paths == ["C:\\clips\\a.mp4", "C:\\clips\\b.mp4"]


def test_default_factory_uses_the_video_source_for_one_file():
    camera = CameraConfig(id="clip", name="Clip", source="C:\\clips\\a.mp4")

    assert isinstance(_default_factory(VigilConfig())(camera), VideoFileSource)


def test_default_factory_keeps_a_camera_index():
    camera = CameraConfig(id="cam", name="Cam", source="0")

    assert isinstance(_default_factory(VigilConfig())(camera), OpenCVSource)
