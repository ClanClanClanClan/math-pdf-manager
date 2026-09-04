"""Library search + export helpers (cockpit "Search" page).

Pure, UI-free functions so the search/export logic is unit-testable;
``ui.cockpit.render_search`` provides the thin Streamlit layer.

Search is over the canonical FILENAMES — which, in this library, encode
authors and title in a strict convention — using an in-memory index
built from one library walk (cached by the caller).  Matching is
case- and accent-insensitive; multiple space-separated terms must ALL
match (AND semantics), each anywhere in the name.

Export produces CSV and BibTeX from the filtered rows.  BibTeX entry
types map from the library's folder convention (01/02/03 → article-ish,
05 → book, 06 → phdthesis); DOIs are pulled from sidecars for the
result set only (bounded), never a whole-library sidecar sweep.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_EXPORT_SIDECAR_READS = 500


def _fold(s: str) -> str:
    """Casefold, strip accents, and fold apostrophe-like marks.

    The apostrophe fold matters because NO Unicode normalisation form
    equates U+0027 and U+2019 -- unlike accents, where NFD/NFC does the
    work. Without it, searching "d'Amato" with the keyboard apostrophe
    finds one of that author's two files and misses the other.
    """
    from processing.apostrophes import fold_marks
    nfkd = unicodedata.normalize("NFD", fold_marks(s))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).casefold()


def build_index(library_root: Path) -> list:
    """One library walk → ``[(name, relpath, folded_key), ...]``."""
    from processing.identity import iter_pdfs
    rows = []
    for pdf in iter_pdfs(library_root):
        try:
            rel = str(pdf.relative_to(library_root))
        except ValueError:
            rel = str(pdf)
        name = unicodedata.normalize("NFC", pdf.name)
        rows.append((name, rel, _fold(name)))
    return rows


def search_index(index: list, query: str, *, limit: int = 200) -> list:
    """AND-match all space-separated terms; returns ``[(name, relpath)]``."""
    terms = [_fold(t) for t in query.split() if t.strip()]
    if not terms:
        return []
    out = []
    for name, rel, key in index:
        if all(t in key for t in terms):
            out.append((name, rel))
            if len(out) >= limit:
                break
    return out


# ---------------------------------------------------------------------------
# Row model for export
# ---------------------------------------------------------------------------

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def row_details(name: str, rel: str, library_root: Optional[Path] = None) -> dict:
    """Parse one result into export fields (authors/title/status/year/doi)."""
    stem = name[:-4] if name.lower().endswith(".pdf") else name
    authors, title = "", stem
    if " - " in stem:
        authors, title = stem.split(" - ", 1)

    top = rel.split("/", 1)[0] if "/" in rel else ""
    status = top
    # Papers inside topic folders keep their status sub-bucket.
    if top.startswith("07") and "/" in rel:
        for part in rel.split("/"):
            if part[:2] in ("01", "02", "03", "05", "06") and " - " in part:
                status = part
                break

    year = ""
    m = _YEAR_RE.search(rel) or _YEAR_RE.search(stem)
    if m:
        year = m.group(0)

    doi = ""
    if library_root is not None:
        try:
            from processing.identity import PaperIdentity
            ident = PaperIdentity.load(library_root / rel)
            if not ident.is_new():
                doi = ident.doi or ""
        except Exception:
            pass

    return {"authors": authors, "title": title, "status": status,
            "year": year, "doi": doi, "path": rel}


def to_csv(rows: list) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["authors", "title", "status",
                                        "year", "doi", "path"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# BibTeX
# ---------------------------------------------------------------------------

_BIB_SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_"}


def _bib_escape(s: str) -> str:
    for k, v in _BIB_SPECIALS.items():
        s = s.replace(k, v)
    return s


def _bib_key(r: dict, seen: set) -> str:
    fam = "unknown"
    if r["authors"]:
        fam = r["authors"].split(",", 1)[0]
    fam = re.sub(r"[^A-Za-z]", "", _fold(fam)) or "unknown"
    base = f"{fam}{r['year']}" if r["year"] else fam
    key, n = base, 1
    while key in seen:
        n += 1
        key = f"{base}{chr(ord('a') + n - 2)}"
    seen.add(key)
    return key


def _bib_type(status: str) -> str:
    if status.startswith("05"):
        return "book"
    if status.startswith("06"):
        return "phdthesis"
    if status.startswith(("02", "03")):
        return "unpublished"
    return "article"


def _bib_authors(authors: str) -> str:
    """"Dalang, R. C., Possamai, D." → "Dalang, R. C. and Possamai, D."."""
    if not authors:
        return ""
    parts = re.split(r"(?<=\.),\s(?=[^\s])", authors)
    return " and ".join(p.strip().rstrip(",") for p in parts if p.strip())


def to_bibtex(rows: list) -> str:
    seen: set = set()
    entries = []
    for r in rows:
        key = _bib_key(r, seen)
        fields = [f"  title = {{{_bib_escape(r['title'])}}}"]
        if r["authors"]:
            fields.append(f"  author = {{{_bib_escape(_bib_authors(r['authors']))}}}")
        if r["year"]:
            fields.append(f"  year = {{{r['year']}}}")
        if r["doi"]:
            fields.append(f"  doi = {{{r['doi']}}}")
        fields.append(f"  note = {{{_bib_escape(r['path'])}}}")
        body = ",\n".join(fields)
        entries.append(f"@{_bib_type(r['status'])}{{{key},\n{body}\n}}")
    return "\n\n".join(entries) + ("\n" if entries else "")
