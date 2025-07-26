#!/usr/bin/env python3
"""
Mathematical Context Detection and Processing
Extracted from filename_checker.py to improve maintainability
"""

import re
from typing import List, Tuple, Set
from .debug_utils import debug_print


def find_math_regions(text: str) -> List[Tuple[int, int]]:
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
        # Look for LaTeX style \[...\]
        elif text[i : i + 2] == "\\[":
            start = i
            i += 2
            while i < len(text) - 1:
                if text[i : i + 2] == "\\]":
                    regions.append((start, i + 2))
                    i += 2
                    break
                i += 1
            else:
                i += 1
        else:
            i += 1
    
    return regions


def is_filename_math_token(token: str) -> bool:
    """
    Check if a token contains mathematical symbols.
    
    Args:
        token: Text token to check
        
    Returns:
        True if token contains math symbols
    """
    math_symbols = (
        "\u2211\u220f\u222b\u221e\u00b1\u00f7\u00d7\u2264\u2265\u2260"
        "\u2208\u2209\u222a\u2229\u2205\u221a\u2032\u2033\u2202\u2207"
        "\u2248\u2245\u2261\u2282\u2283\u2286\u2287\u2295\u2297\u22a5\u22a4"
    )
    
    return any(c in token for c in math_symbols)


def contains_math(text: str) -> bool:
    """
    Check if text contains mathematical content.
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains math regions or symbols
    """
    return bool(find_math_regions(text)) or any(
        is_filename_math_token(word) for word in text.split()
    )


def iterate_nonmath_segments(text: str, regions: List[Tuple[int, int]]):
    """
    Iterate over non-mathematical segments of text.
    
    Args:
        text: Input text
        regions: List of (start, end) tuples for math regions
        
    Yields:
        Tuples of (start, end, segment) for non-math segments
    """
    if not regions:
        yield 0, len(text), text
        return
    
    # Sort regions by start position
    sorted_regions = sorted(regions)
    
    pos = 0
    for start, end in sorted_regions:
        if pos < start:
            # Yield segment before math region
            yield pos, start, text[pos:start]
        pos = max(pos, end)
    
    # Yield remaining segment after last math region
    if pos < len(text):
        yield pos, len(text), text[pos:]


def is_in_spans(start: int, end: int, spans: List[Tuple[int, int]]) -> bool:
    """
    Check if a range overlaps with any span in the list.
    
    Args:
        start: Start position
        end: End position
        spans: List of (start, end) tuples to check against
        
    Returns:
        True if range overlaps with any span
    """
    for span_start, span_end in spans:
        if not (end <= span_start or start >= span_end):
            return True
    return False


def fix_ellipsis(text: str, regions: List[Tuple[int, int]], spans: List[Tuple[int, int]] = None) -> str:
    """
    Fix ellipsis (...) in non-mathematical text.
    
    Args:
        text: Input text
        regions: Mathematical regions to avoid
        spans: Exception spans to avoid
        
    Returns:
        Text with ellipsis replaced by …
    """
    spans = spans or []
    
    def make_repl(offset):
        def repl(m):
            s, e = m.span()
            abs_s, abs_e = s + offset, e + offset
            if is_in_spans(abs_s, abs_e, spans):
                return m.group()
            return "…"
        return repl
    
    out, last = [], 0
    for s, e, seg in iterate_nonmath_segments(text, regions):
        transformed = re.sub(r"(?<!.)\.\.\.(?!\.)", make_repl(s), seg)
        out.append(text[last:s] + transformed)
        last = e
    out.append(text[last:])
    result = "".join(out)
    return result


