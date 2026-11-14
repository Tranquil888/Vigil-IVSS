"""Diagnostics page. Read-only runtime facts for support and gray-box runs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton, QWidget

from ...diagnostics import build_report, format_report
from .base import Page


class DiagnosticsPage(Page):
    config_reloaded = Signal()

    def __init__(
        self,
        context,
        config_path: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            "Diagnostics",
            "No diagnostics yet",
            "Runtime details appear once the application context is built.",
            None,
            parent,
        )
        self.context = context
        self.config_path = Path(config_path) if config_path else None

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_from_button)
        self.copy_button = QPushButton("Copy report")
        self.copy_button.clicked.connect(self.copy_report)
        self.reload_button = QPushButton("Reload config")
        self.reload_button.clicked.connect(self.reload_config)
        self.reload_button.setEnabled(self.config_path is not None)
        self.header.addWidget(self.refresh_button)
        self.header.addWidget(self.copy_button)
        self.header.addWidget(self.reload_button)

        self.updated_label = QLabel("")
        self.updated_label.setObjectName("Muted")
        self.body_layout.addWidget(self.updated_label)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setObjectName("Mono")
        self.text.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.body_layout.addWidget(self.text, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(2500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.refresh()

    def _tick(self) -> None:
        if self.isVisible():
            self.refresh()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # The constructor refreshes before the workers start. Refresh again on
        # every visit so a thread that died later does not stay hidden.
        self.refresh()

    def refresh_from_button(self) -> None:
        if self.refresh():
            self.report_action("Report updated.")

    def report(self) -> str:
        report = build_report(self.context)
        if self.config_path is not None:
            report["paths"]["config"] = str(self.config_path)
        return format_report(report)

    def refresh(self) -> bool:
        try:
            text = self.report()
        except Exception as err:
            self.show_error("Could not read diagnostics: %s" % err)
            return False
        self.text.setPlainText(text)
        self.updated_label.setText("Updates every 2.5 seconds while this page is open.")
        self.show_content()
        return True

    def copy_report(self) -> None:
        clipboard = QGuiApplication.clipboard()
        try:
            text = self.report()
        except Exception as err:
            self.report_action("Could not build the report: %s" % err, "error")
            return
        if clipboard is None:
            self.report_action("The clipboard is not available.", "error")
            return
        clipboard.setText(text)
        self.report_action("Report copied to the clipboard.")

    def reload_config(self) -> None:
        if self.config_path is None:
            self.report_action("No config file is set for this app.", "error")
            return
        action = getattr(self.context, "reload_config", None)
        if not callable(action):
            self.report_action("This context cannot reload a config file.", "error")
            return
        try:
            action(self.config_path)
        except Exception as err:
            self.report_action("Reload failed: %s" % err, "error")
            return
        self.refresh()
        self.report_action("Config reloaded from %s." % self.config_path)
        self.config_reloaded.emit()
