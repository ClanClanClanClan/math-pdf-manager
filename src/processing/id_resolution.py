#!/usr/bin/env python3
"""Resolve identifier-named PDFs to real title/authors via public APIs.

Many PDFs arrive named after an IDENTIFIER rather than a real title —
``2103.04185.pdf`` (arXiv), ``10.1214_aop-2022-1234.pdf`` (a DOI with
``/`` escaped to ``_`` or ``-``), ``SSRN-id1234567.pdf`` (SSRN), or
``hal-01234567.pdf`` (HAL).  The live extractor (``ingest.py``) already
detects arXiv IDs / DOIs in the PAGE TEXT and queries the arXiv and
Crossref APIs — but it never looks at the FILENAME, so an
identifier-named scan whose text lacks the ID is left unresolved.

This module fills that gap:

* ``detect_filename_ids()`` — pull arXiv / DOI / SSRN / HAL ids out of a
  filename.
* SSRN: there is no open SSRN metadata API, but SSRN papers carry the
  DOI ``10.2139/ssrn.<id>``, which Crossref resolves — so we map an SSRN
  id to that DOI and let the existing Crossref lookup do the work.
* HAL: a real public API (api.archives-ouvertes.fr) returns title +
  authors; ``resolve_hal()`` queries it.

All network calls are best-effort, time-bounded, and never raise.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# --- Filename identifier patterns -----------------------------------------
# arXiv new (2401.04185, optional version) and old (math.PR/0501001 or
# math/0501001) schemes, anchored so we don't match arbitrary digit runs.
_ARXIV_NEW = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(v\d+)?(?!\d)")
# Old scheme "archive[.SUB]/NNNNNNN"; on disk the "/" is escaped to "_".
# The archive token excludes ssrn/hal/tel so those never false-match.
_ARXIV_OLD = re.compile(
    r"\b(?!ssrn|hal|tel)([a-z][a-z-]+(?:\.[A-Z]{2})?)[_/](\d{7})(v\d+)?\b"
)
# A DOI inside a filename: the canonical "10.xxxx/suffix", OR a filesystem
# -safe form where the single "/" after the registrant is escaped to "_"
# or "-" (a common way to store a DOI as a filename).
_DOI_PLAIN = re.compile(r"\b(10\.\d{4,9}/[^\s]+?)(?:\.pdf)?$", re.IGNORECASE)
_DOI_ESCAPED = re.compile(r"\b(10\.\d{4,9})[_-]([A-Za-z0-9._()-]+?)(?:\.pdf)?$")
_SSRN = re.compile(r"\bssrn[-_ ]?(?:id)?[-_ ]?(\d{4,})\b", re.IGNORECASE)
_HAL = re.compile(r"\b(hal[-_]\d{6,})\b", re.IGNORECASE)
_TEL = re.compile(r"\b(tel[-_]\d{6,})\b", re.IGNORECASE)  # HAL theses server


def detect_filename_ids(filename: str) -> dict:
    """Return any identifiers found in ``filename`` (stem only matters).

    Keys present only when found: ``arxiv_id``, ``doi``, ``ssrn_id``,
    ``hal_id``.  Detection is conservative; ambiguous names yield {}.
    """
    stem = Path(filename).name
    out: dict = {}

    # A file already in canonical "Author - Title" form is NOT an
    # identifier-named scan — skip detection so a title that merely
    # *contains* a digit pattern (e.g. "... 2024.12345 ...") can't be
    # mistaken for an arXiv id.  Identifier dumps ("2401.07160v3.pdf")
    # never carry the " - " author/title separator.
    if " - " in stem:
        return out

    # HAL / TEL (theses) first — distinctive prefix.
    m = _HAL.search(stem) or _TEL.search(stem)
    if m:
        out["hal_id"] = m.group(1).lower().replace("_", "-")

    # SSRN.
    m = _SSRN.search(stem)
    if m:
        out["ssrn_id"] = m.group(1)

    # arXiv (new then old) — skip if we already matched a HAL/SSRN id
    # (the filename is a single identifier; those tokens can otherwise
    # collide with the loose old-arXiv archive pattern).
    if "hal_id" not in out and "ssrn_id" not in out:
        m = _ARXIV_NEW.search(stem)
        if m:
            out["arxiv_id"] = m.group(1) + (m.group(2) or "")
        else:
            m = _ARXIV_OLD.search(stem)
            if m:
                out["arxiv_id"] = f"{m.group(1)}/{m.group(2)}" + (m.group(3) or "")

    # DOI — only if the stem really looks like a bare DOI (starts at/near
    # the front), to avoid grabbing "10.1007" out of a normal title.
    if "10." in stem:
        mp = _DOI_PLAIN.search(stem)
        if mp and stem.lower().lstrip().startswith(mp.group(1).lower()[:7]):
            out["doi"] = mp.group(1).rstrip(".")
        else:
            me = _DOI_ESCAPED.search(stem)
            if me and stem.lstrip().startswith(me.group(1)):
                # Reconstruct the canonical "/" form.
                out["doi"] = f"{me.group(1)}/{me.group(2)}".rstrip(".")

    return out


def ssrn_doi(ssrn_id: str) -> str:
    """The Crossref-resolvable DOI for an SSRN abstract id."""
    return f"10.2139/ssrn.{ssrn_id}"


def resolve_hal(hal_id: str, *, timeout: float = 10.0) -> Optional[dict]:
    """Look up a HAL id via the HAL public API. Returns
    ``{"title": str, "authors": [str, ...]}`` or ``None``. Never raises."""
    try:
        import requests
        resp = requests.get(
            "https://api.archives-ouvertes.fr/search/",
            params={"q": f"halId_s:{hal_id}", "fl": "title_s,authFullName_s",
                    "wt": "json", "rows": 1},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        docs = resp.json().get("response", {}).get("docs", [])
        if not docs:
            return None
        d = docs[0]
        title = d.get("title_s")
        if isinstance(title, list):
            title = title[0] if title else None
        authors = d.get("authFullName_s") or []
        if isinstance(authors, str):
            authors = [authors]
        if not title:
            return None
        import unicodedata
        return {
            "title": unicodedata.normalize("NFC", re.sub(r"\s+", " ", title).strip()),
            "authors": [a.strip() for a in authors if a and a.strip()],
        }
    except Exception as exc:  # network/parse — best effort
        logger.warning("HAL lookup failed for %s: %s", hal_id, exc)
        return None


def augment_metadata_with_filename_ids(filename: str, metadata: dict) -> dict:
    """Fill missing id fields in ``metadata`` from the filename.

    Mutates and returns ``metadata``.  Only fills gaps — never overrides
    an id already found in the page text.  Maps SSRN -> its Crossref DOI
    so the existing Crossref lookup resolves it.  Sets ``hal_id`` for the
    caller to resolve via :func:`resolve_hal`.
    """
    ids = detect_filename_ids(filename)
    if ids.get("arxiv_id") and not metadata.get("arxiv_id"):
        metadata["arxiv_id"] = ids["arxiv_id"]
    if ids.get("doi") and not metadata.get("doi"):
        metadata["doi"] = ids["doi"]
    if ids.get("ssrn_id") and not metadata.get("doi"):
        metadata["doi"] = ssrn_doi(ids["ssrn_id"])
    if ids.get("hal_id") and not metadata.get("hal_id"):
        metadata["hal_id"] = ids["hal_id"]
    return metadata
