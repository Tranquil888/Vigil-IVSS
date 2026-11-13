"""Runtime report used by the Diagnostics page and the gray-box probe.

The report is plain data. Nothing here touches a queue or starts a worker, so
it is safe to call from the GUI thread while the pipeline runs.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

from .analysis.backend import CNN_MODEL, FACE_MODEL, SHAPE_MODEL
from .paths import db_path, models_for, people_dir, snapshots_dir


def _model_state(directory: Path) -> Dict[str, bool]:
    return {
        name: (directory / name).is_file()
        for name in (CNN_MODEL, SHAPE_MODEL, FACE_MODEL)
    }


def _count(reader, method: str):
    action = getattr(reader, method, None)
    if not callable(action):
        return None
    try:
        return int(action())
    except Exception:
        return None


def build_report(context) -> Dict[str, Any]:
    config = getattr(context, "config", None)
    data_path = Path(getattr(context, "data_path", "."))
    models = models_for(config, data_path) if config is not None else data_path / "models"
    status = getattr(context, "status", None)
    reader = getattr(context, "reader", None)

    report: Dict[str, Any] = {
        "generated_at": time.time(),
        "pid": os.getpid(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "paths": {
            "data": str(data_path),
            "database": str(db_path(config, data_path)) if config is not None else "",
            "models": str(models),
            "people": str(people_dir(config, data_path)) if config is not None else "",
            "snapshots": str(snapshots_dir(config, data_path))
            if config is not None
            else "",
        },
        "models": _model_state(models),
        "backend": {
            "available": getattr(status, "available", None),
            "cuda": getattr(status, "cuda", None),
            "cudnn": getattr(status, "cudnn", None),
            "detector": getattr(status, "detector", None),
            "reason": getattr(status, "reason", None),
            "can_embed": bool(getattr(getattr(context, "backend", None), "can_embed", False)),
        },
        "database": {
            "events": _count(reader, "count_events"),
            "notifications": _count(reader, "count_notifications"),
            "people": _count(reader, "count_people"),
            "snapshots": _count(reader, "count_snapshots"),
            "unknown_clusters": _count(reader, "count_unknown_clusters"),
        },
        "config": {},
        "runtime": {},
    }

    if config is not None:
        report["config"] = {
            "cameras": [camera.id for camera in config.cameras],
            "enabled_cameras": [camera.id for camera in config.cameras if camera.enabled],
            "analysis_fps": config.inference.analysis_fps,
            "queue_size": config.inference.queue_size,
            "detector": config.face.detector,
            "motion_enabled": config.motion.enabled,
            "event_retention_days": config.storage.event_retention_days,
        }

    stats = getattr(context, "stats", None)
    if callable(stats):
        try:
            report["runtime"] = stats()
        except Exception as err:
            report["runtime"] = {"error": str(err)}
    return report


def _fmt(value) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def format_report(report: Dict[str, Any]) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report["generated_at"]))
    lines = [
        "Vigil diagnostics  %s" % stamp,
        "process %s, Python %s, %s"
        % (report.get("pid"), report.get("python"), report.get("platform")),
        "",
        "Paths",
    ]
    for name, value in (report.get("paths") or {}).items():
        lines.append("  %-10s %s" % (name, value))

    models = report.get("models") or {}
    lines.append("")
    lines.append("Models")
    for name, present in models.items():
        lines.append("  %-38s %s" % (name, "present" if present else "MISSING"))

    backend = report.get("backend") or {}
    lines.append("")
    lines.append("Backend")
    lines.append("  detector   %s" % _fmt(backend.get("detector")))
    lines.append("  CUDA       %s" % _fmt(backend.get("cuda")))
    lines.append("  cuDNN      %s" % _fmt(backend.get("cudnn")))
    lines.append("  embedding  %s" % _fmt(backend.get("can_embed")))
    lines.append("  reason     %s" % _fmt(backend.get("reason")))

    database = report.get("database") or {}
    lines.append("")
    lines.append("Database")
    for name, value in database.items():
        lines.append("  %-16s %s" % (name, _fmt(value)))

    config = report.get("config") or {}
    if config:
        lines.append("")
        lines.append("Config")
        lines.append(
            "  cameras    %s" % (", ".join(config.get("cameras") or []) or "none")
        )
        lines.append(
            "  enabled    %s"
            % (", ".join(config.get("enabled_cameras") or []) or "none")
        )
        lines.append(
            "  fps %s, queue %s, detector %s, motion %s"
            % (
                _fmt(config.get("analysis_fps")),
                _fmt(config.get("queue_size")),
                _fmt(config.get("detector")),
                _fmt(config.get("motion_enabled")),
            )
        )

    runtime = report.get("runtime") or {}
    if runtime:
        lines.append("")
        lines.append("Runtime")
        threads = runtime.get("threads") or []
        alive = sum(1 for thread in threads if thread.get("alive"))
        lines.append("  threads    %d alive, %d dead" % (alive, len(threads) - alive))
        for thread in threads:
            if not thread.get("alive"):
                lines.append("    DEAD %s" % thread.get("name"))
        for key in ("inference", "database", "notifier"):
            block = runtime.get(key)
            if isinstance(block, dict):
                lines.append(
                    "  %-10s %s"
                    % (key, ", ".join("%s=%s" % (k, v) for k, v in block.items()))
                )
        for camera in runtime.get("cameras") or []:
            lines.append(
                "  camera %-10s state=%s frames=%s reconnects=%s inference_sent=%s"
                % (
                    camera.get("camera_id"),
                    camera.get("state"),
                    camera.get("frames"),
                    camera.get("reconnects"),
                    camera.get("inference_sent"),
                )
            )
    return "\n".join(lines)
