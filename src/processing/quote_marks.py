"""Quotation marks in titles: one house convention per language.

The owner's ruling, 2026-10-14 ("1B"), on his instruction of 2026-09-05
("typographically correct, ALWAYS"):

    English   ‘ outer ’   with  “ inner ”     (Oxford / New Hart's / LMS)
    French    « outer »   with  ‹ inner ›     ordinary U+0020 inside each
    otherwise leave the marks as they are, and say why (never guess)

British vs American does not choose a glyph -- both varieties use the
same four characters; which level comes first is publisher house style
(agent-results/NAMING-RULING.md section 1.4) -- so the owner chose one
English convention, single-outer.

TITLES ONLY. An author block never carries quotation marks, and the
apostrophe is a different mark with its own settled rule
(processing/apostrophes.py): a mark flanked by letters on both sides is
an apostrophe or a prime, never a quote, and is never touched here.

This module only PROPOSES: ``requote`` returns the new title and a
status. The language is the language of the TITLE AROUND the quotation,
not of the quotation: "Yule’s ‘nonsense correlation’, moments and
density" is English. ``quotation_language`` decides that, from the
detector's answer and the small words outside the quoted passage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

LSQ, RSQ = "‘", "’"      # ‘ ’
LDQ, RDQ = "“", "”"      # “ ”
LAQ, RAQ = "«", "»"      # « »
LSAQ, RSAQ = "‹", "›"    # ‹ ›

#: (outer open, outer close, inner open, inner close, padded with a space?)
CONVENTION = {
    "en": (LSQ, RSQ, LDQ, RDQ, False),
    "fr": (LAQ, RAQ, LSAQ, RSAQ, True),
}

#: Every double-quote-like mark a title may arrive with.
_DOUBLE_MARKS = '"' + LDQ + RDQ + LAQ + RAQ + "„‟"
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


@dataclass(frozen=True)
class Requote:
    title: str
    status: str          # "changed" | "unchanged" | "review"
    why: str = ""


def _pairs(title: str) -> Optional[list]:
    """Spans (open_index, close_index) of the double-quoted passages, or
    None when the marks cannot be paired with certainty."""
    idx = [i for i, c in enumerate(title) if c in _DOUBLE_MARKS]
    if not idx:
        return []
    # A straight " between two letters is an inch mark or a typo, not a
    # quote -- never pair it.
    for i in idx:
        if title[i] == '"' and 0 < i < len(title) - 1 \
                and _LETTER.match(title[i - 1]) and _LETTER.match(title[i + 1]):
            return None
    if len(idx) != 2:
        return None          # odd count, or nesting written with the same mark
    a, b = idx
    if title[a] in (RDQ, RAQ) or title[b] in (LDQ, LAQ, "„"):
        # A closer first, or an opener last: malformed beyond a straight
        # pairing ("“…“" is fine -- both openers -- see the caller's list).
        if not (title[a] == LDQ and title[b] == LDQ):
            return None
    return [(a, b)]


def requote(title: str, lang: Optional[str]) -> Requote:
    """The title with its quotation marks in the house convention.

    ``lang`` is the title's language ("en", "fr") or None/other when not
    known -- then nothing changes and the reason is given.
    """
    has_double = any(c in _DOUBLE_MARKS for c in title)
    has_single_quote = LSQ in title     # an opening single is always a quote
    if not has_double and not has_single_quote:
        return Requote(title, "unchanged")
    if lang not in CONVENTION:
        return Requote(title, "review", f"language not known ({lang or 'none'})")
    o, c, io, ic, pad = CONVENTION[lang]

    if has_single_quote:
        # A top-level ‘…’ already present: English is already right; any
        # other combination is nesting, which is never done mark by mark.
        if not has_double and lang == "en" and title.count(LSQ) == 1:
            return Requote(title, "unchanged")
        return Requote(title, "review", "single quotation marks present: nesting or another convention")

    spans = _pairs(title)
    if spans is None:
        return Requote(title, "review", "the marks cannot be paired with certainty")
    (a, b), = spans
    inner = title[a + 1:b]
    if pad:
        inner = f" {inner.strip()} "
    new = title[:a] + o + inner + c + title[b + 1:]
    return Requote(new, "changed" if new != title else "unchanged")


#: Small words that only ONE of English and French uses. Outside a
#: quotation they say which of the two the title is written in.
#: Measured 2026-10-15 on the 216 titles whose quote language the owner
#: settled: whole-filename detection got 5 wrong (four English titles
#: quoting French, read as French), this rule 0. The detector cannot do
#: this itself: on two-word frames it reads "Comment on" as French and
#: "Erratum to" as Portuguese.
_EN_FRAME = frozenset({
    "the", "and", "of", "to", "with", "for", "from", "by", "on", "in",
    "an", "at", "is", "are", "its", "their", "this", "that", "which",
    "into", "without", "between", "toward", "towards", "versus",
})
_FR_FRAME = frozenset({
    "le", "la", "les", "des", "du", "de", "et", "sur", "pour", "une",
    "un", "dans", "par", "au", "aux", "à", "en", "avec", "sans", "entre",
    "vers", "chez", "est",
})
#: l’espace, d’une, qu’il, and l’ / d’ right before a quotation --
#: French elision. Not "Yule’s".
_FR_ELISION = re.compile(r"^(?:l|d|qu|j|n|s|c)[’'](?:\w|$)", re.IGNORECASE)
_TOKEN = re.compile(r"[^\W\d_][\w’']*", re.UNICODE)


def quotation_language(title: str, detected: Optional[str]) -> Optional[str]:
    """The language ``title``'s quotation marks follow.

    ``detected`` is the language detector's answer for the whole title
    (None when it failed). A quoted passage pulls the detector toward its
    own language, so the words OUTSIDE it arbitrate: when they carry
    small words of exactly one of English and French, that language wins.
    "Correction" alone, or a frame with both, says nothing -- the
    detector's answer stands.

    Only ever chooses BETWEEN English and French: any other answer comes
    back unchanged and ``requote`` leaves the marks alone. "in", "la" and
    "un" are German, Spanish and Italian words too, so the frame is never
    allowed to turn another language into one of these two.
    """
    if detected not in CONVENTION:
        return detected
    spans = _pairs(title)
    if not spans:
        return detected
    frame, last = [], 0
    for a, b in spans:
        frame.append(title[last:a])
        last = b + 1
    frame.append(title[last:])
    words = [w.lower() for w in _TOKEN.findall(" ".join(frame))]
    en = any(w in _EN_FRAME for w in words)
    fr = any(w in _FR_FRAME or _FR_ELISION.match(w) for w in words)
    if en != fr:
        return "en" if en else "fr"
    return detected


def fold_quotes(s: str) -> str:
    """The text with every QUOTATION mark removed -- for MATCHING only.

    Converting a title's quotes must not fork the keys that Search and
    same-paper detection compare: "hot hand", “hot hand”, ‘hot hand’ and
    « hot hand » all fold to the same text (NAMING-RULING 1.3 made this a
    precondition of any quote change). Removed: every double mark,
    guillemets single and double, an opening single ‘, and the ’ that
    closes it. An apostrophe -- ’ between letters, or not preceded by an
    opening ‘ -- stays, for the apostrophe fold to handle. Whitespace is
    collapsed, so the spaces French puts inside « » do not count either.
    Never use this to build a name written to disk.
    """
    if not any(c in s for c in _DOUBLE_MARKS + LSQ + LSAQ + RSAQ):
        return s
    out, open_single = [], False
    for i, ch in enumerate(s):
        if ch in _DOUBLE_MARKS or ch in (LSAQ, RSAQ):
            out.append(" ")
            continue
        if ch == LSQ:
            open_single = True
            out.append(" ")
            continue
        if ch == RSQ and open_single and (i + 1 == len(s) or not _LETTER.match(s[i + 1])):
            open_single = False
            out.append(" ")
            continue
        out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()
