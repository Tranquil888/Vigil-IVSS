import os

import pytest

from vigil.config.loader import (
    defaults_dict,
    load_config,
    resolve_data_dir,
    save_config,
)
from vigil.config.models import VigilConfig


def test_load_without_a_file_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "missing.toml")
    assert isinstance(cfg, VigilConfig)
    assert cfg.cameras == []


def test_camera_override_beats_global(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        """
[motion]
threshold_pct = 2.0

[[cameras]]
id = "front"
name = "Front"
source = "rtsp://10.0.0.2/sub"
[cameras.motion]
threshold_pct = 8.0
""",
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.motion.threshold_pct == 2.0
    assert cfg.cameras[0].motion.threshold_pct == 8.0
    assert cfg.cameras[0].motion.min_area_px == 150


def test_defaults_dict_is_valid_config():
    assert VigilConfig.model_validate(defaults_dict()).app.theme == "dark"


def test_save_preserves_comments(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        "# keep me\n[inference]\n# fps matters\nanalysis_fps = 5\n",
        encoding="utf-8",
    )
    cfg = load_config(path)
    cfg.inference.analysis_fps = 8
    save_config(path, cfg)
    text = path.read_text(encoding="utf-8")
    assert "# keep me" in text
    assert "# fps matters" in text
    assert load_config(path).inference.analysis_fps == 8


def test_env_overrides_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIL_DATA_DIR", str(tmp_path / "custom"))
    cfg = VigilConfig()
    assert resolve_data_dir(cfg) == tmp_path / "custom"


def test_explicit_data_dir_beats_env(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIL_DATA_DIR", str(tmp_path / "custom"))
    cfg = VigilConfig()
    cfg.storage.data_dir = str(tmp_path / "explicit")
    assert resolve_data_dir(cfg) == tmp_path / "explicit"


def test_bad_toml_raises_a_clear_error(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[inference\nanalysis_fps = 5", encoding="utf-8")
    with pytest.raises(ValueError) as err:
        load_config(path)
    assert "config.toml" in str(err.value)
