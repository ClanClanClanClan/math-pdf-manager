#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/sentence_case.py - Academic Title Sentence Case Conversion
Extracted from utils.py to improve modularity

This module handles the complex logic for converting academic titles to proper sentence case
while preserving technical terms, mathematical expressions, and proper nouns.
"""

import os
from typing import Iterable, Tuple, Set, Optional, Dict
import regex as re

from .io import load_yaml_config, debug_print
from .math_tokenization import robust_tokenize_with_math, DASH_CHARS

# Constants for sentence case processing
MATH_TECHNICAL_PREFIXES = {
    # Lowercase Latin letters often used as technical prefixes
    "g", "h", "l", "f", "c", "k", "p", "q", "r", "s", "t", "w", "v", "u", "x", "y", "z",
    "l^2", "l^p", "c_0", "l_infty", "l^infty", "h-process", "g-expectation", "c_0-sequence",
    # Lowercase Greek technical terms (Unicode)
    "α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π", "ρ",
    "σ", "τ", "υ", "φ", "χ", "ψ", "ω",
    # Common single Greek letter prefixes for chemistry/biology
    "α-synuclein", "ω-automata"
}

# Number to word conversion for sentence starts
NUMBERS = {
    '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', 
    '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', 
    '10': 'ten', '11': 'eleven', '12': 'twelve', '13': 'thirteen', 
    '14': 'fourteen', '15': 'fifteen', '16': 'sixteen', '17': 'seventeen', 
    '18': 'eighteen', '19': 'nineteen', '20': 'twenty'
}

# Module-level config cache
_CONFIG_CACHE = {}

# Debug mode flag
DEBUG_SENTENCE_CASE = False


def _load_sentence_case_config() -> Dict:
    """Load configuration for sentence case conversion"""
    global _CONFIG_CACHE
    
    if _CONFIG_CACHE:
        return _CONFIG_CACHE
    
    # Try to load from config.yaml in known locations
    config_paths = [
        "config/config.yaml",
        "config.yaml",
        "Scripts/config.yaml",
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.yaml"),
        os.path.join(os.path.dirname(__file__), "config.yaml"),
    ]
    
    config_data = {}
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                config_data = load_yaml_config(config_path)
                debug_print(f"Loaded config from: {config_path}")
                break
            except Exception as e:
                debug_print(f"Failed to load config from {config_path}: {e}")
                continue
    
    if not config_data:
        debug_print("No config file found, using minimal defaults")
    
    # Initialize with config data or minimal defaults
    _CONFIG_CACHE = {
        'common_acronyms': frozenset(config_data.get('common_acronyms', [])),
        'mixed_case_words': frozenset(config_data.get('mixed_case_words', [
            'LaTeX', 'macOS', 'iOS', 'iPhone', 'iPad', 'iPod', 'eBay', 
            'PyTorch', 'TensorFlow', 'JavaScript', 'TypeScript', 'CoffeeScript', 
            'XeLaTeX', 'LuaTeX', 'ConTeXt', 'BibTeX', 'PostScript', 'FaceTime', 
            'GitHub', 'GitLab', 'LinkedIn', 'YouTube'
        ])),
        'compound_terms': frozenset(config_data.get('compound_terms', [])),
        'proper_adjectives': frozenset(config_data.get('proper_adjectives', [
            'Bayesian', 'Gaussian', 'Markovian', 'Newtonian', 'Euclidean', 'Laplacian'
        ])),
        'capitalization_whitelist': frozenset(
            config_data.get('capitalization_whitelist', [])
            or config_data.get('exceptions', {}).get('capitalization_whitelist', [])
        ),
        'name_dash_whitelist': frozenset(),  # Will be loaded from file if specified
        'known_words': frozenset(),  # Will be loaded from file if specified
    }
    
    # Load name_dash_whitelist from data file
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    dash_whitelist_paths = [
        "data/name_dash_whitelist.txt",
        os.path.join(data_dir, "name_dash_whitelist.txt"),
    ]
    for path in dash_whitelist_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    names = frozenset(
                        line.strip() for line in fh
                        if line.strip() and not line.startswith("#")
                    )
                _CONFIG_CACHE['name_dash_whitelist'] = names
                debug_print(f"Loaded {len(names)} name-dash whitelist entries from {path}")
            except Exception:
                pass
            break

    # Add math technical prefixes to the config
    _CONFIG_CACHE['math_technical_prefixes'] = MATH_TECHNICAL_PREFIXES

    debug_print(f"Loaded config: {len(_CONFIG_CACHE)} sections")
    return _CONFIG_CACHE


def extract_title_words(title: str) -> Set[str]:
    """Extract all words from title for filtering whitelist terms."""
    words = set()
    
    # Extract individual words (letters, numbers, apostrophes)
    for match in re.finditer(r"\b\w+(?:[''][a-zA-Z]+)?\b", title, re.U):
        full = match.group().lower()
        words.add(full)
        # Also add the base word without possessive suffix so that
        # whitelist terms like "Euler" match title words like "Euler's"
        for poss in ("\u2019s", "'s"):
            if full.endswith(poss):
                words.add(full[:-2])
                break
    
    # Extract compound terms with dashes
    for match in re.finditer(rf"\b\w+(?:[{DASH_CHARS}]\w+)+\b", title, re.U):
        compound = match.group().lower()
        words.add(compound)
        # Also add normalized versions
        words.add(compound.replace('–', '-').replace('—', '-').replace('−', '-'))
    
    # Extract space-separated phrases (up to 3 words)
    # First extract all word positions
    word_matches = list(re.finditer(r"\b\w+\b", title, re.U))
    
    # Extract 2-word phrases
    for i in range(len(word_matches) - 1):
        phrase = f"{word_matches[i].group()} {word_matches[i+1].group()}".lower()
        words.add(phrase)
    
    # Extract 3-word phrases
    for i in range(len(word_matches) - 2):
        phrase = f"{word_matches[i].group()} {word_matches[i+1].group()} {word_matches[i+2].group()}".lower()
        words.add(phrase)
    
    debug_print(f"Extracted {len(words)} words from title")
    return words


def filter_relevant_whitelist_terms(
    title: str,
    capitalization_whitelist: Optional[Iterable[str]] = None,
    name_dash_whitelist: Optional[Iterable[str]] = None,
    technical_prefix_whitelist: Optional[Iterable[str]] = None,
) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Filter whitelist terms to only include those relevant to the title.
    This optimization significantly improves performance for large whitelists.
    """
    debug_print(f"Filtering whitelist terms for title: '{title}'")
    
    # Extract all possible words and phrases from the title
    title_words = extract_title_words(title)
    
    # Filter capitalization whitelist
    filtered_cap = set()
    for term in capitalization_whitelist or []:
        term_lower = term.lower()
        debug_print(f"  Checking cap term: '{term}' -> '{term_lower}'")
        if term_lower in title_words:
            debug_print("      -> relevant (exact match)")
            filtered_cap.add(term)
        # Match with dash normalization
        normalized = term_lower.replace('–', '-').replace('—', '-').replace('−', '-')
        if normalized in title_words:
            debug_print("      -> relevant (normalized dash match)")
            filtered_cap.add(term)
        # Match individual words in compound terms
        if any(dash in term_lower for dash in ['-', '–', '—', '−']):
            parts = re.split(rf'[{DASH_CHARS}]+', term_lower)
            if all(part in title_words for part in parts if part):
                debug_print("      -> relevant (compound word parts match)")
                filtered_cap.add(term)
        # Match space-separated terms
        if ' ' in term_lower:
            if term_lower in title_words:
                debug_print("      -> relevant (space-separated match)")
                filtered_cap.add(term)
    
    # Filter name dash whitelist
    filtered_dash = set()
    for term in name_dash_whitelist or []:
        term_lower = term.lower()
        if term_lower in title_words:
            filtered_dash.add(term)
        # Match with dash normalization
        normalized = term_lower.replace('–', '-').replace('—', '-').replace('−', '-')
        if normalized in title_words:
            filtered_dash.add(term)
    
    # Filter technical prefix whitelist
    filtered_tech = set()
    for term in technical_prefix_whitelist or []:
        term_lower = term.lower()
        if term_lower in title_words:
            filtered_tech.add(term)
        # Check if title starts with this technical prefix
        if title.lower().startswith(term_lower):
            filtered_tech.add(term)
    
    debug_print(f"    filtered_cap: {len(filtered_cap)} terms")
    debug_print(f"    filtered_dash: {len(filtered_dash)} terms")
    debug_print(f"    filtered_tech: {len(filtered_tech)} terms")
    
    return filtered_cap, filtered_dash, filtered_tech


