"""Empty, loading, and error views. Every data screen uses the same three."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class EmptyState(QWidget):
    action_clicked = Signal()

    def __init__(
        self,
        title: str,
        body: str = "",
        action_label: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)
        layout.addStretch(1)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.body_label = QLabel(body)
        self.body_label.setObjectName("Muted")
        self.body_label.setWordWrap(True)
        self.body_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.body_label)
        self.action_button = None
        if action_label:
            self.action_button = QPushButton(action_label)
            self.action_button.clicked.connect(self.action_clicked)
            layout.addWidget(self.action_button, 0, Qt.AlignCenter)
        layout.addStretch(1)

    def set_text(self, title: Optional[str] = None, body: Optional[str] = None) -> None:
        if title is not None:
            self.title_label.setText(title)
        if body is not None:
            self.body_label.setText(body)


class ErrorState(QWidget):
    retry_clicked = Signal()

    def __init__(
        self,
        message: str = "Something went wrong.",
        retry_label: str = "Try again",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)
        layout.addStretch(1)

        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.retry_button = QPushButton(retry_label)
        self.retry_button.clicked.connect(self.retry_clicked)

        layout.addWidget(self.message_label)
        layout.addWidget(self.retry_button, 0, Qt.AlignCenter)
        layout.addStretch(1)

    def set_message(self, message: str) -> None:
        self.message_label.setText(message)


class LoadingState(QWidget):
    def __init__(self, label: str = "Loading", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(10)
        layout.addStretch(1)

        self.label = QLabel(label)
        self.label.setObjectName("Muted")
        self.label.setAlignment(Qt.AlignCenter)
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setFixedWidth(220)
        bar.setTextVisible(False)

        layout.addWidget(self.label)
        layout.addWidget(bar, 0, Qt.AlignCenter)
        layout.addStretch(1)

    def set_label(self, label: str) -> None:
        self.label.setText(label)


class StateView(QStackedWidget):
    """One content widget plus the three states, with a mode the tests can read."""

    def __init__(
        self,
        content: QWidget,
        empty_title: str = "Nothing here yet",
        empty_body: str = "",
        empty_action: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.content = content
        self._retry_callback = None
        self.empty = EmptyState(empty_title, empty_body, empty_action)
        self.loading = LoadingState()
        self.error = ErrorState()
        self.addWidget(content)
        self.addWidget(self.empty)
        self.addWidget(self.loading)
        self.addWidget(self.error)
        self.setCurrentWidget(content)

    @property
    def mode(self) -> str:
        current = self.currentWidget()
        if current is self.empty:
            return "empty"
        if current is self.loading:
            return "loading"
        if current is self.error:
            return "error"
        return "content"

    def set_retry(self, callback) -> None:
        if self._retry_callback is not None:
            try:
                self.error.retry_clicked.disconnect(self._retry_callback)
            except (RuntimeError, TypeError):
                pass
        self._retry_callback = callback
        self.error.retry_clicked.connect(callback)

    def show_content(self) -> None:
        self.setCurrentWidget(self.content)

    def show_empty(
        self, title: Optional[str] = None, body: Optional[str] = None
    ) -> None:
        self.empty.set_text(title, body)
        self.setCurrentWidget(self.empty)

    def show_loading(self, label: Optional[str] = None) -> None:
        if label is not None:
            self.loading.set_label(label)
        self.setCurrentWidget(self.loading)

    def show_error(self, message: str) -> None:
        self.error.set_message(message)
        self.setCurrentWidget(self.error)
