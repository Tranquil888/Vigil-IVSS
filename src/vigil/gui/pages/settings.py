"""Settings page. Every value is a real config field with a reset control."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...config.loader import save_config
from ...config.models import VigilConfig
from ..widgets.fields import FieldRow
from .base import Page

SPEC = [
    (
        "App",
        "app",
        [
            ("Theme", "theme", "theme", ["system", "dark", "light"], False),
            (
                "Log level",
                "log_level",
                "combo",
                ["DEBUG", "INFO", "WARNING", "ERROR"],
                False,
            ),
            ("Start minimized", "start_minimized", "bool", None, False),
        ],
    ),
    (
        "Inference",
        "inference",
        [
            ("Device", "device", "text", None, False),
            ("Analysis fps", "analysis_fps", "float", None, False),
            ("Queue size", "queue_size", "int", None, False),
            ("Max frame age (s)", "max_frame_age_s", "float", None, False),
        ],
    ),
    (
        "Face recognition",
        "face",
        [
            (
                "Detector",
                "detector",
                "combo",
                ["dlib_cnn", "dlib_hog", "none"],
                False,
            ),
            ("Known threshold", "known_threshold", "float", None, True),
            ("Unknown threshold", "unknown_threshold", "float", None, True),
            ("Margin", "margin", "float", None, True),
            ("Minimum votes", "min_votes", "int", None, False),
            ("Minimum face px", "min_face_px", "int", None, False),
            ("Embed face px", "min_face_px_embed", "int", None, True),
            ("Best observations", "best_k", "int", None, True),
            (
                "Uncertain policy",
                "uncertain_policy",
                "combo",
                ["review", "unknown", "ignore"],
                False,
            ),
            (
                "Gallery score",
                "gallery_score",
                "combo",
                ["min", "top3_mean"],
                True,
            ),
            ("Max detect side", "max_detect_side", "int", None, True),
            ("Stranger window (s)", "unknown_merge_window_s", "float", None, True),
            ("Stranger threshold", "unknown_merge_threshold", "float", None, True),
            ("Track IoU", "track_iou", "float", None, True),
            ("Track max gap (s)", "track_max_gap_s", "float", None, True),
            ("Models directory", "models_dir", "text", None, True),
        ],
    ),
    (
        "Motion",
        "motion",
        [
            ("Enabled", "enabled", "bool", None, False),
            (
                "Algorithm",
                "algorithm",
                "combo",
                ["mog2", "running_avg", "frame_diff"],
                False,
            ),
            ("Sample every", "sample_every", "int", None, False),
            ("Max side", "max_side", "int", None, True),
            ("Threshold percent", "threshold_pct", "float", None, False),
            ("Minimum area px", "min_area_px", "int", None, True),
            ("Minimum frames", "min_duration_frames", "int", None, False),
            ("Cooldown (s)", "cooldown_s", "float", None, False),
            ("Suppress global percent", "suppress_global_pct", "float", None, True),
            ("Preroll (s)", "preroll_s", "float", None, True),
        ],
    ),
    (
        "Display",
        "display",
        [
            ("Grid fps", "grid_fps", "float", None, False),
            ("Single fps", "single_fps", "float", None, False),
            ("Overlay TTL (s)", "overlay_ttl_s", "float", None, True),
        ],
    ),
    (
        "Notifications",
        "notify",
        [
            ("Desktop notifications", "desktop_enabled", "bool", None, False),
            ("Sound", "sound_enabled", "bool", None, False),
            ("Stranger cooldown (s)", "stranger_cooldown_s", "float", None, False),
        ],
    ),
    (
        "Capture",
        "capture",
        [
            ("Stall timeout (s)", "stall_timeout_s", "float", None, False),
            ("Backoff initial (s)", "backoff_initial_s", "float", None, False),
            ("Backoff max (s)", "backoff_max_s", "float", None, False),
            ("Backoff jitter", "backoff_jitter", "float", None, True),
            ("Offline notify after (s)", "offline_notify_after_s", "float", None, False),
            ("Open timeout (ms)", "open_timeout_ms", "int", None, True),
            ("Capture buffer", "buffer_size", "int", None, True),
        ],
    ),
    (
        "Storage",
        "storage",
        [
            ("Data directory", "data_dir", "text", None, True),
            ("Event retention (days)", "event_retention_days", "int", None, False),
            ("Log retention (days)", "log_retention_days", "int", None, False),
            ("Snapshot quality", "snapshot_jpeg_quality", "int", None, True),
        ],
    ),
]


class SettingsPage(Page):
    def __init__(
        self,
        context,
        config_path: Path,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            "Settings",
            "No settings to edit",
            "The configuration model did not expose any fields.",
            None,
            parent,
        )
        self.context = context
        self.config = context.config
        self.config_path = Path(config_path)
        self.on_saved = None
        self.rows: List[FieldRow] = []
        self._bindings: List[Tuple[str, str, FieldRow]] = []
        self.defaults = VigilConfig()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        for title, section_name, fields in SPEC:
            content_layout.addWidget(
                self._build_section(title, section_name, fields)
            )
        content_layout.addStretch(1)
        scroll.setWidget(content)
        self.body_layout.addWidget(scroll, 1)

        footer = QHBoxLayout()
        self.advanced_box = QCheckBox("Show advanced settings")
        self.advanced_box.toggled.connect(self._set_advanced)
        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        footer.addWidget(self.advanced_box)
        footer.addWidget(self.status_label, 1)
        self.save_button = QPushButton("Save settings")
        self.save_button.setObjectName("Primary")
        self.save_button.clicked.connect(self.save)
        footer.addWidget(self.save_button)
        self.body_layout.addLayout(footer)

        self._set_advanced(False)
        self.view.set_retry(self.show_content)
        self.show_content()

    def _build_section(
        self, title: str, section_name: str, fields
    ) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)

        section = getattr(self.config, section_name)
        defaults = getattr(self.defaults, section_name)
        for label, attribute, kind, choices, advanced in fields:
            widget = self._make_widget(kind, choices)
            default = getattr(defaults, attribute)
            row = FieldRow(label, widget, default, advanced=advanced)
            row.set_value(getattr(section, attribute))
            self.rows.append(row)
            self._bindings.append((section_name, attribute, row))
            layout.addWidget(row)
        return frame

    @staticmethod
    def _make_widget(kind: str, choices) -> QWidget:
        if kind == "bool":
            return QCheckBox()
        if kind in ("combo", "theme"):
            combo = QComboBox()
            combo.addItems(list(choices or []))
            return combo
        if kind == "int":
            spin = QSpinBox()
            spin.setLocale(QLocale.c())
            spin.setRange(0, 1000000)
            return spin
        if kind == "float":
            spin = QDoubleSpinBox()
            spin.setLocale(QLocale.c())
            spin.setDecimals(3)
            spin.setRange(0.0, 1000000.0)
            return spin
        return QLineEdit()

    def _set_advanced(self, visible: bool) -> None:
        for row in self.rows:
            row.set_advanced_visible(visible)

    def save(self) -> None:
        try:
            for section_name, attribute, row in self._bindings:
                section = getattr(self.config, section_name)
                setattr(section, attribute, row.value())
            save_config(self.config_path, self.config)
        except Exception as err:
            self._report(False, "The settings were not saved: %s" % err)
            return

        message = "Saved and applied to the running workers."
        apply_config = getattr(self.context, "apply_config", None)
        if callable(apply_config):
            try:
                summary = apply_config()
            except Exception as err:
                self._report(False, "Saved, but could not apply: %s" % err)
                return
            if summary.get("cameras_rebuilt"):
                message = "Saved and applied. Capture restarted for %d camera(s)." % int(
                    summary.get("cameras", 0)
                )
            if summary.get("backend_rebuilt"):
                message += " The face backend was reloaded."
        else:
            message = "Saved. The running app was not changed."

        self._report(True, message)
        if callable(self.on_saved):
            self.on_saved()

    def reload(self) -> None:
        """Re-read the live config after an external reload."""
        for section_name, attribute, row in self._bindings:
            section = getattr(self.config, section_name)
            defaults = getattr(self.defaults, section_name)
            row.default = getattr(defaults, attribute)
            row.set_value(getattr(section, attribute))

    def _report(self, ok: bool, message: str) -> None:
        self.status_label.setObjectName("Muted" if ok else "Danger")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.setText(message)
