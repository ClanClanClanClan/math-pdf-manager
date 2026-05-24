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
            # No-op rerun.  Streamlit's real ``rerun`` short-circuits
            # the script via an internal exception, but for smoke
            # tests we just want the function to keep going past the
            # rerun call so we exercise everything below it.
            return lambda: None
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
    """No-op context manager that masquerades as a streamlit column.

    Streamlit code does ``cols[1].button("X")`` -- the column object
    needs to behave like the streamlit module itself for the duration
    of the call.  We intercept the known UI methods to return their
    inert defaults (button=False, text_input="", etc.) so the surface
    behaves predictably under smoke tests; everything else falls
    through to another _NullCM (still callable, still a context
    manager) so deeper accesses don't explode.
    """
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def __call__(self, *a, **kw):
        return _NullCM()
    def __iter__(self):
        return iter([])
    def __getattr__(self, name):
        # Match the top-level streamlit stub's defaults for the inputs
        # smoke tests care about.
        if name in {"button", "checkbox", "toggle", "form_submit_button"}:
            return lambda *a, **kw: False
        if name in {"text_input", "text_area"}:
            return lambda *a, **kw: ""
        if name in {"number_input", "slider"}:
            return lambda *a, **kw: 0
        if name == "selectbox":
            return lambda label, options=(), *a, **kw: (
                options[0] if options else None
            )
        return _NullCM()


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
        "render_to_download",
        "render_conflicts",
        "render_maintenance",
        "render_stats",
        "render_activity",
        "render_settings",
    ]
    for name in required:
        assert callable(getattr(cockpit, name, None)), f"{name} not defined"


def test_render_to_download_does_not_raise(st_stub, tmp_path, monkeypatch):
    """Phase 5 page: 04/ browser + DOI form."""
    (tmp_path / "04 - Papers to be downloaded" / "J").mkdir(parents=True)
    flag = tmp_path / "04 - Papers to be downloaded" / "J" / "p.txt"
    flag.write_text("DOI: 10.1/x\nURL: https://doi.org/10.1/x\n", encoding="utf-8")
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    cockpit.render_to_download()


def test_render_settings_does_not_raise(st_stub, tmp_path, monkeypatch):
    """Phase 5 page: config form."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    cockpit.render_settings()


def test_render_conflicts_does_not_raise(st_stub, tmp_path, monkeypatch):
    """Phase 6 page + Task #8 multi-select renders without crashing."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    # Seed one conflict so the bulk-select bar actually renders.
    (tmp_path / "Foo (DESKTOP-X's conflicted copy 2024-05-13).pdf").write_bytes(
        b"%PDF-1.4 fake"
    )
    (tmp_path / "Foo.pdf").write_bytes(b"%PDF-1.4 canon")
    import ui.cockpit as cockpit
    cockpit.render_conflicts()


def test_conflicts_bulk_apply_single_transaction(st_stub, tmp_path, monkeypatch):
    """Task #8: bulk resolution wraps every conflict in one undo
    transaction so users can reverse the batch as a unit."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    # Three conflicts of the canonical-wins flavour.
    for stem in ("A", "B", "C"):
        (tmp_path / f"{stem}.pdf").write_bytes(b"%PDF canon")
        (tmp_path / f"{stem} (host's conflicted copy 2024-05-13).pdf").write_bytes(
            b"%PDF conflict"
        )
    from processing.conflict_resolver import scan_conflicts
    found = scan_conflicts(tmp_path)
    assert len(found) == 3

    import ui.cockpit as cockpit
    paths = {c.conflict for c in found}
    n_ok, n_fail, errors = cockpit._conflicts_bulk_apply(
        found, paths, tmp_path, "keep_canonical",
    )
    assert n_ok == 3, errors
    assert n_fail == 0
    # All conflicts moved to trash; canonicals untouched
    for stem in ("A", "B", "C"):
        assert (tmp_path / f"{stem}.pdf").exists()
        assert not (
            tmp_path / f"{stem} (host's conflicted copy 2024-05-13).pdf"
        ).exists()


def test_render_conflicts_does_not_raise(st_stub, tmp_path, monkeypatch):
    """Phase 6 page: conflict-copy diff/decide.  Should render the
    'no conflicts' success state on an empty library, and the
    per-conflict cards when a real conflict pair is present."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit

    # Empty library -> success state
    cockpit.render_conflicts()

    # One conflict + canonical pair -> renders the diff card
    (tmp_path / "Foo.pdf").write_bytes(b"%PDF-1.4 a")
    (tmp_path / "Foo (conflicted copy 2024-05-13).pdf").write_bytes(
        b"%PDF-1.4 a"
    )
    cockpit.render_conflicts()


def test_render_sort_queue_with_real_pdf_does_not_raise(st_stub, tmp_path, monkeypatch):
    """Drive render_sort_queue() with a PDF in 12/ to exercise the
    Phase 4 topic-router integration.  A typo in the topic-checkbox
    wiring or the classify_and_link call would surface here.

    The stub leaves Approve as ``False`` (default) so no actual filing
    happens -- this is purely a render-path smoke test.
    """
    # Build a synth library with the staging folder and one PDF
    staging = tmp_path / "12 - To be sorted" / "03 - Working papers"
    staging.mkdir(parents=True)
    pdf = staging / "drop.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n"
        b"%%EOF\n"
    )
    # Topic folders so find_topic_folder has somewhere to discover
    (tmp_path / "07a - BSDEs").mkdir()
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))

    import ui.cockpit as cockpit
    cockpit.render_sort_queue()


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
