"""Compatibility layer for test_main.py after refactoring"""

# Mock implementations for test compatibility
import logging
import os
import unicodedata
from functools import lru_cache

def setup_logging(verbose=False):
    """Mock setup_logging for tests"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")
    
    # Suppress noisy libraries like original
    suppressed_loggers = ["fitz", "pdfminer", "pdfplumber"]
    for lib_name in suppressed_loggers:
        logging.getLogger(lib_name).setLevel(logging.ERROR)
    
    return logging.getLogger("main")

def setup_environment():
    """Mock setup_environment for tests"""
    env_config = {
        "PYTHONWARNINGS": "ignore",
        "MPLBACKEND": "agg",
        "FITZ_IGNORE_NO_MUPDF": "1",
        "PYTHONIOENCODING": "utf-8",
        "TESTING": "1"
    }
    os.environ.update(env_config)
    if hasattr(os, 'stat_float_times'):
        os.stat_float_times(False)

# Import actual functions
from main import main
from config_loader import load_yaml_config_secure
from main_processing import process_files, verify_configuration
from scanner import scan_directory
from filename_checker import batch_check_filenames
from author_processing import fix_author_block, authors_are_equivalent
from file_operations import safe_file_rename, normalize_file_metadata
from reporter import generate_html_report, generate_csv_report
from duplicate_detector import find_duplicates
from text_normalization import get_suffix_map
from utils import *

# Alias for backward compatibility
_get_suffix_map = get_suffix_map

# Create mock cache functions
@lru_cache(maxsize=4096)
def _normalize_nfc_cached(text):
    """NFC normalization with caching"""
    if not isinstance(text, str):
        return text
    return unicodedata.normalize('NFC', text)

@lru_cache(maxsize=4096)
def _normalize_nfd_cached(text):
    """NFD normalization with caching"""
    if not isinstance(text, str):
        return text
    return unicodedata.normalize('NFD', text)

_fix_initials_cache = lru_cache(maxsize=2048)(lambda x: x)
_fix_initials_periods_cache = lru_cache(maxsize=2048)(lambda x: x)

# Export all available functions for test fixture
__all__ = [
    'setup_logging',
    'setup_environment', 
    'main',
    'load_yaml_config_secure',
    'process_files',
    'verify_configuration',
    'scan_directory',
    'batch_check_filenames',
    'fix_author_block',
    'authors_are_equivalent',
    'safe_file_rename',
    'normalize_file_metadata',
    'generate_html_report',
    'generate_csv_report',
    'find_duplicates',
    'get_suffix_map',
    '_get_suffix_map',
    '_normalize_nfc_cached',
    '_normalize_nfd_cached',
    '_fix_initials_cache',
    '_fix_initials_periods_cache'
]