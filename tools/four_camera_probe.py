"""Run the real pipeline against several 1080p files and measure display age.

    python tools/four_camera_probe.py --video-dir data/latency-1080p

Unlike ``video_latency_probe`` this composition starts the real dlib backend,
the real inference worker, the database writer, and four capture threads. The
display consumer only reads ``LatestFrame``, so the inference load must not
change the measured frame age. The probe is the software half of the sprint
criterion; the physical four-camera run is still manual.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

if __package__ in (None, ""):
    root = Path(__file__).resolve().parents[1]
    for entry in (root, root / "src"):
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))

from vigil.config.models import (  # noqa: E402
    CameraConfig,
    CaptureConfig,
    FaceConfig,
    InferenceConfig,
    MotionConfig,
    VigilConfig,
)
from vigil.core.app_context import AppContext  # noqa: E402
from vigil.video.source import VIDEO_SUFFIXES  # noqa: E402

from tools.latency_harness import percentile  # noqa: E402


def resolve_videos(video_dir: str, count: int) -> List[Path]:
    root = Path(video_dir)
    if not root.is_dir():
        raise ValueError("video directory not found: %s" % root)
    found = sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )
    if len(found) < count:
        raise ValueError(
            "asked for %d cameras but only %d videos are available"
            % (count, len(found))
        )
    return found[:count]


def default_models_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Vigil" / "models"
    return Path.home() / ".vigil" / "models"


def build_config(
    paths: List[Path], models: Path, analysis_fps: float
) -> VigilConfig:
    cameras = [
        CameraConfig(
            id="video-%d" % (index + 1),
            name="Video %d" % (index + 1),
            source=str(path),
        )
        for index, path in enumerate(paths)
    ]
    config = VigilConfig(cameras=cameras)
    config.face = FaceConfig(detector="dlib_cnn", models_dir=str(models))
    config.inference = InferenceConfig(
        analysis_fps=analysis_fps,
        queue_size=4,
        max_frame_age_s=60.0,
    )
    config.motion = MotionConfig(enabled=False)
    config.capture = CaptureConfig(
        stall_timeout_s=2.0,
        backoff_initial_s=0.05,
        backoff_max_s=0.2,
        backoff_jitter=0.0,
        offline_notify_after_s=999.0,
    )
    return config


def probe(
    paths: List[Path],
    models: Path,
    seconds: float,
    analysis_fps: float,
    display_interval_ms: float,
) -> dict:
    data_dir = Path(tempfile.mkdtemp(prefix="vigil-four-camera-"))
    config = build_config(paths, models, analysis_fps)
    context = AppContext(config, data_path=data_dir)
    status = context.backend.status
    context.start()

    started = time.monotonic()
    deadline = started + seconds
    interval = max(1.0, display_interval_ms) / 1000.0
    samples: List[float] = []
    per_camera: Dict[str, List[float]] = {camera.id: [] for camera in config.cameras}
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            for camera in config.cameras:
                frame = context.manager.display_queue(camera.id).latest()
                if frame is None or frame.image is None:
                    continue
                age = max(0.0, (now - frame.captured_at) * 1000.0)
                samples.append(age)
                per_camera[camera.id].append(age)
            wait = interval - (time.monotonic() - now)
            if wait > 0:
                time.sleep(wait)
    finally:
        elapsed = time.monotonic() - started
        inference = context.inference.stats()
        camera_stats = context.manager.stats()
        context.shutdown(timeout=8.0)

    if not samples:
        raise RuntimeError("no frames reached the display queue")
    ordered = sorted(samples)
    return {
        "data_dir": str(data_dir),
        "backend": {
            "detector": status.detector,
            "cuda": bool(status.cuda),
            "cudnn": bool(getattr(status, "cudnn", False)),
            "available": bool(status.available),
            "reason": status.reason,
        },
        "display": {
            "p50": round(percentile(ordered, 0.50), 2),
            "p95": round(percentile(ordered, 0.95), 2),
            "p99": round(percentile(ordered, 0.99), 2),
            "max": round(max(ordered), 2),
            "n": len(ordered),
            "duration_s": round(elapsed, 2),
        },
        "inference": inference,
        "cameras": [
            {
                "camera_id": camera.id,
                "frames": next(
                    (
                        row.get("frames")
                        for row in camera_stats
                        if row.get("camera_id") == camera.id
                    ),
                    None,
                ),
                "display": {
                    "p50": round(percentile(per_camera[camera.id], 0.50), 2),
                    "p95": round(percentile(per_camera[camera.id], 0.95), 2),
                    "n": len(per_camera[camera.id]),
                }
                if per_camera[camera.id]
                else None,
            }
            for camera in config.cameras
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-dir", default="data/latency-1080p")
    parser.add_argument("--cameras", type=int, default=4)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--analysis-fps", type=float, default=5.0)
    parser.add_argument("--display-interval-ms", type=float, default=15.0)
    parser.add_argument("--models", default=None)
    parser.add_argument("--max-p95", type=float, default=0.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        paths = resolve_videos(args.video_dir, args.cameras)
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 2
    models = Path(args.models) if args.models else default_models_dir()
    try:
        report = probe(
            paths,
            models,
            max(1.0, args.seconds),
            max(0.1, args.analysis_fps),
            max(1.0, args.display_interval_ms),
        )
    except RuntimeError as err:
        print(str(err), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        display = report["display"]
        backend = report["backend"]
        print(
            "four-camera probe: %s on %s, %d samples in %.1f s"
            % (
                backend["detector"],
                "GPU" if backend["cuda"] else "CPU",
                display["n"],
                display["duration_s"],
            )
        )
        print(
            "  display   p50 %.1f ms, p95 %.1f ms, p99 %.1f ms, max %.1f ms"
            % (display["p50"], display["p95"], display["p99"], display["max"])
        )
        print(
            "  inference frames=%s faces=%s errors=%s dropped=%s"
            % (
                report["inference"].get("frames"),
                report["inference"].get("faces"),
                report["inference"].get("errors"),
                report["inference"].get("dropped"),
            )
        )
        if backend["reason"]:
            print("  backend note: %s" % backend["reason"])

    if args.max_p95 > 0 and report["display"]["p95"] > args.max_p95:
        print(
            "p95 %.1f ms exceeds the %.1f ms budget"
            % (report["display"]["p95"], args.max_p95),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
