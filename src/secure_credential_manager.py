#!/usr/bin/env python3
"""Local encrypted credential store (ETH institutional login, API keys).

Restored in the Phase-1b work: ``core.config.secure_config`` and
``core.config.setup_credentials`` both import ``secure_credential_manager``
at the top level, but the module had gone missing from the tree — so the
secure store silently fell back to "not available" and there was no way
to hold ETH credentials.  This is that module.

Design:
* Credentials are stored as a JSON dict encrypted with **Fernet** to
  ``<repo>/config/credentials.enc`` (the existing location/format).
* The Fernet key lives in the OS keychain via ``keyring`` (macOS
  Keychain), so there is **no master password to type** and the key
  never sits in the repo — it's machine-bound.  Entering a credential
  (e.g. from the cockpit Settings tab) is all that's needed; no terminal.
* If an existing ``credentials.enc`` can't be decrypted with the current
  key (e.g. it was written by an older key we no longer have), it's
  backed up to ``credentials.enc.bak`` and treated as empty so the user
  can re-enter — never a hard crash.

Interface expected by callers: ``SecureCredentialManager(app_name)`` with
``get_credential(type)`` / ``store_credential(type, value)``, plus
``store_credentials(mapping)`` / ``delete_credential(type)`` and the
``get_credential_manager()`` factory.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "math-pdf-manager"
_KEYRING_KEY_NAME = "credential-store-fernet-key"
_DEFAULT_ENC = Path(__file__).resolve().parent.parent / "config" / "credentials.enc"


def _load_or_create_key(app_name: str) -> bytes:
    """Fetch the Fernet key from the OS keychain, creating it on first use."""
    import keyring
    from cryptography.fernet import Fernet

    service = f"{_KEYRING_SERVICE}:{app_name}"
    existing = keyring.get_password(service, _KEYRING_KEY_NAME)
    if existing:
        return existing.encode()
    key = Fernet.generate_key()
    keyring.set_password(service, _KEYRING_KEY_NAME, key.decode())
    return key


class SecureCredentialManager:
    """Fernet-encrypted, keychain-keyed credential store."""

    def __init__(self, app_name: str = "academic_papers", *,
                 enc_path: Optional[Path] = None, key: Optional[bytes] = None):
        self.app_name = app_name
        self.enc_path = Path(enc_path) if enc_path else _DEFAULT_ENC
        # ``key`` is for tests (avoids touching the real keychain); in
        # production the key comes from the OS keychain lazily.
        self._key = key

    # -- internals ------------------------------------------------------
    def _fernet(self):
        from cryptography.fernet import Fernet
        if self._key is None:
            self._key = _load_or_create_key(self.app_name)
        return Fernet(self._key)

    def _load(self) -> dict:
        # Read-only and side-effect-free: an unreadable store (e.g.
        # written with a key we no longer have) is treated as empty, but
        # the file is NOT modified here — destroying/renaming it on a mere
        # read would be surprising.  Preservation happens at write time.
        if not self.enc_path.exists():
            return {}
        try:
            return json.loads(self._fernet().decrypt(self.enc_path.read_bytes()))
        except Exception as exc:
            logger.warning("credential store unreadable (%s); treating as empty", exc)
            return {}

    def _save(self, data: dict) -> None:
        self.enc_path.parent.mkdir(parents=True, exist_ok=True)
        # If an existing store can't be read with the current key, back it
        # up ONCE before overwriting so nothing is silently destroyed.
        if self.enc_path.exists():
            try:
                json.loads(self._fernet().decrypt(self.enc_path.read_bytes()))
            except Exception:
                bak = self.enc_path.with_suffix(self.enc_path.suffix + ".bak")
                if not bak.exists():
                    try:
                        bak.write_bytes(self.enc_path.read_bytes())
                    except OSError:
                        pass
        token = self._fernet().encrypt(json.dumps(data).encode("utf-8"))
        tmp = self.enc_path.with_suffix(self.enc_path.suffix + ".tmp")
        tmp.write_bytes(token)
        os.replace(tmp, self.enc_path)

    # -- public API -----------------------------------------------------
    def get_credential(self, credential_type: str) -> Optional[str]:
        return self._load().get(credential_type)

    def store_credential(self, credential_type: str, value: str) -> bool:
        try:
            data = self._load()
            data[credential_type] = value
            self._save(data)
            return True
        except Exception as exc:  # pragma: no cover -- defensive
            logger.error("failed to store credential %s: %s", credential_type, exc)
            return False

    def store_credentials(self, mapping: dict) -> bool:
        try:
            data = self._load()
            data.update(mapping)
            self._save(data)
            return True
        except Exception as exc:  # pragma: no cover
            logger.error("failed to store credentials: %s", exc)
            return False

    def delete_credential(self, credential_type: str) -> bool:
        data = self._load()
        if credential_type in data:
            del data[credential_type]
            self._save(data)
        return True

    def list_credential_types(self) -> list:
        return sorted(self._load().keys())


_manager: Optional[SecureCredentialManager] = None


def get_credential_manager() -> SecureCredentialManager:
    """Process-wide singleton used by setup_credentials / secure_config."""
    global _manager
    if _manager is None:
        _manager = SecureCredentialManager()
    return _manager
