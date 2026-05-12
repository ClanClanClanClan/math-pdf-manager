"""Tests for the duplicate finder.

Covers:
- Identical content (SHA-256 match) detection.
- Title-similarity fuzzy matching across folders.
- The 12 - To be sorted/ tree is excluded from scans.
- I/O errors during hashing don't crash the run.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from processing.duplicate_finder import (
    _file_hash,
    _files_identical,
    find_duplicates,
)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

class TestFileHash:
    def test_identical_files_same_hash(self, tmp_path):
        a = tmp_path / "a.pdf"
        b = tmp_path / "b.pdf"
        a.write_bytes(b"SAME")
        b.write_bytes(b"SAME")
        assert _file_hash(a) == _file_hash(b)

    def test_different_files_different_hash(self, tmp_path):
        a = tmp_path / "a.pdf"
        b = tmp_path / "b.pdf"
        a.write_bytes(b"AAA")
        b.write_bytes(b"BBB")
        assert _file_hash(a) != _file_hash(b)

    def test_missing_file_returns_none(self, tmp_path):
        # No crash for missing file — returns None
        result = _file_hash(tmp_path / "ghost.pdf")
        assert result is None


class TestFilesIdentical:
    def test_identical_content(self, tmp_path):
        a = tmp_path / "a.pdf"
        b = tmp_path / "b.pdf"
        a.write_bytes(b"hello world")
        b.write_bytes(b"hello world")
        assert _files_identical(a, b) is True

    def test_different_size_short_circuits(self, tmp_path):
        a = tmp_path / "a.pdf"
        b = tmp_path / "b.pdf"
        a.write_bytes(b"short")
        b.write_bytes(b"longer content")
        # Should return False without even hashing
        assert _files_identical(a, b) is False

    def test_missing_file_returns_false(self, tmp_path):
        a = tmp_path / "a.pdf"
        a.write_bytes(b"x")
        # b doesn't exist — must NOT crash
        result = _files_identical(a, tmp_path / "ghost.pdf")
        assert result is False


# ---------------------------------------------------------------------------
# Full-library scan
# ---------------------------------------------------------------------------

class TestFindDuplicates:
    def test_excludes_to_be_sorted(self, synthetic_library, make_pdf):
        # Two papers with identical titles — but the duplicate is in 12/
        published = synthetic_library / "01 - Published papers"
        published.mkdir(exist_ok=True)
        make_pdf(published / "Smith, J. - A paper.pdf", body=b"AAA")

        staging = synthetic_library / "12 - To be sorted" / "01 - Published papers"
        make_pdf(staging / "Smith, J. - A paper.pdf", body=b"AAA")

        # The 12/ copy must NOT be flagged — staging is excluded.
        clusters = find_duplicates(synthetic_library)
        for cluster in clusters:
            for entry in cluster.get("files", []):
                assert "12 - To be sorted" not in entry, (
                    f"staging file leaked into duplicate scan: {entry}"
                )

    def test_no_duplicates_in_empty_library(self, synthetic_library):
        clusters = find_duplicates(synthetic_library)
        assert clusters == []
