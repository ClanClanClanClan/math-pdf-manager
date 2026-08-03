"""Retroactive, review-gated normalization of the EXISTING library.

Naming is canonicalised automatically at ingest and on every move
(``move_normalizer`` / ``file_into_topic``): author initials get spaced
("R.C."→"R. C.") and the title gets safe-default sentence casing.  But
that only ever touched papers as they *arrived* or *moved* — the tens of
thousands already sitting in the library keep whatever formatting they
were filed with years ago.

This module brings the back-catalogue up to the same standard, as a
**dry-run-first, reversible, gated** batch (never automatic):

  * ``scan`` walks every PDF, computes its canonical name via
    ``move_normalizer.normalize_full_name`` and returns the proposed
    renames — split by WHAT changed so the owner can trust the mechanical
    author-spacing bucket and review the title-casing bucket separately —
    plus the uncertain title words the walk surfaced.  Read-only.
  * ``apply_renames`` renames a chosen subset in ONE undo transaction
    (``logged_rename`` carries each sidecar and is fully reversible),
    skips any name collision rather than clobbering, and queues the
    uncertain words for the vocabulary review.

Only *meaningful* textual changes are proposed: a rename whose sole
difference is Unicode NFD↔NFC (invisible to the eye and treacherous on a
case-/normalization-folding filesystem) is deliberately skipped.

Renames are in-place (same directory): author-initial spacing and title
casing never change the surname, so a paper's A–Z / topic location is
unaffected.  The library has no hardlink copies (every PDF is a primary),
so an in-place ``logged_rename`` is safe; were a copy ever to exist,
``logged_rename`` already cascades to it.
"""
from __future__ import annotations

import logging
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# Change categories.
# macOS/APFS and ext4 both cap a single path COMPONENT at 255 bytes.
# Canonical names are long (every author spelled out), so this is a real
# boundary, not a theoretical one.
_MAX_FILENAME_BYTES = 255

try:                                        # pragma: no cover - trivial
    from organization.system import TO_BE_SORTED as _STAGING_DIR
except ImportError:                         # pragma: no cover
    _STAGING_DIR = "12 - To be sorted"

AUTHOR = "author"   # only the author block changed (initial spacing, cosmetic)
TITLE = "title"     # only the title changed (safe-default sentence casing)
BOTH = "both"       # both sides changed


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _split(name: str) -> tuple[str, str]:
    """Split ``"Authors - Title.pdf"`` into (author_part, remainder)."""
    if " - " in name:
        a, _, rest = name.partition(" - ")
        return a, rest
    return "", name


def _classify(old_name: str, new_name: str) -> str:
    """Which side changed, comparing NFC-folded author/title parts."""
    a_old, t_old = _split(_nfc(old_name))
    a_new, t_new = _split(_nfc(new_name))
    author_changed = a_old != a_new
    title_changed = t_old != t_new
    if author_changed and title_changed:
        return BOTH
    if author_changed:
        return AUTHOR
    return TITLE


def propose_renames(
    library_root: Path, *, limit: Optional[int] = None, progress=None
) -> tuple[list[dict], set[str]]:
    """Walk the library; return ``(proposals, pending_words)``.

    ``proposals`` — one dict per file whose canonical name differs
    meaningfully from its current name::

        {"old": <rel>, "new": <rel>, "name": <new basename>,
         "old_name": <cur basename>, "kind": author|title|both}

    ``pending_words`` — uncertain title words the caser could not settle,
    for the vocabulary review.  Read-only; touches nothing on disk.
    """
    from processing.identity import iter_pdfs
    from processing.move_normalizer import normalize_full_name

    proposals: list[dict] = []
    pending: set[str] = set()
    n = 0
    # A progress bar needs a denominator; materialising the file list
    # costs ~5s against an ~85s scan.  Without a callback (CLI, tests)
    # we stream exactly as before.
    if progress is not None and limit is None:
        pdfs = list(iter_pdfs(library_root))
        total = len(pdfs)
    else:
        pdfs = iter_pdfs(library_root)
        total = limit or 0
    for pdf in pdfs:
        if limit is not None and n >= limit:
            break
        # The inbox is not part of the library yet.  Those papers still
        # carry whatever the publisher or arXiv called them and get their
        # canonical name when they are FILED, so proposing renames for
        # them is noise in a review of the existing library.
        if _STAGING_DIR in pdf.parts:
            continue
        n += 1
        if progress is not None:
            try:
                progress(n, total, pdf.name)
            except Exception:  # progress reporting must never abort a scan
                logger.debug("progress callback raised", exc_info=True)
        try:
            new_name, changed, pend = normalize_full_name(pdf.name, library_root)
        except Exception as exc:  # never let one bad name abort the scan
            logger.debug("normalize failed for %r: %s", pdf.name, exc)
            continue
        if pend:
            pending.update(pend)
        if not changed or new_name == pdf.name:
            continue
        # Skip renames that differ only by Unicode normalization form:
        # invisible to the reader and unsafe on a normalization-folding
        # filesystem (the target "already exists" as the same inode).
        if _nfc(pdf.name) == _nfc(new_name):
            continue
        try:
            rel = str(pdf.relative_to(library_root))
            new_rel = str((pdf.parent / new_name).relative_to(library_root))
        except ValueError:  # pragma: no cover — pdf always under root
            continue
        proposals.append({
            "old": rel,
            "new": new_rel,
            "name": new_name,
            "old_name": pdf.name,
            "kind": _classify(pdf.name, new_name),
        })
    return proposals, pending


