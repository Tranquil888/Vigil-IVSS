"""In-memory embedding gallery. One score per enrolled person."""

from __future__ import annotations

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
    def __init__(self, vectors: Optional[Dict[int, np.ndarray]] = None) -> None:
        self._vectors: Dict[int, np.ndarray] = {}
        if vectors:
            for person_id, rows in vectors.items():
                self.add_person(person_id, rows)

    def add(self, person_id: int, vector: np.ndarray) -> None:
        self.add_person(person_id, np.atleast_2d(np.asarray(vector)))

    def add_person(self, person_id: int, vectors: np.ndarray) -> None:
        rows = np.atleast_2d(np.asarray(vectors, dtype=np.float32))
        rows = np.vstack([_normalize(row) for row in rows])
        if person_id in self._vectors:
            self._vectors[person_id] = np.vstack([self._vectors[person_id], rows])
        else:
            self._vectors[person_id] = rows

    def remove_person(self, person_id: int) -> None:
        self._vectors.pop(person_id, None)

    def clear(self) -> None:
        self._vectors.clear()

    def person_ids(self) -> List[int]:
        return sorted(self._vectors)

    def score(self, vector: np.ndarray, mode: str = "min") -> List[PersonScore]:
        query = _normalize(vector)
        scores: List[PersonScore] = []
        for person_id, rows in self._vectors.items():
            distances = np.linalg.norm(rows - query, axis=1)
            if mode == "top3_mean":
                nearest = np.sort(distances)[:3]
                distance = float(np.mean(nearest))
            else:
                distance = float(np.min(distances))
            scores.append(PersonScore(person_id=person_id, distance=distance))
        scores.sort(key=lambda item: item.distance)
        return scores
