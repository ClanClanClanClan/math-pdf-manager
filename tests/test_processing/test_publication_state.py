"""Tests for ``processing.publication_state``.

Covers the permanently-unpublished state machine: misses advance the
counter, hits reset it, the tip-into-permanent only fires after
``max_rechecks`` consecutive misses *and* zero historical hits, and
sidecar errors don't poison a whole batch.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from processing.identity import PaperIdentity, sidecar_path
from processing.publication_state import (
    DEFAULT_MAX_RECHECKS,
    list_permanently_unpublished,
    reset_recheck_state,
    update_publication_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4 test")
    return path


def _result(path: Path, *, published: bool = False, confidence: float = 0.0, doi: str = "") -> dict:
    """Build a fake ``scan_directory`` result dict."""
    entry = {"file": str(path), "filename": path.name, "published": published}
    if published:
        entry["match"] = {"doi": doi, "confidence": confidence}
    return entry


# ---------------------------------------------------------------------------
# Single-paper transitions
# ---------------------------------------------------------------------------

class TestSinglePaperTransitions:

    def test_miss_increments_counter(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        PaperIdentity().save(pdf)
        update_publication_state([_result(pdf, published=False)])
        ident = PaperIdentity.load(pdf)
        assert ident.recheck_count == 1
        assert not ident.permanently_unpublished

    def test_hit_does_not_increment_counter(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        PaperIdentity().save(pdf)
        update_publication_state(
            [_result(pdf, published=True, confidence=0.95, doi="10.1/x")]
        )
        ident = PaperIdentity.load(pdf)
        assert ident.recheck_count == 0
        assert ident.publication_checks[-1]["hit"] is True

    def test_low_confidence_hit_treated_as_miss(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        PaperIdentity().save(pdf)
        update_publication_state(
            [_result(pdf, published=True, confidence=0.50, doi="10.1/x")]
        )
        ident = PaperIdentity.load(pdf)
        # Counter advances because confidence below default threshold (0.75)
        assert ident.recheck_count == 1
        assert ident.publication_checks[-1]["hit"] is False

    def test_three_misses_with_no_history_tips_permanent(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        PaperIdentity().save(pdf)
        for _ in range(DEFAULT_MAX_RECHECKS):
            update_publication_state([_result(pdf, published=False)])
        ident = PaperIdentity.load(pdf)
        assert ident.permanently_unpublished
        assert ident.recheck_count == DEFAULT_MAX_RECHECKS

    def test_summary_records_newly_permanent(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        PaperIdentity().save(pdf)
        # First two misses: not yet permanent
        for _ in range(DEFAULT_MAX_RECHECKS - 1):
            s = update_publication_state([_result(pdf, published=False)])
            assert s.newly_permanent == []
        # Third miss: tips
        s = update_publication_state([_result(pdf, published=False)])
        assert s.newly_permanent == [str(pdf)]

    def test_hit_after_misses_resets_counter(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        PaperIdentity().save(pdf)
        # 2 misses
        update_publication_state([_result(pdf, published=False)])
        update_publication_state([_result(pdf, published=False)])
        # then a hit
        update_publication_state(
            [_result(pdf, published=True, confidence=0.95, doi="10.1/x")]
        )
        # then more misses — must NOT tip permanent because a hit lives
        # in history
        for _ in range(DEFAULT_MAX_RECHECKS + 1):
            update_publication_state([_result(pdf, published=False)])
        ident = PaperIdentity.load(pdf)
        assert not ident.permanently_unpublished, \
            "a confirmed hit should immunise the paper from auto-give-up"

    def test_hit_recovers_from_previously_permanent(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity(permanently_unpublished=True, recheck_count=10)
        ident.save(pdf)
        s = update_publication_state(
            [_result(pdf, published=True, confidence=0.95, doi="10.1/x")]
        )
        ident2 = PaperIdentity.load(pdf)
        assert not ident2.permanently_unpublished
        assert ident2.recheck_count == 0
        # Hit reported even though sidecar said skip
        assert len(s.hits) == 1


# ---------------------------------------------------------------------------
# Skipping permanently-unpublished papers
# ---------------------------------------------------------------------------

class TestSkipping:

    def test_permanent_paper_skipped_on_miss(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity(permanently_unpublished=True)
        ident.save(pdf)
        s = update_publication_state([_result(pdf, published=False)])
        assert s.skipped == [str(pdf)]
        assert s.checked == []

    def test_budget_exhausted_paper_skipped_on_miss(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity(recheck_count=DEFAULT_MAX_RECHECKS)
        ident.save(pdf)
        s = update_publication_state([_result(pdf, published=False)])
        assert s.skipped == [str(pdf)]


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------

class TestRobustness:

    def test_missing_sidecar_creates_one_on_first_check(self, tmp_path):
        # The state-machine doesn't require a pre-existing sidecar;
        # the first check creates one with recheck_count=1.
        pdf = _pdf(tmp_path / "p.pdf")
        assert not sidecar_path(pdf).exists()
        update_publication_state([_result(pdf, published=False)])
        assert sidecar_path(pdf).exists()
        assert PaperIdentity.load(pdf).recheck_count == 1

    def test_empty_results_returns_empty_summary(self):
        s = update_publication_state([])
        assert s.to_dict() == {
            "checked": [], "hits": [], "skipped": [],
            "newly_permanent": [], "errors": [],
        }

    def test_result_without_file_is_skipped(self, tmp_path):
        s = update_publication_state([{"file": "", "published": False}])
        assert s.checked == []

    def test_one_bad_entry_doesnt_block_others(self, tmp_path):
        good = _pdf(tmp_path / "good.pdf")
        PaperIdentity().save(good)
        bad_path = tmp_path / "subdir" / "missing.pdf"  # never created

        s = update_publication_state([
            _result(bad_path, published=False),  # parent dir doesn't exist
            _result(good, published=False),
        ])
        # good entry is processed; bad entry recorded too (sidecar is
        # written to disk even without the PDF — that's fine).
        assert str(good) in s.checked


# ---------------------------------------------------------------------------
# Library-wide listing
# ---------------------------------------------------------------------------

class TestListPermanent:

    def test_finds_permanent_papers(self, tmp_path):
        a = _pdf(tmp_path / "a.pdf")
        b = _pdf(tmp_path / "b.pdf")
        c = _pdf(tmp_path / "c.pdf")
        PaperIdentity(permanently_unpublished=True).save(a)
        PaperIdentity().save(b)
        PaperIdentity(permanently_unpublished=True).save(c)
        out = list_permanently_unpublished(tmp_path)
        assert sorted(p.name for p in out) == ["a.pdf", "c.pdf"]

    def test_skips_trash(self, tmp_path):
        live = _pdf(tmp_path / "live.pdf")
        trashed = _pdf(tmp_path / ".trash" / "old.pdf")
        PaperIdentity(permanently_unpublished=True).save(live)
        PaperIdentity(permanently_unpublished=True).save(trashed)
        out = list_permanently_unpublished(tmp_path)
        assert [p.name for p in out] == ["live.pdf"]

    def test_missing_library_root_returns_empty(self, tmp_path):
        assert list_permanently_unpublished(tmp_path / "nope") == []


class TestListBorderlineMatches:

    def test_finds_borderline_hit(self, tmp_path):
        from processing.publication_state import list_borderline_matches
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity()
        # One borderline hit recorded
        ident.record_publication_check(
            hit=True, source="crossref", confidence=0.85,
            details={"doi": "10.1/borderline"},
        )
        ident.save(pdf)
        out = list_borderline_matches(tmp_path)
        assert len(out) == 1
        assert out[0]["confidence"] == 0.85
        assert out[0]["doi"] == "10.1/borderline"

    def test_high_confidence_hit_not_borderline(self, tmp_path):
        from processing.publication_state import list_borderline_matches
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity()
        ident.record_publication_check(
            hit=True, source="crossref", confidence=0.99,
        )
        ident.save(pdf)
        assert list_borderline_matches(tmp_path) == []

    def test_miss_only_history_not_borderline(self, tmp_path):
        from processing.publication_state import list_borderline_matches
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity()
        ident.record_publication_check(hit=False, source="crossref")
        ident.save(pdf)
        assert list_borderline_matches(tmp_path) == []

    def test_most_recent_hit_wins(self, tmp_path):
        """If the paper had a strong hit later, it's not borderline anymore."""
        from processing.publication_state import list_borderline_matches
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity()
        ident.record_publication_check(hit=True, source="crossref", confidence=0.85)
        ident.record_publication_check(hit=True, source="crossref", confidence=0.97)
        ident.save(pdf)
        assert list_borderline_matches(tmp_path) == []

    def test_custom_band(self, tmp_path):
        from processing.publication_state import list_borderline_matches
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity()
        ident.record_publication_check(hit=True, source="crossref", confidence=0.60)
        ident.save(pdf)
        # Default band [0.75, 0.95) excludes 0.60
        assert list_borderline_matches(tmp_path) == []
        # Widen the band -> includes it
        assert len(list_borderline_matches(tmp_path, low=0.50, high=0.95)) == 1


