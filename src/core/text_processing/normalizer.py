"""
Text Normalization Utilities
Consolidates all normalize/canonicalize functions found throughout the codebase.
"""

import unicodedata
import re
from typing import Optional, Dict, Any
from functools import lru_cache
from dataclasses import dataclass

@dataclass
class NormalizationConfig:
    """Configuration for text normalization."""
    unicode_form: str = 'NFC'  # NFC, NFD, NFKC, NFKD
    remove_accents: bool = True
    normalize_dashes: bool = True
    normalize_quotes: bool = True
    normalize_whitespace: bool = True
    lowercase: bool = False
    strip_punctuation: bool = False

class TextNormalizer:
    """
    Consolidated text normalization utility.
    
    This class consolidates all the various normalize(), canonicalize(),
    and clean_text() functions found throughout the codebase.
    """
    
    def __init__(self, config: Optional[NormalizationConfig] = None):
        self.config = config or NormalizationConfig()
        self._setup_regex_patterns()
    
    def _setup_regex_patterns(self):
        """Setup compiled regex patterns for performance."""
        # Dash normalization patterns
        self.dash_patterns = [
            (re.compile(r'[‒–—―]'), '-'),  # Various dashes to hyphen
            (re.compile(r'[-]{2,}'), '-'),  # Multiple hyphens to single
        ]
        
        # Quote normalization patterns  
        self.quote_patterns = [
            (re.compile(r'[""''‚„‹›«»]'), '"'),  # Smart quotes to straight
            (re.compile(r'[`´]'), "'"),  # Backticks to apostrophe
        ]
        
        # Whitespace normalization
        self.whitespace_pattern = re.compile(r'\s+')
        
        # Punctuation removal (if needed)
        self.punctuation_pattern = re.compile(r'[^\w\s]')
    
    @lru_cache(maxsize=1000)
    def normalize(self, text: str) -> str:
        """
        Main normalization function.
        
        This is the primary entry point that consolidates all normalization
        logic found throughout the codebase.
        """
        if not text:
            return text
            
        # Unicode normalization
        text = self._normalize_unicode(text)
        
        # Remove accents if configured
        if self.config.remove_accents:
            text = self._remove_accents(text)
        
        # Normalize dashes
        if self.config.normalize_dashes:
            text = self._normalize_dashes(text)
        
        # Normalize quotes
        if self.config.normalize_quotes:
            text = self._normalize_quotes(text)
        
        # Normalize whitespace
        if self.config.normalize_whitespace:
            text = self._normalize_whitespace(text)
        
        # Lowercase if configured
        if self.config.lowercase:
            text = text.lower()
        
        # Strip punctuation if configured
        if self.config.strip_punctuation:
            text = self._strip_punctuation(text)
        
        return text.strip()
    
    def canonicalize(self, text: str) -> str:
        """
        Canonicalize text for consistent comparison.
        
        This function provides the same functionality as the canonicalize()
        functions found in filename_checker.py and other modules.
        """
        # Use normalization with specific config for canonicalization
        canon_config = NormalizationConfig(
            unicode_form='NFC',
            remove_accents=True,
            normalize_dashes=True,
            normalize_quotes=True,
            normalize_whitespace=True,
            lowercase=True,
            strip_punctuation=False
        )
        
        # Create temporary normalizer with canonicalization config
        temp_normalizer = TextNormalizer(canon_config)
        return temp_normalizer.normalize(text)
    
    def clean_text(self, text: str) -> str:
        """
        Clean text for processing.
        
        This provides the same functionality as various clean_text()
        functions found throughout the codebase.
        """
        # Use normalization with cleaning config
        clean_config = NormalizationConfig(
            unicode_form='NFC',
            remove_accents=False,
            normalize_dashes=True,
            normalize_quotes=False,
            normalize_whitespace=True,
            lowercase=False,
            strip_punctuation=False
        )
        
        # Create temporary normalizer with cleaning config
        temp_normalizer = TextNormalizer(clean_config)
        return temp_normalizer.normalize(text)
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode form."""
        try:
            return unicodedata.normalize(self.config.unicode_form, text)
        except Exception:
            return text
    
    def _remove_accents(self, text: str) -> str:
        """Remove accents from text."""
        try:
            # Convert to NFD and remove combining characters
            nfd_text = unicodedata.normalize('NFD', text)
            return ''.join(char for char in nfd_text 
                          if unicodedata.category(char) != 'Mn')
        except Exception:
            return text
    
    def _normalize_dashes(self, text: str) -> str:
        """Normalize various dash characters."""
        for pattern, replacement in self.dash_patterns:
            text = pattern.sub(replacement, text)
        return text
    
    def _normalize_quotes(self, text: str) -> str:
        """Normalize various quote characters."""
        for pattern, replacement in self.quote_patterns:
            text = pattern.sub(replacement, text)
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace characters."""
        return self.whitespace_pattern.sub(' ', text)
    
    def _strip_punctuation(self, text: str) -> str:
        """Strip punctuation characters."""
        return self.punctuation_pattern.sub('', text)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        return {
            'config': self.config,
            'cache_info': self.normalize.cache_info(),
            'patterns_loaded': len(self.dash_patterns) + len(self.quote_patterns)
        }

# Create default normalizer instance
default_normalizer = TextNormalizer()

# Convenience functions for backward compatibility
def normalize(text: str) -> str:
    """Convenience function for default normalization."""
    return default_normalizer.normalize(text)

def canonicalize(text: str) -> str:
    """Convenience function for canonicalization."""
    return default_normalizer.canonicalize(text)

def clean_text(text: str) -> str:
    """Convenience function for text cleaning."""
    return default_normalizer.clean_text(text)