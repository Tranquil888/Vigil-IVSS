import json
import logging

from vigil.telemetry.logging_setup import setup_logging


def test_log_lines_are_json_and_redacted(tmp_path):
    logger = setup_logging(tmp_path, level="INFO", force=True)
    logger.info(
        "camera open failed for rtsp://admin:hunter2@10.0.0.5/sub",
        extra={"event": "camera.open_failed", "camera_id": "front"},
    )
    logging.shutdown()

    files = list(tmp_path.glob("*.log"))
    assert files
    lines = [line for line in files[0].read_text(encoding="utf-8").splitlines() if line]
    assert lines
    payload = json.loads(lines[0])
    assert payload["event"] == "camera.open_failed"
    assert payload["camera_id"] == "front"
    assert "hunter2" not in lines[0]


def test_logger_can_be_created_twice_without_duplicate_handlers(tmp_path):
    first = setup_logging(tmp_path, force=True)
    count = len(first.handlers)
    second = setup_logging(tmp_path, force=True)
    assert len(second.handlers) == count


def test_prune_removes_old_log_files(tmp_path):
    import os
    import time

    from vigil.telemetry.logging_setup import prune_old_logs

    old = tmp_path / "vigil-old.log"
    old.write_text("old", encoding="utf-8")
    past = time.time() - 20 * 86400
    os.utime(old, (past, past))

    fresh = tmp_path / "vigil-new.log"
    fresh.write_text("new", encoding="utf-8")

    removed = prune_old_logs(tmp_path, days=14)
    assert removed == 1
    assert not old.exists()
    assert fresh.exists()
