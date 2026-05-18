"""Topic router — hardlink filed PDFs into 07a-07f topic folders.

The user's library has a per-topic taxonomy (``07a - BSDEs``, ``07b -
2BSDEs``, ...) for cross-cutting access.  Until Phase 4 the cockpit
showed *suggested* topics in the Sort Queue preview but never created
the topic copies; users had to file them manually.  This module
closes that gap.

Mechanics
---------
The "topic copy" is implemented as a POSIX hard link
(``os.link``) when source and destination share an inode (i.e. live
on the same filesystem).  Hard links cost zero extra storage --
both paths point to the same inode -- and stay in sync when the
underlying file is edited.  When linking across volumes fails
(``OSError: Cross-device link``), we fall back to ``shutil.copy2``
and accept the storage cost.

Every link is recorded as a ``copy`` op in the undo log, so a single
``undo`` call deletes the hardlink without touching the original.
The sidecar's ``copy_locations`` is updated to remember where the
copies live, and ``topic_codes`` records which topics linked.

Safety
------
* Never overwrites an existing file at the topic destination -- a
  collision aborts THAT topic but leaves the rest of the routing
  intact.
* Topic folder names are auto-discovered by ``07x - `` prefix; a
  missing topic folder skips silently rather than creating it.
* All routing is opt-in: callers must explicitly invoke
  ``classify_and_link``.  Watcher ingest does NOT auto-link.
* Hardlinks behave correctly under Dropbox sync (Dropbox sees them
  as independent files, so cloud cost doubles -- local storage is
  what's optimised here).
"""
from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default scoring thresholds.  ``score`` here is the keyword classifier's
# weighted hit count, NOT a probability.  Anything that clears
# ``suggest_threshold`` shows up in the cockpit; ``auto_threshold`` is
# what the cockpit pre-checks for the user.
DEFAULT_SUGGEST_THRESHOLD = 1.0
DEFAULT_AUTO_THRESHOLD = 2.0


@dataclass
class TopicRoutingResult:
    """What ``classify_and_link`` did and would have done."""

    suggested: list[dict] = field(default_factory=list)  # full classifier output
    linked: list[str] = field(default_factory=list)      # absolute paths created
    skipped: list[str] = field(default_factory=list)     # reasons (path -> reason str)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "suggested": list(self.suggested),
            "linked": list(self.linked),
            "skipped": list(self.skipped),
            "errors": list(self.errors),
        }


def find_topic_folder(library_root: Path, topic_code: str) -> Optional[Path]:
    """Find the ``07x - …`` folder matching ``topic_code``.

    Case-insensitive match on the prefix.  Returns ``None`` if no
    matching folder exists (a missing topic folder is not an error --
    the user may have removed it).
    """
    needle = topic_code.lower().strip() + " "
    if not library_root.exists():
        return None
    for child in library_root.iterdir():
        if not child.is_dir():
            continue
        if child.name.lower().startswith(needle):
            return child
    return None


