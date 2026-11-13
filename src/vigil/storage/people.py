"""Person records edited from the GUI. Same database, short transactions."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine

from .schema import person, person_image


class PeopleStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add(self, name: str, notes: Optional[str] = None, enabled: bool = True) -> int:
        now = time.time()
        with self.engine.begin() as conn:
            result = conn.execute(
                person.insert().values(
                    name=name,
                    notes=notes,
                    enabled=1 if enabled else 0,
                    created_at=now,
                    updated_at=now,
                )
            )
            return int(result.inserted_primary_key[0])

    def update(
        self,
        person_id: int,
        name: str,
        notes: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                person.update()
                .where(person.c.id == person_id)
                .values(
                    name=name,
                    notes=notes,
                    enabled=1 if enabled else 0,
                    updated_at=time.time(),
                )
            )

    def delete(self, person_id: int) -> None:
        with self.engine.begin() as conn:
            conn.execute(delete(person).where(person.c.id == person_id))

    def add_image(
        self,
        person_id: int,
        path: str,
        sha256: str,
        quality: float = 0.0,
    ) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(
                person_image.insert().values(
                    person_id=person_id,
                    path=path,
                    sha256=sha256,
                    quality=float(quality),
                    added_at=time.time(),
                )
            )
            return int(result.inserted_primary_key[0])

    def count_images(self, person_id: int) -> int:
        with self.engine.connect() as conn:
            return int(
                conn.execute(
                    select(func.count())
                    .select_from(person_image)
                    .where(person_image.c.person_id == person_id)
                ).scalar()
                or 0
            )

    def images(self, person_id: int) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(person_image)
                .where(person_image.c.person_id == person_id)
                .order_by(person_image.c.added_at)
            )
            return [dict(row._mapping) for row in rows]
