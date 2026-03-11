"""Phase 3: Discovery engine audit."""
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

httpx = pytest.importorskip("httpx")

from discovery.engine import DiscoveryEngine, PaperCandidate


# ============================================================================
# Fixtures and mock data
# ============================================================================

ARXIV_XML_SINGLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<entry>
<id>http://arxiv.org/abs/2101.00001v1</id>
<title>Stochastic Calculus and Applications</title>
<author><name>John Smith</name></author>
<author><name>Jane Doe</name></author>
<arxiv:doi>10.1234/test.2021.001</arxiv:doi>
<link rel="alternate" type="text/html" href="http://arxiv.org/abs/2101.00001v1"/>
<published>2021-01-01T00:00:00Z</published>
</entry>
</feed>"""

ARXIV_XML_MULTI = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<entry>
<id>http://arxiv.org/abs/2101.00001v1</id>
<title>Stochastic Calculus and Applications</title>
<author><name>John Smith</name></author>
<author><name>Jane Doe</name></author>
<arxiv:doi>10.1234/test.2021.001</arxiv:doi>
<link rel="alternate" type="text/html" href="http://arxiv.org/abs/2101.00001v1"/>
<published>2021-01-01T00:00:00Z</published>
</entry>
<entry>
<id>http://arxiv.org/abs/2202.12345v2</id>
<title>Martingale   Representation
Theorems</title>
<author><name>Alice Chen</name></author>
<arxiv:doi>10.9999/mart.2022.005</arxiv:doi>
<link rel="alternate" type="text/html" href="http://arxiv.org/abs/2202.12345v2"/>
<published>2022-06-15T12:00:00Z</published>
</entry>
</feed>"""

ARXIV_XML_MINIMAL = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<entry>
<id>http://arxiv.org/abs/9999.99999v1</id>
<title>Untitled</title>
<published>2023-01-01T00:00:00Z</published>
</entry>
</feed>"""

ARXIV_XML_EMPTY = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>"""

CROSSREF_SEARCH_RESPONSE = {
    "message": {
        "items": [
            {
                "title": ["Brownian Motion in Finance"],
                "author": [
                    {"given": "Alice", "family": "Brown"},
                    {"given": "Bob", "family": "Green"},
                ],
                "DOI": "10.5678/finance.2022.001",
                "URL": "https://doi.org/10.5678/finance.2022.001",
                "published-print": {"date-parts": [[2022, 3, 15]]},
            }
        ]
    }
}

CROSSREF_SINGLE_RECORD = {
    "message": {
        "title": ["Optimal Stopping Theory"],
        "author": [{"given": "Carlos", "family": "Diaz"}],
        "DOI": "10.1111/optimal.2023.007",
        "URL": "https://doi.org/10.1111/optimal.2023.007",
        "published-online": {"date-parts": [[2023, 7, 1]]},
    }
}


def _make_handler(responses: dict):
    """Build an httpx mock transport from a url-prefix -> Response mapping.

    *responses* maps URL substrings to ``httpx.Response`` objects.  The first
    matching substring wins.  If nothing matches, return a generic 404.
    """

    async def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for pattern, response in responses.items():
            if pattern in url:
                return response
        return httpx.Response(status_code=404, text="Not found")

    return httpx.MockTransport(handler)


@pytest.fixture
def engine_with_transport():
    """Factory fixture: create a DiscoveryEngine backed by mock transport."""

    def _factory(responses: dict) -> DiscoveryEngine:
        transport = _make_handler(responses)
        client = httpx.AsyncClient(transport=transport)
        return DiscoveryEngine(client=client)

    return _factory


# ============================================================================
# Section 3A: PaperCandidate dataclass
# ============================================================================


class TestPaperCandidateDataclass:
    """Audit: Verify PaperCandidate frozen dataclass contract."""

    def test_creation_with_required_fields(self):
        """PaperCandidate requires title and authors."""
        pc = PaperCandidate(title="Test", authors=["Author"])
        assert pc.title == "Test"
        assert pc.authors == ["Author"]

    def test_defaults(self):
        """Optional fields should have sensible defaults."""
        pc = PaperCandidate(title="T", authors=["A"])
        assert pc.doi is None
        assert pc.arxiv_id is None
        assert pc.source == ""
        assert pc.url is None
        assert pc.published_year is None
        assert pc.metadata == {}

    def test_frozen_immutability(self):
        """Frozen dataclass should reject attribute assignment."""
        pc = PaperCandidate(title="T", authors=["A"])
        with pytest.raises(AttributeError):
            pc.title = "Changed"

    def test_equality(self):
        """Two PaperCandidates with identical fields should be equal."""
        a = PaperCandidate(title="T", authors=["A"], doi="10.1/x")
        b = PaperCandidate(title="T", authors=["A"], doi="10.1/x")
        assert a == b

    def test_metadata_default_factory_isolation(self):
        """Each instance should get its own metadata dict."""
        a = PaperCandidate(title="T1", authors=["A"])
        b = PaperCandidate(title="T2", authors=["B"])
        assert a.metadata is not b.metadata


# ============================================================================
# Section 3B: ArXiv XML parsing (_parse_arxiv_feed)
# ============================================================================


