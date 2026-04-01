#!/usr/bin/env python3
"""
Comprehensive Test Suite for Advanced PDF Processing Heuristics

Tests the new advanced layout analyzer, statistical pattern matcher,
and mathematical notation handler with extensive edge cases and
performance benchmarks.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

# Import the modules under test — some classes were renamed or removed
try:
    from pdf_processing.parsers.advanced_layout_analyzer import (
        AdvancedLayoutAnalyzer,
        LayoutAnalysis,
        TextElement,
    )
    from pdf_processing.parsers.math_notation_handler import MathNotationHandler
    from pdf_processing.parsers.statistical_pattern_matcher import (
        StatisticalPatternMatcher,
    )
    # Aliases for renamed/removed classes
    PublisherPatterns = None
    ExtractionPattern = None
    TrainingExample = None
except ImportError as exc:
    pytest.skip(f"PDF processing modules not available: {exc}", allow_module_level=True)


class TestAdvancedLayoutAnalyzer:
    """Test suite for the advanced layout analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance with test config."""
        config = {
            "min_title_font_size": 12.0,
            "max_title_lines": 4,
            "clustering_eps": 0.1,
            "clustering_min_samples": 2
        }
        return AdvancedLayoutAnalyzer(config)
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample text elements for testing."""
        return [
            # Title element
            TextElement(
                text="Advanced Methods in Machine Learning Theory",
                bbox=(100, 700, 500, 720),
                font_name="TimesNewRoman-Bold",
                font_size=16.0,
                font_flags=16,  # Bold
                color=0,
                page_number=1,
                confidence=0.9,
                element_type="title"
            ),
            # Author elements
            TextElement(
                text="John Smith",
                bbox=(150, 660, 300, 675),
                font_name="TimesNewRoman",
                font_size=12.0,
                font_flags=0,
                color=0,
                page_number=1,
                confidence=0.8,
                element_type="author"
            ),
            TextElement(
                text="University of Example",
                bbox=(150, 645, 350, 660),
                font_name="TimesNewRoman",
                font_size=10.0,
                font_flags=0,
                color=0,
                page_number=1,
                confidence=0.7,
                element_type="author"
            ),
            # Abstract
            TextElement(
                text="Abstract",
                bbox=(100, 600, 160, 615),
                font_name="TimesNewRoman-Bold",
                font_size=12.0,
                font_flags=16,
                color=0,
                page_number=1,
                confidence=0.9,
                element_type="abstract"
            ),
            TextElement(
                text="This paper presents novel approaches to machine learning...",
                bbox=(100, 580, 500, 595),
                font_name="TimesNewRoman",
                font_size=10.0,
                font_flags=0,
                color=0,
                page_number=1,
                confidence=0.6,
                element_type="abstract"
            ),
            # Body text
            TextElement(
                text="1. Introduction",
                bbox=(100, 540, 200, 555),
                font_name="TimesNewRoman-Bold",
                font_size=12.0,
                font_flags=16,
                color=0,
                page_number=1,
                confidence=0.5,
                element_type="text"
            ),
        ]
    
    def test_analyze_layout_basic(self, analyzer, sample_elements):
        """Test basic layout analysis."""
        layout = analyzer.analyze_layout(sample_elements)
        
        assert isinstance(layout, LayoutAnalysis)
        assert len(layout.title_candidates) >= 1
        assert len(layout.author_candidates) >= 1
        assert len(layout.abstract_candidates) >= 1
        assert layout.confidence_score > 0.5
    
    def test_column_analysis_single_column(self, analyzer):
        """Test single column detection."""
        elements = [
            TextElement(
                text="Text in single column",
                bbox=(100, 700, 300, 715),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=1
            ),
            TextElement(
                text="More text in same column",
                bbox=(105, 680, 295, 695),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=1
            ),
        ]
        
        column_info = analyzer._analyze_columns(elements)
        assert column_info["count"] == 1
        assert len(column_info["boundaries"]) == 0
    
    def test_column_analysis_two_columns(self, analyzer):
        """Test two column detection."""
        elements = [
            # Left column
            TextElement(
                text="Left column text",
                bbox=(50, 700, 250, 715),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=1
            ),
            TextElement(
                text="More left text",
                bbox=(55, 680, 245, 695),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=1
            ),
            # Right column
            TextElement(
                text="Right column text",
                bbox=(300, 700, 500, 715),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=1
            ),
            TextElement(
                text="More right text",
                bbox=(305, 680, 495, 695),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=1
            ),
        ]
        
        column_info = analyzer._analyze_columns(elements)
        assert column_info["count"] == 2
        assert len(column_info["boundaries"]) == 2
    
    def test_font_analysis(self, analyzer, sample_elements):
        """Test font analysis functionality."""
        font_analysis = analyzer._analyze_fonts(sample_elements)
        
        assert "dominant_size" in font_analysis
        assert "title_size" in font_analysis
        assert font_analysis["dominant_size"] > 0
        assert font_analysis["title_size"] >= font_analysis["dominant_size"]
    
    def test_title_extraction_ieee_pattern(self, analyzer):
        """Test title extraction with IEEE pattern."""
        ieee_elements = [
            TextElement(
                text="IEEE TRANSACTIONS ON PATTERN ANALYSIS",
                bbox=(100, 750, 500, 770),
                font_name="Times-Bold", font_size=14.0, font_flags=16, color=0, page_number=1
            ),
            TextElement(
                text="Deep Learning Approaches for Image Recognition",
                bbox=(120, 720, 480, 740),
                font_name="Times-Bold", font_size=16.0, font_flags=16, color=0, page_number=1
            ),
        ]
        
        layout = analyzer.analyze_layout(ieee_elements)
        assert len(layout.title_candidates) >= 1
        assert "Deep Learning" in layout.title_candidates[0].text
    
    def test_multiline_title_grouping(self, analyzer):
        """Test grouping of multi-line titles."""
        multiline_elements = [
            TextElement(
                text="A Comprehensive Study of Advanced Machine Learning",
                bbox=(100, 720, 500, 735),
                font_name="Times-Bold", font_size=14.0, font_flags=16, color=0, page_number=1
            ),
            TextElement(
                text="Techniques for Natural Language Processing",
                bbox=(100, 705, 480, 720),
                font_name="Times-Bold", font_size=14.0, font_flags=16, color=0, page_number=1
            ),
        ]
        
        font_analysis = {"dominant_size": 12.0, "title_size": 14.0}
        title_candidates = analyzer._extract_title_candidates(
            multiline_elements, font_analysis, None
        )
        
        # Should group into single title
        assert len(title_candidates) == 1
        assert "Comprehensive Study" in title_candidates[0].text
        assert "Natural Language Processing" in title_candidates[0].text
    
    def test_publisher_detection(self):
        """Test publisher pattern detection."""
        # IEEE pattern
        ieee_elements = [
            TextElement(
                text="IEEE Transactions on Software Engineering",
                bbox=(100, 700, 400, 715),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=1
            ),
        ]
        pattern = PublisherPatterns.detect_publisher(ieee_elements)
        assert pattern is not None
        assert pattern.name == "IEEE"
        
        # ArXiv pattern
        arxiv_elements = [
            TextElement(
                text="arXiv:2023.12345v1 [cs.LG] 15 Dec 2023",
                bbox=(100, 700, 400, 715),
                font_name="Times", font_size=10.0, font_flags=0, color=0, page_number=1
            ),
        ]
        pattern = PublisherPatterns.detect_publisher(arxiv_elements)
        assert pattern is not None
        assert pattern.name == "ArXiv"
    
    def test_reference_section_detection(self, analyzer):
        """Test reference section detection."""
        elements_with_refs = [
            TextElement(
                text="Conclusion",
                bbox=(100, 400, 200, 415),
                font_name="Times-Bold", font_size=12.0, font_flags=16, color=0, page_number=2
            ),
            TextElement(
                text="References",
                bbox=(100, 350, 200, 365),
                font_name="Times-Bold", font_size=12.0, font_flags=16, color=0, page_number=2
            ),
            TextElement(
                text="[1] Smith, J. et al. Machine Learning Theory...",
                bbox=(100, 330, 500, 345),
                font_name="Times", font_size=10.0, font_flags=0, color=0, page_number=2
            ),
        ]
        
        ref_start = analyzer._find_reference_section(elements_with_refs)
        assert ref_start is not None
        assert ref_start == 1  # Index of "References" element
    
    def test_empty_input_handling(self, analyzer):
        """Test handling of empty input."""
        layout = analyzer.analyze_layout([])
        assert isinstance(layout, LayoutAnalysis)
        assert len(layout.title_candidates) == 0
        assert len(layout.author_candidates) == 0
        assert layout.confidence_score == 0.0
    
    @pytest.mark.performance
    def test_layout_analysis_performance(self, analyzer):
        """Test performance of layout analysis with large input."""
        # Generate large number of elements
        large_elements = []
        for i in range(1000):
            element = TextElement(
                text=f"Text element {i}",
                bbox=(100 + i % 400, 700 - i * 2, 300 + i % 400, 715 - i * 2),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=i // 50 + 1
            )
            large_elements.append(element)
        
        start_time = time.time()
        layout = analyzer.analyze_layout(large_elements)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 5.0
        assert isinstance(layout, LayoutAnalysis)

