"""Audit-10: airtightness fixes for crash-safety, concurrency and
unattended robustness on a Dropbox-synced library.

Covers:
  * atomic_write_text -- unique temp, no turds, atomic replace
  * sidecar + publication cache routed through it
  * collision-proof undo transaction ids
  * self-healing / tolerant list_transactions
  * record-before-mutate (copy + trash move recorded first)
  * truncated-download guard
  * watcher skips Dropbox conflict copies
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


# ---------------------------------------------------------------------------
# atomic_write_text
# ---------------------------------------------------------------------------

class TestAtomicWrite:

    def test_writes_content(self, tmp_path):
        from core.io import atomic_write_text
        target = tmp_path / "sub" / "f.json"
        atomic_write_text(target, '{"a": 1}')
        assert target.read_text() == '{"a": 1}'

    def test_unique_temp_no_turd_left(self, tmp_path):
        from core.io import atomic_write_text
        target = tmp_path / "f.json"
        atomic_write_text(target, "x")
        # No leftover temp siblings.
        leftovers = [p.name for p in tmp_path.iterdir() if p.name != "f.json"]
        assert leftovers == []

    def test_very_long_name_does_not_overflow_filename_limit(self, tmp_path):
        # A near-limit sidecar name plus the unique .<pid>.<rand>.tmp suffix
        # must not exceed the 255-byte component limit (was an ENAMETOOLONG
        # crash that aborted a live bulk-apply mid-transaction).
        from core.io import atomic_write_text
        # 240-char name; with the old suffix the temp would be > 255 bytes.
        target = tmp_path / (("L" * 230) + ".meta.json")
        atomic_write_text(target, '{"ok": 1}')
        assert target.exists() and target.read_text() == '{"ok": 1}'
        leftovers = [p.name for p in tmp_path.iterdir() if p != target]
        assert leftovers == []                     # no stranded temp

    def test_failure_cleans_temp(self, tmp_path, monkeypatch):
        import core.io as io_mod
        target = tmp_path / "f.json"

        def boom(*a, **k):
            raise RuntimeError("replace failed")

        monkeypatch.setattr(io_mod.os, "replace", boom)
        with pytest.raises(RuntimeError):
            io_mod.atomic_write_text(target, "data")
        # Temp must not survive a failed write.
        assert list(tmp_path.iterdir()) == []

    def test_cleanup_stale_temps(self, tmp_path):
        from core.io import cleanup_stale_temps
        (tmp_path / ".f.json.999.deadbeef.tmp").write_text("junk")
        (tmp_path / "real.json").write_text("keep")
        removed = cleanup_stale_temps(tmp_path)
        assert removed == 1
        assert (tmp_path / "real.json").exists()
        assert not (tmp_path / ".f.json.999.deadbeef.tmp").exists()


# ---------------------------------------------------------------------------
# Sidecar + cache use the atomic helper
# ---------------------------------------------------------------------------

class TestSidecarAtomic:

    def test_sidecar_save_leaves_no_tmp(self, tmp_path):
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        enable_sidecar_mirror(tmp_path)
        pdf = tmp_path / "Smith, J. - X.pdf"
        _write_minimal_pdf(pdf, title="X", author="Smith, J.")
        ident = PaperIdentity()
        ident.save(pdf)
        # Walk the whole tree; no .tmp turds anywhere.
        turds = [p for p in tmp_path.rglob("*.tmp")]
        assert turds == []
        # And the sidecar round-trips.
        again = PaperIdentity.load(pdf)
        assert not again.is_new()


# ---------------------------------------------------------------------------
# Undo transaction id uniqueness + listing robustness
# ---------------------------------------------------------------------------

class TestUndoTxIds:

    def test_concurrent_same_desc_ids_differ(self, tmp_path, monkeypatch):
        # Two transactions begun "at the same time" with the same
        # description must still get distinct ids (audit-10: the old
        # md5(time-desc) collided here and clobbered the first record).
        from processing.undo_log import UndoLog
        import processing.undo_log as ul
        monkeypatch.setattr(ul.time, "time", lambda: 1234567.0)
        a = UndoLog(log_dir=tmp_path)
        b = UndoLog(log_dir=tmp_path)
        id_a = a.begin_transaction("ingest batch")
        id_b = b.begin_transaction("ingest batch")
        assert id_a != id_b

    def test_has_operations_reflects_recorded_ops(self, tmp_path):
        from processing.undo_log import UndoLog
        log = UndoLog(log_dir=tmp_path)
        assert log.has_operations() is False        # no tx yet
        log.begin_transaction("t")
        assert log.has_operations() is False        # begun but empty
        log.record_move(tmp_path / "a", tmp_path / "b")
        assert log.has_operations() is True
        log.commit()
        assert log.has_operations() is False        # committed -> no open tx

    def test_upgrade_process_report_commits_in_finally(self):
        # Crash-safety regression: a paper raising mid-batch must not lose the
        # transaction or leak the temp dir — commit/discard + rmtree live in a
        # finally after the loop (asserted structurally, like the trash-order
        # test below, since the real path needs network downloads).
        import inspect
        import processing.upgrade_to_published as up
        # The batch body now lives in upgrade_entries, which process_report
        # and the Monday sweep both call (cockpit audit, finding 16).
        assert "upgrade_entries(" in inspect.getsource(up.process_report)
        src = inspect.getsource(up.upgrade_entries)
        assert "finally:" in src
        fin = src.index("finally:")
        assert src.index("undo_log.commit()") > fin
        assert src.index("shutil.rmtree(download_dir") > fin
        assert "undo_log.discard()" in src          # empty-tx path

    def test_bulk_sort_guards_empty_transaction(self):
        import inspect
        import processing.bulk_sort as bs
        src = inspect.getsource(bs)
        assert "has_operations()" in src
        assert "undo_log.discard()" in src

    def test_discard_writes_no_transaction(self, tmp_path):
        # A begun-but-empty transaction must be DISCARDABLE without writing
        # a 0-op record (the watcher does this on a duplicate arrival).
        from processing.undo_log import UndoLog
        log = UndoLog(log_dir=tmp_path)
        log.begin_transaction("empty ingest")
        log.discard()
        assert log.list_transactions() == []
        assert list(tmp_path.glob("*.json")) == []
        assert not (tmp_path / "index.jsonl").exists()

    def test_list_tolerates_malformed_index_line(self, tmp_path):
        from processing.undo_log import UndoLog
        log = UndoLog(log_dir=tmp_path)
        log.begin_transaction("good one")
        log.record_move(tmp_path / "a", tmp_path / "b")
        log.commit()
        # Corrupt the index with a torn line.
        idx = tmp_path / "index.jsonl"
        idx.write_text(idx.read_text() + '{"id": "torn", "timesta\n')
        txs = log.list_transactions()
        # The good transaction still shows; the torn line is skipped.
        assert any(t["description"] == "good one" for t in txs)

    def test_list_self_heals_orphan_tx(self, tmp_path):
        # A {tx}.json with no index entry (crash between write and
        # append) must still be listable so it can be undone.
        from processing.undo_log import UndoLog
        log = UndoLog(log_dir=tmp_path)
        orphan = {
            "id": "abc123orphan",
            "description": "orphaned tx",
            "timestamp": "2026-06-15T00:00:00+00:00",
            "operations": [{"type": "move", "source": "/x", "destination": "/y"}],
            "undone": False,
        }
        (tmp_path / "abc123orphan.json").write_text(json.dumps(orphan))
        txs = log.list_transactions()
        ids = {t["id"] for t in txs}
        assert "abc123orphan" in ids
        rec = next(t for t in txs if t["id"] == "abc123orphan")
        assert rec["operations_count"] == 1


# ---------------------------------------------------------------------------
# Record-before-mutate
# ---------------------------------------------------------------------------

class TestRecordBeforeMutate:

    def test_copy_recorded_before_copy2(self, tmp_path, monkeypatch):
        # If copy2 dies, the undo log must already hold the copy entry
        # so an operator can see (and skip-undo) the attempted op.
        from organization.system import OrganizationSystem
        import organization.system as sysmod
        from processing.undo_log import UndoLog

        for d in ["01 - Published papers"]:
            (tmp_path / d).mkdir(parents=True)
        src = tmp_path / "_in" / "p.pdf"
        src.parent.mkdir()
        _write_minimal_pdf(src, title="Title", author="Smith, J.")

        log = UndoLog(log_dir=tmp_path / ".operation_log")
        log.begin_transaction("ingest")

        def boom(*a, **k):
            raise RuntimeError("disk full")

        monkeypatch.setattr(sysmod.shutil, "copy2", boom)
        org = OrganizationSystem(tmp_path, dry_run=False)
        meta = {"doi": "10.1/x", "authors": [{"family": "Smith", "given": "J."}]}
        org.organize(src, meta, "Smith, J. - Title.pdf", undo_log=log)
        # The copy op was recorded even though copy2 raised.
        assert any(op["type"] == "copy" for op in log._current_tx["operations"])

    def test_trash_move_is_recorded_before_the_file_moves(self, tmp_path, monkeypatch):
        # The preprint-to-trash move must be in the undo log BEFORE the file
        # moves, so a crash in the gap still leaves a reversible entry. This
        # used to assert the order of two lines of source text; the move now
        # goes through logged_move (which also carries the paper's record),
        # so the BEHAVIOUR is checked instead: the move fails, the entry is
        # already there.
        import processing.ingest as ingest
        import processing.undo_log as ul
        import processing.upgrade_to_published as up
        from processing.identity import enable_sidecar_mirror
        from processing.undo_log import UndoLog

        lib = tmp_path / "lib"
        enable_sidecar_mirror(lib)
        pre = lib / "02 - Unpublished papers" / "S" / "Smith, J. - A.pdf"
        pre.parent.mkdir(parents=True)
        pre.write_bytes(b"%PDF-1.4 preprint")

        def _download(doi, download_dir):
            f = Path(download_dir) / "pub.pdf"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"%PDF-1.4 the published version, a little longer")
            return f

        def boom(*a, **k):
            raise OSError("disk full")

        monkeypatch.setattr(up, "try_download_by_doi", _download)
        monkeypatch.setattr(ingest, "ingest_paper",
                            lambda p, **k: {"success": True, "destination": ""})
        monkeypatch.setattr(ul.shutil, "move", boom)
        log = UndoLog(log_dir=tmp_path / ".operation_log")
        log.begin_transaction("upgrade")
        res = up.upgrade_paper({"file": str(pre), "match": {"doi": "10.1/x"}},
                               lib, tmp_path / "dl", undo_log=log)
        assert "preprint move error" in res["action"], res
        assert pre.exists(), "the failed move left the preprint where it was"
        ops = [(op["type"], Path(op["source"]).name, Path(op["destination"]).parent.name)
               for op in log._current_tx["operations"]]
        assert ops == [("move", pre.name, "upgraded_preprints")], ops


# ---------------------------------------------------------------------------
# Truncated-download guard
# ---------------------------------------------------------------------------

class TestDownloadValidation:

    def _resp(self, length):
        class R:
            headers = {"Content-Length": str(length)}
        return R()

    def test_rejects_too_small(self, tmp_path):
        from processing.upgrade_to_published import _validate_pdf_download
        f = tmp_path / "x.pdf"
        f.write_bytes(b"%PDF" + b"0" * 10)  # 14 bytes
        assert _validate_pdf_download(f, self._resp(0)) is False
        assert not f.exists()

    def test_rejects_truncated_vs_content_length(self, tmp_path):
        from processing.upgrade_to_published import _validate_pdf_download
        f = tmp_path / "x.pdf"
        f.write_bytes(b"%PDF" + b"0" * 2000)  # 2004 bytes
        assert _validate_pdf_download(f, self._resp(999999)) is False
        assert not f.exists()

    def test_accepts_complete(self, tmp_path):
        from processing.upgrade_to_published import _validate_pdf_download
        f = tmp_path / "x.pdf"
        body = b"%PDF" + b"0" * 5000
        f.write_bytes(body)
        assert _validate_pdf_download(f, self._resp(len(body))) is True
        assert f.exists()


# ---------------------------------------------------------------------------
# Watcher skips Dropbox conflict copies
# ---------------------------------------------------------------------------

class TestWatcherConflictFilter:

    def test_conflict_copy_not_ingestable(self):
        from watcher.daemon import _is_ingestable_pdf
        p = Path("/inbox/Smith - Paper (DESKTOP-AB's conflicted copy 2026-06-15).pdf")
        assert _is_ingestable_pdf(p) is False

    def test_plain_pdf_is_ingestable(self):
        from watcher.daemon import _is_ingestable_pdf
        assert _is_ingestable_pdf(Path("/inbox/Smith - Paper.pdf")) is True

    def test_non_pdf_not_ingestable(self):
        from watcher.daemon import _is_ingestable_pdf
        assert _is_ingestable_pdf(Path("/inbox/notes.txt")) is False
