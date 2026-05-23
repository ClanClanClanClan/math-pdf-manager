"""Tests for ``processing.topic_router``.

The topic router classifies a filed PDF and hardlinks it into matching
``07x - …`` folders.  Hardlinks save local storage on the user's
28k-paper library; copy is the fallback for cross-device.

Coverage:
* find_topic_folder finds the right folder regardless of suffix.
* classify_and_link respects ``only_codes`` (user's explicit selection).
* Sidecar's ``copy_locations`` and ``topic_codes`` grow with each link.
* Hardlinks are real (inode-shared) on POSIX.
* Collisions (existing destination) abort that topic but don't crash.
* dry_run touches no files.
* unlink_topic removes a link and updates the sidecar.
* Undo via the recorded transaction deletes the hardlinks cleanly.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from processing.identity import PaperIdentity, sidecar_path
from processing.topic_router import (
    DEFAULT_AUTO_THRESHOLD,
    DEFAULT_SUGGEST_THRESHOLD,
    classify_and_link,
    find_topic_folder,
    unlink_topic,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4 fake")
    return path


@pytest.fixture
def library_with_topics(tmp_path):
    """Build a synth library with the user's actual 07x topic folders."""
    for folder in [
        "01 - Published papers",
        "02 - Unpublished papers",
        "03 - Working papers",
        "07a - BSDEs",
        "07b - 2BSDEs",
        "07c - Stochastic control",
        "07f - Non-commutative",
    ]:
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# find_topic_folder
# ---------------------------------------------------------------------------

class TestFindTopicFolder:

    def test_finds_existing(self, library_with_topics):
        out = find_topic_folder(library_with_topics, "07a")
        assert out is not None
        assert out.name == "07a - BSDEs"

    def test_case_insensitive(self, library_with_topics):
        assert find_topic_folder(library_with_topics, "07A").name == "07a - BSDEs"

    def test_missing_returns_none(self, library_with_topics):
        assert find_topic_folder(library_with_topics, "07z") is None

    def test_partial_code_does_not_match(self, library_with_topics):
        """``07`` shouldn't match ``07a - BSDEs`` -- requires trailing space."""
        assert find_topic_folder(library_with_topics, "07") is None

    def test_missing_library_returns_none(self, tmp_path):
        assert find_topic_folder(tmp_path / "nope", "07a") is None


# ---------------------------------------------------------------------------
# classify_and_link
# ---------------------------------------------------------------------------

class TestClassifyAndLink:

    def test_links_when_codes_explicit(self, library_with_topics):
        """``only_codes`` overrides the auto-threshold; user picked these."""
        pdf = _make_pdf(library_with_topics / "02 - Unpublished papers" / "Smith - p.pdf")
        PaperIdentity().save(pdf)
        result = classify_and_link(
            pdf, library_with_topics,
            title="Backward stochastic differential equations",
            only_codes=["07a"],
        )
        # Even if the classifier scores below auto_threshold, the
        # user's explicit selection wins.
        assert len(result.linked) == 1
        linked_path = Path(result.linked[0])
        assert linked_path.exists()
        assert linked_path.parent.name == "07a - BSDEs"

    def test_auto_threshold_filters_low_scores(self, library_with_topics):
        """Without ``only_codes``, low-score suggestions aren't linked."""
        pdf = _make_pdf(library_with_topics / "02 - Unpublished papers" / "p.pdf")
        PaperIdentity().save(pdf)
        # Title with no topic-specific keywords -> no auto-link
        result = classify_and_link(
            pdf, library_with_topics,
            title="Some generic title with no specific topic words",
        )
        assert result.linked == []

    def test_only_codes_restricts_even_with_many_suggestions(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "p.pdf")
        PaperIdentity().save(pdf)
        result = classify_and_link(
            pdf, library_with_topics,
            title="BSDE stochastic control problem",
            only_codes=["07a"],  # only one even though 07c might also match
        )
        for linked in result.linked:
            assert Path(linked).parent.name == "07a - BSDEs"

    def test_missing_topic_folder_skipped(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "p.pdf")
        PaperIdentity().save(pdf)
        # 07z doesn't exist in our fixture
        result = classify_and_link(
            pdf, library_with_topics,
            title="anything",
            only_codes=["07z"],
        )
        assert result.linked == []
        assert any("07z" in s for s in result.skipped)

    def test_destination_collision_skipped(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "Smith - p.pdf")
        PaperIdentity().save(pdf)
        # Pre-create a colliding file
        target_folder = library_with_topics / "07a - BSDEs"
        (target_folder / "Smith - p.pdf").write_bytes(b"%PDF different")
        result = classify_and_link(
            pdf, library_with_topics,
            title="BSDE",
            only_codes=["07a"],
        )
        assert result.linked == []
        assert any("exists" in s for s in result.skipped)

    def test_dry_run_creates_nothing(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "p.pdf")
        PaperIdentity().save(pdf)
        result = classify_and_link(
            pdf, library_with_topics,
            title="BSDE",
            only_codes=["07a"],
            dry_run=True,
        )
        # "WOULD link" entry appears but no file created
        assert any("WOULD" in entry for entry in result.linked)
        assert not (library_with_topics / "07a - BSDEs" / "p.pdf").exists()

    def test_sidecar_updated_with_new_locations(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "02 - Unpublished papers" / "p.pdf")
        PaperIdentity().save(pdf)
        result = classify_and_link(
            pdf, library_with_topics,
            title="BSDE",
            only_codes=["07a"],
        )
        assert len(result.linked) == 1
        ident = PaperIdentity.load(pdf)
        assert str(pdf) in ident.copy_locations
        assert result.linked[0] in ident.copy_locations
        assert "07a" in ident.topic_codes

    def test_hardlink_shares_inode_when_same_volume(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "p.pdf")
        PaperIdentity().save(pdf)
        result = classify_and_link(
            pdf, library_with_topics,
            title="BSDE",
            only_codes=["07a"],
        )
        linked = Path(result.linked[0])
        # On a single-volume tmp_path both paths should resolve to the
        # same inode.  If the fallback to ``shutil.copy2`` fired we'd
        # have two distinct inodes -- in that case the test is just
        # a no-op (env-dependent).
        if linked.stat().st_dev == pdf.stat().st_dev:
            assert linked.stat().st_ino == pdf.stat().st_ino

    def test_missing_canonical_pdf_records_error(self, library_with_topics):
        ghost = library_with_topics / "nonexistent.pdf"
        result = classify_and_link(
            ghost, library_with_topics,
            title="BSDE",
            only_codes=["07a"],
        )
        assert any("missing" in e for e in result.errors)