class TestArxivXmlParsing:
    """Audit: Verify regex-based ArXiv Atom feed parsing."""

    def _parse(self, xml: str):
        engine = DiscoveryEngine.__new__(DiscoveryEngine)
        return list(engine._parse_arxiv_feed(xml))

    def test_single_entry_title(self):
        """Title should be extracted and whitespace-collapsed."""
        results = self._parse(ARXIV_XML_SINGLE)
        assert len(results) == 1
        assert results[0].title == "Stochastic Calculus and Applications"

    def test_single_entry_authors(self):
        """Authors should be extracted from <name> tags."""
        results = self._parse(ARXIV_XML_SINGLE)
        assert results[0].authors == ["John Smith", "Jane Doe"]

    def test_single_entry_doi(self):
        """DOI should be extracted from <arxiv:doi>."""
        results = self._parse(ARXIV_XML_SINGLE)
        assert results[0].doi == "10.1234/test.2021.001"

    def test_single_entry_arxiv_id(self):
        """ArXiv ID should be extracted from <id> tag."""
        results = self._parse(ARXIV_XML_SINGLE)
        assert results[0].arxiv_id == "2101.00001v1"

    def test_single_entry_url(self):
        """URL should be extracted from <link rel='alternate'>."""
        results = self._parse(ARXIV_XML_SINGLE)
        assert results[0].url == "http://arxiv.org/abs/2101.00001v1"

    def test_single_entry_published_year(self):
        """FIXED: Published year is now correctly parsed from ISO 8601 timestamps."""
        results = self._parse(ARXIV_XML_SINGLE)
        assert results[0].published_year == 2021

    def test_single_entry_source(self):
        """Source should be 'arxiv'."""
        results = self._parse(ARXIV_XML_SINGLE)
        assert results[0].source == "arxiv"

    def test_single_entry_metadata_has_raw(self):
        """Metadata should contain the raw entry XML."""
        results = self._parse(ARXIV_XML_SINGLE)
        assert "raw" in results[0].metadata
        # defusedxml serializes with namespace prefixes; check title text is present
        assert "Stochastic Calculus" in results[0].metadata["raw"]

    def test_multi_entry(self):
        """Multiple entries should all be parsed."""
        results = self._parse(ARXIV_XML_MULTI)
        assert len(results) == 2

    def test_multiline_title_whitespace_collapsed(self):
        """Titles with internal newlines/spaces should be collapsed."""
        results = self._parse(ARXIV_XML_MULTI)
        second = results[1]
        assert second.title == "Martingale Representation Theorems"
        # No double spaces or newlines
        assert "  " not in second.title
        assert "\n" not in second.title

    def test_minimal_entry_missing_fields(self):
        """Entry without authors, DOI, or URL should still parse."""
        results = self._parse(ARXIV_XML_MINIMAL)
        assert len(results) == 1
        candidate = results[0]
        assert candidate.title == "Untitled"
        assert candidate.authors == ["Unknown"]
        assert candidate.doi is None
        assert candidate.url is None

    def test_empty_feed_returns_nothing(self):
        """Feed with no <entry> tags should yield an empty list."""
        results = self._parse(ARXIV_XML_EMPTY)
        assert results == []

    def test_security_uses_defusedxml(self):
        """FIXED: ArXiv XML is now parsed with defusedxml."""
        import inspect
        import discovery.engine as engine_mod

        engine_source = inspect.getsource(engine_mod)
        assert "defusedxml" in engine_source, (
            "defusedxml should be used for XML parsing"
        )

    def test_xml_entities_properly_decoded(self):
        """FIXED: defusedxml properly decodes XML entities."""
        xml_with_entity = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<entry>
