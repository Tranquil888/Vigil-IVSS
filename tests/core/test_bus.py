import time
from dataclasses import dataclass

from vigil.core.bus import EventBus
from vigil.core.records import EventRecord, EventType


def event(index: int) -> EventRecord:
    return EventRecord(
        camera_id="front",
        type=EventType.MOTION,
        ts_start=float(index),
        dedupe_key="motion:%d" % index,
    )


def test_a_slow_subscriber_cannot_block_publish():
    bus = EventBus()
    slow = bus.subscribe(maxsize=1)
    started = time.monotonic()
    for index in range(1000):
        bus.publish(event(index))
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert slow.qsize() == 1
    assert slow.get(timeout=0).dedupe_key == "motion:999"


def test_every_subscriber_receives_the_event():
    bus = EventBus()
    first = bus.subscribe()
    second = bus.subscribe()
    bus.publish(event(1))
    assert first.get(timeout=0).dedupe_key == "motion:1"
    assert second.get(timeout=0).dedupe_key == "motion:1"


def test_unsubscribed_queue_stops_receiving():
    bus = EventBus()
    queue = bus.subscribe()
    bus.unsubscribe(queue)
    bus.publish(event(2))
    assert queue.get(timeout=0) is None
