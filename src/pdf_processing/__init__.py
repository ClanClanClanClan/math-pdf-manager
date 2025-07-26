"""
PDF Processing Module

Modular PDF processing system extracted from src.parsers.pdf_parser.py.
Provides comprehensive PDF metadata extraction, text processing,
and document structure analysis capabilities.

Components:
- models: Data models and structures
- constants: Configuration constants
- utilities: Utility functions
- extractors: Content extraction classes
- parsers: Core parsing logic
"""

# Core models and data structures
from .models import (
    MetadataSource,
    PDFMetadata,
    TextBlock,
    DocumentStructure,
    ArxivMetadata,
    # Backward compatibility aliases
    Metadata,
    Structure,
    Block,
)

# Configuration constants
from .constants import (
    PDFConstants,
    MAX_AUTHORS,
    MAX_FILENAME_LEN,
    MAX_TITLE_LEN,
    MAX_TEXT_LENGTH,
    DEFAULT_TIMEOUT,
    MAX_PROCESSING_TIME,
    CACHE_SIZE,
    MIN_TITLE_LENGTH,
    MAX_AUTHOR_TOKENS,
)

# Utility functions
from .utilities import (
    grobid_available,
    ocr_available,
    timeout_handler,
    clean_text_advanced,
    _fake_image_to_string,
)

# Core parser
from .parsers import UltraEnhancedPDFParser

# Extractors
from .extractors import (
    AdvancedSSRNExtractor,
    AdvancedArxivExtractor,
    AdvancedJournalExtractor,
    ArxivAPIClient,
)

__all__ = [
    # Models
    'MetadataSource',
    'PDFMetadata',
    'TextBlock',
    'DocumentStructure',
    'ArxivMetadata',
    'Metadata',
    'Structure', 
    'Block',
    
    # Constants
    'PDFConstants',
    'MAX_AUTHORS',
    'MAX_FILENAME_LEN',
    'MAX_TITLE_LEN',
    'MAX_TEXT_LENGTH',
    'DEFAULT_TIMEOUT',
    'MAX_PROCESSING_TIME',
    'CACHE_SIZE',
    'MIN_TITLE_LENGTH',
    'MAX_AUTHOR_TOKENS',
    
    # Utilities
    'grobid_available',
    'ocr_available',
    'timeout_handler',
    'clean_text_advanced',
    '_fake_image_to_string',
    
    # Core parser
    'UltraEnhancedPDFParser',
    
    # Extractors
    'AdvancedSSRNExtractor',
    'AdvancedArxivExtractor',
    'AdvancedJournalExtractor',
    'ArxivAPIClient',
]