#!/usr/bin/env python3
"""
Comprehensive data quality inspection for PDF metadata training data.

Run this BEFORE training to catch problems early.  Produces a detailed
report covering:

1. **Distribution analysis** — title/author/text length histograms,
   author counts, token counts
2. **Anomaly detection** — suspiciously short/long titles, single-char
   authors, encoding issues, duplicate near-matches
3. **Content quality** — title-in-text match scores, language detection,
   math-heavy titles, non-ASCII density
4. **Tokenisation audit** — sequence length distribution, label mask
   ratios, truncation rate
5. **Random sample review** — prints N random examples for manual spot-check

Usage::

    # Full inspection of prepared datasets
    python scripts/inspect_dataset.py datasets/

    # Inspect raw extraction before filtering
    python scripts/inspect_dataset.py --raw raw_data.jsonl

    # Print 20 random samples for manual review
    python scripts/inspect_dataset.py datasets/ --show-samples 20

    # Export report to JSON
    python scripts/inspect_dataset.py datasets/ --output report.json
"""

import argparse
import json
import logging
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(values: List[float], p: float) -> float:
    """Compute the p-th percentile (0–100)."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] + frac * (s[hi] - s[lo])


def _histogram_ascii(values: List[float], bins: int = 20, width: int = 40) -> str:
    """Render a simple ASCII histogram."""
    if not values:
        return "  (no data)"
    lo, hi = min(values), max(values)
    if lo == hi:
        return f"  all values = {lo}"
    step = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = min(int((v - lo) / step), bins - 1)
        counts[idx] += 1
    max_count = max(counts) if counts else 1
    lines = []
    for i, c in enumerate(counts):
        left = lo + i * step
        bar = "#" * int(c / max_count * width) if max_count > 0 else ""
        lines.append(f"  {left:8.1f} | {bar} ({c})")
    return "\n".join(lines)


def _non_ascii_ratio(s: str) -> float:
    """Fraction of characters that are non-ASCII."""
    if not s:
        return 0.0
    return sum(1 for c in s if ord(c) > 127) / len(s)


def _is_math_heavy(title: str) -> bool:
    """Check if a title contains substantial math notation."""
    math_chars = set("αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩ∞∂∇∀∃∈⊂⊆∪∩×·≤≥≠≈∼≡±ℝℓ→←⇒⇔")
    count = sum(1 for c in title if c in math_chars)
    return count >= 3


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_split(path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file and extract title, authors, text from messages."""
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"Malformed JSON at {path}:{line_num}")
                continue

            messages = obj.get("messages", [])
            if len(messages) < 3:
                continue

            # Extract text from user message
            user_content = messages[1].get("content", "")
            text = user_content
            if "<PDF text>" in text and "</PDF text>" in text:
                start = text.index("<PDF text>") + len("<PDF text>\n")
                end = text.index("\n</PDF text>")
                text = text[start:end]

            # Extract ground truth from assistant
            try:
                gt = json.loads(messages[2].get("content", "{}"))
            except json.JSONDecodeError:
                gt = {}

            title = gt.get("title", "")
            authors = gt.get("authors", [])
            if isinstance(authors, str):
                authors = [a.strip() for a in authors.split(";") if a.strip()]

            samples.append({
                "title": title,
                "authors": authors,
                "text": text,
                "messages": messages,
                "line_num": line_num,
            })
    return samples


# ---------------------------------------------------------------------------
# Inspection checks
# ---------------------------------------------------------------------------

