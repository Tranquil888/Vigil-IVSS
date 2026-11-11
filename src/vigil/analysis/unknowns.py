"""Group separate unknown tracklets into one stranger visit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np


@dataclass
class UnknownAssignment:
    id: int
    is_new: bool
    n_visits: int
    first_seen: float
    last_seen: float
    centroid: np.ndarray


@dataclass
class _Cluster:
    id: int
    camera_id: str
    centroid: np.ndarray
    first_seen: float
    last_seen: float
    n_visits: int


def _normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        return vector
    return vector / norm


class StrangerGrouper:
    def __init__(self, window_s: float = 60.0, threshold: float = 0.6) -> None:
        self.window_s = float(window_s)
        self.threshold = float(threshold)
        self._clusters: Dict[int, _Cluster] = {}
        self._next_id = 1

    def assign(self, camera_id: str, vector: np.ndarray, now: float) -> UnknownAssignment:
        query = _normalize(vector)
        best: Optional[_Cluster] = None
        best_distance = self.threshold

        for cluster in self._clusters.values():
            if cluster.camera_id != camera_id:
                continue
            if now - cluster.last_seen > self.window_s:
                continue
            distance = float(np.linalg.norm(cluster.centroid - query))
            if distance <= best_distance:
                best = cluster
                best_distance = distance

        if best is not None:
            best.centroid = _normalize(
                (best.centroid * best.n_visits + query) / (best.n_visits + 1)
            )
            best.n_visits += 1
            best.last_seen = now
            return UnknownAssignment(
                id=best.id,
                is_new=False,
                n_visits=best.n_visits,
                first_seen=best.first_seen,
                last_seen=best.last_seen,
                centroid=best.centroid,
            )

        cluster = _Cluster(
            id=self._next_id,
            camera_id=camera_id,
            centroid=query,
            first_seen=now,
            last_seen=now,
            n_visits=1,
        )
        self._next_id += 1
        self._clusters[cluster.id] = cluster
        return UnknownAssignment(
            id=cluster.id,
            is_new=True,
            n_visits=1,
            first_seen=cluster.first_seen,
            last_seen=cluster.last_seen,
            centroid=cluster.centroid,
        )

    def cluster_count(self) -> int:
        return len(self._clusters)
