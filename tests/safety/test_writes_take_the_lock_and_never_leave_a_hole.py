"""Cockpit writes take the library lock; "Keep conflict" never leaves an empty shelf.

Cockpit audit findings 10 and 20, both approved.

10. The watcher, the weekly job and the filename tidy-up all take
    ``LibraryLock``. Every OTHER cockpit path that moves, renames or
    rewrites papers did not -- bulk filing, single filing, upgrades, topic
    apply, conflict resolution, duplicate and variant retirement, the
    publication check's record rewrites, the Home page's actions, and Undo.
    The sharpest collision: Home's "retry" re-ingests a file still sitting
    in the filer's own inbox. The lock is NOT re-entrant (each acquire opens
    a new descriptor, and macOS blocks a second flock even in-process), so
    it is taken once, at the button, and never around apply_renames, which
    takes it itself.

20. ``resolve_keep_conflict`` retired the canonical to the trash BEFORE
    checking that the conflict copy was still there. If it had gone since
    the scan (Dropbox sync, a second tab), the shelf was left empty and the
    page said only "failed". The sibling resolve_keep_canonical always had
    the pre-check. Reproduced by the audit in a sandbox.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

COCKPIT = Path(__file__).resolve().parents[2] / "src" / "ui" / "cockpit.py"


# ------------------------------------------------------- 20. keep conflict

@pytest.fixture
def shelf(tmp_path):
    folder = tmp_path / "01 - Published papers" / "S"
    folder.mkdir(parents=True)
    canonical = folder / "Smith, J. - A paper.pdf"
    conflict = folder / "Smith, J. - A paper (conflicted copy 2026-10-09).pdf"
    canonical.write_bytes(b"%PDF-1.4 original")
    conflict.write_bytes(b"%PDF-1.4 the other version")
    return tmp_path, canonical, conflict


def _log(lib):
    from processing.undo_log import UndoLog
    log = UndoLog(log_dir=lib / ".operation_log")
    log.begin_transaction("test")
    return log


def test_a_vanished_conflict_touches_nothing(shelf):
    from processing.conflict_resolver import resolve_keep_conflict
    lib, canonical, conflict = shelf
    conflict.unlink()
    ok, msg = resolve_keep_conflict(conflict, lib, canonical=canonical,
                                    undo_log=_log(lib))
    assert not ok and "conflict gone" in msg
    assert canonical.read_bytes() == b"%PDF-1.4 original", "the shelf must be untouched"
    trash = lib / ".trash" / "conflict_copies"
    assert not trash.exists() or not any(trash.iterdir())


def test_a_failed_promotion_puts_the_original_back(shelf, monkeypatch):
    """The conflict vanishes BETWEEN the check and the move."""
    import processing.undo_log as ul
    from processing.conflict_resolver import resolve_keep_conflict
    lib, canonical, conflict = shelf
    real = ul.logged_move
    calls = {"n": 0}

    def _move(src, dst, **kw):
        calls["n"] += 1
        if calls["n"] == 2:                       # the promotion
            raise FileNotFoundError(f"Source does not exist: {src}")
        return real(src, dst, **kw)

    monkeypatch.setattr(ul, "logged_move", _move)
    ok, msg = resolve_keep_conflict(conflict, lib, canonical=canonical,
                                    undo_log=_log(lib))
    assert not ok and "put back" in msg
    assert canonical.exists() and canonical.read_bytes() == b"%PDF-1.4 original"


def test_if_putting_it_back_also_fails_the_message_says_where_it_is(shelf, monkeypatch):
    import processing.undo_log as ul
    from processing.conflict_resolver import resolve_keep_conflict
    lib, canonical, conflict = shelf
    real = ul.logged_move
    calls = {"n": 0}

    def _move(src, dst, **kw):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise OSError("disk went away")
        return real(src, dst, **kw)

    monkeypatch.setattr(ul, "logged_move", _move)
    ok, msg = resolve_keep_conflict(conflict, lib, canonical=canonical,
                                    undo_log=_log(lib))
    assert not ok and ".trash/conflict_copies/" in msg and "Activity" in msg
    retired = list((lib / ".trash" / "conflict_copies").iterdir())
    assert len(retired) == 1 and retired[0].read_bytes() == b"%PDF-1.4 original", (
        "even then the original must be in the trash, not lost")


def test_the_ordinary_case_still_promotes(shelf):
    from processing.conflict_resolver import resolve_keep_conflict
    lib, canonical, conflict = shelf
    ok, msg = resolve_keep_conflict(conflict, lib, canonical=canonical,
                                    undo_log=_log(lib))
    assert ok, msg
    assert canonical.read_bytes() == b"%PDF-1.4 the other version"
    assert not conflict.exists()


# ------------------------------------------------------------ 10. the lock

@pytest.fixture
def C(monkeypatch, tmp_path):
    from tests.ui.test_cockpit_smoke import _StreamlitModule
    fake = _StreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as cockpit
    import processing.library_normalize as ln
    monkeypatch.setattr(ln, "LOCK_WAIT_SECONDS", 0.2)
    return cockpit


def test_a_locked_call_runs_and_releases(C, tmp_path):
    ran = []
    ok, out = C._locked_call(tmp_path, "test", lambda x: ran.append(x) or 7, 3)
    assert (ok, out, ran) == (True, 7, [3])
    from processing.locking import LibraryLock
    lock = LibraryLock(tmp_path)
    assert lock.acquire(blocking=False), "the lock was not released"
    lock.release()


def test_when_the_filer_holds_the_lock_nothing_runs_and_he_is_told(C, tmp_path):
    """A second holder in the same process is refused exactly like another
    process would be -- which is what makes this testable."""
    from processing.locking import LibraryLock
    other = LibraryLock(tmp_path)
    assert other.acquire(blocking=False)
    try:
        ran = []
        ok, out = C._locked_call(tmp_path, "File these papers",
                                 lambda: ran.append(1))
        assert (ok, out, ran) == (False, None, [])
        flashes = C.st.session_state.get("flash", [])
        assert flashes and flashes[-1][0] == "error"
        assert "File these papers" in flashes[-1][1] and "Nothing was changed" in flashes[-1][1]
    finally:
        other.release()


def test_an_exception_inside_still_releases_the_lock(C, tmp_path):
    def boom():
        raise RuntimeError("x")
    with pytest.raises(RuntimeError):
        C._locked_call(tmp_path, "t", boom)
    from processing.locking import LibraryLock
    lock = LibraryLock(tmp_path)
    assert lock.acquire(blocking=False)
    lock.release()


# ------------------------------------------------- structure: no path forgotten

#: Functions the cockpit calls that move, rename, trash or rewrite papers.
#: Each call must go through _locked_call -- unless it is an explicit dry run.
MUTATORS = {"bulk_sort", "_approve_sort", "_approve_upgrade", "process_report",
            "check_publications", "apply_topic_proposals", "_undo_transaction",
            "_conflicts_bulk_apply", "retire_variant",
            "apply_duplicate_resolutions", "resolve_group"}


def _tree():
    return ast.parse(COCKPIT.read_text(encoding="utf-8"))


def _name(node):
    return getattr(node, "id", None) or getattr(node, "attr", None)


def test_every_writing_call_goes_through_the_lock():
    direct = []
    for n in ast.walk(_tree()):
        if not isinstance(n, ast.Call) or _name(n.func) not in MUTATORS:
            continue
        kw = {k.arg: k.value for k in n.keywords}
        dry = kw.get("dry_run")
        if isinstance(dry, ast.Constant) and dry.value is True:
            continue                                   # a preview
        direct.append(f"line {n.lineno}: {_name(n.func)}(...)")
    assert not direct, (
        "called directly, outside the library lock -- pass it to "
        "_locked_call instead:\n  " + "\n  ".join(direct))


def test_the_locked_mutators_are_all_actually_reached():
    """Pathology guard: if a refactor renamed a mutator, the test above
    would pass vacuously. Every name must appear as a _locked_call target."""
    targets = set()
    for n in ast.walk(_tree()):
        if isinstance(n, ast.Call) and _name(n.func) == "_locked_call" and len(n.args) >= 3:
            targets.add(_name(n.args[2]))
    missing = MUTATORS - targets
    assert not missing, f"never passed to _locked_call: {sorted(missing)}"


def test_nothing_wraps_apply_renames_which_locks_itself():
    """The lock is not re-entrant: wrapping apply_renames would deadlock
    the button for LOCK_WAIT_SECONDS and then refuse every rename."""
    for n in ast.walk(_tree()):
        if isinstance(n, ast.Call) and _name(n.func) == "_locked_call" and len(n.args) >= 3:
            assert _name(n.args[2]) != "apply_renames", f"line {n.lineno}"


def test_the_home_actions_dispatch_under_the_lock():
    fn = next(n for n in _tree().body
              if isinstance(n, ast.FunctionDef) and n.name == "render_attention")
    src = ast.unparse(fn)
    assert "_acquire_library_lock(" in src
    assert src.index("_acquire_library_lock(") < src.index("'watcher_retry'"), (
        "the lock must be taken before the action branches run")
    assert "_attn_lock.release()" in src
