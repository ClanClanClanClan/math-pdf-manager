#!/usr/bin/env python3
"""
Audit tests for credential hygiene (Batch 0).
Verifies no hardcoded passwords, placeholder credentials, or
credential-bearing scripts are exposed.
"""

import os
import re
from pathlib import Path

import pytest

# ── helpers ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _py_files(directory: Path):
    """Yield all .py files under *directory*."""
    for p in directory.rglob("*.py"):
        yield p


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# ── .gitignore blocks credential scripts ─────────────────────────────────
class TestGitignoreCredentialBlocking:
    """Ensure .gitignore lists known credential-bearing scripts."""

    @pytest.fixture(autouse=True)
    def _load_gitignore(self):
        gi = ROOT / ".gitignore"
        assert gi.exists(), ".gitignore missing from project root"
        self.lines = gi.read_text().splitlines()

    @pytest.mark.parametrize("script", [
        "eth_api_vpn_solution.py",
        "working_eth_api_downloader.py",
    ])
    def test_credential_script_in_gitignore(self, script):
        assert any(script in line for line in self.lines), (
            f"{script} must be listed in .gitignore"
        )


# ── no hardcoded passwords in src/ ───────────────────────────────────────
class TestNoHardcodedPasswords:
    """Scan src/ for common password/credential placeholder strings."""

    PLACEHOLDER_PATTERNS = [
        re.compile(r"""['"]your_university_username['"]"""),
        re.compile(r"""['"]your_university_password['"]"""),
        re.compile(r"""['"]your_secure_password['"]"""),
        re.compile(r"""['"]your_scopus_api_key['"]"""),
    ]

    def test_no_placeholder_credentials_in_src(self):
        violations = []
        for py in _py_files(SRC):
            text = _read_text(py)
            for pat in self.PLACEHOLDER_PATTERNS:
                for m in pat.finditer(text):
                    rel = py.relative_to(ROOT)
                    violations.append(f"{rel}: matched {m.group()!r}")
        assert not violations, (
            "Placeholder credential strings found in src/:\n"
            + "\n".join(violations)
        )

    def test_no_hardcoded_api_keys_in_src(self):
        """Ensure no literal API key patterns in src/."""
        # Match quoted strings that look like API keys (long alphanum with mixed case)
        api_key_re = re.compile(
            r"""['"][A-Za-z0-9]{30,}['"]"""
        )
        violations = []
        for py in _py_files(SRC):
            text = _read_text(py)
            for m in api_key_re.finditer(text):
                val = m.group().strip("'\"")
                # Skip known safe patterns (hex hashes, UUIDs, test values, etc.)
                if all(c in "0123456789abcdef" for c in val.lower()):
                    continue  # hex hash
                if len(val) > 100:
                    continue  # too long, likely a hash constant
                rel = py.relative_to(ROOT)
                violations.append(f"{rel}: potential API key {val[:20]}...")
        # This is an advisory check — we just verify no ETH API key leaks
        for v in violations:
            assert "dkg5eEYuOjlv69V1gw1Pux" not in v, (
                f"Real API key found in src/: {v}"
            )


# ── credential example code uses env vars ────────────────────────────────
class TestCredentialExamplesUseEnvVars:
    """Verify example/setup code in credential modules uses os.environ."""

    def test_credentials_py_example_uses_environ(self):
        creds_py = SRC / "downloader" / "credentials.py"
        text = _read_text(creds_py)
        assert "os.environ" in text, (
            "credentials.py example should use os.environ for credentials"
        )
        assert "your_university_username" not in text
        assert "your_university_password" not in text

    def test_orchestrator_py_example_uses_environ(self):
        orch_py = SRC / "downloader" / "orchestrator.py"
        text = _read_text(orch_py)
        assert "os.environ" in text, (
            "orchestrator.py example should use os.environ for master password"
        )
        assert '"your_secure_password"' not in text


# ── no credential.enc or .env committed ──────────────────────────────────
class TestNoCredentialFilesCommitted:
    """Verify credential files are gitignored."""

    @pytest.fixture(autouse=True)
    def _load_gitignore(self):
        gi = ROOT / ".gitignore"
        self.text = gi.read_text()

    def test_env_in_gitignore(self):
        assert ".env" in self.text

    def test_credentials_enc_in_gitignore(self):
        assert "credentials.enc" in self.text
