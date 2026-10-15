"""
Text processing and correction utilities for filename validation.

This module provides text correction functionality including ellipsis fixing,
ligature handling, quote processing, and number spelling.
"""

import re
from typing import List, Tuple, Set, Optional

from .debug import debug_print
from .unicode_utils import iterate_nonmath_segments, is_in_spans
from .math_utils import should_preserve_digit


# Number word mappings
NUMBERS = {
    "0": "zero",
    "1": "one", 
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine"
}

# Compiled regex patterns
DIGIT1_RE = re.compile(r"\b[0-9]\b")
ELLIPSIS_RE = re.compile(r"(?<!\.)\.\.\.(?!\.)")
YEAR_RE = re.compile(r'^(?:19|20)\d{2}$')
THOUSANDS_RE = re.compile(r"\b\d{1,3}(?:[, ]\d{3})+\b")

# Unicode mapping constants
SUPERSCRIPT_MAP = {
    "0": "\u2070", "1": "\u00b9", "2": "\u00b2", "3": "\u00b3", "4": "\u2074", "5": "\u2075", "6": "\u2076", "7": "\u2077", "8": "\u2078", "9": "\u2079",
    "a": "\u1d43", "b": "\u1d47", "c": "\u1d9c", "d": "\u1d48", "e": "\u1d49", "f": "\u1da0", "g": "\u1d4d", "h": "\u02b0", "i": "\u2071", "j": "\u02b2",
    "k": "\u1d4f", "l": "\u02e1", "m": "\u1d50", "n": "\u207f", "o": "\u1d52", "p": "\u1d56", "q": "\u1da0", "r": "\u02b3", "s": "\u02e2", "t": "\u1d57",
    "u": "\u1d58", "v": "\u1d5b", "w": "\u02b7", "x": "\u02e3", "y": "\u02b8", "z": "\u1dbb",
    "A": "\u1d2c", "B": "\u1d2e", "C": "\u1d9c", "D": "\u1d30", "E": "\u1d31", "F": "\u1da0", "G": "\u1d33", "H": "\u1d34", "I": "\u1d35", "J": "\u1d36",
    "K": "\u1d37", "L": "\u1d38", "M": "\u1d39", "N": "\u1d3a", "O": "\u1d3c", "P": "\u1d3e", "Q": "Q", "R": "\u1d3f", "S": "\u02e2", "T": "\u1d40",
    "U": "\u1d41", "V": "\u2c7d", "W": "\u1d42", "X": "\u02e3", "Y": "\u02b8", "Z": "\u1dbb",
    "+": "\u207a", "-": "\u207b", "=": "\u207c", "(": "\u207d", ")": "\u207e",
}

SUBSCRIPT_MAP = {
    "0": "\u2080", "1": "\u2081", "2": "\u2082", "3": "\u2083", "4": "\u2084", "5": "\u2085", "6": "\u2086", "7": "\u2087", "8": "\u2088", "9": "\u2089",
    "+": "\u208a", "-": "\u208b", "=": "\u208c", "(": "\u208d", ")": "\u208e",
    "a": "\u2090", "e": "\u2091", "h": "\u2095", "i": "\u1d62", "j": "\u2c7c", "k": "\u2096", "l": "\u2097", "m": "\u2098", "n": "\u2099", "o": "\u2092",
    "p": "\u209a", "r": "\u1d63", "s": "\u209b", "t": "\u209c", "u": "\u1d64", "v": "\u1d65", "x": "\u2093",
}

MATHBB_MAP = {
    "A": "\U0001d538", "B": "\U0001d539", "C": "\u2102", "D": "\U0001d53b", "E": "\U0001d53c", "F": "\U0001d53d", "G": "\U0001d53e", "H": "\u210d", "I": "\U0001d540", "J": "\U0001d541",
    "K": "\U0001d542", "L": "\U0001d543", "M": "\U0001d544", "N": "\u2115", "O": "\U0001d546", "P": "\u2119", "Q": "\u211a", "R": "\u211d", "S": "\U0001d54a", "T": "\U0001d54b",
    "U": "\U0001d54c", "V": "\U0001d54d", "W": "\U0001d54e", "X": "\U0001d54f", "Y": "\U0001d550", "Z": "\u2124",
}

