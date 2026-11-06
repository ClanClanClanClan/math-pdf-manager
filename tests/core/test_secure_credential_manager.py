"""Credentials live in this Mac's Keychain, and nothing lives in Dropbox.

The owner's ruling of 2026-11-06 (step-back audit D9-6). Every test runs on
the in-memory keyring tests/conftest.py installs: reaching the real
Keychain from a test raises modal dialogs, which once locked him out.
"""
from __future__ import annotations

import json
from pathlib import Path

import keyring
import pytest
from cryptography.fernet import Fernet
from hypothesis import given, strategies as hst

import secure_credential_manager as M
from secure_credential_manager import SecureCredentialManager
from tests.ui.test_cockpit_renders_content import cockpit, home, lib  # noqa: F401 -- fixtures


@pytest.fixture(autouse=True)
def _clean_keychain():
    store = keyring.get_keyring()._store
    store.clear()
    yield
    store.clear()


def _old_file(path: Path, data: dict, app="academic_papers") -> bytes:
    """The old store as it stands on the owner's Mac."""
    key = Fernet.generate_key()
    keyring.set_password(f"math-pdf-manager:{app}", M._KEYRING_KEY_NAME, key.decode())
    token = Fernet(key).encrypt(json.dumps(data).encode())
    path.write_bytes(token)
    return token


def _mgr(tmp_path):
    return SecureCredentialManager(enc_path=tmp_path / "credentials.enc")


