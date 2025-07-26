"""
Mathematical Context Detection and Processing

This module consolidates mathematical context detection from validators/math_context.py
and validators/math_utils.py into a unified handler.
"""

import re
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class MathHandler:
    """Handle mathematical context detection and processing"""
    
    # LaTeX math delimiters
    MATH_DELIMITERS = [
        (r'\$\$', r'\$\$'),  # Display math
        (r'\$', r'\$'),      # Inline math
        (r'\\\[', r'\\\]'),  # Display math
        (r'\\\(', r'\\\)'),  # Inline math
        (r'\\begin\{equation\}', r'\\end\{equation\}'),
        (r'\\begin\{align\}', r'\\end\{align\}'),
        (r'\\begin\{displaymath\}', r'\\end\{displaymath\}'),
        (r'\\begin\{eqnarray\}', r'\\end\{eqnarray\}'),
    ]
    
    # Mathematical notation patterns
    MATH_PATTERNS = [
        # Variables with subscripts/superscripts
        r'[a-zA-Z]_\{?\w+\}?',
        r'[a-zA-Z]\^\{?\w+\}?',
        
        # Greek letters
        r'\\(?:alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|phi|chi|psi|omega)',
        r'\\(?:Alpha|Beta|Gamma|Delta|Epsilon|Zeta|Eta|Theta|Iota|Kappa|Lambda|Mu|Nu|Xi|Pi|Rho|Sigma|Tau|Phi|Chi|Psi|Omega)',
        
        # Mathematical operators
        r'\\(?:sum|prod|int|oint|partial|nabla|pm|mp|times|div|cdot|cap|cup|subset|supset|in|notin)',
        r'\\(?:forall|exists|nexists|therefore|because)',
        
        # Functions
        r'\\(?:sin|cos|tan|log|ln|exp|lim|sup|inf|max|min|det|dim|ker|deg|arcsin|arccos|arctan)',
        
        # Common expressions
        r'[a-zA-Z]\([^)]+\)',  # f(x)
        r'\d+[a-zA-Z]',         # 2x, 3y
        r'[a-zA-Z]\d+',         # x1, y2
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self._delimiter_patterns = [
            (re.compile(start), re.compile(end)) 
            for start, end in self.MATH_DELIMITERS
        ]
        self._math_patterns = [re.compile(p) for p in self.MATH_PATTERNS]
    
    def find_math_regions(self, text: str) -> List[Tuple[int, int]]:
        """
        Find mathematical regions in text (delimited by $ or LaTeX commands).
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of (start, end) tuples for math regions
        """
        regions = []
        i = 0
        
        while i < len(text):
            # Look for $ delimited math
            if text[i] == "$":
                if i + 1 < len(text) and text[i + 1] == "$":
                    # Display math $$...$$
                    start = i
                    i += 2
                    while i < len(text) - 1:
                        if text[i] == "$" and text[i + 1] == "$":
                            regions.append((start, i + 2))
                            i += 2
                            break
                        i += 1
                    else:
                        i += 1
                else:
                    # Inline math $...$
                    start = i
                    i += 1
                    while i < len(text):
                        if text[i] == "$":
                            regions.append((start, i + 1))
                            i += 1
                            break
                        i += 1
                    else:
                        i += 1
            else:
                # Look for LaTeX delimiters
                found_delimiter = False
                for start_pattern, end_pattern in self._delimiter_patterns:
                    match = start_pattern.match(text, i)
                    if match:
                        start = match.start()
                        end_pos = match.end()
                        
                        # Find matching end delimiter
                        end_match = end_pattern.search(text, end_pos)
                        if end_match:
                            regions.append((start, end_match.end()))
                            i = end_match.end()
                            found_delimiter = True
                            break
                
                if not found_delimiter:
                    i += 1
        
        return self._merge_overlapping_regions(regions)
    
    def _merge_overlapping_regions(self, regions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merge overlapping math regions"""
        if not regions:
            return []
        
        # Sort by start position
        sorted_regions = sorted(regions)
        merged = [sorted_regions[0]]
        
        for current in sorted_regions[1:]:
            last = merged[-1]
            if current[0] <= last[1]:
                # Overlapping regions, merge them
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)
        
        return merged
    
    def is_in_math_region(self, pos: int, regions: List[Tuple[int, int]]) -> bool:
        """Check if a position is within any math region"""
        for start, end in regions:
            if start <= pos < end:
                return True
        return False
    
    def has_mathematical_content(self, text: str) -> bool:
        """Check if text contains mathematical notation"""
        # Check for math delimiters
        if any(d in text for d in ['$', '\\[', '\\(', '\\begin{equation']):
            return True
        
        # Check for math patterns
        for pattern in self._math_patterns:
            if pattern.search(text):
                return True
        
        return False
    
    def should_preserve_digit(self, text: str, pos: int) -> bool:
        """
        Determine if a digit at position should be preserved (not spelled out).
        
        Args:
            text: The full text
            pos: Position of the digit
            
        Returns:
            True if digit should be preserved
        """
        # Find math regions
        math_regions = self.find_math_regions(text)
        
        # Check if in math region
        if self.is_in_math_region(pos, math_regions):
            logger.debug(f"Digit at position {pos} is in math region")
            return True
        
        # Check surrounding context for mathematical indicators
        window_size = 10
        start = max(0, pos - window_size)
        end = min(len(text), pos + window_size + 1)
        context = text[start:end]
        
        # Mathematical context indicators
        math_indicators = [
            r'[=+\-*/^]',  # Math operators
            r'[<>≤≥≠≈]',   # Comparison operators
            r'[∑∏∫∂∇]',    # Mathematical symbols
            r'x\d+|y\d+|z\d+',  # Variables with indices
            r'\d+\.\d+',   # Decimals
            r'1\d{3}',     # Years (don't spell out)
        ]
        
        for indicator in math_indicators:
            if re.search(indicator, context):
                logger.debug(f"Digit at position {pos} has mathematical context: {indicator}")
                return True
        
        return False


# Module-level functions for backward compatibility
_default_handler = MathHandler()

def find_math_regions(text: str) -> List[Tuple[int, int]]:
    """Find mathematical regions in text"""
    return _default_handler.find_math_regions(text)

def is_in_math_region(pos: int, regions: List[Tuple[int, int]]) -> bool:
    """Check if position is in math region"""
    return _default_handler.is_in_math_region(pos, regions)

def has_mathematical_content(text: str) -> bool:
    """Check if text has mathematical content"""
    return _default_handler.has_mathematical_content(text)

def should_preserve_digit(text: str, pos: int) -> bool:
    """Check if digit should be preserved"""
    return _default_handler.should_preserve_digit(text, pos)