class DatasetInspector:
    """Run all quality checks on a dataset split."""

    def __init__(self, samples: List[Dict[str, Any]], split_name: str = ""):
        self.samples = samples
        self.split_name = split_name
        self.issues: List[Dict[str, Any]] = []

    def run_all(self) -> Dict[str, Any]:
        """Run all checks and return a report dict."""
        report = {
            "split": self.split_name,
            "total_samples": len(self.samples),
        }
        report["distributions"] = self._distributions()
        report["anomalies"] = self._anomalies()
        report["content_quality"] = self._content_quality()
        report["tokenisation"] = self._tokenisation_audit()
        report["issues"] = self.issues
        report["issue_count"] = len(self.issues)
        return report

    # -- Distribution analysis --

    def _distributions(self) -> Dict[str, Any]:
        title_lens = [len(s["title"]) for s in self.samples]
        author_counts = [len(s["authors"]) for s in self.samples]
        text_lens = [len(s["text"]) for s in self.samples]
        author_name_lens = [
            len(a) for s in self.samples for a in s["authors"]
        ]

        def stats(vals):
            if not vals:
                return {}
            return {
                "count": len(vals),
                "min": min(vals),
                "max": max(vals),
                "mean": round(sum(vals) / len(vals), 1),
                "median": round(_percentile(vals, 50), 1),
                "p5": round(_percentile(vals, 5), 1),
                "p95": round(_percentile(vals, 95), 1),
            }

        return {
            "title_length": stats(title_lens),
            "author_count": stats(author_counts),
            "author_name_length": stats(author_name_lens),
            "text_length": stats(text_lens),
        }

    # -- Anomaly detection --

    def _anomalies(self) -> Dict[str, Any]:
        anomalies = defaultdict(list)

        for i, s in enumerate(self.samples):
            title = s["title"]
            authors = s["authors"]
            text = s["text"]

            # Suspiciously short title
            if len(title) < 15:
                anomalies["short_title"].append({
                    "idx": i, "title": title, "len": len(title)
                })
                self.issues.append({
                    "type": "short_title", "idx": i,
                    "detail": f"Title only {len(title)} chars: {title!r}"
                })

            # Suspiciously long title
            if len(title) > 200:
                anomalies["long_title"].append({
                    "idx": i, "title": title[:100] + "...", "len": len(title)
                })
                self.issues.append({
                    "type": "long_title", "idx": i,
                    "detail": f"Title {len(title)} chars"
                })

            # Single-character author names
            for a in authors:
                if len(a.strip()) <= 1:
                    anomalies["single_char_author"].append({
                        "idx": i, "author": a, "title": title[:60]
                    })
                    self.issues.append({
                        "type": "single_char_author", "idx": i,
                        "detail": f"Author {a!r} in: {title[:60]}"
                    })

            # Too many authors (possible parsing issue)
            if len(authors) > 15:
                anomalies["many_authors"].append({
                    "idx": i, "count": len(authors), "title": title[:60]
                })
                self.issues.append({
                    "type": "many_authors", "idx": i,
                    "detail": f"{len(authors)} authors in: {title[:60]}"
                })

            # Encoding issues — replacement characters or garbled text
            if "\ufffd" in title or "\ufffd" in " ".join(authors):
                anomalies["encoding_issues"].append({
                    "idx": i, "title": title[:80]
                })
                self.issues.append({
                    "type": "encoding_issue", "idx": i,
                    "detail": f"Replacement char in: {title[:60]}"
                })

            # Title looks like it contains the full author list
            if authors:
                author_str = ", ".join(authors).lower()
                if len(author_str) > 10 and author_str in title.lower():
                    anomalies["authors_in_title"].append({
                        "idx": i, "title": title[:80]
                    })
                    self.issues.append({
                        "type": "authors_in_title", "idx": i,
                        "detail": f"Authors appear in title: {title[:60]}"
                    })

            # Very short text (might produce bad training signal)
            if len(text) < 500:
                anomalies["short_text"].append({
                    "idx": i, "text_len": len(text), "title": title[:60]
                })

        # Near-duplicate detection (sample-based for speed)
        near_dupes = self._find_near_duplicates()
        if near_dupes:
            anomalies["near_duplicates"] = near_dupes
            for d in near_dupes:
                self.issues.append({
                    "type": "near_duplicate", "idx": d["idx_a"],
                    "detail": f"Similarity {d['score']:.0f}% with idx {d['idx_b']}: {d['title_a'][:50]}"
                })

        return {k: len(v) if isinstance(v, list) else v for k, v in anomalies.items()}

    def _find_near_duplicates(self, sample_size: int = 2000, threshold: float = 92.0) -> List[Dict]:
        """Find near-duplicate titles by sampling pairs."""
        n = len(self.samples)
        if n < 2:
            return []

        # For large datasets, sample random pairs
        indices = list(range(n))
        if n > sample_size:
            random.seed(42)
            indices = random.sample(indices, sample_size)

        titles = [(i, self.samples[i]["title"].lower().strip()) for i in indices]
        dupes = []

        for a_pos in range(len(titles)):
            for b_pos in range(a_pos + 1, min(a_pos + 50, len(titles))):
                idx_a, t_a = titles[a_pos]
                idx_b, t_b = titles[b_pos]
                score = fuzz.ratio(t_a, t_b)
                if score >= threshold and t_a != t_b:
                    dupes.append({
                        "idx_a": idx_a, "idx_b": idx_b,
                        "title_a": self.samples[idx_a]["title"],
                        "title_b": self.samples[idx_b]["title"],
                        "score": score,
                    })
        return dupes[:50]  # Cap output

    # -- Content quality --

    def _content_quality(self) -> Dict[str, Any]:
        title_in_text_scores = []
        non_ascii_ratios = []
        math_heavy_count = 0
        languages = Counter()

        for s in self.samples:
            title = s["title"]
            text = s["text"]

            # Title-in-text score
            score = fuzz.partial_ratio(title.lower(), text[:8000].lower())
            title_in_text_scores.append(score)

            # Non-ASCII density
            ratio = _non_ascii_ratio(title)
            non_ascii_ratios.append(ratio)

            # Math-heavy titles
            if _is_math_heavy(title):
                math_heavy_count += 1

            # Simple language detection (presence of common French/German words)
            text_lower = text[:2000].lower()
            if re.search(r"\b(théorème|démonstration|soit|dans|nous|une)\b", text_lower):
                languages["french"] += 1
            elif re.search(r"\b(beweis|satz|sei|und|die|der)\b", text_lower):
                languages["german"] += 1
            else:
                languages["english"] += 1

        low_match = sum(1 for s in title_in_text_scores if s < 70)
        medium_match = sum(1 for s in title_in_text_scores if 70 <= s < 85)
        high_match = sum(1 for s in title_in_text_scores if s >= 85)

        return {
            "title_in_text": {
                "mean": round(sum(title_in_text_scores) / len(title_in_text_scores), 1) if title_in_text_scores else 0,
                "p5": round(_percentile(title_in_text_scores, 5), 1),
                "p25": round(_percentile(title_in_text_scores, 25), 1),
                "low_match_lt70": low_match,
                "medium_match_70_85": medium_match,
                "high_match_gte85": high_match,
            },
            "non_ascii_title_ratio": {
                "mean": round(sum(non_ascii_ratios) / len(non_ascii_ratios) * 100, 2) if non_ascii_ratios else 0,
                "titles_with_non_ascii": sum(1 for r in non_ascii_ratios if r > 0),
            },
            "math_heavy_titles": math_heavy_count,
            "language_distribution": dict(languages.most_common()),
        }

    # -- Tokenisation audit --

    def _tokenisation_audit(self) -> Dict[str, Any]:
        """Estimate token counts and label mask ratios."""
        # Rough estimate: 1 token ≈ 4 chars for English text
        CHARS_PER_TOKEN = 4.0

        seq_lengths = []
        assistant_ratios = []
        truncated = 0
        MAX_SEQ = 2048

        for s in self.samples:
            messages = s["messages"]

            # Estimate total sequence length
            total_chars = sum(len(m.get("content", "")) for m in messages)
            total_chars += 50  # chat template overhead
            est_tokens = total_chars / CHARS_PER_TOKEN
            seq_lengths.append(est_tokens)

            if est_tokens > MAX_SEQ:
                truncated += 1

            # Estimate assistant response ratio
            assistant_chars = len(messages[-1].get("content", ""))
            if total_chars > 0:
                assistant_ratios.append(assistant_chars / total_chars)

        return {
            "estimated_token_lengths": {
                "mean": round(sum(seq_lengths) / len(seq_lengths), 0) if seq_lengths else 0,
                "median": round(_percentile(seq_lengths, 50), 0),
                "p95": round(_percentile(seq_lengths, 95), 0),
                "max": round(max(seq_lengths), 0) if seq_lengths else 0,
            },
            "truncation_rate": f"{truncated}/{len(self.samples)} ({truncated/len(self.samples)*100:.1f}%)" if self.samples else "0/0",
            "assistant_response_ratio": {
                "mean": round(sum(assistant_ratios) / len(assistant_ratios) * 100, 1) if assistant_ratios else 0,
                "description": "% of total chars that are the assistant response (training signal)",
            },
        }


