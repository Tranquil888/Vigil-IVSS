import threading
import time

import numpy as np

from vigil.core.queues import DropOldestQueue, LatestFrame
from vigil.core.records import Frame


def frame(index: int) -> Frame:
    return Frame(
        camera_id="front",
        index=index,
        captured_at=time.monotonic(),
        wall_time=time.time(),
        image=np.zeros((2, 2, 3), dtype=np.uint8),
    )


def test_latest_frame_keeps_only_the_newest():
    latest = LatestFrame()
    started = time.monotonic()
    for index in range(100):
        latest.put(frame(index))
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert latest.latest().index == 99
    assert latest.generation == 100


def test_latest_frame_get_times_out_without_a_frame():
    latest = LatestFrame()
    started = time.monotonic()
    assert latest.get(timeout=0.05) is None
    assert time.monotonic() - started < 0.5


def test_latest_frame_get_returns_the_next_frame():
    latest = LatestFrame()
    result = {}

    def reader():
        result["frame"] = latest.get(timeout=2.0)

    thread = threading.Thread(target=reader)
    thread.start()
    time.sleep(0.05)
    latest.put(frame(7))
    thread.join(2.0)
    assert result["frame"].index == 7


def test_drop_oldest_keeps_insertion_order_and_counts_drops():
    queue = DropOldestQueue(maxsize=2)
    assert queue.put("a") == 0
    assert queue.put("b") == 0
    assert queue.put("c") == 1
    assert queue.put("d") == 1
    assert queue.qsize() == 2
    assert queue.get(timeout=0) == "c"
    assert queue.get(timeout=0) == "d"
    assert queue.get(timeout=0) is None


def test_bounded_queue_get_waits_for_an_item():
    queue = DropOldestQueue(maxsize=2)
    result = {}

    def reader():
        result["item"] = queue.get(timeout=2.0)

    thread = threading.Thread(target=reader)
    thread.start()
    time.sleep(0.05)
    queue.put("x")
    thread.join(2.0)
    assert result["item"] == "x"


def test_queue_close_wakes_a_waiting_reader():
    queue = DropOldestQueue(maxsize=2)
    result = {}

    def reader():
        result["item"] = queue.get(timeout=5.0)

    thread = threading.Thread(target=reader)
    thread.start()
    time.sleep(0.05)
    queue.close()
    thread.join(2.0)
    assert result["item"] is None
