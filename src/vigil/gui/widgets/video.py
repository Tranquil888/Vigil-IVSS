"""Live video tile. It only reads a LatestFrame and the overlay store."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
from PySide6.QtCore import QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..theme import palette


class VideoTile(QWidget):
    def __init__(
        self,
        latest,
        overlays,
        camera_id: str,
        fps: float = 15.0,
        stale_after_s: float = 1.5,
        scheme: str = "dark",
        label: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._latest = latest
        self._overlays = overlays
        self.camera_id = camera_id
        self.label = label or camera_id
        self._stale_after_s = float(stale_after_s)
        self.scheme = scheme
        self.has_signal = False
        self._image: Optional[QImage] = None
        self._source_width = 1
        self._source_height = 1
        self._last_error: Optional[str] = None

        self.setMinimumSize(240, 135)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._timer = QTimer(self)
        self._timer.setInterval(max(16, int(1000.0 / max(1.0, float(fps)))))
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        """Skip hidden tiles, so the inactive grid or single view costs nothing."""
        if not self.isVisible():
            return
        self.refresh()

    def set_scheme(self, scheme: str) -> None:
        self.scheme = scheme
        self.update()

    def stop(self) -> None:
        self._timer.stop()

    def status_text(self) -> str:
        if not self.has_signal:
            return "No signal"
        return "Live"

    def refresh(self, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else float(now)
        try:
            frame = self._latest.latest() if self._latest is not None else None
        except Exception as err:
            frame = None
            self._last_error = str(err)
        if frame is None or frame.image is None:
            self.has_signal = False
        else:
            age = now - float(frame.captured_at)
            if age > self._stale_after_s:
                self.has_signal = False
            else:
                self._image = self._to_qimage(frame.image)
                self.has_signal = self._image is not None
                if self._image is not None:
                    self._source_width = max(1, self._image.width())
                    self._source_height = max(1, self._image.height())
        self.update()
        return self.has_signal

    def sizeHint(self) -> QSize:
        return QSize(480, 270)

    @staticmethod
    def _to_qimage(image: np.ndarray) -> Optional[QImage]:
        array = np.ascontiguousarray(image)
        height, width = array.shape[:2]
        if array.ndim == 2:
            return QImage(
                array.data, width, height, int(array.strides[0]), QImage.Format_Grayscale8
            ).copy()
        if array.shape[2] == 3:
            return QImage(
                array.data, width, height, int(array.strides[0]), QImage.Format_BGR888
            ).copy()
        if array.shape[2] == 4:
            return QImage(
                array.data, width, height, int(array.strides[0]), QImage.Format_ARGB32
            ).copy()
        return None

    def _target(self, width: int, height: int) -> QRect:
        area = self.rect().adjusted(1, 1, -1, -1)
        if width <= 0 or height <= 0 or area.width() <= 0 or area.height() <= 0:
            return QRect()
        scale = min(area.width() / float(width), area.height() / float(height))
        draw_width = max(1, int(width * scale))
        draw_height = max(1, int(height * scale))
        left = area.x() + (area.width() - draw_width) // 2
        top = area.y() + (area.height() - draw_height) // 2
        return QRect(left, top, draw_width, draw_height)

    def paintEvent(self, event) -> None:
        colors = palette(self.scheme)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(colors["bg"]))

        if not self.has_signal or self._image is None:
            painter.setPen(QPen(QColor(colors["line"]), 1))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
            painter.setPen(QColor(colors["muted"]))
            painter.drawText(self.rect(), Qt.AlignCenter, "No signal")
            self._paint_camera_tag(painter, self.rect(), colors)
            painter.end()
            return

        target = self._target(self._image.width(), self._image.height())
        painter.fillRect(target, QColor(colors["panel"]))
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawImage(target, self._image)
        painter.setPen(QPen(QColor(colors["line"]), 1))
        painter.drawRect(target.adjusted(0, 0, -1, -1))
        self._paint_overlays(painter, target, colors)
        self._paint_camera_tag(painter, target, colors)
        painter.end()

    def _paint_camera_tag(self, painter: QPainter, area: QRect, colors) -> None:
        label = self.label
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(label) + 12
        box = QRect(area.left() + 8, area.top() + 8, width, 20)
        painter.fillRect(box, QColor(colors["panel"]))
        painter.setPen(QColor(colors["text"]))
        painter.drawText(box.adjusted(6, 0, 0, 0), Qt.AlignVCenter, label)

    def _paint_overlays(self, painter: QPainter, target: QRect, colors) -> None:
        if self._overlays is None:
            return
        items = self._overlays.get(self.camera_id)
        if not items:
            return
        scale_x = target.width() / float(self._source_width)
        scale_y = target.height() / float(self._source_height)
        for item in items:
            x, y, width, height = item.rect
            box = QRect(
                target.left() + int(x * scale_x),
                target.top() + int(y * scale_y),
                max(1, int(width * scale_x)),
                max(1, int(height * scale_y)),
            )
            if item.kind == "known":
                color = QColor(colors["accent"])
            elif item.kind == "unknown":
                color = QColor(colors["danger"])
            else:
                color = QColor(colors["warn"])
            painter.setPen(QPen(color, 2))
            painter.drawRect(box)
            metrics = painter.fontMetrics()
            label_width = metrics.horizontalAdvance(item.label) + 8
            tag = QRect(box.left(), max(target.top(), box.top() - 18), label_width, 18)
            painter.fillRect(tag, color)
            painter.setPen(QColor(colors["on_accent"]))
            painter.drawText(tag.adjusted(4, 0, 0, 0), Qt.AlignVCenter, item.label)
