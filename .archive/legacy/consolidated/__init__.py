"""
ARCHIVE DIRECTORY - DO NOT IMPORT FROM HERE

This directory contains legacy code that has been archived.
Importing from this directory will raise an error.
"""

import sys
import warnings

# Prevent imports from archive directory
def _block_archive_imports():
    """Block imports from archive directory"""
    frame = sys._getframe(1)
    if frame and frame.f_code.co_filename:
        filename = frame.f_code.co_filename
        if '_archive' in filename:
            raise ImportError(
                "❌ BLOCKED: Cannot import from _archive directory. "
                "Use the current modular structure instead:\n"
                "  ✅ from filename_checker import ...\n"
                "  ✅ from validators import ...\n"
                "  ❌ from _archive import ..."
            )

# Warning for any access to this module
warnings.warn(
    "⚠️  WARNING: Accessing _archive directory. "
    "This contains legacy code that should not be used. "
    "Use the current modular structure instead.",
    DeprecationWarning,
    stacklevel=2
)

_block_archive_imports()