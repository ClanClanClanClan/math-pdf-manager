"""
Validation Module - Refactored from validators.filename_checker.py

This module contains the validation logic extracted from the monolithic
filename_checker.py file, organized into focused components.

Components:
- filename_validator: Core validation logic
- author_parser: Author name parsing and normalization
- title_normalizer: Title normalization and fixing
- unicode_handler: Unicode processing and security
- pattern_matcher: Pattern matching and analysis
- suggestion_engine: Auto-fix suggestions
- validation_result: Result objects and data models
- validation_utils: Utility functions
"""

# Core validation functionality
from .filename_validator import (
    FilenameValidator,
    check_filename,
    batch_check_filenames,
)

# Author processing
from .author_parser import (
    AuthorParser,
    fix_author_block,
    normalize_author_string,
    author_string_is_normalized,
)

# Title processing
from .title_normalizer import (
    TitleNormalizer,
    normalize_title,
    fix_title_capitalization,
    spelling_and_format_errors,
    is_mathematical_variable_in_context,
)

# Unicode handling
from .unicode_handler import (
    UnicodeHandler,
    sanitize_unicode_security,
    normalize_for_comparison,
)

# Pattern matching
from .pattern_matcher import (
    PatternMatcher,
    robust_tokenize_with_math,
    normalize_token,
    find_bad_dash_patterns,
    is_math_token,
    Token,
)

# Math handling
from .math_handler import (
    MathHandler,
    find_math_regions,
    is_in_math_region,
    has_mathematical_content,
    should_preserve_digit,
)

# Suggestion engine
from .suggestion_engine import (
    SuggestionEngine,
    generate_suggestions,
    get_quick_fixes,
    apply_suggestion,
    apply_all_suggestions,
)

# Result objects
from .validation_result import (
    ValidationResult,
    FilenameCheckResult,
    Message,
)

# Utility functions
from core.validation import (
    enable_debug,
    disable_debug,
    debug_print,
)

__all__ = [
    # Core validation
    'FilenameValidator',
    'check_filename',
    'batch_check_filenames',
    
    # Author processing
    'AuthorParser', 
    'fix_author_block',
    'normalize_author_string',
    'author_string_is_normalized',
    
    # Title processing
    'TitleNormalizer',
    'normalize_title',
    'fix_title_capitalization',
    'spelling_and_format_errors',
    'is_mathematical_variable_in_context',
    
    # Unicode handling
    'UnicodeHandler',
    'sanitize_unicode_security',
    'normalize_for_comparison',
    
    # Pattern matching
    'PatternMatcher',
    'robust_tokenize_with_math',
    'normalize_token',
    'find_bad_dash_patterns',
    'is_math_token',
    'Token',
    
    # Math handling
    'MathHandler',
    'find_math_regions',
    'is_in_math_region',
    'has_mathematical_content',
    'should_preserve_digit',
    
    # Suggestion engine
    'SuggestionEngine',
    'generate_suggestions',
    'get_quick_fixes',
    'apply_suggestion',
    'apply_all_suggestions',
    
    # Result objects
    'ValidationResult',
    'FilenameCheckResult',
    'Message',
    
    # Utilities
    'enable_debug',
    'disable_debug', 
    'debug_print',
]