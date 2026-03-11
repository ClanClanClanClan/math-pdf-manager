#!/usr/bin/env python3
"""
Metadata Extraction Facade
===========================

Single entry-point for extracting metadata from a PDF file.

This module wraps the :class:`EnhancedPDFParser` (5-method pipeline) behind a
simple function call so that both ``main_async.py`` and
``main_processing.py`` can use the full extraction stack without
duplicating initialisation logic.

Thread-safety is ensured via a module-level lock guarding the singleton
parser instance.  The function is synchronous (it does blocking I/O) so
callers in async contexts should use ``run_in_executor``.
"""

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton for EnhancedPDFParser
# ---------------------------------------------------------------------------
_parser_lock = threading.Lock()
_parser_instance = None


def _get_parser():
    """Return a module-level EnhancedPDFParser singleton (thread-safe)."""
    global _parser_instance
    if _parser_instance is not None:
        return _parser_instance

    with _parser_lock:
        # Double-checked locking
        if _parser_instance is not None:
            return _parser_instance

        try:
            from pdf_processing.parsers.enhanced_parser import EnhancedPDFParser
            _parser_instance = EnhancedPDFParser()
            logger.info("EnhancedPDFParser singleton initialised")
        except Exception as e:
            logger.warning(f"Failed to initialise EnhancedPDFParser: {e}")
            _parser_instance = None

    return _parser_instance


# ---------------------------------------------------------------------------
# Filename-based fallback (the old logic from main_async.py)
# ---------------------------------------------------------------------------
def _extract_from_filename(pdf_path: Path) -> Dict[str, Any]:
    """Best-effort metadata from the filename alone."""
    filename = pdf_path.stem

    title = filename
    authors: List[str] = []
    year: Optional[int] = None
    arxiv_id: Optional[str] = None

    # Try "Author1, Author2 - Title" pattern
    if " - " in filename:
        authors_part, title_part = filename.split(" - ", 1)
        authors = [a.strip() for a in re.split(r"\s+and\s+|,\s*", authors_part) if a.strip()]
        title = title_part.strip()

    # Try to detect arXiv ID in filename
    m = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", filename)
    if m:
        arxiv_id = m.group(1)

    # Try to detect DOI encoded in filename (10.XXXX_suffix)
    doi = None
    try:
        from pdf_processing.parsers.metadata_quality import extract_doi_from_filename
        doi = extract_doi_from_filename(pdf_path.name)
    except ImportError:
        pass

    # Try to detect SSRN ID in filename
    ssrn_id = None
    try:
        from pdf_processing.parsers.metadata_quality import extract_ssrn_id_from_filename
        ssrn_id = extract_ssrn_id_from_filename(pdf_path.name)
    except ImportError:
        pass

    # Try to detect year
    m = re.search(r"\b((?:19|20)\d{2})\b", filename)
    if m:
        year = int(m.group(1))

    return {
        "title": title or "Unknown Title",
        "authors": authors,
        "year": year,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "abstract": None,
        "confidence": 0.2,
        "source_method": "filename",
    }


# ---------------------------------------------------------------------------
# Public facade
# ---------------------------------------------------------------------------
def extract_pdf_metadata_enhanced(
    pdf_path: Path,
    *,
    offline: bool = False,
    use_llm: bool = False,
) -> Dict[str, Any]:
    """Extract metadata from *pdf_path* using the full extraction pipeline.

    Returns a plain ``dict`` with keys:

    - ``title`` (str)
    - ``authors`` (list[str])
    - ``year`` (int | None)
    - ``doi`` (str | None)
    - ``arxiv_id`` (str | None)
    - ``abstract`` (str | None)
    - ``confidence`` (float, 0–1)
    - ``source_method`` (str — e.g. ``"arxiv_api"``, ``"heuristic"``, …)

    Falls back to filename parsing when the enhanced parser is unavailable
    or raises an unexpected error.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists() or not pdf_path.is_file():
        logger.warning(f"PDF not found: {pdf_path}")
        return _extract_from_filename(pdf_path)

    parser = _get_parser()
    if parser is None:
        logger.debug("EnhancedPDFParser not available, using filename fallback")
        return _extract_from_filename(pdf_path)

    try:
        metadata = parser.extract_metadata(
            str(pdf_path),
            use_llm=use_llm,
        )

        # Convert PDFMetadata → plain dict
        # Parse authors string into a list
        authors_str = metadata.authors or ""
        if authors_str and authors_str != "Unknown":
            authors = [a.strip() for a in authors_str.split(";") if a.strip()]
        else:
            authors = []

        # Try to extract year from published date or other fields
        year = None
        if hasattr(metadata, "published") and metadata.published:
            m = re.search(r"((?:19|20)\d{2})", str(metadata.published))
            if m:
                year = int(m.group(1))

        confidence = metadata.confidence if metadata.confidence else 0.0
        source_method = metadata.extraction_method or "unknown"

        result = {
            "title": metadata.title or "Unknown Title",
            "authors": authors,
            "year": year,
            "doi": metadata.doi,
            "arxiv_id": metadata.arxiv_id,
            "abstract": metadata.abstract,
            "confidence": confidence,
            "source_method": source_method,
        }

        # If confidence is very low, supplement with filename info
        if confidence < 0.4:
            filename_meta = _extract_from_filename(pdf_path)
            if not authors and filename_meta["authors"]:
                result["authors"] = filename_meta["authors"]
            if result["title"] in ("Unknown Title", "") and filename_meta["title"]:
                result["title"] = filename_meta["title"]
            if result["arxiv_id"] is None and filename_meta["arxiv_id"]:
                result["arxiv_id"] = filename_meta["arxiv_id"]

        logger.debug(
            f"Extracted metadata for {pdf_path.name}: "
            f"title='{result['title'][:60]}…' method={source_method} "
            f"confidence={confidence:.2f}"
        )
        return result

    except Exception as e:
        logger.error(f"Enhanced extraction failed for {pdf_path}: {e}")
        return _extract_from_filename(pdf_path)
