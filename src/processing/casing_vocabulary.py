"""Which words this library capitalises, learned from the library itself.

WHY THIS EXISTS. ``core.sentence_case`` lowercases every capitalised word it
does not recognise, and no hand-curated whitelist can hold every
mathematician, city, month and journal. Measured over the 25,043 in-scope
titles, that destroyed 2,964 mid-title capitals: Bourbaki 64, Saint-Flour 59,
Fock 22, Japan 22, Landau 15, Azema 13, Hartree 12, Doeblin 9, Gronwall 8,
every month of the year, and Possamai.

THE LIBRARY ALREADY KNOWS. It writes "Saint-Flour" 59 times and "flour" never;
"stochastic" 3,333 times in lower case and 3 capitalised. So the vocabulary is
not curated, it is a CENSUS: for every word, how often this library's own
titles write it capitalised mid-title, and how often in lower case. That one
table answers mathematicians, places, months, Roman numerals and ordinary
prose with a single rule and no lists at all.

The title's FIRST word is never counted -- every title starts with a capital,
so it is evidence about nothing. Titles that are themselves Title Cased are
excluded from the census for the same reason: every word in them carries a
capital that means nothing.

WHAT THIS IS NOT. These words are used ONLY to preserve a capital that is
already there. They are never added to ``capitalization_whitelist``, because
an entry in that config IMPOSES its spelling: matching is case-insensitive
and the entry's own capitalisation is emitted. Measured, the shipped 848-entry
list already imposes 267 wrong capitals -- "sur le grossissement" becomes
"sur Le grossissement" 131 times, and "well-posedness" becomes
"well-Posedness" 86 times.

THREE-VALUED, like everything else here. A word whose evidence is mixed is not
guessed at: it is HELD BACK and put in front of the owner. See ``verdict`` and
``review_queue``. Author surnames are still mined, but only as a HINT shown
beside a question -- knowing that Green is an author in this library helps the
owner answer, and no longer decides anything on its own.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Set

_CONFIG = Path(__file__).resolve().parents[2] / "config"

#: The census and the author hint. GENERATED.
VOCAB_PATH = _CONFIG / "title_casing.json"

#: The owner's own calls, which beat the evidence. Written by the cockpit.
#: Never overwritten by a re-mine.
DECISIONS_PATH = _CONFIG / "casing_decisions.json"

#: How lopsided the evidence must be before a word is decided without asking.
#: Below this, the word goes to the review queue instead.
#:
#: Measured over the 25,043 in-scope titles and all 10,866 distinct mid-title
#: words: 2,375 are only ever capitalised, 8,368 only ever lower case, and
#: 123 are genuinely mixed. At 6:1 that leaves a queue of 123 -- long enough
#: to be worth sorting closest-call-first, short enough to read.
DOMINANCE = 6

NAME = "name"
COMMON = "common"
REVIEW = "review"

#: Tokens that reach an AUTHOR BLOCK but are not surnames.
#:
#: This list guards the author set ONLY, never the census. The census gets
#: months right by itself, and per language: measured, the library writes
#: April 38/0 and September 13/0 (English capitalises months) but mai 0/7,
#: juin 0/10 and septembre 0/2 (French does not), and juillet 3/1 and May
#: 42/10 land in the review band where they belong. Filtering the census
#: with this list removed the English months from the vocabulary and cost
#: real recoveries -- caught by a test asserting April survives.
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


def _is_title_cased(title: str) -> bool:
    """Does this title carry a capital on nearly every word?

    Such a title is evidence about nothing -- its capitals are a house style,
    not a claim that any particular word is a proper noun -- so it is left out
    of the census. Measured: 19 of the 25,043 in-scope titles read this way,
    affecting the counts of 85 words. A small correction, but a free one.
    """
    words = [m.group() for m in _TOKEN.finditer(title)][1:]
    if len(words) < 3:
        return False
    caps = sum(1 for w in words if w[:1].isupper())
    return caps / len(words) >= 0.70


def mine(library_root: Path):
    """Walk the in-scope library READ-ONLY. Returns (evidence, authors).

    Never writes. The library is irreplaceable data and a probe once polluted
    228 sidecars; this opens nothing and only reads directory entries.

    ``evidence`` maps every mid-title word to (capitalised, lower-case)
    counts -- the census this module exists for. ``authors`` is the set of
    surnames appearing in author blocks, kept ONLY as a hint to show beside a
    question in the review queue.
    """
    from processing.library_scope import exclusion_reason
    from processing.filename_ground_truth import decompose

    authors: Set[str] = set()
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
                    authors.add(tok.lower())
    authors -= _NOT_SURNAMES

    upper: dict = {}
    lower: dict = {}
    for t in titles:
        if _is_title_cased(t):
            continue
        for m in _TOKEN.finditer(t):
            if m.start() == 0:
                continue
            w = m.group()
            k = w.lower()
            bucket = upper if w[:1].isupper() else lower
            bucket[k] = bucket.get(k, 0) + 1

    evidence = {k: (upper.get(k, 0), lower.get(k, 0))
                for k in set(upper) | set(lower)}
    return evidence, authors


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


def write(evidence, authors=(), path: Path = VOCAB_PATH) -> int:
    """Persist the census and the author hint."""
    evidence = {k: list(v) for k, v in dict(evidence).items()}
    path.write_text(json.dumps({
        "_readme": (
            "GENERATED by processing.casing_vocabulary.mine(). Do not "
            "hand-edit -- put your own calls in casing_decisions.json, which "
            "survives a re-mine. 'evidence' is [capitalised, lower] counts of "
            "how this library's own titles write each word MID-TITLE, "
            "ignoring the first word of every title and any title that is "
            "itself Title Cased. 'authors' is only a hint shown beside a "
            "question; it decides nothing."
        ),
        "evidence": evidence,
        "authors": sorted(set(authors) - _NOT_SURNAMES),
    }, ensure_ascii=False, indent=0), encoding="utf-8")
    return len(evidence)


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
    global _CACHE, _EVIDENCE, _AUTHORS, _DECISIONS
    _CACHE = _EVIDENCE = _AUTHORS = _DECISIONS = None


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
_AUTHORS: Set[str] | None = None
_DECISIONS: dict | None = None


_CACHE: Set[str] | None = None


def _load(path: Path = VOCAB_PATH):
    """(evidence, authors). Empty on any failure -- never raises."""
    global _EVIDENCE, _AUTHORS
    ev: dict = {}
    au: Set[str] = set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        ev = {str(k).lower(): tuple(v)
              for k, v in (raw.get("evidence") or {}).items()}
        au = {str(a).lower() for a in raw.get("authors") or ()} - _NOT_SURNAMES
    except (OSError, ValueError):
        pass
    _EVIDENCE, _AUTHORS = ev, au
    return ev, au


def evidence(path: Path = VOCAB_PATH) -> dict:
    """{word: (capitalised, lower)} from this library's own titles."""
    if _EVIDENCE is None:
        _load(path)
    return _EVIDENCE or {}


