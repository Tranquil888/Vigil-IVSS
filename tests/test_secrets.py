"""Camera secrets: encryption at rest, config token, and live resolution."""

from __future__ import annotations

import json

import pytest

from vigil.config.loader import load_config, save_config
from vigil.config.models import CameraConfig, VigilConfig
from vigil.secrets import (
    VAULT_SOURCE,
    SecretStore,
    has_credentials,
    protect_camera_sources,
    resolve_camera_sources,
)

RTSP = "rtsp://operator:s3cret@10.0.0.5/stream1"
PLAIN = "rtsp://10.0.0.5/stream1"


def make_config(source: str = RTSP) -> VigilConfig:
    return VigilConfig(
        cameras=[CameraConfig(id="front", name="Front door", source=source)]
    )


def test_has_credentials_only_matches_a_url_with_a_password():
    assert has_credentials(RTSP)
    assert not has_credentials("rtsp://user@10.0.0.5/stream")
    assert not has_credentials("rtsp://10.0.0.5/stream")
    assert not has_credentials("0")
    assert not has_credentials("C:\\videos\\clip.mp4")
    assert has_credentials("rtsp://user:pass@host/a\nC:\\videos\\clip.mp4")
    assert not has_credentials("C:\\videos\\a.mp4\nC:\\videos\\b.mp4")


def test_store_round_trip_encrypts_on_disk(tmp_path):
    store = SecretStore(tmp_path)
    store.set("front", RTSP)

    assert store.get("front") == RTSP
    assert "s3cret" not in (tmp_path / "secrets.json").read_text(encoding="utf-8")
    document = json.loads((tmp_path / "secrets.json").read_text(encoding="utf-8"))
    assert document["version"] == 1
    assert "front" in document["entries"]

    reopened = SecretStore(tmp_path)
    assert reopened.get("front") == RTSP


def test_store_delete_removes_the_entry(tmp_path):
    store = SecretStore(tmp_path)
    store.set("front", RTSP)
    assert store.delete("front")
    assert store.get("front") is None
    assert not store.delete("front")


def test_protect_replaces_the_source_with_the_vault_token(tmp_path):
    config = make_config()
    store = SecretStore(tmp_path)

    assert protect_camera_sources(config, store) == 1
    assert config.cameras[0].source == VAULT_SOURCE
    assert store.get("front") == RTSP


def test_resolve_restores_the_source(tmp_path):
    config = make_config()
    store = SecretStore(tmp_path)
    protect_camera_sources(config, store)

    assert resolve_camera_sources(config, store) == 1
    assert config.cameras[0].source == RTSP


def test_plain_sources_are_left_alone(tmp_path):
    config = make_config(PLAIN)
    store = SecretStore(tmp_path)

    assert protect_camera_sources(config, store) == 0
    assert config.cameras[0].source == PLAIN


def test_replacing_a_secret_source_drops_the_old_secret(tmp_path):
    config = make_config()
    store = SecretStore(tmp_path)
    protect_camera_sources(config, store)
    assert store.get("front") == RTSP

    config.cameras[0].source = PLAIN
    protect_camera_sources(config, store)
    assert store.get("front") is None


def test_save_config_writes_the_token_and_keeps_memory_plain(tmp_path):
    config = make_config()
    config_path = tmp_path / "config.toml"
    store = SecretStore(tmp_path / "data")

    save_config(config_path, config, secrets=store)

    text = config_path.read_text(encoding="utf-8")
    assert 'source = "vault"' in text
    assert "s3cret" not in text
    assert config.cameras[0].source == RTSP
    assert store.get("front") == RTSP


def test_save_config_creates_a_store_when_none_is_given(tmp_path):
    config = make_config()
    config.storage.data_dir = str(tmp_path / "data")
    config_path = tmp_path / "config.toml"

    save_config(config_path, config)

    text = config_path.read_text(encoding="utf-8")
    assert 'source = "vault"' in text
    assert "s3cret" not in text
    assert (tmp_path / "data" / "secrets.json").exists()
    assert SecretStore(tmp_path / "data").get("front") == RTSP


def test_a_saved_vault_config_loads_and_resolves(tmp_path):
    config = make_config()
    config_path = tmp_path / "config.toml"
    store = SecretStore(tmp_path / "data")
    save_config(config_path, config, secrets=store)

    loaded = load_config(config_path)
    assert loaded.cameras[0].source == VAULT_SOURCE
    resolve_camera_sources(loaded, store)
    assert loaded.cameras[0].source == RTSP


def test_missing_secret_leaves_the_token_and_warns(tmp_path):
    config = make_config()
    config.cameras[0].source = VAULT_SOURCE
    store = SecretStore(tmp_path)

    assert resolve_camera_sources(config, store) == 0
    assert config.cameras[0].source == VAULT_SOURCE


def test_corrupt_store_is_reported(tmp_path):
    from vigil.secrets import SecretError

    (tmp_path / "secrets.json").write_text("{not json", encoding="utf-8")
    store = SecretStore(tmp_path)

    with pytest.raises(SecretError):
        store.get("front")
