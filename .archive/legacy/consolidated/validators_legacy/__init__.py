"""Validators package for Math-PDF Manager"""
from .filename import FilenameValidator
from .author import AuthorValidator
from .unicode import UnicodeValidator
from .math_context import MathContextDetector
from .exceptions import *

# New extracted modules
from .unicode_constants import *
from .debug_utils import enable_debug, disable_debug, debug_print
from .math_utils import find_math_regions, contains_math, is_filename_math_token

__all__ = [
    'FilenameValidator',
    'AuthorValidator', 
    'UnicodeValidator',
    'MathContextDetector',
    'ValidationError',
    'FilenameValidationError',
    # Debug utilities
    'enable_debug',
    'disable_debug', 
    'debug_print',
    # Math utilities
    'find_math_regions',
    'contains_math',
    'is_filename_math_token',
    # Unicode constants
    'SUPERSCRIPT_MAP',
    'SUBSCRIPT_MAP',
    'MATHBB_MAP',
    'MATHEMATICAL_OPERATORS',
    'MATHEMATICAL_GREEK_LETTERS',
]
