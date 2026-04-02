"""Tests for advanced layout analysis, pattern matching, and math notation.

Tests the current API of:
- AdvancedLayoutAnalyzer (title/author detection from TextElements)
- StatisticalPatternMatcher (learning + scoring)
- MathNotationHandler (LaTeX→Unicode, author name correction)
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from pdf_processing.parsers.advanced_layout_analyzer import (
    AdvancedLayoutAnalyzer,
    LayoutAnalysis,
    TextElement,
)
from pdf_processing.parsers.math_notation_handler import MathNotationHandler
from pdf_processing.parsers.statistical_pattern_matcher import (
    ElementPattern,
    FeatureStats,
    StatisticalPatternMatcher,
)


# ============================================================================
# TextElement
# ============================================================================

class TestTextElement:

    def test_basic_creation(self):
        elem = TextElement(text="Hello", bbox=(10, 20, 100, 40), font_size=14.0)
        assert elem.text == "Hello"
        assert elem.font_size == 14.0

    def test_properties(self):
        elem = TextElement(text="T", bbox=(10, 20, 100, 40))
        assert elem.x == 10
        assert elem.y == 20
        assert elem.width == 90
        assert elem.height == 20

    def test_is_bold(self):
        bold = TextElement(text="B", font_flags=16)
        not_bold = TextElement(text="N", font_flags=0)
        assert bold.is_bold
        assert not not_bold.is_bold

    def test_is_italic(self):
        italic = TextElement(text="I", font_flags=2)
        not_italic = TextElement(text="N", font_flags=0)
        assert italic.is_italic
        assert not not_italic.is_italic

    def test_bold_and_italic(self):
        both = TextElement(text="BI", font_flags=18)  # 16 + 2
        assert both.is_bold
        assert both.is_italic

    def test_defaults(self):
        elem = TextElement(text="D")
        assert elem.bbox == (0, 0, 0, 0)
        assert elem.font_name == ""
        assert elem.font_size == 12.0
        assert elem.page_number == 0


# ============================================================================
# LayoutAnalysis
# ============================================================================

class TestLayoutAnalysis:

    def test_defaults(self):
        analysis = LayoutAnalysis()
        assert analysis.title_candidates == []
        assert analysis.author_candidates == []
        assert analysis.abstract_start_y is None
        assert analysis.confidence_score == 0.0
        assert analysis.publisher_template is None

    def test_with_candidates(self):
        title = TextElement(text="On BSDEs", font_size=18.0, bbox=(50, 50, 500, 70))
        author = TextElement(text="N. Touzi", font_size=12.0, bbox=(50, 80, 200, 95))
        analysis = LayoutAnalysis(
            title_candidates=[title],
            author_candidates=[author],
            body_font_size=10.0,
            title_font_size=18.0,
            confidence_score=0.85,
        )
        assert len(analysis.title_candidates) == 1
        assert analysis.title_candidates[0].text == "On BSDEs"
        assert analysis.confidence_score == 0.85


# ============================================================================
# AdvancedLayoutAnalyzer
# ============================================================================

class TestAdvancedLayoutAnalyzer:

    @pytest.fixture
    def analyzer(self):
        return AdvancedLayoutAnalyzer()

    def _make_page(self, lines):
        """Build TextElements from (text, font_size, y, bold) tuples."""
        elements = []
        for text, size, y, bold in lines:
            flags = 16 if bold else 0
            elements.append(TextElement(
                text=text, font_size=size, font_flags=flags,
                bbox=(50, y, 500, y + size + 2), page_number=0,
            ))
        return elements

    def test_simple_paper_layout(self, analyzer):
        elements = self._make_page([
            ("On the convergence of stochastic gradient descent", 16.0, 50, True),
            ("Jean Dupont and Marie Martin", 11.0, 80, False),
            ("Abstract", 12.0, 120, True),
            ("We study the convergence properties...", 10.0, 140, False),
        ])
        result = analyzer.analyze_layout(elements)
        assert isinstance(result, LayoutAnalysis)
        assert len(result.title_candidates) >= 1
        assert result.title_candidates[0].text == "On the convergence of stochastic gradient descent"

    def test_empty_input(self, analyzer):
        result = analyzer.analyze_layout([])
        assert isinstance(result, LayoutAnalysis)
        assert result.title_candidates == []

    def test_single_element(self, analyzer):
        elements = [TextElement(text="Only line", font_size=14.0, bbox=(50, 50, 400, 70))]
        result = analyzer.analyze_layout(elements)
        assert isinstance(result, LayoutAnalysis)

    def test_publisher_detection_arxiv(self, analyzer):
        elements = self._make_page([
            ("arXiv:2401.07160v3", 8.0, 10, False),
            ("Some Title", 16.0, 50, True),
            ("Author Name", 11.0, 80, False),
        ])
        result = analyzer.analyze_layout(elements)
        assert result.publisher_template == "arxiv"

    def test_header_excluded_from_title(self, analyzer):
        elements = self._make_page([
            ("Vol. 45, No. 3, pp. 1234–1256", 8.0, 10, False),
            ("Journal of Mathematics", 9.0, 25, False),
            ("Actual Paper Title", 16.0, 60, True),
            ("Author Name", 11.0, 90, False),
        ])
        result = analyzer.analyze_layout(elements)
        # The header lines should not be the title
        if result.title_candidates:
            assert "Vol." not in result.title_candidates[0].text

    def test_confidence_score(self, analyzer):
        elements = self._make_page([
            ("Clear Title With Large Font", 18.0, 50, True),
            ("First Author and Second Author", 11.0, 80, False),
            ("Abstract", 12.0, 120, True),
            ("Body text here.", 10.0, 140, False),
        ])
        result = analyzer.analyze_layout(elements)
        assert 0.0 <= result.confidence_score <= 1.0

    def test_body_font_size_detection(self, analyzer):
        elements = self._make_page([
            ("Title", 18.0, 50, True),
            ("Body line 1", 10.0, 100, False),
            ("Body line 2", 10.0, 115, False),
            ("Body line 3", 10.0, 130, False),
            ("Body line 4", 10.0, 145, False),
            ("Body line 5", 10.0, 160, False),
        ])
        result = analyzer.analyze_layout(elements)
        assert 9.0 <= result.body_font_size <= 11.0


# ============================================================================
# StatisticalPatternMatcher
# ============================================================================

class TestStatisticalPatternMatcher:

    def test_init(self):
        matcher = StatisticalPatternMatcher()
        assert not matcher.has_learned("title")

    def test_learn_and_query(self):
        matcher = StatisticalPatternMatcher()
        for i in range(5):
            matcher.learn_from_extraction(
                text="Title text",
                font_size=16.0 + i * 0.1,
                position=50.0,
                is_bold=True,
                is_italic=False,
                actual_type="title",
            )
        assert matcher.has_learned("title", min_observations=3)

    def test_score_candidate(self):
        matcher = StatisticalPatternMatcher()
        for _ in range(5):
            matcher.learn_from_extraction(
                text="Title text",
                font_size=16.0,
                position=50.0,
                is_bold=True,
                is_italic=False,
                actual_type="title",
            )
        score = matcher.score_candidate(
            font_size=16.0,
            position=50.0,
            is_bold=True,
            is_italic=False,
            candidate_type="title",
        )
        assert isinstance(score, float)
        assert score >= 0.0

    def test_stats(self):
        matcher = StatisticalPatternMatcher()
        matcher.learn_from_extraction(
            text="T", font_size=16.0, position=50.0,
            is_bold=True, is_italic=False, actual_type="title",
        )
        stats = matcher.get_stats()
        assert isinstance(stats, dict)

    def test_no_learning_returns_default(self):
        matcher = StatisticalPatternMatcher()
        score = matcher.score_candidate(
            font_size=16.0, position=50.0,
            is_bold=True, is_italic=False,
            candidate_type="title",
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestFeatureStats:

    def test_update_and_mean(self):
        stats = FeatureStats()
        stats.update(10.0)
        stats.update(20.0)
        assert stats.mean == 15.0

    def test_empty_mean(self):
        stats = FeatureStats()
        assert stats.mean == 0.0


# ============================================================================
# MathNotationHandler
# ============================================================================

class TestMathNotationHandler:

    @pytest.fixture
    def handler(self):
        return MathNotationHandler()

    def test_latex_greek_replacement(self, handler):
        result = handler.normalize_mathematical_text(r"\alpha + \beta = \gamma")
        assert "α" in result
        assert "β" in result
        assert "γ" in result
        assert r"\alpha" not in result

    def test_latex_formatting_stripped(self, handler):
        result = handler.normalize_mathematical_text(r"\textbf{important}")
        assert "important" in result
        assert r"\textbf" not in result

    def test_dollar_signs_removed(self, handler):
        result = handler.normalize_mathematical_text("The value $x + y$ is positive")
        assert "$" not in result
        assert "x + y" in result

    def test_braces_removed(self, handler):
        result = handler.normalize_mathematical_text("f{x} = {y}")
        assert "{" not in result
        assert "}" not in result

    def test_empty_input(self, handler):
        assert handler.normalize_mathematical_text("") == ""
        assert handler.normalize_mathematical_text(None) is None

    def test_whitespace_collapsed(self, handler):
        result = handler.normalize_mathematical_text("a   b   c")
        assert result == "a b c"

    def test_author_name_correction(self, handler):
        # Known corrections (if any are configured)
        result = handler.normalize_author_name("  John Smith  ")
        assert result == "John Smith"

    def test_author_name_empty(self, handler):
        assert handler.normalize_author_name("") == ""
        assert handler.normalize_author_name(None) is None

    def test_clean_extracted_text(self, handler):
        result = handler.clean_extracted_text("Some  text   with   spaces")
        # clean_extracted_text does light cleanup — may or may not collapse spaces
        assert isinstance(result, str)
        assert "text" in result

    def test_clean_extracted_text_empty(self, handler):
        assert handler.clean_extracted_text("") == ""
        assert handler.clean_extracted_text(None) is None
