#!/usr/bin/env python3
"""Weekly library maintenance: publication checks, duplicates, aging.

Runs all maintenance checks in sequence and produces an HTML report
with macOS notification summary.

Usage::

    # Run all checks (default: last report saved to ~/.mathpdf/reports/)
    python -m maintenance.weekly_report

    # Dry run (check but don't move anything)
    python -m maintenance.weekly_report --dry-run

    # Limit Crossref queries (for testing)
    python -m maintenance.weekly_report --limit 20

    # Skip specific checks
    python -m maintenance.weekly_report --skip aging --skip duplicates
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Default paths
LIBRARY_ROOT = Path.home() / "Library/CloudStorage/Dropbox/Work/Maths"
REPORT_DIR = Path.home() / ".mathpdf" / "reports"


def check_publications(
    library_root: Path,
    *,
    limit: Optional[int] = None,
    verbose: bool = False,
) -> dict:
    """Check if unpublished/working papers have been published."""
    from processing.publication_checker import scan_directory

    results = {"unpublished": [], "working": []}

    for folder_name, key in [
        ("02 - Unpublished papers", "unpublished"),
        ("03 - Working papers", "working"),
    ]:
        folder = library_root / folder_name
        if not folder.exists():
            continue

        if verbose:
            print(f"\nChecking {folder_name}...")

        found = scan_directory(folder, limit=limit, verbose=verbose)
        published = [r for r in found if r.get("published")]
        results[key] = published

        if verbose:
            print(f"  Found {len(published)} newly published papers")

    return results


def check_aging(
    library_root: Path,
    *,
    max_age_years: int = 5,
    verbose: bool = False,
) -> list[dict]:
    """Find working papers that should move to unpublished (too old)."""
    from processing.aging_checker import find_aged_papers

    candidates = find_aged_papers(
        library_root, max_age_years=max_age_years, verbose=verbose
    )
    return candidates


def check_duplicates(
    library_root: Path,
    *,
    verbose: bool = False,
) -> list[dict]:
    """Find duplicate papers across the library."""
    from processing.duplicate_finder import find_duplicates

    clusters = find_duplicates(
        library_root,
        min_title_similarity=95.0,
        exclude_cross_filings=True,
        verbose=verbose,
    )
    return clusters


def generate_html_report(
    results: dict,
    report_path: Path,
) -> None:
    """Generate an HTML report from all maintenance check results."""
    pub = results.get("publications", {})
    aging = results.get("aging", [])
    dupes = results.get("duplicates", [])
    timestamp = results.get("timestamp", "")

    newly_published = pub.get("unpublished", []) + pub.get("working", [])
    n_published = len(newly_published)
    n_aging = len(aging)
    n_dupes = len(dupes)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Math-PDF Library Report — {timestamp}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; }}
h1 {{ color: #333; border-bottom: 2px solid #007AFF; padding-bottom: 0.3em; }}
h2 {{ color: #555; margin-top: 2em; }}
.summary {{ background: #f5f5f7; padding: 1em; border-radius: 8px; margin: 1em 0; }}
.count {{ font-size: 2em; font-weight: bold; color: #007AFF; }}
.item {{ padding: 0.5em 0; border-bottom: 1px solid #eee; }}
.item:last-child {{ border-bottom: none; }}
.doi {{ color: #888; font-size: 0.85em; }}
.journal {{ color: #007AFF; font-weight: 500; }}
.confidence {{ color: #999; font-size: 0.85em; }}
.folder {{ color: #666; font-size: 0.85em; }}
.empty {{ color: #999; font-style: italic; }}
</style>
</head>
<body>
<h1>Library Maintenance Report</h1>
<p>{timestamp}</p>

<div class="summary">
<span class="count">{n_published}</span> newly published &nbsp;|&nbsp;
<span class="count">{n_aging}</span> aging papers &nbsp;|&nbsp;
<span class="count">{n_dupes}</span> potential duplicates
</div>
"""

    # Publication section
    html += "<h2>Newly Published Papers</h2>\n"
    if newly_published:
        for p in newly_published:
            match = p.get("match", {})
            html += f"""<div class="item">
<strong>{p.get('filename', '?')[:80]}</strong><br>
<span class="journal">{match.get('journal', '?')}</span>
<span class="doi">DOI: {match.get('doi', '?')}</span>
<span class="confidence">({match.get('confidence', 0):.0%})</span>
</div>\n"""
    else:
        html += '<p class="empty">No newly published papers found.</p>\n'

    # Aging section
    html += "<h2>Aging Working Papers (move to Unpublished?)</h2>\n"
    if aging:
        by_year = {}
        for a in aging:
            y = a.get("year", "?")
            by_year.setdefault(y, []).append(a)
        for year in sorted(by_year.keys(), key=lambda y: y or 0):
            html += f"<h3>{year} ({len(by_year[year])} papers)</h3>\n"
            for a in by_year[year][:10]:
                html += f'<div class="item">{a.get("filename", "?")[:80]}</div>\n'
            if len(by_year[year]) > 10:
                html += f'<p class="empty">... and {len(by_year[year]) - 10} more</p>\n'
    else:
        html += '<p class="empty">No aging papers found.</p>\n'

    # Duplicates section
    html += "<h2>Potential Duplicates</h2>\n"
    if dupes:
        for i, cluster in enumerate(dupes[:20], 1):
            match_type = "EXACT" if cluster.get("content_match") else f"FUZZY ({cluster.get('title_similarity', 0):.0f}%)"
            html += f'<div class="item"><strong>Cluster {i}</strong> [{match_type}]<br>\n'
            for f in cluster.get("files", []):
                html += f'&nbsp;&nbsp;{f.get("filename", "?")[:70]}<br>\n'
                html += f'&nbsp;&nbsp;<span class="folder">{f.get("folder", "")}</span><br>\n'
            html += "</div>\n"
        if len(dupes) > 20:
            html += f'<p class="empty">... and {len(dupes) - 20} more clusters</p>\n'
    else:
        html += '<p class="empty">No duplicates found.</p>\n'

    html += "</body></html>"

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")


