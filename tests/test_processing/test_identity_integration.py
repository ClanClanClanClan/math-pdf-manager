"""Integration tests: identity sidecar through the real pipeline.

These tests use the synthetic library helpers in ``tests/harness`` to
prove the sidecar travels correctly through ``ingest_paper`` and the
``logged_move``/``logged_rename`` helpers.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))

from synth_library import _write_minimal_pdf  # noqa: E402

from processing.identity import PaperIdentity, sidecar_path  # noqa: E402


# ---------------------------------------------------------------------------
# ingest_paper writes the sidecar
# ---------------------------------------------------------------------------

def test_ingest_writes_sidecar_at_filing(tmp_path, synthetic_library):
    """A successful ingest leaves a sidecar next to the filed PDF."""
    from processing.ingest import ingest_paper

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    src = inbox / "drop.pdf"
    _write_minimal_pdf(src, title="On Brownian Motion", author="Smith, J.")

    result = ingest_paper(src, library_root=synthetic_library, status="working", dry_run=False)
    assert result["success"], f"ingest failed: {result.get('error') or result.get('actions')}"

    dest = Path(result["destination"])
    assert dest.exists()
    assert sidecar_path(dest).exists(), "sidecar was not written next to filed PDF"

    ident = PaperIdentity.load(dest)
    assert not ident.is_new()
    assert ident.original_filename == "drop.pdf"
    assert ident.first_ingested_at, "ingest timestamp empty"
    assert str(dest) in ident.copy_locations
    # Content hash recorded
    assert len(ident.content_sha256) == 64


def test_ingest_preserves_existing_sidecar_metadata(tmp_path, synthetic_library):
    """If a sidecar already exists (re-ingest), DOI/arXiv aren't wiped."""
    from processing.ingest import ingest_paper

    src = tmp_path / "drop.pdf"
    _write_minimal_pdf(src, title="Re-ingest paper", author="Brown, A.")

    # First ingest
    r1 = ingest_paper(src, library_root=synthetic_library, status="working", dry_run=False)
    assert r1["success"]
    dest = Path(r1["destination"])

    # Manually enrich the sidecar with a DOI an earlier pass would have
    # discovered.
    ident = PaperIdentity.load(dest)
    ident.doi = "10.1007/s10000-024-0042-z"
    ident.save(dest)

    # Re-ingest by copying the PDF back into the inbox and processing
    # again — the system shouldn't lose the DOI.
    import shutil
    inbox = tmp_path / "inbox2"
    inbox.mkdir()
    again = inbox / "drop2.pdf"
    shutil.copy2(dest, again)

    r2 = ingest_paper(again, library_root=synthetic_library, status="working", dry_run=False)
    assert r2["success"]
    dest2 = Path(r2["destination"])
    ident2 = PaperIdentity.load(dest2)
    assert ident2.doi == "10.1007/s10000-024-0042-z", \
        "re-ingest wiped the previously-known DOI"


def test_ingest_dry_run_writes_no_sidecar(tmp_path, synthetic_library):
    """Dry-run mode is observably side-effect-free at the sidecar level too."""
    from processing.ingest import ingest_paper

    src = tmp_path / "drop.pdf"
    _write_minimal_pdf(src, title="Should not file", author="Doe, J.")
    ingest_paper(src, library_root=synthetic_library, status="working", dry_run=True)

    sidecars = list(synthetic_library.rglob("*.meta.json"))
    assert sidecars == []


# ---------------------------------------------------------------------------
# logged_move carries the sidecar
# ---------------------------------------------------------------------------

def test_logged_move_carries_sidecar(tmp_path):
    from processing.undo_log import UndoLog, logged_move

    src = tmp_path / "paper.pdf"
    _write_minimal_pdf(src, title="x", author="y")
    PaperIdentity(doi="10.1/x").save(src)

    log = UndoLog(log_dir=tmp_path / "ops")
    tx_id = log.begin_transaction("test")
    dst = tmp_path / "moved" / "paper.pdf"
    logged_move(src, dst, undo_log=log)
    log.commit()

    assert not src.exists()
    assert not sidecar_path(src).exists()
    assert dst.exists()
    assert sidecar_path(dst).exists()
    assert PaperIdentity.load(dst).doi == "10.1/x"

    # And undo brings both back
    log.undo_transaction(tx_id)
    assert src.exists()
    assert sidecar_path(src).exists()
    assert not dst.exists()
    assert not sidecar_path(dst).exists()
    assert PaperIdentity.load(src).doi == "10.1/x"


def test_logged_move_without_sidecar_works(tmp_path):
    """PDFs without sidecars (legacy files) still move cleanly."""
    from processing.undo_log import logged_move

    src = tmp_path / "paper.pdf"
    _write_minimal_pdf(src, title="x", author="y")
    dst = tmp_path / "dst.pdf"
    logged_move(src, dst)
    assert dst.exists()
    assert not sidecar_path(dst).exists()


def test_logged_move_refuses_to_clobber_destination_sidecar(tmp_path):
    from processing.undo_log import logged_move

    src = tmp_path / "src.pdf"
    _write_minimal_pdf(src, title="x", author="y")
    PaperIdentity(doi="10.1/src").save(src)
    dst = tmp_path / "dst.pdf"
    PaperIdentity(doi="10.1/dst").save(dst)
    # destination sidecar exists; destination PDF doesn't (simulating a
    # rare contended state)
    with pytest.raises(FileExistsError, match="sidecar already exists"):
        logged_move(src, dst)


def test_logged_rename_carries_sidecar(tmp_path):
    from processing.undo_log import logged_rename

    src = tmp_path / "old.pdf"
    _write_minimal_pdf(src, title="x", author="y")
    PaperIdentity(arxiv_id="2401.01234").save(src)

    dst = tmp_path / "new.pdf"
    logged_rename(src, dst)
    assert dst.exists()
    assert sidecar_path(dst).exists()
    assert PaperIdentity.load(dst).arxiv_id == "2401.01234"


def test_logged_copy_does_not_copy_sidecar(tmp_path):
    """Copies need their own identity — sidecar duplication would point
    at the wrong file's history."""
    from processing.undo_log import logged_copy

    src = tmp_path / "src.pdf"
    _write_minimal_pdf(src, title="x", author="y")
    PaperIdentity(doi="10.1/x").save(src)

    dst = tmp_path / "dst.pdf"
    logged_copy(src, dst)
    assert dst.exists()
    # sidecar of dst is NOT auto-created
    assert not sidecar_path(dst).exists()
    # And the original sidecar is untouched
    assert sidecar_path(src).exists()
