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

from processing.undo_log import UndoLog, logged_rename
from processing.identity import iter_pdfs


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
    #
    # NOT after a dash.  "Reygner, J. - , Propagation of chaos" has a stray
    # comma opening the title; without the guard this ate the separator's
    # space and produced "J. -, Propagation", destroying the author/title
    # boundary — which then hides the file from every rule that splits on
    # " - ", exactly how "Shiryaev, A.N.-" escaped the author sweep.
    s = re.sub(r"(?<![-–—‐])\s+,", ",", s)

    # A colon that a download tool sanitised into a hyphen.
    #
    # ":" is illegal in a filename on macOS, so browsers and publisher
    # sites save "Title: Subtitle" as "Title- Subtitle" — note the
    # asymmetry, NO space before the hyphen and one after, which a real
    # author-title separator (" - ") and a real hyphenated word
    # ("delay-differential") never have.  The house convention turns a
    # subtitle colon into ", " (cmo.py does this at ingest), so restore
    # that here; the subtitle's first word then lowercases by the normal
    # rule.  Measured: 4 files in the library, e.g.
    # "…delay-differential equations- When delay-systems…".
    s = re.sub(r"(?<=[^\W\d_])- (?=[A-ZÀ-ÖØ-Þ])", ", ", s)

    # A dash straight after a sentence-ending mark is redundant: the mark
    # has already closed the sentence, so "airplane?—The correct defence"
    # and "Mind the cap!—constrained portfolio" are stacking two
    # separators.  Drop the dash and start the next word as the new
    # sentence it is.
    #
    # Restricted to "?" and "!" ON PURPOSE.  A period is also a sentence
    # end, but it is equally the end of an abbreviation, and there the
    # dash is a genuine author-title separator that must survive:
    #   "…, Jr. - Option pricing theory"
    #   "Helffer, B., …, et al. - Première classe de Chern"
    #   "Yoeurp, Ch. - Compléments sur les temps locaux"
    # No abbreviation ends in "?" or "!", so this cannot misfire.
    s = re.sub(r"([?!])\s*[-–—‐]+\s*([^\W\d_])",
               lambda m: f"{m.group(1)} {m.group(2).upper()}", s)

    # The author-title separator with its space eaten: "Itô, K.- Poisson".
    # The rules below only normalise a dash that ALREADY has a space on
    # one side, and the sanitised-colon rule above needs a word character
    # before the dash, so a dash hugging an initial's period fell through
    # both.  A compound initial ("Zou, H.-F.") is untouched because its
    # dash has no space after it.
    s = re.sub(r"(?<=[A-ZÀ-Þ]\.)-\s+(?=[^\W\d_\s])", " - ", s)

    # Fix spaces around the author-title separator dash
    # "Author  - Title" → "Author - Title"
    # "Author -Title" → "Author - Title"
    # "Author- Title" → "Author - Title"
    # But DON'T touch hyphens inside initials like "J.-P."
    s = re.sub(r"(?<!\.)  +- +", " - ", s)  # double+ space before dash
    s = re.sub(r"(?<!\.) +- +", " - ", s)   # normalize single space around dash

    # Missing space after a comma: "Possamaï,D." → "Possamaï, D."
    #
    # AUTHOR BLOCK ONLY, and this is the whole point.  Applied to the full
    # name it rewrote MATHEMATICS — "C^{0,1}" became "C^{0, 1}", "W^{2,p}"
    # became "W^{2, p}", "CARMA(p,q)" became "CARMA(p, q)", "10,000" would
    # become "10, 000".  86 files were damaged that way by a batch labelled
    # "cosmetic, no letters changed"; no letters had changed, but the
    # notation had.  Measured over the whole library, the title side has
    # ZERO commas needing a space and one that must never be touched, so
    # restricting the rule costs nothing and is the only thing that makes
    # it structurally unable to reach a formula.
    #
    # Deliberately AFTER the separator repairs above: "Possamaï,D.- Title"
    # has no " - " until they run, and the author block cannot be
    # identified before the boundary exists.
    _head, _sep, _tail = s.partition(" - ")
    if _sep:
        s = re.sub(r",([^\s])", r", \1", _head) + _sep + _tail

    # "--" is ambiguous, so decide by context rather than blanket-replacing.
    # Between digits it is a range and becomes an en dash ("pp. 10--20").
    # Spaced, it is a subtitle break — the same role as the colon handled
    # above — so it takes the house comma: "…term structure -- An empirical
    # study" is "…term structure, an empirical study", and the subtitle's
    # first word then lowercases by the normal rule.  It is NOT an en dash:
    # that mark joins two co-equal entities, which a title and its subtitle
    # are not.  Measured: exactly one "--" in 29,336 filenames.
    s = re.sub(r"(?<=\d)--(?=\d)", "–", s)
    s = re.sub(r"\s+--\s+", ", ", s)

    # A title that opens with the separator's own punctuation: "J. - ,
    # Propagation of chaos".  The comma is a leftover from whatever wrote
    # the name, not part of the title.
    s = re.sub(r"( - )[,;]\s*", r"\1", s)

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

    pattern = iter_pdfs(directory) if recursive else iter_pdfs(directory, recursive=False)

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
