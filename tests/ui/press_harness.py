"""Press a cockpit button on a synthetic library, and prove it was pressed.

``@presses("render_activity[undo_{}_{}]")`` on a test says: this test
presses that write site (an id from :mod:`library_write_sites`).  After
the test body has passed, the decorator checks that at least one of the
site's library-writing lines actually EXECUTED while the test ran -- a
test that sets up the page, misses the button, and asserts on an
unchanged disk cannot claim the site.  Lines are recorded with
``sys.monitoring`` on the cockpit's own code objects only, which is cheap
and never collides with coverage's tracer.

The structural test reads the ``presses`` attribute of every test in
:data:`PRESS_MODULES` and requires every write site found in the source
to be claimed by one of them.
"""
from __future__ import annotations

import functools
import hashlib
import importlib
import re
import sys
import types
from pathlib import Path

import pytest

from tests.ui.library_write_sites import WriteSite, find_write_sites
from tests.ui.streamlit_double import StreamlitDouble

#: The test modules whose ``@presses`` claims count.
PRESS_MODULES = (
    "tests.ui.test_buttons_that_file_papers",
    "tests.ui.test_buttons_that_rename_papers",
    "tests.ui.test_buttons_that_retire_papers",
    "tests.ui.test_buttons_that_rewrite_records",
    "tests.ui.test_home_buttons",
    "tests.ui.test_undo_button",
)

_SITES: dict[str, WriteSite] | None = None


def sites() -> dict[str, WriteSite]:
    global _SITES
    if _SITES is None:
        _SITES = {s.id: s for s in find_write_sites()}
    return _SITES


# --------------------------------------------------------------------------
# which lines of the cockpit ran
# --------------------------------------------------------------------------

class LineRecorder:
    """Every (file, line) executed in the given modules' functions."""

    def __init__(self, *modules: types.ModuleType):
        self.hits: set[tuple[str, int]] = set()
        self._codes = []
        for m in modules:
            self._codes += _codes_of(m)
        self._tool = None

    def _on_line(self, code, line):
        self.hits.add((code.co_filename, line))

    def __enter__(self):
        mon = sys.monitoring
        for tool in (3, 4):
            if mon.get_tool(tool) is None:
                self._tool = tool
                break
        else:                                         # pragma: no cover
            raise RuntimeError("no free sys.monitoring tool id")
        mon.use_tool_id(self._tool, "cockpit-press-check")
        mon.register_callback(self._tool, mon.events.LINE, self._on_line)
        for code in self._codes:
            mon.set_local_events(self._tool, code, mon.events.LINE)
        return self

    def __exit__(self, *exc):
        mon = sys.monitoring
        for code in self._codes:
            mon.set_local_events(self._tool, code, 0)
        mon.register_callback(self._tool, mon.events.LINE, None)
        mon.free_tool_id(self._tool)
        return False


def _codes_of(module) -> list:
    """Every code object defined in ``module``'s file, nested ones too."""
    fname = getattr(module, "__file__", None)
    out, seen = [], set()

    def add(code):
        if id(code) in seen or code.co_filename != fname:
            return
        seen.add(id(code))
        out.append(code)
        for c in code.co_consts:
            if isinstance(c, types.CodeType):
                add(c)

    for v in list(vars(module).values()):
        fn = getattr(v, "__wrapped__", v)
        if isinstance(fn, types.FunctionType):
            add(fn.__code__)
        elif isinstance(v, type):
            for a in vars(v).values():
                if isinstance(a, types.FunctionType):
                    add(a.__code__)
    return out


# --------------------------------------------------------------------------
# the cockpit, under the double, on a synthetic library
# --------------------------------------------------------------------------

class Cockpit:
    """``ck.module`` is ``ui.cockpit``; ``ck.st`` the Streamlit double."""

    def __init__(self, module, st: StreamlitDouble, lib: Path, recorder):
        self.module = module
        self.st = st
        self.lib = lib
        self.recorder = recorder
        self.home: Path | None = None     # this test's $HOME

    def run(self, page: str | object, *args, **kwargs) -> str:
        fn = getattr(self.module, page) if isinstance(page, str) else page
        return self.st.run(fn, *args, **kwargs)

    def ran(self, site_id: str) -> bool:
        """Did any of ``site_id``'s library-writing lines execute?"""
        s = sites()[site_id]
        fname = sys.modules[s.module_name].__file__
        return any((fname, ln) in self.recorder.hits for ln in s.write_lines)

    def flashes(self) -> list[tuple[str, str]]:
        """(kind, message) queued for the next page, as the owner reads them."""
        return [(f[0], f[1]) for f in self.st.session_state.get("flash", [])]


