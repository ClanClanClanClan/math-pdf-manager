"""
Application constants for Math-PDF Manager

This module contains all configuration constants used throughout the application.
"""
import re
from pathlib import Path

# Version information
__version__ = "2.0.0"
APP_NAME = "Math-PDF Manager"
APP_DESCRIPTION = "Academic PDF management system for mathematics research"

# File processing limits
MAX_FILENAME_LENGTH = 255
MAX_AUTHOR_LENGTH = 100
MAX_TITLE_LENGTH = 200
MAX_FILES_PER_SCAN = 10000
MAX_FILE_SIZE_MB = 100

# Timeout settings (in seconds)
PDF_PARSING_TIMEOUT = 30
API_REQUEST_TIMEOUT = 10
OCR_PROCESSING_TIMEOUT = 60
GROBID_PROCESSING_TIMEOUT = 30

# Regular expressions
FILENAME_PATTERN = re.compile(
    r'^(?P<authors>[^-]+?)\s*-\s*(?P<title>[^-]+?)\.pdf$',
    re.UNICODE | re.IGNORECASE
)

AUTHOR_SEPARATOR_PATTERN = re.compile(
    r',(?:\s*(?:and|&)\s*)|;\s*|\s+and\s+|\s*&\s*'
)

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.pdf'}
SUPPORTED_MIME_TYPES = {'application/pdf'}

# Unicode normalization
DEFAULT_UNICODE_FORM = 'NFC'
SUSPICIOUS_UNICODE_CATEGORIES = {
    'Cc',  # Control characters
    'Cf',  # Format characters
    'Cs',  # Surrogates
    'Co',  # Private use
    'Cn',  # Unassigned
}

# Output formats
SUPPORTED_OUTPUT_FORMATS = {'html', 'json', 'csv', 'txt'}
DEFAULT_OUTPUT_FORMAT = 'html'

# Cache settings
DEFAULT_CACHE_TTL = 3600  # 1 hour
MAX_CACHE_SIZE = 1000
CACHE_DIRECTORY = Path.home() / '.cache' / 'math-pdf-manager'

# API settings
DEFAULT_USER_AGENT = f"{APP_NAME}/{__version__}"
DEFAULT_RATE_LIMIT = 10  # requests per second
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.3

# Logging
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Validation thresholds
MIN_CONFIDENCE_SCORE = 0.7
HIGH_CONFIDENCE_SCORE = 0.9
OCR_CONFIDENCE_THRESHOLD = 0.8
SIMILARITY_THRESHOLD = 0.85

# Mathematical context keywords
MATH_KEYWORDS = {
    'theorem', 'lemma', 'proof', 'proposition', 'corollary',
    'definition', 'equation', 'formula', 'algorithm',
    'matrix', 'vector', 'topology', 'algebra', 'analysis',
    'geometry', 'calculus', 'statistics', 'probability'
}

# Common name particles for author parsing
NAME_PARTICLES = {
    'von', 'van', 'de', 'der', 'den', 'ter', 'te', 'la', 'le',
    'du', 'des', 'della', 'degli', 'di', 'da', 'del', 'do', 'dos'
}

# Academic suffixes
ACADEMIC_SUFFIXES = {'Jr.', 'Sr.', 'II', 'III', 'IV', 'V', 'Ph.D.', 'M.D.'}

# Error messages
ERROR_MESSAGES = {
    'file_not_found': "File not found: {path}",
    'invalid_pdf': "Invalid PDF file: {path}",
    'parsing_failed': "Failed to parse PDF: {error}",
    'network_error': "Network error: {error}",
    'timeout_error': "Operation timed out after {timeout} seconds",
    'validation_failed': "Validation failed: {error}",
    'unicode_error': "Unicode processing error: {error}",
}

# Success messages
SUCCESS_MESSAGES = {
    'file_processed': "Successfully processed: {path}",
    'validation_passed': "Validation passed for: {path}",
    'metadata_extracted': "Metadata extracted from: {source}",
    'fix_applied': "Applied fix: {fix_type}",
}

# Default configuration
DEFAULT_CONFIG = {
    'strict_mode': False,
    'auto_fix': False,
    'backup_files': True,
    'parallel_processing': True,
    'max_workers': 4,
    'enable_ocr': False,
    'enable_grobid': False,
    'output_format': DEFAULT_OUTPUT_FORMAT,
    'log_level': DEFAULT_LOG_LEVEL,
}

# Directory names for organization
DIRECTORY_NAMES = {
    'core': 'core',
    'validators': 'validators',
    'extractors': 'extractors',
    'utils': 'utils',
    'cli': 'cli',
    'tests': 'tests',
    'docs': 'docs',
    'data': 'data',
    'scripts': 'scripts',
    'archive': 'archive',
    'output': 'output',
    'tools': 'tools',
}