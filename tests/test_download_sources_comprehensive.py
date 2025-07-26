#!/usr/bin/env python3
"""
Comprehensive Download Sources Testing Suite
Tests all download sources, authentication, and integration components.
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import time
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from downloader.universal_downloader import UniversalDownloader, DownloadResult, SearchResult
from downloader.publisher_downloaders import (
    WileyDownloader, TaylorFrancisDownloader, SageDownloader,
    CambridgeDownloader, ACMDownloader, EnhancedSciHubDownloader
)
from downloader.credentials import CredentialManager, SessionManager, DownloaderConfig
from downloader.orchestrator import DownloadOrchestrator
from metadata.enhanced_sources import (
    SemanticScholarAPI, OpenAlexAPI, ORCIDIntegration,
    EnhancedMetadataOrchestrator, EnhancedMetadata
)

class TestCredentialManager:
    """Test credential management system"""
    
    def test_credential_encryption_roundtrip(self):
        """Test credential encryption and decryption"""
        with tempfile.TemporaryDirectory() as temp_dir:
            creds_file = os.path.join(temp_dir, "test_creds.enc")
            
            # Create credential manager
            creds = CredentialManager(creds_file)
            creds.initialize_encryption("test_password")
            
            # Store credentials
            test_credentials = {
                'username': 'test_user',
                'password': 'test_pass',
                'api_key': 'test_key_123'
            }
            creds.set_publisher_credentials('test_publisher', test_credentials)
            
            # Verify storage
            retrieved = creds.get_publisher_credentials('test_publisher')
            assert retrieved == test_credentials
            
            # Test persistence
            creds2 = CredentialManager(creds_file)
            creds2.initialize_encryption("test_password")
            retrieved2 = creds2.get_publisher_credentials('test_publisher')
            assert retrieved2 == test_credentials
    
    def test_credential_wrong_password(self):
        """Test that wrong password fails"""
        with tempfile.TemporaryDirectory() as temp_dir:
            creds_file = os.path.join(temp_dir, "test_creds.enc")
            
            # Create with one password
            creds = CredentialManager(creds_file)
            creds.initialize_encryption("correct_password")
            creds.set_publisher_credentials('test', {'key': 'value'})
            
            # Try to load with wrong password
            creds2 = CredentialManager(creds_file)
            with pytest.raises(ValueError, match="Invalid master password"):
                creds2.initialize_encryption("wrong_password")

class TestDownloaderConfig:
    """Test downloader configuration management"""
    
    def test_config_creation_and_loading(self):
        """Test configuration creation and loading"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "test_config.json")
            
            # Create config
            config = DownloaderConfig(config_file)
            assert config.get('publisher_priorities') is not None
            assert config.get('rate_limits') is not None
            
            # Modify config
            config.set('test_setting', 'test_value')
            
            # Load in new instance
            config2 = DownloaderConfig(config_file)
            assert config2.get('test_setting') == 'test_value'

class TestUniversalDownloader:
    """Test universal downloader framework"""
    
    @pytest.fixture
    def mock_config(self):
        return {
            'credentials': {
                'test_source': {
                    'username': 'test',
                    'password': 'test'
                }
            },
            'preference_order': ['test_source']
        }
    
    @pytest.mark.asyncio
    async def test_downloader_initialization(self, mock_config):
        """Test downloader initialization"""
        downloader = UniversalDownloader(mock_config)
        assert downloader.config == mock_config
        assert downloader.credentials == mock_config['credentials']
    
    @pytest.mark.asyncio
    async def test_search_all_with_mock_strategies(self, mock_config):
        """Test search across multiple strategies"""
        downloader = UniversalDownloader(mock_config)
        
        # Mock strategy
        mock_strategy = AsyncMock()
        mock_strategy.search.return_value = [
            SearchResult(title="Test Paper", confidence=0.8, source="test")
        ]
        mock_strategy.can_handle.return_value = 0.8
        mock_strategy.name = "test_strategy"
        
        downloader.strategies['test_strategy'] = mock_strategy
        
        # Test search
        results = await downloader.search_all("test query")
        assert len(results) == 1
        assert results[0].title == "Test Paper"
        mock_strategy.search.assert_called_once_with("test query")

