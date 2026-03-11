#!/usr/bin/env python3
"""
Audit tests for asyncio patterns (Batch 4).
Verifies no deprecated new_event_loop()/set_event_loop() patterns remain.
"""

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


class TestNoDeprecatedAsyncioPatterns:
    """Ensure no deprecated asyncio event loop patterns in src/."""

    # async_compat.py is the replacement — its docstring mentions the old pattern
    ALLOWED = {"src/core/utils/async_compat.py"}

    def test_no_new_event_loop_set_event_loop(self):
        """No new_event_loop() + set_event_loop() pattern in src/ code."""
        violations = []
        for py in _py_files(SRC):
            rel = str(py.relative_to(ROOT))
            if rel in self.ALLOWED:
                continue
            # Strip docstrings/comments to avoid false positives
            text = _read_text(py)
            # Only check actual code lines (skip lines inside triple-quoted strings)
            code_lines = []
            in_docstring = False
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    count = stripped.count('"""') + stripped.count("'''")
                    if count == 1:
                        in_docstring = not in_docstring
                    continue
                if in_docstring:
                    continue
                if stripped.startswith('#'):
                    continue
                code_lines.append(line)
            code_text = "\n".join(code_lines)
            if "new_event_loop()" in code_text and "set_event_loop(" in code_text:
                violations.append(rel)
        assert not violations, (
            "Deprecated new_event_loop()/set_event_loop() pattern found in:\n"
            + "\n".join(violations)
        )


class TestRunSyncHelper:
    """Verify the run_sync helper exists and is correct."""

    def test_async_compat_module_exists(self):
        compat = SRC / "core" / "utils" / "async_compat.py"
        assert compat.exists(), "src/core/utils/async_compat.py must exist"

    def test_run_sync_exported(self):
        compat = SRC / "core" / "utils" / "async_compat.py"
        text = _read_text(compat)
        assert "def run_sync" in text, "async_compat.py must define run_sync()"
