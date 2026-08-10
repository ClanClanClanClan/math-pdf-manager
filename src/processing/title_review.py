"""Turn a wall of title renames into a handful of decisions.

The retroactive scan produces ~1,000 title proposals.  The cockpit could
only offer them as one all-or-nothing bucket: tick "Title casing" and
apply up to N.  For a thousand filenames that is not a review, it is a
leap of faith — the owner has to trust every one or none.

Measured on the real library (1,084 title/both proposals), they are not
a thousand independent judgements:

  * 186 change no letters at all — only spacing, punctuation or accent
    composition ("(0,π)" -> "(0, π)", a stripped leading space).
    Mechanical, exactly like the author-spacing bucket.
  * 771 only capitalise the title's FIRST word.  That is what sentence
    case means, not a judgement call; the bulk are French journal issues
    filed as "sciences mathématiques, 2ème partie, 1966".
  * 126 change capitalisation MID-title.  These are the real decisions —
    and they collapse to ~135 distinct word rulings ("Integrals" ->
    "integrals"), each of which settles every file containing that word
    and is the same ruling the vocabulary store already keeps, so it
    holds for future papers too.
  * 1 genuinely rewrites text and deserves to be looked at.

So 957 of the 1,084 are two obvious approvals, and the review that
actually needs the owner's eye is a hundred-odd files, not a thousand.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

COSMETIC = "cosmetic"     # no letter changed — spacing/punctuation/accents
FIRSTWORD = "firstword"   # only the title's FIRST word was capitalised
CASE = "case"             # mid-title capitalisation — needs a ruling
REWRITE = "rewrite"       # the text itself differs

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _title_of(name: str) -> str:
    """The title half of ``Authors - Title.pdf`` (or the whole name)."""
    n = unicodedata.normalize("NFC", name)
    return n.split(" - ", 1)[1] if " - " in n else n


def _letters_signature(s: str) -> str:
    """Everything that is not a letter or digit, folded away.

    Two strings with the same signature differ only in spacing,
    punctuation, accent composition or case — never in their words.
    """
    decomposed = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^\w]", "", decomposed).lower()


def _cased_signature(s: str) -> str:
    """As above but CASE-PRESERVING — the difference the other one hides."""
    return re.sub(r"[^\w]", "", unicodedata.normalize("NFKD", s))


def classify_proposal(old_name: str, new_name: str) -> str:
    """Which kind of title change this is: cosmetic, case, or rewrite."""
    old_t, new_t = _title_of(old_name), _title_of(new_name)
    old_w, new_w = _WORD_RE.findall(old_t), _WORD_RE.findall(new_t)
    if len(old_w) == len(new_w) and [w.lower() for w in old_w] == [w.lower() for w in new_w]:
        # Same words in the same order; only capitalisation moved.  If the
        # non-letter characters also moved it is still a case decision —
        # the punctuation ride-along is not what he is judging.
        if old_w == new_w:
            return COSMETIC
        differing = [i for i, (a, b) in enumerate(zip(old_w, new_w)) if a != b]
        # Capitalising the title's FIRST word is not a judgement call —
        # it is what sentence case means, and on this library it is the
        # single biggest group (French journal issues filed as
        # "sciences mathématiques, 2ème partie, 1966").  Keeping it out of
        # the review turns hundreds of files into one obvious approval.
        if differing == [0] and new_w[0][:1].isupper() and old_w[0][:1].islower():
            return FIRSTWORD
        return CASE
    if _letters_signature(old_t) == _letters_signature(new_t):
        # Same letters — but that signature is LOWERCASED, so on its own
        # it cannot tell "only punctuation moved" from "the capitals also
        # moved".  Reaching here at all means the word lists disagreed,
        # which now happens whenever maths was converted: "L^2" tokenises
        # as "L" and "L²" as one word, so a title with both a superscript
        # and a casing decision fell straight through to COSMETIC and the
        # owner would never have been asked.
        return (COSMETIC if _cased_signature(old_t) == _cased_signature(new_t)
                else CASE)
    return REWRITE


def word_decisions(proposals) -> dict:
    """Group case-changing proposals by the WORD decision behind them.

    Returns ``{(old_word, new_word): {"count", "files", "examples"}}``.
    One ruling per key settles every file in ``files``.
    """
    out: dict = defaultdict(lambda: {"count": 0, "files": [], "examples": []})
    for p in proposals:
        old_t, new_t = _title_of(p["old_name"]), _title_of(p["name"])
        old_w, new_w = _WORD_RE.findall(old_t), _WORD_RE.findall(new_t)
        if len(old_w) != len(new_w):
            continue
        for a, b in zip(old_w, new_w):
            if a == b:
                continue
            e = out[(a, b)]
            e["count"] += 1
            e["files"].append(p["old"])
            if len(e["examples"]) < 3:
                e["examples"].append(old_t[:110])
    return dict(out)


def split_titles(proposals) -> dict:
    """Split title/both proposals into the three review groups."""
    groups: dict = {COSMETIC: [], FIRSTWORD: [], CASE: [], REWRITE: []}
    for p in proposals:
        groups[classify_proposal(p["old_name"], p["name"])].append(p)
    return groups


def proposals_for_words(proposals, approved: set) -> list:
    """Proposals whose every word change is in ``approved``.

    A file is only renamed once the owner has agreed to EVERY word
    change it contains — a title with one approved and one unreviewed
    change stays untouched rather than being half-applied.
    """
    ok = []
    for p in proposals:
        old_t, new_t = _title_of(p["old_name"]), _title_of(p["name"])
        old_w, new_w = _WORD_RE.findall(old_t), _WORD_RE.findall(new_t)
        if len(old_w) != len(new_w):
            continue
        changes = {(a, b) for a, b in zip(old_w, new_w) if a != b}
        if changes and changes <= approved:
            ok.append(p)
    return ok
