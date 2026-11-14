"""Measure display latency and queue drops for several video-file cameras.

    python tools/video_latency_probe.py --video-dir data/chokepoint/videos --seconds 15

The probe builds the real camera manager with one ``VideoFileSource`` per
camera, runs the real capture threads, and consumes inference on a deliberately
slow thread. The display side only reads ``LatestFrame``, so the inference delay
must not reach the measured frame age. The report includes per-camera frame
counts, inference drops, reconnects, and the p50/p95/p99 frame age.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
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
    InferenceConfig,
    MotionConfig,
    VigilConfig,
)
from vigil.video.manager import CameraManager  # noqa: E402
from vigil.video.source import VIDEO_SUFFIXES, VideoFileSource  # noqa: E402

from tools.latency_harness import percentile  # noqa: E402


def resolve_videos(videos: List[str], video_dir: Optional[str], count: int) -> List[Path]:
    paths = [Path(item) for item in videos]
    if video_dir:
        root = Path(video_dir)
        if not root.is_dir():
            raise ValueError("video directory not found: %s" % root)
        found = sorted(
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
        )
        paths.extend(found)
    if not paths:
        raise ValueError("no videos given; use --video or --video-dir")
    if len(paths) < count:
        raise ValueError(
            "asked for %d cameras but only %d videos are available"
            % (count, len(paths))
        )
    return paths[:count]


def build_config(paths: List[Path], queue_size: int, analysis_fps: float) -> VigilConfig:
    cameras = [
        CameraConfig(
            id="video-%d" % (index + 1),
            name="Video %d" % (index + 1),
            source=str(path),
        )
        for index, path in enumerate(paths)
    ]
    config = VigilConfig(cameras=cameras)
    config.inference = InferenceConfig(
        analysis_fps=analysis_fps,
        queue_size=queue_size,
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


def summarize(samples: List[float], duration_s: float) -> dict:
    if not samples:
        raise RuntimeError("no frames reached the display queue")
    ordered = sorted(samples)
    return {
        "p50": round(percentile(ordered, 0.50), 2),
        "p95": round(percentile(ordered, 0.95), 2),
        "p99": round(percentile(ordered, 0.99), 2),
        "max": round(max(ordered), 2),
        "n": len(ordered),
        "duration_s": round(duration_s, 2),
    }


def probe(
    paths: List[Path],
    seconds: float,
    display_interval_ms: float,
    inference_delay_ms: float,
    queue_size: int,
    analysis_fps: float,
) -> dict:
    config = build_config(paths, queue_size, analysis_fps)
    by_id: Dict[str, Path] = {
        camera.id: paths[index] for index, camera in enumerate(config.cameras)
    }
    manager = CameraManager(
        config,
        source_factory=lambda camera: VideoFileSource([str(by_id[camera.id])]),
    )
    manager.start_all()

    stop = threading.Event()

    def consume_inference() -> None:
        while not stop.is_set():
            frame = manager.inference_queue.get(timeout=0.02)
            if frame is None:
                continue
            if inference_delay_ms > 0:
                time.sleep(inference_delay_ms / 1000.0)

    consumer = threading.Thread(
        target=consume_inference, name="probe-inference", daemon=True
    )
    consumer.start()

    started = time.monotonic()
    deadline = started + seconds
    interval = max(1.0, display_interval_ms) / 1000.0
    samples: List[float] = []
    per_camera: Dict[str, List[float]] = {camera.id: [] for camera in config.cameras}
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            for camera in config.cameras:
                frame = manager.display_queue(camera.id).latest()
                if frame is None or frame.image is None:
                    continue
                age = max(0.0, (now - frame.captured_at) * 1000.0)
                samples.append(age)
                per_camera[camera.id].append(age)
            wait = interval - (time.monotonic() - now)
            if wait > 0:
                time.sleep(wait)
    finally:
        stop.set()
        consumer.join(timeout=1.0)
        manager.stop_all(timeout=4.0)

    stats = {item["camera_id"]: item for item in manager.stats()}
    cameras = []
    for camera in config.cameras:
        row = stats.get(camera.id, {})
        camera_samples = per_camera[camera.id]
        cameras.append(
            {
                "camera_id": camera.id,
                "video": str(by_id[camera.id]),
                "frames": row.get("frames"),
                "inference_sent": row.get("inference_sent"),
                "reconnects": row.get("reconnects"),
                "state": row.get("state"),
                "display": {
                    "p50": round(percentile(camera_samples, 0.50), 2),
                    "p95": round(percentile(camera_samples, 0.95), 2),
                    "n": len(camera_samples),
                }
                if camera_samples
                else None,
            }
        )

    return {
        "cameras": cameras,
        "display": summarize(samples, time.monotonic() - started),
        "inference_delay_ms": inference_delay_ms,
        "queue_size": queue_size,
        "analysis_fps": analysis_fps,
        "inference_dropped": manager.inference_queue.dropped,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", action="append", default=[], help="video file; repeatable")
    parser.add_argument("--video-dir", default=None, help="use the first files in a folder")
    parser.add_argument("--cameras", type=int, default=4)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--display-interval-ms", type=float, default=15.0)
    parser.add_argument("--inference-delay-ms", type=float, default=150.0)
    parser.add_argument("--queue-size", type=int, default=4)
    parser.add_argument("--analysis-fps", type=float, default=5.0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--max-p95",
        type=float,
        default=0.0,
        help="exit non-zero when combined p95 exceeds this many milliseconds",
    )
    args = parser.parse_args(argv)

    try:
        paths = resolve_videos(args.video, args.video_dir, args.cameras)
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 2

    report = probe(
        paths,
        seconds=max(0.5, args.seconds),
        display_interval_ms=args.display_interval_ms,
        inference_delay_ms=max(0.0, args.inference_delay_ms),
        queue_size=max(1, args.queue_size),
        analysis_fps=max(0.1, args.analysis_fps),
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        display = report["display"]
        print(
            "video latency: %d cameras, %d samples in %.1f s"
            % (len(report["cameras"]), display["n"], display["duration_s"])
        )
        print(
            "  display   p50 %.1f ms, p95 %.1f ms, p99 %.1f ms, max %.1f ms"
            % (
                display["p50"],
                display["p95"],
                display["p99"],
                display["max"],
            )
        )
        print(
            "  inference delay %.0f ms, queue %d, dropped %d"
            % (
                report["inference_delay_ms"],
                report["queue_size"],
                report["inference_dropped"],
            )
        )
        for camera in report["cameras"]:
            shown = camera["display"]
            print(
                "  %-8s frames=%s sent=%s reconnects=%s state=%s p95=%s"
                % (
                    camera["camera_id"],
                    camera["frames"],
                    camera["inference_sent"],
                    camera["reconnects"],
                    camera["state"],
                    "n/a" if shown is None else "%.1f ms" % shown["p95"],
                )
            )

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
