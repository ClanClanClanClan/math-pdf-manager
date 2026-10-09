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


def _file_id(p: Path):
    """``(st_dev, st_ino)``, or ``None`` when there is no such file.

    A record is identified by the FILE, not by how its path is spelled.
    APFS folds case and macOS hands names back NFD-decomposed, so one
    record can be reached under two spellings; comparing path strings
    counted such a record as both claimed and orphaned. ``stat`` also
    answers ``None`` instead of raising when a name is over the 255-byte
    limit, which ``exists()`` does not.
    """
    try:
        st = p.stat()
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


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


def claimed_records(pdfs) -> tuple[set, list]:
    """``(claimed, homeless)`` over ``pdfs``.

    ``claimed`` -- the file ids of every record some PDF would read: each
    of its ``sidecar_candidates`` that exists, including the hashed
    location used for over-long names. ``homeless`` -- the PDFs with no
    record anywhere.

    This used to be guessed from the record's own name: strip
    ``.meta.json``, add ``.pdf``, see if that file exists. The hashed
    ``.sidecars/<sha1>.meta.json`` records of the longest names can never
    pass that test, so 24 healthy records were called orphans while one
    real orphan was missed (cockpit audit, measured 2026-09-05).
    """
    from processing.identity import sidecar_candidates
    claimed: set = set()
    homeless: list = []
    for pdf in pdfs:
        ids = [fid for fid in map(_file_id, sidecar_candidates(pdf)) if fid]
        claimed.update(ids)
        if not ids:
            homeless.append(pdf)
    return claimed, homeless


def unclaimed_records(library_root: Path, claimed: set) -> list[Path]:
    """THE orphan rule: a record in the mirror that no paper claims.

    Shared with ``maintenance.conformance.check_sidecars`` so the number
    Conformance prints in red and the list this module repairs are the
    same list. Records shadowing ``.trash`` (and the other non-library
    folders) are not orphans: a retired paper's record is unclaimable by
    construction.
    """
    from processing.identity import _NON_LIBRARY_DIRS
    mirror = _sidecar_root(library_root)
    if not mirror.is_dir():
        return []
    out = []
    for sc in mirror.rglob("*.meta.json"):
        if any(part in _NON_LIBRARY_DIRS
               for part in sc.relative_to(mirror).parts):
            continue
        fid = _file_id(sc)
        if fid is not None and fid not in claimed:
            out.append(sc)
    return sorted(out)


def find_orphans(library_root: Path) -> list[Path]:
    """Records that belong to no paper in the library."""
    from processing.identity import iter_pdfs
    claimed, _ = claimed_records(iter_pdfs(library_root))
    return unclaimed_records(library_root, claimed)


def _recorded_hash(sidecar: Path) -> str:
    try:
        return json.loads(sidecar.read_text(encoding="utf-8")).get(
            "content_sha256") or ""
    except Exception:
        return ""


def plan_reconnect(library_root: Path) -> dict:
    """Work out which orphan belongs to which PDF.  Touches nothing.

    Returns ``{"orphans": n, "matched": [(sidecar, pdf)], "ambiguous":
    [...], "unmatched": [...], "candidates": n}``.

    Only PDFs with NO record anywhere are candidates. A PDF that already
    has one is never offered another, so a reconnect cannot replace a
    good record with a stale one.
    """
    from processing.identity import compute_content_hash, iter_pdfs

    claimed, homeless = claimed_records(iter_pdfs(library_root))
    orphans = unclaimed_records(library_root, claimed)

    by_hash: dict[str, list[Path]] = {}
    if orphans:                       # nothing to match: hash nothing
        for pdf in homeless:
            h = compute_content_hash(pdf)
            if h:
                by_hash.setdefault(h, []).append(pdf)

    matched, ambiguous, unmatched = [], [], []
    claimed_pdfs: set[Path] = set()
    for s in orphans:
        want = _recorded_hash(s)
        hits = [p for p in by_hash.get(want, []) if p not in claimed_pdfs] if want else []
        if len(hits) == 1:
            claimed_pdfs.add(hits[0])
            matched.append((s, hits[0]))
        elif len(hits) > 1:
            ambiguous.append(s)
        else:
            unmatched.append(s)
    return {"orphans": len(orphans), "matched": matched,
            "ambiguous": ambiguous, "unmatched": unmatched,
            "candidates": len(homeless)}


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

    from processing.identity import (compute_content_hash, find_sidecar,
                                     sidecar_path)
    moved, skipped = 0, []
    try:
        for sidecar, pdf in pairs:
            sidecar, pdf = Path(sidecar), Path(pdf)
            # The plan can be minutes old. Everything it relied on is
            # checked again, at the moment of the move.
            if _file_id(sidecar) is None:
                skipped.append({"sidecar": sidecar.name, "reason":
                                "the record is no longer where the check found it"})
                continue
            if _file_id(pdf) is None:
                skipped.append({"sidecar": sidecar.name, "reason":
                                "the paper is no longer where the check found it"})
                continue
            # Where a NEW record for this paper is written -- the hashed
            # location for an over-long name, which the naive mirror path
            # used to ignore (the move then failed on ENAMETOOLONG).
            dest = sidecar_path(pdf)
            if find_sidecar(pdf) is not None or _exists(dest) is not False:
                skipped.append({"sidecar": sidecar.name, "reason":
                                "that paper already has a record"})
                continue
            want = _recorded_hash(sidecar)
            if not want or compute_content_hash(pdf) != want:
                skipped.append({"sidecar": sidecar.name, "reason":
                                "the paper's contents no longer match the record"})
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
