"""Camera stream secrets, encrypted at rest.

A camera URL can carry a username and password. The TOML config must not hold
that password in plain text, so the source moves to a small encrypted store and
the config keeps the token ``vault`` instead. On Windows the store uses DPAPI,
which ties the ciphertext to the current user account. Everywhere else it uses
Fernet with a key file next to the store.

The store is keyed by camera id, so resolving is a direct lookup. The live
config object keeps the plaintext source in memory for the capture thread, and
``save_config`` encrypts it again on the way out.
"""

from __future__ import annotations

import base64
import ctypes
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional

from .config.models import VigilConfig

log = logging.getLogger(__name__)

VAULT_SOURCE = "vault"
STORE_NAME = "secrets.json"
KEY_NAME = "secrets.key"
STORE_VERSION = 1

_CREDENTIAL_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^/@\s]+:[^/@\s]+@")


class SecretError(RuntimeError):
    """The secret store cannot be read, decrypted, or written."""


def has_credentials(source: str) -> bool:
    """True when a source line embeds a user:password pair in a URL."""
    for line in str(source).splitlines():
        if _CREDENTIAL_URL.match(line.strip()):
            return True
    return False


# -- Windows DPAPI -----------------------------------------------------


if sys.platform == "win32":  # pragma: no branch - the fallback covers other OSes

    class _DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.c_uint32),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    _crypt32 = ctypes.windll.crypt32
    _kernel32 = ctypes.windll.kernel32
    _crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.c_wchar_p,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(_DataBlob),
    ]
    _crypt32.CryptProtectData.restype = ctypes.c_bool
    _crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(ctypes.c_wchar_p),
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(_DataBlob),
    ]
    _crypt32.CryptUnprotectData.restype = ctypes.c_bool
    _kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    _kernel32.LocalFree.restype = ctypes.c_void_p
    _CRYPTPROTECT_UI_FORBIDDEN = 0x01


def _to_blob(payload: bytes):
    buffer = ctypes.create_string_buffer(payload, len(payload))
    blob = _DataBlob(
        len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
    )
    return blob, buffer


def _dpapi_protect(payload: bytes) -> bytes:
    source, source_buffer = _to_blob(payload)
    target = _DataBlob()
    ok = _crypt32.CryptProtectData(
        ctypes.byref(source),
        "Vigil camera secret",
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(target),
    )
    del source_buffer
    if not ok:
        raise SecretError("DPAPI could not encrypt the camera secret")
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        _kernel32.LocalFree(target.pbData)


def _dpapi_unprotect(payload: bytes) -> bytes:
    source, source_buffer = _to_blob(payload)
    target = _DataBlob()
    description = ctypes.c_wchar_p()
    ok = _crypt32.CryptUnprotectData(
        ctypes.byref(source),
        ctypes.byref(description),
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(target),
    )
    del source_buffer
    if not ok:
        raise SecretError("DPAPI could not decrypt the camera secret")
    try:
        if description:
            _kernel32.LocalFree(ctypes.cast(description, ctypes.c_void_p))
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        _kernel32.LocalFree(target.pbData)


# -- Fernet fallback ---------------------------------------------------


def _fernet(key_path: Path):
    from cryptography.fernet import Fernet

    if not key_path.exists():
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(Fernet.generate_key())
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
    return Fernet(key_path.read_bytes().strip())


class SecretStore:
    """A JSON map of camera id to encrypted source text."""

    def __init__(self, root: Path, scheme: Optional[str] = None) -> None:
        self.root = Path(root)
        self.path = self.root / STORE_NAME
        self.key_path = self.root / KEY_NAME
        self.scheme = scheme or ("dpapi" if sys.platform == "win32" else "fernet")
        self._entries: Dict[str, str] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.path.exists():
            return
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as err:
            raise SecretError("cannot read %s: %s" % (self.path, err)) from err
        if document.get("version") != STORE_VERSION:
            raise SecretError("%s has an unknown version" % self.path)
        if document.get("scheme") not in (None, self.scheme):
            raise SecretError(
                "%s was written with a different encryption scheme" % self.path
            )
        entries = document.get("entries")
        if not isinstance(entries, dict):
            raise SecretError("%s has no entries table" % self.path)
        self._entries = {
            str(key): str(value) for key, value in entries.items()
        }

    def _save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        document = {
            "version": STORE_VERSION,
            "scheme": self.scheme,
            "entries": self._entries,
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(document, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def _encrypt(self, payload: bytes) -> bytes:
        if self.scheme == "dpapi":
            return _dpapi_protect(payload)
        return _fernet(self.key_path).encrypt(payload)

    def _decrypt(self, payload: bytes) -> bytes:
        if self.scheme == "dpapi":
            return _dpapi_unprotect(payload)
        return _fernet(self.key_path).decrypt(payload)

    def set(self, key: str, value: str) -> None:
        self._load()
        sealed = self._encrypt(str(value).encode("utf-8"))
        self._entries[str(key)] = base64.b64encode(sealed).decode("ascii")
        self._save()

    def get(self, key: str) -> Optional[str]:
        self._load()
        sealed = self._entries.get(str(key))
        if sealed is None:
            return None
        try:
            return self._decrypt(base64.b64decode(sealed)).decode("utf-8")
        except SecretError:
            raise
        except Exception as err:
            raise SecretError("cannot decrypt the secret for %s: %s" % (key, err))

    def delete(self, key: str) -> bool:
        self._load()
        if self._entries.pop(str(key), None) is None:
            return False
        self._save()
        return True

    def keys(self) -> list:
        self._load()
        return sorted(self._entries)


def resolve_camera_sources(config: VigilConfig, store: SecretStore) -> int:
    """Replace ``vault`` sources with their decrypted value, in place."""
    resolved = 0
    for camera in config.cameras:
        if camera.source != VAULT_SOURCE:
            continue
        secret = store.get(camera.id)
        if not secret:
            log.warning(
                "no stored secret for camera %s", camera.id,
                extra={"event": "secrets.missing", "camera_id": camera.id},
            )
            continue
        camera.source = secret
        resolved += 1
    return resolved


def protect_camera_sources(config: VigilConfig, store: SecretStore) -> int:
    """Encrypt credential-bearing sources and replace them with ``vault``."""
    protected = 0
    for camera in config.cameras:
        source = camera.source
        if source == VAULT_SOURCE:
            continue
        if has_credentials(source):
            store.set(camera.id, source)
            camera.source = VAULT_SOURCE
            protected += 1
        elif store.get(camera.id) is not None:
            # The operator replaced an encrypted source with a plain one, so
            # the old secret must not outlive it.
            store.delete(camera.id)
    return protected


def protected_config(config: VigilConfig, store: SecretStore) -> VigilConfig:
    """A deep copy safe to serialize, with every secret moved to the store."""
    copy = config.model_copy(deep=True)
    protect_camera_sources(copy, store)
    return copy
