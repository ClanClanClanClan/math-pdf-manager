#!/usr/bin/env python3
"""Find duplicate papers across the library using fuzzy filename matching.

Detects duplicates caused by:
- Trailing/leading spaces in author names
- Punctuation variants (comma vs period)
- Unicode normalization differences
- Preprint vs published title changes

Usage::

    python -m processing.duplicate_finder /path/to/library
    python -m processing.duplicate_finder /path/to/library --min-similarity 90
    python -m processing.duplicate_finder /path/to/library --json --output dupes.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from processing.undo_log import UndoLog


def normalize_for_comparison(filename: str) -> str:
    """Normalize a filename stem for fuzzy comparison.

    Strips noise that causes false non-matches: extra spaces, trailing
    spaces around commas, unicode normalization differences, punctuation
    variants.
    """
    s = unicodedata.normalize("NFC", filename)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    # Normalize spaces around punctuation
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"\s*-\s*", " - ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_for_scoring(filename: str) -> str:
    """Aggressively normalize for similarity scoring.

    Removes all punctuation and lowercases for maximum fuzzy match recall.
    """
    s = normalize_for_comparison(filename)
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_title_from_filename(stem: str) -> str:
    """Extract just the title part from a filename stem."""
    stem = re.sub(r"^\d+\s*[-–]\s*", "", stem)  # strip number prefixes
    if " - " in stem:
        return stem.split(" - ", 1)[1].strip()
    return stem


def extract_first_author(stem: str) -> str:
    """Extract first author lastname from a filename stem."""
    stem = re.sub(r"^\d+\s*[-–]\s*", "", stem)
    if " - " in stem:
        authors_part = stem.split(" - ", 1)[0]
        return authors_part.split(",")[0].strip().lower()
    return ""


def find_duplicates(
    library_root: Path,
    *,
    min_title_similarity: float = 95.0,
    exclude_cross_filings: bool = True,
    verbose: bool = False,
) -> list[dict]:
    """Find duplicate papers across the library.

    Matching is based primarily on **title similarity** (≥ min_title_similarity).
    Papers are grouped by first author lastname for efficiency, but the match
    decision is driven by title — many authors share family names and write
    different papers.

    Parameters
    ----------
    library_root : Path
        Root of the library (e.g. ``…/Maths/``).
    min_title_similarity : float
        Minimum fuzzy *title* similarity (0-100) to consider a match.
        Default 95 is deliberately strict — different papers by the same
        author often share keywords but have clearly different titles.
    exclude_cross_filings : bool
        If True, skip pairs where one file is in a topic folder (07x/) and
        the other is in the corresponding main folder (01-03/).  These are
        intentional copies, not true duplicates.
    verbose : bool
        Print progress.

    Returns
    -------
    list[dict]
        List of duplicate clusters, each with files and similarity scores.
    """
    if verbose:
        print("Scanning library for PDFs...")

    entries = []
    for pdf in library_root.rglob("*.pdf"):
        rel = pdf.relative_to(library_root)
        if any(part.startswith(("Scripts", "archive", ".", "unicode")) for part in rel.parts):
            continue

        stem = unicodedata.normalize("NFC", pdf.stem)
        title = extract_title_from_filename(stem)
        first_author = extract_first_author(stem)
        normalized_title = normalize_for_scoring(title)

        # Track which top-level folder this belongs to
        top_folder = rel.parts[0] if rel.parts else ""
        is_topic = top_folder.startswith("07")

        entries.append({
            "path": pdf,
            "stem": stem,
            "title": title,
            "first_author": first_author,
            "normalized_title": normalized_title,
            "size": pdf.stat().st_size,
            "top_folder": top_folder,
            "is_topic": is_topic,
        })

    if verbose:
        print(f"Found {len(entries):,} PDFs. Comparing...")

    # Group by first author for efficiency
    by_author = defaultdict(list)
    for e in entries:
        by_author[e["first_author"]].append(e)

    clusters = []
    seen_pairs = set()
    total_entries = sum(len(g) for g in by_author.values() if len(g) > 1)
    checked = 0

    for group in by_author.values():
        if len(group) < 2:
            continue

        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                # Quick length filter
                len_a = len(a["normalized_title"])
                len_b = len(b["normalized_title"])
                if len_a > 0 and len_b > 0:
                    ratio = min(len_a, len_b) / max(len_a, len_b)
                    if ratio < 0.6:
                        continue

                # Title similarity is the PRIMARY criterion
                title_score = fuzz.ratio(a["normalized_title"], b["normalized_title"])

                if title_score < min_title_similarity:
                    continue

                # Skip intentional cross-filings
                if exclude_cross_filings:
                    if a["is_topic"] != b["is_topic"]:
                        # One is in 07x, the other in 01-03 — likely intentional
                        continue
                    if a["is_topic"] and b["is_topic"] and a["top_folder"] != b["top_folder"]:
                        # Both in different topic folders — also likely intentional
                        continue

                pair_key = tuple(sorted([str(a["path"]), str(b["path"])]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                content_match = _files_identical(a["path"], b["path"])

                clusters.append({
                    "title_similarity": title_score,
                    "content_match": content_match,
                    "files": [
                        {
                            "path": str(a["path"]),
                            "filename": a["path"].name,
                            "title": a["title"],
                            "size_kb": a["size"] // 1024,
                            "folder": a["top_folder"],
                        },
                        {
                            "path": str(b["path"]),
                            "filename": b["path"].name,
                            "title": b["title"],
                            "size_kb": b["size"] // 1024,
                            "folder": b["top_folder"],
                        },
                    ],
                })

            checked += 1
            if verbose and checked % 500 == 0:
                print(f"  Checked {checked:,}/{total_entries:,}, found {len(clusters)} potential duplicates...")

    # Sort by: content matches first, then by title similarity
    clusters.sort(key=lambda c: (-c["content_match"], -c["title_similarity"]))

    if verbose:
        exact = sum(1 for c in clusters if c["content_match"])
        print(f"\nFound {len(clusters)} potential duplicate pairs ({exact} exact content matches)")

    return clusters


def _files_identical(a: Path, b: Path) -> bool:
    """Check if two files have identical content (SHA-256)."""
    if a.stat().st_size != b.stat().st_size:
        return False
    return _file_hash(a) == _file_hash(b)


def _file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find duplicate papers in the library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("library", type=Path, help="Library root directory")
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=95.0,
        help="Minimum title similarity (0-100, default: 95)",
    )
    parser.add_argument("--include-cross-filings", action="store_true",
                        help="Also show intentional cross-filings between topic and main folders")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path, help="Write report to file")
    parser.add_argument("--limit", type=int, help="Show top N clusters only")
    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = build_parser()
    args = parser.parse_args(argv)

    clusters = find_duplicates(
        args.library.resolve(),
        min_title_similarity=args.min_similarity,
        exclude_cross_filings=not args.include_cross_filings,
        verbose=args.verbose,
    )

    if args.limit:
        clusters = clusters[: args.limit]

    if args.json:
        output = json.dumps(clusters, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(output)
            print(f"Report written to {args.output}")
        else:
            print(output)
    else:
        if not clusters:
            print("No duplicates found.")
            return

        exact = sum(1 for c in clusters if c["content_match"])
        fuzzy = len(clusters) - exact
        print(f"\nFound {len(clusters)} potential duplicate pairs:")
        print(f"  {exact} exact content matches (identical files)")
        print(f"  {fuzzy} fuzzy matches (similar filenames, possibly different versions)")

        for i, cluster in enumerate(clusters, 1):
            match_type = "EXACT" if cluster["content_match"] else f"FUZZY ({cluster['title_similarity']:.0f}%)"
            print(f"\n--- Cluster {i} [{match_type}] ---")
            for f in cluster["files"]:
                print(f"  [{f['size_kb']:>6,} KB] {f['filename'][:80]}")
                # Show relative path for context
                parts = Path(f["path"]).parts
                try:
                    maths_idx = parts.index("Maths")
                    folder = "/".join(parts[maths_idx + 1 : maths_idx + 3])
                    print(f"             in {folder}")
                except ValueError:
                    pass


if __name__ == "__main__":
    main()
