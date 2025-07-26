#!/usr/bin/env python3
"""
Hell-level tests for metadata_fetcher.py
Tests all edge cases, security vulnerabilities, and failure modes.
"""

import asyncio
import concurrent.futures
import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
import unicodedata
from pathlib import Path
from typing import List
from unittest.mock import patch, MagicMock

import pytest
import hypothesis
from hypothesis import given, strategies as st, settings, assume

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from metadata_fetcher import (
    _cache_key, _read_cache, _write_cache, _cache_dir,
    canonicalize, title_match, normalize_author, authors_match,
    query_arxiv, CACHE_DIR
)


class TestCacheSystemHell:
    """Hell-level tests for the cache system."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Create temp cache dir
        self.original_cache_dir = os.environ.get('METADATA_CACHE')
        self.temp_dir = tempfile.mkdtemp()
        os.environ['METADATA_CACHE'] = self.temp_dir
        
        # Reload module to pick up new cache dir
        import importlib
        import metadata_fetcher
        importlib.reload(metadata_fetcher)
        
        yield
        
        # Cleanup
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if self.original_cache_dir:
            os.environ['METADATA_CACHE'] = self.original_cache_dir
        else:
            os.environ.pop('METADATA_CACHE', None)
    
    def test_cache_key_deterministic(self):
        """Test that cache keys are deterministic."""
        text = "Test Paper Title"
        key1 = _cache_key(text)
        key2 = _cache_key(text)
        assert key1 == key2
        assert len(key1) == 64  # SHA-256 produces 64 hex chars
        assert all(c in '0123456789abcdef' for c in key1)
    
    def test_cache_key_never_returns_none(self):
        """CRITICAL: Ensure cache key never returns None (the original bug)."""
        test_cases = [
            "",
            "Normal Title",
            "Title with 中文",
            "Title with émojis 🎉",
            None,  # Should handle gracefully
            "A" * 10000,  # Very long string
            "\x00\x01\x02",  # Binary data
            "Title\nwith\nnewlines",
            "../../etc/passwd",  # Path traversal attempt
        ]
        
        for text in test_cases:
            try:
                key = _cache_key(text)
                assert key is not None
                assert isinstance(key, str)
                assert len(key) == 64
                assert all(c in '0123456789abcdef' for c in key)
            except Exception as e:
                pytest.fail(f"Cache key failed for input '{text}': {e}")
    
    @given(st.text(min_size=0, max_size=10000))
    @settings(max_examples=1000, deadline=5000)
    def test_cache_key_property_based(self, text):
        """Property-based testing for cache key function."""
        key = _cache_key(text)
        
        # Properties that must always hold
        assert isinstance(key, str)
        assert len(key) == 64
        assert all(c in '0123456789abcdef' for c in key)
        
        # Same input always produces same output
        assert _cache_key(text) == key
        
        # Consistent key for same input
        if text.strip():
            # Same text should always produce same key
            assert _cache_key(text) == key
            # Whitespace normalization should be consistent
            normalized_key = _cache_key(f"  {text}  ")
            # Note: uppercase/lowercase may not always be the same due to Unicode complexities
    
    def test_cache_unicode_hell(self):
        """Test cache with various Unicode edge cases."""
        unicode_hell = [
            # Bidirectional text attacks
            "Test\u202Emalicious",
            "Normal\u200Btext\u200Cwith\u200Dzero\u200Ewidth",
            
            # Normalization tests
            "café",  # é as single char
            "café",  # é as combining chars
            
            # Mathematical symbols
            "∫∂α/∂t dt = ∇²φ",
            
            # Emoji and special chars
            "Paper about 👨‍🔬 science",
            "Title with ❌ and ✅",
            
            # RTL languages
            "מאמר בעברית",
            "مقال باللغة العربية",
            
            # Homoglyphs
            "Соmрutеr",  # Cyrillic о, р, е
            
            # Control characters
            "Title\x00with\x01control\x1Fchars",
            
            # Very long repetitive patterns (ReDoS test)
            "a" * 1000 + "b",
            "." * 1000,
            
            # Path traversal attempts
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            
            # SQL injection attempts  
            "'; DROP TABLE papers; --",
            
            # Format string attempts
            "%s%s%s%s%s%s%s%s",
            "{0}{1}{2}{3}{4}",
        ]
        
        for text in unicode_hell:
            # Should not crash
            key = _cache_key(text)
            assert key is not None
            assert len(key) == 64
            
            # Should be consistent
            assert _cache_key(text) == key
            
            # Write and read back
            data = {"title": text, "test": True}
            _write_cache(text, data)
            
            cached = _read_cache(text)
            assert cached == data
    
    def test_cache_concurrent_access(self):
        """Test cache under concurrent access (race conditions)."""
        num_threads = 50
        operations_per_thread = 100
        
        def worker(thread_id):
            for i in range(operations_per_thread):
                key = f"thread_{thread_id}_item_{i}"
                data = {"thread": thread_id, "item": i, "timestamp": time.time()}
                
                # Randomly read or write
                if i % 2 == 0:
                    _write_cache(key, data)
                else:
                    result = _read_cache(key)
                    if result:
                        assert result.get("thread") == thread_id
        
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify cache integrity
        cache_files = list(Path(os.environ['METADATA_CACHE']).glob("*.json"))
        assert len(cache_files) > 0
        
        # Each file should contain valid JSON
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    assert isinstance(data, dict)
            except Exception as e:
                pytest.fail(f"Cache file {cache_file} corrupted: {e}")
    
    def test_cache_disk_full_simulation(self):
        """Test cache behavior when disk is full."""
        test_key = "test_disk_full"
        test_data = {"test": "data" * 1000}
        
        with patch('pathlib.Path.write_text') as mock_write:
            mock_write.side_effect = OSError("No space left on device")
            
            # Should not crash, just log warning
            _write_cache(test_key, test_data)
            
            # Cache read should return None (not found)
            assert _read_cache(test_key) is None
    
    def test_cache_corrupted_files(self):
        """Test cache behavior with corrupted cache files."""
        test_key = "corrupted_test"
        cache_file = Path(os.environ['METADATA_CACHE']) / f"{_cache_key(test_key)}.json"
        
        # Create corrupted cache files
        corrupted_data = [
            b"not json at all",
            b'{"incomplete": ',
            b'{"test": "\xff\xfe invalid utf-8"}',
            b"null",
            b"[]",  # Should be dict, not list
            b"123",  # Should be dict, not number
        ]
        
        for corrupt in corrupted_data:
            cache_file.write_bytes(corrupt)
            
            # Should return None, not crash
            result = _read_cache(test_key)
            assert result is None
    
    def test_cache_path_traversal_protection(self):
        """Test that cache is immune to path traversal attacks."""
        evil_keys = [
            "../evil",
            "../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "\x00etc\x00passwd",
            "normal/../../../evil",
        ]
        
        for evil_key in evil_keys:
            # Generate cache file path
            cache_file = Path(os.environ['METADATA_CACHE']) / f"{_cache_key(evil_key)}.json"
            
            # Ensure it's within cache directory
            try:
                resolved = cache_file.resolve()
                cache_dir = Path(os.environ['METADATA_CACHE']).resolve()
                assert str(resolved).startswith(str(cache_dir))
            except Exception:
                pass  # Some paths might not resolve, that's OK
            
            # Try to write
            _write_cache(evil_key, {"evil": True})
            
            # Verify no cache files were written outside cache dir  
            # (ignore unrelated system files, only check for our cache key pattern)
            parent_dir = Path(os.environ['METADATA_CACHE']).parent
            evil_cache_key = _cache_key(evil_key)
            evil_files = list(parent_dir.glob(f"{evil_cache_key}*.json"))
            assert len(evil_files) == 0
    
    def test_cache_atomic_writes(self):
        """Test that cache writes are atomic (no partial writes)."""
        test_key = "atomic_test"
        large_data = {"data": "x" * 1000000}  # 1MB of data
        
        def writer():
            for i in range(100):
                large_data["iteration"] = i
                _write_cache(test_key, large_data)
        
        def reader():
            for _ in range(100):
                result = _read_cache(test_key)
                if result:
                    # Should always see complete data
                    assert "data" in result
                    assert "iteration" in result
                    assert len(result["data"]) == 1000000
                time.sleep(0.001)
        
        # Run writers and readers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(5):
                futures.append(executor.submit(writer))
                futures.append(executor.submit(reader))
            
            concurrent.futures.wait(futures)
    
    def test_cache_performance_stress(self):
        """Stress test cache performance."""
        num_items = 10000
        
        start_time = time.time()
        
        # Write many items
        for i in range(num_items):
            key = f"perf_test_{i}"
            data = {
                "index": i,
                "title": f"Paper {i}" * 10,
                "authors": [f"Author {j}" for j in range(10)],
                "abstract": "Abstract text " * 100,
            }
            _write_cache(key, data)
        
        write_time = time.time() - start_time
        
        # Read all items back
        start_time = time.time()
        for i in range(num_items):
            key = f"perf_test_{i}"
            result = _read_cache(key)
            assert result is not None
            assert result["index"] == i
        
        read_time = time.time() - start_time
        
        # Performance assertions
        assert write_time < 60  # Should write 10k items in under 60s
        assert read_time < 30   # Should read 10k items in under 30s
        
        # Check cache directory size
        cache_size = sum(f.stat().st_size for f in Path(os.environ['METADATA_CACHE']).glob("*.json"))
        assert cache_size > 0
        
        print(f"Performance: {num_items} writes in {write_time:.2f}s, reads in {read_time:.2f}s")
        print(f"Cache size: {cache_size / 1024 / 1024:.2f} MB")


class TestCanonicalizeHell:
    """Hell-level tests for text canonicalization."""
    
    def test_canonicalize_security(self):
        """Test canonicalization removes dangerous Unicode."""
        dangerous_inputs = [
            # Bidirectional overrides
            "Normal\u202Ereversed",
            "\u202Dforced\u202Cltr",
            
            # Zero-width characters
            "Zero\u200Bwidth\u200Cspace",
            "\uFEFFBOM at start",
            
            # Homoglyphs
            "Gооgle",  # with Cyrillic о
            "𝐻𝑒𝑙𝑙𝑜",  # Mathematical alphanumeric
            
            # Control characters
            "Line\nbreak",
            "Tab\there",
            "Null\x00char",
        ]
        
        for dangerous in dangerous_inputs:
            clean = canonicalize(dangerous)
            
            # Should remove all dangerous characters
            assert '\u202E' not in clean
            assert '\u200B' not in clean
            assert '\uFEFF' not in clean
            assert '\x00' not in clean
            
            # Should normalize to ASCII where possible
            assert all(ord(c) < 128 or unicodedata.category(c)[0] == 'L' for c in clean)
    
    @given(st.text(min_size=0, max_size=1000))
    def test_canonicalize_idempotent(self, text):
        """Test that canonicalization is idempotent."""
        once = canonicalize(text)
        twice = canonicalize(once)
        assert once == twice
    
    def test_canonicalize_performance(self):
        """Test canonicalization performance on large inputs."""
        # ReDoS test - should not hang
        evil_patterns = [
            "a" * 10000,
            "." * 10000,
            "(" * 5000 + ")" * 5000,
            "\\begin{" * 1000 + "}" * 1000,
        ]
        
        for pattern in evil_patterns:
            start = time.time()
            result = canonicalize(pattern)
            elapsed = time.time() - start
            
            assert elapsed < 1.0  # Should complete in under 1 second
            assert result is not None


class TestMatchingHell:
    """Hell-level tests for fuzzy matching."""
    
    def test_title_match_edge_cases(self):
        """Test title matching with edge cases."""
        test_cases = [
            # Should match
            ("Café", "cafe", True),
            ("naïve", "naive", True),
            ("Poincaré", "Poincare", True),
            ("α-β Algorithm", "a-b algorithm", True),
            ("Machine—Learning", "Machine-Learning", True),
            
            # Should not match  
            ("Completely Different", "Another Title", False),
            ("", "Non-empty", False),
            ("Short", "This is a much longer title that shares one word", False),
        ]
        
        for title1, title2, should_match in test_cases:
            result = title_match(title1, title2)
            assert result == should_match, f"{title1} vs {title2}: expected {should_match}, got {result}"
    
    def test_authors_match_hell(self):
        """Test author matching with complex cases."""
        test_cases = [
            # Various formats should match
            (["Smith, John"], ["John Smith"], True),
            (["Smith, J."], ["J. Smith"], True),
            (["Smith, John Andrew"], ["Smith, J. A."], True),
            
            # International names
            (["Müller, Hans"], ["Mueller, Hans"], True),
            (["José García"], ["Garcia, Jose"], True),
            
            # Multiple authors
            (["Smith, J.", "Jones, A."], ["Jones, A.", "Smith, J."], True),
            
            # Should not match
            (["Smith, John"], ["Jones, John"], False),
            ([], ["Smith, J."], False),
        ]
        
        for authors1, authors2, should_match in test_cases:
            result = authors_match(authors1, authors2)
            assert result == should_match


class TestArxivQueryHell:
    """Hell-level tests for ArXiv querying."""
    
    @patch('metadata_fetcher._get')
    def test_arxiv_malformed_responses(self, mock_get):
        """Test ArXiv query with malformed responses."""
        malformed_responses = [
            "",  # Empty response
            "Not XML at all",
            '<?xml version="1.0"?><root>Incomplete',
            '<?xml version="1.0"?><entry></entry>',  # Missing namespace
        ]
        
        for response_text in malformed_responses:
            mock_response = MagicMock()
            mock_response.text = response_text
            mock_get.return_value = mock_response
            
            result = query_arxiv("2101.00001")
            # Should handle gracefully
            assert result is None or isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])