# ---------------------------------------------------------------------------
# Report printing
# ---------------------------------------------------------------------------

def print_report(report: Dict[str, Any]) -> None:
    """Print a human-readable inspection report."""
    split = report.get("split", "")
    n = report["total_samples"]
    print(f"\n{'=' * 70}")
    print(f"  DATA QUALITY REPORT — {split}  ({n:,} samples)")
    print(f"{'=' * 70}")

    # Distributions
    dist = report["distributions"]
    print(f"\n--- Distributions ---")
    for key in ["title_length", "author_count", "author_name_length", "text_length"]:
        d = dist.get(key, {})
        if d:
            print(f"  {key}:")
            print(f"    min={d['min']}  p5={d['p5']}  median={d['median']}  "
                  f"mean={d['mean']}  p95={d['p95']}  max={d['max']}")

    # Anomalies
    anom = report["anomalies"]
    print(f"\n--- Anomalies ---")
    if not anom:
        print("  None detected")
    else:
        for key, count in sorted(anom.items()):
            flag = " !!!" if count > 10 else ""
            print(f"  {key:<25s} {count:>6}{flag}")

    # Content quality
    cq = report["content_quality"]
    print(f"\n--- Content Quality ---")
    tit = cq["title_in_text"]
    print(f"  Title-in-text match:  mean={tit['mean']}  p5={tit['p5']}  p25={tit['p25']}")
    print(f"    High (>=85): {tit['high_match_gte85']:,}  "
          f"Medium (70-85): {tit['medium_match_70_85']:,}  "
          f"Low (<70): {tit['low_match_lt70']:,}")
    na = cq["non_ascii_title_ratio"]
    print(f"  Titles with non-ASCII chars: {na['titles_with_non_ascii']:,} "
          f"(mean ratio: {na['mean']}%)")
    print(f"  Math-heavy titles: {cq['math_heavy_titles']:,}")
    print(f"  Languages: {cq['language_distribution']}")

    # Tokenisation
    tok = report["tokenisation"]
    print(f"\n--- Tokenisation (estimated) ---")
    tl = tok["estimated_token_lengths"]
    print(f"  Sequence length:  mean={tl['mean']:.0f}  median={tl['median']:.0f}  "
          f"p95={tl['p95']:.0f}  max={tl['max']:.0f}")
    print(f"  Truncation (>{2048} tokens): {tok['truncation_rate']}")
    ar = tok["assistant_response_ratio"]
    print(f"  Assistant response ratio: {ar['mean']}% of total chars")

    # Issues summary
    issues = report["issues"]
    if issues:
        print(f"\n--- Issues ({len(issues)} total) ---")
        by_type = Counter(i["type"] for i in issues)
        for t, c in by_type.most_common():
            print(f"  {t:<25s} {c:>6}")
        # Show first 5 issues as examples
        print(f"\n  First 5 issues:")
        for issue in issues[:5]:
            print(f"    [{issue['type']}] {issue['detail']}")
    else:
        print(f"\n  No issues detected")

    print()


