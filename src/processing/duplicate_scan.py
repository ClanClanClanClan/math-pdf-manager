"""Authoritative whole-library duplicate detection + reversible resolution.

The library accumulated duplicates several ways over the years:

* the same download hand-filed into both a top-level status folder
  (``01 - Published papers/G/foo.pdf``) AND its topic folder
  (``07a - BSDEs/01 - Published papers/G/foo.pdf``) -- the
  "status+topic" case that the topic bulk-apply surfaced as a bare
  "destination already exists" failure;
* preprint leftovers in ``04 - Papers to be downloaded`` that were
  later filed under a real status/topic;
* byte-identical copies under slightly different filenames.

Before this module the dedup story was fragmented across three siloed,
incomplete surfaces (Dropbox-conflict resolver, a fuzzy-title finder
that *excludes* cross-filings by design, and a display-only 1MB-hash
collision list) and **none of them caught the status+topic case**.

This module is the single authoritative detector + resolver:

* **Detection is correctness-grade and sidecar-independent.**  Two
  byte-identical files always share an exact ``st_size``, so we bucket
  by size first (a cheap ``stat``, no content read, works even on
  Dropbox online-only placeholders) and then confirm each size
  collision with a **full-file SHA-256**.  This deliberately avoids the
  1MB-prefix hash (``identity.compute_content_hash``), which has false
  positives on template-heavy publishers and needs a populated sidecar.

* **Resolution is reversible.**  Redundant copies are moved to
  ``.trash/duplicates/`` through ``logged_move`` inside ONE undo
  transaction (never hard-deleted), exactly like the conflict resolver.
  The kept copy inherits the removed copies' sidecar knowledge
  (topic codes, publication-check history, DOI/arXiv) before they go.

* **Policy is explicit and conservative.**  A topic copy beats a
  top-level status copy (the topic folder is a filed paper's home); the
  ``04``/``12`` staging folders always lose to a real home; and any
  group that touches a *curated* special collection (``08``/``09``/``10``
  /``archive``) is flagged ``review`` and never auto-removed.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Full-file hashing chunk size.
_HASH_CHUNK = 1 << 20  # 1 MiB

# Top-level folders that are real "homes" for a filed paper.
STATUS_DIRS = {
    "01 - Published papers",
    "02 - Unpublished papers",
    "03 - Working papers",
    "05 - Books and lecture notes",
    "06 - Theses",
}
# Staging areas -- a copy here is always redundant to a real home.
STAGING_DIRS = {
    "04 - Papers to be downloaded",
    "12 - To be sorted",
}
# Topic folders are matched by the ``07x`` prefix (07a..07f and any
# future sibling) so we don't hard-code the French titles.
TOPIC_PREFIX = "07"
# Curated special collections: a copy here is intentional, so a group
# spanning one is flagged for review rather than auto-resolved.  Matched
# by leading token / name.
SPECIAL_PREFIXES = ("08", "09", "10", "archive")
# Directories under the library root that are not the paper library.
NON_LIBRARY_TOP = {"Scripts", "gmnap", "unicode_utils"}

# Location-class ranking for choosing which copy to KEEP (lower = keep).
_CLASS_RANK = {"topic": 0, "status": 1, "special": 2, "staging": 3, "other": 4}

# Filenames at or above this token-sorted similarity (0-100) are treated
# as the same paper under a trivially different label (typo, punctuation,
# an extra initial).  Below it, two byte-identical files with *different*
# names are suspicious — possibly a mis-file where one name's real paper
# is actually missing — so the group is flagged for human review rather
# than auto-removed.
_NAME_SIM_AUTO = 90.0


def _name_similarity(a: str, b: str) -> float:
    """Token-sorted similarity of two filename stems, 0-100.

    Prefers rapidfuzz (already a dependency of ``duplicate_finder``);
    falls back to the stdlib ``difflib`` so the detector never hard-fails
    if rapidfuzz is unavailable.
    """
    if a == b:
        return 100.0
    try:
        from rapidfuzz import fuzz
        return float(fuzz.token_sort_ratio(a, b))
    except Exception:
        import difflib
        return difflib.SequenceMatcher(None, a, b).ratio() * 100.0


def compute_full_hash(pdf_path: Path) -> str:
    """SHA-256 of the WHOLE file (chunked).  ``""`` if unreadable.

    Unlike ``identity.compute_content_hash`` (first 1MB only), this is a
    correctness-grade fingerprint: equal full hashes mean byte-identical
    files.  Only ever called on the small set of size-collision
    candidates, so the extra I/O is bounded.
    """
    try:
        h = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(_HASH_CHUNK), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError as exc:
        logger.warning("compute_full_hash failed for %s: %s", pdf_path, exc)
        return ""


def _toplevel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        return ""


def _classify_location(path: Path, root: Path) -> str:
    """One of ``topic|status|staging|special|other`` for a PDF path."""
    top = _toplevel(path, root)
    if not top:
        return "other"
    if top.startswith(TOPIC_PREFIX) and top not in STAGING_DIRS:
        # 07x topics (but '04'/'12' don't start with '07' so safe).
        return "topic"
    if top in STATUS_DIRS:
        return "status"
    if top in STAGING_DIRS:
        return "staging"
    if any(top.startswith(p) or top == p for p in SPECIAL_PREFIXES):
        return "special"
    return "other"


def _has_sidecar(path: Path) -> bool:
    try:
        from processing.identity import sidecar_path
        return sidecar_path(path).exists()
    except Exception:
        return False


@dataclass
class DuplicateGroup:
    """A set of byte-identical PDFs and the resolution we propose."""

    sha256: str
    size: int
    paths: list[str]                       # all copies, sorted
    keep: str                              # the copy to keep
    remove: list[str]                      # copies to trash (never specials)
    kind: str                              # status+topic | staging-leftover | ...
    reason: str                            # human explanation of the keep choice
    auto_safe: bool                        # True -> eligible for the default apply
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _decide(paths: list[Path], root: Path) -> DuplicateGroup:
    """Pick the keeper and the removable copies for one byte-identical set."""
    classes = {str(p): _classify_location(p, root) for p in paths}
    has_special = any(c == "special" for c in classes.values())

    def sort_key(p: Path):
        cls = classes[str(p)]
        rel = p.relative_to(root) if _is_under(p, root) else p
        depth = len(rel.parts)
        # Prefer: better class, then a copy WITH a sidecar, then a
        # DEEPER path (alpha-subdir / topic over bare root), then a
        # stable alphabetical tie-break for determinism.
        return (_CLASS_RANK.get(cls, 4), 0 if _has_sidecar(p) else 1, -depth, str(p))

    ordered = sorted(paths, key=sort_key)
    keep = ordered[0]
    # Never auto-remove a curated special-collection copy.
    removable = [p for p in ordered[1:] if classes[str(p)] != "special"]

    present = set(classes.values())
    if "topic" in present and "status" in present:
        kind = "status+topic"
    elif present & {"staging"}:
        kind = "staging-leftover"
    elif len({_toplevel(p, root) for p in paths}) == 1:
        kind = "same-folder"
    else:
        kind = "cross-folder"

    keep_cls = classes[str(keep)]
    reason = {
        "topic": "kept the topic-folder copy (a filed paper's home)",
        "status": "kept the status-folder copy",
        "special": "kept the curated-collection copy",
        "staging": "kept the staging copy (no real home found)",
        "other": "kept this copy",
    }[keep_cls]

    # A removed copy is "clearly redundant" only if it sits in a staging
    # dump (04/12) OR carries a near-identical filename to the keeper.
    # A byte-identical copy under a *substantially different* name is the
    # dangerous case (possible mis-file), so it blocks auto-resolution.
    name_divergent = [
        p for p in removable
        if classes[str(p)] != "staging"
        and _name_similarity(keep.stem, p.stem) < _NAME_SIM_AUTO
    ]

    notes: list[str] = []
    auto_safe = True
    if has_special:
        auto_safe = False
        notes.append(
            "group touches a curated special collection "
            "(08/09/10/archive) — review before removing."
        )
    if not removable:
        auto_safe = False
        notes.append("nothing safely removable; review.")
    if kind == "cross-folder":
        # Byte-identical across different real homes (e.g. Published vs
        # Books vs Theses, or Working vs Published).  Which folder is the
        # correct home is a judgment call the user must make.
        auto_safe = False
        notes.append(
            "byte-identical across different homes (e.g. published vs "
            "book vs thesis) — pick the correct home before removing."
        )
    if name_divergent:
        auto_safe = False
        notes.append(
            f"byte-identical but {len(name_divergent)} copy/copies carry a "
            "different title — possible mis-file (the differently-named "
            "paper may be missing); review before removing."
        )

    return DuplicateGroup(
        sha256="",  # filled by caller
        size=keep.stat().st_size if keep.exists() else 0,
        paths=sorted(str(p) for p in paths),
        keep=str(keep),
        remove=[str(p) for p in removable],
        kind=kind,
        reason=reason,
        auto_safe=auto_safe,
        notes=notes,
    )


def _is_under(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root)
        return True
    except ValueError:
        return False


def _scannable(root: Path):
    """Yield library PDFs, skipping code dirs, dotdirs and ``.trash``."""
    from processing.identity import iter_pdfs
    for pdf in iter_pdfs(root):
        top = _toplevel(pdf, root)
        if top in NON_LIBRARY_TOP or top.startswith("."):
            continue
        yield pdf


def find_exact_duplicates(root: Path) -> list[DuplicateGroup]:
    """Return byte-identical duplicate groups across the whole library.

    Algorithm: bucket by ``st_size`` (cheap metadata, no content read),
    then for every size shared by 2+ files confirm with a full-file
    SHA-256 and emit a group per hash shared by 2+ files.
    """
    if not root.exists():
        return []

    size_buckets: dict[int, list[Path]] = {}
    for pdf in _scannable(root):
        try:
            size = pdf.stat().st_size
        except OSError:
            continue
        if size <= 0:
            continue
        size_buckets.setdefault(size, []).append(pdf)

    groups: list[DuplicateGroup] = []
    for size, candidates in size_buckets.items():
        if len(candidates) < 2:
            continue
        by_hash: dict[str, list[Path]] = {}
        for pdf in candidates:
            digest = compute_full_hash(pdf)
            if not digest:
                continue
            by_hash.setdefault(digest, []).append(pdf)
        for digest, members in by_hash.items():
            if len(members) < 2:
                continue
            grp = _decide(members, root)
            grp.sha256 = digest
            grp.size = size
            groups.append(grp)

    # Stable, reviewer-friendly order: auto-safe first, then by kind,
    # then by keeper path.
    groups.sort(key=lambda g: (not g.auto_safe, g.kind, g.keep))
    return groups


def find_library_duplicate(
    pdf: Path,
    root: Path,
    *,
    ignore: Optional[list] = None,
) -> Optional[str]:
    """Return an existing library path byte-identical to ``pdf``, else None.

    The ingest guard: before filing a new arrival, check whether the
    library already holds the exact same bytes (e.g. a re-download of an
    already-filed paper).  Size-prefiltered — stats library PDFs and only
    full-hashes the (usually zero) candidates whose size matches ``pdf`` —
    so the common "unique size" case costs a single metadata walk.

    ``ignore`` is a list of directories to exclude from the comparison
    (typically the inbox the file is arriving from, so it doesn't match
    itself or its siblings).  Best-effort: returns None on any read error
    rather than raising, so it can never block an ingest.
    """
    if not pdf.exists():
        return None
    try:
        target_size = pdf.stat().st_size
    except OSError:
        return None
    if target_size <= 0:
        return None

    ignore_dirs = [Path(p) for p in (ignore or [])]

    def _ignored(p: Path) -> bool:
        return any(p == d or d in p.parents for d in ignore_dirs)

    target_hash: Optional[str] = None
    for other in _scannable(root):
        if other == pdf or _ignored(other):
            continue
        try:
            if other.stat().st_size != target_size:
                continue
        except OSError:
            continue
        if target_hash is None:
            target_hash = compute_full_hash(pdf)
            if not target_hash:
                return None
        if compute_full_hash(other) == target_hash:
            return str(other)
    return None


# ---------------------------------------------------------------------------
# Reversible resolution
# ---------------------------------------------------------------------------

def _merge_into_keeper(keep: Path, removed: list[Path], undo_log=None) -> None:
    """Fold removed copies' sidecar knowledge into the keeper's sidecar.

    Best-effort and reversible: the field changes are recorded as a
    ``sidecar_edit`` so undo restores the keeper's prior sidecar.  The
    keeper file itself never moves.
    """
    try:
        from processing.identity import PaperIdentity, sidecar_path
        from processing.conflict_resolver import _merge_sidecars
    except Exception:  # pragma: no cover - defensive
        return
    if not sidecar_path(keep).exists():
        return
    keeper = PaperIdentity.load(keep)
    if keeper.is_new():
        return
    before = {
        "topic_codes": list(keeper.topic_codes),
        "doi": keeper.doi,
        "arxiv_id": keeper.arxiv_id,
        "publication_checks": list(keeper.publication_checks),
        "recheck_count": keeper.recheck_count,
        "permanently_unpublished": keeper.permanently_unpublished,
        "copy_locations": list(keeper.copy_locations),
        "first_ingested_at": keeper.first_ingested_at,
    }
    changed = False
    for r in removed:
        if not sidecar_path(r).exists():
            continue
        loser = PaperIdentity.load(r)
        if loser.is_new():
            continue
        if _merge_sidecars(loser, keeper):
            changed = True
    if not changed:
        return
    after = {
        "topic_codes": list(keeper.topic_codes),
        "doi": keeper.doi,
        "arxiv_id": keeper.arxiv_id,
        "publication_checks": list(keeper.publication_checks),
        "recheck_count": keeper.recheck_count,
        "permanently_unpublished": keeper.permanently_unpublished,
        "copy_locations": list(keeper.copy_locations),
        "first_ingested_at": keeper.first_ingested_at,
    }
    keeper.save(keep, recompute_hash=False)
    if undo_log is not None:
        diff = {k: [before[k], after[k]] for k in before if before[k] != after[k]}
        if diff:
            undo_log.record_sidecar_edit(keep, diff)


def resolve_group(
    group: DuplicateGroup,
    root: Path,
    *,
    undo_log=None,
) -> list[tuple[bool, str]]:
    """Trash this group's removable copies (reversibly) into ``.trash/duplicates``.

    The keeper inherits the removed copies' sidecar knowledge first, then
    each removable copy is moved (with its sidecar) into the trash via
    ``logged_move``.  Records go into ``undo_log`` so the whole thing is
    one-click reversible.  Returns ``(ok, message)`` per removed copy.
    """
    from processing.undo_log import logged_move

    keep = Path(group.keep)
    removed = [Path(p) for p in group.remove if Path(p) != keep]
    # Enrich the keeper's sidecar BEFORE the copies are trashed.  This MUST
    # precede the moves: ``logged_move`` carries each removed copy's sidecar
    # into the trash mirror, so once moved ``sidecar_path(original)`` no
    # longer resolves and the merge would silently find nothing to fold in.
    # The keeper file itself never moves, so its recorded ``sidecar_edit``
    # reverses correctly regardless of position in the transaction.
    if removed:
        _merge_into_keeper(keep, [p for p in removed if p.exists()],
                           undo_log=undo_log)

    results: list[tuple[bool, str]] = []
    trash = root / ".trash" / "duplicates"
    trash.mkdir(parents=True, exist_ok=True)
    for src in removed:
        if not src.exists():
            results.append((False, f"already gone: {src}"))
            continue
        dest = trash / src.name
        n = 1
        while dest.exists():
            dest = trash / f"{src.stem} ({n}){src.suffix}"
            n += 1
        try:
            logged_move(src, dest, undo_log=undo_log)
            results.append((True, f"trashed {src} -> {dest}"))
        except Exception as exc:
            results.append((False, f"{src}: {exc}"))
    return results


def apply_duplicate_resolutions(
    root: Path,
    groups: Optional[list[DuplicateGroup]] = None,
    *,
    dry_run: bool = True,
    auto_only: bool = True,
    limit: Optional[int] = None,
    exclude: Optional[set] = None,
    undo_log=None,
) -> dict:
    """Gated, reversible duplicate cleanup.

    * ``dry_run`` (default True): compute and return what WOULD be
      removed; touch nothing, open no transaction.
    * ``auto_only`` (default True): only act on ``auto_safe`` groups
      (skips anything touching a curated special collection).
    * ``exclude``: keeper paths to skip (Unicode-normalised, like the
      topic bulk-apply), so a reviewer can veto individual groups.
    * Each real run wraps every group in ONE undo transaction and is
      crash-safe: a single failing group never aborts the batch or loses
      the transaction (commit happens in ``finally``).
    """
    import unicodedata

    if groups is None:
        groups = find_exact_duplicates(root)

    def norm(s: str) -> str:
        return unicodedata.normalize("NFC", s)

    excl = {norm(e) for e in (exclude or set())}
    selected = [
        g for g in groups
        if (g.auto_safe or not auto_only) and norm(g.keep) not in excl and g.remove
    ]
    if limit is not None:
        selected = selected[:limit]

    if dry_run:
        return {
            "dry_run": True,
            "groups_total": len(groups),
            "selected": len(selected),
            "would_remove": sum(len(g.remove) for g in selected),
            "would_apply": [g.to_dict() for g in selected],
            "skipped_review": [g.to_dict() for g in groups if not g.auto_safe],
        }

    from processing.undo_log import UndoLog
    # Default to the library's shared operation log so the dedup shows up
    # in the cockpit Activity tab alongside every other reversible action.
    log = undo_log or UndoLog(log_dir=root / ".operation_log")
    own_tx = undo_log is None
    tx_id = None
    if own_tx:
        tx_id = log.begin_transaction(
            f"dedup: trash {sum(len(g.remove) for g in selected)} copies"
        )

    applied: list[dict] = []
    failed: list[dict] = []
    try:
        for g in selected:
            try:
                res = resolve_group(g, root, undo_log=log)
                for ok, msg in res:
                    (applied if ok else failed).append({"keep": g.keep, "msg": msg})
            except Exception as exc:  # never let one group abort the batch
                failed.append({"keep": g.keep, "msg": f"error: {exc}"})
    finally:
        if own_tx:
            log.commit()  # crash-safe: done work stays recorded/reversible

    return {
        "dry_run": False,
        "applied": applied,
        "failed": failed,
        "removed": len(applied),
        "tx_id": tx_id,
    }
