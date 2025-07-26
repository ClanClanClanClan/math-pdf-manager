"""
Mathematical context detection

This module detects mathematical expressions and notation in text,
helping to prevent false positives in spell checking and validation.
"""
import re
from typing import List, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MathContextDetector:
    """Detect mathematical context in text"""
    
    # LaTeX math delimiters
    MATH_DELIMITERS = [
        (r'\$\$', r'\$\$'),  # Display math
        (r'\$', r'\$'),      # Inline math
        (r'\\\[', r'\\\]'),  # Display math
        (r'\\\(', r'\\\)'),  # Inline math
        (r'\\begin\{equation\}', r'\\end\{equation\}'),
        (r'\\begin\{align\}', r'\\end\{align\}'),
    ]
    
    # Mathematical notation patterns
    MATH_PATTERNS = [
        # Variables with subscripts/superscripts
        r'[a-zA-Z]_\{?\w+\}?',
        r'[a-zA-Z]\^\{?\w+\}?',
        
        # Greek letters
        r'\\(?:alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|phi|chi|psi|omega)',
        
        # Mathematical operators
        r'\\(?:sum|prod|int|oint|partial|nabla|pm|mp|times|div|cdot|cap|cup|subset|supset|in|notin)',
        
        # Functions
        r'\\(?:sin|cos|tan|log|ln|exp|lim|sup|inf|max|min|det|dim|ker|deg)',
        
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
        Find regions containing mathematical expressions.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (start, end) positions of math regions
        """
        regions = []
        
        # Find delimited math regions
        for start_pattern, end_pattern in self._delimiter_patterns:
            pos = 0
            while True:
                start_match = start_pattern.search(text, pos)
                if not start_match:
                    break
                
                end_match = end_pattern.search(text, start_match.end())
                if not end_match:
                    break
                
                regions.append((start_match.start(), end_match.end()))
                pos = end_match.end()
        
        # Find inline math patterns
        for pattern in self._math_patterns:
            for match in pattern.finditer(text):
                regions.append((match.start(), match.end()))
        
        # Merge overlapping regions
        return self._merge_regions(regions)
    
    def _merge_regions(self, regions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merge overlapping regions"""
        if not regions:
            return []
        
        # Sort by start position
        sorted_regions = sorted(regions)
        merged = [sorted_regions[0]]
        
        for start, end in sorted_regions[1:]:
            last_start, last_end = merged[-1]
            
            if start <= last_end:
                # Overlapping, merge
                merged[-1] = (last_start, max(last_end, end))
            else:
                # Non-overlapping, add new region
                merged.append((start, end))
        
        return merged
    
    def is_math_context(self, text: str, position: int) -> bool:
        """
        Check if a position in text is within mathematical context.
        
        Args:
            text: Full text
            position: Position to check
            
        Returns:
            True if position is within math context
        """
        math_regions = self.find_math_regions(text)
        
        for start, end in math_regions:
            if start <= position < end:
                return True
        
        return False
    
    def contains_math(self, text: str) -> bool:
        """
        Check if text contains any mathematical expressions.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains math
        """
        return len(self.find_math_regions(text)) > 0
    
    def extract_non_math_text(self, text: str) -> str:
        """
        Extract text that is not within mathematical regions.
        
        Args:
            text: Original text
            
        Returns:
            Text with math regions removed
        """
        math_regions = self.find_math_regions(text)
        
        if not math_regions:
            return text
        
        result = []
        last_end = 0
        
        for start, end in math_regions:
            # Add text before this math region
            result.append(text[last_end:start])
            last_end = end
        
        # Add remaining text
        result.append(text[last_end:])
        
        return ' '.join(result)
