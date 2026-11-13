"""Composition root. Builds the workers, then shuts them down in one order."""

from __future__ import annotations

import hashlib
import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import cv2
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..analysis.backend import MODEL_ID, DlibBackend
from ..analysis.gallery import Gallery
from ..analysis.pipeline import InferenceWorker, OverlayStore
from ..analysis.unknowns import StrangerGrouper
from ..config.models import VigilConfig
from .bus import EventBus
from ..notify.notifier import Notifier
from ..paths import data_dir, db_path, models_for, people_dir, snapshots_dir
from ..storage.db import Database
from ..storage.embeddings import EmbeddingStore
from ..storage.people import PeopleStore
from ..storage.reader import Reader
from ..storage.schema import camera as camera_table
from ..storage.snapshots import SnapshotStore
from ..storage.writer import DBWriterThread
from ..video.manager import CameraManager
from ..video.source import FrameSource

log = logging.getLogger(__name__)


def _backend_signature(config: VigilConfig, data_path: Path):
    return (
        config.face.detector,
        config.inference.device,
        config.face.max_detect_side,
        str(models_for(config, data_path)),
    )


class AppContext:
    """Everything the GUI may read, plus the threads the app must join."""

    def __init__(
        self,
        config: VigilConfig,
        data_path: Optional[Path] = None,
        source_factory: Optional[Callable[[object], FrameSource]] = None,
        backend=None,
        bus: Optional[EventBus] = None,
        gallery: Optional[Gallery] = None,
        toast_callback: Optional[Callable[[str, str], None]] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.data_path = Path(data_path) if data_path is not None else data_dir(config)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._started = False
        self._shutdown_done = False

        self.database = Database(db_path(config, self.data_path)).create()
        self.reader = Reader(self.database.path)
        self.bus = bus if bus is not None else EventBus()
        self.db_writer = DBWriterThread(
            self.bus,
            self.database.path,
            retention_days=config.storage.event_retention_days,
        )

        self._seed_cameras()

        people = self.reader.people()
        self.names: Dict[int, str] = {int(row["id"]): row["name"] for row in people}
        self.embeddings = EmbeddingStore(self.database.engine)
        self.people_store = PeopleStore(self.database.engine)
        if gallery is not None:
            self.gallery = gallery
        else:
            self.gallery = Gallery(self.embeddings.gallery(MODEL_ID))

        self._injected_backend = backend is not None
        self._backend_signature = _backend_signature(config, self.data_path)
        if backend is not None:
            self.backend = backend
        else:
            self.backend = DlibBackend(
                models_for(config, self.data_path),
                detector=config.face.detector,
                device=config.inference.device,
                max_detect_side=config.face.max_detect_side,
            )
        self.status = self.backend.status

        self.snapshots = SnapshotStore(
            snapshots_dir(config, self.data_path),
            jpeg_quality=config.storage.snapshot_jpeg_quality,
        )
        self.manager = CameraManager(config, bus=self.bus, source_factory=source_factory)
        self.overlays = OverlayStore()
        grouper = StrangerGrouper(
            config.face.unknown_merge_window_s,
            config.face.unknown_merge_threshold,
        )
        try:
            grouper.seed_next_id(self.reader.max_unknown_cluster_id() + 1)
        except Exception:
            log.exception("could not seed unknown cluster ids")
        self.inference = InferenceWorker(
            queue=self.manager.inference_queue,
            config=config,
            backend=self.backend,
            gallery=self.gallery,
            grouper=grouper,
            bus=self.bus,
            snapshot_store=self.snapshots,
            overlays=self.overlays,
            cameras=config.cameras,
            names=self.names,
            clock=clock,
        )
        self.notifier = Notifier(
            bus=self.bus,
            config=config.notify,
            toast_callback=toast_callback,
            names=self.names,
        )
        self._manager_signature = self.manager.runtime_signature()

    # -- lifecycle -----------------------------------------------------

    def reload_config(self, path: Path) -> dict:
        """Read the TOML file again and apply it to the shared config object.

        Sections are replaced wholesale so interdependent validation happens
        once, on the freshly loaded model, not field by field.
        """
        from ..config.loader import load_config

        fresh = load_config(Path(path))
        for name in (
            "app",
            "inference",
            "face",
            "motion",
            "display",
            "notify",
            "capture",
            "storage",
        ):
            setattr(self.config, name, getattr(fresh, name))
        self.config.cameras = fresh.cameras
        # Section objects were replaced, so existing supervisors and motion
        # workers hold stale references. Force one rebuild.
        self._manager_signature = None
        return self.apply_config()

    def apply_config(self) -> dict:
        """Push live edits from the shared config into the running workers.

        Called by the GUI after a save. It rebuilds only what the changed
        values require, so editing a face threshold does not interrupt capture.
        """
        summary = {
            "cameras": len(self.manager.camera_ids),
            "cameras_rebuilt": False,
            "backend_rebuilt": False,
        }

        signature = self.manager.runtime_signature()
        if signature != self._manager_signature:
            self.manager.reconfigure(self.config)
            self._manager_signature = self.manager.runtime_signature()
            self.overlays.clear()
            summary["cameras"] = len(self.manager.camera_ids)
            summary["cameras_rebuilt"] = True
        else:
            self.manager.inference_queue.resize(self.config.inference.queue_size)
            for supervisor in self.manager._supervisors:
                supervisor.set_analysis_fps(self.config.inference.analysis_fps)

        if not self._injected_backend:
            signature = _backend_signature(self.config, self.data_path)
            if signature != self._backend_signature:
                self.backend = DlibBackend(
                    models_for(self.config, self.data_path),
                    detector=self.config.face.detector,
                    device=self.config.inference.device,
                    max_detect_side=self.config.face.max_detect_side,
                )
                self._backend_signature = signature
                self.status = self.backend.status
                self.inference.set_backend(self.backend)
                summary["backend_rebuilt"] = True

        self.inference.reconfigure(self.config)
        self.notifier.set_config(self.config.notify)
        self.snapshots.jpeg_quality = int(self.config.storage.snapshot_jpeg_quality)
        self.db_writer.retention_days = float(self.config.storage.event_retention_days)
        return summary

    def start(self) -> "AppContext":
        if self._started:
            return self
        self._started = True
        try:
            self.db_writer.start()
            self.notifier.start()
            self.inference.start()
            self.manager.start_all()
        except Exception:
            log.exception("startup failed", extra={"event": "app.start_failed"})
            self.shutdown()
            raise
        return self

    def shutdown(self, timeout: float = 5.0) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        deadline = time.monotonic() + float(timeout)

        def left() -> float:
            return max(0.05, deadline - time.monotonic())

        steps = [
            ("camera", self.manager.stop_all),
            ("inference", self.inference.stop),
            ("notifier", self.notifier.stop),
            ("database", self.db_writer.stop),
        ]
        for name, stop in steps:
            try:
                stop(left())
            except Exception:
                log.exception(
                    "shutdown step failed",
                    extra={"event": "app.shutdown_failed", "detail": name},
                )

        self.bus.close()
        self.overlays.clear()
        self.reader.close()
        self.database.close()

    def set_toast_callback(
        self, callback: Optional[Callable[[str, str], None]]
    ) -> None:
        self.notifier.set_toast_callback(callback)

    def rebuild_gallery(self) -> int:
        vectors = self.embeddings.gallery(MODEL_ID)
        self.gallery.replace(vectors)
        return len(vectors)

    def remember_person(self, person_id: int, name: Optional[str]) -> None:
        """Keep the shared name map in step with people edits, for live lookups."""
        if name is None:
            self.names.pop(int(person_id), None)
        else:
            self.names[int(person_id)] = name

    def add_person_photo(self, person_id: int, path: Path) -> Tuple[bool, str]:
        """Store a face photo even when the models are not installed yet.

        The photo is the durable asset. The embedding is derived data, so a
        later ``rebuild_embeddings`` can fill it in without asking the operator
        to import the photo again.
        """
        image = cv2.imread(str(path))
        if image is None:
            return False, "That file could not be read as an image."

        can_embed = bool(getattr(self.backend, "can_embed", False))
        vector = None
        largest = None
        if can_embed:
            try:
                rects = self.backend.detect(image)
            except Exception as err:
                return False, "Face detection failed: %s" % err
            if not rects:
                return False, "No face was found in that photo."
            largest = max(rects, key=lambda rect: int(rect[2]) * int(rect[3]))
            try:
                vector = self.backend.embed(image, largest)
            except Exception as err:
                return False, "The face could not be embedded: %s" % err
            if vector is None:
                return False, "The recognition model returned no embedding."

        payload = Path(path).read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        existing = self.people_store.find_image(person_id, digest)
        if existing is not None:
            if (
                vector is not None
                and not self.embeddings.has_image(int(existing["id"]), MODEL_ID)
            ):
                self.embeddings.add(person_id, int(existing["id"]), MODEL_ID, vector)
                self.rebuild_gallery()
                return True, "That photo was already on file. The embedding was added."
            return True, "That photo is already on file for this person."

        directory = people_dir(self.config, self.data_path)
        directory.mkdir(parents=True, exist_ok=True)
        suffix = Path(path).suffix.lower() or ".jpg"
        target = directory / ("person-%d-%s%s" % (person_id, digest[:12], suffix))
        shutil.copyfile(path, target)
        quality = float(largest[2] * largest[3]) if largest is not None else 0.0
        image_id = self.people_store.add_image(
            person_id, str(target), digest, quality=quality
        )
        if vector is None:
            return (
                True,
                "Photo saved. Recognition is unavailable, so it will be embedded "
                "when the models are installed and you rebuild embeddings.",
            )
        self.embeddings.add(person_id, image_id, MODEL_ID, vector)
        self.rebuild_gallery()
        return True, "Photo added and the gallery was rebuilt."

    def rebuild_embeddings(self) -> dict:
        """Embed every stored photo that has no vector for the current model."""
        result = {
            "embedded": 0,
            "already": 0,
            "failed": 0,
            "people": 0,
            "reason": "",
        }
        if not getattr(self.backend, "can_embed", False):
            result["reason"] = (
                "The recognition model is not available, so no embeddings were added."
            )
            return result

        indexed = self.embeddings.image_ids(MODEL_ID)
        for row in self.people_store.all_images():
            image_id = int(row["id"])
            if image_id in indexed:
                result["already"] += 1
                continue
            try:
                image = cv2.imread(str(row["path"]))
                if image is None:
                    result["failed"] += 1
                    continue
                rects = self.backend.detect(image)
                if not rects:
                    result["failed"] += 1
                    continue
                largest = max(rects, key=lambda rect: int(rect[2]) * int(rect[3]))
                vector = self.backend.embed(image, largest)
                if vector is None:
                    result["failed"] += 1
                    continue
                self.embeddings.add(int(row["person_id"]), image_id, MODEL_ID, vector)
                result["embedded"] += 1
            except Exception:
                result["failed"] += 1
                log.exception(
                    "embedding rebuild failed",
                    extra={
                        "event": "people.rebuild_failed",
                        "detail": str(row.get("path", "")),
                    },
                )
        result["people"] = self.rebuild_gallery()
        return result

    def stats(self) -> dict:
        return {
            "inference": self.inference.stats(),
            "notifier": self.notifier.stats(),
            "database": self.db_writer.stats(),
            "cameras": self.manager.stats(),
            "threads": [
                {"name": thread.name, "alive": thread.is_alive()}
                for thread in self._threads()
            ],
        }

    def _threads(self) -> List[threading.Thread]:
        threads = [self.db_writer, self.notifier, self.inference]
        threads.extend(getattr(self.manager, "_supervisors", []))
        threads.extend(getattr(self.manager, "_motion_workers", []))
        return threads

    def _seed_cameras(self) -> None:
        now = time.time()
        with self.database.engine.begin() as conn:
            for camera in self.config.cameras:
                conn.execute(
                    sqlite_insert(camera_table)
                    .values(id=camera.id, name=camera.name, created_at=now)
                    .on_conflict_do_nothing(index_elements=["id"])
                )
