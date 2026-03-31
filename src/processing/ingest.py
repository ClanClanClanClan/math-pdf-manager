#!/usr/bin/env python3
"""Ingest a new PDF into the library.

Extracts metadata, generates the canonical filename, and files the paper
in the correct directory.

Usage::

    python -m processing.ingest paper.pdf
    python -m processing.ingest paper.pdf --status published
    python -m processing.ingest paper.pdf --topic 07a
    python -m processing.ingest paper.pdf --dry-run
    python -m processing.ingest *.pdf --status working --year 2025
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# Ensure src/ is on the path when invoked directly
# ---------------------------------------------------------------------------
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from arxivbot.models.cmo import Author, CMO
from organization.system import OrganizationSystem

logger = logging.getLogger(__name__)

# Default library root
LIBRARY_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "Maths"
if not LIBRARY_ROOT.exists():
    # Fallback for Dropbox path
    LIBRARY_ROOT = Path.home() / "Library/CloudStorage/Dropbox/Work/Maths"


# ---------------------------------------------------------------------------
# Metadata extraction (lightweight — uses PyMuPDF + filename heuristics)
# ---------------------------------------------------------------------------
def extract_metadata_from_pdf(pdf_path: Path) -> dict:
    """Extract basic metadata from a PDF file.

    Tries embedded PDF metadata first, then falls back to the LLM extractor
    if available, then to filename parsing.
    """
    metadata = {"title": "", "authors": [], "doi": None, "arxiv_id": None, "year": None}

    try:
        doc = fitz.open(pdf_path)
        pdf_meta = doc.metadata or {}

        # Extract title from PDF metadata
        title = (pdf_meta.get("title") or "").strip()
        if title and len(title) > 5:
            metadata["title"] = unicodedata.normalize("NFC", title)

        # Extract author from PDF metadata
        author_str = (pdf_meta.get("author") or "").strip()
        if author_str:
            metadata["authors_raw"] = author_str

        # Check for DOI in first few pages
        text = ""
        for page_num in range(min(3, len(doc))):
            text += doc[page_num].get_text()

        import re

        # DOI detection
        doi_match = re.search(r"\b(10\.\d{4,}/\S+)", text)
        if doi_match:
            doi = doi_match.group(1).rstrip(".")
            metadata["doi"] = doi

        # ArXiv ID detection
        arxiv_match = re.search(r"arXiv[:\s]*(\d{4}\.\d{4,5}(?:v\d+)?)", text)
        if arxiv_match:
            metadata["arxiv_id"] = arxiv_match.group(1)

        # Year detection
        year_match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", pdf_meta.get("creationDate", ""))
        if year_match:
            metadata["year"] = int(year_match.group(1))

        doc.close()
    except Exception as exc:
        logger.warning("Failed to extract PDF metadata from %s: %s", pdf_path, exc)

    # Try Crossref lookup if we have a DOI
    if metadata.get("doi") and not metadata["title"]:
        try:
            import requests

            resp = requests.get(
                f"https://api.crossref.org/works/{metadata['doi']}",
                headers={"User-Agent": "MathPDFManager/1.0 (mailto:admin@example.com)"},
                timeout=10,
            )
            if resp.status_code == 200:
                cr = resp.json().get("message", {})
                titles = cr.get("title", [])
                if titles:
                    metadata["title"] = unicodedata.normalize("NFC", titles[0])
                cr_authors = cr.get("author", [])
                if cr_authors:
                    metadata["authors"] = [
                        {"family": a.get("family", ""), "given": a.get("given", "")}
                        for a in cr_authors
                        if a.get("family")
                    ]
                if cr.get("journal"):
                    metadata["journal"] = cr["journal"]
                pub_date = cr.get("published-print") or cr.get("published-online")
                if pub_date and pub_date.get("date-parts"):
                    parts = pub_date["date-parts"][0]
                    if parts:
                        metadata["year"] = parts[0]
        except Exception as exc:
            logger.debug("Crossref lookup failed for %s: %s", metadata["doi"], exc)

    # Try LLM extraction if title is still missing
    if not metadata["title"]:
        try:
            from pdf_processing.llm_extractor import LLMMetadataExtractor

            extractor = LLMMetadataExtractor()
            llm_result = extractor.extract(pdf_path)
            if llm_result and llm_result.get("title"):
                metadata["title"] = llm_result["title"]
                if llm_result.get("authors"):
                    metadata["authors"] = llm_result["authors"]
        except Exception:
            pass  # LLM not available

    return metadata


def parse_authors_string(raw: str) -> list[Author]:
    """Parse a raw author string into Author objects.

    Handles formats like:
    - ``"Jean-Pierre Dupont; Nicole el Karoui"``
    - ``"Dupont, J.-P. and el Karoui, N."``
    - ``"J.-P. Dupont, N. el Karoui"``
    """
    import re

    # Split on semicolons, " and ", or " & "
    parts = re.split(r"\s*(?:;|\s+and\s+|\s*&\s*)\s*", raw)

    authors = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Try "Lastname, Given" format
        if ", " in part:
            pieces = part.split(", ", 1)
            authors.append(Author(family=pieces[0].strip(), given=pieces[1].strip()))
        elif " " in part:
            # "Given Lastname" — last word is family name (heuristic)
            words = part.rsplit(" ", 1)
            authors.append(Author(family=words[-1].strip(), given=words[0].strip()))
        else:
            authors.append(Author(family=part))

    return authors


def metadata_to_cmo(metadata: dict, pdf_path: Path) -> CMO:
    """Convert extracted metadata dict into a CMO object."""
    authors = []
    if metadata.get("authors") and isinstance(metadata["authors"], list):
        for a in metadata["authors"]:
            if isinstance(a, str):
                # "Firstname Lastname" format from LLM
                if " " in a:
                    parts = a.rsplit(" ", 1)
                    authors.append(Author(family=parts[-1], given=parts[0]))
                else:
                    authors.append(Author(family=a))
            elif isinstance(a, dict):
                authors.append(Author(**a))
    elif metadata.get("authors_raw"):
        authors = parse_authors_string(metadata["authors_raw"])

    title = metadata.get("title", "")
    if not title:
        # Last resort: use filename stem
        title = pdf_path.stem

    return CMO(
        external_id=str(pdf_path),
        source="local",
        title=title,
        authors=authors,
        doi=metadata.get("doi"),
    )


# ---------------------------------------------------------------------------
# Main ingest logic
# ---------------------------------------------------------------------------
def ingest_paper(
    pdf_path: Path,
    *,
    library_root: Path = LIBRARY_ROOT,
    status: Optional[str] = None,
    topic: Optional[str] = None,
    year: Optional[int] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Ingest a single PDF into the library.

    Parameters
    ----------
    pdf_path : Path
        Path to the PDF file.
    library_root : Path
        Root of the library (e.g. ``…/Maths/``).
    status : str or None
        Force publication status (``"published"``, ``"unpublished"``,
        ``"working"``).  If None, auto-detected from metadata.
    topic : str or None
        Topic prefix (e.g. ``"07a"``) for topic-specific filing.
    year : int or None
        Year for working papers.  Auto-detected if not provided.
    dry_run : bool
        If True, report actions without moving files.
    verbose : bool
        If True, print detailed progress.

    Returns
    -------
    dict
        Summary of actions taken.
    """
    result = {
        "file": str(pdf_path),
        "success": False,
        "actions": [],
        "filename": "",
        "destination": "",
    }

    if not pdf_path.exists():
        result["error"] = f"File not found: {pdf_path}"
        return result

    if not pdf_path.suffix.lower() == ".pdf":
        result["error"] = f"Not a PDF file: {pdf_path}"
        return result

    # Step 1: Extract metadata
    if verbose:
        print(f"  Extracting metadata from {pdf_path.name}...")
    metadata = extract_metadata_from_pdf(pdf_path)

    # Step 2: Build CMO and generate canonical filename
    cmo = metadata_to_cmo(metadata, pdf_path)
    canonical_name = cmo.get_canonical_filename()
    result["filename"] = canonical_name

    if verbose:
        print(f"  Title: {cmo.title}")
        print(f"  Authors: {', '.join(a.display_name() for a in cmo.authors)}")
        print(f"  Canonical name: {canonical_name}")
        if metadata.get("doi"):
            print(f"  DOI: {metadata['doi']}")
        if metadata.get("arxiv_id"):
            print(f"  ArXiv: {metadata['arxiv_id']}")

    # Step 3: Override status if specified
    if status:
        metadata["_forced_status"] = status
        if status == "published":
            metadata.setdefault("doi", "forced")
        elif status == "unpublished":
            metadata.setdefault("arxiv_id", "forced")
            metadata.pop("doi", None)
        elif status == "working":
            metadata.pop("doi", None)
            metadata.pop("arxiv_id", None)

    # Step 4: Determine year for working papers
    paper_year = year or metadata.get("year")

    # Step 5: Organize (route to correct directory)
    org = OrganizationSystem(library_root, topic=topic, dry_run=dry_run)
    org_result = org.organize(pdf_path, metadata, canonical_name, year=paper_year)

    result["destination"] = str(org_result.destination)
    result["status"] = org_result.publication_status
    result["actions"] = org_result.actions
    result["success"] = not any("ERROR" in a for a in org_result.actions)

    if verbose:
        print(f"  Status: {org_result.publication_status}")
        for action in org_result.actions:
            prefix = "  " if "WARNING" not in action else "  ⚠ "
            print(f"{prefix}{action}")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest PDFs into the math library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s paper.pdf                     Auto-detect and file
  %(prog)s paper.pdf --status published  Force as published
  %(prog)s paper.pdf --topic 07a         File under BSDEs
  %(prog)s *.pdf --dry-run               Preview without moving
  %(prog)s paper.pdf --status working --year 2025
