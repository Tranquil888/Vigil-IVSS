"""Print a gray-box report for a Vigil config and, optionally, a live run.

    python scripts/graybox_probe.py
    python scripts/graybox_probe.py --run 10 --fake-camera --json

Without ``--run`` the script builds the context, probes the backend, reads the
database, and exits. With ``--run`` it also starts the real workers for the
given number of seconds, so queue depths, thread liveness, and camera state can
be observed. ``--fake-camera`` replaces every configured camera with a
synthetic source, which makes the probe safe on a machine without cameras.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from vigil.config.loader import ConfigError, load_config
from vigil.config.models import CameraConfig, MotionConfig
from vigil.core.app_context import AppContext
from vigil.diagnostics import build_report, format_report
from vigil.video.source import FakeSource


def probe_frame(index: int) -> np.ndarray:
    frame = np.full((240, 320, 3), 24, dtype=np.uint8)
    left = 20 + (index * 4) % 240
    cv2.rectangle(frame, (left, 70), (left + 40, 130), (230, 230, 230), -1)
    rng = np.random.default_rng(index)
    frame[80:150, 140:210] = rng.integers(0, 255, (70, 70, 3), dtype=np.uint8)
    return frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="path to config.toml")
    parser.add_argument("--data-dir", default=None, help="override the data directory")
    parser.add_argument(
        "--run",
        type=float,
        default=0.0,
        help="seconds to run the real workers before reporting (0 means inspect only)",
    )
    parser.add_argument(
        "--fake-camera",
        action="store_true",
        help="replace configured cameras with a synthetic 320x240 source",
    )
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--log-level", default="WARNING")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.WARNING),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        config = load_config(Path(args.config) if args.config else None)
    except ConfigError as err:
        print("Vigil: %s" % err, file=sys.stderr)
        return 2

    if args.fake_camera:
        if not config.cameras:
            config.cameras.append(
                CameraConfig(id="probe", name="Gray-box probe", source="fake://")
            )
        config.motion = MotionConfig(
            enabled=True,
            sample_every=1,
            max_side=160,
            threshold_pct=0.5,
            min_area_px=20,
            min_duration_frames=2,
            cooldown_s=0.5,
            suppress_global_pct=90.0,
        )
        for camera in config.cameras:
            camera.motion = None
            camera.enabled = True

    factory = None
    if args.fake_camera:
        factory = lambda camera: FakeSource(  # noqa: E731 - one local factory
            read_delay=1.0 / 30.0, frame_factory=probe_frame
        )

    data_path = Path(args.data_dir) if args.data_dir else None
    context = AppContext(config, data_path=data_path, source_factory=factory)
    started = time.monotonic()
    try:
        if args.run > 0:
            context.start()
            time.sleep(float(args.run))
        report = build_report(context)
        report["probe"] = {
            "config": str(args.config) if args.config else None,
            "data_dir": str(context.data_path),
            "ran_seconds": round(time.monotonic() - started, 2),
            "fake_camera": bool(args.fake_camera),
        }
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            print(format_report(report))
            print("")
            print(
                "probe: ran %.2f s, fake_camera=%s, data=%s"
                % (
                    report["probe"]["ran_seconds"],
                    report["probe"]["fake_camera"],
                    report["probe"]["data_dir"],
                )
            )
        return 0
    finally:
        context.shutdown(timeout=5.0)


if __name__ == "__main__":
    raise SystemExit(main())
