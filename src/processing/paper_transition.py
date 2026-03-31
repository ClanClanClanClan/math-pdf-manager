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
from organization.system import FolderRouter, PUBLISHED, UNPUBLISHED, WORKING
from processing.undo_log import UndoLog, logged_move

# Default library root
LIBRARY_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "Maths"
if not LIBRARY_ROOT.exists():
    LIBRARY_ROOT = Path.home() / "Library/CloudStorage/Dropbox/Work/Maths"


def find_preprint_versions(
    library_root: Path,
    filename: str,
    published_path: Path,
) -> list[dict]:
    """Search for preprint versions of a paper in 02/ and 03/.

    Returns a list of candidate preprint files with size comparison info.
    """
    from rapidfuzz import fuzz

    stem = unicodedata.normalize("NFC", Path(filename).stem)
    title = stem.split(" - ", 1)[1].strip() if " - " in stem else stem
    title_norm = re.sub(r"[^\w\s]", "", title.lower())

    candidates = []
    for folder_name in [UNPUBLISHED, WORKING]:
        folder = library_root / folder_name
        if not folder.exists():
            continue
        for pdf in folder.rglob("*.pdf"):
            if pdf == published_path:
                continue
            pdf_stem = unicodedata.normalize("NFC", pdf.stem)
            pdf_title = pdf_stem.split(" - ", 1)[1].strip() if " - " in pdf_stem else pdf_stem
            pdf_title_norm = re.sub(r"[^\w\s]", "", pdf_title.lower())

            score = fuzz.ratio(title_norm, pdf_title_norm)
            if score >= 90:
                pub_size = published_path.stat().st_size if published_path.exists() else 0
                pre_size = pdf.stat().st_size

                candidates.append({
                    "path": str(pdf),
                    "filename": pdf.name,
                    "title_similarity": score,
                    "preprint_size_kb": pre_size // 1024,
                    "published_size_kb": pub_size // 1024,
                    "preprint_larger": pre_size > pub_size * 1.2,  # >20% larger
                })

    return candidates


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

    # Perform the move (with undo log)
    undo_log = entry.get("_undo_log")
    try:
        logged_move(source, destination, undo_log=undo_log)
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
    interactive: bool = False,
    auto_approve: bool = False,
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
    interactive : bool
        Ask for approval before each move.
    auto_approve : bool
        Approve all moves without asking (batch mode).
    verbose : bool
        Print progress.
    """
    report = json.loads(report_path.read_text())
    published = report.get("published", [])

    if not published:
        if verbose:
            print("No published papers found in report.")
        return []

    # Filter by confidence
    candidates = []
    for entry in published:
        match = entry.get("match", {})
        confidence = match.get("confidence", 0)
        if confidence >= min_confidence:
            candidates.append(entry)
        elif verbose:
            print(f"  SKIP (confidence {confidence:.0%} < {min_confidence:.0%}): {entry.get('filename', '?')[:60]}")

    if not candidates:
        print("No papers above confidence threshold.")
        return []

    # Show preview if interactive
    if interactive and not auto_approve:
        print(f"\n{len(candidates)} papers would be moved to {PUBLISHED}/:\n")
        for i, entry in enumerate(candidates, 1):
            m = entry.get("match", {})
            print(f"  [{i}] {entry.get('filename', '?')[:65]}")
            print(f"      → DOI: {m.get('doi', '?')}  |  {m.get('journal', '?')[:40]}  |  Conf: {m['confidence']:.0%}")

        print(f"\nOptions: [a]pprove all, [s]elect individually, [c]ancel")
        choice = input("> ").strip().lower()

        if choice == "c":
            print("Cancelled.")
            return []
        elif choice == "s":
            # Individual selection
            approved = []
            for i, entry in enumerate(candidates, 1):
                resp = input(f"  Move [{i}] {entry.get('filename', '?')[:50]}? [y/n] ").strip().lower()
                if resp == "y":
                    approved.append(entry)
            candidates = approved
            if not candidates:
                print("No papers approved.")
                return []
        elif choice != "a":
            print("Cancelled.")
            return []

    # Set up undo log
    undo_log = None
    if not dry_run:
        undo_log = UndoLog()
        desc = f"Transition {len(candidates)} papers from {report_path.name}"
        tx_id = undo_log.begin_transaction(desc)
        print(f"Transaction ID: {tx_id}  (use 'python -m processing.undo_log undo' to revert)")

    results = []
    moved = 0

    for entry in candidates:
        if undo_log:
            entry["_undo_log"] = undo_log
        result = transition_paper(entry, library_root=library_root, dry_run=dry_run)
        # Clean up internal key
        entry.pop("_undo_log", None)
        results.append(result)

        if result["success"] and "MOVED" in result["action"]:
            moved += 1

        if verbose or not dry_run:
            print(f"  {result['action']}")

    # Commit the undo log
    if undo_log and moved > 0:
        log_file = undo_log.commit()
        print(f"\nMoved {moved} papers. Undo log: {log_file}")
        print(f"To revert: python -m processing.undo_log undo --transaction {tx_id}")
    elif dry_run:
        print(f"\nWould move {len(candidates)} papers (dry run)")

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
    parser.add_argument("-i", "--interactive", action="store_true", help="Ask before each move")
    parser.add_argument("-y", "--yes", action="store_true", help="Approve all without asking")
    parser.add_argument("--cleanup-preprints", action="store_true",
                        help="After moving, search for and delete preprint versions in 02/03")
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
        interactive=args.interactive or (not args.yes and not args.dry_run),
        auto_approve=args.yes,
        verbose=True,
    )

    ok = sum(1 for r in results if r["success"])
    print(f"\n{ok}/{len(results)} transitions completed")


if __name__ == "__main__":
    main()