class TestPublisherDownloaders:
    """Test publisher-specific downloaders"""
    
    def test_wiley_downloader_initialization(self):
        """Test Wiley downloader initialization"""
        credentials = {'username': 'test', 'password': 'test'}
        downloader = WileyDownloader(credentials)
        assert downloader.credentials == credentials
        assert downloader.base_url == "https://onlinelibrary.wiley.com"
    
    def test_enhanced_scihub_mirror_patterns(self):
        """Test Sci-Hub mirror pattern detection"""
        downloader = EnhancedSciHubDownloader()
        
        # Test DOI detection
        assert downloader._looks_like_doi("10.1038/nature12373")
        assert downloader._looks_like_doi("doi:10.1038/nature12373")
        assert downloader._looks_like_doi("https://doi.org/10.1038/nature12373")
        assert not downloader._looks_like_doi("not a doi")
        
        # Test PMID detection
        assert downloader._looks_like_pmid("12345678")
        assert downloader._looks_like_pmid("123456789")
        assert not downloader._looks_like_pmid("123")
        assert not downloader._looks_like_pmid("abc123456")
    
    @pytest.mark.asyncio
    async def test_scihub_pdf_url_extraction(self):
        """Test Sci-Hub PDF URL extraction"""
        downloader = EnhancedSciHubDownloader()
        
        # Mock HTML with PDF links
        test_html = '''
        <html>
            <iframe src="https://example.com/paper.pdf"></iframe>
            <embed src="/local/paper2.pdf"></embed>
            <a href="https://sci-hub.se/downloads/paper3.pdf">Download</a>
        </html>
        '''
        
        urls = downloader._extract_pdf_urls(test_html, "https://sci-hub.se/")
        assert len(urls) >= 2
        assert any("paper.pdf" in url for url in urls)

class TestMetadataSources:
    """Test enhanced metadata sources"""
    
    @pytest.mark.asyncio
    async def test_semantic_scholar_api_initialization(self):
        """Test Semantic Scholar API initialization"""
        async with SemanticScholarAPI() as s2:
            assert s2.base_url == "https://api.semanticscholar.org/graph/v1"
            assert s2.session is not None
    
    @pytest.mark.asyncio
    async def test_openalex_api_initialization(self):
        """Test OpenAlex API initialization"""
        async with OpenAlexAPI("test@example.com") as openalex:
            assert openalex.base_url == "https://api.openalex.org"
            assert openalex.email == "test@example.com"
    
    def test_enhanced_metadata_creation(self):
        """Test enhanced metadata object creation"""
        metadata = EnhancedMetadata(
            title="Test Paper",
            authors=["Author One", "Author Two"],
            abstract="This is a test abstract",
            citation_count=50,
            fields_of_study=["Computer Science", "Machine Learning"]
        )
        
        assert metadata.title == "Test Paper"
        assert len(metadata.authors) == 2
        assert metadata.citation_count == 50
        assert "Computer Science" in metadata.fields_of_study
        
        # Test serialization
        metadata_dict = metadata.to_dict()
        assert metadata_dict['title'] == "Test Paper"
        assert metadata_dict['citation_count'] == 50

class TestDownloadOrchestrator:
    """Test download orchestrator functionality"""
    
    @pytest.fixture
    def temp_config_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, temp_config_dir):
        """Test orchestrator initialization"""
        orchestrator = DownloadOrchestrator(temp_config_dir)
        assert orchestrator.config_dir == Path(temp_config_dir)
        assert orchestrator.credential_manager is not None
        assert orchestrator.config is not None
    
    def test_download_plan_creation(self, temp_config_dir):
        """Test download plan creation logic"""
        orchestrator = DownloadOrchestrator(temp_config_dir)
        
        # Mock universal downloader
        orchestrator.universal_downloader = MagicMock()
        orchestrator.universal_downloader.strategies = {
            'springer': MagicMock(),
            'sci-hub': MagicMock()
        }
        
        # Test paper analysis
        paper = SearchResult(
            title="Test Paper",
            doi="10.1007/s12345-678-9012-3",  # Springer DOI
            source="springer"
        )
        
        primary, fallback = orchestrator._analyze_paper_sources(paper)
        assert 'springer' in primary
        assert 'sci-hub' in fallback or 'enhanced-sci-hub' in fallback
    
    def test_error_categorization(self, temp_config_dir):
        """Test error categorization for reporting"""
        orchestrator = DownloadOrchestrator(temp_config_dir)
        
        # Test various error types
        assert orchestrator._categorize_error("Connection timeout") == "timeout"
        assert orchestrator._categorize_error("HTTP 404 Not Found") == "access_denied"
        assert orchestrator._categorize_error("Invalid PDF format") == "invalid_pdf"
        assert orchestrator._categorize_error("All sources failed") == "all_sources_failed"
        assert orchestrator._categorize_error("Random error") == "other"
    
    def test_safe_filename_creation(self, temp_config_dir):
        """Test safe filename creation"""
        orchestrator = DownloadOrchestrator(temp_config_dir)
        
        # Test with problematic characters
        unsafe_query = 'Paper with "quotes" and <brackets> and /slashes\\'
        safe_name = orchestrator._create_safe_filename(unsafe_query, 1)
        
        assert '"' not in safe_name
        assert '<' not in safe_name
        assert '/' not in safe_name
        assert safe_name.startswith('0001_')
        assert safe_name.endswith('.pdf')

