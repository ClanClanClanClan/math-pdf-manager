"""Core metadata object (CMO) definitions used across the ArXiv bot."""
from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)


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
        """Generate a ready-to-use canonical filename.

        Format: ``Lastname1, I., Lastname2, I. - Title.pdf``

        Runs the complete validation pipeline:
        1. NFC normalisation
        2. Colon → comma (subtitle convention)
        3. Build author + title filename
        4. **Full validation via ``check_filename()``** — sentence case,
           dash whitelist, ligature expansion, quotation marks, ellipsis,
           dangerous Unicode removal, author format validation
        5. Byte-limit enforcement (author list compressed if needed)

        Falls back to basic formatting if the validator is unavailable.
        """
        if max_bytes <= 0:
            max_bytes = _get_fs_name_max() - 4  # reserve for ".pdf"

        title = unicodedata.normalize("NFC", re.sub(r"\s+", " ", self.title.strip()))

        # Replace colon with comma (subtitle convention: "Title: Subtitle"
        # → "Title, subtitle" after sentence case lowercases the next word)
        title = title.replace(":", ",")

        # Clean filesystem-unsafe characters from title
        title = _clean_for_fs(title)

        # Build filename with as many authors as possible
        if not self.authors:
            base = title
        else:
            all_segments = self._author_segments()
            separator = " - "
            title_part = separator + title

            base = self._build_with_max_authors(
                all_segments, title_part, max_bytes
            )

        # Add .pdf before validation (check_filename expects it)
        if not base.lower().endswith(".pdf"):
            base += ".pdf"

        # ── Full validation pipeline ──────────────────────────────────
        base = _validate_filename(base)

        # Final byte-limit enforcement (safety net after validation)
        encoded = base.encode("utf-8")
        max_with_ext = max_bytes + 4  # include .pdf in limit
        if len(encoded) > max_with_ext:
            # Strip .pdf, truncate, re-add
            stem = encoded[: max_bytes].decode("utf-8", "ignore").rstrip()
            base = stem + ".pdf"

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

        full = ", ".join(all_segments) + title_part
        if len(full.encode("utf-8")) <= max_bytes:
            return full

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
        library = os.path.expanduser(
            "~/Library/CloudStorage/Dropbox/Work/Maths"
        )
        if os.path.isdir(library):
            _FS_NAME_MAX = os.pathconf(library, "PC_NAME_MAX")
        else:
            _FS_NAME_MAX = os.pathconf(".", "PC_NAME_MAX")
    except (OSError, ValueError):
        _FS_NAME_MAX = 255

    return _FS_NAME_MAX


