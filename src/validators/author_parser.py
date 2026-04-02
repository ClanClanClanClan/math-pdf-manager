"""
Author Parser Module

Author name parsing, normalization, and validation functions
extracted from validators.filename_checker.py
"""

import logging
import re
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)
from .unicode_handler import nfc


class AuthorParser:
    """Advanced author name parsing and normalization"""
    
    def __init__(self):
        # Dangerous Unicode characters to remove
        self.dangerous_chars = [
            "\ufeff",  # BOM
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\u200e",  # Left-to-right mark
            "\u200f",  # Right-to-left mark
            "\u202a",  # Left-to-right embedding
            "\u202b",  # Right-to-left embedding
            "\u202c",  # Pop directional formatting
            "\u202d",  # Left-to-right override
            "\u202e",  # Right-to-left override
            "\u2060",  # Word joiner
            "\u2061",  # Function application
            "\u2062",  # Invisible times
            "\u2063",  # Invisible separator
            "\u2064",  # Invisible plus
            "\u202f",  # Narrow no-break space
        ]
    
    def remove_dangerous_unicode(self, text: str) -> str:
        """Remove dangerous Unicode characters"""
        for char in self.dangerous_chars:
            text = text.replace(char, "")
        return text
    
    def fix_initial_spacing(self, author_part: str) -> str:
        """Fix spacing in initials: 'J.D.' -> 'J. D.'"""
        if not author_part:
            return author_part
            
        # Pattern for initials like "J.D." or "A.B.C."
        pattern = r'([A-Z])\.([A-Z])'
        
        # Keep applying until no more matches (for cases like A.B.C.D.)
        while re.search(pattern, author_part):
            author_part = re.sub(pattern, r'\1. \2', author_part)
            
        return author_part
    
    def fix_author_suffixes(self, text: str) -> str:
        """Fix spacing around author suffixes"""
        # Common suffixes
        suffixes = ['Jr', 'Sr', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
                   'MD', 'PhD', 'Prof', 'Dr']
        
        for suffix in suffixes:
            # Fix missing comma before suffix
            pattern = rf'\b(\w+)\s+({suffix})\b'
            text = re.sub(pattern, r'\1, \2', text)
        
        return text
    
    def normalize_author_string(self, s: str) -> str:
        """Normalize author string with comprehensive cleaning"""
        if not s:
            return ""
            
        # Remove dangerous Unicode characters
        s = self.remove_dangerous_unicode(s)
        
        # Normalize Unicode
        s = nfc(s) if s else ""
        
        # Normalize whitespace
        s = re.sub(r"\s+", " ", s).strip()
        
        # Fix spacing around commas
        s = re.sub(r"\s*,\s*", ", ", s)
        
        # Add comma if missing between surname and initials
        # Pattern: "Surname I." or "Surname Initial" -> "Surname, I."
        if ',' not in s:
            # Common particles/prefixes in surnames
            particles = ['von', 'van', 'de', 'di', 'da', 'del', 'della', 'des', 'du', 'la', 'le', 'der', 'den', 'ter', 'ten']
            
            # Try to match: (optional particles) + surname(s) + initials
            # This handles "von Neumann J." and "García López A.B."
            pattern = r'^((?:(?:' + '|'.join(particles) + r')\s+)?(?:\w+\s+)*\w+)\s+([A-Z]\.?(?:\s*[A-Z]\.?)*)$'
            match = re.match(pattern, s)
            if match:
                surname, initials = match.groups()
                s = f"{surname}, {initials}"
        
        # Fix initial spacing
        s = self.fix_initial_spacing(s)
        
        # Fix author suffixes
        s = self.fix_author_suffixes(s)
        
        return s
    
    def author_string_is_normalized(self, raw: str) -> Tuple[bool, str]:
        """Check if author string is normalized and return normalized version"""
        if not raw:
            return True, ""
            
        normalized = self.normalize_author_string(raw)
        is_normalized = (raw == normalized)
        
        logger.debug(f"Author normalization check: '{raw}' -> '{normalized}' (normalized: {is_normalized})")
        
        return is_normalized, normalized
    
    def parse_authors_and_title(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse filename to extract authors and title"""
        if not filename or " - " not in filename:
            return None, None
            
        parts = filename.split(" - ", 1)
        if len(parts) != 2:
            return None, None
            
        author_part = parts[0].strip()
        title_part = parts[1].strip()
        
        # Remove file extension from title
        if title_part.endswith('.pdf'):
            title_part = title_part[:-4]
        elif '.' in title_part:
            title_part = title_part.rsplit('.', 1)[0]
            
        return author_part, title_part
    
    def debug_author_string(self, s: str) -> str:
        """Debug representation of author string showing special characters"""
        if not s:
            return "«empty»"
            
        debug_repr = ""
        for char in s:
            if ord(char) < 32 or ord(char) > 126:
                debug_repr += f"\\u{ord(char):04x}"
            else:
                debug_repr += char
                
        return f"«{debug_repr}»"
    
    def enforce_ndash_between_authors(self, text: str, pairs: List[Tuple[int, int]]) -> str:
        """Enforce n-dash between authors in hyphenated names"""
        if not pairs:
            return text
            
        # Convert text to list for easier manipulation
        chars = list(text)
        
        for start, end in pairs:
            if start < len(chars) and chars[start] == '-':
                chars[start] = '–'  # n-dash
                
        return ''.join(chars)


# Module-level functions for backward compatibility
_default_parser = AuthorParser()

def fix_author_block(raw_input: str) -> str:
    """
    Main author processing function that handles all formats correctly.
    This is a simple implementation for filename_checker compatibility.
    """
    if not raw_input or not isinstance(raw_input, str):
        return ""

    # Use the comprehensive author processing from author_processing.py if available
    try:
        from author_processing import fix_author_block as comprehensive_fix
        return comprehensive_fix(raw_input)
    except ImportError:
        # Fallback to basic processing
        logger.debug("Using fallback author processing")
        return _default_parser.normalize_author_string(raw_input)


def normalize_author_string(s: str) -> str:
    """Normalize author string - main entry point"""
    return _default_parser.normalize_author_string(s)


def author_string_is_normalized(raw: str) -> Tuple[bool, str]:
    """Check if author string is normalized"""
    return _default_parser.author_string_is_normalized(raw)


def fix_initial_spacing(author_part: str) -> str:
    """Fix spacing in initials"""
    return _default_parser.fix_initial_spacing(author_part)


def fix_author_suffixes(s: str) -> str:
    """Fix spacing around author suffixes"""
    return _default_parser.fix_author_suffixes(s)


def parse_authors_and_title(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse filename to extract authors and title"""
    return _default_parser.parse_authors_and_title(filename)


def debug_author_string(s: str) -> str:
    """Debug representation of author string"""
    return _default_parser.debug_author_string(s)


def enforce_ndash_between_authors(text: str, pairs: List[Tuple[int, int]]) -> str:
    """Enforce n-dash between authors"""
    return _default_parser.enforce_ndash_between_authors(text, pairs)


# Enhanced functions for complete compatibility
def normalize_author_string_complete(text: str) -> str:
    """Alias for fix_author_block for test compatibility"""
    return fix_author_block(text)


def author_string_is_normalized_complete(text: str) -> Tuple[bool, str]:
    """Enhanced version for test compatibility"""
    return author_string_is_normalized(text)


def author_string_is_normalized_debug(raw: str) -> Tuple[bool, str, Optional[str]]:
    """Debug version that includes debug information"""
    is_norm, normalized = author_string_is_normalized(raw)
    debug_info = debug_author_string(raw) if not is_norm else None
    return is_norm, normalized, debug_info


def fix_authors(text: str) -> str:
    """Fix multiple authors in text"""
    # Split by common author separators
    separators = [', ', ' and ', ' & ', '; ']
    
    authors = [text]
    for sep in separators:
        new_authors = []
        for author in authors:
            new_authors.extend(author.split(sep))
        authors = new_authors
    
    # Normalize each author
    normalized_authors = [normalize_author_string(author.strip()) for author in authors if author.strip()]
    
    # Rejoin with proper separator
    return ', '.join(normalized_authors)