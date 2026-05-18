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

# Default paths
from core.config_paths import get_library_root as _get_library_root
LIBRARY_ROOT = _get_library_root()
REPORT_DIR = Path.home() / ".mathpdf" / "reports"


def check_publications(
    library_root: Path,
    *,
    limit: Optional[int] = None,
    verbose: bool = False,
) -> dict:
    """Check if unpublished/working papers have been published.

    Each folder is wrapped in a try/except so a single failure (e.g., Crossref
    timeout) doesn't crash the whole maintenance run; the failed folder gets
    an empty result + an entry in ``results['_errors']``.

    Side effect: every Crossref query result is fed through
    ``processing.publication_state.update_publication_state`` so the
    per-paper recheck counter advances and papers tip into
    ``permanently_unpublished`` after enough consecutive misses.  This
    is what makes the Phase 2 state machine actually run -- without
    this hook the sidecars would never update.
    """
    from processing.publication_checker import scan_directory
    from processing.publication_state import update_publication_state

    results: dict = {
        "unpublished": [],
        "working": [],
        "newly_permanent": [],
        "_errors": [],
    }

    for folder_name, key in [
        ("02 - Unpublished papers", "unpublished"),
        ("03 - Working papers", "working"),
    ]:
        folder = library_root / folder_name
        if not folder.exists():
            continue

        if verbose:
            print(f"\nChecking {folder_name}...")

        try:
            found = scan_directory(folder, limit=limit, verbose=verbose)
            # Advance the per-paper state machine over every entry in
            # ``found`` (hits and misses both).  Errors here don't
            # abort the report -- they're a soft, optional layer.
            try:
                state = update_publication_state(found)
                results["newly_permanent"].extend(state.newly_permanent)
                if verbose and state.newly_permanent:
                    print(
                        f"  {len(state.newly_permanent)} paper(s) tipped into "
                        f"permanently_unpublished after this scan"
                    )
            except Exception as exc:
                logger.warning("update_publication_state failed: %s", exc)

            published = [r for r in found if r.get("published")]
            results[key] = published
            if verbose:
                print(f"  Found {len(published)} newly published papers")
        except Exception as exc:
            logger.exception("Publication check failed for %s", folder_name)
            results["_errors"].append({
                "step": f"check_publications/{folder_name}",
                "error": str(exc),
            })
            if verbose:
                print(f"  ERROR: {exc} (continuing)")

    return results


def check_aging(
    library_root: Path,
    *,
    max_age_years: int = 5,
    verbose: bool = False,
) -> list[dict]:
    """Find working papers that should move to unpublished (too old)."""
    from processing.aging_checker import find_aged_papers
    try:
        return find_aged_papers(
            library_root, max_age_years=max_age_years, verbose=verbose
        )
    except Exception as exc:
        logger.exception("Aging check failed")
        if verbose:
            print(f"  ERROR in check_aging: {exc} (continuing)")
        return []


def check_duplicates(
    library_root: Path,
    *,
    verbose: bool = False,
) -> list[dict]:
    """Find duplicate papers across the library."""
    from processing.duplicate_finder import find_duplicates
    try:
        return find_duplicates(
            library_root,
            min_title_similarity=95.0,
            exclude_cross_filings=True,
            verbose=verbose,
        )
    except Exception as exc:
        logger.exception("Duplicate check failed")
        if verbose:
            print(f"  ERROR in check_duplicates: {exc} (continuing)")
        return []


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


def count_to_be_sorted(library_root: Path) -> dict:
    """Count PDFs awaiting sorting in ``12 - To be sorted/{01,03,05}/``."""
    try:
        from organization.system import TO_BE_SORTED
    except ImportError:
        TO_BE_SORTED = "12 - To be sorted"
    base = library_root / TO_BE_SORTED
    counts: dict = {"total": 0, "by_subfolder": {}}
    if not base.exists():
        return counts
    for child in sorted(base.iterdir()):
        if child.is_dir():
            n = sum(1 for _ in child.rglob("*.pdf"))
            counts["by_subfolder"][child.name] = n
            counts["total"] += n
    return counts


# ---------------------------------------------------------------------------
# Phase 3: auto-apply only the safe subset of weekly findings
# ---------------------------------------------------------------------------

# Confidence at or above which a Crossref hit is considered "safe to
# auto-upgrade".  Borderline matches still appear in the report; the
# user reviews them via the Upgrade Queue / Attention Queue tabs.
SAFE_UPGRADE_CONFIDENCE = 0.95


def auto_apply_safe_transitions(
    results: dict,
    library_root: Path,
    *,
    upgrade_confidence_threshold: float = SAFE_UPGRADE_CONFIDENCE,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Auto-execute only the SAFE subset of the weekly maintenance results.

    Two kinds of transitions are considered safe enough to run without
    user confirmation:

    1. **High-confidence upgrade**: a Crossref hit with confidence at
       or above ``upgrade_confidence_threshold`` AND exactly one
       parsed author (multi-author papers carry a real merge risk if
       the title collides).  These are passed to
       ``upgrade_to_published.upgrade_paper`` which downloads the
       published PDF, files it, and moves the preprint to .trash/.

    2. **Aged + permanently unpublished**: working papers older than
       the aging cutoff whose sidecar says
       ``permanently_unpublished=True`` (we already tried Crossref
       three times and failed).  These are moved 03 → 02 via
       ``aging_checker.transition_aged_papers``.

    Everything else stays in the report and surfaces in the Attention
    Queue for user review.
    """
    summary: dict = {
        "upgraded": [],
        "aged_moved": [],
        "skipped_borderline": [],
        "errors": [],
    }

    # -----------------------------------------------------------------
    # 1. Safe upgrades
    # -----------------------------------------------------------------
    pubs = results.get("publications", {})
    all_hits = list(pubs.get("unpublished", [])) + list(pubs.get("working", []))

    def _is_safe_upgrade(entry: dict) -> bool:
        match = entry.get("match") or {}
        conf = float(match.get("confidence", 0))
        if conf < upgrade_confidence_threshold:
            return False
        # Single-author check: BOTH the filename parse AND the Crossref
        # match must agree the paper has exactly one author.  A
        # multi-author paper filed with only the first author in the
        # filename (legitimate filing convention) would otherwise
        # auto-upgrade with a real merge risk if the title collides.
        parsed_authors = entry.get("parsed_authors") or []
        if len(parsed_authors) != 1:
            return False
        # ``author_count`` is set by publication_checker.py when it
        # builds the match dict.  Older cached results without it fall
        # back to ``1`` so we don't break existing pipelines, but a
        # *non-1* count is a hard block.
        cr_count = match.get("author_count", 1)
        if cr_count != 1:
            return False
        return True

    safe_upgrades = [e for e in all_hits if _is_safe_upgrade(e)]
    borderline = [
        {"file": e["file"], "reason": "confidence or multi-author below auto-apply threshold"}
        for e in all_hits if not _is_safe_upgrade(e)
    ]
    summary["skipped_borderline"].extend(borderline)

    if safe_upgrades:
        if verbose:
            print(f"\nAuto-upgrading {len(safe_upgrades)} safe candidate(s)"
                  + (" (dry run)" if dry_run else ""))
        if not dry_run:
            try:
                from processing.upgrade_to_published import upgrade_paper
            except ImportError as exc:
                summary["errors"].append(f"upgrade module unavailable: {exc}")
                return summary
            for entry in safe_upgrades:
                try:
                    r = upgrade_paper(entry, library_root, dry_run=False)
                    if r.get("success"):
                        summary["upgraded"].append(entry["file"])
                    else:
                        summary["skipped_borderline"].append({
                            "file": entry["file"],
                            "reason": r.get("error", "upgrade returned no success"),
                        })
                except Exception as exc:
                    summary["errors"].append(f"{entry.get('file')}: {exc}")
        else:
            # In dry-run mode we still report what *would* upgrade.
            for entry in safe_upgrades:
                summary["upgraded"].append(entry["file"] + "  (WOULD)")

    # -----------------------------------------------------------------
    # 2. Aged AND permanently_unpublished -> move to 02
    # -----------------------------------------------------------------
    aging_candidates = results.get("aging", [])
    if aging_candidates:
        try:
            from processing.identity import PaperIdentity
            from processing.aging_checker import transition_aged_papers
        except ImportError as exc:
            summary["errors"].append(f"aging modules unavailable: {exc}")
            return summary

        # Only safe to auto-move papers we've already given up on.  A
        # 6-year-old paper we never Crossref-checked might still get
        # published next month; we don't want to pre-emptively bury it.
        safe_age = []
        for cand in aging_candidates:
            try:
                ident = PaperIdentity.load(Path(cand["path"]))
            except Exception:
                continue
            if ident.permanently_unpublished:
                safe_age.append(cand)

        if safe_age:
            if verbose:
                print(f"\nAuto-aging {len(safe_age)} permanent + aged paper(s)"
                      + (" (dry run)" if dry_run else ""))
            if not dry_run:
                age_results = transition_aged_papers(safe_age, dry_run=False)
                for r in age_results:
                    if r.get("status") == "MOVED":
                        summary["aged_moved"].append(r["file"])
                    elif "ERROR" in (r.get("status") or ""):
                        summary["errors"].append(
                            f"aging {r.get('file')}: {r.get('status')}"
                        )
            else:
                for cand in safe_age:
                    summary["aged_moved"].append(cand["filename"] + "  (WOULD)")

    return summary


def run_maintenance(
    library_root: Path = LIBRARY_ROOT,
    *,
    limit: Optional[int] = None,
    skip: Optional[set] = None,
    verbose: bool = False,
    auto_apply_safe: bool = False,
    auto_apply_dry_run: bool = False,
) -> dict:
    """Run all maintenance checks and return results."""
    skip = skip or set()
    results = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}

    # Cheap: count the to-be-sorted backlog so it's always visible.
    try:
        results["to_be_sorted"] = count_to_be_sorted(library_root)
    except Exception as exc:
        logger.warning("Could not count to-be-sorted backlog: %s", exc)
        results["to_be_sorted"] = {"total": 0, "by_subfolder": {}}

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

    # 4. Optional: auto-apply only the safe subset of findings.
    # Borderline cases stay in the report.
    if auto_apply_safe:
        if verbose:
            print("\n" + "=" * 60)
            print("AUTO-APPLY SAFE TRANSITIONS"
                  + (" (DRY RUN)" if auto_apply_dry_run else ""))
            print("=" * 60)
        results["auto_applied"] = auto_apply_safe_transitions(
            results, library_root,
            dry_run=auto_apply_dry_run, verbose=verbose,
        )
    else:
        results["auto_applied"] = {
            "upgraded": [], "aged_moved": [], "skipped_borderline": [], "errors": [],
        }

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
    parser.add_argument(
        "--auto-apply-safe",
        action="store_true",
        help="Auto-execute only the safe subset (single-author Crossref "
             "hits at confidence >= 0.95 and aged + permanently-unpublished "
             "papers).  Borderline cases stay in the report.",
    )
    parser.add_argument(
        "--auto-apply-dry-run",
        action="store_true",
        help="With --auto-apply-safe, list what would be applied without "
             "actually moving anything.",
    )
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
        auto_apply_safe=args.auto_apply_safe,
        auto_apply_dry_run=args.auto_apply_dry_run,
    )

    # Generate report. Include time so two runs on the same day don't
    # overwrite each other.
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report_path = args.report_dir / f"maintenance_{timestamp}.html"
    generate_html_report(results, report_path)
    print(f"\nReport: {report_path}")

    # Also save JSON (same timestamp keeps html/json paired)
    json_path = args.report_dir / f"maintenance_{timestamp}.json"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))

    # Summary
    pub = results.get("publications", {})
    n_pub = len(pub.get("unpublished", [])) + len(pub.get("working", []))
    n_aging = len(results.get("aging", []))
    n_dupes = len(results.get("duplicates", []))

    summary = f"{n_pub} published, {n_aging} aging, {n_dupes} duplicates"
    auto = results.get("auto_applied") or {}
    if auto.get("upgraded") or auto.get("aged_moved"):
        summary += (
            f", auto-upgraded {len(auto['upgraded'])}, "
            f"auto-aged {len(auto['aged_moved'])}"
        )
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
