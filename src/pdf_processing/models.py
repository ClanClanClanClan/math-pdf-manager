"""
PDF Processing Models

Data models and structures for PDF processing operations.
Extracted from parsers.pdf_parser.py for better modularity.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


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
    abstract: Optional[str] = None

    @property
    def confidence_score(self) -> float:
        """Alias for confidence for backward compatibility"""
        return self.confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with all fields"""
        return {
            "title": self.title,
            "authors": self.authors,
            "source": (
                self.source.value if hasattr(self.source, "value") else str(self.source)
            ),
            "confidence": self.confidence,
            "filename": self.filename,
            "path": self.path,
            "error": self.error,
            "warnings": self.warnings,
            "processing_time": self.processing_time,
            "repository_type": self.repository_type,
            "language": self.language,
            "is_published": self.is_published,
            "page_count": self.page_count,
            "text_quality": self.text_quality,
            "extraction_method": self.extraction_method,
            "arxiv_id": self.arxiv_id,
            "doi": self.doi,
            "categories": self.categories,
            "abstract": self.abstract,
        }


@dataclass
class TextBlock:
    """Enhanced text block with position and formatting"""

    text: str
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    font_size: float = 12.0
    font_name: str = ""
    is_bold: bool = False
    is_italic: bool = False
    page_num: int = 0
    confidence: float = 1.0

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class DocumentStructure:
    """Enhanced document structure analysis"""

    title_candidates: List[Tuple[str, float, Dict[str, Any]]] = field(
        default_factory=list
    )
    author_candidates: List[Tuple[str, float, Dict[str, Any]]] = field(
        default_factory=list
    )
    repository_type: Optional[str] = None
    is_published: bool = False
    is_multi_column: bool = False
    has_header_footer: bool = False
    language: str = "en"
    text_quality: float = 0.0
    structure_score: float = 0.0
    extraction_challenges: List[str] = field(default_factory=list)


@dataclass
class ArxivMetadata:
    """Metadata extracted from arXiv API"""

    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    primary_category: str
    published: str
    updated: str
    doi: Optional[str] = None
    journal_ref: Optional[str] = None
    comment: Optional[str] = None
    pdf_url: str = ""
    confidence: float = 0.95


# Backward compatibility aliases
Metadata = PDFMetadata
Structure = DocumentStructure
Block = TextBlock