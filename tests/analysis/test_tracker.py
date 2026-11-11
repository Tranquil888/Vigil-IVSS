from vigil.analysis.tracker import IouTracker


def test_track_keeps_its_id_across_small_motion():
    tracker = IouTracker(iou_threshold=0.3, max_gap_s=1.0)
    first = tracker.update([(10, 10, 50, 50)], now=0.0)
    second = tracker.update([(12, 11, 50, 50)], now=0.1)
    assert first[0].id == second[0].id
    assert second[0].observations == 2


def test_non_overlapping_detection_gets_a_new_id():
    tracker = IouTracker(iou_threshold=0.3, max_gap_s=1.0)
    first = tracker.update([(10, 10, 50, 50)], now=0.0)
    second = tracker.update([(300, 300, 50, 50)], now=0.1)
    assert first[0].id != second[0].id


def test_stale_track_is_closed_after_the_gap():
    tracker = IouTracker(iou_threshold=0.3, max_gap_s=1.0)
    tracker.update([(10, 10, 50, 50)], now=0.0)
    assert tracker.close_stale(now=0.5) == []
    closed = tracker.close_stale(now=2.0)
    assert len(closed) == 1
    assert closed[0].last_seen == 0.0


def test_close_all_returns_open_tracks_once():
    tracker = IouTracker(iou_threshold=0.3, max_gap_s=1.0)
    tracker.update([(10, 10, 50, 50), (200, 200, 40, 40)], now=0.0)
    closed = tracker.close_all()
    assert len(closed) == 2
    assert tracker.close_all() == []


def test_two_faces_keep_separate_ids():
    tracker = IouTracker(iou_threshold=0.3, max_gap_s=1.0)
    tracks = tracker.update([(0, 0, 40, 40), (200, 0, 40, 40)], now=0.0)
    assert tracks[0].id != tracks[1].id
