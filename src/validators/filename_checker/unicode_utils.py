"""
Unicode utilities for filename validation.

This module provides Unicode handling functionality, including security
sanitization and script detection.
"""

import unicodedata
import re
import itertools
from typing import List, Tuple, Set, Iterable, Sequence

from .debug import debug_print


# Dangerous Unicode characters that should be removed
DANGEROUS_UNICODE_CHARS = {
    "\u202e": "RIGHT-TO-LEFT OVERRIDE",
    "\u202d": "LEFT-TO-RIGHT OVERRIDE",
    "\u202a": "LEFT-TO-RIGHT EMBEDDING",
    "\u202b": "RIGHT-TO-LEFT EMBEDDING",
    "\u202c": "POP DIRECTIONAL FORMATTING",
    "\u200b": "ZERO WIDTH SPACE",
    "\u200c": "ZERO WIDTH NON-JOINER",
    "\u200d": "ZERO WIDTH JOINER",
    "\u200e": "LEFT-TO-RIGHT MARK",
    "\u200f": "RIGHT-TO-LEFT MARK",
    "\ufeff": "BYTE-ORDER MARK",
    "\u2060": "WORD JOINER",
    "\u2061": "FUNCTION APPLICATION",
    "\u2062": "INVISIBLE TIMES",
    "\u2063": "INVISIBLE SEPARATOR",
    "\u2064": "INVISIBLE PLUS",
    "\u202f": "NARROW NO-BREAK SPACE",
}


def nfc(text: str) -> str:
    """Normalize text to NFC form."""
    return unicodedata.normalize('NFC', text)


def has_mathematical_greek(text: str) -> bool:
    """
    Check if text contains mathematical Greek letters.
    
    Args:
        text: The text to check
    
    Returns:
        True if text contains mathematical Greek letters
    """
    # Import MATHEMATICAL_GREEK_LETTERS from math_utils
    try:
        from .math_utils import MATHEMATICAL_GREEK_LETTERS
        math_greek_chars = MATHEMATICAL_GREEK_LETTERS
    except ImportError:
        # Fallback to hardcoded set if import fails
        math_greek_chars = {
            'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω',
            'Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ', 'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω',
            # Mathematical superscript Greek letters
            "ᵅ", "ᵝ", "ᵞ", "ᵟ", "ᵋ", "ᶿ", "ᶥ", "ᶲ", "ᵡ", "ᵠ"
        }
    
    # Check for Greek letters
    if any(char in math_greek_chars for char in text):
        return True
    
    # Check for mathematical Greek modifier letters and symbols
    for char in text:
        try:
            name = unicodedata.name(char)
            if ("GREEK" in name and 
                ("MODIFIER" in name or "MATHEMATICAL" in name or "SMALL" in name)):
                return True
        except ValueError:
            continue
    
    return False


def sanitize_unicode_security(text: str) -> Tuple[str, List[str], Set[str]]:
    """
    Enhanced to properly handle BOM and other dangerous characters.
    
    Args:
        text: The text to sanitize
    
    Returns:
        Tuple of (sanitized_text, removed_characters, scripts_found)
    """
    removed = []
    # Normalise special spaces to regular space (U+0020) before stripping
    # dangerous chars.  U+00A0 (NBSP) and U+2000-U+200A (various width
    # spaces) are not dangerous, just non-standard.
    text = re.sub(r"[\u00a0\u2000-\u200a\u2009]", " ", text)
    for ch, name in DANGEROUS_UNICODE_CHARS.items():
        if ch in text:
            text = text.replace(ch, "")
            removed.append(name)

    scripts = set()
    for ch in text:
        try:
            nm = unicodedata.name(ch)
        except ValueError:
            continue
        for label in ("GREEK", "CYRILLIC", "LATIN"):
            if label in nm:
                scripts.add(label)

    # Enhanced mixed script handling for mathematical content
    if len(scripts) > 1 and "LATIN" in scripts and "GREEK" in scripts:
        if has_mathematical_greek(text):
            debug_print(
                f"Allowing mixed GREEK/LATIN scripts due to mathematical content: {text}"
            )
            scripts = {"LATIN"}  # Don't report this as mixed scripts
        
        # Check for mathematical superscript/subscript characters
        mathematical_unicode_ranges = [
            (0x2070, 0x209F),  # Superscripts and subscripts
            (0x1D400, 0x1D7FF),  # Mathematical Alphanumeric Symbols
            (0x2100, 0x214F),  # Letterlike symbols
        ]
        
        has_math_unicode = any(
            any(start <= ord(char) <= end for start, end in mathematical_unicode_ranges)
            for char in text
        )
        
        if has_math_unicode:
            debug_print(
                f"Allowing mixed scripts due to mathematical Unicode symbols: {text}"
            )
            scripts = {"LATIN"}  # Don't report this as mixed scripts

    return text, removed, scripts


