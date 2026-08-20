"""Guard tests for the undo log — the owner's only guarantee.

Every test here is written against a POSTCONDITION: what must be true of
the bytes on disk after the call. None of them asserts "the helper was
called" or "the branch was taken", because that is exactly the kind of
test that let a re-armed ``path.unlink()`` sail through the suite.

Each test in this file has been shown FAILING against a specific
mutation of the guard it protects (see the task report). If you weaken a
guard in ``src/processing/undo_log.py`` or ``src/processing/identity.py``
and this file stays green, the test is broken, not the mutation.

Naming: tests are named after the damage they prevent, not the function
they call.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return p


def _names(d: Path) -> set[str]:
    """Real on-disk basenames. ``Path.exists`` is case-blind on APFS."""
    return set(os.listdir(d))


def _fs_is_case_insensitive(tmp_path: Path) -> bool:
    probe = tmp_path / "CaseProbe.tmp"
    probe.write_text("x")
    try:
        return (tmp_path / "caseprobe.tmp").exists()
    finally:
        probe.unlink()


@pytest.fixture()
def logdir(tmp_path):
    d = tmp_path / "oplog"
    d.mkdir()
    return d


@pytest.fixture()
def log(logdir):
    from processing.undo_log import UndoLog
    return UndoLog(log_dir=logdir)


@pytest.fixture()
def lib(tmp_path):
    """A library root with the sidecar mirror enabled (the shipped layout)."""
    from processing.identity import enable_sidecar_mirror
    root = tmp_path / "lib"
    (root / "01 - Published papers").mkdir(parents=True)
    (root / "03 - Working papers").mkdir(parents=True)
    enable_sidecar_mirror(root)
    return root


# ===========================================================================
# 1. _restore: never overwrite whatever now occupies the original path
# ===========================================================================

class TestUndoNeverOverwritesAnOccupant:
    """``_restore`` refuses when ``src`` is occupied by a DIFFERENT file.

    Both branches matter: renames are 14,697 of the 15,314 operations in
    the real log, so a guard that only covers ``move`` covers 4% of the
    owner's history.
    """

    def test_undoing_a_move_leaves_a_new_occupant_byte_identical(self, tmp_path, log):
        old = _write(tmp_path / "old" / "paper.pdf", "ORIGINAL-PAPER-BYTES")
        new = tmp_path / "new" / "paper.pdf"

        from processing.undo_log import logged_move
        log.begin_transaction("file it")
        logged_move(old, new, undo_log=log)
        tx = log._tx_id
        log.commit()

        # Something else now lives at the old path (a re-download, a
        # different paper the owner put there by hand).
        occupant = _write(tmp_path / "old" / "paper.pdf", "SOMEONE-ELSES-BYTES")

        results = log.undo_transaction(tx)

        # THE postcondition: the occupant's bytes are still on disk.
        assert occupant.read_bytes() == b"SOMEONE-ELSES-BYTES"
        # ...and the thing we refused to move is still where it was, so
        # nothing was lost in either direction.
        assert new.read_bytes() == b"ORIGINAL-PAPER-BYTES"
        assert any(str(r["action"]).startswith("CANNOT UNDO") for r in results)

    def test_undoing_a_rename_leaves_a_new_occupant_byte_identical(self, tmp_path, log):
        old = _write(tmp_path / "d" / "Smith, J. - Old title.pdf", "ORIGINAL-PAPER-BYTES")
        new = tmp_path / "d" / "Smith, J. - New title.pdf"

        from processing.undo_log import logged_rename
        log.begin_transaction("rename it")
        logged_rename(old, new, undo_log=log)
        tx = log._tx_id
        log.commit()

        occupant = _write(tmp_path / "d" / "Smith, J. - Old title.pdf",
                          "SOMEONE-ELSES-BYTES")

        results = log.undo_transaction(tx)

        assert occupant.read_bytes() == b"SOMEONE-ELSES-BYTES"
        assert new.read_bytes() == b"ORIGINAL-PAPER-BYTES"
        assert any(str(r["action"]).startswith("CANNOT UNDO") for r in results)

    def test_a_partially_undoable_transaction_does_not_lose_the_rest(self, tmp_path, log):
        """A refusal on one op must not stop the others coming home."""
        a = _write(tmp_path / "a.pdf", "AAA")
        c = _write(tmp_path / "c.pdf", "CCC")
        a2, c2 = tmp_path / "moved" / "a.pdf", tmp_path / "moved" / "c.pdf"

        from processing.undo_log import logged_move
        log.begin_transaction("batch")
        logged_move(a, a2, undo_log=log)
        logged_move(c, c2, undo_log=log)
        tx = log._tx_id
        log.commit()

        _write(tmp_path / "a.pdf", "OCCUPIED")   # blocks the first op only

        log.undo_transaction(tx)

        assert (tmp_path / "a.pdf").read_bytes() == b"OCCUPIED"
        assert c.read_bytes() == b"CCC"          # the other one came back


class TestUndoOfAMissingFileIsSkippedNotFatal:

    def test_a_vanished_destination_does_not_abort_the_rest_of_the_undo(
            self, tmp_path, log):
        a = _write(tmp_path / "a.pdf", "AAA")
        c = _write(tmp_path / "c.pdf", "CCC")
        a2, c2 = tmp_path / "moved" / "a.pdf", tmp_path / "moved" / "c.pdf"

        from processing.undo_log import logged_move
        log.begin_transaction("batch")
        logged_move(a, a2, undo_log=log)
        logged_move(c, c2, undo_log=log)
        tx = log._tx_id
        log.commit()

        c2.unlink()   # the owner deleted it in Finder afterwards

        results = log.undo_transaction(tx)   # must not raise

        assert a.read_bytes() == b"AAA"      # the survivor still came home
        assert any(str(r["action"]).startswith("SKIP") for r in results)

    def test_undo_recreates_the_folder_the_move_emptied(self, tmp_path, log):
        """Filing the last paper out of a topic folder often leaves it
        empty, and empty folders get cleaned up. Undo must rebuild the
        path, not fail because the parent is gone."""
        from processing.undo_log import logged_move
        src = _write(tmp_path / "07a - BSDEs" / "p.pdf", "PAPER")
        dst = tmp_path / "01 - Published papers" / "p.pdf"

        log.begin_transaction("refile")
        logged_move(src, dst, undo_log=log)
        tx = log._tx_id
        log.commit()

        (tmp_path / "07a - BSDEs").rmdir()          # the emptied folder is gone

        log.undo_transaction(tx)

        assert src.read_bytes() == b"PAPER"


# ===========================================================================
# 2. The APFS same-file check: a case-only rename is NOT a clobber
# ===========================================================================

class TestCaseOnlyRenamesAreNotTreatedAsClobbers:
    """``_is_same_file`` asks the filesystem instead of comparing strings.

    On a case-insensitive volume ``Space-time.pdf`` and ``space-time.pdf``
    are the same inode; a string comparison made every capitalisation fix
    look like it would destroy another paper. This silently blocked 771
    renames once already.
    """

    def test_a_capitalisation_fix_is_performed_not_refused(self, tmp_path, log):
        if not _fs_is_case_insensitive(tmp_path):
            pytest.skip("case-sensitive filesystem: no same-file collision")
        d = tmp_path / "d"
        old = _write(d / "space-time tradeoffs.pdf", "PAPER")
        new = d / "Space-Time Tradeoffs.pdf"

        from processing.undo_log import logged_rename
        log.begin_transaction("case fix")
        logged_rename(old, new, undo_log=log)

        assert "Space-Time Tradeoffs.pdf" in _names(d)
        assert (d / "Space-Time Tradeoffs.pdf").read_bytes() == b"PAPER"

    def test_undoing_a_capitalisation_fix_restores_the_old_casing(self, tmp_path, log):
        if not _fs_is_case_insensitive(tmp_path):
            pytest.skip("case-sensitive filesystem: no same-file collision")
        d = tmp_path / "d"
        old = _write(d / "space-time tradeoffs.pdf", "PAPER")
        new = d / "Space-Time Tradeoffs.pdf"

        from processing.undo_log import logged_rename
        log.begin_transaction("case fix")
        logged_rename(old, new, undo_log=log)
        tx = log._tx_id
        log.commit()

        log.undo_transaction(tx)

        # POSTCONDITION on the bytes AND on the real basename: undo of a
        # case-only rename must actually put the old spelling back, not
        # bail out with CANNOT UNDO because src "exists".
        assert "space-time tradeoffs.pdf" in _names(d)
        assert (d / "space-time tradeoffs.pdf").read_bytes() == b"PAPER"


# ===========================================================================
# 3. logged_move / logged_rename refuse an occupied destination
# ===========================================================================

class TestAMoveNeverClobbersTheDestination:

    def test_logged_move_leaves_both_files_intact_when_the_target_is_taken(
            self, tmp_path, log):
        src = _write(tmp_path / "in" / "p.pdf", "INCOMING")
        dst = _write(tmp_path / "out" / "p.pdf", "ALREADY-THERE")

        from processing.undo_log import logged_move
        log.begin_transaction("t")
        with pytest.raises(FileExistsError):
            logged_move(src, dst, undo_log=log)

        assert dst.read_bytes() == b"ALREADY-THERE"
        assert src.read_bytes() == b"INCOMING"

    def test_logged_rename_leaves_both_files_intact_when_the_target_is_taken(
            self, tmp_path, log):
        """``Path.rename`` clobbers silently on POSIX — the guard is the
        only thing between two papers and one surviving."""
        src = _write(tmp_path / "d" / "a.pdf", "PAPER-A")
        dst = _write(tmp_path / "d" / "b.pdf", "PAPER-B")

        from processing.undo_log import logged_rename
        log.begin_transaction("t")
        with pytest.raises(FileExistsError):
            logged_rename(src, dst, undo_log=log)

        assert dst.read_bytes() == b"PAPER-B"
        assert src.read_bytes() == b"PAPER-A"

    def test_a_refused_move_records_no_phantom_operation(self, tmp_path, log):
        """A recorded op for a move that never happened is a booby trap:
        undo would later move the destination somewhere it never was."""
        src = _write(tmp_path / "in" / "p.pdf", "INCOMING")
        dst = _write(tmp_path / "out" / "p.pdf", "ALREADY-THERE")

        from processing.undo_log import logged_move
        log.begin_transaction("t")
        with pytest.raises(FileExistsError):
            logged_move(src, dst, undo_log=log)
        assert not log.has_operations()

    def test_logged_copy_leaves_both_files_intact_when_the_target_is_taken(
            self, tmp_path, log):
        src = _write(tmp_path / "in" / "p.pdf", "CANONICAL")
        dst = _write(tmp_path / "07a - BSDEs" / "p.pdf", "ALREADY-THERE")

        from processing.undo_log import logged_copy
        log.begin_transaction("t")
        with pytest.raises(FileExistsError):
            logged_copy(src, dst, undo_log=log)

        assert dst.read_bytes() == b"ALREADY-THERE"
        assert src.read_bytes() == b"CANONICAL"
        # A phantom copy op would make undo DELETE the occupant.
        assert not log.has_operations()

    def test_a_move_from_a_missing_source_records_no_phantom_operation(
            self, tmp_path, log):
        from processing.undo_log import logged_move
        log.begin_transaction("t")
        with pytest.raises(FileNotFoundError):
            logged_move(tmp_path / "nope.pdf", tmp_path / "out.pdf", undo_log=log)
        assert not log.has_operations()

    def test_a_rename_from_a_missing_source_records_no_phantom_operation(
            self, tmp_path, log):
        from processing.undo_log import logged_rename
        log.begin_transaction("t")
        with pytest.raises(FileNotFoundError):
            logged_rename(tmp_path / "nope.pdf", tmp_path / "new.pdf", undo_log=log)
        assert not log.has_operations()

    def test_a_file_is_never_moved_before_the_record_exists(self, tmp_path, logdir):
        """Record-then-move, never move-then-record.

        If recording fails (here: no open transaction) the file must not
        have moved, otherwise the owner has an unrecorded, unreversible
        change on disk.
        """
        from processing.undo_log import UndoLog, logged_move
        unopened = UndoLog(log_dir=logdir)      # begin_transaction NOT called
        src = _write(tmp_path / "in" / "p.pdf", "INCOMING")
        dst = tmp_path / "out" / "p.pdf"

        with pytest.raises(RuntimeError):
            logged_move(src, dst, undo_log=unopened)

        assert src.read_bytes() == b"INCOMING"
        assert not dst.exists()


# ===========================================================================
# 4. The sidecar-clobber refusal
# ===========================================================================

class TestAPapersIdentityIsNeverOverwrittenByAnotherPapers:
    """A sidecar carries the DOI, arXiv id, ingest date and cached text.
    Moving a PDF onto a free name whose SIDECAR is taken must not
    silently overwrite that other paper's identity.
    """

    def test_logged_move_refuses_when_the_destination_sidecar_is_occupied(
            self, lib, log):
        from processing.identity import PaperIdentity, sidecar_path, load_sidecar
        from processing.undo_log import logged_move

        src = _write(lib / "03 - Working papers" / "Mine.pdf", "MINE")
        PaperIdentity(doi="10.1/MINE").save(src, recompute_hash=False)

        dst = lib / "01 - Published papers" / "Mine.pdf"
        # An orphaned sidecar for a different paper sits at the target.
        ghost = _write(lib / "01 - Published papers" / "Ghost.pdf", "GHOST")
        PaperIdentity(doi="10.2/GHOST").save(ghost, recompute_hash=False)
        # Re-home the ghost's sidecar onto the destination name.
        sidecar_path(dst).parent.mkdir(parents=True, exist_ok=True)
        sidecar_path(dst).write_text(sidecar_path(ghost).read_text())

        log.begin_transaction("t")
        with pytest.raises(FileExistsError):
            logged_move(src, dst, undo_log=log)

        # POSTCONDITION: the occupied identity is byte-for-byte untouched
        # and the mover is still at home with its own identity.
        assert json.loads(sidecar_path(dst).read_text())["doi"] == "10.2/GHOST"
        assert src.read_bytes() == b"MINE"
        assert load_sidecar(src).doi == "10.1/MINE"

    def test_logged_rename_refuses_when_the_destination_sidecar_is_occupied(
            self, lib, log):
        from processing.identity import PaperIdentity, sidecar_path, load_sidecar
        from processing.undo_log import logged_rename

        d = lib / "03 - Working papers"
        src = _write(d / "Old name.pdf", "MINE")
        PaperIdentity(doi="10.1/MINE").save(src, recompute_hash=False)

        dst = d / "New name.pdf"
        ghost = _write(d / "Ghost.pdf", "GHOST")
        PaperIdentity(doi="10.2/GHOST").save(ghost, recompute_hash=False)
        sidecar_path(dst).parent.mkdir(parents=True, exist_ok=True)
        sidecar_path(dst).write_text(sidecar_path(ghost).read_text())

        log.begin_transaction("t")
        with pytest.raises(FileExistsError):
            logged_rename(src, dst, undo_log=log)

        assert json.loads(sidecar_path(dst).read_text())["doi"] == "10.2/GHOST"
        assert src.read_bytes() == b"MINE"
        assert load_sidecar(src).doi == "10.1/MINE"

    def test_moving_a_non_pdf_does_not_drag_a_pdfs_sidecar_away(self, tmp_path, log):
        """``_maybe_sidecar_pair`` only attaches sidecars to PDFs.

        Without that check, moving ``notes.txt`` next to ``notes.pdf``
        would steal ``notes.meta.json`` — the PDF's identity — because
        ``with_suffix('.meta.json')`` resolves to the same file.
        """
        from processing.identity import PaperIdentity, sidecar_path, load_sidecar
        from processing.undo_log import logged_move

        d = tmp_path / "d"
        pdf = _write(d / "notes.pdf", "PAPER")
        PaperIdentity(doi="10.9/KEEP").save(pdf, recompute_hash=False)
        side = sidecar_path(pdf)
        assert side.exists()

        txt = _write(d / "notes.txt", "just notes")
        log.begin_transaction("t")
        logged_move(txt, tmp_path / "elsewhere" / "notes.txt", undo_log=log)

        assert side.exists(), "the PDF's sidecar was dragged away by a .txt move"
        assert load_sidecar(pdf).doi == "10.9/KEEP"


# ===========================================================================
# 5. The byte-length limit on sidecar names
# ===========================================================================

class TestOverlongNamesStillGetASidecarThatTheFilesystemAccepts:
    """Filenames are capped in BYTES, not characters.

    A 125-character accented title is 250 bytes; adding ``.meta.json``
    makes 260 — over the 255-byte APFS/ext4 limit. If the cap is
    measured in characters, or removed, the write raises ENAMETOOLONG
    and the paper silently ends up with no identity at all.
    """

    LONG_STEM = "é" * 125          # 250 bytes, 125 characters

    def test_the_resolved_sidecar_name_fits_the_filesystem(self, tmp_path):
        from processing.identity import sidecar_path
        pdf = tmp_path / f"{self.LONG_STEM}.pdf"
        assert len(pdf.name.encode("utf-8")) <= 255      # premise
        name = sidecar_path(pdf).name
        assert len(name.encode("utf-8")) <= 255, (
            f"sidecar name is {len(name.encode('utf-8'))} bytes; the "
            f"filesystem will reject it")

    def test_a_paper_with_an_overlong_name_keeps_its_identity(self, tmp_path):
        from processing.identity import PaperIdentity, load_sidecar
        pdf = _write(tmp_path / f"{self.LONG_STEM}.pdf", "PAPER")
        PaperIdentity(doi="10.5/LONG").save(pdf, recompute_hash=False)
        assert load_sidecar(pdf).doi == "10.5/LONG"

    def test_an_overlong_name_survives_a_move_and_its_undo(self, tmp_path, log):
        from processing.identity import PaperIdentity, load_sidecar
        from processing.undo_log import logged_move

        src = _write(tmp_path / "in" / f"{self.LONG_STEM}.pdf", "PAPER")
        PaperIdentity(doi="10.5/LONG").save(src, recompute_hash=False)
        dst = tmp_path / "out" / f"{self.LONG_STEM}.pdf"

        log.begin_transaction("file it")
        logged_move(src, dst, undo_log=log)
        tx = log._tx_id
        log.commit()

        assert dst.read_bytes() == b"PAPER"
        assert load_sidecar(dst).doi == "10.5/LONG"

        log.undo_transaction(tx)

        assert src.read_bytes() == b"PAPER"
        assert load_sidecar(src).doi == "10.5/LONG"


# ===========================================================================
# 6. The "already undone" refusal
# ===========================================================================

class TestATransactionIsNeverUndoneTwice:

    def test_a_second_undo_is_refused_and_moves_nothing(self, tmp_path, log):
        from processing.undo_log import logged_move
        src = _write(tmp_path / "in" / "p.pdf", "PAPER")
        dst = tmp_path / "out" / "p.pdf"

        log.begin_transaction("file it")
        logged_move(src, dst, undo_log=log)
        tx = log._tx_id
        log.commit()

        log.undo_transaction(tx)
        assert src.read_bytes() == b"PAPER"

        # Time passes. The owner deletes the restored file and an
        # UNRELATED paper is later filed at the old destination name.
        src.unlink()
        unrelated = _write(dst, "A-DIFFERENT-PAPER")

        with pytest.raises(ValueError):
            log.undo_transaction(tx)

        # POSTCONDITION: the unrelated paper has not been dragged
        # anywhere by a replayed undo.
        assert unrelated.read_bytes() == b"A-DIFFERENT-PAPER"
        assert not src.exists()

    def test_get_latest_skips_transactions_that_are_already_undone(
            self, tmp_path, log):
        """The CLI's default target. If it hands back an undone tx, the
        owner's ``undo`` does nothing but raise."""
        from processing.undo_log import logged_move
        first = _write(tmp_path / "in" / "first.pdf", "FIRST")
        second = _write(tmp_path / "in" / "second.pdf", "SECOND")

        log.begin_transaction("first")
        logged_move(first, tmp_path / "out" / "first.pdf", undo_log=log)
        log.commit()

        log.begin_transaction("second")
        logged_move(second, tmp_path / "out" / "second.pdf", undo_log=log)
        tx2 = log._tx_id
        log.commit()

        log.undo_transaction(tx2)

        # Undoing "the latest" again must bring the FIRST batch home.
        latest = log.get_latest_transaction_id()
        log.undo_transaction(latest)
        assert first.read_bytes() == b"FIRST"


