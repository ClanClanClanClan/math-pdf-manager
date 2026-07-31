"""Preprint ↔ published variant detection (same paper, different bytes).

The owner's case (flagged during the duplicate review): a paper filed
once under its PREPRINT title ("…irregular expectation functionals in
the drift") and again under its PUBLISHED title ("…irregular drift").
Content-hash dedup is blind to this — the PDFs differ byte-wise — so
identity must come from what survives the preprint→published transition:

  Tier 1  DOI match         (definitive)
  Tier 2  arXiv-id match    (definitive)
  Tier 3  author overlap + title/abstract similarity   (review)

Identifier coverage is bootstrapped by ``backfill_identifiers``, which
mines DOIs / arXiv ids from the sidecars' ALREADY-CACHED first-pages
text (``classifier_text`` — the arXiv margin stamp and publisher DOI
line live there) and from arXiv-style filenames.  No PDF is opened.

Resolution follows the library policy — the preprint is RETIRED
(reversibly, to ``.trash/upgraded_preprints/``) unless it is an extended
version, which is the owner's call: pairs are always review-gated, with
page/size comparison shown so extended preprints stand out.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# arXiv ids: new style 2201.03562(v1), old style math.PR/0605274.
_ARXIV_NEW_RE = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")
_ARXIV_CTX_RE = re.compile(
    r"arxiv[:\s/]*(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
_ARXIV_OLD_RE = re.compile(
    r"arxiv[:\s/]*([a-z-]+(?:\.[A-Z]{2})?/\d{7})", re.IGNORECASE)
# DOI: strip common trailing punctuation the text layer glues on.
_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>]+)")

# ISBN-based BOOK DOIs (10.xxxx/978… or /979…) are printed on every chapter
# of an edited volume, so they are shared by many DISTINCT papers and are
# never a per-article variant key.  The real-library probe surfaced exactly
# this: one World Scientific volume (10.1142/9789811259142) mined into ~15
# unrelated chapters and cross-paired them all.
_ISBN_DOI_RE = re.compile(r"^10\.\d{4,9}/(?:97[89])[\d-]")

PREPRINT_TOPS = ("02", "03", "04")
PUBLISHED_TOP = "01"

# A DOI/arXiv id shared by more than this many files is treated as a
# collection identifier (proceedings/book), not a variant signal.
_MAX_IDENT_BUCKET = 3


def is_collection_doi(doi: str) -> bool:
    """True for ISBN-based book DOIs — shared across all chapters."""
    return bool(_ISBN_DOI_RE.match((doi or "").strip().lower()))


def extract_identifiers(text: str) -> dict:
    """Mine ``{"doi": ..., "arxiv_id": ...}`` from first-pages text."""
    out = {"doi": "", "arxiv_id": ""}
    if not text:
        return out
    m = _ARXIV_CTX_RE.search(text) or _ARXIV_OLD_RE.search(text)
    if m:
        out["arxiv_id"] = m.group(1)
    d = _DOI_RE.search(text)
    if d:
        doi = d.group(1).rstrip(".,;:)]}»")
        # Publisher boilerplate sometimes glues the next word on; a DOI
        # suffix never contains whitespace so the regex handles that, but
        # trailing "/pdf" or "/full" fragments from URLs are common.
        doi = re.sub(r"/(pdf|full|abstract|html)$", "", doi, flags=re.I)
        out["doi"] = doi.lower()
    return out


def arxiv_id_from_filename(name: str) -> str:
    """``2301.03756v1.pdf`` → ``2301.03756`` (staging leftovers)."""
    stem = name[:-4] if name.lower().endswith(".pdf") else name
    m = re.fullmatch(r"(\d{4}\.\d{4,5})(?:v\d+)?", stem.strip())
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Identifier backfill (metadata-only enrichment; no PDF I/O)
# ---------------------------------------------------------------------------

def backfill_identifiers(library_root: Path, *, limit: Optional[int] = None) -> dict:
    """Fill empty sidecar ``doi``/``arxiv_id`` from cached text + filename.

    Returns ``{"scanned", "doi_added", "arxiv_added"}``.  Best-effort:
    per-sidecar failures are counted, never raised.
    """
    from processing.identity import PaperIdentity, iter_pdfs

    scanned = doi_added = arxiv_added = 0
    for pdf in iter_pdfs(library_root):
        if limit is not None and scanned >= limit:
            break
        try:
            ident = PaperIdentity.load(pdf)
        except Exception:
            continue
        if ident.is_new():
            continue
        scanned += 1
        if ident.doi and ident.arxiv_id:
            continue
        found = extract_identifiers(ident.classifier_text or "")
        if not found["arxiv_id"]:
            found["arxiv_id"] = arxiv_id_from_filename(pdf.name)
        changed = False
        # Never store a BOOK DOI as the paper's own DOI: it's the volume's,
        # shared by every chapter, and would both mispopulate the field and
        # break the ingest twin-lookup for the next chapter of that book.
        if not ident.doi and found["doi"] and not is_collection_doi(found["doi"]):
            ident.doi = found["doi"]
            doi_added += 1
            changed = True
        if not ident.arxiv_id and found["arxiv_id"]:
            ident.arxiv_id = found["arxiv_id"]
            arxiv_added += 1
            changed = True
        if changed:
            try:
                ident.save(pdf, recompute_hash=False)
            except Exception:  # pragma: no cover
                logger.warning("could not save enriched sidecar for %s", pdf)
    return {"scanned": scanned, "doi_added": doi_added,
            "arxiv_added": arxiv_added}


def clear_collection_dois(library_root: Path, *, dry_run: bool = True) -> dict:
    """Clear book/collection DOIs wrongly stored as a paper's own DOI.

    A book DOI is printed on every chapter, so an earlier identifier
    backfill could store the volume's DOI on each chapter's sidecar.
    Those are corrected here (metadata-only; no PDF touched) — EXCEPT on
    an actual book/thesis (``05``/``06`` bucket), where the ISBN DOI is
    the item's own correct DOI and must be kept.  Returns
    ``{"found": [...paths...], "cleared": N}``; ``dry_run`` reports
    without writing.
    """
    from processing.identity import PaperIdentity, iter_pdfs

    def _is_book_or_thesis(rel: str) -> bool:
        parts = rel.split("/")
        tops = [parts[0]] + [p for p in parts[1:] if " - " in p]
        return any(t.startswith(("05", "06")) for t in tops)

    found: list = []
    cleared = 0
    for pdf in iter_pdfs(library_root):
        try:
            ident = PaperIdentity.load(pdf)
        except Exception:
            continue
        if ident.is_new() or not is_collection_doi(ident.doi or ""):
            continue
        try:
            rel = str(pdf.relative_to(library_root))
        except ValueError:
            rel = str(pdf)
        if _is_book_or_thesis(rel):
            continue                       # legit ISBN DOI on a real book
        found.append(rel)
        if not dry_run:
            ident.doi = ""
            try:
                ident.save(pdf, recompute_hash=False)
                cleared += 1
            except Exception:  # pragma: no cover
                logger.warning("could not clear book DOI on %s", pdf)
    return {"found": found, "cleared": cleared}


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

@dataclass
class VariantPair:
    preprint: str                      # path of the preprint-side copy
    published: str                     # path of the published-side copy
    tier: str                          # doi | arxiv | fuzzy
    evidence: dict = field(default_factory=dict)

    def key(self) -> str:
        return "||".join(sorted((self.preprint, self.published)))

    def to_dict(self) -> dict:
        return asdict(self)


def _fold(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).casefold()


def _status_class(rel: str) -> str:
    """preprint | published | other, honoring topic-folder sub-buckets."""
    parts = rel.split("/")
    tops = [parts[0]] if parts else []
    if parts and parts[0].startswith("07"):
        tops += [p for p in parts[1:] if " - " in p]
    for t in tops:
        if t.startswith(PUBLISHED_TOP):
            return "published"
        if t.startswith(PREPRINT_TOPS):
            return "preprint"
    return "other"


def _surnames(authors_part: str) -> set:
    """Folded family names from a canonical author block."""
    out = set()
    for chunk in re.split(r",\s*(?=[^\s])", authors_part):
        token = chunk.split(",")[0].strip()
        # Drop initials-only chunks ("R. C.")
        if token and not re.fullmatch(r"(?:[A-Z]\.[\s-]*)+", token):
            for word in token.replace("-", " ").split():
                if len(word) >= 3:
                    out.add(_fold(word))
    return out


def _collect_records(library_root: Path) -> list:
    from processing.identity import PaperIdentity, iter_pdfs
    records = []
    for pdf in iter_pdfs(library_root):
        try:
            rel = str(pdf.relative_to(library_root))
        except ValueError:
            continue
        stem = unicodedata.normalize("NFC", pdf.stem)
        authors, title = "", stem
        if " - " in stem:
            authors, title = stem.split(" - ", 1)
        rec = {
            "rel": rel, "cls": _status_class(rel),
            "surnames": _surnames(authors), "title": title,
            "doi": "", "arxiv": "", "abstract": "",
        }
        try:
            ident = PaperIdentity.load(pdf)
            if not ident.is_new():
                rec["doi"] = (ident.doi or "").strip().lower()
                rec["arxiv"] = re.sub(r"v\d+$", "",
                                      (ident.arxiv_id or "").strip().lower())
                rec["abstract"] = (ident.classifier_text or "")[:4000]
        except Exception:
            pass
        if not rec["arxiv"]:
            rec["arxiv"] = arxiv_id_from_filename(pdf.name)
        records.append(rec)
    return records


def _abstract_tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", _fold(text))[:400]}


def _title_ratio(a: str, b: str) -> float:
    try:
        from rapidfuzz import fuzz
        return float(fuzz.token_set_ratio(_fold(a), _fold(b)))
    except Exception:
        import difflib
        return difflib.SequenceMatcher(None, _fold(a), _fold(b)).ratio() * 100


FUZZY_TITLE_MIN = 62.0        # below this, don't even consider
FUZZY_TITLE_STRONG = 87.0     # strong on its own
FUZZY_ABSTRACT_MIN = 0.6      # Jaccard on cached first-pages tokens


def find_variant_pairs(library_root: Path) -> list:
    """Return ``VariantPair`` list, strongest evidence first."""
    records = _collect_records(library_root)
    pairs: dict = {}

    def add(pre, pub, tier, evidence):
        p = VariantPair(preprint=pre["rel"], published=pub["rel"],
                        tier=tier, evidence=evidence)
        k = p.key()
        rank = {"doi": 0, "arxiv": 1, "fuzzy": 2}
        if k not in pairs or rank[tier] < rank[pairs[k].tier]:
            pairs[k] = p

    def orient(a, b):
        """(preprint-side, published-side) or None when undecidable."""
        if a["cls"] == "preprint" and b["cls"] == "published":
            return a, b
        if b["cls"] == "preprint" and a["cls"] == "published":
            return b, a
        return None

    # Tier 1/2: identifier buckets.  Two guards, learned from the real
    # library, keep a SHARED identifier from cross-pairing unrelated papers:
    #   * skip book/collection DOIs and over-shared buckets (>3 files); and
    #   * require AUTHOR-SURNAME OVERLAP for every emitted pair — a paper and
    #     its preprint/published variant share authors, while distinct
    #     chapters of one book do not (this alone eliminated the entire
    #     book-DOI false-positive class in the probe).
    for field_, tier in (("doi", "doi"), ("arxiv", "arxiv")):
        buckets: dict = {}
        for r in records:
            val = r[field_]
            if not val:
                continue
            if field_ == "doi" and is_collection_doi(val):
                continue
            buckets.setdefault(val, []).append(r)
        for ident_val, members in buckets.items():
            if not (2 <= len(members) <= _MAX_IDENT_BUCKET):
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    if not a["surnames"] & b["surnames"]:
                        # No shared author.  A DOI shared by different,
                        # known authors is a collection coincidence — reject.
                        # An arXiv id is unique per paper, so accept it only
                        # when one side has NO author info (a bare
                        # "2301.03756v1.pdf" staging leftover); reject when
                        # both authors are known but differ.
                        if field_ == "doi":
                            continue
                        if a["surnames"] and b["surnames"]:
                            continue
                    o = orient(a, b) or (a, b)
                    add(o[0], o[1], tier, {field_: ident_val})

    # Tier 3: fuzzy — block by shared surname to control O(n²), and only
    # across preprint/published classes.
    blocks: dict = {}
    for r in records:
        if r["cls"] in ("preprint", "published"):
            for s in r["surnames"]:
                blocks.setdefault(s, []).append(r)
    seen_cmp: set = set()
    for members in blocks.values():
        if len(members) < 2 or len(members) > 400:
            continue
        pres = [r for r in members if r["cls"] == "preprint"]
        pubs = [r for r in members if r["cls"] == "published"]
        for a in pres:
            for b in pubs:
                ck = (a["rel"], b["rel"])
                if ck in seen_cmp:
                    continue
                seen_cmp.add(ck)
                # Author sets must overlap substantially (authors can be
                # ADDED between versions, so subset counts fully).
                inter = a["surnames"] & b["surnames"]
                if not inter:
                    continue
                min_side = min(len(a["surnames"]), len(b["surnames"])) or 1
                if len(inter) / min_side < 0.99 and len(inter) < 2:
                    continue
                tr = _title_ratio(a["title"], b["title"])
                if tr < FUZZY_TITLE_MIN:
                    continue
                if tr >= FUZZY_TITLE_STRONG:
                    add(a, b, "fuzzy", {"title_ratio": round(tr, 1)})
                    continue
                ta, tb = _abstract_tokens(a["abstract"]), _abstract_tokens(b["abstract"])
                if ta and tb:
                    jac = len(ta & tb) / len(ta | tb)
                    if jac >= FUZZY_ABSTRACT_MIN:
                        add(a, b, "fuzzy",
                            {"title_ratio": round(tr, 1),
                             "abstract_jaccard": round(jac, 2)})

    out = list(pairs.values())
    out.sort(key=lambda p: ({"doi": 0, "arxiv": 1, "fuzzy": 2}[p.tier],
                            p.published))
    return out


def find_identifier_twin(
    library_root: Path,
    *,
    doi: str = "",
    arxiv_id: str = "",
    exclude: Optional[Path] = None,
) -> Optional[str]:
    """Return an existing library path sharing ``doi``/``arxiv_id``.

    The ingest-time variant check: a new arrival whose DOI or arXiv id
    already lives in a DIFFERENT file is almost certainly the other side
    of a preprint↔published pair.  Walks the sidecar mirror (JSON reads
    only — no PDF I/O); best-effort, returns None on any error.
    """
    doi = (doi or "").strip().lower()
    if is_collection_doi(doi):
        doi = ""                       # book DOI — not a per-article key
    arxiv = re.sub(r"v\d+$", "", (arxiv_id or "").strip().lower())
    if not doi and not arxiv:
        return None
    try:
        from processing.identity import PaperIdentity, iter_pdfs
        for pdf in iter_pdfs(library_root):
            if exclude is not None and pdf == exclude:
                continue
            try:
                ident = PaperIdentity.load(pdf)
            except Exception:
                continue
            if ident.is_new():
                continue
            if doi and (ident.doi or "").strip().lower() == doi:
                return str(pdf)
            if arxiv and re.sub(
                    r"v\d+$", "", (ident.arxiv_id or "").strip().lower()) == arxiv:
                return str(pdf)
    except Exception:  # pragma: no cover — never block an ingest
        logger.warning("identifier twin lookup failed", exc_info=True)
    return None


# ---------------------------------------------------------------------------
# Dismissals ("keep both" decisions persist)
# ---------------------------------------------------------------------------

def _dismissals_path(library_root: Path) -> Path:
    return library_root / ".mathpdf-config" / "variant_dismissals.json"


def load_dismissals(library_root: Path) -> set:
    try:
        return set(json.loads(_dismissals_path(library_root).read_text()))
    except (OSError, json.JSONDecodeError, ValueError):
        return set()


def dismiss_pair(library_root: Path, pair: VariantPair) -> None:
    from core.io import atomic_write_text
    d = load_dismissals(library_root)
    d.add(pair.key())
    p = _dismissals_path(library_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(p, json.dumps(sorted(d)))


# ---------------------------------------------------------------------------
# Resolution (review-gated, reversible)
# ---------------------------------------------------------------------------

def retire_variant(
    pair: VariantPair,
    library_root: Path,
    *,
    drop: str,
    undo_log=None,
) -> tuple:
    """Retire the ``drop`` side of the pair (the copy the owner did NOT keep).

    ``drop`` must be one of the pair's two paths.  The KEPT side inherits
    the dropped sidecar's knowledge FIRST (topic codes, publication
    history, identifiers — the merge must precede the move; once moved,
    the dropped sidecar lives in the trash mirror).  The move goes through
    ``logged_move`` so one undo restores file + sidecar.  A dropped
    preprint-class copy lands in ``.trash/upgraded_preprints/``; any other
    dropped copy in ``.trash/duplicates/``.  Returns ``(ok, message)``.
    """
    from processing.duplicate_scan import _merge_into_keeper
    from processing.undo_log import logged_move

    if drop not in (pair.preprint, pair.published):
        return False, "drop must be one of the pair's paths"
    keep_rel = pair.published if drop == pair.preprint else pair.preprint
    dropped = library_root / drop
    kept = library_root / keep_rel
    if not dropped.exists():
        return False, f"copy to retire is gone: {drop}"
    if not kept.exists():
        return False, f"copy to keep is gone: {keep_rel}"

    _merge_into_keeper(kept, [dropped], undo_log=undo_log)

    sub = ("upgraded_preprints" if _status_class(drop) == "preprint"
           else "duplicates")
    trash = library_root / ".trash" / sub
    trash.mkdir(parents=True, exist_ok=True)
    dest = trash / dropped.name
    n = 1
    while dest.exists():
        dest = trash / f"{dropped.stem} ({n}){dropped.suffix}"
        n += 1
    try:
        logged_move(dropped, dest, undo_log=undo_log)
    except Exception as exc:
        return False, f"retire failed: {exc}"
    return True, f"retired to {dest.relative_to(library_root)}"


def retire_preprint(pair: VariantPair, library_root: Path, *, undo_log=None) -> tuple:
    """Convenience: retire the preprint side (see ``retire_variant``)."""
    return retire_variant(pair, library_root, drop=pair.preprint, undo_log=undo_log)


def compare_pair(pair: VariantPair, library_root: Path) -> dict:
    """Pages/bytes for both sides so extended preprints stand out."""
    def info(rel: str) -> dict:
        p = library_root / rel
        d = {"exists": p.exists(), "bytes": 0, "pages": None}
        if d["exists"]:
            try:
                d["bytes"] = p.stat().st_size
            except OSError:
                pass
            try:
                import fitz
                with fitz.open(p) as doc:
                    d["pages"] = doc.page_count
            except Exception:
                pass
        return d

    return {"preprint": info(pair.preprint), "published": info(pair.published)}
