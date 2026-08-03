"""User title-vocabulary store — the learning loop for title normalization.

The safe-default title caser (``processing.title_normalize``) never
lowercases a word it cannot prove is an ordinary common word.  Words it
can't classify are queued here as *pending*; the owner settles each one
ONCE in the cockpit ("proper noun — keep capitalized" vs "common word —
lowercase") and the decision applies library-wide forever after.

The vocabulary lives IN the library (``<lib>/.mathpdf-config/
title_vocab.json``) so it syncs across machines with Dropbox, exactly
like the sidecars and the operation log.  Writes go through the atomic
helper; a torn/concurrent write can at worst lose a pending-word count,
never a decision that was already saved by the last writer.
"""
from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

VOCAB_DIRNAME = ".mathpdf-config"
VOCAB_FILENAME = "title_vocab.json"

# Parsed-vocab cache keyed by (path, mtime).  A library-wide title sweep
# resolves every filename through the caser, which loads the vocabulary
# once per file; without this each call would re-parse the JSON and
# NFC-normalise every word.  Callers receive a fresh COPY (below) so their
# in-place mutations never poison the cache, and any atomic rewrite bumps
# mtime and invalidates the stale entry.
_VOCAB_CACHE: dict = {}


def vocab_path(library_root: Path) -> Path:
    return library_root / VOCAB_DIRNAME / VOCAB_FILENAME


def _norm(word: str) -> str:
    """Case-preserving NFC normalisation (macOS filenames arrive NFD)."""
    return unicodedata.normalize("NFC", word.strip())


def load_vocab(library_root: Path) -> dict:
    """Return ``{"proper": set, "common": set, "pending": {word: info}}``.

    ``proper``  — keep capitalized wherever it appears in a title.
    ``common``  — safe to lowercase (non-first, outside math).
    ``pending`` — seen but not yet decided; ``info`` = {"count", "example"}.

    Missing/corrupt file degrades to an empty vocabulary (never raises) —
    the caser then simply preserves more and queues more.
    """
    empty = {"proper": set(), "common": set(), "pending": {}, "phrases": []}
    p = vocab_path(library_root)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return empty

    key = (str(p), mtime)
    cached = _VOCAB_CACHE.get(key)
    if cached is None:
        try:
            raw = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError, ValueError):
            return empty
        try:
            cached = {
                "proper": {_norm(w) for w in raw.get("proper", [])},
                "common": {_norm(w).lower() for w in raw.get("common", [])},
                # Multi-word names that only make sense WHOLE: "New York",
                # "American Mathematical Monthly", "Root barrier".  Judged
                # one word at a time each looks like ordinary vocabulary,
                # so the phrase is the unit of the owner's ruling.
                "phrases": [_norm(w) for w in raw.get("phrases", []) if _norm(w)],
                "pending": {
                    _norm(w): {"count": int(i.get("count", 1)),
                               "example": str(i.get("example", ""))}
                    for w, i in dict(raw.get("pending", {})).items()
                },
            }
        except Exception:  # defensive: malformed structure
            logger.warning("title_vocab.json malformed; starting empty")
            return empty
        _VOCAB_CACHE[key] = cached

    # Hand back a private copy — callers (decide/record_pending) mutate the
    # returned dict in place before saving, which must not touch the cache.
    return {
        "proper": set(cached["proper"]),
        "common": set(cached["common"]),
        "phrases": list(cached.get("phrases", [])),
        "pending": {w: dict(i) for w, i in cached["pending"].items()},
    }


def _save(library_root: Path, vocab: dict) -> None:
    from core.io import atomic_write_text
    p = vocab_path(library_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "proper": sorted(vocab["proper"]),
        "common": sorted(vocab["common"]),
        # Preserved verbatim: dropping these on a save would silently
        # undo the owner's phrase rulings the next time a word is decided.
        "phrases": sorted(vocab.get("phrases", [])),
        "pending": {
            w: {"count": i["count"], "example": i["example"][:120]}
            for w, i in sorted(vocab["pending"].items())
        },
    }
    atomic_write_text(p, json.dumps(payload, indent=2, ensure_ascii=False))


def record_pending(library_root: Path, words, example: str = "") -> None:
    """Queue uncertain words for review (best-effort, never raises)."""
    words = [_norm(w) for w in words if w and w.strip()]
    if not words:
        return
    try:
        vocab = load_vocab(library_root)
        changed = False
        for w in words:
            if w in vocab["proper"] or w.lower() in vocab["common"]:
                continue
            info = vocab["pending"].get(w, {"count": 0, "example": example})
            info["count"] = int(info.get("count", 0)) + 1
            if not info.get("example"):
                info["example"] = example
            vocab["pending"][w] = info
            changed = True
        if changed:
            _save(library_root, vocab)
    except Exception as exc:  # pragma: no cover — must never block a move
        logger.warning("could not record pending title words: %s", exc)


def decide(library_root: Path, word: str, kind: str) -> None:
    """Persist the owner's ruling for ``word``: ``"proper"`` or ``"common"``.

    Removes the word from pending.  A later opposite ruling simply moves it
    between the sets.
    """
    if kind not in ("proper", "common"):
        raise ValueError(f"kind must be 'proper' or 'common', got {kind!r}")
    w = _norm(word)
    vocab = load_vocab(library_root)
    vocab["pending"].pop(w, None)
    if kind == "proper":
        vocab["common"].discard(w.lower())
        vocab["proper"].add(w)
    else:
        vocab["proper"].discard(w)
        vocab["common"].add(w.lower())
    _save(library_root, vocab)
