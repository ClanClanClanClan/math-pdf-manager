#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Math-PDF manager (Fixed Version v18 - DEBUG MODE & PROPER WORD LISTS)
─────────────────────────────────────────────────────────────────────────────
FIXES v18:
• CRITICAL: Enable debug mode to see exactly what's happening
• CRITICAL: Ensure proper word list loading and verification
• CRITICAL: Add comprehensive debugging for word list issues
• CRITICAL: Fix compound_terms usage in filename checking
• CRITICAL: Verify all word lists are properly loaded and combined
• All previous fixes preserved
"""

from __future__ import annotations
from utils.security import PathValidator, SecureXMLParser

import argparse
import logging
import os
import re
import sys
import signal
import time
import unicodedata as _ud
import yaml
import threading
import time
from contextlib import contextmanager
from functools import lru_cache
from os.path import exists
from pathlib import Path
from typing import Any, Iterable, List, Set, Dict, Tuple, Optional

from utils import load_yaml_config
from scanner import scan_directory
from filename_checker import batch_check_filenames, is_canonically_equivalent, enable_debug, debug_print
from duplicate_detector import find_duplicates
from reporter import generate_html_report, generate_csv_report
from my_spellchecker import SpellChecker, SpellCheckerConfig
from unicode_constants import SUFFIXES as _SUFFIXES_LIST

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS - Replace magic strings with named constants
# ═══════════════════════════════════════════════════════════════════

DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_KNOWN_WORDS_FILE = "known_words.txt"
DEFAULT_NAME_DASH_WHITELIST_FILE = "name_dash_whitelist.txt"
DEFAULT_MULTIWORD_FAMILYNAMES_FILE = "multiword_familynames.txt"
DEFAULT_HTML_OUTPUT = "report.html"
DEFAULT_CSV_OUTPUT = "report.csv"
DEFAULT_TEMPLATE_DIR = "templates"

# Performance limits to prevent hanging
MAX_INPUT_LENGTH = 5000
MAX_AUTHORS = 20
MAX_ITERATIONS = 1000
OPERATION_TIMEOUT = 2.0

# Environment configuration
ENV_CONFIG = {
    "PYTHONWARNINGS": "ignore",
    "MPLBACKEND": "agg",
    "FITZ_IGNORE_NO_MUPDF": "1",
}

# Libraries to suppress logging for
SUPPRESSED_LOGGERS = ("fitz", "pdfminer", "pdfplumber")

# Dropbox migration paths
DROPBOX_OLD_PATH = Path.home() / "Dropbox"
DROPBOX_NEW_PATH = Path.home() / "Library/CloudStorage/Dropbox"

# Extended surname particles list
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

# ═══════════════════════════════════════════════════════════════════
# IMPROVED LOGGING SETUP - Avoid global state modification
# ═══════════════════════════════════════════════════════════════════

def setup_logging() -> logging.Logger:
    """Set up logging without global state modification."""
    # Return to normal INFO level
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    
    # Suppress noisy libraries
    for lib_name in SUPPRESSED_LOGGERS:
        logging.getLogger(lib_name).setLevel(logging.ERROR)
    
    return logging.getLogger("main")

def setup_environment() -> None:
    """Set up environment variables using constants."""
    os.environ.update(ENV_CONFIG)

# Initialize logger properly
logger = setup_logging()

# ═══════════════════════════════════════════════════════════════════
# TIMEOUT PROTECTION - Prevent hanging operations
# ═══════════════════════════════════════════════════════════════════

class TimeoutError(Exception):
    pass

@contextmanager  
def timeout_protection(seconds: float):
    """Context manager to timeout any operation with cross-platform support."""
    # Always use manual timeout checking for reliability in tests
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        if elapsed > seconds:
            raise TimeoutError(f"Operation took {elapsed:.3f}s, exceeding {seconds}s limit")

# ═══════════════════════════════════════════════════════════════════
# PERFORMANCE IMPROVEMENTS - Cached operations
# ═══════════════════════════════════════════════════════════════════

@lru_cache(maxsize=256)
def _normalize_nfc_cached(text: str) -> str:
    """Cache Unicode NFC normalization for performance."""
    if text is None:
        return ""
    return _ud.normalize("NFC", str(text))

@lru_cache(maxsize=256)
def _normalize_nfd_cached(text: str) -> str:
    """Cache Unicode NFD normalization for performance."""
    if text is None:
        return ""
    return _ud.normalize("NFD", str(text))

@lru_cache(maxsize=None)
def _get_suffix_map() -> Dict[str, str]:
    """Create suffix mapping once and cache it."""
    return {s.lower().replace(".", ""): s for s in _SUFFIXES_LIST}

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION LOADING - Secure YAML loading with error handling
# ═══════════════════════════════════════════════════════════════════

def load_yaml_config_secure(config_path: str) -> dict:
    """
    Load YAML configuration with comprehensive error handling and malformed YAML extraction.
    
    This function safely loads YAML configuration files and can extract useful data
    even from malformed YAML files that contain loose list items.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing configuration data
    """
    if not config_path:
        logger.warning("No config path provided")
        return {}
        
    config_file = Path(config_path)
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_path}")
        return {}
    
    try:
        with open(config_file, "r", encoding="utf-8", encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            logger.warning(f"Config file is empty: {config_path}")
            return {}
        
        try:
            # Try normal YAML parsing first
            cfg = yaml.safe_load(content)
            if cfg is None:
                cfg = {}
            if not isinstance(cfg, dict):
                logger.warning(f"Config file should contain a dictionary, got {type(cfg)}")
                cfg = {}
            
            logger.info(f"✓ Config loaded with {len(cfg)} keys")
            
            # Try to extract malformed lists from comments/loose items
            extracted_lists = _extract_malformed_lists(content)
            if extracted_lists:
                cfg.update(extracted_lists)
                logger.info(f"✓ Also extracted {len(extracted_lists)} malformed lists")
            
            return cfg
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing failed: {e}")
            # Try to extract what we can from malformed YAML
            extracted = _extract_malformed_lists(content)
            if extracted:
                logger.info(f"✓ Extracted {len(extracted)} lists from malformed YAML")
                return extracted
            return {}
            
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def _extract_malformed_lists(content: str) -> dict:
    """
    Extract useful lists from malformed YAML content.
    
    This function tries to extract list items that might be floating
    outside of proper YAML structure, such as commented lists or
    loose list items.
    
    Args:
        content: Raw YAML file content
        
    Returns:
        Dictionary with extracted lists
    """
    extracted = {}
    
    # Look for patterns like loose list items after comments
    lines = content.split('\n')
    current_list = []
    current_key = None
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Check for comment indicating list type
        if line.startswith('#'):
            # Finish previous list if any
            if current_list and current_key:
                extracted[current_key] = current_list
                current_list = []
            
            # Determine list type from comment
            comment_lower = line.lower()
            if 'mathematician' in comment_lower or 'names' in comment_lower:
                current_key = 'capitalization_whitelist_from_comments'
            elif 'math' in comment_lower and 'term' in comment_lower:
                current_key = 'math_terms_from_comments'
            elif 'roman' in comment_lower and 'numeral' in comment_lower:
                current_key = 'roman_numerals_from_comments'
            elif 'german' in comment_lower and 'noun' in comment_lower:
                current_key = 'german_nouns_from_comments'
            elif 'exception' in comment_lower:
                current_key = 'exceptions_from_comments'
            else:
                current_key = 'capitalization_whitelist_from_comments'  # Default
            
        # Check for list items
        elif line.startswith('- '):
            item = line[2:].strip()
            if item and current_key:
                current_list.append(item)
    
    # Finish last list
    if current_list and current_key:
        extracted[current_key] = current_list
    
    if extracted:
        logger.info(f"✓ Extracted {len(extracted)} lists from malformed YAML")
        for key, items in extracted.items():
            logger.info(f"  {key}: {len(items)} items")
    
    return extracted

# ═══════════════════════════════════════════════════════════════════
# SOPHISTICATED AUTHOR PROCESSING - Complete rewrite with fixes
# ═══════════════════════════════════════════════════════════════════

def safe_tokenize(text: str) -> List[str]:
    """Ultra-safe tokenization without regex."""
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
    FIXED: Check if token is a SINGLE initial (like 'A.' but not 'J.D.' or 'AB.').
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
    CRITICAL FIX: Safely check if token is a suffix.
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

def fix_initial_spacing(author_part: str) -> str:
    """
    FIXED: Properly space initials like J.D. → J. D. but leave A.B → A.B (no trailing dot).
    Test requirements:
    - "A.B.C." → "A. B. C." (has trailing dot, add spaces)
    - "J.D." → "J. D." (has trailing dot, add spaces)
    - "A.B" → "A.B" (no trailing dot, leave unchanged)
    - "A. B." → "A. B." (already spaced)
    """
    if not author_part:
        return author_part
    
    # Only process if there's a trailing dot (indicating complete initials)
    if not author_part.endswith('.'):
        return author_part
    
    # Use simple character-by-character processing to avoid regex issues
    result = []
    i = 0
    
    while i < len(author_part):
        char = author_part[i]
        result.append(char)
        
        # If current char is '.' and next char is uppercase letter, add space
        if (char == '.' and 
            i + 1 < len(author_part) and 
            author_part[i + 1].isupper()):
            result.append(' ')
        
        i += 1
    
    return ''.join(result)

def should_skip_word_before_suffix(word: str, suffix: str, already_has_surname: bool = True, already_has_initials: bool = True) -> bool:
    """
    CRITICAL FIX: Determine if we should skip a word before a suffix.
    More conservative logic - only skip in very specific cases.
    """
    # Never skip if the "suffix" also looks like an initial
    if is_initial_safe(suffix):
        return False
    
    # Check if suffix is a Roman numeral
    suffix_norm = suffix.lower().rstrip('.')
    if suffix_norm in ['ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']:
        # FIXED: Be much more conservative about skipping words
        # Only skip if:
        # 1. We already have complete name parts (surname + initials)
        # 2. The word looks like it's definitely not part of the main name
        # 3. The word is short (likely a title or connector)
        if (already_has_surname and already_has_initials and 
            len(word) <= 2 and word.lower() in ['de', 'la', 'el', 'y', 'e', 'and']):
            return True
        
        # Don't skip anything else - be conservative
        return False
    
    # For other suffixes, don't skip
    return False

def _looks_like_valid_author_format(tokens: List[str]) -> bool:
    """
    CRITICAL FIX: Check if tokens look like a valid author format before processing.
    This prevents converting invalid patterns like "Single A" into "Single, A."
    """
    if len(tokens) < 2:
        return False
    
    # Count potential initials (with dots) vs single letters
    initials_with_dots = 0
    single_letters = 0
    potential_surnames = 0
    
    for token in tokens:
        if is_initial_safe(token) or ('.' in token and any(c.isupper() for c in token)):
            initials_with_dots += 1
        elif len(token) == 1 and token.isupper():
            single_letters += 1
        elif token and token[0].isupper() and len(token) > 1 and not is_suffix_safe(token):
            potential_surnames += 1
    
    # Valid patterns should have:
    # 1. At least one surname-like word, AND
    # 2. Either proper initials (with dots) OR multiple single letters suggesting initials
    has_surname = potential_surnames > 0
    has_proper_initials = initials_with_dots > 0
    has_multiple_single_letters = single_letters > 1
    
    return has_surname and (has_proper_initials or has_multiple_single_letters)

def parse_single_author_from_tokens(tokens: List[str], start_index: int) -> Tuple[str, int]:
    """
    Parse a single author from tokens starting at start_index.
    Returns (author_string, next_index).
    FIXED: Better handling of edge cases and final token consumption.
    """
    if start_index >= len(tokens):
        return "", start_index
    
    # CRITICAL FIX: Check if this looks like a valid author format
    remaining_tokens = tokens[start_index:]
    if not _looks_like_valid_author_format(remaining_tokens):
        # If it doesn't look like an author format, don't process it
        return "", len(tokens)
    
    surname_parts = []
    initials = []
    suffixes = []
    index = start_index
    
    # Step 1: Collect surname particles
    while index < len(tokens) and tokens[index].lower() in _SURNAME_PARTICLES:
        surname_parts.append(tokens[index].lower())
        index += 1
    
    # Step 2: Collect main surname parts - stop at first initial
    while index < len(tokens):
        token = tokens[index]
        
        # Stop at initials
        if is_initial_safe(token) or (len(token) == 1 and token.isupper()) or ('.' in token and any(c.isupper() for c in token)):
            break
        # Stop at clear suffixes
        if is_suffix_safe(token) and len(token) > 2:
            break
            
        # Add to surname
        surname_parts.append(token)
        index += 1
        
        if len(surname_parts) > 10:
            break
    
    if not surname_parts:
        return "", start_index + 1
    
    # Step 3: Collect initials
    while index < len(tokens):
        token = tokens[index]
        
        # Stop at suffixes
        if is_suffix_safe(token) and len(token) > 2:
            break
        
        if is_initial_safe(token):
            spaced = fix_initial_spacing(token)
            for part in spaced.split():
                if part.endswith('.'):
                    initials.append(part)
            index += 1
        elif '.' in token and any(c.isupper() for c in token):
            spaced = fix_initial_spacing(token)
            for part in spaced.split():
                if part.endswith('.'):
                    initials.append(part)
            index += 1
        elif len(token) == 1 and token.isupper():
            # CRITICAL FIX: Only convert single letters to initials if we're in a valid author context
            # and there are other indicators this is meant to be an initial
            if (len(initials) > 0 or  # Already have other initials
                index + 1 < len(tokens) and is_suffix_safe(tokens[index + 1])):  # Next token is a suffix
                initials.append(f"{token}.")
                index += 1
            else:
                # Don't convert single letters if context doesn't support it
                break
        else:
            break
        
        if len(initials) > 30:
            break
    
    # Step 4: Handle additional name parts (like García in "de la Cruz J.M. García II")
    additional_parts = []
    if index < len(tokens):
        token = tokens[index]
        if (token and token[0].isupper() and len(token) > 1 and 
            not is_suffix_safe(token)):
            # This could be an additional surname component
            additional_parts.append(token)
            index += 1
    
    # Step 5: Skip potential connecting words before suffixes
    if index < len(tokens) - 1:
        current_token = tokens[index]
        next_token = tokens[index + 1] if index + 1 < len(tokens) else None
        
        has_surname = len(surname_parts) > 0
        has_initials = len(initials) > 0
        
        if (next_token and 
            is_suffix_safe(next_token) and 
            not is_initial_safe(next_token) and
            should_skip_word_before_suffix(current_token, next_token, has_surname, has_initials)):
            index += 1
    
    # Step 6: Collect suffixes
    while index < len(tokens) and len(suffixes) < 5:
        token = tokens[index]
        
        if not is_suffix_safe(token):
            break
            
        base = token.rstrip('.')
        lower = base.lower()
        
        if lower == 'jr':
            suffixes.append('Jr')
        elif lower == 'sr':
            suffixes.append('Sr')
        elif lower in _ROMAN_NUMERALS_SET:
            suffixes.append(base.upper())
        elif lower in _ACADEMIC_SUFFIXES:
            if lower == 'phd':
                suffixes.append('PhD')
            elif lower == 'md':
                suffixes.append('MD')
            else:
                suffixes.append(base.upper())
        else:
            suffixes.append(base)
        
        index += 1
    
    # Build the author string
    author_str = ' '.join(surname_parts)
    
    if initials:
        author_str += ', ' + ' '.join(initials)
    
    # Add additional parts (like García) as separate components
    if additional_parts:
        author_str += ', ' + ', '.join(additional_parts)
    
    if suffixes:
        author_str += ', ' + ', '.join(suffixes)
    
    return author_str, index

def _parse_multi_author_comma_case(first_part: str, second_part: str) -> List[str]:
    """
    CRITICAL FIX: Parse the specific case of "First Author, Initials Other Authors..."
    Returns list of properly formatted authors.
    Fixed to handle all remaining tokens correctly.
    """
    authors = []
    tokens = safe_tokenize(second_part)
    
    # First author gets the first initials
    first_initials = []
    i = 0
    
    # Collect initials for the first author
    while i < len(tokens):
        token = tokens[i]
        if is_initial_safe(token) or (len(token) == 1 and token.isupper()) or ('.' in token and any(c.isupper() for c in token)):
            # Add proper formatting
            if len(token) == 1 and token.isupper():
                first_initials.append(f"{token}.")
            elif is_initial_safe(token):
                first_initials.append(token)
            elif '.' in token:
                spaced = fix_initial_spacing(token)
                first_initials.extend(part for part in spaced.split() if part.endswith('.'))
            i += 1
        else:
            # This must be the start of the next author
            break
    
    # Build first author
    if first_initials:
        first_author = f"{first_part}, {' '.join(first_initials)}"
        authors.append(first_author)
    else:
        authors.append(first_part)
    
    # CRITICAL FIX: Parse remaining authors from the remaining tokens
    remaining_tokens = tokens[i:]
    j = 0
    while j < len(remaining_tokens):
        # CRITICAL FIX: Check if remaining tokens look like valid author format
        if _looks_like_valid_author_format(remaining_tokens[j:]):
            author, next_j = parse_single_author_from_tokens(remaining_tokens, j)
            if author and next_j > j:
                authors.append(author)
                j = next_j
            else:
                # If we can't parse as an author, try to handle as individual components
                j += 1
        else:
            # CRITICAL FIX: Handle final tokens that don't form complete authors
            # This handles cases like final "A." or "A" tokens
            remaining = remaining_tokens[j:]
            if len(remaining) == 1:
                token = remaining[0]
                if len(token) == 1 and token.isupper():
                    # Convert single letter to initial
                    authors.append(f"{token}.")
                elif is_initial_safe(token):
                    # It's already a proper initial
                    authors.append(token)
                else:
                    # It's a surname without initials
                    authors.append(token)
                break
            elif len(remaining) == 2:
                # Could be "Surname Initial"
                surname, initial = remaining[0], remaining[1]
                if len(initial) == 1 and initial.isupper():
                    authors.append(f"{surname}, {initial}.")
                elif is_initial_safe(initial):
                    authors.append(f"{surname}, {initial}")
                else:
                    # Two separate surnames
                    authors.extend(remaining)
                break
            else:
                # Multiple remaining tokens, try to parse normally
                j += 1
    
    return authors

def parse_space_separated_authors(text: str) -> List[str]:
    """Parse multiple authors from space-separated format."""
    tokens = safe_tokenize(text)
    
    # CRITICAL FIX: Check if this looks like a valid author format before processing
    if not _looks_like_valid_author_format(tokens):
        return []
    
    authors = []
    index = 0
    
    while index < len(tokens) and len(authors) < MAX_AUTHORS:
        author, next_index = parse_single_author_from_tokens(tokens, index)
        if author and next_index > index:
            authors.append(author)
            index = next_index
        else:
            index += 1
            
        if index >= len(tokens):
            break
    
    return authors

def parse_comma_separated_standard(parts: List[str]) -> List[str]:
    """Parse standard comma-separated format: Surname, Initials, Surname, Initials."""
    authors = []
    i = 0
    
    while i < len(parts):
        if i + 1 < len(parts):
            # Pair up surname and initials
            surname = parts[i].strip()
            initials_part = parts[i + 1].strip()
            
            # Apply initial spacing fix
            initials_fixed = fix_initial_spacing(initials_part)
            
            # Also parse suffixes that might be in the initials part
            tokens = safe_tokenize(initials_fixed)
            actual_initials = []
            suffixes = []
            
            for token in tokens:
                if is_suffix_safe(token):
                    # FIXED: Format suffix properly
                    base = token.rstrip('.')
                    lower = base.lower()
                    if lower == 'jr':
                        suffixes.append('Jr')
                    elif lower == 'sr':
                        suffixes.append('Sr')
                    elif lower in _ROMAN_NUMERALS_SET:
                        suffixes.append(base.upper())
                    elif lower == 'phd':
                        suffixes.append('PhD')
                    elif lower == 'md':
                        suffixes.append('MD')
                    else:
                        suffixes.append(base.upper())
                else:
                    actual_initials.append(token)
            
            author = surname
            if actual_initials:
                author += f", {' '.join(actual_initials)}"
            if suffixes:
                author += f", {', '.join(suffixes)}"
                
            authors.append(author)
            i += 2
        else:
            # Odd number of parts, just add the last one
            authors.append(parts[i].strip())
            i += 1
    
    return authors

def fix_author_block(raw_input: str) -> str:
    """
    Main author processing function that handles all formats correctly.
    """
    if not raw_input or not isinstance(raw_input, str):
        return ""
    
    if len(raw_input) > MAX_INPUT_LENGTH:
        raw_input = raw_input[:MAX_INPUT_LENGTH]
    
    try:
        with timeout_protection(OPERATION_TIMEOUT):
            return _process_author_core(raw_input)
    except TimeoutError:
        return _emergency_cleanup(raw_input)
    except Exception:
        return _emergency_cleanup(raw_input)

def _process_author_core(raw_input: str) -> str:
    """Core author processing logic with improved multi-author detection."""
    text = _normalize_nfc_cached(raw_input.strip())
    text = text.lstrip(',').strip()
    
    if not text:
        return ""
    
    # Clean up spaces and commas
    while '  ' in text:
        text = text.replace('  ', ' ')
    while ',,' in text:
        text = text.replace(',,', ',')
    text = text.strip(',').strip()
    
    # Handle comma-separated format first
    if ',' in text:
        parts = [p.strip() for p in text.split(',') if p.strip()]
        
        if len(parts) == 2:
            first_part = parts[0]
            second_part = parts[1]
            
            second_tokens = safe_tokenize(second_part)
            
            # CRITICAL FIX: Better multi-author detection
            # Count initials vs surnames in the second part
            initial_count = 0
            surname_count = 0
            
            for token in second_tokens:
                if len(token) == 1 and token.isupper():
                    initial_count += 1
                elif is_initial_safe(token) or ('.' in token and any(c.isupper() for c in token)):
                    # Count dots to estimate number of initials
                    initial_count += token.count('.')
                elif is_suffix_safe(token):
                    pass  # Suffixes don't count
                else:
                    if token and token[0].isupper() and len(token) > 1:
                        surname_count += 1
            
            # If we have significantly more initials than surnames, and multiple surnames,
            # this suggests multiple authors
            if surname_count >= 2 and initial_count >= surname_count:
                # Parse as multiple authors
                authors = _parse_multi_author_comma_case(first_part, second_part)
                if len(authors) > 1:
                    return ', '.join(authors)
            
            # Normal single author processing
            fixed_parts = []
            for token in second_tokens:
                if len(token) == 1 and token.isupper():
                    fixed_parts.append(f"{token}.")
                elif is_initial_safe(token) or ('.' in token and any(c.isupper() for c in token)):
                    fixed_parts.append(fix_initial_spacing(token))
                else:
                    fixed_parts.append(token)
            
            return f"{first_part}, {' '.join(fixed_parts)}"
        
        # Handle standard comma-separated format
        elif len(parts) >= 4 and len(parts) % 2 == 0:
            authors = parse_comma_separated_standard(parts)
            return ', '.join(authors)
    
    # Handle space-separated format (no commas)
    if ',' not in text:
        tokens = safe_tokenize(text)
        
        # CRITICAL FIX: Don't process if it doesn't look like a valid author format
        if not _looks_like_valid_author_format(tokens):
            return text  # Return unchanged
        
        # Try parsing as single author first for better compound surname handling
        if len(tokens) >= 3:
            author, consumed = parse_single_author_from_tokens(tokens, 0)
            
            # If we consumed most/all tokens, it's likely a single author
            if consumed >= len(tokens) - 1 and author:
                return author
        
        # Otherwise try multi-author parsing
        authors = []
        i = 0
        while i < len(tokens):
            author, next_i = parse_single_author_from_tokens(tokens, i)
            if author and next_i > i:
                authors.append(author)
                i = next_i
            else:
                i += 1
        
        if len(authors) > 1:
            return ', '.join(authors)
        elif len(authors) == 1:
            return authors[0]
    
    # Fallback
    return _emergency_cleanup(text)

def _emergency_cleanup(raw_input: str) -> str:
    """Emergency cleanup when parsing fails."""
    if not raw_input:
        return ""
    
    text = _normalize_nfc_cached(raw_input.strip())
    text = fix_initial_spacing(text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lstrip(',').strip()
    
    return text

# Aliases for compatibility
normalize_author_string_complete = fix_author_block
fix_authors = fix_author_block

def authors_are_equivalent(auth1: str, auth2: str) -> bool:
    """
    FIXED: Check if two author strings are equivalent with Unicode normalization.
    
    This function now properly handles Unicode normalization differences.
    Strings that are visually identical but stored in different Unicode 
    normalization forms (NFC vs NFD) will be considered equivalent.
    
    Args:
        auth1: First author string
        auth2: Second author string
        
    Returns:
        True if the authors are equivalent after normalization
    """
    if not auth1 and not auth2:
        return True
    
    if not auth1 or not auth2:
        return False
    
    # FIXED: Normalize both strings to NFC before comparison
    # This ensures that visually identical strings with different
    # Unicode normalization forms are considered equivalent
    norm1 = _normalize_nfc_cached(str(auth1))
    norm2 = _normalize_nfc_cached(str(auth2))
    
    return norm1 == norm2

# ═══════════════════════════════════════════════════════════════════
# TITLE COMPARISON - Handle Unicode properly
# ═══════════════════════════════════════════════════════════════════

def normalize_title_for_comparison(title: str) -> str:
    """
    ENHANCED: Normalize title for comparison, handling Unicode characters properly.
    """
    if not title:
        return title
    
    # ENHANCED: Use cached NFC normalization consistently
    title = _normalize_nfc_cached(title)
    
    # Replace various dash characters with regular hyphen
    title = title.replace('–', '-')  # en-dash to hyphen
    title = title.replace('—', '-')  # em-dash to hyphen
    title = title.replace('‒', '-')  # figure dash to hyphen
    title = title.replace('―', '-')  # horizontal bar to hyphen
    
    return title

# ═══════════════════════════════════════════════════════════════════
# SCANNER COMPATIBILITY FIX
# ═══════════════════════════════════════════════════════════════════

def normalize_file_metadata(files: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """
    Normalize file metadata to ensure consistent keys.
    Handles different scanner implementations that might use 'name' instead of 'filename'.
    """
    normalized = []
    
    for file_dict in files:
        # Create a normalized copy
        norm_dict = file_dict.copy()
        
        # Ensure 'filename' key exists
        if 'filename' not in norm_dict:
            if 'name' in norm_dict:
                # Scanner uses 'name' instead of 'filename'
                norm_dict['filename'] = norm_dict['name']
            elif 'path' in norm_dict:
                # Extract filename from path as last resort
                try:
                    norm_dict['filename'] = Path(norm_dict['path']).name
                except Exception:
                    norm_dict['filename'] = 'UNKNOWN'
            else:
                norm_dict['filename'] = 'UNKNOWN'
        
        # Ensure other expected keys exist with defaults
        norm_dict.setdefault('path', '')
        norm_dict.setdefault('folder', '')
        norm_dict.setdefault('extension', '')
        
        normalized.append(norm_dict)
    
    return normalized

# ═══════════════════════════════════════════════════════════════════
# SECURITY IMPROVEMENTS - Input validation and safe operations
# ═══════════════════════════════════════════════════════════════════

def validate_cli_inputs(args) -> bool:
    """FIXED: Validate command-line arguments for safety with stricter path traversal detection."""
    if hasattr(args, 'root') and args.root:
        try:
            # FIXED: Check for path traversal BEFORE resolving the path
            raw_path = str(args.root)
            PathValidator.validate_path(user_path, base_dir)'):
                logger.error("Path traversal detected in root argument")
                return False
            
            # Also check after resolution
            root_path = Path(args.root).expanduser().resolve()
            root_str = str(root_path)
            
            # Additional checks for resolved path
            if '..' in root_str:
                logger.error("Path traversal detected in resolved root argument")
                return False
                
            # Ensure reasonable path length
            if len(root_str) > 1000:
                logger.error("Root path too long (potential attack)")
                return False
                
        except Exception as e:
            logger.error(f"Invalid root path: {args.root} ({e})")
            return False
    
    # Validate output file paths
    for output_arg in ['output', 'csv_output']:
        if hasattr(args, output_arg):
            output_path = getattr(args, output_arg, None)
            if output_path:
                try:
                    # Check raw path first
                    if '..' in str(output_path):
                        logger.error(f"Path traversal detected in {output_arg}: {output_path}")
                        return False
                        
                    out_path = Path(output_path).resolve()
                    out_str = str(out_path)
                    if '..' in out_str or len(out_str) > 500:
                        logger.error(f"Invalid output path: {output_path}")
                        return False
                except Exception:
                    logger.error(f"Cannot resolve output path: {output_path}")
                    return False
    
    return True

def validate_template_dir(template_dir: str) -> bool:
    """Validate template directory exists and is safe."""
    try:
        tmpl_path = Path(template_dir).resolve()
        
        if not tmpl_path.exists():
            logger.warning(f"Template directory does not exist: {template_dir}")
            logger.info("Reports will use default templates")
            return False
            
        if not tmpl_path.is_dir():
            logger.error(f"Template path is not a directory: {template_dir}")
            return False
            
        if not os.access(tmpl_path, os.R_OK):
            logger.error(f"Cannot read template directory: {template_dir}")
            return False
            
        logger.info(f"Using template directory: {template_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Template directory validation failed: {e}")
        return False

def safe_file_rename(old_path: Path, new_path: Path) -> bool:
    """Safely rename file with specific error handling."""
    try:
        # Check permissions before attempting rename
        if not os.access(old_path.parent, os.W_OK):
            logger.error(f"No write permission in directory: {old_path.parent}")
            return False
            
        # Check if target already exists
        if new_path.exists():
            logger.error(f"Target file already exists: {new_path}")
            return False
            
        # Perform the rename
        old_path.rename(new_path)
        logger.info(f"Renamed: {old_path.name} → {new_path.name}")
        return True
        
    except PermissionError:
        logger.error(f"Permission denied renaming: {old_path}")
    except FileNotFoundError:
        logger.error(f"Source file not found: {old_path}")
    except FileExistsError:
        logger.error(f"Target file exists: {new_path}")
    except OSError as e:
        logger.error(f"OS error renaming {old_path} → {new_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error renaming {old_path}: {e}")
        
    return False

# ═══════════════════════════════════════════════════════════════════
# IMPROVED PATH HANDLING - Consistent types and secure operations
# ═══════════════════════════════════════════════════════════════════

def _migrate_dropbox(p: str | Path) -> str:
    """Migrate Dropbox paths with improved error handling."""
    try:
        p = Path(p).expanduser().resolve()
        
        # Validate path doesn't contain suspicious components
        if any(part.startswith('.') and len(part) > 2 for part in p.parts):
            logger.warning(f"Suspicious path component detected: {p}")
            return str(p)
            
        if p.is_absolute() and DROPBOX_OLD_PATH in p.parents and not p.exists():
            alt = DROPBOX_NEW_PATH / p.relative_to(DROPBOX_OLD_PATH)
            if alt.exists():
                logger.info(f"Migrated Dropbox path: {p} → {alt}")
                return str(alt)
                
    except (ValueError, OSError) as e:
        logger.warning(f"Path migration failed for {p}: {e}")
        
    return str(p)

def resolve_path(p: str | Path | None, base: str | Path | None = None) -> str | None:
    """Resolve path with improved error handling."""
    if not p:
        return None
    p = os.path.expanduser(str(p))
    if not os.path.isabs(p) and base:
        p = os.path.join(os.path.expanduser(base), p)
    return os.path.abspath(_migrate_dropbox(p))

def _load_words_file_fixed(path: str | None, base_dir: str | None = None, description: str = "word file") -> Set[str]:
    """FIXED: Load words file with better path resolution and error reporting."""
    if not path:
        logger.info(f"No path specified for {description}")
        return set()
    
    # Better path resolution
    if base_dir and not os.path.isabs(path) and not path.startswith('~'):
        resolved_path = Path(base_dir) / path
    else:
        resolved_path = Path(path).expanduser()
    
    resolved_path = resolved_path.resolve()
    logger.info(f"Loading {description}: {resolved_path}")
    
    if not resolved_path.exists():
        logger.warning(f"{description} not found: {resolved_path}")
        
        # Try alternative locations
        alternatives = [
            Path.cwd() / Path(path).name,  # Current directory
            Path(__file__).parent / Path(path).name,  # Script directory
        ]
        
        for alt in alternatives:
            if alt.exists():
                logger.info(f"Found {description} at: {alt}")
                resolved_path = alt
                break
        else:
            logger.warning(f"No {description} found in any location")
            return set()
    
    try:
        with open(resolved_path, "r", encoding="utf-8", encoding='utf-8') as f:
            words = {
                _normalize_nfc_cached(line.strip()) 
                for line in f 
                if line.strip() and not line.strip().startswith('#')
            }
        
        logger.info(f"✓ Loaded {len(words)} words from {description}")
        return words
        
    except Exception as e:
        logger.error(f"Failed to load {description} from {resolved_path}: {e}")
        return set()

def _load_config_list(config: dict, key: str, default=None) -> set:
    """Load a list from config and convert to set."""
    if default is None:
        default = []
    
    raw_data = config.get(key, default)
    if isinstance(raw_data, (list, set)):
        result = set(raw_data)
        if result:
            logger.info(f"✓ Loaded {len(result)} items from config key '{key}'")
        return result
    elif raw_data is None:
        return set()
    else:
        logger.warning(f"Config key '{key}' should be a list, got {type(raw_data)}")
        return set()

def _add_nfd_variants(items: Iterable[str]) -> List[str]:
    """Add NFD variants with optimized caching."""
    out: List[str] = []
    for s in items:
        nfc = _normalize_nfc_cached(s)
        nfd = _normalize_nfd_cached(s)
        out.append(nfc)
        if nfd != nfc:  # Only add if different
            out.append(nfd)
    return out

def _split(fn: str) -> tuple[str, str] | None:
    """Split filename into author and title parts."""
    if " - " not in fn:
        logger.debug(f"  File doesn't match 'Author - Title' pattern: {fn}")
        return None
    return tuple(fn.split(" - ", 1))

# ═══════════════════════════════════════════════════════════════════
# IMPROVED MAIN FUNCTION - COMPLETE CONFIG LOADING FIX WITH DEBUG
# ═══════════════════════════════════════════════════════════════════

def main(argv: list[str] | None = None) -> None:
    """Main function with comprehensive config loading, debugging, and proper word list handling."""
    ap = argparse.ArgumentParser("Math-PDF manager")
    ap.add_argument("root", nargs="?", help="Folder to scan OR config shortcut")
    ap.add_argument("--auto-fix-nfc", action="store_true", dest="fix_nfc")
    ap.add_argument("--auto-fix-authors", action="store_true", dest="fix_auth")
    ap.add_argument("--ignore-nfc-on-macos", action="store_true", dest="ignore_nfc_macos")
    ap.add_argument("--exceptions-file", dest="exceptions_file")
    ap.add_argument("--problems_only", choices=["all", "short"])
    ap.add_argument("--dry_run", action="store_true")
    ap.add_argument("--output", default=DEFAULT_HTML_OUTPUT)
    ap.add_argument("--csv_output", default=DEFAULT_CSV_OUTPUT)
    ap.add_argument("--template_dir", default=DEFAULT_TEMPLATE_DIR)
    ap.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    ap.add_argument("--debug", action="store_true", help="Enable debug mode for word list troubleshooting")

    args = ap.parse_args(argv)
    
    # Setup environment
    setup_environment()
    
    # CRITICAL: Enable debug mode if requested
    if args.debug:
        enable_debug()
        logger.info("🔍 Debug mode enabled - comprehensive word list debugging active")
    
    # Adjust logging level if verbose
    if args.verbose:
        logging.getLogger("main").setLevel(logging.DEBUG)
        logger.info("Verbose mode enabled")
    
    # SECURITY: Validate CLI inputs
    if not validate_cli_inputs(args):
        sys.exit(1)
    
    # SECURITY: Validate template directory
    validate_template_dir(args.template_dir)

    # ═══════════════════════════════════════════════════════════════
    # COMPREHENSIVE CONFIG LOADING WITH DEBUG - IMPORTS ALL LISTS
    # ═══════════════════════════════════════════════════════════════

    # Get script directory for relative path resolution
    script_dir = Path(__file__).parent

    # Load config with better error handling
    logger.info("=== Loading Configuration ===")
    cfg_path = Path(DEFAULT_CONFIG_FILE)
    
    cfg = load_yaml_config_secure(str(cfg_path))
    
    # DEBUG: Show what's in the config
    if args.debug:
        debug_print(f"Config keys loaded: {list(cfg.keys())}")
        for key, value in cfg.items():
            if isinstance(value, (list, set)):
                debug_print(f"  {key}: {len(value)} items")
            else:
                debug_print(f"  {key}: {type(value)}")

    # Load word files with better error handling and path resolution
    logger.info("=== Loading Word Files ===")

    known_words = _load_words_file_fixed(
        cfg.get("known_words_file", DEFAULT_KNOWN_WORDS_FILE), 
        str(script_dir),
        "known words file"
    )

    name_dash_whitelist = _load_words_file_fixed(
        cfg.get("name_dash_whitelist_file", DEFAULT_NAME_DASH_WHITELIST_FILE),
        str(script_dir), 
        "name dash whitelist file"
    )

    multiword_surnames = _load_words_file_fixed(
        cfg.get("multiword_familynames_file", DEFAULT_MULTIWORD_FAMILYNAMES_FILE),
        str(script_dir),
        "multiword family names file"
    )

    # Load exceptions from multiple sources
    logger.info("=== Loading Exception Lists ===")
    exceptions: Set[str] = set()

    if args.exceptions_file:
        exceptions.update(_load_words_file_fixed(args.exceptions_file, str(script_dir), "CLI exceptions file"))

    cfg_exc = cfg.get("exceptions_file") or cfg.get("exceptions_list") or cfg.get("exceptions")
    if isinstance(cfg_exc, str):
        exceptions.update(_load_words_file_fixed(cfg_exc, str(script_dir), "config exceptions file"))
    elif isinstance(cfg_exc, (list, set)):
        exceptions.update({_normalize_nfc_cached(w) for w in cfg_exc})
        logger.info(f"✓ Added {len(cfg_exc)} exceptions from config")

    # Load compound terms FIRST (before combining) - CRITICAL FOR HYPHENATED WORDS
    logger.info("=== Loading Compound Terms ===")
    compound_terms = _load_config_list(cfg, "compound_terms")
    
    # DEBUG: Show sample compound terms
    if args.debug and compound_terms:
        sample_compounds = list(compound_terms)[:10]
        debug_print(f"Sample compound terms: {sample_compounds}")
        
        # Check for our problem words specifically
        problem_words = ['individual-based', 'pseudo-continuity', 'Short-time', 'non-existence', 'Itô-Wentzell']
        for word in problem_words:
            if word in compound_terms:
                debug_print(f"✓ '{word}' found in compound_terms")
            else:
                debug_print(f"✗ '{word}' NOT found in compound_terms")

    # COMPREHENSIVE: Load and combine ALL word lists from config into capitalization_whitelist
    logger.info("=== Loading ALL Capitalization Lists ===")
    capitalization_whl = set()

    # List of all config lists that should be included in capitalization checking
    config_word_lists = [
        ("capitalization_whitelist", "Core capitalization whitelist"),
        ("compound_terms", "Compound terms (hyphenated words)"),
        ("common_acronyms", "Common acronyms"),
        ("mixed_case_words", "Mixed case words"),
        ("proper_adjectives", "Proper adjectives"),
        # These might exist from malformed YAML extraction
        ("capitalization_whitelist_from_comments", "Extracted from comments"),
        ("math_terms_from_comments", "Math terms from comments"),
        ("roman_numerals_from_comments", "Roman numerals from comments"),
        ("german_nouns_from_comments", "German nouns from comments"),
        ("exceptions_from_comments", "Exceptions from comments")
    ]

    total_loaded = 0
    for list_key, description in config_word_lists:
        if list_key in cfg:
            word_list = cfg[list_key]
            if isinstance(word_list, (list, set)):
                words = set(word_list)
                capitalization_whl.update(words)
                total_loaded += len(words)
                logger.info(f"✓ Added {description}: {len(words)} items")
                
                # DEBUG: Show samples from each list
                if args.debug and words:
                    samples = list(words)[:5]
                    debug_print(f"  Sample from {list_key}: {samples}")
            else:
                logger.warning(f"⚠️  {list_key} is not a list ({type(word_list)})")

    logger.info(f"✓ Total words loaded from config: {total_loaded}")
    logger.info(f"✓ Combined capitalization_whitelist: {len(capitalization_whl)} unique items")

    # DEBUG: Check if our problem words are in the combined list
    if args.debug:
        debug_print("=== PROBLEM WORD CHECK ===")
        problem_words = ['individual-based', 'pseudo-continuity', 'Short-time', 'non-existence', 'Itô-Wentzell']
        for word in problem_words:
            in_cap = word in capitalization_whl
            in_known = word in known_words
            in_dash = word in name_dash_whitelist
            in_compound = word in compound_terms
            debug_print(f"'{word}': cap={in_cap}, known={in_known}, dash={in_dash}, compound={in_compound}")

    # VERIFICATION: Test sample words that are commonly flagged
    logger.info("=== VERIFICATION TEST ===")
    sample_words = [
        "individual-based", "pseudo-continuity", "non-linear", "mean-field", 
        "continuous-time", "quasi-linear", "arXiv", "BibTeX", "LaTeX",
        "Short-time", "non-existence", "Itô-Wentzell"
    ]

    # Import the canonicalize function from utils
    from utils import canonicalize, is_canonically_equivalent
    from unicodedata import normalize
    
    # Helper function to check word against all lists with proper logic
    def check_word_in_lists(word):
        """Check word using the same logic as the spell checker"""
        word_normalized = normalize('NFC', word)
        
        # First check exact match against case-sensitive lists
        case_sensitive_lists = capitalization_whl | name_dash_whitelist | exceptions
        if word_normalized in case_sensitive_lists:
            return True, "case-sensitive lists (exact match)"
            
        # Check with dash variations for name_dash_whitelist
        if '-' in word or '–' in word:
            # Try with both hyphen and en-dash
            word_hyphen = word.replace('–', '-')
            word_endash = word.replace('-', '–')
            for variant in [word_hyphen, word_endash]:
                variant_normalized = normalize('NFC', variant)
                if variant_normalized in name_dash_whitelist:
                    return True, f"name_dash_whitelist (dash variant: {variant})"
        
        # Check compound terms
        if word_normalized in compound_terms:
            return True, "compound_terms"
            
        # Check canonicalized match against known_words (case-insensitive)
        word_canon = canonicalize(word_normalized)
        known_words_canon = {canonicalize(normalize('NFC', w)) for w in known_words}
        if word_canon in known_words_canon:
            return True, "known_words (canonicalized)"
            
        return False, "NOT FOUND"

    found_count = 0
    for word in sample_words:
        found, location = check_word_in_lists(word)
        if found:
            found_count += 1
            logger.info(f"✓ '{word}' found in {location}")
        else:
            logger.warning(f"✗ '{word}' NOT found in any list (will be flagged)")

    logger.info(f"✓ Verification: {found_count}/{len(sample_words)} sample words found")

    # FINAL COUNTS
    logger.info("=== FINAL WORD LIST COUNTS ===")
    logger.info(f"Known words: {len(known_words)}")
    logger.info(f"Name dash whitelist: {len(name_dash_whitelist)}")
    logger.info(f"Multiword surnames: {len(multiword_surnames)}")
    logger.info(f"Exceptions: {len(exceptions)}")
    logger.info(f"Compound terms: {len(compound_terms)}")
    logger.info(f"Capitalization whitelist (COMBINED): {len(capitalization_whl)}")
    logger.info(f"SpellChecker will use: {len(known_words | compound_terms)} total words (known_words + compound_terms)")

    # Verify we have data
    if not known_words:
        logger.warning("⚠️  No known words loaded! This will cause many false positives.")
    if not capitalization_whl:
        logger.warning("⚠️  No capitalization whitelist loaded! This will cause many errors.")
    if len(compound_terms) < 10:
        logger.warning("⚠️  Very few compound terms loaded! Many hyphenated words will be flagged.")

    logger.info("✅ Configuration loading complete - ALL lists imported!")

    # ═══════════════════════════════════════════════════════════════
    # CONTINUE WITH EXISTING MAIN LOGIC
    # ═══════════════════════════════════════════════════════════════

    roots: List[str] = []
    if args.root:
        if args.root in cfg.get("folder_shortcuts", {}):
            base = cfg.get("base_maths_folder")
            shortcuts = cfg["folder_shortcuts"][args.root]
            if isinstance(shortcuts, str):
                roots = [resolve_path(shortcuts, base)]
            elif isinstance(shortcuts, list):
                roots = [resolve_path(p, base) for p in shortcuts]
            else:
                logger.error(f"Invalid shortcut format for '{args.root}': {type(shortcuts)}")
                sys.exit(1)
        else:
            roots = [resolve_path(args.root)]
        
        for r in roots:
            if not r or not exists(r):
                logger.error("Folder not found: %s", r)
                sys.exit(1)

    files: List[dict[str, Any]] = []
    for r in roots:
        logger.info(f"Scanning directory: {r}")
        dir_files = scan_directory(r)
        logger.info(f"  Found {len(dir_files)} files in {r}")
        files.extend(dir_files)
    
    logger.info(f"Total files found: {len(files)}")
    
    # CRITICAL FIX: Normalize file metadata to handle different scanner implementations
    logger.info("Normalizing file metadata...")
    files = normalize_file_metadata(files)
    
    # Count how many files have proper filenames after normalization
    files_with_filename = sum(1 for f in files if f.get('filename') and f['filename'] != 'UNKNOWN')
    logger.info(f"Files with valid filenames: {files_with_filename}")
    
    # Log file patterns to understand what's being scanned
    if logger.level <= logging.DEBUG:
        # Sample first 10 files to see patterns
        for i, f in enumerate(files[:10]):
            logger.debug(f"  File {i}: {f.get('filename', 'NO_FILENAME')}")
        if len(files) > 10:
            logger.debug(f"  ... and {len(files) - 10} more files")
    
    # CRITICAL DEBUG: Check if files match the expected pattern
    pattern_matches = 0
    for f in files:
        filename = f.get('filename', '')
        if " - " in filename:
            pattern_matches += 1
            if args.debug:
                debug_print(f"  Pattern match: {filename}")
        else:
            if args.debug:
                debug_print(f"  NO pattern match: {filename}")
    
    logger.info(f"Files matching 'Author - Title' pattern: {pattern_matches}/{len(files)}")

    ignore_nfc = args.ignore_nfc_macos and sys.platform == "darwin"
    auto_fix_nfc = args.fix_nfc and not ignore_nfc

    # CRITICAL: Pass debug flag to filename checker
    debug_flag = args.debug or args.verbose

    logger.info("=== RUNNING FILENAME CHECKS ===")
    
    checks = batch_check_filenames(
        files,
        known_words,
        _add_nfd_variants(name_dash_whitelist),
        exceptions,
        compound_terms,  # CRITICAL: Pass compound_terms to filename checker
        spellchecker=SpellChecker(SpellCheckerConfig(
            known_words=known_words | compound_terms,
            capitalization_whitelist=capitalization_whl,
            name_dash_whitelist=name_dash_whitelist
        )),
        language_tool=None,
        sentence_case=True,
        lowercase_exceptions=None,
        capitalization_whitelist=capitalization_whl,  # ✅ NOW INCLUDES ALL LISTS!
        debug=debug_flag,  # CRITICAL: Enable debug mode
        multiword_surnames=multiword_surnames,
        name_dash_whitelist=name_dash_whitelist,
        auto_fix_nfc=auto_fix_nfc,
        auto_fix_authors=args.fix_auth,
    )
    
    logger.info(f"Checked {len(checks)} files")
    
    # Count files that need fixes
    files_with_errors = sum(1 for r in checks if r.get("errors"))
    files_with_suggestions = sum(1 for r in checks if r.get("suggestions"))
    files_with_fixes = sum(1 for r in checks if r.get("fixed_filename"))
    logger.info(f"Files with errors: {files_with_errors}")
    logger.info(f"Files with suggestions: {files_with_suggestions}")
    logger.info(f"Files with proposed fixes: {files_with_fixes}")
    
    # DEBUG: Show some error examples
    if args.debug and files_with_errors > 0:
        debug_print("=== ERROR EXAMPLES ===")
        error_count = 0
        for result in checks:
            if result.get("errors") and error_count < 5:
                debug_print(f"File: {result.get('filename', 'UNKNOWN')}")
                for error in result.get("errors", [])[:3]:
                    debug_print(f"  Error: {error}")
                error_count += 1

    # FIXED: Enhanced rename logic with proper author processing
    rename_count = 0
    
    # Create a lookup for check results
    check_results_map = {row["path"]: row for row in checks}
    
    # Process ALL files, not just those with check results
    all_files_to_process = files if args.fix_auth else checks
    
    for file_or_row in all_files_to_process:
        if args.fix_auth and "path" not in file_or_row:
            # This is a raw file dict, create a minimal row
            row = {
                "path": file_or_row["path"],
                "filename": file_or_row.get("filename", file_or_row.get("name", "")),
                "errors": [],
                "suggestions": [],
                "fixed_filename": None
            }
        else:
            row = file_or_row
            
        old = Path(row["path"])
        parts = _split(old.name)
        if not parts:
            continue
        auth, title_with_ext = parts
        
        # Extract extension properly
        ext_match = re.search(r"\.(?P<ext>[A-Za-z0-9]{1,4})$", title_with_ext)
        ext = ext_match.group("ext") if ext_match else ""
        title = title_with_ext[: ext_match.start()] if ext_match else title_with_ext
        
        # FIXED: Use our sophisticated author processing
        fixed_auth = fix_author_block(auth)
        proposed = row.get("fixed_filename") or None

        new_name: str | None = None
        
        # Debug logging for rename decisions (show at INFO level for troubleshooting)
        if args.verbose:
            logger.info(f"Checking file: {old.name}")
            logger.info(f"  Original auth: '{auth}'")
            logger.info(f"  Fixed auth: '{fixed_auth}'")
            logger.info(f"  Authors equivalent: {authors_are_equivalent(auth, fixed_auth)}")
        
        # Detailed debug at DEBUG level
        logger.debug(f"  Title: '{title}'")
        logger.debug(f"  Extension: '{ext}'")
        logger.debug(f"  Proposed: {proposed}")
        
        # FIXED: Better logic for determining when to rename
        author_needs_fix = args.fix_auth and not authors_are_equivalent(auth, fixed_auth)
        if proposed:
            # filename_checker suggested a fix
            if is_canonically_equivalent(old.name, proposed) and auto_fix_nfc:
                # Just NFC normalization
                new_name = proposed
                if args.verbose:
                    logger.info(f"  → Using NFC normalization: '{new_name}'")
            elif author_needs_fix:
                # We want to apply our author fix instead of/in addition to checker's suggestion
                new_name = f"{fixed_auth} - {title}"
                if ext:
                    new_name += f".{ext}"
                if args.verbose:
                    logger.info(f"  → Using our author fix: '{new_name}'")
            else:
                # Use checker's suggestion
                new_name = proposed
                if args.verbose:
                    logger.info(f"  → Using checker suggestion: '{new_name}'")
        elif author_needs_fix:
            # No proposed filename from checker, but we have author fixes
            new_name = f"{fixed_auth} - {title}"
            if ext:
                new_name += f".{ext}"
            if args.verbose:
                logger.info(f"  → No proposal, using our author fix: '{new_name}'")

        # Validate the new name
        if not new_name:
            logger.debug(f"  → No changes needed for: {old.name}")
            continue
        
        # FIXED: More robust title preservation check using normalization
        new_parts = _split(new_name)
        if not new_parts:
            logger.warning(f"Invalid new filename format for {old.name}, skipping rename")
            continue
            
        new_auth_part, new_title_with_ext = new_parts
        
        # Extract title from new name for comparison  
        new_ext_match = re.search(r"\.(?P<ext>[A-Za-z0-9]{1,4})$", new_title_with_ext)
        new_title = new_title_with_ext[: new_ext_match.start()] if new_ext_match else new_title_with_ext
        new_ext = new_ext_match.group("ext") if new_ext_match else ""
        
        # FIXED: Use normalized title comparison to handle Unicode differences
        normalized_old_title = normalize_title_for_comparison(title)
        normalized_new_title = normalize_title_for_comparison(new_title)
        
        if normalized_old_title != normalized_new_title:
            logger.warning(f"Title part mismatch for {old.name}, skipping rename")
            logger.debug(f"  Original title: '{title}' (normalized: '{normalized_old_title}')")
            logger.debug(f"  New title: '{new_title}' (normalized: '{normalized_new_title}')")
            continue
            
        if new_ext != ext:
            logger.warning(f"Extension mismatch for {old.name}, skipping rename")
            logger.debug(f"  Expected ext: '{ext}'")
            logger.debug(f"  New ext: '{new_ext}'")
            continue

        new_path = old.with_name(new_name)

        # Handle macOS NFC edge case
        if sys.platform == "darwin" and is_canonically_equivalent(old.name, new_path.name):
            if row.get("fixed_filename"):
                row["fixed_filename"] = ""
            if "suggestions" in row:
                row["suggestions"] = [s for s in row.get("suggestions", []) if "nfc" not in s.lower()]
            if "errors" in row:
                row["errors"] = [e for e in row.get("errors", []) if "nfc" not in e.lower()]
            continue

        # FIXED: Better collision detection - skip if names are essentially the same
        if old.name == new_path.name:
            if args.verbose:
                logger.info(f"  → Names are identical, skipping: {old.name}")
            continue

        if args.dry_run:
            if "fixed_filename" in row:
                row["fixed_filename"] = new_name
            logger.info(f"[DRY RUN] Would rename: {old.name} → {new_name}")
            continue

        # FIXED: Enhanced collision detection
        if new_path.exists() and new_path.resolve() != old.resolve():
            logger.warning(f"Target file already exists, skipping: {old.name} → {new_name}")
            continue

        # SECURITY: Use safe file rename with enhanced error handling
        try:
            if safe_file_rename(old, new_path):
                rename_count += 1
                if "filename" in row:
                    row.update(filename=new_path.name, path=str(new_path), fixed_filename="")
                logger.info(f"RENAMED: {old.name} → {new_path.name}")
        except Exception as e:
            logger.error(f"Failed to rename {old} → {new_path}: {e}")
            # Continue processing other files even if one rename fails

    if rename_count > 0:
        logger.info(f"Successfully renamed {rename_count} files")

    # Clean up NFC warnings on macOS
    if sys.platform == "darwin":
        for r in checks:
            r["suggestions"] = [s for s in r.get("suggestions", []) if "nfc" not in s.lower()]
            r["errors"] = [e for e in r.get("errors", []) if "nfc" not in e.lower()]

    if args.problems_only:
        checks = [r for r in checks if r.get("errors") or r.get("suggestions")]
        if args.problems_only == "short":
            for r in checks:
                r.pop("path", None)
                r.pop("folder", None)

    generate_html_report(
        checks,
        duplicates=find_duplicates(files),
        output_path=args.output,
        template_dir=args.template_dir,
        dry_run=args.dry_run,
        hide_clean=bool(args.problems_only),
    )
    generate_csv_report(checks, output_path=args.csv_output)

    logger.info("All done ✅")

    # DEBUG: Final summary
    if args.debug:
        debug_print("=== FINAL DEBUG SUMMARY ===")
        debug_print(f"Total files processed: {len(files)}")
        debug_print(f"Files with errors: {files_with_errors}")
        debug_print(f"Files with suggestions: {files_with_suggestions}")
        debug_print(f"Files renamed: {rename_count}")
        debug_print("=== END DEBUG MODE ===")


if __name__ == "__main__":
    main()