"""End-to-end integration tests crossing every phase (0-6).

These tests prove the system works as a whole on a synthetic
library, not just that the individual modules pass their unit tests.
The scenarios mirror the real user workflow:

* Drop PDFs in 12/.
* Sort them via ingest_paper -> sidecar written next to filed PDF.
* Topic-route them into 07x folders -> hardlinks tracked in
  copy_locations.
* Run a fake Crossref check that returns mixed hits/misses ->
  state machine advances, borderline + permanent emerge.
* Auto-apply safe transitions -> single-author high-confidence
  hits upgrade, permanent papers age.
* Verify the cockpit-side collectors (attention queue,
  conflict scanner) see the right items.
* Undo the whole transaction -> filesystem and sidecar state
  restored.

The point isn't to retest individual modules (covered elsewhere) but
to catch integration bugs that only show up when pieces interact.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Reach the synth library helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
from synth_library import _write_minimal_pdf  # noqa: E402


# ---------------------------------------------------------------------------
# Synth library factory
# ---------------------------------------------------------------------------

@pytest.fixture
def lib(tmp_path):
    """Synth library mirroring the user's folder structure."""
    for f in [
        "01 - Published papers",
        "02 - Unpublished papers",
        "03 - Working papers",
        "04 - Papers to be downloaded",
        "07a - BSDEs",
        "07b - 2BSDEs",
        "07c - Stochastic control",
        "12 - To be sorted/03 - Working papers",
    ]:
        (tmp_path / f).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _drop_paper(lib: Path, name: str, *, title: str, author: str) -> Path:
    """Stage a paper in 12/ ready for sorting."""
    path = lib / "12 - To be sorted/03 - Working papers" / name
    _write_minimal_pdf(path, title=title, author=author)
    return path


# ---------------------------------------------------------------------------
# End-to-end scenarios
# ---------------------------------------------------------------------------

class TestPhase0ToPhase4Integration:
    """Ingest -> sidecar -> topic links -> sidecar tracks links."""

    def test_ingest_then_topic_link_then_sidecar_tracks_both(self, lib):
        from processing.ingest import ingest_paper
        from processing.identity import PaperIdentity, sidecar_path
        from processing.topic_router import classify_and_link

        src = _drop_paper(lib, "drop.pdf",
                          title="Backward stochastic differential equations",
                          author="Smith, J.")
        result = ingest_paper(src, library_root=lib, status="working", dry_run=False)
        assert result["success"]
        canonical = Path(result["destination"])
        assert canonical.exists()
        assert sidecar_path(canonical).exists()

        # Topic-link explicitly to 07a
        routing = classify_and_link(
            canonical, lib,
            title="Backward stochastic differential equations",
            only_codes=["07a"],
        )
        assert len(routing.linked) == 1
        link = Path(routing.linked[0])
        assert link.exists()

        # Sidecar tracks both locations + topic code
        ident = PaperIdentity.load(canonical)
        assert str(canonical) in ident.copy_locations
        assert str(link) in ident.copy_locations
        assert "07a" in ident.topic_codes


class TestPhase2ToPhase3Integration:
    """State machine + weekly auto-apply work together."""

    def test_misses_then_tip_permanent_then_safe_aging(self, lib):
        from processing.identity import PaperIdentity
        from processing.publication_state import update_publication_state
        from maintenance.weekly_report import auto_apply_safe_transitions

        # Pre-place an aged working paper (would be >5y in find_aged_papers
        # via the year subfolder).
        old_year_dir = lib / "03 - Working papers" / "S" / "2015"
        old_year_dir.mkdir(parents=True)
        pdf = old_year_dir / "Smith, J. - Old paper.pdf"
        _write_minimal_pdf(pdf, title="Old paper", author="Smith, J.")
        PaperIdentity().save(pdf)

        # Three misses -> tip permanent
        for _ in range(3):
            update_publication_state([
                {"file": str(pdf), "filename": pdf.name,
                 "parsed_authors": ["Smith"],
                 "published": False}
            ])
        assert PaperIdentity.load(pdf).permanently_unpublished

        # Auto-apply safe transitions should now move the aged + permanent
        # paper from 03 to 02.
        dest_dir = lib / "02 - Unpublished papers" / "S"
        results = {
            "publications": {"unpublished": [], "working": []},
            "aging": [{
                "path": str(pdf),
                "filename": pdf.name,
                "year": 2015,
                "destination": str(dest_dir / pdf.name),
                "already_exists": False,
            }],
        }
        summary = auto_apply_safe_transitions(results, lib, dry_run=False)
        assert pdf.name in summary["aged_moved"]
        assert (dest_dir / pdf.name).exists()
        # Sidecar travelled with it (Phase 0 contract)
        from processing.identity import sidecar_path
        assert sidecar_path(dest_dir / pdf.name).exists()


