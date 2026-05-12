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
