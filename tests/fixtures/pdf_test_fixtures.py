#!/usr/bin/env python3
"""
PDF Test Fixtures and Mock Framework

Provides comprehensive test fixtures for PDF processing tests including:
- Mock PDF files with realistic content
- Publisher-specific test cases
- Mathematical notation samples
- Multi-language test cases
- Error condition simulations
- Performance test data generators
"""

import io
import json
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, Mock


@dataclass
class MockPDFDocument:
    """Mock PDF document for testing."""

    title: str
    authors: List[str]
    abstract: str
    content: str
    publisher: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    year: Optional[int] = None
    pages: int = 1
    has_math: bool = False
    language: str = "en"
    file_size: int = 1024


@dataclass
class MockTextElement:
    """Mock text element for layout analysis testing."""

    text: str
    bbox: Tuple[float, float, float, float]
    font_name: str
    font_size: float
    is_bold: bool = False
    is_italic: bool = False
    page_number: int = 1
    confidence: float = 1.0


class PDFTestFixtures:
    """Central repository for PDF test fixtures."""

    def __init__(self):
        self.mock_documents = self._create_mock_documents()
        self.test_cases = self._create_test_cases()

    def _create_mock_documents(self) -> Dict[str, MockPDFDocument]:
        """Create a comprehensive set of mock PDF documents."""
        documents = {}

        # IEEE Paper
        documents["ieee_ml"] = MockPDFDocument(
            title="Deep Learning Approaches for Automated Feature Extraction in Computer Vision",
            authors=["John Smith", "Mary Johnson", "Robert Chen"],
            abstract="This paper presents novel deep learning architectures for automated feature extraction in computer vision applications. We demonstrate significant improvements over traditional methods.",
            content="1. Introduction\nComputer vision has evolved rapidly with the advent of deep learning...\n\n2. Related Work\nPrevious approaches to feature extraction...",
            publisher="IEEE",
            doi="10.1109/TPAMI.2024.12345",
            year=2024,
            pages=12,
            has_math=True,
        )

        # ArXiv Preprint with Mathematics
        documents["arxiv_math"] = MockPDFDocument(
            title="On the Convergence Properties of Stochastic Gradient Descent in Non-Convex Settings",
            authors=["Alice Anderson", "Bob Wilson"],
            abstract="We analyze the convergence properties of SGD when applied to non-convex optimization problems, providing theoretical guarantees under mild assumptions.",
            content="Abstract\nWe analyze the convergence properties...\n\n1 Introduction\nStochastic gradient descent (SGD) is a fundamental optimization algorithm...",
            publisher="ArXiv",
            arxiv_id="2024.01234",
            year=2024,
            pages=25,
            has_math=True,
        )

        # Springer Article
        documents["springer_bio"] = MockPDFDocument(
            title="Advances in Protein Structure Prediction Using Machine Learning",
            authors=["Dr. Sarah Miller", "Prof. James Wilson", "Dr. Lisa Chen"],
            abstract="Recent developments in machine learning have revolutionized protein structure prediction. This review examines current state-of-the-art methods.",
            content="Introduction\nProtein structure prediction has been a central challenge in computational biology...",
            publisher="Springer",
            doi="10.1007/s00401-024-12345-6",
            year=2024,
            pages=18,
        )

        # ACM Conference Paper
        documents["acm_systems"] = MockPDFDocument(
            title="Scalable Distributed Computing Framework for Large-Scale Data Analytics",
            authors=["Michael Brown", "Jennifer Davis", "David Lee"],
            abstract="We present a novel distributed computing framework designed for processing large-scale datasets with improved fault tolerance and performance.",
            content="1. INTRODUCTION\nThe exponential growth of data in modern applications...\n\n2. RELATED WORK\nExisting distributed computing frameworks...",
            publisher="ACM",
            doi="10.1145/3445678.3445679",
            year=2024,
            pages=10,
        )

        # Nature Article
        documents["nature_physics"] = MockPDFDocument(
            title="Quantum Entanglement in Many-Body Systems: Theory and Experimental Verification",
            authors=["Prof. Elena Rodriguez", "Dr. Thomas Anderson", "Dr. Maria Garcia"],
            abstract="We investigate quantum entanglement phenomena in many-body quantum systems, providing both theoretical analysis and experimental validation.",
            content="Quantum entanglement is one of the most fundamental aspects of quantum mechanics...",
            publisher="Nature",
            doi="10.1038/s41567-024-02345-1",
            year=2024,
            pages=8,
            has_math=True,
        )

        # Mathematical Journal
        documents["math_journal"] = MockPDFDocument(
            title="Riemann Hypothesis and L-Functions: New Computational Approaches",
            authors=["Prof. Alexander Petrov", "Dr. Catherine Williams"],
            abstract="We present new computational methods for investigating the Riemann Hypothesis through the lens of L-functions, with numerical results supporting the conjecture.",
            content="1. Introduction\nThe Riemann Hypothesis, formulated in 1859, remains one of the most important unsolved problems in mathematics...",
            publisher="American Mathematical Society",
            doi="10.1090/jams/987654",
            year=2024,
            pages=35,
            has_math=True,
        )

        # Multi-language Paper (French)
        documents["french_cs"] = MockPDFDocument(
            title="Algorithmes d'apprentissage automatique pour la reconnaissance vocale",
            authors=["Dr. Pierre Dubois", "Prof. Marie Lefebvre"],
            abstract="Cet article présente de nouveaux algorithmes d'apprentissage automatique pour améliorer la reconnaissance vocale en français.",
            content="1. Introduction\nLa reconnaissance vocale est un domaine en pleine expansion...",
            publisher="HAL",
            year=2024,
            pages=15,
            language="fr",
        )

        # Elsevier Medical Journal
        documents["elsevier_medical"] = MockPDFDocument(
            title="Clinical Applications of AI in Medical Imaging: A Comprehensive Review",
            authors=["Dr. Susan Thompson", "Dr. Richard Clark", "Prof. Jennifer Martinez"],
            abstract="This comprehensive review examines the current state and future prospects of artificial intelligence applications in medical imaging diagnostics.",
            content="1. Introduction\nArtificial intelligence (AI) has transformed medical imaging...",
            publisher="Elsevier",
            doi="10.1016/j.media.2024.12345",
            year=2024,
            pages=22,
        )

        # Technical Report
        documents["tech_report"] = MockPDFDocument(
            title="Performance Evaluation of Distributed Database Systems in Cloud Environments",
            authors=["Research Team"],
            abstract="This technical report evaluates the performance characteristics of various distributed database systems when deployed in cloud computing environments.",
            content="Executive Summary\nThis report presents a comprehensive evaluation...",
            publisher="Technical Report",
            year=2024,
            pages=45,
        )

        # Thesis/Dissertation
        documents["phd_thesis"] = MockPDFDocument(
            title="Novel Approaches to Natural Language Processing in Low-Resource Languages",
            authors=["Jane Thompson"],
            abstract="This dissertation explores novel computational approaches for natural language processing in languages with limited digital resources.",
            content="Abstract\nNatural language processing (NLP) has achieved remarkable success...\n\nChapter 1: Introduction\nThe field of natural language processing...",
            publisher="University",
            year=2024,
            pages=180,
        )

        return documents

    def _create_test_cases(self) -> Dict[str, Dict[str, Any]]:
        """Create specific test cases for different scenarios."""
        test_cases = {}

        # Title extraction test cases
        test_cases["title_extraction"] = {
            "simple_title": {
                "elements": [
                    MockTextElement(
                        text="Machine Learning in Computer Vision",
                        bbox=(100, 750, 500, 770),
                        font_name="Times-Bold",
                        font_size=16.0,
                        is_bold=True,
                        page_number=1,
                    )
                ],
                "expected_title": "Machine Learning in Computer Vision",
            },
            "multiline_title": {
                "elements": [
                    MockTextElement(
                        text="Advanced Methods for Large-Scale",
                        bbox=(100, 750, 500, 770),
                        font_name="Times-Bold",
                        font_size=16.0,
                        is_bold=True,
                        page_number=1,
                    ),
                    MockTextElement(
                        text="Distributed Computing Systems",
                        bbox=(100, 730, 480, 750),
                        font_name="Times-Bold",
                        font_size=16.0,
                        is_bold=True,
                        page_number=1,
                    ),
                ],
                "expected_title": "Advanced Methods for Large-Scale Distributed Computing Systems",
            },
            "mathematical_title": {
                "elements": [
                    MockTextElement(
                        text="Analysis of L²-spaces and α-stable Processes",
                        bbox=(100, 750, 500, 770),
                        font_name="Times-Bold",
                        font_size=16.0,
                        is_bold=True,
                        page_number=1,
                    )
                ],
                "expected_title": "Analysis of L²-spaces and α-stable Processes",
            },
        }

        # Author extraction test cases
        test_cases["author_extraction"] = {
            "single_author": {
                "elements": [
                    MockTextElement(
                        text="John Smith",
                        bbox=(150, 720, 300, 735),
                        font_name="Times",
                        font_size=12.0,
                        page_number=1,
                    ),
                    MockTextElement(
                        text="University of Example",
                        bbox=(150, 705, 350, 720),
                        font_name="Times",
                        font_size=10.0,
                        page_number=1,
                    ),
                ],
                "expected_authors": ["John Smith"],
            },
            "multiple_authors": {
                "elements": [
                    MockTextElement(
                        text="John Smith¹, Mary Johnson², Bob Wilson¹",
                        bbox=(100, 720, 500, 735),
                        font_name="Times",
                        font_size=12.0,
                        page_number=1,
                    ),
                    MockTextElement(
                        text="¹University of Example, ²MIT",
                        bbox=(100, 705, 400, 720),
                        font_name="Times",
                        font_size=10.0,
                        page_number=1,
                    ),
                ],
                "expected_authors": ["John Smith", "Mary Johnson", "Bob Wilson"],
            },
        }

        # Mathematical notation test cases
        test_cases["math_notation"] = {
            "latex_symbols": {
                "input": r"The function $f(x) = \alpha x^2 + \beta \sin(\pi x)$ converges",
                "expected_output": "The function f(x) = α x^2 + β sin(π x) converges",
            },
            "unicode_math": {
                "input": "For all x ∈ ℝ, we have x ≤ ∞",
                "expected_output": "For all x ∈ ℝ, we have x ≤ ∞",
            },
            "subscripts_superscripts": {
                "input": "H₂O and E = mc²",
                "expected_output": "H_2O and E = mc^2",
            },
        }

        # Error conditions test cases
        test_cases["error_conditions"] = {
            "corrupted_pdf": {
                "content": b"This is not a PDF file",
                "expected_error": "Invalid PDF format",
            },
            "empty_pdf": {"content": b"%PDF-1.4\n%%EOF", "expected_text": ""},
            "password_protected": {
                "content": b"%PDF-1.4\n/Encrypt\n%%EOF",
                "expected_error": "Password protected",
            },
        }

        # Performance test cases
        test_cases["performance"] = {
            "large_document": {
                "pages": 1000,
                "content_per_page": "Large content " * 1000,
                "expected_processing_time": 30.0,  # seconds
            },
            "batch_processing": {
                "document_count": 100,
                "expected_throughput": 10.0,  # documents per second
            },
        }

        return test_cases

    def get_mock_document(self, doc_id: str) -> MockPDFDocument:
        """Get a mock document by ID."""
        return self.mock_documents.get(doc_id)

    def get_test_case(self, category: str, case_id: str) -> Dict[str, Any]:
        """Get a specific test case."""
        return self.test_cases.get(category, {}).get(case_id, {})

    def create_temporary_pdf(self, doc_id: str) -> str:
        """Create a temporary PDF file from a mock document."""
        doc = self.get_mock_document(doc_id)
        if not doc:
            raise ValueError(f"Unknown document ID: {doc_id}")

        # Create minimal PDF content
        pdf_content = self._generate_pdf_content(doc)

        # Write to temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            return tmp_file.name

    def _generate_pdf_content(self, doc: MockPDFDocument) -> bytes:
        """Generate minimal PDF content for a mock document."""
        # This is a simplified PDF structure
        # In reality, you might use reportlab or similar to generate proper PDFs

        title_obj = f"({doc.title}) Tj"
        authors_obj = f"({', '.join(doc.authors)}) Tj"
        content_obj = f"({doc.content[:500]}...) Tj"  # Truncate for simplicity

        pdf_template = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(title_obj) + len(authors_obj) + len(content_obj) + 100} >>
