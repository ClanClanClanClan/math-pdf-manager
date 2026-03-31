#!/usr/bin/env python3
"""Normalize filename formatting across the library.

Fixes common issues:
- Trailing/leading spaces around commas and dashes
- Double spaces
- Unicode normalization (NFD → NFC)
- Inconsistent dash types (-- → –)

Usage::

    python -m processing.filename_normalizer /path/to/library --dry-run
    python -m processing.filename_normalizer /path/to/library
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from processing.undo_log import UndoLog, logged_rename


def normalize_filename(name: str) -> str:
    """Normalize a PDF filename.

    Returns the normalized name, or the original if no changes needed.
    """
    stem, ext = name.rsplit(".", 1) if "." in name else (name, "")

    s = stem

    # NFC normalize (macOS stores as NFD)
    s = unicodedata.normalize("NFC", s)

    # Fix double/triple spaces
    s = re.sub(r"  +", " ", s)

    # Fix spaces before commas: "Possamaï , D." → "Possamaï, D."
    s = re.sub(r"\s+,", ",", s)

    # Fix missing space after comma: "Possamaï,D." → "Possamaï, D."
    s = re.sub(r",([^\s])", r", \1", s)

    # Fix spaces around the author-title separator dash
    # "Author  - Title" → "Author - Title"
    # "Author -Title" → "Author - Title"
    # "Author- Title" → "Author - Title"
    s = re.sub(r"\s*\s+-\s*", " - ", s)
    s = re.sub(r"\s+-\s+", " - ", s)

    # Normalize dash types: "--" → "–", but keep single "-" in names like "J.-P."
    # Only replace standalone double-dashes (not in initials)
    s = re.sub(r"(?<!\.)--(?!\.)", "–", s)

    # Strip trailing/leading whitespace
    s = s.strip()

    result = f"{s}.{ext}" if ext else s
    return result


def scan_and_propose(
    directory: Path,
    *,
    recursive: bool = True,
    verbose: bool = False,
) -> list[dict]:
    """Scan a directory and propose filename normalizations.

    Returns a list of proposals with original and normalized names.
    """
    proposals = []

    pattern = directory.rglob("*.pdf") if recursive else directory.glob("*.pdf")

    for pdf in sorted(pattern):
        # Skip non-library directories
        try:
            rel = pdf.relative_to(directory)
        except ValueError:
            continue
        if any(part.startswith(("Scripts", "archive", ".", "unicode")) for part in rel.parts):
            continue

        original = pdf.name
        normalized = normalize_filename(original)

        if normalized != original:
            proposals.append({
                "path": str(pdf),
                "directory": str(pdf.parent),
                "original": original,
                "normalized": normalized,
                "changes": _describe_changes(original, normalized),
            })

    return proposals


def _describe_changes(original: str, normalized: str) -> list[str]:
    """Describe what changed between original and normalized."""
    changes = []
    if "  " in original:
        changes.append("double spaces")
    if re.search(r"\s,", original):
        changes.append("space before comma")
    if original != unicodedata.normalize("NFC", original):
        changes.append("unicode normalization")
    if "--" in original:
        changes.append("double dash")
    if not changes:
        changes.append("whitespace/formatting")
    return changes


def apply_proposals(
    proposals: list[dict],
    *,
    dry_run: bool = False,
    undo_log: UndoLog | None = None,
) -> list[dict]:
    """Apply filename normalization proposals."""
    results = []
    for p in proposals:
        old_path = Path(p["path"])
        new_path = old_path.parent / p["normalized"]

        if new_path.exists() and old_path != new_path:
            results.append({"proposal": p, "status": "SKIP: destination exists"})
            continue

        if dry_run:
            results.append({"proposal": p, "status": "WOULD RENAME"})
        else:
            try:
                logged_rename(old_path, new_path, undo_log=undo_log)
                results.append({"proposal": p, "status": "RENAMED"})
            except Exception as exc:
                results.append({"proposal": p, "status": f"ERROR: {exc}"})

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description="Normalize filenames in the library")
    parser.add_argument("directory", type=Path, help="Directory to scan")
    parser.add_argument("--dry-run", action="store_true", help="Preview without renaming")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    directory = args.directory.resolve()
    proposals = scan_and_propose(directory, verbose=args.verbose)

    if not proposals:
        print("All filenames are already normalized.")
        return

    print(f"Found {len(proposals)} filenames needing normalization:\n")

    for p in proposals[:50]:  # show first 50
        print(f"  {p['original'][:70]}")
        print(f"  → {p['normalized'][:70]}")
        print(f"    Changes: {', '.join(p['changes'])}")
        print()

    if len(proposals) > 50:
        print(f"  ... and {len(proposals) - 50} more\n")

    if args.dry_run:
        print(f"Dry run: {len(proposals)} files would be renamed.")
        return

    confirm = input(f"Rename {len(proposals)} files? [y/N] ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    undo_log = UndoLog()
    tx_id = undo_log.begin_transaction(f"Normalize {len(proposals)} filenames")

    results = apply_proposals(proposals, undo_log=undo_log)

    renamed = sum(1 for r in results if r["status"] == "RENAMED")
    undo_log.commit()

    print(f"\nRenamed {renamed}/{len(proposals)} files.")
    print(f"To revert: python -m processing.undo_log undo --transaction {tx_id}")


if __name__ == "__main__":
    main()
