#!/usr/bin/env python3
"""Validate the topic classifier against the user's hand-filed topic folders.

The library's six ``07x`` topic folders are a labelled dataset: every
paper already filed under ``07a - BSDEs/`` is a known BSDE positive,
etc.  This tool measures the keyword classifier against that ground
truth and reports per-topic recall + precision, so any future change
to the patterns can be re-benchmarked with one command.

Usage::

    PYTHONPATH=src python3 tools/validate_topic_classifier.py
    PYTHONPATH=src python3 tools/validate_topic_classifier.py --sample 120 --pages 2
    PYTHONPATH=src python3 tools/validate_topic_classifier.py --misses 07e

Read-only: never moves or writes anything.

Benchmark as of the mining-driven pattern improvements (sample=120,
pages=2):
    07a 91%  07b 80%  07c 83%  07d 81%  07e 79%  07f 86%
    overall recall 83%, precision 89-100% per topic.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

TOPIC_FOLDERS = {
    "07a - BSDEs": "07a",
    "07b - Contract theory": "07b",
    "07c - Time-inconsistent stochastic control": "07c",
    "07d - Stackelberg games": "07d",
    "07e - Optimal control on networks": "07e",
    "07f - Non-commutative stochastic calculus": "07f",
}


def _title_of(pdf: Path) -> str:
    stem = unicodedata.normalize("NFC", pdf.stem)
    stem = re.sub(r"^\d+\s*[-–]\s*", "", stem)
    return stem.split(" - ", 1)[1].strip() if " - " in stem else stem


def _body_of(pdf: Path, pages: int) -> str:
    if pages <= 0:
        return ""
    try:
        import fitz
        doc = fitz.open(pdf)
        text = "".join(doc[i].get_text() for i in range(min(pages, len(doc))))
        doc.close()
        return text[:4000]
    except Exception:
        return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=120,
                    help="papers per topic (0 = all)")
    ap.add_argument("--pages", type=int, default=2,
                    help="first-page count to read as body text (0 = title only)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--misses", default="",
                    help="print the titles a given topic code misses, then exit")
    args = ap.parse_args(argv)

    from core.config_paths import get_library_root
    from processing.publication_topic_router import resolve_topic
    lib = get_library_root()
    random.seed(args.seed)

    if args.misses:
        target_folder = next(
            (f for f, c in TOPIC_FOLDERS.items() if c == args.misses), None
        )
        if not target_folder:
            print(f"unknown topic code: {args.misses}", file=sys.stderr)
            return 2
        p = lib / target_folder
        misses = []
        for pdf in p.rglob("*.pdf"):
            d = resolve_topic(_title_of(pdf), _body_of(pdf, args.pages))
            if not (d.topic_code or d.suggested_code):
                misses.append(_title_of(pdf))
        print(f"{args.misses}: {len(misses)} miss(es)")
        for m in misses:
            print(f"  - {m[:90]}")
        return 0

    conf: dict = defaultdict(Counter)
    N: Counter = Counter()
    for folder, code in TOPIC_FOLDERS.items():
        p = lib / folder
        if not p.exists():
            continue
        pdfs = list(p.rglob("*.pdf"))
        chosen = pdfs if args.sample <= 0 else random.sample(
            pdfs, min(args.sample, len(pdfs)))
        for pdf in chosen:
            N[code] += 1
            d = resolve_topic(_title_of(pdf), _body_of(pdf, args.pages))
            conf[code][d.topic_code or d.suggested_code or "NONE"] += 1

    predtot: Counter = Counter()
    correct: Counter = Counter()
    tr = tn = 0
    print(f"{'true':5s} {'N':>5s} {'recall':>7s} {'wrong':>6s} {'miss':>6s}")
    print("-" * 36)
    for code in ("07a", "07b", "07c", "07d", "07e", "07f"):
        n = N[code]
        if not n:
            continue
        rec = conf[code][code]
        none = conf[code]["NONE"]
        wrong = n - rec - none
        print(f"{code:5s} {n:>5d} {100*rec/n:>6.0f}% {100*wrong/n:>5.0f}% {100*none/n:>5.0f}%")
        for k, v in conf[code].items():
            predtot[k] += v
            if k == code:
                correct[k] += v
        tr += rec
        tn += n
    print("-" * 36)
    print(f"overall recall: {100*tr/max(tn,1):.0f}%  (n={tn}, sample={args.sample}, pages={args.pages})")
    prec = {c: f"{100*correct[c]/predtot[c]:.0f}%"
            for c in ("07a", "07b", "07c", "07d", "07e", "07f") if predtot[c]}
    print(f"precision per predicted topic: {prec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
