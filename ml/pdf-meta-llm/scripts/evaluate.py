#!/usr/bin/env python3
"""
Evaluation framework for PDF metadata extraction.

Measures extraction accuracy against ground-truth labels derived from
the filename convention ``Author1, Author2 - Title.pdf``.

Usage::

    # Evaluate the full enhanced pipeline on a sample
    python scripts/evaluate.py <pdf_root> --methods pipeline --sample 500

    # Evaluate all methods and compare
    python scripts/evaluate.py <pdf_root> --methods all --sample 200 --output results.json

    # Evaluate with a specific seed for reproducibility
    python scripts/evaluate.py <pdf_root> --methods pipeline llm --sample 300 --seed 42

Metrics:
    - Title exact match (after normalization)
    - Title fuzzy match (rapidfuzz ratio)
    - Title token F1 (word-level precision/recall)
    - Author set match (Jaccard similarity of normalized name sets)
    - Combined score (harmonic mean of title fuzzy + author Jaccard)
    - Per-sample timing
"""

import argparse
import json
import logging
import random
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

# Add src/ to path so pdf_processing imports work
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_src_dir = str(_project_root / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Reuse extraction and parsing from the existing training data script
try:
    from extract_text import extract_text, parse_filename, skip_this
except ImportError:
    # When invoked from the repo root
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_text import extract_text, parse_filename, skip_this

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metric functions
# ---------------------------------------------------------------------------

def _normalize_for_comparison(s: str) -> str:
    """NFC-normalise, lowercase, collapse whitespace, strip boundary punctuation.

    macOS HFS+/APFS stores filenames in NFD (decomposed) form, while LLMs
    output NFC (composed) form.  Without NFC normalisation, identical-looking
    strings like ``é`` (U+00E9) and ``e`` + combining acute (U+0065 U+0301)
    are treated as different, producing ~10% false misses on French/German titles.
    """
    s = unicodedata.normalize("NFC", s)
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^[^\w]+|[^\w]+$", "", s)
    return s


def title_exact_match(predicted: str, ground_truth: str) -> bool:
    return _normalize_for_comparison(predicted) == _normalize_for_comparison(ground_truth)


def title_fuzzy_score(predicted: str, ground_truth: str) -> float:
    """Return similarity ratio in [0, 100]."""
    return fuzz.ratio(
        _normalize_for_comparison(predicted),
        _normalize_for_comparison(ground_truth),
    )


def title_token_f1(predicted: str, ground_truth: str) -> float:
    """Word-level F1 between predicted and ground-truth title."""
    pred_tokens = set(_normalize_for_comparison(predicted).split())
    gt_tokens = set(_normalize_for_comparison(ground_truth).split())

    if not pred_tokens or not gt_tokens:
        return 0.0

    common = pred_tokens & gt_tokens
    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(gt_tokens)

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _normalize_author_name(name: str) -> str:
    """Normalize an author name for comparison."""
    name = unicodedata.normalize("NFC", name)
    name = name.lower().strip()
    name = re.sub(r"^(dr|prof|professor)\s+", "", name)
    return " ".join(name.split())


def author_set_jaccard(predicted: List[str], ground_truth: List[str]) -> float:
    """Jaccard similarity of author name sets."""
    pred_set = {_normalize_author_name(a) for a in predicted if a.strip()}
    gt_set = {_normalize_author_name(a) for a in ground_truth if a.strip()}

    if not pred_set and not gt_set:
        return 1.0
    if not pred_set or not gt_set:
        return 0.0

    intersection = len(pred_set & gt_set)
    union = len(pred_set | gt_set)
    return intersection / union if union else 0.0


def combined_score(title_fuzzy: float, author_jaccard: float) -> float:
    """Harmonic mean of title fuzzy (normalised to 0-1) and author Jaccard."""
    tf = title_fuzzy / 100.0
    if tf + author_jaccard == 0:
        return 0.0
    return 2 * tf * author_jaccard / (tf + author_jaccard)


# ---------------------------------------------------------------------------
# Evaluation result accumulator
# ---------------------------------------------------------------------------

class EvaluationResult:
    """Accumulates metrics across many samples."""

    def __init__(self, method_name: str):
        self.method_name = method_name
        self.title_exact: List[bool] = []
        self.title_fuzzy: List[float] = []
        self.title_f1: List[float] = []
        self.author_match: List[float] = []
        self.combined: List[float] = []
        self.timings: List[float] = []
        self.errors: List[Dict[str, Any]] = []
        self.samples: List[Dict[str, Any]] = []

    def add(
        self,
        pdf_path: str,
        predicted_title: str,
        predicted_authors: List[str],
        gt_title: str,
        gt_authors: List[str],
        elapsed: float,
    ) -> None:
        exact = title_exact_match(predicted_title, gt_title)
        fuzzy = title_fuzzy_score(predicted_title, gt_title)
        f1 = title_token_f1(predicted_title, gt_title)
        am = author_set_jaccard(predicted_authors, gt_authors)
        cs = combined_score(fuzzy, am)

        self.title_exact.append(exact)
        self.title_fuzzy.append(fuzzy)
        self.title_f1.append(f1)
        self.author_match.append(am)
        self.combined.append(cs)
        self.timings.append(elapsed)

        self.samples.append({
            "path": pdf_path,
            "gt_title": gt_title,
            "gt_authors": gt_authors,
            "pred_title": predicted_title,
            "pred_authors": predicted_authors,
            "title_exact": exact,
            "title_fuzzy": fuzzy,
            "title_f1": f1,
            "author_jaccard": am,
            "combined": cs,
            "time_sec": elapsed,
        })

    def add_error(self, pdf_path: str, error: str) -> None:
        self.errors.append({"path": pdf_path, "error": error})

    def summary(self) -> Dict[str, Any]:
        n = len(self.title_exact)
        if n == 0:
            return {"method": self.method_name, "n_samples": 0}
        return {
            "method": self.method_name,
            "n_samples": n,
            "title_exact_match": sum(self.title_exact) / n,
            "title_fuzzy_mean": sum(self.title_fuzzy) / n,
            "title_token_f1_mean": sum(self.title_f1) / n,
            "author_jaccard_mean": sum(self.author_match) / n,
            "combined_score": sum(self.combined) / n,
            "mean_time_sec": sum(self.timings) / n,
            "n_errors": len(self.errors),
        }


# ---------------------------------------------------------------------------
# Extraction method wrappers
# ---------------------------------------------------------------------------

def _extract_filename(pdf_path: Path, text: str) -> Dict[str, Any]:
    """Baseline: just parse the filename."""
    from extract_text import parse_filename as pf

    title, authors = pf(pdf_path)
    return {"title": title or "", "authors": authors}


def _extract_pipeline(pdf_path: Path, text: str) -> Dict[str, Any]:
    """Full enhanced pipeline via the facade."""
    from pdf_processing.extract_metadata_facade import extract_pdf_metadata_enhanced

    meta = extract_pdf_metadata_enhanced(pdf_path)
    title = meta.get("title", "")
    authors_raw = meta.get("authors", [])
    if isinstance(authors_raw, str):
        authors_raw = [a.strip() for a in authors_raw.split(";") if a.strip()]
    return {"title": title, "authors": authors_raw}


def _extract_heuristic(pdf_path: Path, text: str) -> Dict[str, Any]:
    """Heuristic-only extraction from text blocks."""
    try:
        from pdf_processing.parsers.metadata_extraction import (
            extract_title_multi_method,
            extract_authors_multi_method,
        )
        from pdf_processing.parsers.text_extraction import extract_with_pymupdf

        blocks = extract_with_pymupdf(str(pdf_path), max_pages=3)
        title_result = extract_title_multi_method(blocks, str(pdf_path))
        author_result = extract_authors_multi_method(blocks, str(pdf_path))

        title = title_result[0] if title_result else ""
        authors_str = author_result[0] if author_result else ""
        authors = [a.strip() for a in authors_str.split(";") if a.strip()] if authors_str else []
        return {"title": title, "authors": authors}
    except Exception as e:
        logger.debug(f"Heuristic extraction failed: {e}")
        return {"title": "", "authors": []}


def _extract_llm(pdf_path: Path, text: str) -> Dict[str, Any]:
    """LLM-only extraction using GBNF grammar constraints."""
    from pdf_processing.llm_extractor import LLMMetadataExtractor

    if not LLMMetadataExtractor.is_available():
        raise RuntimeError("llama-cpp-python not installed")

    # Use module-level singleton to avoid reloading model per PDF
    global _llm_extractor
    if "_llm_extractor" not in globals() or _llm_extractor is None:
        _llm_extractor = LLMMetadataExtractor()

    result = _llm_extractor.extract(text)
    return {
        "title": result.get("title", ""),
        "authors": result.get("authors", []),
    }

_llm_extractor = None


METHOD_REGISTRY = {
    "filename": _extract_filename,
    "pipeline": _extract_pipeline,
    "heuristic": _extract_heuristic,
    "llm": _extract_llm,
}


# ---------------------------------------------------------------------------
# Main evaluation logic
# ---------------------------------------------------------------------------

def collect_samples(
    pdf_root: Path,
    sample_size: Optional[int] = None,
    seed: int = 42,
) -> List[Tuple[Path, str, List[str]]]:
    """Collect PDFs with ground-truth from filenames.

    Returns list of (pdf_path, gt_title, gt_authors).
    """
    candidates = []
    for pdf in pdf_root.rglob("*.pdf"):
        if skip_this(pdf):
            continue
        title, authors = parse_filename(pdf)
        if title and authors:
            candidates.append((pdf, title, authors))

    if sample_size and sample_size < len(candidates):
        random.seed(seed)
        candidates = random.sample(candidates, sample_size)

    return candidates


def evaluate_method(
    method_name: str,
    samples: List[Tuple[Path, str, List[str]]],
    verbose: bool = False,
) -> EvaluationResult:
    """Run a single extraction method on all samples and collect metrics."""
    extract_fn = METHOD_REGISTRY[method_name]
    result = EvaluationResult(method_name)

    for pdf_path, gt_title, gt_authors in samples:
        try:
            # Extract text for methods that need it
            text = extract_text(pdf_path)

            t0 = time.monotonic()
            extracted = extract_fn(pdf_path, text)
            elapsed = time.monotonic() - t0

            pred_title = extracted.get("title", "")
            pred_authors = extracted.get("authors", [])
            if isinstance(pred_authors, str):
                pred_authors = [a.strip() for a in pred_authors.split(";") if a.strip()]

            result.add(
                str(pdf_path), pred_title, pred_authors,
                gt_title, gt_authors, elapsed,
            )

            if verbose and not title_exact_match(pred_title, gt_title):
                print(
                    f"  MISS [{method_name}] {pdf_path.name}\n"
                    f"    GT:   {gt_title}\n"
                    f"    PRED: {pred_title}"
                )

        except Exception as e:
            result.add_error(str(pdf_path), str(e))
            if verbose:
                print(f"  ERROR [{method_name}] {pdf_path.name}: {e}")

    return result


def print_summary_table(results: List[EvaluationResult]) -> None:
    """Print a formatted comparison table."""
    header = (
        f"{'Method':<16} | {'Title Exact':>11} | {'Title Fuzzy':>11} | "
        f"{'Title F1':>8} | {'Author Match':>12} | {'Combined':>8} | {'Avg Time':>8}"
    )
    sep = "-" * len(header)

    print()
    print("=== PDF Metadata Extraction Benchmark ===")
    print()
    print(header)
    print(sep)

    for r in results:
        s = r.summary()
        if s["n_samples"] == 0:
            print(f"{s['method']:<16} | {'no data':>11} |")
            continue
        print(
            f"{s['method']:<16} | "
            f"{s['title_exact_match']:>10.1%} | "
            f"{s['title_fuzzy_mean']:>10.1f} | "
            f"{s['title_token_f1_mean']:>7.3f} | "
            f"{s['author_jaccard_mean']:>11.3f} | "
            f"{s['combined_score']:>7.3f} | "
            f"{s['mean_time_sec']:>7.3f}s"
        )

    print(sep)
    print(f"Samples: {results[0].summary()['n_samples']}  |  "
          f"Errors: {sum(len(r.errors) for r in results)}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate PDF metadata extraction accuracy",
    )
    parser.add_argument(
        "pdf_root", type=Path,
        help="Root directory of PDF library",
    )
    parser.add_argument(
        "--methods", nargs="+",
        choices=list(METHOD_REGISTRY.keys()) + ["all"],
        default=["pipeline"],
        help="Extraction methods to evaluate (default: pipeline)",
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="Number of PDFs to sample (default: all)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for sampling (default: 42)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write detailed JSON results to this file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-sample misses",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    # Resolve methods
    methods = args.methods
    if "all" in methods:
        methods = list(METHOD_REGISTRY.keys())

    # Collect samples
    print(f"Collecting samples from {args.pdf_root}...")
    samples = collect_samples(args.pdf_root, args.sample, args.seed)
    print(f"Found {len(samples)} PDFs with ground-truth filenames")

    if not samples:
        print("No samples found. Check that PDFs follow 'Author - Title.pdf' format.")
        sys.exit(1)

    # Evaluate each method
    all_results = []
    for method in methods:
        print(f"Evaluating: {method}...")
        result = evaluate_method(method, samples, verbose=args.verbose)
        all_results.append(result)

    # Print summary
    print_summary_table(all_results)

    # Write detailed results
    if args.output:
        output_data = {
            "seed": args.seed,
            "n_samples": len(samples),
            "methods": {},
        }
        for r in all_results:
            output_data["methods"][r.method_name] = {
                "summary": r.summary(),
                "samples": r.samples,
                "errors": r.errors,
            }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Detailed results written to {args.output}")


if __name__ == "__main__":
    main()
