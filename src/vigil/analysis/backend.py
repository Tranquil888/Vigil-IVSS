"""The only module that imports dlib. Everything above it works without it."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from ..config.models import FaceConfig

Rect = Tuple[int, int, int, int]

CNN_MODEL = "mmod_human_face_detector.dat"
SHAPE_MODEL = "shape_predictor_68_face_landmarks.dat"
FACE_MODEL = "dlib_face_recognition_resnet_model_v1.dat"

log = logging.getLogger(__name__)


@dataclass
class BackendStatus:
    available: bool
    cuda: bool
    detector: str
    reason: str


def probe_backend(face: FaceConfig, models_dir: Path) -> BackendStatus:
    if face.detector == "none":
        return BackendStatus(False, False, "none", "face recognition is disabled in config")
    try:
        import dlib
    except Exception as err:
        return BackendStatus(False, False, "none", "dlib is not installed: %s" % err)

    cuda = bool(getattr(dlib, "DLIB_USE_CUDA", False))
    try:
        cuda = cuda and int(dlib.cuda.get_num_devices()) > 0
    except Exception:
        cuda = False

    if face.detector == "dlib_cnn":
        model = Path(models_dir) / CNN_MODEL
        if not model.exists():
            return BackendStatus(
                True,
                cuda,
                "dlib_hog",
                "CNN model missing at %s, using HOG" % model,
            )
    return BackendStatus(
        True,
        cuda,
        face.detector,
        "ready on GPU" if cuda else "dlib is running on CPU",
    )


class DlibBackend:
    def __init__(
        self,
        models_dir: Path,
        detector: str = "dlib_cnn",
        device: str = "auto",
        max_detect_side: int = 800,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.max_detect_side = int(max_detect_side)
        self.status = probe_backend(
            FaceConfig(detector=detector, max_detect_side=max_detect_side),
            self.models_dir,
        )
        self._dlib = None
        self._detector = None
        self._shape = None
        self._net = None
        if not self.status.available or self.status.detector == "none":
            return

        import dlib

        self._dlib = dlib
        if self.status.detector == "dlib_cnn":
            self._detector = dlib.cnn_face_detection_model_v1(
                str(self.models_dir / CNN_MODEL)
            )
        else:
            self._detector = dlib.get_frontal_face_detector()

        shape_path = self.models_dir / SHAPE_MODEL
        if shape_path.exists():
            self._shape = dlib.shape_predictor(str(shape_path))
        else:
            log.warning(
                "landmark model missing, embedding is disabled",
                extra={"event": "face.shape_missing", "detail": str(shape_path)},
            )

        face_path = self.models_dir / FACE_MODEL
        if face_path.exists():
            self._net = dlib.face_recognition_model_v1(str(face_path))
        else:
            log.warning(
                "recognition model missing, embedding is disabled",
                extra={"event": "face.model_missing", "detail": str(face_path)},
            )

    @property
    def can_embed(self) -> bool:
        return self._shape is not None and self._net is not None

    def detect(self, image: np.ndarray) -> List[Rect]:
        if self._detector is None or self._dlib is None:
            return []
        height, width = image.shape[:2]
        scale = min(1.0, float(self.max_detect_side) / float(max(width, height)))
        if scale < 1.0:
            small = cv2.resize(
                image,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        else:
            small = image
            scale = 1.0

        if self.status.detector == "dlib_cnn":
            found = self._detector(small, 0)
            rectangles = [item.rect for item in found]
        else:
            rectangles = list(self._detector(small, 0))

        result: List[Rect] = []
        small_height, small_width = small.shape[:2]
        for rectangle in rectangles:
            left = max(0, int(rectangle.left() / scale))
            top = max(0, int(rectangle.top() / scale))
            right = min(width, int(rectangle.right() / scale))
            bottom = min(height, int(rectangle.bottom() / scale))
            if right > left and bottom > top:
                result.append((left, top, right - left, bottom - top))
        return result

    def landmarks(self, image: np.ndarray, rect: Rect) -> Optional[np.ndarray]:
        if self._shape is None or self._dlib is None:
            return None
        x, y, width, height = rect
        shape = self._shape(
            image, self._dlib.rectangle(x, y, x + width, y + height)
        )
        return np.array(
            [(point.x, point.y) for point in shape.parts()], dtype=np.float32
        )

    def embed(self, image: np.ndarray, rect: Rect) -> Optional[np.ndarray]:
        if not self.can_embed or self._dlib is None:
            return None
        x, y, width, height = rect
        rectangle = self._dlib.rectangle(x, y, x + width, y + height)
        try:
            shape = self._shape(image, rectangle)
            chip = self._dlib.get_face_chip(image, shape, size=150)
            descriptor = self._net.compute_face_descriptor(chip)
        except Exception:
            log.exception("embedding failed", extra={"event": "face.embed_failed"})
            return None
        vector = np.asarray(descriptor, dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector = vector / norm
        return vector
