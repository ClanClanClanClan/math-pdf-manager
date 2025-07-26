"""
Tokenization utilities for filename validation.

This module provides text tokenization functionality for the filename
validation system, including support for mathematical expressions and
compound terms.
"""

import unicodedata
from typing import List, Optional, Set, Tuple

from .data_structures import Token
from .debug import debug_print


def robust_tokenize_with_math(text: str, phrases: List[str], regions: Optional[List[Tuple[int, int]]] = None) -> List[Token]:
    """
    Tokenize text with proper handling of compound terms and mathematical expressions.
    
    Args:
        text: The text to tokenize
        phrases: List of known phrases to match as single tokens
        regions: Optional list of (start, end) tuples for mathematical regions
    
    Returns:
        List of Token objects
    """
    tokens = []
    phrases_set = set(phrases) if phrases else set()

    debug_print(f"Tokenizing: '{text}' with {len(phrases_set)} phrases")
    if phrases_set:
        compound_phrases = [p for p in phrases_set if "-" in p]
        debug_print(f"Sample compound phrases: {compound_phrases[:10]}")

    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue

        start = i

        # Try to match longest phrase first (greedy approach)
        matched_phrase = None
        max_phrase_len = 0

        for phrase in phrases_set:
            if (
                i + len(phrase) <= len(text)
                and text[i : i + len(phrase)].lower() == phrase.lower()
            ):
                # Check word boundaries
                before_ok = i == 0 or not text[i - 1].isalnum()
                after_ok = (
                    i + len(phrase) >= len(text) or not text[i + len(phrase)].isalnum()
                )

                if before_ok and after_ok and len(phrase) > max_phrase_len:
                    matched_phrase = phrase
                    max_phrase_len = len(phrase)

        if matched_phrase:
            # Found a phrase match
            actual_text = text[i : i + len(matched_phrase)]
            tokens.append(Token("PHRASE", actual_text, i, i + len(matched_phrase)))
            debug_print(f"  Matched phrase: '{actual_text}' -> PHRASE")
            i += len(matched_phrase)
        else:
            # Collect regular token (word or punctuation)
            if text[i].isalnum() or unicodedata.category(text[i])[0] in "LMN":
                # Word token - collect letters, marks, numbers, and internal hyphens
                while i < len(text) and (
                    text[i].isalnum()
                    or unicodedata.category(text[i])[0] in "LMN"
                    or (
                        text[i] in "-–'"
                        and i + 1 < len(text)
                        and (
                            text[i + 1].isalnum()
                            or unicodedata.category(text[i + 1])[0] in "LMN"
                        )
                    )
                ):
                    i += 1
            else:
                # Single punctuation/symbol
                i += 1

            value = text[start:i]
            tokens.append(Token("TOKEN", value, start, i))
            debug_print(f"  Regular token: '{value}' -> TOKEN")

    return tokens


def get_first_word_properly(title: str, math_regions: List[Tuple[int, int]], 
                           all_allowed_words: Set[str]) -> Optional[Tuple[str, int, int]]:
    """
    Get the first word from a title, handling mathematical regions and known phrases.
    
    Args:
        title: The title text
        math_regions: List of (start, end) tuples for mathematical regions
        all_allowed_words: Set of allowed words/phrases
    
    Returns:
        Tuple of (word, start_position, end_position) or None if no valid first word
    """
    debug_print(f"Getting first word from: '{title}'")

    # Skip leading whitespace and punctuation
    i = 0
    while i < len(title) and (title[i].isspace() or title[i] in ".,;:!?()[]{}\"'-"):
        i += 1

    if i >= len(title):
        debug_print("No first word found (empty or only punctuation)")
        return None

    # Check if we're in a math region
    if any(start <= i < end for start, end in math_regions):
        debug_print("First word is in math region, skipping")
        return None

    start_pos = i

    # First try to match against known phrases
    for phrase in sorted(all_allowed_words, key=len, reverse=True):
        if (
            i + len(phrase) <= len(title)
            and title[i : i + len(phrase)].lower() == phrase.lower()
        ):
            # Check word boundaries
            before_ok = i == 0 or not title[i - 1].isalnum()
            after_ok = (
                i + len(phrase) >= len(title) or not title[i + len(phrase)].isalnum()
            )

            if before_ok and after_ok:
                debug_print(f"First word is phrase: '{phrase}'")
                return (title[i : i + len(phrase)], i, i + len(phrase))

    # No phrase match, collect regular word
    while i < len(title) and (
        title[i].isalnum()
        or unicodedata.category(title[i])[0] in "LMN"
        or (
            title[i] in "-–'"
            and i + 1 < len(title)
            and (
                title[i + 1].isalnum() or unicodedata.category(title[i + 1])[0] in "LMN"
            )
        )
    ):
        i += 1

    if i > start_pos:
        word = title[start_pos:i]
        debug_print(f"First word is regular word: '{word}'")
        return (word, start_pos, i)

    debug_print("No valid first word found")
    return None


def normalize_token(token: str) -> str:
    """Normalize a token to lowercase for comparison."""
    return token.lower()


