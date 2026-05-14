"""End-to-end pipeline test using the synthetic library generator.

Run with:
    PYTHONPATH=src pytest tests/harness/test_pipeline_e2e.py -v

This is the "everything together" smoke test:
  1. Build a synthetic library with 12 canonical specs.
  2. Run bulk_sort on `12 - To be sorted/`.
  3. Verify every spec produces the expected outcome (ok? destination folder?
     destination letter? filename keywords?).
  4. Run weekly_report.run_maintenance and verify it doesn't crash.
  5. Run undo on every successful sort and verify the original state restores.

The test is SELF-CONTAINED: no network, no real library, no environment
state. Anyone can run it; CI can run it; future regressions will be
caught here before they reach real data.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))

from synth_library import (  # noqa: E402
    STANDARD_SPECS,
    SynthPdfSpec,
    build_synth_library,
)


# ---------------------------------------------------------------------------
# Fixture: build the library once per test module
# ---------------------------------------------------------------------------

@pytest.fixture
def synth_lib(tmp_path: Path) -> Path:
    return build_synth_library(tmp_path / "lib", STANDARD_SPECS)


# ---------------------------------------------------------------------------
# 1. Every spec produces the expected outcome
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spec", STANDARD_SPECS, ids=[s.filename for s in STANDARD_SPECS])
def test_bulk_sort_each_spec_outcome(spec: SynthPdfSpec, synth_lib: Path) -> None:
    """Each synth spec produces its expected ok/destination/filename."""
    from processing.bulk_sort import sort_one

    pdf = synth_lib / spec.subfolder / spec.filename
    assert pdf.exists(), f"setup failure: spec PDF missing at {pdf}"

    # Derive status hint from the subfolder name
    status_map = {
        "01 - Published papers": "published",
        "02 - Unpublished papers": "unpublished",
        "03 - Working papers": "working",
        "05 - Books and lecture notes": "book",
        "06 - Theses": "thesis",
    }
    sub = pdf.parent.name
    status = status_map[sub]

    result = sort_one(pdf, status, library_root=synth_lib, dry_run=True)

    # The most important assertion: does the spec's expected outcome match?
    assert result.get("ok") == spec.expect_ok, (
        f"{spec.filename}: expected ok={spec.expect_ok} but got "
        f"ok={result.get('ok')}, error={result.get('error')!r}.\n"
        f"Spec notes: {spec.notes}"
    )

    if not spec.expect_ok:
        return  # quality-gate failures don't have destination details

    canonical = result.get("filename", "")
    destination = result.get("destination", "")

    if spec.expect_destination_folder:
        assert spec.expect_destination_folder in destination, (
            f"{spec.filename}: expected destination under "
            f"{spec.expect_destination_folder!r}, got {destination!r}"
        )

    if spec.expect_destination_letter:
        # Letter appears as a path component like "/A/"
        # Books and lecture notes have no alpha subdir, so this only applies
        # when the spec sets it.
        if spec.expect_destination_folder != "05 - Books and lecture notes":
            assert f"/{spec.expect_destination_letter}/" in destination, (
                f"{spec.filename}: expected alpha-subdir "
                f"{spec.expect_destination_letter!r} in {destination!r}"
            )

    for keyword in spec.expect_filename_contains:
        assert keyword in canonical, (
            f"{spec.filename}: expected {keyword!r} in canonical {canonical!r}"
        )


# ---------------------------------------------------------------------------
# 2. The whole bulk_sort run is internally consistent
# ---------------------------------------------------------------------------

def test_bulk_sort_full_run_summary(synth_lib: Path) -> None:
    """bulk_sort run on the synthetic library produces sensible aggregate stats."""
    from processing.bulk_sort import bulk_sort

    summary = bulk_sort(synth_lib, dry_run=True)

    assert summary["processed"] == len(STANDARD_SPECS)
    # Expected number of fileable specs
    expected_filed = sum(1 for s in STANDARD_SPECS if s.expect_ok)
    expected_failed = len(STANDARD_SPECS) - expected_filed
    assert summary["filed"] == expected_filed, (
        f"expected {expected_filed} filed, got {summary['filed']}; "
        f"results: {[(r.get('source'), r.get('ok'), r.get('error', ''))[:2] for r in summary['results']]}"
    )
    assert summary["failed"] == expected_failed


# ---------------------------------------------------------------------------
# 3. Maintenance run does not crash on the synthetic library
# ---------------------------------------------------------------------------

def test_maintenance_run_against_synth(synth_lib: Path) -> None:
    from maintenance.weekly_report import count_to_be_sorted, check_aging, check_duplicates

    backlog = count_to_be_sorted(synth_lib)
    assert backlog["total"] == len(STANDARD_SPECS)

    # check_aging: synth lib has no aged papers, must return empty without crashing
    aged = check_aging(synth_lib, verbose=False)
    assert aged == []

    # check_duplicates: no duplicates either
    dupes = check_duplicates(synth_lib, verbose=False)
    assert dupes == []


# ---------------------------------------------------------------------------
# 4. End-to-end: bulk_sort writes, then undo restores the original tree
# ---------------------------------------------------------------------------

def test_bulk_sort_then_undo_restores_originals(synth_lib: Path) -> None:
    """The full round trip: actually move files, then undo, then check they're back."""
    from processing.bulk_sort import bulk_sort
    from processing.undo_log import UndoLog

    # Snapshot the source paths before
    sources_before = {p for p in (synth_lib / "12 - To be sorted").rglob("*.pdf")}
    assert len(sources_before) == len(STANDARD_SPECS)

    summary = bulk_sort(synth_lib, dry_run=False)
    tx_id = summary.get("transaction_id")
    assert tx_id, "bulk_sort should have created a transaction"

    # After the run: the "ok" sources are no longer in 12/, they're in their
    # destination folders and the original was moved to .trash/.
    sources_after = {p for p in (synth_lib / "12 - To be sorted").rglob("*.pdf")}
    # Each successfully-filed spec leaves its source in 12/ (failed quality
    # gate) OR moves it out (success). So the number remaining = failed count.
    expected_remaining = sum(1 for s in STANDARD_SPECS if not s.expect_ok)
    assert len(sources_after) == expected_remaining

    # The trash has the moved sources
    trash = synth_lib / ".trash" / "sorted_originals"
    assert trash.exists()
    trashed = {p for p in trash.rglob("*.pdf")}
    expected_trashed = sum(1 for s in STANDARD_SPECS if s.expect_ok)
    assert len(trashed) == expected_trashed

    # Now undo. After undo, everything should be back where it started.
    log = UndoLog()
    log.undo_transaction(tx_id, dry_run=False)

    sources_restored = {p for p in (synth_lib / "12 - To be sorted").rglob("*.pdf")}
    # Same count as before
    assert len(sources_restored) == len(STANDARD_SPECS)


