"""Composition root. Builds the workers, then shuts them down in one order."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..analysis.backend import MODEL_ID, DlibBackend
from ..analysis.gallery import Gallery
from ..analysis.pipeline import InferenceWorker, OverlayStore
from ..analysis.unknowns import StrangerGrouper
from ..config.models import VigilConfig
from .bus import EventBus
from ..notify.notifier import Notifier
from ..paths import data_dir, db_path, models_dir, snapshots_dir
from ..storage.db import Database
from ..storage.embeddings import EmbeddingStore
from ..storage.reader import Reader
from ..storage.schema import camera as camera_table
from ..storage.snapshots import SnapshotStore
from ..storage.writer import DBWriterThread
from ..video.manager import CameraManager
from ..video.source import FrameSource

log = logging.getLogger(__name__)


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
        self.db_writer = DBWriterThread(self.bus, self.database.path)

        self._seed_cameras()

        people = self.reader.people()
        self.names: Dict[int, str] = {int(row["id"]): row["name"] for row in people}
        if gallery is not None:
            self.gallery = gallery
        else:
            self.gallery = Gallery(EmbeddingStore(self.database.engine).gallery(MODEL_ID))

        if backend is not None:
            self.backend = backend
        else:
            self.backend = DlibBackend(
                models_dir(config),
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
        self.inference = InferenceWorker(
            queue=self.manager.inference_queue,
            config=config,
            backend=self.backend,
            gallery=self.gallery,
            grouper=StrangerGrouper(
                config.face.unknown_merge_window_s,
                config.face.unknown_merge_threshold,
            ),
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

    # -- lifecycle -----------------------------------------------------

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
