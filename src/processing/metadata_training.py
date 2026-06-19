#!/usr/bin/env python3
"""Capture gold (pdf-text -> title/authors) pairs for the LLM extractor.

The continuous-learning insight: every AUTHORITATIVE metadata resolution
is a free, perfectly-labelled training example.  When arXiv / Crossref /
HAL returns the title+authors for a paper, the pair
``(first-pages text, correct title, correct authors)`` is exactly what a
PDF-metadata model should learn — captured with zero extra user effort.
The user's own cockpit name-corrections are gold pairs too.

This module records those pairs to a JSONL dataset in a hidden infra dir
inside the library (``<library>/.mathpdf-training/metadata_pairs.jsonl``,
Dropbox-synced like the sidecar mirror and the operation log).  An
offline eval / fine-tune harness (run on a GPU machine) consumes it.

It also exposes the pure scoring helpers the eval harness uses, so they
can be unit-tested without the model.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DATASET_DIRNAME = ".mathpdf-training"
DATASET_FILENAME = "metadata_pairs.jsonl"
_TEXT_CAP = 6000  # chars stored per example (matches the LLM input budget)
_MIN_TEXT = 100   # below this the text is uninformative


def dataset_path(library_root: Path) -> Path:
    return Path(library_root) / DATASET_DIRNAME / DATASET_FILENAME


def _pair_key(text: str) -> str:
    """Stable dedup key from the (normalized) text prefix."""
    norm = re.sub(r"\s+", " ", text).strip().lower()[:500]
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()


def record_pair(
    library_root: Path,
    *,
    text: str,
    title: str,
    authors,
    source: str,
) -> bool:
    """Append one gold training pair.  Returns True if written.

    No-ops (returns False) when text or title is too thin to be useful.
    Authors may be a list of strings or of ``{family,given}`` dicts; both
    are normalised to a list of display strings.  Best-effort and never
    raises into the caller (capture must never break ingest).
    """
    try:
        if not text or len(text.strip()) < _MIN_TEXT or not title or not title.strip():
            return False
        norm_authors = []
        for a in (authors or []):
            if isinstance(a, dict):
                fam, giv = a.get("family", ""), a.get("given", "")
                disp = f"{giv} {fam}".strip() if giv else fam
            else:
                disp = str(a)
            disp = disp.strip()
            if disp:
                norm_authors.append(disp)

        record = {
            "key": _pair_key(text),
            "text": re.sub(r"\s+", " ", text).strip()[:_TEXT_CAP],
            "title": unicodedata.normalize("NFC", title).strip(),
            "authors": norm_authors,
            "source": source,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        path = dataset_path(library_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Single-line append is atomic under PIPE_BUF for a small record.
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception as exc:  # pragma: no cover -- capture is best-effort
        logger.debug("training-pair capture failed: %s", exc)
        return False


def load_pairs(library_root: Path, *, dedup: bool = True) -> list[dict]:
    """Load recorded pairs, optionally de-duplicated by text key
    (latest record per key wins)."""
    path = dataset_path(library_root)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    if not dedup:
        return rows
    by_key: dict = {}
    for r in rows:
        by_key[r.get("key") or _pair_key(r.get("text", ""))] = r
    return list(by_key.values())


# ---------------------------------------------------------------------------
# Pure scoring helpers (used by the offline eval harness; model-free)
# ---------------------------------------------------------------------------

def _norm_title(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_exact(pred: str, gold: str) -> bool:
    return _norm_title(pred) == _norm_title(gold) and bool(_norm_title(gold))


def title_similarity(pred: str, gold: str) -> float:
    """Token Jaccard on normalized titles (0..1)."""
    p, g = set(_norm_title(pred).split()), set(_norm_title(gold).split())
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    return len(p & g) / len(p | g)


def _last_name(name: str) -> str:
    name = unicodedata.normalize("NFC", name or "").strip()
    if "," in name:                       # "Family, Given"
        return name.split(",")[0].strip().lower()
    parts = name.split()
    return parts[-1].lower() if parts else ""


def author_f1(pred_authors, gold_authors) -> float:
    """F1 over the set of author last names (order-insensitive)."""
    p = {_last_name(a) for a in (pred_authors or []) if _last_name(a)}
    g = {_last_name(a) for a in (gold_authors or []) if _last_name(a)}
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    tp = len(p & g)
    if tp == 0:
        return 0.0
    prec, rec = tp / len(p), tp / len(g)
    return 2 * prec * rec / (prec + rec)
