"""
Round 3 Audit Tests
===================
Regression tests for Round 3 findings:
- No ast.literal_eval on data (use json.loads instead)
- No redundant import re inside functions
- No f-strings without placeholders
- NameError guard on tmp_file in security utils
"""

import ast
import os
import textwrap
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"


class TestNoAstLiteralEval:
    """ast.literal_eval should not be used to parse data — use json.loads."""

    # Files where ast.literal_eval is acceptable (test utilities, etc.)
    ALLOWED = {"tests/"}

    def test_no_ast_literal_eval_in_src(self):
        violations = []
        for py in SRC.rglob("*.py"):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "literal_eval"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "ast"
                ):
                    rel = py.relative_to(SRC.parent)
                    violations.append(f"{rel}:{node.lineno}")
        assert violations == [], (
            f"ast.literal_eval found (use json.loads instead): {violations}"
        )


class TestNoRedundantImportRe:
    """import re should not appear inside functions when already at module level."""

    def test_no_inner_import_re_when_module_level(self):
        violations = []
        for py in SRC.rglob("*.py"):
            try:
                source = py.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except SyntaxError:
                continue

            # Check if re is imported at module level
            has_module_level_re = False
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "re":
                            has_module_level_re = True
                elif isinstance(node, ast.ImportFrom) and node.module == "re":
                    has_module_level_re = True

            if not has_module_level_re:
                continue

            # Now check for inner imports of re
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Import):
                            for alias in child.names:
                                if alias.name == "re":
                                    rel = py.relative_to(SRC.parent)
                                    violations.append(f"{rel}:{child.lineno}")

        assert violations == [], (
            f"Redundant 'import re' inside functions (already at module level): {violations}"
        )


class TestNoFStringsWithoutPlaceholders:
    """f-strings should contain at least one {…} placeholder."""

    @staticmethod
    def _collect_format_spec_ids(tree):
        """Collect ids of JoinedStr nodes used as format_spec (not real f-strings)."""
        spec_ids = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FormattedValue) and node.format_spec is not None:
                spec_ids.add(id(node.format_spec))
        return spec_ids

    def test_no_empty_fstrings_in_src(self):
        violations = []
        for py in SRC.rglob("*.py"):
            rel = str(py.relative_to(SRC.parent))
            try:
                tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            format_spec_ids = self._collect_format_spec_ids(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.JoinedStr) and id(node) not in format_spec_ids:
                    if len(node.values) == 1 and isinstance(node.values[0], ast.Constant):
                        violations.append(f"{rel}:{node.lineno}")
        assert violations == [], (
            f"f-strings without placeholders (remove f prefix): {violations}"
        )


class TestTmpFileNameErrorGuard:
    """utils/security.py must guard tmp_file cleanup against NameError."""

    def test_tmp_file_initialized_before_try(self):
        security_py = SRC / "utils" / "security.py"
        if not security_py.exists():
            return  # Skip if file doesn't exist
        source = security_py.read_text(encoding="utf-8", errors="replace")
        # The fix is: tmp_file = None appears before the try block
        assert "tmp_file = None" in source, (
            "tmp_file should be initialized to None before the try block "
            "to prevent NameError in the finally clause"
        )


class TestNoMutableDefaultArguments:
    """Function defaults must not be mutable (list, dict, set)."""

    MUTABLE_TYPES = (ast.List, ast.Dict, ast.Set)

    def test_no_mutable_defaults_in_src(self):
        violations = []
        for py in SRC.rglob("*.py"):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for default in node.args.defaults + node.args.kw_defaults:
                        if default is not None and isinstance(default, self.MUTABLE_TYPES):
                            rel = py.relative_to(SRC.parent)
                            violations.append(f"{rel}:{default.lineno} - {node.name}()")
        assert violations == [], (
            f"Mutable default arguments found (use None + init inside body): {violations}"
        )
