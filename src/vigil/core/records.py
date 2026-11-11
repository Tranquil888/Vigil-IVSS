"""Records passed between workers. Plain data, no Qt, no dlib."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

Rect = Tuple[int, int, int, int]  # x, y, width, height


class EventType:
    MOTION = "motion"
    KNOWN_FACE = "known_face"
    STRANGER = "stranger"
    UNCERTAIN_FACE = "uncertain_face"
    CAMERA_OFFLINE = "camera_offline"
    CAMERA_ONLINE = "camera_online"

    ALL = (
        MOTION,
        KNOWN_FACE,
        STRANGER,
        UNCERTAIN_FACE,
        CAMERA_OFFLINE,
        CAMERA_ONLINE,
    )


class Decision:
    KNOWN = "known"
    UNKNOWN = "unknown"
    UNCERTAIN = "uncertain"
    IGNORED = "ignored"


@dataclass
class Frame:
    camera_id: str
    index: int
    captured_at: float
    wall_time: float
    image: Any
    width: int = 0
    height: int = 0

    def age(self, now: float) -> float:
        return max(0.0, now - self.captured_at)


@dataclass
class Observation:
    camera_id: str
    track_id: int
    rect: Rect
    captured_at: float
    face_px: int
    quality: float
    embedding: Optional[Any] = None
    blur: float = 0.0
    yaw: float = 0.0
    person_id: Optional[int] = None
    distance: Optional[float] = None
    decision: Optional[str] = None


@dataclass
class VisitRecord:
    camera_id: str
    tracklet_id: int
    started_at: float
    ended_at: float
    decision: str
    person_id: Optional[int] = None
    score: Optional[float] = None
    embedding: Optional[Any] = None
    rect: Optional[Rect] = None
    n_obs: int = 0
    unknown_cluster_id: Optional[int] = None


@dataclass
class EventRecord:
    camera_id: str
    type: str
    ts_start: float
    ts_end: Optional[float] = None
    zone: Optional[str] = None
    person_id: Optional[int] = None
    tracklet_id: Optional[int] = None
    unknown_cluster_id: Optional[int] = None
    score: Optional[float] = None
    snapshot_id: Optional[int] = None
    dedupe_key: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationRecord:
    event_id: Optional[int]
    channel: str
    status: str
    reason: Optional[str] = None
    title: str = "Vigil"
    body: str = ""


@dataclass
class OverlayItem:
    camera_id: str
    rect: Rect
    label: str
    kind: str
    expires_at: float


@dataclass(frozen=True)
class SnapshotRecord:
    id: int
    path: str
    sha256: str
    width: int
    height: int
    created_at: float