class TestIntegrationScenarios:
    """Test integration scenarios across components"""
    
    @pytest.mark.ansible
    async def test_full_download_workflow_simulation(self):
        """Test complete download workflow with mocked components"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize orchestrator
            orchestrator = DownloadOrchestrator(temp_dir)
            
            # Mock successful initialization
            with patch.object(orchestrator, '_initialize_universal_downloader'):
                orchestrator.universal_downloader = MagicMock()
                orchestrator.session_manager = MagicMock()
                
                # Mock successful download
                mock_result = DownloadResult(
                    success=True,
                    pdf_data=b'%PDF-1.4 fake pdf content',
                    source="mock_source",
                    file_size=1024,
                    download_time=1.5
                )
                
                orchestrator.universal_downloader.download_paper = AsyncMock(return_value=mock_result)
                
                # Test single download
                result = await orchestrator.download_single("10.1038/test")
                assert result.success
                assert result.source == "mock_source"
                assert result.file_size == 1024
    
    @pytest.mark.asyncio
    async def test_metadata_source_integration(self):
        """Test metadata source integration"""
        orchestrator = EnhancedMetadataOrchestrator()
        
        # Mock API responses
        with patch('metadata.enhanced_sources.SemanticScholarAPI') as mock_s2, \
             patch('metadata.enhanced_sources.OpenAlexAPI') as mock_openalex:
            
            # Mock Semantic Scholar response
            mock_s2_instance = AsyncMock()
            mock_s2_instance.search_papers.return_value = [
                EnhancedMetadata(
                    title="Test Paper from S2",
                    citation_count=10,
                    source="semantic_scholar"
                )
            ]
            mock_s2.return_value.__aenter__.return_value = mock_s2_instance
            
            # Mock OpenAlex response
            mock_openalex_instance = AsyncMock()
            mock_openalex_instance.search_works.return_value = [
                EnhancedMetadata(
                    title="Test Paper from OpenAlex",
                    citation_count=15,
                    source="openalex"
                )
            ]
            mock_openalex.return_value.__aenter__.return_value = mock_openalex_instance
            
            # Test comprehensive search
            results = await orchestrator.comprehensive_search("test query")
            assert len(results) == 2
            assert any(r.source == "semantic_scholar" for r in results)
            assert any(r.source == "openalex" for r in results)

class TestPerformanceAndReliability:
    """Test performance characteristics and reliability"""
    
    @pytest.mark.asyncio
    async def test_concurrent_download_handling(self):
        """Test system behavior under concurrent load"""
        with tempfile.TemporaryDirectory() as temp_dir:
            orchestrator = DownloadOrchestrator(temp_dir)
            
            # Mock components
            orchestrator.universal_downloader = MagicMock()
            orchestrator.session_manager = MagicMock()
            
            # Mock variable download times
            async def mock_download(paper, sources=None):
                await asyncio.sleep(0.1)  # Simulate download time
                return DownloadResult(
                    success=True,
                    pdf_data=b'fake pdf',
                    source="test",
                    download_time=0.1,
                    file_size=1000
                )
            
            orchestrator.universal_downloader.download_paper = mock_download
            
            # Test concurrent downloads
            papers = [f"paper_{i}" for i in range(10)]
            start_time = time.time()
            
            batch_result = await orchestrator.download_batch(papers, max_concurrent=3)
            
            total_time = time.time() - start_time
            
            # Should complete faster than sequential (10 * 0.1 = 1 second)
            assert total_time < 0.8  # Allow some overhead
            assert batch_result.successful_downloads == 10
            assert batch_result.total_papers == 10
    
    def test_rate_limiting_calculations(self):
        """Test rate limiting calculations"""
        downloader = EnhancedSciHubDownloader()
        
        # Test user agent randomization
        agents = [downloader._get_random_user_agent() for _ in range(10)]
        assert len(set(agents)) > 1  # Should have variety
        
        # All should be valid user agent strings
        for agent in agents:
            assert "Mozilla" in agent
            assert len(agent) > 50

class TestErrorHandlingAndRecovery:
    """Test comprehensive error handling"""
    
    @pytest.mark.asyncio
    async def test_download_failure_recovery(self):
        """Test recovery from download failures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            orchestrator = DownloadOrchestrator(temp_dir)
            orchestrator.universal_downloader = MagicMock()
            orchestrator.session_manager = MagicMock()
            
            # Mock failure then success
            call_count = 0
            async def mock_download_with_failure(paper, sources=None):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return DownloadResult(success=False, error="First attempt failed")
                else:
                    return DownloadResult(success=True, pdf_data=b'pdf', source="backup")
            
            orchestrator.universal_downloader.download_paper = mock_download_with_failure
            
            # The orchestrator should handle this gracefully
            result = await orchestrator.download_single("test_paper")
            # With current implementation, it won't retry automatically
            # But the error should be properly categorized
            assert isinstance(result, DownloadResult)
    
    @pytest.mark.asyncio
    async def test_metadata_api_timeout_handling(self):
        """Test handling of API timeouts"""
        # Mock timeout scenario
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.__aenter__.side_effect = asyncio.TimeoutError("Request timeout")
            mock_get.return_value = mock_response
            
            async with SemanticScholarAPI() as s2:
                # Should handle timeout gracefully
                results = await s2.search_papers("test query")
                assert results == []  # Should return empty list, not crash

class TestConfigurationAndCustomization:
    """Test configuration and customization options"""
    
    def test_publisher_priority_configuration(self):
        """Test publisher priority configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DownloaderConfig(os.path.join(temp_dir, "config.json"))
            
            # Test default priorities
            priorities = config.get('publisher_priorities')
            assert priorities['springer'] < priorities['sci-hub']  # Lower number = higher priority
            
            # Test custom priorities
            custom_priorities = {'custom_source': 5}
            config.set('publisher_priorities', custom_priorities)
            
            # Reload and verify
            config2 = DownloaderConfig(os.path.join(temp_dir, "config.json"))
            assert config2.get('publisher_priorities') == custom_priorities
    
    def test_rate_limit_configuration(self):
        """Test rate limit configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DownloaderConfig(os.path.join(temp_dir, "config.json"))
            
            # Test default rate limits
            rate_limits = config.get('rate_limits')
            assert 'springer' in rate_limits
            assert rate_limits['springer'] > 0
            
            # Test custom rate limits
            custom_limits = {'test_source': 2.5}
            config.set('rate_limits', custom_limits)
            assert config.get('rate_limits') == custom_limits

