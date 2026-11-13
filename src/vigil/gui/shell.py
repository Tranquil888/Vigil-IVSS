"""Main window: an 88 px rail, six destinations, and no worker calls."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..config.loader import default_config_path
from ..config.models import VigilConfig
from .pages.cameras import CamerasPage
from .pages.diagnostics import DiagnosticsPage
from .pages.events import EventsPage
from .pages.live import LivePage
from .pages.people import PeoplePage
from .pages.settings import SettingsPage
from .theme import build_theme, palette
from .tray import TrayIcon

NAV = [
    ("Cameras", "camera"),
    ("Live", "grid"),
    ("Events", "list"),
    ("People", "person"),
    ("Settings", "sliders"),
    ("Diagnostics", "pulse"),
]


def _nav_pixmap(kind: str, color: str, size: int = 40) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(2.0)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    if kind == "camera":
        painter.drawRoundedRect(10, 14, 20, 14, 3, 3)
        painter.drawEllipse(16, 17, 8, 8)
        painter.drawLine(16, 10, 24, 10)
    elif kind == "grid":
        painter.drawRoundedRect(10, 10, 8, 8, 1, 1)
        painter.drawRoundedRect(22, 10, 8, 8, 1, 1)
        painter.drawRoundedRect(10, 22, 8, 8, 1, 1)
        painter.drawRoundedRect(22, 22, 8, 8, 1, 1)
    elif kind == "list":
        for offset in (12, 20, 28):
            painter.drawLine(17, offset, 30, offset)
            painter.drawPoint(12, offset)
    elif kind == "person":
        painter.drawEllipse(16, 11, 8, 8)
        painter.drawArc(11, 21, 18, 12, 0, 180 * 16)
    elif kind == "sliders":
        for offset in (13, 20, 27):
            painter.drawLine(10, offset, 30, offset)
        painter.setBrush(QColor(color))
        painter.drawEllipse(15, 10, 6, 6)
        painter.drawEllipse(23, 17, 6, 6)
        painter.drawEllipse(16, 24, 6, 6)
    elif kind == "pulse":
        painter.drawLine(10, 20, 15, 20)
        painter.drawLine(15, 20, 18, 13)
        painter.drawLine(18, 13, 22, 27)
        painter.drawLine(22, 27, 25, 20)
        painter.drawLine(25, 20, 30, 20)

    painter.end()
    return pixmap


def _nav_icon(kind: str, scheme: str) -> QIcon:
    colors = palette(scheme)
    icon = QIcon()
    icon.addPixmap(_nav_pixmap(kind, colors["muted"]), QIcon.Normal, QIcon.Off)
    icon.addPixmap(_nav_pixmap(kind, colors["text"]), QIcon.Active, QIcon.Off)
    icon.addPixmap(_nav_pixmap(kind, colors["accent"]), QIcon.Normal, QIcon.On)
    icon.addPixmap(_nav_pixmap(kind, colors["accent"]), QIcon.Active, QIcon.On)
    return icon


class ToastBridge(QObject):
    """Carries notifier messages from the notifier thread onto the GUI thread."""

    message = Signal(str, str)

    def __init__(self, on_message, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.message.connect(on_message)


class MainWindow(QMainWindow):
    def __init__(
        self,
        context,
        config: VigilConfig,
        config_path: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.context = context
        self.config = config
        self.config_path = Path(config_path) if config_path else default_config_path()
        self._quitting = False

        self.setWindowTitle("Vigil")
        self.resize(1180, 760)
        self.setMinimumSize(960, 640)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.rail = QWidget()
        self.rail.setObjectName("Rail")
        self.rail.setFixedWidth(88)
        rail_layout = QVBoxLayout(self.rail)
        rail_layout.setContentsMargins(8, 12, 8, 12)
        rail_layout.setSpacing(6)

        self.stack = QStackedWidget()
        self.cameras_page = CamerasPage(context, self.config_path)
        self.live_page = LivePage(context)
        self.events_page = EventsPage(context)
        self.people_page = PeoplePage(context)
        self.settings_page = SettingsPage(context, self.config_path)
        self.diagnostics_page = DiagnosticsPage(context, self.config_path)
        self.pages = [
            self.cameras_page,
            self.live_page,
            self.events_page,
            self.people_page,
            self.settings_page,
            self.diagnostics_page,
        ]
        for page in self.pages:
            self.stack.addWidget(page)

        self.nav_buttons = []
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, (label, kind) in enumerate(NAV):
            button = QToolButton()
            button.setObjectName("RailButton")
            button.setText(label)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(22, 22))
            button.setCheckable(True)
            button.setFixedHeight(62)
            button.setAccessibleName(label)
            button.clicked.connect(
                lambda checked=False, page_index=index: self.set_page(page_index)
            )
            self.nav_buttons.append(button)
            self.nav_group.addButton(button, index)
            rail_layout.addWidget(button)
        rail_layout.addStretch(1)

        version = QLabel("2.0")
        version.setObjectName("Muted")
        version.setAlignment(Qt.AlignCenter)
        rail_layout.addWidget(version)

        layout.addWidget(self.rail)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        status = QStatusBar()
        self.setStatusBar(status)
        self.backend_label = QLabel("")
        self.backend_label.setObjectName("Muted")
        self.camera_label = QLabel("0 cameras")
        self.camera_label.setObjectName("Muted")
        status.addPermanentWidget(self.camera_label)
        status.addPermanentWidget(self.backend_label)
        self._update_status()

        self.cameras_page.on_applied = self.after_config_applied
        self.settings_page.on_saved = self.apply_config_from_page
        self.diagnostics_page.config_reloaded.connect(self.after_config_reloaded)
        self.scheme = self._resolved_scheme()
        self.apply_scheme(self.config.app.theme)
        self.set_page(1)

        self.tray = TrayIcon(self.show_window, self.quit_app, scheme=self.scheme)
        self.toast_bridge = ToastBridge(self._show_toast, self)
        setter = getattr(self.context, "set_toast_callback", None)
        if callable(setter):
            setter(self.notify)

    # -- navigation ----------------------------------------------------

    def set_page(self, index: int) -> None:
        index = max(0, min(index, len(self.pages) - 1))
        self.stack.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        if index in (1, 2, 3, 5):
            self.pages[index].refresh()
        if index == 1:
            self.live_page.set_mode("grid")

    def current_page(self):
        return self.pages[self.stack.currentIndex()]

    # -- theme ---------------------------------------------------------

    def _resolved_scheme(self) -> str:
        scheme = self.config.app.theme
        if scheme in ("dark", "light"):
            return scheme
        try:
            hints = QGuiApplication.styleHints()
            if hints.colorScheme() == Qt.ColorScheme.Light:
                return "light"
        except Exception:
            pass
        return "dark"

    def apply_theme_from_config(self) -> None:
        self.apply_scheme(self.config.app.theme)
        self._update_status()

    def after_config_applied(self) -> None:
        """Refresh the read-only views after a live config change."""
        self.live_page.refresh()
        self._update_status()

    def apply_config_from_page(self) -> None:
        self.apply_theme_from_config()
        self.after_config_applied()

    def after_config_reloaded(self) -> None:
        """Rebuild editor widgets after the TOML file was reloaded from disk."""
        self.settings_page.reload()
        self.cameras_page.refresh()
        self.apply_config_from_page()

    def apply_scheme(self, scheme: str) -> None:
        self.scheme = scheme if scheme in ("dark", "light") else self._resolved_scheme()
        self.setStyleSheet(build_theme(self.scheme))
        for button, (label, kind) in zip(self.nav_buttons, NAV):
            button.setIcon(_nav_icon(kind, self.scheme))
        self.live_page.set_scheme(self.scheme)
        if hasattr(self, "tray"):
            self.tray.set_scheme(self.scheme)

    # -- status and notifications --------------------------------------

    def _update_status(self) -> None:
        status = getattr(self.context, "status", None)
        if status is None:
            self.backend_label.setText("Face backend: unknown")
        elif not getattr(status, "available", False):
            self.backend_label.setText("Face backend: motion only")
            self.backend_label.setObjectName("Warning")
        else:
            device = "GPU" if getattr(status, "cuda", False) else "CPU"
            text = "Face backend: %s, %s" % (
                getattr(status, "detector", "none"),
                device,
            )
            reason = getattr(status, "reason", "") or ""
            lowered = reason.lower()
            degraded = any(
                word in lowered
                for word in ("missing", "disabled", "not installed", "not found")
            )
            if degraded:
                text = "%s. %s" % (text, reason)
                self.backend_label.setObjectName("Warning")
            else:
                self.backend_label.setObjectName("Muted")
            self.backend_label.setText(text)
        self.backend_label.style().unpolish(self.backend_label)
        self.backend_label.style().polish(self.backend_label)
        try:
            count = len(self.context.manager.camera_ids)
        except Exception:
            count = 0
        self.camera_label.setText(
            "%d camera%s" % (count, "" if count == 1 else "s")
        )

    def notify(self, title: str, body: str) -> None:
        """Safe to call from any thread; the bridge queues it onto the GUI thread."""
        self.toast_bridge.message.emit(title, body)

    def _show_toast(self, title: str, body: str) -> None:
        self.tray.notify(title, body)
        self.statusBar().showMessage("%s: %s" % (title, body), 8000)
        if self.config.notify.sound_enabled:
            QApplication.beep()

    # -- window behaviour ----------------------------------------------

    def show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        self._quitting = True
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        if self.tray.available and not self._quitting:
            self.hide()
            event.ignore()
            return
        event.accept()
