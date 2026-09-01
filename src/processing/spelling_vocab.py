"""The owner's rulings on suspected misspellings.

Deliberately a SEPARATE store from ``title_vocab``. That one answers "is
this word a proper noun or an ordinary word", which is a question about
CASING; this one answers "is this word spelled correctly", which is a
question about SPELLING. Filing a spelling ruling as ``proper`` would
also change how the word is capitalised everywhere — the same
scope-collision that once let an author-block rule rewrite mathematics
in 86 files under a batch labelled "cosmetic".

Three rulings, and the difference between the last two matters:

  correct   — a real word; stop flagging it, library-wide and for good.
  typo      — confirmed, with the correction, so a rename can be offered.
  deferred  — "not now". It does NOT stop the conformance report calling
              the file suspect, because it is still suspect; it only
              takes the row out of the owner's working queue. A checker
              that forgot a problem because someone looked away once is
              the failure this whole subsystem exists to end.

Lives in the library so Dropbox syncs it, like the sidecars and the
operation log — not in ``~/.mathpdf``, which does not sync.
"""
from __future__ import annotations

import json
import re
import logging
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

VOCAB_DIRNAME = ".mathpdf-config"
VOCAB_FILENAME = "spelling_rulings.json"

CORRECT = "correct"
TYPO = "typo"
DEFERRED = "deferred"
_KINDS = (CORRECT, TYPO, DEFERRED)


def rulings_path(library_root: Path) -> Path:
    return library_root / VOCAB_DIRNAME / VOCAB_FILENAME


def _norm(word: str) -> str:
    return unicodedata.normalize("NFC", word.strip()).lower()


