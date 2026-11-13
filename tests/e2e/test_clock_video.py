"""The burned-clock codec has to work before it can measure anything."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tests.e2e.clock_video import burn_clock, read_clock_ms

pytestmark = pytest.mark.e2e


def test_clock_round_trips_through_a_raw_frame():
    frame = np.zeros((90, 640, 3), dtype=np.uint8)

    burn_clock(frame, 12345)

    assert read_clock_ms(frame) == 12345


def test_clock_rejects_a_frame_without_a_strip():
    frame = np.zeros((90, 640, 3), dtype=np.uint8)

    assert read_clock_ms(frame) is None


def test_clock_survives_jpeg_compression():
    frame = np.zeros((90, 640, 3), dtype=np.uint8)
    burn_clock(frame, 9876)

    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    assert ok
    assert read_clock_ms(decoded) == 9876
