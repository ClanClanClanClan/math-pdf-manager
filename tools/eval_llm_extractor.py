#!/usr/bin/env python3
"""Measure the LLM metadata extractor against gold pairs.

Answers "is the LLM good enough yet?" with numbers, before investing in a
fine-tuning loop.  Runs the local GGUF model over recorded gold pairs
(text -> title/authors from authoritative API resolutions / user
corrections) and reports title-exact, title-similarity, and author-F1.

REQUIRES a GPU machine with ``llama-cpp-python`` + the model present
(``~/.mathpdf_models/gguf/``).  It is NOT run in CI — the pure scoring
helpers it uses live in ``processing.metadata_training`` and ARE unit
tested there.

Usage::

    PYTHONPATH=src python tools/eval_llm_extractor.py --limit 200
    PYTHONPATH=src python tools/eval_llm_extractor.py --dataset /path/pairs.jsonl
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Eval the LLM metadata extractor")
    ap.add_argument("--dataset", default=None,
                    help="JSONL of gold pairs (default: the library dataset)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--model", default=None, help="explicit GGUF path")
    ap.add_argument("--show-misses", type=int, default=10)
    args = ap.parse_args(argv)

    from processing.metadata_training import (
        load_pairs, dataset_path, title_exact, title_similarity, author_f1,
    )
    from pdf_processing.llm_extractor import LLMMetadataExtractor

    if not LLMMetadataExtractor.is_available():
        print("ERROR: llama-cpp-python not installed; run on the model machine.",
              file=sys.stderr)
        return 2
    model_path = args.model or LLMMetadataExtractor.local_model_path()
    if not model_path:
        print("ERROR: no GGUF model cached in ~/.mathpdf_models/gguf/.",
              file=sys.stderr)
        return 2

    if args.dataset:
        import json
        pairs = [json.loads(l) for l in Path(args.dataset).read_text().splitlines() if l.strip()]
    else:
        from core.config_paths import get_library_root
        pairs = load_pairs(get_library_root())
    if not pairs:
        print("No gold pairs found. Ingest some papers first to capture them.")
        return 1
    if args.limit:
        pairs = pairs[: args.limit]

    print(f"Evaluating {len(pairs)} pairs with {Path(str(model_path)).name} …")
    ex = LLMMetadataExtractor(model_path=model_path)
    t_exact, t_sim, a_f1, misses = [], [], [], []
    try:
        for i, p in enumerate(pairs, 1):
            pred = ex.extract(p.get("text", ""))
            te = title_exact(pred.get("title", ""), p.get("title", ""))
            ts = title_similarity(pred.get("title", ""), p.get("title", ""))
            af = author_f1(pred.get("authors", []), p.get("authors", []))
            t_exact.append(1.0 if te else 0.0)
            t_sim.append(ts)
            a_f1.append(af)
            if not te and len(misses) < args.show_misses:
                misses.append((p.get("title", ""), pred.get("title", ""), ts))
            if i % 25 == 0:
                print(f"  {i}/{len(pairs)}…")
    finally:
        ex.close()

    n = len(t_exact)
    print("\n=== LLM extractor eval ===")
    print(f"  title exact-match : {sum(t_exact)/n:.1%}")
    print(f"  title similarity  : mean {statistics.mean(t_sim):.2f}, "
          f"median {statistics.median(t_sim):.2f}")
    print(f"  author F1         : mean {statistics.mean(a_f1):.2f}")
    if misses:
        print("\n  sample title misses (gold -> predicted, sim):")
        for gold, pred, sim in misses:
            print(f"   [{sim:.2f}] {gold[:60]!r} -> {pred[:60]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
