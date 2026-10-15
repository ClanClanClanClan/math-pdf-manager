"""Undo takes back what the six unlogged buttons did -- exactly that, no more.

Measured 2026-10-15 by pressing every library-writing button in a test:
six changed the library outside ``processing/undo_log.py``, so Activity
could not reverse them --

* Mark done (To Download, its "Download now", and Home) moved the note
  to ``.trash/done_flags/`` with a bare ``shutil.move``;
* Home's "Look again" rewrote the record (``reset_recheck_state``);
* the Upgrade Queue's "Flag for manual" wrote a note into 04/;
* "Fill in missing details" and "Cache abstracts now" wrote records.

Two of those MAKE a file. A record made for a paper that had none is
logged as made (``record_new_record``, as a topic filing does), so undo
retires it while it holds only what was made. A download note is not a
record: the log has ``file_created`` for it, and undo retires the note to
``.trash/undone_creations/`` -- never deletes it -- while it is still byte
for byte what was written.

The library is a weak oracle, so each rule is checked over generated
inputs and against the cases where it would be wrong: the file changed
since, gone since, replaced by another paper's, unreadable.
"""
from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from contextlib import contextmanager
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from processing.identity import (PaperIdentity, enable_sidecar_mirror,
                                 find_sidecar, record_location, sidecar_path)
from processing.undo_log import UndoLog, created_file_blocker

TRASHED = Path(".trash") / "undone_creations"
#: Where undo retires a record it made (the record mirror's trash).
RETIRED_RECORDS = ".mathpdf-sidecars/.trash/undone_records/"
FAST = settings(max_examples=25, deadline=None,
                suppress_health_check=[HealthCheck.function_scoped_fixture])


@contextmanager
def _library():
    """A fresh library, pointed at the way production code finds it."""
    old = os.environ.get("MATH_LIBRARY")
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "Maths"
        (root / "04 - Papers to be downloaded").mkdir(parents=True)
        enable_sidecar_mirror(root)
        os.environ["MATH_LIBRARY"] = str(root)
        try:
            yield root
        finally:
            if old is None:
                os.environ.pop("MATH_LIBRARY", None)
            else:
                os.environ["MATH_LIBRARY"] = old


@pytest.fixture
def lib():
    with _library() as root:
        yield root


def _log(root: Path, what: str = "t") -> UndoLog:
    log = UndoLog(log_dir=root / ".operation_log")
    log.begin_transaction(what)
    return log


def _commit(log: UndoLog) -> str:
    tx = log._tx_id
    log.commit()
    return tx


def _tree(root: Path) -> dict[str, bytes]:
    """Every file of the library but the undo history itself."""
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()
            and ".operation_log" not in p.relative_to(root).parts}


def _without_retired(tree: dict) -> dict:
    """The tree less what undo retired -- by design never deleted."""
    return {k: v for k, v in tree.items()
            if not k.startswith((TRASHED.as_posix() + "/", RETIRED_RECORDS))}


