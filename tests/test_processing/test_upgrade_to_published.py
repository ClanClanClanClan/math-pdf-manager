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

    def _report(self, tmp_path, entries):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps({
            "total_checked": len(entries),
            "published_count": len(entries),
            "not_published_count": 0,
            "published": entries,
        }))
        return report_path

    def _tmp_undolog(self, monkeypatch, tmp_path):
        # process_report constructs UndoLog() with the DEFAULT log dir (the
        # real library's .operation_log) — point it at a tmp dir instead.
        import processing.upgrade_to_published as up
        from processing.undo_log import UndoLog
        log_dir = tmp_path / ".operation_log"
        monkeypatch.setattr(up, "UndoLog", lambda: UndoLog(log_dir=log_dir))
        return log_dir

    def test_one_paper_raising_does_not_abort_batch(
        self, synthetic_library, report_entry, tmp_path, monkeypatch
    ):
        # Regression (audit): a raise mid-batch used to skip commit(),
        # losing the undo record for papers already processed.
        import processing.upgrade_to_published as up
        log_dir = self._tmp_undolog(monkeypatch, tmp_path)

        bad = dict(report_entry, filename="bad.pdf")
        good = report_entry

        real = up.upgrade_paper
        calls = {"n": 0}

        def flaky(entry, *a, **k):
            calls["n"] += 1
            # NB: entries round-trip through the report JSON, so compare by
            # value (filename), never by object identity.
            if entry.get("filename") == "bad.pdf":
                raise OSError("simulated network error")
            # Simulate real work that records an operation.
            undo_log = k.get("undo_log")
            if undo_log is not None:
                undo_log.record_move(Path("/a"), Path("/b"))
            return {"action": "FLAGGED for manual", "filename": entry["filename"]}

        monkeypatch.setattr(up, "upgrade_paper", flaky)
        summary = process_report(
            self._report(tmp_path, [bad, good]),
            library_root=synthetic_library, verbose=False,
        )
        assert calls["n"] == 2                       # batch continued past the raise
        actions = [r["action"] for r in summary["results"]]
        assert any(a.startswith("ERROR") for a in actions)
        assert any("FLAGGED" in a for a in actions)
        # The transaction with the recorded op was committed despite the raise.
        from processing.undo_log import UndoLog
        txs = UndoLog(log_dir=log_dir).list_transactions()
        assert len(txs) == 1 and txs[0]["operations_count"] == 1
        monkeypatch.setattr(up, "upgrade_paper", real)

    def test_all_skipped_batch_discards_empty_tx(
        self, synthetic_library, report_entry, tmp_path, monkeypatch
    ):
        import processing.upgrade_to_published as up
        log_dir = self._tmp_undolog(monkeypatch, tmp_path)
        monkeypatch.setattr(
            up, "upgrade_paper",
            lambda entry, *a, **k: {"action": "SKIP: no DOI",
                                    "filename": entry.get("filename", "?")},
        )
        process_report(
            self._report(tmp_path, [report_entry]),
            library_root=synthetic_library, verbose=False,
        )
        # Nothing recorded -> no 0-op transaction litters the log.
        from processing.undo_log import UndoLog
        assert UndoLog(log_dir=log_dir).list_transactions() == []
