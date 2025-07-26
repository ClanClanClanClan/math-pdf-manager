#!/usr/bin/env python3
"""
Hell-level tests for async metadata fetcher.
Tests performance, concurrency, error handling, and edge cases.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from async_metadata_fetcher import (
    AsyncMetadataFetcher, AsyncMetadataResult, BatchResult, RateLimiter,
    fetch_metadata_async, fetch_metadata_batch_async
)
from metadata_fetcher import Metadata


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(0.1)  # 100ms rate limit
        
        start_time = time.time()
        
        # First call should be immediate
        await limiter.acquire()
        first_time = time.time()
        
        # Second call should be delayed
        await limiter.acquire()
        second_time = time.time()
        
        # Should be at least 100ms between calls
        assert second_time - first_time >= 0.09  # Allow small timing variations
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent(self):
        """Test rate limiter under concurrent access."""
        limiter = RateLimiter(0.05)  # 50ms rate limit
        
        async def make_call(call_id):
            await limiter.acquire()
            return time.time(), call_id
        
        # Make multiple concurrent calls
        start_time = time.time()
        tasks = [make_call(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Sort by timestamp
        results.sort(key=lambda x: x[0])
        
        # Verify calls are properly spaced
        for i in range(1, len(results)):
            time_diff = results[i][0] - results[i-1][0]
            assert time_diff >= 0.04  # Allow small timing variations


class TestAsyncMetadataFetcher:
    """Test async metadata fetcher functionality."""
    
    @pytest.fixture
    async def fetcher(self):
        """Create fetcher instance for testing."""
        async with AsyncMetadataFetcher(max_concurrency=5) as fetcher:
            yield fetcher
    
    @pytest.mark.asyncio
    async def test_single_metadata_fetch(self, fetcher):
        """Test fetching metadata for a single query."""
        # Mock ArXiv response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="""<?xml version="1.0"?>
        <feed xmlns="https://www.w3.org/2005/Atom">
            <entry>
                <title>Test Paper Title</title>
                <author><name>Test Author</name></author>
                <published>2021-01-01</published>
            </entry>
        </feed>""")
        
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await fetcher.fetch_metadata("2101.00001")
            
            assert isinstance(result, AsyncMetadataResult)
            assert result.query == "2101.00001"
            assert result.error is None
    
    @pytest.mark.asyncio
    async def test_batch_metadata_fetch(self, fetcher):
        """Test batch metadata fetching."""
        queries = ["2101.00001", "2101.00002", "2101.00003"]
        
        # Mock successful responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="""<?xml version="1.0"?>
        <feed xmlns="https://www.w3.org/2005/Atom">
            <entry>
                <title>Test Paper</title>
                <author><name>Test Author</name></author>
            </entry>
        </feed>""")
        
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await fetcher.fetch_metadata_batch(queries)
            
            assert isinstance(result, BatchResult)
            assert result.total_queries == 3
            assert len(result.results) == 3
            assert result.total_time > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_performance(self, fetcher):
        """Test that concurrent fetching is actually faster."""
        queries = [f"2101.{i:05d}" for i in range(10)]
        
        # Mock response with small delay to simulate network
        async def mock_response():
            await asyncio.sleep(0.1)  # 100ms delay
            mock = AsyncMock()
            mock.status = 200
            mock.text = AsyncMock(return_value='<feed xmlns="https://www.w3.org/2005/Atom"><entry><title>Test</title></entry></feed>')
            return mock
        
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_get.return_value.__aenter__ = mock_response
            
            start_time = time.time()
            result = await fetcher.fetch_metadata_batch(queries)
            concurrent_time = time.time() - start_time
            
            # With 10 requests of 100ms each, concurrent should be much faster than 1000ms
            # With concurrency limit of 5, should take around 200ms (2 batches)
            assert concurrent_time < 0.5  # Should be much faster than sequential
            assert result.total_queries == 10
    
    @pytest.mark.asyncio
    async def test_error_handling(self, fetcher):
        """Test error handling in async operations."""
        # Mock failing response
        mock_response = AsyncMock()
        mock_response.status = 500
        
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await fetcher.fetch_metadata("invalid_id")
            
            assert isinstance(result, AsyncMetadataResult)
            assert result.query == "invalid_id"
            assert result.metadata is None
            assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_streaming_metadata(self, fetcher):
        """Test streaming metadata functionality."""
        queries = [f"2101.{i:05d}" for i in range(5)]
        
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='<feed xmlns="https://www.w3.org/2005/Atom"><entry><title>Test</title></entry></feed>')
        
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            results = []
            async for result in fetcher.stream_metadata(queries, chunk_size=2):
                results.append(result)
                assert isinstance(result, AsyncMetadataResult)
            
            assert len(results) == 5
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, fetcher):
        """Test caching works correctly in async version."""
        query = "2101.00001"
        
        # First call - should hit API
        with patch('async_metadata_fetcher._read_cache', return_value=None), \
             patch('async_metadata_fetcher._write_cache') as mock_write, \
             patch.object(fetcher, '_fetch_from_provider', return_value=Metadata(title="Test", source="test")):
            
            result1 = await fetcher.fetch_metadata(query)
            assert not result1.from_cache
            mock_write.assert_called_once()
        
        # Second call - should hit cache
        cached_data = {'title': 'Test', 'authors': [], 'source': 'test'}
        with patch('async_metadata_fetcher._read_cache', return_value=cached_data):
            result2 = await fetcher.fetch_metadata(query)
            assert result2.from_cache
            assert result2.source == 'cache'


class TestPerformanceBenchmarks:
    """Performance benchmarks and stress tests."""
    
    @pytest.mark.asyncio
    async def test_large_batch_performance(self):
        """Test performance with large batches."""
        queries = [f"2101.{i:05d}" for i in range(100)]
        
        # Mock fast response
        async def mock_session_get(url):
            mock = AsyncMock()
            mock.status = 200
            mock.text = AsyncMock(return_value='<feed xmlns="https://www.w3.org/2005/Atom"><entry><title>Test</title></entry></feed>')
            return mock
        
        async with AsyncMetadataFetcher(max_concurrency=20) as fetcher:
            with patch.object(fetcher.session, 'get', side_effect=mock_session_get):
                start_time = time.time()
                result = await fetcher.fetch_metadata_batch(queries)
                elapsed = time.time() - start_time
                
                # Should handle 100 queries reasonably quickly
                assert elapsed < 10.0  # Should complete in under 10 seconds
                assert result.total_queries == 100
                
                print(f"Processed {result.total_queries} queries in {elapsed:.3f}s")
                print(f"Rate: {result.total_queries / elapsed:.1f} queries/sec")
    
    @pytest.mark.asyncio
    async def test_concurrency_limits(self):
        """Test that concurrency limits are respected."""
        queries = [f"2101.{i:05d}" for i in range(20)]
        
        # Track concurrent calls
        concurrent_calls = 0
        max_concurrent = 0
        
        async def mock_session_get(url):
            nonlocal concurrent_calls, max_concurrent
            concurrent_calls += 1
            max_concurrent = max(max_concurrent, concurrent_calls)
            
            await asyncio.sleep(0.1)  # Simulate network delay
            
            concurrent_calls -= 1
            
            mock = AsyncMock()
            mock.status = 200
            mock.text = AsyncMock(return_value='<feed xmlns="https://www.w3.org/2005/Atom"><entry><title>Test</title></entry></feed>')
            return mock
        
        async with AsyncMetadataFetcher(max_concurrency=5) as fetcher:
            with patch.object(fetcher.session, 'get', side_effect=mock_session_get):
                await fetcher.fetch_metadata_batch(queries)
                
                # Should not exceed concurrency limit
                assert max_concurrent <= 5
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test that memory usage remains stable during large operations."""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process many batches
        for batch_num in range(10):
            queries = [f"batch{batch_num}_{i:03d}" for i in range(50)]
            
            async with AsyncMetadataFetcher() as fetcher:
                # Mock to avoid actual API calls
                with patch.object(fetcher, 'fetch_metadata', return_value=AsyncMetadataResult(query="test")):
                    await fetcher.fetch_metadata_batch(queries)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        print(f"Memory growth: {memory_growth:.2f} MB")
        
        # Should not have significant memory growth
        assert memory_growth < 50  # Less than 50MB growth


