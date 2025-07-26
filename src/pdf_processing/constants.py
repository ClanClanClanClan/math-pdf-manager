"""
PDF Processing Constants

Constants and configuration values for PDF processing operations.
Extracted from src.parsers.pdf_parser.py for better modularity.
"""


class PDFConstants:
    """Enhanced constants for PDF processing"""

    MAX_AUTHORS = 5
    MAX_FILENAME_LEN = 255
    MAX_TITLE_LEN = 300
    MAX_TEXT_LENGTH = 1000000  # 1MB text limit
    DEFAULT_TIMEOUT = 45
    MAX_PROCESSING_TIME = 60
    CACHE_SIZE = 2000
    MIN_TITLE_LENGTH = 10
    MAX_AUTHOR_TOKENS = 20


# Backward compatibility
MAX_AUTHORS = PDFConstants.MAX_AUTHORS
MAX_FILENAME_LEN = PDFConstants.MAX_FILENAME_LEN
MAX_TITLE_LEN = PDFConstants.MAX_TITLE_LEN
MAX_TEXT_LENGTH = PDFConstants.MAX_TEXT_LENGTH
DEFAULT_TIMEOUT = PDFConstants.DEFAULT_TIMEOUT
MAX_PROCESSING_TIME = PDFConstants.MAX_PROCESSING_TIME
CACHE_SIZE = PDFConstants.CACHE_SIZE
MIN_TITLE_LENGTH = PDFConstants.MIN_TITLE_LENGTH
MAX_AUTHOR_TOKENS = PDFConstants.MAX_AUTHOR_TOKENS