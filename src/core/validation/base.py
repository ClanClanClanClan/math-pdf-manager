#!/usr/bin/env python3
"""
Core validation base classes and utilities
Extracted from src.validators.filename_checker.py for better modularity
"""

import unicodedata
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    suggestions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseValidator(ABC):
    """Abstract base class for all validators."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    @abstractmethod
    def validate(self, text: str) -> ValidationResult:
        """Validate the given text."""
        pass
    
    def debug_print(self, *args, **kwargs):
        """Print debug message if debugging is enabled."""
        if self.debug:
            print("🔍 DEBUG:", *args, **kwargs)


class UnicodeValidator(BaseValidator):
    """Validates Unicode normalization and encoding."""
    
    def validate(self, text: str) -> ValidationResult:
        """Check if text is properly normalized."""
        try:
            # Check if already NFC normalized
            nfc_form = unicodedata.normalize("NFC", text)
            if text != nfc_form:
                return ValidationResult(
                    is_valid=False,
                    error_type="unicode_normalization",
                    error_message="Text is not in NFC normalized form",
                    suggestions=[nfc_form],
                    metadata={"original": text, "normalized": nfc_form}
                )
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_type="unicode_error",
                error_message=f"Unicode validation failed: {str(e)}"
            )


def canonicalize(text: str) -> str:
    """
    Canonicalize text for comparison purposes.
    This is the core canonicalization function used throughout the system.
    """
    if not text:
        return ""
    
    # Normalize Unicode to NFC form
    text = unicodedata.normalize("NFC", text)
    
    # Normalize dashes (em-dash and en-dash to hyphen)
    text = text.replace("—", "-").replace("–", "-")
    
    # Convert to lowercase for case-insensitive comparison
    text = text.lower()
    
    return text