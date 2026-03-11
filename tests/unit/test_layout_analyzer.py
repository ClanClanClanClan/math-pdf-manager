#!/usr/bin/env python3
"""Tests for the advanced layout analyzer."""

import pytest
from pdf_processing.parsers.advanced_layout_analyzer import (
    AdvancedLayoutAnalyzer,
    TextElement,
    LayoutAnalysis,
)


@pytest.fixture
def analyzer():
    return AdvancedLayoutAnalyzer()


def _make_element(text, y, font_size=10, bold=False, page=0, x=50, width=400):
    """Helper to create TextElement with standard defaults."""
    flags = 16 if bold else 0
    return TextElement(
        text=text,
        bbox=(x, y, x + width, y + font_size + 2),
        font_name="Times-Roman",
        font_size=font_size,
        font_flags=flags,
        page_number=page,
    )


class TestTitleDetection:
    """Test font-size-based title detection."""

    def test_title_is_largest_text(self, analyzer):
        """The title should be the largest font text on the first page."""
        elements = [
            _make_element("On the Convergence of SGD", y=100, font_size=16, bold=True),
            _make_element("John Smith and Jane Doe", y=130, font_size=12),
            _make_element("Department of Mathematics, MIT", y=150, font_size=10),
            _make_element("Abstract", y=200, font_size=12, bold=True),
            _make_element("This paper studies the convergence of SGD in the case of...", y=220, font_size=10),
            _make_element("More body text here discussing results", y=240, font_size=10),
            _make_element("And more body text for good measure", y=260, font_size=10),
        ]

        result = analyzer.analyze_layout(elements)
        assert result.title_candidates
        title_text = " ".join(t.text for t in result.title_candidates)
        assert "Convergence of SGD" in title_text
        assert result.confidence_score > 0.5

    def test_multi_line_title(self, analyzer):
        """Multi-line titles should be merged into a single title."""
        elements = [
            _make_element("Optimal Control of McKean-Vlasov", y=100, font_size=16, bold=True),
            _make_element("Dynamics with Applications to Finance", y=120, font_size=16, bold=True),
            _make_element("Author Name", y=155, font_size=12),
            _make_element("Body text in normal size for the actual paper content", y=200, font_size=10),
            _make_element("More body text here that makes up the bulk of the paper", y=220, font_size=10),
        ]

        result = analyzer.analyze_layout(elements)
        title_text = " ".join(t.text for t in result.title_candidates)
        assert "McKean-Vlasov" in title_text
        assert "Finance" in title_text

    def test_no_elements(self, analyzer):
        """Empty input should return empty result."""
        result = analyzer.analyze_layout([])
        assert not result.title_candidates
        assert not result.author_candidates
        assert result.confidence_score == 0.0


class TestAuthorDetection:
    """Test author detection between title and abstract."""

    def test_authors_between_title_and_abstract(self, analyzer):
        """Authors should be found between the title and abstract."""
        elements = [
            _make_element("A Great Paper Title", y=100, font_size=16, bold=True),
            _make_element("John Smith and Jane Doe", y=140, font_size=12),
            _make_element("Abstract", y=200, font_size=11, bold=True),
            _make_element("This paper presents some results on a topic.", y=220, font_size=10),
            _make_element("More body text to fill out the paper a bit.", y=240, font_size=10),
        ]

        result = analyzer.analyze_layout(elements)
        assert result.author_candidates
        author_texts = [a.text for a in result.author_candidates]
        assert any("John Smith" in t for t in author_texts)

    def test_affiliations_excluded(self, analyzer):
        """University/department lines should NOT be authors."""
        elements = [
            _make_element("A Paper Title Here", y=100, font_size=16, bold=True),
            _make_element("John Smith", y=140, font_size=12),
            _make_element("Department of Mathematics, MIT", y=160, font_size=10),
            _make_element("Abstract", y=200, font_size=11, bold=True),
            _make_element("Body text goes here and should not be considered.", y=220, font_size=10),
        ]

        result = analyzer.analyze_layout(elements)
        author_texts = [a.text for a in result.author_candidates]
        assert not any("Department" in t for t in author_texts)
        assert not any("MIT" in t for t in author_texts)


class TestBodyFontSize:
    """Test body font size computation."""

    def test_body_size_is_mode(self, analyzer):
        """Body font size should be the most common size (weighted by text length)."""
        elements = [
            _make_element("Title", y=50, font_size=18, bold=True),
            _make_element("Author", y=80, font_size=12),
            # Many body-text lines at size 10
            _make_element("A" * 200, y=150, font_size=10),
            _make_element("B" * 200, y=170, font_size=10),
            _make_element("C" * 200, y=190, font_size=10),
            _make_element("D" * 200, y=210, font_size=10),
        ]

        body_size = analyzer._compute_body_font_size(elements)
        assert body_size == 10.0


class TestPublisherDetection:
    """Test publisher template detection."""

    def test_elsevier_detection(self, analyzer):
        """Should detect Elsevier from ScienceDirect header."""
        elements = [
            _make_element("Contents lists available at ScienceDirect", y=20, font_size=8),
            _make_element("Journal of Mathematical Analysis", y=40, font_size=10),
            _make_element("Some Paper Title", y=100, font_size=16, bold=True),
        ]

        pub = analyzer._detect_publisher(elements)
        assert pub == "elsevier"

    def test_arxiv_detection(self, analyzer):
        """Should detect arXiv stamp."""
        elements = [
            _make_element("arXiv:2301.12345v2 [math.PR] 15 Jan 2023", y=20, font_size=8),
            _make_element("Some Paper Title", y=100, font_size=16, bold=True),
        ]

        pub = analyzer._detect_publisher(elements)
        assert pub == "arxiv"

    def test_no_publisher(self, analyzer):
        """No publisher should return None."""
        elements = [
            _make_element("Just a regular title", y=100, font_size=16, bold=True),
            _make_element("Body text without publisher info", y=200, font_size=10),
        ]

        pub = analyzer._detect_publisher(elements)
        assert pub is None


class TestHeaderFooterFiltering:
    """Test header/footer identification."""

    def test_page_number_filtered(self, analyzer):
        """Page numbers should be identified as header/footer."""
        elements = [
            _make_element("42", y=780, font_size=10, x=300, width=20),
            _make_element("Paper Title", y=100, font_size=16, bold=True),
        ]

        hf = analyzer._find_header_footer(elements, elements)
        hf_texts = [e.text for e in hf]
        assert "42" in hf_texts

    def test_doi_filtered(self, analyzer):
        """DOI lines should be filtered as headers."""
        elements = [
            _make_element("doi: 10.1234/example", y=10, font_size=8),
            _make_element("Paper Title", y=100, font_size=16, bold=True),
        ]

        hf = analyzer._find_header_footer(elements, elements)
        hf_texts = [e.text for e in hf]
        assert any("doi" in t for t in hf_texts)


class TestConfidenceScoring:
    """Test confidence computation."""

    def test_high_confidence_with_clear_layout(self, analyzer):
        """Clear title + authors + abstract should give high confidence."""
        elements = [
            _make_element("A Markov Chain Monte Carlo Approach", y=100, font_size=18, bold=True),
            _make_element("John Smith and Jane Doe", y=140, font_size=12),
            _make_element("Abstract", y=200, font_size=11, bold=True),
            _make_element("This paper presents a novel MCMC algorithm for sampling.", y=220, font_size=10),
            _make_element("More body text to pad out the paper.", y=240, font_size=10),
            _make_element("And even more body text for good measure.", y=260, font_size=10),
        ]

        result = analyzer.analyze_layout(elements)
        assert result.confidence_score >= 0.6