# ===========================================================================
# 7. Partial undo stays retryable
# ===========================================================================

class TestAPartialUndoStaysRetryable:
    """122 real operations are already stranded because a single SKIP
    marked the whole transaction undone forever."""

    def test_a_blocked_operation_can_be_retried_once_the_block_clears(
            self, tmp_path, log):
        from processing.undo_log import logged_move
        a = _write(tmp_path / "a.pdf", "AAA")
        c = _write(tmp_path / "c.pdf", "CCC")
        a2, c2 = tmp_path / "moved" / "a.pdf", tmp_path / "moved" / "c.pdf"

        log.begin_transaction("batch")
        logged_move(a, a2, undo_log=log)
        logged_move(c, c2, undo_log=log)
        tx = log._tx_id
        log.commit()

        blocker = _write(tmp_path / "a.pdf", "BLOCKER")

        log.undo_transaction(tx)
        assert blocker.read_bytes() == b"BLOCKER"
        assert c.read_bytes() == b"CCC"

        record = json.loads((log.log_dir / f"{tx}.json").read_text())
        assert record["undone"] is False
        assert record["partial_undo"]["reversed"] == 1

        # The owner clears the blocker and retries.
        blocker.unlink()
        log.undo_transaction(tx)

        # POSTCONDITION: the stranded operation came home.
        assert a.read_bytes() == b"AAA"

    def test_a_fully_successful_undo_is_marked_done(self, tmp_path, log):
        from processing.undo_log import logged_move
        a = _write(tmp_path / "a.pdf", "AAA")
        log.begin_transaction("batch")
        logged_move(a, tmp_path / "moved" / "a.pdf", undo_log=log)
        tx = log._tx_id
        log.commit()

        log.undo_transaction(tx)
        record = json.loads((log.log_dir / f"{tx}.json").read_text())
        assert record["undone"] is True
        assert "partial_undo" not in record