stream
BT
/F1 16 Tf
100 750 Td
{title_obj}
/F1 12 Tf
100 720 Td
{authors_obj}
/F1 10 Tf
100 680 Td
{content_obj}
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000251 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
%%EOF"""

        return pdf_template.encode("utf-8")

    def create_test_pdf_batch(self, doc_ids: List[str]) -> List[str]:
        """Create a batch of temporary PDF files."""
        pdf_files = []
        for doc_id in doc_ids:
            pdf_path = self.create_temporary_pdf(doc_id)
            pdf_files.append(pdf_path)
        return pdf_files

    def get_mathematical_test_cases(self) -> Dict[str, str]:
        """Get test cases specifically for mathematical notation."""
        return {
            "basic_greek": "The parameter α determines the convergence rate",
            "complex_formula": r"The integral $\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$",
            "subscripts": "Consider the sequence x₁, x₂, ..., xₙ",
            "superscripts": "The function f(x) = x² + 2x³ - x⁴",
            "mixed_notation": r"For α ∈ ℝ⁺ and β₁, β₂ ∈ ℂ, we have |α|² ≤ β₁β₂*",
            "latex_commands": r"\begin{equation}\sum_{i=1}^{n} x_i = \int_0^1 f(t) dt\end{equation}",
            "unicode_symbols": "The set {x ∈ ℕ : x ≤ n} has cardinality ℵ₀",
        }

    def get_publisher_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get publisher-specific test patterns."""
        return {
            "IEEE": {
                "title_position": (0.15, 0.35),
                "title_font_size": 14.0,
                "title_alignment": "center",
                "author_offset": 0.08,
                "keywords": ["ieee", "transactions", "doi: 10.1109"],
            },
            "ACM": {
                "title_position": (0.12, 0.3),
                "title_font_size": 16.0,
                "title_alignment": "left",
                "author_offset": 0.06,
                "keywords": ["acm", "doi:10.1145"],
            },
            "Springer": {
                "title_position": (0.2, 0.4),
                "title_font_size": 15.0,
                "title_alignment": "left",
                "author_offset": 0.1,
                "keywords": ["springer", "doi:10.1007"],
            },
            "ArXiv": {
                "title_position": (0.25, 0.45),
                "title_font_size": 12.0,
                "title_alignment": "center",
                "author_offset": 0.1,
                "keywords": ["arxiv:", "submitted to"],
            },
        }


