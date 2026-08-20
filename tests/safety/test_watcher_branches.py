"""Branch-level safety tests for the unattended watcher daemon.

``src/watcher/daemon.py`` files papers with nobody watching.  The audit
found 31 of its 41 single-branch ``if``s could be forced to ``if False:``
with the existing watcher tests still green -- i.e. the tests proved the
module imports, not that its decisions matter.

Every test here was written against a mutated copy of the daemon on
/tmp: the branch it claims to protect was flipped, the test was shown
FAILING, the branch was restored, the test was shown PASSING.  Tests
that could not be shown failing were deleted, and the branches they
would have covered are reported as survivors instead.

The assertions are deliberately POSTCONDITIONS -- what is true of the
bytes on disk after the call -- rather than "the helper was invoked".
The re-armed hard-delete survived four tests that proved a helper
worked and none that proved the caller called it.
"""
from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

from synth_library import _write_minimal_pdf, build_synth_library  # noqa: E402

pytest.importorskip("watchdog")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def _make(tmp_path, monkeypatch, *, dry_run: bool = False, **cfg_kwargs):
    """A PDFHandler over a synthetic library + inbox, both under tmp_path.

    ``MATH_LIBRARY`` is pointed at the synthetic library so that the
    UndoLog, the library write lock and every other helper that resolves
    the library for itself agree with ``config.library_root``.
    """
    from watcher.config import WatcherConfig
    from watcher.daemon import PDFHandler

    lib = build_synth_library(tmp_path / "lib", specs=[])
    monkeypatch.setenv("MATH_LIBRARY", str(lib))
    inbox = tmp_path / "inbox"
    inbox.mkdir(exist_ok=True)
    log_dir = tmp_path / "logs"
    log_dir.mkdir(exist_ok=True)

    opts = dict(
        inbox_dir=inbox,
        library_root=lib,
        log_dir=log_dir,
        default_status="working",
        settle_seconds=0.01,
        poll_interval=0.0,
        notifications=False,
        delete_source=False,
    )
    opts.update(cfg_kwargs)
    return PDFHandler(WatcherConfig(**opts), dry_run=dry_run), lib, inbox


def _created(path: Path):
    return MagicMock(is_directory=False, src_path=str(path))


def _moved(src, dest):
    return MagicMock(is_directory=False, src_path=str(src), dest_path=str(dest))


def _settle_and_process(handler, path: Path) -> None:
    """Force ``path``'s settle timer to be expired, then run a poll cycle."""
    handler._pending[str(path)] = (path.stat().st_size, time.time() - 3600)
    handler.process_settled()


def _library_pdfs(lib: Path) -> list[str]:
    """Every PDF filed anywhere in the library, trash included."""
    return sorted(str(p.relative_to(lib)) for p in lib.rglob("*.pdf"))


def _filed_pdfs(lib: Path) -> list[str]:
    """PDFs filed into the library proper (excludes the trash)."""
    return [p for p in _library_pdfs(lib) if not p.startswith(".trash")]


def _copies_of(root: Path, blob: bytes) -> list[Path]:
    """Every readable file under ``root`` whose bytes are exactly ``blob``.

    This is the conservation counter: for any outcome of an ingest the
    answer must never be zero.
    """
    out = []
    for p in root.rglob("*"):
        if p.is_file():
            try:
                if p.read_bytes() == blob:
                    out.append(p)
            except OSError:
                pass
    return out


def _transactions(lib: Path) -> list[str]:
    """Committed undo transactions (``<id>.json`` records)."""
    log_dir = lib / ".operation_log"
    if not log_dir.exists():
        return []
    return sorted(p.name for p in log_dir.glob("*.json"))


@pytest.fixture
def spy_notify(monkeypatch):
    """Capture notifications instead of firing real macOS ones.

    ``notify`` shells out to osascript on darwin, so a test that leaves
    it live pops real notifications on the owner's desktop.
    """
    calls: list[tuple[str, str]] = []

    def _fake(title, message, *, sound=""):
        calls.append((title, message))

    monkeypatch.setattr("watcher.daemon.notify", _fake)
    return calls


# ---------------------------------------------------------------------------
# 1. Ignore rules: a file that is still downloading is not a paper
# ---------------------------------------------------------------------------

