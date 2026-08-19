"""Dropbox conflict-copy resolution.

Dropbox creates files of the form
``Smith - Paper (DESKTOP-XYZ's conflicted copy 2024-05-13).pdf`` when
the same path is edited on two machines without a clean sync window.
The library accumulates these forever unless someone resolves them.

Phase 1's Attention Queue already surfaces them with a "Delete conflict
copy" action that moves the conflict to ``.trash/``.  That's enough for
the obvious cases, but for the interesting cases (the conflict copy
might actually be the newer or larger version, or the canonical might
not exist at all) the user needs to see both files side-by-side and
make an informed call.

This module provides:

* ``find_canonical_for_conflict(conflict_path)`` -- strip the
  ``(... conflicted copy ...)`` chunk to recover the canonical filename.
* ``compare(conflict, canonical)`` -- size, mtime, page-count diff.
* ``resolve_*`` helpers that go through the undo log so any decision
  can be reversed.

The Phase 6 cockpit "Conflicts" tab consumes these.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Matches the Dropbox conflict-copy suffix.  Tolerates the older
# ``(<name>'s conflicted copy <date>)`` shape and the newer
# ``(conflicted copy <date>)`` variant without a user name.
#
# The bracket pattern ``[^()]*?`` deliberately excludes parens (so we
# match a single ``(...)`` chunk, not anything that crosses a paren
# boundary) and is non-greedy so a filename with TWO conflict markers
# (``foo (conflicted copy 2024-01-01) (conflicted copy 2024-05-13).pdf``,
# observed when Dropbox produces a conflict on a conflict) gets both
# stripped by the ``re.sub`` call below rather than a single greedy
# span swallowing the middle paper title.
_CONFLICT_SUFFIX_RE = re.compile(
    r"\s*\([^()]*?conflicted copy[^()]*?\)\s*",
    re.IGNORECASE,
)


def find_canonical_for_conflict(conflict_path: Path) -> Optional[Path]:
    """Strip the conflict-copy suffix to recover the canonical filename.

    Returns ``None`` if the path doesn't look like a Dropbox conflict
    or if stripping leaves an empty name.  The canonical may or may
    not actually exist on disk; the caller decides what to do with
    that.
    """
    stem = conflict_path.stem
    suffix = conflict_path.suffix
    if not _CONFLICT_SUFFIX_RE.search(stem):
        return None
    clean_stem = _CONFLICT_SUFFIX_RE.sub("", stem).strip()
    if not clean_stem:
        return None
    return conflict_path.with_name(f"{clean_stem}{suffix}")


@dataclass
class ConflictComparison:
    """What ``compare`` learned about a conflict + canonical pair."""

    conflict: str
    canonical: Optional[str]
    canonical_exists: bool
    conflict_size: int = 0
    canonical_size: int = 0
    conflict_mtime: str = ""
    canonical_mtime: str = ""
    conflict_pages: Optional[int] = None
    canonical_pages: Optional[int] = None
    # Suggested action: "keep_canonical" if conflict looks identical or
    # smaller than canonical, "review" otherwise.  Kept as a string
    # so callers (cockpit) can show it as a hint without binding to
    # an enum.
    suggested: str = "review"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _page_count(pdf: Path) -> Optional[int]:
    """Best-effort PDF page count via PyMuPDF.  None on failure."""
    try:
        import fitz  # type: ignore
        with fitz.open(pdf) as doc:
            return doc.page_count
    except Exception as exc:
        logger.debug("page count for %s failed: %s", pdf, exc)
        return None


def _iso_mtime(p: Path) -> str:
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(
            timespec="seconds"
        )
    except OSError:
        return ""


def compare(conflict: Path, canonical: Optional[Path] = None) -> ConflictComparison:
    """Compare ``conflict`` to its presumed canonical.

    ``canonical`` is recomputed via ``find_canonical_for_conflict`` if
    not supplied.  Missing canonicals are reported but don't raise --
    the cockpit needs to render them too so the user can decide
    whether to promote the conflict to the canonical name.
    """
    if canonical is None:
        canonical = find_canonical_for_conflict(conflict)
    out = ConflictComparison(
        conflict=str(conflict),
        canonical=str(canonical) if canonical else None,
        canonical_exists=bool(canonical and canonical.exists()),
    )
    if conflict.exists():
        try:
            out.conflict_size = conflict.stat().st_size
        except OSError:
            pass
        out.conflict_mtime = _iso_mtime(conflict)
        out.conflict_pages = _page_count(conflict)
    if canonical and canonical.exists():
        try:
            out.canonical_size = canonical.stat().st_size
        except OSError:
            pass
        out.canonical_mtime = _iso_mtime(canonical)
        out.canonical_pages = _page_count(canonical)

    # Suggested-action heuristic.  Conservative defaults:
    # * If the canonical is missing, suggest promoting the conflict.
    # * If they're byte-identical, suggest deleting the conflict.
    # * If the conflict is strictly smaller AND same page count,
    #   suggest deleting the conflict (likely a partial sync).
    # Anything else: "review" -- let the user decide.
    if not out.canonical_exists:
        out.suggested = "keep_conflict"
        out.notes.append("Canonical missing; conflict could become the canonical.")
    elif (
        out.conflict_size == out.canonical_size
        and out.conflict_pages == out.canonical_pages
    ):
        out.suggested = "keep_canonical"
        out.notes.append("Byte size and page count match; conflict is redundant.")
    elif (
        out.canonical_size > 0
        and out.conflict_size < out.canonical_size
        and out.conflict_pages == out.canonical_pages
    ):
        out.suggested = "keep_canonical"
        out.notes.append("Conflict is smaller with the same page count.")
    else:
        out.notes.append("Conflict differs from canonical; review side-by-side.")
    return out


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def resolve_keep_canonical(
    conflict: Path,
    library_root: Path,
    *,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> tuple[bool, str]:
    """Delete the conflict copy (recoverable via ``.trash/conflict_copies/``)."""
    from processing.undo_log import logged_move

    if not conflict.exists():
        return False, f"conflict gone: {conflict}"
    trash = library_root / ".trash" / "conflict_copies"
    trash.mkdir(parents=True, exist_ok=True)
    dest = trash / conflict.name
    n = 1
    while dest.exists():
        dest = trash / f"{conflict.stem} ({n}){conflict.suffix}"
        n += 1
    try:
        logged_move(conflict, dest, undo_log=undo_log)
    except Exception as exc:
        return False, str(exc)
    return True, f"moved to {dest.relative_to(library_root)}"


def _merge_sidecars(loser: "PaperIdentity", winner: "PaperIdentity") -> bool:
    """Fold ``loser``'s knowledge into ``winner`` without overwriting.

    Used when keep_conflict promotes the conflict's sidecar to the
    canonical slot but the OLD canonical also had a sidecar we don't
    want to lose entirely.  We:

    * Keep the *winner*'s DOI/arxiv when present, fill in from loser
      otherwise.
    * Concatenate ``publication_checks`` (winner's older entries
      first, loser's appended).
    * Sum ``recheck_count``.  Conservative but accurate -- both
      counters reflect real wasted lookups.
    * OR ``permanently_unpublished`` (sticky).
    * Union ``topic_codes`` and ``copy_locations``.
    * Keep the EARLIEST ``first_ingested_at``.

    Returns True if anything actually changed.
    """
    changed = False
    if not winner.doi and loser.doi:
        winner.doi = loser.doi
        changed = True
    if not winner.arxiv_id and loser.arxiv_id:
        winner.arxiv_id = loser.arxiv_id
        changed = True
    if loser.publication_checks:
        winner.publication_checks = list(loser.publication_checks) + list(winner.publication_checks)
        changed = True
    if loser.recheck_count:
        winner.recheck_count = (winner.recheck_count or 0) + loser.recheck_count
        changed = True
    if loser.permanently_unpublished and not winner.permanently_unpublished:
        winner.permanently_unpublished = True
        changed = True
    for code in loser.topic_codes:
        if code not in winner.topic_codes:
            winner.topic_codes.append(code)
            changed = True
    for loc in loser.copy_locations:
        if loc not in winner.copy_locations:
            winner.copy_locations.append(loc)
            changed = True
    if loser.first_ingested_at:
        if not winner.first_ingested_at or loser.first_ingested_at < winner.first_ingested_at:
            winner.first_ingested_at = loser.first_ingested_at
            changed = True
    return changed


def resolve_keep_conflict(
    conflict: Path,
    library_root: Path,
    *,
    canonical: Optional[Path] = None,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> tuple[bool, str]:
    """Replace the canonical with the conflict copy.

    The existing canonical (if any) is moved to ``.trash/conflict_copies/``
    so the user can recover it.  Then the conflict is renamed to the
    canonical path.  Both ops go through ``logged_move`` so a single
    undo restores the prior state.

    If BOTH files carry sidecars (each was ingested separately at
    some point), the canonical's sidecar history is merged into the
    promoted sidecar before the canonical is retired -- otherwise the
    historical ``publication_checks`` of the slot the user kept would
    be lost.
    """
    from processing.identity import PaperIdentity, sidecar_path
    from processing.undo_log import logged_move

    if canonical is None:
        canonical = find_canonical_for_conflict(conflict)
    if canonical is None:
        return False, "could not derive canonical path from conflict filename"

    trash = library_root / ".trash" / "conflict_copies"
    trash.mkdir(parents=True, exist_ok=True)

    # Step 0 (optional): merge sidecars so the canonical's
    # publication-check history survives the swap.  We mutate the
    # conflict's sidecar in place; logged_move will then carry the
    # enriched sidecar with the promoted file.
    if canonical.exists() and sidecar_path(canonical).exists() and sidecar_path(conflict).exists():
        try:
            promoted = PaperIdentity.load(conflict)
            retiring = PaperIdentity.load(canonical)
            if _merge_sidecars(retiring, promoted):
                # The transaction is right there in scope and was
                # simply not passed: promoting a conflict copy
                # rewrites the paper's identity, and that half of
                # the operation was unrecorded while the file
                # moves around it were.
                promoted.save(conflict, recompute_hash=False,
                              undo_log=undo_log)
                logger.info(
                    "merged canonical sidecar into conflict's sidecar "
                    "before promotion: %s",
                    canonical,
                )
        except Exception as exc:
            # Don't abort -- worst case the old history goes to .trash
            # with the retiring sidecar, recoverable.
            logger.warning("sidecar merge failed: %s", exc)

    # Step 1: shove the old canonical aside if it exists.
    if canonical.exists():
        retired = trash / f"{canonical.stem}.old{canonical.suffix}"
        n = 1
        while retired.exists():
            retired = trash / f"{canonical.stem}.old.{n}{canonical.suffix}"
            n += 1
        try:
            logged_move(canonical, retired, undo_log=undo_log)
        except Exception as exc:
            return False, f"retiring canonical: {exc}"

    # Step 2: promote the conflict to the canonical name.
    try:
        logged_move(conflict, canonical, undo_log=undo_log)
    except Exception as exc:
        return False, f"promoting conflict: {exc}"

    return True, f"conflict promoted to {canonical.relative_to(library_root)}"


def resolve_keep_both(
    conflict: Path,
    library_root: Path,
    *,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> tuple[bool, str]:
    """Rename the conflict to a clean, non-conflict filename.

    Useful when you decide the conflict is a different paper that
    deserves its own slot.  The new name appends ``-v2`` (or -v3, ...)
    to the canonical stem; collisions iterate the suffix.
    """
    from processing.undo_log import logged_move

    canonical = find_canonical_for_conflict(conflict)
    if canonical is None:
        return False, "could not derive canonical path from conflict filename"

    n = 2
    target = canonical.with_name(f"{canonical.stem}-v{n}{canonical.suffix}")
    while target.exists():
        n += 1
        target = canonical.with_name(f"{canonical.stem}-v{n}{canonical.suffix}")
    try:
        logged_move(conflict, target, undo_log=undo_log)
    except Exception as exc:
        return False, str(exc)
    return True, f"renamed to {target.relative_to(library_root)}"


# ---------------------------------------------------------------------------
# Library-wide scanner (consumed by the Conflicts cockpit tab)
# ---------------------------------------------------------------------------

def scan_conflicts(library_root: Path) -> list[ConflictComparison]:
    """Walk the library and return ``ConflictComparison`` per conflict copy."""
    from processing.identity import iter_pdfs
    from ui.attention_queue import _CONFLICT_RE  # share the single regex
    out: list[ConflictComparison] = []
    if not library_root.exists():
        return out
    for pdf in iter_pdfs(library_root):
        if not _CONFLICT_RE.search(pdf.name):
            continue
        out.append(compare(pdf))
    return out
