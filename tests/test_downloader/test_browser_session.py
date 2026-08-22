"""Browser-session cookie import — pure unit tests.

No network, no real Keychain, no real Chrome: we build a synthetic Chrome
profile tree (MATHPDF_CHROME_BASE) with a SQLite cookie DB whose values are
encrypted with a test key, and inject that key into ``load_cookies``.
"""
from __future__ import annotations

import sqlite3
import time

import pytest


# ---- helpers --------------------------------------------------------------

def _test_key() -> bytes:
    from downloader.browser_session import derive_key
    return derive_key(b"unit-test-pw")


def _v10(value: str, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import (
        Cipher, algorithms, modes)
    data = value.encode("utf-8")
    pad = 16 - (len(data) % 16)
    data += bytes([pad]) * pad
    enc = Cipher(algorithms.AES(key), modes.CBC(b" " * 16)).encryptor()
    return b"v10" + enc.update(data) + enc.finalize()


def _make_profile(base, profile_name, rows):
    """rows: list of (host, name, value, path, expires_utc, secure, httponly, samesite)."""
    pdir = base / profile_name
    pdir.mkdir(parents=True, exist_ok=True)
    db = pdir / "Cookies"
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, encrypted_value BLOB, "
        "path TEXT, expires_utc INTEGER, is_secure INTEGER, is_httponly INTEGER, "
        "samesite INTEGER)"
    )
    key = _test_key()
    for host, name, value, path, exp, sec, http, ss in rows:
        con.execute(
            "INSERT INTO cookies VALUES (?,?,?,?,?,?,?,?)",
            (host, name, _v10(value, key), path, exp, sec, http, ss),
        )
    con.commit()
    con.close()
    return db


# ---- crypto ---------------------------------------------------------------

class TestDecrypt:
    def test_round_trip(self):
        from downloader.browser_session import _decrypt
        key = _test_key()
        assert _decrypt(_v10("sim-inst-token-abc123", key), key) == "sim-inst-token-abc123"

    def test_non_v10_returns_none(self):
        from downloader.browser_session import _decrypt
        assert _decrypt(b"plainvalue", _test_key()) is None
        assert _decrypt(b"", _test_key()) is None


class TestAllowlist:
    @pytest.mark.parametrize("host,ok", [
        (".springer.com", True),
        ("link.springer.com", True),
        ("onlinelibrary.wiley.com", True),
        ("epubs.siam.org", True),
        ("mail.google.com", False),
        ("chase.com", False),
        ("notspringer.evil.com", False),
        # Bare-suffix bypass: attacker-registrable look-alikes must NOT pass.
        ("notspringer.com", False),
        ("evil-wiley.com", False),
        ("evilspringer.com", False),
        ("xjstor.org", False),
        ("myaps.org", False),
        ("badacm.org", False),
        # …but genuine subdomains and exact matches still must.
        (".springer.com", True),
        ("epubs.siam.org", True),
        ("journals.aps.org", True),
    ])
    def test_host_allowed(self, host, ok):
        from downloader.browser_session import _host_allowed
        assert _host_allowed(host) is ok


# ---- profile scan + load --------------------------------------------------

