"""Tests for ``processing.publication_topic_router`` and the
auto-topic routing wired into ``ingest_paper``.

The library has six 07x topic folders mirroring the standard
structure.  A published/upgraded paper that matches a topic should
land in that topic's subtree; otherwise the standard top-level
Published folder.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

from processing.publication_topic_router import (
    DEFAULT_TOPIC_THRESHOLD,
    TopicDecision,
    preview_destination,
    resolve_topic,
)


# ---------------------------------------------------------------------------
# resolve_topic
# ---------------------------------------------------------------------------

class TestResolveTopic:

    def test_bsde_title_routes_to_07a(self):
        d = resolve_topic("Reflected BSDEs and obstacle problems")
        assert d.topic_code == "07a"
        assert not d.is_standard

    def test_contract_theory_routes_to_07b(self):
        d = resolve_topic("A principal-agent model with moral hazard")
        assert d.topic_code == "07b"

    def test_stackelberg_routes_to_07d(self):
        d = resolve_topic("Stackelberg games in continuous time")
        assert d.topic_code == "07d"

    def test_generic_title_is_standard(self):
        d = resolve_topic("On the rate of escape of random walks")
        assert d.is_standard
        assert d.topic_code is None

    def test_empty_title_is_standard(self):
        d = resolve_topic("")
        assert d.is_standard

    def test_weak_match_below_threshold_is_standard(self):
        # A title with no primary-keyword hit should not route.
        d = resolve_topic("Some general analysis of functions")
        assert d.is_standard

    def test_subtopic_never_auto_supported(self):
        # Even a clear BSDE-numerical title only reaches the top-level
        # topic; sub-sub-topic routing is intentionally unsupported.
        d = resolve_topic("Numerical methods for BSDEs via deep learning")
        if d.topic_code:  # may or may not clear threshold
            assert d.subtopic_supported is False


class TestConfidenceBands:

    def test_confident_match_auto_files(self):
        # Strong, unambiguous BSDE signal in title + body.
        d = resolve_topic(
            "Reflected BSDEs and obstacle problems",
            "backward stochastic differential equations BSDE reflected",
        )
        assert d.auto
        assert d.topic_code == "07a"
        assert d.confidence >= 0.70

    def test_no_keyword_is_standard(self):
        # No topic keyword at all -> standard, no suggestion.
        d = resolve_topic("On the rate of escape of random walks")
        assert not d.auto
        assert not d.needs_review
        assert d.is_standard

    def test_single_specific_keyword_auto_files(self):
        # Hyper-specific terms (BSDE, Stackelberg) are confident on a
        # single hit -- they essentially never appear off-topic.
        assert resolve_topic("A remark on a BSDE example").auto
        assert resolve_topic("On Stackelberg equilibria").auto

    def test_contested_match_lands_in_review_band(self):
        # A title hitting TWO topics' primary keywords is ambiguous ->
        # the dominance penalty drops confidence into the review band,
        # so it's suggested (not auto-filed) for the user to confirm.
        d = resolve_topic("Stackelberg games and BSDEs")
        # Two strong competing topics -> not auto.
        assert not d.auto
        # The classifier still has a best guess to surface.
        if d.needs_review:
            assert d.topic_code is None
            assert d.suggested_code in ("07a", "07d")

    def test_confidence_is_a_percentage(self):
        d = resolve_topic("Principal-agent moral hazard contract design",
                          "moral hazard principal agent")
        assert 0.0 <= d.confidence <= 1.0


class TestSuggestionLifecycle:

    @pytest.fixture
    def lib_with_suggestion(self, topic_library):
        """A paper filed in standard Published with a pending 07a suggestion."""
        from processing.identity import enable_sidecar_mirror, PaperIdentity
        enable_sidecar_mirror(topic_library)
        sub = topic_library / "01 - Published papers" / "S"
        sub.mkdir(parents=True)
        pdf = sub / "Smith, J. - A study.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")
        ident = PaperIdentity()
        ident.topic_suggestion = "07a"
        ident.topic_confidence = 0.55
        ident.save(pdf)
        return topic_library, pdf

    def test_list_suggestions(self, lib_with_suggestion):
        from processing.publication_topic_router import list_topic_suggestions
        lib, pdf = lib_with_suggestion
        rows = list_topic_suggestions(lib)
        assert len(rows) == 1
        assert rows[0]["topic"] == "07a"
        assert rows[0]["confidence"] == 0.55

    def test_accept_moves_into_topic(self, lib_with_suggestion):
        from processing.publication_topic_router import accept_topic_suggestion
        from processing.identity import PaperIdentity
        lib, pdf = lib_with_suggestion
        ok, msg = accept_topic_suggestion(pdf, lib)
        assert ok, msg
        # Moved into 07a's Published/S
        moved = lib / "07a - BSDEs" / "01 - Published papers" / "S" / "Smith, J. - A study.pdf"
        assert moved.exists()
        assert not pdf.exists()
        ident = PaperIdentity.load(moved)
        assert ident.topic_suggestion == ""
        assert "07a" in ident.topic_codes

    def test_reject_clears_without_moving(self, lib_with_suggestion):
        from processing.publication_topic_router import reject_topic_suggestion
        from processing.identity import PaperIdentity
        lib, pdf = lib_with_suggestion
        assert reject_topic_suggestion(pdf) is True
        assert pdf.exists()  # not moved
        assert PaperIdentity.load(pdf).topic_suggestion == ""

    def test_accept_is_undoable(self, lib_with_suggestion):
        from processing.publication_topic_router import accept_topic_suggestion
        from processing.undo_log import UndoLog
        lib, pdf = lib_with_suggestion
        log = UndoLog(log_dir=lib / ".ops")
        tx = log.begin_transaction("accept topic")
        ok, _ = accept_topic_suggestion(pdf, lib, undo_log=log)
        assert ok
        log.commit()
        moved = lib / "07a - BSDEs" / "01 - Published papers" / "S" / "Smith, J. - A study.pdf"
        assert moved.exists()
        log.undo_transaction(tx)
        # Back where it started
        assert pdf.exists()
        assert not moved.exists()


# ---------------------------------------------------------------------------
# preview_destination
# ---------------------------------------------------------------------------

@pytest.fixture
def topic_library(tmp_path):
    """Synth library with the six topic folders + standard dirs."""
    for d in [
        "01 - Published papers",
        "02 - Unpublished papers",
        "03 - Working papers",
        "07a - BSDEs",
        "07b - Contract theory",
        "07c - Time-inconsistent stochastic control",
        "07d - Stackelberg games",
        "07e - Optimal control on networks",
        "07f - Non-commutative stochastic calculus",
    ]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


class TestPreviewDestination:

    def test_standard_destination(self, topic_library):
        dec = TopicDecision(None, "", 0.0)
        dest = preview_destination(
            topic_library, dec, "Bass, R.F. - Random walks.pdf",
        )
        rel = dest.relative_to(topic_library)
        assert str(rel).startswith("01 - Published papers/B/")

    def test_topic_destination(self, topic_library):
        dec = TopicDecision("07a", "BSDEs", 4.0)
        dest = preview_destination(
            topic_library, dec, "Smith, J. - Reflected BSDEs.pdf",
        )
        rel = dest.relative_to(topic_library)
        assert str(rel).startswith("07a - BSDEs/01 - Published papers/S/")


# ---------------------------------------------------------------------------
# ingest integration
# ---------------------------------------------------------------------------

class TestIngestAutoTopic:

    def test_bsde_paper_auto_files_into_topic(self, topic_library):
        from processing.ingest import ingest_paper
        inbox = topic_library / "_inbox"
        inbox.mkdir()
        pdf = inbox / "drop.pdf"
        _write_minimal_pdf(pdf, title="Reflected BSDEs and optimal stopping",
                           author="Smith, J.")
        result = ingest_paper(
            pdf, library_root=topic_library, status="published", dry_run=False,
        )
        assert result["success"]
        # Landed inside the 07a topic subtree
        assert "07a - BSDEs/01 - Published papers" in result["destination"]
        assert result.get("auto_topic") == "07a"

    def test_generic_paper_uses_standard_folder(self, topic_library):
        from processing.ingest import ingest_paper
        inbox = topic_library / "_inbox"
        inbox.mkdir()
        pdf = inbox / "drop.pdf"
        _write_minimal_pdf(pdf, title="On the rate of escape of random walks",
                           author="Bass, R.")
        result = ingest_paper(
            pdf, library_root=topic_library, status="published", dry_run=False,
        )
        assert result["success"]
        # Standard top-level (NOT a topic subtree)
        assert result["destination"].count(" - Published papers") == 1
        assert "07" not in Path(result["destination"]).relative_to(topic_library).parts[0]
        assert "auto_topic" not in result

    def test_explicit_topic_overrides_auto(self, topic_library):
        from processing.ingest import ingest_paper
        inbox = topic_library / "_inbox"
        inbox.mkdir()
        pdf = inbox / "drop.pdf"
        # Title says BSDE but caller pins 07b -> caller wins
        _write_minimal_pdf(pdf, title="Reflected BSDEs", author="Smith, J.")
        result = ingest_paper(
            pdf, library_root=topic_library, status="published",
            topic="07b", dry_run=False,
        )
        assert result["success"]
        assert "07b - Contract theory" in result["destination"]
        # auto_topic not set because caller pinned one
        assert "auto_topic" not in result
