"""
filename_checker - Academic filename validation and correction.

This module provides comprehensive filename validation for academic papers,
including mathematical symbol detection, author name validation, and
format correction.
"""

from .data_structures import Token, Message, FilenameCheckResult
from .core import check_filename
from .batch_processing import batch_check_filenames
from .debug import enable_debug, disable_debug

__version__ = "2.17.4"
__all__ = ["Token", "Message", "FilenameCheckResult", "check_filename", "batch_check_filenames", "enable_debug", "disable_debug"]