# ===========================================================================
# 8. The write-ahead journal under a REAL interruption
# ===========================================================================

_KILL_SCRIPT = textwrap.dedent(
    """
    import os, signal, sys
    from pathlib import Path
    sys.path.insert(0, {src!r})
    from processing.undo_log import UndoLog, logged_move
    log = UndoLog(log_dir=Path({logdir!r}))
    log.begin_transaction("interrupted batch")
    logged_move(Path({a!r}), Path({a2!r}), undo_log=log)
    logged_move(Path({c!r}), Path({c2!r}), undo_log=log)
    sys.stdout.write(log._tx_id)
    sys.stdout.flush()
    os.kill(os.getpid(), signal.SIGKILL)     # no commit, no atexit, no flush
    """
)


class TestAnInterruptedBatchIsStillUndoable:
    """SIGKILL between the first move and the commit.

    The files really moved. If the record only exists in the dead
    process's memory, the owner has an unreversible change. The
    write-ahead journal is the whole answer, so kill the process for
    real rather than simulating a crash.
    """

    def test_a_sigkilled_run_recovers_into_an_undoable_transaction(
            self, tmp_path, logdir):
        from processing.undo_log import UndoLog

        a = _write(tmp_path / "a.pdf", "AAA")
        c = _write(tmp_path / "c.pdf", "CCC")
        a2, c2 = tmp_path / "moved" / "a.pdf", tmp_path / "moved" / "c.pdf"

        script = _KILL_SCRIPT.format(
            src=str(SRC), logdir=str(logdir),
            a=str(a), a2=str(a2), c=str(c), c2=str(c2))
        env = dict(os.environ, PYTHONPATH=str(SRC),
                   MATH_LIBRARY=str(tmp_path / "fake-library"))
        proc = subprocess.run([sys.executable, "-c", script],
                              capture_output=True, text=True, env=env)

        assert proc.returncode == -9, f"expected SIGKILL, got {proc.returncode}"
        # The moves really happened before the kill.
        assert a2.read_bytes() == b"AAA"
        assert c2.read_bytes() == b"CCC"
        assert not a.exists() and not c.exists()
        # No commit ran.
        assert not (logdir / f"{proc.stdout.strip()}.json").exists()

        recovered = UndoLog(log_dir=logdir).recover_journals()

        assert recovered == [proc.stdout.strip()], (
            "the interrupted batch produced no recoverable record; the "
            "moved files are unreversible")

        # THE postcondition: the owner can put the files back.
        fresh = UndoLog(log_dir=logdir)
        assert [t["id"] for t in fresh.list_transactions()] == recovered
        fresh.undo_transaction(recovered[0])
        assert a.read_bytes() == b"AAA"
        assert c.read_bytes() == b"CCC"
        assert not a2.exists() and not c2.exists()

    def test_operations_are_on_disk_before_the_commit(self, tmp_path, log):
        """The journal is write-AHEAD: it must be readable from another
        process the instant the operation is recorded."""
        from processing.undo_log import logged_move
        a = _write(tmp_path / "a.pdf", "AAA")
        log.begin_transaction("batch")
        logged_move(a, tmp_path / "moved" / "a.pdf", undo_log=log)

        journal = log.log_dir / f"{log._tx_id}.journal.jsonl"
        lines = [l for l in journal.read_text().splitlines() if l.strip()]
        assert [json.loads(l)["source"] for l in lines] == [str(a)]

    def test_a_committed_transaction_leaves_no_journal_behind(self, tmp_path, log):
        from processing.undo_log import logged_move
        a = _write(tmp_path / "a.pdf", "AAA")
        log.begin_transaction("batch")
        logged_move(a, tmp_path / "moved" / "a.pdf", undo_log=log)
        journal = log.log_dir / f"{log._tx_id}.journal.jsonl"
        log.commit()
        assert not journal.exists()


