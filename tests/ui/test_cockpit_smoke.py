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
        # Every streamlit attribute a page touches, in order.
        #
        # Without this the smoke tests could only say "rendering did not
        # raise", which is equally true of a page that returns on its
        # first line. Nine of them asserted nothing at all and the commit
        # gate was right to refuse them.
        self.calls: list = []

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
        self.calls.append("columns")
        n = spec if isinstance(spec, int) else len(spec)
        return [_NullCM() for _ in range(n)]

    def tabs(self, labels, *a, **kw):
        self.calls.append("tabs")
        return [_NullCM() for _ in labels]

    def __getattr__(self, name):
        if not name.startswith("_"):
            # Normal attribute lookup found nothing, so this is a widget
            # call; record it before handing back the no-op.
            self.__dict__.setdefault("calls", []).append(name)
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
def st_stub(monkeypatch, tmp_path):
    """Install the stub as the ``streamlit`` module before importing cockpit."""
    fake_module = _StreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake_module)
    # Tests must NEVER touch the real library.  cockpit runs main() at
    # module import, and the sidebar's attention count walks the whole
    # library — against the real 29k-PDF Dropbox tree that walk can
    # exceed the per-test timeout (observed flake) and violates test
    # isolation.  Point MATH_LIBRARY at a fresh tmp dir BEFORE any
    # import; individual tests may re-point it before importing cockpit.
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
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
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_attention()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

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
        "render_pipeline_preview",
        "render_conformance",
        "render_stats",
        "render_activity",
        "render_settings",
    ]
    for name in required:
        assert callable(getattr(cockpit, name, None)), f"{name} not defined"


def test_render_pipeline_preview_empty_does_not_raise(st_stub, tmp_path, monkeypatch):
    """Pipeline Preview with no prior run shows the info prompt path."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_pipeline_preview()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

def test_render_pipeline_preview_with_results_does_not_raise(st_stub, tmp_path, monkeypatch):
    """With seeded results, the metrics + band expanders + dataframe all
    render (exercises the _rows / relative_to / dataframe path)."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    cockpit.st.session_state["preview_summary"] = {
        "scanned": 3, "agreement_rate": 0.5, "topic_recall": 0.67,
        "disagree": 1, "agree": 1, "recall_miss": 1,
        "proposed_moves": 1, "proposed_suggestions": 0, "in_topic": 2,
    }
    base = tmp_path / "07a - BSDEs" / "01 - Published papers"
    cockpit.st.session_state["preview_proposals"] = [
        {"path": str(base / "X - a.pdf"), "status": "agree",
         "current_topic": "07a", "proposed_topic": "07a",
         "suggested_topic": None, "confidence": 0.9},
        {"path": str(base / "X - b.pdf"), "status": "disagree",
         "current_topic": "07a", "proposed_topic": "07b",
         "suggested_topic": None, "confidence": 0.9},
        {"path": str(tmp_path / "01 - Published papers" / "X - c.pdf"),
         "status": "move", "current_topic": None, "proposed_topic": "07a",
         "suggested_topic": None, "confidence": 0.9},
    ]
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_pipeline_preview()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

def test_render_to_download_does_not_raise(st_stub, tmp_path, monkeypatch):
    """Phase 5 page: 04/ browser + DOI form."""
    (tmp_path / "04 - Papers to be downloaded" / "J").mkdir(parents=True)
    flag = tmp_path / "04 - Papers to be downloaded" / "J" / "p.txt"
    flag.write_text("DOI: 10.1/x\nURL: https://doi.org/10.1/x\n", encoding="utf-8")
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_to_download()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

def test_render_settings_does_not_raise(st_stub, tmp_path, monkeypatch):
    """Phase 5 page: config form (incl. the ETH-credential section)."""
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    # Don't touch the real OS keychain / credentials.enc when rendering the
    # ETH-credential section — stub the secure-store read (the function
    # re-reads the module attribute at call time).
    import core.config.secure_config as sc
    monkeypatch.setattr(sc, "get_secure_credential", lambda *a, **k: None)
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_settings()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