# ---------------------------------------------------------------------------
# 5. Cockpit "canonical_override" pathway: user edits are honoured
# ---------------------------------------------------------------------------

def test_cockpit_canonical_override_honoured(synth_lib: Path) -> None:
    """When the cockpit passes canonical_override, that exact name is used.

    Regression test for the bug where the UI showed an edited filename to the
    user but the pipeline silently re-derived its own filename and filed under
    that instead.
    """
    from processing.bulk_sort import sort_one

    pdf = synth_lib / "12 - To be sorted" / "01 - Published papers" / "paper001.pdf"
    assert pdf.exists()

    user_edited_name = "Smith, J. - Custom title from user.pdf"
    result = sort_one(
        pdf, "published",
        library_root=synth_lib,
        dry_run=True,
        canonical_override=user_edited_name,
    )

    assert result["ok"] is True
    assert result["filename"] == user_edited_name, (
        f"override ignored: got {result['filename']!r} instead of {user_edited_name!r}"
    )
    assert "Smith, J. - Custom title from user.pdf" in result["destination"]


# ---------------------------------------------------------------------------
# 6. UI smoke test: cockpit imports + paper_preview works on a synth PDF
# ---------------------------------------------------------------------------

def test_ui_paper_preview_does_not_crash(synth_lib: Path) -> None:
    from ui.paper_preview import preview_pdf

    pdf = synth_lib / "12 - To be sorted" / "01 - Published papers" / "paper002.pdf"
    prev = preview_pdf(pdf)

    assert prev.error is None, f"preview returned error: {prev.error}"
    assert "Abraham" in prev.canonical_filename
    assert prev.title  # non-empty
    assert prev.authors  # non-empty
