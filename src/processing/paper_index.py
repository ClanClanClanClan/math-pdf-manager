#!/usr/bin/env python3
"""Build a cross-reference index of all papers in the library.

Maps each paper identity (normalized title + first author) to all file
paths where it appears.  Distinguishes intentional cross-filings (same
paper in 01/ and 07a/) from true duplicates (same paper twice in 01/).

Usage::

    python -m processing.paper_index /path/to/library
    python -m processing.paper_index /path/to/library --duplicates-only
    python -m processing.paper_index /path/to/library --json --output index.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def _normalize_key(title: str, first_author: str) -> str:
    """Create a canonical identity key from title + first author."""
    t = unicodedata.normalize("NFC", title.lower())
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    a = unicodedata.normalize("NFC", first_author.lower())
    a = re.sub(r"[^\w]", "", a)
    return f"{a}::{t}"


def _parse_stem(stem: str) -> tuple[str, str]:
    """Parse filename stem into (title, first_author_lastname)."""
    stem = re.sub(r"^\d+\s*[-–]\s*", "", stem)
    if " - " not in stem:
        return stem, ""
    authors_part, title = stem.split(" - ", 1)
    first_author = authors_part.split(",")[0].strip()
    return title.strip(), first_author


def _classify_location(path: Path, library_root: Path) -> dict:
    """Classify where a file sits in the library structure."""
    try:
        rel = path.relative_to(library_root)
    except ValueError:
        return {"type": "unknown", "folder": str(path.parent)}

    parts = rel.parts
    if not parts:
        return {"type": "unknown", "folder": ""}

    top = parts[0]
    is_topic = top.startswith("07")

    if "01 - Published" in top or (is_topic and len(parts) > 1 and "01 - Published" in parts[1]):
        status = "published"
    elif "02 - Unpublished" in top or (is_topic and len(parts) > 1 and "02 - Unpublished" in parts[1]):
        status = "unpublished"
    elif "03 - Working" in top or (is_topic and len(parts) > 1 and "03 - Working" in parts[1]):
        status = "working"
    elif "05 - Books" in top:
        status = "book"
    elif "06 - Theses" in top:
        status = "thesis"
    else:
        status = "other"

    return {
        "type": status,
        "folder": top,
        "is_topic": is_topic,
    }


def build_index(
    library_root: Path,
    *,
    verbose: bool = False,
) -> dict:
    """Build a paper identity index.

    Returns a dict mapping identity keys to lists of file locations.
    """
    index = defaultdict(list)

    pdfs = list(library_root.rglob("*.pdf"))
    if verbose:
        print(f"Indexing {len(pdfs):,} PDFs...")

    for pdf in pdfs:
        rel = pdf.relative_to(library_root)
        if any(p.startswith(("Scripts", "archive", ".", "unicode")) for p in rel.parts):
            continue

        stem = unicodedata.normalize("NFC", pdf.stem)
        title, first_author = _parse_stem(stem)
        key = _normalize_key(title, first_author)

        location = _classify_location(pdf, library_root)

        index[key].append({
            "path": str(pdf),
            "filename": pdf.name,
            "title": title,
            "first_author": first_author,
            **location,
        })

    if verbose:
        multi = sum(1 for v in index.values() if len(v) > 1)
        print(f"Indexed {len(index):,} unique papers, {multi:,} appear in multiple locations")

    return dict(index)


def analyze_index(index: dict) -> dict:
    """Analyze the index for duplicates, cross-filings, and anomalies."""
    analysis = {
        "total_unique_papers": len(index),
        "multi_location_papers": 0,
        "true_duplicates": [],      # same paper, same folder type, NOT cross-filing
        "cross_filings": [],        # same paper in topic + main folder (intentional)
        "status_conflicts": [],     # same paper in both published and unpublished
        "preprint_with_published": [],  # preprint exists alongside published version
    }

    for key, locations in index.items():
        if len(locations) < 2:
            continue

        analysis["multi_location_papers"] += 1

        # Classify the relationship
        folders = {loc["folder"] for loc in locations}
        types = {loc["type"] for loc in locations}
        has_topic = any(loc["is_topic"] for loc in locations)
        has_main = any(not loc["is_topic"] for loc in locations)

        if "published" in types and ("unpublished" in types or "working" in types):
            analysis["preprint_with_published"].append({
                "title": locations[0]["title"],
                "first_author": locations[0]["first_author"],
                "locations": [{"path": l["path"], "type": l["type"], "folder": l["folder"]} for l in locations],
            })
        elif has_topic and has_main:
            analysis["cross_filings"].append({
                "title": locations[0]["title"][:60],
                "count": len(locations),
                "folders": list(folders),
            })
        elif len(folders) == 1 or (not has_topic and not has_main):
            # Same folder or both in main — true duplicate
            analysis["true_duplicates"].append({
                "title": locations[0]["title"][:60],
                "first_author": locations[0]["first_author"],
                "locations": [{"path": l["path"], "folder": l["folder"]} for l in locations],
            })

    return analysis


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description="Build paper identity index")
    parser.add_argument("library", type=Path, help="Library root directory")
    parser.add_argument("--duplicates-only", action="store_true",
                        help="Only show true duplicates (not cross-filings)")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path, help="Write full index to file")
    args = parser.parse_args(argv)

    index = build_index(args.library.resolve(), verbose=args.verbose)
    analysis = analyze_index(index)

    if args.output:
        args.output.write_text(json.dumps(index, indent=2, ensure_ascii=False))
        print(f"Full index written to {args.output}")

    if args.json:
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
        return

    print(f"\n=== Paper Identity Index ===")
    print(f"Unique papers: {analysis['total_unique_papers']:,}")
    print(f"In multiple locations: {analysis['multi_location_papers']:,}")
    print(f"  Cross-filings (intentional): {len(analysis['cross_filings']):,}")
    print(f"  True duplicates: {len(analysis['true_duplicates']):,}")
    print(f"  Preprint + published coexist: {len(analysis['preprint_with_published']):,}")

    if analysis["preprint_with_published"]:
        print(f"\n--- Preprints that should be deleted (published version exists) ---")
        for p in analysis["preprint_with_published"][:20]:
            print(f"\n  {p['first_author']} - {p['title'][:55]}")
            for loc in p["locations"]:
                print(f"    [{loc['type']:12s}] {loc['folder']}")

    if not args.duplicates_only and analysis["true_duplicates"]:
        print(f"\n--- True duplicates ---")
        for d in analysis["true_duplicates"][:20]:
            print(f"\n  {d['first_author']} - {d['title'][:55]}")
            for loc in d["locations"]:
                print(f"    {loc['path'][-70:]}")


if __name__ == "__main__":
    main()
