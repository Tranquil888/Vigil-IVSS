"""Common page frame: title row, content body, and the three data states."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..widgets.states import StateView

TONE_OBJECTS = {
    "info": "FeedbackInfo",
    "warning": "FeedbackWarning",
    "error": "FeedbackError",
}


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

        # One banner per page reports the outcome of every control, so an
        # action never looks like it did nothing. The shell mirrors it in the
        # status bar through ``feedback_handler``.
        self.feedback = QLabel("")
        self.feedback.setObjectName("FeedbackInfo")
        self.feedback.setWordWrap(True)
        self.feedback.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.feedback.setAccessibleName("Action status")
        self.feedback.setVisible(False)
        outer.addWidget(self.feedback)

        self.feedback_handler: Optional[Callable[[str, str], None]] = None
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(self.clear_feedback)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(10)

        self.view = StateView(self.body, empty_title, empty_body, empty_action)
        outer.addWidget(self.view, 1)

    def report_action(self, message: str, tone: str = "info") -> None:
        """Show the result of a control on this page and in the shell."""
        name = TONE_OBJECTS.get(tone, TONE_OBJECTS["info"])
        self.feedback.setObjectName(name)
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)
        self.feedback.setText(message)
        self.feedback.setVisible(True)
        self._feedback_timer.start(6000 if name == "FeedbackInfo" else 12000)
        handler = self.feedback_handler
        if callable(handler):
            handler(message, tone)

    def clear_feedback(self) -> None:
        self._feedback_timer.stop()
        self.feedback.clear()
        self.feedback.setVisible(False)

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