class TestPartialDownloadsAreNotPapers:
    """``_is_ingestable_pdf``'s suffix gate, from all four entry points.

    A browser writes ``Paper.pdf.crdownload`` / ``Paper.pdf.part`` while
    the bytes are still arriving.  Ingesting one of those files a paper
    that is half-written -- and with ``delete_source`` on, retires the
    only complete copy.
    """

    TEMP_NAMES = [
        "Paper.pdf.crdownload",
        "Paper.pdf.part",
        "Paper.pdf.partial",
        "Paper.pdf.download",
        ".hidden-notes.txt",
        "readme.txt",
    ]

    def test_a_partial_download_is_never_a_candidate(
        self, tmp_path, monkeypatch, spy_notify
    ):
        handler, lib, inbox = _make(tmp_path, monkeypatch, notifications=True)

        blobs = {}
        for name in self.TEMP_NAMES:
            p = inbox / name
            _write_minimal_pdf(p, title="Half arrived", author="Partial, P.")
            blobs[name] = p.read_bytes()
            handler.on_created(_created(p))
            handler.on_modified(_created(p))
            handler.on_moved(_moved(inbox / "elsewhere.tmp", p))

        assert handler._pending == {}, (
            "a file still being downloaded was queued for ingest: "
            f"{list(handler._pending)}"
        )
        assert handler.scan_existing_inbox() == 0, (
            "startup scan picked up a partial download"
        )

        handler.process_settled()

        # Postconditions: nothing filed, every temp file still sitting in
        # the inbox under its own name with its own bytes, and the user
        # was not bothered about any of it.
        assert _library_pdfs(lib) == []
        for name in self.TEMP_NAMES:
            p = inbox / name
            assert p.exists(), f"{name} disappeared from the inbox"
            assert p.read_bytes() == blobs[name], f"{name} was rewritten"
        assert spy_notify == [], f"watcher notified about a partial download: {spy_notify}"

    def test_but_the_completed_rename_is_filed(self, tmp_path, monkeypatch):
        """Proves the test above is not vacuously green.

        The browser's final step is a rename to ``.pdf`` -- an on_moved,
        not an on_created.  That one MUST be ingested, or the watcher
        silently swallows every browser download.
        """
        handler, lib, inbox = _make(tmp_path, monkeypatch)

        temp = inbox / "Paper.pdf.crdownload"
        final = inbox / "Paper.pdf"
        _write_minimal_pdf(temp, title="Fully arrived", author="Complete, C.")
        handler.on_created(_created(temp))
        assert str(temp) not in handler._pending

        temp.rename(final)
        handler.on_moved(_moved(temp, final))

        assert str(final) in handler._pending
        assert str(temp) not in handler._pending, (
            "the pre-rename name stayed queued; the watcher will keep "
            "polling a path that no longer exists"
        )

        _settle_and_process(handler, final)
        assert any("Complete" in p for p in _filed_pdfs(lib)), _filed_pdfs(lib)

    def test_a_rename_inside_the_inbox_stops_tracking_the_old_name(
        self, tmp_path, monkeypatch
    ):
        """``a.pdf`` -> ``b.pdf``: the old key must leave the queue.

        Otherwise the watcher keeps re-stat'ing a path that no longer
        exists on every poll for the rest of the daemon's life.
        """
        handler, lib, inbox = _make(tmp_path, monkeypatch, settle_seconds=600)
        old = inbox / "a.pdf"
        new = inbox / "b.pdf"
        _write_minimal_pdf(old, title="Renamed in place", author="Rename, R.")
        handler.on_created(_created(old))
        assert str(old) in handler._pending

        old.rename(new)
        handler.on_moved(_moved(old, new))

        assert str(new) in handler._pending
        assert str(old) not in handler._pending, (
            "the pre-rename name is still queued for ingest"
        )

    def test_a_moved_in_directory_is_not_ingested(self, tmp_path, monkeypatch):
        handler, lib, inbox = _make(tmp_path, monkeypatch)
        sub = inbox / "a folder.pdf"      # a *directory* whose name ends .pdf
        sub.mkdir()
        handler.on_moved(MagicMock(is_directory=True, src_path=str(tmp_path / "x"),
                                   dest_path=str(sub)))
        handler.on_created(MagicMock(is_directory=True, src_path=str(sub)))
        handler.on_modified(MagicMock(is_directory=True, src_path=str(sub)))
        assert handler._pending == {}
        assert handler.scan_existing_inbox() == 0, (
            "the startup scan queued a DIRECTORY named *.pdf for ingest"
        )
        assert handler._pending == {}
        handler.process_settled()
        assert _library_pdfs(lib) == []
        assert sub.is_dir()


class TestStartupScan:

    def test_a_second_scan_neither_re_adds_nor_restarts_the_timer(
        self, tmp_path, monkeypatch
    ):
        """The startup scan must be idempotent.

        Re-adding an already-pending file rewrites its ``last_change``
        stamp, so a file that is scanned repeatedly can have its settle
        timer pushed forward forever and never be ingested.
        """
        handler, lib, inbox = _make(tmp_path, monkeypatch, settle_seconds=600)
        p = inbox / "already-here.pdf"
        _write_minimal_pdf(p, title="Already here", author="Here, H.")

        assert handler.scan_existing_inbox() == 1
        first = handler._pending[str(p)]

        assert handler.scan_existing_inbox() == 0, (
            "the startup scan re-added a file that was already pending"
        )
        assert handler._pending[str(p)] == first, (
            "a re-scan restarted the settle timer of a file already waiting"
        )