class TestResetRecheckState:

    def test_clears_flag_and_counter(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        ident = PaperIdentity(permanently_unpublished=True, recheck_count=5)
        ident.save(pdf)
        out = reset_recheck_state(pdf)
        assert out is not None
        assert not out.permanently_unpublished
        assert out.recheck_count == 0
        # Persisted
        assert not PaperIdentity.load(pdf).permanently_unpublished

    def test_no_sidecar_returns_none(self, tmp_path):
        pdf = _pdf(tmp_path / "p.pdf")
        assert reset_recheck_state(pdf) is None


# ---------------------------------------------------------------------------
# Year-based ingest routing — Phase 2 organization rule
# ---------------------------------------------------------------------------

class TestAgeBasedRouting:

    def test_old_preprint_routes_to_unpublished(self, tmp_path):
        from organization.system import OrganizationSystem
        org = OrganizationSystem(tmp_path)
        # 12+ years old, no DOI/journal — would normally route to
        # working; age rule sends it to unpublished.
        from datetime import datetime
        old_year = datetime.now().year - 12
        status = org.router.determine_publication_status({"year": old_year})
        assert status == "unpublished"

    def test_recent_preprint_stays_working(self, tmp_path):
        from organization.system import OrganizationSystem
        org = OrganizationSystem(tmp_path)
        from datetime import datetime
        recent = datetime.now().year - 1
        status = org.router.determine_publication_status({"year": recent})
        assert status == "working"

    def test_unparseable_year_falls_through(self, tmp_path):
        from organization.system import OrganizationSystem
        org = OrganizationSystem(tmp_path)
        status = org.router.determine_publication_status({"year": "n/a"})
        assert status == "working"

    def test_published_doi_always_wins_over_age(self, tmp_path):
        from organization.system import OrganizationSystem
        org = OrganizationSystem(tmp_path)
        from datetime import datetime
        old_year = datetime.now().year - 20
        status = org.router.determine_publication_status({
            "year": old_year,
            "doi": "10.1007/s12345-024-0001-x",  # real publisher DOI
        })
        assert status == "published"

    def test_three_digit_year_does_not_trigger_unpublished(self, tmp_path):
        """Defensive: "202" (3 digits) must not be read as the year 202 CE
        and route the paper to Unpublished as 1800-years-old."""
        from organization.system import OrganizationSystem
        org = OrganizationSystem(tmp_path)
        assert org.router.determine_publication_status({"year": "202"}) == "working"
        assert org.router.determine_publication_status({"year": "20"}) == "working"
        # Pure-int 202 also rejected by the sanity gate (1000-9999)
        assert org.router.determine_publication_status({"year": 202}) == "working"

    def test_iso_date_string_uses_first_four_digits(self, tmp_path):
        from organization.system import OrganizationSystem
        org = OrganizationSystem(tmp_path)
        from datetime import datetime
        recent = f"{datetime.now().year - 1}-05-13"
        old = f"{datetime.now().year - 12}-05-13"
        assert org.router.determine_publication_status({"year": recent}) == "working"
        assert org.router.determine_publication_status({"year": old}) == "unpublished"

    def test_garbage_year_strings_fall_through(self, tmp_path):
        from organization.system import OrganizationSystem
        org = OrganizationSystem(tmp_path)
        for v in ("n.d.", "forthcoming", "tba", "", "  ", "year=2024"):
            assert org.router.determine_publication_status({"year": v}) == "working", \
                f"unexpected route for {v!r}"
