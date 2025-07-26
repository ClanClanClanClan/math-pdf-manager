"""
Transitional filename checker that uses the new modular structure.

This file provides backward compatibility while the full refactoring is completed.
"""

# Import from new modular structure
from filename_checker.core import check_filename
from filename_checker.data_structures import Token, Message, FilenameCheckResult
from filename_checker.debug import enable_debug, disable_debug, debug_print
from filename_checker.unicode_utils import sanitize_unicode_security, nfc
from filename_checker.tokenization import (
    robust_tokenize_with_math,
    get_first_word_properly,
    normalize_token,
    find_bad_dash_patterns
)

# Backward compatibility exports
__all__ = [
    'check_filename',
    'Token',
    'Message', 
    'FilenameCheckResult',
    'enable_debug',
    'disable_debug',
    'debug_print',
    'sanitize_unicode_security',
    'nfc',
    'robust_tokenize_with_math',
    'get_first_word_properly',
    'normalize_token',
    'find_bad_dash_patterns',
    # Additional compatibility functions
    'check_filename_spelling_and_format',
    'check_filename_basic',
    'check_filename_advanced'
]

# Provide backward compatibility functions
def check_filename_spelling_and_format(*args, **kwargs):
    """Backward compatibility wrapper."""
    return check_filename(*args, **kwargs)

def check_filename_basic(*args, **kwargs):
    """Backward compatibility wrapper."""
    return check_filename(*args, **kwargs)

def check_filename_advanced(*args, **kwargs):
    """Backward compatibility wrapper."""
    return check_filename(*args, **kwargs)

# Version information
__version__ = "2.17.4"