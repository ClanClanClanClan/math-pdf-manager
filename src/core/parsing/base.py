#!/usr/bin/env python3
"""
Core parsing base classes and utilities
Extracted from parsers.pdf_parser.py for better modularity
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum


class ParsingMethod(Enum):
    """Available parsing methods."""
    PYMUPDF = "pymupdf"
    PYPDF = "pypdf"
    GROBID = "grobid"
    OCR = "ocr"


@dataclass
class ParsedDocument:
    """Result of document parsing."""
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parsing_method: Optional[ParsingMethod] = None
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)


class BaseParser(ABC):
    """Abstract base class for document parsers."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse the document and extract metadata."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this parser is available on the system."""
        pass
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate that the file exists and is readable."""
        if not file_path.exists():
            self.logger.error(f"File does not exist: {file_path}")
            return False
        
        if not file_path.is_file():
            self.logger.error(f"Path is not a file: {file_path}")
            return False
        
        try:
            with open(file_path, "rb") as f:
                # Try to read first few bytes
                f.read(1024)
            return True
        except Exception as e:
            self.logger.error(f"Cannot read file {file_path}: {e}")
            return False


class ParserManager:
    """Manages multiple parsers with fallback logic."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.parsers: Dict[ParsingMethod, BaseParser] = {}
        self.parser_priority: List[ParsingMethod] = [
            ParsingMethod.PYMUPDF,
            ParsingMethod.PYPDF,
            ParsingMethod.GROBID,
            ParsingMethod.OCR
        ]
    
    def register_parser(self, method: ParsingMethod, parser: BaseParser):
        """Register a parser for a specific method."""
        self.parsers[method] = parser
        self.logger.debug(f"Registered parser: {method.value}")
    
    def parse_document(self, file_path: Path, preferred_method: Optional[ParsingMethod] = None) -> ParsedDocument:
        """Parse document using available parsers with fallback."""
        if preferred_method and preferred_method in self.parsers:
            parser = self.parsers[preferred_method]
            if parser.is_available():
                try:
                    return parser.parse(file_path)
                except Exception as e:
                    self.logger.warning(f"Preferred parser {preferred_method.value} failed: {e}")
        
        # Try parsers in priority order
        for method in self.parser_priority:
            if method in self.parsers:
                parser = self.parsers[method]
                if parser.is_available():
                    try:
                        result = parser.parse(file_path)
                        if result.title or result.authors:  # Basic success check
                            return result
                    except Exception as e:
                        self.logger.warning(f"Parser {method.value} failed: {e}")
                        continue
        
        # Return empty result if all parsers fail
        return ParsedDocument(
            errors=["All parsing methods failed"],
            parsing_method=None
        )