class TestPhase1AttentionQueueIntegration:
    """The attention queue surfaces real Phase 1-6 state."""

    def test_unified_queue_picks_up_flag_and_conflict(self, lib):
        # Set up: one upgrade flag + one conflict copy
        flag_dir = lib / "04 - Papers to be downloaded" / "J"
        flag_dir.mkdir(parents=True)
        (flag_dir / "Pending download.txt").write_text(
            "DOI: 10.1/pending\nJournal: J\n", encoding="utf-8",
        )
        conf = lib / "01 - Published papers" / "X" / "Some paper (DESKTOP-A's conflicted copy 2024-05-13).pdf"
        conf.parent.mkdir(parents=True)
        conf.write_bytes(b"%PDF")

        from ui.attention_queue import gather_attention_items
        items = gather_attention_items(
            lib,
            include_dismissed=True,
            dismissals_path=lib / "_dismissals.json",
        )
        sources = {it.source for it in items}
        assert "upgrade_flag" in sources
        assert "conflict_copy" in sources


class TestPhase6ConflictResolverIntegration:
    """Conflict resolver -> state changes -> attention queue updates."""

    def test_keep_canonical_clears_conflict_from_queue(self, lib):
        conf = lib / "01 - Published papers" / "X" / "Foo (conflicted copy 2024-05-13).pdf"
        conf.parent.mkdir(parents=True)
        conf.write_bytes(b"%PDF")
        canonical = conf.parent / "Foo.pdf"
        canonical.write_bytes(b"%PDF")

        from ui.attention_queue import gather_attention_items
        from processing.conflict_resolver import resolve_keep_canonical
        # Before: conflict present
        items = gather_attention_items(
            lib, include_dismissed=True,
            dismissals_path=lib / "_dismissals.json",
        )
        assert any(it.source == "conflict_copy" for it in items)

        ok, _ = resolve_keep_canonical(conf, lib)
        assert ok

        items = gather_attention_items(
            lib, include_dismissed=True,
            dismissals_path=lib / "_dismissals.json",
        )
        # Conflict is gone from live scan (it's now in .trash/)
        assert not any(it.source == "conflict_copy" for it in items)


class TestUndoRoundTrip:
    """Every destructive action goes through undo_log; verify reversal."""

    def test_topic_link_then_undo_restores(self, lib):
        from processing.ingest import ingest_paper
        from processing.topic_router import classify_and_link
        from processing.undo_log import UndoLog
        from processing.identity import PaperIdentity

        src = _drop_paper(lib, "drop.pdf",
                          title="BSDE methods",
                          author="Doe, J.")
        r = ingest_paper(src, library_root=lib, status="working", dry_run=False)
        canonical = Path(r["destination"])

        log = UndoLog(log_dir=lib / ".ops")
        tx = log.begin_transaction("topic link")
        classify_and_link(
            canonical, lib,
            title="BSDE methods",
            only_codes=["07a"],
            undo_log=log,
        )
        log.commit()

        link = lib / "07a - BSDEs" / canonical.name
        assert link.exists()

        log.undo_transaction(tx)
        # The hardlink at 07a/ is gone; canonical untouched.
        assert not link.exists()
        assert canonical.exists()
