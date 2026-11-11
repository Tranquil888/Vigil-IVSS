import time

from vigil.core.bus import EventBus
from vigil.core.records import EventRecord, EventType, NotificationRecord
from vigil.storage.reader import Reader
from vigil.storage.schema import create_schema, make_engine
from vigil.storage.writer import DBWriterThread


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_writer_persists_events_and_stops_quickly(tmp_path):
    db = tmp_path / "vigil.db"
    create_schema(make_engine(db))
    bus = EventBus()
    writer = DBWriterThread(bus, db)
    writer.start()

    for index in range(500):
        bus.publish(
            EventRecord(
                camera_id="front",
                type=EventType.MOTION,
                ts_start=float(index),
                dedupe_key="motion:%d" % index,
            )
        )

    reader = Reader(db)
    assert wait_for(lambda: reader.count_events() == 500)

    started = time.monotonic()
    writer.stop(timeout=5)
    assert time.monotonic() - started < 5
    assert not writer.is_alive()


def test_duplicate_dedupe_key_is_inserted_once(tmp_path):
    db = tmp_path / "vigil.db"
    create_schema(make_engine(db))
    bus = EventBus()
    writer = DBWriterThread(bus, db)
    writer.start()

    record = EventRecord(
        camera_id="front",
        type=EventType.STRANGER,
        ts_start=10.0,
        dedupe_key="stranger:1:0",
    )
    bus.publish(record)
    bus.publish(record)

    reader = Reader(db)
    assert wait_for(lambda: reader.count_events() == 1)
    time.sleep(0.1)
    assert reader.count_events() == 1
    writer.stop()


def test_writer_stores_tracklet_attached_to_event(tmp_path):
    db = tmp_path / "vigil.db"
    engine = create_schema(make_engine(db))
    from .conftest import seed_person

    seed_person(engine, 3, "Cara")
    bus = EventBus()
    writer = DBWriterThread(bus, db)
    writer.start()

    bus.publish(
        EventRecord(
            camera_id="front",
            type=EventType.KNOWN_FACE,
            ts_start=5.0,
            person_id=3,
            dedupe_key="known:1",
            detail={
                "tracklet": {
                    "camera_id": "front",
                    "started_at": 4.0,
                    "ended_at": 6.0,
                    "decision": "known",
                    "person_id": 3,
                    "agg_score": 0.31,
                    "n_obs": 4,
                }
            },
        )
    )

    reader = Reader(db)
    assert wait_for(lambda: reader.count_events() == 1)
    assert reader.tracklets()[0]["n_obs"] == 4
    assert reader.events()[0]["tracklet_id"] is not None
    writer.stop()


def test_notification_rows_are_written(tmp_path):
    db = tmp_path / "vigil.db"
    create_schema(make_engine(db))
    bus = EventBus()
    writer = DBWriterThread(bus, db)
    writer.start()

    bus.publish(
        NotificationRecord(
            event_id=None, channel="desktop", status="shown", body="Stranger"
        )
    )

    reader = Reader(db)
    assert wait_for(lambda: reader.count_notifications() == 1)
    writer.stop()


def test_writer_survives_a_bad_record(tmp_path):
    db = tmp_path / "vigil.db"
    create_schema(make_engine(db))
    bus = EventBus()
    writer = DBWriterThread(bus, db)
    writer.start()

    bus.publish(object())
    bus.publish(
        EventRecord(
            camera_id="front",
            type=EventType.MOTION,
            ts_start=1.0,
            dedupe_key="after-bad",
        )
    )

    reader = Reader(db)
    assert wait_for(lambda: reader.count_events() == 1)
    assert writer.errors >= 1
    writer.stop()
