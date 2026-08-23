"""Both undo surfaces reported success without checking.

The mechanism itself is sound — 10 of 15,588 logged operations fail
under the real recovery path, 0.064%. What was wrong was what the owner
was TOLD: the preview could not fail, and the confirmation counted
refusals as successes. For a safety feature that is the whole product.
"""
from __future__ import annotations

import shutil

import pytest

from processing.undo_log import UndoLog, restore_blocker


@pytest.fixture
def log_with_three(tmp_path):
    """One operation that will undo, and two that cannot."""
    (tmp_path / "log").mkdir()
    log = UndoLog(log_dir=tmp_path / "log")
    tx = log.begin_transaction("mixed")

    good_src, good_dst = tmp_path / "a.pdf", tmp_path / "b.pdf"
    good_src.write_bytes(b"x")
    shutil.move(str(good_src), str(good_dst))
    log.record_rename(good_src, good_dst)

    # destination never existed — nothing to move back
    log.record_rename(tmp_path / "gone1.pdf", tmp_path / "gone2.pdf")

    # source is occupied by a DIFFERENT file — undoing would destroy it
    occ_src, occ_dst = tmp_path / "o1.pdf", tmp_path / "o2.pdf"
    occ_src.write_bytes(b"someone else's file")
    occ_dst.write_bytes(b"y")
    log.record_rename(occ_src, occ_dst)

    log.commit()
    return log, tx, occ_src


class TestThePreviewCanFail:
    """It could not before. The dry-run branches printed "WOULD MOVE
    BACK" for every operation without touching the filesystem, so
    previewing the oldest real transaction showed 15,588 clean rows
    while the live run fails on 10 of them. A preview that cannot fail
    is not a preview."""

    def test_the_dry_run_predicts_the_live_run_exactly(self, log_with_three):
        log, tx, _ = log_with_three
        dry = log.undo_transaction(tx, dry_run=True)
        live = log.undo_transaction(tx, dry_run=False)
        assert len(dry) == len(live)
        assert [r["ok"] for r in dry] == [r["ok"] for r in live], (
            "the preview disagreed with what actually happened")

    def test_the_dry_run_names_each_reason(self, log_with_three):
        log, tx, _ = log_with_three
        actions = [r["action"] for r in log.undo_transaction(tx, dry_run=True)]
        assert any("file gone" in a for a in actions)
        assert any("occupied" in a for a in actions)

    def test_a_dry_run_still_changes_nothing(self, log_with_three, tmp_path):
        log, tx, occ_src = log_with_three
        before = occ_src.read_bytes()
        log.undo_transaction(tx, dry_run=True)
        assert (tmp_path / "b.pdf").exists(), "the dry run moved a file"
        assert occ_src.read_bytes() == before


class TestEveryRowSaysWhetherItWorked:

    def test_no_row_is_silent_about_its_outcome(self, log_with_three):
        """A caller counting len(results) is counting rows, not successes,
        and that is how a refused undo came to report "Undid 8514 ops"."""
        log, tx, _ = log_with_three
        for row in log.undo_transaction(tx, dry_run=True):
            assert "ok" in row, row

    def test_the_counts_are_what_happened(self, log_with_three):
        log, tx, _ = log_with_three
        results = log.undo_transaction(tx, dry_run=False)
        assert len(results) == 3
        assert sum(1 for r in results if r["ok"]) == 1

    def test_an_occupied_destination_is_refused_not_overwritten(
            self, log_with_three, tmp_path):
        log, tx, occ_src = log_with_three
        log.undo_transaction(tx, dry_run=False)
        assert occ_src.read_bytes() == b"someone else's file", (
            "undo overwrote a different file that had taken the name")


class TestTheBlockerPredicate:

    def test_it_reports_no_blocker_when_the_move_would_work(self, tmp_path):
        dst = tmp_path / "there.pdf"
        dst.write_bytes(b"x")
        assert restore_blocker(dst, tmp_path / "back.pdf") == ""

    def test_a_missing_source_file_blocks(self, tmp_path):
        assert "file gone" in restore_blocker(tmp_path / "nope.pdf",
                                              tmp_path / "back.pdf")

    def test_an_occupied_target_blocks(self, tmp_path):
        dst, src = tmp_path / "d.pdf", tmp_path / "s.pdf"
        dst.write_bytes(b"x")
        src.write_bytes(b"different")
        assert "occupied" in restore_blocker(dst, src)

    def test_the_same_file_under_a_case_variant_does_not_block(self, tmp_path):
        """APFS folds case, so a rename that only changes capitalisation
        has a "target" that IS the source. Treating that as a collision
        refused 771 legitimate renames in one batch."""
        dst = tmp_path / "Paper.pdf"
        dst.write_bytes(b"x")
        assert restore_blocker(dst, tmp_path / "paper.pdf") == ""
