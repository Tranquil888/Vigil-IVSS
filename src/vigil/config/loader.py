"""Read and write the TOML config without losing comments on scalar sections."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import tomlkit

from .models import VigilConfig

try:  # Python 3.11+
    import tomllib as _toml_reader
except ModuleNotFoundError:  # pragma: no cover - exercised on 3.9
    import tomli as _toml_reader


class ConfigError(ValueError):
    """A config file exists but cannot be used."""


def defaults_dict() -> Dict[str, Any]:
    return VigilConfig().model_dump(mode="json", exclude_none=True)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_config_path() -> Path:
    explicit = os.environ.get("VIGIL_CONFIG")
    if explicit:
        return Path(explicit)
    appdata = os.environ.get("APPDATA")
    root = Path(appdata) if appdata else Path.home() / ".config"
    return root / "Vigil" / "config.toml"


def read_toml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return _toml_reader.load(handle)
    except _toml_reader.TOMLDecodeError as err:
        raise ConfigError("%s is not valid TOML: %s" % (path, err)) from err
    except OSError as err:
        raise ConfigError("cannot read %s: %s" % (path, err)) from err


def load_config(path: Optional[Path] = None) -> VigilConfig:
    target = Path(path) if path is not None else default_config_path()
    if not target.exists():
        return VigilConfig()
    raw = read_toml(target)
    try:
        return VigilConfig.model_validate(deep_merge(defaults_dict(), raw))
    except Exception as err:  # pydantic raises ValidationError
        raise ConfigError("%s is not a valid Vigil config: %s" % (target, err)) from err


def _is_same(current: Any, wanted: Any) -> bool:
    if isinstance(current, (list, tuple)) and isinstance(wanted, (list, tuple)):
        return list(current) == list(wanted)
    return current == wanted


def _apply(table: Any, data: Dict[str, Any]) -> None:
    """Write data into a tomlkit table, keeping untouched items and comments."""
    for key, value in data.items():
        if isinstance(value, dict):
            if key not in table or not isinstance(table[key], (dict, tomlkit.items.Table)):
                table[key] = tomlkit.table()
            _apply(table[key], value)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            # Arrays of tables are rebuilt. Comments inside [[cameras]] do not
            # survive an edit, which is the documented cost of structured edits.
            array = tomlkit.aot()
            for item in value:
                entry = tomlkit.table()
                _apply(entry, item)
                array.append(entry)
            table[key] = array
        else:
            if key in table and _is_same(table[key], value):
                continue
            table[key] = value


def save_config(
    path: Path, config: VigilConfig, secrets=None
) -> None:
    from ..secrets import SecretStore, protected_config, has_credentials

    if secrets is None and any(
        has_credentials(camera.source) for camera in config.cameras
    ):
        secrets = SecretStore(resolve_data_dir(config))
    safe = protected_config(config, secrets) if secrets is not None else config
    data = safe.model_dump(mode="json", exclude_none=True)
    document = tomlkit.document()
    if path.exists():
        try:
            document = tomlkit.parse(path.read_text(encoding="utf-8"))
        except Exception as err:
            raise ConfigError("%s is not valid TOML: %s" % (path, err)) from err
    _apply(document, data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(document), encoding="utf-8")


def resolve_data_dir(
    config: VigilConfig, override: Optional[Path] = None
) -> Path:
    if override is not None:
        return Path(override)
    if config.storage.data_dir:
        return Path(config.storage.data_dir).expanduser()
    env = os.environ.get("VIGIL_DATA_DIR")
    if env:
        return Path(env).expanduser()
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Vigil"
    return Path.home() / ".vigil"