class TestDropboxConflictCopies:
    """A ``(machine's conflicted copy …)`` sibling is not a new paper."""

    def test_a_conflict_copy_is_left_for_review(self, tmp_path, monkeypatch):
        handler, lib, inbox = _make(tmp_path, monkeypatch)
        p = inbox / "Smith, J. - A paper (Dylan's conflicted copy 2026-06-15).pdf"
        _write_minimal_pdf(p, title="A paper", author="Smith, J.")
        blob = p.read_bytes()

        handler.on_created(_created(p))
        assert handler._pending == {}
        handler.process_settled()

        assert _library_pdfs(lib) == [], "a Dropbox conflict copy was auto-filed"
        assert p.read_bytes() == blob

    def test_a_broken_conflict_detector_never_blocks_a_real_ingest(
        self, tmp_path, monkeypatch
    ):
        """The detector is best-effort; if it throws, the paper still files."""
        import processing.conflict_resolver as cr

        def _boom(path):
            raise RuntimeError("resolver exploded")

        monkeypatch.setattr(cr, "find_canonical_for_conflict", _boom)

        handler, lib, inbox = _make(tmp_path, monkeypatch)
        p = inbox / "ordinary.pdf"
        _write_minimal_pdf(p, title="Ordinary paper", author="Ordin, O.")
        handler.on_created(_created(p))
        _settle_and_process(handler, p)

        assert any("Ordin" in f for f in _filed_pdfs(lib)), _filed_pdfs(lib)


# ---------------------------------------------------------------------------
# 2. The settle timer: never file a file that is still being written
# ---------------------------------------------------------------------------