def _pdf(path: Path, body: bytes = b"%PDF-1.4\n%%EOF\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


# ==========================================================================
# The new operation: a file this transaction made
# ==========================================================================

#: Latin, Greek and Cyrillic with their combining marks -- the scripts the
#: library's names are in. APFS refuses code points newer than its own
#: Unicode tables (U+18DF3, say) with EILSEQ, which is not this rule.
_names = st.text(st.characters(min_codepoint=0x20, max_codepoint=0x04FF,
                               exclude_characters="/:",
                               exclude_categories=("Cs", "Cc", "Cn")),
                 min_size=1, max_size=40).filter(
    lambda s: s.strip(" .") == s and s not in (".", ".."))


class TestUndoingACreation:

    @FAST
    @given(name=_names, body=st.binary(max_size=2000),
           nfd=st.booleans())
    def test_it_retires_exactly_what_was_made(self, name, body, nfd):
        """Any name -- accents in either Unicode form -- any bytes."""
        name = unicodedata.normalize("NFD" if nfd else "NFC", name) + ".txt"
        with _library() as root:
            before = _tree(root)
            log = _log(root)
            made = root / "04 - Papers to be downloaded" / name
            made.write_bytes(body)
            log.record_new_file(made)
            tx = _commit(log)

            preview = log.undo_transaction(tx, dry_run=True)
            assert [r["ok"] for r in preview] == [True]
            assert preview[0]["action"].startswith("WOULD RETIRE")
            assert made.exists(), "the preview changed something"

            rows = log.undo_transaction(tx)
            assert [r["ok"] for r in rows] == [True], rows
            after = _tree(root)
            assert _without_retired(after) == before
            retired = {k: v for k, v in after.items() if k not in before}
            assert list(retired.values()) == [body], retired
            assert json.loads((root / ".operation_log" / f"{tx}.json")
                              .read_text())["undone"] is True

    def test_a_file_changed_since_is_left_alone(self, lib):
        log = _log(lib)
        made = lib / "04 - Papers to be downloaded" / "Note.txt"
        made.write_text("DOI: 10.1/a\n")
        log.record_new_file(made)
        tx = _commit(log)
        made.write_text("DOI: 10.1/a\nmy own notes\n")

        assert not log.undo_transaction(tx, dry_run=True)[0]["ok"]
        (row,) = log.undo_transaction(tx)

        assert not row["ok"] and row["action"].startswith("CANNOT UNDO")
        assert made.read_text() == "DOI: 10.1/a\nmy own notes\n"
        assert not (lib / TRASHED).exists()
        assert json.loads((lib / ".operation_log" / f"{tx}.json")
                          .read_text())["undone"] is False

    def test_another_papers_note_under_the_same_name_is_left_alone(self, lib):
        """Marked done, then written again for a different paper: the name
        is the same, the note is not this transaction's."""
        log = _log(lib)
        made = lib / "04 - Papers to be downloaded" / "Stopping.txt"
        made.write_text("DOI: 10.1/first\n")
        log.record_new_file(made)
        tx = _commit(log)
        made.rename(lib / "elsewhere.txt")
        made.write_text("DOI: 10.1/second\n")

        (row,) = log.undo_transaction(tx)

        assert not row["ok"]
        assert made.read_text() == "DOI: 10.1/second\n"

    def test_a_file_gone_since_is_reported_not_counted(self, lib):
        log = _log(lib)
        made = lib / "x.txt"
        made.write_text("x")
        log.record_new_file(made)
        tx = _commit(log)
        made.unlink()
        (row,) = log.undo_transaction(tx)
        assert not row["ok"] and row["action"].startswith("SKIP")

    def test_an_entry_without_a_digest_refuses_rather_than_guesses(self, lib):
        made = lib / "x.txt"
        made.write_text("x")
        assert created_file_blocker(made, "").startswith("CANNOT UNDO")

    def test_two_undone_creations_of_one_name_do_not_become_one(self, lib):
        bodies = []
        for i in range(2):
            log = _log(lib)
            made = lib / "04 - Papers to be downloaded" / "Same.txt"
            made.write_text(f"note {i}")
            bodies.append(f"note {i}")
            log.record_new_file(made)
            log.undo_transaction(_commit(log))
        kept = sorted(p.read_text() for p in (lib / TRASHED).iterdir())
        assert kept == bodies

    def test_it_needs_an_open_transaction(self, lib):
        made = lib / "x.txt"
        made.write_text("x")
        with pytest.raises(RuntimeError):
            UndoLog(log_dir=lib / ".operation_log").record_new_file(made)

    def test_an_interrupted_run_keeps_its_creations_undoable(self, lib):
        """The entry is journaled as it is made: a crash before commit still
        leaves it to recover_journals."""
        log = _log(lib)
        made = lib / "x.txt"
        made.write_text("x")
        log.record_new_file(made)
        # no commit -- the process "dies" here
        (tx,) = UndoLog(log_dir=lib / ".operation_log").recover_journals()
        UndoLog(log_dir=lib / ".operation_log").undo_transaction(tx)
        assert not made.exists() and (lib / TRASHED / "x.txt").exists()


# ==========================================================================
# Mark done
# ==========================================================================

def _note(root: Path, name="Stopping.txt", body="DOI: 10.1000/stop\n") -> Path:
    p = root / "04 - Papers to be downloaded" / "Ann. Probab" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


class TestMarkDone:

    def test_it_will_not_run_outside_the_log(self, lib):
        from ui.cockpit_actions import mark_flag_done
        note = _note(lib)
        with pytest.raises(ValueError):
            mark_flag_done(note, lib, undo_log=None)
        assert note.exists()

    @FAST
    @given(names=st.lists(st.sampled_from(["A.txt", "a.txt", "B.txt",
                                           "Café.txt", "Café.txt"]),
                          min_size=1, max_size=6))
    def test_undo_brings_every_note_back_exactly(self, names):
        """Several notes, colliding names in the trash, one transaction."""
        from ui.cockpit_actions import mark_flag_done
        with _library() as root:
            notes = []
            for i, name in enumerate(names):
                p = root / "04 - Papers to be downloaded" / f"J{i}" / name
                p.parent.mkdir(parents=True)
                p.write_text(f"note {i}")
                notes.append(p)
            before = _tree(root)
            log = _log(root)
            assert all(mark_flag_done(p, root, undo_log=log) for p in notes)
            assert len(list((root / ".trash/done_flags").iterdir())) == len(notes)
            rows = log.undo_transaction(_commit(log))
            assert all(r["ok"] for r in rows), rows
            assert _tree(root) == before

    def test_undo_never_writes_over_a_note_that_took_its_place(self, lib):
        from ui.cockpit_actions import mark_flag_done
        note = _note(lib, body="first\n")
        log = _log(lib)
        mark_flag_done(note, lib, undo_log=log)
        tx = _commit(log)
        note.write_text("second, flagged again since\n")

        (row,) = log.undo_transaction(tx)

        assert not row["ok"] and row["action"].startswith("CANNOT UNDO")
        assert note.read_text() == "second, flagged again since\n"
        assert (lib / ".trash/done_flags/Stopping.txt").read_text() == "first\n"


# ==========================================================================
# Look again
# ==========================================================================

#: A record as most of the real library has it: written before several
#: fields existed, so a whole-record save would add them.
OLD_RECORD = {
    "schema_version": 1, "content_sha256": "ab" * 32,
    "original_filename": "x.pdf", "doi": "", "arxiv_id": "",
    "first_ingested_at": "2025-01-01T00:00:00", "copy_locations": [],
    "publication_checks": [{"hit": False}], "topic_codes": [],
}


def _write_record(pdf: Path, data: dict) -> Path:
    path = sidecar_path(pdf)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False,
                               sort_keys=True), encoding="utf-8")
    return path


