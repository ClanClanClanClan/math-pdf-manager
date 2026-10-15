#!/usr/bin/env python3
"""Cache each paper's abstract / first-pages text for the classifier.

Why (proven, not a hunch): ~98% of topic recall-misses have no topic
keyword in the *filename*, but the topic IS named in the abstract.  A
sample experiment flipped 75% of recall-misses to confident-correct just
by feeding the abstract, lifting recall ~63%->~91% at unchanged
precision — because it's *more real evidence*, not keyword overfitting.

This module extracts the first few pages of text once and stores it in
the sidecar (``PaperIdentity.classifier_text``) so the classifier can
read content without re-parsing the PDF on every run.  Extraction is the
slow part; it happens once per paper (resumable).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Defaults chosen to capture the abstract + start of the introduction
# while bounding sidecar growth (a few KB/paper).
DEFAULT_MAX_PAGES = 3
DEFAULT_MAX_CHARS = 4000


def extract_classifier_text(
    pdf_path: Path,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """Return whitespace-collapsed text from the first ``max_pages`` pages
    of a PDF, capped at ``max_chars``.  Empty string on any failure
    (encrypted, corrupt, cloud-only placeholder, no text layer)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:  # pragma: no cover
        logger.warning("PyMuPDF unavailable; cannot extract classifier text")
        return ""
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        logger.debug("open failed for %s: %s", pdf_path, exc)
        return ""
    try:
        parts = []
        for i in range(min(max_pages, doc.page_count)):
            try:
                parts.append(doc[i].get_text())
            except Exception:
                continue
    finally:
        doc.close()
    text = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return text[:max_chars]


def backfill_classifier_text(
    library_root: Path,
    *,
    scope: Optional[Path] = None,
    limit: Optional[int] = None,
    overwrite: bool = False,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_seconds: Optional[float] = None,
    undo_log=None,
) -> dict:
    """Populate ``classifier_text`` on sidecars across the library.

    ``limit`` is how many papers to READ: papers that still need their
    text. Those that already have it (or were tried) are passed over and
    do not count. The batch used to count every paper it looked at, so on
    the real library (measured 2026-10-15) "100" read 3 papers, "500" 4
    and "2000" 6 of the 758 waiting -- only "All" reached them. Once the
    batch is full the walk goes on without reading, to count
    ``still_waiting``: what the next press would read.

    Resumable (skips papers that already have text unless ``overwrite``),
    and guarded by a dedicated ``classifier-backfill`` lock so two
    backfills can't run at once.  It deliberately does NOT take the
    global library write lock: that would stall the watcher for the whole
    (long) run, and this only writes one sidecar field via the atomic
    sidecar writer.

    ``max_seconds`` makes the run self-bounded: it stops gracefully after
    the current paper once the budget is exceeded and sets
    ``stats["stopped_early"]`` (``still_waiting`` is then ``None``: not
    counted).  This keeps each invocation comfortably under any
    harness/cron timeout — drive it to completion by calling repeatedly
    (it resumes where it left off).

    ``undo_log`` (an open transaction) makes the run undoable from
    Activity. An existing record gains its two fields and nothing else
    (``patch_record``, previous values recorded before the write) -- the
    whole-record ``save`` used here rewrote every field a record predated,
    so no undo could have given the record back. A paper with no record
    gets a whole one, as "Fill in missing details" makes it
    (``backfill_sidecar``: fingerprint, filing date, name, and the text),
    logged as made. It used to get the text alone, and was then passed
    over by "Fill in missing details" for good (147 such records in the
    library, measured 2026-10-15). A record-less paper whose contents
    match a record a rename left behind is neither read nor given one
    (``kept_for_reconnect``): the reconnect needs the spot free.

    Returns ``stats``: ``scanned`` papers looked at; ``skipped`` already
    done; ``read`` (at most ``limit``) of which ``extracted`` stored text,
    ``empty`` found none, ``failed`` could not be saved, and
    ``records_made`` had no record; ``kept_for_reconnect``; ``unreadable``
    -- a record that cannot be read, neither read nor written over;
    ``still_waiting``; and ``unreadable_papers`` / ``failed_papers``, the
    names of those two kinds.
    """
    import time as _time
    from processing.identity import (backfill_sidecar, find_sidecar,
                                     iter_pdfs, PaperIdentity, patch_record)
    from processing.pipeline_preview import is_routable
    from processing.locking import LibraryLock
    from processing.sidecar_repair import stranded_fingerprints, stranded_match

    stats = {"scanned": 0, "skipped": 0, "read": 0, "extracted": 0,
             "empty": 0, "failed": 0, "records_made": 0,
             "kept_for_reconnect": 0, "unreadable": 0, "still_waiting": 0,
             "unreadable_papers": [], "failed_papers": []}

    lock = LibraryLock(library_root, name="classifier-backfill")
    if not lock.acquire(blocking=False):
        stats["skipped_locked"] = True
        stats["still_waiting"] = None
        return stats

    start = _time.time()
    stranded = None                    # asked of the library when first needed
    try:
        root = scope or library_root
        filter_routable = scope is None
        from processing.library_scope import why_not_proposable
        for pdf in iter_pdfs(root):
            if why_not_proposable(library_root, pdf) is not None:
                stats["left_alone"] = stats.get("left_alone", 0) + 1
                continue
            if filter_routable and not is_routable(pdf, library_root):
                continue
            if max_seconds is not None and (_time.time() - start) >= max_seconds:
                stats["stopped_early"] = True
                stats["still_waiting"] = None
                break
            stats["scanned"] += 1

            ident = PaperIdentity.load(pdf)
            if (ident.classifier_text or ident.classifier_text_tried) and not overwrite:
                stats["skipped"] += 1
                continue
            # Asked of the disk, not of ``is_new()`` alone: an UNREADABLE
            # record also loads as new, and saving a fresh one there wrote
            # blanks over whatever it held. Now it is left alone -- and not
            # read, so a run of them cannot fill every batch for ever.
            has_record = find_sidecar(pdf) is not None
            if has_record and ident.is_new():
                stats["unreadable"] += 1
                stats["unreadable_papers"].append(pdf.name)
                continue
            digest = ""
            if not has_record:
                if stranded is None:
                    stranded = stranded_fingerprints(library_root)
                waits, digest = stranded_match(pdf, stranded)
                if waits:
                    stats["kept_for_reconnect"] += 1
                    continue
            if limit is not None and stats["read"] >= limit:
                stats["still_waiting"] += 1
                continue
            stats["read"] += 1

            # Extract OUTSIDE any sidecar hold (the slow part).
            text = extract_classifier_text(pdf, max_pages=max_pages,
                                           max_chars=max_chars)

            # Persist only the new field(s), into the record as it is NOW:
            # patch_record re-reads it, so a concurrent topic edit is not
            # lost.  Mark ``classifier_text_tried`` either way so an
            # un-extractable (image-only) PDF isn't retried on every
            # future run.
            values = {"classifier_text_tried": True}
            if text:
                values["classifier_text"] = text
            try:
                # A record made while the text was being read is patched,
                # not passed over: backfill_sidecar never writes over one.
                if not has_record and backfill_sidecar(
                        pdf, content_hash=digest, extra=values,
                        undo_log=undo_log):
                    stats["records_made"] += 1
                elif patch_record(pdf, values, undo_log=undo_log) is None:
                    raise OSError("its record could not be read")
                stats["extracted" if text else "empty"] += 1
            except Exception as exc:
                logger.warning("save failed for %s: %s", pdf, exc)
                stats["failed"] += 1
                stats["failed_papers"].append(pdf.name)
    finally:
        lock.release()

    return stats


