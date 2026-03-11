"""
Backward Compatibility Layer for Validation Systems

This module provides backward compatibility for existing validation imports
while redirecting to the new unified validation system.
"""

from typing import Any, List, Optional, Union
from pathlib import Path
import warnings

from .unified_validator import UnifiedValidationService

# Create global instance
_validator = UnifiedValidationService()

# ========================================
# Legacy CLI Validation (from core_validation.py)
# ========================================

def validate_cli_inputs(args) -> bool:
    """Legacy CLI validation function."""
    warnings.warn(
        "validate_cli_inputs is deprecated. Use UnifiedValidationService.validate_cli_inputs",
        DeprecationWarning,
        stacklevel=2
    )
    return _validator.validate_cli_inputs(args)


def validate_template_dir(template_dir: str) -> bool:
    """Legacy template directory validation."""
    warnings.warn(
        "validate_template_dir is deprecated. Use UnifiedValidationService.validate_directory_path",
        DeprecationWarning,
        stacklevel=2
    )
    return _validator.validate_directory_path(template_dir)


# ========================================
# Legacy Input Validation (from input_validation.py)
# ========================================

class ValidationError(Exception):
    """Legacy validation error for backward compatibility."""
    pass


class InputValidator:
    """Legacy InputValidator class that redirects to unified validator."""
    
    @classmethod
    def validate_string(cls, value: Any, min_length: int = 0, max_length: int = 1000,
                       allowed_chars: Optional[set] = None, pattern: Optional[Any] = None) -> str:
        """Legacy string validation."""
        warnings.warn(
            "InputValidator.validate_string is deprecated. Use UnifiedValidationService.validate_string",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _validator.validate_string(value, min_length, max_length, allowed_chars)
        except ValueError as e:
            raise ValidationError(str(e))
    
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Legacy email validation."""
        warnings.warn(
            "InputValidator.validate_email is deprecated. Use UnifiedValidationService.validate_email",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _validator.validate_email(email)
        except ValueError as e:
            raise ValidationError(str(e))
    
    @classmethod
    def validate_url(cls, url: str, allowed_schemes: Optional[List[str]] = None) -> str:
        """Legacy URL validation."""
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        warnings.warn(
            "InputValidator.validate_url is deprecated. Use UnifiedValidationService.validate_url",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _validator.validate_url(url, allowed_schemes)
        except ValueError as e:
            raise ValidationError(str(e))
    
    @classmethod
    def validate_filename(cls, filename: str, allow_paths: bool = False) -> str:
        """Legacy filename validation."""
        warnings.warn(
            "InputValidator.validate_filename is deprecated. Use UnifiedValidationService.sanitize_filename",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _validator.sanitize_filename(filename)
        except ValueError as e:
            raise ValidationError(str(e))
    
    @classmethod
    def validate_path(cls, path: Union[str, Path], base_path: Optional[Path] = None) -> Path:
        """Legacy path validation."""
        warnings.warn(
            "InputValidator.validate_path is deprecated. Use UnifiedValidationService.validate_file_path",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            _validator.validate_file_path(path)
            return Path(path).resolve()
        except ValueError as e:
            raise ValidationError(str(e))
    
    @classmethod
    def validate_integer(cls, value: Any, min_value: Optional[int] = None, 
                        max_value: Optional[int] = None) -> int:
        """Legacy integer validation."""
        warnings.warn(
            "InputValidator.validate_integer is deprecated. Use UnifiedValidationService.validate_integer",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _validator.validate_integer(value, min_value, max_value)
        except ValueError as e:
            raise ValidationError(str(e))
    
    @classmethod
    def validate_ip_address(cls, ip: str, version: Optional[int] = None) -> str:
        """Legacy IP address validation."""
        warnings.warn(
            "InputValidator.validate_ip_address is deprecated. Use UnifiedValidationService.validate_ip_address",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _validator.validate_ip_address(ip, version)
        except ValueError as e:
            raise ValidationError(str(e))


class SecureFileHandler:
    """Legacy SecureFileHandler class that redirects to unified validator."""
    
    @classmethod
    def validate_file_extension(cls, filename: str, allowed_extensions: Optional[set] = None,
                               file_type: Optional[str] = None) -> str:
        """Legacy file extension validation."""
        warnings.warn(
            "SecureFileHandler.validate_file_extension is deprecated. Use UnifiedValidationService.validate_file_extension",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _validator.validate_file_extension(filename, allowed_extensions, file_type)
        except ValueError as e:
            raise ValidationError(str(e))


# ========================================
# Legacy Validation Utils (from validation_utils.py)
# ========================================

def get_language(text: str) -> str:
    """Legacy language detection."""
    warnings.warn(
        "get_language is deprecated. Use UnifiedValidationService.detect_language",
        DeprecationWarning,
        stacklevel=2
    )
    return _validator.detect_language(text)


def debug_print(*args, **kwargs):
    """Legacy debug print function."""
    warnings.warn(
        "debug_print is deprecated. Use standard logging instead",
        DeprecationWarning,
        stacklevel=2
    )
    print("🔍 DEBUG:", *args, **kwargs)


def enable_debug():
    """Legacy debug enable function."""
    warnings.warn(
        "enable_debug is deprecated. Use standard logging configuration",
        DeprecationWarning,
        stacklevel=2
    )
    pass


def disable_debug():
    """Legacy debug disable function."""
    warnings.warn(
        "disable_debug is deprecated. Use standard logging configuration",
        DeprecationWarning,
        stacklevel=2
    )
    pass


def is_debug_enabled() -> bool:
    """Legacy debug status function."""
    warnings.warn(
        "is_debug_enabled is deprecated. Use standard logging configuration",
        DeprecationWarning,
        stacklevel=2
    )
    return False


# ========================================
# Legacy DI Validation Service 
# ========================================

class UnifiedValidationService_Legacy:
    """Legacy unified validation service for DI compatibility."""
    
    def __init__(self, logging_service=None):
        warnings.warn(
            "Legacy UnifiedValidationService is deprecated. Use src.core.validation.UnifiedValidationService",
            DeprecationWarning,
            stacklevel=2
        )
        self._validator = _validator
    
    def validate_cli_arguments(self, args: Any) -> bool:
        """Legacy CLI validation."""
        return self._validator.validate_cli_inputs(args)
    
    def validate_file_path(self, path: Union[str, Path], base_path: Optional[Path] = None, 
                          allow_symlinks: bool = False) -> Path:
        """Legacy file path validation."""
        self._validator.validate_file_path(path)
        return Path(path).resolve()
    
    def validate_filename(self, filename: str, allow_paths: bool = False) -> str:
        """Legacy filename validation."""
        return self._validator.sanitize_filename(filename)
    
    def has_mathematical_content(self, text: str) -> bool:
        """Legacy mathematical content detection."""
        result = self._validator.validate_mathematical_content(text)
        return result.get('has_math', False)
    
    def detect_language(self, text: str) -> str:
        """Legacy language detection."""
        return self._validator.detect_language(text)


# Export all legacy interfaces
__all__ = [
    # Legacy CLI validation
    'validate_cli_inputs',
    'validate_template_dir',
    
    # Legacy input validation
    'ValidationError',
    'InputValidator', 
    'SecureFileHandler',
    
    # Legacy validation utils
    'get_language',
    'debug_print',
    'enable_debug',
    'disable_debug',
    'is_debug_enabled',
    
    # Legacy DI validation
    'UnifiedValidationService_Legacy',
    
    # Direct access to new unified validator
    'UnifiedValidationService'
]