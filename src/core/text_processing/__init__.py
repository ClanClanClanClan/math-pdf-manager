"""
Core Text Processing Module
Consolidated text processing utilities for the academic papers system.
"""

from .normalizer import TextNormalizer, normalize, canonicalize, clean_text as normalize_clean_text
from .unicode_utils import UnicodeProcessor, normalize_unicode, detect_homoglyphs, sanitize_filename, is_safe_unicode
from .tokenizer import TextTokenizer, tokenize, extract_words, extract_academic_tokens
from .cleaner import TextCleaner, clean_text, clean_academic_text, clean_filename

__all__ = [
    # Classes
    'TextNormalizer',
    'UnicodeProcessor', 
    'TextTokenizer',
    'TextCleaner',
    
    # Convenience functions
    'normalize',
    'canonicalize',
    'normalize_clean_text',
    'normalize_unicode',
    'detect_homoglyphs',
    'sanitize_filename',
    'is_safe_unicode',
    'tokenize',
    'extract_words',
    'extract_academic_tokens',
    'clean_text',
    'clean_academic_text',
    'clean_filename'
]