def find_bad_dash_patterns(text: str) -> List[str]:
    """
    Find problematic dash patterns in text.
    
    Args:
        text: The text to analyze
    
    Returns:
        List of error messages for bad dash patterns
    """
    import re
    
    errors = []

    # Allow legitimate compound constructions like "pair- and triple-wise"
    compound_pattern = r"\b\w+- and \w+-\w+\b"
    if re.search(compound_pattern, text):
        debug_print(f"Found legitimate compound construction in: {text}")
        return errors  # Don't flag legitimate compound constructions

    # Check for problematic dash patterns
    bad_dash_space_pattern = r"\b\w+- (?!and\s+\w+-\w+\b)"
    matches = list(re.finditer(bad_dash_space_pattern, text))
    for match in matches:
        errors.append("word- space (should not occur)")
        debug_print(
            f"Found bad dash pattern: '{match.group()}' at position {match.start()}-{match.end()}"
        )

    return errors


def enforce_ndash_between_authors(text: str, pairs: List[Tuple[str, str]]) -> str:
    """
    Enforce n-dash between authors (placeholder implementation).
    
    Args:
        text: The text to process
        pairs: List of author pairs
    
    Returns:
        Processed text
    """
    return text


def check_dash_pairs(text: str, whitelist: list) -> list:
    """Dash pair checking compatibility - RESTORED from original"""
    # Import here to avoid circular imports
    from ..validators.title_normalizer import check_title_dashes
    return check_title_dashes(text, set(whitelist), set())


def find_dash_pairs(text: str) -> list:
    """Find dash pairs compatibility - RESTORED from original"""
    return find_dash_pairs_with_positions(text)


def find_dash_pairs_with_positions(title: str) -> list:
    """FIXED: Find dash pairs with their positions in the text using Unicode-aware pattern - RESTORED from original"""
    import re
    from .debug import debug_print
    
    try:
        # Simple timeout context
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError("Operation timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(1)  # 1 second timeout
        
        try:
            if (
                len(title) > 200
                or title.count("—") > 10
                or title.count("-") > 15
                or title.count("»") > 5
            ):
                return []

            # FIXED: Use Unicode-aware pattern that handles accented characters
            # \w already includes Unicode letters in Python 3, but the initial [A-Za-z] was too restrictive
            pattern = r"\b(\w[\w\-]*)\s*([–-])\s*(\w[\w\-]*)\b"
            pairs = []

            for match in re.finditer(pattern, title, re.UNICODE):
                left = match.group(1)
                dash = match.group(2)
                right = match.group(3)
                start = match.start()
                end = match.end()

                # Only include if both parts are reasonable length and start with letters
                if (
                    len(left) > 0
                    and len(right) > 0
                    and len(left) <= 20
                    and len(right) <= 20
                    and left[0].isalpha()
                    and right[0].isalpha()
                ):
                    pairs.append((left, right, dash, start, end))
                    debug_print(
                        f"Found dash pair: '{left}{dash}{right}' at {start}-{end}"
                    )

            return pairs
        finally:
            signal.alarm(0)  # Cancel the alarm
            
    except (TimeoutError, Exception) as e:
        debug_print(f"Error in find_dash_pairs_with_positions: {e}")
        return []


def robust_phrase_tokenize(
    text: str, phrases: set, math_regions: list = None
) -> list:
    """
    Compatibility function for old test format - RESTORED from original
    
    Args:
        text: The text to tokenize
        phrases: Set of phrases to recognize
        math_regions: Mathematical regions to consider
    
    Returns:
        List of tuples (is_phrase, value, start, end)
    """
    import inspect
    
    sig = inspect.signature(robust_tokenize_with_math)
    if len(sig.parameters) == 3:
        toks = robust_tokenize_with_math(text, phrases, math_regions or [])
    else:
        toks = robust_tokenize_with_math(text, phrases)
    result = [(t.kind == "PHRASE", t.value, t.start, t.end) for t in toks]
    return result


def dash_pair_cap_checker(text: str, whitelist: set) -> list:
    """Check capitalization in dash pairs - RESTORED from original"""
    errors = []
    dash_pairs = find_dash_pairs_with_positions(text)
    
    for left, right, dash, start, end in dash_pairs:
        # Check if both parts are properly capitalized
        if left.lower() in whitelist and right.lower() in whitelist:
            continue
            
        # Check if capitalization is consistent
        if left[0].islower() and right[0].isupper():
            errors.append(f"Inconsistent capitalization in dash pair: {left}{dash}{right}")
        elif left[0].isupper() and right[0].islower():
            errors.append(f"Inconsistent capitalization in dash pair: {left}{dash}{right}")
    
    return errors


def dash_pair_hyphen_checker(text: str, whitelist: set) -> list:
    """Check for proper en-dash usage in dash pairs - RESTORED from original"""
    errors = []
    dash_pairs = find_dash_pairs_with_positions(text)
    
    for left, right, dash, start, end in dash_pairs:
        # Check if hyphen should be en-dash
        if dash == "-" and f"{left}-{right}" not in whitelist:
            errors.append(f"Dash pair '{left}-{right}' should use en-dash (–)")
    
    return errors