def to_sentence_case_academic(
    title: str,
    capitalization_whitelist: Optional[Iterable[str]] = None,
    name_dash_whitelist: Optional[Iterable[str]] = None,
    known_words: Optional[Iterable[str]] = None,
    technical_prefix_whitelist: Optional[Iterable[str]] = None,
    debug: bool = False,
) -> Tuple[str, bool]:
    """
    Convert title to academic sentence case.
    
    Rules:
    - First word is capitalized (unless technical prefix)
    - All other words are lowercase except:
      - Whitelisted terms (preserved exactly)
      - Short acronyms (2-4 letters, all caps)
      - Mixed-case brands (iPhone, eBay)
      - Proper adjectives (Bayesian, Gaussian, etc.)
    - Technical prefixes like "g-expectation" stay lowercase even when first
    - Context-aware contractions: "It's" stays as pronoun, not "IT" acronym
    
    Performance optimization: Automatically filters whitelists to only relevant terms.
    """
    global DEBUG_SENTENCE_CASE
    old_debug = DEBUG_SENTENCE_CASE
    if debug:
        DEBUG_SENTENCE_CASE = True
    
    try:
        debug_print("=== to_sentence_case_academic ===")
        debug_print(f"Input title: '{title}'")
        
        if not title or not title.strip():
            debug_print("Empty title, returning 'X'")
            return "X", True
        
        
        # Load configuration
        config = _load_sentence_case_config()
        
        # Use provided whitelists or fall back to config
        cap_whitelist = set(capitalization_whitelist or config.get('capitalization_whitelist', []))
        dash_whitelist = set(name_dash_whitelist or config.get('name_dash_whitelist', []))
        tech_whitelist = set(technical_prefix_whitelist or config.get('math_technical_prefixes', []))
        
        # Filter whitelists to only relevant terms (performance optimization)
        filtered_cap, filtered_dash, filtered_tech = filter_relevant_whitelist_terms(
            title, cap_whitelist, dash_whitelist, tech_whitelist
        )
        
        # Tokenize with math protection
        tokens = robust_tokenize_with_math(title, filtered_cap | filtered_dash)
        
        # Check for edge cases after tokenization
        word_tokens = [token for token in tokens if token.kind == 'WORD']
        
        # If no word tokens, handle special cases
        if not word_tokens:
            # Check if it's punctuation only
            punct_tokens = [token for token in tokens if token.kind == 'PUNCT']
            if punct_tokens:
                # Punctuation only gets X prefix
                result = "X " + ''.join(token.value for token in tokens)
                return result, True
            else:
                # No words or punctuation, return X
                return "X", True
        
        # Handle emoji/punctuation stripping at the beginning
        # If title starts with emoji/punctuation followed by words, strip leading punctuation
        if (len(tokens) > 0 and tokens[0].kind == 'PUNCT' and 
            any(token.kind == 'WORD' for token in tokens)):
            # Check if first punctuation token is emoji-like (non-ASCII punctuation)
            first_punct = tokens[0].value
            if ord(first_punct[0]) > 127:  # Non-ASCII character (likely emoji)
                # Strip leading emoji and spaces
                new_tokens = []
                skip_leading = True
                for token in tokens:
                    if skip_leading and token.kind in ['PUNCT', 'SPACE']:
                        continue
                    else:
                        skip_leading = False
                        new_tokens.append(token)
                tokens = new_tokens
        
        # Convert to sentence case
        result_parts = []
        changed = False
        
        for i, token in enumerate(tokens):
            if token.kind == 'MATH':
                # Preserve math exactly
                result_parts.append(token.value)
                continue
            elif token.kind == 'PHRASE':
                # Check if phrase has whitelist match
                phrase = token.value
                exact_match = None
                matched_via_dash_norm = False
                for term in filtered_cap | filtered_dash:
                    if phrase.lower() == term.lower():
                        exact_match = term
                        break
                    # Check with dash normalization
                    phrase_normalized = phrase.replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-')
                    term_normalized = term.replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-')
                    if phrase_normalized.lower() == term_normalized.lower():
                        exact_match = term
                        matched_via_dash_norm = True
                        break

                if exact_match:
                    if matched_via_dash_norm:
                        # Apply the whitelist's EXACT form: both the
                        # capitalisation AND the dash characters.  The
                        # whitelist is authoritative — if it says en-dash,
                        # the output uses en-dash regardless of the input.
                        out_chars = []
                        ti = 0  # index into exact_match (whitelist term)
                        for pc in phrase:
                            if pc in '-\u2013\u2014\u2212':
                                # Use the dash character from the WHITELIST
                                while ti < len(exact_match) and exact_match[ti] not in '-\u2013\u2014\u2212':
                                    ti += 1
                                if ti < len(exact_match):
                                    out_chars.append(exact_match[ti])
                                    ti += 1
                                else:
                                    out_chars.append(pc)
                            else:
                                if ti < len(exact_match):
                                    # Apply case from whitelist term
                                    wc = exact_match[ti]
                                    if wc.isupper():
                                        out_chars.append(pc.upper())
                                    elif wc.islower():
                                        out_chars.append(pc.lower())
                                    else:
                                        out_chars.append(pc)
                                    ti += 1
                                else:
                                    out_chars.append(pc)
                        replacement = ''.join(out_chars)
                    else:
                        replacement = exact_match
                    result_parts.append(replacement)
                    if phrase != replacement:
                        changed = True
                else:
                    # No whitelist match, preserve exactly
                    result_parts.append(phrase)
                continue
            elif token.kind == 'WORD':
                # Process regular words
                word = token.value
                
                # Check if it's a technical prefix (should stay lowercase even if first)
                if word.lower() in filtered_tech:
                    result_parts.append(word.lower())
                    if word != word.lower():
                        changed = True
                    continue
                
                # Strip possessive suffix for whitelist comparison
                # e.g. "Euler's" → base "Euler", suffix "'s"
                possessive_suffix = ""
                word_base = word
                for poss in ("\u2019s", "'s"):  # curly then straight apostrophe
                    if word.endswith(poss):
                        possessive_suffix = word[-2:]
                        word_base = word[:-2]
                        break

                # Check exact whitelist matches (using base form for possessives)
                exact_match = None
                for term in filtered_cap | filtered_dash:
                    if word_base.lower() == term.lower():
                        exact_match = term
                        break

                if exact_match:
                    result_parts.append(exact_match + possessive_suffix)
                    if word != exact_match + possessive_suffix:
                        changed = True
                    continue
                
                # Check if it's a known acronym (check before sentence start to preserve acronyms)
                if word in config.get('common_acronyms', []):
                    result_parts.append(word)
                    continue
                
                # Check if it's a likely acronym (2-3 letters, all caps, not pronouns or common words)
                # For possessives, check the base word without apostrophe
                base_word = word.split("'")[0] if "'" in word else word
                if (2 <= len(base_word) <= 3 and base_word.isupper() and 
                    base_word not in ['IT', 'HE', 'SHE', 'WE', 'YOU', 'THE', 'AND', 'FOR', 'BUT', 'NOT', 'FOX', 'DOG', 'CAT', 'OF', 'TO', 'IN', 'ON', 'AT', 'BY', 'OR', 'SO', 'UP', 'IF', 'AS', 'MY', 'NO', 'GO', 'DO', 'BE', 'AM', 'IS', 'WAS', 'ARE']):
                    result_parts.append(word)
                    continue
                
                # Check if it's a mixed-case brand (before sentence start check)
                if word in config.get('mixed_case_words', []):
                    result_parts.append(word)
                    continue
                
                # Check if it's a proper adjective (before sentence start check)  
                proper_adjective_match = None
                for adj in config.get('proper_adjectives', []):
                    if word.lower() == adj.lower():
                        proper_adjective_match = adj
                        break
                        
                if proper_adjective_match:
                    result_parts.append(proper_adjective_match)
                    if word != proper_adjective_match:
                        changed = True
                    continue
                
                # Check if this is the start of a sentence (first word or after sentence-ending punctuation)
                # Also check for opening-quote context (quoted titles like: Corrigendum for "A probabilistic approach")
                _UNAMBIGUOUS_OPEN_QUOTES = {'\u201c', '\u00ab', '\u201e', '\u2018', '\u201a'}  # " « „ ' ‚
                _ALL_QUOTE_CHARS = _UNAMBIGUOUS_OPEN_QUOTES | {'"', "'"}
                is_sentence_start = False
                if i == 0:
                    # First word of the title
                    is_sentence_start = True
                elif i > 0:
                    # Check if we're after sentence-ending punctuation
                    for j in range(i - 1, -1, -1):
                        if tokens[j].kind == 'PUNCT':
                            if tokens[j].value in ['.', '!', '?', '…', ':']:
                                # Special case: check if this period is part of a section number
                                if tokens[j].value == '.':
                                    # Look for number before and after the period
                                    before_is_number = (j > 0 and tokens[j-1].kind == 'WORD' and
                                                       tokens[j-1].value.isdigit())
                                    after_is_number = (i < len(tokens) and tokens[i].kind == 'WORD' and
                                                      tokens[i].value.isdigit())
                                    if before_is_number and after_is_number:
                                        # This is likely a section number like "2.3", not a sentence end
                                        break
                                is_sentence_start = True
                                break
                        elif tokens[j].kind == 'WORD':
                            # Found a word before any punctuation, not sentence start
                            break

                # Opening-quote detection: if the word is immediately after an
                # opening quotation mark that begins a quoted title (≥3 words),
                # capitalise the first word.  Short quoted spans (1–2 words)
                # like the "big" problem or the "very big" problem are
                # scare-quotes / emphasis and stay lowercase.
                # Unambiguous Unicode openers (" « „ ' ‚) are always opening.
                # For ASCII " we use adjacency: preceded by space → opening.
                _QUOTED_TITLE_MIN_WORDS = 3
                _ANY_QUOTE = _ALL_QUOTE_CHARS | {
                    '\u201d', '\u00bb', '\u2019', '\u201f', '\u201b',
                }
                if not is_sentence_start and i > 0:
                    for j in range(i - 1, -1, -1):
                        if tokens[j].kind == 'SPACE':
                            continue
                        if tokens[j].kind == 'PUNCT' and tokens[j].value in _ALL_QUOTE_CHARS:
                            qchar = tokens[j].value
                            is_opening = False
                            if qchar in _UNAMBIGUOUS_OPEN_QUOTES:
                                is_opening = True
                            elif (j > 0 and tokens[j - 1].kind == 'SPACE') or j == 0:
                                # ASCII " or ' preceded by space → opening
                                is_opening = True
                            if is_opening:
                                # Count words until the matching closing quote.
                                # Only capitalise for quoted titles (≥3 words);
                                # shorter spans are scare-quotes / emphasis.
                                words_in_quote = 0
                                found_close = False
                                for k in range(i, len(tokens)):
                                    if tokens[k].kind == 'WORD':
                                        words_in_quote += 1
                                    elif (tokens[k].kind == 'PUNCT'
                                          and tokens[k].value in _ANY_QUOTE):
                                        found_close = True
                                        break
                                if found_close and words_in_quote >= _QUOTED_TITLE_MIN_WORDS:
                                    is_sentence_start = True
                        break  # Only check the immediately preceding non-space token
                
                if is_sentence_start and word.lower() not in filtered_tech:
                    # Check if it's a number that should be converted to word
                    if word in NUMBERS:
                        new_word = NUMBERS[word].capitalize()
                        result_parts.append(new_word)
                        if word != new_word:
                            changed = True
                        continue
                    else:
                        new_word = word.capitalize()
                        result_parts.append(new_word)
                        if word != new_word:
                            changed = True
                        continue
                
                # Default: lowercase
                new_word = word.lower()
                result_parts.append(new_word)
                if word != new_word:
                    changed = True
            else:
                # Preserve spaces and punctuation
                result_parts.append(token.value)
        
        result = ''.join(result_parts)
        
        debug_print(f"Result: '{result}' (changed: {changed})")
        return result, changed
        
    finally:
        DEBUG_SENTENCE_CASE = old_debug


# Export all functions
__all__ = [
    'to_sentence_case_academic',
    'extract_title_words',
    'filter_relevant_whitelist_terms',
    'DEBUG_SENTENCE_CASE',
    'MATH_TECHNICAL_PREFIXES'
]