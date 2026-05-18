"""Tests for ``maintenance.weekly_report.auto_apply_safe_transitions``.

Phase 3 promises: the Monday plist now *acts* on safe findings,
not just reports them.  These tests pin down what "safe" means:

* Single-author Crossref hits at confidence >= 0.95 are auto-upgraded.
* Multi-author or low-confidence hits are NOT auto-applied
  (they land in ``skipped_borderline`` for the Attention Queue).
* Aged working papers (>5y) are only auto-moved to Unpublished when
  their sidecar already says ``permanently_unpublished=True``.
* A bad upgrade is recorded but doesn't poison the whole batch.
* The integration point (``check_publications`` calling
  ``update_publication_state``) actually advances the state machine.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from maintenance.weekly_report import (
    SAFE_UPGRADE_CONFIDENCE,
    auto_apply_safe_transitions,
    run_maintenance,
)
from processing.identity import PaperIdentity, sidecar_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def lib(tmp_path):
    """Synthetic library with the folders weekly_report expects."""
    for f in [
        "01 - Published papers",
        "02 - Unpublished papers",
        "03 - Working papers",
        "04 - Papers to be downloaded",
        "12 - To be sorted",
    ]:
        (tmp_path / f).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4 test")
    return path


def _hit(
    path: Path,
    *,
    confidence: float,
    authors: int,
    cr_author_count: int | None = None,
) -> dict:
    """Build a publication_checker-shaped 'published' result.

    ``authors`` controls the *parsed_authors* list length (from
    filename); ``cr_author_count`` controls the *Crossref* author
    count.  The auto-upgrade selector now requires BOTH to be 1.
    """
    if cr_author_count is None:
        cr_author_count = authors
    return {
        "file": str(path),
        "filename": path.name,
        "parsed_title": "Some Title",
        "parsed_authors": ["LastName" + str(i) for i in range(authors)],
        "published": True,
        "match": {
            "doi": "10.1/x",
            "confidence": confidence,
            "journal": "Test Journal",
            "year": 2024,
            "author_count": cr_author_count,
        },
    }


def _miss(path: Path) -> dict:
    return {
        "file": str(path),
        "filename": path.name,
        "parsed_title": "Some Title",
        "parsed_authors": ["LastName1"],
        "published": False,
    }


# ---------------------------------------------------------------------------
# auto_apply_safe_transitions — selection rules
# ---------------------------------------------------------------------------

class TestSafeUpgradeSelection:

    def test_single_author_high_confidence_is_safe(self, lib):
        pdf = _make_pdf(lib / "02 - Unpublished papers" / "p.pdf")
        results = {"publications": {"unpublished": [_hit(pdf, confidence=0.97, authors=1)],
                                    "working": []}}
        # Patch upgrade_paper so we observe selection without doing
        # network calls.
        with patch("processing.upgrade_to_published.upgrade_paper") as up:
            up.return_value = {"success": True}
            summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["upgraded"] == [str(pdf)]
        up.assert_called_once()

    def test_multi_author_blocked_even_at_high_confidence(self, lib):
        pdf = _make_pdf(lib / "02 - Unpublished papers" / "p.pdf")
        results = {"publications": {"unpublished": [_hit(pdf, confidence=0.99, authors=3)],
                                    "working": []}}
        with patch("processing.upgrade_to_published.upgrade_paper") as up:
            summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["upgraded"] == []
        assert any(b["file"] == str(pdf) for b in summary["skipped_borderline"])
        up.assert_not_called()

    def test_low_confidence_single_author_blocked(self, lib):
        pdf = _make_pdf(lib / "02 - Unpublished papers" / "p.pdf")
        results = {"publications": {"unpublished": [_hit(pdf, confidence=0.85, authors=1)],
                                    "working": []}}
        with patch("processing.upgrade_to_published.upgrade_paper") as up:
            summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["upgraded"] == []
        up.assert_not_called()

    def test_crossref_says_multi_author_blocks_even_if_filename_single(self, lib):
        """A multi-author paper filed with only the first author in the
        filename used to slip past safe-upgrade.  Now blocked by the
        Crossref author_count check."""
        pdf = _make_pdf(lib / "02 - Unpublished papers" / "p.pdf")
        results = {"publications": {"unpublished": [
            _hit(pdf, confidence=0.99, authors=1, cr_author_count=5),
        ], "working": []}}
        with patch("processing.upgrade_to_published.upgrade_paper") as up:
            summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["upgraded"] == []
        up.assert_not_called()

    def test_legacy_match_without_author_count_still_safe_when_single(self, lib):
        """Older cached match dicts have no ``author_count`` key.  Falling
        back to ``1`` is the safe-by-default behaviour: callers always
        also pass the parsed-author check so we're not blindly
        upgrading."""
        pdf = _make_pdf(lib / "02 - Unpublished papers" / "p.pdf")
        entry = _hit(pdf, confidence=0.99, authors=1)
        del entry["match"]["author_count"]
        results = {"publications": {"unpublished": [entry], "working": []}}
        with patch("processing.upgrade_to_published.upgrade_paper") as up:
            up.return_value = {"success": True}
            summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["upgraded"] == [str(pdf)]

    def test_exact_threshold_is_safe(self, lib):
        pdf = _make_pdf(lib / "02 - Unpublished papers" / "p.pdf")
        results = {"publications": {"unpublished": [
            _hit(pdf, confidence=SAFE_UPGRADE_CONFIDENCE, authors=1)
        ], "working": []}}
        with patch("processing.upgrade_to_published.upgrade_paper") as up:
            up.return_value = {"success": True}
            summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["upgraded"] == [str(pdf)]

    def test_upgrade_failure_recorded_but_batch_continues(self, lib):
        good = _make_pdf(lib / "02 - Unpublished papers" / "good.pdf")
        bad = _make_pdf(lib / "02 - Unpublished papers" / "bad.pdf")
        results = {"publications": {"unpublished": [
            _hit(good, confidence=0.97, authors=1),
            _hit(bad, confidence=0.97, authors=1),
        ], "working": []}}
        def fake_upgrade(entry, root, *, dry_run=False):
            return {"success": True} if "good" in entry["file"] else {"success": False, "error": "network"}
        with patch("processing.upgrade_to_published.upgrade_paper", side_effect=fake_upgrade):
            summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["upgraded"] == [str(good)]
        assert any("bad" in b["file"] and "network" in b["reason"]
                   for b in summary["skipped_borderline"])

    def test_dry_run_does_not_call_upgrade(self, lib):
        pdf = _make_pdf(lib / "p.pdf")
        results = {"publications": {"unpublished": [_hit(pdf, confidence=0.99, authors=1)],
                                    "working": []}}
        with patch("processing.upgrade_to_published.upgrade_paper") as up:
            summary = auto_apply_safe_transitions(results, lib, dry_run=True)
        up.assert_not_called()
        assert any("WOULD" in u for u in summary["upgraded"])


class TestSafeAgingSelection:

    def test_aged_with_permanent_flag_is_moved(self, lib):
        # Put a working PDF and mark its sidecar permanently_unpublished.
        pdf = _make_pdf(lib / "03 - Working papers" / "S" / "2018" / "Smith - x.pdf")
        PaperIdentity(permanently_unpublished=True).save(pdf)
        # Build aging candidate matching aging_checker's shape.
        dest = lib / "02 - Unpublished papers" / "S" / pdf.name
        results = {"publications": {"unpublished": [], "working": []},
                   "aging": [{
                       "path": str(pdf),
                       "filename": pdf.name,
                       "year": 2018,
                       "age": 8,
                       "first_author_alpha": "S",
                       "destination": str(dest),
                       "already_exists": False,
                   }]}
        summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert pdf.name in summary["aged_moved"]
        assert dest.exists()
        assert not pdf.exists()
        # Sidecar travelled along (Phase 0 contract)
        assert sidecar_path(dest).exists()

    def test_aged_without_permanent_flag_is_not_moved(self, lib):
        pdf = _make_pdf(lib / "03 - Working papers" / "S" / "2018" / "Smith - x.pdf")
        PaperIdentity().save(pdf)  # no permanent flag
        dest = lib / "02 - Unpublished papers" / "S" / pdf.name
        results = {"publications": {"unpublished": [], "working": []},
                   "aging": [{
                       "path": str(pdf), "filename": pdf.name,
                       "destination": str(dest), "already_exists": False,
                   }]}
        summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["aged_moved"] == []
        assert pdf.exists()
        assert not dest.exists()

    def test_aged_paper_without_sidecar_is_not_moved(self, lib):
        # No sidecar at all -> we haven't checked Crossref, so we
        # don't dare auto-move yet.
        pdf = _make_pdf(lib / "03 - Working papers" / "S" / "2018" / "x.pdf")
        results = {"publications": {"unpublished": [], "working": []},
                   "aging": [{
                       "path": str(pdf), "filename": pdf.name,
                       "destination": str(lib / "02 - Unpublished papers" / pdf.name),
                       "already_exists": False,
                   }]}
        summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert summary["aged_moved"] == []


class TestEndToEndIntegration:

    def test_check_publications_advances_state_machine(self, tmp_path):
        """The Phase 2 state machine must actually run during weekly check."""
        from maintenance.weekly_report import check_publications
        # Build a tiny library with one paper in 02
        lib = tmp_path / "lib"
        unpub = lib / "02 - Unpublished papers"
        unpub.mkdir(parents=True)
        pdf = _make_pdf(unpub / "Smith, J. - Paper.pdf")
        PaperIdentity().save(pdf)

        # Patch scan_directory so we don't hit Crossref; return a miss.
        with patch("processing.publication_checker.scan_directory",
                   return_value=[_miss(pdf)]):
            results = check_publications(lib, verbose=False)

        # Sidecar should now have recheck_count == 1
        ident = PaperIdentity.load(pdf)
        assert ident.recheck_count == 1
        # And the results dict carries a (likely empty) newly_permanent list
        assert "newly_permanent" in results

    def test_run_maintenance_with_auto_apply_threaded_through(self, lib):
        """Smoke test: --auto-apply-safe makes it from CLI into results."""
        # Empty library -> nothing to do, but we want to make sure the
        # flag plumbing works without exploding.
        results = run_maintenance(
            lib,
            skip={"publications", "aging", "duplicates"},
            verbose=False,
            auto_apply_safe=True,
        )
        assert "auto_applied" in results
        # Empty inputs -> empty outputs across the board.
        for k in ("upgraded", "aged_moved", "skipped_borderline", "errors"):
            assert results["auto_applied"][k] == []
