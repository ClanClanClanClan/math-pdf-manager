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
import unicodedata
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


def _read_record(sidecar: Path) -> dict:
    """The record's fields; ``{}`` when it cannot be read as an object."""
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _recorded_hash(sidecar: Path) -> str:
    return _read_record(sidecar).get("content_sha256") or ""


def _places_it_answers_for(sidecar: Path, locations):
    """The entries of ``locations`` naming where this record's paper was
    when the record was left behind -- ``None`` when that cannot be told
    (the field is not a list of paths).

    An entry names that place when a paper there would read THIS record,
    asked of the filesystem by file identity, not by spelling. One rule
    for every kind of record: an ordinary one, a full-name one of 252-255
    bytes, and a coded ``.sidecars/<sha1>`` one, whose name is a hash of
    the old filename -- it cannot be read back, but it can be checked.
    The hash is of the name as it was spelled, so each entry is also
    tried in both Unicode forms; case and the other kinds' forms the
    filesystem folds by itself.
    """
    from processing.identity import sidecar_candidates
    fid = _file_id(sidecar)
    if (fid is None or not isinstance(locations, list)
            or not all(isinstance(loc, str) for loc in locations)):
        return None
    out = []
    for loc in locations:
        # A relative entry means nothing fixed: read against the working
        # directory, it could answer to a record from one place and not
        # from another.
        if not Path(loc).is_absolute():
            continue
        forms = {loc, *(unicodedata.normalize(f, loc) for f in ("NFC", "NFD"))}
        if any(_file_id(c) == fid
               for form in forms for c in sidecar_candidates(Path(form))):
            out.append(loc)
    return out


def _name_the_paper_here(pdf: Path, old_places, log) -> list[str]:
    """After a reconnect: the record, now beside ``pdf``, names it.

    What ``logged_rename`` does to the list, had the rename that stranded
    the record gone through it: the entry for the old place becomes
    ``pdf``, which is added if no entry named it. Only ``copy_locations``
    changes, in the same transaction as the move, so undo puts the record
    back byte for byte. Entries the record does not answer to are not
    touched -- they may be a topic copy, or a place from an older history
    this move knows nothing about -- and no other file is renamed (unlike
    ``logged_rename``, which also renames topic copies: the reconnect
    moves a record, nothing else).

    Returns what is still wrong, in words; an empty list when nothing is.
    """
    from processing.identity import record_location, repath_copy_locations
    if old_places is None:
        return ["its list of the paper's places could not be read, so it "
                "was left as it was"]
    try:
        repath_copy_locations(pdf, old_path=Path(old_places[0]) if old_places else None,
                              new_path=pdf, undo_log=log)
    except OSError as exc:            # the write; the list holds only paths
        return [f"its list of the paper's places could not be updated: {exc}"]
    now = _read_record(record_location(pdf)).get("copy_locations", [])
    return [f"it still lists a place where no file is: {loc}"
            for loc in now if _file_id(Path(loc)) is None]


def plan_reconnect(library_root: Path) -> dict:
    """Work out which orphan belongs to which PDF.  Touches nothing.

    Returns ``{"orphans": n, "matched": [(sidecar, pdf)], "ambiguous":
    [...], "to_trash": [(sidecar, trash_pdf)], "to_trash_refused":
    [(sidecar, reason)], "unmatched": [...], "candidates": n,
    "trash_candidates": n}``.

    Only PDFs with NO record anywhere are candidates. A PDF that already
    has one is never offered another, so a reconnect cannot replace a
    good record with a stale one.

    ``to_trash``: records no paper in the library matches, whose paper is
    already in ``.trash`` -- retired by a path that left the record
    behind (measured 2026-10-09: 3 of 39, the preprints of the June pilot
    upgrade). Same rule, among record-less PDFs in the trash, tried only
    after the library: a paper on the shelves always comes first. Kept
    apart from ``matched`` so the owner decides each kind separately. A
    record whose old place is an archival collection is not proposed
    (``to_trash_refused``, with the reason): those keep their records,
    and no tool proposes retiring anything in them.
    """
    from processing.identity import PDF_GLOB, compute_content_hash, iter_pdfs
    from processing.library_scope import why_not_proposable

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

    to_trash, refused, n_trash = [], [], 0
    trash = library_root / ".trash"
    if unmatched and trash.is_dir():
        _, trash_homeless = claimed_records(sorted(trash.rglob(PDF_GLOB)))
        n_trash = len(trash_homeless)
        in_trash: dict[str, list[Path]] = {}
        for pdf in trash_homeless:
            h = compute_content_hash(pdf)
            if h:
                in_trash.setdefault(h, []).append(pdf)
        def lone_hit(s):
            want = _recorded_hash(s)
            hits = in_trash.get(want, []) if want else []
            return hits[0] if len(hits) == 1 else None   # two papers: not guessed
        # Two records wanting ONE paper are not chosen between either (the
        # standing ruling: two records for one paper are merged, never
        # picked from); both stay where they are.
        wanted: dict[Path, int] = {}
        for s in unmatched:
            hit = lone_hit(s)
            if hit is not None:
                wanted[hit] = wanted.get(hit, 0) + 1
        still = []
        for s in unmatched:
            hit = lone_hit(s)
            if hit is None or wanted[hit] != 1:
                still.append(s)
                continue
            why = why_not_proposable(library_root, _former_place(library_root, s))
            if why:
                refused.append((s, why))
                still.append(s)
                continue
            to_trash.append((s, hit))
        unmatched = still
    return {"orphans": len(orphans), "matched": matched,
            "ambiguous": ambiguous, "to_trash": to_trash,
            "to_trash_refused": refused, "unmatched": unmatched,
            "candidates": len(homeless), "trash_candidates": n_trash}


