"""Tests for the undo log: record / commit / undo round-trips.

Critical invariants:
- A move can be undone (file goes back to source).
- A move recorded with destination=/dev/null cannot accidentally restore
  the device file over the source (historical data-loss bug).
- Multiple operations in a transaction are undone in reverse order.
- A transaction can only be undone once.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from processing.undo_log import UndoLog


@pytest.fixture
def fresh_log(tmp_path):
    """Provide a tmp UndoLog so we never write into the real .operation_log."""
    return UndoLog(log_dir=tmp_path / ".operation_log")


@pytest.fixture
def files(tmp_path):
    """Create a small file set to move around in tests."""
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    a.write_bytes(b"%PDF-A")
    b.write_bytes(b"%PDF-B")
    return {"a": a, "b": b, "tmp": tmp_path}


# ---------------------------------------------------------------------------
# Basic transactions
# ---------------------------------------------------------------------------

class TestBasicTransactions:
    def test_begin_and_commit(self, fresh_log):
        tx_id = fresh_log.begin_transaction("test")
        assert tx_id  # non-empty string
        path = fresh_log.commit()
        assert path.exists()

    def test_record_move_then_commit(self, fresh_log, files):
        tx_id = fresh_log.begin_transaction("move test")
        new_path = files["tmp"] / "moved.pdf"
        shutil.move(str(files["a"]), str(new_path))
        fresh_log.record_move(files["a"], new_path)
        log_path = fresh_log.commit()

        # Log file should contain one operation
        import json
        data = json.loads(log_path.read_text())
        assert len(data["operations"]) == 1
        assert data["operations"][0]["type"] == "move"

    def test_record_without_begin_raises(self, fresh_log, files):
        with pytest.raises(RuntimeError):
            fresh_log.record_move(files["a"], files["b"])


# ---------------------------------------------------------------------------
# Round-trip: move + undo restores file
# ---------------------------------------------------------------------------

class TestUndoRoundTrip:
    def test_undo_restores_moved_file(self, fresh_log, files):
        tx_id = fresh_log.begin_transaction("move and undo")
        target = files["tmp"] / "subdir" / "a.pdf"
        target.parent.mkdir()
        shutil.move(str(files["a"]), str(target))
        fresh_log.record_move(files["a"], target)
        fresh_log.commit()

        # Undo
        results = fresh_log.undo_transaction(tx_id)

        assert any("MOVED BACK" in r["action"] for r in results)
        assert files["a"].exists()
        assert files["a"].read_bytes() == b"%PDF-A"
        assert not target.exists()

    def test_undo_dry_run_does_not_move(self, fresh_log, files):
        tx_id = fresh_log.begin_transaction("dry undo")
        target = files["tmp"] / "moved.pdf"
        shutil.move(str(files["a"]), str(target))
        fresh_log.record_move(files["a"], target)
        fresh_log.commit()

        results = fresh_log.undo_transaction(tx_id, dry_run=True)

        assert any("WOULD MOVE BACK" in r["action"] for r in results)
        # Actually nothing changed
        assert target.exists()
        assert not files["a"].exists()

    def test_multiple_operations_undone_in_reverse(self, fresh_log, files):
        tx_id = fresh_log.begin_transaction("multi op")
        # Step 1: a -> a1
        a1 = files["tmp"] / "a1.pdf"
        shutil.move(str(files["a"]), str(a1))
        fresh_log.record_move(files["a"], a1)
        # Step 2: a1 -> a2
        a2 = files["tmp"] / "a2.pdf"
        shutil.move(str(a1), str(a2))
        fresh_log.record_move(a1, a2)
        fresh_log.commit()

        results = fresh_log.undo_transaction(tx_id)

        # After reverse-order undo: a2 -> a1, then a1 -> original 'a'
        assert files["a"].exists()
        assert files["a"].read_bytes() == b"%PDF-A"
        assert not a1.exists()
        assert not a2.exists()

    def test_cannot_undo_twice(self, fresh_log, files):
        tx_id = fresh_log.begin_transaction("once")
        target = files["tmp"] / "moved.pdf"
        shutil.move(str(files["a"]), str(target))
        fresh_log.record_move(files["a"], target)
        fresh_log.commit()

        fresh_log.undo_transaction(tx_id)
        with pytest.raises(ValueError):
            fresh_log.undo_transaction(tx_id)


# ---------------------------------------------------------------------------
# /dev/null safeguard — historical data-loss bug
# ---------------------------------------------------------------------------

class TestDevNullSafeguard:
    def test_undo_refuses_devnull_move(self, fresh_log, files):
        """A move recorded as src→/dev/null must NOT actually move the device file.

        Before the fix, ``undo_transaction`` would call
        ``shutil.move("/dev/null", source)`` because /dev/null "exists",
        either erroring out destructively or replacing the source with the
        device file. The fix recognises /dev/null and other special devices
        and returns a CANNOT UNDO message instead of moving anything.
        """
        tx_id = fresh_log.begin_transaction("simulated delete via dev/null")
        # NOTE: we don't actually move the file — we just record what a
        # buggy caller might have recorded.
        fresh_log.record_move(files["a"], Path("/dev/null"))
        fresh_log.commit()

        original_a_content = files["a"].read_bytes()

        results = fresh_log.undo_transaction(tx_id)

        assert any("CANNOT UNDO" in r["action"] for r in results)
        # Source file was NOT touched
        assert files["a"].exists()
        assert files["a"].read_bytes() == original_a_content
        # /dev/null is still /dev/null (we wouldn't be running otherwise)
        assert Path("/dev/null").exists()

    def test_undo_refuses_other_special_devices(self, fresh_log, files):
        for special in ("/dev/zero", "/dev/random", "/dev/urandom"):
            tx_id = fresh_log.begin_transaction(f"to {special}")
            fresh_log.record_move(files["a"], Path(special))
            fresh_log.commit()
            results = fresh_log.undo_transaction(tx_id)
            assert any("CANNOT UNDO" in r["action"] for r in results), (
                f"Should refuse {special}"
            )


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

class TestListing:
    def test_list_empty(self, fresh_log):
        assert fresh_log.list_transactions() == []

    def test_list_after_commits(self, fresh_log):
        for desc in ["t1", "t2", "t3"]:
            fresh_log.begin_transaction(desc)
            fresh_log.commit()
        txs = fresh_log.list_transactions()
        assert len(txs) == 3
        assert {t["description"] for t in txs} == {"t1", "t2", "t3"}


class TestNeverWritesToTheRealLibrary:
    """A test run must not land in the owner's real undo history.

    ``UndoLog.__init__`` used to default to a module-level ``LOG_DIR``
    computed at IMPORT time, so pointing MATH_LIBRARY elsewhere
    afterwards had no effect.  Helpers that build their own UndoLog deep
    inside (bulk_sort, process_report, bulk_apply) therefore wrote to the
    real library during tests: 342 of the 357 entries in his history were
    test junk, burying the 15 real ones and making Activity useless.
    """

    def test_default_log_dir_follows_the_environment(self, tmp_path, monkeypatch):
        from processing.undo_log import UndoLog
        monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
        log = UndoLog()
        assert tmp_path in log.log_dir.parents or log.log_dir.parent == tmp_path, \
            f"UndoLog wrote to {log.log_dir}, not under {tmp_path}"

    def test_conftest_points_every_test_at_a_throwaway_library(self):
        # The autouse guard in tests/conftest.py must actually be active,
        # so even a test that never thinks about paths is safe.
        import os
        from pathlib import Path
        root = os.environ.get("MATH_LIBRARY", "")
        assert root, "MATH_LIBRARY is unset — the conftest guard is not running"
        assert "library" in Path(root).name or "/T/" in root or "tmp" in root.lower(), \
            f"MATH_LIBRARY points at {root!r}, which may be the real library"


class TestUndoNeverOverwritesAnOccupant:
    """Restoring a file on top of a different file destroys a paper to
    recover another — the one thing an undo must never do.

    `logged_rename` already refuses this. The UNDO path did not: it
    checked only `dst.exists()` and called shutil.move. 15 recorded
    operations across two real transactions would take that branch.
    """

    def test_it_refuses_and_says_why(self, tmp_path):
        from processing.undo_log import UndoLog, logged_move
        lib = tmp_path
        (lib / "a").mkdir(); (lib / "b").mkdir()
        paper = lib / "a" / "paper.pdf"
        paper.write_bytes(b"%PDF-1.4 ORIGINAL")

        log = UndoLog(log_dir=lib / ".operation_log")
        tx = log.begin_transaction("move it away")
        logged_move(paper, lib / "b" / "paper.pdf", undo_log=log)
        log.commit()

        # a DIFFERENT paper now occupies the old path
        intruder = lib / "a" / "paper.pdf"
        intruder.write_bytes(b"%PDF-1.4 SOMEONE ELSE")

        res = log.undo_transaction(tx)
        assert intruder.read_bytes() == b"%PDF-1.4 SOMEONE ELSE", \
            "the occupant was destroyed"
        assert (lib / "b" / "paper.pdf").exists(), "the moved file still exists"
        assert any("CANNOT UNDO" in str(r) for r in res), res

    def test_the_ordinary_case_still_works(self, tmp_path):
        from processing.undo_log import UndoLog, logged_move
        lib = tmp_path
        (lib / "a").mkdir(); (lib / "b").mkdir()
        paper = lib / "a" / "paper.pdf"
        paper.write_bytes(b"%PDF-1.4 ORIGINAL")
        log = UndoLog(log_dir=lib / ".operation_log")
        tx = log.begin_transaction("move it away")
        logged_move(paper, lib / "b" / "paper.pdf", undo_log=log)
        log.commit()
        log.undo_transaction(tx)
        assert paper.exists() and paper.read_bytes() == b"%PDF-1.4 ORIGINAL"


class TestTheUndoGuaranteeItself:
    """The seven holes. Each test fails if its fix is reverted."""

    def _log(self, tmp_path):
        from processing.undo_log import UndoLog
        return UndoLog(log_dir=tmp_path / ".operation_log")

    # ---- hole 1: nothing reached disk until commit() --------------------
    def test_operations_are_on_disk_before_commit(self, tmp_path):
        """A SIGKILL mid-batch used to lose the WHOLE record; the largest
        real transaction holds 8,514 operations."""
        log = self._log(tmp_path)
        tx = log.begin_transaction("big batch")
        log.record_move(tmp_path / "a.pdf", tmp_path / "b.pdf")
        journal = (tmp_path / ".operation_log" / f"{tx}.journal.jsonl")
        assert journal.exists(), "the operation must be durable immediately"
        assert "a.pdf" in journal.read_text()

    def test_a_crashed_run_is_recovered_into_a_real_transaction(self, tmp_path):
        log = self._log(tmp_path)
        tx = log.begin_transaction("interrupted")
        log.record_move(tmp_path / "a.pdf", tmp_path / "b.pdf")
        log.record_move(tmp_path / "c.pdf", tmp_path / "d.pdf")
        # simulate SIGKILL: drop the object without commit()
        del log
        fresh = self._log(tmp_path)
        assert fresh.recover_journals() == [tx]
        ids = [t["id"] for t in fresh.list_transactions()]
        assert tx in ids
        rec = [t for t in fresh.list_transactions() if t["id"] == tx][0]
        assert rec["operations_count"] == 2

    def test_a_torn_final_line_does_not_lose_the_rest(self, tmp_path):
        log = self._log(tmp_path)
        tx = log.begin_transaction("interrupted")
        log.record_move(tmp_path / "a.pdf", tmp_path / "b.pdf")
        j = tmp_path / ".operation_log" / f"{tx}.journal.jsonl"
        j.write_text(j.read_text() + '{"type": "move", "sou')
        fresh = self._log(tmp_path)
        assert fresh.recover_journals() == [tx]

    def test_committing_removes_the_journal(self, tmp_path):
        log = self._log(tmp_path)
        tx = log.begin_transaction("done")
        log.record_move(tmp_path / "a.pdf", tmp_path / "b.pdf")
        log.commit()
        assert not (tmp_path / ".operation_log" / f"{tx}.journal.jsonl").exists()

    # ---- hole 2: a partial undo burned the transaction -----------------
    def test_a_partial_undo_stays_retryable(self, tmp_path):
        from processing.undo_log import logged_move
        lib = tmp_path
        (lib / "a").mkdir(); (lib / "b").mkdir()
        p1 = lib / "a" / "one.pdf"; p1.write_bytes(b"%PDF-1")
        p2 = lib / "a" / "two.pdf"; p2.write_bytes(b"%PDF-2")
        log = self._log(tmp_path)
        tx = log.begin_transaction("move both")
        logged_move(p1, lib / "b" / "one.pdf", undo_log=log)
        logged_move(p2, lib / "b" / "two.pdf", undo_log=log)
        log.commit()
        (lib / "b" / "one.pdf").unlink()            # one leg becomes unreversible
        log.undo_transaction(tx)
        rec = [t for t in log.list_transactions() if t["id"] == tx][0]
        assert rec.get("undone") is False, "a partial undo must not burn the tx"
        # the other leg really did come back
        assert (lib / "a" / "two.pdf").exists()

    def test_a_complete_undo_is_marked_done(self, tmp_path):
        from processing.undo_log import logged_move
        lib = tmp_path
        (lib / "a").mkdir(); (lib / "b").mkdir()
        p = lib / "a" / "one.pdf"; p.write_bytes(b"%PDF-1")
        log = self._log(tmp_path)
        tx = log.begin_transaction("move")
        logged_move(p, lib / "b" / "one.pdf", undo_log=log)
        log.commit()
        log.undo_transaction(tx)
        rec = [t for t in log.list_transactions() if t["id"] == tx][0]
        assert rec.get("undone") is True

    # ---- hole 3: discard() threw away work already done ----------------
    def test_discard_refuses_to_drop_recorded_work(self, tmp_path):
        log = self._log(tmp_path)
        tx = log.begin_transaction("partial")
        log.record_move(tmp_path / "a.pdf", tmp_path / "b.pdf")
        log.discard()
        ids = [t["id"] for t in log.list_transactions()]
        assert tx in ids, "work already on disk must stay undoable"

    def test_discard_still_drops_an_empty_transaction(self, tmp_path):
        log = self._log(tmp_path)
        tx = log.begin_transaction("nothing happened")
        log.discard()
        assert tx not in [t["id"] for t in log.list_transactions()]


class TestSidecarEditsAreReversible:
    """A sidecar carries a paper's identity — DOI, arXiv id,
    first-ingested date, cached text. Rewriting one is a mutation of the
    owner's data just as much as moving the file, yet every writer
    bypassed the undo log; a bulk pass over 300 sidecars was
    irreversible."""

    def test_an_edit_is_recorded_and_restorable(self, tmp_path):
        from processing.identity import PaperIdentity
        from processing.undo_log import UndoLog
        pdf = tmp_path / "Smith, J. - A paper.pdf"
        pdf.write_bytes(b"%PDF-1.4 x")
        ident = PaperIdentity(original_filename=pdf.name, doi="10.1000/original")
        ident.save(pdf)

        log = UndoLog(log_dir=tmp_path / ".operation_log")
        tx = log.begin_transaction("edit identity")
        ident.doi = "10.1000/CHANGED"
        ident.save(pdf, recompute_hash=False, undo_log=log)
        log.commit()

        assert PaperIdentity.load(pdf).doi == "10.1000/CHANGED"
        log.undo_transaction(tx)
        assert PaperIdentity.load(pdf).doi == "10.1000/original"

    def test_no_transaction_means_no_change_in_behaviour(self, tmp_path):
        from processing.identity import PaperIdentity
        pdf = tmp_path / "Smith, J. - B paper.pdf"
        pdf.write_bytes(b"%PDF-1.4 y")
        i = PaperIdentity(original_filename=pdf.name, doi="10.1/a")
        i.save(pdf)
        i.doi = "10.1/b"
        i.save(pdf, recompute_hash=False)          # undo_log omitted
        assert PaperIdentity.load(pdf).doi == "10.1/b"

    def test_an_unchanged_save_records_nothing(self, tmp_path):
        from processing.identity import PaperIdentity
        from processing.undo_log import UndoLog
        pdf = tmp_path / "Smith, J. - C paper.pdf"
        pdf.write_bytes(b"%PDF-1.4 z")
        i = PaperIdentity(original_filename=pdf.name, doi="10.1/a")
        i.save(pdf)
        log = UndoLog(log_dir=tmp_path / ".operation_log")
        log.begin_transaction("no-op")
        i.save(pdf, recompute_hash=False, undo_log=log)
        assert not log.has_operations()


class TestBulkSidecarPassesAreReversible:
    """The two passes that rewrite identity across the whole library.

    Both mutated doi/arxiv_id on hundreds of sidecars with no undo record
    at all — and clear_collection_dois DELETES a field, which is how 228
    polluted records were cleaned irreversibly.
    """

    def _lib(self, tmp_path):
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        lib = tmp_path / "lib"
        (lib / "01 - Published papers" / "S").mkdir(parents=True)
        enable_sidecar_mirror(lib)
        pdf = lib / "01 - Published papers" / "S" / "Smith, J. - A paper.pdf"
        pdf.write_bytes(b"%PDF-1.4 content")
        return lib, pdf, PaperIdentity

    def test_clearing_a_doi_can_be_undone(self, tmp_path):
        from processing.preprint_variants import clear_collection_dois
        from processing.undo_log import UndoLog
        lib, pdf, PI = self._lib(tmp_path)
        i = PI(original_filename=pdf.name, doi="10.1007/978-3-540-48831-6")
        i.save(pdf)

        res = clear_collection_dois(lib, dry_run=False)
        assert res["cleared"] == 1
        assert PI.load(pdf).doi == ""

        log = UndoLog(log_dir=lib / ".operation_log")
        txs = log.list_transactions()
        assert txs, "the bulk pass must leave a transaction"
        log.undo_transaction(txs[0]["id"])
        assert PI.load(pdf).doi == "10.1007/978-3-540-48831-6", "the DOI must come back"

    def test_a_dry_run_opens_no_transaction(self, tmp_path):
        from processing.preprint_variants import clear_collection_dois
        from processing.undo_log import UndoLog
        lib, pdf, PI = self._lib(tmp_path)
        PI(original_filename=pdf.name, doi="10.1007/978-3-540-48831-6").save(pdf)
        clear_collection_dois(lib, dry_run=True)
        assert not UndoLog(log_dir=lib / ".operation_log").list_transactions()

    def test_a_pass_that_changes_nothing_leaves_no_empty_transaction(self, tmp_path):
        """An empty tx shows in the Activity tab with a live Undo button."""
        from processing.preprint_variants import clear_collection_dois
        from processing.undo_log import UndoLog
        lib, pdf, PI = self._lib(tmp_path)
        PI(original_filename=pdf.name, doi="").save(pdf)
        clear_collection_dois(lib, dry_run=False)
        assert not UndoLog(log_dir=lib / ".operation_log").list_transactions()
