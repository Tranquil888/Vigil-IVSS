"""Snapshot files on disk. Rows are written by the DB writer thread."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Dict, Optional

import cv2


class SnapshotStore:
    def __init__(self, directory: Path, jpeg_quality: int = 90) -> None:
        self.directory = Path(directory)
        self.jpeg_quality = int(jpeg_quality)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        image: Any,
        camera_id: str,
        when: Optional[float] = None,
    ) -> Dict[str, Any]:
        when = time.time() if when is None else when
        ok, encoded = cv2.imencode(
            ".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        )
        if not ok:
            raise ValueError("could not encode the snapshot as JPEG")
        payload = encoded.tobytes()
        digest = hashlib.sha256(payload).hexdigest()
        name = "%s-%d-%s.jpg" % (camera_id, int(when * 1000), digest[:10])
        path = self.directory / name
        path.write_bytes(payload)
        height, width = image.shape[:2]
        return {
            "path": str(path),
            "sha256": digest,
            "width": int(width),
            "height": int(height),
            "created_at": float(when),
        }

    def remove(self, path: str) -> None:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass
