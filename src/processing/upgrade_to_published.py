#!/usr/bin/env python3
"""Upgrade working papers to published versions.

Takes a publication checker report, downloads the published PDF via
DOI (Unpaywall → direct resolution), files it in the library, and
deletes the preprint.  Papers that can't be auto-downloaded are
flagged for manual download.

Usage::

    # Preview (no downloads, no moves)
    python -m processing.upgrade_to_published report.json --dry-run

    # Process top 20 highest-confidence
    python -m processing.upgrade_to_published report.json --limit 20

    # Just flag everything for manual download
    python -m processing.upgrade_to_published report.json --manual-only
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from processing.undo_log import UndoLog, logged_move, logged_copy

LIBRARY_ROOT = Path.home() / "Library/CloudStorage/Dropbox/Work/Maths"
import os as _os
UNPAYWALL_EMAIL = _os.environ.get("UNPAYWALL_EMAIL", "mathpdf-manager@example.com")
RATE_LIMIT_SECS = 1.0


# ---------------------------------------------------------------------------
# Download strategies
# ---------------------------------------------------------------------------

def _try_unpaywall(doi: str, output_path: Path) -> bool:
    """Try to download via Unpaywall (open access)."""
    try:
        resp = requests.get(
            f"https://api.unpaywall.org/v2/{doi}",
            params={"email": UNPAYWALL_EMAIL},
            timeout=15,
        )
        if resp.status_code != 200:
            return False

        data = resp.json()
        if not data.get("is_oa"):
            return False

        # Find best PDF URL
        pdf_url = None
        best = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf") or best.get("url")

        if not pdf_url:
            # Try other locations
            for loc in data.get("oa_locations", []):
                url = loc.get("url_for_pdf") or loc.get("url")
                if url and url.lower().endswith(".pdf"):
                    pdf_url = url
                    break

        if not pdf_url:
            return False

        # Download the PDF
        pdf_resp = requests.get(pdf_url, timeout=30, stream=True)
        if pdf_resp.status_code != 200:
            return False

        # Verify it's actually a PDF
        content_type = pdf_resp.headers.get("Content-Type", "")
        first_bytes = b""
        with open(output_path, "wb") as f:
            for chunk in pdf_resp.iter_content(chunk_size=8192):
                if not first_bytes:
                    first_bytes = chunk[:4]
                f.write(chunk)

        if first_bytes != b"%PDF":
            output_path.unlink(missing_ok=True)
            return False

        logger.info("Downloaded via Unpaywall: %s", doi)
        return True

    except Exception as exc:
        logger.debug("Unpaywall failed for %s: %s", doi, exc)
        output_path.unlink(missing_ok=True)
        return False


def _try_direct_doi(doi: str, output_path: Path) -> bool:
    """Try to download by following DOI redirect."""
    try:
        resp = requests.get(
            f"https://doi.org/{doi}",
            timeout=15,
            allow_redirects=True,
            headers={"Accept": "application/pdf"},
            stream=True,
        )

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            return False

        first_bytes = b""
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if not first_bytes:
                    first_bytes = chunk[:4]
                f.write(chunk)

        if first_bytes != b"%PDF":
            output_path.unlink(missing_ok=True)
            return False

        logger.info("Downloaded via DOI redirect: %s", doi)
        return True

    except Exception as exc:
        logger.debug("Direct DOI failed for %s: %s", doi, exc)
        output_path.unlink(missing_ok=True)
        return False


def try_download_by_doi(doi: str, output_dir: Path) -> Optional[Path]:
    """Try to download a published PDF via DOI.

    Strategies (in order):
    1. Unpaywall API (open access)
    2. Direct DOI resolution (follow redirects)

    Returns path to downloaded PDF, or None if all fail.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_doi = re.sub(r"[/\\:]", "_", doi)
    output_path = output_dir / f"{safe_doi}.pdf"

    time.sleep(RATE_LIMIT_SECS)

    if _try_unpaywall(doi, output_path):
        return output_path

    time.sleep(RATE_LIMIT_SECS)

    if _try_direct_doi(doi, output_path):
        return output_path

    return None


