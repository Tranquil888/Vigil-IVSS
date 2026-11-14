"""Cameras page. The model is the TOML config, not a second database."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...config.loader import save_config
from ...config.models import CameraConfig
from ..widgets.fields import FieldRow
from .base import Page


class CamerasPage(Page):
    def __init__(
        self,
        context,
        config_path: Path,
        parent: Optional[QWidget] = None,
        on_applied=None,
    ) -> None:
        super().__init__(
            "Cameras",
            "No cameras configured",
            "Add a camera and give it a stream address.",
            "Add camera",
            parent,
        )
        self.context = context
        self.config = context.config
        self.config_path = Path(config_path)
        self.on_applied = on_applied
        self._rows = []
        self._selected: Optional[CameraConfig] = None

        split = QHBoxLayout()
        split.setSpacing(12)

        left = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(260)
        self.list_widget.currentItemChanged.connect(self._on_selected)
        left.addWidget(self.list_widget, 1)
        buttons = QHBoxLayout()
        self.add_button = QPushButton("Add camera")
        self.add_button.clicked.connect(self.add_camera)
        self.remove_button = QPushButton("Remove camera")
        self.remove_button.setObjectName("Danger")
        self.remove_button.clicked.connect(self.remove_camera)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        left.addLayout(buttons)
        split.addLayout(left, 1)

        editor = QWidget()
        editor.setObjectName("Panel")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(14, 14, 14, 14)
        editor_layout.setSpacing(8)

        heading = QLabel("Camera settings")
        heading.setObjectName("SectionTitle")
        editor_layout.addWidget(heading)

        self.name_field = FieldRow("Name", QLineEdit(), "")
        source_edit = QPlainTextEdit()
        source_edit.setPlaceholderText(
            "0\nrtsp://user:pass@host/stream\nC:\\videos\\clip.mp4"
        )
        source_edit.setFixedHeight(64)
        source_edit.setTabChangesFocus(True)
        self.source_field = FieldRow("Stream address", source_edit, "")
        self.enabled_field = FieldRow("Enabled", QCheckBox(), False)
        self.stream_field = FieldRow(
            "Analysis stream",
            QComboBox(),
            "sub",
        )
        self.stream_field.widget.addItems(["sub", "main"])
        self.snapshot_field = FieldRow("Save snapshots", QCheckBox(), True)
        self._rows = [
            self.name_field,
            self.source_field,
            self.enabled_field,
            self.stream_field,
            self.snapshot_field,
        ]
        for row in self._rows:
            editor_layout.addWidget(row)

        hint = QLabel(
            "One entry per line: a camera index, a stream URL, or video files "
            "that play in order and loop."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        editor_layout.addWidget(hint)

        self.state_label = QLabel("State: unknown")
        self.state_label.setObjectName("Muted")
        editor_layout.addWidget(self.state_label)
        editor_layout.addStretch(1)

        editor_buttons = QHBoxLayout()
        self.save_button = QPushButton("Save camera")
        self.save_button.setObjectName("Primary")
        self.save_button.clicked.connect(self.save_selected)
        editor_buttons.addStretch(1)
        editor_buttons.addWidget(self.save_button)
        editor_layout.addLayout(editor_buttons)
        split.addWidget(editor, 2)

        self.body_layout.addLayout(split, 1)
        self.view.set_retry(self.refresh)
        self.view.empty.action_clicked.connect(self.add_camera)
        self.refresh()

    # -- list ----------------------------------------------------------

    def refresh(self) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for camera in self.config.cameras:
            item = QListWidgetItem("%s  (%s)" % (camera.name, camera.id))
            item.setData(Qt.UserRole, camera.id)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        if not self.config.cameras:
            self.show_empty()
            self._set_editor_enabled(False)
            return
        self.show_content()
        self._set_editor_enabled(True)
        self.list_widget.setCurrentRow(0)

    def _set_editor_enabled(self, enabled: bool) -> None:
        for row in self._rows:
            row.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)

    def _on_selected(self, current: Optional[QListWidgetItem], _previous=None) -> None:
        if current is None:
            self._selected = None
            return
        camera_id = current.data(Qt.UserRole)
        try:
            camera = self.config.camera(camera_id)
        except KeyError:
            self._selected = None
            return
        self._selected = camera
        self.name_field.set_value(camera.name)
        self.source_field.set_value(camera.source)
        self.enabled_field.set_value(camera.enabled)
        self.stream_field.set_value(camera.analysis_stream)
        self.snapshot_field.set_value(camera.snapshot_enabled)
        for row in self._rows:
            row.default = row.value()
        state = self.context.manager.state(camera.id)
        state_text = getattr(state, "value", state) or "unknown"
        self.state_label.setText("State: %s" % state_text)

    # -- actions -------------------------------------------------------

    def add_camera(self) -> None:
        used = {camera.id for camera in self.config.cameras}
        index = len(used) + 1
        while "camera-%d" % index in used:
            index += 1
        camera = CameraConfig(
            id="camera-%d" % index,
            name="New camera",
            source="0",
            enabled=False,
        )
        self.config.cameras.append(camera)
        ok, message = self._persist()
        self.refresh()
        self._select_camera(camera.id)
        self._report(ok, message)

    def remove_camera(self) -> None:
        camera = self._selected
        if camera is None:
            self._report(False, "Select a camera before removing one.")
            return
        answer = QMessageBox.question(
            self,
            "Remove camera",
            "Remove %s from the configuration?" % camera.name,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.config.cameras = [
            item for item in self.config.cameras if item.id != camera.id
        ]
        ok, message = self._persist()
        self.refresh()
        self._report(ok, message)

    def save_selected(self) -> None:
        camera = self._selected
        if camera is None:
            self._report(False, "Select a camera before saving one.")
            return
        try:
            camera.name = self.name_field.value().strip()
            camera.source = self.source_field.value().strip()
            camera.enabled = bool(self.enabled_field.value())
            camera.analysis_stream = self.stream_field.value()
            camera.snapshot_enabled = bool(self.snapshot_field.value())
        except Exception as err:
            self._report(False, "The camera was not saved: %s" % err)
            return
        ok, message = self._persist()
        self.refresh()
        self._select_camera(camera.id)
        self._report(ok, message)

    def _persist(self):
        try:
            save_config(self.config_path, self.config)
        except Exception as err:
            return False, "Could not write the config: %s" % err
        apply_config = getattr(self.context, "apply_config", None)
        if not callable(apply_config):
            return True, "Saved. The running app was not changed."
        try:
            summary = apply_config()
        except Exception as err:
            return False, "Saved, but the running app was not changed: %s" % err
        if callable(self.on_applied):
            self.on_applied()
        active = int(summary.get("cameras", 0))
        if active == 0:
            return True, "Saved and applied. No cameras are enabled."
        return True, "Saved and applied. %d camera(s) running." % active

    def _report(self, ok: bool, message: str) -> None:
        self.report_action(message, "info" if ok else "error")

    def _select_camera(self, camera_id: str) -> None:
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.data(Qt.UserRole) == camera_id:
                self.list_widget.setCurrentRow(index)
                return
