import numpy as np

from vigil.analysis.pipeline import OverlayStore
from vigil.core.queues import LatestFrame
from vigil.core.records import Frame, OverlayItem
from vigil.gui.widgets.video import VideoTile


def make_tile():
    latest = LatestFrame()
    overlays = OverlayStore()
    tile = VideoTile(latest, overlays, "front", fps=30, stale_after_s=1.0)
    tile.resize(320, 180)
    return tile, latest, overlays


def test_tile_paints_a_fresh_frame_then_shows_no_signal(qapp):
    tile, latest, _overlays = make_tile()
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    latest.put(Frame("front", 1, 100.0, 100.0, image, 64, 48))

    assert tile.refresh(now=100.5) is True
    assert tile.status_text() == "Live"
    assert tile._image is not None
    assert tile._image.width() == 64

    assert tile.refresh(now=102.0) is False
    assert tile.status_text() == "No signal"
    tile.stop()


def test_tile_reads_overlays_it_is_given(qapp):
    tile, latest, overlays = make_tile()
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    latest.put(Frame("front", 1, 100.0, 100.0, image, 64, 48))
    overlays.put(
        "front",
        [OverlayItem("front", (4, 4, 20, 20), "Ann", "known", 0.0)],
        ttl=1.0,
        now=100.0,
    )
    tile.refresh(now=100.5)
    assert len(overlays.get("front", now=100.5)) == 1
    tile.stop()


def test_tile_reports_no_signal_without_a_frame(qapp):
    tile, _latest, _overlays = make_tile()
    assert tile.refresh(now=100.0) is False
    assert tile.status_text() == "No signal"
    tile.stop()
