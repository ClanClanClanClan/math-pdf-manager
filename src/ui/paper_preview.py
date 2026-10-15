"""Reusable paper-preview helpers for the cockpit UI.

Each helper takes a Path to a PDF and returns a small dict suitable for
rendering in Streamlit. Nothing in here writes to the library; registry
and model answers met along the way are remembered under ~/.mathpdf/cache
(``processing.lookup_cache``).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
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
    #: Where the title came from: "arxiv", "crossref", "hal", "embedded"
    #: (the PDF's own metadata), "llm" (the local model) or "" (none).
    title_source: str = ""
    #: What each registry asked said: {"arxiv": {"state": "found" |
    #: "absent" | "unknown", "reason": "..."}, "crossref": {...}}.
    lookups: dict = field(default_factory=dict)


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
        title_source=meta.get("title_source") or "",
        lookups=dict(meta.get("lookups") or {}),
    )


#: Where a title can come from, in the owner's words.
_SOURCE_WORDS = {
    "arxiv": "arXiv",
    "crossref": "Crossref",
    "hal": "HAL",
    "embedded": "the PDF's own metadata",
    "llm": "the local AI model's reading of the first pages",
}
_REGISTRY_WORDS = {"arxiv": "arXiv", "crossref": "Crossref"}


def unsettled_lookups(prev: PaperPreview) -> list:
    """Registries that were asked about this paper and could not answer."""
    return [svc for svc in ("arxiv", "crossref")
            if (prev.lookups.get(svc) or {}).get("state") == "unknown"]


def name_source_note(prev: PaperPreview) -> tuple:
    """``(level, text)``: where the proposed name came from, plainly.

    ``level`` is "warning" when the owner should look harder before
    approving (a registry could not be asked, or the local model guessed
    the title), else "caption". "Could not be asked" and "has no such
    paper" are never worded alike: the first is retried, the second is
    an answer.
    """
    src = _SOURCE_WORDS.get(prev.title_source, "")
    from_where = src or "the file name (no title was found)"
    # A registry that could not answer cannot also be the title's source,
    # nor can one that answered "no such paper".
    for svc in unsettled_lookups(prev):
        why = (prev.lookups.get(svc) or {}).get("reason") or "no reason given"
        return ("warning",
                f"{_REGISTRY_WORDS[svc]} could not be checked: {why}. "
                f"This name comes from {from_where} instead. Check it, or "
                f"skip the paper and come back later.")
    for svc in ("arxiv", "crossref"):
        if (prev.lookups.get(svc) or {}).get("state") == "absent":
            return ("caption",
                    f"{_REGISTRY_WORDS[svc]} has no record of this paper, so "
                    f"this name comes from {from_where}.")
    if prev.title_source == "llm":
        return ("warning",
                "No title in the PDF or the registries: the local AI model "
                "read it from the first pages. Check it before approving.")
    if prev.title_source in ("arxiv", "crossref", "hal"):
        return ("caption", f"Title and authors from {src}.")
    return ("caption", f"Name from {from_where}.")
