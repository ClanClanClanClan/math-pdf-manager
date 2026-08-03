"""Reconnect sidecars that were stranded when their PDF was renamed.

A sidecar lives in the hidden mirror at the PDF's own relative path, so
renaming a PDF must rename its sidecar too.  ``logged_rename`` does that
— but renames that happened outside it (earlier tooling, a manual
Finder rename) left the sidecar behind under the old name.  The paper
then has NO identity record: its DOI, arXiv id, cached first-page text
and content hash are all sitting in a file nothing points at.

Matching is by CONTENT HASH, never by guessing at names.  Each orphan
sidecar already records the ``content_sha256`` of the PDF it belongs to,
so the safe question is "which PDF hashes to this?" rather than "which
filename looks similar?".  Only PDFs that currently LACK a sidecar are
candidates, which keeps the hashing cheap (hundreds of files, not tens
of thousands) and means a reconnect can never steal another paper's
record.

Everything is dry-run by default and applied through the undo log.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _sidecar_root(library_root: Path) -> Path:
    from processing.identity import MIRROR_DIR_NAME
    return library_root / MIRROR_DIR_NAME


def _pdf_for_sidecar(library_root: Path, sidecar: Path) -> Path:
    rel = sidecar.relative_to(_sidecar_root(library_root))
    return library_root / rel.with_name(rel.name[: -len(".meta.json")] + ".pdf")


def _exists(p: Path):
    """``True``/``False``, or ``None`` when the path itself is unusable.

    A canonical name can be long enough that appending ``.meta.json``
    pushes the sidecar past the filesystem's 255-byte limit, and
    ``exists()`` RAISES there rather than answering.
    """
    try:
        return p.exists()
    except OSError:
        return None


def find_orphans(library_root: Path) -> list[Path]:
    """Sidecars whose PDF is not where the mirror says it should be."""
    root = _sidecar_root(library_root)
    if not root.is_dir():
        return []
    out = []
    for s in root.rglob("*.meta.json"):
        if _exists(_pdf_for_sidecar(library_root, s)) is False:
            out.append(s)
    return out


def plan_reconnect(library_root: Path) -> dict:
    """Work out which orphan belongs to which PDF.  Touches nothing.

    Returns ``{"matched": [(sidecar, pdf)], "ambiguous": [...],
    "unmatched": [...], "candidates": n}``.
    """
    from processing.identity import compute_content_hash, iter_pdfs

    orphans = find_orphans(library_root)
    # Only PDFs with no sidecar of their own can receive one.
    homeless = []
    for pdf in iter_pdfs(library_root):
        rel = pdf.relative_to(library_root)
        side = _sidecar_root(library_root) / rel.with_suffix(".meta.json")
        if _exists(side) is False:
            homeless.append(pdf)

    by_hash: dict[str, list[Path]] = {}
    for pdf in homeless:
        h = compute_content_hash(pdf)
        if h:
            by_hash.setdefault(h, []).append(pdf)

    matched, ambiguous, unmatched = [], [], []
    claimed: set[Path] = set()
    for s in orphans:
        try:
            want = json.loads(s.read_text()).get("content_sha256") or ""
        except Exception:
            want = ""
        hits = [p for p in by_hash.get(want, []) if p not in claimed] if want else []
        if len(hits) == 1:
            claimed.add(hits[0])
            matched.append((s, hits[0]))
        elif len(hits) > 1:
            ambiguous.append(s)
        else:
            unmatched.append(s)
    return {"matched": matched, "ambiguous": ambiguous,
            "unmatched": unmatched, "candidates": len(homeless)}


def apply_reconnect(library_root: Path, plan: dict, *, dry_run: bool = True,
                    undo_log=None) -> dict:
    """Move each matched sidecar to sit beside its PDF.

    Never overwrites: if the destination already exists the pair is
    skipped, because that PDF already has a record and clobbering it
    would destroy a good one to save a stale one.
    """
    pairs = plan.get("matched", [])
    if dry_run:
        return {"dry_run": True, "would_reconnect": len(pairs)}

    from processing.undo_log import UndoLog

    own = undo_log is None
    log = undo_log or UndoLog(log_dir=library_root / ".operation_log")
    tx_id = None
    if own:
        tx_id = log.begin_transaction(f"reconnect {len(pairs)} orphaned sidecars")

    moved, skipped = 0, []
    try:
        for sidecar, pdf in pairs:
            rel = pdf.relative_to(library_root)
            dest = _sidecar_root(library_root) / rel.with_suffix(".meta.json")
            if _exists(dest) is not False:
                skipped.append({"sidecar": sidecar.name, "reason":
                                "that paper already has a record"})
                continue
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                log.record_rename(sidecar, dest)
                sidecar.rename(dest)
                moved += 1
            except OSError as exc:
                skipped.append({"sidecar": sidecar.name, "reason": str(exc)})
    finally:
        if own:
            if log.has_operations():
                log.commit()
            else:
                log.discard()
                tx_id = None
    return {"dry_run": False, "reconnected": moved, "skipped": skipped,
            "tx_id": tx_id}
