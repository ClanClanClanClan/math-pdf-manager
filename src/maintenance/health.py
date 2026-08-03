"""Library-health indicators for the cockpit Stats page.

One cheap, read-only pass over the library's METADATA surfaces (sidecar
mirror, vocabulary, assist model, undo log, trash) — never the PDFs
themselves — answering the questions a 29k-paper owner can't currently
see anywhere: how complete is the sidecar coverage, is anything piling
up unreviewed, when did the machinery last run.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def _count_files(root: Path, suffix: str) -> int:
    """Count the owner's files, not the repo's.

    A bare rglob counted the code checkout that lives under the library
    root (77 publisher-download test fixtures) and everything already
    thrown away in .trash, so the health numbers overstated the library.
    Shares the exclusion list with ``iter_pdfs`` rather than keeping a
    second, drifting copy.
    """
    if not root.exists():
        return 0
    from processing.identity import _NON_LIBRARY_DIRS
    total = 0
    for p in root.rglob(f"*{suffix}"):
        if not p.is_file():
            continue
        # Judge the path RELATIVE to the root being counted.  Counting
        # the library must skip .trash; counting .trash itself must not
        # skip everything just because the root is named .trash.
        try:
            parts = p.relative_to(root).parts
        except ValueError:          # pragma: no cover - p is under root
            parts = p.parts
        if any(part in _NON_LIBRARY_DIRS for part in parts):
            continue
        total += 1
    return total


def _age_days(p: Path) -> float:
    try:
        return round((time.time() - p.stat().st_mtime) / 86400, 1)
    except OSError:
        return -1.0


def collect_library_health(library_root: Path) -> dict:
    """Return the health snapshot (all fields present even on empty libs)."""
    from processing.identity import iter_pdfs

    out: dict = {}

    # Sidecar coverage — identity travels with every paper only if the
    # sidecar exists.  Counting the mirror is far cheaper than resolving
    # sidecar_path per PDF.
    n_pdfs = sum(1 for _ in iter_pdfs(library_root))
    mirror = library_root / ".mathpdf-sidecars"
    n_sidecars = _count_files(mirror, ".meta.json")
    out["pdfs"] = n_pdfs
    out["sidecars"] = n_sidecars
    out["sidecar_coverage"] = round(n_sidecars / n_pdfs, 4) if n_pdfs else 0.0

    # Title vocabulary + assist model (the learning loop's backlog).
    try:
        from processing.title_vocab import load_vocab
        v = load_vocab(library_root)
        out["vocab_pending"] = len(v["pending"])
        out["vocab_ruled"] = len(v["proper"]) + len(v["common"])
    except Exception:
        out["vocab_pending"] = out["vocab_ruled"] = 0
    try:
        from processing.title_model import model_path
        mp = model_path(library_root)
        if mp.exists():
            m = json.loads(mp.read_text())
            out["model_trained_on"] = int(m.get("trained_on", 0))
            out["model_accuracy"] = float(
                m.get("metrics", {}).get("accuracy", 0.0))
            out["model_age_days"] = _age_days(mp)
        else:
            out["model_trained_on"] = 0
            out["model_accuracy"] = 0.0
            out["model_age_days"] = -1.0
    except Exception:
        out["model_trained_on"] = 0
        out["model_accuracy"] = 0.0
        out["model_age_days"] = -1.0

    # Undo log: how much reversible history exists, and how fresh.
    ops = library_root / ".operation_log"
    tx_files = list(ops.glob("*.json")) if ops.exists() else []
    out["undo_transactions"] = len(tx_files)
    out["last_tx_age_days"] = (
        min((_age_days(p) for p in tx_files), default=-1.0)
        if tx_files else -1.0
    )

    # Trash: recoverable removals awaiting eventual purge.
    trash = library_root / ".trash"
    out["trash_pdfs"] = _count_files(trash, ".pdf")

    # Corpus stats freshness (the title caser's oracle).
    try:
        from processing.title_corpus import stats_path
        sp = stats_path(library_root)
        out["corpus_stats_age_days"] = _age_days(sp) if sp.exists() else -1.0
    except Exception:
        out["corpus_stats_age_days"] = -1.0

    return out
