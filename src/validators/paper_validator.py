#!/usr/bin/env python3
"""
Enhanced Paper Validation Pipeline
==================================

Comprehensive validation for downloaded academic papers including:
- PDF validation and repair
- Content verification
- Metadata extraction and validation
- Duplicate detection
- Quality assessment
"""

import os
import hashlib
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# PDF processing libraries
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger("paper_validator")

# Validation constants
PDF_MAGIC = b"%PDF"
MIN_PDF_SIZE = 1000  # 1KB minimum
MAX_PDF_SIZE = 100 * 1024 * 1024  # 100MB maximum
MIN_PAGES = 1
MAX_PAGES = 5000
MIN_TEXT_LENGTH = 100  # Minimum text characters for valid paper


class ValidationStatus(Enum):
    """Validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    CORRUPTED = "corrupted"
    INCOMPLETE = "incomplete"
    DUPLICATE = "duplicate"
    LOW_QUALITY = "low_quality"
    NEEDS_OCR = "needs_ocr"
    REPAIRED = "repaired"


class ContentType(Enum):
    """Type of academic content."""
    RESEARCH_PAPER = "research_paper"
    PREPRINT = "preprint"
    THESIS = "thesis"
    BOOK_CHAPTER = "book_chapter"
    CONFERENCE_PAPER = "conference_paper"
    TECHNICAL_REPORT = "technical_report"
    REVIEW = "review"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Results of paper validation."""
    file_path: str
    status: ValidationStatus
    file_size: int
    file_hash: str
    page_count: Optional[int] = None
    content_type: Optional[ContentType] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    text_preview: Optional[str] = None
    issues: List[str] = None
    repair_actions: List[str] = None
    quality_score: Optional[float] = None
    validation_timestamp: datetime = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.repair_actions is None:
            self.repair_actions = []
        if self.validation_timestamp is None:
            self.validation_timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        if self.content_type:
            data['content_type'] = self.content_type.value
        data['validation_timestamp'] = self.validation_timestamp.isoformat()
        return data


