#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/math_tokenization.py - Math-aware Text Tokenization
Extracted from utils.py to improve modularity
"""

from typing import List, Iterable, Tuple, Set
import regex as re

from core.text_processing import math_detector
from .tokenization import Token

# Common dash characters
DASH_CHARS = r'\-–—‐−'

# Simple segment regex that handles words, spaces, and punctuation
_SEGMENT_RE = re.compile(r"""
    (?P<SPACE>\s+)
  | (?P<PUNCT>[^\w\s''])  # Everything that's not word, space, or apostrophes
  | (?P<WORD>\w+(?:[''][a-zA-Z]+)?)  # Word with optional apostrophe suffix
""",
    re.X | re.U,
)


def robust_tokenize_with_math(
    text: str, phrases: Iterable[str] = None
) -> List[Token]:
    """
    Tokenize text while protecting math regions and specified phrases.
    
    Only multi-word items (containing spaces or dashes) create PHRASE tokens.
    Single words that look like they might be math (e.g., "C^∞(M)") also create PHRASE tokens.
    Regular single words do not create PHRASE tokens.
    """
    from .tokenization import _phrase_regex
    
    phrases = set(phrases or ())
    
    # Separate different types of protected items
    multi_word_phrases = set()
    math_like_phrases = set()
    
    for ph in phrases:
        if ' ' in ph or any(d in ph for d in DASH_CHARS):
            # Multi-word phrase
            multi_word_phrases.add(ph)
        elif any(c in ph for c in ['^', '_', '∞', '∂', '∑', '∏', '∫', '(', ')', '[', ']']):
            # Single item that looks math-like - treat as phrase to protect from math detection
            math_like_phrases.add(ph)
        # Note: Regular single words are NOT added to any phrase set

    # ── 1. phrase hits first (for multi-word and math-like phrases only) ────────
    hits: List[Tuple[int, int, str]] = []
    
    # Process only phrases that should create PHRASE tokens
    for ph in multi_word_phrases | math_like_phrases:
        # Create appropriate regex based on phrase type
        if ' ' in ph and not any(d in ph for d in DASH_CHARS):
            # Space-only phrase - match with flexible spacing
            parts = ph.split(' ')
            pattern = r'\b' + r'\s+'.join(re.escape(p) for p in parts) + r'\b'
            regex = re.compile(pattern, re.I | re.U)  # Case insensitive
        elif any(d in ph for d in DASH_CHARS) and ' ' not in ph:
            # Dash-only phrase
            parts = re.split(rf'[{DASH_CHARS}]+', ph)
            pattern = r'\b' + rf'[{DASH_CHARS}]+'.join(re.escape(p) for p in parts) + r'\b'
            regex = re.compile(pattern, re.I | re.U)  # Case insensitive
        elif ' ' in ph or any(d in ph for d in DASH_CHARS):
            # Has both spaces and dashes
            regex = _phrase_regex(ph)
        else:
            # Single word/phrase - for math-like phrases, use flexible boundaries
            if any(c in ph for c in ['^', '_', '∞', '∂', '∑', '∏', '∫', '(', ')', '[', ']']):
                # Math-like phrase - use lookaround assertions for flexible boundaries
                escaped = re.escape(ph)
                pattern = rf'(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])'
                regex = re.compile(pattern, re.U)  # NOT case insensitive for math
            else:
                # Regular word - use word boundaries
                regex = re.compile(rf'\b{re.escape(ph)}\b', re.I | re.U)  # Case insensitive
        
        for m in regex.finditer(text):
            s, e = m.span()
            matched_text = text[s:e]
            # For space-containing phrases, verify the match has reasonable spacing
            if ' ' in ph:
                # Check if there are excessive spaces (3 or more consecutive spaces)
                if re.search(r' {3,}', matched_text):
                    continue
                # Also verify word sequence matches (case-insensitive)
                matched_words = [w.lower() for w in matched_text.split()]
                phrase_words = [w.lower() for w in ph.split()]
                if matched_words != phrase_words:
                    continue
            hits.append((s, e, matched_text))
        
        # Also check for hyphenated variants of space-separated phrases
        if ' ' in ph:
            parts = ph.split(' ')
            hyphen_pattern = r'\b' + r'[‐\-–—−]'.join(re.escape(p) for p in parts) + r'\b'
            hyphen_regex = re.compile(hyphen_pattern, re.I | re.U)
            
            for m in hyphen_regex.finditer(text):
                s, e = m.span()
                matched_text = text[s:e]
                if not any(s >= h[0] and e <= h[1] for h in hits):
                    hits.append((s, e, matched_text))
                    
    # ── 2. keep longest non-overlapping phrase per start ──────────────────
    hits.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    occupied: Set[int] = set()
    kept: List[Tuple[int, int, str]] = []
    for s, e, v in hits:
        if occupied.isdisjoint(range(s, e)):
            kept.append((s, e, v))
            occupied.update(range(s, e))

    phrase_by_start = {s: (e, v) for s, e, v in kept}

    # ── 3. maths (excluding phrases) ───────────────────────────────────────
    math_spans = math_detector.find_math_regions(text)
    
    # Also detect $$...$$ display math explicitly since math_detector doesn't handle it well
    display_math_pattern = re.compile(r'\$\$[^$]+\$\$')
    for m in display_math_pattern.finditer(text):
        math_spans.append(m.span())
    
    # Remove duplicates and sort
    math_spans = sorted(set(math_spans))
    
    math_by_start = {}
    
    for s, e in math_spans:
        # Skip if overlaps with a phrase
        if any(not (e <= ps or s >= pe) for ps, pe, _ in kept):
            continue
        
        math_by_start[s] = e

    # helper: does <word> occur again outside *all* phrases?
    def _appears_outside(word: str, from_pos: int) -> bool:
        pat = re.compile(rf"\b{re.escape(word)}\b", re.I | re.U)
        for m in pat.finditer(text, from_pos):
            s = m.start()
            if all(not (ps <= s < pe) for ps, pe, _ in kept):
                return True
        return False

    # ── 4. linear scan ────────────────────────────────────────────────────
    tokens: List[Token] = []
    i = 0
    while i < len(text):
        # ── phrase: highest priority, consumes its span
        if i in phrase_by_start:
            e, v = phrase_by_start[i]
            tokens.append(Token("PHRASE", v, i, e))

            # emit trailing word if it re-appears later outside any phrase
            words = re.findall(r"\b\w+\b", v, flags=re.U)
            if words:
                suffix = words[-1]
                if _appears_outside(suffix, e):
                    suffix_start = e - len(suffix)
                    # Only add if it doesn't overlap with the phrase token
                    if suffix_start >= i:
                        tokens.append(Token("WORD", suffix, suffix_start, e))

            i = e
            continue

        # ── maths: second priority, consumes its span
        if i in math_by_start:
            j = math_by_start[i]
            tokens.append(Token("MATH", text[i:j], i, j))
            i = j
            continue

        # ── ordinary segment
        m = _SEGMENT_RE.match(text, i)
        if not m:  # single-character fallback
            tokens.append(Token("PUNCT", text[i], i, i + 1))
            i += 1
            continue

        kind = m.lastgroup
        if kind:
            kind = kind.upper()
        else:
            kind = "PUNCT"
        s, e = m.span()
        tokens.append(Token(kind, text[s:e], s, e))
        i = e

    return tokens


# Export all functions
__all__ = [
    'robust_tokenize_with_math',
    'DASH_CHARS'
]