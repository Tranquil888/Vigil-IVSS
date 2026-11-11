"""Face quality gate: size, blur, and a yaw proxy from landmarks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from ..config.models import FaceConfig

Rect = Tuple[int, int, int, int]


@dataclass
class FaceQuality:
    face_px: int
    blur: float
    yaw: float
    score: float


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _yaw_proxy(landmarks) -> float:
    points = np.asarray(landmarks, dtype=np.float32)
    if points.shape[0] < 68:
        return 0.0
    left_eye = points[36:42].mean(axis=0)
    right_eye = points[42:48].mean(axis=0)
    nose = points[30]
    interocular = max(1.0, float(right_eye[0] - left_eye[0]))
    asymmetry = abs(
        float(nose[0] - left_eye[0]) - float(right_eye[0] - nose[0])
    )
    return _clamp(asymmetry / interocular, 0.0, 1.5) * 60.0


def assess_quality(
    image: np.ndarray,
    rect: Rect,
    config: FaceConfig,
    landmarks: Optional[np.ndarray] = None,
) -> FaceQuality:
    x, y, width, height = [int(value) for value in rect]
    image_height, image_width = image.shape[:2]
    x = max(0, min(x, image_width - 1))
    y = max(0, min(y, image_height - 1))
    width = max(1, min(width, image_width - x))
    height = max(1, min(height, image_height - y))

    crop = image[y : y + height, x : x + width]
    if crop.size == 0:
        return FaceQuality(0, 0.0, 0.0, 0.0)
    gray = (
        cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if crop.ndim == 3
        else crop
    )
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    face_px = int(min(width, height))
    yaw = _yaw_proxy(landmarks) if landmarks is not None else 0.0

    ideal_px = max(16, config.min_face_px_embed * 2)
    size_score = _clamp(face_px / float(ideal_px))
    blur_score = _clamp(blur / 150.0)
    yaw_score = 1.0 - _clamp(abs(yaw) / 60.0)
    score = float((size_score * blur_score * yaw_score) ** (1.0 / 3.0))
    return FaceQuality(face_px=face_px, blur=blur, yaw=yaw, score=score)
