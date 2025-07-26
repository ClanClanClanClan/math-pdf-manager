#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/text_canonicalization.py - Text Normalization and Canonicalization
Extracted from utils.py to improve modularity
"""

import itertools
import unicodedata
from typing import Dict, Sequence, Optional
import regex as re

# Control characters regex
_CONTROL_CHARS = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]", flags=re.UNICODE)


def canonicalize(s: Optional[str]) -> str:
    """
    Canonicalize text for consistent comparison.
    
    NOTE: This function is now available in consolidated form at:
    core.text_processing.canonicalize() - consider migrating to use that version.
    """
    if not isinstance(s, str):
        return ""
    s = (
        s.replace("\ufeff", "")
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )
    s = _CONTROL_CHARS.sub("", s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"-{2,}", "-", s.lower().strip())  # collapse multiple dashes
    return s


def build_canonical_exceptions(
    cap: Optional[Sequence[str]], dash: Optional[Sequence[str]]
) -> Dict[str, str]:
    """Build canonical exceptions dictionary from cap and dash lists."""
    out: Dict[str, str] = {}
    for w in itertools.chain(cap or (), dash or ()):
        out[canonicalize(w)] = w
    return out


def normalize_token(tok: Optional[str]) -> str:
    """Normalize a single token for consistent processing."""
    if not tok:
        return ""
    tok = unicodedata.normalize("NFKD", tok)
    tok = "".join(c for c in tok if not unicodedata.combining(c))
    tok = tok.replace("\ufeff", "").replace("\u200b", "")
    return tok.lower().strip("- ").strip()


# Export all functions
__all__ = [
    'canonicalize',
    'build_canonical_exceptions',
    'normalize_token'
]