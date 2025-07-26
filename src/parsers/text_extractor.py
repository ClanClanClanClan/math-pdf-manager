#!/usr/bin/env python3
"""
Text Extraction Engine
Extracted from src.parsers.pdf_parser.py - Handles text extraction from PDFs using multiple backends
"""

import logging
import warnings
from typing import List
from pathlib import Path
import time

# PDF processing libraries
PDF_LIBRARIES = {}

try:
    import fitz  # PyMuPDF
    PDF_LIBRARIES["pymupdf"] = fitz
except ImportError:
    PDF_LIBRARIES["pymupdf"] = None

try:
    import pdfplumber
    PDF_LIBRARIES["pdfplumber"] = pdfplumber
except ImportError:
    PDF_LIBRARIES["pdfplumber"] = None

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDF_LIBRARIES["pdfminer"] = pdfminer_extract
except ImportError:
    PDF_LIBRARIES["pdfminer"] = None

# Suppress warnings
warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


class TextExtractor:
    """Enhanced text extraction with multiple backend support"""
    
    def __init__(self, preferred_backend: str = "pymupdf"):
        """Initialize text extractor with preferred backend"""
        self.preferred_backend = preferred_backend
        self.available_backends = {
            name: lib for name, lib in PDF_LIBRARIES.items() 
            if lib is not None
        }
        
        if not self.available_backends:
            logger.warning("No PDF libraries available for text extraction")
        
        logger.info(f"Available backends: {list(self.available_backends.keys())}")
    
    def extract_text(self, pdf_path: str, max_pages: int = 3) -> tuple[str, dict]:
        """
        Extract text from PDF with quality metrics
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to process
            
        Returns:
            Tuple of (extracted_text, extraction_info)
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return "", {"error": f"File not found: {pdf_path}"}
        
        # Try backends in order of preference
        backends_to_try = [self.preferred_backend] + [
            b for b in self.available_backends.keys() 
            if b != self.preferred_backend
        ]
        
        for backend in backends_to_try:
            if backend not in self.available_backends:
                continue
                
            try:
                start_time = time.time()
                text, info = self._extract_with_backend(pdf_path, backend, max_pages)
                processing_time = time.time() - start_time
                
                if text.strip():
                    info.update({
                        "backend": backend,
                        "processing_time": processing_time,
                        "text_length": len(text),
                        "success": True
                    })
                    return text, info
                    
            except Exception as e:
                logger.warning(f"Backend {backend} failed: {e}")
                continue
        
        return "", {"error": "All extraction backends failed"}
    
    def _extract_with_backend(self, pdf_path: Path, backend: str, max_pages: int) -> tuple[str, dict]:
        """Extract text using specific backend"""
        
        if backend == "pymupdf":
            return self._extract_with_pymupdf(pdf_path, max_pages)
        elif backend == "pdfplumber":
            return self._extract_with_pdfplumber(pdf_path, max_pages)
        elif backend == "pdfminer":
            return self._extract_with_pdfminer(pdf_path, max_pages)
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    def _extract_with_pymupdf(self, pdf_path: Path, max_pages: int) -> tuple[str, dict]:
        """Extract text using PyMuPDF"""
        fitz = PDF_LIBRARIES["pymupdf"]
        
        doc = fitz.open(str(pdf_path))
        text_parts = []
        page_count = min(len(doc), max_pages)
        
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            text_parts.append(page_text)
        
        doc.close()
        
        full_text = "\n".join(text_parts)
        
        return full_text, {
            "pages_processed": page_count,
            "total_pages": len(doc),
            "quality_score": self._calculate_text_quality(full_text)
        }
    
    def _extract_with_pdfplumber(self, pdf_path: Path, max_pages: int) -> tuple[str, dict]:
        """Extract text using pdfplumber"""
        pdfplumber = PDF_LIBRARIES["pdfplumber"]
        
        with pdfplumber.open(str(pdf_path)) as pdf:
            text_parts = []
            page_count = min(len(pdf.pages), max_pages)
            
            for page_num in range(page_count):
                page = pdf.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            full_text = "\n".join(text_parts)
            
            return full_text, {
                "pages_processed": page_count,
                "total_pages": len(pdf.pages),
                "quality_score": self._calculate_text_quality(full_text)
            }
    
    def _extract_with_pdfminer(self, pdf_path: Path, max_pages: int) -> tuple[str, dict]:
        """Extract text using pdfminer"""
        pdfminer_extract = PDF_LIBRARIES["pdfminer"]
        
        # Note: pdfminer doesn't easily support page limits
        # This is a simplified version
        text = pdfminer_extract(str(pdf_path))
        
        return text, {
            "pages_processed": max_pages,
            "total_pages": -1,  # Unknown with pdfminer
            "quality_score": self._calculate_text_quality(text)
        }
    
    def _calculate_text_quality(self, text: str) -> float:
        """Calculate text quality score based on various metrics"""
        if not text:
            return 0.0
        
        # Simple heuristics for text quality
        score = 0.0
        
        # Length bonus (longer text usually better)
        if len(text) > 1000:
            score += 0.3
        elif len(text) > 500:
            score += 0.2
        elif len(text) > 100:
            score += 0.1
        
        # Character diversity
        unique_chars = len(set(text))
        if unique_chars > 50:
            score += 0.2
        elif unique_chars > 30:
            score += 0.1
        
        # Word count
        words = text.split()
        if len(words) > 200:
            score += 0.2
        elif len(words) > 100:
            score += 0.1
        
        # Sentence structure (rough heuristic)
        sentence_endings = text.count('.') + text.count('!') + text.count('?')
        if sentence_endings > 10:
            score += 0.1
        
        # Penalty for too many special characters (might indicate OCR errors)
        special_char_ratio = sum(1 for c in text if not c.isalnum() and c not in ' \n\t.,;:!?-') / len(text)
        if special_char_ratio > 0.1:
            score -= 0.2
        
        return min(1.0, max(0.0, score))
    
    def get_available_backends(self) -> List[str]:
        """Get list of available extraction backends"""
        return list(self.available_backends.keys())
    
    def is_backend_available(self, backend: str) -> bool:
        """Check if a specific backend is available"""
        return backend in self.available_backends