"""Which existing filenames a phrase ruling would target.

A phrase ruling (``title_vocab.decide_phrase``) is the one vocabulary
decision that is RETROACTIVE: unlike a word ruling, which only preserves
a capital that is already there, a phrase ruling matches case- and
dash-insensitively and rewrites the span to the ruled spelling.  So
before the owner makes one, he should be able to see what it would touch.

This module answers exactly one question and does not pretend to answer
more:

    "Which filenames spell this phrase some OTHER way today?"

That is a statement about text, computed exactly.  It is deliberately NOT
"which files would this rename" -- the caser may also change other words
in the same name, or decline to touch the file at all.  The authoritative
answer to *that* is the Maintenance sweep, which runs the real
``normalize_full_name`` over the library.  Confusing the two is how a
count becomes a promise.

ONE MATCHER. ``title_normalize.propose_title_case`` finds the spans it
rewrites by calling :func:`occurrences` -- the same function this
module's counts use -- so the two cannot disagree about WHICH spans a
ruling governs. (On 2026-09-02 they were two implementations that
happened to agree on the 28 files measured; they differed on dashes and
on hand-lowercasing, and a fix to one would not have reached the other.)
The caser can still decline a whole file for reasons outside phrase
matching, which is why the wording stays "spelled differently" and the
Maintenance sweep remains the authority on renames.

Read-only: nothing here opens a file.
"""
from __future__ import annotations

import re
import unicodedata

#: Every dash the library has ever used for the same name.  Matching is
#: dash-blind because typewriter habits scatter a name across "-", "–"
#: and "—".
#:
#: This is the ONE definition. ``title_normalize`` imports it rather than
#: keeping its own. Until 2026-10 it did keep its own -- eight marks there,
#: three here -- so a ruled phrase spelled with U+2010 HYPHEN, U+2011
#: NON-BREAKING HYPHEN, U+2012 FIGURE DASH or U+2015 HORIZONTAL BAR was
#: rewritten by the renamer and missing from this module's count.
DASH_FOLD_SET = "-\u2013\u2014\u2010\u2011\u2012\u2015\u2212"
_DASHES = str.maketrans({c: "-" for c in DASH_FOLD_SET if c != "-"})

_SEP = " - "


def title_of(name: str) -> str:
    """The part of a filename the title caser will actually look at.

    Split on the FIRST separator, matching ``normalize_full_name``.

    A name with NO separator has no title here -- empty string, not the
    whole name.  ``normalize_full_name`` returns early on those
    (``if " - " not in new: return``), so the caser never reads them and
    no ruling can ever change them.  The first version of this function
    treated them as all-title and claimed in its own docstring that this
    was "what the caser sees too".  MEASURED against the real library,
    that was false and expensive: it reported 17 files needing "Tōhoku
    Imperial University" fixed, of which the renamer would fix ZERO,
    because every one of them is an un-separated scan name like
    "09-The science reports of the Tōhoku imperial university...".
    Offering the owner a count of files that cannot be repaired is the
    same class of error as a check that cannot fail.
    """
    name = unicodedata.normalize("NFC", name)
    if _SEP not in name:
        return ""
    return name.split(_SEP, 1)[1]


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def occurrences(title: str, phrase: str) -> list:
    """The spans of ``title`` that the ruling ``phrase`` governs.

    Word-bounded, case- and dash-blind -- except that a ruling spelled
    with a lower-case first letter does not govern a span that opens the
    title (see :func:`_sentence_initial`).

    Returns ``[(start, end)]`` indexing the NFC-normalised ``title``
    (which is what :func:`title_of` hands back, so callers inside this
    module can slice their own string directly).

    CASE-FOLDING MUST NOT HAPPEN BY HAND HERE.  The first version folded
    both strings and did index arithmetic on the result, documenting the
    fold as "length-preserving".  It is not: "ß".casefold() is "ss", and
    this library deliberately keeps German ß (FILENAME_CONVENTION 3.15),
    while NFD→NFC shortens any decomposed accent — and macOS hands out
    NFD.  Either shifts every index after the character, so the reported
    span was silently the wrong slice.  It survived the whole test file
    because title_of() had already normalised, which hid it everywhere
    except a direct call.  ``re.IGNORECASE`` does the same comparison
    without ever changing a length, so spans stay valid by construction.
    """
    t, ph = _nfc(title), _nfc(phrase)
    if not ph.strip():
        return []
    # Dash folding IS 1:1 (str.translate of single chars), so it is safe
    # to do by hand — it is only the CASE fold that had to move.
    pattern = re.compile(re.escape(ph.translate(_DASHES)), re.IGNORECASE)
    lowercase_ruling = ph[:1].islower()
    out = []
    for m in pattern.finditer(t.translate(_DASHES)):
        a, b = m.start(), m.end()
        before_ok = a == 0 or not t[a - 1].isalpha()
        after_ok = b >= len(t) or not t[b].isalpha()
        if not (before_ok and after_ok):
            continue
        if lowercase_ruling and _sentence_initial(t, a):
            continue
        out.append((a, b))
    return out


def _sentence_initial(title: str, at: int) -> bool:
    """Does the span at ``at`` open the title's first sentence?

    True when no letter or digit comes before it, so an opening quote or
    bracket in front ("“De Rham” revisited") still counts as the start.

    WHY THIS EXISTS. A ruling whose spelling begins in lower case --
    "de Rham", "van der Waerden", "in 't Hout" -- is right mid-title and
    WRONG as the first word of a title, where sentence case demands the
    capital. Without this, ruling "de Rham" would have rewritten

        De Rham–Hodge–Kodaira's decomposition on an abstract Wiener space

    to "de Rham–Hodge–…", making a correct filename incorrect. That was
    the only file the ruling would have touched, measured on 2026-09-05.
    The span is not governed by the ruling at all there: it is neither
    rewritten, nor counted as needing a fix, nor counted as correct.
    """
    return not any(ch.isalnum() for ch in title[:at])


def would_change(name: str, phrase: str) -> bool:
    """Does this filename spell ``phrase`` some other way in its title?"""
    title, ph = title_of(name), _nfc(phrase)
    return any(title[a:b] != ph for a, b in occurrences(title, ph))


def impact(names, phrase: str) -> list:
    """The filenames whose title spells ``phrase`` differently.

    ``names`` is any iterable of filenames (the cockpit passes the cached
    search index's names, so this costs no extra library walk).
    """
    phrase = unicodedata.normalize("NFC", phrase).strip()
    if not phrase:
        return []
    return [n for n in names if would_change(n, phrase)]


def already_correct(names, phrase: str) -> int:
    """How many filenames ALREADY spell it the ruled way.

    Shown next to the impact count so a zero-impact ruling reads as
    "nothing to fix" rather than "this phrase does not occur".  Those are
    different states and the owner should not have to guess which he is
    looking at.
    """
    phrase = unicodedata.normalize("NFC", phrase).strip()
    if not phrase:
        return 0
    n = 0
    for name in names:
        title = title_of(name)
        if any(title[a:b] == phrase for a, b in occurrences(title, phrase)):
            n += 1
    return n
