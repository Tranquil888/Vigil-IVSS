"""One labelled setting with a visible reset to its default."""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)


class FieldRow(QWidget):
    def __init__(
        self,
        label: str,
        widget: QWidget,
        default: Any,
        advanced: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.field_label = label
        self.widget = widget
        self.default = default
        self.advanced = bool(advanced)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        text = QLabel(label)
        text.setFixedWidth(180)
        text.setWordWrap(True)
        if hasattr(widget, "setAccessibleName"):
            widget.setAccessibleName(label)
        self.label_widget = text

        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset %s to its default" % label)
        self.reset_button.setAccessibleName("Reset %s to default" % label)
        self.reset_button.clicked.connect(self.reset)

        layout.addWidget(text)
        layout.addWidget(widget, 1)
        layout.addWidget(self.reset_button, 0, Qt.AlignRight)

    def reset(self) -> None:
        self.set_value(self.default)

    def set_advanced_visible(self, visible: bool) -> None:
        self.setVisible(visible or not self.advanced)

    def value(self) -> Any:
        widget = self.widget
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.value()
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        if isinstance(widget, QLineEdit):
            return widget.text()
        return None

    def set_value(self, value: Any) -> None:
        widget = self.widget
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setValue(value)
        elif isinstance(widget, QPlainTextEdit):
            widget.setPlainText("" if value is None else str(value))
        elif isinstance(widget, QLineEdit):
            widget.setText("" if value is None else str(value))