""",
    )
    parser.add_argument("files", nargs="+", type=Path, help="PDF files to ingest")
    parser.add_argument(
        "--status",
        choices=["published", "unpublished", "working", "book", "thesis"],
        help="Force publication status (auto-detected if omitted)",
    )
    parser.add_argument("--topic", help="Topic prefix for filing (e.g. '07a')")
    parser.add_argument("--year", type=int, help="Year for working papers")
    parser.add_argument(
        "--library",
        type=Path,
        default=LIBRARY_ROOT,
        help=f"Library root (default: {LIBRARY_ROOT})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without moving files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = build_parser()
    args = parser.parse_args(argv)

    results = []
    for pdf_path in args.files:
        pdf_path = pdf_path.resolve()
        if not args.json and not args.verbose:
            print(f"Ingesting {pdf_path.name}...", end=" ")

        result = ingest_paper(
            pdf_path,
            library_root=args.library,
            status=args.status,
            topic=args.topic,
            year=args.year,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        results.append(result)

        if not args.json and not args.verbose:
            if result["success"]:
                print(f"→ {result['destination']}")
            else:
                print(f"FAILED: {result.get('error', 'unknown')}")

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    # Summary
    if len(results) > 1 and not args.json:
        ok = sum(1 for r in results if r["success"])
        print(f"\n{ok}/{len(results)} papers ingested successfully")


if __name__ == "__main__":
    main()
