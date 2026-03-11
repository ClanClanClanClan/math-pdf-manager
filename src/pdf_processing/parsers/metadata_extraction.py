#!/usr/bin/env python3
"""
Metadata Extraction Methods
Extracted from monolithic parsers.py for better modularity
"""

import logging
from typing import Tuple, List, Dict, Any
import regex as re

from ..models import TextBlock, DocumentStructure
from ..constants import PDFConstants

# Get logger
logger = logging.getLogger(__name__)

# Try to import the layout analyzer (created in Phase 3)
try:
    from .advanced_layout_analyzer import AdvancedLayoutAnalyzer, TextElement
    _LAYOUT_ANALYZER = AdvancedLayoutAnalyzer()
    _LAYOUT_AVAILABLE = True
except ImportError:
    _LAYOUT_AVAILABLE = False


def _text_blocks_have_font_metrics(text_blocks: List[TextBlock]) -> bool:
    """Check whether text blocks contain real font-size data.

    If all blocks have ``font_size == 12.0`` and ``font_name == ""``, the data
    is placeholder (from the old extraction path) and layout analysis would be
    meaningless.
    """
    if not text_blocks or len(text_blocks) < 3:
        return False

    distinct_sizes = set()
    for b in text_blocks[:30]:
        distinct_sizes.add(round(b.font_size, 1))
        if b.font_name and b.font_name.strip():
            return True  # real font name → real data

    # At least 2 distinct sizes means real extraction
    return len(distinct_sizes) >= 2


def _blocks_to_text_elements(text_blocks: List[TextBlock]) -> List[TextElement]:
    """Convert TextBlock objects to TextElement objects for the layout analyzer."""
    elements = []
    for i, b in enumerate(text_blocks):
        flags = 0
        if b.is_bold:
            flags |= 16
        if b.is_italic:
            flags |= 2
        elements.append(TextElement(
            text=b.text,
            bbox=(b.x, b.y, b.x + b.width, b.y + b.height),
            font_name=b.font_name,
            font_size=b.font_size,
            font_flags=flags,
            page_number=b.page_num,
            line_number=i,
        ))
    return elements


def extract_title_multi_method(
    full_text: str, text_blocks: List[TextBlock], structure: DocumentStructure,
    repository_extractors: Dict[str, Any], normalise_title_func
) -> Tuple[str, float]:
    """Extract title using multiple methods with better reliability"""

    logger.debug(f"Extracting title from text preview: {full_text[:100]}...")

    # Method 1: Repository-specific extractor
    if (
        structure.repository_type
        and structure.repository_type in repository_extractors
    ):
        extractor = repository_extractors[structure.repository_type]
        try:
            title, confidence = extractor.extract_title(full_text, text_blocks)

            # If the repository extractor produced something usable keep it,
            # otherwise fall through to the heuristic path.
            if title and len(title.strip()) >= PDFConstants.MIN_TITLE_LENGTH:
                title = normalise_title_func(title)
                logger.debug(
                    f"Repository extractor found title: {title} "
                    f"(conf: {confidence})"
                )
                return title, confidence
        except Exception as e:
            logger.debug(f"Repository extractor error: {e}")

    # Method 2: Layout-based title extraction (when we have real font metrics)
    if _LAYOUT_AVAILABLE and _text_blocks_have_font_metrics(text_blocks):
        try:
            elements = _blocks_to_text_elements(text_blocks)
            layout = _LAYOUT_ANALYZER.analyze_layout(elements)
            if layout.title_candidates and layout.confidence_score > 0.5:
                title = " ".join(t.text for t in layout.title_candidates)
                title = normalise_title_func(title)
                logger.debug(f"Layout analyzer found title: {title} (conf: {layout.confidence_score})")
                return title, layout.confidence_score
        except Exception as e:
            logger.debug(f"Layout-based title extraction failed: {e}")

    # Method 3: Heuristic title extraction (text-line scanning fallback)
    title, confidence = extract_title_heuristic(full_text, text_blocks)
    if title and confidence > 0.4:
        title = normalise_title_func(title)
        return title, confidence

    logger.debug("No title extraction method succeeded")
    return "Unknown Title", 0.0


