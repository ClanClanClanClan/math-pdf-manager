"""
Custom exceptions for validators

This module defines specific exceptions for validation errors,
providing better error handling and debugging information.
"""
from typing import Optional, Dict, Any


class ValidationError(Exception):
    """Base validation error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class FilenameValidationError(ValidationError):
    """Filename validation error"""
    
    def __init__(self, message: str, filename: str, **kwargs):
        super().__init__(message, {'filename': filename, **kwargs})
        self.filename = filename


class AuthorValidationError(ValidationError):
    """Author validation error"""
    
    def __init__(self, message: str, author: str, **kwargs):
        super().__init__(message, {'author': author, **kwargs})
        self.author = author


class UnicodeValidationError(ValidationError):
    """Unicode validation error"""
    
    def __init__(self, message: str, text: str, **kwargs):
        super().__init__(message, {'text': text, **kwargs})
        self.text = text


class MathContextError(ValidationError):
    """Mathematical context detection error"""
    pass
