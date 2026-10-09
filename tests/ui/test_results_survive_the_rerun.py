"""An action's result must reach the owner, and Undo must not fire by accident.

Cockpit audit findings 7, 19 and 11, all approved.

7.  The Normalize apply and the bulk filer drew their result with
    ``st.success`` and then called ``st.rerun()``, which throws the drawn
    page away. A fully REFUSED batch -- including "the library is busy,
    nothing was renamed", which arrives as ``res["error"]`` and was never
    read at all -- looked exactly like an applied one. ``_flash`` existed
    for this, but its renderer was only called inside the Home page, so a
    message queued anywhere else was never drawn.

19. A PARTIAL undo looked exactly like a complete one: the refusal list
    was drawn with st.warning and destroyed by the caller's rerun, and the
    ``partial_undo`` record the undo log writes was read by nothing, so the
    Activity row was identical to one never touched. Measured by the audit
    on the real log: 18 of 133 still-undoable transactions would undo only
    in part.

11. Undo -- up to 8,514 changes, with no redo -- was the only bulk action
    in the cockpit without an "I've read it" tick.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.ui.test_cockpit_smoke import st_stub  # noqa: F401  (fixture)

COCKPIT = Path(__file__).resolve().parents[2] / "src" / "ui" / "cockpit.py"


@pytest.fixture
def C(st_stub, monkeypatch):
    """The cockpit module, with message widgets recorded by kind and text."""
    import ui.cockpit as cockpit
    shown = []
    for kind in ("error", "warning", "success", "info", "caption", "toast"):
        monkeypatch.setattr(st_stub, kind,
                            lambda msg="", *a, _k=kind, **kw: shown.append((_k, str(msg))))
    monkeypatch.setattr(cockpit, "_log_activity", lambda *a, **k: None)
    st_stub.session_state.pop("flash", None)
    cockpit._shown = shown
    return cockpit


def _render(C):
    C._shown.clear()
    C._render_flashes()
    return list(C._shown)


# ----------------------------------------------- the flash reaches every page

def test_a_flash_is_drawn_once_with_its_details_then_cleared(C):
    C._flash("warning", "2 left alone", ["`a.pdf` — target exists",
                                          "`b.pdf` — source gone"], "Left alone")
    shown = _render(C)
    assert ("warning", "2 left alone") in shown
    assert ("caption", "`a.pdf` — target exists") in shown
    assert ("caption", "`b.pdf` — source gone") in shown
    assert _render(C) == [], "a flash is shown once, not on every rerun"


def test_success_is_a_kind_the_renderer_draws(C):
    C._flash("success", "18 file(s) renamed.")
    assert ("success", "18 file(s) renamed.") in _render(C)


def _main_and_attention():
    tree = ast.parse(COCKPIT.read_text(encoding="utf-8"))
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    return funcs["main"], funcs["render_attention"]


def test_main_draws_flashes_before_it_dispatches_to_any_page():
    """The renderer used to be called only from the Home page."""
    main, _ = _main_and_attention()
    src = ast.unparse(main)
    assert "_render_flashes()" in src
    assert src.index("_render_flashes()") < src.index("if page == "), (
        "flashes must be drawn before the page, whichever page it is")


def test_home_does_not_draw_them_a_second_time():
    _, home = _main_and_attention()
    assert "_render_flashes()" not in ast.unparse(home)


# ------------------------------------------- four outcomes, four messages

def test_a_busy_library_says_so_instead_of_vanishing(C):
    """res['error'] was never read: the lock-busy explanation was
    unreachable even before the rerun discarded everything."""
    C._flash_rename_result({"renamed": 0, "tx_id": None, "error": "another process is working",
                            "skipped": [{"old": "a.pdf", "reason": "library busy"}]},
                           noun="renamed")
    shown = _render(C)
    assert any(k == "error" and "another process is working" in m for k, m in shown)


def test_all_done_partly_done_and_nothing_done_look_different(C):
    C._flash_rename_result({"renamed": 3, "skipped": [], "tx_id": "t"}, noun="renamed")
    ok = _render(C)
    C._flash_rename_result({"renamed": 3, "tx_id": "t",
                            "skipped": [{"old": "x.pdf", "reason": "target exists"}]},
                           noun="renamed")
    part = _render(C)
    C._flash_rename_result({"renamed": 0, "tx_id": None,
                            "skipped": [{"old": "x.pdf", "reason": "target exists"}]},
                           noun="renamed")
    none = _render(C)
    assert ok[0][0] == "success"
    assert part[0][0] == "warning" and ("caption", "`x.pdf` — target exists") in part
    assert none[0][0] == "error" and ("caption", "`x.pdf` — target exists") in none


def test_a_refused_file_stays_in_the_list_so_it_can_be_retried(C):
    """It used to drop the whole attempted batch, refused ones included."""
    proposals = [{"old": f"{n}.pdf"} for n in "abcd"]
    batch = proposals[:3]
    res = {"renamed": 2, "skipped": [{"old": "b.pdf", "reason": "target exists"}]}
    left = [p["old"] for p in C._remaining_after_apply(proposals, batch, res)]
    assert left == ["b.pdf", "d.pdf"]


# ------------------------------------------------------- partial undo

class _FakeLog:
    results: list = []

    def __init__(self, *a, **k):
        pass

    def undo_transaction(self, tx_id, dry_run=False):
        if isinstance(self.results, Exception):
            raise self.results
        return self.results


@pytest.fixture
def fake_undo(monkeypatch):
    import processing.undo_log as ul
    monkeypatch.setattr(ul, "UndoLog", _FakeLog)
    return _FakeLog


def test_a_partial_undo_is_reported_as_partial_with_what_failed(C, fake_undo):
    fake_undo.results = ([{"ok": True, "action": "RENAMED x"}] * 5
                         + [{"ok": False, "action": "SKIP y: target occupied"}] * 2)
    assert C._undo_transaction("tx1") is True
    shown = _render(C)
    assert shown[0][0] == "warning" and "5 of 7" in shown[0][1]
    assert ("caption", "SKIP y: target occupied") in shown


def test_a_complete_undo_says_complete(C, fake_undo):
    fake_undo.results = [{"ok": True, "action": "RENAMED x"}] * 4
    assert C._undo_transaction("tx1") is True
    assert _render(C)[0][0] == "success"


def test_a_refused_undo_says_nothing_happened_and_returns_false(C, fake_undo):
    fake_undo.results = [{"ok": False, "action": "CANNOT UNDO z"}]
    assert C._undo_transaction("tx1") is False
    shown = _render(C)
    assert shown[0][0] == "error" and "Nothing was undone" in shown[0][1]


def test_an_exploding_undo_is_reported_not_swallowed(C, fake_undo):
    fake_undo.results = OSError("disk went away")
    C._undo_transaction("tx1")
    shown = _render(C)
    assert shown and shown[0][0] == "error" and "disk went away" in shown[0][1]


def test_the_row_of_a_partly_undone_transaction_says_so(C):
    base = {"timestamp": "2026-10-09T10:00:00", "description": "normalize existing filenames: 3 file(s)",
            "operations_count": 7}
    plain = C._activity_row_label(base)
    partial = C._activity_row_label({**base, "partial_undo": {
        "reversed": 5, "not_reversed": ["SKIP a", "SKIP b"]}})
    done = C._activity_row_label({**base, "undone": True})
    assert "PARTLY UNDONE (5 reversed, 2 not)" in partial
    assert "UNDONE" not in plain
    assert "ALREADY UNDONE" in done and "PARTLY" not in done


# ------------------------------------------------------- the undo gate

def test_undo_does_not_fire_until_the_box_is_ticked(C, st_stub, monkeypatch):
    """Drive the real Activity page with one transaction on record."""
    import processing.undo_log as ul

    class _Log:
        def __init__(self, *a, **k):
            pass

        def list_transactions(self):
            return [{"id": "tx9", "timestamp": "2026-10-09T10:00:00",
                     "description": "normalize existing filenames: 4265 file(s)",
                     "operations_count": 8514, "undone": False}]

    monkeypatch.setattr(ul, "UndoLog", _Log)
    fired = []
    monkeypatch.setattr(C, "_undo_transaction", lambda tx: fired.append(tx) or True)
    ticked = {"v": False}

    def _checkbox(label, *a, **kw):
        return ticked["v"] if "Reverse all" in str(label) else False

    def _button(label, *a, disabled=False, **kw):
        # A button only reports a click when it is enabled.
        return str(label).startswith("↶ Undo") and not disabled

    monkeypatch.setattr(st_stub, "checkbox", _checkbox)
    monkeypatch.setattr(st_stub, "button", _button)
    # The undo controls sit inside st.columns -> _NullCM; route those too.
    import tests.ui.test_cockpit_smoke as smoke
    orig = smoke._NullCM.__getattr__

    def _cm_getattr(self, name):
        if name == "checkbox":
            return _checkbox
        if name == "button":
            return _button
        return orig(self, name)

    monkeypatch.setattr(smoke._NullCM, "__getattr__", _cm_getattr)

    C.render_activity()
    assert fired == [], "Undo fired without the confirmation box ticked"
    ticked["v"] = True
    C.render_activity()
    assert fired == ["tx9"], "with the box ticked, Undo must work"
