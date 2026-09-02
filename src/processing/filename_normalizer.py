#!/usr/bin/env python3
"""Normalize filename formatting across the library.

Fixes common issues:
- Trailing/leading spaces around commas and dashes
- Double spaces
- Unicode normalization (NFD → NFC)
- Inconsistent dash types (-- → –)

This module is now ONE function. The CLI half — scan_and_propose,
apply_proposals, _describe_changes and main — was deleted: it had no
callers anywhere in the tree, sat at 26.71% coverage, and a mutation
campaign found 13 of its 14 guards could be removed with nothing
noticing. It was a second, unused implementation of what
``library_normalize.apply_renames`` does for real, and an unused path
that can rename files is a hazard, not a feature.
"""
from __future__ import annotations


import logging
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)



def _raise_after_sentence_mark(m):
    """"work?—mlOSP" -> "work? mlOSP", not "work? MlOSP".

    A "?" or "!" ends a sentence, so the word after it starts a new one and
    IS normally capitalised -- "Mind the cap!—constrained portfolio" really
    should become "Mind the cap! Constrained portfolio", and a test has
    asserted that for as long as the rule has existed.

    But the rule upper-cased the next letter unconditionally, and this runs
    on EVERY ingest and every move, inside the bucket labelled "cosmetic --
    no word changes" that is ticked by default. It corrupted exactly the
    identifiers the caser works hardest to keep:

        "work?—mlOSP"   ->  "work? MlOSP"
        "Really?—iOS"   ->  "Really? IOS"
        "cap!—p-adic"   ->  "cap! P-adic"

    So the capital is still applied, EXCEPT where the word's own shape says
    it is an identifier: an interior capital (mlOSP, iOS, q-Gaussian), or a
    stem the technical-prefix list already protects (p-adic, g-expectation).
    Both signals already exist in this project; neither is invented here.

    MEASURED: 0 of the 25,252 in-scope filenames match the pattern today,
    so the exposure is on future arrivals rather than on files already
    filed.
    """
    mark, word = m.group(1), m.group(2)
    if any(c.isupper() for c in word[1:]):
        return f"{mark} {word}"                  # mlOSP, iOS, q-Gaussian
    stem = word.split("-", 1)[0].split("_", 1)[0]
    try:
        from core.sentence_case import _load_sentence_case_config
        prefixes = {str(x).lower()
                    for x in _load_sentence_case_config()
                    .get("math_technical_prefixes", ())}
        if word.lower() in prefixes or ("-" in word and stem.lower() in prefixes):
            return f"{mark} {word}"              # p-adic, g-expectation
    except Exception:                            # pragma: no cover - defensive
        pass
    return f"{mark} {word[:1].upper()}{word[1:]}"