class TestJournalRecoveryToleratesATornLine:

    def test_a_torn_final_line_does_not_lose_the_complete_operations(
            self, tmp_path, logdir):
        """A hard kill truncates the last append mid-write. Dropping the
        whole journal because of it strands every completed move."""
        from processing.undo_log import UndoLog

        a2 = _write(tmp_path / "moved" / "a.pdf", "AAA")
        c2 = _write(tmp_path / "moved" / "c.pdf", "CCC")
        a, c = tmp_path / "a.pdf", tmp_path / "c.pdf"

        good = [json.dumps({"type": "move", "source": str(a), "destination": str(a2)}),
                json.dumps({"type": "move", "source": str(c), "destination": str(c2)})]
        torn = '{"type": "move", "source": "/x/y.pdf", "destin'
        (logdir / "deadbeef1234.journal.jsonl").write_text(
            "\n".join(good) + "\n" + torn)

        recovered = UndoLog(log_dir=logdir).recover_journals()   # must not raise

        assert recovered == ["deadbeef1234"]

        log = UndoLog(log_dir=logdir)
        log.undo_transaction("deadbeef1234")
        assert a.read_bytes() == b"AAA"
        assert c.read_bytes() == b"CCC"

    def test_a_journal_of_nothing_but_a_torn_line_creates_no_transaction(
            self, logdir):
        from processing.undo_log import UndoLog
        (logdir / "cafebabe0001.journal.jsonl").write_text('{"type": "mo')
        assert UndoLog(log_dir=logdir).recover_journals() == []
        assert not (logdir / "cafebabe0001.json").exists()

    def test_a_stale_journal_never_resurrects_an_already_undone_transaction(
            self, tmp_path, logdir):
        """``commit`` writes ``<id>.json`` then deletes the journal. If a
        journal survives (crash, Dropbox re-sync), recovery must leave
        the committed record alone — rewriting it resets ``undone`` to
        False and re-arms a double undo."""
        from processing.undo_log import UndoLog, logged_move

        log = UndoLog(log_dir=logdir)
        a = _write(tmp_path / "a.pdf", "AAA")
        a2 = tmp_path / "moved" / "a.pdf"
        log.begin_transaction("batch")
        logged_move(a, a2, undo_log=log)
        tx = log._tx_id
        log.commit()
        log.undo_transaction(tx)
        assert a.read_bytes() == b"AAA"

        # A stale journal reappears for the same, already-undone tx.
        (logdir / f"{tx}.journal.jsonl").write_text(
            json.dumps({"type": "move", "source": str(a), "destination": str(a2)})
            + "\n")

        UndoLog(log_dir=logdir).recover_journals()

        record = json.loads((logdir / f"{tx}.json").read_text())
        assert record["undone"] is True, "an undone transaction was re-armed"
        assert record["description"] == "batch"
        with pytest.raises(ValueError):
            UndoLog(log_dir=logdir).undo_transaction(tx)


