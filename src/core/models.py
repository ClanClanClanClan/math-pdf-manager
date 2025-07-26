"""
Data models for Math-PDF Manager

This module contains all data structures used throughout the application,
providing type safety and clear interfaces.
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


class MetadataSource(Enum):
    """Source of metadata extraction"""
    UNKNOWN = "unknown"
    FILENAME = "filename"
    PDF_TEXT = "pdf_text"
    PDF_METADATA = "pdf_metadata"
    ARXIV_API = "arxiv_api"
    CROSSREF_API = "crossref_api"
    SCHOLAR_API = "scholar_api"
    GROBID = "grobid"
    OCR = "ocr"
    MANUAL = "manual"


class DocumentType(Enum):
    """Type of document"""
    UNKNOWN = "unknown"
    JOURNAL_ARTICLE = "journal_article"
    CONFERENCE_PAPER = "conference_paper"
    ARXIV_PREPRINT = "arxiv_preprint"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    THESIS = "thesis"
    TECHNICAL_REPORT = "technical_report"
    WORKING_PAPER = "working_paper"


class ValidationSeverity(Enum):
    """Severity of validation issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Author:
    """Structured author representation"""
    given_name: str = ""
    family_name: str = ""
    full_name: str = ""
    initials: str = ""
    suffix: Optional[str] = None
    affiliation: Optional[str] = None
    orcid: Optional[str] = None
    email: Optional[str] = None
    
    def __post_init__(self):
        """Compute derived fields"""
        if not self.full_name and self.given_name and self.family_name:
            self.full_name = f"{self.given_name} {self.family_name}"
        if not self.initials and self.given_name:
            self.initials = "".join(name[0].upper() + "." 
                                   for name in self.given_name.split())


@dataclass
class PDFMetadata:
    """Enhanced metadata with detailed analysis"""
    # Basic metadata
    title: str = "Unknown Title"
    authors: List[Author] = field(default_factory=list)
    authors_string: str = "Unknown"  # Legacy compatibility
    year: Optional[int] = None
    
    # Source information
    source: MetadataSource = MetadataSource.UNKNOWN
    confidence: float = 0.0
    filename: str = ""
    path: Path = field(default_factory=Path)
    
    # Document classification
    document_type: DocumentType = DocumentType.UNKNOWN
    repository_type: Optional[str] = None
    language: str = "en"
    is_published: bool = False
    
    # Identifiers
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    isbn: Optional[str] = None
    issn: Optional[str] = None
    pmid: Optional[str] = None
    
    # Content metadata
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    references_count: int = 0
    page_count: int = 0
    
    # Quality metrics
    text_quality: float = 0.0
    extraction_method: str = "unknown"
    ocr_confidence: Optional[float] = None
    
    # Technical details
    pdf_version: Optional[str] = None
    file_size: int = 0
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    
    # Processing information
    processing_time: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    extraction_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationIssue:
    """Validation issue with context"""
    severity: ValidationSeverity
    category: str
    message: str
    field: Optional[str] = None
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None
    line_number: Optional[int] = None
    position: Optional[int] = None
    context: Optional[str] = None
    fix_available: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'field': self.field,
            'current_value': self.current_value,
            'suggested_value': self.suggested_value,
            'line_number': self.line_number,
            'position': self.position,
            'context': self.context,
            'fix_available': self.fix_available
        }


@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Optional[PDFMetadata] = None
    suggested_filename: Optional[str] = None
    validation_time: float = 0.0
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues"""
        return sum(1 for issue in self.issues 
                  if issue.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues"""
        return sum(1 for issue in self.issues 
                  if issue.severity == ValidationSeverity.WARNING)
    
    @property
    def has_auto_fixable_issues(self) -> bool:
        """Check if any issues can be auto-fixed"""
        return any(issue.fix_available for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'is_valid': self.is_valid,
            'issues': [issue.to_dict() for issue in self.issues],
            'suggested_filename': self.suggested_filename,
            'validation_time': self.validation_time,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'has_auto_fixable_issues': self.has_auto_fixable_issues
        }


@dataclass
class ScanResult:
    """Result of directory scanning"""
    total_files: int = 0
    pdf_files: int = 0
    skipped_files: int = 0
    error_files: int = 0
    scan_time: float = 0.0
    files: List[Path] = field(default_factory=list)
    errors: Dict[Path, str] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DuplicateGroup:
    """Group of duplicate files"""
    master_file: Path
    duplicates: List[Path]
    similarity_scores: Dict[Path, float]
    metadata: Dict[Path, PDFMetadata]
    suggested_action: str = "review"
    
    @property
    def size(self) -> int:
        """Total number of files in group (including master)"""
        return len(self.duplicates) + 1
    
    @property
    def total_size_bytes(self) -> int:
        """Total disk space used by duplicates"""
        total = 0
        for path in [self.master_file] + self.duplicates:
            if path.exists():
                total += path.stat().st_size
        return total


@dataclass
class ProcessingStats:
    """Statistics for processing operations"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    files_processed: int = 0
    files_succeeded: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    peak_memory_usage: int = 0
    api_calls_made: Dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    
    def complete(self):
        """Mark processing as complete and calculate final stats"""
        self.end_time = datetime.now()
        self.total_processing_time = (self.end_time - self.start_time).total_seconds()
        if self.files_processed > 0:
            self.average_processing_time = self.total_processing_time / self.files_processed