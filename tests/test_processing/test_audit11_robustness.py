"""Audit-11: cross-process locking, reversibility, and stuck-state nags.

Covers:
  * LibraryLock -- mutual exclusion, auto-release, context manager
  * weekly auto-apply skips when the lock is held
  * sidecar_edit undo op: reject is reversible; accept-undo restores
    the suggestion + topic_codes
  * collect_unsorted_backlog flags stale "12 - To be sorted" papers
  * publication_state CLI reset-recheck
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


# ---------------------------------------------------------------------------
# LibraryLock
# ---------------------------------------------------------------------------

class TestLibraryLock:

    def test_mutual_exclusion_nonblocking(self, tmp_path):
        from processing.locking import LibraryLock, _HAVE_FCNTL
        if not _HAVE_FCNTL:
            pytest.skip("fcntl unavailable")
        a = LibraryLock(tmp_path)
        b = LibraryLock(tmp_path)
        assert a.acquire(blocking=False) is True
        # A second handle cannot take it while A holds it.
        assert b.acquire(blocking=False) is False
        a.release()
        # Now B can.
        assert b.acquire(blocking=False) is True
        b.release()

    def test_release_is_idempotent(self, tmp_path):
        from processing.locking import LibraryLock
        a = LibraryLock(tmp_path)
        a.acquire(blocking=False)
        a.release()
        a.release()  # no raise
        assert not a.held

    def test_context_manager(self, tmp_path):
        from processing.locking import LibraryLock
        with LibraryLock(tmp_path) as lk:
            assert lk.held
        assert not lk.held

    def test_blocking_timeout_returns_false(self, tmp_path):
        from processing.locking import LibraryLock, _HAVE_FCNTL
        if not _HAVE_FCNTL:
            pytest.skip("fcntl unavailable")
        a = LibraryLock(tmp_path)
        b = LibraryLock(tmp_path)
        a.acquire(blocking=False)
        t0 = time.time()
        got = b.acquire(blocking=True, timeout=0.5)
        assert got is False
        assert time.time() - t0 >= 0.4
        a.release()


# ---------------------------------------------------------------------------
# Weekly auto-apply respects the lock
# ---------------------------------------------------------------------------

class TestWeeklyLockGuard:

    def test_auto_apply_skips_when_locked(self, tmp_path):
        from processing.locking import LibraryLock, _HAVE_FCNTL
        if not _HAVE_FCNTL:
            pytest.skip("fcntl unavailable")
        from maintenance.weekly_report import auto_apply_safe_transitions
        holder = LibraryLock(tmp_path)
        assert holder.acquire(blocking=False)
        try:
            out = auto_apply_safe_transitions(
                {"publications": {}, "aging": {}}, tmp_path, dry_run=False,
            )
            assert "skipped" in out
        finally:
            holder.release()

    def test_dry_run_ignores_lock(self, tmp_path):
        from processing.locking import LibraryLock, _HAVE_FCNTL
        if not _HAVE_FCNTL:
            pytest.skip("fcntl unavailable")
        from maintenance.weekly_report import auto_apply_safe_transitions
        holder = LibraryLock(tmp_path)
        holder.acquire(blocking=False)
        try:
            out = auto_apply_safe_transitions(
                {"publications": {}, "aging": {}}, tmp_path, dry_run=True,
            )
            # Dry run proceeds (no lock needed); not skipped.
            assert "skipped" not in out
        finally:
            holder.release()


# ---------------------------------------------------------------------------
# sidecar_edit undo op
# ---------------------------------------------------------------------------

class TestSidecarEditUndo:

    def test_reject_is_reversible(self, tmp_path):
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        from processing.publication_topic_router import reject_topic_suggestion
        from processing.undo_log import UndoLog
        enable_sidecar_mirror(tmp_path)
        pdf = tmp_path / "Smith, J. - X.pdf"
        _write_minimal_pdf(pdf, title="X", author="Smith, J.")
        ident = PaperIdentity()
        ident.topic_suggestion = "07a"
        ident.topic_confidence = 0.5
        ident.save(pdf)

        log = UndoLog(log_dir=tmp_path / ".operation_log")
        tx = log.begin_transaction("reject")
        assert reject_topic_suggestion(pdf, undo_log=log) is True
        log.commit()
        # Cleared.
        assert PaperIdentity.load(pdf).topic_suggestion == ""
        # Undo restores it.
        log.undo_transaction(tx)
        restored = PaperIdentity.load(pdf)
        assert restored.topic_suggestion == "07a"
        assert restored.topic_confidence == pytest.approx(0.5)

    def test_accept_undo_restores_suggestion_and_codes(self, tmp_path):
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        from processing.publication_topic_router import accept_topic_suggestion
        from processing.undo_log import UndoLog
        for d in ["07a - BSDEs", "03 - Working papers"]:
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        enable_sidecar_mirror(tmp_path)
        sub = tmp_path / "03 - Working papers" / "S" / "2020"
        sub.mkdir(parents=True)
        pdf = sub / "Smith, J. - X.pdf"
        _write_minimal_pdf(pdf, title="X", author="Smith, J.")
        ident = PaperIdentity()
        ident.topic_suggestion = "07a"
        ident.topic_confidence = 0.5
        ident.save(pdf)

        log = UndoLog(log_dir=tmp_path / ".operation_log")
        tx = log.begin_transaction("accept")
        ok, msg = accept_topic_suggestion(pdf, tmp_path, undo_log=log)
        assert ok, msg
        log.commit()
        moved = (tmp_path / "07a - BSDEs" / "03 - Working papers" / "S" / "2020"
                 / "Smith, J. - X.pdf")
        assert moved.exists()
        assert "07a" in PaperIdentity.load(moved).topic_codes

        # Undo: file back in working folder AND sidecar consistent
        # (suggestion restored, topic_codes reverted).
        log.undo_transaction(tx)
        assert pdf.exists()
        back = PaperIdentity.load(pdf)
        assert back.topic_suggestion == "07a"
        assert "07a" not in back.topic_codes

    def test_undo_dry_run_describes_sidecar_edit(self, tmp_path):
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        from processing.publication_topic_router import reject_topic_suggestion
        from processing.undo_log import UndoLog
        enable_sidecar_mirror(tmp_path)
        pdf = tmp_path / "Smith, J. - X.pdf"
        _write_minimal_pdf(pdf, title="X", author="Smith, J.")
        ident = PaperIdentity(); ident.topic_suggestion = "07a"; ident.save(pdf)
        log = UndoLog(log_dir=tmp_path / ".operation_log")
        tx = log.begin_transaction("reject")
        reject_topic_suggestion(pdf, undo_log=log)
        log.commit()
        actions = log.undo_transaction(tx, dry_run=True)
        assert any("WOULD RESTORE" in a["action"] for a in actions)
        # Dry run did not actually restore.
        assert PaperIdentity.load(pdf).topic_suggestion == ""


# ---------------------------------------------------------------------------
# Unsorted-backlog collector
# ---------------------------------------------------------------------------

class TestUnsortedBacklog:

    def test_flags_old_unsorted_paper(self, tmp_path):
        from ui.attention_queue import collect_unsorted_backlog
        staging = tmp_path / "12 - To be sorted" / "01 - Published papers"
        staging.mkdir(parents=True)
        old = staging / "Old, P. - Forgotten.pdf"
        _write_minimal_pdf(old, title="Forgotten", author="Old, P.")
        # Backdate mtime 40 days.
        past = time.time() - 40 * 86400
        os.utime(old, (past, past))
        items = collect_unsorted_backlog(tmp_path, max_age_days=14)
        assert len(items) == 1
        assert items[0].source == "unsorted_backlog"
        assert items[0].payload["age_days"] >= 14

    def test_ignores_fresh_unsorted_paper(self, tmp_path):
        from ui.attention_queue import collect_unsorted_backlog
        staging = tmp_path / "12 - To be sorted" / "01 - Published papers"
        staging.mkdir(parents=True)
        fresh = staging / "New, P. - Recent.pdf"
        _write_minimal_pdf(fresh, title="Recent", author="New, P.")
        items = collect_unsorted_backlog(tmp_path, max_age_days=14)
        assert items == []

    def test_registered_in_collectors(self):
        from ui.attention_queue import COLLECTORS
        assert any(name == "unsorted_backlog" for name, _ in COLLECTORS)


# ---------------------------------------------------------------------------
# publication_state CLI
# ---------------------------------------------------------------------------

class TestPublicationStateCLI:

    def test_reset_recheck_path(self, tmp_path, capsys):
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        from processing import publication_state as ps
        enable_sidecar_mirror(tmp_path)
        pdf = tmp_path / "Smith, J. - X.pdf"
        _write_minimal_pdf(pdf, title="X", author="Smith, J.")
        ident = PaperIdentity()
        ident.permanently_unpublished = True
        ident.recheck_count = 3
        ident.save(pdf)
        ps.main(["reset-recheck", str(pdf)])
        reloaded = PaperIdentity.load(pdf)
        assert reloaded.permanently_unpublished is False
        assert reloaded.recheck_count == 0
        out = capsys.readouterr().out
        assert "Reset recheck state" in out

    def test_reset_missing_file_errors(self, tmp_path):
        from processing import publication_state as ps
        with pytest.raises(SystemExit):
            ps.main(["reset-recheck", str(tmp_path / "nope.pdf")])