def extract_authors_multi_method(
    full_text: str, text_blocks: List[TextBlock], structure: DocumentStructure,
    repository_extractors: Dict[str, Any]
) -> Tuple[str, float]:
    """Extract authors using multiple methods with better reliability"""

    # Method 1: Repository-specific extractor
    if (
        structure.repository_type
        and structure.repository_type in repository_extractors
    ):
        extractor = repository_extractors[structure.repository_type]
        try:
            authors, confidence = extractor.extract_authors(full_text, text_blocks)
            if authors and confidence > 0.5:
                return authors, confidence
        except Exception as e:
            logger.debug(f"Repository extractor error: {e}")

    # Method 2: Layout-based author extraction (when we have real font metrics)
    if _LAYOUT_AVAILABLE and _text_blocks_have_font_metrics(text_blocks):
        try:
            elements = _blocks_to_text_elements(text_blocks)
            layout = _LAYOUT_ANALYZER.analyze_layout(elements)
            if layout.author_candidates:
                authors = "; ".join(a.text for a in layout.author_candidates)
                confidence = min(0.8, layout.confidence_score + 0.1)
                logger.debug(f"Layout analyzer found authors: {authors} (conf: {confidence})")
                return authors, confidence
        except Exception as e:
            logger.debug(f"Layout-based author extraction failed: {e}")

    # Method 3: Heuristic author extraction (text-line scanning fallback)
    authors, confidence = extract_authors_heuristic(full_text)
    if authors and confidence > 0.4:
        return authors, confidence

    return "Unknown", 0.0


def extract_title_heuristic(
    full_text: str, text_blocks: List[TextBlock]
) -> Tuple[str, float]:
    """Improved heuristic title extraction"""
    lines = full_text.split("\n")

    # First pass: Look for well-structured titles
    for i, line in enumerate(lines[:15]):
        line = line.strip()
        if not line or len(line) < PDFConstants.MIN_TITLE_LENGTH:
            continue

        # Score this line as potential title
        score = score_title_line(line, i)

        if score > 0.5:  # High confidence threshold
            return clean_title(line), score

    # Second pass: Look for reasonable titles with lower threshold
    for i, line in enumerate(lines[:15]):
        line = line.strip()
        if not line or len(line) < PDFConstants.MIN_TITLE_LENGTH:
            continue

        score = score_title_line(line, i)

        if score > 0.3:  # Lower threshold
            # Try to extract just the title part from longer lines
            cleaned_title = extract_title_from_line(line)
            return cleaned_title, score

    # Fallback: look for any substantial line that could be a title
    for i, line in enumerate(lines[:20]):
        line = line.strip()
        if 10 <= len(line) <= 200:  # Broader length range
            # Simple check for title-like content
            if any(
                word in line.lower()
                for word in [
                    "theory",
                    "model",
                    "approach",
                    "method",
                    "algorithm",
                    "system",
                    "framework",
                    "analysis",
                ]
            ):
                cleaned_title = extract_title_from_line(line)
                return cleaned_title, 0.3

    return "Unknown Title", 0.0


def extract_title_from_line(line: str) -> str:
    """Extract clean title from a potentially messy line"""
    line = line.strip()
    logger.debug(f"Extracting title from line: {line[:100]}...")

    # Remove common prefixes/artifacts that shouldn't be in titles
    original_line = line

    # Remove arXiv identifiers and metadata
    line = re.sub(r"arxiv:\d{4}\.\d{4,5}v?\d*\s*", "", line, flags=re.IGNORECASE)
    # Remove category codes
    line = re.sub(r"\[[a-z]+\.[a-z]+\]\s*", "", line, flags=re.IGNORECASE)

    # Remove journal names at the beginning
    journal_prefixes = [
        r"^nature\s+machine\s+intelligence\s*",
        r"^nature\s+\w+\s*",
        r"^proceedings\s+of\s+.*?\s*",
        r"^journal\s+of\s+.*?\s*",
        r"^ieee\s+transactions\s+on\s+.*?\s*",
    ]
    for pattern in journal_prefixes:
        line = re.sub(pattern, "", line, flags=re.IGNORECASE)

    # If the line is very long, extract just the title portion
    if len(line) > 200:
        # Look for where authors/institutions start
        author_patterns = [
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\s*,",  # John Smith,
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s*,",  # John A. Smith,
        ]

        earliest_author_pos = len(line)
        for pattern in author_patterns:
            match = re.search(pattern, line)
            if match:
                earliest_author_pos = min(earliest_author_pos, match.start())

        # Check for institutions which often follow author names
        institution_indicators = [
            r"\b(?:University|Institute|College|School|Department)\b",
            r"\b(?:MIT|IBM|Google|Microsoft|Stanford|Harvard|Cambridge)\b",
        ]

        for pattern in institution_indicators:
            match = re.search(pattern, line, re.IGNORECASE)
            if match and match.start() > 30:
                text_before = line[: match.start()]
                name_match = re.search(
                    r"[A-Z][a-z]+\s+[A-Z][a-z]+", text_before[-50:]
                )
                if name_match:
                    author_start = text_before.rfind(name_match.group())
                    if author_start > 30:
                        earliest_author_pos = min(earliest_author_pos, author_start)

        # Extract title portion before authors/institutions
        if earliest_author_pos < len(line) and earliest_author_pos > 30:
            line = line[:earliest_author_pos].strip()
        else:
            # Look for common end-of-title patterns
            title_end_patterns = [
                r"\s+abstract\s*:",
                r"\s+keywords\s*:",
                r"\s+introduction\s*:",
                r"\s+authors?\s*:",
                r"\s+[A-Z][a-z]+\s+[A-Z][a-z]+,",
                r"\s+university\s+",
                r"\s+institute\s+",
                r"\s+department\s+",
            ]

            for pattern in title_end_patterns:
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if match:
                    potential_title = line[: match.start()].strip()
                    if len(potential_title) >= 10:
                        line = potential_title
                        break

            # If still too long, extract first reasonable portion
            if len(line) > 150:
                sentences = re.split(r"[.!?]\s+", line)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if 15 <= len(sentence) <= 150:
                        words = sentence.split()
                        if words and len(words) >= 3:
                            capital_ratio = sum(
                                1 for word in words if word and word[0].isupper()
                            ) / len(words)
                            if capital_ratio > 0.3:
                                line = sentence
                                break

    # Final cleanup
    line = clean_title(line)
    
    # Validate result
    if len(line) < PDFConstants.MIN_TITLE_LENGTH:
        logger.debug(f"Title too short after extraction: '{line}'")
        return original_line[:100] if len(original_line) > 10 else "Unknown Title"
    
    if len(line) > PDFConstants.MAX_TITLE_LEN:
        line = line[:PDFConstants.MAX_TITLE_LEN].strip()
    
    logger.debug(f"Final extracted title: '{line}'")
    return line


