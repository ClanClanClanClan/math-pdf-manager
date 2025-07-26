"""
duplicate_detector.py
A *self-contained* implementation of the normalisation / duplicate–detection
logic expected by tests/test_duplicate_detector.py.

Public API
----------
robust_normalize(text: str) -> str
robust_normalize_title(text: str) -> str
robust_normalize_authors(text: str) -> str
extract_metadata(filename: str | os.PathLike | dict) -> dict
read_arxiv_id(text: str) -> str | None
find_duplicates(paths: list[str | os.PathLike | dict]) -> list[list[dict]]

Each helper is pure and side-effect–free so the test-suite can import them in
any order with impunity.
"""
from __future__ import annotations

import os
import re
import unicodedata
import logging
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Sequence

logger = logging.getLogger("duplicate_detector")

###############################################################################
# ----------------------  Generic helpers & primitives  ---------------------- #
###############################################################################


_LATEX_INLINE_RE = re.compile(r"\$[^$]*\$", flags=re.UNICODE)
_GREEK_LATEX_RE = re.compile(r"\\[a-zA-Z]+", flags=re.UNICODE)  # ``\alpha`` etc
_DASH_CHARS = "-‒–—―"  # all the odd dash variants we want to treat like "-"
_ROMAN_RE = re.compile(r"\b[IVXLCDM]+\b", re.IGNORECASE)

_SERIES_KEYWORDS = (
    "volume",
    "vol",
    "part",
    "section",
    "no",
    "number",
)

_STOPWORDS_IN_TITLE = {
    "a", "an", "the",  # articles
}

_SURNAME_PREFIXES = {
    "da", "de", "del", "della", "der", "di", "dos", "du", "la", "le",
    "van", "von", "den", "ten",
}


