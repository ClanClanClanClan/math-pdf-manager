"""Surnames, mined from the library's own author blocks.

WHY THIS EXISTS. ``core.sentence_case`` lowercases every capitalised word it
does not recognise, and no hand-curated whitelist can hold every
mathematician. Measured over the 25,049 in-scope titles, that cost 2,964
mid-title capitals: Bourbaki 64, Fock 22, Landau 15, Azéma 13, Hartree 12,
Paley 12, Doeblin 9, Gronwall 8.

The library already knows these names. Every filename carries an author
block, and ``filename_ground_truth.decompose`` reads it reliably for 99.9% of
them. So the vocabulary is not curated, it is DERIVED -- and a new eponym
arrives with its first paper rather than with a hand-edited config entry.

WHAT THIS IS NOT. The names here are used ONLY to preserve a capital that is
already there. They are never added to ``capitalization_whitelist``, because
a whitelist entry in that config IMPOSES its spelling: matching is
case-insensitive and the entry's own capitalisation is emitted. Measured on
the shipped 848-entry list, that already imposes 263 wrong capitals --
"sur le grossissement" becomes "sur Le grossissement" 103 times. Feeding
11,782 surnames into the same mechanism was measured at 5,823 imposed
capitals. See docs/proper-nouns-measured.md.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Set

_CONFIG = Path(__file__).resolve().parents[2] / "config"

#: The mined vocabulary and the evidence behind it. GENERATED.
VOCAB_PATH = _CONFIG / "author_surnames.json"

#: The owner's own calls, which beat the evidence. HAND-EDITED via the
#: cockpit. Never overwritten by a re-mine.
DECISIONS_PATH = _CONFIG / "surname_decisions.json"

#: How lopsided the evidence must be before a word is decided without asking.
#: Below this, the word goes to the review queue instead.
#:
#: Measured over the 25,043 in-scope titles: of 11,779 mined surnames, 10,925
#: never appear in a title at all, 731 appear only capitalised, 84 only in
#: lower case, and just 39 appear BOTH WAYS. At 6:1 that 39 splits into a
#: handful decided either way and a short queue for the owner -- small enough
#: to read, which is the point of asking at all.
DOMINANCE = 6

NAME = "name"
COMMON = "common"
REVIEW = "review"

#: Tokens that reach an author block but are not surnames.
#:
#: MONTHS IN EVERY LANGUAGE THE LIBRARY USES. This is not hypothetical
#: tidiness: "Juillet" is a real probabilist's surname AND French for July,
#: and it produced 3 of the 4 measured errors of the rule this vocabulary
#: feeds. An English dictionary cannot find these, which is why they are
#: listed rather than filtered.
_NOT_SURNAMES = {
    # French
    "janvier", "février", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "août", "aout", "septembre", "octobre", "novembre", "décembre",
    "decembre",
    # Italian
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
    "agosto", "settembre", "ottobre", "novembre", "dicembre",
    # German
    "januar", "februar", "märz", "maerz", "april", "juni", "juli", "august",
    "september", "oktober", "november", "dezember",
    # Spanish / Portuguese
    "enero", "febrero", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
    # editorial words that ride along in an author slot
    "editors", "editor", "eds", "ed", "herausgeber", "collectif", "anonymous",
    "unknown", "various", "et", "al",
}

_TOKEN = re.compile(r"[^\W\d_]{2,}", re.UNICODE)


def _clean(token: str) -> str:
    return unicodedata.normalize("NFC", token)


def mine(library_root: Path):
    """Walk the in-scope library READ-ONLY. Returns (surnames, evidence).

    Never writes. The library is irreplaceable data and a probe once polluted
    228 sidecars; this opens nothing and only reads directory entries.

    ``evidence`` maps a surname to (capitalised, lower-case) counts of how the
    library's own TITLES use it, mid-title. That is the whole basis for
    deciding whether a mined surname may be treated as a name: someone is
    called Law, Price, Case and Root, but the titles say those words are
    common nouns here.

    The title's FIRST word is never counted. Every title starts with a
    capital, so it is evidence about nothing.
    """
    from processing.library_scope import exclusion_reason
    from processing.filename_ground_truth import decompose

    out: Set[str] = set()
    titles: list = []
    root = Path(library_root)
    for pdf in root.rglob("*.pdf"):
        try:
            rel = str(pdf.relative_to(root))
        except ValueError:                       # pragma: no cover - defensive
            continue
        if exclusion_reason(rel):
            continue
        d = decompose(_clean(pdf.stem))
        if not (getattr(d, "reliability", None)
                and "RELIABLE" in str(d.reliability)):
            continue
        title = getattr(d, "title", None)
        if title:
            titles.append(_clean(str(title)))
        block = getattr(d, "authors", None) or getattr(d, "author_block", None)
        if not block:
            continue
        for segment in str(block).split(","):
            segment = segment.strip()
            if not segment or "." in segment:    # an initials group, not a name
                continue
            for tok in _TOKEN.findall(segment):
                if tok[:1].isupper():
                    out.add(tok.lower())
    out -= _NOT_SURNAMES

    upper: dict = {}
    lower: dict = {}
    for t in titles:
        for m in _TOKEN.finditer(t):
            if m.start() == 0:
                continue
            w = m.group()
            k = w.lower()
            if k not in out:
                continue
            bucket = upper if w[:1].isupper() else lower
            bucket[k] = bucket.get(k, 0) + 1

    evidence = {k: (upper.get(k, 0), lower.get(k, 0))
                for k in out if upper.get(k) or lower.get(k)}
    return out, evidence


def verdict(up: int, low: int) -> str:
    """NAME, COMMON or REVIEW, from the title evidence alone.

    * no lower-case use at all -> NAME. Nothing argues against it.
    * no capitalised use at all -> COMMON. The library only ever writes it
      as an ordinary word, whoever else may be called that.
    * one side at least DOMINANCE times the other -> that side.
    * anything else -> REVIEW. The evidence is genuinely mixed and the
      owner is the one who should say.
    """
    if up and not low:
        return NAME
    if low and not up:
        return COMMON
    if not up and not low:
        return NAME          # never used in a title; nothing can go wrong
    if up >= low * DOMINANCE:
        return NAME
    if low >= up * DOMINANCE:
        return COMMON
    return REVIEW


def write(names, evidence=None, path: Path = VOCAB_PATH) -> int:
    """Persist the mined vocabulary and its evidence."""
    names = sorted(set(names) - _NOT_SURNAMES)
    evidence = {k: list(v) for k, v in (evidence or {}).items()
                if k not in _NOT_SURNAMES}
    path.write_text(json.dumps({
        "_readme": (
            "GENERATED by processing.author_vocabulary.mine(). Do not "
            "hand-edit -- put your own calls in surname_decisions.json, "
            "which survives a re-mine. 'evidence' is [capitalised, lower] "
            "counts of how this library's own titles use the word "
            "mid-title; it is what decides whether a mined surname may be "
            "treated as a name."
        ),
        "names": names,
        "evidence": evidence,
    }, ensure_ascii=False, indent=0), encoding="utf-8")
    return len(names)


def load_decisions(path: Path = DECISIONS_PATH) -> dict:
    """The owner's own calls: {word: "name"|"common"}.

    Kept in a separate file from the generated vocabulary precisely so a
    re-mine cannot erase them.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for k, v in (raw.get("decisions") or {}).items():
        if isinstance(v, str) and v in (NAME, COMMON):
            out[str(k).lower()] = v
        elif isinstance(v, dict) and v.get("verdict") in (NAME, COMMON):
            out[str(k).lower()] = v["verdict"]
    return out


