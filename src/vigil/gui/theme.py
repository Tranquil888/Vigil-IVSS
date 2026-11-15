"""Theme tokens and the single QSS builder for both schemes.

The palette follows docs/DESIGN.md: grayscale surfaces, one green accent for
active states and primary actions, and red reserved for alerts. Every corner
is square, and separators are one-pixel rules rather than shadows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

DARK = {
    "bg": "#0B0D0F",
    "panel": "#15181B",
    "panel_alt": "#1E2225",
    "line": "#2E3337",
    "text": "#E9ECEE",
    "muted": "#A6ADB3",
    "accent": "#34D058",
    "accent_fill": "#34D058",
    "warn": "#F05252",
    "danger": "#F05252",
    "on_accent": "#07110A",
}

LIGHT = {
    "bg": "#F2F3F2",
    "panel": "#FFFFFF",
    "panel_alt": "#E9EBE9",
    "line": "#C7CBC7",
    "text": "#15181A",
    "muted": "#555C60",
    "accent": "#0B6B2E",
    "accent_fill": "#1FA84F",
    "warn": "#B42318",
    "danger": "#B42318",
    "on_accent": "#07110A",
}

PALETTES: Dict[str, Dict[str, str]] = {"dark": DARK, "light": LIGHT}

# Foreground and background token pairs that carry text or a control label.
# A green fill is lighter than the green used for text, so the two have their
# own pair: accent is readable as text, accent_fill carries dark text.
TEXT_PAIRS: List[Tuple[str, str]] = [
    ("text", "bg"),
    ("text", "panel"),
    ("text", "panel_alt"),
    ("muted", "bg"),
    ("muted", "panel"),
    ("muted", "panel_alt"),
    ("accent", "bg"),
    ("accent", "panel"),
    ("warn", "bg"),
    ("warn", "panel"),
    ("danger", "bg"),
    ("danger", "panel"),
    ("on_accent", "accent_fill"),
]


def _channel(value: str) -> float:
    value = value / 255.0
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    text = hex_color.lstrip("#")
    red = _channel(int(text[0:2], 16))
    green = _channel(int(text[2:4], 16))
    blue = _channel(int(text[4:6], 16))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def palette(scheme: str) -> Dict[str, str]:
    try:
        return PALETTES[scheme]
    except KeyError:
        raise ValueError("unknown theme scheme %r" % scheme)


def build_theme(scheme: str = "dark") -> str:
    colors = dict(palette(scheme))
    check_icon = Path(__file__).with_name("resources") / ("check-%s.png" % scheme)
    colors["check"] = check_icon.as_posix()
    base = """
