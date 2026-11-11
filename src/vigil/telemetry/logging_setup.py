"""Rotating JSON-lines developer log with redaction on every line."""

from __future__ import annotations

import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from .redaction import redact_text

LOGGER_NAME = "vigil"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.name),
            "message": record.getMessage(),
        }
        camera_id = getattr(record, "camera_id", None)
        if camera_id:
            payload["camera_id"] = camera_id
        detail = getattr(record, "detail", None)
        if detail is not None:
            payload["detail"] = detail
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return redact_text(json.dumps(payload, ensure_ascii=False, default=str))


class _RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = ()
        return True


def setup_logging(
    log_dir: Union[str, Path],
    level: str = "INFO",
    max_bytes: int = 10_000_000,
    backups: int = 5,
    force: bool = False,
) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    logger.propagate = False

    if logger.handlers and not force:
        return logger
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / "vigil.log",
        maxBytes=max_bytes,
        backupCount=backups,
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    handler.addFilter(_RedactionFilter())
    logger.addHandler(handler)

    if os.environ.get("VIGIL_LOG_STDERR"):
        stream = logging.StreamHandler()
        stream.setFormatter(JsonFormatter())
        logger.addHandler(stream)

    return logger


def prune_old_logs(log_dir: Union[str, Path], days: int = 14) -> int:
    cutoff = time.time() - days * 86400
    removed = 0
    for path in Path(log_dir).glob("*.log*"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed
