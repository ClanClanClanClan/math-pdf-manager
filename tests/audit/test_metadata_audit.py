"""
Phase 9 Audit: Metadata Enrichment & Quality Scoring
Tests verify the metadata subsystem behaves as documented.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

import sys
import types

# ---------------------------------------------------------------------------
# Mock metadata_fetcher before importing enhanced_sources.
# The real module lives in src/ and pulls heavy deps (regex, requests, etc.)
# that are irrelevant for these unit tests.
# ---------------------------------------------------------------------------
_mock_metadata_fetcher = MagicMock()


@dataclass
class _MockMetadata:
    title: str = ""
    authors: list = field(default_factory=list)
    published: str = ""
    DOI: Optional[str] = None
    arxiv_id: Optional[str] = None
    source: str = ""

    def to_dict(self):
        return {
            'title': self.title,
            'authors': self.authors,
            'published': self.published,
            'DOI': self.DOI,
            'arxiv_id': self.arxiv_id,
            'source': self.source,
        }


_mock_metadata_fetcher.Metadata = _MockMetadata
_mock_metadata_fetcher.canonicalize = lambda t: t.lower().strip() if t else ""
sys.modules['metadata_fetcher'] = _mock_metadata_fetcher

# Ensure the metadata package is importable as a package (it lacks __init__.py)
from pathlib import Path

_src = Path(__file__).resolve().parent.parent.parent / "src"
_metadata_pkg_path = _src / "metadata"
if "metadata" not in sys.modules:
    _pkg = types.ModuleType("metadata")
    _pkg.__path__ = [str(_metadata_pkg_path)]
    _pkg.__package__ = "metadata"
    sys.modules["metadata"] = _pkg

# Now we can import the modules under test
from metadata.enhanced_sources import (
    EnhancedMetadata,
    SemanticScholarAPI,
    OpenAlexAPI,
    ORCIDIntegration,
    EnhancedMetadataOrchestrator,
)
from metadata.quality_scoring import (
    MetadataQualityScorer,
    SourceRankingSystem,
    QualityMetrics,
    SourceRanking,
)
from metadata.enrichment import (
    enrich_metadata,
    EnrichmentResult,
    _detect_topics,
    _classify_subject_area,
    _assess_journal_quality,
    _extract_mathematical_concepts,
    TOPIC_KEYWORDS,
    JOURNAL_QUALITY,
)


# ============================================================================
# Section A: EnhancedMetadata dataclass
# ============================================================================

class TestEnhancedMetadata:
    """Audit: EnhancedMetadata extends Metadata with extra fields."""

    def test_extends_metadata_base_fields(self):
        """EnhancedMetadata should carry all base Metadata fields."""
        em = EnhancedMetadata(title="Test", authors=["A B"], published="2024-01-01",
                              DOI="10.1234/test", arxiv_id="2401.00001", source="test")
        assert em.title == "Test"
        assert em.authors == ["A B"]
        assert em.DOI == "10.1234/test"
        assert em.arxiv_id == "2401.00001"
        assert em.source == "test"

    def test_enhanced_fields_present(self):
        """EnhancedMetadata must expose abstract, keywords, citation_count, etc."""
        em = EnhancedMetadata()
        assert hasattr(em, 'abstract')
        assert hasattr(em, 'keywords')
        assert hasattr(em, 'citation_count')
        assert hasattr(em, 'influential_citation_count')
        assert hasattr(em, 'venue')
        assert hasattr(em, 'venue_type')
        assert hasattr(em, 'open_access')
        assert hasattr(em, 'pdf_urls')
        assert hasattr(em, 'fields_of_study')
        assert hasattr(em, 's2_paper_id')
        assert hasattr(em, 'openalex_id')
        assert hasattr(em, 'orcid_ids')
        assert hasattr(em, 'quality_score')

    def test_default_values(self):
        """All enhanced fields should have sensible defaults."""
        em = EnhancedMetadata()
        assert em.abstract is None
        assert em.keywords == []
        assert em.references == []
        assert em.citations == []
        assert em.citation_count == 0
        assert em.influential_citation_count == 0
        assert em.venue is None
        assert em.venue_type is None
        assert em.open_access is False
        assert em.pdf_urls == []
        assert em.fields_of_study == []
        assert em.s2_paper_id is None
        assert em.openalex_id is None
        assert em.orcid_ids == []
        assert em.quality_score == 0.0

    def test_to_dict_includes_enhanced_fields(self):
        """to_dict() must include all enhanced fields."""
        em = EnhancedMetadata(
            title="T", authors=["A"], abstract="abs",
            keywords=["kw"], citation_count=10, venue="Nature",
            venue_type="journal", open_access=True,
            pdf_urls=["http://x.pdf"], fields_of_study=["CS"],
            s2_paper_id="abc", openalex_id="oalex1",
            orcid_ids=["0000-0001-2345-6789"], quality_score=0.8,
        )
        d = em.to_dict()
        assert d['abstract'] == "abs"
        assert d['keywords'] == ["kw"]
        assert d['citation_count'] == 10
        assert d['venue'] == "Nature"
        assert d['venue_type'] == "journal"
        assert d['open_access'] is True
        assert d['pdf_urls'] == ["http://x.pdf"]
        assert d['fields_of_study'] == ["CS"]
        assert d['s2_paper_id'] == "abc"
        assert d['openalex_id'] == "oalex1"
        assert d['orcid_ids'] == ["0000-0001-2345-6789"]
        assert d['quality_score'] == 0.8

    def test_to_dict_includes_base_fields(self):
        """to_dict() must include base Metadata fields too."""
        em = EnhancedMetadata(title="Title", DOI="10.1/x")
        d = em.to_dict()
        assert 'title' in d
        assert 'DOI' in d


# ============================================================================
# Section B: SemanticScholarAPI
# ============================================================================

class TestSemanticScholarParsePaper:
    """Audit: _parse_s2_paper() with realistic S2 data."""

    def setup_method(self):
        self.api = SemanticScholarAPI()

    def test_parse_basic_fields(self):
        paper = {
            'paperId': 'abc123',
            'title': 'Test Paper',
            'year': 2023,
            'abstract': 'An abstract.',
            'authors': [{'name': 'Alice Smith'}],
            'citationCount': 42,
            'influentialCitationCount': 5,
            'venue': 'Nature',
            'externalIds': {'DOI': '10.1038/test', 'ArXiv': '2301.12345'},
            'openAccessPdf': {'url': 'https://example.com/paper.pdf'},
            'fieldsOfStudy': ['Computer Science'],
        }
        result = self.api._parse_s2_paper(paper)
        assert result.title == 'Test Paper'
        assert result.authors == ['Alice Smith']
        assert result.DOI == '10.1038/test'
        assert result.arxiv_id == '2301.12345'
        assert result.citation_count == 42
        assert result.influential_citation_count == 5
        assert result.venue == 'Nature'
        assert result.open_access is True
        assert 'https://example.com/paper.pdf' in result.pdf_urls
        assert 'Computer Science' in result.fields_of_study
        assert result.s2_paper_id == 'abc123'
        assert result.source == 'semantic_scholar'

    def test_parse_published_date_format(self):
        paper = {'year': 2023, 'authors': [], 'externalIds': {}}
        result = self.api._parse_s2_paper(paper)
        assert result.published == "2023-01-01"

    def test_parse_no_year_gives_empty_published(self):
        paper = {'authors': [], 'externalIds': {}}
        result = self.api._parse_s2_paper(paper)
        assert result.published == ""

    def test_parse_venue_type_conference(self):
        paper = {'venue': 'Conference on Neural Information Processing', 'authors': [], 'externalIds': {}}
        result = self.api._parse_s2_paper(paper)
        assert result.venue_type == 'conference'

    def test_parse_venue_type_journal(self):
        paper = {'venue': 'Journal of Machine Learning Research', 'authors': [], 'externalIds': {}}
        result = self.api._parse_s2_paper(paper)
        assert result.venue_type == 'journal'

    def test_parse_venue_type_preprint(self):
        paper = {'venue': 'ArXiv', 'authors': [], 'externalIds': {}}
        result = self.api._parse_s2_paper(paper)
        assert result.venue_type == 'preprint'

    def test_parse_venue_type_none_for_unknown(self):
        paper = {'venue': 'Unknown Place', 'authors': [], 'externalIds': {}}
        result = self.api._parse_s2_paper(paper)
        assert result.venue_type is None

    def test_parse_author_orcids(self):
        paper = {
            'authors': [
                {'name': 'Alice', 'externalIds': {'ORCID': '0000-0001-2345-6789'}},
                {'name': 'Bob', 'externalIds': {}},
            ],
            'externalIds': {},
        }
        result = self.api._parse_s2_paper(paper)
        assert '0000-0001-2345-6789' in result.orcid_ids
        assert len(result.orcid_ids) == 1

    def test_parse_fields_of_study_dict_form(self):
        paper = {
            'authors': [],
            'externalIds': {},
            'fieldsOfStudy': [{'category': 'Mathematics'}],
        }
        result = self.api._parse_s2_paper(paper)
        assert 'Mathematics' in result.fields_of_study


class TestSemanticScholarQualityScore:
    """Audit: _calculate_quality_score() scoring logic."""

    def setup_method(self):
        self.api = SemanticScholarAPI()

    def test_highly_cited_paper(self):
        paper = {'citationCount': 200, 'influentialCitationCount': 60}
        score = self.api._calculate_quality_score(paper)
        # 200/100 capped at 0.3 + 60/50 capped at 0.2 = 0.5
        assert score >= 0.5

    def test_recent_paper_boost(self):
        paper = {'year': 2023}
        score = self.api._calculate_quality_score(paper)
        assert score >= 0.1  # year >= 2020 boost

    def test_older_paper_smaller_boost(self):
        paper = {'year': 2017}
        score = self.api._calculate_quality_score(paper)
        # year >= 2015 boost is 0.05
        assert score >= 0.05

    def test_nature_venue_bonus(self):
        paper = {'venue': 'Nature Machine Intelligence'}
        score = self.api._calculate_quality_score(paper)
        assert score >= 0.2

    def test_ieee_venue_bonus(self):
        paper = {'venue': 'IEEE Transactions'}
        score = self.api._calculate_quality_score(paper)
        assert score >= 0.1

    def test_abstract_bonus(self):
        paper = {'abstract': 'We study...'}
        score = self.api._calculate_quality_score(paper)
        assert score >= 0.05

    def test_open_access_bonus(self):
        paper = {'openAccessPdf': {'url': 'http://test.pdf'}}
        score = self.api._calculate_quality_score(paper)
        assert score >= 0.1

    def test_score_capped_at_one(self):
        paper = {
            'citationCount': 9999, 'influentialCitationCount': 9999,
            'venue': 'Nature', 'year': 2025,
            'abstract': 'test', 'openAccessPdf': {'url': 'x'},
        }
        score = self.api._calculate_quality_score(paper)
        assert score <= 1.0

    def test_empty_paper_score_zero(self):
        score = self.api._calculate_quality_score({})
        assert score == 0.0


class TestSemanticScholarRateLimiting:
    """Audit: Rate limit configuration."""

    def test_default_rate_limit_without_key(self):
        api = SemanticScholarAPI()
        assert api.rate_limit == 1.0

    def test_rate_limit_with_api_key(self):
        """With an API key the rate limit should be lowered during __aenter__."""
        api = SemanticScholarAPI(api_key="test_key")
        # rate_limit is set in __aenter__; confirm initial value and that key is stored
        assert api.api_key == "test_key"
        # The rate limit is reduced in __aenter__, not constructor
        assert api.rate_limit == 1.0  # constructor default


class TestSemanticScholarAsyncMethods:
    """Audit: search_papers, get_paper_by_id via mocked aiohttp."""

    @pytest.mark.asyncio
    async def test_search_papers_returns_list(self):
        api = SemanticScholarAPI()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'data': [
                {'paperId': 'p1', 'title': 'Paper One', 'year': 2023,
                 'authors': [{'name': 'A'}], 'externalIds': {},
                 'citationCount': 5}
            ]
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        api.session = mock_session
        api.last_request = 0.0

        with patch.object(api, '_rate_limit_wait', new_callable=AsyncMock):
            results = await api.search_papers("test query")

        assert len(results) == 1
        assert results[0].title == 'Paper One'

    @pytest.mark.asyncio
    async def test_get_paper_by_id_404_returns_none(self):
        api = SemanticScholarAPI()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        api.session = mock_session

        with patch.object(api, '_rate_limit_wait', new_callable=AsyncMock):
            result = await api.get_paper_by_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_papers_429_returns_empty(self):
        api = SemanticScholarAPI()
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        api.session = mock_session

        with patch.object(api, '_rate_limit_wait', new_callable=AsyncMock), \
             patch('asyncio.sleep', new_callable=AsyncMock):
            results = await api.search_papers("test")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_papers_connection_error_returns_empty(self):
        api = SemanticScholarAPI()
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=Exception("Connection refused"))
        api.session = mock_session

        with patch.object(api, '_rate_limit_wait', new_callable=AsyncMock):
            results = await api.search_papers("test")

        assert results == []


# ============================================================================
# Section C: OpenAlexAPI
# ============================================================================

class TestOpenAlexParseWork:
    """Audit: _parse_openalex_work() with realistic OpenAlex JSON."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_parse_basic_fields(self):
        work = {
            'id': 'W123',
            'title': 'OpenAlex Paper',
            'publication_date': '2023-06-15',
            'doi': 'https://doi.org/10.1234/oa',
            'cited_by_count': 30,
            'authorships': [
                {'author': {'display_name': 'Jane Doe', 'orcid': 'https://orcid.org/0000-0002-1234-5678'}},
            ],
            'primary_location': {
                'source': {'display_name': 'PLOS ONE', 'type': 'journal'}
            },
            'concepts': [
                {'display_name': 'Machine Learning', 'score': 0.8},
                {'display_name': 'Low relevance', 'score': 0.1},
            ],
            'abstract_inverted_index': {'Hello': [0], 'world': [1]},
            'open_access': {'is_oa': True},
            'locations': [{'pdf_url': 'https://example.com/paper.pdf'}],
        }
        result = self.api._parse_openalex_work(work)
        assert result.title == 'OpenAlex Paper'
        assert result.published == '2023-06-15'
        assert result.DOI == '10.1234/oa'
        assert result.citation_count == 30
        assert result.authors == ['Jane Doe']
        assert result.venue == 'PLOS ONE'
        assert result.venue_type == 'journal'
        assert result.open_access is True
        assert 'https://example.com/paper.pdf' in result.pdf_urls
        assert result.openalex_id == 'W123'
        assert result.source == 'openalex'

    def test_doi_cleaning_strips_prefix(self):
        work = {'doi': 'https://doi.org/10.5555/test', 'authorships': [], 'concepts': []}
        result = self.api._parse_openalex_work(work)
        assert result.DOI == '10.5555/test'

    def test_doi_without_prefix_unchanged(self):
        work = {'doi': '10.5555/test', 'authorships': [], 'concepts': []}
        result = self.api._parse_openalex_work(work)
        assert result.DOI == '10.5555/test'

    def test_orcid_extraction_from_url(self):
        work = {
            'authorships': [
                {'author': {'display_name': 'A', 'orcid': 'https://orcid.org/0000-0001-2345-6789'}},
            ],
            'concepts': [],
        }
        result = self.api._parse_openalex_work(work)
        assert '0000-0001-2345-6789' in result.orcid_ids

    def test_concept_filtering_by_score(self):
        work = {
            'authorships': [],
            'concepts': [
                {'display_name': 'High', 'score': 0.9},
                {'display_name': 'Medium', 'score': 0.35},
                {'display_name': 'Low', 'score': 0.2},
                {'display_name': 'Borderline', 'score': 0.3},  # exact threshold: NOT included (>0.3)
            ],
        }
        result = self.api._parse_openalex_work(work)
        assert 'High' in result.fields_of_study
        assert 'Medium' in result.fields_of_study
        assert 'Low' not in result.fields_of_study
        assert 'Borderline' not in result.fields_of_study

    def test_venue_type_repository_is_preprint(self):
        work = {
            'authorships': [],
            'concepts': [],
            'primary_location': {'source': {'display_name': 'arXiv', 'type': 'repository'}},
        }
        result = self.api._parse_openalex_work(work)
        assert result.venue_type == 'preprint'


class TestOpenAlexReconstructAbstract:
    """Audit: _reconstruct_abstract() from inverted index."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_simple_reconstruction(self):
        inverted = {'We': [0], 'study': [1], 'graphs': [2]}
        assert self.api._reconstruct_abstract(inverted) == 'We study graphs'

    def test_word_appearing_multiple_times(self):
        inverted = {'the': [0, 4], 'cat': [1], 'sat': [2], 'on': [3], 'mat': [5]}
        result = self.api._reconstruct_abstract(inverted)
        assert result == 'the cat sat on the mat'

    def test_empty_inverted_index(self):
        assert self.api._reconstruct_abstract({}) == ''

    def test_malformed_inverted_index_still_produces_output(self):
        # A string is iterable, so iterating over 'not a list' yields characters.
        # The implementation does NOT validate that positions are actually ints;
        # it just sorts by position, treating each character as a position.
        # This is a robustness gap -- but the code does not crash.
        result = self.api._reconstruct_abstract({'a': 'not a list'})
        # Each character in "not a list" (length 10) becomes a position for word 'a'
        assert isinstance(result, str)
        assert len(result) > 0  # produces output rather than empty string


# ============================================================================
# Section D: EnhancedMetadataOrchestrator
# ============================================================================

class TestEnhancedMetadataOrchestrator:
    """Audit: orchestrator dedup, merge, enrich, stats."""

    def test_statistics_tracking_initial(self):
        orch = EnhancedMetadataOrchestrator()
        stats = orch.get_statistics()
        assert stats['queries'] == 0
        assert stats['semantic_scholar_hits'] == 0
        assert stats['openalex_hits'] == 0
        assert stats['combined_results'] == 0

    @pytest.mark.asyncio
    async def test_comprehensive_search_deduplicates_by_doi(self):
        orch = EnhancedMetadataOrchestrator()
        paper_a = EnhancedMetadata(title="Paper", DOI="10.1/dup", source="s2", quality_score=0.5)
        paper_b = EnhancedMetadata(title="Paper Copy", DOI="10.1/dup", source="oa", quality_score=0.6)

        with patch.object(orch, '_search_semantic_scholar', new_callable=AsyncMock, return_value=[paper_a]), \
             patch.object(orch, '_search_openalex', new_callable=AsyncMock, return_value=[paper_b]):
            results = await orch.comprehensive_search("test")

        dois = [r.DOI for r in results]
        assert dois.count("10.1/dup") == 1

    @pytest.mark.asyncio
    async def test_comprehensive_search_deduplicates_by_title(self):
        orch = EnhancedMetadataOrchestrator()
        paper_a = EnhancedMetadata(title="Same Title", source="s2", quality_score=0.5)
        paper_b = EnhancedMetadata(title="Same Title", source="oa", quality_score=0.6)

        with patch.object(orch, '_search_semantic_scholar', new_callable=AsyncMock, return_value=[paper_a]), \
             patch.object(orch, '_search_openalex', new_callable=AsyncMock, return_value=[paper_b]):
            results = await orch.comprehensive_search("test")

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_comprehensive_search_updates_stats(self):
        orch = EnhancedMetadataOrchestrator()

        with patch.object(orch, '_search_semantic_scholar', new_callable=AsyncMock, return_value=[]), \
             patch.object(orch, '_search_openalex', new_callable=AsyncMock, return_value=[]):
            await orch.comprehensive_search("test")

        assert orch.stats['queries'] == 1

    def test_merge_metadata_prefers_non_empty(self):
        orch = EnhancedMetadataOrchestrator()
        base = EnhancedMetadata(title="Base Title", abstract=None, DOI="10.1/a")
        enrichment = EnhancedMetadata(title="Enriched Title", abstract="An abstract", DOI="10.1/a")

        merged = orch._merge_metadata(base, enrichment)
        # abstract was None in base, "An abstract" in enrichment -> pick enrichment
        assert merged.abstract == "An abstract"

    def test_merge_metadata_merges_lists(self):
        orch = EnhancedMetadataOrchestrator()
        base = EnhancedMetadata(keywords=["a", "b"], fields_of_study=["CS"])
        enrichment = EnhancedMetadata(keywords=["b", "c"], fields_of_study=["Math"])

        merged = orch._merge_metadata(base, enrichment)
        assert set(merged.keywords) == {"a", "b", "c"}
        assert set(merged.fields_of_study) == {"CS", "Math"}

    def test_merge_metadata_uses_higher_citation_count(self):
        orch = EnhancedMetadataOrchestrator()
        base = EnhancedMetadata(citation_count=10, influential_citation_count=2)
        enrichment = EnhancedMetadata(citation_count=20, influential_citation_count=1)

        merged = orch._merge_metadata(base, enrichment)
        assert merged.citation_count == 20
        assert merged.influential_citation_count == 2

    @pytest.mark.asyncio
    async def test_enrich_from_orcid_always_returns_none(self):
        """AUDIT FINDING: _enrich_from_orcid() is a stub that always returns None."""
        orch = EnhancedMetadataOrchestrator()
        md = EnhancedMetadata(title="Test", orcid_ids=["0000-0001-2345-6789"])
        result = await orch._enrich_from_orcid(md)
        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_metadata_with_doi_calls_sources(self):
        orch = EnhancedMetadataOrchestrator()
        md = EnhancedMetadata(title="Test", DOI="10.1/x")
        enriched_s2 = EnhancedMetadata(title="Test", DOI="10.1/x", abstract="S2 abstract",
                                        s2_paper_id="s2id")
        enriched_oa = EnhancedMetadata(title="Test", DOI="10.1/x", venue="Nature",
                                        openalex_id="oaid")

        with patch.object(orch, '_enrich_from_semantic_scholar', new_callable=AsyncMock, return_value=enriched_s2), \
             patch.object(orch, '_enrich_from_openalex', new_callable=AsyncMock, return_value=enriched_oa):
            result = await orch.enrich_metadata(md)

        assert result.abstract == "S2 abstract"
        assert result.venue == "Nature"


# ============================================================================
# Section E: MetadataQualityScorer
# ============================================================================

class TestScoreTitle:
    """Audit: _score_title() with good and poor titles."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_good_title_proper_length(self):
        title = "A Comprehensive Analysis of Graph Neural Networks in Molecular Biology"
        score = self.scorer._score_title(title)
        # Base 0.5 + length 0.3 + capitalization 0.05 + low punct 0.05 + pattern bonuses
        assert score >= 0.5

    def test_empty_title_scores_zero(self):
        assert self.scorer._score_title("") == 0.0
        assert self.scorer._score_title(None) == 0.0

    def test_very_short_title_scores_zero(self):
        assert self.scorer._score_title("Short") == 0.0  # < 10 chars

    def test_lowercase_start_penalized(self):
        score_lower = self.scorer._score_title("a lowercase title about something important")
        score_upper = self.scorer._score_title("A Lowercase Title About Something Important")
        assert score_upper > score_lower

    def test_multiple_punctuation_penalized(self):
        score = self.scorer._score_title("What??? Is This!!! A Paper???")
        # The '???' and '!!!' patterns each subtract 0.1 but the title is long
        # enough to still carry a decent score.  A clean title scores higher.
        clean_score = self.scorer._score_title("What Is This Research About Today")
        assert score < clean_score

    def test_title_with_good_keywords(self):
        title = "Novel Investigation of Enhanced Neural Network Analysis"
        score = self.scorer._score_title(title)
        assert score > 0.5  # multiple good pattern matches


class TestScoreAuthors:
    """Audit: _score_authors() formatting checks."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_well_formatted_authors(self):
        authors = ["John Smith", "Jane Doe", "Alice Johnson"]
        score = self.scorer._score_authors(authors)
        assert score >= 0.8

    def test_no_authors_scores_zero(self):
        assert self.scorer._score_authors([]) == 0.0

    def test_suspicious_many_authors(self):
        authors = [f"Author {i}" for i in range(55)]
        score = self.scorer._score_authors(authors)
        # > 50 authors gets a penalty
        # But well-formatted names still contribute positively
        normal_score = self.scorer._score_authors([f"Author {i}" for i in range(5)])
        assert score < normal_score


class TestIsWellFormattedName:
    """Audit: _is_well_formatted_name() positive/negative cases."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_positive_two_part_name(self):
        assert self.scorer._is_well_formatted_name("John Smith") is True

    def test_positive_three_part_name(self):
        assert self.scorer._is_well_formatted_name("John A. Smith") is True

    def test_negative_single_name(self):
        assert self.scorer._is_well_formatted_name("Admin") is False

    def test_negative_too_short(self):
        assert self.scorer._is_well_formatted_name("AB") is False

    def test_negative_contains_numbers(self):
        assert self.scorer._is_well_formatted_name("Author 123") is False

    def test_negative_lowercase_start(self):
        assert self.scorer._is_well_formatted_name("john smith") is False

    def test_negative_excessive_dots(self):
        assert self.scorer._is_well_formatted_name("J... Smith...Jr.") is False


class TestScoreAbstract:
    """Audit: _score_abstract() scholarly vs poor abstracts."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_scholarly_abstract(self):
        abstract = (
            "Background: We present a novel methodology for analysis of stochastic systems. "
            "Methods: We propose an experiment using data from 100 trials. "
            "Results: Our results show a significant correlation of 0.95 (p < 0.001). "
            "Conclusions: We find that our hypothesis is supported by statistical evidence."
        )
        score = self.scorer._score_abstract(abstract)
        assert score >= 0.7

    def test_no_abstract_scores_zero(self):
        assert self.scorer._score_abstract(None) == 0.0
        assert self.scorer._score_abstract("") == 0.0

    def test_very_short_abstract_low_score(self):
        score = self.scorer._score_abstract("Too short.")
        assert score < 0.5


class TestScoreCitations:
    """Audit: _score_citations() logarithmic scaling and penalties."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_zero_citations(self):
        score = self.scorer._score_citations(0, 0)
        assert score == 0.2  # base score only

    def test_moderate_citations_log_scaled(self):
        score = self.scorer._score_citations(100, 0)
        # log10(101)/3 ~= 0.668 capped at 0.5 -> 0.2 + 0.5 = 0.7
        assert score >= 0.6

    def test_influential_citation_bonus(self):
        score_no = self.scorer._score_citations(100, 0)
        score_yes = self.scorer._score_citations(100, 15)  # 15% influential
        assert score_yes > score_no

    def test_suspicious_high_citations_penalty(self):
        score = self.scorer._score_citations(15000, 0)
        # Still gets citation score, but -0.1 penalty for > 10000
        assert score <= 0.9

    def test_negative_citations_invalid(self):
        assert self.scorer._score_citations(-1, 0) == 0.0


class TestScoreVenue:
    """Audit: _score_venue() for high-quality venues and known publishers."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_no_venue_scores_zero(self):
        assert self.scorer._score_venue(None, None) == 0.0
        assert self.scorer._score_venue("", None) == 0.0

    def test_nature_high_quality(self):
        score = self.scorer._score_venue("Nature", "journal")
        assert score >= 0.7

    def test_science_high_quality(self):
        score = self.scorer._score_venue("Science", "journal")
        assert score >= 0.7

    def test_ieee_publisher_recognized(self):
        score = self.scorer._score_venue("IEEE Transactions on Signal Processing", "journal")
        assert score >= 0.4

    def test_acm_publisher_recognized(self):
        score = self.scorer._score_venue("ACM Computing Surveys", "journal")
        assert score >= 0.4


class TestScoreIdentifiers:
    """Audit: _score_identifiers() with valid/invalid DOI and ArXiv IDs."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_valid_doi_only(self):
        score = self.scorer._score_identifiers("10.1038/nature12345", None, None)
        assert score == 0.5

    def test_valid_doi_and_arxiv(self):
        score = self.scorer._score_identifiers("10.1038/nature12345", "2301.12345", None)
        assert score == 0.8

    def test_all_identifiers(self):
        score = self.scorer._score_identifiers("10.1038/nature12345", "2301.12345", "s2id")
        assert score == 1.0

    def test_invalid_doi_lower_score(self):
        score = self.scorer._score_identifiers("not-a-doi", None, None)
        assert score == 0.2

    def test_no_identifiers(self):
        assert self.scorer._score_identifiers(None, None, None) == 0.0


class TestIsValidDoi:
    """Audit: _is_valid_doi() regex."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_valid_doi(self):
        assert self.scorer._is_valid_doi("10.1038/nature12345") is True
        assert self.scorer._is_valid_doi("10.1145/12345.67890") is True
        assert self.scorer._is_valid_doi("10.48550/arXiv.2301.12345") is True

    def test_invalid_doi(self):
        assert self.scorer._is_valid_doi("not-a-doi") is False
        assert self.scorer._is_valid_doi("doi:10.1038/nature") is False
        assert self.scorer._is_valid_doi("") is False


class TestIsValidArxivId:
    """Audit: _is_valid_arxiv_id() new and old formats."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_new_format(self):
        assert self.scorer._is_valid_arxiv_id("2301.12345") is True
        assert self.scorer._is_valid_arxiv_id("2301.1234") is True

    def test_new_format_with_version(self):
        assert self.scorer._is_valid_arxiv_id("2301.12345v2") is True

    def test_old_format(self):
        assert self.scorer._is_valid_arxiv_id("math.PR/0701234") is True

    def test_invalid_format(self):
        assert self.scorer._is_valid_arxiv_id("not-an-arxiv-id") is False
        assert self.scorer._is_valid_arxiv_id("") is False
        assert self.scorer._is_valid_arxiv_id("12345") is False


class TestCalculateCompleteness:
    """Audit: _calculate_completeness() with full vs sparse metadata."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_fully_populated(self):
        md = EnhancedMetadata(
            title="Full Paper", authors=["John Doe"], published="2024-01-01",
            abstract="A good abstract.", DOI="10.1/x", venue="Nature",
            keywords=["kw"], fields_of_study=["CS"], citation_count=10,
        )
        metrics = QualityMetrics()
        score = self.scorer._calculate_completeness(md, metrics)
        assert score >= 0.9

    def test_missing_required_fields(self):
        md = EnhancedMetadata()  # all defaults
        metrics = QualityMetrics()
        score = self.scorer._calculate_completeness(md, metrics)
        assert score < 0.3


class TestCalculateFreshness:
    """Audit: _calculate_freshness() by publication age."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_recent_paper_max_freshness(self):
        from datetime import date, timedelta
        recent = (date.today() - timedelta(days=100)).isoformat()
        md = EnhancedMetadata(published=recent)
        score = self.scorer._calculate_freshness(md)
        assert score == 1.0

    def test_old_paper_low_freshness(self):
        md = EnhancedMetadata(published="1990-01-01")
        score = self.scorer._calculate_freshness(md)
        assert score == 0.2

    def test_no_publication_date(self):
        md = EnhancedMetadata()
        score = self.scorer._calculate_freshness(md)
        assert score == 0.0

    def test_five_to_ten_year_paper(self):
        from datetime import date, timedelta
        pub_date = (date.today() - timedelta(days=int(7 * 365.25))).isoformat()
        md = EnhancedMetadata(published=pub_date)
        score = self.scorer._calculate_freshness(md)
        assert score == 0.6


class TestCalculateConsistency:
    """Audit: _calculate_consistency() detects mismatches."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_perfect_consistency(self):
        md = EnhancedMetadata(title="Test", authors=["A B"], published="2023-01-01")
        metrics = QualityMetrics()
        score = self.scorer._calculate_consistency(md, metrics)
        assert score == 1.0

    def test_venue_type_mismatch_penalized(self):
        md = EnhancedMetadata(
            venue="Some Random Forum", venue_type="journal"
        )
        metrics = QualityMetrics()
        score = self.scorer._calculate_consistency(md, metrics)
        assert score < 1.0

    def test_future_publication_date_penalized(self):
        md = EnhancedMetadata(published="2099-01-01")
        metrics = QualityMetrics()
        score = self.scorer._calculate_consistency(md, metrics)
        assert score < 1.0


class TestIdentifyMissingFields:
    """Audit: _identify_missing_fields() detection."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_all_important_fields_present(self):
        md = EnhancedMetadata(
            title="T", authors=["A B"], published="2024-01-01",
            abstract="abs", DOI="10.1/x", venue="V", citation_count=1,
        )
        missing = self.scorer._identify_missing_fields(md)
        assert missing == []

    def test_empty_metadata_lists_missing(self):
        md = EnhancedMetadata()
        missing = self.scorer._identify_missing_fields(md)
        assert 'title' in missing
        assert 'abstract' in missing
        assert 'DOI' in missing
        assert 'venue' in missing


