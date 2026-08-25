"""Undoing a copy must not hard-delete, and must refuse when it is the last one.

This branch has already cost a paper. Transaction 9b9d5b2f584e, in a SECOND
undo log inside the repository that the cockpit cannot see, records

    move  03 - Working papers/A/2023/Abraham, R., Delmas, J.-F., Weibel, J. -
          Probability-graphons, limits of large dense weighted graphs.pdf
          →  /dev/null

That file is gone from its working-papers shelf and from its intended home in
01 - Published papers/Z. The only reason the paper still exists is an
accidental copy under 07e - Optimal control on networks.

It was the one hard delete of a library PDF anywhere in src/.
"""
import os

import pytest

from processing.undo_log import UndoLog, logged_copy


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "Maths"
    (root / "01 - Published papers").mkdir(parents=True)
    monkeypatch.setenv("MATH_LIBRARY", str(root))
    return root


def _copy_and_commit(root, src_name, dst_name):
    src = root / "01 - Published papers" / src_name
    dst = root / "01 - Published papers" / dst_name
    src.write_bytes(b"%PDF-1.4\n")
    log = UndoLog(log_dir=root / ".operation_log")
    tx = log.begin_transaction("copy")
    logged_copy(src, dst, undo_log=log)
    log.commit()
    return log, tx, src, dst


class TestItRetiresRatherThanDeletes:
    def test_the_copy_ends_up_in_trash_not_gone(self, library):
        log, tx, src, dst = _copy_and_commit(library, "Orig, A. - A paper.pdf", "copy.pdf")
        log.undo_transaction(tx, dry_run=False)

        assert not dst.exists(), "the copy should have moved"
        retired = library / ".trash" / "undone_copies" / "copy.pdf"
        assert retired.exists(), "the copy was DELETED instead of retired"
        assert retired.read_bytes() == b"%PDF-1.4\n"

    def test_two_undone_copies_of_one_name_do_not_collide(self, library):
        """Overwriting in the trash would make two retirements into one."""
        for i in range(2):
            log, tx, src, dst = _copy_and_commit(
                library, f"Orig{i}, A. - A paper.pdf", "same-name.pdf")
            log.undo_transaction(tx, dry_run=False)
        trash = library / ".trash" / "undone_copies"
        assert len(list(trash.iterdir())) == 2, list(trash.iterdir())

    def test_the_result_row_says_retired_and_is_ok(self, library):
        log, tx, src, dst = _copy_and_commit(library, "Orig, A. - A paper.pdf", "copy.pdf")
        rows = log.undo_transaction(tx, dry_run=False)
        rows = rows if isinstance(rows, list) else rows.get("results", [])
        assert any("RETIRED COPY" in r.get("action", "") for r in rows), rows
        assert all(r.get("ok") for r in rows), rows


class TestItRefusesWhenTheCopyIsTheLastOne:
    def test_the_sole_remaining_version_is_not_touched(self, library):
        """Undoing a copy means "remove the duplicate". With the original
        gone it means "remove the only version", which is the shape of the
        loss that actually happened."""
        log, tx, src, dst = _copy_and_commit(
            library, "Only, B. - Sole copy.pdf", "sole_copy.pdf")
        src.unlink()

        rows = log.undo_transaction(tx, dry_run=False)
        rows = rows if isinstance(rows, list) else rows.get("results", [])

        assert dst.exists(), "the last remaining version was removed"
        assert any("REFUSED" in r.get("action", "") for r in rows), rows

    def test_the_refusal_is_reported_as_not_ok(self, library):
        """"I refused" and "I did it" must not be the same return value."""
        log, tx, src, dst = _copy_and_commit(
            library, "Only, B. - Sole copy.pdf", "sole_copy.pdf")
        src.unlink()
        rows = log.undo_transaction(tx, dry_run=False)
        rows = rows if isinstance(rows, list) else rows.get("results", [])
        refusals = [r for r in rows if "REFUSED" in r.get("action", "")]
        assert refusals and not any(r.get("ok") for r in refusals), rows

    def test_nothing_is_written_to_trash_when_it_refuses(self, library):
        log, tx, src, dst = _copy_and_commit(
            library, "Only, B. - Sole copy.pdf", "sole_copy.pdf")
        src.unlink()
        log.undo_transaction(tx, dry_run=False)
        trash = library / ".trash" / "undone_copies"
        assert not trash.exists() or not list(trash.iterdir())


class TestNothingInSrcHardDeletesALibraryPdf:
    def test_no_unlink_survives_in_the_undo_path(self):
        """A grep-level guard. If someone reintroduces a bare unlink() in the
        undo path, this fails before it reaches the library."""
        import pathlib
        src = (pathlib.Path(__file__).resolve().parents[2]
               / "src" / "processing" / "undo_log.py").read_text()
        offenders = [ln.strip() for ln in src.splitlines()
                     if ".unlink()" in ln and not ln.strip().startswith("#")]
        assert offenders == [], offenders
