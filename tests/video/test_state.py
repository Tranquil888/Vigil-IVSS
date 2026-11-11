from vigil.video.state import BackoffPolicy, CameraState, OfflineTracker


def test_backoff_grows_and_caps():
    policy = BackoffPolicy(initial_s=1.0, max_s=60.0, jitter=0.0)
    assert policy.delay(0) == 1.0
    assert policy.delay(1) == 2.0
    assert policy.delay(2) == 4.0
    assert policy.delay(10) == 60.0


def test_backoff_jitter_stays_within_bounds():
    policy = BackoffPolicy(initial_s=1.0, max_s=60.0, jitter=0.2)
    for attempt in range(10):
        delay = policy.delay(attempt)
        base = min(60.0, 2.0 ** attempt)
        assert base * 0.8 <= delay <= base * 1.2


def test_offline_event_fires_once_after_the_threshold():
    tracker = OfflineTracker(notify_after_s=120)
    assert tracker.failure(1000.0) is False
    assert tracker.failure(1100.0) is False
    assert tracker.failure(1120.0) is True
    assert tracker.failure(1200.0) is False


def test_reconnect_reports_online_only_if_offline_was_reported():
    tracker = OfflineTracker(notify_after_s=10)
    tracker.failure(0.0)
    assert tracker.frame(1.0) is False
    assert tracker.failure(0.0) is False
    assert tracker.failure(11.0) is True
    assert tracker.frame(12.0) is True


def test_state_enum_has_the_plan_states():
    assert {state.name for state in CameraState} == {
        "INIT",
        "CONNECTING",
        "STREAMING",
        "STALLED",
        "BACKOFF",
        "CLOSED",
    }