class TestLookAgain:

    @FAST
    @given(flag=st.one_of(st.none(), st.booleans()),
           count=st.one_of(st.none(), st.integers(0, 50)),
           last=st.one_of(st.none(), st.text(max_size=30)))
    def test_undo_gives_the_record_back_byte_for_byte(self, flag, count, last):
        """Whatever the three fields held -- or whether they were there."""
        from processing.publication_state import reset_recheck_state
        with _library() as root:
            pdf = _pdf(root / "02 - Unpublished papers/S/Smith, J. - P.pdf")
            data = dict(OLD_RECORD)
            for k, v in (("permanently_unpublished", flag),
                         ("recheck_count", count), ("last_check_date", last)):
                if v is not None:
                    data[k] = v
            rec = _write_record(pdf, data)
            original = rec.read_bytes()
            log = _log(root)

            out = reset_recheck_state(pdf, undo_log=log)

            assert out is not None and out.recheck_count == 0
            now = json.loads(rec.read_text())
            assert now["permanently_unpublished"] is False
            assert now["recheck_count"] == 0
            assert set(now) - set(data) <= {"permanently_unpublished",
                                             "recheck_count", "last_check_date"}, (
                "the reset rewrote fields it does not own")
            tx = _commit(log)
            assert all(r["ok"] for r in log.undo_transaction(tx))
            assert rec.read_bytes() == original

    def test_the_old_values_are_recorded_before_the_record_is_written(
            self, lib, monkeypatch):
        """A write that dies half-way must find its undo already on disk."""
        import core.io
        from processing.publication_state import reset_recheck_state
        pdf = _pdf(lib / "02 - Unpublished papers/S/Smith, J. - P.pdf")
        _write_record(pdf, dict(OLD_RECORD, permanently_unpublished=True,
                                recheck_count=3))
        log = _log(lib)
        journal = lib / ".operation_log" / f"{log._tx_id}.journal.jsonl"
        seen = []
        real = core.io.atomic_write_text

        def spy(path, *a, **k):
            if str(path).endswith(".meta.json"):
                seen.append(journal.read_text() if journal.exists() else "")
            return real(path, *a, **k)

        monkeypatch.setattr(core.io, "atomic_write_text", spy)
        reset_recheck_state(pdf, undo_log=log)
        (journaled,) = seen
        op = json.loads(journaled)
        assert op["type"] == "sidecar_edit"
        assert op["changes"]["permanently_unpublished"][0] is True
        assert op["changes"]["recheck_count"][0] == 3

    def test_a_record_that_vanished_since_it_was_read_is_not_a_reset(
            self, lib, monkeypatch):
        """Read, then gone before the write (a sync, another process)."""
        import processing.publication_state as ps
        pdf = _pdf(lib / "02 - Unpublished papers/S/Smith, J. - P.pdf")
        ghost = PaperIdentity(permanently_unpublished=True)
        ghost._is_new = False
        monkeypatch.setattr(ps.PaperIdentity, "load", classmethod(
            lambda cls, p: ghost))
        log = _log(lib)
        assert ps.reset_recheck_state(pdf, undo_log=log) is None
        assert not log.has_operations()
        assert find_sidecar(pdf) is None, "a record was made from nothing"

    def test_the_command_line_reset_is_in_activity_too(self, lib):
        from processing.publication_state import main
        pdf = _pdf(lib / "02 - Unpublished papers/S/Smith, J. - P.pdf")
        rec = _write_record(pdf, dict(OLD_RECORD, permanently_unpublished=True))
        original = rec.read_bytes()
        main(["reset-recheck", str(pdf)])
        log = UndoLog()
        (tx,) = log.list_transactions()
        assert "command line" in tx["description"]
        log.undo_transaction(tx["id"])
        assert rec.read_bytes() == original

    def test_the_command_line_reset_of_nothing_leaves_no_entry(self, lib):
        from processing.publication_state import main
        pdf = _pdf(lib / "02 - Unpublished papers/S/Smith, J. - P.pdf")
        main(["reset-recheck", str(pdf)])
        assert UndoLog().list_transactions() == []