class PDFValidator:
    """Core PDF validation functionality."""
    
    def __init__(self):
        self.duplicate_cache: Dict[str, str] = {}
        self._load_duplicate_cache()
    
    def _load_duplicate_cache(self):
        """Load cache of known file hashes."""
        cache_file = Path.home() / ".academic_papers" / "duplicate_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.duplicate_cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load duplicate cache: {e}")
    
    def _save_duplicate_cache(self):
        """Save duplicate cache."""
        cache_file = Path.home() / ".academic_papers" / "duplicate_cache.json"
        cache_file.parent.mkdir(exist_ok=True)
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.duplicate_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save duplicate cache: {e}")
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def check_basic_validity(self, file_path: str) -> Tuple[bool, List[str]]:
        """Perform basic PDF validity checks."""
        issues = []
        
        # Check file exists
        if not os.path.exists(file_path):
            issues.append("File does not exist")
            return False, issues
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size < MIN_PDF_SIZE:
            issues.append(f"File too small ({file_size} bytes)")
            return False, issues
        
        if file_size > MAX_PDF_SIZE:
            issues.append(f"File too large ({file_size} bytes)")
            return False, issues
        
        # Check PDF header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != PDF_MAGIC:
                    issues.append("Invalid PDF header")
                    return False, issues
        except Exception as e:
            issues.append(f"Cannot read file: {e}")
            return False, issues
        
        return True, issues
    
    def extract_pdf_info(self, file_path: str) -> Dict[str, Any]:
        """Extract information from PDF using multiple libraries."""
        info = {
            'page_count': None,
            'metadata': {},
            'text_preview': None,
            'has_text': False,
            'has_images': False,
            'extraction_method': None
        }
        
        # Try PyMuPDF first (most reliable)
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                info['page_count'] = len(doc)
                info['metadata'] = doc.metadata
                
                # Extract text from first few pages
                text_parts = []
                for page_num in range(min(3, len(doc))):
                    page = doc[page_num]
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(text)
                        info['has_text'] = True
                    
                    # Check for images
                    if page.get_images():
                        info['has_images'] = True
                
                if text_parts:
                    info['text_preview'] = '\n'.join(text_parts)[:1000]
                
                info['extraction_method'] = 'pymupdf'
                doc.close()
                return info
                
            except Exception as e:
                logger.debug(f"PyMuPDF extraction failed: {e}")
        
        # Try pdfplumber
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(file_path) as pdf:
                    info['page_count'] = len(pdf.pages)
                    info['metadata'] = pdf.metadata
                    
                    # Extract text
                    text_parts = []
                    for i, page in enumerate(pdf.pages[:3]):
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                            info['has_text'] = True
                    
                    if text_parts:
                        info['text_preview'] = '\n'.join(text_parts)[:1000]
                    
                    info['extraction_method'] = 'pdfplumber'
                    return info
                    
            except Exception as e:
                logger.debug(f"pdfplumber extraction failed: {e}")
        
        # Try PyPDF2 as fallback
        if PYPDF2_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    info['page_count'] = len(reader.pages)
                    
                    if reader.metadata:
                        info['metadata'] = {
                            'title': reader.metadata.get('/Title'),
                            'author': reader.metadata.get('/Author'),
                            'subject': reader.metadata.get('/Subject'),
                            'creator': reader.metadata.get('/Creator'),
                        }
                    
                    # Extract text
                    text_parts = []
                    for i in range(min(3, len(reader.pages))):
                        try:
                            text = reader.pages[i].extract_text()
                            if text.strip():
                                text_parts.append(text)
                                info['has_text'] = True
                        except Exception:
                            pass
                    
                    if text_parts:
                        info['text_preview'] = '\n'.join(text_parts)[:1000]
                    
                    info['extraction_method'] = 'pypdf2'
                    return info
                    
            except Exception as e:
                logger.debug(f"PyPDF2 extraction failed: {e}")
        
        return info
    
    def identify_content_type(self, text: str, metadata: Dict[str, Any]) -> ContentType:
        """Identify the type of academic content based on text and metadata."""
        if not text:
            return ContentType.UNKNOWN
        
        text_lower = text.lower()
        
        # Check for thesis indicators
        thesis_keywords = ['dissertation', 'thesis', 'doctoral', 'master of', 'submitted in partial']
        if any(keyword in text_lower[:2000] for keyword in thesis_keywords):
            return ContentType.THESIS
        
        # Check for book chapter
        if 'chapter' in text_lower[:500] and ('book' in text_lower[:500] or '©' in text[:500]):
            return ContentType.BOOK_CHAPTER
        
        # Check for conference paper
        conference_keywords = ['conference', 'proceedings', 'symposium', 'workshop']
        if any(keyword in text_lower[:1000] for keyword in conference_keywords):
            return ContentType.CONFERENCE_PAPER
        
        # Check for technical report
        if 'technical report' in text_lower[:1000] or 'tech report' in text_lower[:1000]:
            return ContentType.TECHNICAL_REPORT
        
        # Check for review
        review_keywords = ['review', 'survey', 'overview', 'state of the art']
        if any(keyword in text_lower[:500] for keyword in review_keywords):
            return ContentType.REVIEW
        
        # Check for preprint
        preprint_keywords = ['preprint', 'arxiv', 'biorxiv', 'medrxiv', 'ssrn']
        if any(keyword in text_lower[:1000] for keyword in preprint_keywords):
            return ContentType.PREPRINT
        
        # Default to research paper
        return ContentType.RESEARCH_PAPER
    
    def calculate_quality_score(self, info: Dict[str, Any], issues: List[str]) -> float:
        """Calculate a quality score for the PDF."""
        score = 1.0
        
        # Deduct for issues
        score -= len(issues) * 0.1
        
        # Check page count
        page_count = info.get('page_count', 0)
        if page_count < 2:
            score -= 0.3
        elif page_count > 100:
            score -= 0.1
        
        # Check for text
        if not info.get('has_text'):
            score -= 0.5
        
        # Check text length
        text_preview = info.get('text_preview', '')
        if len(text_preview) < MIN_TEXT_LENGTH:
            score -= 0.3
        
        # Check metadata
        metadata = info.get('metadata', {})
        if not metadata.get('title') and not metadata.get('Title'):
            score -= 0.1
        if not metadata.get('author') and not metadata.get('Author'):
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def check_duplicate(self, file_hash: str, file_path: str) -> Optional[str]:
        """Check if file is a duplicate based on hash."""
        if file_hash in self.duplicate_cache:
            existing_path = self.duplicate_cache[file_hash]
            if existing_path != file_path and os.path.exists(existing_path):
                return existing_path
        
        # Add to cache
        self.duplicate_cache[file_hash] = file_path
        self._save_duplicate_cache()
        
        return None
    
    def validate_paper(self, file_path: str) -> ValidationResult:
        """Perform complete validation of a paper."""
        logger.info(f"Validating paper: {file_path}")
        
        # Basic validity checks
        is_valid, issues = self.check_basic_validity(file_path)
        if not is_valid:
            return ValidationResult(
                file_path=file_path,
                status=ValidationStatus.INVALID,
                file_size=0,
                file_hash="",
                issues=issues
            )
        
        # Calculate file info
        file_size = os.path.getsize(file_path)
        file_hash = self.calculate_file_hash(file_path)
        
        # Check for duplicates
        duplicate_path = self.check_duplicate(file_hash, file_path)
        if duplicate_path:
            return ValidationResult(
                file_path=file_path,
                status=ValidationStatus.DUPLICATE,
                file_size=file_size,
                file_hash=file_hash,
                issues=[f"Duplicate of {duplicate_path}"]
            )
        
        # Extract PDF information
        info = self.extract_pdf_info(file_path)
        
        # Additional validation
        if info['page_count'] is None:
            issues.append("Cannot determine page count")
            status = ValidationStatus.CORRUPTED
        elif info['page_count'] < MIN_PAGES:
            issues.append(f"Too few pages ({info['page_count']})")
            status = ValidationStatus.INCOMPLETE
        elif info['page_count'] > MAX_PAGES:
            issues.append(f"Too many pages ({info['page_count']})")
            status = ValidationStatus.INVALID
        else:
            status = ValidationStatus.VALID
        
        # Check for text content
        if not info.get('has_text') and info.get('has_images'):
            issues.append("No extractable text (may need OCR)")
            status = ValidationStatus.NEEDS_OCR
        elif not info.get('has_text'):
            issues.append("No content found")
            status = ValidationStatus.INVALID
        
        # Identify content type
        content_type = self.identify_content_type(
            info.get('text_preview', ''),
            info.get('metadata', {})
        )
        
        # Calculate quality score
        quality_score = self.calculate_quality_score(info, issues)
        if quality_score < 0.5 and status == ValidationStatus.VALID:
            status = ValidationStatus.LOW_QUALITY
        
        return ValidationResult(
            file_path=file_path,
            status=status,
            file_size=file_size,
            file_hash=file_hash,
            page_count=info.get('page_count'),
            content_type=content_type,
            extracted_metadata=info.get('metadata'),
            text_preview=info.get('text_preview'),
            issues=issues,
            quality_score=quality_score
        )


