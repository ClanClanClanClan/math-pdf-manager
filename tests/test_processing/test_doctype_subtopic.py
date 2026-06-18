"""Document-type detection + sub-subtopic routing."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


# ---------------------------------------------------------------------------
# Document-type classifier
# ---------------------------------------------------------------------------

class TestDocType:

    def test_thesis_by_filename(self):
        from processing.doctype_classifier import classify_document_type
        d = classify_document_type("Dupont, A. - A PhD thesis on rough paths.pdf")
        assert d.kind == "thesis"
        assert d.folder == "06 - Theses"

    def test_dissertation_word(self):
        from processing.doctype_classifier import classify_document_type
        assert classify_document_type("Smith - Doctoral dissertation.pdf").kind == "thesis"

    def test_book_lecture_notes(self):
        from processing.doctype_classifier import classify_document_type
        d = classify_document_type("Lions - Lecture notes on mean field games.pdf")
        assert d.kind == "book"
        assert d.folder == "05 - Books and lecture notes"

    def test_book_introduction_to(self):
        from processing.doctype_classifier import classify_document_type
        assert classify_document_type("X - An introduction to malliavin calculus.pdf").kind == "book"

    def test_isbn_makes_book(self):
        from processing.doctype_classifier import classify_document_type
        d = classify_document_type("X - Some title.pdf", has_isbn=True)
        assert d.kind == "book"

    def test_long_pagecount_book(self):
        from processing.doctype_classifier import classify_document_type
        d = classify_document_type("X - Some title.pdf", page_count=300)
        assert d.kind == "book"

    def test_ordinary_article(self):
        from processing.doctype_classifier import classify_document_type
        d = classify_document_type("Smith, J. - Reflected BSDEs and optimal stopping.pdf",
                                   page_count=28)
        assert d.kind == "article"
        assert d.folder is None

    def test_thesis_beats_book_signal(self):
        from processing.doctype_classifier import classify_document_type
        d = classify_document_type("X - PhD thesis: lecture notes approach.pdf")
        assert d.kind == "thesis"

    def test_current_doc_bucket(self, tmp_path):
        from processing.doctype_classifier import current_doc_bucket
        assert current_doc_bucket(
            tmp_path / "06 - Theses" / "S" / "x.pdf", tmp_path) == "thesis"
        assert current_doc_bucket(
            tmp_path / "05 - Books and lecture notes" / "x.pdf", tmp_path) == "book"
        assert current_doc_bucket(
            tmp_path / "01 - Published papers" / "S" / "x.pdf", tmp_path) == "article"
        assert current_doc_bucket(
            tmp_path / "12 - To be sorted" / "x.pdf", tmp_path) is None


# ---------------------------------------------------------------------------
# Sub-subtopic router
# ---------------------------------------------------------------------------

class TestSubtopic:

    def _make_topic(self, root):
        # Mirror the real 07a layout: status folders + sub-subtopics.
        topic = root / "07a - BSDEs"
        for d in ["01 - Published papers", "07a - Numerical methods",
                  "07b - 2BSDEs", "07c - G-BSDEs"]:
            (topic / d).mkdir(parents=True)
        return topic

    def test_discover_subtopics(self, tmp_path):
        from processing.subtopic_classifier import discover_subtopics
        topic = self._make_topic(tmp_path)
        subs = discover_subtopics(topic)
        labels = {label for _, label in subs}
        assert labels == {"Numerical methods", "2BSDEs", "G-BSDEs"}
        # Status folders are NOT sub-subtopics.
        assert all("Published" not in label for _, label in subs)

    def test_classify_numerical(self, tmp_path):
        from processing.subtopic_classifier import discover_subtopics, classify_subtopic
        subs = discover_subtopics(self._make_topic(tmp_path))
        d = classify_subtopic(
            "A deep learning scheme for numerical simulation of BSDEs", "", subs)
        assert d is not None and d.label == "Numerical methods"

    def test_classify_gbsde(self, tmp_path):
        from processing.subtopic_classifier import discover_subtopics, classify_subtopic
        subs = discover_subtopics(self._make_topic(tmp_path))
        d = classify_subtopic("G-expectation and G-Brownian motion", "", subs)
        assert d is not None and d.label == "G-BSDEs"

    def test_no_match_returns_none(self, tmp_path):
        from processing.subtopic_classifier import discover_subtopics, classify_subtopic
        subs = discover_subtopics(self._make_topic(tmp_path))
        assert classify_subtopic("Reflected equations and optimal stopping", "", subs) is None

    def test_no_subtopics_returns_none(self, tmp_path):
        from processing.subtopic_classifier import classify_subtopic
        assert classify_subtopic("anything numerical", "", []) is None

    def test_resolve_subtopic_end_to_end(self, tmp_path):
        from processing.subtopic_classifier import resolve_subtopic
        self._make_topic(tmp_path)
        pdf = (tmp_path / "07a - BSDEs" / "07a - Numerical methods"
               / "01 - Published papers" / "X - Deep BSDE solver scheme.pdf")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(pdf, title="t", author="X")
        d = resolve_subtopic(pdf, "07a", tmp_path)
        assert d is not None and d.label == "Numerical methods"
