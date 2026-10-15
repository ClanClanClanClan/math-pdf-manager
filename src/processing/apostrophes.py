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

See docs/FILENAME_CONVENTION.md 3.4 for the taxonomy, the per-class
rulings and what the naming code actually does with them.  This module
answers two questions: how to MATCH (``fold_marks``), and which straight
marks in a new paper's TITLE are apostrophes (``title_apostrophes``).

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

import re
import unicodedata
from typing import Iterable, Tuple

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


# ---------------------------------------------------------------------------
# The title apostrophe
# ---------------------------------------------------------------------------

#: A TITLE's punctuation apostrophe.  The title is prose -- the citation
#: string that finds the paper -- so it takes the typographic mark; the
#: author block is a key and keeps U+0027.  Measured 2026-10-15 over the
#: 25,251 in-scope names: 1,699 titles carry U+2019.
TITLE_APOSTROPHE = "’"

#: The one elision at the START of a word this library holds ("’Tis an
#: equity puzzle").  Every other word-initial straight mark opens a
#: quotation ("'Choose your opponent', a new knot…"): not an apostrophe.
_WORD_INITIAL_ELISION = re.compile(r"tis(?![^\W\d_])", re.IGNORECASE)


def _is_letter(c: str) -> bool:
    return c.isalpha()


def _base_before(text: str, i: int) -> int:
    """Index of the character before ``i``, stepping over combining marks.

    macOS hands back decomposed names: "Itô's" can arrive as ``o`` + U+0302
    + ``'``, and a mark is not a letter. -1 at the start of the text.
    """
    j = i - 1
    # "j >= 0" keeps text[-1] -- the END of the title -- out of it. Today
    # every caller only asks whether the answer is negative, so dropping it
    # changes nothing; it is kept so the index is never a lie.
    while j >= 0 and unicodedata.combining(text[j]):
        j -= 1
    return j


def _quotation_open_at(text: str, i: int) -> bool:
    """A single quotation is still open at ``i``.

    It opens at a ‘ or at a straight mark starting a word, and closes at a
    single mark that ends one.  While one is open, a mark after "s" may
    close it ("the 'reversals' and …") rather than make a possessive
    ("Walras' equilibrium"), and the two cannot be told apart.  Once it has
    closed -- "‘Théorie de la spéculation’, the missing piece in Walras'
    general equilibrium" -- they can again.
    """
    is_open = False
    for j in range(i):
        c = text[j]
        if c not in "‘’'":
            continue
        starts_word = j == 0 or text[j - 1].isspace()
        letter_next = j + 1 < len(text) and _is_letter(text[j + 1])
        if c == "‘" or (c == "'" and starts_word and letter_next):
            is_open = True
        elif not letter_next and not starts_word:
            is_open = False
    return is_open


#: Marks that only ever OPEN a quotation.
_OPENERS = "«‹“‘„"


def _opens_quotation(text: str, j: int) -> bool:
    """``text[j]`` opens a quotation: an opener, or a straight " before a
    letter.  Elision runs into one in French -- "l’« inégalité »"."""
    if j >= len(text):
        return False
    if text[j] in _OPENERS:
        return True
    return text[j] == '"' and j + 1 < len(text) and _is_letter(text[j + 1])


def is_title_apostrophe(title: str, i: int) -> bool:
    """True when the straight mark ``title[i]`` is certainly an apostrophe.

    Elision, possessive or contraction: the mark is PUNCTUATION.  Anything
    this cannot be sure of is False, and the caller leaves the mark as it
    is -- above all a mathematical prime, which is not an apostrophe and
    must never be written as one ("f'(x)" stays "f'(x)", never "f’(x)").

      * letter ' letter          l'équation, Itô's, don't, Tsirel'son,
                                 L'Hôpital, SDE's;
      * letter ' opening mark    l'« inégalité », d'"équations";
      * a word in -s, then '     Walras' equilibrium, Robbins' problem --
                                 unless a single quotation is open before it;
      * ) or a digit, then 's    Heston (2008)'s model, the 1990's;
      * 'tis                     at the start of a word.

    Never an apostrophe: a doubled mark (TeX's '' closer, or u''), a mark
    after one letter standing alone (S'-processes, X'_t, a closing prime),
    a mark after any other character, or a word-initial mark that opens a
    quotation.

    Measured 2026-10-15, with every ’ ‘ ′ in the 25,251 in-scope titles
    made straight again: this restores U+2019 at all 1,803 apostrophes and
    at none of the 350 single quotation marks or the 2 primes.  On the
    straight marks papers ARRIVED with (their records' original filenames),
    it calls an apostrophe every mark the library now writes as one.
    """
    if not (0 <= i < len(title)) or title[i] != "'":
        return False
    nxt = title[i + 1] if i + 1 < len(title) else ""
    b = _base_before(title, i)
    before = title[b] if b >= 0 else ""
    if nxt == "'":
        return False
    if _is_letter(before):
        if _is_letter(nxt) or _opens_quotation(title, i + 1):
            return True
        # A word in -s: two letters at least, so a lone "s'" -- a variable
        # and its prime -- is not one.
        bb = _base_before(title, b)
        return (before in "sS" and bb >= 0 and _is_letter(title[bb])
                and not _quotation_open_at(title, i))
    if b < 0 or before.isspace():
        return _WORD_INITIAL_ELISION.match(title, i + 1) is not None
    if before in ")]" or before.isdigit():
        # A tuple, not "sS": the empty string is "in" every string, and a
        # mark ending the title -- "(uv)'" -- is a prime.
        return nxt in ("s", "S")
    return False


def title_apostrophes(title: str,
                      protected: Iterable[Tuple[int, int]] = ()) -> str:
    """``title`` with each straight mark that is an apostrophe as U+2019.

    TITLES ONLY: the author block keeps U+0027 (it is a key).  Nothing but
    U+0027 is ever changed, and nothing inside a ``protected`` span --
    mathematics.  Applied at arrival only; nothing rewrites a name already
    on a shelf.
    """
    if "'" not in title:
        return title
    spans = list(protected)
    out = list(title)
    for i in range(len(title)):
        if is_title_apostrophe(title, i) and not any(a <= i < e for a, e in spans):
            out[i] = TITLE_APOSTROPHE
    return "".join(out)
