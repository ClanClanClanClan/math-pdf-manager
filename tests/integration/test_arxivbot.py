#!/usr/bin/env python3
"""
Test suite for ArXiv Bot Integration
Tests harvesting, scoring, and pipeline functionality
"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Mock sentence_transformers before importing scorer
sys.modules['sentence_transformers'] = MagicMock()

from mathpdf.arxivbot.harvester import Harvester, HarvesterConfig
from mathpdf.arxivbot.integration import ArxivBotIntegration, SimpleVectorStore
from mathpdf.arxivbot.models.cmo import CMO, Author
from mathpdf.arxivbot.scorer import Scorer, ScorerConfig, SemanticFilter


class TestCMO:
    """Test Core Metadata Object functionality."""
    
    def test_cmo_creation(self):
        """Test CMO creation with all fields."""
        authors = [
            Author(family="Smith", given="John"),
            Author(family="Doe", given="Jane")
        ]
        
        cmo = CMO(
            external_id="arXiv:2401.12345",
            source="arxiv",
            title="Test Paper Title",
            authors=authors,
            published="2024-01-15T00:00:00Z",
            abstract="This is a test abstract",
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
            categories=["cs.AI", "cs.LG"],
            doi="10.1234/test",
            license="CC-BY-4.0"
        )
        
        assert cmo.external_id == "arXiv:2401.12345"
        assert cmo.source == "arxiv"
        assert len(cmo.authors) == 2
        assert cmo.authors[0].family == "Smith"
    
    def test_canonical_filename_generation(self):
        """Test canonical filename generation."""
        authors = [
            Author(family="Smith", given="John Paul"),
            Author(family="O'Brien", given="Mary-Jane"),
            Author(family="García", given="José"),
            Author(family="Lee", given="Wei")
        ]
        
        cmo = CMO(
            external_id="test",
            source="arxiv",
            title="A Very Long Title That Should Be Truncated: An Investigation Into Something Interesting",
            authors=authors,
            published="2024-01-15"
        )
        
        filename = cmo.get_canonical_filename(max_authors=3)
        
        # Should format as: "Smith, J.P., O'Brien, M.-J., García, J., et al. - A Very Long Title..."
        assert "Smith, J.P." in filename or "Smith, J. P." in filename  # Allow both formats
        assert "O'Brien, M.-J." in filename or "O'Brien, M-J." in filename  # Allow both hyphen formats
        assert "et al." in filename
        assert filename.endswith(".pdf")
        assert len(filename.encode('utf-8')) <= 140
    
    def test_embedding_text_generation(self):
        """Test text generation for embeddings."""
        cmo = CMO(
            external_id="test",
            source="arxiv",
            title="Test Title",
            authors=[Author(family="Test")],
            published="2024-01-15",
            abstract="This is\na multi-line\nabstract"
        )
        
        embedding_text = cmo.get_embedding_text()
        
        # Should combine title and abstract, remove newlines
        assert "Test Title" in embedding_text
        assert "multi-line abstract" in embedding_text
        assert "\n" not in embedding_text
    
    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        cmo = CMO(
            external_id="test:123",
            source="test",
            title="Test Paper",
            authors=[Author(family="Author", given="Test")],
            published="2024-01-15T00:00:00Z",
            categories=["test.CAT"]
        )
        
        # Serialize to JSON
        json_str = cmo.to_json()
        data = json.loads(json_str)
        
        assert data["external_id"] == "test:123"
        assert data["source"] == "test"
        assert len(data["authors"]) == 1
        
        # Deserialize from JSON
        cmo2 = CMO.from_json(json_str)
        assert cmo2.external_id == cmo.external_id
        assert cmo2.title == cmo.title


class TestHarvester:
    """Test Harvester component."""
    
    @pytest.mark.asyncio
    async def test_harvester_initialization(self):
        """Test harvester initialization with config."""
        config = HarvesterConfig(
            arxiv_enabled=True,
            hal_enabled=False,
            biorxiv_enabled=True,
            days_back=7,
            ingest_dir="/tmp/test_ingest"
        )
        
        harvester = Harvester(config)
        assert harvester.config.arxiv_enabled
        assert not harvester.config.hal_enabled
        assert harvester.config.days_back == 7
    
    @pytest.mark.asyncio
    async def test_harvest_mock(self):
        """Test harvesting with mocked responses."""
        config = HarvesterConfig(
            arxiv_enabled=True,
            hal_enabled=False,
            ingest_dir=tempfile.mkdtemp()
        )
        
        harvester = Harvester(config)
        
        # Mock the harvest methods
        mock_cmos = [
            CMO(
                external_id="arXiv:2401.00001",
                source="arxiv",
                title="Test Paper 1",
                authors=[Author(family="Author1")],
                published="2024-01-15T00:00:00Z"
            ),
            CMO(
                external_id="arXiv:2401.00002",
                source="arxiv",
                title="Test Paper 2",
                authors=[Author(family="Author2")],
                published="2024-01-15T00:00:00Z"
            )
        ]
        
        with patch.object(harvester, 'harvest_arxiv', return_value=mock_cmos):
            async with harvester:
                results = await harvester.harvest_all()
        
        assert "arxiv" in results
        assert len(results["arxiv"]) == 2
        assert results["arxiv"][0].title == "Test Paper 1"


class TestScorer:
    """Test Scorer component."""
    
    def test_semantic_filter(self):
        """Test semantic filter evaluation."""
        # Create allow filter
        allow_filter = SemanticFilter(
            filter_id="allow_1",
            rule_type="allow",
            rule_text="contains machine learning"
        )
        
        # Create deny filter
        deny_filter = SemanticFilter(
            filter_id="deny_1",
            rule_type="deny",
            rule_text="contains workshop"
        )
        
        # Test CMO that should be allowed
        cmo_allowed = CMO(
            external_id="test:1",
            source="test",
            title="Machine Learning for Science",
            authors=[Author(family="Test")],
            published="2024-01-15",
            abstract="This paper discusses machine learning applications"
        )
        
        # Test CMO that should be denied
        cmo_denied = CMO(
            external_id="test:2",
            source="test",
            title="Workshop Proceedings",
            authors=[Author(family="Test")],
            published="2024-01-15",
            abstract="These are workshop papers"
        )
        
        # Test filters
        assert allow_filter.evaluate(cmo_allowed) == True
        assert allow_filter.evaluate(cmo_denied) is None
        assert deny_filter.evaluate(cmo_denied) == False
        assert deny_filter.evaluate(cmo_allowed) is None
    
    def test_vector_store(self):
        """Test simple vector store functionality."""
        import numpy as np
        
        store = SimpleVectorStore()
        
        # Insert some vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        vec3 = np.array([0.0, 0.0, 1.0])
        
        store.insert("paper1", vec1)
        store.insert("paper2", vec2)
        store.insert("paper3", vec3)
        
        # Query for nearest neighbors
        query_vec = np.array([0.9, 0.1, 0.0])
        neighbors = store.knn(query_vec, k=2)
        
        assert len(neighbors) == 2
        assert neighbors[0][0] == "paper1"  # Should be closest
        assert neighbors[0][1] > neighbors[1][1]  # Should have higher score


class TestIntegration:
    """Test ArxivBotIntegration."""
    
    @pytest.mark.asyncio
    async def test_integration_initialization(self):
        """Test integration initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                'personal_corpus_path': f'{temp_dir}/papers',
                'download_dir': f'{temp_dir}/downloads',
                'ingest_dir': f'{temp_dir}/ingest',
                'sources': {
                    'arxiv': {'enabled': True},
                    'hal': {'enabled': False}
                }
            }
            
            integration = ArxivBotIntegration(config)
            
            # Check config was parsed correctly
            assert integration.harvester_config.arxiv_enabled
            assert not integration.harvester_config.hal_enabled
            
            # Initialize async components
            await integration.initialize()
            
            assert integration.harvester is not None
            assert integration.scorer is not None
    
    @pytest.mark.asyncio
    async def test_cmo_to_paper_candidate_conversion(self):
        """Test conversion from CMO to PaperCandidate."""
        config = {}
        integration = ArxivBotIntegration(config)
        
        cmo = CMO(
            external_id="arXiv:2401.12345",
            source="arxiv",
            title="Test Paper",
            authors=[Author(family="Smith", given="John")],
            published="2024-01-15",
            doi="10.1234/test",
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf"
        )
        
        paper_candidate = integration._cmo_to_paper_candidate(cmo)
        
        assert paper_candidate.title == "Test Paper"
        assert paper_candidate.arxiv_id == "2401.12345"
        assert paper_candidate.doi == "10.1234/test"
        assert "Smith, John" in paper_candidate.authors
    
    @pytest.mark.asyncio
    async def test_daily_pipeline_mock(self):
        """Test daily pipeline with mocked components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                'download_dir': temp_dir,
                'ingest_dir': temp_dir,
                'sources': {'arxiv': {'enabled': True}}
            }
            
            integration = ArxivBotIntegration(config)
            
            # Mock harvester results
            mock_cmos = [
                CMO(
                    external_id="arXiv:2401.00001",
                    source="arxiv",
                    title="Important Paper",
                    authors=[Author(family="Researcher")],
                    published="2024-01-15T00:00:00Z",
                    pdf_url="https://arxiv.org/pdf/2401.00001.pdf"
                )
            ]
            
            # Mock components
            with patch.object(integration, 'harvester') as mock_harvester:
                mock_harvester.__aenter__ = AsyncMock(return_value=mock_harvester)
                mock_harvester.__aexit__ = AsyncMock()
                mock_harvester.harvest_all = AsyncMock(return_value={'arxiv': mock_cmos})
                
                with patch.object(integration, 'scorer') as mock_scorer:
                    mock_scorer.batch_score = Mock(return_value=mock_cmos)
                    mock_scorer.filter_by_threshold = Mock(return_value=mock_cmos)
                    mock_scorer.tau = 0.35
                    
                    with patch.object(integration, '_download_papers', return_value=[
                        {'external_id': 'arXiv:2401.00001', 'success': True}
                    ]):
                        # Run pipeline
                        results = await integration.daily_pipeline()
            
            assert 'harvested' in results
            assert results['harvested']['arxiv'] == 1
            assert len(results['accepted']) == 1
            assert results['accepted'][0] == "arXiv:2401.00001"


class TestEndToEnd:
    """End-to-end tests with real components (mocked network)."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_pipeline_mock(self):
        """Test full pipeline with mocked network calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup config
            config = {
                'personal_corpus_path': temp_dir,
                'download_dir': f"{temp_dir}/downloads",
                'ingest_dir': f"{temp_dir}/ingest",
                'sources': {
                    'arxiv': {'enabled': True},
                    'hal': {'enabled': False},
                    'biorxiv': {'enabled': False}
                },
                'scoring': {
                    'k_neighbours': 3,
                    'default_tau': 0.30
                }
            }
            
            # Create integration
            integration = ArxivBotIntegration(config)
            
            # Mock network responses
            mock_arxiv_response = """<?xml version="1.0"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
                <entry>
                    <id>http://arxiv.org/abs/2401.00001</id>
                    <title>Attention Is All You Need</title>
                    <author><name>Vaswani, A.</name></author>
                    <published>2024-01-15T00:00:00Z</published>
                    <summary>Transformers are great.</summary>
                    <link href="http://arxiv.org/pdf/2401.00001" type="application/pdf"/>
                    <category term="cs.AI"/>
                </entry>
            </feed>"""
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.text = AsyncMock(return_value=mock_arxiv_response)
                mock_response.status = 200
                mock_session.get = AsyncMock(return_value=mock_response)
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Initialize and run
                await integration.initialize()
                
                # Run with smaller mock to avoid ML model loading
                with patch.object(integration.scorer, 'batch_score', return_value=[]):
                    with patch.object(integration.scorer, 'filter_by_threshold', return_value=[]):
                        results = await integration.daily_pipeline()
            
            # Verify results structure
            assert 'date' in results
            assert 'harvested' in results
            assert 'scored' in results
            assert 'accepted' in results
            assert 'downloaded' in results
            assert 'errors' in results


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])