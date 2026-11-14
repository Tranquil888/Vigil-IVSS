import cv2
import numpy as np
import pytest

from tools import video_latency_probe as probe


def write_video(path, frames=30, fps=15.0):
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (320, 240)
    )
    assert writer.isOpened()
    try:
        for index in range(frames):
            frame = np.full((240, 320, 3), 30, dtype=np.uint8)
            frame[80:160, 40 + index * 4 : 120 + index * 4] = 220
            writer.write(frame)
    finally:
        writer.release()
    return path


def test_resolve_videos_takes_the_requested_count_from_a_folder(tmp_path):
    first = write_video(tmp_path / "a.avi")
    second = write_video(tmp_path / "b.avi")
    third = write_video(tmp_path / "c.avi")
    chosen = probe.resolve_videos([], str(tmp_path), 2)
    assert [path.name for path in chosen] == [first.name, second.name]
    assert third.exists()


def test_resolve_videos_rejects_too_few_files(tmp_path):
    write_video(tmp_path / "only.avi")
    with pytest.raises(ValueError):
        probe.resolve_videos([], str(tmp_path), 4)


def test_build_config_puts_each_video_on_its_own_camera(tmp_path):
    paths = [tmp_path / "a.avi", tmp_path / "b.avi"]
    config = probe.build_config(paths, queue_size=3, analysis_fps=4.0)
    assert [camera.id for camera in config.cameras] == ["video-1", "video-2"]
    assert [camera.source for camera in config.cameras] == [str(p) for p in paths]
    assert config.inference.queue_size == 3
    assert config.inference.analysis_fps == 4.0
    assert config.motion.enabled is False


def test_summarize_reports_percentiles():
    report = probe.summarize([10.0, 20.0, 30.0, 40.0], 2.0)
    assert report["p50"] == 25.0
    assert report["max"] == 40.0
    assert report["n"] == 4
    assert report["duration_s"] == 2.0
    with pytest.raises(RuntimeError):
        probe.summarize([], 1.0)


@pytest.mark.e2e
def test_two_video_cameras_keep_display_latency_while_inference_drops(tmp_path):
    paths = [write_video(tmp_path / "a.avi"), write_video(tmp_path / "b.avi")]
    report = probe.probe(
        paths,
        seconds=1.5,
        display_interval_ms=15.0,
        inference_delay_ms=200.0,
        queue_size=1,
        analysis_fps=5.0,
    )
    assert report["display"]["n"] > 20
    assert report["display"]["p95"] < 400.0
    assert report["inference_dropped"] > 0
    assert all(camera["reconnects"] == 0 for camera in report["cameras"])