def _former_place(library_root: Path, sidecar: Path) -> Path:
    """Where the paper this record belonged to used to be (its folder, for
    a coded ``.sidecars/<sha1>`` record, whose name is not recoverable)."""
    from processing.identity import MIRROR_DIR_NAME
    rel = sidecar.relative_to(library_root / MIRROR_DIR_NAME)
    parts = [p for p in rel.parent.parts if p != ".sidecars"]
    name = rel.name[:-len(".meta.json")] + ".pdf"
    return library_root.joinpath(*parts, name)


def _claimed_in_library(library_root: Path, sidecar: Path) -> bool:
    """Does a paper now on the shelf beside this record's old place read it?

    The plan can be minutes old. Had the paper come back since -- an undo
    of the move that stranded the record -- the record is no longer an
    orphan, and moving it would strand the paper instead.
    """
    from processing.identity import PDF_GLOB, sidecar_candidates
    fid = _file_id(sidecar)
    folder = _former_place(library_root, sidecar).parent
    try:
        pdfs = list(folder.glob(PDF_GLOB))
    except OSError:
        return False
    return any(_file_id(c) == fid for pdf in pdfs for c in sidecar_candidates(pdf))


def apply_reconnect(library_root: Path, plan: dict, *, dry_run: bool = True,
                    undo_log=None, pairs_key: str = "matched",
                    description: str = "reconnect {n} orphaned sidecars") -> dict:
    """Move each matched sidecar to sit beside its PDF.

    Never overwrites: if the destination already exists the pair is
    skipped, because that PDF already has a record and clobbering it
    would destroy a good one to save a stale one.

    The record then names the paper where it is now: the entry of its
    ``copy_locations`` for the place it was left at is replaced, in the
    same transaction (:func:`_name_the_paper_here`). A record that kept
    the old place there named a file that no longer exists (9 of the 10
    such records in the library, measured 2026-10-10, were orphans left
    by a rename). Each moved item's ``still`` lists in words what is left
    wrong -- an entry still naming no file, a list that could not be read.

    ``pairs_key`` picks which of the plan's lists to act on -- only that
    one: the papers on the shelves (``matched``) and those already in the
    trash (``to_trash``) are separate decisions.
    """
    pairs = plan.get(pairs_key, [])
    if dry_run:
        return {"dry_run": True, "would_reconnect": len(pairs)}

    from processing.undo_log import UndoLog

    own = undo_log is None
    log = undo_log or UndoLog(log_dir=library_root / ".operation_log")
    tx_id = None
    if own:
        tx_id = log.begin_transaction(description.format(n=len(pairs)))

    from processing.identity import (compute_content_hash, find_sidecar,
                                     sidecar_path)
    moved, skipped, done = 0, [], []
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
            if _claimed_in_library(library_root, sidecar):
                skipped.append({"sidecar": sidecar.name, "reason":
                                "a paper in the library reads this record again"})
                continue
            # Where a NEW record for this paper is written -- the hashed
            # location for an over-long name, which the naive mirror path
            # used to ignore (the move then failed on ENAMETOOLONG).
            dest = sidecar_path(pdf)
            if find_sidecar(pdf) is not None or _exists(dest) is not False:
                skipped.append({"sidecar": sidecar.name, "reason":
                                "that paper already has a record"})
                continue
            record = _read_record(sidecar)
            want = record.get("content_sha256")
            if not want or compute_content_hash(pdf) != want:
                skipped.append({"sidecar": sidecar.name, "reason":
                                "the paper's contents no longer match the record"})
                continue
            # Asked BEFORE the move: afterwards the record answers to the
            # paper's new place, not its old one.
            old_places = _places_it_answers_for(
                sidecar, record.get("copy_locations", []))
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                log.record_rename(sidecar, dest)
                sidecar.rename(dest)
            except OSError as exc:
                skipped.append({"sidecar": sidecar.name, "reason": str(exc)})
                continue
            moved += 1
            done.append({"sidecar": sidecar.name, "paper": pdf.name,
                         "still": _name_the_paper_here(pdf, old_places, log)})
    finally:
        if own:
            if log.has_operations():
                log.commit()
            else:
                log.discard()
                tx_id = None
    return {"dry_run": False, "reconnected": moved, "moved": done,
            "skipped": skipped, "tx_id": tx_id}


