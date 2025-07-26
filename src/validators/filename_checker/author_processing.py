"""
Author processing utilities for filename validation.

This module provides functionality to process and normalize author names
in academic filenames.
"""

import re
import unicodedata
from typing import Tuple, Set, Optional, List

from .debug import debug_print
from .unicode_utils import nfc


# Constants
MAX_INPUT_LENGTH = 5000


# Common author suffixes
SUFFIXES = [
    "Jr.", "Sr.", "Jr", "Sr", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
]

# Surname particles that should not be treated as suffixes
_SURNAME_PARTICLES = {
    "de", "la", "van", "von", "di", "del", "le", "da", "dos", "der",
    "du", "des", "den", "het", "ter", "ten", "te", "zur", "zum", "am",
    "im", "vom", "auf", "aus", "das", "los", "las", "el", "al", "dal",
    "della", "delle", "dello", "degli", "dei", "do"
}

# Comprehensive academic suffixes including Roman numerals
_ACADEMIC_SUFFIXES = {
    "jr", "sr", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    "md", "phd", "dds", "ma", "ms", "ba", "bs", "mph", "jd", "dvm", "od",
    "pharmd", "dpt", "edd", "psyd", "dnp", "dsc", "drph", "pharm"
}

# Roman numerals
_ROMAN_NUMERALS_SET = {
    'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
    'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx'
}


def debug_author_string(s: str) -> str:
    """
    Debug function to show all characters in an author string.
    
    Args:
        s: The author string to debug
    
    Returns:
        String with non-printable characters shown explicitly
    """
    debug_parts = []
    for i, char in enumerate(s):
        code = ord(char)
        if code < 32 or code > 126:
            debug_parts.append(f"[U+{code:04X}:{char}]")
        else:
            debug_parts.append(char)
    return "".join(debug_parts)


def has_invisible_differences(s1: str, s2: str) -> bool:
    """
    Check if two strings have invisible character differences.
    
    Args:
        s1: First string
        s2: Second string
    
    Returns:
        True if the strings differ only by invisible characters
    """
    if s1 == s2:
        return False

    invisible_chars = [
        "\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\u202a", "\u202b",
        "\u202c", "\u202d", "\u202e", "\u2060", "\u2061", "\u2062", "\u2063",
        "\u2064", "\ufeff", "\u202f",
    ]

    has_invisible_in_s1 = any(char in s1 for char in invisible_chars)

    clean1 = s1
    clean2 = s2
    for char in invisible_chars:
        clean1 = clean1.replace(char, "")
        clean2 = clean2.replace(char, "")

    return clean1 == clean2 and has_invisible_in_s1


