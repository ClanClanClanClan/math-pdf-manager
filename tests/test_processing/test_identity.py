"""Tests for ``processing.identity`` — the paper identity sidecar.

Cover:
* round-trip load/save with all fields populated
* missing sidecar yields a fresh object (``is_new() == True``)
* corrupt / truncated sidecars don't raise
* atomic write — interrupted save leaves the previous sidecar intact
* drift detection (hash mismatch flagged, hash absence ignored)
* state machine (recheck counter, permanently_unpublished)
* move/rename preserve the sidecar via ``move_with_sidecar``
* backfill walks a directory and writes minimal sidecars
* sidecar collisions (two papers landing on the same destination) refuse
  to clobber
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from processing.identity import (
    HASH_PREFIX_BYTES,
    PaperIdentity,
    SCHEMA_VERSION,
    backfill_directory,
    backfill_sidecar,
    compute_content_hash,
    move_with_sidecar,
    rename_with_sidecar,
    sidecar_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(path: Path, content: bytes = b"%PDF-1.4 fake content for test") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


# ---------------------------------------------------------------------------
# load / save round trip
# ---------------------------------------------------------------------------

class TestRoundTrip:

    def test_missing_sidecar_yields_new_object(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        ident = PaperIdentity.load(pdf)
        assert ident.is_new()
        assert ident.schema_version == SCHEMA_VERSION
        assert ident.doi == ""
        assert ident.copy_locations == []

    def test_save_then_load_preserves_all_fields(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        ident = PaperIdentity(
            doi="10.1007/s12345-024-0001-x",
            arxiv_id="2401.01234",
            copy_locations=["/lib/07a/paper.pdf", "/lib/07b/paper.pdf"],
            topic_codes=["07a", "07b"],
            recheck_count=2,
        )
        ident.save(pdf)
        assert sidecar_path(pdf).exists()

        loaded = PaperIdentity.load(pdf)
        assert not loaded.is_new()
        assert loaded.doi == "10.1007/s12345-024-0001-x"
        assert loaded.arxiv_id == "2401.01234"
        assert loaded.copy_locations == ["/lib/07a/paper.pdf", "/lib/07b/paper.pdf"]
        assert loaded.topic_codes == ["07a", "07b"]
        assert loaded.recheck_count == 2

    def test_save_records_original_filename_and_hash(self, tmp_path):
        pdf = _make_pdf(tmp_path / "Smith, J. - Paper.pdf")
        ident = PaperIdentity()
        ident.save(pdf)
        loaded = PaperIdentity.load(pdf)
        assert loaded.original_filename == "Smith, J. - Paper.pdf"
        assert len(loaded.content_sha256) == 64  # sha256 hex digest length

    def test_save_with_recompute_hash_false_preserves_existing(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf", content=b"%PDF-1.4 v1")
        ident = PaperIdentity()
        ident.save(pdf)
        old_hash = ident.content_sha256

        # Now mutate the file but save with recompute_hash=False
        pdf.write_bytes(b"%PDF-1.4 v2 different content")
        ident.save(pdf, recompute_hash=False)
        loaded = PaperIdentity.load(pdf)
        assert loaded.content_sha256 == old_hash


# ---------------------------------------------------------------------------
# Robustness — bad sidecars never raise
# ---------------------------------------------------------------------------

class TestRobustness:

    def test_truncated_json_treated_as_missing(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        sidecar_path(pdf).write_text("{not valid json")
        ident = PaperIdentity.load(pdf)
        assert ident.is_new()  # treated as fresh

    def test_non_object_json_treated_as_missing(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        sidecar_path(pdf).write_text('["this", "is", "a", "list"]')
        ident = PaperIdentity.load(pdf)
        assert ident.is_new()

    def test_unknown_fields_ignored_for_forward_compat(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        sidecar_path(pdf).write_text(json.dumps({
            "schema_version": 999,  # future schema
            "doi": "10.1/x",
            "future_field_we_dont_know_about": [1, 2, 3],
        }))
        ident = PaperIdentity.load(pdf)
        # Unknown field dropped, known field kept, NOT treated as new.
        assert not ident.is_new()
        assert ident.doi == "10.1/x"

    def test_atomic_write_leaves_no_tmp_file(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        PaperIdentity(doi="10.1/x").save(pdf)
        tmps = list(tmp_path.glob("*.tmp"))
        assert tmps == []

    def test_save_with_missing_pdf_still_writes_sidecar(self, tmp_path):
        # The sidecar can be saved before the PDF is in place (rare
        # but happens during migration).  In that case the hash is
        # simply empty, not an error.
        pdf = tmp_path / "ghost.pdf"
        PaperIdentity(doi="10.1/x").save(pdf)
        loaded = PaperIdentity.load(pdf)
        assert loaded.doi == "10.1/x"
        assert loaded.content_sha256 == ""


# ---------------------------------------------------------------------------
# Hash + drift detection
# ---------------------------------------------------------------------------

class TestHashAndDrift:

    def test_compute_content_hash_stable(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf", content=b"x" * 100)
        h1 = compute_content_hash(pdf)
        h2 = compute_content_hash(pdf)
        assert h1 == h2 and len(h1) == 64

    def test_compute_content_hash_hashes_only_prefix(self, tmp_path):
        # Files that share the first 1MB get the same hash even if
        # they differ later — this is a deliberate trade-off for speed.
        prefix = b"y" * HASH_PREFIX_BYTES
        a = _make_pdf(tmp_path / "a.pdf", content=prefix + b"AAAA")
        b = _make_pdf(tmp_path / "b.pdf", content=prefix + b"BBBB")
        assert compute_content_hash(a) == compute_content_hash(b)

    def test_drift_check_no_drift(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        ident = PaperIdentity()
        ident.save(pdf)
        assert ident.drift_check(pdf) is None

    def test_drift_check_detects_changed_content(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf", content=b"%PDF-1.4 original")
        ident = PaperIdentity()
        ident.save(pdf)

        pdf.write_bytes(b"%PDF-1.4 modified content body")
        drift = ident.drift_check(pdf)
        assert drift is not None
        assert "drift" in drift

    def test_drift_check_with_empty_hash_returns_none(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        ident = PaperIdentity()  # no hash stored
        assert ident.drift_check(pdf) is None

    def test_drift_check_missing_pdf_reports(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        ident = PaperIdentity()
        ident.save(pdf)
        pdf.unlink()
        drift = ident.drift_check(pdf)
        assert drift is not None
        assert "missing" in drift.lower()


# ---------------------------------------------------------------------------
# Publication-check state machine
# ---------------------------------------------------------------------------

class TestStateMachine:

    def test_miss_increments_recheck_count(self):
        ident = PaperIdentity()
        assert ident.recheck_count == 0
        ident.record_publication_check(hit=False, source="crossref")
        assert ident.recheck_count == 1
        ident.record_publication_check(hit=False, source="crossref")
        assert ident.recheck_count == 2

    def test_hit_does_not_increment_recheck_count(self):
        ident = PaperIdentity()
        ident.record_publication_check(hit=True, source="crossref", confidence=0.99)
        assert ident.recheck_count == 0
        assert len(ident.publication_checks) == 1
        assert ident.publication_checks[0]["hit"] is True

    def test_should_skip_after_budget_exhausted(self):
        ident = PaperIdentity()
        for _ in range(3):
            ident.record_publication_check(hit=False, source="crossref")
        assert ident.should_skip_publication_check(max_rechecks=3)
        assert not ident.should_skip_publication_check(max_rechecks=10)

    def test_permanently_unpublished_skipped_immediately(self):
        ident = PaperIdentity(permanently_unpublished=True)
        assert ident.should_skip_publication_check()

    def test_last_check_date_updates(self):
        ident = PaperIdentity()
        assert ident.last_check_date == ""
        ident.record_publication_check(hit=False, source="crossref")
        assert ident.last_check_date != ""


# ---------------------------------------------------------------------------
# Move / rename preservation
# ---------------------------------------------------------------------------

class TestMoveAndRename:

    def test_move_with_sidecar_moves_both(self, tmp_path):
        src = _make_pdf(tmp_path / "src.pdf")
        PaperIdentity(doi="10.1/x").save(src)
        dst = tmp_path / "subdir" / "dst.pdf"
        move_with_sidecar(src, dst)
        assert not src.exists()
        assert not sidecar_path(src).exists()
        assert dst.exists()
        assert sidecar_path(dst).exists()
        # Identity preserved
        assert PaperIdentity.load(dst).doi == "10.1/x"

    def test_move_with_no_sidecar_still_moves_pdf(self, tmp_path):
        src = _make_pdf(tmp_path / "src.pdf")
        dst = tmp_path / "dst.pdf"
        move_with_sidecar(src, dst)
        assert dst.exists()
        assert not sidecar_path(dst).exists()

    def test_move_refuses_to_clobber_existing_sidecar(self, tmp_path):
        src = _make_pdf(tmp_path / "src.pdf")
        PaperIdentity(doi="10.1/src").save(src)
        dst = _make_pdf(tmp_path / "dst.pdf")
        PaperIdentity(doi="10.1/dst").save(dst)
        # destination sidecar exists; the PDF doesn't (we'd remove dst.pdf
        # first in real life), so simulate the contended condition.
        dst.unlink()
        with pytest.raises(FileExistsError, match="sidecar already exists"):
            move_with_sidecar(src, dst)

    def test_rename_with_sidecar_preserves_identity(self, tmp_path):
        src = _make_pdf(tmp_path / "old name.pdf")
        PaperIdentity(arxiv_id="2401.01234").save(src)
        dst = tmp_path / "new name.pdf"
        rename_with_sidecar(src, dst)
        assert dst.exists()
        assert sidecar_path(dst).exists()
        assert PaperIdentity.load(dst).arxiv_id == "2401.01234"

    def test_move_repaths_copy_locations(self, tmp_path):
        """After logged_move, the sidecar's copy_locations must reflect
        the destination, not the source.  Audit caught this as a real
        bug -- the topic router would otherwise chase a path that
        doesn't exist anymore."""
        from processing.undo_log import logged_move
        src = _make_pdf(tmp_path / "src.pdf")
        ident = PaperIdentity()
        ident.copy_locations = [str(src), "/some/other/copy.pdf"]
        ident.save(src)

        dst = tmp_path / "subdir" / "dst.pdf"
        logged_move(src, dst)

        reloaded = PaperIdentity.load(dst)
        assert str(dst) in reloaded.copy_locations
        assert str(src) not in reloaded.copy_locations
        assert "/some/other/copy.pdf" in reloaded.copy_locations  # unrelated entries preserved

    def test_rename_repaths_copy_locations(self, tmp_path):
        from processing.undo_log import logged_rename
        old = _make_pdf(tmp_path / "old.pdf")
        ident = PaperIdentity()
        ident.copy_locations = [str(old)]
        ident.save(old)

        new = tmp_path / "new.pdf"
        logged_rename(old, new)
        reloaded = PaperIdentity.load(new)
        assert reloaded.copy_locations == [str(new)]

    def test_move_with_undo_log_records_both_ops(self, tmp_path):
        from processing.undo_log import UndoLog

        src = _make_pdf(tmp_path / "src.pdf")
        PaperIdentity(doi="10.1/x").save(src)
        dst = tmp_path / "sub" / "dst.pdf"

        log = UndoLog(log_dir=tmp_path / "ops")
        tx_id = log.begin_transaction("move with sidecar")
        move_with_sidecar(src, dst, undo_log=log)
        log.commit()

        tx = json.loads((tmp_path / "ops" / f"{tx_id}.json").read_text())
        kinds = [op["type"] for op in tx["operations"]]
        # PDF move first, then sidecar move
        assert kinds == ["move", "move"]
        # And undo brings them back
        log.undo_transaction(tx_id)
        assert src.exists()
        assert sidecar_path(src).exists()
        assert not dst.exists()
        assert not sidecar_path(dst).exists()


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------

