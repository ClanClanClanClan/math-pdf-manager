#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Constants Module
Phase 1, Week 2: Extracted from main.py to reduce file size

Contains all constants used throughout the application.
"""

from pathlib import Path

# Default file names
DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_KNOWN_WORDS_FILE = "known_words.txt"
DEFAULT_NAME_DASH_WHITELIST_FILE = "name_dash_whitelist.txt"
DEFAULT_MULTIWORD_FAMILYNAMES_FILE = "multiword_familynames.txt"
DEFAULT_HTML_OUTPUT = "report.html"
DEFAULT_CSV_OUTPUT = "report.csv"
DEFAULT_TEMPLATE_DIR = "templates"

# Performance limits to prevent hanging
MAX_INPUT_LENGTH = 5000
MAX_AUTHORS = 20
MAX_ITERATIONS = 1000
OPERATION_TIMEOUT = 2.0

# Environment configuration
ENV_CONFIG = {
    "PYTHONWARNINGS": "ignore",
    "MPLBACKEND": "agg",
    "FITZ_IGNORE_NO_MUPDF": "1",
}

# Libraries to suppress logging for
SUPPRESSED_LOGGERS = ("fitz", "pdfminer", "pdfplumber")

# Dropbox migration paths (also in file_operations.py for consistency)
DROPBOX_OLD_PATH = Path.home() / "Dropbox"
DROPBOX_NEW_PATH = Path.home() / "Library/CloudStorage/Dropbox"

# Extended surname particles list
_SURNAME_PARTICLES = {
    "de", "la", "van", "von", "di", "del", "le", "da", "dos", "der",
    "du", "des", "den", "het", "ter", "ten", "te", "zur", "zum", "am",
    "im", "vom", "auf", "aus", "das", "los", "las", "el", "al", "dal",
    "della", "delle", "dello", "degli", "dei", "do",
}

# Comprehensive academic suffixes including Roman numerals
_ACADEMIC_SUFFIXES = {
    "jr", "sr", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    "md", "phd", "dds", "ma", "ms", "ba", "bs", "mph", "jd", "dvm", "od",
    "pharmd", "dpt", "edd", "psyd", "dnp", "dsc", "drph", "pharm",
}

# Roman numerals
_ROMAN_NUMERALS_SET = {
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
}