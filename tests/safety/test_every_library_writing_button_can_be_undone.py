"""Every cockpit button that changes the library is undone by its test.

``test_every_library_writing_button_is_pressed`` proves each writing
button is pressed. That was not enough: on 2026-10-15 six of the 37 were
pressed, checked on disk -- and could not be undone from Activity,
because they wrote outside ``processing/undo_log.py`` (Mark done three
times, "Look again", "Flag for manual", both backfills). Their tests
passed because none of them pressed ↶ Undo.

So the rule here: among the tests claiming a write site with
``@presses``, at least one presses ↶ Undo on the Activity page
(``undo_from_activity``, directly or through a helper in its module).
A button that genuinely cannot be undone goes in :data:`NOT_UNDONE` with
the reason -- and the page must say so where the button is
(``_irreversible_note``), or the reason must name the tests that prove
its writes reversible elsewhere.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import textwrap
from pathlib import Path

from tests.ui import library_write_sites as W
from tests.ui.press_harness import PRESS_MODULES

UNDO_CALLS = {"undo_from_activity"}

#: Write sites whose press test does not press ↶ Undo, and why.
NOT_UNDONE: dict[str, str] = {
    "render_maintenance[run_weekly_now]": (
        "runs maintenance.weekly_report in a subprocess; its test proves a "
        "run Crossref cannot answer changes nothing, and what a run does "
        "write is one transaction each: tests/safety/"
        "test_monday_sweep_has_a_surface.py::test_the_sweeps_publication_"
        "check_is_one_undoable_transaction and ::test_file_the_safe_ones_"
        "runs_the_real_upgrader_reversibly"),
}


def _calls(fn: ast.FunctionDef, module_fns: dict, seen: set) -> set[str]:
    """Names called in ``fn``, through the module's own helpers."""
    out: set[str] = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            name = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
            out.add(name)
            if name in module_fns and name not in seen:
                seen.add(name)
                out |= _calls(module_fns[name], module_fns, seen)
    return out


def undoing_claims(source: str) -> dict[str, list[tuple[str, bool]]]:
    """{site: [(test name, does it press Undo?)]} for one test module."""
    tree = ast.parse(source)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    # ``@presses(UNDO)`` names its site through a module constant.
    consts = {t.id: n.value.value for n in tree.body
              if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
              for t in n.targets if isinstance(t, ast.Name)}
    out: dict[str, list[tuple[str, bool]]] = {}
    for name, fn in fns.items():
        for d in fn.decorator_list:
            if not (isinstance(d, ast.Call)
                    and getattr(d.func, "id", "") == "presses"):
                continue
            undoes = bool(_calls(fn, fns, {name}) & UNDO_CALLS)
            for a in d.args:
                site = (a.value if isinstance(a, ast.Constant)
                        else consts.get(getattr(a, "id", None)))
                if isinstance(site, str):
                    out.setdefault(site, []).append((name, undoes))
    return out


def _all_claims() -> dict[str, list[tuple[str, bool]]]:
    out: dict[str, list[tuple[str, bool]]] = {}
    for mod in PRESS_MODULES:
        src = inspect.getsource(importlib.import_module(mod))
        for site, tests in undoing_claims(src).items():
            out.setdefault(site, []).extend(
                (f"{mod}::{t}", u) for t, u in tests)
    return out


# --------------------------------------------------------------------------
# the rule
# --------------------------------------------------------------------------

def test_every_library_writing_button_is_undone_by_a_test():
    sites = {s.id: s for s in W.find_write_sites()}
    claims = _all_claims()
    never = [f"{s.module}:{s.line} {sid}  (pressed by "
             f"{', '.join(t for t, _ in claims.get(sid, [])) or 'nothing'})"
             for sid, s in sorted(sites.items())
             if sid not in NOT_UNDONE
             and not any(u for _, u in claims.get(sid, []))]
    assert not never, (
        "These buttons change the library and no test presses ↶ Undo after "
        "them, so nothing shows Activity can put the change back. Press it "
        "(undo_from_activity) and check the library came back -- or, if it "
        "truly cannot be undone, say so on the page with _irreversible_note "
        "and list it in NOT_UNDONE:\n  " + "\n  ".join(never))


