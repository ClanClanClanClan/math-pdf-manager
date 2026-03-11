#!/usr/bin/env python3
"""
Audit tests for import hygiene (Batch 5).
Verifies no builtin shadowing, no sys.path hacks in production code.
"""

import ast
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


class TestNoBuiltinShadowing:
    """Ensure no class shadows Python builtins."""

    SHADOWED_BUILTINS = {"TimeoutError", "ConnectionError", "PermissionError"}

    def test_no_class_named_TimeoutError_in_src(self):
        """Custom class should not shadow builtin TimeoutError."""
        violations = []
        for py in _py_files(SRC):
            try:
                text = py.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text, filename=str(py))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "TimeoutError":
                    rel = py.relative_to(ROOT)
                    violations.append(f"{rel}:{node.lineno}")
        assert not violations, (
            "Class 'TimeoutError' shadows Python builtin:\n"
            + "\n".join(violations)
        )


class TestNoSysPathHacks:
    """Ensure no sys.path.insert/append in production src/ modules."""

    # Allowed files that legitimately need sys.path manipulation
    ALLOWED = {
        "src/__init__.py",                          # Package root needs path setup
        "src/utils/__init__.py",                    # Utils package root
        "src/validators/manual_validation.py",      # Standalone validation script
        "src/core/utils/check_python.py",           # Standalone utility
        "src/core/config/migrate_insecure_config.py",  # Migration script
        "src/pdf_processing/parsers/enhanced_parser.py",  # Parser with grobid deps
    }

    def test_no_sys_path_manipulation_in_src(self):
        """Scan for sys.path.insert/append outside of allowed files."""
        violations = []
        for py in _py_files(SRC):
            rel = str(py.relative_to(ROOT))
            if rel in self.ALLOWED:
                continue
            text = _read_text(py)
            for i, line in enumerate(text.splitlines(), 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if re.search(r"sys\.path\.(insert|append)\s*\(", stripped):
                    violations.append(f"{rel}:{i}: {stripped[:80]}")
        assert not violations, (
            "sys.path manipulation found in src/ modules:\n"
            + "\n".join(violations)
        )
