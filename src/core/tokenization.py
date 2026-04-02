#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/tokenization.py - Tokenization and Regex Utilities
Extracted from utils.py to improve modularity
"""

import itertools
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List, Tuple
import regex as re

from core.text_processing import math_detector


@dataclass(frozen=True, slots=True)
class Token:
    """Data class for representing text tokens."""
    kind: str  # 'PHRASE' | 'MATH' | 'WORD' | 'SPACE' | 'PUNCT'
    value: str
    start: int
    end: int  # exclusive


# Simple segment regex that handles words, spaces, and punctuation
_SEGMENT_RE = re.compile(r"""
    (?P<SPACE>\s+)
  | (?P<PUNCT>[^\w\s''])  # Everything that's not word, space, or apostrophes
  | (?P<WORD>\w+(?:[''][a-zA-Z]+)?)  # Word with optional apostrophe suffix
""",
    re.X | re.U,
)


@lru_cache(maxsize=512)
def _phrase_regex(phrase: str) -> re.Pattern:
    """Create regex that matches phrase with flexible whitespace/dashes"""
    # Normalize spaces in the phrase first
    phrase = re.sub(r'\s+', ' ', phrase.strip())
    
    # Escape special regex characters
    phrase = re.escape(phrase)
    
    # Replace escaped spaces with flexible whitespace/dash pattern
    phrase = phrase.replace(r'\ ', r'[\s\-–—]+')
    
    # Make it case-insensitive and word-bounded
    return re.compile(r'\b' + phrase + r'\b', re.IGNORECASE | re.UNICODE)


def mask_math_regions(text: str, mask: str = "¤") -> str:
    """Mask math regions in text with specified character."""
    chars = list(text)
    for s, e in math_detector.find_math_regions(text):
        chars[s:e] = itertools.repeat(mask, e - s)
    return "".join(chars)


def iterate_nonmath_segments(
    text: str,
    regions: List[Tuple[int, int]]
) -> Iterable[Tuple[int, int, str]]:
    """
    Yield (start, end, slice) triples for every part of *text* that is
    **not** covered by a math region, but be tolerant when the list of
    regions is stale (i.e. it was computed before another normaliser
    changed the string length).
    """
    n = len(text)

    # 1. Discard / clamp invalid regions
    clean: List[Tuple[int, int]] = []
    for s, e in regions:
        s = max(0, min(s, n))
        e = max(0, min(e, n))
        if s < e:                       # keep only non-empty spans
            clean.append((s, e))

    # 2. Sort and merge any overlaps
    clean.sort()
    merged: List[Tuple[int, int]] = []
    for s, e in clean:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    # 3. Yield the complementary (non-math) slices
    last = 0
    for s, e in merged:
        if last < s:
            yield last, s, text[last:s]
        last = e
    if last < n:
        yield last, n, text[last:]


# Export all functions
__all__ = [
    'Token',
    '_phrase_regex',
    'mask_math_regions',
    'iterate_nonmath_segments'
]