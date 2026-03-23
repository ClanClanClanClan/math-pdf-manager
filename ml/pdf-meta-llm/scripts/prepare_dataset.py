#!/usr/bin/env python3
"""
Training data preparation for LLM-based metadata extraction.

Takes raw chat-format JSONL produced by ``extract_text.py`` and applies
quality filters, deduplication, and deterministic train/val/test splits.

Quality filters (drop if any fail):
    1. Title 5–300 characters
    2. Title passes ``is_valid_embedded_title()``
    3. At least 1 author with 2+ characters
    4. PDF text >= 200 characters
    5. Title appears in PDF text (rapidfuzz token_sort_ratio >= 70)
    6. No duplicate titles (dedup by normalised title)

Usage::

    # From raw chat JSONL (produced by extract_text.py --format chat)
    python scripts/prepare_dataset.py raw_data.jsonl --output-dir datasets/

    # With custom split ratios
    python scripts/prepare_dataset.py raw_data.jsonl --output-dir datasets/ \\
        --train-ratio 0.90 --val-ratio 0.05 --seed 42

    # Direct from PDF root (extracts + filters in one step)
    python scripts/prepare_dataset.py --pdf-root ~/Dropbox/Work/Maths \\
        --output-dir datasets/
"""

import argparse
import json
import logging
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

# Reuse extraction and parsing from extract_text
try:
    from extract_text import extract_text, parse_filename, skip_this, _SYSTEM_PROMPT, _USER_TEMPLATE
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_text import extract_text, parse_filename, skip_this, _SYSTEM_PROMPT, _USER_TEMPLATE

# Reuse quality validators
try:
    from pdf_processing.parsers.metadata_quality import is_valid_embedded_title
except ImportError:
    # Add src/ to path for direct invocation
    _project_root = Path(__file__).resolve().parent.parent.parent.parent
    _src_dir = str(_project_root / "src")
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)
    from pdf_processing.parsers.metadata_quality import is_valid_embedded_title

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_title(title: str) -> str:
    """Normalise a title for deduplication.

    NFC-normalises, lowercases, strips non-alphanumeric characters.
    """
    t = unicodedata.normalize("NFC", title)
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9 ]", "", t)
    return t


# ---------------------------------------------------------------------------
# Quality filters
# ---------------------------------------------------------------------------

