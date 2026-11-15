"""Build local 1080p videos for capture and display latency runs.

    python tools/make_test_videos.py --out data/latency-1080p --count 4

No download is involved. Each file is a moving pattern with a frame counter,
which is enough to keep a real decoder busy and to show that frames advance.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np


def build_video(path: Path, index: int, seconds: float, fps: float) -> None:
    width, height = 1920, 1080
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not open a writer for %s" % path)
    total = max(1, int(seconds * fps))
    try:
        for frame_index in range(total):
            frame = np.full((height, width, 3), 18 + index * 6, dtype=np.uint8)
            x = int((frame_index * 7 + index * 60) % (width - 240))
            y = int((frame_index * 3 + index * 90) % (height - 160))
            cv2.rectangle(frame, (x, y), (x + 220, y + 140), (60, 200, 90), -1)
            cv2.rectangle(frame, (x + 24, y + 20), (x + 196, y + 120), (20, 40, 24), 3)
            cv2.putText(
                frame,
                "cam %d  frame %06d" % (index + 1, frame_index),
                (40, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.4,
                (235, 238, 240),
                3,
                cv2.LINE_AA,
            )
            writer.write(frame)
    finally:
        writer.release()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/latency-1080p")
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    for index in range(max(1, args.count)):
        path = root / ("cam-%d.mp4" % (index + 1))
        if path.exists() and not args.force:
            print("keep", path)
            continue
        build_video(path, index, max(1.0, args.seconds), max(1.0, args.fps))
        size = path.stat().st_size / (1024 * 1024)
        print("wrote %s (%.1f MB)" % (path, size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
