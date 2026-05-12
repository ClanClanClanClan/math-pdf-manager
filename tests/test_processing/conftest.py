"""Shared fixtures for the processing test suite.

We build a synthetic library tree under tmp_path so tests can exercise the
filing pipeline without touching the user's real Dropbox.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def make_minimal_pdf(path: Path, *, body: bytes = b"hello") -> Path:
    """Write a minimal valid PDF for tests that just need a file PyMuPDF
    can open (returning empty metadata, exercising the fall-back paths)."""
    minimal = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<<>>\nendobj\n"
        b"trailer\n<<>>\n"
        b"%%EOF\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(minimal)
    return path


@pytest.fixture
def make_pdf():
    """Provide make_minimal_pdf as a fixture for tests that prefer that style."""
    return make_minimal_pdf


@pytest.fixture
def synthetic_library(tmp_path):
    """Build a minimal mirror of the real library structure under tmp_path.

    Includes:
      01 - Published papers/  (with A-Z subfolders pre-created on demand)
      02 - Unpublished papers/
      03 - Working papers/
      04 - Papers to be downloaded/
      05 - Books and lecture notes/
      06 - Theses/
      07a - BSDEs/
      08 - Séminaires de probabilités de Strasbourg/
      12 - To be sorted/
        01 - Published papers/
        03 - Working papers/
        05 - Books and lecture notes/
    """
    folders = [
        "01 - Published papers",
        "02 - Unpublished papers",
        "03 - Working papers",
        "04 - Papers to be downloaded",
        "04 - Papers to be downloaded/Not fully published version",
        "05 - Books and lecture notes",
        "06 - Theses",
        "07a - BSDEs",
        "08 - Séminaires de probabilités de Strasbourg",
        "12 - To be sorted",
        "12 - To be sorted/01 - Published papers",
        "12 - To be sorted/03 - Working papers",
        "12 - To be sorted/05 - Books and lecture notes",
    ]
    for f in folders:
        (tmp_path / f).mkdir(parents=True, exist_ok=True)
    return tmp_path


def make_minimal_pdf(path: Path, *, body: bytes = b"hello") -> Path:
    """Write a minimal valid PDF to ``path`` for tests that just need a file
    that PyMuPDF can open without crashing."""
    # A real PDF needs more structure than just a header, but the bare
    # ``%PDF-1.4`` prefix + an EOF marker is enough that ``fitz.open`` will
    # not blow up; metadata extraction will return empty fields, which is
    # exactly what we want for testing fall-back paths.
    minimal = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<<>>\nendobj\n"
        b"trailer\n<<>>\n"
        b"%%EOF\n"
    )
    path.write_bytes(minimal)
    return path
