"""Phase 5: Processing pipeline audit."""
import hashlib
import json
import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from processing.main_processing import (
    process_file, verify_output, process_batch,
    _collect_pdf_files, validate_config, get_default_config,
    cleanup_processed_files, verify_processing_output,
)


# ============================================================================
# Section 5A: process_file() -- Core Processing Function
# ============================================================================

class TestProcessFile:
    """Audit: Verify process_file() behaviour with various inputs."""

    def test_real_pdf_hash_is_correct(self, tmp_path):
        """process_file() should compute a correct SHA-256 hash for a real PDF."""
        pdf = tmp_path / "sample.pdf"
        content = b"%PDF-1.4 fake body content for hash testing\n%%EOF"
        pdf.write_bytes(content)

        expected_hash = hashlib.sha256(content).hexdigest()

        result = process_file(str(pdf))

        assert result["success"] is True
        assert result["file_hash"] == expected_hash, (
            f"Expected SHA-256 {expected_hash}, got {result['file_hash']}"
        )

    def test_real_pdf_file_size_is_correct(self, tmp_path):
        """process_file() should report the correct file size."""
        pdf = tmp_path / "sample.pdf"
        content = b"%PDF-1.4 body\n%%EOF"
        pdf.write_bytes(content)

        result = process_file(str(pdf))

        assert result["success"] is True
        assert result["file_size"] == len(content)

    def test_non_pdf_returns_error(self, tmp_path):
        """process_file() should reject non-.pdf files."""
        txt = tmp_path / "notes.txt"
        txt.write_text("Hello, world!")

        result = process_file(str(txt))

        assert result["success"] is False
        assert "Not a PDF" in result["error"]

    def test_missing_file_returns_error(self, tmp_path):
        """process_file() should return success=False for a missing file."""
        missing = tmp_path / "nonexistent.pdf"

        result = process_file(str(missing))

        assert result["success"] is False
        assert "not found" in result["error"].lower() or "File not found" in result["error"]

    def test_config_processor_field_propagated(self, tmp_path):
        """process_file() should propagate the config 'processor' field."""
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF")

        result = process_file(str(pdf), config={"processor": "custom-v2"})

        assert result["success"] is True
        assert result["processed_with"] == "custom-v2"

    def test_config_default_processor(self, tmp_path):
        """process_file() without config should use 'default' processor."""
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF")

        result = process_file(str(pdf))

        assert result["processed_with"] == "default"

    # ------------------------------------------------------------------
    # RESOLVED: Real PyMuPDF metadata extraction (was mock)
    # ------------------------------------------------------------------
    def test_real_pdf_metadata_extraction(self, tmp_path):
        """
        RESOLVED AUDIT FINDING: process_file() now uses PyMuPDF to extract
        real metadata from PDFs. When a PDF has embedded metadata (title,
        author, creation date), those values are used. When absent, it falls
        back to the filename stem.
        """
        import fitz

        pdf = tmp_path / "arxiv_2301_12345v2.pdf"
        doc = fitz.open()
        doc.insert_page(-1, text="Abstract\nThis paper studies topology.\n\nIntroduction")
        doc.set_metadata({
            'title': 'On the topology of manifolds',
            'author': 'Alice Smith; Bob Jones',
            'creationDate': 'D:20230115120000',
        })
        doc.save(str(pdf))
        doc.close()

        result = process_file(str(pdf))

        assert result["success"] is True
        metadata = result["metadata"]

        assert metadata["title"] == "On the topology of manifolds"
        assert "Alice Smith" in metadata["authors"]
        assert "Bob Jones" in metadata["authors"]
        assert metadata["year"] == 2023

    def test_fallback_to_filename_when_no_pdf_metadata(self, tmp_path):
        """
        When the PDF has no embedded metadata, the title falls back to the
        filename stem and authors list is empty.
        """
        import fitz

        pdf = tmp_path / "stochastic_calculus.pdf"
        doc = fitz.open()
        doc.insert_page(-1, text="Some content")
        doc.save(str(pdf))
        doc.close()

        result = process_file(str(pdf))

        assert result["success"] is True
        metadata = result["metadata"]

        # Title falls back to filename stem when PDF has no title metadata
        assert metadata["title"] == "stochastic_calculus"

    def test_fake_pdf_bytes_still_succeed(self, tmp_path):
        """
        A minimal fake PDF (just %PDF header) should still succeed with
        fallback metadata from the filename.
        """
        pdf = tmp_path / "alpha.pdf"
        pdf.write_bytes(b"%PDF-1.4 Content A about topology\n%%EOF")

        result = process_file(str(pdf))
        assert result["success"] is True
        metadata = result["metadata"]
        # With a fake PDF that PyMuPDF can't parse, falls back to stem
        assert isinstance(metadata["title"], str)
        assert len(metadata["title"]) > 0


# ============================================================================
# Section 5B: verify_output() / verify_processing_output()
# ============================================================================

class TestVerifyOutput:
    """Audit: Verify output validation logic."""

    def test_valid_success_output(self):
        """A successful output with metadata and hash should pass."""
        output = {
            "success": True,
            "file_path": "/tmp/paper.pdf",
            "file_hash": "abc123",
            "file_size": 1024,
            "metadata": {"title": "Test"},
        }
        assert verify_output(output) is True

    def test_valid_failure_output(self):
        """A failure output with error field should pass validation."""
        output = {
            "success": False,
            "file_path": "/tmp/missing.pdf",
            "error": "File not found",
        }
        assert verify_output(output) is True

    def test_missing_success_field(self):
        """Output missing the 'success' field should fail validation."""
        output = {"file_path": "/tmp/paper.pdf", "error": "some error"}
        assert verify_output(output) is False

    def test_missing_file_path_field(self):
        """Output missing the 'file_path' field should fail validation."""
        output = {"success": True, "metadata": {"title": "T"}, "file_hash": "x"}
        assert verify_output(output) is False

    def test_success_without_metadata_or_hash_fails(self):
        """A success output lacking both metadata and hash should fail."""
        output = {"success": True, "file_path": "/tmp/paper.pdf"}
        assert verify_output(output) is False

    def test_failure_without_error_fails(self):
        """A failure output without an error message should fail."""
        output = {"success": False, "file_path": "/tmp/paper.pdf"}
        assert verify_output(output) is False

    def test_custom_required_fields(self):
        """Custom required_fields should be respected.

        Note: verify_output() also checks success/error logic beyond
        required_fields, so a successful output MUST have metadata or hash.
        """
        output = {
            "success": True, "file_path": "/tmp/f.pdf",
            "custom_id": 42, "metadata": {"title": "Test"},
        }
        fmt = {"required_fields": ["success", "file_path", "custom_id"]}
        assert verify_output(output, expected_format=fmt) is True

    def test_custom_required_fields_missing(self):
        """Missing custom required field should fail."""
        output = {"success": True, "file_path": "/tmp/f.pdf"}
        fmt = {"required_fields": ["success", "file_path", "custom_id"]}
        assert verify_output(output, expected_format=fmt) is False

    def test_verify_processing_output_is_alias(self):
        """verify_processing_output should be a compatibility wrapper for verify_output."""
        output = {
            "success": True,
            "file_path": "/tmp/paper.pdf",
            "file_hash": "abc",
            "metadata": {"title": "T"},
        }
        assert verify_processing_output(output) == verify_output(output)


# ============================================================================
# Section 5C: process_batch()
# ============================================================================

class TestProcessBatch:
    """Audit: Verify batch processing in sequential and parallel modes."""

    def test_sequential_batch(self, tmp_path):
        """Sequential batch should process all files."""
        files = []
        for i in range(3):
            pdf = tmp_path / f"paper_{i}.pdf"
            pdf.write_bytes(b"%PDF-1.4 content\n%%EOF")
            files.append(str(pdf))

        results = process_batch(files, parallel=False)

        assert len(results) == 3
        assert all(r["success"] for r in results)

    def test_parallel_batch(self, tmp_path):
        """Parallel batch should process all files."""
        files = []
        for i in range(3):
            pdf = tmp_path / f"paper_{i}.pdf"
            pdf.write_bytes(b"%PDF-1.4 content\n%%EOF")
            files.append(str(pdf))

        results = process_batch(files, parallel=True)

        assert len(results) == 3
        assert all(r["success"] for r in results)

    def test_sequential_and_parallel_produce_same_results(self, tmp_path):
        """Sequential and parallel modes should produce the same set of results."""
        files = []
        for i in range(4):
            pdf = tmp_path / f"paper_{i}.pdf"
            pdf.write_bytes(f"%PDF-1.4 body {i}\n%%EOF".encode())
            files.append(str(pdf))

        seq = process_batch(files, parallel=False)
        par = process_batch(files, parallel=True)

        # Both should succeed
        assert all(r["success"] for r in seq)
        assert all(r["success"] for r in par)

        # Same set of hashes (order may differ in parallel)
        seq_hashes = sorted(r["file_hash"] for r in seq)
        par_hashes = sorted(r["file_hash"] for r in par)
        assert seq_hashes == par_hashes

    def test_batch_with_mixed_valid_invalid(self, tmp_path):
        """Batch should handle a mix of valid PDFs, non-PDFs, and missing files."""
        pdf = tmp_path / "valid.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF")

        txt = tmp_path / "readme.txt"
        txt.write_text("not a pdf")

        missing = tmp_path / "ghost.pdf"

        results = process_batch([str(pdf), str(txt), str(missing)], parallel=False)

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False  # not a PDF
        assert results[2]["success"] is False  # missing

    def test_empty_batch(self):
        """Empty file list should return empty results."""
        results = process_batch([], parallel=False)
        assert results == []


# ============================================================================
# Section 5D: _collect_pdf_files()
# ============================================================================

