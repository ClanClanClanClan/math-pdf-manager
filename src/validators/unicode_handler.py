"""
Unicode Handler Module

Unicode processing, normalization, and security functions
extracted from src.validators.filename_checker.py
"""

import re
import unicodedata
from typing import Tuple, List, Set, Iterable
from src.core.validation import debug_print


class UnicodeHandler:
    """Advanced Unicode processing and security validation"""
    
    def __init__(self):
        # Dangerous Unicode characters that should be removed
        self.dangerous_unicode_chars = {
            "\ufeff": "BOM (Byte Order Mark)",
            "\u200b": "Zero-Width Space",
            "\u200c": "Zero-Width Non-Joiner", 
            "\u200d": "Zero-Width Joiner",
            "\u200e": "Left-to-Right Mark",
            "\u200f": "Right-to-Left Mark",
            "\u202a": "Left-to-Right Embedding",
            "\u202b": "Right-to-Left Embedding", 
            "\u202c": "Pop Directional Formatting",
            "\u202d": "Left-to-Right Override",
            "\u202e": "Right-to-Left Override",
            "\u2060": "Word Joiner",
            "\u2061": "Function Application",
            "\u2062": "Invisible Times",
            "\u2063": "Invisible Separator",
            "\u2064": "Invisible Plus",
            "\u202f": "Narrow No-Break Space",
        }
        
        # Mathematical Greek letters (commonly used in academic papers)
        self.mathematical_greek_letters = {
            'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ',
            'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω',
            'Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ',
            'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω'
        }
    
    def nfc(self, s: str | None) -> str | None:
        """Normalize to NFC (Canonical Decomposition, then Canonical Composition)"""
        return unicodedata.normalize("NFC", s) if s else s
    
    def is_nfc(self, s: str) -> bool:
        """Check if string is in NFC normalized form"""
        return s == unicodedata.normalize("NFC", s)
    
    def normalize_for_comparison(self, s: str) -> str:
        """Normalize string for comparison with robust Unicode handling"""
        if not s:
            return s

        # Ensure NFC normalization first
        s = self.nfc(s)

        # Replace various dash characters with regular hyphen
        s = re.sub(r"[–—−‐]", "-", s)

        # Normalize whitespace
        result = re.sub(r"\s+", " ", s).strip()
        return result
    
    def has_mathematical_greek(self, text: str) -> bool:
        """Check if text contains mathematical Greek letters or terms"""
        # Check for individual Greek letters
        if any(char in self.mathematical_greek_letters for char in text):
            debug_print(f"Found mathematical Greek letters in: {text}")
            return True
        
        # Check for common mathematical Greek terms (as standalone words)
        greek_terms = {
            'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta',
            'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi', 'rho',
            'sigma', 'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega'
        }
        
        # Use word boundaries to avoid false positives like "beta test" or "alphabet"
        import re
        text_lower = text.lower()
        for term in greek_terms:
            if re.search(rf'\b{term}\b', text_lower):
                # Additional check: is it in a mathematical context?
                # Look for nearby mathematical indicators
                math_context = any(indicator in text_lower for indicator in 
                                 ['-particle', 'function', 'distribution', 'angle', 'coefficient'])
                if math_context or term == 'pi':  # pi is almost always mathematical
                    debug_print(f"Found mathematical Greek term '{term}' in: {text}")
                    return True
        
        return False
    
    def sanitize_unicode_security(self, text: str) -> Tuple[str, List[str], Set[str]]:
        """Enhanced Unicode security sanitization"""
        removed = []
        
        # Remove dangerous Unicode characters
        for ch, name in self.dangerous_unicode_chars.items():
            if ch in text:
                text = text.replace(ch, "")
                removed.append(name)

        # Detect Unicode scripts
        scripts = set()
        for ch in text:
            try:
                name = unicodedata.name(ch)
            except ValueError:
                continue
            for label in ("GREEK", "CYRILLIC", "LATIN", "ARABIC", "HEBREW"):
                if label in name:
                    scripts.add(label)

        # Enhanced mixed script handling for mathematical content
        if len(scripts) > 1 and "LATIN" in scripts and "GREEK" in scripts:
            if self.has_mathematical_greek(text):
                debug_print(
                    f"Allowing mixed GREEK/LATIN scripts due to mathematical content: {text}"
                )
                scripts = {"LATIN"}  # Don't report this as mixed scripts

        return text, removed, scripts
    
    def iterate_nonmath_segments(self, text: str, regions: List[Tuple[int, int]]) -> Iterable[Tuple[int, int, str]]:
        """Iterate over non-mathematical segments of text"""
        n = len(text)
        
        # Clean and sort regions
        clean = [(max(0, s), min(n, e)) for s, e in regions if s < e]
        clean.sort()
        
        # Merge overlapping regions
        merged = []
        for s, e in clean:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        
        # Yield segments between mathematical regions
        last = 0
        for s, e in merged:
            if last < s:
                segment = text[last:s]
                yield last, s, segment
            last = e
        
        # Yield final segment if any
        if last < n:
            segment = text[last:]
            yield last, n, segment
    
    def detect_encoding_issues(self, text: str) -> List[str]:
        """Detect potential encoding issues in text"""
        issues = []
        
        # Check for replacement characters
        if '\ufffd' in text:
            issues.append("Contains Unicode replacement character (�)")
        
        # Check for control characters
        control_chars = [ch for ch in text if unicodedata.category(ch).startswith('C')]
        if control_chars:
            issues.append(f"Contains {len(control_chars)} control characters")
        
        # Check for private use characters
        private_chars = [ch for ch in text if unicodedata.category(ch) == 'Co']
        if private_chars:
            issues.append(f"Contains {len(private_chars)} private use characters")
        
        return issues
    
    def normalize_mathematical_symbols(self, text: str) -> str:
        """Normalize mathematical symbols to standard forms"""
        # Common mathematical symbol normalizations
        normalizations = {
            # Fractions
            '½': '1/2',
            '⅓': '1/3', 
            '⅔': '2/3',
            '¼': '1/4',
            '¾': '3/4',
            
            # Superscripts
            '²': '^2',
            '³': '^3',
            
            # Mathematical operators
            '×': '*',
            '÷': '/',
            '≠': '!=',
            '≤': '<=',
            '≥': '>=',
            '∞': 'infinity',
            
            # Arrows
            '→': '->',
            '←': '<-',
            '↔': '<->',
        }
        
        for symbol, replacement in normalizations.items():
            text = text.replace(symbol, replacement)
        
        return text
    
    def debug_unicode_difference(self, str1: str, str2: str, label: str = "") -> None:
        """Debug Unicode differences between two strings"""
        if str1 == str2:
            debug_print(f"{label}Strings are identical")
            return
        
        debug_print(f"{label}String differences:")
        debug_print(f"  String 1: {repr(str1)}")
        debug_print(f"  String 2: {repr(str2)}")
        
        # Character-by-character comparison
        min_len = min(len(str1), len(str2))
        for i in range(min_len):
            if str1[i] != str2[i]:
                debug_print(f"  Diff at pos {i}: {repr(str1[i])} vs {repr(str2[i])}")
        
        if len(str1) != len(str2):
            debug_print(f"  Length difference: {len(str1)} vs {len(str2)}")