def run_maintenance(
    library_root: Path = LIBRARY_ROOT,
    *,
    limit: Optional[int] = None,
    skip: Optional[set] = None,
    verbose: bool = False,
) -> dict:
    """Run all maintenance checks and return results."""
    skip = skip or set()
    results = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}

    t0 = time.time()

    # 1. Publication checks
    if "publications" not in skip:
        if verbose:
            print("=" * 60)
            print("PUBLICATION CHECKS")
            print("=" * 60)
        results["publications"] = check_publications(
            library_root, limit=limit, verbose=verbose
        )
    else:
        results["publications"] = {"unpublished": [], "working": []}

    # 2. Aging checks
    if "aging" not in skip:
        if verbose:
            print("\n" + "=" * 60)
            print("AGING CHECKS")
            print("=" * 60)
        results["aging"] = check_aging(library_root, verbose=verbose)
    else:
        results["aging"] = []

    # 3. Duplicate checks
    if "duplicates" not in skip:
        if verbose:
            print("\n" + "=" * 60)
            print("DUPLICATE CHECKS")
            print("=" * 60)
        results["duplicates"] = check_duplicates(library_root, verbose=verbose)
    else:
        results["duplicates"] = []

    elapsed = time.time() - t0
    results["elapsed_seconds"] = round(elapsed, 1)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run weekly library maintenance checks",
    )
    parser.add_argument("--library", type=Path, default=LIBRARY_ROOT)
    parser.add_argument("--limit", type=int, help="Limit Crossref queries (for testing)")
    parser.add_argument("--skip", action="append", default=[],
                        choices=["publications", "aging", "duplicates"],
                        help="Skip a check")
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    print(f"Running maintenance on {args.library}...")
    results = run_maintenance(
        args.library.resolve(),
        limit=args.limit,
        skip=set(args.skip),
        verbose=args.verbose,
    )

    # Generate report
    timestamp = datetime.now().strftime("%Y-%m-%d")
    report_path = args.report_dir / f"maintenance_{timestamp}.html"
    generate_html_report(results, report_path)
    print(f"\nReport: {report_path}")

    # Also save JSON
    json_path = args.report_dir / f"maintenance_{timestamp}.json"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))

    # Summary
    pub = results.get("publications", {})
    n_pub = len(pub.get("unpublished", [])) + len(pub.get("working", []))
    n_aging = len(results.get("aging", []))
    n_dupes = len(results.get("duplicates", []))

    summary = f"{n_pub} published, {n_aging} aging, {n_dupes} duplicates"
    print(f"\nSummary: {summary}")
    print(f"Elapsed: {results.get('elapsed_seconds', 0)}s")

    # macOS notification
    if not args.no_notify:
        try:
            from watcher.notifier import notify
            notify("Library Maintenance Complete", summary)
        except Exception:
            pass

    # Open report in browser
    if not args.dry_run:
        import subprocess
        subprocess.run(["open", str(report_path)], capture_output=True)


if __name__ == "__main__":
    main()