class TestBackfill:

    def test_backfill_single_writes_sidecar(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        assert backfill_sidecar(pdf) is True
        assert sidecar_path(pdf).exists()

    def test_backfill_single_skips_existing(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        PaperIdentity(doi="10.1/x").save(pdf)
        assert backfill_sidecar(pdf) is False
        # And the existing sidecar wasn't overwritten
        assert PaperIdentity.load(pdf).doi == "10.1/x"

    def test_backfill_single_overwrite_replaces(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        PaperIdentity(doi="10.1/x").save(pdf)
        assert backfill_sidecar(pdf, overwrite=True) is True
        # DOI is wiped because backfill writes a minimal sidecar
        assert PaperIdentity.load(pdf).doi == ""

    def test_backfill_directory_walks_recursively(self, tmp_path):
        _make_pdf(tmp_path / "a.pdf")
        _make_pdf(tmp_path / "sub" / "b.pdf")
        _make_pdf(tmp_path / "sub" / "deep" / "c.pdf")
        summary = backfill_directory(tmp_path)
        assert summary["scanned"] == 3
        assert summary["written"] == 3
        assert summary["skipped"] == 0
        assert summary["errors"] == 0

    def test_backfill_directory_skips_trash(self, tmp_path):
        _make_pdf(tmp_path / "live.pdf")
        _make_pdf(tmp_path / ".trash" / "old.pdf")
        summary = backfill_directory(tmp_path)
        assert summary["scanned"] == 1
        assert summary["written"] == 1

    def test_backfill_directory_respects_limit(self, tmp_path):
        for i in range(5):
            _make_pdf(tmp_path / f"p{i}.pdf")
        summary = backfill_directory(tmp_path, limit=2)
        assert summary["scanned"] == 2
        assert summary["written"] == 2

    def test_backfill_sets_ingest_timestamp(self, tmp_path):
        pdf = _make_pdf(tmp_path / "paper.pdf")
        backfill_sidecar(pdf)
        ident = PaperIdentity.load(pdf)
        assert ident.first_ingested_at  # non-empty ISO string

    def test_backfill_missing_pdf_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            backfill_sidecar(tmp_path / "nonexistent.pdf")


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------

class TestCLI:

    def test_cli_backfill(self, tmp_path, capsys):
        from processing.identity import main
        _make_pdf(tmp_path / "a.pdf")
        _make_pdf(tmp_path / "b.pdf")
        main(["backfill", str(tmp_path)])
        out = capsys.readouterr().out
        assert "Scanned 2 PDFs" in out
        assert "wrote 2" in out

    def test_cli_show_missing(self, tmp_path, capsys):
        from processing.identity import main
        pdf = _make_pdf(tmp_path / "p.pdf")
        main(["show", str(pdf)])
        out = capsys.readouterr().out
        assert "No sidecar" in out

    def test_cli_show_existing(self, tmp_path, capsys):
        from processing.identity import main
        pdf = _make_pdf(tmp_path / "p.pdf")
        PaperIdentity(doi="10.1/x").save(pdf)
        main(["show", str(pdf)])
        out = capsys.readouterr().out
        assert "10.1/x" in out

    def test_cli_drift_clean(self, tmp_path, capsys):
        from processing.identity import main
        pdf = _make_pdf(tmp_path / "p.pdf")
        PaperIdentity().save(pdf)
        main(["drift", str(pdf)])
        out = capsys.readouterr().out
        assert "OK" in out

    def test_cli_drift_dirty(self, tmp_path, capsys):
        from processing.identity import main
        pdf = _make_pdf(tmp_path / "p.pdf")
        PaperIdentity().save(pdf)
        pdf.write_bytes(b"different content")
        main(["drift", str(pdf)])
        out = capsys.readouterr().out
        assert "DRIFT" in out