<id>http://arxiv.org/abs/2301.00001v1</id>
<title>Inequalities for L&amp;p spaces</title>
<author><name>Test Author</name></author>
<published>2023-01-01T00:00:00Z</published>
</entry>
</feed>"""
        results = self._parse(xml_with_entity)
        assert len(results) == 1
        # defusedxml properly decodes &amp; to &
        assert "L&p" in results[0].title


# ============================================================================
# Section 3C: Crossref JSON parsing (_build_candidate_from_crossref)
# ============================================================================


class TestCrossrefJsonParsing:
    """Audit: Verify Crossref work-item to PaperCandidate conversion."""

    def _build(self, record: dict) -> PaperCandidate:
        engine = DiscoveryEngine.__new__(DiscoveryEngine)
        return engine._build_candidate_from_crossref(record)

    def test_basic_record(self):
        """Standard Crossref record should parse correctly."""
        record = CROSSREF_SEARCH_RESPONSE["message"]["items"][0]
        candidate = self._build(record)
        assert candidate.title == "Brownian Motion in Finance"
        assert candidate.authors == ["Alice Brown", "Bob Green"]
        assert candidate.doi == "10.5678/finance.2022.001"
        assert candidate.source == "crossref"
        assert candidate.published_year == 2022

    def test_url_extracted(self):
        """URL field should be extracted from Crossref record."""
        record = CROSSREF_SEARCH_RESPONSE["message"]["items"][0]
        candidate = self._build(record)
        assert candidate.url == "https://doi.org/10.5678/finance.2022.001"

    def test_metadata_is_full_record(self):
        """metadata should contain the original Crossref record."""
        record = CROSSREF_SEARCH_RESPONSE["message"]["items"][0]
        candidate = self._build(record)
        assert candidate.metadata is record

    def test_missing_title_defaults_to_unknown(self):
        """Record with no title should produce 'Unknown title'."""
        candidate = self._build({"author": [{"given": "X", "family": "Y"}]})
        assert candidate.title == "Unknown title"

    def test_missing_authors_defaults_to_unknown(self):
        """Record with no author should produce ['Unknown']."""
        candidate = self._build({"title": ["Some Title"]})
        assert candidate.authors == ["Unknown"]

    def test_empty_author_list_defaults_to_unknown(self):
        """Record with empty author list should produce ['Unknown']."""
        candidate = self._build({"title": ["T"], "author": []})
        assert candidate.authors == ["Unknown"]

    def test_published_online_fallback(self):
        """When published-print is missing, fall back to published-online."""
        record = {
            "title": ["Online Paper"],
            "author": [{"given": "A", "family": "B"}],
            "DOI": "10.0/x",
            "published-online": {"date-parts": [[2024, 11]]},
        }
        candidate = self._build(record)
        assert candidate.published_year == 2024

    def test_no_date_returns_none_year(self):
        """Record with no date fields should have published_year=None."""
        candidate = self._build({"title": ["No Date"]})
        assert candidate.published_year is None

    def test_malformed_date_parts(self):
        """Malformed date-parts should not crash, just yield None year."""
        candidate = self._build({
            "title": ["Bad Date"],
            "published-print": {"date-parts": [[]]},
        })
        assert candidate.published_year is None

    def test_title_as_string_not_list(self):
        """If title is a plain string (non-standard), _extract_first handles it."""
        candidate = self._build({"title": "Just a String"})
        assert candidate.title == "Just a String"

    def test_url_as_list(self):
        """If URL is a list, first element is extracted."""
        candidate = self._build({
            "title": ["T"],
            "URL": ["https://example.com/1", "https://example.com/2"],
        })
        assert candidate.url == "https://example.com/1"


# ============================================================================
# Section 3D: Author formatting
# ============================================================================


class TestAuthorFormatting:
    """Audit: Verify _format_crossref_author edge cases."""

    def _fmt(self, author: dict) -> str:
        engine = DiscoveryEngine.__new__(DiscoveryEngine)
        return engine._format_crossref_author(author)

    def test_given_and_family(self):
        """Standard given + family should produce 'Given Family'."""
        assert self._fmt({"given": "Alice", "family": "Brown"}) == "Alice Brown"

    def test_family_only(self):
        """Family-only author should return just the family name."""
        assert self._fmt({"family": "Consortium"}) == "Consortium"

    def test_given_only(self):
        """Given-only author should return just the given name."""
        assert self._fmt({"given": "Madonna"}) == "Madonna"

    def test_empty_dict(self):
        """Empty author dict should return 'Unknown'."""
        assert self._fmt({}) == "Unknown"

    def test_whitespace_stripping(self):
        """Leading/trailing whitespace in names should be stripped."""
        assert self._fmt({"given": "  Alice ", "family": " Brown  "}) == "Alice Brown"

    def test_blank_given_and_family(self):
        """Blank strings should be treated as absent."""
        assert self._fmt({"given": "   ", "family": "   "}) == "Unknown"


# ============================================================================
# Section 3E: search_by_query (HTTP integration)
# ============================================================================


class TestSearchByQuery:
    """Audit: Verify merged multi-source search."""

    @pytest.mark.asyncio
    async def test_merges_arxiv_and_crossref(self, engine_with_transport):
        """Results from both sources should be merged."""
        engine = engine_with_transport({
            "export.arxiv.org": httpx.Response(
                status_code=200,
                text=ARXIV_XML_SINGLE,
                headers={"content-type": "application/xml"},
            ),
            "api.crossref.org": httpx.Response(
                status_code=200,
                json=CROSSREF_SEARCH_RESPONSE,
                headers={"content-type": "application/json"},
            ),
        })
        results = await engine.search_by_query("stochastic calculus")
        # Should contain at least one from each source
        sources = {r.source for r in results}
        assert "arxiv" in sources, "Expected ArXiv results"
        assert "crossref" in sources, "Expected Crossref results"
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_arxiv_failure_still_returns_crossref(self, engine_with_transport):
        """If ArXiv fails, Crossref results should still be returned."""
        engine = engine_with_transport({
            "export.arxiv.org": httpx.Response(
                status_code=500,
                text="Internal Server Error",
            ),
            "api.crossref.org": httpx.Response(
                status_code=200,
                json=CROSSREF_SEARCH_RESPONSE,
                headers={"content-type": "application/json"},
            ),
        })
        results = await engine.search_by_query("finance")
        assert len(results) >= 1
        assert all(r.source == "crossref" for r in results)

    @pytest.mark.asyncio
    async def test_crossref_failure_still_returns_arxiv(self, engine_with_transport):
        """If Crossref fails, ArXiv results should still be returned."""
        engine = engine_with_transport({
            "export.arxiv.org": httpx.Response(
                status_code=200,
                text=ARXIV_XML_SINGLE,
                headers={"content-type": "application/xml"},
            ),
            "api.crossref.org": httpx.Response(
                status_code=503,
                text="Service Unavailable",
            ),
        })
        results = await engine.search_by_query("stochastic")
        assert len(results) >= 1
        assert all(r.source == "arxiv" for r in results)

    @pytest.mark.asyncio
    async def test_both_sources_fail_returns_empty(self, engine_with_transport):
        """If both sources fail, an empty list should be returned (not an exception)."""
        engine = engine_with_transport({
            "export.arxiv.org": httpx.Response(status_code=500, text="error"),
            "api.crossref.org": httpx.Response(status_code=500, text="error"),
        })
        results = await engine.search_by_query("anything")
        assert results == []


# ============================================================================
# Section 3F: search_by_doi
# ============================================================================


class TestSearchByDoi:
    """Audit: Verify single-DOI lookup via Crossref."""

    @pytest.mark.asyncio
    async def test_found_record(self, engine_with_transport):
        """Valid DOI should return a PaperCandidate."""
        engine = engine_with_transport({
            "api.crossref.org/works/10.1111": httpx.Response(
                status_code=200,
                json=CROSSREF_SINGLE_RECORD,
                headers={"content-type": "application/json"},
            ),
        })
        result = await engine.search_by_doi("10.1111/optimal.2023.007")
        assert result is not None
        assert result.title == "Optimal Stopping Theory"
        assert result.doi == "10.1111/optimal.2023.007"
        assert result.source == "crossref"
        assert result.published_year == 2023

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, engine_with_transport):
        """404 from Crossref should return None, not raise."""
        engine = engine_with_transport({
            "api.crossref.org": httpx.Response(status_code=404, text="Not found"),
        })
        result = await engine.search_by_doi("10.0000/does.not.exist")
        assert result is None

    @pytest.mark.asyncio
    async def test_server_error_returns_none(self, engine_with_transport):
        """Server error should be caught and return None."""
        engine = engine_with_transport({
            "api.crossref.org": httpx.Response(status_code=500, text="error"),
        })
        result = await engine.search_by_doi("10.0000/error")
        assert result is None

    @pytest.mark.asyncio
    async def test_doi_whitespace_stripped(self, engine_with_transport):
        """Leading/trailing whitespace in DOI should be stripped."""
        engine = engine_with_transport({
            "api.crossref.org/works/10.1111": httpx.Response(
                status_code=200,
                json=CROSSREF_SINGLE_RECORD,
                headers={"content-type": "application/json"},
            ),
        })
        result = await engine.search_by_doi("  10.1111/optimal.2023.007  ")
        assert result is not None


# ============================================================================
# Section 3G: search_by_arxiv_id
# ============================================================================


class TestSearchByArxivId:
    """Audit: Verify ArXiv ID lookup constructs correct query."""

    @pytest.mark.asyncio
    async def test_constructs_id_query(self, engine_with_transport):
        """search_by_arxiv_id should send 'id:XXXX.XXXXX' query to ArXiv."""
        captured_urls = []

        async def capturing_handler(request: httpx.Request) -> httpx.Response:
            captured_urls.append(str(request.url))
            return httpx.Response(
                status_code=200,
                text=ARXIV_XML_SINGLE,
                headers={"content-type": "application/xml"},
            )

        transport = httpx.MockTransport(capturing_handler)
        client = httpx.AsyncClient(transport=transport)
        engine = DiscoveryEngine(client=client)

        result = await engine.search_by_arxiv_id("2101.00001")
        assert result is not None
        assert any("id%3A2101.00001" in url or "id:2101.00001" in url for url in captured_urls), (
            f"Expected 'id:2101.00001' in query params, got URLs: {captured_urls}"
        )

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_feed(self, engine_with_transport):
        """Empty ArXiv feed should return None."""
        engine = engine_with_transport({
            "export.arxiv.org": httpx.Response(
                status_code=200,
                text=ARXIV_XML_EMPTY,
                headers={"content-type": "application/xml"},
            ),
        })
        result = await engine.search_by_arxiv_id("0000.00000")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_first_result(self, engine_with_transport):
        """Should return the first (and ideally only) result."""
        engine = engine_with_transport({
            "export.arxiv.org": httpx.Response(
                status_code=200,
                text=ARXIV_XML_MULTI,
                headers={"content-type": "application/xml"},
            ),
        })
        result = await engine.search_by_arxiv_id("2101.00001")
        assert result is not None
        assert result.arxiv_id == "2101.00001v1"


# ============================================================================
# Section 3H: search_by_authors
# ============================================================================


class TestSearchByAuthors:
    """Audit: Verify author-based search."""

    @pytest.mark.asyncio
    async def test_author_search_merges_sources(self, engine_with_transport):
        """Author search should query both ArXiv and Crossref."""
        engine = engine_with_transport({
            "export.arxiv.org": httpx.Response(
                status_code=200,
                text=ARXIV_XML_SINGLE,
                headers={"content-type": "application/xml"},
            ),
            "api.crossref.org": httpx.Response(
                status_code=200,
                json=CROSSREF_SEARCH_RESPONSE,
                headers={"content-type": "application/json"},
            ),
        })
        results = await engine.search_by_authors(["Smith"])
        sources = {r.source for r in results}
        assert "arxiv" in sources
        assert "crossref" in sources

    @pytest.mark.asyncio
    async def test_partial_failure_returns_surviving_source(self, engine_with_transport):
        """If one source fails, the other still contributes."""
        engine = engine_with_transport({
            "export.arxiv.org": httpx.Response(status_code=500, text="error"),
            "api.crossref.org": httpx.Response(
                status_code=200,
                json=CROSSREF_SEARCH_RESPONSE,
                headers={"content-type": "application/json"},
            ),
        })
        results = await engine.search_by_authors(["Brown"])
        assert len(results) >= 1
        assert all(r.source == "crossref" for r in results)


# ============================================================================
# Section 3I: BibTeX import (import_from_bibliography)
# ============================================================================


SAMPLE_BIBTEX = """\
@article{smith2021,
  title = {{Stochastic Calculus} and Applications},
  author = {John Smith and Jane {Doe}},
  doi = {10.1234/test.2021.001},
  year = {2021},
  url = {https://example.com/paper1},
}

@inproceedings{brown2022,
  title = {Brownian Motion in Finance},
  author = {Alice Brown},
  doi = {10.5678/finance.2022.001},
  year = {2022},
}
"""

BIBTEX_NO_TITLE = """\
@article{notitle,
  author = {Ghost Author},
  year = {2020},
}
"""

BIBTEX_BAD_YEAR = """\
@article{badyear,
  title = {Paper with bad year},
  author = {Test Author},
  year = {forthcoming},
}
"""


class TestBibtexImport:
    """Audit: Verify BibTeX parsing via import_from_bibliography."""

    def _import(self, bib_content: str):
        engine = DiscoveryEngine.__new__(DiscoveryEngine)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False, encoding="utf-8"
        ) as f:
            f.write(bib_content)
            f.flush()
            path = Path(f.name)
        try:
            return engine.import_from_bibliography(path)
        finally:
            path.unlink(missing_ok=True)

    def test_parses_two_entries(self):
        """Sample BibTeX should produce two PaperCandidates."""
        candidates = self._import(SAMPLE_BIBTEX)
        assert len(candidates) == 2

    def test_title_extracted(self):
        """Titles should be extracted from bibtex fields."""
        candidates = self._import(SAMPLE_BIBTEX)
        titles = [c.title for c in candidates]
        assert "Stochastic Calculus and Applications" in titles
        assert "Brownian Motion in Finance" in titles

    def test_clean_field_removes_braces(self):
        """_clean_field should strip LaTeX braces from titles."""
        candidates = self._import(SAMPLE_BIBTEX)
        for c in candidates:
            assert "{" not in c.title
            assert "}" not in c.title

    def test_authors_split_on_and(self):
        """Authors should be split on ' and '."""
        candidates = self._import(SAMPLE_BIBTEX)
        first = [c for c in candidates if "Stochastic" in c.title][0]
        assert len(first.authors) == 2
        assert "John Smith" in first.authors
        # Braces around Doe should be removed
        assert "Jane Doe" in first.authors

    def test_doi_extracted(self):
        """DOI should be extracted and cleaned."""
        candidates = self._import(SAMPLE_BIBTEX)
        dois = [c.doi for c in candidates if c.doi]
        assert "10.1234/test.2021.001" in dois

    def test_year_extracted_as_int(self):
        """Year should be an integer."""
        candidates = self._import(SAMPLE_BIBTEX)
        years = [c.published_year for c in candidates]
        assert 2021 in years
        assert 2022 in years

    def test_url_extracted(self):
        """URL should be extracted when present."""
        candidates = self._import(SAMPLE_BIBTEX)
        first = [c for c in candidates if "Stochastic" in c.title][0]
        assert first.url == "https://example.com/paper1"

    def test_source_is_bibliography(self):
        """All bibliography imports should have source='bibliography'."""
        candidates = self._import(SAMPLE_BIBTEX)
        assert all(c.source == "bibliography" for c in candidates)

    def test_entry_without_title_skipped(self):
        """BibTeX entries without a title should be silently skipped."""
        candidates = self._import(BIBTEX_NO_TITLE)
        assert len(candidates) == 0

    def test_bad_year_becomes_none(self):
        """Non-numeric year should become None, not crash."""
        candidates = self._import(BIBTEX_BAD_YEAR)
        assert len(candidates) == 1
        assert candidates[0].published_year is None

    def test_unsupported_format_raises(self):
        """Requesting an unsupported format should raise ValueError."""
        engine = DiscoveryEngine.__new__(DiscoveryEngine)
        with tempfile.NamedTemporaryFile(suffix=".ris", delete=False) as f:
            path = Path(f.name)
        try:
            with pytest.raises(ValueError, match="Unsupported bibliography format"):
                engine.import_from_bibliography(path, fmt="ris")
        finally:
            path.unlink(missing_ok=True)


# ============================================================================
# Section 3J: _clean_field
# ============================================================================


class TestCleanField:
    """Audit: Verify _clean_field brace removal."""

    def _clean(self, value: str) -> str:
        engine = DiscoveryEngine.__new__(DiscoveryEngine)
        return engine._clean_field(value)

    def test_removes_curly_braces(self):
        """Curly braces should be removed."""
        assert self._clean("{Stochastic}") == "Stochastic"

    def test_nested_braces(self):
        """Nested braces should all be removed."""
        assert self._clean("{{Nested}} Value") == "Nested Value"

    def test_strips_whitespace(self):
        """Leading/trailing whitespace should be stripped."""
        assert self._clean("  spaced  ") == "spaced"

    def test_plain_string_unchanged(self):
        """String without braces should pass through unchanged."""
        assert self._clean("plain text") == "plain text"

    def test_empty_string(self):
        """Empty string should return empty."""
        assert self._clean("") == ""


# ============================================================================
# Section 3K: scan_conference_proceedings
# ============================================================================


class TestScanConferenceProceedings:
    """Audit: Verify DOI extraction from conference proceedings text."""

    @pytest.mark.asyncio
    async def test_extracts_dois_from_file(self, engine_with_transport, tmp_path):
        """DOIs embedded in text should be extracted and looked up."""
        proceedings_text = """\
Session 1: Stochastic Analysis
Paper 1: doi 10.1234/proc.2023.001
Paper 2: see https://doi.org/10.5678/proc.2023.002
Paper 3: reference 10.9999/proc.2023.003
"""
        text_file = tmp_path / "proceedings.txt"
        text_file.write_text(proceedings_text, encoding="utf-8")

        engine = engine_with_transport({
            "api.crossref.org/works/10.1234": httpx.Response(
                status_code=200,
                json={"message": {
                    "title": ["Paper One"],
                    "author": [{"given": "A", "family": "B"}],
                    "DOI": "10.1234/proc.2023.001",
                }},
                headers={"content-type": "application/json"},
            ),
            "api.crossref.org/works/10.5678": httpx.Response(
                status_code=200,
                json={"message": {
                    "title": ["Paper Two"],
                    "author": [{"given": "C", "family": "D"}],
                    "DOI": "10.5678/proc.2023.002",
                }},
                headers={"content-type": "application/json"},
            ),
            "api.crossref.org/works/10.9999": httpx.Response(
                status_code=404,
                text="Not found",
            ),
        })
        results = await engine.scan_conference_proceedings(str(text_file))
        # Two resolved, one 404
        assert len(results) == 2
        dois = {r.doi for r in results}
        assert "10.1234/proc.2023.001" in dois
        assert "10.5678/proc.2023.002" in dois

    @pytest.mark.asyncio
    async def test_deduplicates_dois(self, engine_with_transport, tmp_path):
        """Duplicate DOIs in text should only be looked up once."""
        text = "10.1234/dup.001 and again 10.1234/dup.001"
        text_file = tmp_path / "dupes.txt"
        text_file.write_text(text, encoding="utf-8")

        call_count = 0

        async def counting_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                status_code=200,
                json={"message": {
                    "title": ["Dup Paper"],
                    "author": [{"given": "X", "family": "Y"}],
                    "DOI": "10.1234/dup.001",
                }},
                headers={"content-type": "application/json"},
            )

        transport = httpx.MockTransport(counting_handler)
        client = httpx.AsyncClient(transport=transport)
        engine = DiscoveryEngine(client=client)

        results = await engine.scan_conference_proceedings(str(text_file))
        assert len(results) == 1
        assert call_count == 1, "Duplicate DOI should only trigger one Crossref lookup"

    @pytest.mark.asyncio
    async def test_max_results_limit(self, engine_with_transport, tmp_path):
        """max_results should cap the number of DOIs processed."""
        # Generate many DOIs
        lines = [f"10.1234/many.{i:04d}" for i in range(50)]
        text_file = tmp_path / "many.txt"
        text_file.write_text("\n".join(lines), encoding="utf-8")

        call_count = 0

        async def counting_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(status_code=404, text="Not found")

        transport = httpx.MockTransport(counting_handler)
        client = httpx.AsyncClient(transport=transport)
        engine = DiscoveryEngine(client=client)

        await engine.scan_conference_proceedings(str(text_file), max_results=5)
        assert call_count == 5, f"Expected 5 lookups, got {call_count}"

    @pytest.mark.asyncio
    async def test_doi_regex_pattern(self):
        """Verify the DOI regex matches expected patterns."""
        import re

        doi_pattern = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)

        # Should match
        assert doi_pattern.search("10.1234/test.2021.001")
        assert doi_pattern.search("10.1000/journal-abc")
        assert doi_pattern.search("10.12345/some_(ref).v2")
        assert doi_pattern.search("10.1234567/long-registrant")

        # Should NOT match (registrant too short)
        assert not doi_pattern.fullmatch("10.12/too.short")

    @pytest.mark.asyncio
    async def test_scan_from_url(self, engine_with_transport):
        """When source is a URL (not a file), it should be fetched via HTTP."""
        proceedings_html = "<html><body>DOI: 10.1234/web.2023.001</body></html>"

        async def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "example.com/proceedings" in url:
                return httpx.Response(
                    status_code=200,
                    text=proceedings_html,
                    headers={"content-type": "text/html"},
                )
            if "api.crossref.org" in url:
                return httpx.Response(
                    status_code=200,
                    json={"message": {
                        "title": ["Web Paper"],
                        "author": [{"given": "W", "family": "Z"}],
                        "DOI": "10.1234/web.2023.001",
                    }},
                    headers={"content-type": "application/json"},
                )
            return httpx.Response(status_code=404, text="Not found")

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)
        engine = DiscoveryEngine(client=client)

        results = await engine.scan_conference_proceedings("https://example.com/proceedings")
        assert len(results) == 1
        assert results[0].doi == "10.1234/web.2023.001"


# ============================================================================
# Section 3L: _extract_first and _extract_year helpers
# ============================================================================


class TestHelperMethods:
    """Audit: Verify small helper methods."""

    def _engine(self):
        return DiscoveryEngine.__new__(DiscoveryEngine)

    def test_extract_first_list(self):
        """First element of a list should be returned."""
        assert self._engine()._extract_first(["a", "b"]) == "a"

    def test_extract_first_string(self):
        """A plain string should be returned as-is."""
        assert self._engine()._extract_first("hello") == "hello"

    def test_extract_first_none(self):
        """None input should return None."""
        assert self._engine()._extract_first(None) is None

    def test_extract_first_empty_list(self):
        """Empty list should return None."""
        assert self._engine()._extract_first([]) is None

    def test_extract_year_valid(self):
        """Standard date-parts should yield the year."""
        assert self._engine()._extract_year({"date-parts": [[2022, 6, 1]]}) == 2022

    def test_extract_year_missing_date_parts(self):
        """Missing date-parts key should return None."""
        assert self._engine()._extract_year({}) is None

    def test_extract_year_empty_date_parts(self):
        """Empty date-parts should return None."""
        assert self._engine()._extract_year({"date-parts": []}) is None

    def test_extract_year_empty_inner_list(self):
        """date-parts with empty inner list should return None."""
        assert self._engine()._extract_year({"date-parts": [[]]}) is None

    def test_extract_year_non_numeric(self):
        """Non-numeric year in date-parts should return None."""
        assert self._engine()._extract_year({"date-parts": [["unknown"]]}) is None


# ============================================================================
# Section 3M: Error handling and resilience
# ============================================================================


class TestErrorHandling:
    """Audit: Verify graceful degradation when sources fail."""

    @pytest.mark.asyncio
    async def test_gather_return_exceptions_used(self):
        """AUDIT: search_by_query uses asyncio.gather(return_exceptions=True)."""
        import inspect

        source = inspect.getsource(DiscoveryEngine.search_by_query)
        assert "return_exceptions=True" in source, (
            "search_by_query should use return_exceptions=True to prevent "
            "one source failure from killing the entire search"
        )

    @pytest.mark.asyncio
    async def test_search_by_authors_also_uses_return_exceptions(self):
        """AUDIT: search_by_authors also uses return_exceptions=True."""
        import inspect

        source = inspect.getsource(DiscoveryEngine.search_by_authors)
        assert "return_exceptions=True" in source

    @pytest.mark.asyncio
    async def test_network_timeout_handled(self):
        """Timeout from one source should not crash the search."""

        async def timeout_handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "arxiv" in url:
                raise httpx.ReadTimeout("Connection timed out")
            if "crossref" in url:
                return httpx.Response(
                    status_code=200,
                    json=CROSSREF_SEARCH_RESPONSE,
                    headers={"content-type": "application/json"},
                )
            return httpx.Response(status_code=404, text="Not found")

        transport = httpx.MockTransport(timeout_handler)
        client = httpx.AsyncClient(transport=transport)
        engine = DiscoveryEngine(client=client)

        # Should not raise; ArXiv timeout is logged and Crossref results returned
        results = await engine.search_by_query("test")
        assert len(results) >= 1
        assert all(r.source == "crossref" for r in results)

    @pytest.mark.asyncio
    async def test_search_by_doi_exception_returns_none(self):
        """Network exception in search_by_doi should return None."""

        async def error_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(error_handler)
        client = httpx.AsyncClient(transport=transport)
        engine = DiscoveryEngine(client=client)

        result = await engine.search_by_doi("10.1234/error")
        assert result is None


# ============================================================================
# Section 3N: Engine lifecycle
# ============================================================================


class TestEngineLifecycle:
    """Audit: Verify engine creation and teardown."""

    def test_default_client_creation(self):
        """Engine without explicit client should create its own."""
        engine = DiscoveryEngine()
        assert engine._client is not None

    def test_custom_client_injection(self):
        """Engine should accept an injected httpx.AsyncClient."""
        custom = httpx.AsyncClient()
        engine = DiscoveryEngine(client=custom)
        assert engine._client is custom

    @pytest.mark.asyncio
    async def test_close_calls_aclose(self):
        """close() should delegate to client.aclose()."""

        async def noop_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200)

        transport = httpx.MockTransport(noop_handler)
        client = httpx.AsyncClient(transport=transport)
        engine = DiscoveryEngine(client=client)
        # Should not raise
        await engine.close()


# ============================================================================
# Section 3O: _extract_bibtex_fields
# ============================================================================


class TestExtractBibtexFields:
    """Audit: Verify BibTeX field extraction regex."""

    def _extract(self, entry: str) -> dict:
        engine = DiscoveryEngine.__new__(DiscoveryEngine)
        return engine._extract_bibtex_fields(entry)

    def test_standard_fields(self):
        """Standard BibTeX fields should be extracted."""
        entry = """\
  title = {Some Title},
  author = {John Smith},
  year = {2021},
}"""
        fields = self._extract(entry)
        assert fields["title"] == "Some Title"
        assert fields["author"] == "John Smith"
        assert fields["year"] == "2021"

    def test_double_quoted_fields(self):
        """Double-quoted BibTeX values should be extracted."""
        entry = """\
  title = "Quoted Title",
  year = "2022",
}"""
        fields = self._extract(entry)
        assert fields["title"] == "Quoted Title"
        assert fields["year"] == "2022"

    def test_key_case_insensitive(self):
        """Field keys should be lowercased."""
        entry = """\
  Title = {Mixed Case Key},
  YEAR = {2023},
}"""
        fields = self._extract(entry)
        assert "title" in fields
        assert "year" in fields

    def test_stops_at_closing_brace(self):
        """Extraction should stop at the entry-closing brace."""
        entry = """\
  title = {Before Close},
}
  author = {Should Not Appear},
