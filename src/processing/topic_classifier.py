#!/usr/bin/env python3
"""Classify papers into topic folders using keyword matching + LLM.

Supports the topic folders:
- 07a: BSDEs (backward stochastic differential equations)
- 07b: Contract theory (principal-agent problems)
- 07c: Time-inconsistent stochastic control
- 07d: Stackelberg games
- 07e: Optimal control on networks
- 07f: Non-commutative stochastic calculus

Usage::

    python -m processing.topic_classifier "Some Paper Title"
    python -m processing.topic_classifier --file paper.pdf
    python -m processing.topic_classifier --scan /path/to/library/01/A/ --limit 50
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


# ---------------------------------------------------------------------------
# Topic keyword definitions
# ---------------------------------------------------------------------------
TOPICS = {
    "07a": {
        "name": "BSDEs",
        "full_name": "Backward Stochastic Differential Equations",
        "primary": [
            r"\bBSDE\b", r"\bBSDEs\b",
            r"\bbackward stochastic\b",
            r"\breflected BSDE\b",
            r"\bquadratic BSDE\b",
            r"\bmean.field BSDE\b",
            r"\bg.expectation\b",
            r"\bg.supermartingale\b",
            r"\bDoob.Meyer.Mertens\b",
        ],
        "secondary": [
            r"\bstochastic differential equation\b",
            r"\bmartingale representation\b",
            r"\bcomparison theorem\b.*\bSDE\b",
            r"\bPardoux\b.*\bPeng\b",
        ],
        "primary_weight": 3.0,
        "secondary_weight": 1.0,
        "threshold": 3.0,
    },
    "07b": {
        "name": "Contract theory",
        "full_name": "Contract Theory (Principal-Agent Problems)",
        "primary": [
            r"\bprincipal.agent\b",
            r"\bmoral hazard\b",
            r"\badverse selection\b",
            r"\bcontract (?:design|theory)\b",
            r"\bincentive (?:compatible|compatibility|constraint)\b",
            r"\bmechanism design\b",
            r"\bdelegation\b.*\bagent\b",
        ],
        "secondary": [
            r"\basymmetric information\b",
            r"\bhidden (?:action|type|information)\b",
            r"\bscreening\b",
            r"\bsignaling\b.*\bequilibrium\b",
            r"\boptimal compensation\b",
        ],
        "primary_weight": 3.0,
        "secondary_weight": 1.0,
        "threshold": 3.0,
    },
    "07c": {
        "name": "Time-inconsistent control",
        "full_name": "Time-Inconsistent Stochastic Control",
        "primary": [
            r"\btime.inconsisten\w*\b",
            r"\btime.consisten\w*\b.*\b(?:control|equilibri)\b",
            r"\bhyperbolic discount\b",
            r"\bnaive\b.*\bsophisticated\b",
            r"\bpre.commitment\b",
        ],
        "secondary": [
            r"\bequilibrium (?:control|strateg)\b",
            r"\bnon.exponential discount\b",
            r"\bpresent bias\b",
            r"\bquasi.hyperbolic\b",
            r"\bStrotz\b",
        ],
        "primary_weight": 3.0,
        "secondary_weight": 1.0,
        "threshold": 3.0,
    },
    "07d": {
        "name": "Stackelberg games",
        "full_name": "Stackelberg Games",
        "primary": [
            r"\bStackelberg\b",
            r"\bleader.follower\b",
            r"\bhierarchical (?:game|control|equilibrium)\b",
            r"\bbilevel (?:optimization|problem|programming)\b",
        ],
        "secondary": [
            r"\bincentive (?:Stackelberg|equilibrium)\b",
            r"\bmulti.leader\b",
            r"\blead(?:er|ing).*\bfollow(?:er|ing)\b",
        ],
        "primary_weight": 3.0,
        "secondary_weight": 1.0,
        "threshold": 3.0,
    },
    "07e": {
        "name": "Control on networks",
        "full_name": "Optimal Control on Networks",
        "primary": [
            r"\bnetwork\b.*\b(?:Hamilton|HJ|optimal control|junction)\b",
            r"\b(?:Hamilton|HJ|optimal control|junction)\b.*\bnetwork\b",
            r"\bjunction\b.*\b(?:condition|Hamilton|control)\b",
            r"\bmean.field\b.*\bnetwork\b",
            r"\bHamilton.Jacobi\b.*\b(?:network|junction|graph)\b",
            r"\b(?:network|junction|graph)\b.*\bHamilton.Jacobi\b",
        ],
        "secondary": [
            r"\btraffic flow\b.*\bnetwork\b",
            r"\bgraph\b.*\bPDE\b",
            r"\bviscosity solution\b.*\bnetwork\b",
        ],
        "primary_weight": 3.0,
        "secondary_weight": 1.0,
        "threshold": 3.0,
    },
    "07f": {
        "name": "Non-commutative stochastic calculus",
        "full_name": "Non-Commutative Stochastic Calculus",
        "primary": [
            r"\bnon.commutativ\w*\b.*\bstochastic\b",
            r"\bquantum stochastic\b",
            r"\bIt[ôo].Clifford\b",
            r"\bHeisenberg commutation\b",
            r"\bfree Brownian\b",
        ],
        "secondary": [
            r"\bClifford (?:algebra|integral)\b",
            r"\bfree probability\b",
            r"\bquantum (?:process|noise|filtering)\b",
            r"\bWigner\b.*\bsemigroup\b",
        ],
        "primary_weight": 3.0,
        "secondary_weight": 1.0,
        "threshold": 3.0,
    },
}


# ---------------------------------------------------------------------------
# Keyword-based classifier
# ---------------------------------------------------------------------------
def classify_by_keywords(
    title: str,
    abstract: str = "",
    *,
    threshold_multiplier: float = 1.0,
) -> list[dict]:
    """Classify a paper by keyword matching on title and abstract.

    Returns a list of matching topics sorted by score (highest first).
    Each entry has: topic_code, topic_name, score, method, matched_keywords.
    """
    text = f"{title} {abstract}".strip()
    if not text:
        return []

    # NFC normalize
    text = unicodedata.normalize("NFC", text)

    results = []

    for code, topic in TOPICS.items():
        score = 0.0
        matched = []

        for pattern in topic["primary"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += topic["primary_weight"]
                matched.append(pattern)

        for pattern in topic["secondary"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += topic["secondary_weight"]
                matched.append(pattern)

        effective_threshold = topic["threshold"] * threshold_multiplier
        if score >= effective_threshold:
            results.append({
                "topic_code": code,
                "topic_name": topic["name"],
                "full_name": topic["full_name"],
                "score": score,
                "method": "keyword",
                "matched_keywords": matched,
            })

    results.sort(key=lambda x: -x["score"])
    return results


# ---------------------------------------------------------------------------
# LLM-based classifier (zero-shot)
# ---------------------------------------------------------------------------
def classify_by_llm(
    title: str,
    text: str = "",
) -> list[dict]:
    """Classify a paper using the local LLM (Qwen2.5-7B).

    Falls back gracefully if the LLM is not available.
    """
    try:
        from llama_cpp import Llama, LlamaGrammar
    except ImportError:
        logger.debug("llama-cpp-python not available, skipping LLM classification")
        return []

    model_path = Path.home() / ".mathpdf_models/gguf/qwen2.5-7b-pdfmeta-q4_k_m.gguf"
    if not model_path.exists():
        logger.debug("GGUF model not found at %s", model_path)
        return []

    # Build classification prompt
    topic_list = "\n".join(
        f"  {code}: {t['full_name']}" for code, t in TOPICS.items()
    )

    prompt = (
        "<|im_start|>system\n"
        "You are a mathematics paper classifier. Given a paper title and text excerpt, "
        "determine which specialized topic folder(s) it belongs to. "
        "Return a JSON object with \"topics\" (array of topic codes) and \"confidence\" (0-100).\n"
        f"Available topics:\n{topic_list}\n"
        "If the paper doesn't clearly fit any topic, return {\"topics\": [], \"confidence\": 0}.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        f"Title: {title}\n"
    )
    if text:
        # Truncate text to avoid exceeding context
        prompt += f"Text excerpt: {text[:1500]}\n"
    prompt += (
        "\nClassify this paper into the appropriate topic(s).\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    grammar = LlamaGrammar.from_string(r'''
root ::= "{" ws "\"topics\"" ws ":" ws topics "," ws "\"confidence\"" ws ":" ws number ws "}"
topics ::= "[" ws (string (ws "," ws string)*)? ws "]"
string ::= "\"" [a-z0-9]+ "\""
number ::= [0-9]+
ws ::= [ \t\n]*
''')

    try:
        llm = Llama(model_path=str(model_path), n_ctx=4096, verbose=False)
        output = llm.create_completion(
            prompt, max_tokens=128, grammar=grammar, temperature=0.0
        )
        response = json.loads(output["choices"][0]["text"].strip())
        del llm

        results = []
        for code in response.get("topics", []):
            if code in TOPICS:
                results.append({
                    "topic_code": code,
                    "topic_name": TOPICS[code]["name"],
                    "full_name": TOPICS[code]["full_name"],
                    "score": response.get("confidence", 50) / 100.0,
                    "method": "llm",
                })
        return results

    except Exception as exc:
        logger.warning("LLM classification failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------
def classify(
    title: str,
    abstract: str = "",
    text: str = "",
    *,
    use_llm: bool = True,
) -> list[dict]:
    """Classify a paper into topic folders.

    Tries keyword matching first; if no confident match, falls back to LLM.

    Returns a list of matching topics sorted by confidence.
    """
    # Tier 1: keyword matching
    results = classify_by_keywords(title, abstract)
    if results:
        return results

    # Tier 2: LLM classification
    if use_llm:
        llm_results = classify_by_llm(title, text or abstract)
        if llm_results:
            return llm_results

    return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description="Classify papers into topic folders")
    parser.add_argument("title", nargs="?", help="Paper title to classify")
    parser.add_argument("--file", type=Path, help="PDF file to classify")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM, keywords only")
    parser.add_argument("--scan", type=Path, help="Scan a directory of PDFs")
    parser.add_argument("--limit", type=int, help="Limit scan to N files")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.scan:
        # Batch classification
        pdfs = sorted(args.scan.rglob("*.pdf"))
        if args.limit:
            pdfs = pdfs[: args.limit]

        classified = 0
        for pdf in pdfs:
            stem = unicodedata.normalize("NFC", pdf.stem)
            title = stem.split(" - ", 1)[1] if " - " in stem else stem
            results = classify(title, use_llm=not args.no_llm)
            if results:
                classified += 1
                topics = ", ".join(f"{r['topic_code']}({r['topic_name']})" for r in results)
                print(f"  {title[:55]:55s} → {topics}")

        print(f"\nClassified {classified}/{len(pdfs)} papers into topics")

    elif args.file:
        import fitz

        doc = fitz.open(args.file)
        text = ""
        for i in range(min(3, len(doc))):
            text += doc[i].get_text()
        doc.close()

        stem = unicodedata.normalize("NFC", args.file.stem)
        title = stem.split(" - ", 1)[1] if " - " in stem else stem

        results = classify(title, text=text, use_llm=not args.no_llm)
        if results:
            for r in results:
                print(f"  {r['topic_code']}: {r['full_name']} (score: {r['score']:.1f}, method: {r['method']})")
        else:
            print("  No topic match found.")

    elif args.title:
        results = classify(args.title, use_llm=not args.no_llm)
        if args.json:
            print(json.dumps(results, indent=2))
        elif results:
            for r in results:
                print(f"  {r['topic_code']}: {r['full_name']} (score: {r['score']:.1f}, method: {r['method']})")
        else:
            print("  No topic match found.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