# Try to import from existing modules
try:
    from core.text_processing.my_spellchecker import SpellChecker
    from validators.filename_checker import LIGATURE_MAP, LIGATURES_WHITELIST
    _SC = SpellChecker()
    debug_print("Successfully imported SpellChecker and ligature constants")
except ImportError:
    debug_print("Failed to import SpellChecker and ligature constants, using fallbacks")
    LIGATURE_MAP = {"ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬀ": "ff"}
    LIGATURES_WHITELIST = set()
    
    class MockSpellChecker:
        def is_misspelled(self, word):
            return False
    
    _SC = MockSpellChecker()


def fix_ellipsis(text: str, regions: List[Tuple[int, int]], _exc=None, spans: Optional[List[Tuple[int, int]]] = None) -> str:
    """
    Fix ellipsis patterns in text.
    
    Args:
        text: The text to process
        regions: Mathematical regions to avoid
        _exc: Unused parameter for compatibility
        spans: Exception spans to avoid
    
    Returns:
        Text with fixed ellipsis
    """
    spans = spans or []

    def make_repl(offset):
        def repl(m):
            s, e = m.span()
            abs_s, abs_e = s + offset, e + offset
            if is_in_spans(abs_s, abs_e, spans):
                return m.group()
            return "…"
        return repl

    out, last = [], 0
    for s, e, seg in iterate_nonmath_segments(text, regions):
        transformed = re.sub(r"(?<!\.)\.\.\.(?!\.)", make_repl(s), seg)
        out.append(text[last:s] + transformed)
        last = e
    out.append(text[last:])
    result = "".join(out)
    return result


def _restore_missing_e_ff(word: str) -> str:
    """
    Restore missing 'e' before 'ff' in words.
    
    Args:
        word: The word to check
    
    Returns:
        Word with restored 'e' if appropriate
    """
    if len(word) >= 3 and word.lower().startswith("ff"):
        cand = "e" + word
        if _SC.is_misspelled(word) and not _SC.is_misspelled(cand):
            result = (
                cand.upper()
                if word.isupper()
                else cand.capitalize() if word[0].isupper() else cand
            )
            return result
    return word


def fix_ligatures(text: str, regions: List[Tuple[int, int]], _exc=None, spans: Optional[List[Tuple[int, int]]] = None) -> str:
    """
    Fix ligature patterns in text.
    
    Args:
        text: The text to process
        regions: Mathematical regions to avoid
        _exc: Unused parameter for compatibility
        spans: Exception spans to avoid
    
    Returns:
        Text with fixed ligatures
    """
    spans = spans or []
    if not any(lig in text for lig in LIGATURE_MAP) and not re.search(r"\bff[A-Za-z]+\b", text):
        return text

    result = text
    for lig, repl in LIGATURE_MAP.items():
        if lig in result:
            def make_replace_func(offset):
                def replace_func(match):
                    s, e = match.span()
                    abs_s, abs_e = s + offset, e + offset
                    if is_in_spans(abs_s, abs_e, spans):
                        return match.group()
                    return repl
                return replace_func

            # Process each segment separately
            out, last = [], 0
            for s, e, seg in iterate_nonmath_segments(result, regions):
                transformed = re.sub(re.escape(lig), make_replace_func(s), seg)
                out.append(result[last:s] + transformed)
                last = e
            out.append(result[last:])
            result = "".join(out)

    rebuilt = []
    for tok in re.split(r"(\W+)", result):
        if tok.isalpha():
            restored = _restore_missing_e_ff(tok)
            rebuilt.append(restored)
        else:
            rebuilt.append(tok)

    final_result = "".join(rebuilt)
    return final_result


