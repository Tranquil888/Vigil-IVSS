"""Live page. Grid and single view, both fed only by LatestFrame."""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..widgets.video import VideoTile
from .base import Page


class LivePage(Page):
    def __init__(self, context, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Live",
            "No cameras enabled",
            "Enable a camera in Cameras. Live tiles appear here once capture starts.",
            None,
            parent,
        )
        self.context = context
        self.scheme = "dark"
        self.tiles: Dict[str, VideoTile] = {}
        self.single_tiles: Dict[str, VideoTile] = {}
        self._camera_ids = []

        control = QHBoxLayout()
        control.setSpacing(6)
        self.grid_button = QPushButton("Grid")
        self.grid_button.setCheckable(True)
        self.grid_button.setChecked(True)
        self.grid_button.setAutoExclusive(True)
        self.grid_button.clicked.connect(self.show_grid)
        self.single_button = QPushButton("Single")
        self.single_button.setCheckable(True)
        self.single_button.setAutoExclusive(True)
        self.single_button.clicked.connect(self.show_single_mode)
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(180)
        self.camera_combo.currentTextChanged.connect(self._show_single)
        control.addWidget(self.grid_button)
        control.addWidget(self.single_button)
        control.addSpacing(10)
        control.addWidget(QLabel("Camera"))
        control.addWidget(self.camera_combo)
        control.addStretch(1)
        self.header.addLayout(control)

        self.modes = QStackedWidget()
        self.grid_host = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_host)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(10)
        self.single_host = QWidget()
        single_layout = QVBoxLayout(self.single_host)
        single_layout.setContentsMargins(0, 0, 0, 0)
        single_layout.setSpacing(8)
        self.single_hint = QLabel("")
        self.single_hint.setObjectName("Muted")
        single_layout.addWidget(self.single_hint)
        self.single_slot = QVBoxLayout()
        single_layout.addLayout(self.single_slot, 1)
        self.modes.addWidget(self.grid_host)
        self.modes.addWidget(self.single_host)
        self.body_layout.addWidget(self.modes, 1)

        self.view.set_retry(self.refresh)
        self.refresh()

    def set_scheme(self, scheme: str) -> None:
        self.scheme = scheme
        for tile in list(self.tiles.values()) + list(self.single_tiles.values()):
            tile.set_scheme(scheme)

    def show_grid(self) -> None:
        self.set_mode("grid")
        self.report_action("Showing the camera grid.")

    def show_single_mode(self) -> None:
        self.set_mode("single")
        camera = self.camera_combo.currentText()
        self.report_action(
            "Showing %s." % camera if camera else "No camera to show."
        )

    def set_mode(self, mode: str) -> None:
        if mode == "grid":
            self.grid_button.setChecked(True)
            self.modes.setCurrentWidget(self.grid_host)
        else:
            self.single_button.setChecked(True)
            self.modes.setCurrentWidget(self.single_host)
            self._show_single(self.camera_combo.currentText())

    def refresh(self) -> None:
        try:
            camera_ids = list(self.context.manager.camera_ids)
        except Exception as err:
            self.show_error("Could not read the camera list: %s" % err)
            return
        if camera_ids != self._camera_ids:
            self._rebuild(camera_ids)
        if not camera_ids:
            self.show_empty()
            return
        self.show_content()

    def _rebuild(self, camera_ids) -> None:
        for tile in list(self.tiles.values()) + list(self.single_tiles.values()):
            tile.stop()
            tile.deleteLater()
        self.tiles.clear()
        self.single_tiles.clear()
        self._camera_ids = list(camera_ids)
        names = {camera.id: camera.name for camera in self.context.config.cameras}

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for camera_id in self._camera_ids:
            try:
                latest = self.context.manager.display_queue(camera_id)
            except Exception:
                continue
            label = names.get(camera_id, camera_id)
            tile = VideoTile(
                latest,
                self.context.overlays,
                camera_id,
                fps=self.context.config.display.grid_fps,
                scheme=self.scheme,
                label=label,
            )
            self.tiles[camera_id] = tile
            self.grid_layout.addWidget(tile, 1)
            single = VideoTile(
                latest,
                self.context.overlays,
                camera_id,
                fps=self.context.config.display.single_fps,
                scheme=self.scheme,
                label=label,
            )
            self.single_tiles[camera_id] = single

        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        self.camera_combo.addItems(self._camera_ids)
        self.camera_combo.blockSignals(False)
        self._show_single(self.camera_combo.currentText())

    def _show_single(self, camera_id: str) -> None:
        while self.single_slot.count():
            item = self.single_slot.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        tile = self.single_tiles.get(camera_id)
        if tile is None:
            self.single_hint.setText("No camera selected.")
            return
        self.single_hint.setText(
            "%s. Single view refreshes at %d fps."
            % (
                tile.label,
                int(self.context.config.display.single_fps),
            )
        )
        self.single_slot.addWidget(tile)