# ===========================================================================
# 9. discard() refuses to throw away work that happened
# ===========================================================================

class TestDiscardNeverThrowsAwayRealWork:
    """Several callers do ``except: log.discard()``. The files had
    already moved; only the record vanished."""

    def test_discarding_after_a_real_move_keeps_the_move_undoable(
            self, tmp_path, log):
        from processing.undo_log import UndoLog, logged_move
        a = _write(tmp_path / "a.pdf", "AAA")
        a2 = tmp_path / "moved" / "a.pdf"

        log.begin_transaction("batch that blew up halfway")
        logged_move(a, a2, undo_log=log)
        log.discard()                      # the panicking caller

        fresh = UndoLog(log_dir=log.log_dir)
        tx_id = fresh.get_latest_transaction_id()
        assert tx_id is not None, "the move happened but left no record"

        fresh.undo_transaction(tx_id)
        assert a.read_bytes() == b"AAA"    # POSTCONDITION: still reversible
        assert not a2.exists()

    def test_discarding_an_empty_transaction_records_nothing(self, log):
        from processing.undo_log import UndoLog
        log.begin_transaction("nothing happened")
        log.discard()
        assert UndoLog(log_dir=log.log_dir).list_transactions() == []


# ===========================================================================
# 10. A deletion recorded as a move to /dev/null is never "restored"
# ===========================================================================