class QualityFilter:
    """Applies quality filters and tracks rejection reasons."""

    def __init__(
        self,
        title_in_text_threshold: float = 70.0,
        dedup_fuzzy_threshold: float = 95.0,
    ):
        self.title_in_text_threshold = title_in_text_threshold
        self.dedup_fuzzy_threshold = dedup_fuzzy_threshold
        self.rejection_counts: Counter = Counter()
        self.seen_titles_set: set = set()              # exact set for fast exact check
        self._prefix_buckets: Dict[str, List[str]] = defaultdict(list)  # prefix → titles

    def _is_fuzzy_duplicate(self, norm_title: str) -> bool:
        """Check if a normalised title is a near-duplicate of any seen title.

        Uses exact set for O(1) check first, then a fast prefix-bucketed fuzzy
        check for near-duplicates like:
        - "on the convergence of sgd" vs "on the convergence of sgd methods"
        - Same paper with slightly different filename encoding

        Performance: O(1) exact check + O(bucket_size) fuzzy check per title.
        Titles are bucketed by their first 20 alphanumeric characters, so only
        titles with similar beginnings are compared.
        """
        if norm_title in self.seen_titles_set:
            return True

        # Bucket key: first 20 non-space chars — titles that match at 95%
        # almost always share the same prefix
        key = norm_title.replace(" ", "")[:20]
        if key in self._prefix_buckets:
            for seen in self._prefix_buckets[key]:
                if fuzz.ratio(norm_title, seen) >= self.dedup_fuzzy_threshold:
                    return True

        return False

    def check(self, title: str, authors: List[str], text: str) -> Optional[str]:
        """Return rejection reason string, or None if sample passes all filters."""
        # Filter 1: Title length
        if not title or len(title) < 5:
            return "title_too_short"
        if len(title) > 300:
            return "title_too_long"

        # Filter 2: Title quality (not garbage)
        if not is_valid_embedded_title(title):
            return "title_garbage"

        # Filter 3: At least 1 valid author name (not journal metadata)
        valid_authors = [a for a in authors if len(a.strip()) >= 2]
        if not valid_authors:
            return "no_valid_authors"

        # Filter 3b: Reject if authors look like journal metadata or numbers
        # (e.g. "Comptes rendus hebdomadaires...", "tome 273", "série I", "158")
        _metadata_patterns = re.compile(
            r"^(comptes rendus|astérisque|mémoires|tome \d|séri|vol\b|"
            r"nº?\d|supplément|annales|\d+[-–]\d+$|^\d+$)",
            re.IGNORECASE,
        )
        if all(_metadata_patterns.search(a) for a in valid_authors):
            return "authors_are_metadata"

        # Filter 3c: Reject if any author is a bare number (page/article number)
        if any(re.fullmatch(r"\d+", a.strip()) for a in valid_authors):
            return "author_is_number"

        # Filter 4: Sufficient text content
        if not text or len(text.strip()) < 200:
            return "text_too_short"

        # Filter 5: Title appears in the PDF text (NFC-normalised comparison)
        # This is critical — avoids teaching the LLM to hallucinate titles
        # that aren't in the extracted text.
        text_snippet = unicodedata.normalize("NFC", text[:8000])
        title_nfc = unicodedata.normalize("NFC", title)
        similarity = fuzz.partial_ratio(title_nfc.lower(), text_snippet.lower())
        if similarity < self.title_in_text_threshold:
            return "title_not_in_text"

        # Filter 6: Deduplicate by normalised title (exact + fuzzy)
        norm = _normalize_title(title)
        if self._is_fuzzy_duplicate(norm):
            return "duplicate_title"
        self.seen_titles_set.add(norm)
        key = norm.replace(" ", "")[:20]
        self._prefix_buckets[key].append(norm)

        return None

    def apply(self, title: str, authors: List[str], text: str) -> bool:
        """Return True if sample passes all filters."""
        reason = self.check(title, authors, text)
        if reason:
            self.rejection_counts[reason] += 1
            return False
        return True


# ---------------------------------------------------------------------------
# Dataset building from raw JSONL
# ---------------------------------------------------------------------------

def load_chat_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load chat-format JSONL and extract title, authors, text."""
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"Skipping malformed JSON at line {line_num}")
                continue

            messages = obj.get("messages", [])
            if len(messages) < 3:
                continue

            # Extract text from user message
            user_content = messages[1].get("content", "")
            # Strip the template wrapper to get raw PDF text
            text = user_content
            if "<PDF text>" in text:
                start = text.index("<PDF text>") + len("<PDF text>\n")
                end = text.index("\n</PDF text>")
                text = text[start:end]

            # Extract ground truth from assistant message
            try:
                gt = json.loads(messages[2].get("content", "{}"))
            except json.JSONDecodeError:
                continue

            title = gt.get("title", "")
            authors = gt.get("authors", [])
            if isinstance(authors, str):
                authors = [a.strip() for a in authors.split(";") if a.strip()]

            samples.append({
                "title": title,
                "authors": authors,
                "text": text,
                "messages": messages,
            })

    return samples


def build_from_pdf_root(pdf_root: Path, workers: int = None) -> List[Dict[str, Any]]:
    """Build samples directly from a PDF directory."""
    import multiprocessing as mp

    try:
        from tqdm import tqdm as tqdm_iter
    except ImportError:
        def tqdm_iter(it, **kw):
            return it

    pdfs = [p for p in pdf_root.rglob("*.pdf") if not skip_this(p)]
    print(f"Scanning {len(pdfs):,} PDFs...")

    samples = []
    for pdf in tqdm_iter(pdfs, desc="Extracting"):
        title, authors = parse_filename(pdf)
        if not title or not authors:
            continue

        text = extract_text(pdf)
        if not text or len(text.strip()) < 100:
            continue

        # Truncate text to match inference context
        text_truncated = text[:6000]

        # Build chat messages
        ground_truth = json.dumps(
            {"title": title, "authors": authors}, ensure_ascii=False
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_TEMPLATE.format(text=text_truncated)},
            {"role": "assistant", "content": ground_truth},
        ]

        samples.append({
            "title": title,
            "authors": authors,
            "text": text_truncated,
            "messages": messages,
        })

    return samples


# ---------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------

def split_dataset(
    samples: List[Dict[str, Any]],
    train_ratio: float = 0.90,
    val_ratio: float = 0.05,
    seed: int = 42,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Deterministic shuffle and split into train/val/test."""
    assert abs(train_ratio + val_ratio - 0.95) < 0.01 or abs(train_ratio + val_ratio - 1.0) < 0.01, \
        "train_ratio + val_ratio should be ~0.95 (remaining = test) or 1.0"

    test_ratio = 1.0 - train_ratio - val_ratio
    if test_ratio < 0:
        test_ratio = 0.0

    rng = random.Random(seed)
    indices = list(range(len(samples)))
    rng.shuffle(indices)

    n = len(samples)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    train = [samples[i] for i in train_idx]
    val = [samples[i] for i in val_idx]
    test = [samples[i] for i in test_idx]

    return train, val, test


