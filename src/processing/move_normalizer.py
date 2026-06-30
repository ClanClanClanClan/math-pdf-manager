"""Normalize a paper's filename whenever it is moved/filed.

The library convention puts a SPACE between separate author initials
("Dalang, R. C." not "Dalang, R.C."), keeps hyphenated initials
("J.-P.", "H.-J.") and nobiliary particles ("le Bris", "van der",
"el Karoui", "Maldonado López") intact.  That rule was enforced at first
ingest but NOT when a paper later moved between folders, so moved papers
kept stale author formatting (the owner flagged "Dalang, R.C." during the
duplicate review).

This module applies the SAFE, mechanical part of the canonical-filename
rules on a move:
  * author-initial spacing + comma spacing — via the filename checker's
    author auto-fix (``check_filename(auto_fix_authors=True)``), and
  * cosmetic cleanup (NFC, double spaces, dash types) — via
    ``filename_normalizer.normalize_filename``.

It deliberately DOES NOT re-case the TITLE.  Title sentence-casing needs
the full proper-noun / place-name / math whitelist; without it the pass
lowercases legitimate names (empirically "Stefano Franscini, Ascona, May"
→ "stefano franscini, ascona, may").  Title casing is therefore left to a
separate, review-gated path, never auto-applied on a move.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def normalize_authors_in_name(name: str) -> tuple[str, bool]:
    """Return ``(normalized_name, changed)`` — author + cosmetic fixes only.

    The TITLE is preserved verbatim (only cosmetic spacing/NFC applied);
    only the author block is canonicalised.  Best-effort: on any error it
    falls back to the cosmetically-normalised name so a move never fails
    because of formatting.
    """
    from processing.filename_normalizer import normalize_filename

    cosmetic = normalize_filename(name)
    if " - " not in cosmetic:
        # No author/title separator — nothing to canonicalise; cosmetic only.
        return cosmetic, cosmetic != name

    try:
        from validators.filename_checker.core import check_filename
        res = check_filename(
            cosmetic,
            auto_fix_authors=True,
            auto_fix_nfc=True,
            sentence_case=False,   # NEVER auto-recase the title
        )
        corrected = res.corrected_filename
    except Exception as exc:  # never let formatting break a move
        logger.debug("author normalize failed for %r: %s", name, exc)
        return cosmetic, cosmetic != name

    if not corrected or " - " not in corrected:
        return cosmetic, cosmetic != name

    # Take ONLY the checker's fixed author block; keep the ORIGINAL title
    # verbatim so the checker's title-side fixers can never silently
    # rewrite the title (number spell-out, ligatures, casing, ...).
    fixed_authors = corrected.split(" - ", 1)[0]
    orig_title = cosmetic.split(" - ", 1)[1]
    new = f"{fixed_authors} - {orig_title}"
    return new, new != name


def normalize_file_in_place(pdf: Path, *, undo_log=None) -> tuple[bool, str]:
    """Rename ``pdf`` to its author-normalised name if needed (reversible).

    Returns ``(changed, message)``.  Goes through ``logged_rename`` so the
    sidecar travels and the rename is one undoable operation.  Refuses if
    the normalised target already exists (so two papers never collide).
    """
    from processing.undo_log import logged_rename

    new_name, changed = normalize_authors_in_name(pdf.name)
    if not changed:
        return False, "already normalized"
    dest = pdf.with_name(new_name)
    if dest.exists() and dest != pdf:
        return False, f"target exists: {new_name}"
    logged_rename(pdf, dest, undo_log=undo_log)
    return True, new_name
