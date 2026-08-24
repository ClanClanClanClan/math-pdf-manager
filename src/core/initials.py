"""Spacing an author's initials. One rule, one implementation.

The library's convention is spaced initials -- "Rogers, L. C. G.", never
"Rogers, L.C.G." -- and there were THREE implementations of it:

  * ``validators/filename_checker/author_processing.fix_initial_spacing``
    Unicode-aware, and it knows an initial is not always one letter:
    transliterated Cyrillic given names need "Yu.", "Zh.", "Ya.", "Kh.",
    "Shch.".  Its lookahead required the FOLLOWING chunk to carry its own
    period, so a final initial that had lost one -- "Kyprianou, A.E" --
    was invisible to it.

  * ``validators/author_parser.fix_initial_spacing``
    ``([A-Z])\\.([A-Z])`` in a loop.  ASCII-only, so "Kabanov, Yu.A." never
    matched at all.  But it DID catch the final-initial case.

  * ``processing.filename_ground_truth._space_initials``
    a thin wrapper that had to pick one of the two.

Differential-tested over all 17,804 distinct author blocks in the library,
the first two agreed on 17,795, the live one never acted alone, and the
frozen one acted alone on 9.  Neither was a superset of the other, so
deleting either lost real behaviour.  This module is the union, and the
other three now delegate to it.

PRECONDITION -- IT MATTERS MORE THAN THE PATTERN.

Apply this to an AUTHOR BLOCK, never to a title. The reason is not
squeamishness: the two cases are genuinely indistinguishable as strings.
Measured over the library's titles, spacing them out would correctly fix

    Kipnis, C., Varadhan, S.R.S.   ->  Varadhan, S. R. S.
    an inequality of R.E.A.C. Paley -> R. E. A. C. Paley

and would wrongly mangle

    A P.D.E. approach to Asian options   ->  P. D. E.
    Variation des solutions d'une E.D.S. ->  E. D. S.

Both are "capital, period, capital, period". No rule reading the string
alone can separate a person from an acronym, so the caller has to know
which it is holding. Every production caller does: they are all inside
``fix_author_block`` and its siblings.
"""
from __future__ import annotations

import re
import unicodedata

__all__ = ["space_initials", "INITIAL_RE"]


def _letter_class(category: str) -> str:
    """Every letter of ``category`` in Latin, Greek and Cyrillic.

    Enumerating these by hand is how the ASCII-only implementation came to
    miss "Kabanov, Yu.A." and how a sibling module came to reject
    "Sengul, B." and "Banas, L.". unicodedata cannot forget a letter.
    """
    ranges = ((0x41, 0x24F), (0x370, 0x3FF), (0x400, 0x52F), (0x1E00, 0x1EFF))
    return "".join(re.escape(chr(c)) for lo, hi in ranges
                   for c in range(lo, hi + 1)
                   if unicodedata.category(chr(c)) == category)


_UPPER = _letter_class("Lu")

#: _LOWER is symmetry, not necessity. Every multi-letter initial the library
#: actually contains is an ASCII transliteration -- "Yu.", "Zh.", "Ya.",
#: "Kh.", "Shch." -- and initials written in Cyrillic script are single
#: characters ("Ю.", "С."), which the tail never sees. Measured: replacing
#: this with "a-z" changes the answer on ZERO library strings, and on none of
#: the constructed Czech and Polish names I tried either. So a mutation that
#: narrows it survives, and that is recorded here rather than answered with a
#: test over a name nobody has.
_LOWER = _letter_class("Ll")

#: One initial: a capital, then AT MOST THREE lowercase letters.
#:
#: The shape does the work that two hand-written guards used to do. An
#: all-caps run ("USA.") fails because the second character is not
#: lowercase; a lowercase word ("et.") fails because the first is not a
#: capital; and a real word ("St.Petersburg", "O.Brien") fails because
#: what follows is longer than an initial.
INITIAL = rf"[{_UPPER}][{_LOWER}]{{0,3}}"

#: An initial glued to the next one. The following chunk must itself be
#: initial-shaped and must END there -- with its own period, at a comma, or
#: at the end of the block.
#:
#: Admitting "at a comma or the end" is the whole difference from the live
#: implementation, and it is what recovers "Kyprianou, A.E" and
#: "Asheim, G.B". It does NOT open the door to "St.Petersburg": after "St."
#: the pattern needs at most four letters followed by a period, a comma or
#: the end, and "Petersburg" is none of those.
INITIAL_RE = re.compile(rf"({INITIAL}\.)(?={INITIAL}(?:\.|,|$))")


def space_initials(text: str) -> str:
    """``"Kabanov, Yu.A."`` -> ``"Kabanov, Yu. A."``

    ONE pass, not a loop to a fixpoint. ``re.sub`` replaces every
    non-overlapping match, and inserting a space can never create a new
    adjacency, so a run of three -- "Veraart, L.A.M" -- is fully separated
    the first time.

    Both predecessors looped. I kept the loop, then a mutation that removed
    it survived: checked against every author block and every filename in the
    library, and against 200,000 synthetic initial-soup strings, one pass and
    the fixpoint NEVER disagree. Keeping it would have been a branch no test
    could reach.
    """
    if not text:
        return text
    return INITIAL_RE.sub(lambda m: m.group(1) + " ", text)
