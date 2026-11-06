#!/usr/bin/env python3
"""Credentials (ETH login, API keys): in this Mac's Keychain, nowhere else.

The owner's ruling of 2026-11-06: his ETH password lives only in the
Keychain, with nothing in Dropbox. Until then it sat Fernet-encrypted in
``Scripts/config/credentials.enc``, which Dropbox synced, with the key in
the Keychain (step-back audit D9-6).

Each credential is now its own Keychain item, under one service name.
Interface expected by callers: ``SecureCredentialManager(app_name)`` with
``get_credential(type)`` / ``store_credential(type, value)``, plus
``store_credentials(mapping)`` / ``delete_credential(type)`` and the
``get_credential_manager()`` factory.

THE OLD FILE. It has moved out of Dropbox to ``~/.mathpdf/credentials.enc``.
Its contents move into the Keychain only when he presses the button on the
Settings page, and not before: the first read of a Keychain item by a new
program can raise a macOS dialog, and a dialog with nobody expecting it has
locked him out of his machine before (tests/conftest.py). Until then
``get_credential`` still reads it, so nothing stops working.
:meth:`SecureCredentialManager.move_to_keychain` then deletes the file, the
key that opened it, and the publisher logins borrowed in June, which his
ruling does not keep.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "math-pdf-manager"
_KEYRING_KEY_NAME = "credential-store-fernet-key"
#: Publisher cookies, borrowed from Chrome (downloader/browser_session.py).
#: The ruling of 2026-11-06 deletes those of June; they are not moved.
_BORROWED_LOGINS = "browser_cookies_json"


def legacy_store_path() -> Path:
    """Where the old encrypted file lives now: on this Mac, out of Dropbox."""
    return Path.home() / ".mathpdf" / "credentials.enc"


class SecureCredentialManager:
    """One Keychain item per credential."""

    def __init__(self, app_name: str = "academic_papers", *,
                 enc_path: Optional[Path] = None):
        self.app_name = app_name
        self.service = f"{_KEYRING_SERVICE}:{app_name}"
        self.enc_path = Path(enc_path) if enc_path else legacy_store_path()

    # -- the old file ---------------------------------------------------
    def _read_old_file(self) -> Optional[dict]:
        """The old store's contents, ``{}`` when there is no file, ``None``
        when there is one that cannot be read. Writes nothing."""
        import keyring
        from cryptography.fernet import Fernet
        if not self.enc_path.exists():
            return {}
        try:
            key = keyring.get_password(self.service, _KEYRING_KEY_NAME)
            data = json.loads(Fernet(key.encode()).decrypt(self.enc_path.read_bytes()))
        except Exception as exc:
            logger.warning("old credential file unreadable: %s", type(exc).__name__)
            return None
        return data if isinstance(data, dict) else None

    def _rewrite_old_file(self, data: dict) -> None:
        import keyring
        from cryptography.fernet import Fernet
        key = keyring.get_password(self.service, _KEYRING_KEY_NAME)
        self.enc_path.write_bytes(
            Fernet(key.encode()).encrypt(json.dumps(data).encode("utf-8")))

    def has_old_file(self) -> bool:
        return self.enc_path.exists()

    def move_to_keychain(self) -> dict:
        """Move the old file's credentials into the Keychain, read each one
        back, and only then delete the file, its backup and the key that
        opened it. Returns ``{moved, dropped, problem}`` -- names, never
        values. A problem leaves the old file exactly as it was.

        ``unlink``, not the trash: this is a password store, not a paper,
        and "nothing in Dropbox" is the ruling. The trash is in Dropbox.
        """
        import keyring
        data = self._read_old_file()
        if data is None:
            return {"moved": [], "dropped": [],
                    "problem": "the old file could not be read, so it was left "
                               "as it is; type your ETH login in below instead"}
        moved, dropped = [], []
        for name, value in sorted(data.items()):
            if name == _BORROWED_LOGINS:
                dropped.append(name)
                continue
            try:
                keyring.set_password(self.service, name, value)
                same = keyring.get_password(self.service, name) == value
            except Exception as exc:
                logger.warning("Keychain refused %s: %s", name, type(exc).__name__)
                same = False
            if not same:
                return {"moved": moved, "dropped": [],
                        "problem": f"the Keychain did not keep {name}, so the "
                                   f"old file was left as it is"}
            moved.append(name)
        self.enc_path.unlink(missing_ok=True)
        self.enc_path.with_suffix(self.enc_path.suffix + ".bak").unlink(missing_ok=True)
        try:
            keyring.delete_password(self.service, _KEYRING_KEY_NAME)
        except Exception as exc:
            logger.debug("old key not deleted: %s", type(exc).__name__)
        return {"moved": moved, "dropped": dropped, "problem": ""}

    # -- public API -----------------------------------------------------
    def get_credential(self, credential_type: str) -> Optional[str]:
        import keyring
        value = keyring.get_password(self.service, credential_type)
        if value is not None or credential_type == _BORROWED_LOGINS:
            return value
        return (self._read_old_file() or {}).get(credential_type)

    def store_credential(self, credential_type: str, value: str) -> bool:
        import keyring
        try:
            keyring.set_password(self.service, credential_type, value)
            return True
        except Exception as exc:
            logger.error("failed to store credential %s: %s", credential_type,
                         type(exc).__name__)
            return False

    def store_credentials(self, mapping: dict) -> bool:
        return all([self.store_credential(k, v) for k, v in mapping.items()])

    def delete_credential(self, credential_type: str) -> bool:
        import keyring
        from keyring.errors import PasswordDeleteError
        try:
            keyring.delete_password(self.service, credential_type)
        except PasswordDeleteError:
            pass                                    # it was not there
        old = self._read_old_file()
        if old and credential_type in old:
            # Cleared before the old file was moved: gone means gone.
            del old[credential_type]
            self._rewrite_old_file(old)
        return True


_manager: Optional[SecureCredentialManager] = None


def get_credential_manager() -> SecureCredentialManager:
    """Process-wide singleton used by setup_credentials / secure_config."""
    global _manager
    if _manager is None:
        _manager = SecureCredentialManager()
    return _manager