def _create_link(source: Path, destination: Path) -> str:
    """Create a hardlink, falling back to copy on cross-device errors.

    Returns the verb used ("hardlink" or "copy") for logging.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError as exc:
        # ``EXDEV`` (cross-device) and ``EPERM`` (filesystem refuses
        # hardlinks, e.g. some network mounts) both fall back to copy.
        logger.info(
            "hardlink failed (%s); falling back to copy: %s -> %s",
            exc, source, destination,
        )
        shutil.copy2(source, destination)
        return "copy"


def classify_and_link(
    canonical_pdf: Path,
    library_root: Path,
    *,
    title: str = "",
    text: str = "",
    only_codes: Optional[list[str]] = None,
    suggest_threshold: float = DEFAULT_SUGGEST_THRESHOLD,
    auto_threshold: float = DEFAULT_AUTO_THRESHOLD,
    undo_log=None,  # type: ignore[no-untyped-def]
    dry_run: bool = False,
) -> TopicRoutingResult:
    """Classify ``canonical_pdf`` and link it into matching topic folders.

    Parameters
    ----------
    canonical_pdf
        The already-filed primary PDF (e.g. ``02/U/Foo - paper.pdf``).
        Links land at ``07x/Foo - paper.pdf``.
    library_root
        Library root containing the ``07x - …`` folders.
    title, text
        Inputs to ``processing.topic_classifier.classify_by_keywords``.
        Title alone is usually enough; pass the first-page snippet for
        higher recall.
    only_codes
        When non-empty, restricts linking to exactly these topic codes
        (the cockpit passes the user's explicit checkbox selection).
        When ``None``, links every topic whose score >= ``auto_threshold``
        and includes the others (>= ``suggest_threshold``) in
        ``suggested`` for the caller to surface.
    suggest_threshold, auto_threshold
        Lower bound for what to show in ``suggested`` and what to link
        automatically when ``only_codes`` is ``None``.
    undo_log
        Optional ``UndoLog`` instance.  Each created link is recorded
        as a ``copy`` op so undo deletes the link.
    dry_run
        When True, classifies and reports what WOULD be linked without
        touching the filesystem.

    Returns
    -------
    TopicRoutingResult
    """
    from processing.topic_classifier import classify_by_keywords
    from processing.identity import PaperIdentity, sidecar_path

    result = TopicRoutingResult()
    if not canonical_pdf.exists():
        result.errors.append(f"canonical PDF missing: {canonical_pdf}")
        return result

    suggested = classify_by_keywords(title, text)
    result.suggested = suggested
    # Early exit only when there's no classifier signal AND the user
    # didn't override -- explicit ``only_codes`` should always be
    # honoured even if the classifier returns nothing.
    if not suggested and not only_codes:
        return result

    if only_codes is not None:
        # Explicit user selection wins -- link exactly these codes
        # regardless of what the classifier thinks.  The user might
        # know the paper belongs in 07c even if the keyword classifier
        # missed the signal, and they're the one clicking the box.
        codes_to_link = list(dict.fromkeys(only_codes))  # dedupe, preserve order
    else:
        codes_to_link = [s["topic_code"] for s in suggested
                         if s["score"] >= auto_threshold]

    if not codes_to_link:
        return result

    # Load the sidecar once so we can append every new location in
    # one save at the end.
    identity = PaperIdentity.load(canonical_pdf)
    if identity.is_new():
        # Without an existing sidecar we still link the file -- the
        # links should not depend on identity bookkeeping.  But we
        # also can't update copy_locations, so log it.
        logger.info("no sidecar for %s -- linking but not tracking", canonical_pdf)

    primary_str = str(canonical_pdf)
    if not identity.is_new() and primary_str not in identity.copy_locations:
        identity.copy_locations.append(primary_str)

    for code in codes_to_link:
        folder = find_topic_folder(library_root, code)
        if folder is None:
            result.skipped.append(f"{code}: folder missing")
            continue
        dest = folder / canonical_pdf.name
        if dest.exists():
            # Collision -- skip rather than overwrite.  A stray copy
            # with the same name is almost certainly the same paper
            # already filed.
            result.skipped.append(f"{code}: destination exists at {dest}")
            continue

        if dry_run:
            result.linked.append(f"WOULD link to {dest}")
            continue

        try:
            if undo_log is not None:
                undo_log.record_copy(canonical_pdf, dest)
            verb = _create_link(canonical_pdf, dest)
            result.linked.append(str(dest))
            logger.info("topic link %s: %s -> %s", verb, canonical_pdf, dest)
            if not identity.is_new():
                if str(dest) not in identity.copy_locations:
                    identity.copy_locations.append(str(dest))
                if code not in identity.topic_codes:
                    identity.topic_codes.append(code)
        except Exception as exc:
            result.errors.append(f"{code}: {exc}")

    # Persist sidecar updates exactly once
    if not identity.is_new() and not dry_run and (result.linked or result.errors):
        try:
            identity.save(canonical_pdf, recompute_hash=False)
        except Exception as exc:
            result.errors.append(f"sidecar save failed: {exc}")

    return result


def unlink_topic(
    canonical_pdf: Path,
    library_root: Path,
    topic_code: str,
    *,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> bool:
    """Remove the topic copy of ``canonical_pdf`` from ``topic_code``'s folder.

    Returns True if a link was removed, False if it didn't exist.
    The deletion is recorded as a ``move`` (to /dev/null) in the undo
    log so the operation appears in the Activity tab -- but undo
    cannot resurrect a hardlink, only the canonical inode (which
    wasn't removed by this call) so it's logged as a soft action.
    """
    from processing.identity import PaperIdentity

    folder = find_topic_folder(library_root, topic_code)
    if folder is None:
        return False
    dest = folder / canonical_pdf.name
    if not dest.exists():
        return False
    dest.unlink()
    # Update sidecar bookkeeping
    identity = PaperIdentity.load(canonical_pdf)
    if not identity.is_new():
        identity.copy_locations = [
            loc for loc in identity.copy_locations if loc != str(dest)
        ]
        if topic_code in identity.topic_codes:
            identity.topic_codes = [
                c for c in identity.topic_codes if c != topic_code
            ]
        try:
            identity.save(canonical_pdf, recompute_hash=False)
        except Exception as exc:
            logger.warning("sidecar update after unlink_topic failed: %s", exc)
    return True
