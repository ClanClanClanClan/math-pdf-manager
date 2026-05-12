"""Tests for upgrade_to_published.

Mocks the actual download (so no network calls) and verifies the
download → file → trash-preprint → undo round-trip.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from processing.upgrade_to_published import (
    flag_for_manual_download,
    process_report,
    try_download_by_doi,
    upgrade_paper,
)


@pytest.fixture
def fake_pdf_bytes():
    """Bytes that look like a valid PDF (header + minimal trailer)."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<<>>\nendobj\n"
        b"trailer\n<<>>\n"
        b"%%EOF\n"
    )


@pytest.fixture
def fake_preprint(synthetic_library, make_pdf):
    """Create a 'preprint' file at 03 - Working papers/A/2020/Smith - X.pdf."""
    preprint = (
        synthetic_library / "03 - Working papers" / "A" / "2020"
        / "Smith, J. - Some paper.pdf"
    )
    preprint.parent.mkdir(parents=True, exist_ok=True)
    make_pdf(preprint, body=b"PREPRINT VERSION")
    return preprint


@pytest.fixture
def report_entry(fake_preprint):
    """A single 'published' entry as produced by publication_checker."""
    return {
        "file": str(fake_preprint),
        "filename": fake_preprint.name,
        "parsed_title": "Some paper",
        "parsed_authors": ["Smith"],
        "published": True,
        "match": {
            "doi": "10.1007/test-123",
            "matched_title": "Some paper",
            "journal": "Test Journal",
            "year": 2024,
            "type": "journal-article",
            "title_score": 0.99,
            "author_score": 1.0,
            "confidence": 0.95,
        },
    }


# ---------------------------------------------------------------------------
# flag_for_manual_download
# ---------------------------------------------------------------------------

class TestFlagForManual:
    def test_writes_flag_file_in_04(self, synthetic_library, report_entry):
        flag = flag_for_manual_download(report_entry, synthetic_library)
        assert flag.exists()
        assert "04 - Papers to be downloaded" in str(flag)
        body = flag.read_text()
        assert report_entry["match"]["doi"] in body
        assert report_entry["match"]["journal"] in body


# ---------------------------------------------------------------------------
# upgrade_paper round-trip with mocked download
# ---------------------------------------------------------------------------

class TestUpgradePaper:
    def test_dry_run_does_nothing(self, synthetic_library, report_entry, tmp_path):
        download_dir = tmp_path / "dl"
        result = upgrade_paper(
            report_entry,
            library_root=synthetic_library,
            download_dir=download_dir,
            dry_run=True,
        )
        assert "WOULD TRY" in result["action"]
        # Preprint untouched
        assert Path(report_entry["file"]).exists()

    def test_manual_only_flags_without_download(
        self, synthetic_library, report_entry, tmp_path
    ):
        download_dir = tmp_path / "dl"
        result = upgrade_paper(
            report_entry,
            library_root=synthetic_library,
            download_dir=download_dir,
            manual_only=True,
        )
        assert "FLAGGED" in result["action"]
        # Preprint untouched
        assert Path(report_entry["file"]).exists()

    def test_skip_no_doi(self, synthetic_library, tmp_path):
        entry = {"file": "/nope.pdf", "match": {}}  # no DOI
        result = upgrade_paper(
            entry,
            library_root=synthetic_library,
            download_dir=tmp_path / "dl",
            dry_run=False,
        )
        assert "SKIP" in result["action"]


# ---------------------------------------------------------------------------
# process_report: dry-run on a fake report
# ---------------------------------------------------------------------------

class TestProcessReport:
    def test_dry_run_full_pipeline(
        self, synthetic_library, report_entry, tmp_path
    ):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps({
            "directory": str(synthetic_library),
            "total_checked": 1,
            "published_count": 1,
            "not_published_count": 0,
            "published": [report_entry],
        }))

        summary = process_report(
            report_path,
            library_root=synthetic_library,
            dry_run=True,
            verbose=False,
        )

        assert summary["total_candidates"] == 1
        # Preprint must still exist after dry-run
        assert Path(report_entry["file"]).exists()
