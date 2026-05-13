"""Reusable paper-preview helpers for the cockpit UI.

Each helper takes a Path to a PDF and returns a small dict suitable for
rendering in Streamlit. Nothing in here writes to disk or to the library.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PaperPreview:
    """Lightweight render-ready snapshot of a PDF's first page."""

    pdf_path: Path
    canonical_filename: str = ""
    title: str = ""
    authors: str = ""
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    year: Optional[int] = None
    first_page_text: str = ""
    error: Optional[str] = None


def preview_pdf(pdf_path: Path, *, first_page_chars: int = 800) -> PaperPreview:
    """Build a PaperPreview for the given PDF.

    Runs the standard ingest pipeline (no file writes) to compute the
    canonical filename + extracted metadata, plus a snippet of first-page
    text so the user can eyeball the paper without opening it.
    """
    if not pdf_path.exists():
        return PaperPreview(pdf_path=pdf_path, error=f"file not found: {pdf_path}")
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        return PaperPreview(pdf_path=pdf_path, error=f"not a PDF: {pdf_path}")

    try:
        from processing.ingest import extract_metadata_from_pdf, metadata_to_cmo
        meta = extract_metadata_from_pdf(pdf_path)
        cmo = metadata_to_cmo(meta, pdf_path)
    except Exception as exc:
        logger.exception("Metadata extraction failed for %s", pdf_path)
        return PaperPreview(pdf_path=pdf_path, error=f"metadata extraction: {exc}")

    # First-page text snippet
    snippet = ""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            snippet = doc[0].get_text("text")[:first_page_chars]
        doc.close()
    except Exception as exc:
        logger.debug("First-page extraction failed for %s: %s", pdf_path, exc)

    try:
        canonical = cmo.get_canonical_filename()
    except Exception as exc:
        canonical = pdf_path.name
        logger.warning("Canonical filename failed for %s: %s", pdf_path, exc)

    return PaperPreview(
        pdf_path=pdf_path,
        canonical_filename=canonical,
        title=cmo.title or "",
        authors=", ".join(a.display_name() for a in cmo.authors),
        doi=meta.get("doi"),
        arxiv_id=meta.get("arxiv_id"),
        year=meta.get("year"),
        first_page_text=snippet,
    )
