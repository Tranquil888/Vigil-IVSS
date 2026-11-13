"""Events page. One bounded reader query per refresh, never in the worker path."""

from __future__ import annotations

import time
from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.records import EventType
from .base import Page

TYPE_LABELS = {
    EventType.MOTION: "Motion",
    EventType.KNOWN_FACE: "Known face",
    EventType.STRANGER: "Stranger",
    EventType.UNCERTAIN_FACE: "Uncertain",
    EventType.CAMERA_OFFLINE: "Camera offline",
    EventType.CAMERA_ONLINE: "Camera online",
}


class EventsPage(Page):
    def __init__(self, context, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Events",
            "No events match",
            "Change the filters, or wait for motion on a camera.",
            None,
            parent,
        )
        self.context = context
        self._rows = []

        filters = QHBoxLayout()
        filters.setSpacing(8)
        filters.addWidget(QLabel("Camera"))
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("All cameras", "")
        for camera in context.config.cameras:
            self.camera_combo.addItem(camera.name, camera.id)
        filters.addWidget(self.camera_combo)

        filters.addWidget(QLabel("Type"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("All types", "")
        for event_type, label in TYPE_LABELS.items():
            self.type_combo.addItem(label, event_type)
        filters.addWidget(self.type_combo)

        filters.addWidget(QLabel("Limit"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 1000)
        self.limit_spin.setValue(200)
        filters.addWidget(self.limit_spin)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        filters.addWidget(self.refresh_button)
        filters.addStretch(1)
        self.header.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Camera", "Type", "Person", "Score"]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.body_layout.addWidget(self.table, 1)

        preview = QWidget()
        preview.setObjectName("Panel")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        heading = QLabel("Event detail")
        heading.setObjectName("SectionTitle")
        preview_layout.addWidget(heading)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("Select an event to see its details.")
        self.detail.setFixedHeight(120)
        preview_layout.addWidget(self.detail)
        self.body_layout.addWidget(preview)

        self.view.set_retry(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        camera_id = self.camera_combo.currentData() or None
        event_type = self.type_combo.currentData() or None
        limit = int(self.limit_spin.value())
        self.show_loading("Reading the event log")
        try:
            rows = self.context.reader.events(
                limit=limit, camera_id=camera_id, event_type=event_type
            )
        except Exception as err:
            self.show_error("Could not read events: %s" % err)
            return
        self._rows = rows
        self.table.setRowCount(len(rows))
        mono = QFont("Cascadia Mono", 9)
        for row_index, row in enumerate(rows):
            values = [
                self._format_time(row.get("ts_start")),
                row.get("camera_id") or "",
                TYPE_LABELS.get(row.get("type"), row.get("type") or ""),
                self._person_label(row),
                self._score(row.get("score")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setFont(mono)
                self.table.setItem(row_index, column, item)
        self.detail.clear()
        if not rows:
            self.show_empty()
        else:
            self.show_content()

    def _on_selection(self) -> None:
        selected = self.table.currentRow()
        if selected < 0 or selected >= len(self._rows):
            self.detail.clear()
            return
        row = self._rows[selected]
        lines = [
            "Camera: %s" % (row.get("camera_id") or ""),
            "Type: %s" % TYPE_LABELS.get(row.get("type"), row.get("type") or ""),
            "Started: %s" % self._format_time(row.get("ts_start")),
            "Ended: %s" % self._format_time(row.get("ts_end")),
            "Person: %s" % self._person_label(row),
            "Unknown cluster: %s" % (row.get("unknown_cluster_id") or "none"),
            "Score: %s" % self._score(row.get("score")),
        ]
        self.detail.setPlainText("\n".join(lines))

    @staticmethod
    def _format_time(value) -> str:
        if not value:
            return ""
        try:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(value)))
        except (TypeError, ValueError, OSError):
            return str(value)

    def _person_label(self, row) -> str:
        person_id = row.get("person_id")
        if person_id is None:
            return ""
        names = getattr(self.context, "names", {}) or {}
        return names.get(int(person_id), "#%d" % int(person_id))

    @staticmethod
    def _score(value) -> str:
        if value is None:
            return ""
        try:
            return "%.3f" % float(value)
        except (TypeError, ValueError):
            return str(value)
