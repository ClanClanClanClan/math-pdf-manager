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
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def _has_unspaced_initials(author_part: str) -> bool:
    """True when a dot is glued to a following capital ("R.C.", "M.Ø.").

    Spacing those is the ONLY thing the (langdetect-heavy) author checker
    changes in a well-formed author block, so when there are none we skip
    that call entirely — the pre-gate that makes a whole-library sweep
    affordable.  Hyphenated initials ("H.-J.") and trailing single ones
    ("Smith, J.") do not match and are correctly left alone.

    Uses ``str.isupper`` rather than a ``[A-Z]`` character class: the
    ASCII-only version silently skipped every accented initial, so
    "Nielsen, M.Ø." was never even offered to the checker (which handles
    it correctly) — 135 such names in the real library.
    """
    return any(
        author_part[i] == "." and author_part[i + 1].isupper()
        for i in range(len(author_part) - 1)
    )

# One shared spellchecker for the whole process.  check_filename() builds a
# fresh SpellChecker() on every call otherwise (~70ms of JSON-dictionary +
# langdetect-profile loading) — which dominated a whole-library normalization
# sweep (profiling: ~4.45s of every 4.79s was spellchecker construction).
# The instance is used read-only (dictionary lookups), so sharing it is safe;
# this also speeds up every single ingest and move.
_SHARED_SPELLCHECKER = None
_SPELLCHECKER_UNAVAILABLE = False


def _shared_spellchecker():
    """Lazily construct one SpellChecker and reuse it; None if unavailable
    (then check_filename falls back to building its own, as before)."""
    global _SHARED_SPELLCHECKER, _SPELLCHECKER_UNAVAILABLE
    if _SHARED_SPELLCHECKER is None and not _SPELLCHECKER_UNAVAILABLE:
        try:
            from core.text_processing.my_spellchecker import SpellChecker
            _SHARED_SPELLCHECKER = SpellChecker()
        except Exception as exc:  # pragma: no cover — defensive
            logger.debug("shared spellchecker unavailable: %s", exc)
            _SPELLCHECKER_UNAVAILABLE = True
    return _SHARED_SPELLCHECKER


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

    author_part = cosmetic.split(" - ", 1)[0]
    if not _has_unspaced_initials(author_part):
        # Author block already has no unspaced initials — the checker would
        # leave it unchanged.  Skip the heavy call (langdetect on every
        # filename) so bulk sweeps over the whole library stay fast.
        return cosmetic, cosmetic != name

    try:
        from validators.filename_checker.core import check_filename
        res = check_filename(
            cosmetic,
            auto_fix_authors=True,
            auto_fix_nfc=True,
            sentence_case=False,   # NEVER auto-recase the title
            spellchecker=_shared_spellchecker(),
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


def normalize_full_name(
    name: str,
    library_root: Optional[Path] = None,
) -> tuple[str, bool, list]:
    """Author block + (confident) safe-default title casing.

    Returns ``(new_name, changed, pending_words)``.

    Title casing is applied PER WORD: the safe-default caser only ever
    changes words it individually proved common (plus the first word), so
    its proposal is safe to apply even when OTHER words in the title are
    unknown — those are preserved verbatim and returned in
    ``pending_words`` for the owner's vocabulary review.  One eponym in a
    title must not block fixing a blatant "The/Of" (auto-apply is the
    owner's explicit policy choice).
    """
    new, changed = normalize_authors_in_name(name)
    pending: list = []
    if " - " not in new:
        return new, changed, pending
    try:
        from processing.title_normalize import propose_title_case
        authors, title_ext = new.split(" - ", 1)
        if "." in title_ext:
            stem, ext = title_ext.rsplit(".", 1)
        else:
            stem, ext = title_ext, ""
        prop = propose_title_case(stem, library_root)
        pending = list(prop.uncertain)
        if prop.changed:
            new = f"{authors} - {prop.proposed}" + (f".{ext}" if ext else "")
            changed = True
    except Exception as exc:  # never let title casing break a move
        logger.debug("title normalize failed for %r: %s", name, exc)
    return new, changed, pending


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
