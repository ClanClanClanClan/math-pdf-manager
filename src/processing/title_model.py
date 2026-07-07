"""Self-trained proper-noun-vs-common-word model (Stage 2 of titles).

A tiny multinomial Naive Bayes over character n-grams and word-shape
features, implemented in pure Python — no third-party ML, no external
services, trained entirely on the owner's OWN data:

  * word-casing labels harvested from the ~29k curated canonical
    filenames (a word the corpus writes overwhelmingly lowercase
    mid-title is a labelled COMMON example; overwhelmingly capitalized —
    PROPER),
  * the owner's explicit vocabulary rulings (highest weight),
  * GOLD canonical titles from ``metadata_training`` as they accumulate.

Character n-grams generalize to UNSEEN words: "-ov"/"-berg"/"-escu"
endings smell like surnames, ordinary English morphology smells common.

Role (deliberate): the model ASSISTS the owner's vocabulary review —
pre-classifying pending words with a confidence so rulings become
one-glance confirmations (or one bulk click at high confidence).  It
does NOT silently drive the caser; auto-casing stays anchored to the
provable oracles until the model's measured precision earns more.

Model persists as JSON at ``<lib>/.mathpdf-config/title_word_model.json``
with its held-out metrics embedded, so the UI can show how trustworthy
the suggestions are.
"""
from __future__ import annotations

import json
import logging
import math
import random
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_FILENAME = "title_word_model.json"

COMMON, PROPER = "common", "proper"


def model_path(library_root: Path) -> Path:
    return library_root / ".mathpdf-config" / MODEL_FILENAME


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

def word_features(word: str) -> list:
    """Character n-grams (2-4, padded) + shape features for one word."""
    w = unicodedata.normalize("NFC", word.strip()).lower()
    padded = f"^{w}$"
    feats = []
    for n in (2, 3, 4):
        for i in range(len(padded) - n + 1):
            feats.append(padded[i:i + n])
    feats.append(f"LEN={min(len(w), 12)}")
    if any(ord(c) > 127 for c in w):
        feats.append("SHAPE=accented")
    if "-" in w or "'" in w or "’" in w:
        feats.append("SHAPE=compound")
    return feats


# ---------------------------------------------------------------------------
# Training-data harvest
# ---------------------------------------------------------------------------

def _label_from_counts(n_low: int, n_cap: int) -> Optional[str]:
    """Strong-signal labels only; ambiguous casings are skipped."""
    if n_low >= 5 and n_low >= 5 * max(n_cap, 1):
        return COMMON
    if n_cap >= 3 and n_cap >= 5 * max(n_low, 1):
        return PROPER
    return None


def harvest_examples(library_root: Path) -> list:
    """Return ``[(word, label), ...]`` from corpus + GOLD + rulings."""
    examples: list = []

    # 1) Corpus casing statistics (the bulk of the signal).
    try:
        from processing.title_corpus import load_word_stats
        for word, (n_low, n_cap) in load_word_stats(library_root).items():
            label = _label_from_counts(int(n_low), int(n_cap))
            if label and len(word) >= 3:
                examples.append((word, label))
    except Exception:  # pragma: no cover
        logger.warning("corpus stats unavailable for training", exc_info=True)

    # 2) GOLD canonical titles (arXiv/Crossref/HAL-resolved) — same
    #    harvesting rule applied per title as they accumulate.
    try:
        from processing.metadata_training import load_pairs
        import re
        word_re = re.compile(r"[^\W\d_]+", re.UNICODE)
        counts: dict = {}
        for pair in load_pairs(library_root):
            title = str(pair.get("title") or "")
            words = word_re.findall(title)
            for w in words[1:]:
                if len(w) < 3:
                    continue
                slot = counts.setdefault(w.lower(), [0, 0])
                if w[0].isupper():
                    slot[1] += 1
                elif w.islower():
                    slot[0] += 1
        for word, (n_low, n_cap) in counts.items():
            # Weaker thresholds — GOLD is small but very clean.
            if n_low >= 2 and n_cap == 0:
                examples.append((word, COMMON))
            elif n_cap >= 2 and n_low == 0:
                examples.append((word, PROPER))
    except Exception:  # pragma: no cover
        pass

    # 3) Author SURNAMES from the canonical filenames — every "Family, I."
    #    segment is a clean PROPER label, and there are thousands of them.
    #    This is what teaches the n-grams surname morphology (-ov, -berg,
    #    -escu, accents…) far beyond the few names that recur in titles.
    try:
        import re
        from processing.identity import iter_pdfs
        seg_re = re.compile(r"([^\W\d_][\w'’ -]*?),\s")
        surnames: set = set()
        for pdf in iter_pdfs(library_root):
            stem = unicodedata.normalize("NFC", pdf.stem)
            if " - " not in stem:
                continue
            authors_part = stem.split(" - ", 1)[0]
            for m in seg_re.finditer(authors_part + ", "):
                for token in m.group(1).replace("-", " ").split():
                    # Skip particles (de, van…) and initials.
                    if len(token) >= 3 and token[0].isupper():
                        surnames.add(token)
        examples.extend((s, PROPER) for s in surnames)
    except Exception:  # pragma: no cover
        logger.warning("surname harvest failed", exc_info=True)

    # 4) The owner's explicit rulings — repeated for extra weight.
    try:
        from processing.title_vocab import load_vocab
        vocab = load_vocab(library_root)
        for w in vocab["proper"]:
            examples.extend([(w, PROPER)] * 3)
        for w in vocab["common"]:
            examples.extend([(w, COMMON)] * 3)
    except Exception:  # pragma: no cover
        pass

    return examples


