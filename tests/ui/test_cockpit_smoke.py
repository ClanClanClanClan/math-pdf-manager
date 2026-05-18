"""Smoke tests for ``src/ui/cockpit.py``.

Streamlit's ``streamlit run`` is the normal entry point but it's not
hermetic enough for CI.  These tests stub the ``st`` module with a
recording mock and invoke each ``render_*`` function directly so any
``NameError``/``AttributeError`` (e.g. calling a function that doesn't
exist) blows up the test rather than waiting for the user to click the
tab.

This is what would have caught the ``_library_root()`` bug shipped in
Phase 1: the typo never executed under pytest until we drove the page
manually.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Streamlit stub: every attribute returns a MagicMock so chained calls
# like st.columns([0.7, 0.3])[0].markdown(...) just work.
# ---------------------------------------------------------------------------

class _SessionState(dict):
    """``streamlit.session_state`` supports both attribute and item access."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
    def __setattr__(self, name, value):
        self[name] = value
    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


class _StreamlitModule(types.ModuleType):
    """Catch-all streamlit stub: unknown attrs return no-op callables."""
    def __init__(self):
        super().__init__("streamlit")
        self.session_state = _SessionState()

    def cache_data(self, *args, **kwargs):
        # Behaves both as ``@st.cache_data`` (no args) and ``@st.cache_data(ttl=60)``.
        if len(args) == 1 and callable(args[0]) and not kwargs:
            fn = args[0]
            fn.clear = lambda: None
            return fn
        def _wrap(fn):
            fn.clear = lambda: None
            return fn
        return _wrap

    def columns(self, spec, *a, **kw):
        n = spec if isinstance(spec, int) else len(spec)
        return [_NullCM() for _ in range(n)]

    def tabs(self, labels, *a, **kw):
        return [_NullCM() for _ in labels]

    def __getattr__(self, name):
        # Default: every method call returns a NullCM (also callable),
        # every property read returns None.  Booleans default False so
        # button/checkbox handlers don't fire spuriously.
        if name in {"button", "checkbox", "toggle"}:
            return lambda *a, **kw: False
        if name in {"text_input", "text_area"}:
            return lambda *a, **kw: ""
        if name == "radio":
            def _radio(label, *args, options=None, **kw):
                # streamlit's signature: st.radio(label, options, ...).
                # Pick options from kw first, then positional args.
                opts = options if options is not None else (args[0] if args else None)
                if opts:
                    return opts[0]
                return None
            return _radio
        if name == "selectbox":
            def _selectbox(label, *args, options=None, **kw):
                opts = options if options is not None else (args[0] if args else None)
                if opts:
                    return opts[0]
                return None
            return _selectbox
        if name == "sidebar":
            # ``st.sidebar`` is used both as a context manager
            # (``with st.sidebar:``) and as a namespace
            # (``st.sidebar.title("...")``).  _NullCM handles both.
            return _NullCM()
        if name in {"container", "expander", "form", "spinner",
                    "empty", "popover", "status"}:
            return lambda *a, **kw: _NullCM()
        if name == "rerun":
            class _StopRerun(BaseException):
                pass
            def _r():
                raise _StopRerun("rerun")
            return _r
        return lambda *a, **kw: None


@pytest.fixture
def st_stub(monkeypatch):
    """Install the stub as the ``streamlit`` module before importing cockpit."""
    fake_module = _StreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake_module)
    # Ensure a fresh cockpit import each test (cockpit runs main() at
    # module load, which we want to observe under the stub).
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    yield fake_module


class _NullCM:
    """No-op context manager that swallows every method call."""
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def __getattr__(self, name):
        return _NullCM()
    def __call__(self, *a, **kw):
        return _NullCM()
    def __iter__(self):
        return iter([])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_render_attention_does_not_raise(st_stub, tmp_path, monkeypatch):
    """The big one: render_attention() must execute end-to-end with the
    streamlit stub.  If anything in the function references an undefined
    name (the _library_root bug) or otherwise crashes, this fails."""
    # Point the cockpit at an empty synth library
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    cockpit.render_attention()


def test_all_render_functions_exist(st_stub):
    """Every page wired into main() must actually be defined."""
    import ui.cockpit as cockpit
    required = [
        "render_attention",
        "render_sort_queue",
        "render_upgrade_queue",
        "render_maintenance",
        "render_stats",
        "render_activity",
    ]
    for name in required:
        assert callable(getattr(cockpit, name, None)), f"{name} not defined"


def test_main_does_not_raise(st_stub, tmp_path, monkeypatch):
    """``main()`` is what streamlit calls when you ``streamlit run cockpit.py``.
    Driving it once with each page selection catches dispatcher typos."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    for page in ("Attention", "Sort Queue", "Stats", "Activity"):
        cockpit.st.session_state["page"] = page
        try:
            cockpit.main()
        except Exception as exc:
            pytest.fail(f"main() raised on page={page}: {exc!r}")
