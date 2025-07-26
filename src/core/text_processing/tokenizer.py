"""
Text Tokenization Utilities
Consolidates tokenization functions found throughout the codebase.
"""

import re
from typing import List, Optional, Dict, Set, Tuple
from functools import lru_cache
from dataclasses import dataclass
from enum import Enum

class TokenType(Enum):
    """Token types for academic text processing."""
    WORD = "word"
    PUNCTUATION = "punctuation"
    WHITESPACE = "whitespace"
    MATH = "math"
    LATEX = "latex"
    CITATION = "citation"
    URL = "url"
    EMAIL = "email"
    FILENAME = "filename"
    UNKNOWN = "unknown"

@dataclass
class Token:
    """Token representation with type and position information."""
    text: str
    type: TokenType
    start: int
    end: int
    line: Optional[int] = None
    column: Optional[int] = None

@dataclass
class TokenizerConfig:
    """Configuration for text tokenization."""
    preserve_whitespace: bool = False
    extract_math: bool = True
    extract_latex: bool = True
    extract_citations: bool = True
    extract_urls: bool = True
    extract_emails: bool = True
    min_word_length: int = 1
    max_word_length: int = 50
    split_contractions: bool = False
    split_hyphens: bool = False

class TextTokenizer:
    """
    Consolidated text tokenization utility.
    
    This class consolidates tokenization functions found throughout
    the codebase, particularly for academic paper processing.
    """
    
    def __init__(self, config: Optional[TokenizerConfig] = None):
        self.config = config or TokenizerConfig()
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Setup compiled regex patterns for tokenization."""
        
        # Word patterns (handles contractions and hyphenated compounds)
        self.word_pattern = re.compile(
            r"\b\w+(?:'\w+)?(?:[-–—]\w+(?:'\w+)?)*\b",
            re.UNICODE
        )
        
        # Academic-specific patterns
        self.math_pattern = re.compile(
            r'\$[^$]+\$|\\\[[^\]]+\\\]|\\\([^)]+\\\)',
            re.DOTALL
        )
        
        self.latex_pattern = re.compile(
            r'\\[a-zA-Z]+(?:\s*\{[^}]*\})?',
            re.UNICODE
        )
        
        self.citation_pattern = re.compile(
            r'\\cite\{[^}]+\}|\\citep?\{[^}]+\}|\[[^\]]*\d+[^\]]*\]',
            re.UNICODE
        )
        
        # URL and email patterns
        self.url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+',
            re.IGNORECASE
        )
        
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        )
        
        # Filename patterns
        self.filename_pattern = re.compile(
            r'\b[\w\-_.]+\.[a-zA-Z]{2,4}\b',
            re.UNICODE
        )
        
        # Punctuation and whitespace
        self.punctuation_pattern = re.compile(r'[^\w\s]', re.UNICODE)
        self.whitespace_pattern = re.compile(r'\s+', re.UNICODE)
        
        # Special academic characters
        self.academic_chars = re.compile(
            r'[α-ωΑ-Ωμπσλδθφγβετκρξψχζην∑∏∫∂∇∆∞±≤≥≠≈∈∉∪∩⊂⊃∀∃∧∨¬→←↔↕↑↓]',
            re.UNICODE
        )
    
    @lru_cache(maxsize=500)
    def tokenize(self, text: str) -> List[Token]:
        """
        Tokenize text into academic tokens.
        
        Returns list of tokens with type and position information.
        """
        if not text:
            return []
        
        tokens = []
        processed_spans = set()
        
        # Process special tokens first (math, LaTeX, citations, etc.)
        if self.config.extract_math:
            tokens.extend(self._extract_tokens(text, self.math_pattern, TokenType.MATH, processed_spans))
        
        if self.config.extract_latex:
            tokens.extend(self._extract_tokens(text, self.latex_pattern, TokenType.LATEX, processed_spans))
        
        if self.config.extract_citations:
            tokens.extend(self._extract_tokens(text, self.citation_pattern, TokenType.CITATION, processed_spans))
        
        if self.config.extract_urls:
            tokens.extend(self._extract_tokens(text, self.url_pattern, TokenType.URL, processed_spans))
        
        if self.config.extract_emails:
            tokens.extend(self._extract_tokens(text, self.email_pattern, TokenType.EMAIL, processed_spans))
        
        # Extract filenames
        tokens.extend(self._extract_tokens(text, self.filename_pattern, TokenType.FILENAME, processed_spans))
        
        # Extract words from remaining text
        tokens.extend(self._extract_words(text, processed_spans))
        
        # Extract punctuation and whitespace if configured
        if self.config.preserve_whitespace:
            tokens.extend(self._extract_punctuation_whitespace(text, processed_spans))
        
        # Sort tokens by position
        tokens.sort(key=lambda t: (t.start, t.end))
        
        return tokens
    
    def _extract_tokens(self, text: str, pattern: re.Pattern, token_type: TokenType, processed_spans: Set[Tuple[int, int]]) -> List[Token]:
        """Extract tokens using a specific pattern."""
        tokens = []
        
        for match in pattern.finditer(text):
            start, end = match.span()
            
            # Skip if already processed
            if any(s <= start < e or s < end <= e for s, e in processed_spans):
                continue
            
            tokens.append(Token(
                text=match.group(),
                type=token_type,
                start=start,
                end=end
            ))
            
            processed_spans.add((start, end))
        
        return tokens
    
    def _extract_words(self, text: str, processed_spans: Set[Tuple[int, int]]) -> List[Token]:
        """Extract word tokens from unprocessed text."""
        tokens = []
        
        for match in self.word_pattern.finditer(text):
            start, end = match.span()
            
            # Skip if already processed
            if any(s <= start < e or s < end <= e for s, e in processed_spans):
                continue
            
            word = match.group()
            
            # Apply word length filters
            if len(word) < self.config.min_word_length or len(word) > self.config.max_word_length:
                continue
            
            # Handle contractions if configured
            if self.config.split_contractions and "'" in word:
                tokens.extend(self._split_contraction(word, start))
            # Handle hyphens if configured
            elif self.config.split_hyphens and any(c in word for c in ['-', '–', '—']):
                tokens.extend(self._split_hyphenated(word, start))
            else:
                tokens.append(Token(
                    text=word,
                    type=TokenType.WORD,
                    start=start,
                    end=end
                ))
            
            processed_spans.add((start, end))
        
        return tokens
    
    def _split_contraction(self, word: str, start: int) -> List[Token]:
        """Split contractions into separate tokens."""
        tokens = []
        parts = word.split("'")
        
        current_pos = start
        for i, part in enumerate(parts):
            if part:
                tokens.append(Token(
                    text=part,
                    type=TokenType.WORD,
                    start=current_pos,
                    end=current_pos + len(part)
                ))
                current_pos += len(part)
            
            # Add apostrophe as punctuation (except for last part)
            if i < len(parts) - 1:
                tokens.append(Token(
                    text="'",
                    type=TokenType.PUNCTUATION,
                    start=current_pos,
                    end=current_pos + 1
                ))
                current_pos += 1
        
        return tokens
    
    def _split_hyphenated(self, word: str, start: int) -> List[Token]:
        """Split hyphenated words into separate tokens."""
        tokens = []
        
        # Split on various dash types
        parts = re.split(r'([-–—])', word)
        
        current_pos = start
        for part in parts:
            if part:
                token_type = TokenType.PUNCTUATION if part in ['-', '–', '—'] else TokenType.WORD
                tokens.append(Token(
                    text=part,
                    type=token_type,
                    start=current_pos,
                    end=current_pos + len(part)
                ))
                current_pos += len(part)
        
        return tokens
    
    def _extract_punctuation_whitespace(self, text: str, processed_spans: Set[Tuple[int, int]]) -> List[Token]:
        """Extract punctuation and whitespace tokens."""
        tokens = []
        
        # Extract punctuation
        for match in self.punctuation_pattern.finditer(text):
            start, end = match.span()
            
            # Skip if already processed
            if any(s <= start < e or s < end <= e for s, e in processed_spans):
                continue
            
            tokens.append(Token(
                text=match.group(),
                type=TokenType.PUNCTUATION,
                start=start,
                end=end
            ))
        
        # Extract whitespace
        for match in self.whitespace_pattern.finditer(text):
            start, end = match.span()
            
            # Skip if already processed
            if any(s <= start < e or s < end <= e for s, e in processed_spans):
                continue
            
            tokens.append(Token(
                text=match.group(),
                type=TokenType.WHITESPACE,
                start=start,
                end=end
            ))
        
        return tokens
    
    def extract_words(self, text: str) -> List[str]:
        """
        Extract just the words from text.
        
        Provides backward compatibility with existing extract_words functions.
        """
        tokens = self.tokenize(text)
        return [token.text for token in tokens if token.type == TokenType.WORD]
    
    def extract_academic_tokens(self, text: str) -> Dict[str, List[str]]:
        """
        Extract academic-specific tokens grouped by type.
        
        Returns dictionary with token types as keys and lists of tokens as values.
        """
        tokens = self.tokenize(text)
        
        result = {}
        for token in tokens:
            token_type = token.type.value
            if token_type not in result:
                result[token_type] = []
            result[token_type].append(token.text)
        
        return result
    
    def get_token_counts(self, text: str) -> Dict[str, int]:
        """Get count of tokens by type."""
        tokens = self.tokenize(text)
        
        counts = {}
        for token in tokens:
            token_type = token.type.value
            counts[token_type] = counts.get(token_type, 0) + 1
        
        return counts
    
    def find_academic_patterns(self, text: str) -> Dict[str, List[Dict[str, any]]]:
        """
        Find academic writing patterns in text.
        
        Returns patterns like repeated words, long sentences, etc.
        """
        tokens = self.tokenize(text)
        words = [t.text.lower() for t in tokens if t.type == TokenType.WORD]
        
        patterns = {
            'repeated_words': self._find_repeated_words(words),
            'long_words': [w for w in words if len(w) > 15],
            'academic_chars': [t.text for t in tokens if self.academic_chars.search(t.text)],
            'citations': [t.text for t in tokens if t.type == TokenType.CITATION],
            'math_expressions': [t.text for t in tokens if t.type == TokenType.MATH]
        }
        
        return patterns
    
    def _find_repeated_words(self, words: List[str]) -> List[Dict[str, any]]:
        """Find repeated words in close proximity."""
        repeated = []
        
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                repeated.append({
                    'word': words[i],
                    'position': i,
                    'type': 'consecutive'
                })
        
        return repeated
    
    def get_stats(self) -> Dict[str, any]:
        """Get tokenization statistics."""
        return {
            'config': self.config,
            'tokenize_cache_info': self.tokenize.cache_info(),
            'patterns_loaded': sum([
                1 if hasattr(self, attr) else 0 
                for attr in ['word_pattern', 'math_pattern', 'latex_pattern', 
                           'citation_pattern', 'url_pattern', 'email_pattern']
            ])
        }

# Create default tokenizer instance
default_tokenizer = TextTokenizer()

# Convenience functions for backward compatibility
def tokenize(text: str) -> List[Token]:
    """Convenience function for tokenization."""
    return default_tokenizer.tokenize(text)

def extract_words(text: str) -> List[str]:
    """Convenience function for word extraction."""
    return default_tokenizer.extract_words(text)

def extract_academic_tokens(text: str) -> Dict[str, List[str]]:
    """Convenience function for academic token extraction."""
    return default_tokenizer.extract_academic_tokens(text)