def scan(library_root: Path, *, limit: Optional[int] = None, progress=None) -> dict:
    """Read-only summary for the cockpit dry-run.

    Returns counts by change-kind, the uncertain-word count, and the full
    proposal list (so the UI can page/preview and later apply a subset).

    ``progress`` is forwarded to :func:`propose_renames`; the sweep is
    MEASURED at ~85s over 29,393 names, which needs a visible bar.
    """
    proposals, pending = propose_renames(library_root, limit=limit,
                                         progress=progress)
    by_kind = {AUTHOR: 0, TITLE: 0, BOTH: 0}
    for p in proposals:
        by_kind[p["kind"]] = by_kind.get(p["kind"], 0) + 1
    return {
        "total": len(proposals),
        "by_kind": by_kind,
        "pending_words": sorted(pending),
        "proposals": proposals,
    }


def apply_renames(
    library_root: Path,
    proposals: Iterable[dict],
    *,
    dry_run: bool = True,
    pending_words: Optional[Iterable[str]] = None,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> dict:
    """Rename the given ``proposals`` in one reversible transaction.

    ``proposals`` is the exact subset the owner chose to apply (each item
    as produced by :func:`propose_renames`).  Collisions and vanished
    sources are skipped and reported, never forced.  ``pending_words``, if
    given, are queued for the vocabulary review.  With ``dry_run`` (the
    default) nothing is written — it just echoes what would happen.
    """
    items = [p for p in proposals if p.get("old") and p.get("new")]

    if dry_run:
        return {
            "dry_run": True,
            "would_rename": len(items),
            "sample": items[:50],
        }

    from processing.undo_log import UndoLog, logged_rename

    own = undo_log is None
    log = undo_log or UndoLog(log_dir=library_root / ".operation_log")
    tx_id = None
    if own:
        tx_id = log.begin_transaction(
            f"normalize existing filenames: {len(items)} file(s)"
        )

    renamed = 0
    skipped: list[dict] = []
    try:
        for p in items:
            old = library_root / p["old"]
            new = library_root / p["new"]
            # A canonical name can exceed the filesystem's per-component
            # limit: spacing out the initials of a 13-author paper pushed
            # one past macOS's 255 BYTES.  Check before touching the disk,
            # because Path.exists() RAISES ENAMETOOLONG rather than
            # returning False — which aborted a 6,186-file batch partway.
            if len(new.name.encode("utf-8")) > _MAX_FILENAME_BYTES:
                skipped.append({"old": p["old"], "reason": "name too long"})
                continue
            try:
                if not old.exists():
                    skipped.append({"old": p["old"], "reason": "source gone"})
                    continue
                if new.exists() and _nfc(str(new)) != _nfc(str(old)):
                    # macOS/APFS is case-INSENSITIVE: for a rename that only
                    # changes capitalisation ("space–time" -> "Space–time")
                    # the "existing target" IS the source file, so a string
                    # comparison called every such rename a collision and
                    # refused it — 771 of them in one batch, silently
                    # reported as "target exists".  Ask the filesystem
                    # whether it is really a different file.
                    same = False
                    try:
                        same = old.samefile(new)
                    except OSError:
                        same = False
                    if not same:
                        skipped.append({"old": p["old"], "reason": "target exists"})
                        continue
            except OSError as exc:      # unreadable path, ENAMETOOLONG, …
                skipped.append({"old": p["old"], "reason": f"unusable path: {exc}"})
                continue
            try:
                logged_rename(old, new, undo_log=log)
                renamed += 1
            except FileExistsError:
                skipped.append({"old": p["old"], "reason": "target exists"})
            except Exception as exc:
                logger.warning("rename failed for %s: %s", p["old"], exc)
                skipped.append({"old": p["old"], "reason": str(exc)})
    finally:
        if own:
            if log.has_operations():
                log.commit()
            else:
                log.discard()
                tx_id = None

    # Queue uncertain words (best-effort; never fails the batch).
    if pending_words:
        try:
            from processing.title_vocab import record_pending
            record_pending(
                library_root, list(pending_words),
                example="existing-library normalization",
            )
        except Exception:  # pragma: no cover
            logger.debug("could not queue pending words", exc_info=True)

    return {
        "dry_run": False,
        "renamed": renamed,
        "skipped": skipped,
        "tx_id": tx_id,
    }
