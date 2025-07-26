#!/usr/bin/env python3
"""
Enhanced PDF Parser - Main Orchestrator
Streamlined main parser that orchestrates the modular components
Reduced from 2,576 lines to ~200 lines
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from parsers.base_parser import PDFMetadata, MetadataSource, PDFConstants
from parsers.text_extractor import TextExtractor
from api.arxiv_client import ArxivAPIClient

logger = logging.getLogger(__name__)


class EnhancedPDFParser:
    """
    Main PDF parser orchestrator
    Coordinates text extraction, metadata parsing, and API integration
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the enhanced PDF parser"""
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.text_extractor = TextExtractor(
            preferred_backend=self.config.get('pdf_backend', 'pymupdf')
        )
        
        self.arxiv_client = ArxivAPIClient(
            api_available=self.config.get('arxiv_api_enabled', True)
        )
        
        # Processing settings
        self.max_pages = self.config.get('max_pages', 3)
        self.enable_api_lookup = self.config.get('enable_api_lookup', True)
        self.cache_results = self.config.get('cache_results', True)
        
        # Result cache
        self.metadata_cache = {}
        
        logger.info("Enhanced PDF Parser initialized")
        logger.info(f"Available backends: {self.text_extractor.get_available_backends()}")
        logger.info(f"ArXiv API: {'Enabled' if self.arxiv_client.api_available else 'Disabled'}")
    
    def extract_metadata(self, pdf_path: str) -> PDFMetadata:
        """
        Extract metadata from PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PDFMetadata object with extracted information
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        # Initialize metadata
        metadata = PDFMetadata(
            filename=pdf_path.name,
            path=str(pdf_path.absolute())
        )
        
        # Check cache first
        if self.cache_results and str(pdf_path) in self.metadata_cache:
            cached_metadata = self.metadata_cache[str(pdf_path)]
            logger.debug(f"Using cached metadata for {pdf_path.name}")
            return cached_metadata
        
        try:
            # Step 1: Extract text from PDF
            logger.info(f"Extracting text from {pdf_path.name}")
            text, extraction_info = self.text_extractor.extract_text(
                str(pdf_path), 
                max_pages=self.max_pages
            )
            
            if extraction_info.get('error'):
                metadata.error = extraction_info['error']
                metadata.add_warning("Text extraction failed")
                return metadata
            
            # Update metadata with extraction info
            metadata.extraction_method = extraction_info.get('backend', 'unknown')
            metadata.text_quality = extraction_info.get('quality_score', 0.0)
            metadata.page_count = extraction_info.get('total_pages', 0)
            
            # Step 2: Parse metadata from text
            logger.info("Parsing metadata from text")
            self._parse_metadata_from_text(metadata, text)
            
            # Step 3: Try ArXiv API lookup if enabled
            if self.enable_api_lookup and self.arxiv_client.api_available:
                logger.info("Attempting ArXiv API lookup")
                self._enhance_with_arxiv_api(metadata, text)
            
            # Step 4: Final validation and confidence scoring
            self._calculate_final_confidence(metadata)
            
            # Cache result
            if self.cache_results:
                self.metadata_cache[str(pdf_path)] = metadata
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}")
            metadata.error = str(e)
            metadata.add_warning("Processing failed")
        
        finally:
            metadata.processing_time = time.time() - start_time
        
        return metadata
    
    def _parse_metadata_from_text(self, metadata: PDFMetadata, text: str):
        """Parse metadata from extracted text using heuristics"""
        if not text:
            return
        
        lines = text.split('\n')
        
        # Try to extract title (usually first substantial line)
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if len(line) > PDFConstants.MIN_TITLE_LENGTH and len(line) < PDFConstants.MAX_TITLE_LEN:
                # Skip lines that look like headers/footers
                if not self._is_header_or_footer(line):
                    metadata.title = line
                    metadata.source = MetadataSource.HEURISTIC
                    break
        
        # Try to extract authors (look for author patterns)
        authors = self._extract_authors_from_text(text)
        if authors:
            metadata.authors = authors
        
        # Look for ArXiv ID in text
        arxiv_id = self.arxiv_client.extract_arxiv_id_from_text(text)
        if arxiv_id:
            metadata.arxiv_id = arxiv_id
            metadata.repository_type = "arxiv"
        
        # Basic confidence scoring
        if metadata.title != "Unknown Title":
            metadata.confidence = max(metadata.confidence, 0.6)
        
        if metadata.authors != "Unknown":
            metadata.confidence = max(metadata.confidence, 0.5)
    
    def _extract_authors_from_text(self, text: str) -> str:
        """Extract authors from text using heuristics"""
        lines = text.split('\n')
        
        # Look for author patterns in first 20 lines
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            
            # Skip empty lines and very short lines
            if not line or len(line) < 5:
                continue
            
            # Look for author indicators
            if any(indicator in line.lower() for indicator in ['author', 'by ']):
                # Try to extract authors from this line or next few lines
                author_candidates = []
                
                # Check current line and next 3 lines
                for j in range(i, min(i + 4, len(lines))):
                    candidate = lines[j].strip()
                    if self._looks_like_author_line(candidate):
                        author_candidates.append(candidate)
                
                if author_candidates:
                    return ', '.join(author_candidates)
        
        return "Unknown"
    
    def _looks_like_author_line(self, line: str) -> bool:
        """Check if line looks like it contains author names"""
        if not line or len(line) < 5 or len(line) > 200:
            return False
        
        # Should contain mostly letters and common punctuation
        alpha_ratio = sum(c.isalpha() or c in ' ,.()-' for c in line) / len(line)
        if alpha_ratio < 0.7:
            return False
        
        # Should not contain common non-author patterns
        skip_patterns = [
            'abstract', 'introduction', 'conclusion', 'references',
            'university', 'department', 'email', '@', 'http', 'www',
            'page', 'figure', 'table', 'section'
        ]
        
        line_lower = line.lower()
        if any(pattern in line_lower for pattern in skip_patterns):
            return False
        
        return True
    
    def _is_header_or_footer(self, line: str) -> bool:
        """Check if line is likely a header or footer"""
        line_lower = line.lower()
        
        # Common header/footer patterns
        skip_patterns = [
            'page', 'copyright', '©', 'journal', 'proceedings',
            'volume', 'issue', 'doi:', 'issn', 'isbn', 'url:',
            'preprint', 'draft', 'submitted', 'accepted'
        ]
        
        return any(pattern in line_lower for pattern in skip_patterns)
    
    def _enhance_with_arxiv_api(self, metadata: PDFMetadata, text: str):
        """Enhance metadata using ArXiv API"""
        api_result = None
        
        # Try lookup by ArXiv ID first
        if metadata.arxiv_id:
            logger.debug(f"Looking up ArXiv ID: {metadata.arxiv_id}")
            api_result = self.arxiv_client.search_by_id(metadata.arxiv_id)
        
        # If no ArXiv ID or lookup failed, try title search
        if not api_result and metadata.title != "Unknown Title":
            logger.debug(f"Searching ArXiv by title: {metadata.title}")
            results = self.arxiv_client.search_by_title(metadata.title, max_results=1)
            if results:
                api_result = results[0]
        
        # Update metadata with API results
        if api_result:
            logger.info("Enhanced metadata with ArXiv API data")
            
            # Update with high-confidence API data
            if api_result.get('title'):
                metadata.title = api_result['title']
            
            if api_result.get('authors'):
                metadata.authors = api_result['authors']
            
            if api_result.get('arxiv_id'):
                metadata.arxiv_id = api_result['arxiv_id']
            
            if api_result.get('abstract'):
                metadata.abstract = api_result['abstract']
            
            if api_result.get('categories'):
                metadata.categories = api_result['categories']
            
            if api_result.get('doi'):
                metadata.doi = api_result['doi']
            
            if api_result.get('journal'):
                metadata.journal = api_result['journal']
            
            if api_result.get('published'):
                metadata.publication_date = api_result['published']
            
            # Update source and confidence
            metadata.source = MetadataSource.API
            metadata.repository_type = "arxiv"
            metadata.is_published = True
    
    def _calculate_final_confidence(self, metadata: PDFMetadata):
        """Calculate final confidence score"""
        base_confidence = metadata.source.confidence
        
        # Adjust confidence based on data quality
        if metadata.title != "Unknown Title" and len(metadata.title) > PDFConstants.MIN_TITLE_LENGTH:
            base_confidence += 0.1
        
        if metadata.authors != "Unknown" and len(metadata.authors) > 5:
            base_confidence += 0.1
        
        if metadata.arxiv_id:
            base_confidence += 0.2
        
        if metadata.abstract:
            base_confidence += 0.1
        
        if metadata.doi:
            base_confidence += 0.1
        
        # Text quality bonus
        if metadata.text_quality > 0.7:
            base_confidence += 0.1
        elif metadata.text_quality > 0.5:
            base_confidence += 0.05
        
        # Cap confidence at 1.0
        metadata.confidence = min(1.0, base_confidence)
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        default_config = {
            'pdf_backend': 'pymupdf',
            'max_pages': 3,
            'arxiv_api_enabled': True,
            'enable_api_lookup': True,
            'cache_results': True,
            'timeout': PDFConstants.DEFAULT_TIMEOUT
        }
        
        if not config_path:
            return default_config
        
        try:
            config_path = Path(config_path)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    default_config.update(user_config)
                    logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def clear_cache(self):
        """Clear the metadata cache"""
        self.metadata_cache.clear()
        self.arxiv_client.clear_cache()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'metadata_cache_size': len(self.metadata_cache),
            'arxiv_cache_size': self.arxiv_client.get_cache_size()
        }