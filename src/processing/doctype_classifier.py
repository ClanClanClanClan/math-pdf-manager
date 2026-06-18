#!/usr/bin/env python3
"""Document-type detection: article vs book/lecture-notes vs thesis.

The library separates ordinary articles (status folders 01–03) from
books & lecture notes ("05 - Books and lecture notes") and theses
("06 - Theses") — at the top level AND inside every topic folder.  A
book or thesis dropped into a paper folder is a misfiling; this module
flags it.

Library-scale and read-only by design: it classifies from the curated
filename plus optional sidecar signals (page count, ISBN) and never
parses the PDF.  It is deliberately conservative — it only returns
``book``/``thesis`` when the evidence is clear, otherwise ``article`` —
because the cost of dragging a real paper into the books folder is worse
than leaving a book unflagged for the user to catch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Folder names this maps onto.
BOOK_FOLDER = "05 - Books and lecture notes"
THESIS_FOLDER = "06 - Theses"

# Strong thesis signals in the filename (word-boundary, case-insensitive).
_THESIS_PATTERNS = [
    r"\bthesis\b", r"\btheses\b", r"\bdissertation\b", r"\bdoctoral\b",
    r"\bph\.?\s?d\.?\b", r"\bd\.?phil\b", r"\bhabilitation\b",
    r"\bhabilitationsschrift\b", r"\bmémoire\b", r"\bmemoire\b",
    r"\bmaster'?s thesis\b", r"\bdiplomarbeit\b", r"\btesi\b",
]

# Strong book / lecture-notes signals.
_BOOK_PATTERNS = [
    r"\blecture notes\b", r"\blectures on\b", r"\bnotes on\b",
    r"\ban introduction to\b", r"\bintroduction to\b", r"\ba course\b",
    r"\bcourse on\b", r"\bcourse in\b", r"\bhandbook\b", r"\bencyclop-?a?edia\b",
    r"\btextbook\b", r"\bmonograph\b", r"\bgrundlehren\b",
    r"\bgraduate texts\b", r"\bspringer (?:lecture notes|monographs)\b",
    r"\bcambridge (?:studies|tracts)\b", r"\bde gruyter\b",
    r"\bbook\b", r"\bvolume\b",
]

_THESIS_RE = re.compile("|".join(_THESIS_PATTERNS), re.IGNORECASE)
_BOOK_RE = re.compile("|".join(_BOOK_PATTERNS), re.IGNORECASE)

# Page-count heuristics (only used when a sidecar carries the count).
_BOOK_PAGES = 120        # >= this many pages strongly suggests a book/thesis
_ARTICLE_PAGES = 60      # < this is firmly article territory


@dataclass
class DocTypeDecision:
    kind: str               # "article" | "book" | "thesis"
    confidence: float       # 0..1
    reason: str             # human-readable signal that fired

    @property
    def folder(self) -> Optional[str]:
        """Top-level (and per-topic) folder this kind belongs in, or
        None for an ordinary article (which keeps its status folder)."""
        if self.kind == "book":
            return BOOK_FOLDER
        if self.kind == "thesis":
            return THESIS_FOLDER
        return None

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


def classify_document_type(
    filename: str,
    *,
    page_count: Optional[int] = None,
    has_isbn: bool = False,
) -> DocTypeDecision:
    """Best-effort document-type from the filename + optional metadata.

    ``filename`` may be a full name or stem; only the text matters.
    """
    stem = Path(filename).stem

    # Thesis signals win over book signals (a "PhD thesis on ... lecture
    # notes" is still a thesis).
    if _THESIS_RE.search(stem):
        conf = 0.85
        reason = "filename mentions thesis/dissertation"
        if page_count is not None and page_count >= _BOOK_PAGES:
            conf = 0.95
            reason += f" + {page_count} pages"
        return DocTypeDecision("thesis", conf, reason)

    book_hit = _BOOK_RE.search(stem)
    if book_hit:
        conf = 0.8
        reason = f"filename signal: {book_hit.group(0)!r}"
        if has_isbn:
            conf = 0.95
            reason += " + ISBN"
        elif page_count is not None and page_count >= _BOOK_PAGES:
            conf = 0.92
            reason += f" + {page_count} pages"
        return DocTypeDecision("book", conf, reason)

    # No filename signal — fall back to corroborating metadata only.
    if has_isbn:
        return DocTypeDecision("book", 0.7, "ISBN present")
    if page_count is not None and page_count >= _BOOK_PAGES:
        # Long with no thesis wording -> most likely a book.
        return DocTypeDecision("book", 0.65, f"{page_count} pages (long)")

    return DocTypeDecision("article", 0.9, "no book/thesis signal")


# ---------------------------------------------------------------------------
# Current-location helpers for mismatch detection
# ---------------------------------------------------------------------------

# Standard status folder prefixes for the three "article" buckets and the
# two document-type buckets.
_ARTICLE_STATUS_RE = re.compile(r"^0[123] - ")
_BOOK_STATUS_RE = re.compile(r"^05 - ")
_THESIS_STATUS_RE = re.compile(r"^06 - ")


def current_doc_bucket(pdf_path: Path, library_root: Path) -> Optional[str]:
    """Which document-type bucket the paper currently lives in, by path.

    Returns ``"article"`` (under 01/02/03), ``"book"`` (under a 05
    folder), ``"thesis"`` (under a 06 folder), or ``None`` if it sits
    somewhere else (e.g. the inbox or 04)."""
    try:
        rel = pdf_path.relative_to(library_root)
    except ValueError:
        rel = pdf_path
    for part in rel.parts:
        if _BOOK_STATUS_RE.match(part):
            return "book"
        if _THESIS_STATUS_RE.match(part):
            return "thesis"
        if _ARTICLE_STATUS_RE.match(part):
            return "article"
    return None
