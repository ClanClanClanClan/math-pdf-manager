#!/usr/bin/env python3
"""
PDF Processing Parsers Module
Split from monolithic parsers.py for better maintainability
"""

from .base_parser import UltraEnhancedPDFParser
from .text_extraction import (
    extract_with_pymupdf,
    extract_with_pdfplumber, 
    extract_with_pdfminer,
    extract_as_text_file,
    multi_engine_extraction
)
from .metadata_extraction import (
    extract_title_multi_method,
    extract_authors_multi_method,
    extract_title_heuristic,
    extract_title_from_line
)
from .document_analysis import (
    analyze_document_structure,
    calculate_text_quality
)

__all__ = [
    'UltraEnhancedPDFParser',
    'extract_with_pymupdf',
    'extract_with_pdfplumber',
    'extract_with_pdfminer',
    'extract_as_text_file',
    'multi_engine_extraction',
    'extract_title_multi_method',
    'extract_authors_multi_method',
    'extract_title_heuristic',
    'extract_title_from_line',
    'analyze_document_structure',
    'calculate_text_quality'
]