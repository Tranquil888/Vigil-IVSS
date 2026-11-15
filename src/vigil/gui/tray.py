"""Tray icon and toasts. The tray is optional; the app works without one."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .theme import palette


def placeholder_icon(scheme: str = "dark") -> QIcon:
    # Placeholder monogram until the owner supplies an application icon.
    colors = palette(scheme)
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setBrush(QColor(colors["accent"]))
    painter.setPen(Qt.NoPen)
    painter.drawRect(1, 1, 30, 30)
    font = QFont("Segoe UI", 16)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(colors["on_accent"]))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "V")
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    def __init__(
        self,
        on_open,
        on_quit,
        scheme: str = "dark",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._available = QSystemTrayIcon.isSystemTrayAvailable()
        self._tray = QSystemTrayIcon(placeholder_icon(scheme), self)
        self._tray.setToolTip("Vigil")

        menu = QMenu()
        self.open_action = QAction("Open Vigil", menu)
        self.open_action.triggered.connect(on_open)
        self.quit_action = QAction("Quit Vigil", menu)
        self.quit_action.triggered.connect(on_quit)
        menu.addAction(self.open_action)
        menu.addSeparator()
        menu.addAction(self.quit_action)
        self.menu = menu
        self._tray.setContextMenu(menu)
        if self._available:
            self._tray.show()

    @property
    def available(self) -> bool:
        return self._available

    def set_scheme(self, scheme: str) -> None:
        self._tray.setIcon(placeholder_icon(scheme))

    def notify(self, title: str, body: str, seconds: int = 6) -> None:
        if not self._available:
            return
        self._tray.showMessage(
            title, body, QSystemTrayIcon.Information, max(1, int(seconds)) * 1000
        )

    def hide(self) -> None:
        self._tray.hide()