# ---------------------------------------------------------------------------
# Naive Bayes core (pure Python)
# ---------------------------------------------------------------------------

def _train_nb(examples: list) -> dict:
    """Multinomial NB with Laplace smoothing over word_features."""
    feat_counts: dict = {}
    class_counts = {COMMON: 0, PROPER: 0}
    class_feat_totals = {COMMON: 0, PROPER: 0}
    for word, label in examples:
        class_counts[label] += 1
        for f in word_features(word):
            slot = feat_counts.setdefault(f, [0, 0])
            slot[0 if label == COMMON else 1] += 1
            class_feat_totals[label] += 1
    return {
        "class_counts": class_counts,
        "feat_counts": feat_counts,
        "class_feat_totals": class_feat_totals,
        "vocab_size": len(feat_counts),
    }


def score_word(word: str, model: dict) -> float:
    """Return ``p(PROPER)`` for ``word`` under the model, in [0, 1]."""
    cc = model["class_counts"]
    total = cc[COMMON] + cc[PROPER]
    if total == 0:
        return 0.5
    v = max(model["vocab_size"], 1)
    log_odds = math.log((cc[PROPER] + 1) / (cc[COMMON] + 1))
    fc = model["feat_counts"]
    totals = model["class_feat_totals"]
    for f in word_features(word):
        c_common, c_proper = fc.get(f, (0, 0))
        log_odds += math.log((c_proper + 1) / (totals[PROPER] + v))
        log_odds -= math.log((c_common + 1) / (totals[COMMON] + v))
    # Logistic squash of the log-odds.
    try:
        return 1.0 / (1.0 + math.exp(-log_odds))
    except OverflowError:
        return 0.0 if log_odds < 0 else 1.0


def _evaluate(model: dict, held_out: list) -> dict:
    """Per-class precision/recall on a held-out set at p=0.5."""
    tp = {COMMON: 0, PROPER: 0}
    fp = {COMMON: 0, PROPER: 0}
    fn = {COMMON: 0, PROPER: 0}
    for word, label in held_out:
        pred = PROPER if score_word(word, model) >= 0.5 else COMMON
        if pred == label:
            tp[label] += 1
        else:
            fp[pred] += 1
            fn[label] += 1

    def pr(cls):
        p = tp[cls] / (tp[cls] + fp[cls]) if (tp[cls] + fp[cls]) else 0.0
        r = tp[cls] / (tp[cls] + fn[cls]) if (tp[cls] + fn[cls]) else 0.0
        return round(p, 4), round(r, 4)

    pc, rc = pr(COMMON)
    pp, rp = pr(PROPER)
    n = len(held_out)
    acc = (tp[COMMON] + tp[PROPER]) / n if n else 0.0
    return {
        "held_out": n, "accuracy": round(acc, 4),
        "common_precision": pc, "common_recall": rc,
        "proper_precision": pp, "proper_recall": rp,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def train_model(library_root: Path, *, seed: int = 13) -> dict:
    """Harvest, train (90/10 held-out eval), persist, return the model."""
    examples = harvest_examples(library_root)
    if len(examples) < 200:
        raise ValueError(
            f"too few training examples ({len(examples)}) — corpus stats "
            "missing or library too small")
    rng = random.Random(seed)
    # Class balance: the surname harvest floods PROPER (thousands of
    # author names vs ~3k corpus-common words), which skews the priors
    # and erodes common-side precision.  Downsample the majority class
    # to at most 1.5x the minority.
    by_cls = {COMMON: [], PROPER: []}
    for ex in examples:
        by_cls[ex[1]].append(ex)
    minority = min(len(by_cls[COMMON]), len(by_cls[PROPER]))
    cap = int(minority * 1.5)
    for cls in (COMMON, PROPER):
        if len(by_cls[cls]) > cap:
            rng.shuffle(by_cls[cls])
            by_cls[cls] = by_cls[cls][:cap]
    examples = by_cls[COMMON] + by_cls[PROPER]
    rng.shuffle(examples)
    cut = max(1, len(examples) // 10)
    held_out, train = examples[:cut], examples[cut:]
    model = _train_nb(train)
    model["metrics"] = _evaluate(model, held_out)
    model["trained_on"] = len(train)

    # Retrain on ALL data for the shipped model (metrics stay held-out).
    final = _train_nb(examples)
    final["metrics"] = model["metrics"]
    final["trained_on"] = len(examples)

    try:
        from core.io import atomic_write_text
        p = model_path(library_root)
        p.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(p, json.dumps(final, ensure_ascii=False))
    except Exception:  # pragma: no cover — persisting is best-effort
        logger.warning("could not persist title model", exc_info=True)
    return final


def load_model(library_root: Path) -> Optional[dict]:
    """Load the persisted model; None when absent/corrupt."""
    try:
        return json.loads(model_path(library_root).read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def suggest(word: str, model: dict) -> tuple:
    """Return ``(ruling, confidence)`` — e.g. ``("proper", 0.97)``."""
    p = score_word(word, model)
    return (PROPER, p) if p >= 0.5 else (COMMON, 1.0 - p)


if __name__ == "__main__":  # pragma: no cover
    import sys
    from core.config_paths import get_library_root
    lib = Path(sys.argv[1]) if len(sys.argv) > 1 else get_library_root()
    m = train_model(lib)
    print(json.dumps(m["metrics"], indent=2))