def apply_trash_reconnect(library_root: Path, plan: dict, *,
                          dry_run: bool = True, undo_log=None) -> dict:
    """Put each record whose paper is already in the trash beside it.

    The same move, checks and undo as :func:`apply_reconnect`, on the
    plan's ``to_trash`` list only. The record lands in the mirror's
    ``.trash`` shadow, exactly where a retirement through ``logged_move``
    would have put it.
    """
    return apply_reconnect(
        library_root, plan, dry_run=dry_run, undo_log=undo_log,
        pairs_key="to_trash",
        description="Put {n} saved record(s) with their papers in the trash")


# ---------------------------------------------------------------------------
# Papers with TWO records (the older full-name one and the coded one)
# ---------------------------------------------------------------------------

#: Fields that describe the paper's ARRIVAL: when they disagree, the older
#: record is the truer witness (a later blank-then-save wrote the name the
#: paper had by then, not the one it arrived with).
ARRIVAL_FIELDS = ("original_filename", "first_ingested_at")


def plan_record_merges(library_root: Path) -> list:
    """For every paper with two records, what merging them would do.

    Touches nothing. Each item: ``{"pdf", "keep", "retire", "fill": {field:
    value}, "arrival": {field: value}, "conflicts": [field], "refused":
    reason-or-None}``. ``keep`` is the record the app reads (the primary,
    coded location); ``retire`` the older full-name copy. A pair whose
    content fingerprints differ is refused: that is not the same paper.
    """
    from processing.identity import (MIRROR_DIR_NAME, iter_pdfs,
                                     sidecar_path)
    out = []
    mirror = library_root / MIRROR_DIR_NAME
    for pdf in iter_pdfs(library_root):
        keep = sidecar_path(pdf)
        retire = mirror / pdf.relative_to(library_root).parent / (pdf.stem + ".meta.json")
        a, b = _file_id(keep), _file_id(retire)
        if not (a and b) or a == b:
            continue
        item = {"pdf": pdf, "keep": keep, "retire": retire, "fill": {},
                "arrival": {}, "conflicts": [], "refused": None}
        try:
            k = json.loads(keep.read_text(encoding="utf-8"))
            r = json.loads(retire.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            item["refused"] = f"a record could not be read: {exc}"
            out.append(item)
            continue
        if (k.get("content_sha256") and r.get("content_sha256")
                and k["content_sha256"] != r["content_sha256"]):
            item["refused"] = "the two records describe different contents"
            out.append(item)
            continue
        older_is_retire = retire.stat().st_mtime <= keep.stat().st_mtime
        for field, value in r.items():
            if field == "schema_version" or value in (None, "", [], {}, 0, False):
                continue
            mine = k.get(field)
            if mine in (None, "", [], {}, 0, False):
                item["fill"][field] = value
            elif mine != value:
                if field in ARRIVAL_FIELDS and older_is_retire:
                    item["arrival"][field] = value
                elif field not in ARRIVAL_FIELDS:
                    item["conflicts"].append(field)
        out.append(item)
    return out


def apply_record_merges(library_root: Path, plan: list, *, undo_log=None) -> dict:
    """Merge each planned pair into the record the app reads, then retire
    the older copy to ``.trash/duplicate_records/`` -- one undoable
    transaction. Conflicting fields keep the app's value and are reported.
    """
    from processing.identity import PaperIdentity
    from processing.undo_log import UndoLog, logged_move

    own = undo_log is None
    log = undo_log or UndoLog(log_dir=library_root / ".operation_log")
    tx_id = log.begin_transaction(
        f"Merge {len(plan)} papers' two saved records into one") if own else None
    merged, skipped = [], []
    try:
        for item in plan:
            pdf = Path(item["pdf"])
            if item.get("refused"):
                skipped.append({"pdf": pdf.name, "reason": item["refused"]})
                continue
            if _file_id(Path(item["retire"])) is None or _file_id(Path(item["keep"])) is None:
                skipped.append({"pdf": pdf.name, "reason": "the records changed since the plan"})
                continue
            ident = PaperIdentity.load(pdf)
            for field, value in {**item["fill"], **item["arrival"]}.items():
                if hasattr(ident, field):
                    setattr(ident, field, value)
            ident.save(pdf, recompute_hash=False, undo_log=log)
            retire = Path(item["retire"])
            dest = (library_root / ".trash" / "duplicate_records"
                    / retire.relative_to(library_root / ".mathpdf-sidecars"))
            n = 2
            while dest.exists():
                dest = dest.with_name(f"{dest.stem} ({n}){dest.suffix}")
                n += 1
            logged_move(retire, dest, undo_log=log)
            merged.append({"pdf": pdf.name, "filled": sorted(item["fill"]),
                           "arrival": sorted(item["arrival"]),
                           "conflicts": item["conflicts"]})
    finally:
        if own:
            if log.has_operations():
                log.commit()
            else:
                log.discard()
                tx_id = None
    return {"merged": merged, "skipped": skipped, "tx_id": tx_id}
