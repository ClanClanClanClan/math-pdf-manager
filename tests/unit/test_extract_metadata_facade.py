#!/usr/bin/env python3
"""Tests for the metadata extraction facade."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestExtractFromFilename:
    """Test the filename-based fallback extractor."""

    def test_author_title_format(self):
        from pdf_processing.extract_metadata_facade import _extract_from_filename

        meta = _extract_from_filename(Path("Smith, Jones - A Great Title.pdf"))
        assert meta["title"] == "A Great Title"
        assert "Smith" in meta["authors"]
        assert "Jones" in meta["authors"]
        assert meta["source_method"] == "filename"

    def test_author_and_separator(self):
        from pdf_processing.extract_metadata_facade import _extract_from_filename

        meta = _extract_from_filename(Path("Smith and Jones - Some Title.pdf"))
        assert meta["title"] == "Some Title"
        assert "Smith" in meta["authors"]
        assert "Jones" in meta["authors"]

    def test_arxiv_id_in_filename(self):
        from pdf_processing.extract_metadata_facade import _extract_from_filename

        meta = _extract_from_filename(Path("2301.12345.pdf"))
        assert meta["arxiv_id"] == "2301.12345"

    def test_arxiv_id_with_version(self):
        from pdf_processing.extract_metadata_facade import _extract_from_filename

        meta = _extract_from_filename(Path("2301.12345v2.pdf"))
        assert meta["arxiv_id"] == "2301.12345v2"

    def test_plain_filename(self):
        from pdf_processing.extract_metadata_facade import _extract_from_filename

        meta = _extract_from_filename(Path("my paper.pdf"))
        assert meta["title"] == "my paper"
        assert meta["authors"] == []
        assert meta["confidence"] == 0.2

    def test_year_extraction(self):
        from pdf_processing.extract_metadata_facade import _extract_from_filename

        meta = _extract_from_filename(Path("Paper 2023 final.pdf"))
        assert meta["year"] == 2023

    def test_doi_from_filename(self):
        from pdf_processing.extract_metadata_facade import _extract_from_filename

        meta = _extract_from_filename(Path("10.1214_aop.2023.12345.pdf"))
        assert meta["doi"] == "10.1214/aop.2023.12345"

    def test_nonexistent_file(self):
        from pdf_processing.extract_metadata_facade import extract_pdf_metadata_enhanced

        meta = extract_pdf_metadata_enhanced(Path("/nonexistent/path/file.pdf"))
        assert meta["source_method"] == "filename"
        assert meta["confidence"] == 0.2


class TestMetadataQuality:
    """Test the metadata quality filters."""

    def test_valid_title(self):
        from pdf_processing.parsers.metadata_quality import is_valid_embedded_title

        assert is_valid_embedded_title("On the convergence of stochastic processes")
        assert is_valid_embedded_title("A long title about mathematics and related stuff")

    def test_garbage_titles(self):
        from pdf_processing.parsers.metadata_quality import is_valid_embedded_title

        assert not is_valid_embedded_title("Microsoft Word")
        assert not is_valid_embedded_title("LaTeX2e")
        assert not is_valid_embedded_title("Untitled")
        assert not is_valid_embedded_title("document")
        assert not is_valid_embedded_title("paper.tex")
        assert not is_valid_embedded_title("")
        assert not is_valid_embedded_title(None)
        assert not is_valid_embedded_title("ab")  # too short

    def test_valid_authors(self):
        from pdf_processing.parsers.metadata_quality import is_valid_embedded_authors

        assert is_valid_embedded_authors("John Smith")
        assert is_valid_embedded_authors("Smith, J. and Jones, K.")

    def test_garbage_authors(self):
        from pdf_processing.parsers.metadata_quality import is_valid_embedded_authors

        assert not is_valid_embedded_authors("Unknown")
        assert not is_valid_embedded_authors("admin")
        assert not is_valid_embedded_authors("Microsoft")
        assert not is_valid_embedded_authors("")
        assert not is_valid_embedded_authors(None)

    def test_doi_from_filename(self):
        from pdf_processing.parsers.metadata_quality import extract_doi_from_filename

        assert extract_doi_from_filename("10.1214_aop.2023.12345.pdf") == "10.1214/aop.2023.12345"
        assert extract_doi_from_filename("10.1007_s00440-021-01063-1.pdf") == "10.1007/s00440-021-01063-1"
        assert extract_doi_from_filename("regular_paper.pdf") is None

    def test_ssrn_from_filename(self):
        from pdf_processing.parsers.metadata_quality import extract_ssrn_id_from_filename

        assert extract_ssrn_id_from_filename("SSRN-id12345678.pdf") == "12345678"
        assert extract_ssrn_id_from_filename("SSRN_id1234567.pdf") == "1234567"
        assert extract_ssrn_id_from_filename("regular_paper.pdf") is None


class TestArxivAPIClientNewMethods:
    """Test the new methods added to ArxivAPIClient."""

    def test_search_by_id_returns_none_when_offline(self):
        from pdf_processing.extractors.api_client import ArxivAPIClient

        client = ArxivAPIClient()
        # Force offline
        client.api_available = False
        assert client.search_by_id("2301.12345") is None

    def test_search_by_id_returns_dict(self):
        from pdf_processing.extractors.api_client import ArxivAPIClient, ArxivMetadata

        client = ArxivAPIClient()
        # Mock fetch_metadata
        mock_metadata = ArxivMetadata(
            arxiv_id="2301.12345",
            title="Test Title",
            authors=["Author One", "Author Two"],
            abstract="Test abstract",
            categories=["math.PR"],
            primary_category="math.PR",
            published="2023-01-01",
            updated="2023-01-01",
        )
        client.fetch_metadata = MagicMock(return_value=mock_metadata)

        result = client.search_by_id("2301.12345")
        assert result is not None
        assert result["title"] == "Test Title"
        assert isinstance(result["authors"], list)
        assert "Author One" in result["authors"]

    def test_extract_arxiv_id_from_pdf_without_pymupdf(self):
        from pdf_processing.extractors.api_client import ArxivAPIClient

        client = ArxivAPIClient()
        # Should gracefully handle missing fitz
        with patch.dict('sys.modules', {'fitz': None}):
            # This should return None without crashing
            result = client.extract_arxiv_id_from_pdf("/nonexistent/file.pdf")
            assert result is None
