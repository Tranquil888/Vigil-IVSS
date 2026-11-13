"""Offscreen display integration: latest frame, paint, stale state, overlays."""

from __future__ import annotations

import ast
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from tests.e2e.clock_video import burn_clock, read_clock_ms
from vigil.analysis.pipeline import OverlayStore
from vigil.core.queues import LatestFrame
from vigil.core.records import Frame, OverlayItem
from vigil.gui.widgets.video import VideoTile

pytestmark = pytest.mark.e2e


def frame_with_clock(value_ms: int = 4321) -> np.ndarray:
    image = np.full((360, 640, 3), 30, dtype=np.uint8)
    cv2.rectangle(image, (260, 120), (400, 260), (255, 255, 255), -1)
    burn_clock(image, value_ms)
    return image


def test_video_tile_paints_the_newest_frame(qapp, tmp_path):
    latest = LatestFrame()
    overlays = OverlayStore()
    now = time.monotonic()
    image = frame_with_clock()
    latest.put(Frame("front", 0, now, time.time(), image, 640, 360))

    tile = VideoTile(latest, overlays, "front", fps=30.0)
    tile.resize(640, 360)
    tile.show()
    qapp.processEvents()

    assert tile.refresh(now=now + 0.01) is True
    assert tile.status_text() == "Live"

    converted = tmp_path / "converted.png"
    assert tile._image is not None
    assert tile._image.save(str(converted))
    assert read_clock_ms(cv2.imread(str(converted))) == 4321

    grabbed = tile.grab()
    assert not grabbed.isNull()
    grabbed_path = tmp_path / "grabbed.png"
    assert grabbed.save(str(grabbed_path))
    pixels = cv2.imread(str(grabbed_path))
    assert pixels is not None
    assert float(np.std(pixels)) > 5.0

    tile.stop()


def test_video_tile_reports_no_signal_for_a_stale_frame(qapp):
    latest = LatestFrame()
    now = time.monotonic()
    latest.put(
        Frame("front", 0, now - 2.0, time.time(), frame_with_clock(), 640, 360)
    )

    tile = VideoTile(latest, OverlayStore(), "front", fps=30.0)
    tile.resize(640, 360)
    tile.show()
    qapp.processEvents()

    assert tile.refresh(now=now) is False
    assert tile.status_text() == "No signal"

    tile.stop()


def test_overlay_store_expires_items_after_the_ttl():
    store = OverlayStore()
    store.put(
        "front",
        [OverlayItem("front", (0, 0, 10, 10), "Alice", "known", 0.0)],
        ttl=0.05,
        now=100.0,
    )

    assert store.get("front", now=100.01)
    assert store.get("front", now=100.1) == []


def test_gui_modules_do_not_import_dlib():
    gui = Path(__file__).resolve().parents[2] / "src" / "vigil" / "gui"
    offenders = []

    for path in gui.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                if any(name == "dlib" or name.startswith("dlib.") for name in names):
                    offenders.append(str(path))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "dlib" or module.startswith("dlib."):
                    offenders.append(str(path))

    assert offenders == []
