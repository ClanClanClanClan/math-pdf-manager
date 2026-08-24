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


@dataclass
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
        """Initials in the library's canonical SPACED form.

        Separate given names join with dot+space ("Paul André" → "P. A",
        so the filename reads "Dupont, P. A."), matching the owner's rule
        that initials are spaced ("R. C.", never "R.C.") and the
        validator's ``fix_initial_spacing``.  Hyphenated names keep the
        hyphen-dot shape with no inner space ("Jean-Pierre" → "J.-P").
        """
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
        return ". ".join(segments)


@dataclass
class Citation:
    """Minimal citation representation."""

    target_id: str
    context: str | None = None
    score: float | None = None


@dataclass
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
        all_segments = self._author_segments() if self.authors else []
        if not all_segments:
            # Either there were no authors, or sanitising removed every
            # one of them (a surname that was nothing but control
            # characters).  Both mean the same thing here: there is no
            # author block, so the name is the title alone.  Falling
            # through instead produced " - A test title.pdf", with a
            # leading separator and an empty author slot.
            base = title
        else:
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

        # Final byte-limit enforcement (safety net after validation).
        # Decode with errors="ignore" can leave a dangling partial UTF-8
        # sequence at the cut point, so we explicitly trim to a UTF-8 char
        # boundary, then to a clean word boundary if possible.
        encoded = base.encode("utf-8")
        max_with_ext = max_bytes + 4  # include .pdf in limit
        if len(encoded) > max_with_ext:
            # Try to cut at a clean codepoint boundary
            stem_bytes = encoded[:max_bytes]
            # Walk back to a UTF-8 lead byte (top bits not 10xxxxxx) so we
            # don't split a multi-byte character.
            while stem_bytes and (stem_bytes[-1] & 0xC0) == 0x80:
                stem_bytes = stem_bytes[:-1]
            # Decode strictly now that the boundary is clean
            try:
                stem = stem_bytes.decode("utf-8")
            except UnicodeDecodeError:
                # Belt-and-braces — fall back to lossy decode if the lead-byte
                # walk-back wasn't enough (shouldn't happen for valid input).
                stem = stem_bytes.decode("utf-8", "ignore")
            # Prefer to break at a word boundary so we don't cut mid-word.
            # Look for the last space or comma in the last 32 chars; if found,
            # truncate there. Otherwise keep the codepoint-clean cut.
            tail_window = stem[-32:]
            for sep in (" ", ", ", "—", "–"):
                idx = tail_window.rfind(sep)
                if idx >= 0:
                    stem = stem[: len(stem) - len(tail_window) + idx]
                    break
            stem = stem.rstrip(" ,;:.-—–")
            base = stem + ".pdf"

        return base

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _author_segments(self) -> List[str]:
        """Format each author as ``Lastname, I.`` and return a list.

        Audit-8: NFC-normalise each segment so the byte-length
        accounting in ``_build_with_max_authors`` is deterministic
        regardless of input form.  Without this, "Möbius" arriving
        as ``M + U+0308 + öbius`` (decomposed combining mark) would
        encode to one more byte than its precomposed equivalent
        ``Möbius``, and the et-al truncation would inconsistently
        clip one extra author.
        """
        segments: List[str] = []
        for author in self.authors:
            family = unicodedata.normalize("NFC", author.family or "")
            initials = unicodedata.normalize("NFC", author.initials() or "")
            # The title goes through _clean_for_fs; the author block never
            # did, so anything filesystem-hostile in a surname walked
            # straight into the filename.  Measured on a 1,753-paper
            # stratified sample of the library, read through opaque
            # symlinks: 11 proposed names carried a raw U+0010, all from
            # one family of scanned Russian PDFs whose embedded /Author is
            # mojibake for "Администратор".  A surname containing "/" is
            # rarer but worse -- "/" is the one character macOS actually
            # forbids.
            family = _clean_for_fs(family)
            initials = _clean_for_fs(initials)
            if family and initials:
                segments.append(f"{family}, {initials}.")
            elif family:
                segments.append(family)
            elif initials:
                # Cleaning ate the surname entirely.  Emitting ", J." would
                # produce a filename starting with a comma, so drop the
                # author rather than invent a shape the library never uses.
                continue
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
        # Use the configured library root so we query the actual filesystem
        # the user is filing into (its PC_NAME_MAX may differ from ".").
        try:
            from core.config_paths import get_library_root
            library = str(get_library_root())
        except ImportError:
            library = ""
        if library and os.path.isdir(library):
            _FS_NAME_MAX = os.pathconf(library, "PC_NAME_MAX")
        else:
            _FS_NAME_MAX = os.pathconf(".", "PC_NAME_MAX")
    except (OSError, ValueError):
        _FS_NAME_MAX = 255

    return _FS_NAME_MAX


