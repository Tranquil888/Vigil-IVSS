"""The single writer for event rows. Consumes the bus, never blocks producers."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Union

from sqlalchemy import select
from sqlalchemy.engine import Engine

from ..core.bus import EventBus
from ..core.records import EventRecord, NotificationRecord
from .schema import (
    create_schema,
    event as event_table,
    make_engine,
    notification as notification_table,
    snapshot as snapshot_table,
    tracklet as tracklet_table,
    unknown_cluster as unknown_cluster_table,
)

log = logging.getLogger(__name__)


class DBWriterThread(threading.Thread):
    def __init__(
        self,
        bus: EventBus,
        db_path: Union[str, Path],
        queue_size: int = 4096,
        retention_days: float = 0,
        prune_interval_s: float = 3600.0,
    ) -> None:
        super().__init__(name="vigil-db-writer", daemon=True)
        self.db_path = Path(db_path)
        self._queue = bus.subscribe(queue_size)
        self._stop_event = threading.Event()
        self.retention_days = float(retention_days or 0)
        self.prune_interval_s = float(prune_interval_s)
        self._last_prune = 0.0
        self.inserted = 0
        self.duplicates = 0
        self.merged = 0
        self.pruned = 0
        self.errors = 0

    def run(self) -> None:
        engine = make_engine(self.db_path)
        create_schema(engine)
        try:
            self._maybe_prune(engine)
            while not self._stop_event.is_set():
                record = self._queue.get(timeout=0.2)
                if record is not None:
                    self._handle(engine, record)
                self._maybe_prune(engine)
            while True:
                record = self._queue.get(timeout=0)
                if record is None:
                    break
                self._handle(engine, record)
        finally:
            engine.dispose()

    def _maybe_prune(self, engine: Engine) -> None:
        if self.retention_days <= 0:
            return
        now = time.time()
        if self._last_prune and now - self._last_prune < self.prune_interval_s:
            return
        self._last_prune = now
        try:
            self.pruned += self._prune(engine, now)
        except Exception:
            self.errors += 1
            log.exception("event retention failed", extra={"event": "db.prune_failed"})

    def _prune(self, engine: Engine, now: float) -> int:
        if self.retention_days <= 0:
            return 0
        cutoff = now - 86400.0 * self.retention_days
        snapshot_paths = []
        with engine.begin() as conn:
            removed = int(
                conn.execute(
                    event_table.delete().where(event_table.c.ts_start < cutoff)
                ).rowcount
                or 0
            )

            orphan_snapshots = ~snapshot_table.c.id.in_(
                select(event_table.c.snapshot_id).where(
                    event_table.c.snapshot_id.is_not(None)
                )
            )
            snapshot_paths = [
                row[0]
                for row in conn.execute(
                    select(snapshot_table.c.path).where(orphan_snapshots)
                )
            ]
            conn.execute(snapshot_table.delete().where(orphan_snapshots))

            orphan_tracklets = ~tracklet_table.c.id.in_(
                select(event_table.c.tracklet_id).where(
                    event_table.c.tracklet_id.is_not(None)
                )
            )
            conn.execute(tracklet_table.delete().where(orphan_tracklets))

            orphan_clusters = ~unknown_cluster_table.c.id.in_(
                select(event_table.c.unknown_cluster_id).where(
                    event_table.c.unknown_cluster_id.is_not(None)
                )
            )
            conn.execute(unknown_cluster_table.delete().where(orphan_clusters))

            conn.execute(
                notification_table.delete().where(
                    notification_table.c.created_at < cutoff
                )
            )

        for path in snapshot_paths:
            try:
                Path(path).unlink()
            except OSError:
                pass
        return removed

    def _handle(self, engine: Engine, record: Any) -> None:
        try:
            if isinstance(record, EventRecord):
                self._write_event(engine, record)
            elif isinstance(record, NotificationRecord):
                self._write_notification(engine, record)
            else:
                self.errors += 1
                log.warning("db writer ignored an unknown record", extra={"event": "db.unknown_record"})
        except Exception:
            self.errors += 1
            log.exception("db write failed", extra={"event": "db.write_failed"})

    def _write_event(self, engine: Engine, record: EventRecord) -> None:
        detail = record.detail or {}
        with engine.begin() as conn:
            if record.dedupe_key:
                existing = conn.execute(
                    select(event_table.c.id, event_table.c.ts_end).where(
                        event_table.c.dedupe_key == record.dedupe_key
                    )
                ).first()
                if existing is not None:
                    self.duplicates += 1
                    self._merge_visit(conn, existing, record)
                    return

            tracklet_id = record.tracklet_id
            tracklet_values = detail.get("tracklet")
            if tracklet_values:
                result = conn.execute(tracklet_table.insert().values(**tracklet_values))
                tracklet_id = result.inserted_primary_key[0]

            snapshot_id = record.snapshot_id
            snapshot_values = detail.get("snapshot")
            if snapshot_values:
                result = conn.execute(snapshot_table.insert().values(**snapshot_values))
                snapshot_id = result.inserted_primary_key[0]

            cluster_id = record.unknown_cluster_id
            cluster_values = detail.get("unknown_cluster")
            if cluster_values:
                cluster_id = self._upsert_cluster(conn, cluster_values)
            elif cluster_id is not None:
                conn.execute(
                    unknown_cluster_table.update()
                    .where(unknown_cluster_table.c.id == cluster_id)
                    .values(
                        last_seen=record.ts_end or record.ts_start,
                        n_visits=unknown_cluster_table.c.n_visits + 1,
                    )
                )

            conn.execute(
                event_table.insert().values(
                    ts_start=record.ts_start,
                    ts_end=record.ts_end,
                    camera_id=record.camera_id,
                    type=record.type,
                    zone=record.zone,
                    person_id=record.person_id,
                    tracklet_id=tracklet_id,
                    unknown_cluster_id=cluster_id,
                    score=record.score,
                    snapshot_id=snapshot_id,
                    dedupe_key=record.dedupe_key,
                )
            )
            self.inserted += 1

    def _merge_visit(self, conn, existing, record: EventRecord) -> None:
        """Fold a later tracklet of the same unknown visit into one event row."""
        if record.unknown_cluster_id is None:
            return
        self.merged += 1
        end = record.ts_end or record.ts_start
        conn.execute(
            unknown_cluster_table.update()
            .where(unknown_cluster_table.c.id == record.unknown_cluster_id)
            .values(
                last_seen=end,
                n_visits=unknown_cluster_table.c.n_visits + 1,
            )
        )
        if existing.ts_end is None or end > existing.ts_end:
            conn.execute(
                event_table.update()
                .where(event_table.c.id == existing.id)
                .values(ts_end=end)
            )

    @staticmethod
    def _upsert_cluster(conn, values: dict) -> int:
        result = conn.execute(unknown_cluster_table.insert().values(**values))
        return result.inserted_primary_key[0]

    def _write_notification(self, engine: Engine, record: NotificationRecord) -> None:
        with engine.begin() as conn:
            conn.execute(
                notification_table.insert().values(
                    event_id=record.event_id,
                    channel=record.channel,
                    status=record.status,
                    reason=record.reason,
                    created_at=time.time(),
                )
            )

    def stats(self) -> dict:
        return {
            "inserted": self.inserted,
            "duplicates": self.duplicates,
            "merged": self.merged,
            "errors": self.errors,
            "queued": self._queue.qsize(),
            "dropped": self._queue.dropped,
        }

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        self._queue.close()
        if not self.is_alive():
            return
        self.join(timeout)
        if self.is_alive():
            log.warning("db writer did not stop in time", extra={"event": "db.stop_timeout"})
