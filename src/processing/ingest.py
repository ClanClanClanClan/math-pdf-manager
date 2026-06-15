#!/usr/bin/env python3
"""Ingest a new PDF into the library.

Extracts metadata, generates the canonical filename, and files the paper
in the correct directory.

Usage::

    python -m processing.ingest paper.pdf
    python -m processing.ingest paper.pdf --status published
    python -m processing.ingest paper.pdf --topic 07a
    python -m processing.ingest paper.pdf --dry-run
    python -m processing.ingest *.pdf --status working --year 2025
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Optional, Set

import fitz  # PyMuPDF

from arxivbot.models.cmo import Author, CMO
from organization.system import OrganizationSystem
from processing.undo_log import UndoLog

logger = logging.getLogger(__name__)

# Default library root — resolved via ``core.config_paths.get_library_root``
# so the user-specific Dropbox path lives in only one place (constants.py).
from core.config_paths import get_library_root as _get_library_root
LIBRARY_ROOT = _get_library_root()


# ---------------------------------------------------------------------------
# LaTeX-to-Unicode (PDF metadata frequently stores raw LaTeX source)
# ---------------------------------------------------------------------------
# Combining-mark mapping for one-char accent commands like \^o, \'e, \"o:
_LATEX_ACCENT_TO_COMBINING = {
    "^": "̂",   # COMBINING CIRCUMFLEX ACCENT (\^o → ô)
    "'": "́",   # COMBINING ACUTE          (\'e → é)
    "`": "̀",   # COMBINING GRAVE          (\`a → à)
    '"': "̈",   # COMBINING DIAERESIS      (\"o → ö)
    "~": "̃",   # COMBINING TILDE          (\~n → ñ)
    ".": "̇",   # COMBINING DOT ABOVE      (\.z → ż)
    "=": "̄",   # COMBINING MACRON         (\=o → ō)
}
# Multi-letter accent commands of form \c{X}, \v{X}, \u{X}, \r{X}, etc.
_LATEX_MULTILETTER_ACCENTS = {
    "c": "̧",   # COMBINING CEDILLA        (\c{c} → ç)
    "v": "̌",   # COMBINING CARON          (\v{s} → š)
    "u": "̆",   # COMBINING BREVE          (\u{g} → ğ)
    "r": "̊",   # COMBINING RING ABOVE     (\r{a} → å)
    "k": "̨",   # COMBINING OGONEK         (\k{a} → ą)
    "H": "̋",   # COMBINING DOUBLE ACUTE   (\H{o} → ő)
}
# Special-character commands (no argument)
_LATEX_SPECIAL_CHARS = {
    r"\o ": "ø", r"\O ": "Ø",
    r"\o}": "ø}", r"\O}": "Ø}",
    r"\ss": "ß",
    r"\ae": "æ", r"\AE": "Æ",
    r"\oe": "œ", r"\OE": "Œ",
    r"\l ": "ł", r"\L ": "Ł",
    r"\aa": "å", r"\AA": "Å",
    r"\&": "&",
    r"\%": "%",
    r"\$": "$",
    r"\#": "#",
    r"\_": "_",
    r"{\textemdash}": "—",
    r"{\textendash}": "–",
    r"\textemdash": "—",
    r"\textendash": "–",
    r"\textquotedblleft": "“",
    r"\textquotedblright": "”",
    r"\textquoteleft": "‘",
    r"\textquoteright": "’",
}

# Patterns for accent commands. Three forms:
#   \^o     (one-char accent, no braces)
#   \^{o}   (one-char accent, with braces)
#   \c{c}   (multi-letter accent name in braces)
_LATEX_ACCENT_RE = re.compile(
    r"\\([\^'`\"~.=])\{?([a-zA-Z])\}?"
)
_LATEX_MULTILETTER_RE = re.compile(
    r"\\([cvurkH])\{([a-zA-Z])\}"
)


def _unlatex(text: str) -> str:
    """Convert common LaTeX commands to their Unicode equivalents.

    PDF metadata fields in academic papers frequently contain raw LaTeX
    source (e.g. title="Stochastic It\\^o equations"). This function
    converts that to clean Unicode ("Stochastic Itô equations") so
    sentence case and filing logic don't get tripped up.

    Conservative: only handles well-known accent commands and a small set
    of special characters. Anything unrecognised is left as-is.
    """
    if not text or "\\" not in text:
        return text

    def _accent_replace(m: "re.Match[str]") -> str:
        combining = _LATEX_ACCENT_TO_COMBINING.get(m.group(1))
        if combining is None:
            return m.group(0)
        return unicodedata.normalize("NFC", m.group(2) + combining)

    def _multiletter_replace(m: "re.Match[str]") -> str:
        combining = _LATEX_MULTILETTER_ACCENTS.get(m.group(1))
        if combining is None:
            return m.group(0)
        return unicodedata.normalize("NFC", m.group(2) + combining)

    text = _LATEX_ACCENT_RE.sub(_accent_replace, text)
    text = _LATEX_MULTILETTER_RE.sub(_multiletter_replace, text)

    # Multi-character special commands (longest-first so e.g. \aa before \a)
    for cmd, char in sorted(_LATEX_SPECIAL_CHARS.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(cmd, char)

    return text


# ---------------------------------------------------------------------------
# Metadata extraction (lightweight — uses PyMuPDF + filename heuristics)
# ---------------------------------------------------------------------------
def extract_metadata_from_pdf(pdf_path: Path) -> dict:
    """Extract basic metadata from a PDF file.

    Tries embedded PDF metadata first, then falls back to the LLM extractor
    if available, then to filename parsing.

    Audit-8 defensive add: refuses to even open files that don't
    start with the PDF magic bytes (truncated downloads, accidental
    .pdf-renamed images) and surfaces password-protected PDFs as a
    structured warning rather than swallowing the failure into an
    empty metadata dict.
    """
    metadata = {"title": "", "authors": [], "doi": None, "arxiv_id": None, "year": None}

    # Magic-byte check.  A truncated browser download often ends as a
    # partial PDF with the trailer missing -- ``fitz.open`` will
    # cheerfully return an "empty document" instead of raising.  By
    # rejecting non-PDF magic up front we avoid silently filing
    # garbage.
    try:
        with open(pdf_path, "rb") as _f:
            magic = _f.read(5)
    except OSError as exc:
        logger.warning("Cannot read PDF %s: %s", pdf_path, exc)
        metadata["extraction_error"] = f"cannot read: {exc}"
        return metadata
    if not magic.startswith(b"%PDF-"):
        logger.warning(
            "File %s does not start with %%PDF- magic bytes "
            "(got %r); skipping metadata extraction",
            pdf_path, magic,
        )
        metadata["extraction_error"] = "not a PDF (missing magic bytes)"
        return metadata

    try:
        doc = fitz.open(pdf_path)
        # Encrypted / password-protected PDFs: PyMuPDF returns a doc
        # object but most operations fail until ``authenticate``
        # succeeds.  Flag the condition so the watcher / cockpit can
        # surface "please unlock me" rather than dropping the paper
        # into the catch-all "no metadata" fallback.
        if getattr(doc, "needs_pass", False) or getattr(doc, "is_encrypted", False):
            logger.warning(
                "PDF %s is encrypted / password-protected; skipping extraction",
                pdf_path,
            )
            metadata["extraction_error"] = "encrypted PDF (needs password)"
            doc.close()
            return metadata
        pdf_meta = doc.metadata or {}

        # Extract title from PDF metadata. PDF title fields commonly hold
        # raw LaTeX source (e.g. "It\^o" instead of "Itô"); convert before
        # any downstream processing.
        title = (pdf_meta.get("title") or "").strip()
        if title and len(title) > 5:
            metadata["title"] = unicodedata.normalize("NFC", _unlatex(title))

        # Extract author from PDF metadata (same LaTeX cleanup applies)
        author_str = (pdf_meta.get("author") or "").strip()
        if author_str:
            metadata["authors_raw"] = _unlatex(author_str)

        # Embedded PDF keywords (publishers often set these) -- a strong
        # topic-classification signal alongside the title.
        kw = (pdf_meta.get("keywords") or "").strip()
        if kw:
            metadata["keywords"] = _unlatex(kw)

        # Check for DOI in first few pages
        text = ""
        for page_num in range(min(3, len(doc))):
            text += doc[page_num].get_text()

        # Stash a bounded sample of the front-matter text so topic
        # classification can look at the abstract/intro, not just the
        # title (the user's C1 point: topic should consider title +
        # keywords + abstract + body).  Bounded to keep the metadata
        # dict and any logging small.
        if text:
            metadata["fulltext_sample"] = text[:4000]

        # DOI detection
        doi_match = re.search(r"\b(10\.\d{4,}/\S+)", text)
        if doi_match:
            doi = doi_match.group(1).rstrip(".")
            metadata["doi"] = doi

        # ArXiv ID detection (new format: 2401.07160v3, old format: math/0601234)
        arxiv_match = re.search(
            r"arXiv[:\s]*(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+/\d{7}(?:v\d+)?)", text
        )
        if arxiv_match:
            metadata["arxiv_id"] = arxiv_match.group(1)

        # Year detection
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", pdf_meta.get("creationDate", ""))
        if year_match:
            year_val = int(year_match.group(1))
            from datetime import datetime as _dt
            if 1900 <= year_val <= _dt.now().year:
                metadata["year"] = year_val

        doc.close()
    except Exception as exc:
        logger.warning("Failed to extract PDF metadata from %s: %s", pdf_path, exc)

    # Try ArXiv API lookup if we have an arXiv ID
    if metadata.get("arxiv_id") and not metadata["title"]:
        try:
            import xml.etree.ElementTree as ET

            import requests

            arxiv_id = re.sub(r"v\d+$", "", metadata["arxiv_id"])  # strip version
            resp = requests.get(
                f"https://export.arxiv.org/api/query?id_list={arxiv_id}",
                timeout=10,
            )
            if resp.status_code == 200:
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                root = ET.fromstring(resp.content)
                entry = root.find("atom:entry", ns)
                if entry is not None:
                    title_el = entry.find("atom:title", ns)
                    if title_el is not None and title_el.text:
                        metadata["title"] = unicodedata.normalize(
                            "NFC", re.sub(r"\s+", " ", title_el.text.strip())
                        )
                    # Authors
                    arxiv_authors = []
                    for author_el in entry.findall("atom:author", ns):
                        name_el = author_el.find("atom:name", ns)
                        if name_el is not None and name_el.text:
                            arxiv_authors.append(name_el.text.strip())
                    if arxiv_authors:
                        metadata["authors"] = arxiv_authors

                    # Check if ArXiv links to a DOI (paper is published!)
                    for link in entry.findall("atom:link", ns):
                        if link.get("title") == "doi":
                            metadata["doi"] = link.get("href", "").replace("http://dx.doi.org/", "")

                    # Categories
                    for cat in entry.findall("{http://arxiv.org/schemas/atom}primary_category"):
                        metadata["arxiv_category"] = cat.get("term", "")
        except requests.exceptions.RequestException as exc:
            logger.warning("ArXiv API request failed for %s: %s", metadata["arxiv_id"], exc)
        except Exception as exc:
            logger.warning("ArXiv lookup failed for %s: %s", metadata["arxiv_id"], exc)

    # Try Crossref lookup if we have a DOI
    if metadata.get("doi") and not metadata["title"]:
        try:
            import requests

            resp = requests.get(
                f"https://api.crossref.org/works/{metadata['doi']}",
                headers={"User-Agent": "MathPDFManager/1.0 (mailto:admin@example.com)"},
                timeout=10,
            )
            if resp.status_code == 200:
                cr = resp.json().get("message", {})
                titles = cr.get("title", [])
                if titles:
                    metadata["title"] = unicodedata.normalize("NFC", titles[0])
                cr_authors = cr.get("author", [])
                if cr_authors:
                    metadata["authors"] = [
                        {"family": a.get("family", ""), "given": a.get("given", "")}
                        for a in cr_authors
                        if a.get("family")
                    ]
                if cr.get("journal"):
                    metadata["journal"] = cr["journal"]
                pub_date = cr.get("published-print") or cr.get("published-online")
                if pub_date and pub_date.get("date-parts"):
                    parts = pub_date["date-parts"][0]
                    if parts:
                        metadata["year"] = parts[0]
        except requests.exceptions.RequestException as exc:
            logger.warning("Crossref API request failed for DOI %s: %s", metadata["doi"], exc)
        except Exception as exc:
            logger.warning("Crossref lookup failed for DOI %s: %s", metadata["doi"], exc)

    # Try LLM extraction if title is still missing
    if not metadata["title"]:
        try:
            from pdf_processing.llm_extractor import LLMMetadataExtractor

            extractor = LLMMetadataExtractor()
            llm_result = extractor.extract(pdf_path)
            if llm_result and llm_result.get("title"):
                metadata["title"] = llm_result["title"]
                if llm_result.get("authors"):
                    metadata["authors"] = llm_result["authors"]
        except Exception:
            pass  # LLM not available

    return metadata


# ---------------------------------------------------------------------------
# Author parsing
# ---------------------------------------------------------------------------

# Nobiliary particles for compound surnames ("van der Waals", "el Karoui", etc.)
# When a name has the pattern "<Given> <particle> <Family>", treat
# "<particle> <Family>" as the family name.
NOBILIARY_PARTICLES = frozenset({
    "van", "von", "der", "den", "de", "del", "della", "di",
    "la", "le", "el", "ter", "ten", "da", "do", "du", "dos",
    "y", "ben", "bin", "abu", "al", "st", "san", "santa",
    "von der", "van den", "van der", "de la", "de los",
})

# Initials: capital letter (with possible accents/Cyrillic) followed by period,
# possibly with hyphens between (e.g. "F.", "F.-J.", "Yu.M.", "É.")
_INITIAL_TOKEN = (
    r"[A-ZÀ-ſΑ-ΩА-Я]"   # capital (Latin/Greek/Cyrillic)
    r"[A-Za-zÀ-ſΑ-ωА-я]*"  # optional letters (e.g. "Yu.")
    r"\."                                              # required period
)
_INITIALS_RE = re.compile(
    rf"^{_INITIAL_TOKEN}(?:[\s-]*{_INITIAL_TOKEN})*\s*$"
)

# Strong author separators (NOT comma — comma is ambiguous)
_STRONG_SEP_RE = re.compile(r"\s*&\s*|\s*;\s*|\s+and\s+", re.IGNORECASE)


def _looks_like_initials(s: str) -> bool:
    """True if the string looks like initials (e.g., "F.", "J.-F.", "Yu.M.")."""
    if not s:
        return False
    return bool(_INITIALS_RE.match(s.strip()))


def _split_family_with_particle(words: List[str]) -> tuple[int, str]:
    """Given the words of a name, find where the family name starts.

    Returns (family_start_index, family_string). Walks backwards from the last
    word and pulls in nobiliary particles ("van", "der", "el", ...) as part
    of the family name.
    """
    if not words:
        return 0, ""
    family_start = len(words) - 1
    while family_start > 0 and words[family_start - 1].lower() in NOBILIARY_PARTICLES:
        family_start -= 1
    return family_start, " ".join(words[family_start:])


def _parse_first_last(name: str, multiword_surnames: Optional[Set[str]] = None) -> Optional[Author]:
    """Parse a name in 'First [Middle...] [particle] Last' format."""
    name = name.strip()
    if not name:
        return None

    # Check explicit multiword surname whitelist first
    if multiword_surnames:
        for surname in multiword_surnames:
            if name.lower().endswith(" " + surname.lower()):
                given = name[: -len(surname) - 1].strip()
                return Author(family=name[-len(surname):], given=given or None)

    if " " not in name:
        return Author(family=name)

    words = name.split()
    family_start, family = _split_family_with_particle(words)
    given = " ".join(words[:family_start]).strip() if family_start > 0 else None
    return Author(family=family, given=given or None)


def _looks_like_filename_format(raw: str) -> bool:
    """True if the string looks like 'Last, F., Last, F., ...' (filename format).

    The signature: even number of comma-separated parts, where every odd-indexed
    part is initials.
    """
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) < 2 or len(parts) % 2 != 0:
        return False
    for i in range(1, len(parts), 2):
        if not _looks_like_initials(parts[i]):
            return False
    # And the even-indexed parts shouldn't look like initials themselves
    for i in range(0, len(parts), 2):
        if not parts[i] or _looks_like_initials(parts[i]):
            return False
    return True


def _parse_filename_format(raw: str) -> List[Author]:
    """Parse 'Last, F., Last, F., ...' into Author objects."""
    parts = [p.strip() for p in raw.split(",")]
    authors = []
    for i in range(0, len(parts), 2):
        family = parts[i]
        given = parts[i + 1] if i + 1 < len(parts) else None
        if family:
            authors.append(Author(family=family, given=given))
    return authors


def _parse_segment(seg: str, multiword_surnames: Optional[Set[str]] = None) -> List[Author]:
    """Parse one segment (post strong-separator split) into one or more authors.

    The segment may be:
    - "Last, First" / "Last, F." (single author, comma is field separator)
    - "First Last" / "First Middle Last" (single author, no comma)
    - "First Last, First Last" (multiple authors, comma is author separator —
      arises in PDF embedded metadata when authors are listed with full names)
    """
    seg = seg.strip()
    if not seg or seg.lower().rstrip(".") in {"et al", "and others"}:
        return []

    if "," not in seg:
        author = _parse_first_last(seg, multiword_surnames)
        return [author] if author else []

    # Has at least one comma. Decide whether commas separate authors or split Last/First.
    parts = [p.strip() for p in seg.split(",")]

    # Heuristic 1: Pair-style filename format inside one segment
    # ("Last, F., Last, F." inside a single &-delimited segment)
    if _looks_like_filename_format(seg):
        return _parse_filename_format(seg)

    # Heuristic 2: First part has multiple words, AND the part after the first
    # comma does NOT look like initials → this is "First Last, First Last"
    # (comma is author separator).
    first_part = parts[0]
    after_first = parts[1] if len(parts) > 1 else ""
    if (
        len(first_part.split()) >= 2
        and not _looks_like_initials(after_first)
        and not (multiword_surnames and first_part.lower() in {s.lower() for s in multiword_surnames})
    ):
        # Multi-author by comma
        authors = []
        for p in parts:
            a = _parse_first_last(p, multiword_surnames)
            if a:
                authors.append(a)
        return authors

    # Heuristic 3: "Last, First" or "Last, Initials" (single author)
    family = first_part
    given = ", ".join(parts[1:]).strip() if len(parts) > 1 else None
    return [Author(family=family, given=given or None)]


def parse_authors_string(
    raw, multiword_surnames: Optional[Set[str]] = None
) -> List[Author]:
    """Parse a raw author string into Author objects.

    Handles the following formats robustly:

    Format A (PDF embedded, full names):
        "Romain Abraham, Jean-François Delmas & Julien Weibel"
        "Romain Abraham, Jean-François Delmas, Julien Weibel"

    Format B (filename / Crossref):
        "Abraham, R., Delmas, J.-F., Weibel, J."

    Format C (Crossref-style with 'and'):
        "Abraham, R. and Delmas, J.-F. and Weibel, J."

    Format D (already a list):
        ["Romain Abraham", "Jean-François Delmas", ...]

    Multi-part surnames ("van der Waals", "el Karoui") are handled via
    nobiliary-particle detection or the optional ``multiword_surnames``
    whitelist.

    Returns a list of :class:`Author` objects (possibly empty).
    """
    if raw is None:
        return []

    # Format D: already a list — recursively parse each item
    if isinstance(raw, list):
        result: List[Author] = []
        for item in raw:
            result.extend(parse_authors_string(item, multiword_surnames))
        return result

    raw = str(raw).strip()
    if not raw:
        return []

    # Strip a trailing "et al." (with or without comma/period) so it
    # doesn't get parsed as a fake author. The cue can appear at the end
    # of an author list in any format.
    raw = re.sub(
        r",?\s+et\s+al\.?\s*$",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip()
    if not raw:
        return []

    # Step 1: Split on strong separators (&, ;, ' and ')
    if _STRONG_SEP_RE.search(raw):
        segments = _STRONG_SEP_RE.split(raw)
    else:
        segments = [raw]

    authors: List[Author] = []
    for seg in segments:
        authors.extend(_parse_segment(seg, multiword_surnames))
    return authors


# ---------------------------------------------------------------------------
# Metadata → CMO conversion
# ---------------------------------------------------------------------------

def metadata_to_cmo(metadata: dict, pdf_path: Path) -> CMO:
    """Convert extracted metadata dict into a CMO object.

    Author resolution priority:
        1. Structured ``metadata["authors"]`` from APIs (Crossref, ArXiv, LLM),
           IF non-empty.
        2. Raw ``metadata["authors_raw"]`` from PDF embedded metadata,
           parsed via :func:`parse_authors_string`.
        3. Empty list (caller decides how to handle).
    """
    authors: List[Author] = []

    # Priority 1: structured authors list (must be non-empty to count)
    structured = metadata.get("authors")
    if isinstance(structured, list) and structured:
        for a in structured:
            if isinstance(a, str):
                # String entry: parse it (handles "First Last" or "Last, First")
                parsed = parse_authors_string(a)
                authors.extend(parsed)
            elif isinstance(a, dict) and (a.get("family") or a.get("name")):
                # Crossref/ArXiv structured author dict
                family = a.get("family") or a.get("name") or ""
                given = a.get("given") or None
                if family:
                    authors.append(Author(family=family, given=given))
            elif isinstance(a, Author):
                authors.append(a)

    # Priority 2: fall back to raw author string from PDF metadata
    if not authors and metadata.get("authors_raw"):
        authors = parse_authors_string(metadata["authors_raw"])

    title = metadata.get("title", "")
    if not title:
        # Last resort: use filename stem
        title = pdf_path.stem

    return CMO(
        external_id=str(pdf_path),
        source="local",
        title=title,
        authors=authors,
        doi=metadata.get("doi"),
    )


# ---------------------------------------------------------------------------
# Main ingest logic
# ---------------------------------------------------------------------------
def ingest_paper(
    pdf_path: Path,
    *,
    library_root: Path = LIBRARY_ROOT,
    status: Optional[str] = None,
    topic: Optional[str] = None,
    year: Optional[int] = None,
    dry_run: bool = False,
    verbose: bool = False,
    canonical_override: Optional[str] = None,
    auto_topic: bool = True,
    **kwargs,
) -> dict:
    """Ingest a single PDF into the library.

    Parameters
    ----------
    pdf_path : Path
        Path to the PDF file.
    library_root : Path
        Root of the library (e.g. ``…/Maths/``).
    status : str or None
        Force publication status (``"published"``, ``"unpublished"``,
        ``"working"``).  If None, auto-detected from metadata.
    topic : str or None
        Topic prefix (e.g. ``"07a"``) for topic-specific filing.
    year : int or None
        Year for working papers.  Auto-detected if not provided.
    dry_run : bool
        If True, report actions without moving files.
    verbose : bool
        If True, print detailed progress.
    canonical_override : str or None
        If supplied, use this filename verbatim instead of generating one
        from metadata. Used by the cockpit UI to honour user edits.

    Returns
    -------
    dict
        Summary of actions taken.
    """
    result = {
        "file": str(pdf_path),
        "success": False,
        "actions": [],
        "filename": "",
        "destination": "",
    }

    if not pdf_path.exists():
        result["error"] = f"File not found: {pdf_path}"
        return result

    if not pdf_path.suffix.lower() == ".pdf":
        result["error"] = f"Not a PDF file: {pdf_path}"
        return result

    # Step 1: Extract metadata
    if verbose:
        print(f"  Extracting metadata from {pdf_path.name}...")
    metadata = extract_metadata_from_pdf(pdf_path)

    # Surface to callers whether we actually got a title from metadata
    # (vs. silently falling back to the filename stem in metadata_to_cmo).
    # bulk_sort uses this to flag papers that need manual review even when
    # a fake "author" was extracted (e.g. PDF metadata with author=
    # "SoWise" but no title).
    result["title_from_metadata"] = bool(metadata.get("title"))

    # Step 2: Build CMO and generate canonical filename
    cmo = metadata_to_cmo(metadata, pdf_path)
    if canonical_override:
        # User override — preserve verbatim but enforce .pdf suffix
        canonical_name = canonical_override
        if not canonical_name.lower().endswith(".pdf"):
            canonical_name += ".pdf"
        result["canonical_overridden"] = True
        # ROUTING FIX (live trial): the override is authoritative for
        # the alpha-subdir too.  Otherwise a paper whose curated name
        # says "el Karoui, N." but whose (published) metadata says
        # "Karoui, N." would file under the wrong letter -- the name on
        # disk and the folder it lives in must agree.  Re-derive the
        # author list from the override's "Authors - Title" segment.
        override_stem = canonical_name[:-4] if canonical_name.lower().endswith(".pdf") else canonical_name
        if " - " in override_stem:
            try:
                parsed = parse_authors_string(override_stem.split(" - ", 1)[0])
            except Exception:
                parsed = []
            if parsed:
                cmo.authors = parsed
    else:
        canonical_name = cmo.get_canonical_filename()
    result["filename"] = canonical_name

    # Fallback for already-canonical filenames with empty metadata: if the
    # source filename has the "Authors - Title.pdf" shape but metadata
    # extraction yielded no authors, parse the filename's author segment
    # so the file can route to the correct alpha-subdir instead of "Z/".
    if not cmo.authors and " - " in pdf_path.stem:
        authors_part = pdf_path.stem.split(" - ", 1)[0]
        try:
            parsed = parse_authors_string(authors_part)
        except Exception:
            parsed = []
        if parsed:
            cmo.authors = parsed

    # Write the parsed authors BACK into the metadata dict so the downstream
    # OrganizationSystem.route() picks the correct alpha-subdir. Without
    # this, papers whose authors only existed in ``authors_raw`` (PDF
    # embedded metadata) all end up filed under "Z".
    if cmo.authors:
        metadata["authors"] = [
            {"family": a.family, "given": a.given}
            for a in cmo.authors
        ]

    if verbose:
        print(f"  Title: {cmo.title}")
        print(f"  Authors: {', '.join(a.display_name() for a in cmo.authors)}")
        print(f"  Canonical name: {canonical_name}")
        if metadata.get("doi"):
            print(f"  DOI: {metadata['doi']}")
        if metadata.get("arxiv_id"):
            print(f"  ArXiv: {metadata['arxiv_id']}")

    # Step 3: Override status if specified.
    # Routing reads ``metadata["document_type"]`` and DOI/arxiv_id presence
    # via OrganizationSystem.determine_publication_status. We write into
    # BOTH so each forced status produces a clean, unambiguous signal that
    # any future routing change cannot accidentally misinterpret.
    #
    # IMPORTANT: ``dict.setdefault`` does not replace a key whose existing
    # value is ``None``. extract_metadata_from_pdf initialises ``doi``/
    # ``arxiv_id`` to ``None``, so we must use unconditional assignment
    # (gated on the current value being truthy) instead of setdefault.
    def _force_field(key: str, sentinel: str) -> None:
        if not metadata.get(key):
            metadata[key] = sentinel

    if status:
        metadata["_forced_status"] = status
        if status == "published":
            _force_field("doi", "forced")
            # Clear arxiv_id so future routing changes can't downgrade us
            # to "unpublished" based on a still-present arxiv tag.
            metadata.pop("arxiv_id", None)
        elif status == "unpublished":
            _force_field("arxiv_id", "forced")
            metadata.pop("doi", None)
        elif status == "working":
            metadata.pop("doi", None)
            metadata.pop("arxiv_id", None)
        elif status == "book":
            metadata["document_type"] = "book"
            metadata.pop("doi", None)
            metadata.pop("arxiv_id", None)
        elif status == "lecture_notes":
            metadata["document_type"] = "lecture_notes"
            metadata.pop("doi", None)
            metadata.pop("arxiv_id", None)
        elif status == "thesis":
            metadata["document_type"] = "thesis"
            metadata.pop("doi", None)
            metadata.pop("arxiv_id", None)
        else:
            logger.warning("ingest_paper: unknown status hint %r — ignoring", status)

    # Step 4: Determine year for working papers
    paper_year = year or metadata.get("year")

    # Step 4.5: Auto-resolve the topic folder when the caller didn't
    # pin one.  The library's six 07x topic folders (BSDEs, Contract
    # theory, Time-inconsistent control, Stackelberg, Control on
    # networks, Non-commutative calculus) each mirror the standard
    # 01-Published / 02-Unpublished / ... structure.  A paper whose
    # title clearly matches a topic should land in that topic's
    # subtree rather than the flat top-level folder -- this is what
    # the user asked for when papers leave "12 - To be sorted" or get
    # upgraded out of "02 - Unpublished".
    #
    # Conservative: ``resolve_topic`` only returns a code on a
    # confident keyword match, so the common case (no match) keeps
    # the existing top-level routing.  Sub-sub-topics (Numerical
    # methods, 2BSDEs, G-BSDEs, ESG) are NOT auto-routed -- the
    # classifier has no patterns for them -- so a BSDE paper lands in
    # ``07a - BSDEs/01 - Published papers/`` and the user can refile
    # into a finer bucket by hand.
    if topic is None and auto_topic:
        try:
            from processing.publication_topic_router import resolve_topic
            # Feed the classifier everything we have, not just the
            # title: keywords + abstract/first-page text materially
            # improve topic accuracy (user's C1 point).
            extra = " ".join(
                s for s in (
                    metadata.get("keywords") or "",
                    metadata.get("abstract") or "",
                    metadata.get("fulltext_sample") or "",
                ) if s
            )
            decision = resolve_topic(metadata.get("title") or "", extra)
            result["topic_confidence"] = decision.confidence
            if decision.auto:
                # Confident -> file into the topic folder.
                topic = decision.topic_code
                result["auto_topic"] = decision.topic_code
                result["auto_topic_name"] = decision.topic_name
                if verbose:
                    print(
                        f"  Auto-topic: {decision.topic_code} "
                        f"({decision.topic_name}, {decision.confidence:.0%})"
                    )
            elif decision.needs_review:
                # Plausible but uncertain -> file standard, but record
                # the suggestion so the cockpit Attention Queue can ask
                # the user to confirm a move into the topic folder.
                result["topic_suggestion"] = decision.suggested_code
                result["topic_suggestion_name"] = decision.suggested_name
                if verbose:
                    print(
                        f"  Topic suggestion (needs review): "
                        f"{decision.suggested_code} "
                        f"({decision.suggested_name}, {decision.confidence:.0%})"
                    )
        except Exception as exc:  # pragma: no cover -- never block ingest
            logger.warning("auto topic resolution failed: %s", exc)

    # Step 5: Organize (route to correct directory, with undo logging)
    org = OrganizationSystem(library_root, topic=topic, dry_run=dry_run)
    org_result = org.organize(pdf_path, metadata, canonical_name, year=paper_year, undo_log=kwargs.get("undo_log"))

    result["destination"] = str(org_result.destination)
    result["status"] = org_result.publication_status
    result["actions"] = org_result.actions
    result["success"] = not any("ERROR" in a for a in org_result.actions)

    # Step 6: Write the paper identity sidecar next to the filed PDF.
    # Best-effort: a sidecar-write failure does NOT fail the ingest --
    # the PDF is already in the right place, the sidecar is just extra
    # metadata.  Skip in dry-run mode and when the destination doesn't
    # actually exist (e.g. dry-run org with no copy performed).
    if result["success"] and not dry_run:
        try:
            from processing.identity import PaperIdentity
            from datetime import datetime, timezone

            dest_path = Path(org_result.destination)
            if dest_path.exists() and dest_path.suffix.lower() == ".pdf":
                # Preserve any existing sidecar (re-ingest of an
                # already-filed paper); we don't want to wipe DOI/arxiv
                # data that earlier passes recorded.
                identity = PaperIdentity.load(dest_path)
                if identity.is_new():
                    identity.original_filename = pdf_path.name
                    identity.first_ingested_at = datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    )
                    tx = kwargs.get("undo_log")
                    if tx is not None and getattr(tx, "_tx_id", None):
                        identity.first_ingest_tx_id = tx._tx_id
                # Fill in identifiers we now know.
                if not identity.doi and metadata.get("doi"):
                    identity.doi = metadata["doi"]
                if not identity.arxiv_id and metadata.get("arxiv_id"):
                    identity.arxiv_id = metadata["arxiv_id"]
                # The primary location should always appear in
                # copy_locations so the topic router can later append
                # secondary copies without losing the original.
                primary = str(dest_path)
                if primary not in identity.copy_locations:
                    identity.copy_locations.append(primary)
                # Persist a pending topic suggestion (medium
                # confidence) so the cockpit Attention Queue can ask
                # the user to confirm a move into the topic folder.
                # Audit-9 D: a re-ingest that now classifies
                # confidently (auto_topic set) or finds no topic must
                # CLEAR any stale suggestion from a prior pass --
                # otherwise the paper shows up both as auto-filed and
                # as a pending suggestion.
                if result.get("topic_suggestion"):
                    identity.topic_suggestion = result["topic_suggestion"]
                    identity.topic_confidence = result.get("topic_confidence", 0.0)
                else:
                    identity.topic_suggestion = ""
                    identity.topic_confidence = 0.0
                identity.save(dest_path)
        except Exception as exc:  # pragma: no cover -- best effort
            logger.warning("sidecar write failed for %s: %s", org_result.destination, exc)

    if verbose:
        print(f"  Status: {org_result.publication_status}")
        for action in org_result.actions:
            prefix = "  " if "WARNING" not in action else "  ⚠ "
            print(f"{prefix}{action}")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest PDFs into the math library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s paper.pdf                     Auto-detect and file
  %(prog)s paper.pdf --status published  Force as published
  %(prog)s paper.pdf --topic 07a         File under BSDEs
  %(prog)s *.pdf --dry-run               Preview without moving
  %(prog)s paper.pdf --status working --year 2025
""",
    )
    parser.add_argument("files", nargs="+", type=Path, help="PDF files to ingest")
    parser.add_argument(
        "--status",
        choices=["published", "unpublished", "working", "book", "thesis"],
        help="Force publication status (auto-detected if omitted)",
    )
    parser.add_argument("--topic", help="Topic prefix for filing (e.g. '07a')")
    parser.add_argument("--year", type=int, help="Year for working papers")
    parser.add_argument(
        "--library",
        type=Path,
        default=LIBRARY_ROOT,
        help=f"Library root (default: {LIBRARY_ROOT})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without moving files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = build_parser()
    args = parser.parse_args(argv)

    # Set up undo log for non-dry-run operations
    undo_log = None
    tx_id = None
    if not args.dry_run:
        undo_log = UndoLog()
        tx_id = undo_log.begin_transaction(f"Ingest {len(args.files)} paper(s)")

    results = []
    for pdf_path in args.files:
        pdf_path = pdf_path.resolve()
        if not args.json and not args.verbose:
            print(f"Ingesting {pdf_path.name}...", end=" ")

        result = ingest_paper(
            pdf_path,
            library_root=args.library,
            status=args.status,
            topic=args.topic,
            year=args.year,
            dry_run=args.dry_run,
            verbose=args.verbose,
            undo_log=undo_log,
        )
        results.append(result)

        if not args.json and not args.verbose:
            if result["success"]:
                print(f"→ {result['destination']}")
            else:
                print(f"FAILED: {result.get('error', 'unknown')}")

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    # Commit undo log
    if undo_log and any(r["success"] for r in results):
        log_file = undo_log.commit()
        if not args.json:
            print(f"\nUndo log: {log_file}")
            print(f"To revert: python -m processing.undo_log undo --transaction {tx_id}")

    # Summary
    if len(results) > 1 and not args.json:
        ok = sum(1 for r in results if r["success"])
        print(f"\n{ok}/{len(results)} papers ingested successfully")


if __name__ == "__main__":
    main()
