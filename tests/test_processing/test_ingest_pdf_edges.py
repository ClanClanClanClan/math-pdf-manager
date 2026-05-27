"""Audit-8: PDF processing edge cases that the ingest pipeline used to swallow.

Covers:
  * Truncated / non-PDF files rejected at the magic-byte gate
  * Encrypted PDFs flagged via ``metadata["extraction_error"]``
  * Empty / zero-byte files handled gracefully

These cases used to land in the catch-all ``except Exception`` and
return an empty metadata dict indistinguishable from "no metadata
present", which then routed through the fall-back filename parser
and silently filed garbage.  The structured error field gives the
cockpit / watcher a chance to surface the failure.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from processing.ingest import extract_metadata_from_pdf


def test_non_pdf_rejected_by_magic_bytes(tmp_path):
    not_a_pdf = tmp_path / "fake.pdf"
    not_a_pdf.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG header
    meta = extract_metadata_from_pdf(not_a_pdf)
    assert meta["title"] == ""
    assert "extraction_error" in meta
    assert "magic" in meta["extraction_error"].lower()


def test_empty_file_rejected(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    meta = extract_metadata_from_pdf(empty)
    assert "extraction_error" in meta


def test_truncated_pdf_passes_magic_then_extracts_emptily(tmp_path):
    # Valid magic but no body -> PyMuPDF either raises or returns
    # an empty document.  Either way we shouldn't crash and the
    # metadata should be safely empty.
    truncated = tmp_path / "trunc.pdf"
    truncated.write_bytes(b"%PDF-1.4\n")
    meta = extract_metadata_from_pdf(truncated)
    # Empty dict OR error tag -- either is acceptable; the
    # important invariant is "no crash + caller can detect"
    assert meta["title"] == ""


def test_real_pdf_still_extracts(tmp_path):
    """Regression guard: the magic-byte check must NOT reject
    genuine PDFs that happen to have nothing else in them."""
    pdf = tmp_path / "real.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n"
        b"%%EOF\n"
    )
    meta = extract_metadata_from_pdf(pdf)
    # No extraction_error -- the magic-byte gate let it through.
    assert "extraction_error" not in meta


def test_encrypted_pdf_flagged(tmp_path, monkeypatch):
    """We can't easily craft a real encrypted PDF in a unit test;
    monkeypatch fitz.open to return a doc that claims to need a
    password.  The pipeline must surface this rather than treating
    it as "no metadata"."""
    pdf = tmp_path / "encrypted.pdf"
    pdf.write_bytes(b"%PDF-1.4\nfake body\n%%EOF\n")

    class FakeDoc:
        needs_pass = True
        is_encrypted = True
        metadata = {}
        def __len__(self):
            return 0
        def __getitem__(self, _):
            raise ValueError("encrypted")
        def close(self):
            pass

    import processing.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod.fitz, "open", lambda _p: FakeDoc())

    meta = extract_metadata_from_pdf(pdf)
    assert "extraction_error" in meta
    assert "encrypt" in meta["extraction_error"].lower()


def test_canonical_filename_nfc_normalizes_authors():
    """Audit-8 #1: author segments must be NFC-normalised so byte-
    truncation in _build_with_max_authors is deterministic regardless
    of input form (precomposed vs combining-mark)."""
    from arxivbot.models.cmo import CMO, Author
    import unicodedata
    # "Möbius" precomposed (U+00F6) vs decomposed (M + o + U+0308)
    nfc = "Möbius"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd  # they're distinct strings until normalised

    cmo_nfc = CMO(
        external_id="x1", source="test",
        title="On something elegant",
        authors=[Author(family=nfc, given="A.")],
    )
    cmo_nfd = CMO(
        external_id="x2", source="test",
        title="On something elegant",
        authors=[Author(family=nfd, given="A.")],
    )
    assert cmo_nfc.get_canonical_filename() == cmo_nfd.get_canonical_filename()