def _clean_for_fs(text: str) -> str:
    """Remove filesystem-unsafe characters and normalise spaces."""
    text = re.sub(r"[\u0000-\u001f]", "", text)  # control chars
    text = text.replace("/", "–")   # slash → en-dash
    text = text.replace("\\", "–")  # backslash → en-dash
    # Normalise all Unicode space variants to regular space
    text = re.sub(r"[\u00a0\u2000-\u200a\u202f\u2009]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ----------------------------------------------------------------------
# Validator integration
# ----------------------------------------------------------------------
_VALIDATOR_CONFIG: Optional[Dict[str, Any]] = None


def _load_validator_config() -> Dict[str, Any]:
    """Load and cache all whitelists needed by check_filename().

    Searches for data files relative to the project root (detected
    from ``__file__`` → ``src/arxivbot/models/cmo.py`` → up 4 levels).
    """
    global _VALIDATOR_CONFIG
    if _VALIDATOR_CONFIG is not None:
        return _VALIDATOR_CONFIG

    # Find project root: cmo.py is at src/arxivbot/models/cmo.py
    project_root = Path(__file__).resolve().parent.parent.parent.parent

    def _load_set(filename: str) -> Set[str]:
        """Load a newline-delimited text file into a set."""
        for candidate in [
            project_root / "data" / filename,
            project_root / filename,
        ]:
            if candidate.exists():
                return {
                    line.strip()
                    for line in candidate.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.startswith("#")
                }
        return set()

    def _load_yaml_whitelist() -> Set[str]:
        """Load capitalization_whitelist from config.yaml."""
        config_path = project_root / "config" / "config.yaml"
        if not config_path.exists():
            return set()
        try:
            import yaml
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            wl = data.get("capitalization_whitelist") or data.get("exceptions", {}).get("capitalization_whitelist", [])
            return set(wl) if wl else set()
        except Exception:
            return set()

    _VALIDATOR_CONFIG = {
        "known_words": _load_set("known_words_1.txt") | _load_set("known_words.txt"),
        "capitalization_whitelist": _load_yaml_whitelist(),
        "name_dash_whitelist": _load_set("name_dash_whitelist.txt"),
        "exceptions": _load_set("exceptions.txt"),
        "compound_terms": set(),  # loaded from config.yaml if available
        "multiword_surnames": _load_set("multiword_familynames_1.txt") | _load_set("multiword_familynames.txt"),
    }

    logger.debug(
        "Loaded validator config: %s",
        {k: len(v) for k, v in _VALIDATOR_CONFIG.items()},
    )
    return _VALIDATOR_CONFIG


def _validate_filename(filename: str) -> str:
    """Run the full validation pipeline on a filename.

    Calls ``check_filename()`` with all whitelists and auto-fix options.
    Returns the corrected filename if changes were made, otherwise the
    original.  Falls back to basic sentence case if the validator is
    unavailable.
    """
    try:
        from validators.filename_checker.core import check_filename

        config = _load_validator_config()

        result = check_filename(
            filename,
            known_words=config["known_words"],
            whitelist_pairs=list(config["multiword_surnames"]),
            exceptions=config["exceptions"],
            compound_terms=config["compound_terms"],
            capitalization_whitelist=config["capitalization_whitelist"],
            name_dash_whitelist=config["name_dash_whitelist"],
            multiword_surnames=config["multiword_surnames"],
            sentence_case=True,
            auto_fix_nfc=True,
            auto_fix_authors=True,
        )

        if result.corrected_filename:
            return result.corrected_filename
        return filename

    except ImportError:
        logger.debug("Filename validator not available, using basic formatting")
        # Minimal fallback: just apply basic sentence case
        return _minimal_sentence_case_filename(filename)
    except Exception as exc:
        logger.warning("Filename validation failed: %s", exc)
        return filename


def _minimal_sentence_case_filename(filename: str) -> str:
    """Bare-minimum sentence case when the validator isn't available.

    Splits on `` - ``, applies basic sentence case to the title part,
    and reassembles.
    """
    if " - " not in filename:
        return filename

    parts = filename.split(" - ", 1)
    authors = parts[0]
    title_with_ext = parts[1]

    # Strip .pdf for processing
    if title_with_ext.lower().endswith(".pdf"):
        title = title_with_ext[:-4]
        ext = ".pdf"
    else:
        title = title_with_ext
        ext = ""

    # Basic sentence case
    words = title.split()
    result = []
    for i, word in enumerate(words):
        stripped = word.strip(".,;:!?()[]")
        if i == 0:
            if stripped.islower() and "-" in stripped:
                result.append(word.lower())
            else:
                result.append(word[0].upper() + word[1:] if len(word) > 1 else word.upper())
        elif stripped.isupper() and 2 <= len(stripped) <= 5:
            result.append(word)
        elif not stripped.islower() and not stripped.isupper() and any(c.isupper() for c in stripped[1:]):
            result.append(word)
        else:
            result.append(word.lower())

    return f"{authors} - {' '.join(result)}{ext}"


def ensure_iterable_authors(raw: Iterable[dict[str, Any] | Author]) -> List[Author]:
    return [CMO._coerce_author(author) for author in raw]


__all__ = ["Author", "Citation", "CMO", "ensure_iterable_authors"]
