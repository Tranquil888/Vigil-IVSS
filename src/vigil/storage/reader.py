"""Read side. Safe to call from the GUI thread on its own engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from .schema import (
    embedding,
    event,
    make_engine,
    notification,
    person,
    person_image,
    snapshot,
    tracklet,
    unknown_cluster,
)


class Reader:
    def __init__(self, db_path: Union[str, Path]) -> None:
        self.engine: Engine = make_engine(Path(db_path))

    def _rows(self, stmt) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            return [dict(row._mapping) for row in conn.execute(stmt)]

    def count_events(self) -> int:
        with self.engine.connect() as conn:
            return int(conn.execute(select(func.count()).select_from(event)).scalar() or 0)

    def events(
        self,
        limit: int = 200,
        camera_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        stmt = select(event).order_by(event.c.ts_start.desc()).limit(limit)
        if camera_id:
            stmt = stmt.where(event.c.camera_id == camera_id)
        if event_type:
            stmt = stmt.where(event.c.type == event_type)
        if since is not None:
            stmt = stmt.where(event.c.ts_start >= since)
        return self._rows(stmt)

    def tracklets(self, limit: int = 100, camera_id: Optional[str] = None):
        stmt = select(tracklet).order_by(tracklet.c.started_at.desc()).limit(limit)
        if camera_id:
            stmt = stmt.where(tracklet.c.camera_id == camera_id)
        return self._rows(stmt)

    def count_notifications(self) -> int:
        with self.engine.connect() as conn:
            return int(
                conn.execute(select(func.count()).select_from(notification)).scalar() or 0
            )

    def count_people(self) -> int:
        with self.engine.connect() as conn:
            return int(
                conn.execute(select(func.count()).select_from(person)).scalar() or 0
            )

    def count_snapshots(self) -> int:
        with self.engine.connect() as conn:
            return int(
                conn.execute(select(func.count()).select_from(snapshot)).scalar() or 0
            )

    def count_unknown_clusters(self) -> int:
        with self.engine.connect() as conn:
            return int(
                conn.execute(
                    select(func.count()).select_from(unknown_cluster)
                ).scalar()
                or 0
            )

    def notifications(self, limit: int = 100):
        return self._rows(
            select(notification).order_by(notification.c.created_at.desc()).limit(limit)
        )

    def people(self) -> List[Dict[str, Any]]:
        return self._rows(select(person).order_by(person.c.name))

    def person_images(self, person_id: int) -> List[Dict[str, Any]]:
        return self._rows(
            select(person_image)
            .where(person_image.c.person_id == person_id)
            .order_by(person_image.c.added_at)
        )

    def snapshots(self, limit: int = 50):
        return self._rows(
            select(snapshot).order_by(snapshot.c.created_at.desc()).limit(limit)
        )

    def unknown_clusters(self, limit: int = 100):
        return self._rows(
            select(unknown_cluster)
            .order_by(unknown_cluster.c.last_seen.desc())
            .limit(limit)
        )

    def max_unknown_cluster_id(self) -> int:
        with self.engine.connect() as conn:
            value = conn.execute(select(func.max(unknown_cluster.c.id))).scalar()
            return int(value or 0)

    def embeddings(self, person_id: int, model_id: Optional[str] = None):
        stmt = select(embedding).where(embedding.c.person_id == person_id)
        if model_id:
            stmt = stmt.where(embedding.c.model_id == model_id)
        return self._rows(stmt)

    def close(self) -> None:
        self.engine.dispose()