class TestSpecialDevicesAreNeverRestoredFrom:

    def test_a_move_to_dev_null_is_refused_and_creates_nothing(self, tmp_path, log):
        src = tmp_path / "gone.pdf"
        log.begin_transaction("legacy delete")
        log.record_move(src, Path("/dev/null"))
        tx = log._tx_id
        log.commit()

        results = log.undo_transaction(tx)

        assert any(str(r["action"]).startswith("CANNOT UNDO") for r in results)
        # POSTCONDITION: no bogus file conjured at the source, and the
        # system device is still there.
        assert not src.exists()
        assert Path("/dev/null").exists()


# ===========================================================================
# 11. list_transactions: nothing recorded may become invisible
# ===========================================================================

class TestNoRecordedTransactionCanBecomeInvisible:

    def test_one_torn_index_line_does_not_hide_the_other_transactions(
            self, tmp_path, log):
        from processing.undo_log import UndoLog, logged_move
        a = _write(tmp_path / "a.pdf", "AAA")
        log.begin_transaction("batch")
        logged_move(a, tmp_path / "moved" / "a.pdf", undo_log=log)
        tx = log._tx_id
        log.commit()

        with open(log.log_dir / "index.jsonl", "a") as f:
            f.write('{"id": "torn", "timesta\n')

        fresh = UndoLog(log_dir=log.log_dir)
        assert tx in [t["id"] for t in fresh.list_transactions()]
        fresh.undo_transaction(tx)
        assert a.read_bytes() == b"AAA"

    def test_a_transaction_missing_from_the_index_is_still_listed(
            self, tmp_path, log):
        """``commit`` writes ``<id>.json`` then appends to the index. A
        crash in that window must not make the record unreachable."""
        from processing.undo_log import UndoLog, logged_move
        a = _write(tmp_path / "a.pdf", "AAA")
        log.begin_transaction("batch")
        logged_move(a, tmp_path / "moved" / "a.pdf", undo_log=log)
        tx = log._tx_id
        log.commit()

        (log.log_dir / "index.jsonl").unlink()    # the append never happened

        fresh = UndoLog(log_dir=log.log_dir)
        assert [t["id"] for t in fresh.list_transactions()] == [tx]
        fresh.undo_transaction(tx)
        assert a.read_bytes() == b"AAA"

    def test_a_stray_json_file_is_not_offered_as_an_undoable_transaction(
            self, logdir):
        from processing.undo_log import UndoLog
        (logdir / "settings.json").write_text(json.dumps({"theme": "dark"}))
        assert UndoLog(log_dir=logdir).list_transactions() == []