* {{
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 12px;
    color: {text};
}}
QWidget {{
    background: {bg};
}}
QMainWindow, QDialog {{
    background: {bg};
}}
QLabel {{
    background: transparent;
}}
QLabel#PageTitle {{
    font-size: 18px;
    font-weight: 600;
    color: {text};
}}
QLabel#SectionTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {text};
}}
QLabel#Muted {{
    color: {muted};
}}
QLabel#Danger {{
    color: {danger};
}}
QLabel#Warning {{
    color: {warn};
}}
QLabel#FeedbackInfo {{
    background: {panel_alt};
    border: 1px solid {line};
    border-left: 3px solid {accent};
    border-radius: 0;
    padding: 8px 10px;
    color: {text};
}}
QLabel#FeedbackWarning {{
    background: {panel_alt};
    border: 1px solid {line};
    border-left: 3px solid {warn};
    border-radius: 0;
    padding: 8px 10px;
    color: {text};
}}
QLabel#FeedbackError {{
    background: {panel_alt};
    border: 1px solid {line};
    border-left: 3px solid {danger};
    border-radius: 0;
    padding: 8px 10px;
    color: {text};
}}
QLabel#Mono {{
    font-family: "Cascadia Mono", "Consolas", monospace;
}}
QFrame#Panel, QWidget#Panel {{
    background: {panel};
    border: 1px solid {line};
    border-radius: 0;
}}
QWidget#Rail {{
    background: {panel};
    border-right: 1px solid {line};
}}
QLabel#StatusOk {{
    color: {accent};
}}
QLabel#StatusWarn {{
    color: {warn};
}}
QToolButton#RailButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 0;
    padding: 8px 4px;
    color: {muted};
}}
QToolButton#RailButton:hover {{
    background: {panel_alt};
    color: {text};
}}
QToolButton#RailButton:pressed {{
    background: {line};
    color: {text};
}}
QToolButton#RailButton:checked {{
    background: {panel_alt};
    border-color: {accent};
    color: {accent};
}}
QToolButton#RailButton:focus {{
    border-color: {accent};
}}
QPushButton {{
    background: {panel_alt};
    border: 1px solid {line};
    border-radius: 0;
    padding: 6px 12px;
    color: {text};
}}
QPushButton:hover {{
    border-color: {accent};
}}
QPushButton:pressed {{
    background: {line};
    border-color: {accent};
    color: {text};
}}
QPushButton:focus {{
    border-color: {accent};
}}
QPushButton:disabled {{
    background: {panel};
    border-color: {line};
    color: {muted};
}}
QPushButton#Primary {{
    background: {accent_fill};
    border-color: {accent_fill};
    color: {on_accent};
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    border-color: {text};
}}
QPushButton#Primary:pressed {{
    background: {accent_fill};
    border-color: {text};
    color: {on_accent};
}}
QPushButton#Danger {{
    color: {danger};
    border-color: {danger};
}}
QPushButton#Danger:pressed {{
    background: {panel};
    border-color: {danger};
    color: {danger};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {panel};
    border: 1px solid {line};
    border-radius: 0;
    padding: 5px 8px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {accent};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QPlainTextEdit:disabled {{
    background: {panel_alt};
    color: {muted};
}}
QComboBox QAbstractItemView {{
    background: {panel};
    border: 1px solid {line};
    selection-background-color: {panel_alt};
    selection-color: {text};
}}
QTableWidget, QTableView, QListWidget, QTreeWidget {{
    background: {panel};
    alternate-background-color: {panel_alt};
    border: 1px solid {line};
    border-radius: 0;
    gridline-color: {line};
    selection-background-color: {panel_alt};
    selection-color: {text};
}}
QListWidget::item, QTableWidget::item {{
    padding: 5px 6px;
}}
QListWidget::item:selected, QTableWidget::item:selected {{
    background: {panel_alt};
    color: {text};
}}
QListWidget:focus, QTableWidget:focus, QTableView:focus {{
    border-color: {accent};
}}
QHeaderView::section {{
    background: {panel_alt};
    color: {muted};
    border: none;
    border-bottom: 1px solid {line};
    padding: 6px 8px;
    font-weight: 600;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: {bg};
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {line};
    border-radius: 0;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {bg};
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {line};
    border-radius: 0;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QProgressBar {{
    background: {panel};
    border: 1px solid {line};
    border-radius: 0;
    text-align: center;
    color: {muted};
}}
QProgressBar::chunk {{
    background: {accent_fill};
}}
QCheckBox {{
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {line};
    border-radius: 0;
    background: {panel};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
    image: url("{check}");
}}
QCheckBox::indicator:checked:disabled {{
    background: {line};
    border-color: {line};
}}
QCheckBox::indicator:focus {{
    border-color: {accent};
}}
QRadioButton {{
    background: transparent;
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {line};
    border-radius: 0;
    background: {panel};
}}
QRadioButton::indicator:checked {{
    background: {accent};
    border-color: {accent};
}}
QRadioButton::indicator:focus {{
    border-color: {accent};
}}
QSlider::groove:horizontal {{
    background: {line};
    height: 2px;
}}
QSlider::handle:horizontal {{
    background: {accent_fill};
    width: 12px;
    margin: -5px 0;
    border-radius: 0;
}}
QToolTip {{
    background: {panel};
    color: {text};
    border: 1px solid {line};
    padding: 4px 6px;
}}
QMenu {{
    background: {panel};
    border: 1px solid {line};
}}
QMenu::item {{
    padding: 6px 20px;
}}
QMenu::item:selected {{
    background: {panel_alt};
    color: {text};
}}
QStatusBar {{
    background: {panel};
    color: {muted};
    border-top: 1px solid {line};
}}
"""
    return base.format(**colors)