def fix_ligature_words(text: str, regions: List[Tuple[int, int]], exceptions: Set[str], spans: List[Tuple[int, int]]) -> str:
    """
    Ultra-conservative ligature conversion.
    
    Args:
        text: The text to process
        regions: Mathematical regions to avoid
        exceptions: Exception words to avoid
        spans: Exception spans to avoid
    
    Returns:
        Text with ligature words fixed
    """
    debug_print(f"fix_ligature_words called with: '{text}'")

    def make_rep(offset):
        def rep(m):
            s, e = m.span()
            abs_s, abs_e = s + offset, e + offset
            if is_in_spans(abs_s, abs_e, spans):
                debug_print(f"Word '{m.group()}' is in exception spans, not converting")
                return m.group()

            word = m.group()

            debug_print(f"Checking word for ligature conversion: '{word}'")

            # Only allow direct matches (no transformations)
            if word in LIGATURES_WHITELIST:
                debug_print(f"Word '{word}' already has correct ligature form, keeping as-is")
                return word

            debug_print(f"Not converting word (not in direct ligature list): '{word}'")
            return word

        return rep

    # Process only non-math segments
    out, last = [], 0
    for s, e, seg in iterate_nonmath_segments(text, regions):
        transformed = re.sub(r"\b[A-Za-z]+\b", make_rep(s), seg)
        out.append(text[last:s] + transformed)
        last = e
    out.append(text[last:])

    result = "".join(out)
    debug_print(f"fix_ligature_words result: '{result}'")
    return result


def spell_out_small_numbers(text: str, regions: List[Tuple[int, int]], _exc: Set[str], spans: List[Tuple[int, int]]) -> str:
    """
    Enhanced version with comprehensive mathematical context detection.
    
    Args:
        text: The text to process
        regions: Mathematical regions to avoid
        _exc: Unused parameter for compatibility
        spans: Exception spans to avoid
    
    Returns:
        Text with small numbers spelled out
    """
    spans = spans or []

    # If no actual digits to convert, return immediately for stability
    if not DIGIT1_RE.search(text):
        debug_print(f"spell_out_small_numbers: No digits found, returning unchanged: '{text}'")
        return text

    replacements = []

    debug_print(f"spell_out_small_numbers: Processing text: '{text}'")
    debug_print(f"spell_out_small_numbers: Math regions: {regions}")

    # Apply to non-math segments only
    for s, e, seg in iterate_nonmath_segments(text, regions):
        debug_print(f"spell_out_small_numbers: Processing segment [{s}:{e}]: '{seg}'")

        # Find all digit matches in this segment
        for match in DIGIT1_RE.finditer(seg):
            seg_s, seg_e = match.span()
            abs_s, abs_e = seg_s + s, seg_e + s  # Convert to absolute positions
            digit = match.group()

            debug_print(f"spell_out_small_numbers: Found digit '{digit}' at absolute position {abs_s}")

            if is_in_spans(abs_s, abs_e, spans):
                debug_print(f"spell_out_small_numbers: Digit at {abs_s} is in exception spans, keeping as-is")
                continue

            if should_preserve_digit(text, abs_s):
                debug_print(f"spell_out_small_numbers: Digit '{digit}' at position {abs_s} should be preserved, not converting")
                continue

            # Only skip if digit is immediately touching another alphanumeric (no space)
            if (abs_s > 0 and text[abs_s - 1].isalnum()) or (abs_e < len(text) and text[abs_e].isalnum()):
                debug_print(f"spell_out_small_numbers: Digit '{digit}' at position {abs_s} is part of a larger alphanumeric sequence, not converting")
                continue

            # Check if digit is clearly isolated
            before = text[abs_s - 1] if abs_s > 0 else " "
            after = text[abs_e] if abs_e < len(text) else " "

            # Must be surrounded by spaces or sentence boundaries for conversion
            is_isolated = (before.isspace() or before in ".,;:!?()[]{}") and (after.isspace() or after in ".,;:!?()[]{}")

            if not is_isolated:
                debug_print(f"spell_out_small_numbers: Digit '{digit}' at position {abs_s} not isolated (before='{before}', after='{after}'), skipping")
                continue

            # Store replacement for later application
            word = NUMBERS[digit]
            replacements.append((abs_s, abs_e, word))
            debug_print(f"spell_out_small_numbers: Planning to convert digit '{digit}' to '{word}' at position {abs_s}")

    # If no replacements needed, return original text for perfect stability
    if not replacements:
        debug_print(f"spell_out_small_numbers: No replacements needed, returning unchanged: '{text}'")
        return text

    # Apply replacements in reverse order to maintain positions
    result = text
    for abs_s, abs_e, word in reversed(replacements):
        result = result[:abs_s] + word + result[abs_e:]
        debug_print(f"spell_out_small_numbers: Applied replacement at {abs_s}: '{result}'")

    debug_print(f"spell_out_small_numbers: Final result: '{result}'")
    return result


