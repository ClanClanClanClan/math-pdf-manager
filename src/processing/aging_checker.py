#!/usr/bin/env python3
"""Check for working papers that should move to unpublished (aged out).

Papers in ``03 - Working papers/{A-Z}/{year}/`` that are 5+ years old
without updates should move to ``02 - Unpublished papers/{A-Z}/``.

Usage::

    python -m processing.aging_checker /path/to/library
    python -m processing.aging_checker /path/to/library --max-age 5
    python -m processing.aging_checker /path/to/library --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from organization.system import UNPUBLISHED, WORKING
from processing.undo_log import UndoLog, logged_move


def find_aged_papers(
    library_root: Path,
    *,
    max_age_years: int = 5,
    verbose: bool = False,
) -> list[dict]:
    """Find working papers older than max_age_years.

    Scans ``03 - Working papers/{A-Z}/{year}/`` and identifies papers
    in year folders that are too old.
    """
    working_dir = library_root / WORKING
    if not working_dir.exists():
        if verbose:
            print(f"Working papers directory not found: {working_dir}")
        return []

    current_year = datetime.now().year
    cutoff_year = current_year - max_age_years

    candidates = []

    for alpha_dir in sorted(working_dir.iterdir()):
        if not alpha_dir.is_dir() or len(alpha_dir.name) != 1:
            # Loose files (not in A-Z subdirs) — check by filename if possible
            if alpha_dir.suffix.lower() == ".pdf":
                # Loose PDF in working papers root — flag but no year info
                candidates.append({
                    "path": str(alpha_dir),
                    "filename": alpha_dir.name,
                    "year": None,
                    "age": None,
                    "reason": "loose file (no year folder)",
                })
            continue

        for year_dir in sorted(alpha_dir.iterdir()):
            if not year_dir.is_dir():
                # PDF directly in alpha dir (no year subdir)
                continue

            try:
                year = int(year_dir.name)
            except ValueError:
                continue

            if year > cutoff_year:
                continue  # too recent

            age = current_year - year
            for pdf in sorted(year_dir.glob("*.pdf")):
                # Extract first author for destination routing
                stem = unicodedata.normalize("NFC", pdf.stem)
                if " - " in stem:
                    authors_part = stem.split(" - ", 1)[0]
                    first_lastname = authors_part.split(",")[0].strip()
                else:
                    first_lastname = "Z"

                first_char = unicodedata.normalize("NFD", first_lastname)[0].upper()
                alpha = first_char if "A" <= first_char <= "Z" else "Z"

                dest = library_root / UNPUBLISHED / alpha / pdf.name

                candidates.append({
                    "path": str(pdf),
                    "filename": pdf.name,
                    "year": year,
                    "age": age,
                    "first_author_alpha": alpha,
                    "destination": str(dest),
                    "already_exists": dest.exists(),
                })

    if verbose:
        print(f"Found {len(candidates)} papers older than {max_age_years} years")

    return candidates


def transition_aged_papers(
    candidates: list[dict],
    *,
    dry_run: bool = False,
    interactive: bool = False,
) -> list[dict]:
    """Move aged papers from 03 to 02."""
    if not candidates:
        return []

    if interactive and not dry_run:
        print(f"\n{len(candidates)} papers to move from Working → Unpublished:\n")
        for i, c in enumerate(candidates[:20], 1):
            age_str = f"{c['age']}y old" if c.get("age") else "unknown age"
            print(f"  [{i}] ({age_str}) {c['filename'][:65]}")
        if len(candidates) > 20:
            print(f"  ... and {len(candidates) - 20} more")

        choice = input(f"\nMove all {len(candidates)}? [a]ll / [c]ancel: ").strip().lower()
        if choice != "a":
            print("Cancelled.")
            return []

    undo_log = None
    tx_id = None
    if not dry_run:
        undo_log = UndoLog()
        tx_id = undo_log.begin_transaction(f"Age {len(candidates)} papers from Working → Unpublished")

    results = []
    moved = 0

    for c in candidates:
        source = Path(c["path"])
        dest = Path(c["destination"])

        if c.get("already_exists"):
            results.append({"file": c["filename"], "status": "SKIP: already in 02"})
            continue

        if dry_run:
            results.append({"file": c["filename"], "status": f"WOULD MOVE (age: {c.get('age', '?')}y)"})
        else:
            try:
                logged_move(source, dest, undo_log=undo_log)
                results.append({"file": c["filename"], "status": "MOVED"})
                moved += 1
            except Exception as exc:
                results.append({"file": c["filename"], "status": f"ERROR: {exc}"})

    if undo_log and moved > 0:
        undo_log.commit()
        print(f"\nMoved {moved} papers. To revert: python -m processing.undo_log undo --transaction {tx_id}")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description="Find and move aged working papers to unpublished")
    parser.add_argument("library", type=Path, help="Library root directory")
    parser.add_argument("--max-age", type=int, default=5, help="Max age in years (default: 5)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    candidates = find_aged_papers(
        args.library.resolve(),
        max_age_years=args.max_age,
        verbose=args.verbose,
    )

    if not candidates:
        print("No aged papers found.")
        return

    if args.json:
        print(json.dumps(candidates, indent=2, ensure_ascii=False))
        return

    # Group by year
    by_year = {}
    for c in candidates:
        y = c.get("year", "unknown")
        by_year.setdefault(y, []).append(c)

    print(f"\nAged working papers (>{args.max_age} years):")
    for year in sorted(by_year.keys()):
        count = len(by_year[year])
        print(f"  {year}: {count} papers")
    print(f"  Total: {len(candidates)}")

    if args.dry_run:
        results = transition_aged_papers(candidates, dry_run=True)
        print(f"\nDry run: would move {len(results)} papers")
    else:
        results = transition_aged_papers(candidates, interactive=True)


if __name__ == "__main__":
    main()
