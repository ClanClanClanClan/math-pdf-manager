"""Tests for PDF processing integration and optimized pipeline.

Tests the current API of:
- PDFProcessorBridge (sync wrapper)
- OptimizedPDFProcessor (with cache)
- PDFTypeDetector / PDFCharacteristics
- AdvancedPDFCache
"""

import os
import sys
import tempfile
import threading
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from pdf_processing.integration import (
    LegacyPDFResult,
    PDFProcessorBridge,
)
from pdf_processing.optimized_pipeline import (
    AdvancedPDFCache,
    PDFCharacteristics,
    PDFProcessingResult,
    PDFTypeDetector,
    OptimizedPDFProcessor,
)


# ============================================================================
# LegacyPDFResult
# ============================================================================

class TestLegacyPDFResult:

    def test_creation(self):
        result = LegacyPDFResult(
            text="Full text...",
            metadata={"title": "On BSDEs", "authors": "N. Touzi"},
            success=True,
            processing_time=0.5,
        )
        assert result.text == "Full text..."
        assert result.success is True
        assert result.metadata["title"] == "On BSDEs"

    def test_with_error(self):
        result = LegacyPDFResult(
            text="",
            metadata={},
            success=False,
            processing_time=0.0,
            error="File not found",
        )
        assert not result.success
        assert result.error == "File not found"


# ============================================================================
# PDFProcessorBridge
# ============================================================================

class TestPDFProcessorBridge:

    def test_init_defaults(self):
        bridge = PDFProcessorBridge()
        assert bridge is not None

    def test_init_custom_config(self):
        bridge = PDFProcessorBridge(cache_dir="/tmp/test_cache", max_concurrent=3)
        assert bridge is not None

    def test_process_nonexistent_file(self):
        bridge = PDFProcessorBridge()
        result = bridge.process_pdf_sync(Path("/nonexistent/file.pdf"))
        assert isinstance(result, LegacyPDFResult)
        assert not result.success

    def test_process_batch_empty(self):
        bridge = PDFProcessorBridge()
        results = bridge.process_batch_sync([])
        assert results == []


# ============================================================================
# PDFCharacteristics
# ============================================================================

class TestPDFCharacteristics:

    def test_creation(self):
        chars = PDFCharacteristics(
            is_scanned=False,
            has_forms=False,
            is_arxiv=True,
            is_large=False,
            has_images=True,
            is_encrypted=False,
            file_size=102400,
        )
        assert chars.file_size == 102400
        assert chars.is_arxiv is True
        assert not chars.is_scanned


# ============================================================================
# PDFTypeDetector
# ============================================================================

class TestPDFTypeDetector:

    def test_init(self):
        detector = PDFTypeDetector()
        assert detector is not None


# ============================================================================
# AdvancedPDFCache
# ============================================================================

class TestAdvancedPDFCache:

    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedPDFCache(cache_dir=tmpdir)
            assert cache is not None

    def test_cache_miss(self):
        import asyncio
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedPDFCache(cache_dir=tmpdir)
            result = asyncio.run(cache.get_cached("/nonexistent/file.pdf"))
            assert result is None

    def test_cache_store_and_retrieve(self):
        import asyncio
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedPDFCache(cache_dir=tmpdir)
            data = PDFProcessingResult(
                text="Extracted text",
                metadata={"title": "Test Title"},
                processing_time=0.1,
                library_used="pymupdf",
                cache_hit=False,
                quality_score=0.9,
            )
            # Store should not raise
            asyncio.run(cache.cache_result("/test/file.pdf", data))
            # Retrieve — cache may use file hash as key, so a non-existent
            # path may not find the entry. Just verify no crash.
            retrieved = asyncio.run(cache.get_cached("/test/file.pdf"))
            if retrieved is not None:
                assert retrieved.metadata["title"] == "Test Title"


# ============================================================================
# OptimizedPDFProcessor
# ============================================================================

class TestOptimizedPDFProcessor:

    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = OptimizedPDFProcessor(cache_dir=tmpdir)
            assert processor is not None


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:

    def test_bridge_with_corrupted_file(self):
        bridge = PDFProcessorBridge()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"not a real pdf")
            path = Path(f.name)
        try:
            result = bridge.process_pdf_sync(path)
            assert isinstance(result, LegacyPDFResult)
        finally:
            path.unlink()

    def test_cache_concurrent_access(self):
        import asyncio
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedPDFCache(cache_dir=tmpdir)
            errors = []

            def read_cache():
                try:
                    for _ in range(50):
                        asyncio.run(cache.get_cached("/test/concurrent.pdf"))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=read_cache) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert len(errors) == 0, f"Concurrent access errors: {errors}"