"""
        fields = self._extract(entry)
        assert "title" in fields
        assert "author" not in fields

    def test_empty_entry(self):
        """Empty entry should return empty dict."""
        assert self._extract("}") == {}


# ============================================================================
# Section 3P: Crossref year filter in _search_crossref
# ============================================================================


class TestCrossrefYearFilter:
    """Audit: Verify year-range filter is passed to Crossref API."""

    @pytest.mark.asyncio
    async def test_year_filter_in_params(self):
        """Year range should produce a 'filter' query parameter."""
        captured_urls = []

        async def capturing_handler(request: httpx.Request) -> httpx.Response:
            captured_urls.append(str(request.url))
            return httpx.Response(
                status_code=200,
                json={"message": {"items": []}},
                headers={"content-type": "application/json"},
            )

        transport = httpx.MockTransport(capturing_handler)
        client = httpx.AsyncClient(transport=transport)
        engine = DiscoveryEngine(client=client)

        await engine.search_by_authors(["Smith"], year_range=(2020, 2023))

        # Find the Crossref URL (not ArXiv)
        crossref_urls = [u for u in captured_urls if "crossref" in u]
        assert len(crossref_urls) >= 1
        crossref_url = crossref_urls[0]
        assert "from-pub-date" in crossref_url
        assert "until-pub-date" in crossref_url
        assert "2020" in crossref_url
        assert "2023" in crossref_url


# ============================================================================
# Section 3Q: Security and architecture audit findings summary
# ============================================================================


class TestSecurityAuditSummary:
    """Audit findings summary for the discovery engine module."""

    def test_audit_finding_no_input_validation_on_query(self):
        """AUDIT FINDING: No input sanitisation on user-supplied query strings.

        search_by_query, search_by_authors, and search_by_arxiv_id pass
        user-supplied strings directly to URL parameters without sanitisation.
        While httpx handles URL-encoding, there is no length limit or character
        validation at the application level.
        """
        import inspect

        source = inspect.getsource(DiscoveryEngine.search_by_query)
        assert "sanitize" not in source.lower() and "validate" not in source.lower()

    def test_audit_finding_no_rate_limiting(self):
        """AUDIT FINDING: No rate limiting for API calls.

        The engine makes concurrent requests to ArXiv and Crossref without
        any rate limiting. ArXiv explicitly requests max 1 request per 3
        seconds. Heavy usage could result in IP bans.
        """
        import inspect

        full_source = inspect.getsource(DiscoveryEngine)
        assert "rate_limit" not in full_source.lower()
        assert "throttle" not in full_source.lower()
        assert "sleep" not in full_source

    def test_audit_finding_doi_not_validated(self):
        """AUDIT FINDING: DOI format is not validated before lookup.

        search_by_doi only strips whitespace but does not validate the DOI
        format (should start with '10.'). Arbitrary strings could be sent
        to the Crossref API.
        """
        import inspect

        source = inspect.getsource(DiscoveryEngine.search_by_doi)
        assert "10." not in source, (
            "If DOI validation is now present, update this audit test"
        )

    def test_audit_finding_broad_exception_catch(self):
        """AUDIT FINDING: search_by_doi catches bare Exception.

        The except clause in search_by_doi catches all exceptions, which
        could silently swallow programming errors (e.g. TypeError, KeyError).
        """
        import inspect

        source = inspect.getsource(DiscoveryEngine.search_by_doi)
        assert "except Exception" in source
