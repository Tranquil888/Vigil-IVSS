import pytest
from pydantic import ValidationError

from vigil.config.models import CameraConfig, VigilConfig, ZoneConfig


def test_defaults_match_the_plan():
    cfg = VigilConfig()
    assert cfg.inference.analysis_fps == 5
    assert cfg.inference.device == "auto"
    assert cfg.face.detector == "dlib_cnn"
    assert cfg.face.known_threshold == 0.28
    assert cfg.face.unknown_threshold == 0.38
    assert cfg.face.margin == 0.05
    assert cfg.face.min_votes == 2
    assert cfg.face.min_face_px == 48
    assert cfg.face.min_face_px_embed == 64
    assert cfg.face.best_k == 5
    assert cfg.face.uncertain_policy == "review"
    assert cfg.motion.sample_every == 2
    assert cfg.motion.max_side == 320
    assert cfg.motion.threshold_pct == 2.0
    assert cfg.motion.min_area_px == 150
    assert cfg.motion.min_duration_frames == 3
    assert cfg.motion.cooldown_s == 5
    assert cfg.motion.suppress_global_pct == 50.0
    assert cfg.motion.preroll_s == 2
    assert cfg.display.grid_fps == 15
    assert cfg.display.single_fps == 30
    assert cfg.display.overlay_ttl_s == 1
    assert cfg.notify.desktop_enabled is True
    assert cfg.notify.stranger_cooldown_s == 120
    assert cfg.capture.stall_timeout_s == 10
    assert cfg.capture.backoff_initial_s == 1
    assert cfg.capture.backoff_max_s == 60
    assert cfg.capture.offline_notify_after_s == 120
    assert cfg.face.unknown_merge_window_s == 60
    assert cfg.face.unknown_merge_threshold == 0.6
    assert cfg.storage.event_retention_days == 90
    assert cfg.storage.log_retention_days == 14


def test_unknown_threshold_must_exceed_known_threshold():
    with pytest.raises(ValidationError):
        VigilConfig.model_validate(
            {"face": {"known_threshold": 0.7, "unknown_threshold": 0.6}}
        )


def test_camera_id_must_be_a_slug():
    with pytest.raises(ValidationError):
        CameraConfig(id="Front Door", name="Front door", source="rtsp://x")


def test_zone_points_must_be_normalized():
    with pytest.raises(ValidationError):
        ZoneConfig(name="walk", points=[(1.4, 0.2), (0.2, 0.2), (0.2, 0.8)])


def test_zone_accepts_normalized_polygon():
    zone = ZoneConfig(
        name="walk",
        points=[(0.1, 0.1), (0.9, 0.1), (0.9, 0.9)],
        threshold_pct=3.0,
    )
    assert zone.threshold_pct == 3.0
    assert zone.exclude is False