def save_decision(word: str, call: str, path: Path = DECISIONS_PATH,
                  evidence=None) -> None:
    """Record one call, with the evidence it was made against.

    The evidence is stored so that a LATER re-mine can notice the world has
    moved: a word first seen as a common noun may turn up as a mathematician
    once that person publishes, and the reverse happens too. See
    ``needs_recheck``.
    """
    if call not in (NAME, COMMON):
        raise ValueError(f"a decision must be {NAME!r} or {COMMON!r}, not {call!r}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    decisions = raw.get("decisions") or {}
    decisions[word.lower()] = {
        "verdict": call,
        "decided_against": list(evidence) if evidence else None,
    }
    raw["_readme"] = (
        "Your calls on words that are both a surname and an ordinary word. "
        "This file is never overwritten by a re-mine. 'decided_against' is "
        "the evidence at the time you decided; if the library's usage later "
        "moves a long way from it, the word comes back for another look."
    )
    raw["decisions"] = decisions
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    global _CACHE, _EVIDENCE, _DECISIONS
    _CACHE = _EVIDENCE = _DECISIONS = None


def needs_recheck(word: str, now, then) -> bool:
    """Has the evidence moved far enough to ask again?

    THE CASE THIS EXISTS FOR, in the owner's words: a word may "first appear
    as a noun, and later show up as a mathematician, and conversely". A
    decision taken on 2 capitals against 30 should not be trusted for ever
    once the counts read 40 against 30.

    The test is on the VERDICT the evidence would now give, not on the raw
    counts: a word comes back only if the evidence has crossed from one side
    of the dominance rule to the other, or into the review band from outside
    it. Small drifts are ignored, or the queue would never empty.
    """
    if not then:
        return False
    was = verdict(*then)
    is_now = verdict(*now)
    return was != is_now


_CACHE: Set[str] | None = None
_EVIDENCE: dict | None = None
_DECISIONS: dict | None = None


_CACHE: Set[str] | None = None


def _load(path: Path = VOCAB_PATH):
    """(all mined names, evidence). Empty on any failure -- never raises."""
    global _EVIDENCE
    names: Set[str] = set()
    ev: dict = {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        names = {str(n).lower() for n in raw.get("names") or ()} - _NOT_SURNAMES
        ev = {str(k).lower(): tuple(v)
              for k, v in (raw.get("evidence") or {}).items()
              if str(k).lower() not in _NOT_SURNAMES}
    except (OSError, ValueError):
        pass
    _EVIDENCE = ev
    return names, ev


def evidence(path: Path = VOCAB_PATH) -> dict:
    """{word: (capitalised, lower)} from the library's own titles."""
    if _EVIDENCE is None:
        _load(path)
    return _EVIDENCE or {}


def decisions(path: Path = DECISIONS_PATH) -> dict:
    global _DECISIONS
    if _DECISIONS is None:
        _DECISIONS = load_decisions(path)
    return _DECISIONS


def surnames(path: Path = VOCAB_PATH,
             decisions_path: Path = DECISIONS_PATH) -> Set[str]:
    """The names the caser may preserve a capital on.

    A mined surname qualifies when the evidence says NAME, or when the owner
    has said so. A word in the REVIEW band is NOT used until decided -- an
    unanswered question must not quietly act as a yes, which is the same
    three-valued discipline the rest of this project runs on.

    An absent or unreadable vocabulary DEGRADES to the empty set rather than
    raising: this runs inside a live Streamlit page, and the rule it feeds is
    an improvement, not a correctness requirement. Missing vocabulary means
    fewer capitals recovered, which is exactly the behaviour before it
    existed.
    """
    global _CACHE
    if _CACHE is None:
        names, ev = _load(path)
        mine_said = {n for n in names if verdict(*ev.get(n, (0, 0))) == NAME}
        owner = decisions(decisions_path)
        _CACHE = ((mine_said | {w for w, v in owner.items() if v == NAME})
                  - {w for w, v in owner.items() if v == COMMON})
    return _CACHE


def review_queue(path: Path = VOCAB_PATH,
                 decisions_path: Path = DECISIONS_PATH) -> list:
    """Words the library uses BOTH ways, for the owner to settle.

    Each entry is a dict: word, capitalised, lower, suggestion, decided,
    and why it is being asked about. Sorted with the closest calls first,
    because those are the ones where a human actually adds something.

    Two things land here:

    * a word whose evidence is genuinely mixed (neither side dominates), and
    * a word already decided whose evidence has since crossed to the other
      side of the rule -- the "first a noun, later a mathematician, and
      conversely" case. Those carry ``changed_since_you_decided``.
    """
    names, ev = _load(path)
    owner = decisions(decisions_path)
    out = []
    for word, counts in ev.items():
        if word not in names:
            continue
        up, low = counts
        auto = verdict(up, low)
        was = owner.get(word)
        moved = False
        if was:
            stored = load_decisions(decisions_path)
            raw = _decided_against(word, decisions_path)
            moved = needs_recheck(word, counts, raw)
            if not moved:
                continue                     # settled, and still settled
        elif auto != REVIEW:
            continue                         # the evidence is clear enough
        out.append({
            "word": word,
            "capitalised": up,
            "lower": low,
            "suggestion": auto,
            "decided": was,
            "changed_since_you_decided": moved,
        })
    # closest call first: a ratio near 1 is where a human is worth asking
    def _closeness(row):
        up, low = row["capitalised"], row["lower"]
        hi, lo = max(up, low), min(up, low)
        return (0 if row["changed_since_you_decided"] else 1,
                hi / lo if lo else 1e9)
    return sorted(out, key=_closeness)


def _decided_against(word: str, path: Path = DECISIONS_PATH):
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    rec = (raw.get("decisions") or {}).get(word.lower())
    if isinstance(rec, dict):
        got = rec.get("decided_against")
        if isinstance(got, (list, tuple)) and len(got) == 2:
            return tuple(got)
    return None
