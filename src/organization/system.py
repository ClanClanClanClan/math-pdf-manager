#!/usr/bin/env python3
"""Organization, validation, and duplicate detection utilities.

Handles the library's recursive directory structure::

    Maths/
    ├── 01 - Published papers/{A-Z}/
    ├── 02 - Unpublished papers/{A-Z}/
    ├── 03 - Working papers/{A-Z}/{year}/
    ├── 04 - Papers to be downloaded/
    │   └── Not fully published version/
    ├── 05 - Books and lecture notes/{named-series | A-Z}/
    ├── 06 - Theses/{A-Z}/
    ├── 07x - <topic>/ (mirrors 01-06 + nested 07x sub-topics)
    ├── 08 - Séminaires de probabilités/
    ├── 09 - JEHPS/
    └── 10 - Math slides/

Topic folders (07a, 07b, …) recursively mirror the top-level structure.
"""

from __future__ import annotations

import logging
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directory name constants
# ---------------------------------------------------------------------------
PUBLISHED = "01 - Published papers"
UNPUBLISHED = "02 - Unpublished papers"
WORKING = "03 - Working papers"
TO_DOWNLOAD = "04 - Papers to be downloaded"
BOOKS = "05 - Books and lecture notes"
THESES = "06 - Theses"
NOT_FULLY_PUBLISHED = "Not fully published version"
TO_BE_SORTED = "12 - To be sorted"  # staging area for raw bulk-imported PDFs


# Nobiliary particles — "el Karoui" files under K (the Family part), not E.
# Also covers two-word particles like "van der", "de la".
_ALPHA_PARTICLES = frozenset({
    "van", "von", "der", "den", "de", "del", "della", "di",
    "la", "le", "el", "ter", "ten", "da", "do", "du", "dos",
    "y", "ben", "bin", "abu", "al", "st", "san", "santa",
    "von der", "van den", "van der", "de la", "de los", "de las",
})

# Latin letters with strokes/special diacritics that NFD cannot decompose.
# These are precomposed in Unicode and have no combining-mark form.
_LATIN_SPECIAL_TO_LATIN = {
    "Ł": "L", "Ø": "O", "Æ": "A", "Œ": "O", "Þ": "T", "Ð": "D",
    "ß": "S",
}

# Greek capital → Latin equivalent (used for filing α-name papers under A, etc.)
_GREEK_TO_LATIN = {
    "Α": "A", "Β": "B", "Γ": "G", "Δ": "D", "Ε": "E", "Ζ": "Z",
    "Η": "E", "Θ": "T", "Ι": "I", "Κ": "K", "Λ": "L", "Μ": "M",
    "Ν": "N", "Ξ": "X", "Ο": "O", "Π": "P", "Ρ": "R", "Σ": "S",
    "Τ": "T", "Υ": "Y", "Φ": "F", "Χ": "C", "Ψ": "P", "Ω": "O",
}

# Cyrillic → Latin (best-effort romanization for filing only)
_CYRILLIC_TO_LATIN = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E",
    "Ж": "Z", "З": "Z", "И": "I", "Й": "I", "К": "K", "Л": "L",
    "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S",
    "Т": "T", "У": "U", "Ф": "F", "Х": "K", "Ц": "T", "Ч": "C",
    "Ш": "S", "Щ": "S", "Ы": "Y", "Э": "E", "Ю": "Y", "Я": "Y",
}

