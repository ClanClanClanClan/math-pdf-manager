#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.py  —  textual normalisation & tokenisation helpers
(June 2025, config-based version with sentence case fixes - FINAL FIXED VERSION)

Key public helpers
------------------
• robust_tokenize_with_math
• to_sentence_case_academic
• filter_relevant_whitelist_terms (optimization helper)

FINAL FIXES APPLIED:
1. Math region detection: Check if word contains/overlaps with math regions
2. Lookup table: Ensure PyTorch/TensorFlow are properly added
3. Acronym detection: Add pronouns (IT, HE, SHE, WE, YOU) to exclusions
4. Context-aware contractions: Distinguish "It's" (pronoun) from "IT" (acronym)
"""

from __future__ import annotations

import itertools
import unicodedata
from dataclasses import dataclass
from typing import Sequence

import regex as re

# Import I/O functions from core module
from core.io import load_yaml_config, load_word_list
# Import text canonicalization functions from core module
from core.text_canonicalization import canonicalize, build_canonical_exceptions
# Import Token class from core module
from core.tokenization import Token
# Import tokenization functions from core modules
from core.tokenization import _phrase_regex, mask_math_regions
from core.math_tokenization import DASH_CHARS
# Import filename normalization from core module
from core.latex_processing import normalize_filename
# Import LaTeX processing functions from core module
from core.latex_processing import strip_latex, strip_latex_for_comparison, safe_compare_titles
# Import sentence case functions from core module
from core.sentence_case import _load_sentence_case_config, extract_title_words, filter_relevant_whitelist_terms, to_sentence_case_academic
# Import token normalization from core module
from core.text_canonicalization import normalize_token
# Import segment iterator from core module
from core.tokenization import iterate_nonmath_segments
# Import math-aware tokenization from core module
from core.math_tokenization import robust_tokenize_with_math

# Debug flag for sentence case processing
DEBUG_SENTENCE_CASE = False

# Import functions from core modules (moved to top of file)

# Dash pattern constants for detecting problematic dash usage
_DASH_PATTERNS = {
    "word- space (should not occur)": re.compile(r"\w-\s", re.UNICODE),
    "space - space (should not occur)": re.compile(r"\s-\s", re.UNICODE),
    "space- word (should not occur)": re.compile(r"\s-(?=\w)", re.UNICODE),
}

def debug_print(msg: str) -> None:
    if DEBUG_SENTENCE_CASE:
        print(f"[SENTENCE_CASE] {msg}")

@dataclass
class TexNormalizeConfig:
    """
    Configuration for tex normalization.
    """
    compound_terms: set[str]
    canonical_exceptions: dict[str, str]
    context_hints: dict[str, str]

    @classmethod
    def from_data(cls, data: dict) -> "TexNormalizeConfig":
        return cls(
            compound_terms=set(data.get("compound_terms", [])),
            canonical_exceptions=data.get("canonical_exceptions", {}),
            context_hints=data.get("context_hints", {}),
        )

def is_canonically_equivalent(a: str, b: str) -> bool:
    """NFC-equivalence test used all over the checker."""
    return unicodedata.normalize("NFC", a) == unicodedata.normalize("NFC", b)

def is_series_title(title: str) -> bool:
    """Check if title contains series identifiers."""
    return bool(re.search(r",\s*[MDCLXVI]+\s*$", title.strip(), re.IGNORECASE))

def read_arxiv_id(name: str) -> str | None:
    """Extract arXiv ID from filename."""
    m = re.search(r"(?:arxiv[_\-:]?)?(\d{4}\.\d{4,5})(?:v\d+)?", name, re.IGNORECASE)
    return m.group(1) if m else None

def find_bad_dash_patterns(title: str) -> list[str]:
    """Find problematic dash patterns in title."""
    masked = mask_math_regions(title)
    out = []
    for label, pat in _DASH_PATTERNS.items():
        out.extend(itertools.repeat(label, len(pat.findall(masked))))
    return out

# (imports moved to top of file)

def enforce_ndash_between_authors(s: str, pairs: Sequence[str]) -> str:
    for p in pairs:
        patt = re.compile(rf"\b{re.escape(p.replace('–', '-'))}\b")
        s = patt.sub(p, s)
    return s

def replace_hyphens_with_ndash(text: str, pairs: Sequence[str]) -> str:
    for p in pairs:
        norm = p.replace("–", "-")
        text = re.sub(rf"\b{re.escape(norm)}\b", p, text)
    return text

# ────────────────────────────────────────────────────────────────────────
#  LaTeX stripping (imports moved to top of file)
# ────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────
#  canonicalise (imports moved to top of file)
# ────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────
#  sentence case (imports moved to top of file)
# ────────────────────────────────────────────────────────────────────────

# (import moved to top of file)

# ────────────────────────────────────────────────────────────────────────
#  tokeniser (full implementation for public API)
# ────────────────────────────────────────────────────────────────────────

# (import moved to top of file)

# ────────────────────────────────────────────────────────────────────────
#  misc (imports moved to top of file)
# ────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────
#  Segment iterator excluding math regions (imports moved to top of file)
# ────────────────────────────────────────────────────────────────────────

__all__ = [
    "Token",
    "load_yaml_config",
    "load_word_list",
    "is_series_title",
    "read_arxiv_id",
    "find_bad_dash_patterns",
    "normalize_filename",
    "enforce_ndash_between_authors",
    "replace_hyphens_with_ndash",
    "strip_latex",
    "strip_latex_for_comparison",
    "safe_compare_titles",
    "canonicalize",
    "build_canonical_exceptions",
    "to_sentence_case_academic",
    "extract_title_words",
    "filter_relevant_whitelist_terms",
    "robust_tokenize_with_math",
    "normalize_token",
    "iterate_nonmath_segments",
    "is_canonically_equivalent",
    "debug_print",
    "TexNormalizeConfig",
    "DASH_CHARS",
    "_DASH_PATTERNS",
    "DEBUG_SENTENCE_CASE",
    "_load_sentence_case_config",
    "mask_math_regions",
    "_phrase_regex",
]