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

import re
import unicodedata
from pathlib import Path
from typing import Iterable, Set

#: Where the generated list lives, relative to the repository root.
VOCAB_PATH = Path(__file__).resolve().parents[2] / "config" / "author_surnames.txt"

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


def mine(library_root: Path) -> Set[str]:
    """Walk the in-scope library READ-ONLY and return lowercase surnames.

    Never writes. The library is irreplaceable data and a probe once polluted
    228 sidecars; this opens nothing and only reads directory entries.

    THE SECOND HALF OF THE WALK IS A FILTER, and it is what makes the
    vocabulary safe to use. A surname is kept only if the library's own TITLES
    treat it as a name -- either it never appears in lower case mid-title, or
    it appears capitalised more often than not.

    Without it, "law" is in the vocabulary (someone is called Law) and
    "Gauss's Law in electrostatics" keeps its capital L. Measured over the
    25,043 in-scope titles, the words the filter removes are exactly the
    collisions: law 0 capitalised / 240 lower, risk 0/778, price 1/252,
    case 1/211. The words it keeps are exactly the names: hunt 8/0, ray 16/0,
    morse 6/0, abel 6/0, gross 5/0, may 42/10, bell 4/1.

    It costs 10 of 1,043 recoveries. "root" is the notable loss -- 4
    capitalised ("the Root barrier") against 26 lower ("square root"), so the
    library's own usage says it is a common word here, and the filter is
    believed rather than overridden.
    """
    from processing.library_scope import exclusion_reason
    from processing.filename_ground_truth import decompose

    out: Set[str] = set()
    titles: list[str] = []
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
    return {n for n in out if _looks_like_a_name_in_titles(n, titles, out)}


def _title_case_census(titles: Iterable[str], vocab: Set[str]):
    """How often each candidate appears capitalised vs lower, mid-title."""
    upper: dict = {}
    lower: dict = {}
    for t in titles:
        for m in _TOKEN.finditer(t):
            if m.start() == 0:
                continue
            w = m.group()
            k = w.lower()
            if k not in vocab:
                continue
            bucket = upper if w[:1].isupper() else lower
            bucket[k] = bucket.get(k, 0) + 1
    return upper, lower


_CENSUS: tuple | None = None


def _looks_like_a_name_in_titles(name: str, titles, vocab) -> bool:
    global _CENSUS
    if _CENSUS is None:
        _CENSUS = _title_case_census(titles, vocab)
    upper, lower = _CENSUS
    lo = lower.get(name, 0)
    return lo == 0 or upper.get(name, 0) > lo


def write(names: Iterable[str], path: Path = VOCAB_PATH) -> int:
    names = sorted(set(names) - _NOT_SURNAMES)
    path.write_text(
        "# Surnames mined from this library's own author blocks.\n"
        "# GENERATED -- do not hand-edit; regenerate with\n"
        "#   processing.author_vocabulary.mine(get_library_root())\n"
        "# Used ONLY to preserve a capital that is already present. Never fed\n"
        "# to capitalization_whitelist, which imposes its spelling.\n"
        + "\n".join(names) + "\n",
        encoding="utf-8",
    )
    return len(names)


_CACHE: Set[str] | None = None


def surnames(path: Path = VOCAB_PATH) -> Set[str]:
    """The mined surnames, lowercase. Empty set if the file is absent.

    An absent file must DEGRADE, not raise: the caser runs inside a live
    Streamlit page, and the rule this feeds is an improvement, not a
    correctness requirement. Missing vocabulary means fewer capitals
    recovered, which is exactly the behaviour before it existed.
    """
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = {
                line.strip().lower()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            } - _NOT_SURNAMES
        except OSError:
            _CACHE = set()
    return _CACHE