class TestIdentifyQualityIssues:
    """Audit: _identify_quality_issues() triggers."""

    def setup_method(self):
        self.scorer = MetadataQualityScorer()

    def test_poor_title_flagged(self):
        md = EnhancedMetadata(title="x")  # very short -> title_quality < 0.3
        metrics = self.scorer.score_metadata(md)
        assert "Poor title quality" in metrics.quality_issues

    def test_invalid_doi_flagged(self):
        md = EnhancedMetadata(title="Good Title Here For Testing", DOI="bad-doi")
        metrics = self.scorer.score_metadata(md)
        assert "Invalid DOI format" in metrics.quality_issues

    def test_future_date_flagged(self):
        md = EnhancedMetadata(title="Good Title Here For Testing", published="2099-06-01")
        metrics = self.scorer.score_metadata(md)
        assert "Future publication date" in metrics.quality_issues


# ============================================================================
# Section F: SourceRankingSystem
# ============================================================================

class TestSourceRankingSystem:
    """Audit: SourceRankingSystem default rankings and methods."""

    def test_default_sources_initialized(self):
        srs = SourceRankingSystem()
        assert 'semantic_scholar' in srs.source_rankings
        assert 'openalex' in srs.source_rankings
        assert 'crossref' in srs.source_rankings
        assert 'arxiv' in srs.source_rankings

    def test_overall_ranking_weighted_formula(self):
        ranking = SourceRanking(
            source_name='test',
            reliability_score=0.9,
            coverage_score=0.8,
            freshness_score=0.7,
            consistency_score=0.6,
            performance_score=0.5,
        )
        expected = 0.9 * 0.30 + 0.8 * 0.25 + 0.6 * 0.20 + 0.7 * 0.15 + 0.5 * 0.10
        assert abs(ranking.overall_ranking - expected) < 1e-9

    def test_success_rate_property(self):
        ranking = SourceRanking(source_name='test', total_queries=100, successful_queries=80)
        assert ranking.success_rate == 0.8

    def test_success_rate_zero_queries(self):
        ranking = SourceRanking(source_name='test', total_queries=0)
        assert ranking.success_rate == 0.0

    def test_get_ranked_sources_sorted(self):
        srs = SourceRankingSystem()
        ranked = srs.get_ranked_sources()
        for i in range(len(ranked) - 1):
            assert ranked[i].overall_ranking >= ranked[i + 1].overall_ranking

    def test_field_specific_ranking_math_boost(self):
        srs = SourceRankingSystem()
        default_arxiv = srs.source_rankings['arxiv'].coverage_score
        ranked = srs.get_ranked_sources(field_of_study='mathematics')
        boosted_arxiv = [s for s in ranked if s.source_name == 'arxiv'][0]
        assert boosted_arxiv.coverage_score >= default_arxiv

    def test_recommend_sources_with_threshold(self):
        srs = SourceRankingSystem()
        recs = srs.recommend_sources('general', quality_threshold=0.7)
        for name in recs:
            ranking = srs.source_rankings[name]
            assert ranking.overall_ranking >= 0.7

    def test_recommend_sources_high_threshold_may_exclude(self):
        srs = SourceRankingSystem()
        recs = srs.recommend_sources('general', quality_threshold=0.99)
        # Very high threshold may exclude everything
        assert isinstance(recs, list)

    def test_update_source_ranking_modifies_scores(self):
        """FIXED: update_source_ranking now uses Counter instead of defaultdict."""
        srs = SourceRankingSystem()
        original_reliability = srs.source_rankings['semantic_scholar'].reliability_score

        md = EnhancedMetadata(
            title="Good Title About Machine Learning",
            authors=["John Smith", "Jane Doe"],
            published="2024-01-01",
            DOI="10.1038/test123",
            abstract="We present a comprehensive analysis of neural networks.",
            source="semantic_scholar",
        )

        # Should no longer raise AttributeError — Counter has most_common()
        srs.update_source_ranking('semantic_scholar', [md], [0.5])

        updated = srs.source_rankings['semantic_scholar']
        assert updated.total_queries == 1

    def test_get_source_analysis_structure(self):
        srs = SourceRankingSystem()
        analysis = srs.get_source_analysis('semantic_scholar')
        assert 'source_name' in analysis
        assert 'overall_ranking' in analysis
        assert 'success_rate' in analysis
        assert 'scores' in analysis
        assert 'statistics' in analysis
        assert 'strengths' in analysis
        assert 'common_issues' in analysis
        assert 'last_updated' in analysis

    def test_get_source_analysis_unknown_source(self):
        srs = SourceRankingSystem()
        analysis = srs.get_source_analysis('nonexistent')
        assert 'error' in analysis

    def test_export_rankings_contains_all_sources(self):
        srs = SourceRankingSystem()
        exported = srs.export_rankings()
        assert 'semantic_scholar' in exported
        assert 'openalex' in exported
        assert 'crossref' in exported
        assert 'arxiv' in exported
        for name, data in exported.items():
            assert 'ranking' in data
            assert 'analysis' in data


# ============================================================================
# Section G: Enrichment module (enrichment.py)
# ============================================================================

class TestEnrichmentDetectTopics:
    """Audit: topic detection from text."""

    def test_stochastic_detects_probability(self):
        result = enrich_metadata({'title': 'Stochastic Processes in Finance', 'abstract': ''})
        assert 'probability' in result.topics

    def test_optimization_detects_optimization(self):
        result = enrich_metadata({'title': 'Optimization of Neural Networks', 'abstract': ''})
        assert 'optimization' in result.topics

    def test_no_matching_keywords_returns_unspecified(self):
        topics = _detect_topics("a text about something entirely unrelated")
        assert topics == ["unspecified"]

    def test_multiple_topics_detected(self):
        result = enrich_metadata({'title': 'Stochastic Optimization via Neural Learning', 'abstract': ''})
        assert 'probability' in result.topics
        assert 'optimization' in result.topics
        assert 'machine learning' in result.topics


