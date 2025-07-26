"""
Unicode validation and normalization

This module handles Unicode normalization and validation for filenames,
ensuring consistent encoding and preventing homograph attacks.
"""
import unicodedata
import re
from typing import List, Optional, Set
import logging

from core.models import ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class UnicodeValidator:
    """Validate and normalize Unicode in filenames"""
    
    # Suspicious Unicode categories
    SUSPICIOUS_CATEGORIES = {
        'Cc',  # Control characters
        'Cf',  # Format characters
        'Cs',  # Surrogates
        'Co',  # Private use
        'Cn',  # Unassigned
    }
    
    # Allowed scripts for mathematical documents
    ALLOWED_SCRIPTS = {
        'Common',
        'Latin',
        'Greek',  # Mathematical symbols
        'Cyrillic',  # Russian names
        'Han',  # Chinese names
        'Hiragana',
        'Katakana',
        'Arabic',  # Some mathematical notation
    }
    
    def __init__(self):
        self._script_cache = {}
    
    def validate_text(self, text: str) -> List[ValidationIssue]:
        """
        Validate Unicode text for potential issues.
        
        Args:
            text: Text to validate
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        # Check normalization
        nfc_form = unicodedata.normalize('NFC', text)
        nfd_form = unicodedata.normalize('NFD', text)
        
        if text != nfc_form:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='unicode',
                message='Text is not in NFC normalized form',
                field='normalization',
                current_value=text,
                suggested_value=nfc_form,
                fix_available=True
            ))
        
        # Check for suspicious characters
        suspicious_chars = self._find_suspicious_characters(text)
        if suspicious_chars:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='unicode',
                message=f'Contains suspicious Unicode characters: {suspicious_chars}',
                field='characters',
                current_value=text
            ))
        
        # Check for mixed scripts (potential homograph attack)
        scripts = self._get_scripts(text)
        unexpected_scripts = scripts - self.ALLOWED_SCRIPTS
        if unexpected_scripts:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='unicode',
                message=f'Contains unexpected scripts: {unexpected_scripts}',
                field='scripts',
                current_value=text
            ))
        
        # Check for zero-width characters
        if self._has_zero_width_chars(text):
            cleaned = self._remove_zero_width_chars(text)
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='unicode',
                message='Contains zero-width characters',
                field='characters',
                current_value=text,
                suggested_value=cleaned,
                fix_available=True
            ))
        
        return issues
    
    def _find_suspicious_characters(self, text: str) -> List[str]:
        """Find suspicious Unicode characters"""
        suspicious = []
        
        for char in text:
            category = unicodedata.category(char)
            if category in self.SUSPICIOUS_CATEGORIES:
                suspicious.append(f"U+{ord(char):04X} ({category})")
        
        return suspicious
    
    def _get_scripts(self, text: str) -> Set[str]:
        """Get all Unicode scripts used in text"""
        scripts = set()
        
        for char in text:
            # Cache script lookups for performance
            if char not in self._script_cache:
                try:
                    # This would use the unicodedata2 library in production
                    # For now, use a simplified approach
                    if char.isascii():
                        script = 'Latin'
                    elif 'GREEK' in unicodedata.name(char, ''):
                        script = 'Greek'
                    elif 'CYRILLIC' in unicodedata.name(char, ''):
                        script = 'Cyrillic'
                    else:
                        script = 'Common'
                    self._script_cache[char] = script
                except ValueError:
                    self._script_cache[char] = 'Unknown'
            
            scripts.add(self._script_cache[char])
        
        return scripts
    
    def _has_zero_width_chars(self, text: str) -> bool:
        """Check for zero-width characters"""
        zero_width_pattern = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]')
        return bool(zero_width_pattern.search(text))
    
    def _remove_zero_width_chars(self, text: str) -> str:
        """Remove zero-width characters"""
        zero_width_pattern = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]')
        return zero_width_pattern.sub('', text)
    
    def normalize_text(self, text: str, form: str = 'NFC') -> str:
        """
        Normalize Unicode text.
        
        Args:
            text: Text to normalize
            form: Normalization form (NFC, NFD, NFKC, NFKD)
            
        Returns:
            Normalized text
        """
        if form not in ('NFC', 'NFD', 'NFKC', 'NFKD'):
            raise ValueError(f"Invalid normalization form: {form}")
        
        return unicodedata.normalize(form, text)
