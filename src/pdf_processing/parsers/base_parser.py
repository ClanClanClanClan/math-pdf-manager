#!/usr/bin/env python3
"""
Base PDF Parser Implementation
Extracted from monolithic parsers.py
"""

import time
import hashlib
import logging
from pathlib import Path
from collections import defaultdict

import regex as re
import yaml

from ..models import PDFMetadata, MetadataSource
from ..constants import PDFConstants
from ..extractors import AdvancedSSRNExtractor, AdvancedArxivExtractor, AdvancedJournalExtractor, ArxivAPIClient

# Get logger
logger = logging.getLogger(__name__)

# Check if we're in offline mode
try:
    from config import OFFLINE
except ImportError:
    OFFLINE = False

# PDF library availability
PDF_LIBRARIES = {}
try:
    import fitz
    PDF_LIBRARIES["pymupdf"] = fitz
except ImportError:
    PDF_LIBRARIES["pymupdf"] = None

try:
    import pdfplumber
    PDF_LIBRARIES["pdfplumber"] = pdfplumber
except ImportError:
    PDF_LIBRARIES["pdfplumber"] = None

try:
    from pdfminer.high_level import extract_text
    PDF_LIBRARIES["pdfminer"] = extract_text
except ImportError:
    PDF_LIBRARIES["pdfminer"] = None


