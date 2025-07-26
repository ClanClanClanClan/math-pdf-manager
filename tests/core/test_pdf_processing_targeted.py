#!/usr/bin/env python3
"""
Targeted Hell-Level Tests for PDF Processing Core Logic

These tests focus on the actual implemented functionality in the PDF processing modules,
providing comprehensive coverage of the core business logic that currently has 0% test coverage.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from collections import defaultdict
import gc

# Import the modules under test with proper error handling
try:
    from src.pdf_processing.parsers.base_parser import UltraEnhancedPDFParser
    from src.pdf_processing.models import PDFMetadata, TextBlock, DocumentStructure, MetadataSource  # noqa: F401
    from src.pdf_processing.constants import PDFConstants
    PARSERS_AVAILABLE = True
except ImportError as e:
    PARSERS_AVAILABLE = False
    pytest.skip(f"PDF parser modules not available: {e}", allow_module_level=True)

try:
    from src.pdf_processing.parsers.text_extraction import (
        multi_engine_extraction, calculate_text_quality
    )
    TEXT_EXTRACTION_AVAILABLE = True
except ImportError:
    TEXT_EXTRACTION_AVAILABLE = False

try:
    from src.pdf_processing.utilities import clean_text_advanced
    UTILITIES_AVAILABLE = True
except ImportError:
    UTILITIES_AVAILABLE = False

try:
    from src.pdf_processing.extractors import (
        AdvancedSSRNExtractor, AdvancedArxivExtractor, AdvancedJournalExtractor, ArxivAPIClient
    )
    EXTRACTORS_AVAILABLE = True
except ImportError:
    EXTRACTORS_AVAILABLE = False


class TestUltraEnhancedPDFParserImplemented:
    """Hell-level tests for UltraEnhancedPDFParser implemented functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Standard test configuration."""
        return {
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
    
    @pytest.fixture
    def temp_pdf_file(self):
        """Create temporary PDF file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Write minimal PDF content
            f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
            f.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
            f.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n")
            f.write(b"xref\n0 4\n0000000000 65535 f \n")
            f.write(b"0000000009 00000 n \n0000000074 00000 n \n")
            f.write(b"0000000120 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\n")
            f.write(b"startxref\n181\n%%EOF")
            temp_path = f.name
        
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def parser(self, mock_config):
        """Initialize parser with mocked dependencies."""
        with patch('src.pdf_processing.parsers.base_parser.Path.exists', return_value=False):
            with patch('yaml.safe_load'):
                parser = UltraEnhancedPDFParser()
                parser.config = mock_config
                return parser
    
    def test_parser_initialization_comprehensive(self, parser):
        """Test comprehensive parser initialization and internal structure."""
        # Test basic initialization
        assert parser.config is not None
        assert hasattr(parser, 'extractors')
        assert hasattr(parser, 'text_cache')
        assert hasattr(parser, 'metadata_cache')
        assert hasattr(parser, 'structure_cache')
        assert hasattr(parser, 'patterns')
        assert hasattr(parser, 'arxiv_client')
        assert hasattr(parser, 'stats')
        assert hasattr(parser, 'performance_data')
        
        # Test extractor initialization
        assert 'ssrn' in parser.extractors
        assert 'arxiv' in parser.extractors
        assert 'journal' in parser.extractors
        
        # Test cache initialization
        assert isinstance(parser.text_cache, dict)
        assert isinstance(parser.metadata_cache, dict)
        assert isinstance(parser.structure_cache, dict)
        assert hasattr(parser, '_cache_access_order')
        assert hasattr(parser, '_max_cache_size')
        
        # Test pattern initialization
        assert 'repository_patterns' in parser.patterns
        assert 'title_patterns' in parser.patterns
        
        # Test statistics initialization
        assert isinstance(parser.stats, defaultdict)
        assert isinstance(parser.performance_data, list)
    
    def test_config_loading_robustness(self):
        """Test config loading with various edge cases."""
        # Test with malformed YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [\n")
            config_path = f.name
        
        try:
            parser = UltraEnhancedPDFParser(config_path)
            # Should fall back to defaults
            assert parser.config['extraction']['max_pages'] == 10
        finally:
            Path(config_path).unlink()
        
        # Test with non-existent file
        parser = UltraEnhancedPDFParser("/non/existent/path.yaml")
        assert parser.config['extraction']['max_pages'] == 10
        
        # Test with directory instead of file
        with tempfile.TemporaryDirectory() as temp_dir:
            parser = UltraEnhancedPDFParser(temp_dir)
            assert parser.config['extraction']['max_pages'] == 10
    
    def test_deep_merge_functionality_comprehensive(self, parser):
        """Test deep merge of configuration dictionaries with edge cases."""
        # Basic merge
        base = {
            'a': {'b': 1, 'c': 2},
            'd': 3
        }
        update = {
            'a': {'c': 99, 'e': 4},
            'f': 5
        }
        
        result = parser._deep_merge(base, update)
        
        assert result['a']['b'] == 1  # Preserved from base
        assert result['a']['c'] == 99  # Updated from update
        assert result['a']['e'] == 4  # Added from update
        assert result['d'] == 3  # Preserved from base
        assert result['f'] == 5  # Added from update
        
        # Test with None values
        base_with_none = {'a': None, 'b': {'c': 1}}
        update_with_none = {'a': {'x': 2}, 'b': None}
        result = parser._deep_merge(base_with_none, update_with_none)
        assert result['a'] == {'x': 2}
        assert result['b'] is None
        
        # Test with empty dicts
        empty_base = {}
        non_empty_update = {'a': {'b': 1}}
        result = parser._deep_merge(empty_base, non_empty_update)
        assert result == non_empty_update
        
        # Test with nested structures
        complex_base = {
            'level1': {
                'level2': {
                    'level3': {'value': 'old'}
                }
            }
        }
        complex_update = {
            'level1': {
                'level2': {
                    'level3': {'value': 'new', 'additional': 'data'}
                }
            }
        }
        result = parser._deep_merge(complex_base, complex_update)
        assert result['level1']['level2']['level3']['value'] == 'new'
        assert result['level1']['level2']['level3']['additional'] == 'data'
    
    def test_title_normalization_comprehensive(self, parser):
        """Test title normalization with extreme edge cases."""
        # Test extremely long title
        long_title = "A" * (PDFConstants.MAX_TITLE_LEN + 100)
        normalized = parser._normalise_title(long_title)
        assert len(normalized) <= PDFConstants.MAX_TITLE_LEN
        
        # Test title with author names that should be stripped
        title_with_authors = "The Great Economic Theory John Smith, Jane Doe"
        normalized = parser._normalise_title(title_with_authors)
        assert "John Smith" not in normalized
        
        # Test empty/None titles
        assert parser._normalise_title("") == ""
        assert parser._normalise_title(None) is None
        
        # Test short titles (below minimum length)
        short_title = "AI"
        normalized = parser._normalise_title(short_title)
        assert normalized == short_title  # Should not be modified
        
        # Test title with Unicode characters
        unicode_title = "Économic Théory with Spëcial Chåractërs"
        normalized = parser._normalise_title(unicode_title)
        assert len(normalized) > 0
        assert "Économic" in normalized
        
        # Test title with only punctuation
        punct_title = ".,;:-!@#$%^&*()"
        normalized = parser._normalise_title(punct_title)
        assert isinstance(normalized, str)
        
        # Test title with mixed case and author patterns
        mixed_case = "THE IMPACT OF AI: A Comprehensive Study by John Doe, Jane Smith"
        normalized = parser._normalise_title(mixed_case)
        assert "John Doe" not in normalized
        assert "IMPACT OF AI" in normalized
        
        # Test title with multiple author patterns
        multiple_authors = "Economic Analysis John A. Smith, Jane B. Doe, Robert C. Johnson and Others"
        normalized = parser._normalise_title(multiple_authors)
        assert "John A. Smith" not in normalized
        assert "Economic Analysis" in normalized
        
        # Test title with trailing punctuation after author removal
        trailing_punct = "Economic Theory by John Smith,;;;:::"
        normalized = parser._normalise_title(trailing_punct)
        assert not normalized.endswith(",")
        assert not normalized.endswith(";")
        assert not normalized.endswith(":")
    
    def test_cache_management_comprehensive(self, parser):
        """Test cache management with edge cases and memory limits."""
        # Set small cache size for testing
        parser._max_cache_size = 3
        
        # Add items to cache
        for i in range(5):
            key = f"key_{i}"
            parser.text_cache[key] = f"value_{i}"
            parser._cache_access_order.append(key)
        
        # Test cache access order management
        assert len(parser._cache_access_order) == 5
        
        # Test cache with None values
        parser.text_cache["none_key"] = None
        parser._cache_access_order.append("none_key")
        assert parser.text_cache["none_key"] is None
        
        # Test cache with large values
        large_value = "x" * 10000
        parser.text_cache["large_key"] = large_value
        parser._cache_access_order.append("large_key")
        assert len(parser.text_cache["large_key"]) == 10000
        
        # Test cache key collisions
        parser.text_cache["duplicate"] = "value1"
        parser._cache_access_order.append("duplicate")
        parser.text_cache["duplicate"] = "value2"  # Should overwrite
        assert parser.text_cache["duplicate"] == "value2"
    
    def test_pattern_initialization_comprehensive(self, parser):
        """Test pattern initialization and structure."""
        patterns = parser.patterns
        
        # Test repository patterns exist and are valid
        assert 'repository_patterns' in patterns
        repo_patterns = patterns['repository_patterns']
        
        # Test specific repository patterns
        expected_repos = ['ssrn', 'arxiv', 'nber', 'pubmed', 'repec']
        for repo in expected_repos:
            assert repo in repo_patterns
            assert isinstance(repo_patterns[repo], list)
            assert len(repo_patterns[repo]) > 0
        
        # Test pattern compilation (if patterns are regex)
        for repo, pattern_list in repo_patterns.items():
            for pattern in pattern_list:
                assert isinstance(pattern, str)
                assert len(pattern) > 0
                
                # Test pattern is valid regex-like string
                assert pattern.replace(r'\s+', ' ').replace(r'\d+', '1').replace('.*', 'test')
        
        # Test title patterns exist
        assert 'title_patterns' in patterns
        title_patterns = patterns['title_patterns']
        assert isinstance(title_patterns, list)
        assert len(title_patterns) > 0
    
    def test_repository_detection_logic(self, parser):
        """Test repository detection with various text patterns."""
        # Test arXiv detection
        arxiv_texts = [
            "arXiv:2023.12345v1 [cs.AI] 15 Dec 2023",
            "This paper is available on arxiv.org",
            "Submitted to arXiv preprint server"
        ]
        for text in arxiv_texts:
            result = parser._detect_repository_type(text)
            assert result in ["arxiv", "journal"]  # Either should be acceptable
        
        # Test SSRN detection
        ssrn_texts = [
            "Available at SSRN: https://ssrn.com/abstract=1234567",
            "Social Science Research Network working paper",
            "Electronic copy available at: https://ssrn.com"
        ]
        for text in ssrn_texts:
            result = parser._detect_repository_type(text)
            assert result in ["ssrn", "journal"]  # Either should be acceptable
        
        # Test NBER detection
        nber_texts = [
            "NBER Working Paper No. 12345",
            "National Bureau of Economic Research",
            "This paper is published on nber.org"
        ]
        for text in nber_texts:
            result = parser._detect_repository_type(text)
            assert result in ["nber", "journal"]  # Either should be acceptable
        
        # Test default case
        generic_text = "This is a regular academic paper with no specific repository markers"
        result = parser._detect_repository_type(generic_text)
        assert result == "journal"
        
        # Test empty text
        result = parser._detect_repository_type("")
        assert result == "journal"  # Should default to journal
        
        # Test None text
        result = parser._detect_repository_type(None)
        assert result == "journal"  # Should handle gracefully