class TestStatisticalPatternMatcher:
    """Test suite for the statistical pattern matcher."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def matcher(self, temp_cache_dir):
        """Create pattern matcher with temporary cache."""
        return StatisticalPatternMatcher(temp_cache_dir)
    
    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data."""
        return [
            TrainingExample(
                text="Advanced Machine Learning Techniques",
                bbox=(100, 700, 500, 720),
                font_size=16.0,
                font_name="Times-Bold",
                page_position=0.8,
                is_bold=True,
                is_italic=False,
                label="title",
                publisher="IEEE",
                document_id="doc1",
                success=True
            ),
            TrainingExample(
                text="John Smith, University of Example",
                bbox=(150, 660, 400, 675),
                font_size=12.0,
                font_name="Times",
                page_position=0.75,
                is_bold=False,
                is_italic=False,
                label="author",
                publisher="IEEE",
                document_id="doc1",
                success=True
            ),
            TrainingExample(
                text="Random body text that should not be title",
                bbox=(100, 400, 500, 415),
                font_size=10.0,
                font_name="Times",
                page_position=0.4,
                is_bold=False,
                is_italic=False,
                label="other",
                publisher="IEEE",
                document_id="doc1",
                success=True
            ),
        ]
    
    def test_pattern_database_storage_retrieval(self, matcher, temp_cache_dir):
        """Test pattern database storage and retrieval."""
        # Create a test pattern
        pattern = ExtractionPattern(
            pattern_id="test_pattern_1",
            pattern_type="title",
            publisher="IEEE",
            font_size_range=(14.0, 18.0),
            position_range=(0.7, 0.9),
            text_features={"keyword_score": 0.8},
            success_count=10,
            failure_count=2,
            confidence=0.85,
            last_updated="2024-01-01"
        )
        
        # Store pattern
        matcher.pattern_db.store_pattern(pattern)
        
        # Retrieve pattern
        retrieved_patterns = matcher.pattern_db.get_patterns("title", "IEEE")
        assert len(retrieved_patterns) >= 1
        
        found_pattern = next((p for p in retrieved_patterns if p.pattern_id == "test_pattern_1"), None)
        assert found_pattern is not None
        assert found_pattern.publisher == "IEEE"
        assert found_pattern.confidence == 0.85
    
    def test_training_example_storage(self, matcher, sample_training_data):
        """Test training example storage."""
        for example in sample_training_data:
            matcher.pattern_db.store_training_example(example)
        
        # Retrieve training data
        retrieved_data = matcher.pattern_db.get_training_data()
        assert len(retrieved_data) >= len(sample_training_data)
        
        # Check specific labels
        title_examples = matcher.pattern_db.get_training_data("title")
        author_examples = matcher.pattern_db.get_training_data("author")
        
        assert len(title_examples) >= 1
        assert len(author_examples) >= 1
    
    def test_feature_extraction(self, matcher):
        """Test feature extraction for ML models."""
        features = matcher.extract_features(
            text="Machine Learning Theory",
            font_size=16.0,
            position=0.8,
            is_bold=True,
            is_italic=False
        )
        
        assert isinstance(features, np.ndarray)
        assert len(features) > 10  # Should have multiple features
        assert features[0] == len("Machine Learning Theory")  # Text length
    
    def test_model_training(self, matcher, sample_training_data):
        """Test ML model training."""
        # Add training data
        for example in sample_training_data:
            matcher.pattern_db.store_training_example(example)
        
        # Add more examples to meet minimum threshold
        for i in range(50):
            example = TrainingExample(
                text=f"Sample title {i}",
                bbox=(100, 700, 400, 715),
                font_size=14.0 + i % 4,
                font_name="Times",
                page_position=0.8 - i * 0.01,
                is_bold=i % 2 == 0,
                is_italic=False,
                label="title" if i % 3 == 0 else "other",
                publisher="Generic",
                document_id=f"doc_{i}",
                success=True
            )
            matcher.pattern_db.store_training_example(example)
        
        # Train models
        matcher.train_models(min_samples=20)
        
        # Check that models were created
        assert matcher.title_classifier is not None or matcher.author_classifier is not None
        assert matcher.confidence_regressor is not None
        assert matcher.text_vectorizer is not None
    
    def test_prediction(self, matcher, sample_training_data):
        """Test element type prediction."""
        # Add training data and train
        for example in sample_training_data:
            matcher.pattern_db.store_training_example(example)
        
        # Mock trained models for testing
        matcher.title_classifier = Mock()
        matcher.author_classifier = Mock()
        matcher.confidence_regressor = Mock()
        matcher.text_vectorizer = Mock()
        
        matcher.title_classifier.predict_proba.return_value = [[0.2, 0.8]]
        matcher.author_classifier.predict_proba.return_value = [[0.9, 0.1]]
        matcher.confidence_regressor.predict.return_value = [0.85]
        matcher.text_vectorizer.transform.return_value = np.array([[0.1, 0.2, 0.3]])
        
        element_type, confidence = matcher.predict_element_type(
            text="Advanced Machine Learning",
            font_size=16.0,
            position=0.8,
            is_bold=True,
            is_italic=False
        )
        
        assert element_type in ["title", "author", "other"]
        assert 0.0 <= confidence <= 1.0
    
    def test_pattern_matching(self, matcher):
        """Test pattern matching functionality."""
        # Create and store test patterns
        title_pattern = ExtractionPattern(
            pattern_id="title_pattern",
            pattern_type="title",
            publisher="IEEE",
            font_size_range=(14.0, 18.0),
            position_range=(0.7, 0.9),
            text_features={},
            success_count=5,
            failure_count=1,
            confidence=0.8,
            last_updated=""
        )
        matcher.pattern_db.store_pattern(title_pattern)
        matcher._load_patterns()
        
        # Test matching
        scores = matcher.match_patterns(
            text="Machine Learning Methods",
            font_size=16.0,
            position=0.8,
            is_bold=True,
            is_italic=False,
            publisher="IEEE"
        )
        
        assert "title" in scores
        assert scores["title"] > 0
    
    def test_learning_from_extraction(self, matcher):
        """Test learning from extraction results."""
        matcher.learn_from_extraction(
            text="Successful Title Extraction",
            font_size=16.0,
            position=0.8,
            is_bold=True,
            is_italic=False,
            actual_type="title",
            publisher="IEEE",
            document_id="test_doc",
            success=True
        )
        
        # Check that training example was stored
        examples = matcher.pattern_db.get_training_data("title")
        assert len(examples) >= 1
        assert any(ex.text == "Successful Title Extraction" for ex in examples)
    
    def test_statistics_generation(self, matcher):
        """Test statistics generation."""
        stats = matcher.get_statistics()
        
        assert "total_patterns" in stats
        assert "pattern_types" in stats
        assert "training_examples" in stats
        assert "model_status" in stats
        
        assert isinstance(stats["total_patterns"], int)
        assert isinstance(stats["training_examples"], int)