STATUS_DIRS = {
    "published": PUBLISHED,
    "unpublished": UNPUBLISHED,
    "working": WORKING,
    "book": BOOKS,
    "thesis": THESES,
    "not_fully_published": f"{TO_DOWNLOAD}/{NOT_FULLY_PUBLISHED}",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class OrganizationResult:
    file_path: Path
    destination: Path
    actions: List[str] = field(default_factory=list)
    publication_status: str = ""
    duplicate_of: Optional[Path] = None


# ---------------------------------------------------------------------------
# Content validation
# ---------------------------------------------------------------------------
class ContentValidator:
    def validate_pdf_integrity(self, file_path: Path) -> bool:
        if not file_path.exists():
            logger.warning("File missing during content validation: %s", file_path)
            return False
        with open(file_path, "rb") as fh:
            header = fh.read(4)
        return header == b"%PDF"


# Duplicate detection lives in processing.duplicate_scan (the authoritative
# whole-library detector: size prefilter -> full-file SHA-256, keep-policy,
# reversible resolution).  The vestigial per-call DuplicateDetector that used
# to sit here had no live callers and was removed in the audit cleanup.


# ---------------------------------------------------------------------------
# Folder routing — maps metadata to the actual directory structure
# ---------------------------------------------------------------------------
class FolderRouter:
    """Routes a paper to the correct directory in the library.

    Parameters
    ----------
    library_root : Path
        Top-level library directory (e.g. ``…/Maths/``).
    topic : str or None
        Optional topic prefix like ``"07a"`` to file under a topic folder.
        When set, the paper is filed inside the topic's mirrored structure
        (e.g. ``07a - BSDEs/01 - Published papers/A/``).
    """

    def __init__(self, library_root: Path, *, topic: Optional[str] = None):
        self.library_root = library_root
        self.topic_prefix = topic
        self._topic_dir: Optional[Path] = None
        if topic:
            self._topic_dir = self._find_topic_dir(topic)

    def _find_topic_dir(self, prefix: str) -> Optional[Path]:
        """Find the topic directory matching a prefix like '07a'."""
        for d in sorted(self.library_root.iterdir()):
            if d.is_dir() and d.name.lower().startswith(prefix.lower()):
                return d
        logger.warning("Topic directory not found for prefix: %s", prefix)
        return None

    def determine_publication_status(self, metadata: Dict) -> str:
        """Determine publication status from metadata.

        A paper is considered "published" only if it has a DOI from an
        actual journal or publisher.  DOIs from repositories (SSRN, arXiv,
        HAL, Zenodo, NBER, RePEc, etc.) are preprints, not publications.

        Age-based rule (matches user's library policy): a paper whose
        publication year is more than ``working_to_unpublished_years``
        years old at the time of ingest goes straight to Unpublished
        rather than Working.  This keeps Working as a "recent /
        actively pursued" folder rather than letting a 12-year-old
        preprint sit there forever.
        """
        doc_type = metadata.get("document_type", "").lower()
        if doc_type in ("book", "lecture_notes"):
            return "book"
        if doc_type == "thesis":
            return "thesis"

        doi = metadata.get("doi", "")
        journal = metadata.get("journal", "")

        # DOIs from repositories are NOT publications
        if doi and not _is_repository_doi(doi):
            return "published"
        if journal and not _is_repository_journal(journal):
            return "published"

        # Distinguish "preprint we still believe in" (working) from
        # "preprint we've long stopped chasing" (unpublished) by age.
        # Threshold mirrors ``maintenance.weekly_report.check_aging``
        # default of 5 years.
        age_cutoff_years = 5
        try:
            from datetime import date as _date, datetime as _dt
            current_year = _dt.now().year
            paper_year = metadata.get("year")
            # Normalise to ``int`` covering the realistic input shapes
            # we've seen in the wild: ``int``, ``float`` (JSON parsed
            # 2024.0), ``str`` ("2024", "2024-05-13", "  2024 "),
            # ``date`` / ``datetime`` objects (BibTeX libraries),
            # and 1-element ``list`` / ``tuple`` (some API wrappers).
            if isinstance(paper_year, (list, tuple)) and len(paper_year) == 1:
                paper_year = paper_year[0]
            if isinstance(paper_year, (_date, _dt)):
                paper_year = paper_year.year
            if isinstance(paper_year, float):
                paper_year = int(paper_year)
            if isinstance(paper_year, str):
                stripped = paper_year.strip()
                # Require a 4-digit prefix that's a plausible year.
                # Rejects "n.d.", "202", "  ", "forthcoming", etc.
                if not (len(stripped) >= 4 and stripped[:4].isdigit()):
                    raise ValueError(f"unparseable year: {paper_year!r}")
                paper_year = int(stripped[:4])
            if (
                isinstance(paper_year, int)
                and 1000 <= paper_year <= 9999  # sanity gate against year=202
                and (current_year - paper_year) > age_cutoff_years
            ):
                return "unpublished"
        except (ValueError, TypeError):
            pass  # year unparseable — fall through to default routing

        if metadata.get("arxiv_id"):
            return "unpublished"
        return "working"

    def get_alpha_subdir(self, first_author_lastname: str) -> str:
        """Get the A-Z subdirectory letter from the first author's lastname.

        Strategy:
        1. Strip leading nobiliary particles ("van der", "el", "de los", ...)
           so "el Karoui" files under K (existing convention).
        2. NFD-decompose to strip accents, then take the first ASCII letter.
        3. Greek letters are mapped to their Latin equivalents
           (e.g., "Αλεξανδρης" → A).
        4. Cyrillic letters are romanised to Latin (best-effort).
        5. Anything still non-Latin lands in Z, but we log a warning so the
           user can spot misfiled papers.
        """
        if not first_author_lastname:
            return "Z"

        # Remove nobiliary particles from the front so "el Karoui" → "Karoui"
        name = first_author_lastname.strip()
        words = name.split()
        # Try greedy match for two-word particles ("van der", "de la"), then one-word
        if len(words) >= 3 and " ".join(words[:2]).lower() in _ALPHA_PARTICLES:
            words = words[2:]
        elif len(words) >= 2 and words[0].lower() in _ALPHA_PARTICLES:
            words = words[1:]
        if words:
            name = words[0]

        # NFD-decompose then drop combining marks; take the first letter
        decomposed = unicodedata.normalize("NFD", name)
        for ch in decomposed:
            if unicodedata.combining(ch):
                continue
            up = ch.upper()
            if "A" <= up <= "Z":
                return up
            # Latin letters with strokes that NFD doesn't decompose (Ł, Ø, ...)
            if up in _LATIN_SPECIAL_TO_LATIN:
                return _LATIN_SPECIAL_TO_LATIN[up]
            # Greek capital letters → Latin (Α=A, Β=B, etc.)
            if "Α" <= up <= "Ω":
                return _GREEK_TO_LATIN.get(up, "Z")
            # Cyrillic letters → Latin (best effort)
            if "А" <= up <= "Я":
                return _CYRILLIC_TO_LATIN.get(up, "Z")
            # Non-letter (digit/punct) — keep scanning
            if not up.isalpha():
                continue
            break  # other script: give up

        logger.warning("get_alpha_subdir: filing %r under Z (no Latin first letter)", first_author_lastname)
        return "Z"

    def route(
        self,
        metadata: Dict,
        filename: str,
        *,
        year: Optional[int] = None,
    ) -> Path:
        """Determine the full destination path for a paper.

        Parameters
        ----------
        metadata : dict
            Paper metadata (must include at minimum first author info).
        filename : str
            The canonical filename (e.g. ``"Dupont, F. - Title.pdf"``).
        year : int or None
            Publication/submission year (used for working papers).

        Returns
        -------
        Path
            Full destination path including the filename.
        """
        status = self.determine_publication_status(metadata)
        status_dir_name = STATUS_DIRS.get(status, WORKING)

        # Determine base: topic folder or top-level
        base = self._topic_dir if self._topic_dir else self.library_root

        # Build path
        target = base / status_dir_name

        # Extract first author lastname for alphabetical routing
        authors = metadata.get("authors", [])
        first_lastname = ""
        if authors:
            if isinstance(authors[0], dict):
                first_lastname = authors[0].get("family", authors[0].get("name", ""))
            elif isinstance(authors[0], str):
                # "Lastname, I." or "I. Lastname" format
                name = authors[0].strip()
                if ", " in name:
                    first_lastname = name.split(",")[0].strip()
                elif " " in name:
                    # "I. Lastname" — last word is the lastname
                    first_lastname = name.split()[-1].strip()
                else:
                    first_lastname = name

        # Add alphabetical subdirectory (for 01, 02, 03, 06)
        if status in ("published", "unpublished", "working", "thesis"):
            if not first_lastname:
                # Falling through to "Z" silently used to mask malformed
                # metadata. Log so the user can spot data-quality issues
                # in the maintenance report.
                logger.warning(
                    "route: empty first author for %r (authors=%r) — filing under Z",
                    filename, authors,
                )
            alpha = self.get_alpha_subdir(first_lastname)
            target = target / alpha

        # Working papers additionally have year subdirectories
        if status == "working" and year:
            target = target / str(year)

        return target / filename


# ---------------------------------------------------------------------------
# Main organization system
# ---------------------------------------------------------------------------
class OrganizationSystem:
    """Organizes papers into the library directory structure.

    Parameters
    ----------
    library_root : Path
        Top-level library directory (e.g. ``…/Maths/``).
    topic : str or None
        Optional topic prefix (e.g. ``"07a"``) for topic-specific filing.
    dry_run : bool
        If True, report actions without moving files.
    """

    def __init__(
        self,
        library_root: Path,
        *,
        topic: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.library_root = library_root
        self.dry_run = dry_run
        self.validator = ContentValidator()
        self.router = FolderRouter(library_root, topic=topic)

    def organize(
        self,
        file_path: Path,
        metadata: Dict,
        filename: str,
        *,
        year: Optional[int] = None,
        undo_log=None,
    ) -> OrganizationResult:
        """File a paper into the correct library location.

        Parameters
        ----------
        file_path : Path
            Current location of the PDF.
        metadata : dict
            Paper metadata.
        filename : str
            Canonical filename to use (e.g. ``"Dupont, F. - Title.pdf"``).
        year : int or None
            Publication/submission year for working papers.
        """
        actions: List[str] = []

        # Validate PDF
        if not self.validator.validate_pdf_integrity(file_path):
            actions.append("WARNING: failed PDF integrity check")

        # Determine destination
        status = self.router.determine_publication_status(metadata)
        destination = self.router.route(metadata, filename, year=year)

        # Collision guard (live-trial fix): a destination that already
        # exists used to be logged as a WARNING and then COPIED OVER,
        # silently clobbering a previously-filed paper.  That's data
        # loss.  Now we distinguish two cases by CONTENT:
        #   * Same bytes already at the destination -> idempotent
        #     re-ingest (e.g. re-running the pipeline on a paper that's
        #     already filed).  Skip the copy, let downstream sidecar
        #     bookkeeping proceed.
        #   * Different bytes -> a genuinely different paper colliding
        #     on the canonical name.  Refuse: leave the existing file
        #     untouched and surface an ERROR.
        if destination.exists() and destination.resolve() != file_path.resolve():
            if _same_content(file_path, destination):
                actions.append(f"already filed (identical content) at {destination}")
                return OrganizationResult(
                    file_path=file_path,
                    destination=destination,
                    actions=actions,
                    publication_status=status,
                )
            actions.append(
                f"ERROR: destination already exists with different content, "
                f"refusing to overwrite: {destination}"
            )
            return OrganizationResult(
                file_path=file_path,
                destination=destination,
                actions=actions,
                publication_status=status,
            )

        # Perform the move
        if not self.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if file_path.resolve() != destination.resolve():
                try:
                    # Audit-10: record the copy BEFORE performing it.  If
                    # the process dies between copy2 and record_copy, the
                    # destination exists but the undo log has no trace, so
                    # the orphaned PDF can never be undone.  Recording
                    # first is safe: if the copy then fails, undo simply
                    # finds the copy "already gone" and skips it.
                    if undo_log is not None:
                        undo_log.record_copy(file_path, destination)
                    shutil.copy2(file_path, destination)
                    actions.append(f"copied to {destination}")
                except Exception as exc:
                    logger.error("Failed to copy %s → %s: %s", file_path, destination, exc)
                    actions.append(f"ERROR: copy failed: {exc}")
        else:
            actions.append(f"would copy to {destination}")

        return OrganizationResult(
            file_path=file_path,
            destination=destination,
            actions=actions,
            publication_status=status,
        )

# ---------------------------------------------------------------------------
# Repository detection — these are NOT journal publications
# ---------------------------------------------------------------------------

# DOI prefixes that belong to repositories, not journals
_REPOSITORY_DOI_PREFIXES = (
    "10.2139/ssrn",       # SSRN
    "10.48550/arxiv",     # arXiv
    "10.26509/",          # HAL (some)
    "10.5281/zenodo",     # Zenodo
    "10.3386/",           # NBER
    "10.21034/",          # Federal Reserve
    "10.17863/",          # Cambridge repository
    "10.2139/",           # SSRN (broader prefix)
    "10.1101/",           # bioRxiv / medRxiv
)

# Journal names that are actually repositories
_REPOSITORY_JOURNAL_NAMES = (
    "ssrn electronic journal",
    "ssrn",
    "arxiv",
    "hal",
    "nber working paper",
    "nber",
    "cepr discussion paper",
    "repec",
    "zenodo",
    "biorxiv",
    "medrxiv",
    "working paper",
    "discussion paper",
    "technical report",
    "preprint",
)


def _same_content(a: Path, b: Path) -> bool:
    """True if two files are byte-identical (cheap size check first).

    Used by the collision guard to tell an idempotent re-ingest of the
    same paper from a genuine name collision between two different
    papers.  Compares size, then full SHA-256 only when sizes match.
    """
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        import hashlib
        ha, hb = hashlib.sha256(), hashlib.sha256()
        for path, h in ((a, ha), (b, hb)):
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
        return ha.hexdigest() == hb.hexdigest()
    except OSError:
        return False


def _is_repository_doi(doi: str) -> bool:
    """Check if a DOI belongs to a repository (not a journal)."""
    doi_lower = doi.lower().strip()
    return any(doi_lower.startswith(prefix) for prefix in _REPOSITORY_DOI_PREFIXES)


def _is_repository_journal(journal: str) -> bool:
    """Check if a journal name is actually a repository."""
    j_lower = journal.lower().strip()
    return any(repo in j_lower for repo in _REPOSITORY_JOURNAL_NAMES)


__all__ = [
    "OrganizationSystem",
    "OrganizationResult",
    "FolderRouter",
    "PUBLISHED",
    "UNPUBLISHED",
    "WORKING",
    "TO_DOWNLOAD",
    "BOOKS",
    "THESES",
    "STATUS_DIRS",
]