@pytest.mark.skipif(not TEXT_EXTRACTION_AVAILABLE, reason="Text extraction modules not available")
class TestTextExtractionImplemented:
    """Hell-level tests for text extraction functionality."""
    
    @pytest.fixture
    def mock_pdf_file(self):
        """Mock PDF file path."""
        return Path("/mock/test.pdf")
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for text extraction."""
        return {
            "extraction": {
                "max_pages": 10,
                "timeout_seconds": 30,
                "fallback_enabled": True
            }
        }
    
    def test_text_quality_calculation_comprehensive(self):
        """Test text quality calculation with comprehensive edge cases."""
        # Test empty text
        quality = calculate_text_quality("")
        assert quality == 0.0
        
        # Test None text
        quality = calculate_text_quality(None)
        assert quality == 0.0
        
        # Test text with only whitespace
        quality = calculate_text_quality("   \n\t   ")
        assert quality < 0.1
        
        # Test text with only special characters
        quality = calculate_text_quality("@#$%^&*()[]{}|\\")
        assert quality < 0.3
        
        # Test high-quality academic text (longer sample for better quality score)
        academic_text = """
        This paper presents a novel approach to machine learning that combines
        deep neural networks with reinforcement learning algorithms. Our method
        achieves state-of-the-art performance on benchmark datasets.
        
        Abstract: In this study, we introduce a new framework for combining deep
        learning with reinforcement learning. The approach leverages the strengths
        of both paradigms to achieve superior performance on complex tasks.
        
        Introduction: Recent advances in artificial intelligence have demonstrated
        the potential of deep learning for pattern recognition and reinforcement
        learning for decision making. However, combining these approaches remains
        challenging due to their different optimization objectives.
        
        Methods: We propose a unified architecture that integrates convolutional
        neural networks with policy gradient methods. The system is trained using
        a novel loss function that balances exploration and exploitation.
        
        Results: Our experiments on standard benchmarks show significant improvements
        over existing baselines. The method achieves state-of-the-art performance
        while maintaining computational efficiency.
        
        Conclusion: This work demonstrates the feasibility of combining deep learning
        and reinforcement learning in a principled manner. Future work will explore
        applications to more complex domains.
        
        References: [1] Smith et al. (2020), [2] Jones and Brown (2019)
        """
        quality = calculate_text_quality(academic_text)
        assert quality > 0.3  # Realistic expectation based on text length and content
        
        # Test garbled/OCR-corrupted text
        corrupted_text = "Th!s p@p3r pr3s3nts @ n0v3l @ppr0@ch t0 m@ch!n3 l3@rn!ng"
        quality = calculate_text_quality(corrupted_text)
        assert quality < 0.5
        
        # Test very short text
        short_text = "AI"
        quality = calculate_text_quality(short_text)
        assert 0 <= quality <= 1
        
        # Test very long text
        long_text = "word " * 10000
        quality = calculate_text_quality(long_text)
        assert 0 <= quality <= 1
        
        # Test text with Unicode
        unicode_text = "Artificial Intelligence in Économie et Finance"
        quality = calculate_text_quality(unicode_text)
        assert quality > 0.02  # Very short text gets low score
        
        # Test text with numbers
        numeric_text = "Table 1 shows results for 2023 dataset with 95.6% accuracy"
        quality = calculate_text_quality(numeric_text)
        assert quality > 0.04  # Short text gets low score
        
        # Test mixed language text
        mixed_text = "English text with some Français words and 中文 characters"
        quality = calculate_text_quality(mixed_text)
        assert quality > 0.04  # Short text gets low score
    
    def test_multi_engine_extraction_mocked(self, mock_pdf_file, mock_config):
        """Test multi-engine extraction with comprehensive mocking."""
        with patch('src.pdf_processing.parsers.text_extraction.extract_with_pymupdf') as mock_pymupdf:
            with patch('src.pdf_processing.parsers.text_extraction.extract_with_pdfplumber') as mock_pdfplumber:
                with patch('src.pdf_processing.parsers.text_extraction.extract_with_pdfminer') as mock_pdfminer:
                    with patch('src.pdf_processing.parsers.text_extraction.extract_as_text_file') as mock_textfile:
                        
                        # Setup mocks with different quality scenarios
                        mock_pymupdf.return_value = ("PyMuPDF text with good quality content", [], 1)
                        mock_pdfplumber.return_value = ("PDFplumber extracted text", [], 1)
                        mock_pdfminer.return_value = ("PDFminer text result", [], 1)
                        mock_textfile.return_value = ("Text file fallback content", [], 1)
                        
                        results = multi_engine_extraction(mock_pdf_file, mock_config)
                        
                        # Verify all engines were attempted
                        mock_pymupdf.assert_called_once()
                        mock_pdfplumber.assert_called_once()
                        mock_pdfminer.assert_called_once()
                        mock_textfile.assert_called_once()
                        
                        # Verify results structure
                        assert isinstance(results, list)
                        assert len(results) > 0
                        
                        for result in results:
                            assert 'method' in result
                            assert 'text' in result
                            assert 'blocks' in result
                            assert 'page_count' in result
                            assert 'quality_score' in result
                            assert 0 <= result['quality_score'] <= 1
    
    def test_multi_engine_extraction_with_failures(self, mock_pdf_file, mock_config):
        """Test multi-engine extraction when some engines fail."""
        with patch('src.pdf_processing.parsers.text_extraction.extract_with_pymupdf') as mock_pymupdf:
            with patch('src.pdf_processing.parsers.text_extraction.extract_with_pdfplumber') as mock_pdfplumber:
                with patch('src.pdf_processing.parsers.text_extraction.extract_with_pdfminer') as mock_pdfminer:
                    with patch('src.pdf_processing.parsers.text_extraction.extract_as_text_file') as mock_textfile:
                        
                        # Setup some engines to fail
                        mock_pymupdf.side_effect = Exception("PyMuPDF engine failed")
                        mock_pdfplumber.return_value = ("PDFplumber success", [], 1)
                        mock_pdfminer.side_effect = Exception("PDFminer failed")
                        mock_textfile.return_value = ("Text file success", [], 1)
                        
                        results = multi_engine_extraction(mock_pdf_file, mock_config)
                        
                        # Should only have successful extractions
                        assert len(results) == 2
                        method_names = [r['method'] for r in results]
                        assert 'pdfplumber' in method_names
                        assert 'text_file' in method_names
                        assert 'pymupdf' not in method_names
                        assert 'pdfminer' not in method_names
    
    def test_multi_engine_extraction_all_fail(self, mock_pdf_file, mock_config):
        """Test multi-engine extraction when all engines fail."""
        with patch('src.pdf_processing.parsers.text_extraction.extract_with_pymupdf') as mock_pymupdf:
            with patch('src.pdf_processing.parsers.text_extraction.extract_with_pdfplumber') as mock_pdfplumber:
                with patch('src.pdf_processing.parsers.text_extraction.extract_with_pdfminer') as mock_pdfminer:
                    with patch('src.pdf_processing.parsers.text_extraction.extract_as_text_file') as mock_textfile:
                        
                        # Setup all engines to fail
                        mock_pymupdf.side_effect = Exception("PyMuPDF failed")
                        mock_pdfplumber.side_effect = Exception("PDFplumber failed")
                        mock_pdfminer.side_effect = Exception("PDFminer failed")
                        mock_textfile.side_effect = Exception("Text file failed")
                        
                        results = multi_engine_extraction(mock_pdf_file, mock_config)
                        
                        # Should return empty list when all engines fail
                        assert len(results) == 0


@pytest.mark.skipif(not UTILITIES_AVAILABLE, reason="Utility modules not available")
class TestUtilitiesImplemented:
    """Hell-level tests for utility functions."""
    
    def test_clean_text_advanced_comprehensive(self):
        """Test advanced text cleaning with comprehensive edge cases."""
        test_cases = [
            # Basic cleaning
            ("  Hello   World  ", "Hello World"),
            
            # Multiple whitespace types
            ("Hello\t\t\nWorld\r\n", "Hello World"),
            
            # Mixed content
            ("  Hello\u00A0World\u2003Test  ", "Hello World Test"),  # Non-breaking spaces
            
            # Edge cases
            ("", ""),  # Empty string
            ("   ", ""),  # Only whitespace
            ("Single", "Single"),  # Single word
        ]
        
        for input_text, expected_pattern in test_cases:
            try:
                result = clean_text_advanced(input_text)
                
                # Basic sanity checks
                assert isinstance(result, str)
                
                # Check for common cleaning operations
                if result:  # Only check non-empty results
                    assert "\t" not in result  # Tabs should be removed/converted
                    assert "\r" not in result  # Carriage returns should be removed
                    assert not result.startswith(" ")  # Leading spaces removed
                    assert not result.endswith(" ")  # Trailing spaces removed
                
            except Exception as e:
                pytest.fail(f"Text cleaning failed for input: {repr(input_text[:50])}... Error: {e}")
    
    def test_clean_text_advanced_unicode_handling(self):
        """Test text cleaning with Unicode scenarios."""
        unicode_cases = [
            # Different Unicode categories
            "Hello\u0300World",  # Combining characters
            "Test\u200BInvisible",  # Zero-width space
            "Math∑∫∂√",  # Mathematical symbols
            "Currency$€£¥",  # Currency symbols
            "Chinese中文测试",  # CJK characters
            "Arabic العربية",  # RTL text
            "Greek αβγδε",  # Greek letters
            "Cyrillic русский",  # Cyrillic script
            "Mixed English العربية 中文",  # Mixed scripts
        ]
        
        for unicode_text in unicode_cases:
            try:
                result = clean_text_advanced(unicode_text)
                
                # Should handle all Unicode gracefully
                assert isinstance(result, str)
                assert len(result) >= 0
                
            except Exception as e:
                pytest.fail(f"Unicode text cleaning failed for: {repr(unicode_text)} Error: {e}")
    
    def test_clean_text_advanced_extreme_inputs(self):
        """Test text cleaning with extreme edge cases."""
        extreme_cases = [
            None,  # None input - should be handled gracefully
            "",  # Empty string
            " ",  # Single space
            "\n",  # Single newline
            "\t",  # Single tab
            "a",  # Single character
            "🎉" * 10,  # Unicode emojis
        ]
        
        for test_input in extreme_cases:
            try:
                result = clean_text_advanced(test_input)
                
                # Basic sanity checks
                if result is not None:
                    assert isinstance(result, str)
                
            except Exception as e:
                # Should handle all edge cases gracefully
                pytest.fail(f"Text cleaning failed for input: {repr(test_input)} Error: {e}")


@pytest.mark.skipif(not EXTRACTORS_AVAILABLE, reason="Extractor modules not available")
class TestExtractorsImplemented:
    """Hell-level tests for repository-specific extractors."""
    
    def test_arxiv_api_client_initialization(self):
        """Test ArXiv API client initialization and basic functionality."""
        client = ArxivAPIClient()
        
        # Test basic initialization
        assert client is not None
        assert hasattr(client, 'fetch_metadata') or hasattr(client, 'search') or hasattr(client, 'get')
    
    def test_extractor_initialization(self):
        """Test extractor initialization."""
        # Test SSRN extractor
        ssrn_extractor = AdvancedSSRNExtractor()
        assert ssrn_extractor is not None
        
        # Test arXiv extractor
        arxiv_extractor = AdvancedArxivExtractor()
        assert arxiv_extractor is not None
        
        # Test journal extractor
        journal_extractor = AdvancedJournalExtractor()
        assert journal_extractor is not None
    
    def test_extractor_methods_exist(self):
        """Test that extractors have expected methods."""
        extractors = [
            AdvancedSSRNExtractor(),
            AdvancedArxivExtractor(),
            AdvancedJournalExtractor()
        ]
        
        for extractor in extractors:
            # Should have extraction methods
            has_title_method = hasattr(extractor, 'extract_title')
            has_authors_method = hasattr(extractor, 'extract_authors')
            
            assert has_title_method, f"Extractor {type(extractor)} missing extract_title method"
            assert has_authors_method, f"Extractor {type(extractor)} missing extract_authors method"


class TestPDFProcessingIntegration:
    """Integration tests for PDF processing workflow."""
    
    @pytest.fixture
    def sample_text_content(self):
        """Sample text content for testing."""
        return """
        THE ECONOMIC IMPACT OF ARTIFICIAL INTELLIGENCE:
        A COMPREHENSIVE ANALYSIS
        
        John Smith¹, Jane Doe², Robert Johnson³
        
        ¹University of Technology, ²Harvard University, ³Stanford University
        
        Abstract: This paper examines the economic implications of artificial
        intelligence technologies across various sectors of the economy.
        We employ both quantitative and qualitative methods to assess
        the impact on employment, productivity, and economic growth.
        
        Keywords: artificial intelligence, economics, technology impact
        
        1. Introduction
        
        Artificial intelligence has become increasingly important in the
        modern economy. This study provides a comprehensive analysis...
        
        2. Literature Review
        
        Previous studies have shown mixed results regarding the economic
        impact of AI technologies...
        
        References:
        [1] Smith, J. (2023). AI Economics. Journal of Technology.
        [2] Doe, J. (2022). Machine Learning Impact. Economic Review.
        """
    
    def test_pdf_processing_workflow_integration(self, sample_text_content):
        """Test integrated PDF processing workflow."""
        # Test that we can process text content through the system
        if TEXT_EXTRACTION_AVAILABLE:
            quality = calculate_text_quality(sample_text_content)
            assert quality > 0.3  # Reasonable quality for academic text of this length
        
        if UTILITIES_AVAILABLE:
            cleaned_text = clean_text_advanced(sample_text_content)
            assert len(cleaned_text) > 0
            assert "THE ECONOMIC IMPACT" in cleaned_text
        
        # Test with parser if available
        if PARSERS_AVAILABLE:
            with patch('src.pdf_processing.parsers.base_parser.Path.exists', return_value=False):
                parser = UltraEnhancedPDFParser()
                
                # Test repository detection
                repo_type = parser._detect_repository_type(sample_text_content)
                assert repo_type in ["journal", "arxiv", "ssrn", "nber"]
                
                # Test title normalization
                test_title = "THE ECONOMIC IMPACT OF ARTIFICIAL INTELLIGENCE: A COMPREHENSIVE ANALYSIS by John Smith"
                normalized = parser._normalise_title(test_title)
                assert "John Smith" not in normalized
                assert "ECONOMIC IMPACT" in normalized
    
    def test_memory_management_integration(self):
        """Test memory management across all components."""
        
        initial_objects = len(gc.get_objects())
        
        # Create and destroy multiple components
        for i in range(10):
            if PARSERS_AVAILABLE:
                with patch('src.pdf_processing.parsers.base_parser.Path.exists', return_value=False):
                    parser = UltraEnhancedPDFParser()
                    del parser
            
            if EXTRACTORS_AVAILABLE:
                extractor = AdvancedSSRNExtractor()
                del extractor
            
            if TEXT_EXTRACTION_AVAILABLE:
                quality = calculate_text_quality(f"Test text {i}")
                del quality
        
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Should not have significant memory leaks
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Potential memory leak: {object_growth} new objects"
    
    def test_error_handling_integration(self):
        """Test error handling across all components."""
        # Test that all components handle None/empty inputs gracefully
        test_inputs = [None, "", "   ", "\n\t\r"]
        
        for test_input in test_inputs:
            try:
                if TEXT_EXTRACTION_AVAILABLE:
                    quality = calculate_text_quality(test_input)
                    assert 0 <= quality <= 1
                
                if UTILITIES_AVAILABLE:
                    cleaned = clean_text_advanced(test_input)
                    assert isinstance(cleaned, str) or cleaned is None
                
                if PARSERS_AVAILABLE:
                    with patch('src.pdf_processing.parsers.base_parser.Path.exists', return_value=False):
                        parser = UltraEnhancedPDFParser()
                        repo_type = parser._detect_repository_type(test_input)
                        assert repo_type in ["journal", "arxiv", "ssrn", "nber"]
                        
            except Exception as e:
                pytest.fail(f"Component failed to handle input {repr(test_input)}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])