def fix_superscripts_subscripts(text: str, regions: List[Tuple[int, int]], spans: List[Tuple[int, int]] = None) -> str:
    """
    Transform superscript and subscript notation in non-mathematical text.
    
    Args:
        text: Input text
        regions: Mathematical regions to avoid
        spans: Exception spans to avoid
        
    Returns:
        Text with transformed super/subscripts
    """
    from .unicode_constants import SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP
    
    spans = spans or []
    
    def sup(base: str, exp: str) -> str:
        return base + "".join(SUPERSCRIPT_MAP.get(c, c) for c in exp)
    
    def sub(base: str, subscript: str) -> str:
        return base + "".join(SUBSCRIPT_MAP.get(c, c) for c in subscript)
    
    def transform_segment(seg: str, abs_off: int) -> str:
        # Transform superscripts
        seg = re.sub(
            r"\b([A-Za-z])\^([0-9A-Za-z+\-]+)\b",
            lambda m: sup(m.group(1), m.group(2)),
            seg,
        )
        seg = re.sub(
            r"\b([A-Za-z])\^\{([^}]+)\}",
            lambda m: sup(m.group(1), m.group(2)),
            seg
        )
        
        # Transform subscripts
        seg = re.sub(
            r"\b([A-Za-z])_([0-9A-Za-z+\-]+)\b",
            lambda m: sub(m.group(1), m.group(2)),
            seg,
        )
        seg = re.sub(
            r"\b([A-Za-z])_\{([^}]+)\}",
            lambda m: sub(m.group(1), m.group(2)),
            seg
        )
        
        # Transform mathbb
        repls = []
        for m in re.finditer(r"\\mathbb\{([A-Z])\}", seg):
            if not is_in_spans(abs_off + m.start(), abs_off + m.end(), spans):
                replacement = MATHBB_MAP.get(m.group(1), m.group(0))
                repls.append((m.start(), m.end(), replacement))
        
        for s, e, r in sorted(repls, key=lambda x: x[0], reverse=True):
            seg = seg[:s] + r + seg[e:]
        
        return seg
    
    out, last = [], 0
    for s, e, seg in iterate_nonmath_segments(text, regions):
        transformed = transform_segment(seg, s)
        out.append(text[last:s] + transformed)
        last = e
    out.append(text[last:])
    
    result = "".join(out)
    return result


def detect_math_context(text: str) -> dict:
    """
    Detect mathematical context in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with math context information
    """
    regions = find_math_regions(text)
    
    context = {
        'has_math_regions': bool(regions),
        'math_regions': regions,
        'has_math_symbols': any(is_filename_math_token(word) for word in text.split()),
        'math_ratio': 0.0,
        'complexity': 'none'
    }
    
    if regions:
        math_chars = sum(end - start for start, end in regions)
        context['math_ratio'] = math_chars / len(text) if text else 0.0
        
        if context['math_ratio'] > 0.5:
            context['complexity'] = 'high'
        elif context['math_ratio'] > 0.2:
            context['complexity'] = 'medium'
        else:
            context['complexity'] = 'low'
    
    return context


def is_likely_math_filename(filename: str) -> bool:
    """
    Check if filename is likely mathematical based on patterns.
    
    Args:
        filename: Filename to check
        
    Returns:
        True if filename appears to be mathematical
    """
    # Check for mathematical indicators
    math_indicators = [
        'theorem', 'lemma', 'proof', 'equation', 'formula',
        'calculus', 'algebra', 'geometry', 'topology', 'analysis',
        'differential', 'integral', 'matrix', 'vector', 'function',
        'limit', 'derivative', 'convergence', 'manifold', 'space'
    ]
    
    filename_lower = filename.lower()
    
    # Check for math keywords
    if any(indicator in filename_lower for indicator in math_indicators):
        return True
    
    # Check for mathematical symbols
    if contains_math(filename):
        return True
    
    # Check for mathematical notation patterns
    math_patterns = [
        r'[A-Za-z]\^[0-9]',  # Superscripts
        r'[A-Za-z]_[0-9]',   # Subscripts
        r'\\[a-zA-Z]+',      # LaTeX commands
        r'\$.*\$',           # Dollar math
        r'[α-ωΑ-Ω]',         # Greek letters
    ]
    
    for pattern in math_patterns:
        if re.search(pattern, filename):
            return True
    
    return False