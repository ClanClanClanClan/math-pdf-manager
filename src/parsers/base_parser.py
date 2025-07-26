#!/usr/bin/env python3
"""
Base Parser Classes and Constants
Extracted from src.parsers.pdf_parser.py - Contains core data structures and constants
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List


class MetadataSource(Enum):
    """Source of extracted metadata with confidence levels"""

    UNKNOWN = ("unknown", 0.0)
    HEURISTIC = ("heuristic", 0.6)
    FILENAME = ("filename", 0.3)
    API = ("api", 0.9)
    REPOSITORY = ("repository", 0.85)
    MULTI_SOURCE = ("multi_source", 0.8)

    def __new__(cls, value, confidence):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.confidence = confidence
        return obj

    @property
    def value(self):
        return self._value_


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


@dataclass
class PDFMetadata:
    """Enhanced metadata with detailed analysis"""

    title: str = "Unknown Title"
    authors: str = "Unknown"
    source: MetadataSource = MetadataSource.UNKNOWN
    confidence: float = 0.0
    filename: str = ""
    path: str = ""
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    repository_type: Optional[str] = None
    language: str = "en"
    is_published: bool = False
    page_count: int = 0
    text_quality: float = 0.0
    extraction_method: str = "unknown"
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    journal: Optional[str] = None
    venue: Optional[str] = None
    publication_date: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate metadata after initialization"""
        if self.confidence < 0.0:
            self.confidence = 0.0
        elif self.confidence > 1.0:
            self.confidence = 1.0
            
        if self.page_count < 0:
            self.page_count = 0
            
        if self.text_quality < 0.0:
            self.text_quality = 0.0
        elif self.text_quality > 1.0:
            self.text_quality = 1.0

    def add_warning(self, warning: str):
        """Add a warning message"""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def is_high_confidence(self) -> bool:
        """Check if metadata has high confidence (>= 0.7)"""
        return self.confidence >= 0.7

    def is_arxiv_paper(self) -> bool:
        """Check if this is an ArXiv paper"""
        return self.arxiv_id is not None or self.repository_type == "arxiv"

    def get_display_authors(self) -> str:
        """Get authors formatted for display"""
        if not self.authors or self.authors == "Unknown":
            return "Unknown Author"
        return self.authors

    def get_display_title(self) -> str:
        """Get title formatted for display"""
        if not self.title or self.title == "Unknown Title":
            return "Unknown Title"
        return self.title[:PDFConstants.MAX_TITLE_LEN]