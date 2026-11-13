"""Common page frame: title row, content body, and the three data states."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..widgets.states import StateView


class Page(QWidget):
    title = ""

    def __init__(
        self,
        title: str,
        empty_title: str = "Nothing here yet",
        empty_body: str = "",
        empty_action: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        self.header.addWidget(self.title_label)
        self.header.addStretch(1)
        outer.addLayout(self.header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(10)

        self.view = StateView(self.body, empty_title, empty_body, empty_action)
        outer.addWidget(self.view, 1)

    def show_content(self) -> None:
        self.view.show_content()

    def show_empty(
        self, title: Optional[str] = None, body: Optional[str] = None
    ) -> None:
        self.view.show_empty(title, body)

    def show_loading(self, label: Optional[str] = None) -> None:
        self.view.show_loading(label)

    def show_error(self, message: str) -> None:
        self.view.show_error(message)

    def refresh(self) -> None:
        """Reload this page from the context. Pages may override."""
