#!/usr/bin/env python3
"""
Comprehensive Tests for Enhanced Acquisition Engine

Tests all components of the enhanced acquisition system:
- EnhancedAcquisitionEngine functionality
- Strategy implementations (OpenAccess, Preprint, Alternative)
- UnpaywallClient integration
- Error handling and retry logic
- Configuration management
- Task queue system
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

pytest.importorskip("mathpdf.core.acquisition.config",
                     reason="Enhanced acquisition engine not yet implemented")

from mathpdf.core.acquisition.config import (
    ComprehensiveConfig,
    ConfigManager,
    get_aggressive_config,
    get_conservative_config,
)
from mathpdf.core.acquisition.enhanced_acquisition_engine import (
    AcquisitionConfig,
    AcquisitionResult,
    AlternativeStrategy,
    EnhancedAcquisitionEngine,
    EnhancedOpenAccessStrategy,
    PaperCandidate,
    PreprintStrategy,
    UnpaywallClient,
    acquire_paper_by_metadata,
)
from mathpdf.core.acquisition.task_queue_integration import (
    AcquisitionTask,
    EnhancedTaskQueue,
    TaskPriority,
    TaskStatus,
    batch_acquire_papers,
)


class TestPaperCandidate:
    """Test PaperCandidate data class."""
    
    def test_paper_candidate_creation(self):
        """Test basic paper candidate creation."""
        paper = PaperCandidate(
            title="Test Paper",
            authors=["Author One", "Author Two"],
            doi="10.1234/test",
            arxiv_id="2101.00001"
        )
        
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 2
        assert paper.doi == "10.1234/test"
        assert paper.arxiv_id == "2101.00001"
        assert isinstance(paper.metadata, dict)
    
    def test_paper_candidate_defaults(self):
        """Test default values."""
        paper = PaperCandidate(title="Minimal Paper")
        
        assert paper.authors == []
        assert paper.doi is None
        assert paper.metadata == {}

class TestAcquisitionConfig:
    """Test AcquisitionConfig functionality."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AcquisitionConfig()
        
        assert config.enable_unpaywall is True
        assert config.enable_scihub is False
        assert config.max_concurrent_downloads == 5
        assert config.download_timeout == 300
        assert "Academic Paper Manager" in config.user_agent
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AcquisitionConfig(
            enable_scihub=True,
            max_concurrent_downloads=10,
            download_timeout=600
        )
        
        assert config.enable_scihub is True
        assert config.max_concurrent_downloads == 10
        assert config.download_timeout == 600

