"""A rename batch must not run while the watcher is filing a paper.

LibraryLock existed and had exactly ONE production user —
watcher/daemon.py:198 — while the cockpit, which produced the 8,514- and
3,842-operation rename batches in the real log, never took it at all.
The watcher runs 24/7 under KeepAlive, so the two could interleave on
the same file.

The lock is taken inside apply_renames rather than at the four cockpit
call sites, for the same reason the quality gate moved into
ingest_paper: a guard that must be remembered four times will be
forgotten once.
"""
from __future__ import annotations

import pytest

from processing.library_normalize import LOCK_WAIT_SECONDS, apply_renames
from processing.locking import LibraryLock


@pytest.fixture
def lib(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-")
    return tmp_path


class TestTheLockIsTaken:

    def test_an_uncontended_rename_works(self, lib):
        res = apply_renames(lib, [{"old": "a.pdf", "new": "b.pdf"}],
                            dry_run=False)
        assert res["renamed"] == 1
        assert (lib / "b.pdf").exists()

    def test_a_rename_is_refused_while_another_process_holds_it(
            self, lib, monkeypatch):
        """The whole point. Renaming underneath the watcher is how two
        writers come to disagree about where a file is."""
        monkeypatch.setattr(
            "processing.library_normalize.LOCK_WAIT_SECONDS", 0.5)
        other = LibraryLock(lib)
        assert other.acquire(), "could not simulate the other process"
        try:
            res = apply_renames(lib, [{"old": "a.pdf", "new": "b.pdf"}],
                                dry_run=False)
            assert res["renamed"] == 0
            # Assert what the owner needs to learn from it, not a word I
            # guessed: that nothing happened, and why.
            assert res["error"]
            assert "another process" in res["error"]
            assert "Nothing was renamed" in res["error"]
            assert (lib / "a.pdf").exists(), "the file was renamed anyway"
            assert not (lib / "b.pdf").exists()
        finally:
            other.release()

    def test_the_refusal_names_every_file_it_did_not_touch(
            self, lib, monkeypatch):
        monkeypatch.setattr(
            "processing.library_normalize.LOCK_WAIT_SECONDS", 0.5)
        other = LibraryLock(lib)
        other.acquire()
        try:
            res = apply_renames(
                lib, [{"old": "a.pdf", "new": "b.pdf"},
                      {"old": "c.pdf", "new": "d.pdf"}], dry_run=False)
            assert len(res["skipped"]) == 2
        finally:
            other.release()


class TestTheLockIsReleased:
    """A lock leaked by one batch blocks every later one, including the
    watcher — turning a transient conflict into a permanently wedged
    library."""

    def test_it_is_released_after_a_successful_batch(self, lib):
        apply_renames(lib, [{"old": "a.pdf", "new": "b.pdf"}], dry_run=False)
        probe = LibraryLock(lib)
        assert probe.acquire(), "the lock was not released"
        probe.release()

    def test_it_is_released_when_a_rename_fails(self, lib):
        """Nothing to rename, sources gone — the lock must still come
        back."""
        apply_renames(lib, [{"old": "missing.pdf", "new": "x.pdf"}],
                      dry_run=False)
        probe = LibraryLock(lib)
        assert probe.acquire(), "the lock leaked on the failure path"
        probe.release()

    def test_two_batches_in_a_row_both_work(self, lib):
        (lib / "c.pdf").write_bytes(b"%PDF-")
        assert apply_renames(lib, [{"old": "a.pdf", "new": "b.pdf"}],
                             dry_run=False)["renamed"] == 1
        assert apply_renames(lib, [{"old": "c.pdf", "new": "d.pdf"}],
                             dry_run=False)["renamed"] == 1


class TestWhatMustNotBlock:

    def test_a_dry_run_needs_no_lock(self, lib, monkeypatch):
        """A preview must work while the watcher is filing. Blocking it
        would make the safest action in the app the one most likely to
        hang."""
        monkeypatch.setattr(
            "processing.library_normalize.LOCK_WAIT_SECONDS", 0.5)
        other = LibraryLock(lib)
        other.acquire()
        try:
            res = apply_renames(lib, [{"old": "a.pdf", "new": "b.pdf"}],
                                dry_run=True)
            assert res["would_rename"] == 1
        finally:
            other.release()

    def test_a_caller_that_already_holds_it_is_not_deadlocked(self, lib):
        """flock is per open-file-description, so a second acquire in the
        SAME process on a new descriptor still conflicts. Any future
        caller holding the lock must pass lock_held."""
        held = LibraryLock(lib)
        held.acquire()
        try:
            res = apply_renames(lib, [{"old": "a.pdf", "new": "b.pdf"}],
                                dry_run=False, lock_held=True)
            assert res["renamed"] == 1
        finally:
            held.release()

    def test_the_wait_is_bounded(self):
        """LibraryLock.__enter__ blocks forever by default. A Streamlit
        button that never returns is worse than one that reports the
        library is busy."""
        assert 0 < LOCK_WAIT_SECONDS <= 120