def get_quote_positions(text: str) -> List[Tuple[int, str]]:
    """
    Get positions of opening quotes in text with German typography support.
    
    Args:
        text: The text to analyze
    
    Returns:
        List of (position, quote_type) tuples
    """
    opening_quotes = {
        "\u201c": "double",  # Left double quotation mark
        "\u2018": "single",  # Left single quotation mark
        "\u00ab": "guillemet",  # Left-pointing double angle quotation mark
        "\u201a": "low-single",  # Single low-9 quotation mark
        "\u201e": "low-double",  # Double low-9 quotation mark
        '"': "double",  # Straight double quote
        "'": "single",  # Straight single quote
    }

    positions = []

    # Find German-style quote pairs („...") to exclude closing quotes
    german_closing_positions = set()
    i = 0
    while i < len(text):
        if text[i] == "\u201e":  # LOW_DOUBLE_QUOTE (opening in German)
            # Look for matching LEFT_DOUBLE_QUOTE (closing in German)
            for j in range(i + 1, len(text)):
                if text[j] == "\u201c":  # LEFT_DOUBLE_QUOTE (closing in German)
                    german_closing_positions.add(j)
                    break
                elif text[j] == "\u201e":  # Another opening quote, stop looking
                    break
        i += 1

    # Collect opening quote positions, excluding German closing quotes
    for i, char in enumerate(text):
        if char in opening_quotes:
            # Skip if this is a German closing quote
            if char == "\u201c" and i in german_closing_positions:
                continue
            positions.append((i, opening_quotes[char]))

    return positions


def should_capitalize_after_quote(text: str, quote_pos: int) -> bool:
    """
    Check if the word after a quote should be capitalized (for quoted titles).
    
    Args:
        text: The text to analyze
        quote_pos: Position of the quote
    
    Returns:
        True if the word after the quote should be capitalized
    """
    # Check what comes before the quote
    before_start = max(0, quote_pos - 20)
    before_text = text[before_start:quote_pos].lower().strip()

    # Patterns that indicate a quoted title
    title_indicators = [
        "supplement to", "based on", "response to", "reply to", "comment on",
        "translation of", "adapted from", "inspired by", "sequel to", "prequel to",
        "companion to", "introduction to", "guide to", "review of", "critique of",
        "analysis of", "study of",
    ]

    for indicator in title_indicators:
        if before_text.endswith(indicator):
            return True

    # Check if the quote appears to be starting a title
    if quote_pos == 0:
        return True

    # Check for colon or semicolon immediately before the quote
    if quote_pos > 0:
        char_before = text[quote_pos - 1]
        if char_before in ":;":
            return True
        # Also check with space before punctuation
        if quote_pos > 1 and text[quote_pos - 2 : quote_pos] in [": ", "; "]:
            return True

    return False


