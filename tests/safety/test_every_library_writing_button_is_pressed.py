"""Every cockpit button that changes the library is pressed by a test.

Until 2026-10-15, ten of the cockpit's library-changing callbacks had
never been executed by the suite -- ``_undo_transaction`` 0 of 25
statements, ``render_spelling`` 0 of 85 -- and putting back the exact bug
commit 323cdc1 fixed (an undo that counted refusals as successes) left
every test green.  A test pressing each button now exists
(``tests/ui/test_*buttons*.py``, ``tests/ui/test_undo_button.py``).  This
file keeps it that way:

* the write sites are FOUND, by AST, in the cockpit's source
  (:mod:`tests.ui.library_write_sites`), not listed by hand;
* each must be claimed by a test decorated ``@presses(site)``, and that
  decorator fails its test unless a line of the site that changes the
  library actually executed (``tests/ui/press_harness.py``);
* the finder itself is tested on synthetic sources, including a button
  added to a copy of the real cockpit, so a finder that went blind would
  fail here rather than pass by finding nothing.
"""
from __future__ import annotations

import ast
import importlib
import shutil
import textwrap
from pathlib import Path

import pytest

from tests.ui import library_write_sites as W
from tests.ui.press_harness import PRESS_MODULES


def _claims() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for name in PRESS_MODULES:
        mod = importlib.import_module(name)
        for attr, fn in vars(mod).items():
            for site in getattr(fn, "presses", ()):
                out.setdefault(site, []).append(f"{name}::{attr}")
    return out


# --------------------------------------------------------------------------
# the rule
# --------------------------------------------------------------------------

def test_every_library_writing_button_is_pressed_by_a_test():
    sites = {s.id: s for s in W.find_write_sites()}
    claims = _claims()
    unclaimed = [f"{s.module}:{s.line} {sid} -> {', '.join(s.reaches)}"
                 for sid, s in sorted(sites.items()) if sid not in claims]
    assert not unclaimed, (
        "These cockpit buttons change the library and no test presses them. "
        "Add a test in one of " + ", ".join(PRESS_MODULES) + " that presses "
        "the button on a synthetic library, checks the disk, and undoes it "
        "from Activity; decorate it @presses(<id>):\n  " + "\n  ".join(unclaimed))


def test_no_test_claims_a_button_that_no_longer_exists():
    sites = {s.id for s in W.find_write_sites()}
    stale = {sid: who for sid, who in _claims().items() if sid not in sites}
    assert not stale, f"claims for write sites that are gone or renamed: {stale}"


def test_the_finder_still_sees_every_shape_of_press_in_the_cockpit():
    """A finder that went blind would make the rule above pass vacuously
    (the stale-claim test catches a TOTAL blackout; this catches one shape
    going dark).  37 sites measured 2026-10-15."""
    ids = {s.id for s in W.find_write_sites()}
    assert "render_activity[undo_{}_{}]" in ids               # if col.button(...)
    assert "render_attention[{btn_key}]<accept_topic>" in ids  # guard + dispatch
    assert "render_attention[{btn_key}]<mark_flag_done>" in ids  # aliased import
    assert "_render_title_review._apply[tr_apply_{}]" in ids  # nested def
    assert "render_maintenance[▶ Run checks]" in ids          # label, no key


def test_every_ui_module_is_read():
    """A page moved into a new ``ui`` module would otherwise go unread."""
    here = {p.relative_to(W.SRC).as_posix()
            for p in (W.SRC / "ui").glob("*.py") if p.name != "__init__.py"}
    assert here == set(W.UI_MODULES)