def iterate_nonmath_segments(
    text: str, regions: List[Tuple[int, int]]
) -> Iterable[Tuple[int, int, str]]:
    """
    Iterate over non-mathematical segments of text.
    
    Args:
        text: The text to process
        regions: List of (start, end) tuples for mathematical regions
    
    Yields:
        Tuples of (start, end, segment_text) for non-mathematical segments
    """
    n = len(text)
    clean = [(max(0, s), min(n, e)) for s, e in regions if s < e]
    clean.sort()
    merged = []
    for s, e in clean:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    last = 0
    for s, e in merged:
        if last < s:
            segment = text[last:s]
            yield last, s, segment
        last = e
    if last < n:
        segment = text[last:]
        yield last, n, segment


def iterate_nonmath_segments_flat(text: str, regions: List[Tuple[int, int]]) -> str:
    """
    Get concatenated non-mathematical segments of text.
    
    Args:
        text: The text to process
        regions: List of (start, end) tuples for mathematical regions
    
    Returns:
        Concatenated non-mathematical segments
    """
    result = "".join(seg for _, _, seg in iterate_nonmath_segments(text, regions))
    return result


def find_all_exception_spans(txt: str, phrases: Set[str]) -> List[Tuple[int, int]]:
    """
    Find spans of all exception phrases in text.
    
    Args:
        txt: The text to search
        phrases: Set of exception phrases
    
    Returns:
        List of (start, end) tuples for exception spans
    """
    spans = []
    for ph in sorted(phrases, key=len, reverse=True):
        for m in re.finditer(re.escape(ph), txt):
            spans.append(m.span())
    spans.sort()
    merged = []
    for s, e in spans:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
    return merged


def is_in_spans(s: int, e: int, spans: List[Tuple[int, int]]) -> bool:
    """
    Check if a span overlaps with any of the given spans.
    
    Args:
        s: Start position
        e: End position
        spans: List of (start, end) tuples to check against
    
    Returns:
        True if the span overlaps with any of the given spans
    """
    result = any(a < e and b > s for a, b in spans)
    return result


def add_spaces_after_commas(s: str) -> str:
    """
    Add spaces after commas if missing.
    
    Args:
        s: The string to process
    
    Returns:
        String with spaces after commas
    """
    result = re.sub(r",(?=\S)", ", ", s)
    return result


def clean_whitelist_pairs(pairs: Sequence[str]) -> List[str]:
    """
    Clean and normalize whitelist pairs.
    
    Args:
        pairs: Sequence of strings to clean
    
    Returns:
        List of cleaned and normalized strings
    """
    result = [nfc(p.strip()) for p in pairs]
    return result


def phrase_variants(phrase: str) -> set[str]:
    """
    Generate variants of a phrase with different separators.
    
    Args:
        phrase: The phrase to generate variants for
    
    Returns:
        Set of phrase variants
    """
    tokens = re.split(r"[-– ]", phrase)
    if len(tokens) < 2 or len(tokens) > 4 or len(phrase) > 50:
        variants = {phrase, "-".join(tokens), "–".join(tokens), " ".join(tokens)}
        return variants
    variants = set()
    seps = [["-", "–", " ", "—", "−"]] * (len(tokens) - 1)
    for combo in itertools.product(*seps):
        variants.add("".join(a + b for a, b in zip(tokens, combo + ("",))))
    return variants


def is_canonically_equivalent(s1: str, s2: str) -> bool:
    """Check if two strings are canonically equivalent with proper Unicode handling - RESTORED from original"""
    if not s1 and not s2:
        return True
    if not s1 or not s2:
        return False

    # Import here to avoid circular imports
    try:
        from .author_processing import normalize_for_comparison
    except ImportError:
        def normalize_for_comparison(s):
            return s.lower().strip()

    n1 = normalize_for_comparison(nfc(s1) if s1 else "")
    n2 = normalize_for_comparison(nfc(s2) if s2 else "")

    result = n1 == n2
    return result


def is_unicode_normalized(text: str) -> bool:
    """Check if text is NFC normalized - RESTORED from original"""
    return unicodedata.normalize('NFC', text) == text


def normalize_unicode(text: str) -> str:
    """Normalize text to NFC form - RESTORED from original"""
    return nfc(text)


def detect_language(text: str) -> str:
    """Detect language of text - RESTORED from original"""
    # Import here to avoid circular imports
    try:
        from ..utils import get_language
        return get_language(text)
    except ImportError:
        # Fallback to simple heuristic
        if any(char in text for char in "áàâäçéèêëíìîïñóòôöúùûüÿ"):
            return "fr"
        elif any(char in text for char in "äöüß"):
            return "de"
        elif any(char in text for char in "ñáéíóúü"):
            return "es"
        elif any(char in text for char in "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþ"):
            return "it"
        else:
            return "en"