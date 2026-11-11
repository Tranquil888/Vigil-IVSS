import numpy as np

from vigil.analysis.zones import build_zone_masks
from vigil.config.models import ZoneConfig


def test_centered_polygon_covers_the_expected_pixels():
    zones = [
        ZoneConfig(
            name="walk",
            points=[(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)],
        )
    ]
    masks = build_zone_masks(zones, 100, 100)
    assert len(masks) == 1
    assert masks[0].name == "walk"
    assert masks[0].mask[50, 50] == 255
    assert masks[0].mask[5, 5] == 0
    covered = int((masks[0].mask > 0).sum())
    assert 2000 < covered < 3000


def test_exclusion_polygon_removes_its_area():
    zones = [
        ZoneConfig(
            name="walk",
            points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        ),
        ZoneConfig(
            name="timestamp",
            points=[(0.0, 0.0), (0.3, 0.0), (0.3, 0.3), (0.0, 0.3)],
            exclude=True,
        ),
    ]
    masks = build_zone_masks(zones, 100, 100)
    assert len(masks) == 1
    assert masks[0].mask[10, 10] == 0
    assert masks[0].mask[80, 80] == 255


def test_no_zones_means_the_whole_frame():
    masks = build_zone_masks([], 40, 20)
    assert len(masks) == 1
    assert masks[0].name == "all"
    assert (masks[0].mask > 0).all()


def test_zone_threshold_override_is_kept():
    zones = [
        ZoneConfig(
            name="gate",
            points=[(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)],
            threshold_pct=7.5,
        )
    ]
    masks = build_zone_masks(zones, 50, 50)
    assert masks[0].threshold_pct == 7.5


def test_masks_are_uint8():
    masks = build_zone_masks([], 10, 10)
    assert masks[0].mask.dtype == np.uint8
