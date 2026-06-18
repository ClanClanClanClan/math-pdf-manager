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
) -> dict:
    """Populate ``classifier_text`` on sidecars across the library.

    Resumable (skips papers that already have text unless ``overwrite``),
    and guarded by a dedicated ``classifier-backfill`` lock so two
    backfills can't run at once.  It deliberately does NOT take the
    global library write lock: that would stall the watcher for the whole
    (long) run, and this only writes one sidecar field via the atomic
    sidecar writer.

    ``max_seconds`` makes the run self-bounded: it stops gracefully after
    the current paper once the budget is exceeded and sets
    ``stats["stopped_early"]``.  This keeps each invocation comfortably
    under any harness/cron timeout — drive it to completion by calling
    repeatedly (it resumes where it left off).  Returns a stats dict.
    """
    import time as _time
    from processing.identity import iter_pdfs, PaperIdentity
    from processing.pipeline_preview import is_routable
    from processing.locking import LibraryLock

    stats = {"scanned": 0, "extracted": 0, "skipped": 0, "empty": 0,
             "failed": 0}

    lock = LibraryLock(library_root, name="classifier-backfill")
    if not lock.acquire(blocking=False):
        stats["skipped_locked"] = True
        return stats

    start = _time.time()
    try:
        root = scope or library_root
        filter_routable = scope is None
        for pdf in iter_pdfs(root):
            if filter_routable and not is_routable(pdf, library_root):
                continue
            if limit is not None and stats["scanned"] >= limit:
                break
            if max_seconds is not None and (_time.time() - start) >= max_seconds:
                stats["stopped_early"] = True
                break
            stats["scanned"] += 1

            ident = PaperIdentity.load(pdf)
            if (ident.classifier_text or ident.classifier_text_tried) and not overwrite:
                stats["skipped"] += 1
                continue

            # Extract OUTSIDE any sidecar hold (the slow part).
            text = extract_classifier_text(pdf, max_pages=max_pages,
                                           max_chars=max_chars)

            # Re-load fresh right before saving to minimise the window in
            # which a concurrent topic edit could be lost, then persist
            # only the new field(s) via the atomic writer.  Mark
            # ``classifier_text_tried`` either way so an un-extractable
            # (image-only) PDF isn't retried on every future run.
            ident = PaperIdentity.load(pdf)
            ident.classifier_text_tried = True
            if text:
                ident.classifier_text = text
            try:
                ident.save(pdf, recompute_hash=False)
                stats["extracted" if text else "empty"] += 1
            except Exception as exc:  # pragma: no cover -- defensive
                logger.warning("save failed for %s: %s", pdf, exc)
                stats["failed"] += 1
    finally:
        lock.release()

    return stats


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
    print(stats)


if __name__ == "__main__":
    main()