def test_every_exemption_is_still_a_button_and_still_not_undone():
    """An exemption for a button that is gone, or whose test now presses
    Undo, is dead weight that would hide the next one."""
    sites = {s.id for s in W.find_write_sites()}
    claims = _all_claims()
    for sid, why in NOT_UNDONE.items():
        assert sid in sites, f"NOT_UNDONE names {sid}, which is gone"
        assert not any(u for _, u in claims.get(sid, [])), (
            f"{sid} is undone by its test now; drop its exemption")
        assert why.strip(), f"{sid} is exempt with no reason"


def test_every_exemption_is_explained_on_the_page_or_proven_elsewhere():
    cockpit = (W.SRC / "ui" / "cockpit.py").read_text(encoding="utf-8")
    trees = {s.id: s for s in W.find_write_sites()}
    for sid, why in NOT_UNDONE.items():
        fn_name = trees[sid].function.split(".")[0]
        fn_src = ast.get_source_segment(cockpit, next(
            n for n in ast.walk(ast.parse(cockpit))
            if isinstance(n, ast.FunctionDef) and n.name == fn_name))
        named = [p for p in why.replace("::", " ").split() if p.endswith(".py")]
        assert "_irreversible_note(" in fn_src or named, (
            f"{sid}: neither a note on its page nor a test named")
        for rel in named:
            assert (Path(__file__).resolve().parents[2] / rel.strip(",")).exists(), rel


def test_the_six_that_were_outside_the_log_are_undone_by_their_tests():
    """Pinned: the rule above could be satisfied by exempting them."""
    claims = _all_claims()
    for sid in ("render_to_download[flag_done_{}]",
                "render_to_download[flag_dl_{}]",
                "render_attention[{btn_key}]<mark_flag_done>",
                "render_attention[{btn_key}]<reset_recheck>",
                "render_upgrade_queue[upg_flag_{}]",
                "render_settings[bf_run]",
                "render_pipeline_preview[abstracts_bf_run]"):
        assert sid not in NOT_UNDONE
        assert any(u for _, u in claims[sid]), sid


# --------------------------------------------------------------------------
# the detector, on synthetic test modules (pathologies)
# --------------------------------------------------------------------------

def _claims_of(src: str) -> dict:
    return undoing_claims(textwrap.dedent(src))


def test_a_press_test_without_undo_is_seen():
    got = _claims_of('''
        @presses("p[a]")
        def test_x(ck):
            ck.st.press("a")
            ck.run("p")
    ''')
    assert got == {"p[a]": [("test_x", False)]}


def test_undo_through_a_helper_of_the_module_counts():
    got = _claims_of('''
        def _assert_undo_restores(ck, tx):
            undo_from_activity(ck, tx)

        @presses("p[a]")
        def test_x(ck):
            _assert_undo_restores(ck, "t")
    ''')
    assert got == {"p[a]": [("test_x", True)]}


def test_undo_named_but_not_called_does_not_count():
    got = _claims_of('''
        @presses("p[a]")
        def test_x(ck):
            "we should call undo_from_activity here"
            f = undo_from_activity
    ''')
    assert got == {"p[a]": [("test_x", False)]}


def test_a_site_named_through_a_module_constant_is_read():
    got = _claims_of('''
        UNDO = "render_activity[undo_{}_{}]"

        @presses(UNDO)
        def test_x(ck):
            undo_from_activity(ck, "t")
    ''')
    assert got == {"render_activity[undo_{}_{}]": [("test_x", True)]}


def test_a_recursive_helper_does_not_hang_the_detector():
    got = _claims_of('''
        def _h(ck):
            return _h(ck)

        @presses("p[a]", "p[b]")
        def test_x(ck):
            _h(ck)
    ''')
    assert got == {"p[a]": [("test_x", False)], "p[b]": [("test_x", False)]}
