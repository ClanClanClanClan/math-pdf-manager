"""Empirical batch test on a random sample of real PDFs from the user's
``12 - To be sorted/`` backlog.

Goal: catch pipeline bugs that synthetic PDFs can't surface (weird PDF
metadata, real-world author formats, encoding quirks). The test is
READ-ONLY against the live library — it COPIES the sample into /tmp and
processes the copies.

This test is opt-in via the MATHPDF_EMPIRICAL_BATCH env var so it doesn't
slow down normal CI. Set MATHPDF_EMPIRICAL_BATCH=1 (and optionally
MATHPDF_EMPIRICAL_SAMPLE=N for sample size, default 25) to run.

Pass criteria:
  - At least 50% of the sample is successfully filed (the rest are
    flagged for manual review by the quality gate, which is OK).
  - No exceptions during processing — every file gets either a success
    result or a structured failure message.
  - No two papers receive the same destination path (collision detector).
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _live_library_root() -> Optional[Path]:
    """Locate the user's real library, or None if not present."""
    from core.config_paths import get_library_root
    p = get_library_root()
    return p if p.exists() else None


pytestmark = pytest.mark.skipif(
    os.environ.get("MATHPDF_EMPIRICAL_BATCH", "0") != "1",
    reason="Set MATHPDF_EMPIRICAL_BATCH=1 to run empirical-batch tests "
           "against a real-PDF sample (read-only copy to /tmp).",
)


@pytest.fixture
def real_sample_lib(tmp_path):
    """Build a fresh synthetic library in /tmp and copy a random sample of
    real PDFs from the live ``12 - To be sorted/`` tree into the synth's
    ``12/``. Returns ``(lib_root, n_copied)``.

    NEVER modifies the live library.
    """
    live = _live_library_root()
    if live is None:
        pytest.skip("No live library found")
    staging = live / "12 - To be sorted"
    if not staging.exists() or not staging.is_dir():
        pytest.skip("No 12 - To be sorted/ in live library")

    sample_size = int(os.environ.get("MATHPDF_EMPIRICAL_SAMPLE", "25"))

    from synth_library import build_synth_library
    lib = build_synth_library(tmp_path / "lib", specs=[])

    # Random sample of real PDFs across all subfolders
    real_pdfs = list(staging.rglob("*.pdf"))
    if not real_pdfs:
        pytest.skip("No PDFs in live 12 - To be sorted/")
    random.seed(20260514)  # deterministic per-test-run sample
    chosen = random.sample(real_pdfs, min(sample_size, len(real_pdfs)))

    copied = 0
    for src in chosen:
        sub = src.parent.name
        dest_sub = lib / "12 - To be sorted" / sub
        dest_sub.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dest_sub / src.name)
            copied += 1
        except OSError:
            continue

    return lib, copied


# ---------------------------------------------------------------------------
# 1. Pipeline survives the entire sample without exceptions
# ---------------------------------------------------------------------------

def test_pipeline_survives_real_sample(real_sample_lib, caplog):
    lib, n_copied = real_sample_lib
    from processing.bulk_sort import bulk_sort

    summary = bulk_sort(lib, dry_run=True, verbose=False)
    # All real-world papers either succeed or fail gracefully — never raise.
    assert summary["processed"] == n_copied
    assert summary["processed"] == summary["filed"] + summary["failed"]


# ---------------------------------------------------------------------------
# 2. Acceptable filing rate (at least 50%)
# ---------------------------------------------------------------------------

def test_real_sample_filing_rate(real_sample_lib):
    lib, n_copied = real_sample_lib
    from processing.bulk_sort import bulk_sort

    summary = bulk_sort(lib, dry_run=True, verbose=False)
    if n_copied == 0:
        pytest.skip("empty sample")
    rate = summary["filed"] / n_copied
    assert rate >= 0.5, (
        f"Only {summary['filed']}/{n_copied} = {rate:.0%} filed. "
        f"Errors: {[r.get('error', '?')[:50] for r in summary['results'] if not r.get('ok')][:5]}"
    )


# ---------------------------------------------------------------------------
# 3. No destination-path collisions in the sample
# ---------------------------------------------------------------------------

def test_no_destination_collisions(real_sample_lib):
    lib, n_copied = real_sample_lib
    from processing.bulk_sort import bulk_sort

    summary = bulk_sort(lib, dry_run=True, verbose=False)
    destinations = [r.get("destination") for r in summary["results"] if r.get("ok")]
    # Filter out None
    destinations = [d for d in destinations if d]
    seen = set()
    collisions = []
    for d in destinations:
        if d in seen:
            collisions.append(d)
        seen.add(d)
    assert not collisions, f"Destination collisions found: {collisions[:5]}"


# ---------------------------------------------------------------------------
# 4. No canonical filename exceeds the filesystem byte limit
# ---------------------------------------------------------------------------

def test_no_overlong_canonical_names(real_sample_lib):
    lib, n_copied = real_sample_lib
    from processing.bulk_sort import bulk_sort

    summary = bulk_sort(lib, dry_run=True, verbose=False)
    too_long = []
    for r in summary["results"]:
        fn = r.get("filename") or ""
        if len(fn.encode("utf-8")) > 255:
            too_long.append((len(fn.encode("utf-8")), fn[:80]))
    assert not too_long, f"Filenames exceeding 255 bytes: {too_long[:3]}"
