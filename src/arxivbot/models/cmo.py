"""Core metadata object (CMO) definitions used across the ArXiv bot."""
from __future__ import annotations

import json
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

    def get_canonical_filename(self, *, et_al_threshold: int = 8) -> str:
        """Generate a canonical filename matching the library convention.

        Format: ``Lastname1, I., Lastname2, I. - Title.pdf``

        Authors are listed up to ``et_al_threshold`` (default 8).  When
        a paper has more authors than the threshold, only the first 3 are
        listed followed by ", et al.".  Math symbols (ℝ, ℤ, ≤, etc.)
        and Unicode are preserved.  Only filesystem-unsafe characters
        (``/``, ``\\``, null bytes, control chars) are removed.
        """
        author_segments = self._format_authors(et_al_threshold=et_al_threshold)
        title = unicodedata.normalize("NFC", re.sub(r"\s+", " ", self.title.strip()))
        base = f"{author_segments} - {title}" if author_segments else title
        # Remove only control chars and filesystem-unsafe characters
        cleaned = re.sub(r"[\u0000-\u001f]", "", base)
        cleaned = cleaned.replace("/", "–")   # slash → en-dash
        cleaned = cleaned.replace("\\", "–")
        cleaned = cleaned.replace(":", " –")  # colon can be problematic on some FS
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Ensure filename fits filesystem limits (255 bytes UTF-8 for most FS)
        max_bytes = 250  # leave room for .pdf extension
        encoded = cleaned.encode("utf-8")
        if len(encoded) > max_bytes:
            cleaned = encoded[:max_bytes].decode("utf-8", "ignore").rstrip()
        if not cleaned.lower().endswith(".pdf"):
            cleaned += ".pdf"
        return cleaned

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _format_authors(self, *, et_al_threshold: int = 8) -> str:
        """Format authors as ``Lastname, I., Lastname2, I.``

        When there are more than ``et_al_threshold`` authors, only the
        first 3 are listed followed by ", et al.".
        """
        if not self.authors:
            return ""

        use_et_al = len(self.authors) > et_al_threshold
        authors_to_show = self.authors[:3] if use_et_al else self.authors

        segments: List[str] = []
        for author in authors_to_show:
            initials = author.initials()
            if initials:
                segments.append(f"{author.family}, {initials}.")
            else:
                segments.append(author.family)
        if use_et_al:
            segments.append("et al.")
        return ", ".join(segments)

    # Convenience accessors -------------------------------------------------
    def list_author_names(self) -> List[str]:
        return [a.display_name() for a in self.authors]

    def primary_category(self) -> str | None:
        return self.categories[0] if self.categories else None


def ensure_iterable_authors(raw: Iterable[dict[str, Any] | Author]) -> List[Author]:
    return [CMO._coerce_author(author) for author in raw]


__all__ = ["Author", "Citation", "CMO", "ensure_iterable_authors"]
