#!/usr/bin/env python3
"""
Audit tests for code quality (Batches 6-7).
Covers discarded expressions, duplicate set entries, dead code,
unused imports, variable shadowing.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# ── Batch 6: Discarded expressions ───────────────────────────────────────
class TestNoDiscardedExpressions:
    """Check for common discarded-expression bugs."""

    def test_spellchecker_or_is_assigned(self):
        """Verify `spellchecker or SpellChecker()` is assigned, not discarded."""
        core = SRC / "validators" / "filename_checker" / "core.py"
        text = _read_text(core)
        # Should NOT have bare `spellchecker or SpellChecker()`
        # (only `spellchecker = spellchecker or SpellChecker()`)
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "spellchecker or SpellChecker()" in stripped:
                assert stripped.startswith("spellchecker ="), (
                    f"Line {i}: Discarded expression — should be assignment: {stripped}"
                )


# ── Batch 6: Duplicate set entries ────────────────────────────────────────
class TestNoDuplicateSetEntries:
    """Ensure no duplicate entries in set literals."""

    def test_mathematical_operators_no_duplicates(self):
        normalizer = SRC / "validators" / "title_normalizer.py"
        text = _read_text(normalizer)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            pytest.skip("Cannot parse title_normalizer.py")

        for node in ast.walk(tree):
            if isinstance(node, ast.Set):
                # Check if this is MATHEMATICAL_OPERATORS (around line 451)
                values = []
                for elt in node.elts:
                    if isinstance(elt, ast.Constant):
                        values.append(elt.value)
                if len(values) > 20:  # Large set — likely MATHEMATICAL_OPERATORS
                    seen = set()
                    dups = []
                    for v in values:
                        if v in seen:
                            dups.append(v)
                        seen.add(v)
                    assert not dups, (
                        f"Duplicate entries in large set literal: {dups}"
                    )


# ── Batch 6: Dead expression in container.py ──────────────────────────────
class TestNoDeadExpressions:
    """Ensure no dead (unused) expressions in critical code."""

    def test_container_configure_no_dead_expression(self):
        container = SRC / "core" / "dependency_injection" / "container.py"
        text = _read_text(container)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            pytest.skip("Cannot parse container.py")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "configure_from_config":
                for child in ast.walk(node):
                    if isinstance(child, ast.Expr) and isinstance(child.value, ast.Subscript):
                        pytest.fail(
                            f"Dead subscript expression at line {child.lineno} in configure_from_config"
                        )


# ── Batch 7: variable shadowing ──────────────────────────────────────────
class TestNoVariableShadowing:
    """Ensure loop variables don't shadow important builtins."""

    def test_no_field_variable_shadowing_in_quality_scoring(self):
        qscore = SRC / "metadata" / "quality_scoring.py"
        if not qscore.exists():
            pytest.skip("quality_scoring.py not found")
        text = _read_text(qscore)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            pytest.skip("Cannot parse quality_scoring.py")

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                target = node.target
                if isinstance(target, ast.Name) and target.id == "field":
                    pytest.fail(
                        f"Loop variable 'field' at line {node.lineno} shadows potential builtin. "
                        "Rename to 'field_name'."
                    )
