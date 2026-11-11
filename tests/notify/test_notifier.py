from vigil.config.models import NotifyConfig
from vigil.core.bus import EventBus
from vigil.core.records import EventRecord, EventType, NotificationRecord
from vigil.notify.notifier import Notifier


def stranger(camera_id="front", cluster_id=7, ts=100.0):
    return EventRecord(
        camera_id=camera_id,
        type=EventType.STRANGER,
        ts_start=ts,
        unknown_cluster_id=cluster_id,
    )


def known(camera_id="front", person_id=1, ts=100.0):
    return EventRecord(
        camera_id=camera_id,
        type=EventType.KNOWN_FACE,
        ts_start=ts,
        person_id=person_id,
    )


def test_second_stranger_inside_cooldown_is_suppressed():
    toasts = []
    notifier = Notifier(
        config=NotifyConfig(desktop_enabled=True, stranger_cooldown_s=120.0),
        toast_callback=lambda title, body: toasts.append((title, body)),
        clock=lambda: 0.0,
    )

    first = notifier.handle(stranger(), now=100.0)
    second = notifier.handle(stranger(), now=110.0)

    assert isinstance(first, NotificationRecord)
    assert first.status == "shown"
    assert second.status == "suppressed"
    assert second.reason == "cooldown"
    assert len(toasts) == 1


def test_stranger_after_the_cooldown_is_shown_again():
    toasts = []
    notifier = Notifier(
        config=NotifyConfig(desktop_enabled=True, stranger_cooldown_s=120.0),
        toast_callback=lambda title, body: toasts.append(title),
    )

    notifier.handle(stranger(), now=100.0)
    later = notifier.handle(stranger(), now=221.0)

    assert later.status == "shown"
    assert len(toasts) == 2


def test_different_cluster_or_camera_has_its_own_cooldown():
    toasts = []
    notifier = Notifier(
        config=NotifyConfig(desktop_enabled=True, stranger_cooldown_s=120.0),
        toast_callback=lambda title, body: toasts.append(title),
    )

    notifier.handle(stranger(camera_id="front", cluster_id=7), now=100.0)
    other_cluster = notifier.handle(stranger(camera_id="front", cluster_id=8), now=101.0)
    other_camera = notifier.handle(stranger(camera_id="gate", cluster_id=7), now=102.0)

    assert other_cluster.status == "shown"
    assert other_camera.status == "shown"
    assert len(toasts) == 3


def test_disabled_desktop_still_records_the_attempt():
    bus = EventBus()
    queue = bus.subscribe(8)
    notifier = Notifier(
        bus=bus,
        config=NotifyConfig(desktop_enabled=False),
        toast_callback=lambda title, body: (_ for _ in ()).throw(AssertionError("toast")),
    )

    record = notifier.handle(stranger(), now=100.0)

    assert record.status == "disabled"
    assert queue.get(timeout=0.1) is record


def test_known_face_toast_names_the_person():
    toasts = []
    notifier = Notifier(
        config=NotifyConfig(desktop_enabled=True),
        toast_callback=lambda title, body: toasts.append((title, body)),
        names={1: "Ann"},
    )

    record = notifier.handle(known(person_id=1), now=100.0)

    assert record.status == "shown"
    assert "Ann" in toasts[0][0]
    assert "Ann" in toasts[0][1]


def test_events_that_do_not_deserve_a_toast_are_ignored():
    notifier = Notifier(config=NotifyConfig(desktop_enabled=True))
    motion = EventRecord(camera_id="front", type=EventType.MOTION, ts_start=1.0)

    assert notifier.handle(motion, now=100.0) is None