# ---------------------------------------------------------------------------
# unlink_topic
# ---------------------------------------------------------------------------

class TestUnlinkTopic:

    def test_removes_link_and_updates_sidecar(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "p.pdf")
        PaperIdentity().save(pdf)
        classify_and_link(
            pdf, library_with_topics,
            title="BSDE",
            only_codes=["07a"],
        )
        topic_copy = library_with_topics / "07a - BSDEs" / "p.pdf"
        assert topic_copy.exists()

        assert unlink_topic(pdf, library_with_topics, "07a") is True
        assert not topic_copy.exists()
        ident = PaperIdentity.load(pdf)
        assert "07a" not in ident.topic_codes
        assert str(topic_copy) not in ident.copy_locations

    def test_unlink_missing_returns_false(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "p.pdf")
        assert unlink_topic(pdf, library_with_topics, "07a") is False

    def test_unlink_missing_topic_folder(self, library_with_topics):
        pdf = _make_pdf(library_with_topics / "p.pdf")
        assert unlink_topic(pdf, library_with_topics, "07z") is False


# ---------------------------------------------------------------------------
# Undo integration
# ---------------------------------------------------------------------------

class TestUndoIntegration:

    def test_undo_also_cleans_sidecar_copy_locations(self, library_with_topics):
        """Audit-5 #1: after undoing a topic-link transaction, the
        canonical's sidecar must no longer advertise the dead link."""
        from processing.undo_log import UndoLog
        pdf = _make_pdf(library_with_topics / "p.pdf")
        PaperIdentity().save(pdf)

        log = UndoLog(log_dir=library_with_topics / ".ops")
        tx_id = log.begin_transaction("link then undo")
        classify_and_link(
            pdf, library_with_topics,
            title="BSDE methods",
            only_codes=["07a"],
            undo_log=log,
        )
        log.commit()

        # Sanity: sidecar has the link
        ident = PaperIdentity.load(pdf)
        assert any("07a" in loc for loc in ident.copy_locations)
        assert "07a" in ident.topic_codes

        # Undo and re-read
        log.undo_transaction(tx_id)
        reloaded = PaperIdentity.load(pdf)
        # The dead link entry is gone; only the canonical remains.
        assert all("07a" not in loc for loc in reloaded.copy_locations)
        assert "07a" not in reloaded.topic_codes

    def test_undo_removes_hardlinks(self, library_with_topics):
        from processing.undo_log import UndoLog
        pdf = _make_pdf(library_with_topics / "p.pdf")
        PaperIdentity().save(pdf)

        log = UndoLog(log_dir=library_with_topics / ".operation_log")
        tx_id = log.begin_transaction("topic linking test")
        classify_and_link(
            pdf, library_with_topics,
            title="BSDE stochastic control",
            only_codes=["07a", "07c"],
            undo_log=log,
        )
        log.commit()

        link_a = library_with_topics / "07a - BSDEs" / "p.pdf"
        link_c = library_with_topics / "07c - Stochastic control" / "p.pdf"
        assert link_a.exists() and link_c.exists()

        results = log.undo_transaction(tx_id)
        assert not link_a.exists()
        assert not link_c.exists()
        # Canonical untouched
        assert pdf.exists()
        # Undo produced at least one DELETED COPY action per link
        deleted = sum(1 for r in results if "DELETED COPY" in r.get("action", ""))
        assert deleted >= 2