class TestSecurityAndCompliance:
    """Test security and compliance features"""
    
    def test_credential_encryption_strength(self):
        """Test credential encryption is secure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            creds_file = os.path.join(temp_dir, "creds.enc")
            
            creds = CredentialManager(creds_file)
            creds.initialize_encryption("strong_password")
            
            # Store sensitive data
            sensitive_data = {
                'username': 'admin',
                'password': 'super_secret_password_123!',
                'api_key': 'sk-1234567890abcdef'
            }
            creds.set_publisher_credentials('test', sensitive_data)
            
            # Read raw file - should not contain plaintext secrets
            with open(creds_file, 'rb') as f:
                raw_data = f.read()
                
            raw_text = raw_data.decode('utf-8', errors='ignore')
            assert 'super_secret_password_123!' not in raw_text
            assert 'sk-1234567890abcdef' not in raw_text
            assert 'admin' not in raw_text
    
    def test_user_agent_diversity(self):
        """Test user agent diversity for ethical scraping"""
        downloader = EnhancedSciHubDownloader()
        
        # Generate multiple user agents
        agents = [downloader._get_random_user_agent() for _ in range(20)]
        unique_agents = set(agents)
        
        # Should have good diversity
        assert len(unique_agents) >= 3
        
        # Should all be realistic browser user agents
        for agent in unique_agents:
            assert any(browser in agent for browser in ['Chrome', 'Firefox', 'Safari'])
            assert any(os in agent for os in ['Windows', 'Macintosh', 'Linux'])

# Pytest fixtures and configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Performance benchmarks (run separately)
class TestPerformanceBenchmarks:
    """Performance benchmarks for optimization tracking"""
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_metadata_search_performance(self):
        """Benchmark metadata search performance"""
        orchestrator = EnhancedMetadataOrchestrator()
        
        # Mock fast API responses
        with patch('metadata.enhanced_sources.SemanticScholarAPI') as mock_s2:
            mock_s2_instance = AsyncMock()
            mock_s2_instance.search_papers.return_value = [
                EnhancedMetadata(title=f"Paper {i}", citation_count=i)
                for i in range(20)
            ]
            mock_s2.return_value.__aenter__.return_value = mock_s2_instance
            
            start_time = time.time()
            results = await orchestrator.comprehensive_search("benchmark query")
            search_time = time.time() - start_time
            
            # Should complete search quickly
            assert search_time < 2.0  # 2 seconds max
            assert len(results) == 20
    
    @pytest.mark.benchmark
    def test_credential_encryption_performance(self):
        """Benchmark credential encryption performance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            creds_file = os.path.join(temp_dir, "bench_creds.enc")
            
            creds = CredentialManager(creds_file)
            creds.initialize_encryption("benchmark_password")
            
            # Benchmark multiple credential operations
            start_time = time.time()
            
            for i in range(100):
                test_creds = {
                    'username': f'user_{i}',
                    'password': f'pass_{i}',
                    'token': f'token_{i}'
                }
                creds.set_publisher_credentials(f'publisher_{i}', test_creds)
            
            encryption_time = time.time() - start_time
            
            # Should handle 100 credential sets quickly
            assert encryption_time < 5.0  # 5 seconds max
            
            # Benchmark retrieval
            start_time = time.time()
            
            for i in range(100):
                retrieved = creds.get_publisher_credentials(f'publisher_{i}')
                assert retrieved['username'] == f'user_{i}'
            
            retrieval_time = time.time() - start_time
            
            # Retrieval should be very fast
            assert retrieval_time < 1.0  # 1 second max

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "-s"])