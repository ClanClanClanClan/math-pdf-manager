"""Tests for paper_index location classification.

The classifier converts a path under the library into a structured
{type, folder, ...} record. Edge cases include topic folders without
status subfolders (07a/x.pdf) and the 12 - To be sorted/ staging area.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from processing.paper_index import _classify_location


@pytest.fixture
def lib(synthetic_library):
    return synthetic_library


def _classify(lib, *parts):
    """Helper: build a path under lib and run the classifier."""
    p = lib.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF")
    return _classify_location(p, lib)


class TestStatusFolders:
    def test_published(self, lib):
        r = _classify(lib, "01 - Published papers", "A", "Smith, J. - X.pdf")
        assert r["type"] == "published"

    def test_unpublished(self, lib):
        r = _classify(lib, "02 - Unpublished papers", "B", "Brown, A. - X.pdf")
        assert r["type"] == "unpublished"

    def test_working(self, lib):
        r = _classify(lib, "03 - Working papers", "C", "2020", "C, X. - X.pdf")
        assert r["type"] == "working"

    def test_book(self, lib):
        r = _classify(lib, "05 - Books and lecture notes", "Föllmer.pdf")
        assert r["type"] == "book"

    def test_thesis(self, lib):
        r = _classify(lib, "06 - Theses", "PhD.pdf")
        assert r["type"] == "thesis"

    def test_to_download(self, lib):
        r = _classify(lib, "04 - Papers to be downloaded", "Some Journal", "x.pdf")
        assert r["type"] == "to_download"


class TestTopicFolders:
    def test_topic_with_status_subfolder(self, lib):
        # File under 07a - BSDEs/01 - Published papers/A/x.pdf
        r = _classify(lib, "07a - BSDEs", "01 - Published papers", "A", "x.pdf")
        assert r["type"] == "published"
        assert r["is_topic"] is True

    def test_topic_with_direct_file(self, lib):
        # File directly under 07a - BSDEs/x.pdf — used to be misclassified
        # as "other" but should now be "topic".
        r = _classify(lib, "07a - BSDEs", "direct.pdf")
        assert r["type"] == "topic"
        assert r["is_topic"] is True


class TestToBeSortedFolder:
    def test_to_be_sorted_root(self, lib):
        # Files under 12/01/ should be flagged for the bulk_sort tool, not
        # treated as already-published.
        r = _classify(lib, "12 - To be sorted", "01 - Published papers", "raw.pdf")
        assert r["type"] == "to_be_sorted"
        assert r["hinted_status"] == "01 - Published papers"


class TestEdgeCases:
    def test_outside_library_returns_unknown(self, lib, tmp_path_factory):
        # File outside the library entirely
        outside_dir = tmp_path_factory.mktemp("not_lib")
        outside = outside_dir / "elsewhere.pdf"
        outside.write_bytes(b"%PDF")
        r = _classify_location(outside, lib)
        assert r["type"] == "unknown"

    def test_unrecognized_top_folder(self, lib):
        r = _classify(lib, "99 - Unknown", "x.pdf")
        assert r["type"] == "other"