# ---------------------------------------------------------------------------
# Flag for manual download
# ---------------------------------------------------------------------------

def flag_for_manual_download(
    entry: dict,
    library_root: Path,
) -> Path:
    """Create a flag file in 04/ for manual download.

    Returns the path to the flag file.
    """
    match = entry.get("match", {})
    doi = match.get("doi", "unknown")
    journal = match.get("journal", "Unknown Journal")
    title = entry.get("parsed_title", "Unknown")
    authors = ", ".join(entry.get("parsed_authors", []))
    preprint_path = entry.get("file", "")

    # Sanitise journal name for folder
    safe_journal = re.sub(r'[/\\:*?"<>|]', '-', journal)[:80]
    flag_dir = library_root / "04 - Papers to be downloaded" / safe_journal
    flag_dir.mkdir(parents=True, exist_ok=True)

    # Write info file
    safe_title = re.sub(r'[/\\:*?"<>|]', '-', title)[:80]
    flag_file = flag_dir / f"{safe_title}.txt"

    content = f"""DOI: {doi}
Journal: {journal}
Year: {match.get('year', '?')}
Title: {title}
Authors: {authors}
Confidence: {match.get('confidence', 0):.0%}
Preprint: {preprint_path}
URL: https://doi.org/{doi}

Download the published PDF and drop it in ~/Downloads/MathInbox/
The watcher will auto-file it.
"""
    flag_file.write_text(content, encoding="utf-8")
    return flag_file


# ---------------------------------------------------------------------------
# Single paper upgrade
# ---------------------------------------------------------------------------