class TestScanAndLoad:
    def _setup(self, tmp_path, monkeypatch):
        base = tmp_path / "Chrome"
        rows = [
            (".springer.com", "sim-inst-token", "TOK", "/", 0, 1, 1, 2),
            # expires_utc is microseconds since 1601; 1.6e16 ≈ year 2108.
            (".springer.com", "idp_session", "SESS", "/", 16000000000000000, 1, 0, 1),
            ("mail.google.com", "SID", "secret", "/", 0, 1, 1, 0),  # must be ignored
        ]
        _make_profile(base, "Profile 1", rows)
        # a profile with no publisher cookies
        _make_profile(base, "Default", [("example.com", "x", "y", "/", 0, 0, 0, 0)])
        monkeypatch.setenv("MATHPDF_CHROME_BASE", str(base))
        return base

    def test_scan_only_publisher_cookies(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        from downloader import browser_session as bs
        scans = bs.scan_profiles()
        by = {s.profile: s for s in scans}
        assert "Profile 1" in by
        assert by["Profile 1"].cookie_count == 2          # google cookie excluded
        assert "Default" not in by                          # no publisher cookies
        assert "sim-inst-token" in by["Profile 1"].names

    def test_auto_detect_picks_richest(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        from downloader import browser_session as bs
        assert bs.auto_detect_profile() == "Profile 1"

    def test_load_cookies_decrypts_and_scopes(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        from downloader import browser_session as bs
        cookies = bs.load_cookies("Profile 1", key=_test_key())
        names = {c["name"]: c for c in cookies}
        assert set(names) == {"sim-inst-token", "idp_session"}   # google excluded
        tok = names["sim-inst-token"]
        assert tok["value"] == "TOK"
        assert tok["domain"] == ".springer.com"
        assert tok["secure"] is True and tok["httpOnly"] is True
        assert tok["sameSite"] == "Strict"
        assert "expires" not in tok                              # session cookie (0)
        # expiry conversion (1601-epoch microseconds) -> a future unix time
        assert names["idp_session"]["expires"] > time.time()
        assert names["idp_session"]["sameSite"] == "Lax"

    def test_load_cookies_missing_profile(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        from downloader import browser_session as bs
        assert bs.load_cookies("Profile 99", key=_test_key()) == []


# ---- encrypted cache ------------------------------------------------------

class TestCache:
    def _store(self, tmp_path):
        from cryptography.fernet import Fernet
        from secure_credential_manager import SecureCredentialManager
        return SecureCredentialManager(enc_path=tmp_path / "c.enc", key=Fernet.generate_key())

    def test_round_trip(self, tmp_path, monkeypatch):
        from downloader import browser_session as bs
        store = self._store(tmp_path)
        monkeypatch.setattr(bs, "_store", lambda: store)
        cookies = [{"name": "sim-inst-token", "value": "TOK", "domain": ".springer.com",
                    "path": "/", "secure": True, "httpOnly": True}]
        assert bs.save_cached(cookies, "Profile 1") is True
        got = bs.load_cached()
        assert got["profile"] == "Profile 1"
        assert got["cookies"][0]["name"] == "sim-inst-token"
        assert got["captured_at"] > 0
        bs.clear_cached()
        assert bs.load_cached() is None

    def test_cookies_for_download_uses_cache(self, tmp_path, monkeypatch):
        from downloader import browser_session as bs
        store = self._store(tmp_path)
        monkeypatch.setattr(bs, "_store", lambda: store)
        bs.save_cached([{"name": "a", "value": "b", "domain": ".springer.com", "path": "/"}],
                       "Profile 1")
        out = bs.cookies_for_download(allow_import=False)
        assert out and out[0]["name"] == "a"


class TestTheKeyScheduleMatchesChrome:
    """Known-answer vectors, because the rest of this file is a closed loop.

    Every other test here encrypts with the same library the code
    decrypts with, so it would pass just as happily if the parameters
    were wrong — a different salt, a different iteration count, SHA-256
    instead of SHA-1 — and cookie import would then silently fail
    against real Chrome while the suite stayed green.

    These hex values pin Chrome's actual macOS schedule:
    PBKDF2-HMAC-SHA1, salt b"saltysalt", 1003 iterations, 16-byte key.
    "peanuts" is Chrome's documented fallback password when the Keychain
    entry is absent, so it is a vector anyone can check against the
    Chromium source.
    """

    def test_the_derived_key_is_the_expected_bytes(self):
        from downloader.browser_session import derive_key
        assert derive_key(b"unit-test-pw").hex() == \
            "42f1c1d3e55683e3d7d88cd582f391a1"
        assert derive_key(b"peanuts").hex() == \
            "d9a09d499b4e1b7461f28e67972c6dbd"

    def test_the_key_is_128_bit(self):
        from downloader.browser_session import derive_key
        assert len(derive_key(b"anything")) == 16

    def test_a_truncated_value_is_declined_not_crashed(self):
        """AES-CBC needs whole blocks. Chrome's DB can hold a partially
        written blob; returning None beats raising inside a loop over
        every cookie."""
        from downloader.browser_session import _decrypt
        assert _decrypt(b"v10" + b"\x00" * 5, _test_key()) is None
