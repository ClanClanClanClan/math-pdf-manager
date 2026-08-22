#!/usr/bin/env python3
"""Bulk-sort raw PDFs from ``12 - To be sorted/`` into the main library.

The user drops bulk-imported PDFs (raw publisher downloads, ArXiv preprints,
ISBN-named books) into ``12 - To be sorted/{01 - Published, 03 - Working,
05 - Books and lecture notes}/``. The subfolder name is a *status hint*
that overrides the auto-detected status, because the user already knows the
classification when they drop the file.

This tool walks each subfolder, runs the standard ingest pipeline with the
hinted status, and on success moves the source PDF to a recoverable trash
location (``.trash/sorted_originals/``). Files that fail metadata extraction
or filename generation are left in place and listed for manual review.

Usage::

    # Preview what would happen (NEVER touches files)
    python -m processing.bulk_sort --dry-run

    # Process up to 50 papers, asking for confirmation per batch
    python -m processing.bulk_sort --limit 50

    # Actually sort the full backlog
    python -m processing.bulk_sort -y

    # Process only one subfolder
    python -m processing.bulk_sort --only "01 - Published papers" --limit 10

The script never DELETES — sources go to ``{library}/.trash/sorted_originals/``
where you can recover them if a filing decision turns out wrong.
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Callable, Iterable, Optional
from processing.identity import iter_pdfs

logger = logging.getLogger(__name__)

# Default library root — resolved via ``core.config_paths.get_library_root``
# so the user-specific Dropbox path lives in only one place (constants.py).
from core.config_paths import get_library_root as _get_library_root
LIBRARY_ROOT = _get_library_root()


# Map subfolder name → status hint passed to ingest_paper().
# These match the subfolders the user actually creates inside
# ``12 - To be sorted/``.
SUBFOLDER_STATUS = {
    "01 - Published papers": "published",
    "02 - Unpublished papers": "unpublished",
    "03 - Working papers": "working",
    "05 - Books and lecture notes": "book",
    "06 - Theses": "thesis",
}


def iter_pdfs_with_hint(staging_root: Path) -> Iterable[tuple[Path, str]]:
    """Yield ``(pdf_path, status_hint)`` for every PDF under ``12/{subfolder}/``.

    Subfolders not in :data:`SUBFOLDER_STATUS` are skipped with a warning.
    """
    if not staging_root.exists():
        logger.info("Staging area does not exist: %s", staging_root)
        return
    for child in sorted(staging_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        status = SUBFOLDER_STATUS.get(child.name)
        if status is None:
            logger.warning(
                "Unknown subfolder %s in staging area; skipping (rename to one of: %s)",
                child.name, ", ".join(sorted(SUBFOLDER_STATUS)),
            )
            continue
        for pdf in sorted(iter_pdfs(child)):
            if pdf.name.startswith("."):
                continue
            yield pdf, status


def _move_to_trash(
    source: Path,
    library_root: Path,
    *,
    subfolder: str,
    dry_run: bool = False,
) -> Path:
    """Move a successfully-sorted source PDF to ``.trash/sorted_originals/``.

    Returns the trash path the file was moved to (or would be moved to,
    in dry-run mode).
    """
    trash_dir = library_root / ".trash" / "sorted_originals" / subfolder
    if not dry_run:
        trash_dir.mkdir(parents=True, exist_ok=True)
    target = trash_dir / source.name

    # Disambiguate name collisions in trash by appending a counter.
    # The cap is a safety net so a maliciously-pre-populated trash directory
    # can't lock us in an unbounded loop; in practice the counter will be
    # tiny (a paper rarely gets sorted more than once).
    if target.exists() and target.resolve() != source.resolve():
        MAX_DISAMBIG_ATTEMPTS = 10000
        for i in range(1, MAX_DISAMBIG_ATTEMPTS + 1):
            cand = trash_dir / f"{source.stem}.{i}{source.suffix}"
            if not cand.exists():
                target = cand
                break
        else:
            raise RuntimeError(
                f"Cannot find free name for {source.name} in {trash_dir} "
                f"after {MAX_DISAMBIG_ATTEMPTS} attempts"
            )

    if not dry_run:
        shutil.move(str(source), str(target))
    return target


def sort_one(
    pdf: Path,
    status: str,
    *,
    library_root: Path,
    dry_run: bool,
    undo_log=None,
    canonical_override: Optional[str] = None,
    topic: Optional[str] = None,
    auto_topic: bool = True,
) -> dict:
    """Ingest a single PDF, then move source to trash. Returns a result dict.

    ``canonical_override``: if supplied (e.g. by the cockpit UI when the
    user edited the proposed filename), use this exact name instead of
    re-computing the canonical filename from metadata. The override still
    goes through the same routing logic for choosing the destination
    folder, so the status hint and alpha-subdir behaviour are preserved.

    ``topic`` / ``auto_topic``: forwarded to ``ingest_paper``.  The
    cockpit passes the user's explicit topic choice with
    ``auto_topic=False`` so a deliberate "standard, no topic" choice
    isn't overridden by the auto-classifier.
    """
    from processing.ingest import ingest_paper
    from processing.identity import iter_pdfs  # noqa: F401

    result: dict = {
        "source": str(pdf),
        "subfolder": pdf.parent.name,
        "status_hint": status,
        "ok": False,
    }

    try:
        ingest_result = ingest_paper(
            pdf,
            library_root=library_root,
            status=status,
            dry_run=dry_run,
            undo_log=undo_log,
            canonical_override=canonical_override,
            topic=topic,
            auto_topic=auto_topic,
        )
    except Exception as exc:
        logger.exception("Ingest crashed for %s", pdf.name)
        result["error"] = f"ingest crashed: {exc}"
        return result

    result["filename"] = ingest_result.get("filename")
    result["destination"] = ingest_result.get("destination")
    result["actions"] = ingest_result.get("actions", [])
    # Carry the three-state verdict through. Without it the batch rows
    # say only ok/not-ok, and the cockpit cannot tell the owner whether
    # a paper was checked and passed or never checked at all.
    result["identification_state"] = ingest_result.get("identification_state")

    if not ingest_result.get("success"):
        result["error"] = ingest_result.get("error") or "ingest failed (no specific reason)"
        return result

    # QUALITY GATE: refuse to file if metadata extraction was clearly
    # broken. We use two independent signals (either alone is enough):
    #
    #   (a) The title fell back to the source stem. We know this because
    #       ingest_paper sets result["title_from_metadata"] = False when
    #       no title was found in PDF metadata / API / LLM. This catches
    #       the "PDF author=='SoWise' but title missing" case where a
    #       fake author was extracted but the title is junk.
    #
    #   (b) The canonical filename has no " - " separator AND equals the
    #       source stem + .pdf. Catches the "no author, no title" case
    #       where everything fell back.
    #
    # An already-canonical file ("Smith, J. - Already canonical.pdf") has
    # title_from_metadata == False BUT we deliberately accept it via the
    # source-stem check (the filing is a no-op rename + move).
    canonical = ingest_result.get("filename") or ""
    source_stem = pdf.stem
    title_was_extracted = ingest_result.get("title_from_metadata", True)
    canonical_has_author_separator = " - " in canonical
    canonical_equals_source = canonical == source_stem + ".pdf"
    canonical_is_already_clean = canonical_has_author_separator and canonical_equals_source

    if not canonical_is_already_clean:
        if not canonical_has_author_separator and canonical_equals_source:
            # Case (b): nothing was extracted at all
            result["error"] = (
                f"metadata extraction failed (canonical filename would be {canonical!r}); "
                "needs manual review — left in 12 - To be sorted/"
            )
            return result
        if not title_was_extracted:
            # Case (a): title fell back to stem, but a "fake" author may
            # have leaked in via PDF metadata (e.g. PDF software name).
            result["error"] = (
                f"title fell back to filename stem ({canonical!r}); "
                "needs manual review — left in 12 - To be sorted/"
            )
            return result

    # On success, move the source out of staging to recoverable trash.
    try:
        trash_path = _move_to_trash(
            pdf,
            library_root,
            subfolder=pdf.parent.name,
            dry_run=dry_run,
        )
        result["moved_source_to"] = str(trash_path)
        if undo_log is not None and not dry_run:
            undo_log.record_move(pdf, trash_path)
    except Exception as exc:
        logger.exception("Failed to trash source %s", pdf)
        result["error"] = f"ingest ok but trashing source failed: {exc}"
        return result

    result["ok"] = True
    return result


def bulk_sort(
    library_root: Path = LIBRARY_ROOT,
    *,
    only: Optional[str] = None,
    limit: Optional[int] = None,
    exclude: Optional[set] = None,
    dry_run: bool = False,
    verbose: bool = False,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """Walk ``12 - To be sorted/`` and sort everything it can.

    ``progress``, if given, is called as ``(index, total, filename)``
    before each paper.  The cockpit uses it to draw a real progress bar:
    metadata extraction alone is MEASURED at 0.20s/paper, so the 1,933-
    paper inbox is a >6-minute run.

    Returns a summary dict with ``processed``, ``filed``, ``failed``, plus
    a ``results`` list of per-file outcomes.
    """
    try:
        from organization.system import TO_BE_SORTED
    except ImportError:
        TO_BE_SORTED = "12 - To be sorted"
    from processing.undo_log import UndoLog

    staging_root = library_root / TO_BE_SORTED
    candidates = list(iter_pdfs_with_hint(staging_root))
    if only:
        candidates = [(p, s) for (p, s) in candidates if p.parent.name == only]
    if exclude:
        # Papers the owner explicitly set aside in the Sort Queue ("I'll
        # handle this one myself").  Without this the cockpit's batch
        # button files them by machine rules anyway, overriding the one
        # decision he had already recorded about them.
        candidates = [(p, s) for (p, s) in candidates if str(p) not in exclude]
    if limit is not None:
        candidates = candidates[:limit]

    if verbose:
        by_sub: dict = {}
        for _, s in candidates:
            by_sub[s] = by_sub.get(s, 0) + 1
        print(f"Found {len(candidates)} PDFs to sort:")
        for s, n in by_sub.items():
            print(f"  {s}: {n}")

    undo_log = None
    tx_id = None
    if not dry_run and candidates:
        undo_log = UndoLog()
        tx_id = undo_log.begin_transaction(f"bulk_sort: {len(candidates)} papers")

    results: list[dict] = []
    filed = failed = 0
    t0 = time.time()

    # Crash-safety: one paper raising must never abort the batch and lose the
    # in-memory transaction — commit-or-discard ALWAYS runs in ``finally`` so
    # whatever was recorded stays reversible.
    try:
        for i, (pdf, status) in enumerate(candidates, 1):
            if progress is not None:
                try:
                    progress(i, len(candidates), pdf.name)
                except Exception:  # UI feedback must never break a batch
                    logger.debug("progress callback raised", exc_info=True)
            if verbose:
                print(f"  [{i}/{len(candidates)}] ({status}) {pdf.name[:60]}", end=" ", flush=True)
            try:
                r = sort_one(
                    pdf, status,
                    library_root=library_root, dry_run=dry_run, undo_log=undo_log,
                )
            except Exception as exc:  # never abort the whole batch
                r = {"ok": False, "file": str(pdf), "error": f"error: {exc}"}
            results.append(r)
            if r["ok"]:
                filed += 1
                if verbose:
                    dest = r.get("destination", "?")
                    try:
                        dest_short = str(Path(dest).relative_to(library_root))
                    except Exception:
                        dest_short = dest
                    print(f"→ {dest_short}")
            else:
                failed += 1
                if verbose:
                    print(f"FAILED: {r.get('error', '?')}")
    finally:
        if undo_log is not None:
            # Commit if ANY operation was recorded (so a paper that moved then
            # failed with filed==0 still leaves a reversible record); otherwise
            # drop the begun-but-empty transaction.
            if undo_log.has_operations():
                log_path = undo_log.commit()
                if verbose:
                    print(f"\nUndo log: {log_path}")
            else:
                undo_log.discard()

    summary = {
        "processed": len(candidates),
        "filed": filed,
        "failed": failed,
        "elapsed_seconds": round(time.time() - t0, 1),
        "transaction_id": tx_id,
        "results": results,
    }
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Sort PDFs from '12 - To be sorted/' into the main library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subfolder convention (drop your raw PDFs into one of these):

  12 - To be sorted/
    01 - Published papers/         → status=published
    02 - Unpublished papers/       → status=unpublished
    03 - Working papers/           → status=working
    05 - Books and lecture notes/  → status=book
    06 - Theses/                   → status=thesis

Sorted source PDFs are moved to {library}/.trash/sorted_originals/
where you can recover them if needed.
""",
    )
    parser.add_argument("--library", type=Path, default=LIBRARY_ROOT)
    parser.add_argument(
        "--only",
        help="Process only this subfolder name (e.g. '01 - Published papers')",
    )
    parser.add_argument("--limit", type=int, help="Stop after N papers")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only — never touches files")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="Don't prompt for confirmation before processing")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--report", type=Path,
                        help="Write JSON summary to this path")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.library.exists():
        print(f"Error: library not found: {args.library}", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run and not args.yes:
        # Tell the user exactly what will happen and ask permission
        try:
            from organization.system import TO_BE_SORTED
        except ImportError:
            TO_BE_SORTED = "12 - To be sorted"
        candidates = list(iter_pdfs_with_hint(args.library / TO_BE_SORTED))
        if args.only:
            candidates = [(p, s) for (p, s) in candidates if p.parent.name == args.only]
        if args.limit is not None:
            candidates = candidates[:args.limit]
        print(f"\nAbout to ingest and file {len(candidates)} PDFs into {args.library}.")
        print(f"Sources will be moved to {args.library}/.trash/sorted_originals/ on success.")
        ans = input("Proceed? [y/N] ").strip().lower()
        if ans != "y":
            print("Cancelled.")
            return

    summary = bulk_sort(
        args.library,
        only=args.only,
        limit=args.limit,
        dry_run=args.dry_run,
        verbose=True,
    )

    print(f"\n{'='*60}")
    print(f"  processed: {summary['processed']}")
    print(f"  filed:     {summary['filed']}")
    print(f"  failed:    {summary['failed']}")
    print(f"  elapsed:   {summary['elapsed_seconds']}s")
    if summary.get("transaction_id"):
        print(f"  undo with: python -m processing.undo_log undo --transaction {summary['transaction_id']}")

    if args.report:
        args.report.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
        print(f"\nFull report: {args.report}")


if __name__ == "__main__":
    main()