def test_render_conflicts_with_a_desktop_style_conflict_name(
        st_stub, tmp_path, monkeypatch):
    """A DESKTOP-X style conflict name, which parses differently from the
    plain "conflicted copy" form covered below.

    RENAMED: it shared a name with the later test, so Python kept only
    that definition and THIS ONE HAD NEVER RUN — a duplicate function
    name is a silently deleted test, and pytest reports nothing amiss.
    """
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    # Seed one conflict so the bulk-select bar actually renders.
    (tmp_path / "Foo (DESKTOP-X's conflicted copy 2024-05-13).pdf").write_bytes(
        b"%PDF-1.4 fake"
    )
    (tmp_path / "Foo.pdf").write_bytes(b"%PDF-1.4 canon")
    import ui.cockpit as cockpit
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_conflicts()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

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
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_conflicts()

    # One conflict + canonical pair -> renders the diff card
    (tmp_path / "Foo.pdf").write_bytes(b"%PDF-1.4 a")
    (tmp_path / "Foo (conflicted copy 2024-05-13).pdf").write_bytes(
        b"%PDF-1.4 a"
    )
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_conflicts()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

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
    st_stub.calls.clear()   # measure THIS page, not main() at import
    cockpit.render_sort_queue()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

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


# ---------------------------------------------------------------------------
# Every page, not just the four that happened to have a test.
# ---------------------------------------------------------------------------

# Kept in step with the router in main().  The nav was regrouped from a
# flat 12-item radio into Do/Fix/Look/Setup button groups, and only 4 of
# the 12 pages had any smoke coverage at the time — a page could break on
# a refactor and nothing would notice until the owner clicked it.
ALL_PAGE_RENDERERS = [
    "render_attention",
    "render_search",
    "render_sort_queue",
    "render_upgrade_queue",
    "render_to_download",
    "render_conflicts",
    "render_duplicates",
    "render_maintenance",
    "render_pipeline_preview",
    "render_conformance",
    "render_stats",
    "render_activity",
    "render_settings",
]


@pytest.mark.parametrize("renderer", ALL_PAGE_RENDERERS)
def test_every_page_renders_against_an_empty_library(
    st_stub, tmp_path, monkeypatch, renderer
):
    """Each page must survive an empty library without raising.

    An empty library is the harshest ordinary case: every "first item"
    lookup has nothing to bite on, which is exactly where index errors
    and None-derefs live.
    """
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    import ui.cockpit as cockpit
    getattr(cockpit, renderer)()
    assert st_stub.calls, (
        "the page rendered NOTHING — a silent early return passes a "
        "'does not raise' test just as well as a working page")

def test_router_covers_every_nav_entry(st_stub):
    """Every page named in the sidebar must be dispatched by main().

    The sidebar and the router are two separate lists; a page added to
    one and not the other silently renders nothing.

    The list of labels is DERIVED from the sidebar, not written out here.
    It used to be eleven hardcoded strings, and by the time anyone looked
    it was missing "Conformance", "Attention" and "Spelling" — so the
    guard against a page that nobody routes had itself stopped guarding
    against three of them. A checklist that must be updated by hand has
    the same failure mode as the thing it is checking.
    """
    import ast
    import inspect
    import textwrap

    import ui.cockpit as cockpit

    src = inspect.getsource(cockpit.main)
    sidebar_src = inspect.getsource(cockpit.render_sidebar)

    # _GROUPS = [("Do", [...]), ("Fix", [...]), ...] — take the page names
    # out of the inner lists; the group headings are not pages.
    labels = []
    tree = ast.parse(textwrap.dedent(sidebar_src))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(t, "id", "") == "_GROUPS" for t in node.targets):
            continue
        for group in node.value.elts:
            for item in group.elts[1].elts:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    labels.append(item.value)

    assert len(labels) >= 11, (
        f"only found {len(labels)} nav labels — the _GROUPS literal moved "
        "and this test is no longer reading it")
    for label in labels:
        assert f'"{label}"' in src, f"{label} is in the sidebar but main() never dispatches it"


def test_home_and_router_agree_on_the_default_page(st_stub):
    """The sidebar's default page and the router's fallback must match.

    They disagreed (`Attention` vs `Sort Queue`) and only worked because
    the sidebar happens to run first and set session_state.
    """
    import inspect
    import ui.cockpit as cockpit
    router = inspect.getsource(cockpit.main)
    assert 'st.session_state.get("page", "Attention")' in router