def load_cockpit(monkeypatch, lib: Path) -> Cockpit:
    """Import ``ui.cockpit`` fresh under a new double, pointed at ``lib``."""
    st = StreamlitDouble()
    monkeypatch.setitem(sys.modules, "streamlit", st)
    monkeypatch.setenv("MATH_LIBRARY", str(lib))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    module = importlib.import_module("ui.cockpit")
    st.session_state["library_root"] = str(lib)
    st.session_state.pop("_attn_cache", None)
    st.session_state.pop("flash", None)
    st.calls.clear()
    actions = importlib.import_module("ui.cockpit_actions")
    rec = LineRecorder(module, actions)
    return Cockpit(module, st, lib, rec)


@pytest.fixture
def ck(monkeypatch, tmp_path):
    """The cockpit on an empty synthetic library at ``tmp_path/Maths``.

    ``HOME`` is this test's own: the activity feed, skip lists and saved
    scans live under ``~/.mathpdf`` and must not leak between tests.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    lib = tmp_path / "Maths"
    lib.mkdir()
    for folder in ("01 - Published papers", "02 - Unpublished papers",
                   "03 - Working papers", "04 - Papers to be downloaded",
                   "05 - Books and lecture notes", "06 - Theses",
                   "12 - To be sorted"):
        (lib / folder).mkdir()
    from processing.identity import enable_sidecar_mirror
    enable_sidecar_mirror(lib)          # records live in the mirror, as on his Mac
    cockpit = load_cockpit(monkeypatch, lib)
    cockpit.home = home
    with cockpit.recorder:
        yield cockpit


def presses(*site_ids: str):
    """Claim write sites; fail unless each one's write line executed."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            out = fn(*args, **kwargs)
            cockpit = kwargs.get("ck")
            assert cockpit is not None, f"{fn.__name__} must use the ck fixture"
            missed = [s for s in site_ids if not cockpit.ran(s)]
            assert not missed, (
                f"{fn.__name__} claims to press {missed} but no line of the "
                f"button's branch that changes the library ran")
            return out
        wrapper.presses = site_ids
        return wrapper
    return deco


# --------------------------------------------------------------------------
# the library, before and after
# --------------------------------------------------------------------------

#: Not the library's contents: the undo history itself, caches and
#: rulings, the lock.  Records (``.mathpdf-sidecars``) and ``.trash`` ARE
#: compared: undo must give both back.
_BOOKKEEPING = (".operation_log", ".mathpdf-config", ".mathpdf.lock",
                ".mathpdf-lock")


def snapshot(lib: Path) -> dict[str, str]:
    """{relative path: sha256} of every file in the library that matters."""
    out = {}
    for p in sorted(lib.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(lib).as_posix()
        if rel.split("/", 1)[0] in _BOOKKEEPING or p.name.startswith(".mathpdf"):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def transactions(lib: Path) -> list[dict]:
    from processing.undo_log import UndoLog
    return UndoLog(log_dir=lib / ".operation_log").list_transactions()


def undo_from_activity(cockpit: Cockpit, tx_id: str) -> str:
    """Tick "Reverse all N change(s)" and press ↶ Undo on ``tx_id``'s row,
    exactly as the owner does on the Activity page."""
    shown = list(reversed(transactions(cockpit.lib)))
    i = next(n for n, tx in enumerate(shown) if tx["id"] == tx_id)
    cockpit.st.set(**{f"undo_ok_{i}_{tx_id}": True})
    cockpit.st.press(f"undo_{i}_{tx_id}")
    return cockpit.run("render_activity")


def pdf_bytes(tag: str) -> bytes:
    """A small, distinct, valid-enough PDF body."""
    return (b"%PDF-1.4\n% " + tag.encode() + b"\n1 0 obj << /Type /Catalog >> "
            b"endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n")


def put(lib: Path, rel: str, body: bytes | None = None) -> Path:
    p = lib / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body if body is not None else pdf_bytes(rel))
    return p


def key_matching(pattern: str):
    return re.compile(pattern)