def fix_author_block(raw_input: str) -> str:
    """
    Main author processing function that handles all formats correctly.
    Enhanced implementation for ultra-comprehensive author processing.
    
    Args:
        raw_input: Raw author string
    
    Returns:
        Processed author string
    """
    if not raw_input or not isinstance(raw_input, str):
        return ""

    # Basic author processing - normalize and clean up
    text = nfc(raw_input.strip()) if raw_input else ""
    text = re.sub(r"\s+", " ", text).strip()

    # Handle edge case: lone comma or only whitespace/punctuation
    if not text or text.strip() in ['', ',']:
        return ""

    # Clean up multiple commas and spaces
    text = re.sub(r",+", ",", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(',').strip()

    # Handle comma-separated format first (e.g., "Smith, A. B.")
    if ',' in text:
        parts = [p.strip() for p in text.split(',') if p.strip()]
        if len(parts) == 2:
            surname = parts[0]
            initials = parts[1]
            # Check if the initials part contains multiple authors (like "A. M. H. Nodozi I. Halder A.")
            if _contains_multiple_authors(initials):
                # Parse as multi-author format
                authors = _parse_multi_author_from_initials(surname, initials)
                return ", ".join(authors)
            else:
                # Single author format - fix initial spacing in the initials part
                initials = fix_initial_spacing(initials)
                return f"{surname}, {initials}"
        # For multi-part comma format, just clean up spacing
        cleaned_parts = []
        for part in parts:
            cleaned_part = fix_initial_spacing(part)
            cleaned_parts.append(cleaned_part)
        return ", ".join(cleaned_parts)
    
    # Handle space-separated format (e.g., "Smith A.B." -> "Smith, A. B.")
    tokens = safe_tokenize(text)
    if len(tokens) >= 2:
        # Check if this is a multi-author space-separated format
        if _is_multi_author_space_format(tokens):
            return _parse_multi_author_space_format(tokens)
        
        # Find where names end and initials begin
        name_tokens = []
        initial_tokens = []
        
        for i, token in enumerate(tokens):
            # Check if this token looks like an initial or suffix
            if (is_initial_safe(token) or 
                ('.' in token and any(c.isupper() for c in token)) or
                is_suffix_safe(token) or
                (len(token) == 1 and token.isupper())):
                # This and everything after are initials/suffixes
                initial_tokens = tokens[i:]
                break
            else:
                name_tokens.append(token)
        
        # If we found both names and initials, format properly
        if name_tokens and initial_tokens:
            # Check if this is a valid author format
            # Should have at least one proper initial or dot-containing token
            has_proper_initial = any(
                is_initial_safe(token) or ('.' in token and any(c.isupper() for c in token))
                for token in initial_tokens
            )
            
            # If there are no proper initials, it's probably not a valid author format
            if not has_proper_initial and len(initial_tokens) == 1 and len(initial_tokens[0]) == 1:
                # This is likely just "Name A" which is not a valid author format
                return text
            
            name_part = " ".join(name_tokens)
            # Process initials and suffixes
            processed_initials = []
            processed_suffixes = []
            
            for token in initial_tokens:
                if len(token) == 1 and token.isupper():
                    processed_initials.append(f"{token}.")
                elif is_initial_safe(token) or ('.' in token and any(c.isupper() for c in token)):
                    processed_initials.append(fix_initial_spacing(token))
                elif is_suffix_safe(token):
                    processed_suffixes.append(token)
                else:
                    processed_initials.append(token)
            
            # Build the result with proper comma placement
            result_parts = [name_part]
            if processed_initials:
                result_parts.append(" ".join(processed_initials))
            if processed_suffixes:
                result_parts.extend(processed_suffixes)
            
            return ", ".join(result_parts)
    
    # For other cases, just fix initial spacing
    text = fix_initial_spacing(text)
    return text


def normalize_author_string(s: str) -> str:
    """
    FIXED: Use fix_author_block for comprehensive author normalization.
    
    Args:
        s: Author string to normalize
    
    Returns:
        Normalized author string
    """
    # First remove dangerous Unicode characters and normalize whitespace
    # Remove BOM first
    s = s.replace("\ufeff", "")

    # Remove other dangerous Unicode characters
    dangerous_chars = [
        "\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\u202a", "\u202b",
        "\u202c", "\u202d", "\u202e", "\u2060", "\u2061", "\u2062", "\u2063",
        "\u2064", "\u202f",
    ]

    for char in dangerous_chars:
        s = s.replace(char, "")

    # Normalize all whitespace to regular spaces first
    s = re.sub(r"\s", " ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    
    # Now use fix_author_block for comprehensive author fixing
    result = fix_author_block(s)
    
    # Ensure NFC normalization
    result = unicodedata.normalize("NFC", result)
    return result


def normalize_for_comparison(s: str) -> str:
    """
    Normalize string for consistent comparison.
    
    Args:
        s: String to normalize
    
    Returns:
        Normalized string for comparison
    """
    # Simple normalization - just NFC and whitespace cleanup
    normalized = unicodedata.normalize("NFC", s)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def author_string_is_normalized(raw: str) -> Tuple[bool, str]:
    """
    Enhanced check if author string is normalized with robust Unicode handling.
    
    Args:
        raw: Raw author string
    
    Returns:
        Tuple of (is_normalized, normalized_string)
    """
    if not raw:
        return True, raw

    fixed = normalize_author_string(raw)

    # Enhanced Unicode normalization before comparison
    raw_normalized = nfc(raw.strip()) if raw else ""
    fixed_normalized = nfc(fixed.strip()) if fixed else ""

    # Use normalize_for_comparison for consistent comparison
    raw_for_comparison = normalize_for_comparison(raw_normalized)
    fixed_for_comparison = normalize_for_comparison(fixed_normalized)

    is_norm = raw_for_comparison == fixed_for_comparison

    debug_print("Author normalization check:")
    debug_print(f"  Raw: '{raw}' (normalized: '{raw_for_comparison}')")
    debug_print(f"  Fixed: '{fixed}' (normalized: '{fixed_for_comparison}')")
    debug_print(f"  Is normalized: {is_norm}")

    return is_norm, fixed


def author_string_is_normalized_debug(raw: str) -> Tuple[bool, str, Optional[str]]:
    """
    Extended version with debugging info.
    
    Args:
        raw: Raw author string
    
    Returns:
        Tuple of (is_normalized, normalized_string, debug_info)
    """
    fixed = normalize_author_string(raw)
    is_norm = fixed == raw

    debug_info = None
    if not is_norm:
        if has_invisible_differences(raw, fixed):
            debug_info = f"Invisible characters detected: {debug_author_string(raw)}"
        elif (
            raw.strip() != raw
            or "  " in raw
            or "\t" in raw
            or "\n" in raw
            or re.search(r"\s+,", raw)
            or re.search(r",(?!\s)", raw)
        ):
            debug_info = "Extra whitespace"
        elif not is_nfc(raw):
            debug_info = "Not NFC normalized"
        else:
            debug_info = f"Other differences: '{raw}' vs '{fixed}'"

    return is_norm, fixed, debug_info


def parse_authors_and_title(
    fullname: str, multiword_surnames: Optional[Set[str]] = None
) -> Tuple[str, str]:
    """
    Parse authors and title from a full filename.
    
    Args:
        fullname: Full filename string
        multiword_surnames: Optional set of multiword surnames
    
    Returns:
        Tuple of (authors, title)
    """
    # FIXED: Better separator detection
    if " - " not in fullname:
        # Check for missing space variations
        if " -" in fullname:
            return "", fullname  # Missing space after dash
        elif "- " in fullname:
            return "", fullname  # Missing space before dash
        else:
            return "", fullname  # No separator at all
    authors, title = fullname.split(" - ", 1)
    result = (authors.strip(), title.strip())
    return result


def fix_initial_spacing(author_part: str) -> str:
    """
    Fix spacing in author initials.
    
    Args:
        author_part: Author string to fix
    
    Returns:
        String with properly spaced initials
    """
    prev = None
    while prev != author_part:
        prev = author_part
        # Manual approach to handle Unicode uppercase letters
        # Look for pattern: uppercase letter, dot, uppercase letter, dot
        result = ""
        i = 0
        while i < len(author_part):
            char = author_part[i]
            if (i + 3 < len(author_part) and 
                char.isupper() and 
                author_part[i + 1] == '.' and 
                author_part[i + 2].isupper() and 
                author_part[i + 3] == '.'):
                # Found pattern like "A.B." - insert space
                result += char + '. ' + author_part[i + 2] + '.'
                i += 4
            else:
                result += char
                i += 1
        author_part = result
    return author_part


def fix_author_suffixes(s: str) -> str:
    """
    Fix author suffixes in author strings.
    
    Args:
        s: Author string to fix
    
    Returns:
        String with properly formatted suffixes
    """
    parts = [p.strip() for p in s.split(",") if p.strip()]
    res = []
    i = 0
    while i < len(parts):
        name = parts[i]
        # Fixed ReDoS vulnerability - use possessive quantifier and limit repetitions
        next_is_init = i + 1 < len(parts) and re.match(
            r"^[A-Z](?:\.\s?[A-Z]){0,10}\.$", parts[i + 1]
        )
        if (
            any(name.endswith(" " + suf) or name == suf for suf in SUFFIXES)
            and next_is_init
        ):
            surname, suffix = name.rsplit(" ", 1) if " " in name else (name, name)
            res.append(f"{surname}, {parts[i + 1]}, {suffix}")
            i += 2
        elif name in SUFFIXES and res:
            res[-1] = f"{res[-1]}, {name}"
            i += 1
        else:
            if next_is_init:
                res.append(f"{name}, {parts[i + 1]}")
                i += 2
            else:
                res.append(name)
                i += 1
    result = ", ".join(re.sub(r"\s{2,}", " ", x) for x in res)
    return result


def is_nfc(text: str) -> bool:
    """
    Check if text is in NFC normalization form.
    
    Args:
        text: Text to check
    
    Returns:
        True if text is NFC normalized
    """
    return unicodedata.normalize("NFC", text) == text


def safe_tokenize(text: str) -> List[str]:
    """Ultra-safe tokenization without regex - RESTORED from original"""
    if not text or len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH] if text else ""
    
    tokens = []
    current_token = []
    
    for i, char in enumerate(text):
        if i > MAX_INPUT_LENGTH:
            break
            
        if char.isspace() or char in ',;':
            if current_token:
                token = ''.join(current_token).strip()
                if token:
                    tokens.append(token)
                current_token = []
        else:
            current_token.append(char)
    
    if current_token:
        token = ''.join(current_token).strip()
        if token:
            tokens.append(token)
    
    return tokens[:500]  # Hard limit on tokens


def is_initial_safe(token: str) -> bool:
    """
    FIXED: Check if token is a SINGLE initial (like 'A.' but not 'J.D.' or 'AB.') - RESTORED from original
    Test requirements:
    - "A." → True (single initial)
    - "J.D." → False (multiple initials, too long)
    - "AB." → False (multiple letters)
    - "A.B." → False (multiple initials)
    """
    if not token:
        return False
    
    # Must end with dot
    if not token.endswith('.'):
        return False
    
    # Remove the dot to check the part before it
    without_dot = token[:-1]
    
    # Must be exactly one uppercase letter (single initial)
    if len(without_dot) != 1:
        return False
    
    # Must be uppercase letter
    if not without_dot.isupper() or not without_dot.isalpha():
        return False
    
    return True


def is_suffix_safe(tok: str) -> bool:
    """
    CRITICAL FIX: Safely check if token is a suffix - RESTORED from original
    Test requirements:
    - "Jr" → True
    - "Jr." → True  
    - "Sr" → True
    - "II" → True
    - "MD" → True
    - "PhD" → True
    - "A." → False (this is an initial, not suffix)
    - "I." → False (this is an initial, not Roman numeral suffix)
    """
    if not tok:
        return False
    
    # CRITICAL FIX: Don't treat single-letter initials as suffixes
    # This prevents "I.", "V.", "X." from being treated as Roman numerals
    # and fixes the idempotency issue
    if is_initial_safe(tok):
        return False
    
    # Remove trailing dot for normalization
    normalized = tok.lower().rstrip('.')
    
    # Don't treat surname particles as suffixes
    if normalized in _SURNAME_PARTICLES:
        return False
    
    # Check academic suffixes
    if normalized in _ACADEMIC_SUFFIXES:
        return True
    
    # Check Roman numerals
    if normalized in _ROMAN_NUMERALS_SET:
        return True
    
    return False


def _contains_multiple_authors(initials_part: str) -> bool:
    """Check if initials part contains multiple authors."""
    tokens = safe_tokenize(initials_part)
    if len(tokens) < 4:  # Need at least 4 tokens for multi-author
        return False
    
    # Look for pattern: initials surname initials surname
    surname_count = 0
    for token in tokens:
        # Check if token is likely a surname (not an initial, not a suffix, starts with uppercase)
        if (len(token) > 1 and 
            token[0].isupper() and 
            not is_initial_safe(token) and 
            not ('.' in token and any(c.isupper() for c in token)) and
            not is_suffix_safe(token)):
            surname_count += 1
    
    return surname_count >= 2


def _is_multi_author_space_format(tokens: List[str]) -> bool:
    """Check if tokens represent a multi-author space-separated format."""
    if len(tokens) < 4:
        return False
    
    # Look for pattern: surname initials surname [suffix]
    # Count surnames (non-initial, non-suffix tokens that could be surnames)
    surname_count = 0
    for token in tokens:
        if (len(token) > 1 and 
            token[0].isupper() and 
            not is_initial_safe(token) and 
            not ('.' in token and any(c.isupper() for c in token)) and
            not is_suffix_safe(token)):
            surname_count += 1
    
    # If we have multiple surnames and at least one initial, it's likely multi-author
    has_initials = any(is_initial_safe(token) or ('.' in token and any(c.isupper() for c in token)) for token in tokens)
    return surname_count >= 2 and has_initials


def _parse_multi_author_space_format(tokens: List[str]) -> str:
    """Parse multi-author space-separated format."""
    authors = []
    current_name_parts = []
    current_initials = []
    current_suffixes = []
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        if is_initial_safe(token) or ('.' in token and any(c.isupper() for c in token)):
            # This is an initial
            if len(token) == 1 and token.isupper():
                current_initials.append(f"{token}.")
            else:
                current_initials.append(fix_initial_spacing(token))
        elif is_suffix_safe(token):
            # This is a suffix
            current_suffixes.append(token)
        else:
            # This could be a surname
            # Check if we should complete the current author
            if current_initials and current_name_parts:
                # Complete current author
                author_parts = [" ".join(current_name_parts)]
                if current_initials:
                    author_parts.append(" ".join(current_initials))
                if current_suffixes:
                    author_parts.extend(current_suffixes)
                authors.append(", ".join(author_parts))
                
                # Start new author
                current_name_parts = [token]
                current_initials = []
                current_suffixes = []
            else:
                # Continue building the current name
                current_name_parts.append(token)
        
        i += 1
    
    # Handle the last author
    if current_name_parts:
        author_parts = [" ".join(current_name_parts)]
        if current_initials:
            author_parts.append(" ".join(current_initials))
        if current_suffixes:
            author_parts.extend(current_suffixes)
        authors.append(", ".join(author_parts))
    
    return ", ".join(authors)


def _parse_multi_author_from_initials(first_surname: str, initials_part: str) -> List[str]:
    """Parse multi-author format from initials part."""
    tokens = safe_tokenize(initials_part)
    authors = []
    
    # Start with the first author
    current_initials = []
    current_surname = None
    
    for token in tokens:
        if (is_initial_safe(token) or 
            ('.' in token and any(c.isupper() for c in token)) or
            (len(token) == 1 and token.isupper())):
            # This is an initial
            if len(token) == 1 and token.isupper():
                current_initials.append(f"{token}.")
            else:
                current_initials.append(fix_initial_spacing(token))
        elif is_suffix_safe(token):
            # This is a suffix - add to current author
            if current_surname and current_initials:
                author_name = f"{current_surname}, {' '.join(current_initials)}, {token}"
                authors.append(author_name)
                current_initials = []
                current_surname = None
            elif current_initials:
                # Add suffix to initials
                current_initials.append(token)
        else:
            # This is a surname
            if current_initials:
                # Complete the previous author
                if current_surname:
                    author_name = f"{current_surname}, {' '.join(current_initials)}"
                    authors.append(author_name)
                else:
                    # This is the first author
                    author_name = f"{first_surname}, {' '.join(current_initials)}"
                    authors.append(author_name)
                current_initials = []
            current_surname = token
    
    # Handle the last author
    if current_initials:
        if current_surname:
            author_name = f"{current_surname}, {' '.join(current_initials)}"
            authors.append(author_name)
        else:
            # Add remaining initials to the last author
            if authors:
                authors[-1] += f", {' '.join(current_initials)}"
    
    return authors


def _names_are_trivially_equivalent(name1: str, name2: str) -> bool:
    """Check if two names differ only in punctuation/spacing - RESTORED from original"""
    # For ultra-comprehensive testing, we need to be more strict
    # Only consider names equivalent if they have the same structural format
    
    # First normalize whitespace
    norm1 = re.sub(r'\s+', ' ', name1.strip())
    norm2 = re.sub(r'\s+', ' ', name2.strip())
    
    # If they're exactly the same, they're equivalent
    if norm1 == norm2:
        return True
    
    # Check if they have the same comma structure
    # Count commas and their positions
    comma_count1 = norm1.count(',')
    comma_count2 = norm2.count(',')
    
    # If comma counts differ significantly, they're not equivalent
    if abs(comma_count1 - comma_count2) > 1:
        return False
    
    # For basic equivalence, only remove dots and extra spaces
    # but preserve comma structure
    def light_normalize(name):
        # Only remove dots and normalize spaces, keep commas
        name = name.replace('.', '')
        name = re.sub(r'\s+', ' ', name).strip().lower()
        return name
    
    light_norm1 = light_normalize(norm1)
    light_norm2 = light_normalize(norm2)
    
    return light_norm1 == light_norm2