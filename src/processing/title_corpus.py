"""Corpus-derived word-casing statistics — the title caser's oracle.

External dictionaries are unsound for deciding "is this an ordinary
word": this project's own spellchecker deliberately knows mathematician
names (Edgeworth, Nirenberg, Saks…) so they don't flag as typos, and any
English dictionary contains place/name homographs (May, Nice, Bath).

The sound oracle is the library itself: across ~29k of the owner's own
canonical filenames, an ordinary word occurs LOWERCASE mid-title over and
over ("existence" 500×, "equations" 2000×), while an eponym essentially
never does ("edgeworth" 0×).  ``word_stats`` counts, for every mid-title
word, how often it appears lowercase vs capitalized; the caser then
lowercases a capitalized word only when the corpus overwhelmingly writes
it lowercase.

Stats are cached at ``<lib>/.mathpdf-config/title_corpus_stats.json``
(atomic write, auto-rebuilt when older than REBUILD_DAYS) — a filename
walk only, ~seconds on 29k papers.
"""
from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

STATS_FILENAME = "title_corpus_stats.json"
REBUILD_DAYS = 7

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def stats_path(library_root: Path) -> Path:
    return library_root / ".mathpdf-config" / STATS_FILENAME


def build_word_stats(library_root: Path) -> dict:
    """Walk library FILENAMES and count mid-title word casings.

    Returns ``{word_lower: [n_lowercase, n_capitalized]}`` counting only
    words strictly after the first title word (first words are always
    capitalized by convention and carry no signal).
    """
    from processing.identity import iter_pdfs

    counts: dict = {}
    for pdf in iter_pdfs(library_root):
        name = unicodedata.normalize("NFC", pdf.stem)
        if " - " not in name:
            continue
        title = name.split(" - ", 1)[1]
        words = _WORD_RE.findall(title)
        for w in words[1:]:                     # skip the title's first word
            if len(w) < 2:
                continue
            key = w.lower()
            slot = counts.setdefault(key, [0, 0])
            if w[0].isupper():
                slot[1] += 1
            elif w.islower():
                slot[0] += 1
    return counts


def load_word_stats(library_root: Path, *, auto_build: bool = True) -> dict:
    """Load cached stats; (re)build when missing/stale and ``auto_build``.

    Degrades to ``{}`` on any error — the caser then falls back to its
    built-in function-word list and queues the rest (never damages).
    """
    p = stats_path(library_root)
    try:
        if p.exists() and (time.time() - p.stat().st_mtime) < REBUILD_DAYS * 86400:
            return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    if not auto_build:
        return {}
    try:
        stats = build_word_stats(library_root)
        try:
            from core.io import atomic_write_text
            p.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(p, json.dumps(stats, ensure_ascii=False))
        except Exception:  # cache write is best-effort
            logger.debug("could not cache title corpus stats", exc_info=True)
        return stats
    except Exception as exc:  # pragma: no cover — never block a caller
        logger.warning("could not build title corpus stats: %s", exc)
        return {}


def corpus_says_common(word: str, stats: dict) -> bool:
    """True when the corpus overwhelmingly writes ``word`` lowercase.

    Thresholds: seen lowercase at least 5 times AND at least 5× as often
    lowercase as capitalized.  Conservative on purpose — a borderline word
    stays "uncertain" and goes to the vocabulary review instead.
    """
    n_low, n_cap = stats.get(word.lower(), (0, 0))
    return n_low >= 5 and n_low >= 5 * max(n_cap, 1)
