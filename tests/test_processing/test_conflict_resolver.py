"""Tests for ``processing.conflict_resolver`` (Phase 6)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from processing.conflict_resolver import (
    compare,
    find_canonical_for_conflict,
    resolve_keep_both,
    resolve_keep_canonical,
    resolve_keep_conflict,
    scan_conflicts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_pdf(path: Path, content: bytes = b"%PDF-1.4 fake") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


# ---------------------------------------------------------------------------
# find_canonical_for_conflict
# ---------------------------------------------------------------------------

class TestFindCanonical:

    def test_strips_dropbox_user_variant(self, tmp_path):
        p = tmp_path / "Smith, J. - Paper (DESKTOP-ABC's conflicted copy 2024-05-13).pdf"
        out = find_canonical_for_conflict(p)
        assert out == tmp_path / "Smith, J. - Paper.pdf"

    def test_strips_modern_variant(self, tmp_path):
        p = tmp_path / "Paper (conflicted copy 2025-01-02).pdf"
        assert find_canonical_for_conflict(p) == tmp_path / "Paper.pdf"

    def test_case_insensitive(self, tmp_path):
        p = tmp_path / "X (Conflicted Copy 2024-01-01).pdf"
        assert find_canonical_for_conflict(p) == tmp_path / "X.pdf"

    def test_non_conflict_returns_none(self, tmp_path):
        assert find_canonical_for_conflict(tmp_path / "normal.pdf") is None

    def test_empty_stem_after_strip_returns_none(self, tmp_path):
        p = tmp_path / "(conflicted copy 2025-01-02).pdf"
        # Everything is the suffix; stripping leaves an empty stem.
        assert find_canonical_for_conflict(p) is None


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------

class TestCompare:

    def test_canonical_missing_suggests_keep_conflict(self, tmp_path):
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
            content=b"%PDF-1.4 c",
        )
        out = compare(conflict)
        assert out.canonical_exists is False
        assert out.suggested == "keep_conflict"

    def test_identical_files_suggest_keep_canonical(self, tmp_path):
        body = b"%PDF-1.4 identical content here for testing"
        canonical = _write_pdf(tmp_path / "Foo.pdf", content=body)
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
            content=body,
        )
        out = compare(conflict)
        assert out.canonical_exists is True
        assert out.suggested == "keep_canonical"
        assert "redundant" in out.notes[0].lower()

    def test_smaller_conflict_same_pages_suggests_canonical(self, tmp_path):
        # We can't easily synthesize page-count equality without a real
        # PDF library, but we can mock _page_count.
        canonical = _write_pdf(tmp_path / "Foo.pdf", content=b"%PDF" + b"x" * 1000)
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
            content=b"%PDF" + b"y" * 500,
        )
        from unittest.mock import patch
        with patch("processing.conflict_resolver._page_count", return_value=3):
            out = compare(conflict)
        assert out.suggested == "keep_canonical"

    def test_different_suggests_review(self, tmp_path):
        canonical = _write_pdf(tmp_path / "Foo.pdf", content=b"%PDF small")
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
            content=b"%PDF" + b"x" * 5000,
        )
        from unittest.mock import patch
        with patch("processing.conflict_resolver._page_count",
                   side_effect=[2, 7]):  # canonical=2, conflict=7
            out = compare(conflict)
        assert out.suggested == "review"


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

class TestResolveKeepCanonical:

    def test_moves_conflict_to_trash(self, tmp_path):
        canonical = _write_pdf(tmp_path / "Foo.pdf")
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
        )
        ok, msg = resolve_keep_canonical(conflict, tmp_path)
        assert ok
        assert not conflict.exists()
        trashed = tmp_path / ".trash" / "conflict_copies" / conflict.name
        assert trashed.exists()
        # Canonical untouched
        assert canonical.exists()

    def test_collision_disambiguates(self, tmp_path):
        _write_pdf(tmp_path / "Foo.pdf")
        c1 = _write_pdf(tmp_path / "Foo (conflicted copy 2024-05-13).pdf")
        resolve_keep_canonical(c1, tmp_path)
        # Re-create another conflict with the same name and resolve again
        c2 = _write_pdf(tmp_path / "Foo (conflicted copy 2024-05-13).pdf")
        resolve_keep_canonical(c2, tmp_path)
        trash = tmp_path / ".trash" / "conflict_copies"
        names = {p.name for p in trash.iterdir()}
        assert len(names) == 2
        assert any(n.endswith(" (1).pdf") for n in names), names

    def test_missing_conflict_reports_failure(self, tmp_path):
        ok, msg = resolve_keep_canonical(tmp_path / "ghost.pdf", tmp_path)
        assert not ok
        assert "gone" in msg


class TestResolveKeepConflict:

    def test_promotes_conflict_to_canonical(self, tmp_path):
        canonical = _write_pdf(tmp_path / "Foo.pdf", content=b"old")
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
            content=b"new",
        )
        ok, msg = resolve_keep_conflict(conflict, tmp_path)
        assert ok
        # Conflict gone, canonical is now the new content
        assert not conflict.exists()
        assert canonical.exists()
        assert canonical.read_bytes() == b"new"
        # Old canonical retired to trash
        retired = tmp_path / ".trash" / "conflict_copies" / "Foo.old.pdf"
        assert retired.exists()
        assert retired.read_bytes() == b"old"

    def test_missing_canonical_just_renames(self, tmp_path):
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
            content=b"new",
        )
        ok, msg = resolve_keep_conflict(conflict, tmp_path)
        assert ok
        assert (tmp_path / "Foo.pdf").exists()

    def test_merges_sidecars_when_both_have_history(self, tmp_path):
        """Audit-5 #4: keep_conflict must NOT silently drop the
        canonical's publication-check history when promoting a
        conflict that also has a sidecar."""
        from processing.identity import PaperIdentity, sidecar_path
        canonical = _write_pdf(tmp_path / "Foo.pdf", content=b"%PDF-old")
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
            content=b"%PDF-new",
        )
        # Canonical has months of recheck history
        canonical_id = PaperIdentity(doi="10.1/canonical")
        canonical_id.record_publication_check(
            hit=False, source="crossref", confidence=0.0,
        )
        canonical_id.record_publication_check(
            hit=False, source="crossref", confidence=0.0,
        )
        canonical_id.save(canonical)
        # Conflict has a different DOI and topic code, fresh history
        conflict_id = PaperIdentity(arxiv_id="2401.01234")
        conflict_id.topic_codes = ["07a"]
        conflict_id.save(conflict)

        ok, msg = resolve_keep_conflict(conflict, tmp_path)
        assert ok

        promoted = PaperIdentity.load(canonical)
        # DOI from the canonical's history is preserved (conflict had none)
        assert promoted.doi == "10.1/canonical"
        # arxiv_id from the conflict is preserved
        assert promoted.arxiv_id == "2401.01234"
        # Publication-check history concatenated (canonical's 2 + 0)
        assert len(promoted.publication_checks) == 2
        # Topic code carried forward
        assert "07a" in promoted.topic_codes

    def test_undo_restores_state(self, tmp_path):
        from processing.undo_log import UndoLog
        canonical = _write_pdf(tmp_path / "Foo.pdf", content=b"old")
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
            content=b"new",
        )
        log = UndoLog(log_dir=tmp_path / ".ops")
        tx = log.begin_transaction("keep conflict")
        resolve_keep_conflict(conflict, tmp_path, undo_log=log)
        log.commit()
        # Reverse: canonical comes back with "old", conflict comes back
        log.undo_transaction(tx)
        assert canonical.exists() and canonical.read_bytes() == b"old"
        assert conflict.exists() and conflict.read_bytes() == b"new"


class TestResolveKeepBoth:

    def test_appends_v2_suffix(self, tmp_path):
        _write_pdf(tmp_path / "Foo.pdf")
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
        )
        ok, msg = resolve_keep_both(conflict, tmp_path)
        assert ok
        assert (tmp_path / "Foo-v2.pdf").exists()
        assert not conflict.exists()

    def test_iterates_when_v2_taken(self, tmp_path):
        _write_pdf(tmp_path / "Foo.pdf")
        _write_pdf(tmp_path / "Foo-v2.pdf")
        conflict = _write_pdf(
            tmp_path / "Foo (conflicted copy 2024-05-13).pdf",
        )
        resolve_keep_both(conflict, tmp_path)
        assert (tmp_path / "Foo-v3.pdf").exists()

    def test_non_conflict_path_rejected(self, tmp_path):
        p = _write_pdf(tmp_path / "normal.pdf")
        ok, msg = resolve_keep_both(p, tmp_path)
        assert not ok


# ---------------------------------------------------------------------------
# scan_conflicts
# ---------------------------------------------------------------------------

class TestScanConflicts:

    def test_finds_conflicts_recursively(self, tmp_path):
        _write_pdf(tmp_path / "Foo.pdf")
        _write_pdf(tmp_path / "Foo (conflicted copy 2024-05-13).pdf")
        _write_pdf(
            tmp_path / "sub" / "Bar (conflicted copy 2025-01-01).pdf"
        )
        out = scan_conflicts(tmp_path)
        assert len(out) == 2
        # Each ConflictComparison has at least conflict and (maybe) canonical
        for c in out:
            assert c.conflict.endswith(".pdf")

    def test_no_conflicts_yields_empty(self, tmp_path):
        _write_pdf(tmp_path / "x.pdf")
        assert scan_conflicts(tmp_path) == []

    def test_missing_root_returns_empty(self, tmp_path):
        assert scan_conflicts(tmp_path / "nope") == []