class TestErrorResilience:
    """Test error handling and resilience."""
    
    @pytest.mark.asyncio
    async def test_partial_failure_handling(self):
        """Test handling when some requests fail."""
        queries = ["good1", "bad1", "good2", "bad2", "good3"]
        
        async def mock_session_get(url):
            if "bad" in url:
                # Simulate failure
                raise aiohttp.ClientError("Simulated failure")
            
            mock = AsyncMock()
            mock.status = 200
            mock.text = AsyncMock(return_value='<feed xmlns="https://www.w3.org/2005/Atom"><entry><title>Test</title></entry></feed>')
            return mock
        
        async with AsyncMetadataFetcher() as fetcher:
            with patch.object(fetcher.session, 'get', side_effect=mock_session_get):
                result = await fetcher.fetch_metadata_batch(queries)
                
                assert result.total_queries == 5
                assert result.successful + result.failed == 5
                assert result.failed == 2  # The "bad" queries
                
                # Should have results for all queries (some with errors)
                assert len(result.results) == 5
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of request timeouts."""
        async def slow_response(url):
            await asyncio.sleep(2.0)  # Longer than our timeout
            mock = AsyncMock()
            mock.status = 200
            return mock
        
        # Use short timeout for testing
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=0.5)
        
        async with AsyncMetadataFetcher() as fetcher:
            fetcher.session._timeout = timeout
            
            with patch.object(fetcher.session, 'get', side_effect=slow_response):
                result = await fetcher.fetch_metadata("slow_query")
                
                assert result.error is not None
                assert result.metadata is None
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed API responses."""
        malformed_responses = [
            "",  # Empty response
            "Not XML at all",  # Invalid XML
            '<?xml version="1.0"?><invalid>',  # Incomplete XML
            '<?xml version="1.0"?><feed></feed>',  # Valid XML, no entries
        ]
        
        async with AsyncMetadataFetcher() as fetcher:
            for i, bad_response in enumerate(malformed_responses):
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value=bad_response)
                
                with patch.object(fetcher.session, 'get') as mock_get:
                    mock_get.return_value.__aenter__.return_value = mock_response
                    
                    result = await fetcher.fetch_metadata(f"bad_query_{i}")
                    
                    # Should handle gracefully, not crash
                    assert isinstance(result, AsyncMetadataResult)
                    # Might succeed or fail depending on how it's handled


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.asyncio
    async def test_fetch_metadata_async(self):
        """Test single query convenience function."""
        with patch('async_metadata_fetcher.AsyncMetadataFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_metadata.return_value = AsyncMetadataResult(query="test")
            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher
            
            result = await fetch_metadata_async("test_query")
            
            assert isinstance(result, AsyncMetadataResult)
            mock_fetcher.fetch_metadata.assert_called_once_with("test_query")
    
    @pytest.mark.asyncio
    async def test_fetch_metadata_batch_async(self):
        """Test batch query convenience function."""
        queries = ["query1", "query2"]
        
        with patch('async_metadata_fetcher.AsyncMetadataFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_metadata_batch.return_value = BatchResult(
                total_queries=2, successful=2, failed=0, cached=0, 
                total_time=1.0, results=[]
            )
            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher
            
            result = await fetch_metadata_batch_async(queries)
            
            assert isinstance(result, BatchResult)
            mock_fetcher.fetch_metadata_batch.assert_called_once_with(queries)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])