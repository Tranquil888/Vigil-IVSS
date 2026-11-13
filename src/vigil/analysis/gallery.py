"""In-memory embedding gallery. One score per enrolled person."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np


@dataclass
class PersonScore:
    person_id: int
    distance: float


def _normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        return vector
    return vector / norm


class Gallery:
    """Person vectors, safe to rebuild from the GUI while inference scores."""

    def __init__(self, vectors: Optional[Dict[int, np.ndarray]] = None) -> None:
        self._lock = threading.RLock()
        self._vectors: Dict[int, np.ndarray] = {}
        if vectors:
            self.replace(vectors)

    def add(self, person_id: int, vector: np.ndarray) -> None:
        self.add_person(person_id, np.atleast_2d(np.asarray(vector)))

    def add_person(self, person_id: int, vectors: np.ndarray) -> None:
        rows = self._prepare(vectors)
        with self._lock:
            existing = self._vectors.get(person_id)
            if existing is None:
                self._vectors[person_id] = rows
            else:
                self._vectors[person_id] = np.vstack([existing, rows])

    @staticmethod
    def _prepare(vectors: np.ndarray) -> np.ndarray:
        rows = np.atleast_2d(np.asarray(vectors, dtype=np.float32))
        return np.vstack([_normalize(row) for row in rows])

    def replace(self, vectors: Dict[int, np.ndarray]) -> None:
        """Swap the whole gallery in one step, so readers never see it half built."""
        built = {
            int(person_id): self._prepare(rows)
            for person_id, rows in (vectors or {}).items()
        }
        with self._lock:
            self._vectors = built

    def remove_person(self, person_id: int) -> None:
        with self._lock:
            self._vectors.pop(person_id, None)

    def clear(self) -> None:
        with self._lock:
            self._vectors.clear()

    def person_ids(self) -> List[int]:
        with self._lock:
            return sorted(self._vectors)

    def score(self, vector: np.ndarray, mode: str = "min") -> List[PersonScore]:
        with self._lock:
            snapshot = list(self._vectors.items())
        query = _normalize(vector)
        scores: List[PersonScore] = []
        for person_id, rows in snapshot:
            distances = np.linalg.norm(rows - query, axis=1)
            if mode == "top3_mean":
                nearest = np.sort(distances)[:3]
                distance = float(np.mean(nearest))
            else:
                distance = float(np.min(distances))
            scores.append(PersonScore(person_id=person_id, distance=distance))
        scores.sort(key=lambda item: item.distance)
        return scores
