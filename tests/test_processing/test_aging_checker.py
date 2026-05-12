"""Tests for the aging checker.

Covers:
- Year-cutoff math (papers older than max_age_years are flagged).
- Loose files (files in 03/ root, no year subfolder) are skipped, not crashed on.
- Routing to UNPUBLISHED with the right alpha-subdir.
- The transition phase tolerates entries without ``destination``.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from processing.aging_checker import find_aged_papers, transition_aged_papers


@pytest.fixture
def aged_library(synthetic_library, make_pdf):
    """Populate 03 - Working papers/ with a small set of aged + recent papers."""
    root = synthetic_library
    working = root / "03 - Working papers"

    current = datetime.now().year
    old_year = current - 10  # definitely beyond any sensible max_age_years
    fresh_year = current - 1

    # Properly-organized aged paper: 03/A/<year>/<file>
    aged_dir = working / "A" / str(old_year)
    aged_dir.mkdir(parents=True)
    make_pdf(aged_dir / "Abraham, R. - An old paper.pdf")

    # Properly-organized fresh paper: 03/B/<recent_year>/<file>
    fresh_dir = working / "B" / str(fresh_year)
    fresh_dir.mkdir(parents=True)
    make_pdf(fresh_dir / "Brown, A. - A fresh paper.pdf")

    # Loose file in 03/ root (no year folder) — must NOT crash transition
    make_pdf(working / "Loose, F. - Wandering pdf.pdf")

    # File directly in alpha dir (no year subdir) — should be skipped
    (working / "C").mkdir(exist_ok=True)
    make_pdf(working / "C" / "Carter, X. - No year folder.pdf")

    return root


class TestFindAgedPapers:
    def test_finds_only_aged_papers(self, aged_library):
        candidates = find_aged_papers(aged_library, max_age_years=5)
        # Only Abraham (old_year) should be flagged as aged
        names = [c["filename"] for c in candidates]
        assert any("Abraham" in n for n in names)
        assert not any("Brown" in n for n in names)
        assert not any("Loose" in n for n in names)
        assert not any("Carter" in n for n in names)

    def test_aged_paper_has_destination(self, aged_library):
        candidates = find_aged_papers(aged_library, max_age_years=5)
        for c in candidates:
            assert c.get("destination"), f"missing destination: {c}"
            # Should route to UNPUBLISHED
            assert "02 - Unpublished" in c["destination"]

    def test_aged_paper_alpha_subdir(self, aged_library):
        candidates = find_aged_papers(aged_library, max_age_years=5)
        abraham = next((c for c in candidates if "Abraham" in c["filename"]), None)
        assert abraham is not None
        assert abraham["first_author_alpha"] == "A"

    def test_no_working_dir_returns_empty(self, tmp_path):
        # Library exists but no 03/ folder
        result = find_aged_papers(tmp_path, max_age_years=5)
        assert result == []


class TestTransitionAgedPapers:
    def test_dry_run_does_not_move(self, aged_library):
        candidates = find_aged_papers(aged_library, max_age_years=5)
        results = transition_aged_papers(candidates, dry_run=True)
        # All sources should still exist
        for c in candidates:
            assert Path(c["path"]).exists(), f"file moved in dry-run: {c['path']}"
        # All result statuses should say WOULD MOVE
        assert all("WOULD MOVE" in r["status"] for r in results)

    def test_loose_file_does_not_crash(self, aged_library):
        # Synthetic: a candidate dict without 'destination' (loose file)
        bogus = [{"filename": "loose.pdf", "path": "/nope.pdf"}]
        # Must NOT raise — it should produce a SKIP entry instead.
        results = transition_aged_papers(bogus, dry_run=True)
        assert any("SKIP" in r["status"] for r in results)
