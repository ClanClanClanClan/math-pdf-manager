"""
DEPRECATED MODULE

This module has been consolidated into the unified validation system.
Please update your imports:

OLD: from src.validators.core_validation import validate_cli_inputs
NEW: from src.core.validation import validate_cli_inputs

OLD: from src.core.security.input_validation import InputValidator  
NEW: from src.core.validation import InputValidator

For more information, see: src/core/validation/
"""

import warnings

warnings.warn(
    f"Module {__name__} is deprecated. Use src.core.validation instead.",
    DeprecationWarning,
    stacklevel=2
)