# ==========================================================================
# Flag for manual download
# ==========================================================================

def _entry(title="Optimal stopping games", doi="10.1000/games",
           pre="/x/pre.pdf") -> dict:
    return {"file": pre, "parsed_title": title, "parsed_authors": ["Smith, J."],
            "match": {"doi": doi, "journal": "Ann. Probab.", "year": 2024,
                      "confidence": 0.95}}


class TestFlagForManual:

    def test_another_papers_note_is_never_written_over(self, lib):
        from processing.upgrade_to_published import flag_for_manual_download
        first = flag_for_manual_download(_entry(pre="/x/a.pdf"), lib)
        body = first.read_bytes()
        second = flag_for_manual_download(_entry(pre="/x/b.pdf",
                                                 doi="10.1000/other"), lib)
        assert first.read_bytes() == body
        assert second != first and second.name == "Optimal stopping games (1).txt"
        assert b"10.1000/other" in second.read_bytes()

    @pytest.mark.timeout(30)
    def test_three_papers_with_one_title_get_three_notes(self, lib):
        """The second clash is the one a naming loop gets wrong -- by
        never moving past "(1)", which spins for ever."""
        from processing.upgrade_to_published import flag_for_manual_download
        notes = [flag_for_manual_download(_entry(doi=f"10.1000/{i}"), lib)
                 for i in range(3)]
        assert [n.name for n in notes] == [
            "Optimal stopping games.txt", "Optimal stopping games (1).txt",
            "Optimal stopping games (2).txt"]
        assert [f"10.1000/{i}".encode() in n.read_bytes()
                for i, n in enumerate(notes)] == [True] * 3

    def test_a_note_differing_only_in_case_is_not_written_over(self, lib):
        """APFS folds case: on the owner's Mac the two names are one file."""
        from processing.upgrade_to_published import flag_for_manual_download
        folder = lib / "04 - Papers to be downloaded" / "Ann. Probab."
        folder.mkdir(parents=True)
        theirs = folder / "OPTIMAL STOPPING GAMES.txt"
        theirs.write_text("someone else's note\n")
        mine = flag_for_manual_download(_entry(), lib)
        assert theirs.read_text() == "someone else's note\n"
        assert b"10.1000/games" in mine.read_bytes()

    def test_the_same_note_twice_is_one_note_and_no_change(self, lib):
        from processing.upgrade_to_published import flag_for_manual_download
        first = flag_for_manual_download(_entry(), lib)
        before = _tree(lib)
        log = _log(lib)
        again = flag_for_manual_download(_entry(), lib, undo_log=log)
        assert again == first and _tree(lib) == before
        assert not log.has_operations()

    @FAST
    @given(titles=st.lists(st.sampled_from(["A", "a", "B", "Café",
                                            "Café", "x/y", "Q?"]),
                           min_size=1, max_size=6),
           dois=st.lists(st.sampled_from(["10.1/a", "10.1/b"]),
                         min_size=6, max_size=6))
    def test_one_transaction_of_notes_undoes_to_nothing(self, titles, dois):
        from processing.upgrade_to_published import flag_for_manual_download
        with _library() as root:
            before = _tree(root)
            log = _log(root)
            for t, d in zip(titles, dois):
                flag_for_manual_download(_entry(title=t, doi=d), root,
                                         undo_log=log)
            notes = {k for k in _tree(root) if k not in before}
            assert notes, "nothing was written"
            rows = log.undo_transaction(_commit(log))
            assert all(r["ok"] for r in rows), rows
            assert _without_retired(_tree(root)) == before
            assert len(list((root / TRASHED).iterdir())) == len(rows)

    def test_a_batch_upgrade_that_could_not_download_takes_its_note_back(
            self, lib):
        """upgrade_paper flags what it cannot fetch: the note is part of the
        batch's transaction, so undoing the batch takes it back."""
        from processing.upgrade_to_published import upgrade_paper
        pre = _pdf(lib / "03 - Working papers/S/Smith, J. - Games.pdf")
        log = _log(lib)
        r = upgrade_paper(_entry(pre=str(pre)), lib, lib.parent / "dl",
                          manual_only=True, undo_log=log)
        note = Path(r["flag_file"])
        assert note.exists()
        log.undo_transaction(_commit(log))
        assert not note.exists() and pre.exists()