def load_rulings(library_root: Path) -> dict:
    """``{"correct": set, "typo": {word: correction}, "deferred": set}``.

    A missing or corrupt file degrades to empty and never raises: an
    unreadable ruling store must not stop the owner seeing his queue.
    """
    empty = {CORRECT: set(), TYPO: {}, DEFERRED: set(), "_extra": {}}
    try:
        raw = json.loads(rulings_path(library_root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return empty
    if not isinstance(raw, dict):
        logger.warning("spelling_rulings.json is not an object; ignoring")
        return empty
    return {
        CORRECT: {_norm(w) for w in raw.get(CORRECT, []) if str(w).strip()},
        TYPO: {_norm(w): str(c) for w, c in dict(raw.get(TYPO, {})).items()
               if str(w).strip()},
        DEFERRED: {_norm(w) for w in raw.get(DEFERRED, []) if str(w).strip()},
        # Anything a future version adds. _save writes it back untouched,
        # so an older build cannot silently delete a newer build's data —
        # the shape that would have wiped fifteen phrase rulings from
        # title_vocab if load_vocab had ever stopped returning "phrases".
        "_extra": {k: v for k, v in raw.items() if k not in _KINDS},
    }


def _save(library_root: Path, rulings: dict) -> None:
    from core.io import atomic_write_text
    p = rulings_path(library_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(rulings.get("_extra", {}))
    payload[CORRECT] = sorted(rulings[CORRECT])
    payload[TYPO] = {w: rulings[TYPO][w] for w in sorted(rulings[TYPO])}
    payload[DEFERRED] = sorted(rulings[DEFERRED])
    atomic_write_text(p, json.dumps(payload, indent=2, ensure_ascii=False))


def rule(library_root: Path, word: str, kind: str,
         correction: str = "") -> None:
    """Record a ruling.  RAISES on bad input.

    A ruling that silently does nothing is worse than an error: the owner
    believes he has settled the word and it returns on the next sweep.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}, got {kind!r}")
    w = _norm(word)
    if not w:
        raise ValueError("word must not be empty")
    if kind == TYPO and not correction.strip():
        raise ValueError(
            f"confirming {word!r} as a typo needs the correction; recording "
            "'this is wrong' without saying what is right leaves a queue "
            "entry nobody can act on")
    r = load_rulings(library_root)
    # A word holds exactly one ruling; re-ruling replaces it.
    r[CORRECT].discard(w)
    r[DEFERRED].discard(w)
    r[TYPO].pop(w, None)
    if kind == CORRECT:
        r[CORRECT].add(w)
    elif kind == DEFERRED:
        r[DEFERRED].add(w)
    else:
        r[TYPO][w] = correction.strip()
    _save(library_root, r)


def clear_ruling(library_root: Path, word: str) -> bool:
    """Undo a ruling.  Returns True if one was removed.

    Every ruling needs a route back. The title vocabulary shipped without
    one: a word left the pending list and no screen ever showed it again,
    while it silently shaped every future filename.
    """
    w = _norm(word)
    r = load_rulings(library_root)
    had = w in r[CORRECT] or w in r[DEFERRED] or w in r[TYPO]
    if not had:
        return False
    r[CORRECT].discard(w)
    r[DEFERRED].discard(w)
    r[TYPO].pop(w, None)
    _save(library_root, r)
    return True


def ruling_for(library_root: Path, word: str) -> str:
    w = _norm(word)
    r = load_rulings(library_root)
    if w in r[CORRECT]:
        return CORRECT
    if w in r[TYPO]:
        return TYPO
    if w in r[DEFERRED]:
        return DEFERRED
    return ""


def accepted_words(library_root: Path) -> frozenset:
    """Words ruled correct — the only kind that suppresses detection.

    ``deferred`` deliberately does NOT appear here: postponing a decision
    does not make the word right, and the conformance report must keep
    saying so.
    """
    return frozenset(load_rulings(library_root)[CORRECT])


def apply_case_of(original: str, replacement: str) -> str:
    """Give *replacement* the capitalisation of the word it replaces.

    THE BUG THIS FIXES DAMAGED A REAL TITLE. Suggestions come from
    ``maintenance.typos.nearest_frequent``, which looks them up in a corpus
    keyed on LOWER-CASE words, so every suggestion arrives lower case. The
    Spelling page substituted it verbatim:

        "Browniam motion"        ->  "brownian motion"     (want Brownian)
        "Makov chains revisited" ->  "markov chains ..."   (want Markov)
        "On BROWNIAM motion"     ->  "On brownian motion"  (want BROWNIAN)

    The owner hit the third-worst version of this -- the misspelled word
    STARTED the title, so the fix silently lower-cased the first letter of
    the filename, and he had to find the file again and put it back.

    Three shapes, and nothing else is inferred:

        Xxxxx  -> capitalise    a name or a title-initial word
        XXXXX  -> upper         an acronym
        xxxxx  -> leave alone   ordinary prose

    A mixed shape like "McDonald" is left as the suggestion gives it, because
    guessing an interior capital is how "MacKean" becomes "Mckean".
    """
    if not original or not replacement:
        return replacement
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _title_starts_at(name: str) -> int:
    """Index in *name* where the title begins.

    Asks ``processing.filename_ground_truth.decompose``, which is this
    project's single answer to where the author block ends. Rolling a second
    rule here would be a rival implementation, and the obvious guess is
    WRONG: the title starts after the FIRST " - ", not the last, because a
    title may itself contain one --

        "Bouchard, B. - An introduction ... - Lecture 2 - Price models"
                        ^ the title starts here

    An earlier draft used rfind and would have forced a capital in the middle
    of that title. Mutation testing flagged the difference and the decomposer
    settled it.

    Falls back to the first " - " if the name cannot be decomposed reliably;
    that is the same rule for the ordinary case and simply less careful about
    the exotic ones.
    """
    try:
        from processing.filename_ground_truth import decompose
        d = decompose(name[:-4] if name.lower().endswith(".pdf") else name)
        title = getattr(d, "title", None)
        if title:
            idx = name.find(str(title))
            if idx >= 0:
                return idx
    except Exception:                            # pragma: no cover - defensive
        pass
    sep = name.find(" - ")
    return sep + 3 if sep >= 0 else 0


def replace_preserving_case(name: str, word: str, suggestion: str) -> str:
    """Swap *word* for *suggestion* in *name*, keeping the original's case.

    Also forces a capital when the replaced word STARTS THE TITLE, whatever
    case the original carried -- a title's first word is capitalised by
    convention, so a lower-case original there is itself the error and must
    not be propagated.
    """
    start = _title_starts_at(name)

    # Search only the TITLE, and only on a word boundary.
    #
    # A plain name.find(word) reaches into the author block and matches
    # inside a longer surname. Found by an audit of this very function:
    #
    #   "Makovski, D. - Makov chains for finance.pdf"
    #        ^^^^^ matched here
    #   ->  "Markovski, D. - Makov chains for finance.pdf"
    #
    # which corrupts the AUTHOR and leaves the typo in place. The suspect
    # words come from maintenance.typos, which tokenises the TITLE, so the
    # title is the only place the match belongs; and the boundary check stops
    # a short typo matching inside a longer word anywhere.
    pattern = re.compile(r"(?<![^\W\d_])" + re.escape(word) + r"(?![^\W\d_])")
    m = pattern.search(name, start)
    if m is None:
        return name
    idx = m.start()
    replacement = apply_case_of(word, suggestion)
    if idx == start:
        replacement = replacement[:1].upper() + replacement[1:]
    return name[:idx] + replacement + name[idx + len(word):]
