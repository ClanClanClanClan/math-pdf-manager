#!/usr/bin/env python3
"""
Metadata Quality Filters
=========================

Validators for embedded PDF metadata — the ``doc.metadata['title']`` and
``doc.metadata['author']`` fields are notoriously unreliable.  They may
contain the LaTeX class name, "Microsoft Word", the filename, the journal
name, or complete garbage.

These functions help decide whether to trust embedded metadata.
"""

import re
from typing import Optional

# -----------------------------------------------------------------------
# Title quality
# -----------------------------------------------------------------------

# Strings that appear in doc.metadata['title'] but are NOT real titles
_GARBAGE_TITLE_PATTERNS = [
    # LaTeX preamble / class artefacts
    r"^untitled",
    r"^document$",
    r"^(?:la)?tex",
    r"^latex2e",
    r"^manuscript",
    r"^article$",
    r"^paper$",
    r"^template",
    r"^(?:slide|presentation)",

    # Software artefacts
    r"^microsoft\s+word",
    r"^libreoffice",
    r"^openoffice",
    r"^pdflatex",
    r"^dvips",
    r"^ps2pdf",
    r"^pdf-?x",
    r"^acrobat",
    r"^preview",

    # Filename leaks
    r"\.(?:tex|pdf|dvi|ps|docx?)$",
    r"^.*\.(tex|pdf|dvi)$",

    # Generic
    r"^title$",
    r"^no\s+title",
    r"^unknown",
    r"^none$",
    r"^n/?a$",
    r"^draft",
    r"^final\s+version",
    r"^revised",
    r"^preprint",
]

_GARBAGE_TITLE_RE = re.compile(
    "|".join(f"(?:{p})" for p in _GARBAGE_TITLE_PATTERNS),
    re.IGNORECASE,
)


def is_valid_embedded_title(title: Optional[str]) -> bool:
    """Return True if the embedded title looks like a real paper title.

    Returns False for common garbage values like "Microsoft Word", "LaTeX2e",
    filenames, "Untitled", etc.
    """
    if not title:
        return False

    title = title.strip()

    # Too short or too long
    if len(title) < 5 or len(title) > 500:
        return False

    # Matches a known garbage pattern
    if _GARBAGE_TITLE_RE.search(title):
        return False

    # Pure numbers or punctuation
    if re.match(r"^[\d\s\.\-/]+$", title):
        return False

    # All uppercase single word (likely an artefact)
    if re.match(r"^[A-Z]{2,}$", title):
        return False

    # Contains suspicious characters (binary, control codes)
    if any(ord(c) < 32 and c not in "\n\r\t" for c in title):
        return False

    return True


# -----------------------------------------------------------------------
# Author quality
# -----------------------------------------------------------------------

_GARBAGE_AUTHOR_PATTERNS = [
    r"^unknown",
    r"^author$",
    r"^n/?a$",
    r"^none$",
    r"^anonymous$",
    r"^admin",
    r"^user$",
    r"^root$",
    r"^microsoft",
    r"^adobe",
    r"^system",
    r"^owner$",
    r"^default",
    r"^(\w+\s+)+corp",
    r"^the\s+authors?$",
]

_GARBAGE_AUTHOR_RE = re.compile(
    "|".join(f"(?:{p})" for p in _GARBAGE_AUTHOR_PATTERNS),
    re.IGNORECASE,
)


def is_valid_embedded_authors(authors: Optional[str]) -> bool:
    """Return True if the embedded author string looks like real author names.

    Returns False for "Unknown", "Microsoft", "admin", etc.
    """
    if not authors:
        return False

    authors = authors.strip()

    if len(authors) < 3 or len(authors) > 1000:
        return False

    if _GARBAGE_AUTHOR_RE.search(authors):
        return False

    # Pure numbers
    if re.match(r"^[\d\s]+$", authors):
        return False

    return True


# -----------------------------------------------------------------------
# Identifier extraction from filenames
# -----------------------------------------------------------------------

def extract_doi_from_filename(filename: str) -> Optional[str]:
    """Extract a DOI from a filename where ``/`` has been replaced by ``_``.

    Many downloaded PDFs are named using the DOI:

    - ``10.1214_aop.2023.12345.pdf``  →  ``10.1214/aop.2023.12345``
    - ``10.1007_s00440-021-01063-1.pdf``  →  ``10.1007/s00440-021-01063-1``
    """
    from pathlib import Path
    stem = Path(filename).stem

    # DOI pattern: 10.XXXX/suffix  (with _ standing in for /)
    # The DOI prefix is always 10.XXXX where XXXX is 4+ digits
    m = re.match(
        r"(10\.\d{4,9})_(.+)",
        stem,
    )
    if m:
        prefix = m.group(1)
        suffix = m.group(2)
        doi = f"{prefix}/{suffix}"
        return doi

    return None


def extract_ssrn_id_from_filename(filename: str) -> Optional[str]:
    """Extract an SSRN paper ID from the filename.

    SSRN downloads are typically named ``SSRN-id1234567.pdf``.
    """
    from pathlib import Path
    stem = Path(filename).stem

    m = re.search(r"SSRN[-_]?id(\d{5,10})", stem, re.IGNORECASE)
    if m:
        return m.group(1)

    return None
