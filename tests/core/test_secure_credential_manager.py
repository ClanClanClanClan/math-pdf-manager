"""Restored encrypted credential store (ETH login / API keys)."""
from __future__ import annotations

import pytest


def _key():
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


class TestSecureCredentialManager:

    def test_round_trip(self, tmp_path):
        from secure_credential_manager import SecureCredentialManager
        enc = tmp_path / "credentials.enc"
        k = _key()
        m = SecureCredentialManager(enc_path=enc, key=k)
        assert m.store_credential("eth_username", "dpossamai") is True
        assert m.store_credential("eth_password", "s3cr3t") is True
        assert m.get_credential("eth_username") == "dpossamai"
        assert m.get_credential("eth_password") == "s3cr3t"
        # Encrypted on disk — not plaintext.
        blob = enc.read_bytes()
        assert b"s3cr3t" not in blob and b"dpossamai" not in blob

    def test_persists_across_instances(self, tmp_path):
        from secure_credential_manager import SecureCredentialManager
        enc = tmp_path / "credentials.enc"
        k = _key()
        SecureCredentialManager(enc_path=enc, key=k).store_credential("eth_username", "u")
        # A fresh instance with the same key reads it back.
        assert SecureCredentialManager(enc_path=enc, key=k).get_credential("eth_username") == "u"

    def test_store_credentials_bulk_and_delete(self, tmp_path):
        from secure_credential_manager import SecureCredentialManager
        m = SecureCredentialManager(enc_path=tmp_path / "c.enc", key=_key())
        m.store_credentials({"eth_username": "u", "eth_password": "p"})
        assert sorted(m.list_credential_types()) == ["eth_password", "eth_username"]
        m.delete_credential("eth_password")
        assert m.get_credential("eth_password") is None
        assert m.get_credential("eth_username") == "u"

    def test_missing_credential_returns_none(self, tmp_path):
        from secure_credential_manager import SecureCredentialManager
        m = SecureCredentialManager(enc_path=tmp_path / "c.enc", key=_key())
        assert m.get_credential("nope") is None

    def test_unreadable_store_read_is_side_effect_free(self, tmp_path):
        from secure_credential_manager import SecureCredentialManager
        enc = tmp_path / "credentials.enc"
        enc.write_bytes(b"not a valid fernet token")  # e.g. an old key
        m = SecureCredentialManager(enc_path=enc, key=_key())
        # A read treats it as empty but does NOT modify the file.
        assert m.get_credential("x") is None
        assert not (tmp_path / "credentials.enc.bak").exists()
        assert enc.read_bytes() == b"not a valid fernet token"

    def test_unreadable_store_backed_up_on_write(self, tmp_path):
        from secure_credential_manager import SecureCredentialManager
        enc = tmp_path / "credentials.enc"
        enc.write_bytes(b"not a valid fernet token")
        m = SecureCredentialManager(enc_path=enc, key=_key())
        # First store backs up the unreadable file once, then writes fresh.
        assert m.store_credential("eth_username", "u") is True
        assert (tmp_path / "credentials.enc.bak").read_bytes() == b"not a valid fernet token"
        assert m.get_credential("eth_username") == "u"


class TestSecureConfigWiring:

    def test_secure_config_now_finds_the_manager(self):
        # The whole point: secure_config's top-level import no longer fails.
        import importlib
        sc = importlib.import_module("core.config.secure_config")
        assert sc.SECURE_CREDENTIALS_AVAILABLE is True
        mgr = sc.SecureConfigManager()
        assert mgr.credential_manager is not None

    def test_setup_credentials_imports(self):
        # setup_credentials.py also imports the manager at top level.
        import importlib
        m = importlib.import_module("core.config.setup_credentials")
        assert hasattr(m, "setup_credentials_programmatic")