def _clean_for_fs(text: str) -> str:
    """Remove filesystem-unsafe characters and normalise spaces."""
    # All THREE control ranges, not just C0.  The old pattern stopped at
    # U+001F, so U+007F DELETE and the C1 block U+0080-U+009F walked
    # through -- and seven files in the live library are named through
    # that hole today, among them "Lindensj<U+007F>o", "Benezet<U+0084>"
    # and "Cvitanic<U+0087>".  They are invisible in Finder, they break
    # sorting and search, and nothing flagged them because the check only
    # ever looked at the first range.  Found by a property test, not by
    # reading the code.
    text = re.sub(r"[\u0000-\u001f\u007f-\u009f]", "", text)  # C0, DEL, C1
    # "/" is the ONLY character macOS forbids in a filename, and it takes a
    # HYPHEN, not an en dash.  The house convention reserves the en dash for
    # two co-equal entities (Hamilton–Jacobi) and uses a hyphen for one word
    # built from parts — which is exactly what "on/off" and "super/sub" are.
    text = text.replace("/", "-")
    # The backslash is NOT replaced, because it is not illegal: verified on
    # this filesystem, "\\", ":", "|" and "?" are all legal in a macOS
    # filename.  Rewriting it to an en dash had no safety justification and
    # did real damage — 89 of the 1,873 inbox titles carry LaTeX residue,
    # and every one of them was getting a fabricated en dash
    # ("$-\\infty$" -> "$-–infty$", "$\\mathbb{L}^p$" -> "$–mathbb{L}^p$").
    # Residue that survives _unlatex is left visible so the conformance and
    # spelling checks can flag it, rather than disguised as punctuation the
    # library treats as meaningful.
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

    Delegates path resolution to :mod:`core.config_paths` so that this
    module and ``core.sentence_case`` always read the same files
    regardless of cwd.
    """
    global _VALIDATOR_CONFIG
    if _VALIDATOR_CONFIG is not None:
        return _VALIDATOR_CONFIG

    from core.config_paths import load_set_from_files, load_yaml_section

    cap_wl = (
        load_yaml_section("capitalization_whitelist")
        or load_yaml_section("exceptions", "capitalization_whitelist")
        or []
    )

    _VALIDATOR_CONFIG = {
        "known_words": load_set_from_files("known_words_1.txt", "known_words.txt"),
        "capitalization_whitelist": set(cap_wl) if cap_wl else set(),
        "name_dash_whitelist": load_set_from_files("name_dash_whitelist.txt"),
        "exceptions": load_set_from_files("exceptions.txt"),
        "compound_terms": set(),  # loaded from config.yaml if available
        "multiword_surnames": load_set_from_files(
            "multiword_familynames_1.txt", "multiword_familynames.txt"
        ),
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
            # Title casing is deliberately NOT done here: this engine's
            # default lowercases any capitalized word missing from its
            # whitelist, which mangles unseen proper nouns.  The SAFE
            # caser (processing.title_normalize — preserve-and-queue
            # default, corpus oracle) runs in ingest_paper where the
            # library context lives, exactly as on moves.
            sentence_case=False,
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