# ==========================================================================
# The backfills
# ==========================================================================

class TestFillInMissingDetails:

    @FAST
    @given(has_record=st.lists(st.booleans(), min_size=1, max_size=6))
    def test_undo_retires_exactly_the_records_it_made(self, has_record):
        from processing.identity import backfill_directory
        with _library() as root:
            pdfs = []
            for i, has in enumerate(has_record):
                p = _pdf(root / f"01 - Published papers/S/Smith, J. - P{i}.pdf",
                         f"%PDF-1.4\n% {i}\n".encode())
                if has:
                    _write_record(p, dict(OLD_RECORD, doi=f"10.1/{i}"))
                pdfs.append(p)
            before = _tree(root)
            log = _log(root)
            summary = backfill_directory(root, undo_log=log)
            assert summary["written"] == has_record.count(False)
            assert all(not PaperIdentity.load(p).is_new() for p in pdfs)
            if not log.has_operations():
                return
            rows = log.undo_transaction(_commit(log))
            assert len(rows) == summary["written"] and all(r["ok"] for r in rows)
            assert _without_retired(_tree(root)) == before
            assert [PaperIdentity.load(p).is_new() for p in pdfs] == [
                not h for h in has_record]

    def test_a_record_that_has_since_learned_more_stays(self, lib):
        """Made blank, then given a DOI by the publication check: undoing
        the backfill would take the DOI with it, so it refuses."""
        from processing.identity import backfill_directory, patch_record
        a = _pdf(lib / "01 - Published papers/S/Smith, J. - A.pdf", b"%PDF a")
        b = _pdf(lib / "01 - Published papers/S/Smith, J. - B.pdf", b"%PDF b")
        log = _log(lib)
        backfill_directory(lib, undo_log=log)
        tx = _commit(log)
        patch_record(b, {"doi": "10.1000/learned"})

        rows = log.undo_transaction(tx)

        assert sorted(r["ok"] for r in rows) == [False, True]
        assert PaperIdentity.load(a).is_new()
        assert PaperIdentity.load(b).doi == "10.1000/learned"

    def test_overwriting_a_record_is_an_edit_and_undo_restores_it(self, lib):
        from processing.identity import backfill_sidecar
        pdf = _pdf(lib / "01 - Published papers/S/Smith, J. - A.pdf")
        _write_record(pdf, dict(OLD_RECORD, doi="10.1000/keep"))
        log = _log(lib)
        assert backfill_sidecar(pdf, overwrite=True, undo_log=log)
        assert PaperIdentity.load(pdf).doi == ""
        ops = log._current_tx["operations"]
        assert [op["type"] for op in ops] == ["sidecar_edit"]
        log.undo_transaction(_commit(log))
        assert PaperIdentity.load(pdf).doi == "10.1000/keep"


