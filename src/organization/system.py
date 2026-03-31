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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

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


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------
class DuplicateDetector:
    def find_exact_duplicates(self, files: Iterable[Path]) -> Dict[str, List[Path]]:
        import hashlib

        hash_map: Dict[str, List[Path]] = defaultdict(list)
        for file_path in files:
            if not file_path.exists():
                continue
            hasher = hashlib.sha256()
            with open(file_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(8192), b""):
                    hasher.update(chunk)
            hash_map[hasher.hexdigest()].append(file_path)
        return {d: paths for d, paths in hash_map.items() if len(paths) > 1}


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
        """Determine publication status from metadata."""
        doc_type = metadata.get("document_type", "").lower()
        if doc_type in ("book", "lecture_notes"):
            return "book"
        if doc_type == "thesis":
            return "thesis"

        if metadata.get("doi"):
            return "published"
        if metadata.get("journal"):
            # Has a journal but no DOI — accepted but not fully published
            return "published"
        if metadata.get("arxiv_id"):
            return "unpublished"
        return "working"

    def get_alpha_subdir(self, first_author_lastname: str) -> str:
        """Get the A-Z subdirectory letter from the first author's lastname."""
        if not first_author_lastname:
            return "Z"  # fallback
        first_char = unicodedata.normalize("NFD", first_author_lastname)[0].upper()
        if "A" <= first_char <= "Z":
            return first_char
        return "Z"  # non-Latin names go to Z

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
        self.duplicate_detector = DuplicateDetector()

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

        # Check for existing file at destination
        if destination.exists() and destination != file_path:
            actions.append(f"WARNING: destination already exists: {destination}")

        # Perform the move
        if not self.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if file_path.resolve() != destination.resolve():
                try:
                    shutil.copy2(file_path, destination)
                    actions.append(f"copied to {destination}")
                    if undo_log is not None:
                        undo_log.record_copy(file_path, destination)
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

    def find_duplicates(self, files: Iterable[Path]) -> Dict[str, List[Path]]:
        return self.duplicate_detector.find_exact_duplicates(files)


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