def fix_and_flag_quotes(
    text: str,
    lang: str,
    regions: List[Tuple[int, int]],
    spans: List[Tuple[int, int]],
    debug: bool = False,
) -> Tuple[str, List[str]]:
    """Flag straight quote PAIRS as errors and convert them to proper quotes."""
    debug_print(f"Quote processing for language '{lang}' in text: '{text}'")

    flags = []

    # Find straight double quote pairs
    double_quote_positions = [
        i
        for i, char in enumerate(text)
        if char == '"' and not any(start <= i < end for start, end in regions + spans)
    ]
    if len(double_quote_positions) > 0:
        flags.append("straight double quote should use proper quotation marks")

    # Straight single marks that are not apostrophes: a quotation mark, or a
    # prime. Both are left as they are (processing.apostrophes).
    from processing.apostrophes import is_title_apostrophe
    if any(char == "'" and not any(start <= i < end for start, end in regions + spans)
           and not is_title_apostrophe(text, i)
           for i, char in enumerate(text)):
        flags.append("straight single quote left as it is: not an apostrophe "
                     "(a quotation mark or a prime)")

    # Convert straight quotes to proper quotes
    text = convert_straight_quotes_to_proper(text, lang, regions, spans)

    debug_print(f"Quote processing result: '{text}', flags: {flags}")
    return text, flags


def convert_straight_quotes_to_proper(text: str, lang: str, regions: List[Tuple[int, int]], spans: List[Tuple[int, int]]) -> str:
    """A new title's straight marks, in the house conventions.

    Two rules, each kept in one place and only called from here:

    * APOSTROPHES (processing.apostrophes): a straight mark that is
      certainly an apostrophe becomes U+2019, in every language -- the
      apostrophe, unlike the quotation mark, does not depend on one. A
      prime, a quotation mark, or anything uncertain is left as it is.
      Mathematics is protected; a whitelisted phrase is not, because it
      protects casing and dashes, not this mark.
    * QUOTATION MARKS (processing.quote_marks, the owner's ruling of
      2026-10-14): one pair of straight double marks becomes English
      ‘outer’ or French « outer »; any other language is left as it is.

    Apostrophes first, on the text the regions were computed for: French
    guillemets add spaces, which would shift every offset after them.

    Args:
        text: The title, without its extension
        lang: The language its quotation marks follow, or None
        regions: Mathematical regions to avoid
        spans: Exception spans to avoid (quotation marks only)

    Returns:
        The title with its marks converted
    """
    debug_print(f"Converting straight quotes for language '{lang}' in text: '{text}'")

    from processing.apostrophes import title_apostrophes
    text = title_apostrophes(text, regions)

    if '"' in text:
        # A quote inside mathematics or a protected phrase is not ours to
        # touch. Which languages convert is decided in quote_marks alone.
        if any(start <= i < end for i, ch in enumerate(text) if ch == '"'
               for start, end in regions + spans):
            return text
        from processing.quote_marks import requote
        text = requote(text, lang).title

    debug_print(f"Quote conversion result: '{text}'")
    return text


def check_parentheses_brackets_balance(text: str, math_regions=None):
    """FIXED: Improved bracket balance checking - RESTORED from original"""
    OPEN, CLOSE = "([{", ")]}"
    pair = dict(zip(OPEN, CLOSE))
    mask = [False] * len(text)
    for a, b in math_regions or []:
        for i in range(max(0, a), min(len(text), b)):
            mask[i] = True

    issues, stack = [], []
    for pos, ch in enumerate(text):
        if mask[pos]:
            continue
        if ch in OPEN:
            if (
                pos + 1 < len(text)
                and text[pos + 1].isspace()
                and text[pos + 1] != "\n"
            ):
                issue = f"Space after '{ch}' at pos {pos}"
                issues.append(issue)
            stack.append((ch, pos))
        elif ch in CLOSE:
            if pos - 1 >= 0 and text[pos - 1].isspace() and text[pos - 1] != "\n":
                issue = f"Space before '{ch}' at pos {pos}"
                issues.append(issue)
            if not stack:
                issue = f"Unmatched '{ch}' at pos {pos}"
                issues.append(issue)
                continue
            op, op_pos = stack.pop()
            if pair[op] != ch:
                issue = f"Mismatched {op}@{op_pos} / {ch}@{pos}"
                issues.append(issue)

    for ch, pos in stack:
        issue = f"Unmatched '{ch}' at pos {pos}"
        issues.append(issue)

    return issues


