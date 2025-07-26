#!/usr/bin/env python3
"""
Text Extraction Methods
Extracted from monolithic parsers.py for better modularity
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from ..models import TextBlock
from ..utilities import clean_text_advanced

# Get logger
logger = logging.getLogger(__name__)

# PDF library availability
PDF_LIBRARIES = {}
try:
    import fitz
    PDF_LIBRARIES["pymupdf"] = fitz
except ImportError:
    PDF_LIBRARIES["pymupdf"] = None

try:
    import pdfplumber
    PDF_LIBRARIES["pdfplumber"] = pdfplumber
except ImportError:
    PDF_LIBRARIES["pdfplumber"] = None

try:
    from pdfminer.high_level import extract_text
    PDF_LIBRARIES["pdfminer"] = extract_text
except ImportError:
    PDF_LIBRARIES["pdfminer"] = None


def multi_engine_extraction(pdf_file: Path, config: dict, **kwargs) -> List[Dict[str, Any]]:
    """
    Multi-engine text extraction with quality scoring.
    
    Args:
        pdf_file: Path to PDF file
        config: Configuration dict
        **kwargs: Additional options
        
    Returns:
        List of extraction results with quality scores
    """
    results = []
    
    # Try each extraction method
    extraction_methods = [
        ("pymupdf", extract_with_pymupdf),
        ("pdfplumber", extract_with_pdfplumber),
        ("pdfminer", extract_with_pdfminer),
        ("text_file", extract_as_text_file),
    ]
    
    for method_name, method_func in extraction_methods:
        try:
            result = method_func(pdf_file, config)
            if result:
                text, blocks, page_count = result
                quality_score = calculate_text_quality(text)
                
                results.append({
                    'method': method_name,
                    'text': text,
                    'blocks': blocks,
                    'page_count': page_count,
                    'quality_score': quality_score
                })
                
                logger.debug(f"{method_name} extraction: {len(text)} chars, quality: {quality_score:.3f}")
        except Exception as e:
            logger.debug(f"{method_name} extraction failed: {e}")
    
    # Sort by quality score (descending)
    results.sort(key=lambda x: x['quality_score'], reverse=True)
    
    return results


def extract_with_pymupdf(pdf_file: Path, config: dict) -> Optional[Tuple[str, List[TextBlock], int]]:
    """Extract using PyMuPDF with better error handling"""
    if not PDF_LIBRARIES["pymupdf"]:
        return None

    try:
        doc = PDF_LIBRARIES["pymupdf"].open(str(pdf_file))
        text_blocks = []
        all_text = []

        max_pages = min(config.get("extraction", {}).get("max_pages", 10), len(doc))

        for page_num in range(max_pages):
            page = doc[page_num]

            # Extract plain text
            page_text = page.get_text()
            if page_text:
                all_text.append(page_text)

                # Create simple text blocks
                lines = page_text.split("\n")
                for i, line in enumerate(lines):
                    if line.strip():
                        text_block = TextBlock(
                            text=line.strip(),
                            x=0,
                            y=800 - i * 15,  # Approximate y position
                            width=500,
                            height=12,
                            page_num=page_num,
                        )
                        text_blocks.append(text_block)

        doc.close()

        full_text = "\n".join(all_text)
        full_text = clean_text_advanced(full_text)

        return full_text, text_blocks, len(doc)

    except Exception as e:
        logger.debug(f"PyMuPDF extraction error: {e}")
        return None


def extract_with_pdfplumber(pdf_file: Path, config: dict) -> Optional[Tuple[str, List[TextBlock], int]]:
    """Extract using pdfplumber with better error handling"""
    if not PDF_LIBRARIES["pdfplumber"]:
        return None

    try:
        with PDF_LIBRARIES["pdfplumber"].open(str(pdf_file)) as pdf:
            text_blocks = []
            all_text = []

            max_pages = min(config.get("extraction", {}).get("max_pages", 10), len(pdf.pages))

            for page_num in range(max_pages):
                page = pdf.pages[page_num]

                # Extract text
                page_text = page.extract_text()
                if page_text:
                    all_text.append(page_text)

                    # Create text blocks from lines
                    lines = page_text.split("\n")
                    for i, line in enumerate(lines):
                        if line.strip():
                            text_block = TextBlock(
                                text=line.strip(),
                                x=0,
                                y=800 - i * 15,
                                width=500,
                                height=12,
                                page_num=page_num,
                            )
                            text_blocks.append(text_block)

            full_text = "\n".join(all_text)
            full_text = clean_text_advanced(full_text)

            return full_text, text_blocks, len(pdf.pages)

    except Exception as e:
        logger.debug(f"pdfplumber extraction error: {e}")
        return None


def extract_with_pdfminer(pdf_file: Path, config: dict) -> Optional[Tuple[str, List[TextBlock], int]]:
    """Extract using pdfminer with better error handling"""
    if not PDF_LIBRARIES["pdfminer"]:
        return None

    try:
        text = PDF_LIBRARIES["pdfminer"](str(pdf_file))
        if not text:
            return None

        text = clean_text_advanced(text)

        # Create simple text blocks from lines
        text_blocks = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line.strip():
                text_block = TextBlock(
                    text=line.strip(),
                    x=0,
                    y=800 - i * 15,
                    width=500,
                    height=12,
                    page_num=0,  # pdfminer doesn't provide page info easily
                )
                text_blocks.append(text_block)

        return text, text_blocks, 1  # Unknown page count

    except Exception as e:
        logger.debug(f"pdfminer extraction error: {e}")
        return None


def extract_as_text_file(pdf_file: Path, config: dict) -> Optional[Tuple[str, List[TextBlock], int]]:
    """
    Fallback: Try to read as text file in case it's actually a text file
    with .pdf extension
    """
    try:
        with open(pdf_file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        if not text or len(text) < 100:
            return None

        text = clean_text_advanced(text)

        # Create text blocks from lines
        text_blocks = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line.strip():
                text_block = TextBlock(
                    text=line.strip(),
                    x=0,
                    y=800 - i * 15,
                    width=500,
                    height=12,
                    page_num=0,
                )
                text_blocks.append(text_block)

        return text, text_blocks, 1

    except Exception as e:
        logger.debug(f"Text file extraction error: {e}")
        return None


def calculate_text_quality(text: str) -> float:
    """
    Calculate quality score for extracted text.
    
    Args:
        text: Extracted text
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    if not text:
        return 0.0

    score = 0.0
    
    # Length factor (longer is generally better, up to a point)
    length_score = min(len(text) / 10000, 1.0) * 0.3
    score += length_score
    
    # Character variety (more diverse characters = better)
    unique_chars = len(set(text))
    char_variety_score = min(unique_chars / 100, 1.0) * 0.2
    score += char_variety_score
    
    # Word count (more words = better structure)
    word_count = len(text.split())
    word_score = min(word_count / 1000, 1.0) * 0.2
    score += word_score
    
    # Sentence structure (periods, commas indicate proper text)
    sentence_indicators = text.count('.') + text.count(',') + text.count('!') + text.count('?')
    sentence_score = min(sentence_indicators / 100, 1.0) * 0.1
    score += sentence_score
    
    # Academic indicators (common in research papers)
    academic_terms = ['abstract', 'introduction', 'conclusion', 'references', 'bibliography']
    academic_score = sum(1 for term in academic_terms if term.lower() in text.lower()) / len(academic_terms) * 0.2
    score += academic_score
    
    return min(score, 1.0)


# Export functions
__all__ = [
    'multi_engine_extraction',
    'extract_with_pymupdf',
    'extract_with_pdfplumber',
    'extract_with_pdfminer',
    'extract_as_text_file',
    'calculate_text_quality'
]