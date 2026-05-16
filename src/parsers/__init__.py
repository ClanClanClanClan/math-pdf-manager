"""
PDF Parser Module
Extracted from parsers.pdf_parser.py to create focused, maintainable modules
"""

from .base_parser import PDFMetadata, MetadataSource, PDFConstants
from .text_extractor import TextExtractor
from .enhanced_pdf_parser import EnhancedPDFParser

# ArxivParser was extracted to ``src/pdf_processing/extractors/arxiv_extractor.py``
# during the parsers→pdf_processing refactor.  No standalone file remains
# inside this package, so the legacy ``from .arxiv_parser import ArxivParser``
# import has been removed (it raised ModuleNotFoundError at import time).

__all__ = [
    'PDFMetadata',
    'MetadataSource',
    'PDFConstants',
    'TextExtractor',
    'EnhancedPDFParser'
]