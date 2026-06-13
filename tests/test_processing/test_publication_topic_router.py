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