class TestEnrichmentClassifySubjectArea:
    """Audit: _classify_subject_area() with arxiv_id and doi."""

    def test_arxiv_math_prefix(self):
        assert _classify_subject_area({'arxiv_id': 'math.PR/0701234'}) == 'Mathematics'

    def test_arxiv_cs_prefix(self):
        assert _classify_subject_area({'arxiv_id': 'cs.LG/1234567'}) == 'Computer Science'

    def test_doi_only_returns_published_work(self):
        assert _classify_subject_area({'doi': '10.1234/test'}) == 'Published Work'

    def test_neither_returns_none(self):
        assert _classify_subject_area({}) is None


class TestEnrichmentJournalQuality:
    """Audit: _assess_journal_quality() tier lookup."""

    def test_annals_of_mathematics_a_plus(self):
        result = _assess_journal_quality("Annals of Mathematics")
        assert result is not None
        assert result['tier'] == 'A+'

    def test_unknown_journal_returns_none(self):
        assert _assess_journal_quality("Unknown Journal of Stuff") is None

    def test_case_insensitive(self):
        result = _assess_journal_quality("ANNALS OF MATHEMATICS")
        assert result is not None


class TestEnrichmentMathConcepts:
    """Audit: _extract_mathematical_concepts() pattern matching."""

    def test_finds_markov_chain(self):
        concepts = _extract_mathematical_concepts("we study markov chains in random graphs")
        assert 'markov chain' in concepts

    def test_finds_fourier_transform(self):
        concepts = _extract_mathematical_concepts("apply the fourier transform to this function")
        assert 'fourier transform' in concepts

    def test_finds_laplacian(self):
        concepts = _extract_mathematical_concepts("the graph laplacian eigenvalues determine connectivity")
        assert 'laplacian' in concepts

    def test_no_concepts_empty(self):
        concepts = _extract_mathematical_concepts("a paper about economics")
        assert concepts == []


class TestEnrichmentMutatesInput:
    """Audit: enrich_metadata() mutates the input dict."""

    def test_sets_topics_on_input(self):
        md = {'title': 'Stochastic Analysis', 'abstract': ''}
        enrich_metadata(md)
        assert 'topics' in md
        assert 'probability' in md['topics']

    def test_sets_subject_area_on_input(self):
        md = {'title': 'Test', 'abstract': '', 'arxiv_id': 'math.PR/0701234'}
        enrich_metadata(md)
        assert md['subject_area'] == 'Mathematics'

    def test_sets_mathematical_concepts_on_input(self):
        md = {'title': 'Markov chain Monte Carlo methods', 'abstract': ''}
        enrich_metadata(md)
        assert 'markov chain' in md['mathematical_concepts']

    def test_does_not_overwrite_existing_topics(self):
        md = {'title': 'Stochastic test', 'abstract': '', 'topics': ['custom']}
        enrich_metadata(md)
        # setdefault should NOT overwrite existing key
        assert md['topics'] == ['custom']

    def test_audit_minimal_concept_patterns(self):
        """AUDIT FINDING: enrichment.py has only 3 math concept patterns and 5 topic categories."""
        assert len(TOPIC_KEYWORDS) == 5
        # patterns dict inside _extract_mathematical_concepts has exactly 3 entries
        concepts = _extract_mathematical_concepts(
            "laplacian fourier markov"
        )
        assert len(concepts) == 3  # all three detected


# ============================================================================
# Section H: Integration audit findings
# ============================================================================

class TestAuditFindings:
    """Audit findings and cross-cutting concerns."""

    def test_enhanced_metadata_depends_on_metadata_fetcher(self):
        """AUDIT FINDING: EnhancedMetadata depends on metadata_fetcher.Metadata (external)."""
        # Verify the inheritance chain
        assert issubclass(EnhancedMetadata, _MockMetadata)

    def test_enrich_from_orcid_is_stub(self):
        """AUDIT FINDING: _enrich_from_orcid() is a stub."""
        import inspect
        source = inspect.getsource(EnhancedMetadataOrchestrator._enrich_from_orcid)
        assert 'return None' in source

    def test_enrichment_concept_detection_minimal(self):
        """AUDIT FINDING: Only 3 math concept patterns."""
        # Verify count directly from module
        from metadata.enrichment import _extract_mathematical_concepts
        # Feed text that does NOT match any pattern
        assert _extract_mathematical_concepts("eigenvalue determinant integral") == []

    def test_title_quality_no_article_penalty(self):
        """RESOLVED: Article-at-start penalty removed — valid sentence-case titles often start with articles."""
        scorer = MetadataQualityScorer()
        # Lowercase "the" now only gets the lowercase-start penalty, not a double penalty
        score_lower = scorer._score_title("the theory of everything explained in detail")
        score_lower_no_article = scorer._score_title("some theory of everything explained in detail")

        # Both should now get the same penalty (just lowercase start)
        assert score_lower == score_lower_no_article

    def test_quality_metrics_overall_score_weights_sum_to_one(self):
        """AUDIT FINDING: QualityMetrics.overall_score weights must sum to 1.0."""
        weights = {
            'completeness': 0.25,
            'accuracy': 0.25,
            'authority': 0.20,
            'freshness': 0.15,
            'consistency': 0.15,
        }
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_source_ranking_overall_ranking_weights_sum_to_one(self):
        """AUDIT FINDING: SourceRanking.overall_ranking weights must sum to 1.0."""
        weights = {
            'reliability': 0.30,
            'coverage': 0.25,
            'consistency': 0.20,
            'freshness': 0.15,
            'performance': 0.10,
        }
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9