class TestMathNotationHandler:
    """Test suite for the mathematical notation handler."""
    
    @pytest.fixture
    def handler(self):
        """Create math notation handler."""
        return MathNotationHandler()
    
    def test_latex_symbol_conversion(self, handler):
        """Test LaTeX symbol to Unicode conversion."""
        text = r"The function $f(x) = \alpha x^2 + \beta \sin(\pi x)$"
        normalized = handler.normalize_mathematical_text(text)
        
        assert "α" in normalized  # alpha
        assert "β" in normalized  # beta
        assert "π" in normalized  # pi
        assert "sin" in normalized
    
    def test_unicode_math_normalization(self, handler):
        """Test Unicode mathematical symbol normalization."""
        text = "The inequality x ≤ y ≥ z ≠ w"
        normalized = handler.normalize_mathematical_text(text)
        
        assert "≤" in normalized
        assert "≥" in normalized
        assert "≠" in normalized
    
    def test_subscript_superscript_conversion(self, handler):
        """Test subscript and superscript conversion."""
        text = "H₂O and E = mc²"
        normalized = handler.normalize_mathematical_text(text)
        
        assert "_2" in normalized  # subscript 2
        assert "^2" in normalized  # superscript 2
    
    def test_mathematical_content_detection(self, handler):
        """Test detection of mathematical content."""
        math_text = r"The integral $\int_0^\infty e^{-x} dx = 1$"
        analysis = handler.detect_mathematical_content(math_text)
        
        assert analysis['has_math'] is True
        assert analysis['math_density'] > 0
        assert len(analysis['latex_commands']) > 0
        assert 'int' in str(analysis['latex_commands'])
    
    def test_is_mathematical_title(self, handler):
        """Test mathematical title detection."""
        math_title = "Analysis of α-stable Processes in ℝⁿ"
        non_math_title = "A Study of Social Media Behavior"
        
        assert handler.is_mathematical_title(math_title) is True
        assert handler.is_mathematical_title(non_math_title) is False
    
    def test_clean_title_for_filename(self, handler):
        """Test cleaning mathematical titles for filenames."""
        math_title = "The ∞-norm and L² Spaces: α ≤ β Analysis"
        cleaned = handler.clean_title_for_filename(math_title)
        
        # Check that problematic characters are replaced
        assert "infinity" in cleaned.lower()
        assert "leq" in cleaned.lower()
        assert "alpha" in cleaned.lower()
        assert "beta" in cleaned.lower()
        
        # Check that result is filename-safe
        import string
        allowed_chars = string.ascii_letters + string.digits + " -_."
        assert all(c in allowed_chars for c in cleaned)
    
    def test_mathematical_keyword_extraction(self, handler):
        """Test extraction of mathematical keywords."""
        text = r"We analyze the $\nabla$ operator and ∑ convergence"
        keywords = handler.extract_mathematical_keywords(text)
        
        assert any("symbol:" in kw for kw in keywords)
        assert any("concept:" in kw for kw in keywords)
    
    def test_complex_mathematical_expression(self, handler):
        """Test handling of complex mathematical expressions."""
        complex_text = r"""
        The Schrödinger equation $i\hbar \frac{\partial \psi}{\partial t} = \hat{H}\psi$
        where $\hat{H} = -\frac{\hbar^2}{2m}\nabla^2 + V(x)$ is the Hamiltonian.
        """
        
        normalized = handler.normalize_mathematical_text(complex_text)
        analysis = handler.detect_mathematical_content(complex_text)
        
        assert analysis['has_math'] is True
        assert analysis['math_density'] > 0.1
        assert len(analysis['latex_commands']) > 5
    
    def test_greek_letter_detection(self, handler):
        """Test Greek letter detection and handling."""
        text = "The parameters α, β, γ are estimated using maximum likelihood"
        analysis = handler.detect_mathematical_content(text)
        
        assert len(analysis['greek_letters']) >= 3
        assert 'α' in analysis['greek_letters']
        assert 'β' in analysis['greek_letters']
        assert 'γ' in analysis['greek_letters']
    
    def test_formula_extraction(self, handler):
        """Test formula extraction from text."""
        text = "The quadratic formula $x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$ is well known."
        analysis = handler.detect_mathematical_content(text)
        
        assert len(analysis['formulas']) >= 1
        formula = analysis['formulas'][0]
        assert 'frac' in formula
        assert 'sqrt' in formula
    
    def test_empty_input_handling(self, handler):
        """Test handling of empty or None input."""
        assert handler.normalize_mathematical_text("") == ""
        assert handler.normalize_mathematical_text(None) == None
        
        empty_analysis = handler.detect_mathematical_content("")
        assert empty_analysis['has_math'] is False
        assert empty_analysis['math_density'] == 0.0
    
    @pytest.mark.performance
    def test_performance_large_text(self, handler):
        """Test performance with large mathematical text."""
        # Create large text with mathematical content
        large_text = r"The function $f(x) = \sum_{n=0}^{\infty} \frac{x^n}{n!} = e^x$ " * 1000
        
        start_time = time.time()
        normalized = handler.normalize_mathematical_text(large_text)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 2.0
        assert len(normalized) > 0