def authors(path: Path = VOCAB_PATH) -> Set[str]:
    """Surnames seen in author blocks. A HINT for the review queue only."""
    if _AUTHORS is None:
        _load(path)
    return _AUTHORS or set()


def decisions(path: Path = DECISIONS_PATH) -> dict:
    global _DECISIONS
    if _DECISIONS is None:
        _DECISIONS = load_decisions(path)
    return _DECISIONS


def preserved(path: Path = VOCAB_PATH,
              decisions_path: Path = DECISIONS_PATH) -> Set[str]:
    """Words whose existing capital the caser may keep.

    A word qualifies when the census says NAME, or when the owner has said
    so. A word in the REVIEW band is NOT used until decided -- an unanswered
    question must not quietly act as a yes.

    An absent or unreadable vocabulary DEGRADES to the empty set rather than
    raising: this runs inside a live Streamlit page, and the rule it feeds is
    an improvement, not a correctness requirement. Missing vocabulary means
    fewer capitals recovered, which is the behaviour before it existed.
    """
    global _CACHE
    if _CACHE is None:
        ev, au = _load(path)
        census_said = {w for w, c in ev.items() if verdict(*c) == NAME}
        # WHERE THE CENSUS IS SILENT, ask the author blocks. A word that
        # never appears mid-title has no title evidence at all, so the census
        # cannot speak for it -- but if the library has an author of that
        # name, that is evidence of a different kind.
        #
        # This is what keeps "Le Cam" and "Le Gall": neither "cam" nor "gall"
        # appears mid-title anywhere in the library, so both are invisible to
        # the census, and both are authors. Without the fallback the caser
        # produced "Le cam" and "Le gall".
        #
        # It is deliberately a FALLBACK and not a source: where the census
        # HAS spoken it wins, so "law" stays a common word (0 capitalised
        # against 240) however many people are called Law. And it changes
        # nothing on today's library by construction -- a word with no title
        # evidence appears in no title -- so its whole effect is on titles
        # arriving later from ingest.
        silent = {w for w in au if w not in ev}
        owner = decisions(decisions_path)
        _CACHE = ((census_said | silent | {w for w, v in owner.items() if v == NAME})
                  - {w for w, v in owner.items() if v == COMMON})
    return _CACHE