# ---------------------------------------------------------------------------
# Writing outputs
# ---------------------------------------------------------------------------

def generate_empty_text_examples(n: int = 200, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate synthetic training examples with empty/garbage text.

    These teach the model to return empty results instead of hallucinating
    when the PDF text is unreadable (scanned PDFs, image-only pages, etc.).
    """
    rng = random.Random(seed)

    # Diverse garbage-text templates that mimic what scanned PDFs produce
    garbage_templates = [
        "",
        " ",
        "\n\n\n",
        ".............",
        "_ _ _ _ _ _ _ _ _",
        "1 2 3 4 5 6 7 8 9 0",
        "Page 1",
        "This page intentionally left blank.",
        "Copyright © All rights reserved.",
        "Printed in the United States of America.",
        "ISBN 978-0-00-000000-0",
        "Library of Congress Cataloging-in-Publication Data",
        "No part of this publication may be reproduced.",
        "\\x00\\x01\\x02\\x03",  # binary-like garbage
        "ff fi fl ffi ffl",  # ligature artifacts
        "{ } [ ] | \\ / ~ ` @ # $ % ^ & * ( )",
        "i ii iii iv v vi vii viii ix x",  # Roman numeral page numbers
        "Contents\n\nPreface\n\nAcknowledgements",  # Table of contents without title
    ]

    empty_response = json.dumps({"title": "", "authors": []}, ensure_ascii=False)

    examples = []
    for i in range(n):
        # Pick a random garbage template, optionally combine multiples
        n_templates = rng.randint(1, 3)
        chosen = [rng.choice(garbage_templates) for _ in range(n_templates)]
        text = "\n".join(chosen)

        # Add some random whitespace/noise
        text = text + "\n" * rng.randint(0, 5) + " " * rng.randint(0, 20)

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_TEMPLATE.format(text=text)},
            {"role": "assistant", "content": empty_response},
        ]

        examples.append({
            "title": "",
            "authors": [],
            "text": text,
            "messages": messages,
        })

    return examples


def write_jsonl(samples: List[Dict[str, Any]], path: Path) -> None:
    """Write chat-format JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for sample in samples:
            row = {"messages": sample["messages"]}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def compute_stats(
    total_scanned: int,
    pre_filter: int,
    filtered: List[Dict],
    rejection_counts: Counter,
    train: List[Dict],
    val: List[Dict],
    test: List[Dict],
) -> Dict[str, Any]:
    """Compute dataset statistics."""
    def length_stats(values):
        if not values:
            return {"min": 0, "max": 0, "mean": 0, "median": 0}
        values = sorted(values)
        n = len(values)
        return {
            "min": values[0],
            "max": values[-1],
            "mean": round(sum(values) / n, 1),
            "median": values[n // 2],
        }

    title_lengths = [len(s["title"]) for s in filtered]
    author_counts = [len(s["authors"]) for s in filtered]
    text_lengths = [len(s["text"]) for s in filtered]

    return {
        "total_pdfs_scanned": total_scanned,
        "samples_with_ground_truth": pre_filter,
        "samples_after_filtering": len(filtered),
        "rejection_reasons": dict(rejection_counts.most_common()),
        "splits": {
            "train": len(train),
            "val": len(val),
            "test": len(test),
        },
        "distributions": {
            "title_length": length_stats(title_lengths),
            "author_count": length_stats(author_counts),
            "text_length": length_stats(text_lengths),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare filtered training data for PDF metadata LLM",
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "jsonl_input", nargs="?", type=Path,
        help="Path to raw chat-format JSONL (from extract_text.py --format chat)",
    )
    input_group.add_argument(
        "--pdf-root", type=Path,
        help="Extract directly from PDF directory (slower but one-step)",
    )

    parser.add_argument(
        "--output-dir", type=Path, default=Path("datasets"),
        help="Output directory for train/val/test splits (default: datasets/)",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.90,
        help="Fraction for training set (default: 0.90)",
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.05,
        help="Fraction for validation set (default: 0.05)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for split (default: 42)",
    )
    parser.add_argument(
        "--title-threshold", type=float, default=70.0,
        help="Min rapidfuzz token_sort_ratio for title-in-text check (default: 70)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print rejected samples",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    # Load samples
    if args.pdf_root:
        print(f"Extracting from PDF root: {args.pdf_root}")
        raw_samples = build_from_pdf_root(args.pdf_root)
        total_scanned = len(list(args.pdf_root.rglob("*.pdf")))
    else:
        print(f"Loading from JSONL: {args.jsonl_input}")
        raw_samples = load_chat_jsonl(args.jsonl_input)
        total_scanned = len(raw_samples)

    pre_filter_count = len(raw_samples)
    print(f"Loaded {pre_filter_count:,} samples with ground-truth labels")

    # Apply quality filters
    qf = QualityFilter(title_in_text_threshold=args.title_threshold)
    filtered = []
    for sample in raw_samples:
        if qf.apply(sample["title"], sample["authors"], sample["text"]):
            filtered.append(sample)
        elif args.verbose:
            reason = qf.check(sample["title"], sample["authors"], sample["text"])
            # reason is None for the already-accepted copy, but the counter
            # already tracked it — just log the title
            logger.debug(f"Rejected: {sample['title'][:80]}")

    print(f"After filtering: {len(filtered):,} samples "
          f"({len(filtered)/pre_filter_count*100:.1f}% pass rate)")

    if not filtered:
        print("No samples passed filters. Check your data or lower --title-threshold.")
        sys.exit(1)

    # Print rejection breakdown
    print("\nRejection reasons:")
    for reason, count in qf.rejection_counts.most_common():
        print(f"  {reason:<25s} {count:>6,}")

    # Split
    train, val, test = split_dataset(
        filtered,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )

    # Augment training set with empty-text examples
    n_empty = max(200, len(train) // 100)  # ~1% of training set, minimum 200
    empty_examples = generate_empty_text_examples(n=n_empty, seed=args.seed + 1)
    train.extend(empty_examples)
    # Also add a few to val for proper evaluation
    val_empty = generate_empty_text_examples(n=max(20, n_empty // 10), seed=args.seed + 2)
    val.extend(val_empty)

    print(f"\nSplit: train={len(train):,} (incl. {n_empty} empty-text augmented)  "
          f"val={len(val):,}  test={len(test):,}")

    # Write outputs
    output_dir = args.output_dir
    write_jsonl(train, output_dir / "train.jsonl")
    write_jsonl(val, output_dir / "val.jsonl")
    write_jsonl(test, output_dir / "test.jsonl")

    # Write stats
    stats = compute_stats(
        total_scanned, pre_filter_count, filtered,
        qf.rejection_counts, train, val, test,
    )
    stats_path = output_dir / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\nDatasets written to {output_dir}/")
    print(f"  train.jsonl  ({len(train):,} examples)")
    print(f"  val.jsonl    ({len(val):,} examples)")
    print(f"  test.jsonl   ({len(test):,} examples)")
    print(f"  stats.json   (distribution stats)")


if __name__ == "__main__":
    main()