class MockPDFLibrary:
    """Mock PDF library for testing without actual PDF dependencies."""

    def __init__(self, fixtures: PDFTestFixtures):
        self.fixtures = fixtures
        self.mock_extractions = {}

    def mock_pymupdf_extraction(self, pdf_path: str) -> Dict[str, Any]:
        """Mock PyMuPDF extraction."""
        # Determine which document this represents
        doc_id = self._get_doc_id_from_path(pdf_path)
        doc = self.fixtures.get_mock_document(doc_id)

        if not doc:
            return {"text": "", "blocks": [], "error": "Document not found"}

        # Simulate text extraction
        text = f"{doc.title}\n{', '.join(doc.authors)}\n{doc.abstract}\n{doc.content}"

        # Simulate text blocks
        blocks = [
            {
                "bbox": (100, 750, 500, 770),
                "text": doc.title,
                "font_size": 16.0,
                "font_flags": 16,  # Bold
            },
            {
                "bbox": (100, 720, 400, 735),
                "text": ", ".join(doc.authors),
                "font_size": 12.0,
                "font_flags": 0,
            },
            {
                "bbox": (100, 680, 500, 720),
                "text": doc.abstract,
                "font_size": 10.0,
                "font_flags": 0,
            },
        ]

        return {
            "text": text,
            "blocks": blocks,
            "page_count": doc.pages,
            "quality_score": 0.9,
            "processing_time": 0.1,
        }

    def mock_pdfplumber_extraction(self, pdf_path: str) -> Dict[str, Any]:
        """Mock pdfplumber extraction."""
        doc_id = self._get_doc_id_from_path(pdf_path)
        doc = self.fixtures.get_mock_document(doc_id)

        if not doc:
            return {"text": "", "error": "Document not found"}

        # Slightly different extraction to simulate library differences
        text = f"Title: {doc.title}\nAuthors: {', '.join(doc.authors)}\n\n{doc.abstract}\n\n{doc.content}"

        return {
            "text": text,
            "page_count": doc.pages,
            "quality_score": 0.85,
            "processing_time": 0.15,
        }

    def _get_doc_id_from_path(self, pdf_path: str) -> str:
        """Extract document ID from file path."""
        # Simple heuristic: use filename without extension
        filename = Path(pdf_path).stem

        # Map common test filenames to document IDs
        filename_mapping = {
            "ieee_paper": "ieee_ml",
            "arxiv_paper": "arxiv_math",
            "springer_paper": "springer_bio",
            "test_paper": "ieee_ml",  # Default
        }

        for pattern, doc_id in filename_mapping.items():
            if pattern in filename.lower():
                return doc_id

        # Default to first document
        return list(self.fixtures.mock_documents.keys())[0]


