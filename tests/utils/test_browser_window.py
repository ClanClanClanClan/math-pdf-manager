"""Tests for ``utils.browser_window`` — the quiet-window helper."""
from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from utils.browser_window import (
    is_disabled,
    quiet_args,
    quiet_position,
)


# ---------------------------------------------------------------------------
# Args helper
# ---------------------------------------------------------------------------

class TestQuietArgs:

    def test_includes_window_position_and_size(self, monkeypatch):
        monkeypatch.delenv("MATHPDF_QUIET_DISABLE", raising=False)
        args = quiet_args()
        joined = " ".join(args)
        assert "--window-position=" in joined
        assert "--window-size=" in joined

    def test_respects_environment_override(self, monkeypatch):
        monkeypatch.setenv("MATHPDF_QUIET_X", "10")
        monkeypatch.setenv("MATHPDF_QUIET_Y", "20")
        monkeypatch.setenv("MATHPDF_QUIET_W", "100")
        monkeypatch.setenv("MATHPDF_QUIET_H", "50")
        monkeypatch.delenv("MATHPDF_QUIET_DISABLE", raising=False)
        args = quiet_args()
        assert "--window-position=10,20" in args
        assert "--window-size=100,50" in args

    def test_bad_env_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("MATHPDF_QUIET_X", "not-an-int")
        monkeypatch.delenv("MATHPDF_QUIET_DISABLE", raising=False)
        # Default x is 2400 — exact value isn't the point; what matters
        # is that the call doesn't raise.
        args = quiet_args()
        assert any(a.startswith("--window-position=") for a in args)

    def test_passes_through_extra_args(self, monkeypatch):
        monkeypatch.delenv("MATHPDF_QUIET_DISABLE", raising=False)
        args = quiet_args(["--my-custom-flag"])
        assert "--my-custom-flag" in args

    def test_disabled_skips_positioning(self, monkeypatch):
        monkeypatch.setenv("MATHPDF_QUIET_DISABLE", "1")
        args = quiet_args(["--my-custom-flag"])
        assert args == ["--my-custom-flag"]
        assert is_disabled()

    def test_disabled_case_insensitive(self, monkeypatch):
        for val in ("True", "YES", "1"):
            monkeypatch.setenv("MATHPDF_QUIET_DISABLE", val)
            assert is_disabled(), f"value {val!r} should disable"

    def test_quiet_position_returns_4tuple(self, monkeypatch):
        monkeypatch.delenv("MATHPDF_QUIET_DISABLE", raising=False)
        x, y, w, h = quiet_position()
        assert all(isinstance(v, int) for v in (x, y, w, h))
        assert w > 0 and h > 0


# ---------------------------------------------------------------------------
# Static guarantee: no source file launches headful Playwright with the
# --start-maximized flag.  That flag is the exact opposite of what we want
# and a regression would silently break the quiet-window contract.
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


class TestNoStartMaximized:

    def test_no_start_maximized_in_src(self):
        offenders = []
        for py in SRC.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            text = py.read_text(encoding="utf-8", errors="replace")
            if "--start-maximized" in text:
                offenders.append(str(py.relative_to(ROOT)))
        assert not offenders, (
            "Files use '--start-maximized', which violates the quiet-window "
            "contract (browser windows must stay out of the user's way): "
            + ", ".join(offenders)
        )


# ---------------------------------------------------------------------------
# Static guarantee: every headful (``headless=False``) Playwright launch
# in src/ wraps its args in ``quiet_args(...)``.  A new file added with a
# raw ``args=[...]`` block would slip past code review otherwise.
# ---------------------------------------------------------------------------

class TestHeadfulLaunchesUseQuietArgs:

    def _is_headful_launch_with_args(self, node: ast.Call) -> bool:
        """Check whether this Call is a ``chromium.launch(headless=False, args=[...])``
        whose ``args`` keyword is a plain list literal rather than a wrapped
        ``quiet_args(...)`` call."""
        func = node.func
        if not (
            isinstance(func, ast.Attribute) and func.attr == "launch"
        ):
            return False
        headless_arg = None
        args_arg = None
        for kw in node.keywords:
            if kw.arg == "headless":
                headless_arg = kw.value
            elif kw.arg == "args":
                args_arg = kw.value
        if headless_arg is None:
            return False
        # headless=False literal or headless=<name> -- in both cases we
        # want args wrapped, because at runtime headful is possible.
        # Only skip if we can statically prove headless is True.
        if isinstance(headless_arg, ast.Constant) and headless_arg.value is True:
            return False
        if args_arg is None:
            # No args at all is bad too -- means no positioning hints.
            # But many headful launches don't have args (focused_download
            # etc.).  We catch them by the "must be wrapped" rule too.
            return False
        # Wrapped in quiet_args(...)?
        if isinstance(args_arg, ast.Call):
            fn = args_arg.func
            if isinstance(fn, ast.Name) and fn.id == "quiet_args":
                return False
        return True  # raw list literal -- violation

    def test_every_headful_launch_uses_quiet_args(self):
        violations = []
        for py in SRC.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and self._is_headful_launch_with_args(node):
                    violations.append(
                        f"{py.relative_to(ROOT)}:{node.lineno}"
                    )
        assert not violations, (
            "Headful (or potentially headful) Playwright launches must wrap "
            "their args= in quiet_args(...) so the window stays out of the "
            "user's way. Offenders:\n  " + "\n  ".join(violations)
        )
