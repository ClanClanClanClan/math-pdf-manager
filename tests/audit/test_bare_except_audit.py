#!/usr/bin/env python3
"""
Audit tests for bare except clauses (Batch 3).
Uses AST scanning to verify zero bare `except:` handlers in src/.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _py_files(directory: Path):
    for p in directory.rglob("*.py"):
        yield p


class TestNoBareExcepts:
    """AST-based scan asserting zero bare except handlers."""

    def test_no_bare_except_in_src(self):
        """Every ExceptHandler node must have .type set (not None)."""
        violations = []
        for py in _py_files(SRC):
            try:
                text = py.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text, filename=str(py))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    rel = py.relative_to(ROOT)
                    violations.append(f"{rel}:{node.lineno}")

        assert not violations, (
            "Bare `except:` handlers found in src/:\n"
            + "\n".join(violations)
        )
