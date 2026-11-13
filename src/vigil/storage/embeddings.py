"""Embedding index. Adding a photo updates rows; nothing is fine-tuned."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Optional, Sequence

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from .schema import embedding, person


def to_blob(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype="<f4").reshape(-1).tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype="<f4")


class EmbeddingStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add(
        self,
        person_id: int,
        person_image_id: Optional[int],
        model_id: str,
        vector: np.ndarray,
        model_version: str = "1",
    ) -> None:
        vector = np.asarray(vector, dtype="<f4").reshape(-1)
        with self.engine.begin() as conn:
            conn.execute(
                embedding.insert().values(
                    person_id=person_id,
                    person_image_id=person_image_id,
                    model_id=model_id,
                    model_version=model_version,
                    dim=int(vector.size),
                    vector=to_blob(vector),
                )
            )

    def add_many(
        self,
        person_id: int,
        model_id: str,
        vectors: Sequence[np.ndarray],
        model_version: str = "1",
    ) -> None:
        with self.engine.begin() as conn:
            for vector in vectors:
                flat = np.asarray(vector, dtype="<f4").reshape(-1)
                conn.execute(
                    embedding.insert().values(
                        person_id=person_id,
                        person_image_id=None,
                        model_id=model_id,
                        model_version=model_version,
                        dim=int(flat.size),
                        vector=to_blob(flat),
                    )
                )

    def gallery(self, model_id: str) -> Dict[int, np.ndarray]:
        """Only enabled people are matched, so disabling a person takes effect on rebuild."""
        grouped: Dict[int, list] = defaultdict(list)
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(embedding.c.person_id, embedding.c.vector)
                .join(person, person.c.id == embedding.c.person_id)
                .where(
                    embedding.c.model_id == model_id,
                    person.c.enabled == 1,
                )
            )
            for person_id, blob in rows:
                grouped[int(person_id)].append(from_blob(blob))
        return {pid: np.vstack(vectors) for pid, vectors in grouped.items()}

    def remove_person(self, person_id: int) -> None:
        with self.engine.begin() as conn:
            conn.execute(delete(embedding).where(embedding.c.person_id == person_id))

    def remove_image(self, person_image_id: int) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                delete(embedding).where(
                    embedding.c.person_image_id == person_image_id
                )
            )

    def clear_model(self, model_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(delete(embedding).where(embedding.c.model_id == model_id))

    def count(self, model_id: Optional[str] = None) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(embedding)
        if model_id:
            stmt = stmt.where(embedding.c.model_id == model_id)
        with self.engine.connect() as conn:
            return int(conn.execute(stmt).scalar() or 0)