def normalize_filename(name: str) -> str:
    """Normalize a PDF filename.

    Returns the normalized name, or the original if no changes needed.
    """
    stem, ext = name.rsplit(".", 1) if "." in name else (name, "")

    s = stem

    # NFC normalize (macOS stores as NFD)
    s = unicodedata.normalize("NFC", s)

    # Fix double/triple spaces
    s = re.sub(r"  +", " ", s)

    # Fix spaces before commas: "Possamaï , D." → "Possamaï, D."
    #
    # NOT after a dash.  "Reygner, J. - , Propagation of chaos" has a stray
    # comma opening the title; without the guard this ate the separator's
    # space and produced "J. -, Propagation", destroying the author/title
    # boundary — which then hides the file from every rule that splits on
    # " - ", exactly how "Shiryaev, A.N.-" escaped the author sweep.
    s = re.sub(r"(?<![-–—‐])\s+,", ",", s)

    # A colon that a download tool sanitised into a hyphen.
    #
    # ":" is illegal in a filename on macOS, so browsers and publisher
    # sites save "Title: Subtitle" as "Title- Subtitle" — note the
    # asymmetry, NO space before the hyphen and one after, which a real
    # author-title separator (" - ") and a real hyphenated word
    # ("delay-differential") never have.  The house convention turns a
    # subtitle colon into ", " (cmo.py does this at ingest), so restore
    # that here; the subtitle's first word then lowercases by the normal
    # rule.  Measured: 4 files in the library, e.g.
    # "…delay-differential equations- When delay-systems…".
    # NOT after a superscript or subscript glyph.  "W^{1}- Sobolev"
    # canonicalises to "W¹- Sobolev", and Python's \d matches only
    # DECIMAL digits, so "¹" (category No) counts as a word character
    # here and the rule fired on the SECOND pass, giving "W¹, Sobolev".
    # The pipeline therefore had no fixpoint: running it twice changed
    # the answer. A script glyph before the dash means mathematics, and
    # the dash is a compound, not a sanitised colon.
    # Written out, NOT as the range ⁰-ⁿ: superscript ¹ ² ³ live in
    # Latin-1 at U+00B9/B2/B3, outside the U+2070 superscript block, so a
    # range silently misses the three most common exponents there are.
    _SCRIPTS = ("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵃᵇᶜᵈᵉᶠᵍʰʲᵏˡᵐᵒᵖʳˢᵗᵘᵛʷˣʸᶻᵝᵞᵟᶿᵡ"
                "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓᵦᵧᵨᵩᵪ")
    s = re.sub(rf"(?<=[^\W\d_])(?<![{re.escape(_SCRIPTS)}])- (?=[A-ZÀ-ÖØ-Þ])",
               ", ", s)

    # A dash straight after a sentence-ending mark is redundant: the mark
    # has already closed the sentence, so "airplane?—The correct defence"
    # and "Mind the cap!—constrained portfolio" are stacking two
    # separators.  Drop the dash and start the next word as the new
    # sentence it is.
    #
    # Restricted to "?" and "!" ON PURPOSE.  A period is also a sentence
    # end, but it is equally the end of an abbreviation, and there the
    # dash is a genuine author-title separator that must survive:
    #   "…, Jr. - Option pricing theory"
    #   "Helffer, B., …, et al. - Première classe de Chern"
    #   "Yoeurp, Ch. - Compléments sur les temps locaux"
    # No abbreviation ends in "?" or "!", so this cannot misfire.
    s = re.sub(r"([?!])\s*[-–—‐]+\s*([^\W\d_][\w'’-]*)",
               _raise_after_sentence_mark, s)

    # The author-title separator with its space eaten: "Itô, K.- Poisson".
    # The rules below only normalise a dash that ALREADY has a space on
    # one side, and the sanitised-colon rule above needs a word character
    # before the dash, so a dash hugging an initial's period fell through
    # both.  A compound initial ("Zou, H.-F.") is untouched because its
    # dash has no space after it.
    s = re.sub(r"(?<=[A-ZÀ-Þ]\.)-\s+(?=[^\W\d_\s])", " - ", s)

    # Fix spaces around the author-title separator dash
    # "Author  - Title" → "Author - Title"
    # "Author -Title" → "Author - Title"
    # "Author- Title" → "Author - Title"
    # But DON'T touch hyphens inside initials like "J.-P."
    s = re.sub(r"(?<!\.)  +- +", " - ", s)  # double+ space before dash
    s = re.sub(r"(?<!\.) +- +", " - ", s)   # normalize single space around dash

    # Missing space after a comma: "Possamaï,D." → "Possamaï, D."
    #
    # AUTHOR BLOCK ONLY, and this is the whole point.  Applied to the full
    # name it rewrote MATHEMATICS — "C^{0,1}" became "C^{0, 1}", "W^{2,p}"
    # became "W^{2, p}", "CARMA(p,q)" became "CARMA(p, q)", "10,000" would
    # become "10, 000".  86 files were damaged that way by a batch labelled
    # "cosmetic, no letters changed"; no letters had changed, but the
    # notation had.  Measured over the whole library, the title side has
    # ZERO commas needing a space and one that must never be touched, so
    # restricting the rule costs nothing and is the only thing that makes
    # it structurally unable to reach a formula.
    #
    # Deliberately AFTER the separator repairs above: "Possamaï,D.- Title"
    # has no " - " until they run, and the author block cannot be
    # identified before the boundary exists.
    _head, _sep, _tail = s.partition(" - ")
    if _sep:
        s = re.sub(r",([^\s])", r", \1", _head) + _sep + _tail

    # "--" is ambiguous, so decide by context rather than blanket-replacing.
    # Between digits it is a range and becomes an en dash ("pp. 10--20").
    # Spaced, it is a subtitle break — the same role as the colon handled
    # above — so it takes the house comma: "…term structure -- An empirical
    # study" is "…term structure, an empirical study", and the subtitle's
    # first word then lowercases by the normal rule.  It is NOT an en dash:
    # that mark joins two co-equal entities, which a title and its subtitle
    # are not.  Measured: exactly one "--" in 29,336 filenames.
    s = re.sub(r"(?<=\d)--(?=\d)", "–", s)
    s = re.sub(r"\s+--\s+", ", ", s)

    # A title that opens with the separator's own punctuation: "J. - ,
    # Propagation of chaos".  The comma is a leftover from whatever wrote
    # the name, not part of the title.
    s = re.sub(r"( - )[,;]\s*", r"\1", s)

    # …and the mirror image: an author list that ends with a dangling
    # comma, "Delmas, J.-F., Dronnier, D., Zitt, P.-A., - Vaccinating".
    # The separator is intact so nothing downstream notices, but the
    # author block is malformed and one of the three real cases has a
    # correctly-named twin already in the library — a duplicate waiting
    # to be missed, because the two names do not match.
    # Commas AND the whitespace between them: the comma-spacing rule
    # above has already turned ",," into ", ,", so stripping bare commas
    # left "M.,  - " with the comma still there and a doubled space.
    s = re.sub(r"[,\s]*,[,\s]*(?= - )", "", s)

    # Strip trailing/leading whitespace
    s = s.strip()

    result = f"{s}.{ext}" if ext else s
    return result