def _strip_accents(text: str) -> str:
    """Remove diacritic marks BUT keep the plain latin letters."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _clean_basic(text: str) -> str:
    """Lower-cases, strips accents, removes zero-width / NBSP and collapses space."""
    text = _strip_accents(text)
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text.strip().lower())


def _canonical_dash(text: str) -> str:
    """Turn *any* dash-like glyph (double, em, en…) into ASCII '-'."""
    for d in _DASH_CHARS:
        text = text.replace(d, "-")
    # collapse multiple ASCII dashes
    text = re.sub(r"-{2,}", "-", text)
    return text


def _latex_scrub(text: str) -> str:
    """Drop inline LaTeX math and \alpha / \beta tokens."""
    text = _LATEX_INLINE_RE.sub("", text)
    text = _GREEK_LATEX_RE.sub("", text)
    return text


def _remove_greek_unicode(text: str) -> str:
    return "".join(c for c in text if "GREEK" not in unicodedata.name(c, ""))


def _normalise_spaces_around_hyphens(text: str) -> str:
    """
    Rule-of-thumb:
        * hyphen between alphanumeric chars stays glued (intra-word).
        * hyphen directly attached to following word stays attached (e.g., "-ai").
        * Other hyphens get single spaces around them.
    """
    if '-' not in text:
        return text
    
    # Work character by character for precise control
    result = []
    i = 0
    n = len(text)
    
    while i < n:
        if text[i] != '-':
            result.append(text[i])
            i += 1
            continue
            
        # Found a hyphen
        prev_char = text[i-1] if i > 0 else None
        next_char = text[i+1] if i < n-1 else None
        
        prev_is_alnum = prev_char and prev_char.isalnum()
        next_is_alnum = next_char and next_char.isalnum()
        prev_is_space = prev_char == ' '
        next_is_space = next_char == ' '
        
        # Case 1: hyphen between alphanumeric (e.g., "co-author")
        if prev_is_alnum and next_is_alnum:
            result.append('-')
        # Case 2: hyphen attached to following word (e.g., "-ai" or "& -ai")
        elif next_is_alnum and (not prev_is_alnum or prev_is_space or prev_char in '&'):
            # Don't add extra spaces, keep attached to next word
            result.append('-')
        # Case 3: other hyphens - ensure spaces around
        else:
            # Add space before if needed
            if prev_char and not prev_is_space:
                result.append(' ')
            result.append('-')
            # Add space after if needed (unless at end)
            if next_char and not next_is_space:
                result.append(' ')
                
        i += 1
    
    # Join and clean up multiple spaces
    text = ''.join(result)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


###############################################################################
# -----------------------------  Public helpers  ----------------------------- #
###############################################################################


def robust_normalize(text: str) -> str:
    """Aggressive unicode / LaTeX / punctuation scrub used by many tests."""
    if not text:
        return ""

    text = _latex_scrub(text)
    text = _remove_greek_unicode(text)
    text = _canonical_dash(text)
    text = _clean_basic(text)
    text = _normalise_spaces_around_hyphens(text)
    # Finally, strip leading / trailing punctuation artefacts (commas, colons)
    text = text.strip(" ,;:")
    return text


# --------------------------------------------------------------------------- #
#                           ---  AUTHORS  ---                                 #
# --------------------------------------------------------------------------- #

_INITIALS_RE = re.compile(r"(?:[a-z]\., flags=re.UNICODE)+", re.I)


def _initials_to_block(s: str) -> str:
    """Convert various forms of initials to a concatenated lowercase block."""
    # Remove dots, hyphens, and spaces
    s = re.sub(r'[.\-\s]', '', s)
    return s.lower()


def _is_pure_initials(s: str) -> bool:
    """
    Check if string is ONLY initials, with no surname part.
    E.g., "A.B.", "AB", "C.", "C", "A B" -> True
    But "A.B. Smith", "Smith", "Ng" -> False
    """
    s = s.strip()
    if not s:
        return False
    
    # Special case: Single capital letter with optional dot is definitely initials
    if len(s) <= 2 and s.replace('.', '').isalpha() and len(s.replace('.', '')) == 1:
        return True
    
    # Split into tokens and check each
    tokens = s.split()
    
    # All tokens must look like initials
    for token in tokens:
        if not _looks_like_initials(token):
            return False
    
    return True


def _looks_like_initials(s: str) -> bool:
    """
    Check if a string looks like initials.
    Examples:
    - "A.B.", "C.", "A." -> True (dots)
    - "AB", "ABC" -> True (uppercase, ≤3 chars)
    - "A", "B" -> True (single letter)
    - "A B", "A B C" -> True (spaced single letters)
    - "Smith", "Ng", "Zhao" -> False (regular names)
    """
    s = s.strip()
    if not s:
        return False
    
    # Pattern 1: Contains dots (e.g., "A.B.", "C.")
    if '.' in s:
        # Remove spaces, dots, and hyphens to get just letters
        cleaned = re.sub(r"[\s.\-]", "", s)
        # Should be just letters and reasonably short
        return cleaned.isalpha() and len(cleaned) <= 6
    
    # Pattern 2: All uppercase letters, no spaces, short (e.g., "AB", "ABC")
    if s.isupper() and s.isalpha() and len(s) <= 3:
        return True
    
    # Pattern 3: Single letter (e.g., "A", "B", "C")
    if len(s) == 1 and s.isalpha():
        return True
    
    # Pattern 4: Spaced single letters (e.g., "A B", "A B C")
    parts = s.split()
    if len(parts) > 1 and all(len(p) == 1 and p.isalpha() for p in parts):
        return True
    
    # Not initials
    return False


def _tokenise_authors(raw: str) -> List[str]:
    """
    Split a raw author field into candidate author substrings.
    
    Examples:
    - "Smith, A.B., Doe, C.D." -> ["Smith, A.B.", "Doe, C.D."]
    - "A.B. Smith, C.D. Doe" -> ["A.B. Smith", "C.D. Doe"]
    - "A.-B. Ng, Zhao, C." -> ["A.-B. Ng", "Zhao, C."]
    """
    # Replace " and " with a separator
    tmp = raw.replace(" and ", ";")
    
    # Split by semicolon first (definite author separator)
    parts = re.split(r"[;]", tmp)
    
    authors = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        if "," not in part:
            # No comma - it's a single author
            authors.append(part)
            continue
            
        # Has commas - split and process
        segments = [s.strip() for s in part.split(",") if s.strip()]
        
        # Process segments
        i = 0
        n = len(segments)
        
        while i < n:
            # Get current segment
            curr = segments[i]
            
            # Check if we can pair with next segment
            if i + 1 < n:
                next_seg = segments[i + 1]
                
                # Check if this is "Surname, Initials" pattern
                # Current must not be pure initials (has surname part)
                # Next must be pure initials
                if not _is_pure_initials(curr) and _is_pure_initials(next_seg):
                    # Pair them
                    authors.append(f"{curr}, {next_seg}")
                    i += 2  # Skip both
                    continue
            
            # No pairing - add current as standalone
            authors.append(curr)
            i += 1
    
    return authors


def _parse_single_author(raw: str) -> Tuple[str, str]:
    """
    Returns (surname, initials)

    Handles formats like:
        "Smith, A.B."  -> ("smith", "ab")
        "A.B. Smith"   -> ("smith", "ab") 
        "Smith AB"     -> ("smith", "ab")
        "Smith"        -> ("smith", "")
        "A.B.C."       -> ("", "abc")
        "A. Smith"     -> ("smith", "a")
    """
    raw = raw.strip()
    if not raw:
        return ("", "")

    if "," in raw:
        # Format: "Surname, Initials"
        parts = [p.strip() for p in raw.split(",", 1)]
        surname = parts[0]
        given = parts[1] if len(parts) > 1 else ""
    else:
        # No comma - need to identify what's surname vs initials
        tokens = raw.split()
        if not tokens:
            return ("", "")
        
        # Classify each token
        initial_tokens = []
        name_tokens = []
        for token in tokens:
            if _looks_like_initials(token):
                initial_tokens.append(token)
            else:
                name_tokens.append(token)
        
        # Determine surname and initials based on what we have
        if not name_tokens:
            # All initials (e.g., "A.B.C.")
            surname = ""
            given = " ".join(tokens)
        elif not initial_tokens:
            # No initials - need to identify surname
            # Check for surname prefixes like "van der"
            surname_start = len(tokens) - 1
            for i in range(len(tokens) - 2, -1, -1):
                if tokens[i].lower() in _SURNAME_PREFIXES:
                    surname_start = i
                else:
                    break
            surname = " ".join(tokens[surname_start:])
            given = " ".join(tokens[:surname_start])
        else:
            # Mix of initials and names - determine order
            # Find first occurrence of each type
            first_initial = next(i for i, t in enumerate(tokens) if _looks_like_initials(t))
            first_name = next(i for i, t in enumerate(tokens) if not _looks_like_initials(t))
            
            if first_initial < first_name:
                # Initials come first (e.g., "A.B. Smith")
                given = " ".join(t for t in tokens if _looks_like_initials(t))
                name_parts = [t for t in tokens if not _looks_like_initials(t)]
                # Check for surname prefixes
                surname_start = 0
                for i in range(len(name_parts) - 1):
                    if name_parts[i].lower() in _SURNAME_PREFIXES:
                        surname_start = i
                        break
                surname = " ".join(name_parts[surname_start:])
            else:
                # Name comes first (e.g., "Smith A.B.")
                given = " ".join(t for t in tokens if _looks_like_initials(t))
                name_parts = [t for t in tokens if not _looks_like_initials(t)]
                # Handle surname prefixes
                if len(name_parts) >= 2 and name_parts[0].lower() in _SURNAME_PREFIXES:
                    surname = " ".join(name_parts[:2])
                else:
                    surname = name_parts[0]
    
    # Normalize
    surname = surname.lower().strip()
    given = _initials_to_block(given)
    
    # Clean punctuation (but keep hyphens in surnames)
    surname = re.sub(r"[^\w\s\-]", "", surname).strip()
    given = re.sub(r"[^\w\s]", "", given).strip()
    
    return (surname, given)


def robust_normalize_authors(author_field: str) -> str:
    """
    Normalize an author field for comparison.
    
    Examples:
    - "Smith, A.B., Doe, C.D." -> "doe cd,smith ab"
    - "A.-B. Ng, Zhao, C." -> "ng ab,zhao c"
    """
    if not author_field:
        return ""

    # First apply accent stripping
    author_field = _strip_accents(author_field)
    
    # Tokenize - this should handle pairing "Surname, Initials"
    tokens = _tokenise_authors(author_field)
    
    # Parse each token into (surname, initials) pairs
    authors_data = []
    for token in tokens:
        surname, initials = _parse_single_author(token)
        # Only add if we have at least surname or initials
        if surname or initials:
            authors_data.append((surname, initials))
    
    # Remove exact duplicates
    unique_authors = []
    seen = set()
    for author in authors_data:
        if author not in seen:
            seen.add(author)
            unique_authors.append(author)
    
    # Sort by (surname, initials) tuple
    unique_authors.sort()
    
    # Format each author
    formatted_authors = []
    for surname, initials in unique_authors:
        if surname and initials:
            # Both surname and initials
            formatted_authors.append(f"{surname} {initials}")
        elif surname:
            # Just surname
            formatted_authors.append(surname)
        elif initials:
            # Just initials
            formatted_authors.append(initials)
        # Skip if both are empty (shouldn't happen)
    
    # Join with comma
    return ",".join(formatted_authors)


# --------------------------------------------------------------------------- #
#                             ---  TITLES  ---                                #
# --------------------------------------------------------------------------- #

# Patterns for series indicators
_PAREN_SERIES_RE = re.compile(r"\(\s*(?:"
    r"vol(?:ume, flags=re.UNICODE)?\.?\s*[ivxlcdm]+|"
    r"vol(?:ume)?\.?\s*\d+|"
    r"part\s+[ivxlcdm]+|"
    r"part\s+\d+|"
    r"section\s+[ivxlcdm]+|"
    r"section\s+\d+|"
    r"no\.?\s*\d+|"
    r"[ivxlcdm]+)"
    r"\s*\)",
    re.I
)

_TRAILING_SERIES_RE = re.compile(
    r"(?:[,\s]|^)\s*(?:"
    r"vol(?:ume)?\.?\s*[ivxlcdm]+|"
    r"vol(?:ume)?\.?\s*\d+|"
    r"part\s+[ivxlcdm]+|"
    r"part\s+\d+|"
    r"section\s+[ivxlcdm]+|"
    r"section\s+\d+|"
    r"no\.?\s*\d+|"
    r"[ivxlcdm]+)"
    r"\s*$",
    re.I
)

_LEADING_SERIES_RE = re.compile(r"^(?:"
    r"vol(?:ume, flags=re.UNICODE)?\.?\s*[ivxlcdm]+\s*[:\-\s]|"
    r"vol(?:ume)?\.?\s*\d+\s*[:\-\s]|"
    r"part\s+[ivxlcdm]+\s*[:\-\s]|"
    r"part\s+\d+\s*[:\-\s]|"
    r"section\s+[ivxlcdm]+\s*[:\-\s]|"
    r"section\s+\d+\s*[:\-\s]|"
    r"no\.?\s*\d+\s*[:\-\s]|"
    r"[ivxlcdm]+\s+)",
    re.I
)


def _series_scrub(text: str) -> str:
    """Remove parenthetical / trailing / leading 'Vol 2', 'II', 'Part III' etc."""
    # Remove parenthetical series
    text = _PAREN_SERIES_RE.sub("", text)
    
    # Keep removing trailing series until no more changes
    prev_text = None
    while prev_text != text:
        prev_text = text
        text = _TRAILING_SERIES_RE.sub("", text)
    
    # Remove leading series
    text = _LEADING_SERIES_RE.sub("", text)
    
    # Clean up remaining patterns with dashes
    text = re.sub(r"[\-–—]\s*part\s+[ivxlcdm]+\b", "", text, flags=re.I)
    text = re.sub(r"[\-–—]\s*part\s+\d+\b", "", text, flags=re.I)
    text = re.sub(r",\s*part\s+[ivxlcdm]+\b", "", text, flags=re.I)
    text = re.sub(r",\s*part\s+\d+\b", "", text, flags=re.I)
    
    # Remove standalone roman numerals at the end
    text = re.sub(r",\s*[ivxlcdm]+\s*$", "", text, flags=re.I)
    
    # Remove section patterns with dashes
    text = re.sub(r"section\s+[ivxlcdm]+\s*[\-–—]", "", text, flags=re.I)
    text = re.sub(r"section\s+\d+\s*[\-–—]", "", text, flags=re.I)
    
    return text.strip()


def _drop_number_prefix(text: str) -> str:
    # ex. 'No. 5  Theory'   ->  'Theory'
    return re.sub(r"^\s*no\.?\s*\d+\s*", "", text, flags=re.I)


def robust_normalize_title(title: str) -> str:
    if not title:
        return ""

    title = _latex_scrub(title)
    title = _canonical_dash(title)
    title = _series_scrub(title)
    title = _drop_number_prefix(title)
    title = _clean_basic(title)

    # Remove stop-words at beginning
    words = title.split()
    while words and words[0] in _STOPWORDS_IN_TITLE:
        words.pop(0)
    title = " ".join(words)

    # Remove punctuation
    title = re.sub(r"[:;,]", "", title)
    title = _normalise_spaces_around_hyphens(title)
    
    # Clean up any trailing dashes
    title = re.sub(r'\s*-\s*$', '', title)
    
    # Check if what's left is just a series indicator
    title_lower = title.lower().strip()
    if re.match(r'^(volume|vol)\s*\d+$', title_lower):
        return ""
    if re.match(r'^(part|section)\s*[ivxlcdm]+$', title_lower):
        return ""
    if re.match(r'^(part|section)\s*\d+$', title_lower):
        return ""
    if title_lower in {"part", "section", "volume", "vol", "just"}:
        return ""
    
    return title


# --------------------------------------------------------------------------- #
#                       ---  ARXIV & filename helpers  ---                    #
# --------------------------------------------------------------------------- #

_ARXIV_RE = re.compile(r"arxiv[_\- ]?(\d{4}\.\d{5}, flags=re.UNICODE)(?:v\d+)?", re.I)


def read_arxiv_id(text: str) -> str | None:
    """
    Returns the *numerical* arXiv id (e.g. ``2101.00001``) or ``None``.
    """
    m = _ARXIV_RE.search(text)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
#                          ---  METADATA / PATH  ---                          #
# --------------------------------------------------------------------------- #


def _ensure_path_dict(entry) -> dict:
    """
    Accept ``str``, ``Path`` or ``dict`` and always return
    {'path': <absolute str>, 'name': <basename str>}
    """
    if isinstance(entry, dict):
        if "path" in entry and "name" in entry:
            return entry
        # Try to handle dictionaries with different key names for compatibility
        if "path" in entry and "filename" in entry:
            return {"path": entry["path"], "name": entry["filename"]}
        if "path" in entry:
            # Extract name from path
            p = Path(entry["path"])
            return {"path": entry["path"], "name": p.name}
        raise TypeError("Dict entries must contain 'path' and 'name' keys")

    p = Path(entry)
    return {"path": str(p), "name": p.name}


def extract_metadata(input_: str | os.PathLike | dict) -> dict | None:
    """
    Returns a dict with at least:
        {
            'path': full path (str),
            'name': basename without extension,
            'authors_raw': raw part before dash (if any),
            'title_raw'  : raw part after dash  (if any)
        }
    Missing dash → returns None and logs warning.
    """
    itm = _ensure_path_dict(input_)
    name_no_ext = os.path.splitext(itm["name"])[0]

    if " - " not in name_no_ext:
        logger.warning(f"Filename missing ' - ' separator: {itm['name']}")
        return None

    authors_raw, title_raw = name_no_ext.split(" - ", 1)

    return {
        "path": itm["path"],
        "name": itm["name"],
        "authors_raw": authors_raw.strip(),
        "title_raw": title_raw.strip(),
    }


# --------------------------------------------------------------------------- #
#                              ---  DUPLICATES  ---                           #
# --------------------------------------------------------------------------- #


def _canonical_key(meta: dict) -> Tuple[str, str]:
    authors_canon = robust_normalize_authors(meta["authors_raw"])
    title_canon = robust_normalize_title(meta["title_raw"])
    return authors_canon, title_canon


def _is_series_file(meta: dict) -> bool:
    """
    A file is *series* if its canonical title becomes empty ― e.g.
    'Paper, II'  or  'Volume 8'.
    """
    return robust_normalize_title(meta["title_raw"]) == ""


def find_duplicates(files: Sequence[str | os.PathLike | dict]) -> List[List[Dict]]:
    """
    Group paths whose canonical *key* (authors,title) matches,
    subject to the arXiv-ID sanity rule and series-file exclusion.
    """
    buckets: dict[Tuple[str, str], list[dict]] = defaultdict(list)

    # Aggregate by canonical key
    for entry in files:
        meta = extract_metadata(entry)
        
        # Skip if metadata extraction failed
        if meta is None:
            continue

        # Ignore series files
        if _is_series_file(meta):
            continue

        # Get canonical key for grouping
        # For matching purposes, normalize hyphens in author names
        authors_for_matching = robust_normalize_authors(meta["authors_raw"])
        # Replace hyphens with spaces for matching
        authors_for_matching = authors_for_matching.replace('-', ' ')
        
        title_canon = robust_normalize_title(meta["title_raw"])
        key = (authors_for_matching, title_canon)
        
        buckets[key].append(meta)

    # Post-filter for arXiv conflicts
    groups: List[List[dict]] = []
    for metas in buckets.values():
        arxiv_ids = {read_arxiv_id(m["name"]) for m in metas if read_arxiv_id(m["name"])}
        if len(arxiv_ids) > 1:
            # Conflicting arXiv IDs invalidate the bucket
            continue

        # Drop duplicate paths inside a bucket
        unique_by_path = {}
        for m in metas:
            unique_by_path[m["path"]] = m
        if len(unique_by_path) > 1:  # Only keep groups ≥2
            groups.append(list(unique_by_path.values()))

    return groups