class UltraEnhancedPDFParser:
    """Ultra-enhanced PDF parser with ArXiv API integration"""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with comprehensive capabilities"""
        self.config = self._load_config(config_path)
        self._init_extractors()
        self._init_caches()
        self._init_patterns()

        # Initialize ArXiv API client
        self.arxiv_client = ArxivAPIClient()

        # Statistics and monitoring
        self.stats = defaultdict(int)
        self.performance_data = []

        logger.info("Ultra-Enhanced PDF Parser initialized (with ArXiv API)")

    def _load_config(self, path: str) -> dict:
        """Load enhanced configuration with proper defaults"""
        defaults = {
            "extraction": {
                "max_pages": 10,
                "enable_position_analysis": True,
                "enable_font_analysis": True,
                "multi_column_threshold": 0.6,
                "title_max_lines": 5,
                "author_max_lines": 4,
                "timeout_seconds": 45,
                "fallback_enabled": True,
                "cache_enabled": True,
                "enable_arxiv_api": True,
            },
            "repositories": {
                "enable_ssrn_parser": True,
                "enable_arxiv_parser": True,
                "enable_nber_parser": True,
                "enable_journal_parser": True,
                "enable_pubmed_parser": True,
                "enable_repec_parser": True,
            },
            "scoring": {
                "position_weight": 0.25,
                "font_weight": 0.20,
                "length_weight": 0.15,
                "content_weight": 0.40,
                "confidence_threshold": 0.5,
            },
            "performance": {
                "max_memory_mb": 500,
                "cache_size": 2000,
                "parallel_enabled": True,
                "profiling_enabled": False,
            },
            "engines": {"enable_grobid": True, "enable_ocr": True},
        }

        try:
            if Path(path).exists():
                with open(path, "r", encoding="utf-8") as f:
                    user_config = yaml.safe_load(f) or {}
                return self._deep_merge(defaults, user_config)
        except Exception as e:
            logger.warning(f"Config load error: {e}")

        return defaults

    def _normalise_title(self, title: str) -> str:
        """Strip trailing author names & enforce max length."""
        if not title:
            return title

        # --- cut before the first detected author name -----------
        # Enhanced pattern to match various author name formats
        author_patterns = [
            r"\s+[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+",  # "John A. Smith"
            r"\s+[A-Z][a-z]+\s+[A-Z][a-z]+",  # "John Smith"
            r"\s+by\s+[A-Z][a-z]+",  # "by John"
        ]
        
        min_length = PDFConstants.MIN_TITLE_LENGTH if hasattr(PDFConstants, 'MIN_TITLE_LENGTH') else 10
        
        for pattern in author_patterns:
            author_pat = re.compile(pattern)
            m = author_pat.search(title, min_length)
            if m:
                title = title[: m.start()].rstrip(" ,;:-")
                break

        # --- final hard cap --------------------------------------
        return title[:PDFConstants.MAX_TITLE_LEN if hasattr(PDFConstants, 'MAX_TITLE_LEN') else 200]

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _init_extractors(self):
        """Initialize specialized extractors"""
        self.extractors = {
            "ssrn": AdvancedSSRNExtractor(),
            "arxiv": AdvancedArxivExtractor(),
            "journal": AdvancedJournalExtractor(),
        }

    def _init_caches(self):
        """Initialize caching system"""
        cache_size = self.config.get("performance", {}).get("cache_size", 2000)
        self.text_cache = {}
        self.metadata_cache = {}
        self.structure_cache = {}

        # Simple LRU implementation
        self._cache_access_order = []
        self._max_cache_size = cache_size

    def _init_patterns(self):
        """Initialize enhanced pattern matching"""
        self.patterns = {
            # Repository detection patterns
            "repository_patterns": {
                "ssrn": [
                    r"ssrn\.com",
                    r"social\s+science\s+research\s+network",
                    r"electronic\s+copy\s+available",
                ],
                "arxiv": [r"arxiv:\d{4}\.\d{4,5}", r"arxiv\.org", r"arxiv\s+preprint", r"submitted\s+to\s+arxiv"],
                "nber": [
                    r"nber\.org",
                    r"national\s+bureau.*economic\s+research",
                    r"nber\s+working\s+paper",
                ],
                "pubmed": [
                    r"pubmed\.ncbi\.nlm\.nih\.gov",
                    r"pmid:\s*\d+",
                ],
                "repec": [
                    r"repec\.org",
                    r"research\s+papers\s+in\s+economics",
                ],
            },
            # Enhanced title patterns
            "title_patterns": [
                # Academic patterns
                re.compile(r"^\s*([A-Z][^a-z]*(?:[a-z][^A-Z]*)*)\s*$", re.MULTILINE),
                # Question patterns
                re.compile(r"^\s*([A-Z][^?]*\?)\s*$", re.MULTILINE),
                # Colon patterns
                re.compile(r"^\s*([A-Z][^:]*:.*)\s*$", re.MULTILINE),
                # Number patterns
                re.compile(r"^\s*(\d+\.?\s+[A-Z][^a-z]*)\s*$", re.MULTILINE),
            ],
            # Enhanced author patterns
            "author_patterns": [
                # Standard patterns
                re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*$", re.MULTILINE),
                # With institutions
                re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\([^)]+\)\s*$", re.MULTILINE),
                # With emails
                re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[\w.-]+@[\w.-]+\s*$", re.MULTILINE),
                # Multiple authors
                re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)\s*$", re.MULTILINE),
            ],
            # Content quality patterns
            "quality_patterns": {
                "good_indicators": [
                    r"abstract\s*:",
                    r"introduction\s*:",
                    r"conclusion\s*:",
                    r"references\s*:",
                    r"bibliography\s*:",
                ],
                "bad_indicators": [
                    r"^\s*\d+\s*$",  # Page numbers only
                    r"^\s*[a-zA-Z]\s*$",  # Single letters
                    r"^\s*\W+\s*$",  # Only punctuation
                ],
            },
        }

    def _validate_pdf_file(self, pdf_file: Path):
        """Validate PDF file exists and is accessible"""
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_file}")
        
        if not pdf_file.is_file():
            raise ValueError(f"Path is not a file: {pdf_file}")
        
        if pdf_file.stat().st_size == 0:
            raise ValueError(f"PDF file is empty: {pdf_file}")

    def extract_metadata(self, pdf_path: str, **kwargs) -> PDFMetadata:
        """
        Extract comprehensive metadata from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            **kwargs: Additional options
            
        Returns:
            PDFMetadata object with extracted information
        """
        start_time = time.time()
        pdf_file = Path(pdf_path)
        
        # Validate input
        self._validate_pdf_file(pdf_file)
        
        # Check cache first
        cache_key = f"{pdf_file.absolute()}:{pdf_file.stat().st_mtime}"
        if cache_key in self.metadata_cache:
            logger.debug(f"Cache hit for {pdf_file.name}")
            return self.metadata_cache[cache_key]
        
        # Initialize metadata object
        metadata = PDFMetadata(
            path=str(pdf_file),
            filename=pdf_file.name,
            processing_time=0.0,
            source=MetadataSource.HEURISTIC,
            confidence=0.0,
            extraction_method="ultra_enhanced",
            repository_type="unknown",
            arxiv_id=None,
            title="",
            authors="",
            abstract=None,
            doi=None,
            language="en",
            page_count=0,
            text_quality=0.0
        )
        
        try:
            # Multi-engine text extraction
            text_results = self._multi_engine_extraction(pdf_file, **kwargs)
            
            # Select best text result
            best_result = max(text_results, key=lambda x: x.get('quality_score', 0))
            raw_text = best_result['text']
            text_blocks = best_result.get('blocks', [])
            metadata.text_quality = best_result.get('quality_score', 0)
            metadata.extraction_method = best_result.get('method', 'unknown')
            
            # Document structure analysis
            structure = None
            if text_blocks:
                structure = self._analyze_document_structure(text_blocks)
            
            # Repository detection and specialized extraction
            metadata.repository_type = self._detect_repository_type(raw_text)
            
            if metadata.repository_type in self.extractors:
                extractor = self.extractors[metadata.repository_type]
                extracted_metadata = extractor.extract_metadata(raw_text, pdf_file)
                
                # Merge specialized extraction results
                for field in ['title', 'authors', 'abstract', 'keywords', 'doi', 'year', 'journal']:
                    if hasattr(extracted_metadata, field):
                        value = getattr(extracted_metadata, field)
                        if value:
                            setattr(metadata, field, value)
            
            # Fallback to heuristic extraction if needed
            if not metadata.title:
                metadata.title = self._extract_title_multi_method(text_blocks, raw_text)
            
            if not metadata.authors:
                authors_list = self._extract_authors_multi_method(text_blocks, raw_text)
                metadata.authors = "; ".join(authors_list) if authors_list else ""
            
            # ArXiv API integration
            if metadata.repository_type == "arxiv" and self.config.get("extraction", {}).get("enable_arxiv_api", True):
                arxiv_metadata = self.arxiv_client.get_metadata_by_title(metadata.title)
                if arxiv_metadata:
                    # Merge ArXiv API results
                    for field in ['title', 'authors', 'abstract', 'doi', 'year']:
                        api_value = getattr(arxiv_metadata, field, None)
                        if api_value and (not getattr(metadata, field) or len(api_value) > len(str(getattr(metadata, field)))):
                            setattr(metadata, field, api_value)
                    
                    metadata.arxiv_id = arxiv_metadata.arxiv_id
                    metadata.confidence = max(metadata.confidence, 0.9)
            
            # Post-processing
            if metadata.title:
                metadata.title = self._normalise_title(metadata.title)
            
            # Calculate final confidence score
            metadata.confidence = self._calculate_confidence_score(metadata)
            
            # Cache result
            if self.config.get("extraction", {}).get("cache_enabled", True):
                self.metadata_cache[cache_key] = metadata
                self._manage_cache()
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {pdf_file}: {e}")
            metadata.warnings.append(str(e))
            metadata.confidence = 0.0
        
        finally:
            metadata.processing_time = time.time() - start_time
            self.stats['files_processed'] += 1
            self.performance_data.append({
                'file': str(pdf_file),
                'processing_time': metadata.processing_time,
                'quality_score': metadata.text_quality,
                'confidence_score': metadata.confidence,
                'method': metadata.extraction_method
            })
        
        return metadata

    def _calculate_confidence_score(self, metadata: PDFMetadata) -> float:
        """Calculate confidence score based on extracted metadata quality"""
        score = 0.0
        
        # Title quality (40%)
        if metadata.title:
            if len(metadata.title) > 10:
                score += 0.2
            if len(metadata.title) > 30:
                score += 0.2
        
        # Author quality (20%)
        if metadata.authors:
            score += 0.1
            if len(metadata.authors) > 1:
                score += 0.1
        
        # Abstract quality (20%)
        if metadata.abstract and len(metadata.abstract) > 50:
            score += 0.2
        
        # Repository detection (10%)
        if metadata.repository_type != "unknown":
            score += 0.1
        
        # Text quality (10%)
        if metadata.text_quality > 0.7:
            score += 0.1
        
        return min(score, 1.0)

    def _manage_cache(self):
        """Simple LRU cache management"""
        if len(self.metadata_cache) > self._max_cache_size:
            # Remove oldest entry
            oldest_key = min(self.metadata_cache.keys(), key=lambda k: self._cache_access_order.index(k) if k in self._cache_access_order else 0)
            del self.metadata_cache[oldest_key]
            if oldest_key in self._cache_access_order:
                self._cache_access_order.remove(oldest_key)

    def _detect_repository_type(self, text: str) -> str:
        """Detect the type of repository/source"""
        if not text:
            return "journal"
        
        text_lower = text.lower()
        
        for repo_type, patterns in self.patterns["repository_patterns"].items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return repo_type
        
        return "journal"

    def _multi_engine_extraction(self, pdf_file: Path, **kwargs) -> list:
        """
        Multi-engine text extraction using different methods.
        Returns list of extraction results with quality scores.
        """
        results = []
        
        try:
            # Method 1: PyMuPDF extraction
            import fitz
            doc = fitz.open(pdf_file)
            text_content = ""
            blocks = []
            
            for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages
                page = doc[page_num]
                page_text = page.get_text()
                text_content += page_text + "\n"
                
                # Extract text blocks with position info
                for block in page.get_text("dict")["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                if span.get("text", "").strip():
                                    blocks.append({
                                        "text": span["text"],
                                        "bbox": span["bbox"],
                                        "page": page_num,
                                        "font": span.get("font", ""),
                                        "size": span.get("size", 0)
                                    })
            
            doc.close()
            
            # Calculate quality score based on text length and structure
            quality = min(1.0, len(text_content.strip()) / 1000.0)
            if len(blocks) > 10:
                quality = min(1.0, quality + 0.2)
            
            results.append({
                "text": text_content.strip(),
                "blocks": blocks,
                "quality_score": quality,
                "method": "pymupdf"
            })
            
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
        
        try:
            # Method 2: pdfplumber extraction (fallback)
            import pdfplumber
            text_content = ""
            blocks = []
            
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages[:5]):  # Limit to first 5 pages
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                        
                        # Simple block extraction for pdfplumber
                        lines = page_text.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip():
                                blocks.append({
                                    "text": line.strip(),
                                    "page": page_num,
                                    "line": i
                                })
            
            quality = min(0.8, len(text_content.strip()) / 1000.0)  # Slightly lower than PyMuPDF
            
            results.append({
                "text": text_content.strip(),
                "blocks": blocks,
                "quality_score": quality,
                "method": "pdfplumber"
            })
            
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Ensure we have at least one result
        if not results:
            results.append({
                "text": "",
                "blocks": [],
                "quality_score": 0.0,
                "method": "fallback"
            })
        
        return results

    def _analyze_document_structure(self, text_blocks: list) -> dict:
        """Analyze document structure from text blocks."""
        if not text_blocks:
            return {"sections": [], "title_candidates": [], "author_candidates": []}
        
        structure = {
            "sections": [],
            "title_candidates": [],
            "author_candidates": [],
            "abstract_section": None,
            "references_section": None
        }
        
        # Identify potential titles (larger font, top of document)
        for i, block in enumerate(text_blocks[:10]):  # Check first 10 blocks
            text = block.get("text", "").strip()
            font_size = block.get("size", 0)
            
            if len(text) > 10 and len(text) < 200:  # Reasonable title length
                if font_size > 14 or (i < 3 and len(text) > 20):  # Large font or early position
                    structure["title_candidates"].append({
                        "text": text,
                        "position": i,
                        "font_size": font_size,
                        "confidence": min(1.0, (font_size / 20.0) + (0.3 if i < 3 else 0))
                    })
        
        # Look for author patterns
        author_patterns = [
            r'^[A-Z][a-z]+ [A-Z][a-z]+',  # First Last
            r'^[A-Z]\. [A-Z][a-z]+',      # F. Last
            r'^\w+@\w+\.',                # email pattern
        ]
        
        for i, block in enumerate(text_blocks[:20]):  # Check first 20 blocks
            text = block.get("text", "").strip()
            for pattern in author_patterns:
                if re.search(pattern, text):
                    structure["author_candidates"].append({
                        "text": text,
                        "position": i,
                        "confidence": 0.7
                    })
                    break
        
        return structure

    def _extract_title_multi_method(self, text_blocks: list, raw_text: str) -> str:
        """Extract title using multiple methods."""
        candidates = []
        
        # Method 1: From structure analysis
        structure = self._analyze_document_structure(text_blocks)
        for candidate in structure.get("title_candidates", []):
            candidates.append((candidate["text"], candidate["confidence"]))
        
        # Method 2: Pattern-based extraction from raw text
        lines = raw_text.split('\n')[:20]  # First 20 lines
        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) > 15 and len(line) < 200:  # Reasonable title length
                # Higher confidence for earlier lines
                confidence = max(0.3, 0.8 - (i * 0.05))
                candidates.append((line, confidence))
        
        # Method 3: Heuristic patterns
        title_patterns = [
            r'^[A-Z][^.!?]*[a-z][^.!?]*$',  # Capitalized, no punctuation
            r'^[A-Z].*:\s*[A-Z].*',          # Main title: subtitle
        ]
        
        for line in lines[:10]:
            line = line.strip()
            for pattern in title_patterns:
                if re.match(pattern, line) and len(line) > 20:
                    candidates.append((line, 0.6))
        
        # Return best candidate
        if candidates:
            best_title = max(candidates, key=lambda x: x[1])
            return self._normalise_title(best_title[0])
        
        return ""

    def _extract_authors_multi_method(self, text_blocks: list, raw_text: str) -> list:
        """Extract authors using multiple methods."""
        authors = []
        
        # Method 1: From structure analysis
        structure = self._analyze_document_structure(text_blocks)
        for candidate in structure.get("author_candidates", []):
            authors.append(candidate["text"])
        
        # Method 2: Pattern-based extraction
        author_patterns = [
            r'[A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)*\s+[A-Z][a-z]+',  # Full names
            r'[A-Z]\.\s*[A-Z][a-z]+',                            # Initials + last name
        ]
        
        lines = raw_text.split('\n')[:30]  # Check first 30 lines
        for line in lines:
            line = line.strip()
            for pattern in author_patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if match not in authors and len(match) > 3:
                        authors.append(match)
        
        # Clean and deduplicate
        cleaned_authors = []
        for author in authors[:10]:  # Limit to first 10
            author = re.sub(r'\s+', ' ', author.strip())
            if author and author not in cleaned_authors:
                cleaned_authors.append(author)
        
        return cleaned_authors

    def _extract_metadata_by_repository(self, repository_type: str, text: str, pdf_file: Path) -> dict:
        """Extract metadata using repository-specific extractor if available."""
        if repository_type in self.extractors:
            try:
                extractor = self.extractors[repository_type]
                return extractor.extract_metadata(text, pdf_file)
            except Exception as e:
                logger.warning(f"Repository-specific extraction failed for {repository_type}: {e}")
        
        # Fallback: return empty metadata structure
        return {
            "title": "",
            "authors": [],
            "abstract": "",
            "keywords": [],
            "doi": None,
            "year": None,
            "journal": None
        }

    def _cache_metadata(self, cache_key: str, metadata) -> None:
        """Cache metadata result."""
        try:
            self.metadata_cache[cache_key] = metadata
            if cache_key not in self._cache_access_order:
                self._cache_access_order.append(cache_key)
            else:
                # Move to end (most recently used)
                self._cache_access_order.remove(cache_key)
                self._cache_access_order.append(cache_key)
            
            # Manage cache size
            self._manage_cache()
            
        except Exception as e:
            logger.warning(f"Failed to cache metadata: {e}")

    def get_stats(self) -> dict:
        """Get processing statistics"""
        return dict(self.stats)

    def get_performance_data(self) -> list:
        """Get performance data"""
        return self.performance_data.copy()

    def clear_cache(self):
        """Clear all caches"""
        self.text_cache.clear()
        self.metadata_cache.clear()
        self.structure_cache.clear()
        self._cache_access_order.clear()
        logger.info("All caches cleared")