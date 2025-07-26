#!/usr/bin/env python3
"""
Filename Checker Compatibility Layer
This provides backward compatibility while we transition to the new modular structure.
Eventually, the original filename_checker.py will be replaced with this.
"""

# Import from new modular structure
from validators.debug_utils import enable_debug, disable_debug, debug_print
from validators.unicode_constants import (
    SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP, NUMBERS, LIGATURE_MAP, 
    LIGATURES_WHITELIST, SUFFIXES, MATHEMATICAL_OPERATORS, 
    MATHEMATICAL_GREEK_LETTERS, GERMAN_INDICATORS
)
from validators.math_utils import (
    find_math_regions, contains_math, is_filename_math_token,
    iterate_nonmath_segments, is_in_spans, fix_ellipsis,
    fix_superscripts_subscripts, detect_math_context, is_likely_math_filename
)

# Re-export everything for backward compatibility
__all__ = [
    # Debug functions
    'enable_debug',
    'disable_debug', 
    'debug_print',
    
    # Unicode constants
    'SUPERSCRIPT_MAP',
    'SUBSCRIPT_MAP',
    'MATHBB_MAP', 
    'NUMBERS',
    'LIGATURE_MAP',
    'LIGATURES_WHITELIST',
    'SUFFIXES',
    'MATHEMATICAL_OPERATORS',
    'MATHEMATICAL_GREEK_LETTERS',
    'GERMAN_INDICATORS',
    
    # Math utilities
    'find_math_regions',
    'contains_math',
    'is_filename_math_token',
    'iterate_nonmath_segments',
    'is_in_spans',
    'fix_ellipsis',
    'fix_superscripts_subscripts',
    'detect_math_context',
    'is_likely_math_filename',
]

# TODO: Add imports for the remaining functions from filename_checker.py
# This will be done in Phase 2 of the refactoring

print("✅ Filename checker compatibility layer loaded - using modular structure")