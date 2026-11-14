"""Configuration model. Every threshold the plan pins has a field here."""

from __future__ import annotations

import re
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class AppConfig(Section):
    theme: Literal["system", "dark", "light"] = "dark"
    log_level: str = "INFO"
    start_minimized: bool = False


class InferenceConfig(Section):
    device: str = Field(default="auto", pattern=r"^(auto|cpu|cuda(:\d+)?)$")
    analysis_fps: float = Field(default=5.0, gt=0, le=60)
    queue_size: int = Field(default=4, ge=1, le=64)
    # A frame older than this is dropped instead of processed.
    max_frame_age_s: float = Field(default=2.0, gt=0)


class FaceConfig(Section):
    detector: Literal["dlib_cnn", "dlib_hog", "none"] = "dlib_cnn"
    known_threshold: float = Field(default=0.28, gt=0, le=2)
    unknown_threshold: float = Field(default=0.38, gt=0, le=2)
    margin: float = Field(default=0.05, ge=0, le=1)
    min_votes: int = Field(default=2, ge=1, le=50)
    min_face_px: int = Field(default=48, ge=8, le=2048)
    min_face_px_embed: int = Field(default=64, ge=8, le=2048)
    best_k: int = Field(default=5, ge=1, le=50)
    uncertain_policy: Literal["review", "unknown", "ignore"] = "review"
    gallery_score: Literal["min", "top3_mean"] = "min"
    max_detect_side: int = Field(default=800, ge=160, le=4096)
    unknown_merge_window_s: float = Field(default=60.0, ge=0, le=3600)
    unknown_merge_threshold: float = Field(default=0.6, gt=0, le=2)
    track_iou: float = Field(default=0.3, ge=0, le=1)
    track_max_gap_s: float = Field(default=1.0, gt=0, le=60)
    min_tracklet_observations: int = Field(default=1, ge=1, le=100)
    models_dir: Optional[str] = None

    @model_validator(mode="after")
    def thresholds_must_leave_a_band(self) -> "FaceConfig":
        if self.unknown_threshold <= self.known_threshold:
            raise ValueError(
                "unknown_threshold must be greater than known_threshold "
                "so the uncertain band survives"
            )
        return self


class MotionConfig(Section):
    enabled: bool = True
    algorithm: Literal["mog2", "running_avg", "frame_diff"] = "mog2"
    sample_every: int = Field(default=2, ge=1, le=30)
    max_side: int = Field(default=320, ge=64, le=1920)
    threshold_pct: float = Field(default=2.0, ge=0, le=100)
    min_area_px: int = Field(default=150, ge=1)
    min_duration_frames: int = Field(default=3, ge=1, le=120)
    cooldown_s: float = Field(default=5.0, ge=0, le=600)
    suppress_global_pct: float = Field(default=50.0, ge=0, le=100)
    preroll_s: float = Field(default=2.0, ge=0, le=30)


class DisplayConfig(Section):
    grid_fps: float = Field(default=15.0, gt=0, le=60)
    single_fps: float = Field(default=30.0, gt=0, le=60)
    overlay_ttl_s: float = Field(default=1.0, gt=0, le=10)


class NotifyConfig(Section):
    desktop_enabled: bool = True
    sound_enabled: bool = False
    stranger_cooldown_s: float = Field(default=120.0, ge=0, le=86400)


class CaptureConfig(Section):
    stall_timeout_s: float = Field(default=10.0, gt=0)
    backoff_initial_s: float = Field(default=1.0, gt=0)
    backoff_max_s: float = Field(default=60.0, gt=0)
    backoff_jitter: float = Field(default=0.2, ge=0, le=1)
    offline_notify_after_s: float = Field(default=120.0, ge=0)
    open_timeout_ms: int = Field(default=5000, ge=100)
    # Capture buffers above 1 make the decoder hold stale frames.
    buffer_size: int = Field(default=1, ge=1, le=10)


class StorageConfig(Section):
    data_dir: Optional[str] = None
    event_retention_days: int = Field(default=90, ge=1)
    log_retention_days: int = Field(default=14, ge=1)
    snapshot_jpeg_quality: int = Field(default=90, ge=1, le=100)


class ZoneConfig(Section):
    name: str = Field(min_length=1, max_length=64)
    points: List[Tuple[float, float]] = Field(min_length=3)
    threshold_pct: Optional[float] = Field(default=None, ge=0, le=100)
    exclude: bool = False

    @field_validator("points")
    @classmethod
    def points_are_normalized(cls, points: List[Tuple[float, float]]):
        for x, y in points:
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError("zone points must be in the 0..1 range")
        return points


class CameraConfig(Section):
    id: str
    name: str = Field(min_length=1, max_length=64)
    source: str = Field(min_length=1)
    enabled: bool = True
    analysis_stream: Literal["sub", "main"] = "sub"
    snapshot_enabled: bool = True
    motion: Optional[MotionConfig] = None
    zones: List[ZoneConfig] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def id_is_a_slug(cls, value: str) -> str:
        if not SLUG.match(value):
            raise ValueError("camera id must match ^[a-z0-9][a-z0-9_-]*$")
        return value


class VigilConfig(Section):
    app: AppConfig = Field(default_factory=AppConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    face: FaceConfig = Field(default_factory=FaceConfig)
    motion: MotionConfig = Field(default_factory=MotionConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    cameras: List[CameraConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def camera_ids_are_unique(self) -> "VigilConfig":
        seen = set()
        for camera in self.cameras:
            if camera.id in seen:
                raise ValueError("camera id %r is used more than once" % camera.id)
            seen.add(camera.id)
        return self

    def camera(self, camera_id: str) -> CameraConfig:
        for camera in self.cameras:
            if camera.id == camera_id:
                return camera
        raise KeyError(camera_id)

    def motion_for(self, camera: CameraConfig) -> MotionConfig:
        return camera.motion or self.motion
