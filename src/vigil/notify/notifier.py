"""Desktop notifications with a cooldown. Never blocks the inference thread."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, Optional, Tuple

from ..config.models import NotifyConfig
from ..core.records import EventRecord, EventType, NotificationRecord

log = logging.getLogger(__name__)

_WORTH_A_TOAST = frozenset({EventType.KNOWN_FACE, EventType.STRANGER})


class Notifier(threading.Thread):
    def __init__(
        self,
        bus=None,
        config: Optional[NotifyConfig] = None,
        toast_callback: Optional[Callable[[str, str], None]] = None,
        names: Optional[Dict[int, str]] = None,
        queue_size: int = 256,
        clock: Callable[[], float] = time.time,
    ) -> None:
        super().__init__(name="vigil-notifier", daemon=True)
        self._config = config or NotifyConfig()
        self._toast = toast_callback
        self._names = dict(names or {})
        self._clock = clock
        self._queue = bus.subscribe(queue_size) if bus is not None else None
        self._bus = bus
        self._stop_event = threading.Event()
        self._last_shown: Dict[Tuple[str, str, Optional[int], Optional[int]], float] = {}
        self.shown = 0
        self.suppressed = 0
        self.disabled = 0
        self.errors = 0

    def handle(
        self, record: EventRecord, now: Optional[float] = None
    ) -> Optional[NotificationRecord]:
        if not isinstance(record, EventRecord):
            return None
        if record.type not in _WORTH_A_TOAST:
            return None
        now = self._clock() if now is None else float(now)
        title, body = self._compose(record)
        notification = NotificationRecord(
            event_id=None,
            channel="desktop",
            status="shown",
            title=title,
            body=body,
        )

        if not self._config.desktop_enabled:
            notification.status = "disabled"
            self.disabled += 1
        else:
            key = (
                record.camera_id,
                record.type,
                record.person_id,
                record.unknown_cluster_id,
            )
            last = self._last_shown.get(key)
            if last is not None and now - last < self._config.stranger_cooldown_s:
                notification.status = "suppressed"
                notification.reason = "cooldown"
                self.suppressed += 1
            else:
                self._last_shown[key] = now
                self.shown += 1
                self._show(notification)

        self._publish(notification)
        return notification

    def run(self) -> None:
        while True:
            record = self._queue.get(timeout=0.2) if self._queue is not None else None
            if record is None:
                if self._stop_event.is_set() or self._queue is None:
                    break
                continue
            try:
                self.handle(record)
            except Exception:
                self.errors += 1
                log.exception("notification failed", extra={"event": "notify.failed"})
        while self._queue is not None:
            record = self._queue.get(timeout=0)
            if record is None:
                break
            try:
                self.handle(record)
            except Exception:
                self.errors += 1
                log.exception("notification failed", extra={"event": "notify.failed"})

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout)
        if self.is_alive():
            log.warning(
                "notifier did not stop in time",
                extra={"event": "notify.stop_timeout"},
            )

    def stats(self) -> dict:
        return {
            "shown": self.shown,
            "suppressed": self.suppressed,
            "disabled": self.disabled,
            "errors": self.errors,
            "queued": self._queue.qsize() if self._queue is not None else 0,
        }

    # -- internals -----------------------------------------------------

    def _compose(self, record: EventRecord) -> Tuple[str, str]:
        camera = self._camera_name(record.camera_id)
        if record.type == EventType.KNOWN_FACE and record.person_id is not None:
            name = self._names.get(record.person_id, "Person %d" % record.person_id)
            return "Vigil: %s" % name, "%s was recognised at %s." % (name, camera)
        return "Vigil: unknown person", "Someone unknown was seen at %s." % camera

    @staticmethod
    def _camera_name(camera_id: str) -> str:
        return camera_id.replace("_", " ").replace("-", " ")

    def _show(self, notification: NotificationRecord) -> None:
        if self._toast is None:
            return
        try:
            self._toast(notification.title, notification.body)
        except Exception:
            self.errors += 1
            log.exception("tray toast failed", extra={"event": "notify.toast_failed"})

    def _publish(self, notification: NotificationRecord) -> None:
        if self._bus is not None:
            self._bus.publish(notification)