def test_everything_the_cockpit_imports_that_writes_is_a_sink():
    """SINKS is kept by hand; this is the second opinion that catches a new
    writer it forgot (or an old one renamed)."""
    found = W.imports_that_write()
    # Not blind: it must see writers everyone knows write (measured
    # 2026-10-15: 24 of the cockpit's imports reach a STRONG primitive).
    assert {("processing.library_normalize", "apply_renames"),
            ("maintenance.weekly_report", "check_publications"),
            ("processing.undo_log", "logged_move")} <= set(found)
    assert len(found) == 24
    missing = {f"{b}.{n}": sorted(p) for (b, n), p in found.items()
               if n not in W.SINKS and n not in W.IMPORTS_NOT_THE_LIBRARY}
    assert not missing, (
        f"the cockpit imports these, they write the library, and SINKS does "
        f"not name them -- so their buttons are invisible to the rule: {missing}")


def test_every_named_sink_still_exists():
    """A SINKS entry for a function that was renamed away is dead weight
    that hides the rename."""
    trees = W._module_trees(W.SRC.resolve())
    defined = {n.name for t in trees.values() for n in ast.walk(t)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    primitives = {"move", "rename", "unlink", "save"}
    gone = sorted(set(W.SINKS) - defined - primitives)
    assert not gone, f"SINKS names functions that no longer exist: {gone}"


def test_every_exemption_is_real_and_still_needed():
    trees = W.load_trees()
    fns = {}
    for t in trees.values():
        for n in ast.walk(t):
            if isinstance(n, ast.FunctionDef):
                fns[n.name] = n
    for name in W.NOT_THE_LIBRARY:
        assert name in fns, f"NOT_THE_LIBRARY names {name}, which is gone"
        refs = W._refs(x for s in fns[name].body for x in W._walk_own(s))
        assert refs & W.SINKS.keys(), (
            f"{name} no longer uses a write primitive; drop its exemption")
    source = "\n".join((W.SRC / m).read_text(encoding="utf-8")
                       for m in W.UI_MODULES)
    for recv in W.SAVE_NOT_THE_LIBRARY:
        assert f"{recv}.save(" in source, f"no {recv}.save( left to exempt"


# --------------------------------------------------------------------------
# the finder, on synthetic sources (pathologies)
# --------------------------------------------------------------------------

def _src(tmp_path: Path, cockpit: str, actions: str = "") -> Path:
    src = tmp_path / "src"
    (src / "ui").mkdir(parents=True)
    (src / "ui" / "cockpit.py").write_text(textwrap.dedent(cockpit))
    (src / "ui" / "cockpit_actions.py").write_text(textwrap.dedent(actions))
    return src


def _ids(src) -> set[str]:
    return {s.id for s in W.find_write_sites(src)}


def test_a_plain_press_that_renames_is_found(tmp_path):
    assert _ids(_src(tmp_path, """
        def page():
            if st.button("Go", key="go"):
                apply_renames(lib, rows, dry_run=False)
            if st.button("Look", key="look"):
                st.write("nothing written")
    """)) == {"page[go]"}


def test_a_preview_with_a_literal_dry_run_is_not_a_write(tmp_path):
    assert _ids(_src(tmp_path, """
        def page():
            if st.button("Preview", key="pv"):
                bulk_sort(lib, dry_run=True)
            if st.button("Apply", key="ap"):
                bulk_sort(lib, dry_run=not preview_only)
    """)) == {"page[ap]"}


def test_a_press_kept_in_a_variable_is_found(tmp_path):
    assert _ids(_src(tmp_path, """
        def page():
            go = st.form_submit_button("Save")
            if go and ok:
                logged_move(a, b)
    """)) == {"page[Save]"}


def test_a_writer_passed_by_name_through_a_helper_is_found(tmp_path):
    """``_locked_call(lib, "Undo", _undo_transaction, tx)`` never CALLS the
    writer at the button; it names it."""
    assert _ids(_src(tmp_path, """
        def _undo(tx):
            UndoLog().undo_transaction(tx, dry_run=False)
        def _helper(tx):
            return _undo(tx)
        def page():
            if col.button("Undo", key=f"undo_{tx}"):
                _locked_call(lib, "Undo", _helper, tx)
    """)) == {"page[undo_{}]"}


def test_an_imported_alias_is_read_as_what_it_stands_for(tmp_path):
    assert _ids(_src(tmp_path, """
        def page():
            if st.button("Done", key="done"):
                from ui.cockpit_actions import mark_flag_done as _m
                _m(flag, lib)
    """, actions="""
        def mark_flag_done(flag, lib):
            shutil.move(str(flag), str(lib))
    """)) == {"page[done]"}


def test_each_arm_of_a_guarded_dispatch_is_its_own_site(tmp_path):
    assert _ids(_src(tmp_path, """
        def page():
            for label, action_id in actions:
                if not st.button(label, key=f"a_{action_id}"):
                    continue
                lock = take()
                if action_id == "dismiss":
                    dismiss(key)
                elif action_id == "trash":
                    logged_move(p, q)
                elif action_id == "file":
                    ingest_paper(p, dry_run=False)
    """)) == {"page[a_{}]<trash>", "page[a_{}]<file>"}


def test_a_confirm_inside_a_press_belongs_to_the_inner_button(tmp_path):
    assert _ids(_src(tmp_path, """
        def page():
            if st.button("Review", key="outer"):
                st.write("are you sure?")
                if st.button("Yes", key="inner"):
                    apply_renames(lib, rows, dry_run=False)
    """)) == {"page[inner]"}


def test_an_on_click_writer_is_found(tmp_path):
    assert _ids(_src(tmp_path, """
        def _go():
            retire_variant(p, lib, drop=d)
        def page():
            st.button("Retire", key="r", on_click=_go)
    """)) == {"<on_click>[r]"}


def test_exempt_writes_are_not_sites(tmp_path):
    assert _ids(_src(tmp_path, """
        def _log_activity(a):
            path.rename(rotated)
        def page():
            if st.button("Note", key="n"):
                _log_activity("x")
            if st.button("Report", key="rp"):
                C.save(lib, rep)
            if st.button("Record", key="rec"):
                ident.save(pdf)
    """)) == {"page[rec]"}


def test_a_new_button_in_the_real_cockpit_is_caught(tmp_path):
    """The mutation this file exists for, kept as a test: add a library-
    writing button to a copy of the real cockpit and the rule must see an
    unclaimed site."""
    src = tmp_path / "src"
    shutil.copytree(W.SRC / "ui", src / "ui")
    with open(src / "ui" / "cockpit.py", "a", encoding="utf-8") as f:
        f.write(textwrap.dedent("""

            def render_new_page():
                lib = _library()
                if st.button("Tidy everything", key="tidy_all"):
                    _locked_call(lib, "Tidy", apply_renames, lib, rows,
                                 dry_run=False)
        """))
    new = _ids(src) - {s.id for s in W.find_write_sites()}
    assert new == {"render_new_page[tidy_all]"}
    assert "render_new_page[tidy_all]" not in _claims()


@pytest.mark.parametrize("site_id", sorted(s.id for s in W.find_write_sites()))
def test_each_site_reaches_a_named_sink(site_id):
    """Every site says WHAT it writes with, so the report is checkable."""
    site = {s.id: s for s in W.find_write_sites()}[site_id]
    assert site.reaches and set(site.reaches) <= set(W.SINKS)
    assert site.write_lines


def test_the_second_opinion_reads_the_undo_logs_own_calls(tmp_path):
    """A writer that only RECORDS (``log.record_rename``) and never names
    shutil or a record's ``.save(`` must still be seen, through an import
    chain, and a literal ``dry_run=True`` call must not count."""
    src = _src(tmp_path, """
        from processing.sneaky import tidy, preview
        def page():
            tidy(log)
            preview(log)
    """)
    (src / "processing").mkdir()
    (src / "processing" / "sneaky.py").write_text(textwrap.dedent("""
        from processing.deeper import note
        def tidy(log):
            note(log)
        def preview(log):
            note(log, dry_run=True)
    """))
    (src / "processing" / "deeper.py").write_text(textwrap.dedent("""
        def note(log, dry_run=False):
            log.record_rename(a, b)
    """))
    found = W.imports_that_write(src)
    assert found == {("processing.sneaky", "tidy"): {"record_rename"}}
