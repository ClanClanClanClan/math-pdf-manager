#!/usr/bin/env python3
"""
Audit tests for security and code quality (Batches 1-2).
Covers cryptographic salt hygiene, base64 fallback warnings,
hardcoded paths, and deprecated datetime.utcnow() usage.
"""

import ast
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _py_files(directory: Path):
    for p in directory.rglob("*.py"):
        yield p


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# ── Batch 1: Crypto salt & base64 fallback ────────────────────────────────
class TestCryptoSaltHygiene:
    """Ensure no hardcoded salt literals remain in auth modules.

    The auth/store.py tests have been deleted because the module never
    existed in this codebase (the credential store lives in
    ``src/downloader/credentials.py`` instead, which is tested by
    ``TestInputValidationSecurity.test_credential_encryption_uses_pbkdf2_fernet``
    in tests/audit/test_integration_audit.py).
    """

    def test_no_hardcoded_salt_in_secure_credential_manager(self):
        scm = SRC / "secure_credential_manager.py"
        text = _read_text(scm)
        assert 'b"academic_papers_salt"' not in text, (
            "Hardcoded salt b\"academic_papers_salt\" still in secure_credential_manager.py"
        )
        assert "b'academic_papers_salt'" not in text


# TestBase64FallbackWarning deleted: src/auth/store.py never existed.


# ── Batch 2: Hardcoded paths ──────────────────────────────────────────────
class TestNoHardcodedPaths:
    """Ensure no user-specific paths used as config fallbacks in src/."""

    # Files that legitimately define Dropbox constants for migration features
    ALLOWED_FILES = {
        "src/constants.py",
        "src/file_operations.py",
    }

    def test_no_dropbox_paths_in_src(self):
        violations = []
        for py in _py_files(SRC):
            rel = str(py.relative_to(ROOT))
            if rel in self.ALLOWED_FILES:
                continue
            text = _read_text(py)
            for i, line in enumerate(text.splitlines(), 1):
                if "CloudStorage/Dropbox" in line or "CloudStorage\\Dropbox" in line:
                    violations.append(f"{rel}:{i}: {line.strip()[:100]}")
        assert not violations, (
            "User-specific Dropbox paths found in src/:\n"
            + "\n".join(violations)
        )


# ── Batch 2: datetime.utcnow() ───────────────────────────────────────────
class TestNoDeprecatedDatetime:
    """Ensure no datetime.utcnow() calls remain in src/."""

    def test_no_utcnow_in_src(self):
        violations = []
        # Use AST to find actual calls, not just string matches in comments
        for py in _py_files(SRC):
            text = _read_text(py)
            if "utcnow" not in text:
                continue
            try:
                tree = ast.parse(text, filename=str(py))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    # Match datetime.utcnow()
                    if (isinstance(func, ast.Attribute) and
                        func.attr == "utcnow"):
                        rel = py.relative_to(ROOT)
                        violations.append(f"{rel}:{node.lineno}")
        assert not violations, (
            "Deprecated datetime.utcnow() calls found in src/:\n"
            + "\n".join(violations)
        )
