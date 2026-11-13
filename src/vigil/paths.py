"""Filesystem locations used by the app."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config.loader import resolve_data_dir
from .config.models import VigilConfig


def data_dir(config: VigilConfig, override: Optional[Path] = None) -> Path:
    return resolve_data_dir(config, override)


def models_dir(config: VigilConfig, override: Optional[Path] = None) -> Path:
    """Resolve the model directory. ``override`` is the models path itself."""
    if override is not None:
        return Path(override)
    if config.face.models_dir:
        return Path(config.face.models_dir).expanduser()
    return data_dir(config) / "models"


def models_for(config: VigilConfig, data_path: Optional[Path] = None) -> Path:
    """Model directory for a context whose data path may differ from config."""
    if config.face.models_dir:
        return Path(config.face.models_dir).expanduser()
    root = Path(data_path) if data_path is not None else data_dir(config)
    return root / "models"


def db_path(config: VigilConfig, override: Optional[Path] = None) -> Path:
    return data_dir(config, override) / "vigil.db"


def log_dir(config: VigilConfig, override: Optional[Path] = None) -> Path:
    return data_dir(config, override) / "logs"


def people_dir(config: VigilConfig, override: Optional[Path] = None) -> Path:
    return data_dir(config, override) / "people"


def snapshots_dir(config: VigilConfig, override: Optional[Path] = None) -> Path:
    return data_dir(config, override) / "snapshots"