def create_mock_pdf_processor():
    """Create a mock PDF processor for testing."""
    fixtures = PDFTestFixtures()
    mock_library = MockPDFLibrary(fixtures)

    processor = Mock()
    processor.fixtures = fixtures
    processor.mock_library = mock_library

    # Mock extraction methods
    processor.extract_with_pymupdf = mock_library.mock_pymupdf_extraction
    processor.extract_with_pdfplumber = mock_library.mock_pdfplumber_extraction

    return processor


def create_test_data_archive(output_path: str):
    """Create a ZIP archive with test data for distribution."""
    fixtures = PDFTestFixtures()

    with zipfile.ZipFile(output_path, "w") as zip_file:
        # Add mock documents as JSON
        for doc_id, doc in fixtures.mock_documents.items():
            doc_json = {
                "title": doc.title,
                "authors": doc.authors,
                "abstract": doc.abstract,
                "content": doc.content,
                "publisher": doc.publisher,
                "doi": doc.doi,
                "arxiv_id": doc.arxiv_id,
                "year": doc.year,
                "pages": doc.pages,
                "has_math": doc.has_math,
                "language": doc.language,
            }
            zip_file.writestr(f"documents/{doc_id}.json", json.dumps(doc_json, indent=2))

        # Add test cases
        zip_file.writestr("test_cases.json", json.dumps(fixtures.test_cases, indent=2))

        # Add README
        readme_content = """# PDF Processing Test Data

This archive contains test data for PDF processing systems including:

- Mock PDF documents in various formats and publishers
- Test cases for title/author extraction
- Mathematical notation test cases
- Error condition simulations
- Performance test scenarios

## Usage

Load the test fixtures in your tests:

```python
from fixtures.pdf_test_fixtures import PDFTestFixtures
fixtures = PDFTestFixtures()
doc = fixtures.get_mock_document('ieee_ml')
```
"""
        zip_file.writestr("README.md", readme_content)