class TestCacheAbstracts:

    @pytest.fixture(autouse=True)
    def _text(self, monkeypatch):
        import processing.classifier_text as ct
        monkeypatch.setattr(ct, "extract_classifier_text",
                            lambda pdf, **k: f"first pages of {pdf.stem}")

    @FAST
    @given(text_before=st.one_of(st.none(), st.just("")),
           extra=st.dictionaries(st.sampled_from(["title_source", "doi",
                                                  "topic_codes"]),
                                 st.sampled_from(["", "x", "10.1/y"]),
                                 max_size=3))
    def test_an_existing_record_gets_two_fields_and_gives_them_back(
            self, text_before, extra):
        from processing.classifier_text import backfill_classifier_text
        with _library() as root:
            pdf = _pdf(root / "01 - Published papers/S/Smith, J. - P.pdf")
            data = dict(OLD_RECORD, **extra)
            if text_before is not None:
                data["classifier_text"] = text_before
            rec = _write_record(pdf, data)
            original = rec.read_bytes()
            log = _log(root)

            stats = backfill_classifier_text(root, undo_log=log)

            assert stats["extracted"] == 1
            now = json.loads(rec.read_text())
            assert {k: v for k, v in now.items() if k not in (
                "classifier_text", "classifier_text_tried")} == {
                k: v for k, v in data.items() if k != "classifier_text"}, (
                "the backfill rewrote fields it does not own")
            rows = log.undo_transaction(_commit(log))
            assert all(r["ok"] for r in rows), rows
            assert rec.read_bytes() == original

    def test_a_paper_with_no_record_gets_one_and_undo_retires_it(self, lib):
        from processing.classifier_text import backfill_classifier_text
        from processing.identity import compute_content_hash, filing_date
        pdf = _pdf(lib / "01 - Published papers/S/Smith, J. - P.pdf")
        before = _tree(lib)
        log = _log(lib)
        backfill_classifier_text(lib, undo_log=log)
        made = PaperIdentity.load(pdf)
        assert "first pages" in made.classifier_text
        # A whole record, not the text alone: "Fill in missing details"
        # passes over any paper that has one.
        assert made.content_sha256 == compute_content_hash(pdf)
        assert made.first_ingested_at == filing_date(pdf)
        (op,) = log._current_tx["operations"]
        assert op["type"] == "record_created"
        assert op["destination"] == str(record_location(pdf))
        log.undo_transaction(_commit(log))
        assert PaperIdentity.load(pdf).is_new()
        assert _without_retired(_tree(lib)) == before

    def test_an_unreadable_record_is_not_written_over(self, lib):
        """It loads as "no record", and the old code saved a fresh one over
        it -- whatever it held, gone. Now it is left, unread, and counted
        (``unreadable``: before 2026-10-15 it was read first and counted
        ``failed``, which also let a run of them fill every batch)."""
        from processing.classifier_text import backfill_classifier_text
        pdf = _pdf(lib / "01 - Published papers/S/Smith, J. - P.pdf")
        rec = sidecar_path(pdf)
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_bytes(b'{"doi": "10.1000/half-synced", ')
        log = _log(lib)

        stats = backfill_classifier_text(lib, undo_log=log)

        assert rec.read_bytes() == b'{"doi": "10.1000/half-synced", '
        assert stats["unreadable"] == 1 and stats["unreadable_papers"] == [pdf.name]
        assert stats["read"] == stats["failed"] == stats["extracted"] == 0
        assert not log.has_operations()
