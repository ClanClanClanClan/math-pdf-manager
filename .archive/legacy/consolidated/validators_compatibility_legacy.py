"""
Compatibility Layer for Validators to src.validation Migration

This module provides backward compatibility for code that imports from the
'validators' module, redirecting to the new 'src.validation' module structure.

This is a temporary compatibility layer that should be removed once all
imports have been updated to use src.validation directly.
"""

import sys
import warnings
from pathlib import Path

# Add src to path if needed
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import everything from the new module structure
from src.validation import (
    # Core validation
    FilenameValidator,
    check_filename,
    batch_check_filenames,
    
    # Author processing
    AuthorParser,
    fix_author_block,
    normalize_author_string,
    author_string_is_normalized,
    
    # Title processing
    TitleNormalizer,
    normalize_title,
    fix_title_capitalization,
    
    # Unicode handling
    UnicodeHandler,
    sanitize_unicode_security,
    normalize_for_comparison,
    
    # Pattern matching
    PatternMatcher,
    robust_tokenize_with_math,
    normalize_token,
    find_bad_dash_patterns,
    is_math_token,
    Token,
    
    # Math handling
    MathHandler,
    find_math_regions,
    is_in_math_region,
    has_mathematical_content,
    should_preserve_digit,
    
    # Suggestion engine
    SuggestionEngine,
    generate_suggestions,
    get_quick_fixes,
    apply_suggestion,
    apply_all_suggestions,
    
    # Result objects
    ValidationResult,
    FilenameCheckResult,
    Message,
    
    # Utilities
    enable_debug,
    disable_debug,
    debug_print,
)

# Mapping for module-specific imports
MODULE_MAPPING = {
    'validators.filename': 'src.validation.filename_validator',
    'validators.author': 'src.validation.author_parser',
    'validators.unicode': 'src.validation.unicode_handler',
    'validators.math_context': 'src.validation.math_handler',
    'validators.math_utils': 'src.validation.math_handler',
    'validators.exceptions': 'src.validation.validation_result',
    'validators.debug_utils': 'src.validation.validation_utils',
}

def _show_deprecation_warning(old_import, new_import):
    """Show deprecation warning for old imports"""
    warnings.warn(
        f"Import from '{old_import}' is deprecated. "
        f"Please update your code to import from '{new_import}' instead.",
        DeprecationWarning,
        stacklevel=3
    )

# Create module aliases for backward compatibility
class CompatibilityModule:
    """Module wrapper that redirects to new locations with warnings"""
    
    def __init__(self, old_name, new_module):
        self.old_name = old_name
        self.new_module = new_module
        
    def __getattr__(self, name):
        new_name = self.new_module.__name__
        _show_deprecation_warning(f"{self.old_name}.{name}", f"{new_name}.{name}")
        return getattr(self.new_module, name)

# Install compatibility modules
if 'validators' not in sys.modules:
    # Create validators package
    import types
    validators = types.ModuleType('validators')
    sys.modules['validators'] = validators
    
    # Add submodules
    import src.validation.filename_validator
    validators.filename = CompatibilityModule('validators.filename', src.validation.filename_validator)
    sys.modules['validators.filename'] = validators.filename
    
    import src.validation.author_parser
    validators.author = CompatibilityModule('validators.author', src.validation.author_parser)
    sys.modules['validators.author'] = validators.author
    
    import src.validation.unicode_handler
    validators.unicode = CompatibilityModule('validators.unicode', src.validation.unicode_handler)
    sys.modules['validators.unicode'] = validators.unicode
    
    import src.validation.math_handler
    validators.math_context = CompatibilityModule('validators.math_context', src.validation.math_handler)
    validators.math_utils = CompatibilityModule('validators.math_utils', src.validation.math_handler)
    sys.modules['validators.math_context'] = validators.math_context
    sys.modules['validators.math_utils'] = validators.math_utils
    
    import src.validation.validation_result
    validators.exceptions = CompatibilityModule('validators.exceptions', src.validation.validation_result)
    sys.modules['validators.exceptions'] = validators.exceptions
    
    import src.validation.validation_utils
    validators.debug_utils = CompatibilityModule('validators.debug_utils', src.validation.validation_utils)
    sys.modules['validators.debug_utils'] = validators.debug_utils

# For direct imports from this module
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

print("✅ Validators compatibility layer loaded. Please update imports to use src.validation directly.")