# ===========================================================================
# 12. Sidecar edits: recording refuses to invent previous values
# ===========================================================================

class TestSidecarEditsAreOnlyRecordedWhenThePastIsKnown:

    def test_an_unreadable_sidecar_is_never_recorded_as_a_blank_one(
            self, tmp_path, log):
        """``load()`` collapses "missing" and "corrupt" into a blank
        identity. Recording that as the previous value makes undo write
        blanks over the paper's real DOI, arXiv id and cached text."""
        from processing.identity import PaperIdentity, sidecar_path, load_sidecar

        pdf = _write(tmp_path / "p.pdf", "PAPER")
        sidecar_path(pdf).write_text("{not json at all")   # corrupt on disk

        log.begin_transaction("edit")
        PaperIdentity(doi="10.7/REAL", arxiv_id="2401.00001").save(
            pdf, recompute_hash=False, undo_log=log)
        tx = log._tx_id
        record_ops = list(log._current_tx["operations"])
        log.commit()

        assert not any(o["type"] == "sidecar_edit" for o in record_ops), (
            "recorded a sidecar edit whose 'previous' values were invented")

        log.undo_transaction(tx)

        # POSTCONDITION: undo did not blank the identity.
        assert load_sidecar(pdf).doi == "10.7/REAL"
        assert load_sidecar(pdf).arxiv_id == "2401.00001"

    def test_a_readable_sidecar_edit_is_recorded_and_reversible(
            self, tmp_path, log):
        from processing.identity import PaperIdentity, load_sidecar
        pdf = _write(tmp_path / "p.pdf", "PAPER")
        PaperIdentity(doi="10.1/OLD", topic_codes=["07a"]).save(
            pdf, recompute_hash=False)

        log.begin_transaction("edit")
        ident = load_sidecar(pdf)
        ident.doi = "10.2/NEW"
        ident.topic_codes = ["07a", "09b"]
        ident.save(pdf, recompute_hash=False, undo_log=log)
        tx = log._tx_id
        log.commit()

        log.undo_transaction(tx)
        back = load_sidecar(pdf)
        assert back.doi == "10.1/OLD"
        assert back.topic_codes == ["07a"]

    def test_an_edit_inside_a_read_cache_is_still_reversible(self, tmp_path, log):
        """``sidecar_read_cache`` hands back the very object being
        mutated, so a cached ``load()`` sees no diff and records nothing.
        ``save`` must read the previous values UNCACHED."""
        from processing.identity import (PaperIdentity, load_sidecar,
                                         sidecar_read_cache)
        pdf = _write(tmp_path / "p.pdf", "PAPER")
        PaperIdentity(doi="10.1/OLD").save(pdf, recompute_hash=False)

        log.begin_transaction("edit")
        with sidecar_read_cache():
            ident = load_sidecar(pdf)
            ident.doi = "10.2/NEW"
            ident.save(pdf, recompute_hash=False, undo_log=log)
        tx = log._tx_id
        log.commit()

        assert load_sidecar(pdf).doi == "10.2/NEW"
        log.undo_transaction(tx)
        assert load_sidecar(pdf).doi == "10.1/OLD"

    def test_saving_with_a_log_that_has_no_open_transaction_is_an_error(
            self, tmp_path, logdir):
        """Swallowing this made a caller that forgot
        ``begin_transaction()`` record nothing and return success."""
        from processing.identity import PaperIdentity, load_sidecar
        from processing.undo_log import UndoLog

        pdf = _write(tmp_path / "p.pdf", "PAPER")
        PaperIdentity(doi="10.1/OLD").save(pdf, recompute_hash=False)

        unopened = UndoLog(log_dir=logdir)
        with pytest.raises(RuntimeError):
            PaperIdentity(doi="10.2/NEW").save(
                pdf, recompute_hash=False, undo_log=unopened)

        # POSTCONDITION: the unrecordable edit did not land on disk, so
        # nothing irreversible happened behind the raise.
        assert load_sidecar(pdf).doi == "10.1/OLD"
        assert UndoLog(log_dir=logdir).list_transactions() == []