# Module-level functions for backward compatibility
_default_handler = UnicodeHandler()

def nfc(s: str | None) -> str | None:
    """Normalize to NFC form"""
    return _default_handler.nfc(s)

def is_nfc(s: str) -> bool:
    """Check if string is NFC normalized"""
    return _default_handler.is_nfc(s)

def normalize_for_comparison(s: str) -> str:
    """Normalize string for comparison"""
    return _default_handler.normalize_for_comparison(s)

def has_mathematical_greek(text: str) -> bool:
    """Check for mathematical Greek content"""
    return _default_handler.has_mathematical_greek(text)

def sanitize_unicode_security(text: str) -> Tuple[str, List[str], Set[str]]:
    """Sanitize Unicode for security"""
    return _default_handler.sanitize_unicode_security(text)

def iterate_nonmath_segments(text: str, regions: List[Tuple[int, int]]) -> Iterable[Tuple[int, int, str]]:
    """Iterate over non-mathematical segments"""
    return _default_handler.iterate_nonmath_segments(text, regions)

def debug_unicode_difference(str1: str, str2: str, label: str = "") -> None:
    """Debug Unicode differences"""
    _default_handler.debug_unicode_difference(str1, str2, label)


def normalize_unicode_safely(text: str) -> str:
    """
    Safely normalize Unicode text with comprehensive security checks.
    
    This function combines NFC normalization with security sanitization
    to ensure the text is safe and consistent.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized and sanitized text
    """
    if not text:
        return text
    
    # First apply NFC normalization
    normalized = nfc(text)
    if not normalized:
        return ""
    
    # Then apply security sanitization
    sanitized, removed_chars, scripts = sanitize_unicode_security(normalized)
    
    # Apply additional normalization for comparison
    result = normalize_for_comparison(sanitized)
    
    return result


# Constants for external use
DANGEROUS_UNICODE_CHARS = _default_handler.dangerous_unicode_chars
MATHEMATICAL_GREEK_LETTERS = _default_handler.mathematical_greek_letters