def print_samples(samples: List[Dict[str, Any]], n: int = 10, seed: int = 42) -> None:
    """Print random samples for manual spot-checking."""
    rng = random.Random(seed)
    indices = rng.sample(range(len(samples)), min(n, len(samples)))

    print(f"\n{'=' * 70}")
    print(f"  RANDOM SAMPLES ({n} of {len(samples):,})")
    print(f"{'=' * 70}")

    for idx in indices:
        s = samples[idx]
        title = s["title"]
        authors = s["authors"]
        text_preview = s["text"][:200].replace("\n", " ")

        # Check title-in-text
        score = fuzz.partial_ratio(title.lower(), s["text"][:8000].lower())

        print(f"\n  [{idx}] Title: {title}")
        print(f"       Authors: {', '.join(authors)}")
        print(f"       Text preview: {text_preview}...")
        print(f"       Title-in-text: {score:.0f}%  |  Text len: {len(s['text']):,} chars")
        print(f"       {'---' * 20}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect data quality of PDF metadata training datasets",
    )
    parser.add_argument(
        "dataset_dir", nargs="?", type=Path,
        help="Directory containing train.jsonl, val.jsonl, test.jsonl",
    )
    parser.add_argument(
        "--raw", type=Path, default=None,
        help="Inspect a single raw JSONL file instead of split datasets",
    )
    parser.add_argument(
        "--show-samples", type=int, default=0,
        help="Print N random samples for manual review",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write full report to JSON file",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for sampling (default: 42)",
    )
    args = parser.parse_args()

    if not args.dataset_dir and not args.raw:
        parser.error("Provide either dataset_dir or --raw")

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    all_reports = {}

    if args.raw:
        # Inspect raw file
        print(f"Loading {args.raw}...")
        samples = load_split(args.raw)
        inspector = DatasetInspector(samples, split_name=str(args.raw))
        report = inspector.run_all()
        print_report(report)
        all_reports["raw"] = report

        if args.show_samples > 0:
            print_samples(samples, args.show_samples, args.seed)

    else:
        # Inspect each split
        for split_name in ["train", "val", "test"]:
            path = args.dataset_dir / f"{split_name}.jsonl"
            if not path.exists():
                print(f"  Skipping {split_name} (not found)")
                continue

            print(f"Loading {path}...")
            samples = load_split(path)
            inspector = DatasetInspector(samples, split_name=split_name)
            report = inspector.run_all()
            print_report(report)
            all_reports[split_name] = report

            if args.show_samples > 0 and split_name == "train":
                print_samples(samples, args.show_samples, args.seed)

        # Cross-split leakage check
        if "train" in all_reports and "test" in all_reports:
            print(f"\n--- Cross-Split Leakage Check ---")
            train_path = args.dataset_dir / "train.jsonl"
            test_path = args.dataset_dir / "test.jsonl"
            train_samples = load_split(train_path)
            test_samples = load_split(test_path)

            train_titles = {s["title"].lower().strip() for s in train_samples}
            leaked = [s for s in test_samples if s["title"].lower().strip() in train_titles]
            print(f"  Exact title overlap (train vs test): {len(leaked)}")
            if leaked:
                print(f"  !!! DATA LEAKAGE DETECTED — {len(leaked)} test titles appear in train")
                for l in leaked[:5]:
                    print(f"    - {l['title'][:80]}")
            else:
                print(f"  No leakage detected")

    # Write JSON report
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            # Strip non-serialisable fields
            clean = {}
            for k, v in all_reports.items():
                r = dict(v)
                r.pop("issues", None)  # issues contain detail strings, keep in JSON
                clean[k] = v
            json.dump(all_reports, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nFull report written to {args.output}")

    # Summary verdict
    total_issues = sum(r.get("issue_count", 0) for r in all_reports.values())
    total_samples = sum(r.get("total_samples", 0) for r in all_reports.values())
    print(f"\n{'=' * 70}")
    if total_issues == 0:
        print(f"  VERDICT: CLEAN — {total_samples:,} samples, 0 issues")
    elif total_issues < total_samples * 0.01:
        print(f"  VERDICT: GOOD — {total_samples:,} samples, {total_issues} issues (<1%)")
    elif total_issues < total_samples * 0.05:
        print(f"  VERDICT: ACCEPTABLE — {total_samples:,} samples, {total_issues} issues (<5%)")
    else:
        print(f"  VERDICT: NEEDS ATTENTION — {total_samples:,} samples, {total_issues} issues ({total_issues/total_samples*100:.1f}%)")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