def is_common(word: str, path: Path = VOCAB_PATH,
              decisions_path: Path = DECISIONS_PATH) -> bool:
    """Does this library's own usage say the word is an ordinary one?

    Used to stop ``capitalization_whitelist`` IMPOSING a capital against the
    library. Five shipped entries do exactly that today -- Le, posedness,
    White, Bank, Hold -- between them turning 267 lower-case occurrences
    upper: "sur le grossissement" -> "sur Le grossissement" 131 times, and
    "well-posedness" -> "well-Posedness" 86.
    """
    w = word.lower()
    owner = decisions(decisions_path)
    if w in owner:
        return owner[w] == COMMON
    ev = evidence(path).get(w)
    return bool(ev) and verdict(*ev) == COMMON


#: Adjectives French builds FROM a mathematician's name -- "processus
#: gaussiens", "operateur laplacien". French lower-cases these where English
#: would not, so they are the one class where this library's own usage might
#: be systematically wrong rather than merely house style.
#:
#: MEASURED: the plurals are already caught by the census -- gaussiens 9/7,
#: markoviens 5/1 and boreliens 3/1 all land in REVIEW, browniens 0/14 in
#: COMMON, and none is recovered. The singular and feminine forms are not:
#: Gaussiennes 4/0, Laplacien 1/0, Borelien 2/0, Hamiltonienne 1/0. On those
#: the library is unanimous, so the census is believed and the capital kept --
#: overruling a unanimous measurement with a morphology guess is exactly the
#: hand-rule this design exists to avoid. They are FLAGGED instead: applied,
#: and listed for the owner, who is the one who knows.
_NAME_ADJECTIVE = re.compile(
    r"^.{4,}(ien|iens|ienne|iennes|ique|iques|iste|istes)$", re.IGNORECASE)


def review_queue(path: Path = VOCAB_PATH,
                 decisions_path: Path = DECISIONS_PATH) -> list:
    """Words the owner should settle, closest call first.

    Three things land here:

    * ``held`` -- the census is genuinely mixed, so the capital is NOT being
      preserved until answered;
    * ``flagged`` -- the census is unanimous and IS being applied, but the
      word is a French adjective built from a name, the one shape where a
      unanimous library may still be wrong;
    * ``changed_since_you_decided`` -- an answer whose evidence has since
      crossed to the other side of the rule. The "first a noun, later a
      mathematician, and conversely" case.
    """
    ev, au = _load(path)
    owner = decisions(decisions_path)
    out = []
    for word, counts in ev.items():
        up, low = counts
        auto = verdict(up, low)
        was = owner.get(word)
        moved = False
        if was:
            moved = needs_recheck(word, counts, _decided_against(word, decisions_path))
            if not moved:
                continue
            kind = "changed"
        elif auto == REVIEW:
            kind = "held"
        elif auto == NAME and up and not low and _NAME_ADJECTIVE.match(word):
            kind = "flagged"
        else:
            continue
        out.append({
            "word": word,
            "capitalised": up,
            "lower": low,
            "suggestion": auto,
            "decided": was,
            "kind": kind,
            "held_back": kind in ("held",),
            "is_author": word in au,
            "changed_since_you_decided": moved,
        })

    def _order(row):
        up, low = row["capitalised"], row["lower"]
        hi, lo = max(up, low), min(up, low)
        rank = {"changed": 0, "held": 1, "flagged": 2}[row["kind"]]
        return (rank, hi / lo if lo else 1e9, -(up + low))
    return sorted(out, key=_order)


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