def _papers(n: int) -> str:
    return f"{n:,} paper" + ("" if n == 1 else "s")


def describe_run(stats: dict) -> list[tuple[str, str]]:
    """What a run of :func:`backfill_classifier_text` did, in words:
    ``[(kind, sentence)]``, kind one of ``success``/``info``/``warning``.

    The page printed the stats dict itself ("Cached: {'scanned': 3, ...}").
    """
    if stats.get("skipped_locked"):
        return [("warning", "Another run is already reading the abstracts, so "
                            "this one did nothing. Press again once it has "
                            "finished.")]
    out = []
    read = stats.get("read", 0)
    if read:
        stored = stats.get("extracted", 0)
        said = (f"Read {_papers(read)}: {stored:,} now "
                + ("has its" if stored == 1 else "have their") + " text stored")
        if stats.get("empty"):
            said += (f", {stats['empty']:,} had no text to read (scanned "
                     f"pages, most likely) and will not be tried again")
        said += "."
        if stats.get("records_made"):
            said += (f" {stats['records_made']:,} of them had no saved "
                     f"details; each now has them — its fingerprint, filing "
                     f"date and the text.")
        out.append(("success", said))
    if stats.get("failed"):
        out.append(("warning",
                    f"Could not save the text of {_papers(stats['failed'])}; "
                    f"the next press tries again: "
                    + ", ".join(stats.get("failed_papers", [])[:10])))
    if stats.get("unreadable"):
        out.append(("warning",
                    f"Left {_papers(stats['unreadable'])} unread and "
                    f"untouched: the saved details could not be read (a "
                    f"half-synced file, perhaps): "
                    + ", ".join(stats.get("unreadable_papers", [])[:10])))
    if stats.get("kept_for_reconnect"):
        out.append(("info",
                    f"Left {_papers(stats['kept_for_reconnect'])} unread: "
                    f"each has an older record, left behind by a rename, "
                    f"that still holds its details. Put those back from the "
                    f"**Conformance** page (Find the papers these records "
                    f"belong to); the next press reads them."))
    waiting = stats.get("still_waiting")
    held = sum(stats.get(k, 0) for k in ("failed", "unreadable",
                                          "kept_for_reconnect"))
    if stats.get("stopped_early"):
        out.append(("info", "Stopped at the time limit. Press again to carry "
                            "on where it left off."))
    elif waiting:
        out.append(("info", f"{_papers(waiting)} still to read. Press again "
                            f"to read the next batch."))
    elif held:
        out.append(("info", "No other paper is waiting."))
    elif read:
        out.append(("success", "That was the last of them: every paper has "
                               "now had its first pages read."))
    else:
        out.append(("success", "Nothing to read: every paper has already had "
                               "its first pages read."))
    return out


# ---------------------------------------------------------------------------
# CLI: run the (long) backfill headless
# ---------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> None:
    import argparse
    from core.config_paths import get_library_root

    parser = argparse.ArgumentParser(
        description="Cache abstract/first-pages text into sidecars for the "
                    "topic classifier")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--scope", default=None,
                        help="Restrict to a subfolder (relative to library root)")
    parser.add_argument("--max-seconds", type=float, default=None,
                        help="Stop gracefully after this many seconds (resume "
                             "by re-running)")
    args = parser.parse_args(argv)

    root = get_library_root()
    scope = (root / args.scope) if args.scope else None
    stats = backfill_classifier_text(
        root, scope=scope, limit=args.limit, overwrite=args.overwrite,
        max_pages=args.max_pages, max_chars=args.max_chars,
        max_seconds=args.max_seconds,
    )
    for _kind, sentence in describe_run(stats):
        print(sentence)


if __name__ == "__main__":
    main()