def extract_authors_heuristic(full_text: str) -> Tuple[str, float]:
    """Heuristic author extraction from text"""
    lines = full_text.split("\n")
    
    # Look for author lines in the first few lines
    for i, line in enumerate(lines[:10]):
        line = line.strip()
        if not line:
            continue
            
        # Common author patterns
        author_patterns = [
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*$",  # Simple names
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)\s*$",  # Multiple authors
            r"^([A-Z][a-z]+(?:\s+[A-Z]\.|[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z]\.|[A-Z][a-z]+)*)*)\s*$",  # With initials
        ]
        
        for pattern in author_patterns:
            match = re.match(pattern, line)
            if match:
                authors = match.group(1)
                # Basic validation
                if 5 <= len(authors) <= 200:
                    return authors, 0.7
    
    return "Unknown", 0.0


def score_title_line(line: str, line_index: int) -> float:
    """Score a line as a potential title"""
    score = 0.0
    
    # Position weight (earlier lines more likely to be titles)
    position_score = max(0, 1.0 - line_index * 0.1)
    score += position_score * 0.3
    
    # Length weight (reasonable title length)
    length = len(line)
    if 20 <= length <= 150:
        length_score = 1.0
    elif 10 <= length <= 200:
        length_score = 0.7
    else:
        length_score = 0.3
    score += length_score * 0.2
    
    # Capitalization patterns
    words = line.split()
    if words:
        capital_words = sum(1 for word in words if word and word[0].isupper())
        capital_ratio = capital_words / len(words)
        
        if 0.3 <= capital_ratio <= 0.8:
            score += 0.2
        elif capital_ratio > 0.8:
            score += 0.1  # Might be all caps (less desirable)
    
    # Content indicators
    title_indicators = [
        'analysis', 'approach', 'study', 'method', 'algorithm', 'system',
        'framework', 'theory', 'model', 'application', 'evaluation'
    ]
    
    line_lower = line.lower()
    indicator_count = sum(1 for indicator in title_indicators if indicator in line_lower)
    score += min(indicator_count * 0.1, 0.3)
    
    return min(score, 1.0)


def clean_title(title: str) -> str:
    """Clean and normalize a title"""
    title = title.strip()
    
    # Remove common artifacts
    title = re.sub(r'^\d+\.\s*', '', title)  # Remove leading numbers
    title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
    title = re.sub(r'^[^\w]+', '', title)  # Remove leading non-word chars
    title = re.sub(r'[^\w\s\-,.!?():;]+$', '', title)  # Remove trailing artifacts
    
    return title.strip()


# Export functions
__all__ = [
    'extract_title_multi_method',
    'extract_authors_multi_method',
    'extract_title_heuristic',
    'extract_title_from_line',
    'extract_authors_heuristic',
    'score_title_line',
    'clean_title'
]