class TestIntegratedHeuristics:
    """Integration tests for all heuristic components working together."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def integrated_system(self, temp_cache_dir):
        """Create integrated system with all components."""
        analyzer = AdvancedLayoutAnalyzer()
        matcher = StatisticalPatternMatcher(temp_cache_dir)
        math_handler = MathNotationHandler()
        
        return {
            'analyzer': analyzer,
            'matcher': matcher,
            'math_handler': math_handler
        }
    
    def test_mathematical_paper_processing(self, integrated_system):
        """Test processing of a mathematical paper with all components."""
        # Create sample mathematical paper elements
        elements = [
            TextElement(
                text="On the Convergence of ∑ₙ₌₁^∞ aₙxⁿ Series",
                bbox=(100, 750, 500, 770),
                font_name="Times-Bold", font_size=16.0, font_flags=16, color=0, page_number=1
            ),
            TextElement(
                text="John Mathematician, MIT",
                bbox=(150, 720, 350, 735),
                font_name="Times", font_size=12.0, font_flags=0, color=0, page_number=1
            ),
            TextElement(
                text="Abstract",
                bbox=(100, 680, 160, 695),
                font_name="Times-Bold", font_size=12.0, font_flags=16, color=0, page_number=1
            ),
            TextElement(
                text="We study the convergence properties of power series ∑aₙxⁿ...",
                bbox=(100, 660, 500, 675),
                font_name="Times", font_size=10.0, font_flags=0, color=0, page_number=1
            ),
        ]
        
        # Test layout analysis
        layout = integrated_system['analyzer'].analyze_layout(elements)
        assert len(layout.title_candidates) >= 1
        
        # Test mathematical content detection
        title_text = layout.title_candidates[0].text
        math_analysis = integrated_system['math_handler'].detect_mathematical_content(title_text)
        assert math_analysis['has_math'] is True
        
        # Test normalization
        normalized_title = integrated_system['math_handler'].normalize_mathematical_text(title_text)
        assert len(normalized_title) > 0
    
    def test_multilingual_paper_processing(self, integrated_system):
        """Test processing of papers with multilingual mathematical content.""" 
        elements = [
            TextElement(
                text="Analyse des fonctions α-hölderiennes",
                bbox=(100, 750, 400, 770),
                font_name="Times-Bold", font_size=16.0, font_flags=16, color=0, page_number=1
            ),
        ]
        
        layout = integrated_system['analyzer'].analyze_layout(elements)
        title_text = layout.title_candidates[0].text if layout.title_candidates else ""
        
        # Should handle international characters and mathematical symbols
        math_analysis = integrated_system['math_handler'].detect_mathematical_content(title_text)
        normalized = integrated_system['math_handler'].normalize_mathematical_text(title_text)
        
        assert "α" in title_text or "alpha" in normalized.lower()
    
    @pytest.mark.performance
    def test_full_pipeline_performance(self, integrated_system):
        """Test performance of full integrated pipeline."""
        # Create realistic document with many elements
        elements = []
        for i in range(200):
            element = TextElement(
                text=f"Mathematical content with α_{i} and β^{i}",
                bbox=(100 + i % 400, 750 - i * 3, 300 + i % 400, 765 - i * 3),
                font_name="Times", font_size=10.0 + i % 6, font_flags=i % 2 * 16, 
                color=0, page_number=i // 50 + 1
            )
            elements.append(element)
        
        start_time = time.time()
        
        # Run full pipeline
        layout = integrated_system['analyzer'].analyze_layout(elements)
        
        for candidate in layout.title_candidates:
            math_analysis = integrated_system['math_handler'].detect_mathematical_content(candidate.text)
            normalized = integrated_system['math_handler'].normalize_mathematical_text(candidate.text)
        
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 10.0
        assert len(layout.title_candidates) > 0