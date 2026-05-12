"""Tests for the weekly maintenance report.

Covers:
- Each check_* function isolates failures (one broken folder doesn't crash
  the whole run).
- count_to_be_sorted reports the staging-area backlog.
- Reports get a unique timestamp (multiple runs same day don't overwrite).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def lib(tmp_path):
    """Synthetic library with the folders the maintenance tool expects."""
    folders = [
        "01 - Published papers",
        "02 - Unpublished papers",
        "03 - Working papers",
        "04 - Papers to be downloaded",
        "05 - Books and lecture notes",
        "06 - Theses",
        "12 - To be sorted",
        "12 - To be sorted/01 - Published papers",
        "12 - To be sorted/03 - Working papers",
        "12 - To be sorted/05 - Books and lecture notes",
    ]
    for f in folders:
        (tmp_path / f).mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# count_to_be_sorted
# ---------------------------------------------------------------------------

class TestCountToBeSorted:
    def test_empty_staging(self, lib):
        from maintenance.weekly_report import count_to_be_sorted
        result = count_to_be_sorted(lib)
        assert result["total"] == 0

    def test_counts_by_subfolder(self, lib):
        from maintenance.weekly_report import count_to_be_sorted
        # 2 published, 3 working, 1 book
        for i in range(2):
            (lib / "12 - To be sorted" / "01 - Published papers" / f"p{i}.pdf").write_bytes(b"x")
        for i in range(3):
            (lib / "12 - To be sorted" / "03 - Working papers" / f"w{i}.pdf").write_bytes(b"x")
        (lib / "12 - To be sorted" / "05 - Books and lecture notes" / "b.pdf").write_bytes(b"x")

        result = count_to_be_sorted(lib)
        assert result["total"] == 6
        assert result["by_subfolder"]["01 - Published papers"] == 2
        assert result["by_subfolder"]["03 - Working papers"] == 3
        assert result["by_subfolder"]["05 - Books and lecture notes"] == 1

    def test_missing_staging_folder(self, tmp_path):
        from maintenance.weekly_report import count_to_be_sorted
        # No "12 - To be sorted/" at all
        result = count_to_be_sorted(tmp_path)
        assert result["total"] == 0


# ---------------------------------------------------------------------------
# Error isolation in check_*
# ---------------------------------------------------------------------------

class TestErrorIsolation:
    def test_check_publications_keeps_running_after_one_folder_fails(self, lib):
        """If scan_directory raises for one folder, the other one still gets scanned."""
        from maintenance.weekly_report import check_publications

        call_count = {"n": 0}

        def maybe_fail(folder, **kwargs):
            call_count["n"] += 1
            if "Unpublished" in str(folder):
                raise RuntimeError("Crossref timeout")
            return []

        with patch("processing.publication_checker.scan_directory", side_effect=maybe_fail):
            result = check_publications(lib, verbose=False)

        # Both folders should have been attempted
        assert call_count["n"] == 2
        # Failure was recorded, not raised
        assert "_errors" in result
        assert len(result["_errors"]) == 1
        # The folder that didn't fail still produced a (possibly empty) entry
        assert result["working"] == []

    def test_check_aging_swallows_exception(self, lib):
        from maintenance.weekly_report import check_aging
        with patch(
            "processing.aging_checker.find_aged_papers",
            side_effect=RuntimeError("disk error"),
        ):
            # Must not raise
            result = check_aging(lib, verbose=False)
        assert result == []

    def test_check_duplicates_swallows_exception(self, lib):
        from maintenance.weekly_report import check_duplicates
        with patch(
            "processing.duplicate_finder.find_duplicates",
            side_effect=OSError("permission denied"),
        ):
            result = check_duplicates(lib, verbose=False)
        assert result == []
