"""Apostrophe-like marks: one fold for matching, and what each one MEANS.

THE RULE IS KEYED ON FUNCTION, NOT ON LANGUAGE.  The owner asked whether
the apostrophe is language-dependent the way quotation marks are.  It is
not: CLDR gives every locale its own ``quotationStart``/``quotationEnd``
(« » fr, „ " de, " " en) and defines NO apostrophe element in any locale,
and every national authority checked — Imprimerie nationale, Accademia
della Crusca, Duden, Onze Taal, IEC, RAE, Chicago 6.117 — prescribes the
same 9-shaped raised comma for elision.  Nobody flips it.

The real axis of variation is whether the mark is PUNCTUATION or a
LETTER, and Unicode encodes that in different codepoints (core spec
§6.2.7): U+2019 where it is a punctuation apostrophe, U+02BC where it is
a modifier letter.  WHICH SIDE a name falls on IS language-dependent, and
CLDR settles it per language in ``exemplarCharacters``: Ukrainian's and
Breton's alphabets contain U+02BC, Hawaiian's contains U+02BB, while
French, Italian, Irish and Dutch contain no apostrophe at all.

See docs/FILENAME_CONVENTION.md 3.13 for the full taxonomy and the
per-class rulings.  This module exists for ONE purpose: matching.

WHY FOLDING MATTERS MORE THAN THE SPELLING.  No Unicode normalisation
form equates these marks -- NFC, NFD, NFKC, NFKD and casefold all leave
U+0027 and U+2019 distinct, unlike the NFD/NFC accent trap this library
already knows about, where normalising genuinely repairs the match.  So a
corpus holding both spellings has a person who is findable by only half
their own files: measured, "d'Amato" and "d’Amato" are the same author
and two different strings.  Folding on the MATCH side fixes that without
renaming anything.
"""
from __future__ import annotations

#: Every mark that can stand where an apostrophe stands in this corpus,
#: whatever it means.  Deliberately includes the ones that are NOT
#: apostrophes -- the Cyrillic soft-sign prime (U+02B9), the modifier
#: letter apostrophe (U+02BC), and the stray grave/acute that arrive as
#: LaTeX residue -- because the point here is to make them all MATCH each
#: other, not to claim they are the same thing.
APOSTROPHE_LIKE = frozenset(
    "'"  # ' APOSTROPHE
    "’"  # ’ RIGHT SINGLE QUOTATION MARK
    "‘"  # ‘ LEFT SINGLE QUOTATION MARK
    "‛"  # ‛ SINGLE HIGH-REVERSED-9
    "`"  # ` GRAVE ACCENT
    "´"  # ´ ACUTE ACCENT
    "ʹ"  # ʹ MODIFIER LETTER PRIME        (Cyrillic soft sign)
    "ʺ"  # ʺ MODIFIER LETTER DOUBLE PRIME (Cyrillic hard sign)
    "ʻ"  # ʻ MODIFIER LETTER TURNED COMMA (Hawaiian ʻokina)
    "ʼ"  # ʼ MODIFIER LETTER APOSTROPHE   (Breton c'h, Ukrainian)
    "ʽ"  # ʽ MODIFIER LETTER REVERSED COMMA
    "ʾ"  # ʾ MODIFIER LETTER RIGHT HALF RING (Arabic hamza)
    "ʿ"  # ʿ MODIFIER LETTER LEFT HALF RING  (Arabic ayn)
    "′"  # ′ PRIME
    "‵"  # ‵ REVERSED PRIME
)

#: What every one of them folds to for matching.  U+0027 rather than
#: U+2019 because the fold key should be the form the external name
#: authorities use -- measured 99.95% U+0027 across 1,909 name records in
#: ORCID, arXiv, zbMATH and the LC name authority file -- and because
#: Unicode's own identifier-comparison data (UTS #39 confusables.txt)
#: maps U+2019 TO U+0027, not the other way round.
FOLD_TO = "'"


def fold_marks(s: str) -> str:
    """Map every apostrophe-like mark to one character, for MATCHING only.

    Never use this to build a name that will be written to disk: it
    destroys the distinction between a punctuation apostrophe and a
    letter, which is exactly the distinction the convention preserves.
    """
    if not any(c in APOSTROPHE_LIKE for c in s):
        return s
    return "".join(FOLD_TO if c in APOSTROPHE_LIKE else c for c in s)