class TestSettleTimer:
    """NOTE on a branch deliberately left uncovered.

    ``if last_size < 0`` (the sentinel from a first stat() that failed)
    is an EQUIVALENT mutation: ``st_size`` is never negative, so a
    pending entry of ``-1`` always differs from the fresh size and the
    ``current_size != last_size`` branch below resets the timer in
    exactly the same way.  Forcing it to ``if False:`` changes nothing
    observable, here or anywhere else, so no test here claims it.
    """

    def test_a_file_whose_size_changed_is_not_filed_this_tick(
        self, tmp_path, monkeypatch
    ):
        """The truncation law.

        ``cp``/``curl``/a scanner writes the file in pieces.  If the size
        changed since the last poll the watcher must reset the timer, not
        file the fragment.
        """
        handler, lib, inbox = _make(tmp_path, monkeypatch)
        p = inbox / "growing.pdf"
        _write_minimal_pdf(p, title="Still arriving", author="Grow, G.")
        full = p.read_bytes()
        p.write_bytes(full[: len(full) // 2])       # a truncated fragment

        handler.on_created(_created(p))
        # The timer has long expired, but the size is about to change.
        handler._pending[str(p)] = (p.stat().st_size, time.time() - 3600)
        p.write_bytes(full)                          # the writer finishes

        handler.process_settled()
        assert _library_pdfs(lib) == [], (
            "a file whose size changed between polls was filed anyway"
        )
        assert str(p) in handler._pending, "the growing file was dropped entirely"

        # Next tick: size stable, timer expired -> now it may be filed,
        # and what lands in the library must be the COMPLETE bytes.
        handler._pending[str(p)] = (p.stat().st_size, time.time() - 3600)
        handler.process_settled()
        filed = _filed_pdfs(lib)
        assert filed, "a settled file was never filed"
        assert (lib / filed[0]).read_bytes() == full, "a truncated copy was filed"

    def test_settle_seconds_must_actually_elapse(self, tmp_path, monkeypatch):
        handler, lib, inbox = _make(tmp_path, monkeypatch, settle_seconds=600)
        p = inbox / "fresh.pdf"
        _write_minimal_pdf(p, title="Just landed", author="Fresh, F.")

        handler.on_created(_created(p))              # timestamp = now
        handler.process_settled()

        assert _library_pdfs(lib) == [], (
            "a file was filed before settle_seconds elapsed"
        )
        assert str(p) in handler._pending

    def test_a_file_that_vanished_is_forgotten(self, tmp_path, monkeypatch):
        handler, lib, inbox = _make(tmp_path, monkeypatch)
        p = inbox / "ghost.pdf"
        _write_minimal_pdf(p, title="Gone", author="Ghost, G.")
        handler.on_created(_created(p))
        handler._pending[str(p)] = (p.stat().st_size, time.time() - 3600)
        p.unlink()

        handler.process_settled()

        assert str(p) not in handler._pending, (
            "a deleted file stayed in the pending queue forever"
        )
        assert _library_pdfs(lib) == []


# ---------------------------------------------------------------------------
# 3. The library write lock: never interleave with the weekly batch
# ---------------------------------------------------------------------------

class TestLibraryWriteLock:

    def test_nothing_is_filed_while_another_process_holds_the_lock(
        self, tmp_path, monkeypatch
    ):
        from processing.locking import LibraryLock

        handler, lib, inbox = _make(tmp_path, monkeypatch)
        p = inbox / "contended.pdf"
        _write_minimal_pdf(p, title="Contended paper", author="Lock, L.")

        other = LibraryLock(lib)
        assert other.acquire(blocking=False), "test could not take the lock"
        try:
            _settle_and_process(handler, p)
            assert _library_pdfs(lib) == [], (
                "the watcher filed a paper while another writer held the "
                "library write lock"
            )
            assert str(p) in handler._pending, (
                "a deferred ingest was dropped instead of retried"
            )
        finally:
            other.release()

        # And once the other writer is done, the deferred file is filed.
        _settle_and_process(handler, p)
        assert any("Lock" in f for f in _filed_pdfs(lib)), _filed_pdfs(lib)

    def test_an_idle_poll_does_not_contend_for_the_lock(self, tmp_path, monkeypatch):
        """The poll loop runs every second for weeks on end.

        A tick with nothing settled must not take the library write lock,
        or the watcher spends the whole weekly maintenance batch fighting
        it for no reason.
        """
        import processing.locking as locking

        real = locking.LibraryLock
        acquisitions: list[int] = []

        class _Counting(real):                       # type: ignore[misc,valid-type]
            def acquire(self, *a, **kw):
                acquisitions.append(1)
                return super().acquire(*a, **kw)

        monkeypatch.setattr(locking, "LibraryLock", _Counting)

        handler, lib, inbox = _make(tmp_path, monkeypatch, settle_seconds=600)
        handler.process_settled()                    # nothing pending at all

        p = inbox / "not-yet.pdf"
        _write_minimal_pdf(p, title="Not settled yet", author="Wait, W.")
        handler.on_created(_created(p))
        handler.process_settled()                    # pending, but not settled

        assert acquisitions == [], (
            "an idle poll took the library write lock"
        )


# ---------------------------------------------------------------------------
# 4. Duplicate arrivals
# ---------------------------------------------------------------------------

class TestDuplicateArrival:

    def _drop(self, handler, inbox, name):
        p = inbox / name
        _write_minimal_pdf(p, title="A duplicated paper", author="Zeta, Q.")
        _settle_and_process(handler, p)
        return p

    def test_a_byte_identical_redrop_is_not_filed_twice(self, tmp_path, monkeypatch):
        handler, lib, inbox = _make(tmp_path, monkeypatch)

        first = self._drop(handler, inbox, "download.pdf")
        assert len(_filed_pdfs(lib)) == 1, _filed_pdfs(lib)
        after_first = _transactions(lib)

        second = self._drop(handler, inbox, "download (1).pdf")

        assert len(_filed_pdfs(lib)) == 1, (
            f"a byte-identical re-download was filed a second time: "
            f"{_filed_pdfs(lib)}"
        )
        # The source of a duplicate drop is the user's own file: it must
        # survive untouched, in place, for them to deal with.
        assert second.exists(), "the duplicate arrival's source was consumed"
        assert second.read_bytes() == first.read_bytes()
        # An ingest that filed nothing must not leave a 0-op transaction
        # cluttering the undo history / Activity tab.
        assert _transactions(lib) == after_first, (
            "the duplicate drop committed an empty transaction"
        )

    def test_a_duplicate_is_reported_as_a_duplicate_not_as_a_failure(
        self, tmp_path, monkeypatch, spy_notify
    ):
        handler, lib, inbox = _make(tmp_path, monkeypatch, notifications=True)
        self._drop(handler, inbox, "download.pdf")
        spy_notify.clear()
        self._drop(handler, inbox, "download (1).pdf")

        titles = [t for t, _ in spy_notify]
        assert titles, "a duplicate arrival told the user nothing at all"
        assert any("Duplicate" in t for t in titles), titles
        assert not any("Fail" in t or "Error" in t for t in titles), (
            f"a duplicate drop was reported to the user as a failure: {titles}"
        )


# ---------------------------------------------------------------------------
# 5. Failure paths: the paper must never end up nowhere
# ---------------------------------------------------------------------------

class TestAFailedIngestLeavesThePaperSomewhere:

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores mode bits")
    def test_an_unfilable_paper_stays_in_the_inbox(self, tmp_path, monkeypatch,
                                                   spy_notify):
        """Organize fails (destination unwritable) -> source is preserved."""
        handler, lib, inbox = _make(
            tmp_path, monkeypatch, notifications=True, delete_source=True,
        )
        p = inbox / "unfilable.pdf"
        _write_minimal_pdf(p, title="Cannot be filed", author="Nope, N.")
        blob = p.read_bytes()

        target = lib / "03 - Working papers"
        os.chmod(target, 0o500)
        try:
            handler.on_created(_created(p))
            _settle_and_process(handler, p)
        finally:
            os.chmod(target, 0o755)

        assert _copies_of(tmp_path, blob), (
            "a failed ingest left ZERO copies of the paper anywhere"
        )
        assert p.exists() and p.read_bytes() == blob, (
            "the source of a FAILED ingest was retired/altered"
        )
        assert _filed_pdfs(lib) == []
        assert _transactions(lib) == [], (
            "a failed ingest that recorded no operations committed an "
            "empty transaction"
        )
        assert any("Fail" in t or "Error" in t for t, _ in spy_notify), (
            f"a failed ingest was never reported to the user: {spy_notify}"
        )

    def test_a_crashing_ingest_leaves_the_paper_somewhere(
        self, tmp_path, monkeypatch, spy_notify
    ):
        import processing.ingest as ingest_mod

        def _boom(*a, **kw):
            raise RuntimeError("pipeline exploded mid-ingest")

        monkeypatch.setattr(ingest_mod, "ingest_paper", _boom)

        handler, lib, inbox = _make(
            tmp_path, monkeypatch, notifications=True, delete_source=True,
        )
        p = inbox / "crasher.pdf"
        _write_minimal_pdf(p, title="Crashes the pipeline", author="Crash, C.")
        blob = p.read_bytes()

        handler.on_created(_created(p))
        _settle_and_process(handler, p)      # must NOT propagate

        assert p.exists() and p.read_bytes() == blob, (
            "a crashing ingest consumed the source"
        )
        assert any("Error" in t or "Fail" in t for t, _ in spy_notify), spy_notify

    def test_an_ingest_that_reports_failure_files_nothing_and_logs_nothing(
        self, tmp_path, monkeypatch, spy_notify
    ):
        """The plain error branch: ingest_paper RETURNS a failure.

        (Distinct from the crash path above: no exception is raised, the
        pipeline simply reports that it could not extract/organize.)
        """
        import processing.ingest as ingest_mod

        monkeypatch.setattr(ingest_mod, "ingest_paper", lambda p, **kw: {
            "file": str(p), "success": False, "actions": [],
            "filename": "", "destination": "",
            "error": "ERROR: could not extract any metadata",
        })

        handler, lib, inbox = _make(
            tmp_path, monkeypatch, notifications=True, delete_source=True,
        )
        p = inbox / "unextractable.pdf"
        _write_minimal_pdf(p, title="", author="")
        blob = p.read_bytes()

        _settle_and_process(handler, p)

        assert p.exists() and p.read_bytes() == blob, (
            "a paper the pipeline refused was retired anyway — it now "
            "exists nowhere the user will look"
        )
        assert _filed_pdfs(lib) == []
        assert _transactions(lib) == [], (
            "a failure that recorded NO operations committed an empty "
            "transaction into the undo history"
        )
        assert any("Fail" in t for t, _ in spy_notify), spy_notify

    @pytest.mark.parametrize("mode", ["returns_failure", "raises"])
    def test_a_failure_that_already_moved_something_stays_reversible(
        self, tmp_path, monkeypatch, mode
    ):
        """A failure AFTER an operation was recorded must be COMMITTED.

        Discarding it would leave a file that really moved with no undo
        record.  ``UndoLog.discard()`` has its own guard against this, so
        the daemon's ``has_operations()`` check is belt-and-braces; the
        only difference the caller can see is that going through
        ``discard()`` stamps the record "[INCOMPLETE: discarded after
        partial work]" in the Activity tab, which is a lie about a
        transaction the daemon committed on purpose.
        """
        import json

        import processing.ingest as ingest_mod

        def _half_done(p, **kw):
            kw["undo_log"].record_copy(Path(p), Path(p).with_name("phantom.pdf"))
            if mode == "raises":
                raise RuntimeError("refused after copying")
            return {"file": str(p), "success": False, "actions": [],
                    "filename": "", "destination": "",
                    "error": "ERROR: refused after copying"}

        monkeypatch.setattr(ingest_mod, "ingest_paper", _half_done)

        handler, lib, inbox = _make(tmp_path, monkeypatch)
        p = inbox / "halfway.pdf"
        _write_minimal_pdf(p, title="Halfway", author="Half, H.")

        _settle_and_process(handler, p)

        txs = _transactions(lib)
        assert txs, (
            "a failed ingest that had ALREADY recorded a file operation "
            "discarded the record — the move is now unreversible"
        )
        record = json.loads((lib / ".operation_log" / txs[0]).read_text())
        assert record["operations"], "the recorded operation was lost"
        assert "INCOMPLETE" not in record["description"], (
            "the daemon routed a deliberate commit through discard(); the "
            f"undo record is mislabelled: {record['description']!r}"
        )

    def test_one_bad_paper_does_not_stop_the_next_one(self, tmp_path, monkeypatch):
        """A crash inside _ingest must not abort the whole settled batch."""
        import processing.ingest as ingest_mod

        real = ingest_mod.ingest_paper

        def _boom_on_first(pdf_path, **kw):
            if Path(pdf_path).name == "bad.pdf":
                raise RuntimeError("pipeline exploded mid-ingest")
            return real(pdf_path, **kw)

        monkeypatch.setattr(ingest_mod, "ingest_paper", _boom_on_first)

        handler, lib, inbox = _make(tmp_path, monkeypatch)
        bad = inbox / "bad.pdf"
        good = inbox / "good.pdf"
        _write_minimal_pdf(bad, title="Bad one", author="Bad, B.")
        _write_minimal_pdf(good, title="Good one", author="Good, G.")
        for f in (bad, good):
            handler._pending[str(f)] = (f.stat().st_size, time.time() - 3600)

        handler.process_settled()

        assert any("Good" in f for f in _filed_pdfs(lib)), (
            f"a crash on one paper swallowed the rest of the batch: "
            f"{_filed_pdfs(lib)}"
        )
        assert bad.exists()


# ---------------------------------------------------------------------------
# 6. The source original: retired, never destroyed
# ---------------------------------------------------------------------------

class TestTheSourceOriginal:

    def test_delete_source_false_leaves_the_source_exactly_alone(
        self, tmp_path, monkeypatch
    ):
        handler, lib, inbox = _make(tmp_path, monkeypatch, delete_source=False)
        p = inbox / "keepme.pdf"
        _write_minimal_pdf(p, title="Keep the source", author="Keep, K.")
        blob = p.read_bytes()
        mtime = p.stat().st_mtime

        handler.on_created(_created(p))
        _settle_and_process(handler, p)

        assert _filed_pdfs(lib), "nothing was filed; test is vacuous"
        assert p.exists(), "delete_source=False still removed the inbox original"
        assert p.read_bytes() == blob
        assert p.stat().st_mtime == mtime, "the untouched source was rewritten"
        trash = lib / ".trash" / "ingested_originals"
        assert not (trash.exists() and any(trash.iterdir())), (
            "delete_source=False retired the source to the trash anyway"
        )

    def test_delete_source_true_retires_and_never_destroys(
        self, tmp_path, monkeypatch
    ):
        handler, lib, inbox = _make(tmp_path, monkeypatch, delete_source=True)
        p = inbox / "retireme.pdf"
        _write_minimal_pdf(p, title="Retire the source", author="Retire, R.")
        blob = p.read_bytes()

        handler.on_created(_created(p))
        _settle_and_process(handler, p)

        copies = _copies_of(tmp_path, blob)
        assert len(copies) >= 2, (
            f"retiring the source left only {len(copies)} copy/copies of the "
            f"bytes: {copies}"
        )
        assert (lib / ".trash" / "ingested_originals" / "retireme.pdf").exists(), (
            "the ingested original was not retired into the trash"
        )
        assert _transactions(lib), "the retirement was not recorded for undo"

    def test_two_originals_with_the_same_name_both_survive(
        self, tmp_path, monkeypatch
    ):
        """Two different papers both called ``main.pdf``.

        The trash must hold both sets of bytes; the collision suffix is
        the only thing standing between the second drop and silently
        destroying the first.
        """
        handler, lib, inbox = _make(tmp_path, monkeypatch, delete_source=True)

        p = inbox / "main.pdf"
        _write_minimal_pdf(p, title="First main paper", author="Alpha, A.")
        blob_a = p.read_bytes()
        _settle_and_process(handler, p)

        p = inbox / "main.pdf"
        _write_minimal_pdf(p, title="Second main paper", author="Beta, B.")
        blob_b = p.read_bytes()
        assert blob_a != blob_b
        _settle_and_process(handler, p)

        trash = lib / ".trash" / "ingested_originals"
        contents = [f.read_bytes() for f in trash.iterdir() if f.is_file()]
        assert blob_a in contents, "the first original was clobbered in the trash"
        assert blob_b in contents, "the second original never reached the trash"

    def test_a_failed_retirement_leaves_the_original_in_the_inbox(
        self, tmp_path, monkeypatch, spy_notify
    ):
        import processing.undo_log as undo_mod

        def _boom(src, dst, *, undo_log=None):
            raise OSError("read-only trash")

        monkeypatch.setattr(undo_mod, "logged_move", _boom)

        handler, lib, inbox = _make(
            tmp_path, monkeypatch, delete_source=True, notifications=True,
        )
        p = inbox / "stubborn.pdf"
        _write_minimal_pdf(p, title="Cannot be retired", author="Stub, S.")
        blob = p.read_bytes()

        _settle_and_process(handler, p)

        assert p.exists() and p.read_bytes() == blob, (
            "a failed retirement destroyed the original anyway"
        )
        assert _filed_pdfs(lib), "the paper was not filed"
        # The paper WAS filed; a trash move that failed afterwards is a
        # warning in the log, not an ingest failure.
        titles = [t for t, _ in spy_notify]
        assert any("Filed" in t for t in titles), titles
        assert not any("Error" in t or "Fail" in t for t in titles), (
            f"a successful ingest was reported as an error because the "
            f"trash move failed: {titles}"
        )
        assert _transactions(lib), (
            "the successful ingest's transaction was never committed"
        )


# ---------------------------------------------------------------------------
# 7. Dry run
# ---------------------------------------------------------------------------

class TestDryRun:

    def test_a_dry_run_moves_nothing_and_records_nothing(
        self, tmp_path, monkeypatch, spy_notify
    ):
        handler, lib, inbox = _make(
            tmp_path, monkeypatch, dry_run=True,
            delete_source=True, notifications=True,
        )
        p = inbox / "dryrun.pdf"
        _write_minimal_pdf(p, title="Dry run paper", author="Dry, D.")
        blob = p.read_bytes()

        handler.on_created(_created(p))
        _settle_and_process(handler, p)

        assert _library_pdfs(lib) == [], (
            f"a DRY RUN filed a paper into the library: {_library_pdfs(lib)}"
        )
        assert p.exists() and p.read_bytes() == blob, (
            "a DRY RUN retired the inbox original"
        )
        assert _transactions(lib) == [], "a DRY RUN wrote an undo transaction"
        assert any("dry run" in t.lower() for t, _ in spy_notify), (
            f"the dry-run notification did not say it was a dry run: {spy_notify}"
        )


# ---------------------------------------------------------------------------
# 8. Notifications
# ---------------------------------------------------------------------------

class TestNotifications:

    def test_notifications_off_means_completely_silent(
        self, tmp_path, monkeypatch, spy_notify
    ):
        handler, lib, inbox = _make(
            tmp_path, monkeypatch, notifications=False, delete_source=True,
        )
        ok = inbox / "quiet.pdf"
        _write_minimal_pdf(ok, title="Quiet paper", author="Quiet, Q.")
        _settle_and_process(handler, ok)

        dup = inbox / "quiet-again.pdf"
        _write_minimal_pdf(dup, title="Quiet paper", author="Quiet, Q.")
        _settle_and_process(handler, dup)

        assert _filed_pdfs(lib), "nothing happened; test is vacuous"
        assert spy_notify == [], (
            f"notifications=False still notified the user: {spy_notify}"
        )

    def test_a_filed_paper_names_its_destination(
        self, tmp_path, monkeypatch, spy_notify
    ):
        handler, lib, inbox = _make(tmp_path, monkeypatch, notifications=True)
        p = inbox / "loud.pdf"
        _write_minimal_pdf(p, title="Loud paper", author="Loud, L.")
        _settle_and_process(handler, p)

        filed = _filed_pdfs(lib)
        assert filed, "nothing was filed"
        assert len(spy_notify) == 1, spy_notify
        title, message = spy_notify[0]
        assert "Filed" in title, title
        # The message must carry the library-relative destination, not the
        # absolute path and not an empty string.
        assert Path(filed[0]).name in message, (message, filed)
        assert str(lib) not in message, (
            "the notification leaked the absolute library path"
        )

    def test_a_variant_arrival_is_flagged_and_still_filed_and_retired(
        self, tmp_path, monkeypatch, spy_notify
    ):
        """preprint <-> published twin: file it, keep it, but say so."""
        import processing.preprint_variants as pv

        handler, lib, inbox = _make(
            tmp_path, monkeypatch, notifications=True, delete_source=True,
        )
        twin = lib / "01 - Published papers" / "T" / "Twin, T. - The published side.pdf"
        twin.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(twin, title="The published side", author="Twin, T.")

        monkeypatch.setattr(pv, "find_identifier_twin",
                            lambda *a, **kw: str(twin))

        p = inbox / "preprint.pdf"
        _write_minimal_pdf(p, title="The preprint side", author="Twin, T.")
        blob = p.read_bytes()
        _settle_and_process(handler, p)

        titles = [t for t, _ in spy_notify]
        assert any("variant" in t.lower() for t in titles), (
            f"a preprint/published twin was filed with no warning: {titles}"
        )
        # Flagging must not change what happens to the bytes.
        assert len(_filed_pdfs(lib)) == 2, _filed_pdfs(lib)
        assert _copies_of(tmp_path, blob), "the flagged arrival vanished"
        assert (lib / ".trash" / "ingested_originals" / "preprint.pdf").exists(), (
            "a variant-flagged ingest skipped retiring its source"
        )


# ---------------------------------------------------------------------------
# 9. Daemon lifecycle: startup scan and shutdown
# ---------------------------------------------------------------------------

class _FakeObserver:
    """Stands in for watchdog's Observer so run_daemon can be driven."""

    def __init__(self, ticks: int = 1):
        self.ticks = ticks
        self.stop_calls = 0
        self.join_calls = 0
        self.scheduled: list[tuple] = []
        self.started = False

    def schedule(self, handler, path, recursive=False):
        self.scheduled.append((handler, path, recursive))

    def start(self):
        self.started = True

    def is_alive(self):
        if self.ticks <= 0:
            return False
        self.ticks -= 1
        return True

    def stop(self):
        self.stop_calls += 1

    def join(self):
        self.join_calls += 1


@pytest.fixture
def preserved_signal_handlers():
    """run_daemon installs SIGINT/SIGTERM handlers process-wide."""
    saved = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    yield
    for s, h in saved.items():
        signal.signal(s, h)


class TestDaemonLifecycle:

    def _config(self, tmp_path, monkeypatch, **kw):
        from watcher.config import WatcherConfig
        lib = build_synth_library(tmp_path / "lib", specs=[])
        monkeypatch.setenv("MATH_LIBRARY", str(lib))
        inbox = tmp_path / "inbox"
        inbox.mkdir(exist_ok=True)
        opts = dict(
            inbox_dir=inbox, library_root=lib, log_dir=tmp_path / "logs",
            default_status="working", settle_seconds=0.0, poll_interval=0.0,
            notifications=False, delete_source=False,
        )
        opts.update(kw)
        return WatcherConfig(**opts), lib, inbox

    def test_a_pdf_dropped_while_the_daemon_was_offline_is_still_filed(
        self, tmp_path, monkeypatch, preserved_signal_handlers
    ):
        """No fresh on_created event will ever fire for it."""
        import watcher.daemon as daemon

        config, lib, inbox = self._config(tmp_path, monkeypatch)
        p = inbox / "was-here-already.pdf"
        _write_minimal_pdf(p, title="Dropped while offline", author="Offline, O.")

        observer = _FakeObserver(ticks=1)
        monkeypatch.setattr(daemon, "Observer", lambda: observer)
        monkeypatch.setattr(daemon.time, "sleep", lambda _s: None)

        daemon.run_daemon(config, dry_run=False)

        assert observer.started and observer.scheduled
        assert any("Offline" in f for f in _filed_pdfs(lib)), (
            f"a PDF already in the inbox at startup was never ingested: "
            f"{_filed_pdfs(lib)}"
        )

    def test_the_shutdown_handler_actually_stops_the_observer(
        self, tmp_path, monkeypatch, preserved_signal_handlers, spy_notify
    ):
        import watcher.daemon as daemon

        config, lib, inbox = self._config(tmp_path, monkeypatch, notifications=True)
        observer = _FakeObserver(ticks=0)
        monkeypatch.setattr(daemon, "Observer", lambda: observer)
        monkeypatch.setattr(daemon.time, "sleep", lambda _s: None)

        daemon.run_daemon(config, dry_run=False)
        stops_after_run = observer.stop_calls
        spy_notify.clear()

        installed = signal.getsignal(signal.SIGTERM)
        assert callable(installed), "SIGTERM was never wired to a handler"
        installed(signal.SIGTERM, None)

        assert observer.stop_calls == stops_after_run + 1, (
            "SIGTERM did not stop the observer; the daemon would keep "
            "filing papers after being asked to quit"
        )
        assert any("Stop" in t for t, _ in spy_notify), spy_notify


# ---------------------------------------------------------------------------
# 10. A defect this file could not fix (daemon.py is not ours to edit)
# ---------------------------------------------------------------------------

# Was xfail(strict=True) when written: `undo_log` was assigned INSIDE the
# try, after two imports, so if either import raised, the `except
# Exception` handler evaluated `if undo_log:` on an unbound local. The
# resulting UnboundLocalError escaped _ingest AND process_settled and
# killed the watcher loop — the daemon would stop filing anything and say
# nothing. The agent that found it correctly refused to fix a file it did
# not own; `undo_log = None` now precedes the try, and the marker is gone.
def test_an_ingest_that_cannot_even_import_does_not_kill_the_watcher(
    tmp_path, monkeypatch
):
    handler, lib, inbox = _make(tmp_path, monkeypatch)
    p = inbox / "importfail.pdf"
    _write_minimal_pdf(p, title="Import fails", author="Imp, I.")

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) \
        else __builtins__.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "processing.ingest":
            raise ImportError("simulated broken install")
        return real_import(name, *args, **kwargs)

    monkeypatch.setitem(
        __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__,
        "__import__", _fake_import,
    )
    try:
        _settle_and_process(handler, p)   # must not raise
    finally:
        monkeypatch.undo()

    assert p.exists()
