#!/usr/bin/env python3
"""Move papers between status folders when publication status changes.

Takes a publication checker report and moves confirmed-published papers
from their current location (02 - Unpublished, 03 - Working, 04 - Not
fully published) to 01 - Published papers.

Usage::

    # Preview what would be moved (dry run)
    python -m processing.paper_transition report.json --dry-run

    # Actually move the papers
    python -m processing.paper_transition report.json

    # Only move papers above 90% confidence
    python -m processing.paper_transition report.json --min-confidence 0.90

    # Move and re-download journal versions via DOI
    python -m processing.paper_transition report.json --download-published
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from arxivbot.models.cmo import Author, CMO
from organization.system import FolderRouter, PUBLISHED

# Default library root
LIBRARY_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "Maths"
if not LIBRARY_ROOT.exists():
    LIBRARY_ROOT = Path.home() / "Library/CloudStorage/Dropbox/Work/Maths"


def build_canonical_filename_from_crossref(match: dict) -> str:
    """Build a canonical filename from Crossref match data."""
    title = match.get("matched_title", "")
    authors = []

    # We don't have full author info in the report, so we fall back to
    # the original filename's author portion if possible
    return ""  # Let the caller handle this


def transition_paper(
    entry: dict,
    *,
    library_root: Path = LIBRARY_ROOT,
    topic: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Move a single paper to its new location.

    Parameters
    ----------
    entry : dict
        A single entry from the publication checker report
        (must have ``"file"``, ``"match"`` with DOI/journal info).
    library_root : Path
        Root of the library.
    topic : str or None
        Topic prefix if the paper should also be filed under a topic.
    dry_run : bool
        If True, report but don't move.

    Returns
    -------
    dict
        Action taken (or would be taken).
    """
    result = {
        "file": entry["file"],
        "success": False,
        "action": "",
    }

    source = Path(entry["file"])
    if not source.exists():
        result["action"] = f"SKIP: file not found: {source}"
        return result

    match = entry.get("match", {})
    doi = match.get("doi")

    # Determine destination: 01 - Published papers / {A} /
    # Use the existing filename — it's already in the correct format
    filename = source.name

    # Get first author lastname for alphabetical routing
    stem = unicodedata.normalize("NFC", source.stem)
    if " - " in stem:
        authors_part = stem.split(" - ", 1)[0]
        # Strip leading numbers
        authors_part = re.sub(r"^\d+\s*[-–]\s*", "", authors_part)
        # First part before comma is the first author lastname
        first_lastname = authors_part.split(",")[0].strip()
    else:
        first_lastname = "Z"

    # Get alpha subdirectory
    first_char = unicodedata.normalize("NFD", first_lastname)[0].upper()
    alpha = first_char if "A" <= first_char <= "Z" else "Z"

    # Build destination
    base = library_root
    if topic:
        # Find topic directory
        for d in sorted(library_root.iterdir()):
            if d.is_dir() and d.name.lower().startswith(topic.lower()):
                base = d
                break

    dest_dir = base / PUBLISHED / alpha
    destination = dest_dir / filename

    # Check if already exists at destination
    if destination.exists():
        result["action"] = f"SKIP: already exists at {destination}"
        result["success"] = True
        return result

    if dry_run:
        result["action"] = f"WOULD MOVE: {source.name} → {destination}"
        result["destination"] = str(destination)
        result["success"] = True
        return result

    # Perform the move
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        result["action"] = f"MOVED: {source.name} → {destination}"
        result["destination"] = str(destination)
        result["success"] = True
    except Exception as exc:
        result["action"] = f"ERROR: {exc}"
        logger.error("Failed to move %s: %s", source, exc)

    return result


def process_report(
    report_path: Path,
    *,
    library_root: Path = LIBRARY_ROOT,
    min_confidence: float = 0.75,
    dry_run: bool = False,
    verbose: bool = False,
) -> list[dict]:
    """Process a publication checker report and move confirmed papers.

    Parameters
    ----------
    report_path : Path
        Path to the JSON report from publication_checker.
    library_root : Path
        Library root directory.
    min_confidence : float
        Minimum confidence threshold for moving papers.
    dry_run : bool
        Preview without moving.
    verbose : bool
        Print progress.
    """
    report = json.loads(report_path.read_text())
    published = report.get("published", [])

    if not published:
        if verbose:
            print("No published papers found in report.")
        return []

    results = []
    moved = 0

    for entry in published:
        match = entry.get("match", {})
        confidence = match.get("confidence", 0)

        if confidence < min_confidence:
            if verbose:
                print(f"  SKIP (confidence {confidence:.0%} < {min_confidence:.0%}): {entry.get('filename', '?')[:60]}")
            continue

        result = transition_paper(entry, library_root=library_root, dry_run=dry_run)
        results.append(result)

        if result["success"] and "MOVED" in result["action"]:
            moved += 1

        if verbose:
            print(f"  {result['action']}")

    if verbose:
        verb = "Would move" if dry_run else "Moved"
        print(f"\n{verb} {moved} papers to {PUBLISHED}/")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Move papers to new status folders based on publication checker report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow:
  1. Run publication_checker to generate a report
  2. Review the report
  3. Run paper_transition to move confirmed papers

Examples:
  %(prog)s report.json --dry-run         Preview moves
  %(prog)s report.json                   Move confirmed papers
  %(prog)s report.json --min-confidence 0.90  Only move high-confidence
""",
    )
    parser.add_argument("report", type=Path, help="JSON report from publication_checker")
    parser.add_argument("--library", type=Path, default=LIBRARY_ROOT)
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.report.exists():
        print(f"Error: report not found: {args.report}", file=sys.stderr)
        sys.exit(1)

    results = process_report(
        args.report,
        library_root=args.library,
        min_confidence=args.min_confidence,
        dry_run=args.dry_run,
        verbose=True,
    )

    ok = sum(1 for r in results if r["success"])
    print(f"\n{ok}/{len(results)} transitions completed")


if __name__ == "__main__":
    main()