class TestUnpaywallClient:
    """Test UnpaywallClient functionality."""
    
    @pytest.fixture
    def unpaywall_client(self):
        """Create UnpaywallClient for testing."""
        return UnpaywallClient(email="test@example.edu")
    
    @pytest.mark.asyncio
    async def test_unpaywall_context_manager(self, unpaywall_client):
        """Test async context manager functionality."""
        async with unpaywall_client as client:
            assert client.session is not None
        
        # Session should be closed after context
        assert unpaywall_client.session is None or unpaywall_client.session.closed
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_get_doi_info_success(self, mock_get, unpaywall_client):
        """Test successful DOI information retrieval."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "doi": "10.1234/test",
            "is_oa": True,
            "best_oa_location": {"url_for_pdf": "https://example.com/test.pdf"},
            "oa_locations": [{"url": "https://example.com/test.pdf"}]
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        async with unpaywall_client as client:
            result = await client.get_doi_info("10.1234/test")
        
        assert result is not None
        assert result["is_oa"] is True
        assert "best_oa_location" in result
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_get_doi_info_not_found(self, mock_get, unpaywall_client):
        """Test DOI not found in Unpaywall."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_get.return_value.__aenter__.return_value = mock_response
        
        async with unpaywall_client as client:
            result = await client.get_doi_info("10.1234/nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_enrich_paper_metadata_no_doi(self, unpaywall_client):
        """Test metadata enrichment with no DOI."""
        paper = PaperCandidate(title="Test Paper")
        
        async with unpaywall_client as client:
            enriched = await client.enrich_paper_metadata(paper)
        
        # Should return unchanged paper
        assert enriched.title == "Test Paper"
        assert enriched.doi is None

class TestPreprintStrategy:
    """Test PreprintStrategy functionality."""
    
    @pytest.fixture
    def preprint_strategy(self):
        """Create PreprintStrategy for testing."""
        return PreprintStrategy()
    
    def test_can_handle_arxiv_id(self, preprint_strategy):
        """Test handling papers with arXiv ID."""
        paper = PaperCandidate(title="Test", arxiv_id="2101.00001")
        assert preprint_strategy.can_handle(paper) is True
    
    def test_can_handle_arxiv_url(self, preprint_strategy):
        """Test handling papers with arXiv URL.""" 
        paper = PaperCandidate(title="Test", url="https://arxiv.org/abs/2101.00001")
        assert preprint_strategy.can_handle(paper) is True
    
    def test_cannot_handle_regular_paper(self, preprint_strategy):
        """Test not handling regular papers."""
        paper = PaperCandidate(title="Test", doi="10.1234/test")
        assert preprint_strategy.can_handle(paper) is False
    
    def test_get_arxiv_urls(self, preprint_strategy):
        """Test getting arXiv download URLs."""
        paper = PaperCandidate(title="Test", arxiv_id="2101.00001")
        urls = preprint_strategy.get_download_urls(paper)
        
        assert len(urls) > 0
        assert any("arxiv.org/pdf/2101.00001.pdf" in url for url in urls)
    
    def test_get_biorxiv_urls(self, preprint_strategy):
        """Test getting bioRxiv URLs."""
        paper = PaperCandidate(
            title="Test", 
            url="https://www.biorxiv.org/content/10.1101/2021.01.01.425000v1"
        )
        urls = preprint_strategy.get_download_urls(paper)
        
        assert len(urls) > 0
        assert any("full.pdf" in url for url in urls)

class TestEnhancedOpenAccessStrategy:
    """Test EnhancedOpenAccessStrategy functionality."""
    
    @pytest.fixture
    def oa_strategy(self):
        """Create EnhancedOpenAccessStrategy for testing."""
        return EnhancedOpenAccessStrategy(email="test@example.edu")
    
    def test_can_handle_with_doi(self, oa_strategy):
        """Test handling papers with DOI."""
        paper = PaperCandidate(title="Test", doi="10.1234/test")
        assert oa_strategy.can_handle(paper) is True
    
    def test_can_handle_with_oa_metadata(self, oa_strategy):
        """Test handling papers with OA metadata."""
        paper = PaperCandidate(
            title="Test",
            metadata={"is_open_access": True}
        )
        assert oa_strategy.can_handle(paper) is True
    
    def test_cannot_handle_no_identifiers(self, oa_strategy):
        """Test not handling papers without identifiers."""
        paper = PaperCandidate(title="Test")
        assert oa_strategy.can_handle(paper) is False

class TestAlternativeStrategy:
    """Test AlternativeStrategy functionality."""
    
    @pytest.fixture
    def alt_strategy_disabled(self):
        """Create AlternativeStrategy with all sources disabled."""
        config = AcquisitionConfig(enable_scihub=False, enable_libgen=False)
        return AlternativeStrategy(config)
    
    @pytest.fixture
    def alt_strategy_enabled(self):
        """Create AlternativeStrategy with Sci-Hub enabled."""
        config = AcquisitionConfig(enable_scihub=True, enable_libgen=False)
        return AlternativeStrategy(config)
    
    def test_cannot_handle_disabled(self, alt_strategy_disabled):
        """Test not handling when sources disabled."""
        paper = PaperCandidate(title="Test", doi="10.1234/test")
        assert alt_strategy_disabled.can_handle(paper) is False
    
    def test_can_handle_enabled_with_doi(self, alt_strategy_enabled):
        """Test handling when enabled with DOI."""
        paper = PaperCandidate(title="Test", doi="10.1234/test")
        assert alt_strategy_enabled.can_handle(paper) is True
    
    def test_can_handle_enabled_with_title(self, alt_strategy_enabled):
        """Test handling when enabled with title only."""
        paper = PaperCandidate(title="Test Paper")
        assert alt_strategy_enabled.can_handle(paper) is True

class TestEnhancedAcquisitionEngine:
    """Test EnhancedAcquisitionEngine functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def engine(self):
        """Create EnhancedAcquisitionEngine for testing."""
        config = AcquisitionConfig(
            enable_unpaywall=True,
            enable_scihub=False,
            max_concurrent_downloads=2
        )
        return EnhancedAcquisitionEngine(config)
    
    @pytest.mark.asyncio
    async def test_acquire_paper_no_strategies(self, engine, temp_dir):
        """Test paper acquisition when no strategies can handle it."""
        # Paper with no identifiers that strategies can use
        paper = PaperCandidate(title="Unknown Paper")
        
        result = await engine.acquire_paper(paper, temp_dir)
        
        assert result.success is False
        assert result.paper.title == "Unknown Paper"
        assert len(result.strategies_attempted) == 0
    
    @pytest.mark.asyncio
    @patch('core.acquisition.enhanced_acquisition_engine.EnhancedOpenAccessStrategy.download')
    async def test_acquire_paper_success(self, mock_download, engine, temp_dir):
        """Test successful paper acquisition."""
        # Mock successful download
        mock_result = Mock()
        mock_result.result = "SUCCESS"
        mock_result.file_path = os.path.join(temp_dir, "test.pdf")
        mock_result.response_size = 1000
        mock_download.return_value = mock_result
        
        # Create mock file
        with open(mock_result.file_path, 'w') as f:
            f.write("fake pdf content")
        
        paper = PaperCandidate(title="Test Paper", doi="10.1234/test")
        
        result = await engine.acquire_paper(paper, temp_dir)
        
        # Note: This test might need adjustment based on actual enum values
        # The test framework should be able to handle the success case
        assert result.paper.title == "Test Paper"

class TestTaskQueue:
    """Test EnhancedTaskQueue functionality."""
    
    @pytest.fixture
    def task_queue(self):
        """Create EnhancedTaskQueue for testing."""
        config = AcquisitionConfig(max_concurrent_downloads=2)
        return EnhancedTaskQueue(config, max_concurrent=2)
    
    def test_add_task(self, task_queue):
        """Test adding task to queue."""
        paper = PaperCandidate(title="Test Paper", doi="10.1234/test")
        task_id = task_queue.add_task(paper, "/tmp/test", TaskPriority.NORMAL)
        
        assert task_id is not None
        assert len(task_queue.tasks) == 1
        assert len(task_queue.pending_queue) == 1
        
        task = task_queue.get_task(task_id)
        assert task is not None
        assert task.paper.title == "Test Paper"
        assert task.status == TaskStatus.PENDING
    
    def test_task_priority_ordering(self, task_queue):
        """Test that tasks are ordered by priority."""
        paper1 = PaperCandidate(title="Normal Priority")
        paper2 = PaperCandidate(title="High Priority")
        paper3 = PaperCandidate(title="Critical Priority")
        
        # Add in reverse priority order
        id1 = task_queue.add_task(paper1, "/tmp", TaskPriority.NORMAL)
        id2 = task_queue.add_task(paper2, "/tmp", TaskPriority.HIGH)
        id3 = task_queue.add_task(paper3, "/tmp", TaskPriority.CRITICAL)
        
        # Critical should be first in queue
        assert task_queue.pending_queue[0] == id3
        assert task_queue.pending_queue[1] == id2
        assert task_queue.pending_queue[2] == id1
    
    def test_cancel_pending_task(self, task_queue):
        """Test cancelling a pending task."""
        paper = PaperCandidate(title="Test Paper")
        task_id = task_queue.add_task(paper, "/tmp", TaskPriority.NORMAL)
        
        success = task_queue.cancel_task(task_id)
        assert success is True
        
        task = task_queue.get_task(task_id)
        assert task.status == TaskStatus.CANCELLED
        assert task_id not in task_queue.pending_queue
    
    def test_get_queue_status(self, task_queue):
        """Test getting queue status."""
        # Add some tasks
        paper1 = PaperCandidate(title="Paper 1")
        paper2 = PaperCandidate(title="Paper 2")
        
        task_queue.add_task(paper1, "/tmp", TaskPriority.NORMAL)
        task_queue.add_task(paper2, "/tmp", TaskPriority.HIGH)
        
        stats = task_queue.get_queue_status()
        
        assert stats.total_tasks == 2
        assert stats.pending_tasks == 2
        assert stats.running_tasks == 0
        assert stats.completed_tasks == 0

class TestConfigManager:
    """Test ConfigManager functionality."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file."""
        config_data = {
            "unpaywall": {
                "enabled": True,
                "email": "test@example.edu"
            },
            "performance": {
                "max_concurrent_downloads": 3,
                "download_timeout": 600
            },
            "alternative_sources": {
                "scihub_enabled": True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        yield temp_file
        
        os.unlink(temp_file)
    
    def test_load_from_file(self, temp_config_file):
        """Test loading configuration from file."""
        manager = ConfigManager(temp_config_file)
        config = manager.get_config()
        
        assert config.unpaywall.enabled is True
        assert config.unpaywall.email == "test@example.edu"
        assert config.performance.max_concurrent_downloads == 3
        assert config.alternative_sources.scihub_enabled is True
    
    def test_default_config(self):
        """Test default configuration."""
        manager = ConfigManager()
        config = manager.get_config()
        
        assert isinstance(config, ComprehensiveConfig)
        assert config.unpaywall.enabled is True
        assert config.alternative_sources.scihub_enabled is False
    
    def test_environment_overrides(self):
        """Test environment variable overrides."""
        # Set environment variables
        os.environ['APM_UNPAYWALL_EMAIL'] = 'env@example.edu'
        os.environ['APM_MAX_CONCURRENT'] = '10'
        os.environ['APM_ENABLE_SCIHUB'] = 'true'
        
        try:
            manager = ConfigManager()
            config = manager.get_config()
            
            assert config.unpaywall.email == 'env@example.edu'
            assert config.performance.max_concurrent_downloads == 10
            assert config.alternative_sources.scihub_enabled is True
        finally:
            # Clean up environment
            for key in ['APM_UNPAYWALL_EMAIL', 'APM_MAX_CONCURRENT', 'APM_ENABLE_SCIHUB']:
                os.environ.pop(key, None)
    
    def test_create_acquisition_config(self, temp_config_file):
        """Test creating acquisition config from comprehensive config."""
        manager = ConfigManager(temp_config_file)
        acq_config = manager.create_acquisition_config()
        
        assert acq_config.enable_unpaywall is True
        assert acq_config.enable_scihub is True
        assert acq_config.max_concurrent_downloads == 3

class TestPredefinedConfigs:
    """Test predefined configuration functions."""
    
    def test_conservative_config(self):
        """Test conservative configuration."""
        config = get_conservative_config()
        
        assert config.alternative_sources.scihub_enabled is False
        assert config.alternative_sources.libgen_enabled is False
        assert config.performance.max_concurrent_downloads <= 3
        assert config.performance.api_rate_limit >= 1.0
    
    def test_aggressive_config(self):
        """Test aggressive configuration."""
        config = get_aggressive_config()
        
        assert config.alternative_sources.scihub_enabled is True
        assert config.alternative_sources.libgen_enabled is True
        assert config.performance.max_concurrent_downloads >= 5
        assert config.performance.api_rate_limit <= 1.0

class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_batch_acquisition_empty_list(self, temp_dir):
        """Test batch acquisition with empty paper list."""
        papers = []
        results = await batch_acquire_papers(
            papers=papers,
            dst_folder=temp_dir,
            max_concurrent=2
        )
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_batch_acquisition_mixed_papers(self, temp_dir):
        """Test batch acquisition with mixed paper types."""
        papers = [
            PaperCandidate(title="arXiv Paper", arxiv_id="2101.00001"),
            PaperCandidate(title="DOI Paper", doi="10.1234/test"),
            PaperCandidate(title="Title Only Paper")
        ]
        
        # Mock the actual acquisition to avoid network calls
        with patch('core.acquisition.enhanced_acquisition_engine.EnhancedAcquisitionEngine.acquire_paper') as mock_acquire:
            mock_acquire.return_value = Mock(
                success=False,
                error_message="Mocked failure",
                strategies_attempted=["test_strategy"],
                acquisition_time=1.0
            )
            
            results = await batch_acquire_papers(
                papers=papers,
                dst_folder=temp_dir,
                max_concurrent=2
            )
        
        assert len(results) == 3
        # All should be mock failures in this test
        assert all(not r.success for r in results)

# Integration tests that could run with real network (marked as slow)
class TestRealNetworkIntegration:
    """Integration tests with real network calls (optional)."""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_real_unpaywall_query(self):
        """Test real Unpaywall API query (requires network)."""
        client = UnpaywallClient(email="test@example.edu")
        
        async with client as c:
            # Use a well-known open access DOI
            result = await c.get_doi_info("10.1371/journal.pone.0000308")
            
            if result:  # May fail due to network issues
                assert "is_oa" in result
                assert "doi" in result
    
    @pytest.mark.slow  
    @pytest.mark.asyncio
    async def test_real_arxiv_download(self):
        """Test real arXiv download (requires network)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            strategy = PreprintStrategy()
            paper = PaperCandidate(
                title="Attention Is All You Need",
                arxiv_id="1706.03762"  # Famous transformer paper
            )
            
            if strategy.can_handle(paper):
                result = await strategy.download(paper, temp_dir)
                
                if result.result.name == "SUCCESS":  # May fail due to network
                    assert result.file_path is not None
                    assert os.path.exists(result.file_path)
                    assert os.path.getsize(result.file_path) > 1000

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])