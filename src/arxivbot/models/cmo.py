"""Core metadata object (CMO) definitions used across the ArXiv bot."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, List, Optional


@dataclass(slots=True)
class Author:
    """Represents an individual author."""

    family: str
    given: str | None = None
    affiliations: List[str] = field(default_factory=list)

    def display_name(self) -> str:
        if self.given:
            return f"{self.family}, {self.given}"
        return self.family

    def initials(self) -> str:
        if not self.given:
            return ""
        tokens = re.split(r"\s+", self.given.strip())
        segments: List[str] = []
        for token in tokens:
            if not token:
                continue
            subparts = [part for part in token.split("-") if part]
            if not subparts:
                continue
            if len(subparts) == 1:
                segments.append(subparts[0][0].upper())
            else:
                segments.append(".-".join(part[0].upper() for part in subparts))
        return ".".join(segments)


@dataclass(slots=True)
class Citation:
    """Minimal citation representation."""

    target_id: str
    context: str | None = None
    score: float | None = None


@dataclass(slots=True)
class CMO:
    """Core metadata object produced by the harvester layer."""

    external_id: str
    source: str
    title: str
    authors: List[Author] = field(default_factory=list)
    published: str | None = None
    abstract: str | None = None
    pdf_url: str | None = None
    categories: List[str] = field(default_factory=list)
    doi: str | None = None
    license: str | None = None
    citations: List[Citation] = field(default_factory=list)
    score: float | None = None

    def __post_init__(self) -> None:
        # Ensure authors are Author instances even if dictionaries were provided.
        self.authors = [self._coerce_author(a) for a in self.authors or []]
        self.citations = [self._coerce_citation(c) for c in self.citations or []]

    @staticmethod
    def _coerce_author(author: Author | dict | Any) -> Author:
        if isinstance(author, Author):
            return author
        if isinstance(author, dict):
            return Author(**author)
        raise TypeError(f"Unsupported author payload: {author!r}")

    @staticmethod
    def _coerce_citation(citation: Citation | dict | Any) -> Citation:
        if isinstance(citation, Citation):
            return citation
        if isinstance(citation, dict):
            return Citation(**citation)
        raise TypeError(f"Unsupported citation payload: {citation!r}")

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, payload: str | dict[str, Any]) -> "CMO":
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
        return cls(**data)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def get_embedding_text(self) -> str:
        parts = [self.title.strip()]
        if self.abstract:
            parts.append(re.sub(r"\s+", " ", self.abstract.strip()))
        return " ".join(parts)

    def get_canonical_filename(self, *, max_bytes: int = 0) -> str:
        """Generate a canonical filename matching the library convention.

        Format: ``Lastname1, I., Lastname2, I. - Title.pdf``

        Includes as many authors as possible while respecting the
        filesystem byte limit.  When not all authors fit, the included
        authors are followed by ", et al.".

        Title is in sentence case (applied by the caller or by
        ``to_sentence_case_academic`` — this method preserves the title
        as given).

        Math symbols (ℝ, ℤ, ≤, etc.) and Unicode are preserved.  Only
        filesystem-unsafe characters (``/``, ``\\``, null bytes, control
        chars) are removed.

        Parameters
        ----------
        max_bytes : int
            Maximum filename length in UTF-8 bytes (excluding ``.pdf``).
            If 0, auto-detected from the filesystem (``NAME_MAX``).
        """
        if max_bytes <= 0:
            max_bytes = _get_fs_name_max() - 4  # reserve for ".pdf"

        title = unicodedata.normalize("NFC", re.sub(r"\s+", " ", self.title.strip()))

        # Clean title of filesystem-unsafe characters
        title = _clean_for_fs(title)

        # Build filename with as many authors as possible
        if not self.authors:
            base = title
        else:
            all_segments = self._author_segments()
            separator = " - "
            title_part = separator + title  # constant suffix

            # Binary search for maximum authors that fit
            base = self._build_with_max_authors(
                all_segments, title_part, max_bytes
            )

        # Final byte-limit enforcement (safety net)
        encoded = base.encode("utf-8")
        if len(encoded) > max_bytes:
            base = encoded[:max_bytes].decode("utf-8", "ignore").rstrip()

        if not base.lower().endswith(".pdf"):
            base += ".pdf"
        return base

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _author_segments(self) -> List[str]:
        """Format each author as ``Lastname, I.`` and return a list."""
        segments: List[str] = []
        for author in self.authors:
            initials = author.initials()
            if initials:
                segments.append(f"{author.family}, {initials}.")
            else:
                segments.append(author.family)
        return segments

    def _build_with_max_authors(
        self, all_segments: List[str], title_part: str, max_bytes: int
    ) -> str:
        """Include as many authors as possible, using 'et al.' when truncated."""
        n = len(all_segments)
        et_al = ", et al."

        # Try all authors first
        full = ", ".join(all_segments) + title_part
        if len(full.encode("utf-8")) <= max_bytes:
            return full

        # Binary search: find largest k such that
        # "Author1, ..., Authork, et al. - Title" fits
        lo, hi, best_k = 1, n - 1, 1
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = ", ".join(all_segments[:mid]) + et_al + title_part
            if len(candidate.encode("utf-8")) <= max_bytes:
                best_k = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return ", ".join(all_segments[:best_k]) + et_al + title_part

    # Convenience accessors -------------------------------------------------
    def list_author_names(self) -> List[str]:
        return [a.display_name() for a in self.authors]

    def primary_category(self) -> str | None:
        return self.categories[0] if self.categories else None


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------
_FS_NAME_MAX: int | None = None


def _get_fs_name_max() -> int:
    """Return the filesystem NAME_MAX for the library directory."""
    global _FS_NAME_MAX
    if _FS_NAME_MAX is not None:
        return _FS_NAME_MAX

    try:
        # Try the library path first
        library = os.path.expanduser(
            "~/Library/CloudStorage/Dropbox/Work/Maths"
        )
        if os.path.isdir(library):
            _FS_NAME_MAX = os.pathconf(library, "PC_NAME_MAX")
        else:
            _FS_NAME_MAX = os.pathconf(".", "PC_NAME_MAX")
    except (OSError, ValueError):
        _FS_NAME_MAX = 255  # POSIX default

    return _FS_NAME_MAX


def _clean_for_fs(text: str) -> str:
    """Remove filesystem-unsafe characters from text."""
    text = re.sub(r"[\u0000-\u001f]", "", text)  # control chars
    text = text.replace("/", "–")   # slash → en-dash
    text = text.replace("\\", "–")  # backslash → en-dash
    text = text.replace(":", " –")  # colon → space + en-dash
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ensure_iterable_authors(raw: Iterable[dict[str, Any] | Author]) -> List[Author]:
    return [CMO._coerce_author(author) for author in raw]


__all__ = ["Author", "Citation", "CMO", "ensure_iterable_authors"]
