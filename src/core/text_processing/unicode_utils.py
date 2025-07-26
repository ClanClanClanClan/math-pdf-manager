"""
Unicode Processing Utilities

Comprehensive Unicode handling for text processing operations.
Consolidated from various unicode utilities across the project.
"""

import unicodedata
import re
from typing import List, Tuple


class UnicodeProcessor:
    """
    Comprehensive Unicode text processor with security and normalization features.
    """
    
    # Dangerous Unicode characters that should be removed for security
    DANGEROUS_CHARS = {
        "\u0000": "NULL BYTE",  # Critical for security
        "\u202e": "RIGHT-TO-LEFT OVERRIDE",
        "\u202d": "LEFT-TO-RIGHT OVERRIDE", 
        "\u202a": "LEFT-TO-RIGHT EMBEDDING",
        "\u202b": "RIGHT-TO-LEFT EMBEDDING",
        "\u202c": "POP DIRECTIONAL FORMATTING",
        "\u200b": "ZERO WIDTH SPACE",
        "\u200c": "ZERO WIDTH NON-JOINER",
        "\u200d": "ZERO WIDTH JOINER",
        "\u200e": "LEFT-TO-RIGHT MARK",
        "\u200f": "RIGHT-TO-LEFT MARK",
        "\ufeff": "BYTE-ORDER MARK",
        "\u2060": "WORD JOINER",
        "\u2061": "FUNCTION APPLICATION",
        "\u2062": "INVISIBLE TIMES",
        "\u2063": "INVISIBLE SEPARATOR",
        "\u2064": "INVISIBLE PLUS",
        "\u202f": "NARROW NO-BREAK SPACE",
    }
    
    # Common homoglyph patterns
    HOMOGLYPHS = {
        'a': ['а', 'ɑ', 'α'],  # Latin a, Cyrillic a, Greek alpha
        'e': ['е', 'ε'],       # Latin e, Cyrillic e, Greek epsilon
        'o': ['о', 'ο', '0'],  # Latin o, Cyrillic o, Greek omicron, digit 0
        'p': ['р', 'ρ'],       # Latin p, Cyrillic p, Greek rho
        'c': ['с', 'ϲ'],       # Latin c, Cyrillic c, Greek c
        'x': ['х', 'χ'],       # Latin x, Cyrillic x, Greek chi
        'y': ['у', 'γ'],       # Latin y, Cyrillic y, Greek gamma
    }
    
    def __init__(self):
        """Initialize the Unicode processor."""
        self._dangerous_pattern = re.compile('|'.join(re.escape(char) for char in self.DANGEROUS_CHARS.keys()))
    
    def normalize(self, text: str, form: str = 'NFC') -> str:
        """
        Normalize Unicode text to specified form.
        
        Args:
            text: Text to normalize
            form: Unicode normalization form (NFC, NFD, NFKC, NFKD)
            
        Returns:
            Normalized text
        """
        if not text:
            return text
        return unicodedata.normalize(form, text)
    
    def remove_dangerous_chars(self, text: str) -> str:
        """
        Remove dangerous Unicode characters that could be used in attacks.
        
        Args:
            text: Input text
            
        Returns:
            Text with dangerous characters removed
        """
        if not text:
            return text
        return self._dangerous_pattern.sub('', text)
    
    def detect_homoglyphs(self, text: str) -> List[Tuple[str, str, int]]:
        """
        Detect potential homoglyph substitutions in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (character, potential_homoglyph, position) tuples
        """
        results = []
        for i, char in enumerate(text):
            for latin_char, homoglyphs in self.HOMOGLYPHS.items():
                if char in homoglyphs and char != latin_char:
                    results.append((char, latin_char, i))
        return results
    
    def is_safe_unicode(self, text: str) -> bool:
        """
        Check if text contains only safe Unicode characters.
        
        Args:
            text: Text to check
            
        Returns:
            True if text is safe, False otherwise
        """
        if not text:
            return True
        
        # Check for dangerous characters
        if any(char in text for char in self.DANGEROUS_CHARS):
            return False
        
        # Check for suspicious character combinations
        if self.detect_homoglyphs(text):
            return False
            
        return True
    
    def sanitize_filename(self, filename: str, replacement: str = '_') -> str:
        """
        Sanitize filename by removing/replacing problematic Unicode characters.
        
        Args:
            filename: Original filename
            replacement: Character to use for replacement
            
        Returns:
            Sanitized filename safe for filesystem use
        """
        if not filename:
            return filename
        
        # Remove dangerous characters
        sanitized = self.remove_dangerous_chars(filename)
        
        # Normalize to NFC form
        sanitized = self.normalize(sanitized, 'NFC')
        
        # Replace problematic characters for filenames
        problematic_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(problematic_chars, replacement, sanitized)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Ensure not empty
        if not sanitized:
            sanitized = f'untitled{replacement}file'
        
        return sanitized


# Global processor instance
_processor = UnicodeProcessor()


def normalize_unicode(text: str, form: str = 'NFC') -> str:
    """
    Normalize Unicode text to specified form.
    
    Args:
        text: Text to normalize
        form: Unicode normalization form (NFC, NFD, NFKC, NFKD)
        
    Returns:
        Normalized text
    """
    return _processor.normalize(text, form)


def detect_homoglyphs(text: str) -> List[Tuple[str, str, int]]:
    """
    Detect potential homoglyph substitutions in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of (character, potential_homoglyph, position) tuples
    """
    return _processor.detect_homoglyphs(text)


def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """
    Sanitize filename by removing/replacing problematic Unicode characters.
    
    Args:
        filename: Original filename
        replacement: Character to use for replacement
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    return _processor.sanitize_filename(filename, replacement)


def is_safe_unicode(text: str) -> bool:
    """
    Check if text contains only safe Unicode characters.
    
    Args:
        text: Text to check
        
    Returns:
        True if text is safe, False otherwise
    """
    return _processor.is_safe_unicode(text)


# Backward compatibility functions
def nfc(text: str) -> str:
    """Normalize text to NFC form."""
    return normalize_unicode(text, 'NFC')


def nfd(text: str) -> str:
    """Normalize text to NFD form.""" 
    return normalize_unicode(text, 'NFD')


def remove_dangerous_unicode(text: str) -> str:
    """Remove dangerous Unicode characters."""
    return _processor.remove_dangerous_chars(text)