def upgrade_paper(
    entry: dict,
    library_root: Path,
    download_dir: Path,
    *,
    dry_run: bool = False,
    manual_only: bool = False,
    undo_log: Optional[UndoLog] = None,
) -> dict:
    """Upgrade a single paper from preprint to published version."""
    result = {
        "file": entry.get("file", ""),
        "doi": entry.get("match", {}).get("doi", ""),
        "action": "",
        "success": False,
    }

    match = entry.get("match", {})
    doi = match.get("doi")
    if not doi:
        result["action"] = "SKIP: no DOI"
        return result

    preprint_path = Path(entry.get("file", ""))

    if dry_run:
        result["action"] = f"WOULD TRY: download {doi} → replace {preprint_path.name[:50]}"
        result["success"] = True
        return result

    # Try to download the published version
    published_pdf = None
    if not manual_only:
        published_pdf = try_download_by_doi(doi, download_dir)

    if published_pdf:
        # Downloaded successfully — ingest into library
        try:
            from processing.ingest import ingest_paper

            ingest_result = ingest_paper(
                published_pdf,
                library_root=library_root,
                status="published",
                dry_run=False,
                undo_log=undo_log,
            )

            if ingest_result["success"]:
                # Compare file sizes
                pub_size = published_pdf.stat().st_size
                pre_size = preprint_path.stat().st_size if preprint_path.exists() else 0

                if pre_size > pub_size * 1.2:
                    # Preprint is >20% larger — may have extra content
                    result["action"] = f"DOWNLOADED + FILED (kept preprint — {pre_size // 1024}KB > {pub_size // 1024}KB, may have extra content)"
                    result["kept_preprint"] = True
                else:
                    # Delete preprint
                    if preprint_path.exists():
                        if undo_log:
                            undo_log.record_move(preprint_path, Path("/dev/null"))
                        preprint_path.unlink()
                        result["action"] = f"DOWNLOADED + FILED + DELETED preprint"
                    else:
                        result["action"] = f"DOWNLOADED + FILED (preprint already gone)"
                    result["kept_preprint"] = False

                result["destination"] = ingest_result.get("destination", "")
                result["success"] = True
            else:
                result["action"] = f"DOWNLOADED but filing failed: {ingest_result.get('error', '?')}"

        except Exception as exc:
            result["action"] = f"DOWNLOADED but error during filing: {exc}"
            logger.error("Filing error for %s: %s", doi, exc)

        # Clean up temp download
        published_pdf.unlink(missing_ok=True)

    else:
        # Could not download — flag for manual download
        flag_file = flag_for_manual_download(entry, library_root)
        result["action"] = f"FLAGGED for manual download → {flag_file.parent.name}/"
        result["flag_file"] = str(flag_file)
        result["success"] = True  # flagging is a success

    return result


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_report(
    report_path: Path,
    library_root: Path = LIBRARY_ROOT,
    *,
    min_confidence: float = 0.85,
    dry_run: bool = False,
    manual_only: bool = False,
    max_papers: Optional[int] = None,
    verbose: bool = False,
) -> dict:
    """Process a publication checker report.

    Downloads published versions, files them, deletes preprints,
    flags failures for manual download.
    """
    report = json.loads(report_path.read_text())
    published = report.get("published", [])

    # Filter by confidence
    candidates = [
        p for p in published
        if p.get("match", {}).get("confidence", 0) >= min_confidence
    ]

    if max_papers:
        # Sort by confidence (highest first) and take top N
        candidates.sort(key=lambda p: -p.get("match", {}).get("confidence", 0))
        candidates = candidates[:max_papers]

    if verbose:
        print(f"Processing {len(candidates)} papers (from {len(published)} published, confidence ≥ {min_confidence:.0%})")

    # Set up undo log and temp download directory
    undo_log = None
    tx_id = None
    if not dry_run:
        undo_log = UndoLog()
        tx_id = undo_log.begin_transaction(f"Upgrade {len(candidates)} papers to published")

    download_dir = Path(tempfile.mkdtemp(prefix="mathpdf_downloads_"))

    results = []
    downloaded = 0
    flagged = 0
    skipped = 0

    for i, entry in enumerate(candidates, 1):
        match = entry.get("match", {})
        if verbose:
            journal = match.get("journal", "?")[:30]
            conf = match.get("confidence", 0)
            print(f"  [{i}/{len(candidates)}] ({conf:.0%}) {journal}: {entry.get('filename', '?')[:45]}", end=" ")

        r = upgrade_paper(
            entry, library_root, download_dir,
            dry_run=dry_run,
            manual_only=manual_only,
            undo_log=undo_log,
        )
        results.append(r)

        if "DOWNLOADED" in r.get("action", ""):
            downloaded += 1
        elif "FLAGGED" in r.get("action", ""):
            flagged += 1
        else:
            skipped += 1

        if verbose:
            print(f"→ {r['action'][:60]}")

    # Commit undo log
    if undo_log and (downloaded > 0 or flagged > 0):
        log_file = undo_log.commit()
        if verbose:
            print(f"\nUndo log: {log_file}")

    # Clean up temp dir
    shutil.rmtree(download_dir, ignore_errors=True)

    summary = {
        "total_candidates": len(candidates),
        "downloaded": downloaded,
        "flagged": flagged,
        "skipped": skipped,
        "results": results,
    }

    if verbose:
        print(f"\nSummary: {downloaded} downloaded, {flagged} flagged for manual, {skipped} skipped")
        if tx_id:
            print(f"To undo: python -m processing.undo_log undo --transaction {tx_id}")

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Download published versions and replace preprints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s report.json --dry-run           Preview what would happen
  %(prog)s report.json --limit 20          Process top 20
  %(prog)s report.json --manual-only       Just flag for manual download
  %(prog)s report.json --min-confidence 0.90  Only high-confidence matches
""",
    )
    parser.add_argument("report", type=Path, help="JSON report from publication_checker")
    parser.add_argument("--library", type=Path, default=LIBRARY_ROOT)
    parser.add_argument("--min-confidence", type=float, default=0.85)
    parser.add_argument("--limit", type=int, help="Process at most N papers")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--manual-only", action="store_true", help="Skip downloads, just flag for manual")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.report.exists():
        print(f"Error: report not found: {args.report}", file=sys.stderr)
        sys.exit(1)

    summary = process_report(
        args.report,
        args.library,
        min_confidence=args.min_confidence,
        dry_run=args.dry_run,
        manual_only=args.manual_only,
        max_papers=args.limit,
        verbose=True,
    )

    # Save summary
    summary_path = args.report.parent / "upgrade_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print(f"\nDetailed results: {summary_path}")


if __name__ == "__main__":
    main()