class PDFRepairer:
    """Attempt to repair corrupted PDFs."""
    
    def repair_pdf(self, file_path: str, output_path: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Attempt to repair a corrupted PDF."""
        if output_path is None:
            output_path = file_path
        
        actions = []
        
        # Try PyMuPDF repair
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                
                # Remove invalid objects
                doc.clean()
                actions.append("Cleaned invalid objects")
                
                # Save repaired version
                doc.save(output_path, garbage=4, deflate=True)
                doc.close()
                
                actions.append("Saved repaired PDF")
                return True, actions
                
            except Exception as e:
                logger.warning(f"PyMuPDF repair failed: {e}")
        
        # Try ghostscript repair (if available)
        try:
            import subprocess
            
            temp_file = output_path + '.tmp'
            cmd = [
                'gs', '-o', temp_file, '-sDEVICE=pdfwrite',
                '-dPDFSETTINGS=/prepress', file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                os.replace(temp_file, output_path)
                actions.append("Repaired with Ghostscript")
                return True, actions
            else:
                logger.warning(f"Ghostscript repair failed: {result.stderr}")
                
        except Exception as e:
            logger.debug(f"Ghostscript not available: {e}")
        
        return False, actions


class OCRProcessor:
    """Process PDFs that need OCR."""
    
    def __init__(self):
        self.available = OCR_AVAILABLE
    
    def process_pdf(self, file_path: str, output_path: Optional[str] = None) -> bool:
        """OCR process a PDF file."""
        if not self.available:
            logger.error("OCR libraries not available")
            return False
        
        if output_path is None:
            output_path = file_path.replace('.pdf', '_ocr.pdf')
        
        try:
            # Convert PDF to images
            images = convert_from_path(file_path)
            
            # Process each page
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            c = canvas.Canvas(output_path, pagesize=letter)
            
            for i, image in enumerate(images):
                # OCR the image
                text = pytesseract.image_to_string(image)
                
                # Add text to PDF
                c.drawString(100, 750, text)
                c.showPage()
            
            c.save()
            return True
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return False


# Global validator instance
_validator: Optional[PDFValidator] = None


def get_validator() -> PDFValidator:
    """Get or create the global validator instance."""
    global _validator
    if _validator is None:
        _validator = PDFValidator()
    return _validator


def validate_paper(file_path: str) -> ValidationResult:
    """Validate a paper file."""
    validator = get_validator()
    return validator.validate_paper(file_path)


def repair_pdf(file_path: str, output_path: Optional[str] = None) -> Tuple[bool, List[str]]:
    """Attempt to repair a PDF file."""
    repairer = PDFRepairer()
    return repairer.repair_pdf(file_path, output_path)


def process_ocr(file_path: str, output_path: Optional[str] = None) -> bool:
    """OCR process a PDF file."""
    processor = OCRProcessor()
    return processor.process_pdf(file_path, output_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        result = validate_paper(file_path)
        
        print(f"Validation Result: {result.status.value}")
        print(f"File Hash: {result.file_hash}")
        print(f"Page Count: {result.page_count}")
        print(f"Content Type: {result.content_type.value if result.content_type else 'Unknown'}")
        print(f"Quality Score: {result.quality_score:.2f}" if result.quality_score else "N/A")
        
        if result.issues:
            print(f"Issues: {', '.join(result.issues)}")
        
        if result.status == ValidationStatus.CORRUPTED:
            print("\nAttempting repair...")
            success, actions = repair_pdf(file_path)
            if success:
                print(f"Repair successful: {', '.join(actions)}")
            else:
                print("Repair failed")
    else:
        print("Usage: python paper_validator.py <pdf_file>")