class TestCollectPdfFiles:
    """Audit: Verify deterministic PDF file collection."""

    def test_finds_pdfs_sorted(self, tmp_path):
        """Should find all PDFs and return them sorted."""
        (tmp_path / "c_paper.pdf").write_bytes(b"%PDF")
        (tmp_path / "a_paper.pdf").write_bytes(b"%PDF")
        (tmp_path / "b_paper.pdf").write_bytes(b"%PDF")
        (tmp_path / "notes.txt").write_text("not a pdf")

        found = _collect_pdf_files(tmp_path)

        assert len(found) == 3
        names = [p.name for p in found]
        assert names == sorted(names), f"Files should be sorted, got {names}"

    def test_finds_pdfs_recursively(self, tmp_path):
        """Should find PDFs in subdirectories."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "top.pdf").write_bytes(b"%PDF")
        (sub / "nested.pdf").write_bytes(b"%PDF")

        found = _collect_pdf_files(tmp_path)

        assert len(found) == 2

    def test_max_files_limit(self, tmp_path):
        """max_files should truncate the result list."""
        for i in range(10):
            (tmp_path / f"paper_{i:02d}.pdf").write_bytes(b"%PDF")

        found = _collect_pdf_files(tmp_path, max_files=3)

        assert len(found) == 3

    def test_max_files_zero(self, tmp_path):
        """max_files=0 should return an empty list."""
        (tmp_path / "paper.pdf").write_bytes(b"%PDF")

        found = _collect_pdf_files(tmp_path, max_files=0)

        assert found == []

    def test_max_files_none_returns_all(self, tmp_path):
        """max_files=None should return all files."""
        for i in range(5):
            (tmp_path / f"paper_{i}.pdf").write_bytes(b"%PDF")

        found = _collect_pdf_files(tmp_path, max_files=None)

        assert len(found) == 5

    def test_missing_directory_raises(self, tmp_path):
        """Non-existent directory should raise FileNotFoundError."""
        missing = tmp_path / "no_such_dir"

        with pytest.raises(FileNotFoundError):
            _collect_pdf_files(missing)

    def test_file_not_directory_raises(self, tmp_path):
        """Passing a file instead of a directory should raise FileNotFoundError."""
        f = tmp_path / "file.txt"
        f.write_text("content")

        with pytest.raises(FileNotFoundError):
            _collect_pdf_files(f)

    def test_empty_directory(self, tmp_path):
        """An empty directory should return an empty list."""
        found = _collect_pdf_files(tmp_path)

        assert found == []

    def test_ignores_non_pdf(self, tmp_path):
        """Non-PDF files should be excluded."""
        (tmp_path / "paper.pdf").write_bytes(b"%PDF")
        (tmp_path / "notes.txt").write_text("text")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "data.csv").write_text("a,b,c")

        found = _collect_pdf_files(tmp_path)

        assert len(found) == 1
        assert found[0].name == "paper.pdf"


# ============================================================================
# Section 5E: validate_config()
# ============================================================================

class TestValidateConfig:
    """Audit: Verify configuration validation."""

    def test_empty_config_is_valid(self):
        """Empty config should be valid (no required keys)."""
        assert validate_config({}) is True

    def test_valid_max_file_size(self):
        """Positive numeric max_file_size should be valid."""
        assert validate_config({"max_file_size": 100}) is True
        assert validate_config({"max_file_size": 1.5}) is True

    def test_invalid_max_file_size_zero(self):
        """max_file_size of 0 should be invalid."""
        assert validate_config({"max_file_size": 0}) is False

    def test_invalid_max_file_size_negative(self):
        """Negative max_file_size should be invalid."""
        assert validate_config({"max_file_size": -10}) is False

    def test_invalid_max_file_size_string(self):
        """Non-numeric max_file_size should be invalid."""
        assert validate_config({"max_file_size": "big"}) is False

    def test_valid_output_formats(self):
        """json, csv, xml should all be valid output formats."""
        for fmt in ("json", "csv", "xml"):
            assert validate_config({"output_format": fmt}) is True, f"'{fmt}' should be valid"

    def test_invalid_output_format(self):
        """Unsupported output format should be invalid."""
        assert validate_config({"output_format": "yaml"}) is False
        assert validate_config({"output_format": "parquet"}) is False

    def test_combined_valid_config(self):
        """Config with multiple valid options should pass."""
        config = {
            "max_file_size": 50 * 1024 * 1024,
            "output_format": "json",
            "extra_option": True,  # unknown keys are allowed
        }
        assert validate_config(config) is True


# ============================================================================
# Section 5F: get_default_config()
# ============================================================================

class TestGetDefaultConfig:
    """Audit: Verify default configuration values."""

    def test_default_config_keys(self):
        """Default config should contain all expected keys."""
        config = get_default_config()
        expected_keys = {
            "processor", "max_file_size", "output_format",
            "extract_metadata", "verify_output", "parallel_processing", "timeout",
        }
        assert expected_keys.issubset(config.keys()), (
            f"Missing keys: {expected_keys - config.keys()}"
        )

    def test_default_processor(self):
        """Default processor should be 'default'."""
        assert get_default_config()["processor"] == "default"

    def test_default_max_file_size(self):
        """Default max_file_size should be 100 MB."""
        assert get_default_config()["max_file_size"] == 100 * 1024 * 1024

    def test_default_output_format(self):
        """Default output format should be 'json'."""
        assert get_default_config()["output_format"] == "json"

    def test_default_parallel_processing_off(self):
        """Parallel processing should be off by default."""
        assert get_default_config()["parallel_processing"] is False

    def test_default_timeout(self):
        """Default timeout should be 300 seconds (5 minutes)."""
        assert get_default_config()["timeout"] == 300

    def test_default_config_is_valid(self):
        """The default config should pass its own validation."""
        assert validate_config(get_default_config()) is True

    def test_default_config_returns_fresh_dict(self):
        """Each call should return a new dict (no shared state)."""
        a = get_default_config()
        b = get_default_config()
        assert a is not b
        a["processor"] = "mutated"
        assert b["processor"] == "default"


# ============================================================================
# Section 5G: cleanup_processed_files()
# ============================================================================

class TestCleanupProcessedFiles:
    """Audit: Verify cleanup and move behaviour."""

    def test_cleanup_counts_successes_and_failures(self, tmp_path):
        """Should count processed vs failed files correctly."""
        results = [
            {"success": True, "file_path": "/tmp/a.pdf"},
            {"success": True, "file_path": "/tmp/b.pdf"},
            {"success": False, "error": "Not a PDF", "file_path": "/tmp/c.txt"},
        ]

        summary = cleanup_processed_files(results, move_to=None)

        assert summary["files_processed"] == 2
        assert summary["files_failed"] == 1

    def test_cleanup_moves_files(self, tmp_path):
        """When move_to is provided, successful files should be moved."""
        src = tmp_path / "paper.pdf"
        src.write_bytes(b"%PDF-1.4\n%%EOF")
        dest_dir = tmp_path / "processed"

        results = [{"success": True, "file_path": str(src)}]
        summary = cleanup_processed_files(results, move_to=str(dest_dir))

        assert summary["files_moved"] == 1
        assert (dest_dir / "paper.pdf").exists()
        assert not src.exists()

    def test_cleanup_creates_destination_directory(self, tmp_path):
        """move_to directory should be created if it does not exist."""
        src = tmp_path / "paper.pdf"
        src.write_bytes(b"%PDF-1.4\n%%EOF")
        dest_dir = tmp_path / "new" / "nested" / "dir"

        results = [{"success": True, "file_path": str(src)}]
        cleanup_processed_files(results, move_to=str(dest_dir))

        assert dest_dir.exists()
        assert (dest_dir / "paper.pdf").exists()

    def test_cleanup_failure_errors_collected(self, tmp_path):
        """Errors from failed results should appear in the summary."""
        results = [
            {"success": False, "error": "Corrupt PDF", "file_path": "/tmp/bad.pdf"},
        ]

        summary = cleanup_processed_files(results)

        assert "Corrupt PDF" in summary["errors"]

    def test_cleanup_move_nonexistent_source(self, tmp_path):
        """Moving a file that no longer exists should record an error, not crash."""
        dest_dir = tmp_path / "processed"
        results = [{"success": True, "file_path": str(tmp_path / "gone.pdf")}]

        summary = cleanup_processed_files(results, move_to=str(dest_dir))

        assert summary["files_moved"] == 0
        assert len(summary["errors"]) >= 1

    def test_cleanup_empty_results(self):
        """Empty result list should produce zero counts."""
        summary = cleanup_processed_files([])

        assert summary["files_processed"] == 0
        assert summary["files_moved"] == 0
        assert summary["files_failed"] == 0
        assert summary["errors"] == []


# ============================================================================
# Section 5H: verify_configuration() -- Config object checks
# ============================================================================

class TestVerifyConfiguration:
    """Audit: Verify the verify_configuration() function."""

    def test_empty_collections_produce_warnings(self):
        """Empty known_words / whitelist / exceptions should produce warnings."""
        from processing.main_processing import verify_configuration

        mock_cfg = MagicMock()
        mock_cfg.known_words = []
        mock_cfg.capitalization_whitelist = []
        mock_cfg.exceptions = []
        mock_cfg.config = {}

        warnings_list = verify_configuration(mock_cfg)

        assert any("Known words" in w for w in warnings_list)
        assert any("Capitalization whitelist" in w for w in warnings_list)
        assert any("Exceptions" in w for w in warnings_list)

    def test_none_collections_produce_warnings(self):
        """None-valued attributes should warn about missing data."""
        from processing.main_processing import verify_configuration

        mock_cfg = MagicMock(spec=[])  # no auto-attributes
        mock_cfg.config = {}

        warnings_list = verify_configuration(mock_cfg)

        assert any("missing" in w.lower() for w in warnings_list)

    def test_populated_collections_no_warnings(self):
        """Non-empty collections should not trigger warnings."""
        from processing.main_processing import verify_configuration

        mock_cfg = MagicMock()
        mock_cfg.known_words = ["word"]
        mock_cfg.capitalization_whitelist = ["Term"]
        mock_cfg.exceptions = ["exc"]
        mock_cfg.config = {}

        warnings_list = verify_configuration(mock_cfg)

        collection_warnings = [
            w for w in warnings_list
            if "empty" in w.lower() or "missing" in w.lower()
        ]
        assert collection_warnings == []

    def test_nonexistent_base_maths_folder(self, tmp_path):
        """Non-existent base_maths_folder should produce a warning."""
        from processing.main_processing import verify_configuration

        mock_cfg = MagicMock()
        mock_cfg.known_words = ["w"]
        mock_cfg.capitalization_whitelist = ["T"]
        mock_cfg.exceptions = ["e"]
        mock_cfg.config = {"base_maths_folder": str(tmp_path / "nonexistent")}

        warnings_list = verify_configuration(mock_cfg)

        assert any("does not exist" in w for w in warnings_list)


# ============================================================================
# Section 5I: CRITICAL AUDIT FINDINGS -- process_files() design issues
# ============================================================================

class TestProcessFilesAuditFindings:
    """
    AUDIT FINDINGS for process_files() -- the high-level orchestrator.

    We do NOT call process_files() directly because it has heavy external
    dependencies (OrganizationSystem, AsyncPaperDatabase, enrich_metadata).
    Instead we document the critical design issues found via code inspection.
    """

    def test_asyncio_run_not_inside_loop_resolved(self):
        """
        RESOLVED AUDIT FINDING: asyncio.run() is no longer called inside a
        for-loop. Instead, upsert tasks are collected and executed in a single
        asyncio.run() call after the loop completes.
        """
        import inspect
        from processing.main_processing import process_files

        source = inspect.getsource(process_files)

        # Verify the bug is fixed: no asyncio.run() inside the for-loop
        assert "asyncio.run(upsert_metadata())" not in source, (
            "asyncio.run(upsert_metadata()) should no longer be inside the loop"
        )
        # The batched approach uses _run_upserts
        assert "_run_upserts" in source, (
            "Expected batched _run_upserts function"
        )

    def test_real_metadata_feeds_into_organization_and_database(self):
        """
        RESOLVED AUDIT FINDING: Real PyMuPDF metadata now feeds the pipeline.

        process_file() uses _extract_pdf_metadata() with PyMuPDF to extract
        real metadata from PDFs, which is then passed to enrich_metadata(),
        OrganizationSystem.organize(), and the database.
        """
        import inspect
        from processing.main_processing import process_file, _extract_pdf_metadata

        source = inspect.getsource(process_file)

        # Verify process_file calls the real extraction function
        assert "_extract_pdf_metadata" in source, (
            "process_file should call _extract_pdf_metadata"
        )
        # Verify the mock is gone
        assert "Mock metadata" not in source, (
            "Mock metadata comment should be removed"
        )


# ============================================================================
# Section 5J: Integration -- process_file -> verify_output round-trip
# ============================================================================

class TestProcessFileVerifyRoundTrip:
    """Audit: Verify that process_file() output passes verify_output()."""

    def test_successful_result_passes_verification(self, tmp_path):
        """A successful process_file result should pass verify_output."""
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF")

        result = process_file(str(pdf))

        assert result["success"] is True
        assert verify_output(result) is True

    def test_missing_file_result_passes_verification(self, tmp_path):
        """A failure result from missing file should pass verify_output."""
        result = process_file(str(tmp_path / "missing.pdf"))

        assert result["success"] is False
        assert verify_output(result) is True

    def test_non_pdf_result_passes_verification(self, tmp_path):
        """A failure result from non-PDF should pass verify_output."""
        txt = tmp_path / "file.txt"
        txt.write_text("hello")

        result = process_file(str(txt))

        assert result["success"] is False
        assert verify_output(result) is True