def fix_thousand_separators(text: str, regions, _exc, spans):
    """Fix thousand separators in numbers - RESTORED from original"""
    if not re.search(r'\b\d{4,}\b', text) and not THOUSANDS_RE.search(text):
        return text

    def norm(num: str) -> str:
        if YEAR_RE.match(num):
            return num
        if "," in num or " " in num or "\u2009" in num:
            plain = re.sub(r'[,\s\u2009]', '', num)
            if not plain.isdigit() or len(plain) < 4:
                return num
            try:
                val = int(plain)
                result = format(val, ",").replace(",", "\u2009")
                return result
            except ValueError:
                return num
        if len(num) >= 6 and num.isdigit():
            try:
                val = int(num)
                result = format(val, ",").replace(",", "\u2009")
                return result
            except ValueError:
                return num
        return num

    out, last = [], 0
    for s, e, seg in iterate_nonmath_segments(text, regions):
        seg = THOUSANDS_RE.sub(lambda m: norm(m.group()), seg)
        seg = re.sub(r'\b\d{6,}\b', lambda m: norm(m.group()), seg)
        out.append(text[last:s] + seg)
        last = e
    out.append(text[last:])
    result = "".join(out)
    return result


def fix_math_unicode(text: str, regions, exceptions, spans):
    """Convert LaTeX-style math to Unicode - RESTORED from original"""
    if len(text) > 500 or "^" not in text:
        return text
    
    def sup(base: str, exp: str) -> str:
        result = base + "".join(SUPERSCRIPT_MAP.get(c, c) for c in exp)
        return result
    
    def sub(base: str, subscript: str) -> str:
        result = base + "".join(SUBSCRIPT_MAP.get(c, c) for c in subscript)
        return result
    
    def transform_segment(seg: str, abs_off: int) -> str:
        seg = re.sub(r"\b([A-Za-z])\^([0-9A-Za-z+\-]+)\b", lambda m: sup(m.group(1), m.group(2)), seg)
        seg = re.sub(r"\b([A-Za-z])\^\{([^}]+)\}", lambda m: sup(m.group(1), m.group(2)), seg)
        seg = re.sub(r"\b([A-Za-z])_([0-9A-Za-z+\-]+)\b", lambda m: sub(m.group(1), m.group(2)), seg)
        seg = re.sub(r"\b([A-Za-z])_\{([^}]+)\}", lambda m: sub(m.group(1), m.group(2)), seg)
        
        repls = []
        for m in re.finditer(r"\\mathbb\{([A-Z])\}", seg):
            if not is_in_spans(abs_off + m.start(), abs_off + m.end(), spans):
                replacement = MATHBB_MAP.get(m.group(1), m.group(0))
                repls.append((m.start(), m.end(), replacement))
        
        for s, e, r in sorted(repls, key=lambda x: x[0], reverse=True):
            seg = seg[:s] + r + seg[e:]
        
        return seg
    
    out, last = [], 0
    for s, e, seg in iterate_nonmath_segments(text, regions):
        transformed = transform_segment(seg, s)
        out.append(text[last:s] + transformed)
        last = e
    out.append(text[last:])
    
    result = "".join(out)
    return result


def get_ligature_suggestions(text: str):
    """Generate ligature suggestions - RESTORED from original"""
    suggestions = []
    
    # Common ligature patterns
    patterns = [
        (r'\bff\b', 'ff'),
        (r'\bfi\b', 'fi'),
        (r'\bfl\b', 'fl'),
        (r'\bffi\b', 'ffi'),
        (r'\bffl\b', 'ffl')
    ]
    
    for pattern, replacement in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            suggestions.append(f"Consider using ligature for '{match}'")
    
    return suggestions