# ===========================================================================
# 13. Undoing a copy removes the copy and only the copy
# ===========================================================================

class TestUndoingACopyLeavesTheOriginal:

    def test_the_canonical_survives_the_removal_of_its_topic_link(
            self, lib, log):
        from processing.identity import PaperIdentity, load_sidecar
        from processing.undo_log import logged_copy

        canonical = _write(lib / "03 - Working papers" / "P.pdf", "PAPER")
        PaperIdentity(doi="10.1/P", copy_locations=[str(canonical)]).save(
            canonical, recompute_hash=False)
        link = lib / "07a - BSDEs" / "P.pdf"

        log.begin_transaction("route to topic")
        logged_copy(canonical, link, undo_log=log)
        ident = load_sidecar(canonical)
        ident.copy_locations = [str(canonical), str(link)]
        ident.topic_codes = ["07a"]
        ident.save(canonical, recompute_hash=False)
        tx = log._tx_id
        log.commit()

        log.undo_transaction(tx)

        assert not link.exists()
        assert canonical.read_bytes() == b"PAPER"
        back = load_sidecar(canonical)
        assert str(link) not in back.copy_locations
        assert "07a" not in back.topic_codes


class TestGuardsFoundSurvivingAMutationCampaign:
    """Guards that could be deleted with the whole gate still green.

    Found by forcing each `if` in undo_log.py to False and running the
    pre-commit gate: 34 guards mutated, 12 survived. These are the ones
    that were real gaps rather than CLI plumbing — every one is an error
    contract that nothing asserted, so removing it would turn a clear
    refusal into a confusing failure somewhere further downstream.
    """

    def _log(self, tmp_path):
        from processing.undo_log import UndoLog
        return UndoLog(log_dir=tmp_path / ".operation_log")

    # --- "No active transaction" is a contract, not a suggestion -------
    def test_record_copy_without_a_transaction_refuses(self, tmp_path):
        log = self._log(tmp_path)
        with pytest.raises(RuntimeError, match="No active transaction"):
            log.record_copy(tmp_path / "a.pdf", tmp_path / "b.pdf")

    def test_record_rename_without_a_transaction_refuses(self, tmp_path):
        log = self._log(tmp_path)
        with pytest.raises(RuntimeError, match="No active transaction"):
            log.record_rename(tmp_path / "a.pdf", tmp_path / "b.pdf")

    def test_record_move_without_a_transaction_refuses(self, tmp_path):
        log = self._log(tmp_path)
        with pytest.raises(RuntimeError, match="No active transaction"):
            log.record_move(tmp_path / "a.pdf", tmp_path / "b.pdf")

    def test_commit_without_a_transaction_refuses(self, tmp_path):
        log = self._log(tmp_path)
        with pytest.raises(RuntimeError, match="No active transaction"):
            log.commit()

    # --- undoing something that does not exist -------------------------
    def test_undoing_an_unknown_transaction_refuses(self, tmp_path):
        """Silently doing nothing here would tell the owner their undo
        succeeded when no such transaction was ever recorded."""
        log = self._log(tmp_path)
        with pytest.raises((FileNotFoundError, ValueError)):
            log.undo_transaction("deadbeefcafe")

    # --- logged_copy on a vanished source ------------------------------
    def test_logged_copy_refuses_a_missing_source(self, tmp_path):
        from processing.undo_log import logged_copy
        log = self._log(tmp_path)
        log.begin_transaction("copy")
        with pytest.raises(FileNotFoundError):
            logged_copy(tmp_path / "gone.pdf", tmp_path / "dest.pdf",
                        undo_log=log)

    # --- discard with no transaction must not explode ------------------
    def test_discard_without_a_transaction_is_harmless(self, tmp_path):
        log = self._log(tmp_path)
        log.discard()                      # must not raise
        assert not log.list_transactions()

    def test_discard_removes_the_write_ahead_journal(self, tmp_path):
        """"Does not raise" was too weak to notice the cleanup vanishing.

        A journal left behind after an EMPTY discard is later recovered
        by recover_journals() into a phantom transaction offering to undo
        operations that were deliberately abandoned.
        """
        log = self._log(tmp_path)
        tx = log.begin_transaction("will be discarded")
        journal = tmp_path / ".operation_log" / f"{tx}.journal.jsonl"
        journal.write_text("")             # the file the guard must clean up
        log.discard()
        assert not journal.exists(), (
            "the journal outlived its discarded transaction; recover_journals "
            "would resurrect it as a phantom undo")

    # --- the index self-heals when deleted -----------------------------
    def test_list_transactions_survives_a_missing_index(self, tmp_path):
        """index.jsonl is a summary cache; the .json files are the truth.
        Losing the cache must not lose the history."""
        from processing.undo_log import logged_move
        log = self._log(tmp_path)
        (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
        p = tmp_path / "a" / "x.pdf"; p.write_bytes(b"%PDF")
        tx = log.begin_transaction("move")
        logged_move(p, tmp_path / "b" / "x.pdf", undo_log=log)
        log.commit()
        (tmp_path / ".operation_log" / "index.jsonl").unlink()
        assert tx in [t["id"] for t in log.list_transactions()], \
            "history was lost with the cache"