class TestTheKeychainIsTheStore:

    def test_round_trip_touches_no_file(self, tmp_path):
        m = _mgr(tmp_path)
        assert m.store_credential("eth_password", "s3cr3t") is True
        assert m.get_credential("eth_password") == "s3cr3t"
        assert list(tmp_path.iterdir()) == [], "a credential reached a file"

    def test_a_fresh_instance_reads_it_back(self, tmp_path):
        _mgr(tmp_path).store_credential("eth_username", "u")
        assert _mgr(tmp_path).get_credential("eth_username") == "u"

    def test_store_credentials_and_delete(self, tmp_path):
        m = _mgr(tmp_path)
        assert m.store_credentials({"eth_username": "u", "eth_password": "p"}) is True
        m.delete_credential("eth_password")
        assert m.get_credential("eth_password") is None
        assert m.get_credential("eth_username") == "u"

    def test_deleting_what_is_not_there_is_fine(self, tmp_path):
        keyring.get_keyring().delete_password = _raises_not_found
        try:
            assert _mgr(tmp_path).delete_credential("nope") is True
        finally:
            del keyring.get_keyring().delete_password

    def test_missing_credential_returns_none(self, tmp_path):
        assert _mgr(tmp_path).get_credential("nope") is None

    def test_a_keychain_that_refuses_says_so(self, tmp_path, monkeypatch):
        def _no(*a):
            raise RuntimeError("no keychain in this session")
        monkeypatch.setattr(keyring, "set_password", _no)
        m = _mgr(tmp_path)
        assert m.store_credential("eth_password", "p") is False
        assert m.store_credentials({"a": "1", "b": "2"}) is False

    def test_the_old_file_lives_on_this_mac_not_in_dropbox(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        assert M.legacy_store_path() == tmp_path / ".mathpdf" / "credentials.enc"


def _raises_not_found(*a):
    from keyring.errors import PasswordDeleteError
    raise PasswordDeleteError("not found")


class TestUntilHePresses:

    def test_the_old_file_still_answers(self, tmp_path):
        _old_file(tmp_path / "credentials.enc", {"eth_username": "u"})
        assert _mgr(tmp_path).get_credential("eth_username") == "u"

    def test_a_new_value_goes_to_the_keychain_and_wins(self, tmp_path):
        token = _old_file(tmp_path / "credentials.enc", {"eth_username": "old"})
        m = _mgr(tmp_path)
        m.store_credential("eth_username", "new")
        assert m.get_credential("eth_username") == "new"
        assert (tmp_path / "credentials.enc").read_bytes() == token

    def test_the_borrowed_logins_are_not_served_from_it(self, tmp_path):
        _old_file(tmp_path / "credentials.enc", {M._BORROWED_LOGINS: "[cookies]"})
        assert _mgr(tmp_path).get_credential(M._BORROWED_LOGINS) is None

    def test_clearing_reaches_the_old_file_too(self, tmp_path):
        _old_file(tmp_path / "credentials.enc", {"eth_password": "p", "eth_username": "u"})
        m = _mgr(tmp_path)
        m.delete_credential("eth_password")
        assert m.get_credential("eth_password") is None
        assert m.get_credential("eth_username") == "u"

    def test_an_unreadable_old_file_reads_as_nothing_and_is_left(self, tmp_path):
        enc = tmp_path / "credentials.enc"
        enc.write_bytes(b"not a valid fernet token")
        m = _mgr(tmp_path)
        assert m.get_credential("x") is None
        assert enc.read_bytes() == b"not a valid fernet token"

    def test_the_constant_is_the_one_the_downloader_uses(self):
        from downloader import browser_session
        assert M._BORROWED_LOGINS == browser_session._CACHE_KEY


class TestThePress:

    def test_moves_reads_back_and_deletes_the_file_and_key(self, tmp_path):
        enc = tmp_path / "credentials.enc"
        _old_file(enc, {"eth_username": "u", "eth_password": "p",
                        M._BORROWED_LOGINS: "[cookies]"})
        (tmp_path / "credentials.enc.bak").write_bytes(b"older")
        m = _mgr(tmp_path)
        assert m.move_to_keychain() == {
            "moved": ["eth_password", "eth_username"],
            "dropped": [M._BORROWED_LOGINS], "problem": ""}
        assert not enc.exists() and not (tmp_path / "credentials.enc.bak").exists()
        assert m.get_credential("eth_password") == "p"
        assert m.get_credential(M._BORROWED_LOGINS) is None
        assert keyring.get_password(m.service, M._KEYRING_KEY_NAME) is None
        assert m.has_old_file() is False

    def test_a_second_press_is_harmless(self, tmp_path):
        _old_file(tmp_path / "credentials.enc", {"eth_username": "u"})
        m = _mgr(tmp_path)
        m.move_to_keychain()
        assert m.move_to_keychain() == {"moved": [], "dropped": [], "problem": ""}
        assert m.get_credential("eth_username") == "u"

    def test_an_unreadable_file_is_left_and_he_is_told(self, tmp_path):
        enc = tmp_path / "credentials.enc"
        enc.write_bytes(b"not a valid fernet token")
        out = _mgr(tmp_path).move_to_keychain()
        assert out["moved"] == [] and "could not be read" in out["problem"]
        assert enc.read_bytes() == b"not a valid fernet token"

    def test_a_store_that_is_not_a_dict_counts_as_unreadable(self, tmp_path):
        key = Fernet.generate_key()
        keyring.set_password("math-pdf-manager:academic_papers", M._KEYRING_KEY_NAME, key.decode())
        enc = tmp_path / "credentials.enc"
        enc.write_bytes(Fernet(key).encrypt(b"[1, 2]"))
        assert "could not be read" in _mgr(tmp_path).move_to_keychain()["problem"]
        assert enc.exists()

    @pytest.mark.parametrize("failure", ["raises", "loses it"])
    def test_a_keychain_that_does_not_keep_it_leaves_the_file(self, tmp_path, monkeypatch, failure):
        enc = tmp_path / "credentials.enc"
        token = _old_file(enc, {"eth_password": "p"})
        real_get = keyring.get_password

        def _no(*a):
            raise RuntimeError("refused")

        monkeypatch.setattr(keyring, "set_password",
                            _no if failure == "raises" else lambda *a: None)
        out = _mgr(tmp_path).move_to_keychain()
        assert out["moved"] == [] and "did not keep eth_password" in out["problem"]
        assert enc.read_bytes() == token, "the only copy must survive"
        assert real_get("math-pdf-manager:academic_papers", M._KEYRING_KEY_NAME)

    def test_no_value_ever_reaches_the_log(self, tmp_path, caplog, monkeypatch):
        import logging
        caplog.set_level(logging.DEBUG)
        _old_file(tmp_path / "credentials.enc", {"eth_password": "s3cr3t-value"})
        monkeypatch.setattr(keyring, "set_password",
                            lambda *a: (_ for _ in ()).throw(RuntimeError("s3cr3t-value")))
        _mgr(tmp_path).move_to_keychain()
        assert "s3cr3t-value" not in caplog.text


@given(hst.dictionaries(hst.text(min_size=1, max_size=8).filter(lambda k: k != M._KEYRING_KEY_NAME),
                        hst.text(max_size=8), max_size=5))
def test_property_the_press_loses_nothing_but_the_borrowed_logins(tmp_path_factory, data):
    d = tmp_path_factory.mktemp("c")
    keyring.get_keyring()._store.clear()
    _old_file(d / "credentials.enc", data)
    m = _mgr(d)
    out = m.move_to_keychain()
    assert out["problem"] == ""
    for name, value in data.items():
        if name == M._BORROWED_LOGINS:
            assert m.get_credential(name) is None
        else:
            assert m.get_credential(name) == value


class TestSecureConfigWiring:

    def test_secure_config_now_finds_the_manager(self):
        import importlib
        sc = importlib.import_module("core.config.secure_config")
        assert sc.SECURE_CREDENTIALS_AVAILABLE is True
        assert sc.SecureConfigManager().credential_manager is not None


class TestThePasswordIsTypedOnEthsPageOnly:
    """Step-back audit D9-6: ``"aai-logon.ethz.ch" in page.url`` read the
    whole address, so a page carrying that string in a parameter got his
    password."""

    @pytest.mark.parametrize("url,ok", [
        ("https://aai-logon.ethz.ch/idp/profile/SAML2/Redirect/SSO", True),
        ("https://AAI-LOGON.ETHZ.CH/idp", True),
        ("https://aai-logon.ethz.ch:443/idp", True),
        ("http://aai-logon.ethz.ch/idp", False),
        ("https://evil.example/?entityID=https://aai-logon.ethz.ch", False),
        ("https://evil.example/aai-logon.ethz.ch/login", False),
        ("https://aai-logon.ethz.ch.evil.example/idp", False),
        ("https://aai-logon.ethz.ch@evil.example/idp", False),
        ("https://evil-aai-logon.ethz.ch/idp", False),
        ("", False),
        ("not a url", False),
        ("https://[bad", False),
    ])
    def test_the_host_exactly_over_https(self, url, ok):
        from downloader.eth_institutional import is_eth_login
        assert is_eth_login(url) is ok

    def test_the_form_is_not_touched_elsewhere(self):
        import asyncio
        from downloader.eth_institutional import _eth_shibboleth_login

        class _Page:
            url = "https://evil.example/?entityID=https://aai-logon.ethz.ch"

            async def query_selector(self, *_):
                pytest.fail("looked for a password field on someone else's page")

        assert asyncio.run(_eth_shibboleth_login(_Page(), "u", "p")) is False

    def test_no_substring_test_of_the_address_survives(self):
        import re
        root = Path(M.__file__).resolve().parent / "downloader"
        for name in ("eth_institutional.py", "cloudflare_session.py"):
            text = (root / name).read_text(encoding="utf-8")
            assert not re.search(r'"aai-logon[^"]*"\s+(not\s+)?in\s+', text), name


class TestTheSettingsPage:

    def _page(self, tmp_path, monkeypatch, cockpit, *, press=False):
        from tests.ui.test_cockpit_renders_content import rendered_text
        m = _mgr(tmp_path)
        monkeypatch.setattr(M, "get_credential_manager", lambda: m)
        monkeypatch.setattr(cockpit.st, "rerun", lambda: None, raising=False)
        if press:
            cockpit.st.values["eth_to_keychain"] = True
        cockpit.st.calls.clear()
        cockpit._render_move_to_keychain()
        return m, rendered_text(cockpit.st)

    def test_with_the_old_file_it_offers_the_press_and_warns_of_the_dialog(
            self, tmp_path, monkeypatch, cockpit):
        _old_file(tmp_path / "credentials.enc", {"eth_username": "u"})
        m, text = self._page(tmp_path, monkeypatch, cockpit)
        assert "Always Allow" in text and "Move my ETH login" in text
        assert m.has_old_file(), "nothing moves until he presses"

    def test_the_press_moves_it(self, tmp_path, monkeypatch, cockpit):
        _old_file(tmp_path / "credentials.enc", {"eth_username": "u"})
        m, _ = self._page(tmp_path, monkeypatch, cockpit, press=True)
        assert not m.has_old_file() and m.get_credential("eth_username") == "u"

    def test_a_failed_press_says_so(self, tmp_path, monkeypatch, cockpit):
        (tmp_path / "credentials.enc").write_bytes(b"not a valid fernet token")
        said = []
        monkeypatch.setattr(cockpit, "_flash", lambda kind, msg: said.append((kind, msg)))
        self._page(tmp_path, monkeypatch, cockpit, press=True)
        assert said and said[0][0] == "error" and "could not be read" in said[0][1]

    def test_with_no_old_file_it_says_nothing(self, tmp_path, monkeypatch, cockpit):
        _, text = self._page(tmp_path, monkeypatch, cockpit)
        assert "Move my ETH login" not in text
