"""Polygon zones rasterized once into binary masks at working resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import cv2
import numpy as np

from ..config.models import ZoneConfig


@dataclass
class ZoneMask:
    name: str
    mask: np.ndarray
    threshold_pct: float


def _polygon(points: Sequence[tuple], width: int, height: int) -> np.ndarray:
    pixel = np.array(
        [
            [
                int(round(x * (width - 1))),
                int(round(y * (height - 1))),
            ]
            for x, y in points
        ],
        dtype=np.int32,
    )
    return pixel.reshape((-1, 1, 2))


def build_zone_masks(
    zones: List[ZoneConfig],
    width: int,
    height: int,
    default_threshold: float = 2.0,
) -> List[ZoneMask]:
    width = max(1, int(width))
    height = max(1, int(height))
    includes = [zone for zone in zones if not zone.exclude]
    excludes = [zone for zone in zones if zone.exclude]

    exclusion = np.zeros((height, width), dtype=np.uint8)
    for zone in excludes:
        cv2.fillPoly(exclusion, [_polygon(zone.points, width, height)], 255)

    if includes:
        result = []
        for zone in includes:
            mask = np.zeros((height, width), dtype=np.uint8)
            cv2.fillPoly(mask, [_polygon(zone.points, width, height)], 255)
            mask[exclusion > 0] = 0
            result.append(
                ZoneMask(
                    name=zone.name,
                    mask=mask,
                    threshold_pct=(
                        zone.threshold_pct
                        if zone.threshold_pct is not None
                        else default_threshold
                    ),
                )
            )
        return result

    mask = np.full((height, width), 255, dtype=np.uint8)
    mask[exclusion > 0] = 0
    return [ZoneMask(name="all", mask=mask, threshold_pct=default_threshold)]
