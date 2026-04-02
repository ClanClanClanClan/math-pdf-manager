"""
Pattern Matcher Module

Pattern matching, tokenization, and text analysis functions
extracted from validators.filename_checker.py
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Set, Tuple, Optional
from core.validation import debug_print


@dataclass
class Token:
    """Represents a token in the text"""
    type: str  # 'WORD', 'PHRASE', 'PUNCT', 'MATH'
    text: str
    start: int
    end: int


class PatternMatcher:
    """Advanced pattern matching and tokenization"""
    
    def __init__(self):
        # Common patterns
        self.dash_patterns = {
            'hyphen': r'-',
            'en_dash': r'–',
            'em_dash': r'—',
            'minus': r'−',
            'soft_hyphen': r'­',
        }
        
        # Mathematical patterns
        self.math_patterns = {
            'superscript': r'[⁰¹²³⁴⁵⁶⁷⁸⁹]',
            'subscript': r'[₀₁₂₃₄₅₆₇₈₉]',
            'greek': r'[αβγδεζηθικλμνξοπρστυφχψω]',
            'operators': r'[×÷±∓∞∑∏∫∂∇]',
        }
    
    def tokenize_with_math(self, text: str, phrases: Set[str] = None, 
                          regions: List[Tuple[int, int]] = None) -> List[Token]:
        """Tokenize text with support for phrases and mathematical regions"""
        tokens = []
        phrases_set = set(phrases) if phrases else set()
        
        debug_print(f"Tokenizing: '{text}' with {len(phrases_set)} phrases")
        if phrases_set:
            compound_phrases = [p for p in phrases_set if "-" in p]
            debug_print(f"Sample compound phrases: {compound_phrases[:10]}")
        
        i = 0
        while i < len(text):
            # Skip whitespace
            if text[i].isspace():
                i += 1
                continue
            
            # Check if we're in a math region
            in_math = False
            if regions:
                for start, end in regions:
                    if start <= i < end:
                        in_math = True
                        break
            
            # Try to match longest phrase first
            matched_phrase = self._match_phrase(text, i, phrases_set)
            
            if matched_phrase:
                # Found a phrase match
                actual_text = text[i : i + len(matched_phrase)]
                tokens.append(Token("PHRASE", actual_text, i, i + len(matched_phrase)))
                debug_print(f"  Matched phrase: '{actual_text}' -> PHRASE")
                i += len(matched_phrase)
            elif in_math:
                # In math region - collect as MATH token
                start = i
                while i < len(text) and not text[i].isspace():
                    i += 1
                tokens.append(Token("MATH", text[start:i], start, i))
            else:
                # Collect regular token
                token = self._collect_token(text, i)
                tokens.append(token)
                i = token.end
        
        return tokens
    
    def _match_phrase(self, text: str, pos: int, phrases: Set[str]) -> Optional[str]:
        """Match the longest phrase at the given position"""
        matched_phrase = None
        max_phrase_len = 0
        
        for phrase in phrases:
            if (pos + len(phrase) <= len(text) and 
                text[pos : pos + len(phrase)].lower() == phrase.lower()):
                
                # Check word boundaries
                before_ok = pos == 0 or not text[pos - 1].isalnum()
                after_ok = (pos + len(phrase) >= len(text) or 
                           not text[pos + len(phrase)].isalnum())
                
                if before_ok and after_ok and len(phrase) > max_phrase_len:
                    matched_phrase = phrase
                    max_phrase_len = len(phrase)
        
        return matched_phrase
    
    def _collect_token(self, text: str, start: int) -> Token:
        """Collect a single token starting at the given position"""
        i = start
        
        if text[i].isalnum() or unicodedata.category(text[i])[0] in "LMN":
            # Word token - collect letters, marks, numbers
            while i < len(text) and (text[i].isalnum() or 
                                   unicodedata.category(text[i])[0] in "LMN" or
                                   (text[i] == '-' and i + 1 < len(text) and 
                                    text[i + 1].isalnum())):
                i += 1
            return Token("WORD", text[start:i], start, i)
        else:
            # Punctuation token
            i += 1
            return Token("PUNCT", text[start:i], start, i)
    
    def find_bad_dash_patterns(self, text: str) -> List[Tuple[int, int, str]]:
        """Find problematic dash patterns in text"""
        patterns = []
        
        # Pattern 1: Space-hyphen-space (should be em-dash or removed)
        for match in re.finditer(r'\s+-\s+', text):
            patterns.append((match.start(), match.end(), 'space-hyphen-space'))
        
        # Pattern 2: Multiple consecutive hyphens
        for match in re.finditer(r'-{2,}', text):
            patterns.append((match.start(), match.end(), 'multiple-hyphens'))
        
        # Pattern 3: Mixed dash types
        mixed_pattern = r'[' + ''.join(self.dash_patterns.values()) + r']{2,}'
        for match in re.finditer(mixed_pattern, text):
            if len(set(match.group())) > 1:  # Different dash types
                patterns.append((match.start(), match.end(), 'mixed-dashes'))
        
        return patterns
    
    def normalize_token(self, token: str) -> str:
        """Normalize a token for comparison"""
        # Convert to lowercase
        token = token.lower()
        
        # Normalize dashes
        for dash in self.dash_patterns.values():
            token = token.replace(dash, '-')
        
        # Remove trailing punctuation
        token = token.rstrip('.,;:!?')
        
        return token
    
    def is_math_token(self, token: str) -> bool:
        """Check if a token appears to be mathematical"""
        # Check for mathematical characters
        for pattern in self.math_patterns.values():
            if re.search(pattern, token):
                return True
        
        # Check for common math patterns
        math_indicators = [
            r'^\d+[a-z]$',  # 2x, 3y
            r'^[a-z]\d+$',  # x1, y2
            r'^\d+\.\d+$',  # decimal numbers
            r'^[a-z]_\d+$', # x_1, y_2
        ]
        
        for pattern in math_indicators:
            if re.match(pattern, token.lower()):
                return True
        
        return False
    
    def extract_dash_pairs(self, text: str) -> List[Tuple[int, int]]:
        """Extract positions of dash characters that might need fixing"""
        pairs = []
        
        # Find all dash-like characters
        for i, char in enumerate(text):
            if char in '-–—−‐':
                # Check if it's between author names (capital letters)
                if (i > 0 and i < len(text) - 1 and
                    text[i-1].isupper() and text[i+1].isupper()):
                    pairs.append((i, i+1))
        
        return pairs


# Module-level functions for backward compatibility
_default_matcher = PatternMatcher()

def robust_tokenize_with_math(text: str, phrases: Set[str] = None, 
                             regions: List[Tuple[int, int]] = None) -> List[Token]:
    """Tokenize text with phrase and math support"""
    return _default_matcher.tokenize_with_math(text, phrases, regions)

def find_bad_dash_patterns(text: str) -> List[Tuple[int, int, str]]:
    """Find problematic dash patterns"""
    return _default_matcher.find_bad_dash_patterns(text)

def normalize_token(token: str) -> str:
    """Normalize token for comparison"""
    return _default_matcher.normalize_token(token)

def is_math_token(token: str) -> bool:
    """Check if token is mathematical"""
    return _default_matcher.is_math_token(token)

def tokenize_with_phrases(text: str, phrases: set) -> list:
    """Simple tokenization with phrase support"""
    tokens = robust_tokenize_with_math(text, phrases)
    return [token.text for token in tokens]