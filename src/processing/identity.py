#!/usr/bin/env python3
"""Paper identity sidecar.

Each filed PDF gets a ``<stem>.meta.json`` sidecar next to it.  The
sidecar is the single source of truth for everything the system needs
to remember about a paper that isn't recoverable from the filename
alone:

* External identifiers (DOI, arXiv ID)
* Content hash (first 1MB SHA-256) — drift detection
* Publication-checker state machine (recheck counter, permanent flag)
* Copy locations (topic folders, etc.)
* Ingest provenance (timestamp + undo_log transaction)

Design constraints
------------------
1. **Atomic writes** — write to ``<sidecar>.tmp`` then ``rename``.  An
   interrupted write leaves the previous sidecar intact.
2. **Forward-compatible schema** — every sidecar carries
   ``schema_version``.  Loaders ignore unknown fields rather than
   crashing.
3. **Survives moves** — the public ``move_with_sidecar`` helper moves
   both files atomically through the ``undo_log`` so undo restores
   both.
4. **No hashing on the hot path** — content hash is computed at
   ``save()`` and at explicit ``drift_check()`` time, never on
   ``load()``.  Hashing the first 1MB takes ~3ms on Apple Silicon; the
   library has ~28k papers so a full re-hash backfill is ~85s.
5. **Best-effort** — a missing or unreadable sidecar never aborts the
   pipeline.  ``load()`` returns a fresh ``PaperIdentity`` rather than
   raising.  Callers check ``is_new()`` if they need to distinguish.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Number of bytes used to compute the content hash.  1MB is enough to
# detect "completely different PDF, same filename" while keeping the
# backfill cost bounded on a 28k-paper library.
HASH_PREFIX_BYTES = 1024 * 1024

# Current schema version.  Bump when adding fields that older readers
# wouldn't know to default; older sidecars still load (forward-
# compatible) but the loader fills missing fields with defaults.
SCHEMA_VERSION = 1


# Maximum filename basename length on the user's filesystem.  macOS APFS
# and most Linux ext4 setups cap at 255 bytes (NOT 255 chars -- multi-byte
# characters count).  Querying ``os.pathconf(path, "PC_NAME_MAX")`` would
# be more portable but requires the path to exist; we hard-code 255 since
# every realistic target filesystem uses that limit.
#
# We budget 4 fewer bytes because ``PaperIdentity.save`` writes to a
# transient ``<sidecar>.tmp`` file before ``os.replace``.  A sidecar at
# 254 bytes would have a 258-byte tmp -- creating it fails with
# ENAMETOOLONG.  Live-trial finding: 11 papers in the user's library
# sit in the [252, 255]-byte sidecar-name range; without this budget
# 3 of them errored during the first real backfill.
MAX_BASENAME_BYTES = 251

# Name of the hidden mirror folder where every paper's sidecar lives,
# rooted at the library root.  The library tree itself stays free of
# .meta.json files; only this single dotfolder appears.  It syncs via
# Dropbox so laptop <-> desktop share the same sidecar state without
# re-backfilling.
MIRROR_DIR_NAME = ".mathpdf-sidecars"


def _library_root_for(pdf_path: Path) -> Optional[Path]:
    """Find the library root that owns ``pdf_path``, or None.

    Walks up the directory tree looking for the
    ``.mathpdf-sidecars/`` marker.  If not found, falls back to the
    configured library root from ``core.config_paths.get_library_root``.

    Returns None for PDFs that aren't under any known library
    (synth-library tests in tmp_path, ad-hoc PDFs outside Dropbox).
    Those callers get the natural-path sidecar (next-to-PDF) so the
    test suite keeps working unchanged.
    """
    # Walk-up via the marker.  This makes ``enable_sidecar_mirror``
    # idempotent: once the marker exists, every call resolves to that
    # library root regardless of where ``get_library_root()`` points.
    for ancestor in [pdf_path.parent, *pdf_path.parents]:
        try:
            if (ancestor / MIRROR_DIR_NAME).is_dir():
                return ancestor
        except OSError:
            pass
        if ancestor == Path.home() or ancestor.parent == ancestor:
            break
    # Fallback: configured library root.  Only adopt it if the PDF
    # actually lives under it -- a test in tmp_path with no marker
    # should NOT inherit the real Dropbox library's mirror tree.
    try:
        from core.config_paths import get_library_root
        root = get_library_root().resolve()
    except Exception:
        return None
    if not root.exists():
        return None
    try:
        pdf_path.resolve().relative_to(root)
    except (ValueError, OSError):
        return None
    return root


def enable_sidecar_mirror(library_root: Path) -> Path:
    """Create the ``<library>/.mathpdf-sidecars/`` marker dir.

    Idempotent: returns the existing path if already present.
    After this runs, every ``sidecar_path()`` for a PDF under
    ``library_root`` resolves to a mirrored path rather than the
    natural next-to-PDF location.
    """
    marker = library_root / MIRROR_DIR_NAME
    marker.mkdir(parents=True, exist_ok=True)
    return marker


# ---------------------------------------------------------------------------
# Opt-in read cache for READ-ONLY whole-library sweeps
# ---------------------------------------------------------------------------
#
# ``None`` means "no caching" — that is the state everywhere except inside
# an explicit ``sidecar_read_cache()`` block, so no writer path can ever
# see a stale object by accident.
_SIDECAR_READ_CACHE: Optional[dict] = None


@contextmanager
def sidecar_read_cache():
    """Memoise ``PaperIdentity.load`` for the duration of ONE read-only sweep.

    Several library-wide scanners each walk every PDF and load every
    sidecar.  MEASURED on the 29k library: one full sweep of
    ``PaperIdentity.load`` is ~30s, and the cockpit's attention scan does
    three of them back-to-back (borderline matches, topic suggestions,
    permanently-unpublished) for a 111s total.  Sharing the parsed
    sidecars across those three brings the same scan — byte-identical
    output, 3,261 items in the same order — down to 44s.

    STRICTLY read-only.  Objects are shared, not copied, and a sidecar
    written to disk inside the block will NOT be re-read.  Only wrap
    scanners that make no filesystem changes.  Nesting is safe: an inner
    block reuses the outer cache and does not clear it.
    """
    global _SIDECAR_READ_CACHE
    if _SIDECAR_READ_CACHE is not None:
        yield _SIDECAR_READ_CACHE          # already inside a sweep
        return
    _SIDECAR_READ_CACHE = {}
    try:
        yield _SIDECAR_READ_CACHE
    finally:
        _SIDECAR_READ_CACHE = None


def sidecar_path(pdf_path: Path) -> Path:
    """Return the sidecar path for ``pdf_path``.

    Primary location: ``<library>/.mathpdf-sidecars/<relative-path>.meta.json``
    where ``<relative-path>`` mirrors the PDF's path under the library
    root.  Keeps the library tree itself free of sidecar JSONs while
    letting Dropbox sync the hidden mirror to other machines.

    Fallbacks:
    * PDF not under any known library (synth tests, ad-hoc) -> natural
      ``<pdf>.with_suffix(".meta.json")`` next to the PDF.
    * Mirror path exceeds 255 bytes (the 13-author papers in the
      library) -> hash-named entry in a nested ``.sidecars/`` folder
      inside the mirror parent.
    """
    library_root = _library_root_for(pdf_path)
    if library_root is not None:
        try:
            relative = pdf_path.resolve().relative_to(library_root)
        except (ValueError, OSError):
            library_root = None
    if library_root is not None:
        mirror = (
            library_root / MIRROR_DIR_NAME / relative.with_suffix(".meta.json")
        )
        if len(mirror.name.encode("utf-8")) <= MAX_BASENAME_BYTES:
            return mirror
        import hashlib as _hashlib
        h = _hashlib.sha1(pdf_path.name.encode("utf-8")).hexdigest()[:16]
        return mirror.parent / ".sidecars" / f"{h}.meta.json"

    # No library context: natural sibling (backward-compat for tests
    # and ad-hoc PDFs).
    natural = pdf_path.with_suffix(".meta.json")
    if len(natural.name.encode("utf-8")) <= MAX_BASENAME_BYTES:
        return natural
    import hashlib as _hashlib
    h = _hashlib.sha1(pdf_path.name.encode("utf-8")).hexdigest()[:16]
    return pdf_path.parent / ".sidecars" / f"{h}.meta.json"


# Case-insensitive PDF glob.  ``Path.rglob("*.pdf")`` is
# case-sensitive on Linux and case-insensitive on macOS HFS+/APFS by
# default, but APFS volumes can be configured case-sensitive.  Using a
# character-class pattern matches both ``.pdf`` and ``.PDF`` everywhere
# without depending on volume settings.
PDF_GLOB = "*.[Pp][Dd][Ff]"


def iter_pdfs(root: Path, *, recursive: bool = True):
    """Yield every PDF under ``root`` (case-insensitive suffix match).

    Skips files under any ``.trash`` directory so library scans don't
    fold trash entries back into live workflows.  Callers that *want*
    trash should iterate with ``root.rglob(PDF_GLOB)`` directly.

    ``recursive=False`` matches only direct children of ``root`` (the
    non-recursive ``glob`` equivalent), used by callers like
    ``filename_normalizer`` that already loop over subfolders
    themselves.
    """
    if not root.exists():
        return
    walker = root.rglob(PDF_GLOB) if recursive else root.glob(PDF_GLOB)
    for pdf in walker:
        if not _is_library_pdf(pdf):
            continue
        yield pdf


# Directories that live INSIDE the library root but hold no papers.  The
# code checkout is the important one: it sits under the library and had
# 77 publisher-download test fixtures in it, which every scan counted as
# the owner's papers — inflating the library total and feeding duplicate
# and variant detection with files that are not his.
_NON_LIBRARY_DIRS = frozenset({
    ".trash",          # recoverable deletions, deliberately out of scope
    "Scripts",         # the code checkout
    ".git",
    "node_modules",
    "htmlcov",
    "__pycache__",
    ".venv",
    "venv",
})


def _is_library_pdf(pdf: Path) -> bool:
    """Is this PDF one of the owner's papers, rather than repo furniture?"""
    return not any(part in _NON_LIBRARY_DIRS for part in pdf.parts)


def compute_content_hash(pdf_path: Path) -> str:
    """SHA-256 of the first ``HASH_PREFIX_BYTES`` of the file.

    Why a prefix rather than the full file:
    * Most ~1MB PDF prefixes contain the catalog, cross-ref, and at
      least the first few pages — enough to make distinct papers
      distinguishable.
    * Hashing 28k full PDFs would take >10 minutes; hashing prefixes
      takes ~85 seconds.

    Returns an empty string if the file can't be read.  Hashing is a
    nice-to-have for drift detection, not a correctness requirement.
    """
    try:
        h = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            h.update(f.read(HASH_PREFIX_BYTES))
        return h.hexdigest()
    except OSError as exc:
        logger.warning("compute_content_hash failed for %s: %s", pdf_path, exc)
        return ""


@dataclass
class PaperIdentity:
    """Persistent metadata that travels with each filed PDF.

    Field naming convention: snake_case, ISO-8601 timestamps with the
    ``Z`` suffix, lists default to ``[]`` via ``default_factory``.
    """

    schema_version: int = SCHEMA_VERSION

    # Content fingerprint — first 1MB SHA-256.
    content_sha256: str = ""

    # Original filename at first ingest.  Useful for traceability and
    # for backfill code that wants to reconstruct the pre-ingest name.
    original_filename: str = ""

    # External identifiers.
    doi: str = ""
    arxiv_id: str = ""

    # Ingest provenance.
    first_ingested_at: str = ""
    first_ingest_tx_id: str = ""

    # All places this PDF currently lives.  When the topic router
    # copies/hardlinks the PDF into ``07a/``, that path is appended.
    # ``copy_locations`` should always include the primary path.
    copy_locations: list[str] = field(default_factory=list)

    # Publication-checker state machine.
    # publication_checks: list of dicts:
    #   {"date": "...", "source": "crossref", "hit": false, "confidence": 0.0}
    publication_checks: list[dict] = field(default_factory=list)
    recheck_count: int = 0
    last_check_date: str = ""

    # Once true, the weekly run stops querying Crossref for this paper.
    # User can reset via the cockpit Attention Queue.
    permanently_unpublished: bool = False

    # Topic classification cache (e.g. ``["07a", "07b"]``).
    topic_codes: list[str] = field(default_factory=list)

    # Topic the classifier SUGGESTED but wasn't confident enough to
    # auto-file (confidence in [REVIEW, AUTO)).  The paper currently
    # lives in a standard folder; the cockpit Attention Queue surfaces
    # this so the user can confirm a move into the topic folder.
    # Cleared once the user accepts or rejects.
    topic_suggestion: str = ""
    topic_confidence: float = 0.0

    # Cached classifier signal: the paper's abstract / first-pages text,
    # extracted once and stored so the topic classifier can read the
    # actual content (not just the filename) without re-parsing the PDF.
    # Empirically lifts topic recall ~63%->~91% at unchanged precision,
    # because ~98% of recall-misses have no topic keyword in the title.
    # Capped at a few KB; populated by ``backfill_classifier_text``.
    classifier_text: str = ""
    # True once text extraction has been ATTEMPTED, even if it yielded
    # nothing (scanned/image-only PDF, no text layer).  Lets the backfill
    # converge instead of re-extracting the un-extractable every run.
    classifier_text_tried: bool = False

    # Marker for "this object was constructed because no sidecar
    # existed yet".  Not persisted.
    _is_new: bool = field(default=True, repr=False)

    def is_new(self) -> bool:
        """True if this object was synthesised because no sidecar existed."""
        return self._is_new

    # -----------------------------------------------------------------
    # Load / save
    # -----------------------------------------------------------------

    @classmethod
    def load(cls, pdf_path: Path) -> "PaperIdentity":
        """Load the sidecar next to ``pdf_path``.

        Returns a fresh ``PaperIdentity`` (with ``is_new() == True``)
        if the sidecar is missing, unreadable, or has a future
        ``schema_version`` we don't understand.  This is deliberately
        forgiving — sidecars are a nice-to-have layer, not a hard
        precondition.

        Inside a :func:`sidecar_read_cache` block the parsed result is
        memoised (see that function for why, and for the read-only
        constraint).  Outside one — the default everywhere — this is a
        straight passthrough and behaviour is unchanged.
        """
        cache = _SIDECAR_READ_CACHE
        if cache is None:
            return cls._load_uncached(pdf_path)
        key = str(pdf_path)
        hit = cache.get(key)
        if hit is None:
            hit = cls._load_uncached(pdf_path)
            cache[key] = hit
        return hit

    @classmethod
    def _load_uncached(cls, pdf_path: Path) -> "PaperIdentity":
        """Read and parse one sidecar from disk (no memoisation)."""
        path = sidecar_path(pdf_path)
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("sidecar unreadable %s: %s — treating as missing", path, exc)
            return cls()
        if not isinstance(raw, dict):
            logger.warning("sidecar %s is not a JSON object — treating as missing", path)
            return cls()
        # Forward-compat: keep only fields we know about; older readers
        # silently drop newer fields.  Newer readers tolerate missing
        # older fields via dataclass defaults.
        known = {f for f in cls.__dataclass_fields__ if not f.startswith("_")}
        clean = {k: v for k, v in raw.items() if k in known}
        try:
            obj = cls(**clean)
        except TypeError as exc:
            logger.warning("sidecar %s has bad field types: %s", path, exc)
            return cls()
        obj._is_new = False
        return obj

    def save(self, pdf_path: Path, *, recompute_hash: bool = True,
             undo_log=None) -> Path:
        """Atomically write the sidecar next to ``pdf_path``.

        Writes to ``<sidecar>.tmp`` then ``os.replace`` — an interrupted
        write leaves the previous sidecar intact rather than truncating
        it to zero bytes (a real failure mode under Dropbox sync).

        ``recompute_hash`` controls whether ``content_sha256`` is
        refreshed from the file on disk.  Pass ``False`` when you're
        saving after a pure metadata edit and want to preserve the
        existing hash without re-reading the PDF.

        ``undo_log`` makes the edit REVERSIBLE.  A sidecar carries a
        paper's identity — its DOI, arXiv id, first-ingested date,
        cached text — and rewriting it is a mutation of the owner's data
        just as much as moving the file is, yet every writer here bypassed
        the log.  A bulk pass over 300 sidecars was therefore
        irreversible.  Pass an open transaction and the previous field
        values are recorded, so undo restores them.
        """
        if undo_log is not None:
            path_now = sidecar_path(pdf_path)
            existed = path_now.exists()
            readable = True
            if existed:
                try:
                    json.loads(path_now.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    readable = False
            if existed and not readable:
                # An UNREADABLE sidecar is not an empty one.  load()
                # collapses both into a blank PaperIdentity, so recording
                # here would capture "" as the previous value of every
                # field and undo would then write those blanks over the
                # paper's real identity.  Refuse, loudly.
                logger.warning(
                    "refusing to record a sidecar edit for %s: the existing "
                    "sidecar is unreadable, so the previous values are "
                    "unknown", pdf_path.name)
            else:
                try:
                    # UNCACHED on purpose.  Inside sidecar_read_cache()
                    # load() hands back the very object being mutated, so
                    # `before` IS `self`, every diff is empty and recording
                    # is silently disabled — measured: has_operations()
                    # stayed False for a real field change.
                    before = PaperIdentity._load_uncached(pdf_path)
                    old = {k: v for k, v in asdict(before).items()
                           if not k.startswith("_")}
                    new = {k: v for k, v in asdict(self).items()
                           if not k.startswith("_")}
                    changes = {k: [old.get(k), new.get(k)]
                               for k in set(old) | set(new)
                               if old.get(k) != new.get(k)}
                    if changes:
                        undo_log.record_sidecar_edit(pdf_path, changes)
                except RuntimeError:
                    # "No active transaction" is a PROGRAMMER error, not a
                    # runtime hiccup.  Swallowing it meant a caller that
                    # forgot begin_transaction() recorded nothing, warned
                    # nothing and returned success.
                    raise
                except Exception as exc:            # never block the write
                    logger.warning("could not record sidecar edit for %s: %s",
                                   pdf_path, exc)

        if recompute_hash and pdf_path.exists():
            self.content_sha256 = compute_content_hash(pdf_path)
        if not self.original_filename:
            self.original_filename = pdf_path.name

        path = sidecar_path(pdf_path)
        # Live-trial finding: when ``sidecar_path`` falls back to
        # ``.sidecars/<hash>.meta.json``, the parent directory doesn't
        # exist yet.  ``mkdir(parents=True)`` is safe either way --
        # for the natural path it's a no-op since the PDF's parent
        # already exists.
        path.parent.mkdir(parents=True, exist_ok=True)
        # ``asdict`` includes the underscore-prefixed sentinel; strip
        # it so the on-disk schema is clean.
        payload = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        payload["schema_version"] = SCHEMA_VERSION  # enforce current
        # Audit-10: atomic + concurrency-safe write.  The cockpit,
        # watcher and weekly job can all save the SAME sidecar on a
        # Dropbox tree; a fixed ``.tmp`` name let two writers clobber
        # each other's temp.  ``atomic_write_text`` uses a unique temp
        # and cleans up on failure (no turds).
        from core.io import atomic_write_text
        atomic_write_text(
            path,
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        self._is_new = False
        return path

    # -----------------------------------------------------------------
    # Drift detection
    # -----------------------------------------------------------------

    def drift_check(self, pdf_path: Path) -> Optional[str]:
        """Compare stored hash to current file content.

        Returns ``None`` if the file matches or if we have no recorded
        hash.  Returns a short description of the drift otherwise.

        Drift typically means:
        * the user re-OCRed or re-saved the PDF (benign — caller may
          want to refresh the hash);
        * the sidecar got separated from its PDF and reattached to a
          different one (a real problem; caller should investigate);
        * Dropbox restored an older revision (recoverable via Dropbox
          version history).
        """
        if not self.content_sha256:
            return None
        if not pdf_path.exists():
            return f"PDF missing at {pdf_path}"
        current = compute_content_hash(pdf_path)
        if not current:
            return None
        if current != self.content_sha256:
            return (
                f"content drift: stored={self.content_sha256[:12]} "
                f"current={current[:12]}"
            )
        return None

    # -----------------------------------------------------------------
    # State-machine helpers
    # -----------------------------------------------------------------

    def record_publication_check(
        self,
        *,
        hit: bool,
        source: str,
        confidence: float = 0.0,
        details: Optional[dict] = None,
    ) -> None:
        """Append a publication-check result and advance the counter.

        The ``recheck_count`` advances on misses only — a hit ends the
        state machine because the next step is upgrade_to_published.
        """
        entry = {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": source,
            "hit": bool(hit),
            "confidence": float(confidence),
        }
        if details:
            entry["details"] = details
        self.publication_checks.append(entry)
        self.last_check_date = entry["date"]
        if not hit:
            self.recheck_count += 1

    def should_skip_publication_check(self, *, max_rechecks: int = 3) -> bool:
        """Whether the weekly task should skip this paper.

        Returns True if we've already marked the paper permanently
        unpublished, or if we've burned through the recheck budget.
        Borderline policy: hitting the budget *flags* the paper but
        doesn't auto-set ``permanently_unpublished`` — that decision
        belongs to a higher layer (the weekly auto-apply or the user).
        """
        if self.permanently_unpublished:
            return True
        return self.recheck_count >= max_rechecks


# ---------------------------------------------------------------------------
# Filesystem helpers — keep sidecar attached to its PDF across moves
# ---------------------------------------------------------------------------

def move_with_sidecar(
    source: Path,
    destination: Path,
    *,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> None:
    """Explicit PDF+sidecar move.

    Since the ``undo_log`` v2 helpers (``logged_move`` / ``logged_rename``)
    became sidecar-aware automatically, this function is a thin alias
    kept for callers who want the intent in the call site (e.g. tests
    that assert "I moved the pair as one").
    """
    from processing.undo_log import logged_move
    logged_move(source, destination, undo_log=undo_log)


def rename_with_sidecar(
    old_path: Path,
    new_path: Path,
    *,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> None:
    """Explicit PDF+sidecar rename — thin alias for ``logged_rename``."""
    from processing.undo_log import logged_rename
    logged_rename(old_path, new_path, undo_log=undo_log)


def repath_topic_copies(
    sidecar_pdf_path: Path,
    *,
    old_path: Path,
    new_path: Path,
    undo_log=None,  # type: ignore[no-untyped-def]
) -> int:
    """Rename topic-folder hardlinks to match the new canonical basename.

    When the canonical PDF moves from ``old_path`` to ``new_path``,
    any topic-folder copies recorded in ``copy_locations`` retain
    their original directory entries -- POSIX hardlinks are
    independent of the canonical's pathname.  Their inode is shared
    but their NAMES diverge from the canonical, so users browsing
    ``07a - BSDEs/`` would see the paper under the OLD name forever.

    This helper finds every non-canonical entry in copy_locations
    whose basename matches the OLD canonical, and renames it to the
    new basename in-place.  The parent directory is preserved (the
    topic copy stays in its 07x folder).

    Returns the number of topic copies actually renamed.  Failures
    on individual copies are logged but don't abort the rest.
    """
    if not sidecar_path(sidecar_pdf_path).exists():
        return 0
    identity = PaperIdentity.load(sidecar_pdf_path)
    if identity.is_new() or not identity.copy_locations:
        return 0
    old_name = old_path.name
    new_name = new_path.name
    if old_name == new_name:
        return 0  # parent changed, basename didn't -- nothing to rename
    renamed = 0
    new_locations: list[str] = []
    new_path_str = str(new_path)
    for loc in identity.copy_locations:
        p = Path(loc)
        # Canonical entry is updated separately by repath_copy_locations.
        if p == new_path or loc == new_path_str:
            new_locations.append(loc)
            continue
        # Only consider locations whose basename matches the OLD
        # canonical -- anything else is something we didn't create.
        if p.name != old_name:
            new_locations.append(loc)
            continue
        new_loc = p.parent / new_name
        if new_loc.exists():
            # Collision: keep the old entry, log a warning.  The user
            # will see two distinct entries (which is honest -- there
            # ARE two distinct files at that point).
            logger.warning(
                "topic-copy rename would collide at %s; leaving %s",
                new_loc, p,
            )
            new_locations.append(loc)
            continue
        try:
            if undo_log is not None:
                undo_log.record_rename(p, new_loc)
            p.rename(new_loc)
            new_locations.append(str(new_loc))
            renamed += 1
        except OSError as exc:
            logger.warning("could not rename topic copy %s: %s", p, exc)
            new_locations.append(loc)
    if renamed > 0:
        identity.copy_locations = new_locations
        identity.save(sidecar_pdf_path, recompute_hash=False)
    return renamed


def find_canonical_for_link(link_path: Path) -> Optional[Path]:
    """Reverse-lookup the canonical sidecar that lists ``link_path``.

    The topic router (and any future copier) registers each
    derivative location in the canonical's ``copy_locations`` list.
    When a link gets deleted -- via undo, manual removal, or
    ``unlink_topic`` -- we need to find the canonical to clean up
    that stale entry.

    Walks every sidecar under ``link_path``'s top-level parent until
    one matches.  Returns ``None`` if no sidecar references the
    link (likely because the link was created without a sidecar
    update -- e.g. ``classify_and_link`` on a sidecar-less PDF).
    """
    # Heuristic: search from the deepest reasonable ancestor.  We
    # don't know the canonical's location a priori, but it's almost
    # always a sibling in the same library tree.  Walk up to the
    # filesystem root and try each ancestor as the search root.
    link_str = str(link_path)
    parent = link_path.parent
    while parent != parent.parent:
        try:
            for pdf in iter_pdfs(parent):
                if pdf == link_path:
                    continue
                identity = PaperIdentity.load(pdf)
                if identity.is_new():
                    continue
                if link_str in identity.copy_locations:
                    return pdf
        except (OSError, PermissionError):
            pass
        # Stop after walking 4 levels up -- avoids reading the
        # entire library when the link's canonical lives elsewhere.
        if len(parent.parts) <= len(link_path.parts) - 4:
            break
        parent = parent.parent
    return None


def remove_dead_location(
    canonical_pdf: Path,
    dead_location: Path,
    *,
    also_remove_topic_code: Optional[str] = None,
) -> bool:
    """Drop ``dead_location`` from the canonical's ``copy_locations``.

    Used after a topic-link is deleted (e.g. via undo) so the
    sidecar doesn't keep advertising a path that no longer exists.
    Optionally also removes ``also_remove_topic_code`` from
    ``topic_codes`` so the bookkeeping stays consistent.

    Returns True if the sidecar was modified.
    """
    identity = PaperIdentity.load(canonical_pdf)
    if identity.is_new():
        return False
    dead = str(dead_location)
    if dead not in identity.copy_locations and (
        also_remove_topic_code is None
        or also_remove_topic_code not in identity.topic_codes
    ):
        return False
    identity.copy_locations = [
        loc for loc in identity.copy_locations if loc != dead
    ]
    if also_remove_topic_code and also_remove_topic_code in identity.topic_codes:
        identity.topic_codes = [
            c for c in identity.topic_codes if c != also_remove_topic_code
        ]
    identity.save(canonical_pdf, recompute_hash=False)
    return True


def repath_copy_locations(
    sidecar_pdf_path: Path,
    *,
    old_path: Path,
    new_path: Path,
) -> bool:
    """Swap ``old_path`` → ``new_path`` inside the sidecar's ``copy_locations``.

    Called after every PDF move so the sidecar's recorded copy
    locations stay in sync with reality.  Returns True if the sidecar
    actually changed (or False if there was nothing to fix up).

    The caller passes ``sidecar_pdf_path`` (where the sidecar lives
    NOW, post-move).  We swap ``str(old_path)`` for ``str(new_path)``
    inside copy_locations and re-save without recomputing the hash.
    """
    if not sidecar_path(sidecar_pdf_path).exists():
        return False
    identity = load_sidecar(sidecar_pdf_path)
    if identity.is_new():
        return False
    old_str = str(old_path)
    new_str = str(new_path)
    if old_str not in identity.copy_locations and new_str in identity.copy_locations:
        return False
    changed = False
    out: list[str] = []
    seen: set[str] = set()
    for loc in identity.copy_locations:
        repl = new_str if loc == old_str else loc
        if repl in seen:
            continue  # dedup
        out.append(repl)
        seen.add(repl)
        if repl != loc:
            changed = True
    if new_str not in seen:
        out.append(new_str)
        changed = True
    if not changed:
        return False
    identity.copy_locations = out
    identity.save(sidecar_pdf_path, recompute_hash=False)
    return True


# Module-level alias to keep call sites readable: ``load_sidecar(pdf)``
# is clearer than ``PaperIdentity.load(pdf)`` from outside.
load_sidecar = PaperIdentity.load


# ---------------------------------------------------------------------------
# Backfill — best-effort sidecar construction for legacy PDFs
# ---------------------------------------------------------------------------

def backfill_sidecar(
    pdf_path: Path,
    *,
    overwrite: bool = False,
) -> bool:
    """Create a minimal sidecar for a PDF that doesn't have one yet.

    Used during one-shot migration of an existing library.  Only writes
    the fields we can determine cheaply from the file itself:
    ``content_sha256``, ``original_filename``, ``first_ingested_at``
    (best-effort: stat().st_birthtime, falling back to st_mtime).

    External identifiers (DOI / arXiv) are left blank — they require a
    network round-trip and belong to a separate enrichment pass.

    Returns True if a sidecar was written, False if one already existed
    and ``overwrite`` was False.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    sc = sidecar_path(pdf_path)
    if sc.exists() and not overwrite:
        return False

    identity = PaperIdentity()
    identity.content_sha256 = compute_content_hash(pdf_path)
    identity.original_filename = pdf_path.name

    # Filing date: prefer creation time when available (Apple HFS+/APFS),
    # otherwise fall back to mtime.  Filing date matters for the aging
    # state machine.
    stat = pdf_path.stat()
    when = getattr(stat, "st_birthtime", None) or stat.st_mtime
    identity.first_ingested_at = datetime.fromtimestamp(
        when, tz=timezone.utc
    ).isoformat(timespec="seconds")

    identity.save(pdf_path, recompute_hash=False)
    return True


def list_hash_collisions(root: Path) -> dict[str, list[str]]:
    """Return ``{content_sha256: [paths, ...]}`` for hashes shared by 2+ PDFs.

    Audit-7 #8 documented: ``compute_content_hash`` hashes only the
    first 1MB, which means two distinct papers from template-heavy
    publishers (Elsevier, Springer ...) can legitimately collide.
    Drift detection won't tell them apart.  This helper lets the
    cockpit surface "two papers in your library have the same
    content fingerprint" so the user can verify they aren't
    accidental duplicates.

    Only hashes shared by at least two PDFs are returned.  Empty
    string hashes (unreadable sidecars) are skipped to avoid a
    massive false-positive bucket on a library with many
    sidecar-less PDFs.
    """
    buckets: dict[str, list[str]] = {}
    if not root.exists():
        return {}
    for pdf in iter_pdfs(root):
        identity = PaperIdentity.load(pdf)
        if identity.is_new() or not identity.content_sha256:
            continue
        buckets.setdefault(identity.content_sha256, []).append(str(pdf))
    return {h: paths for h, paths in buckets.items() if len(paths) > 1}


def verify_all_sidecars(root: Path, *, limit: Optional[int] = None) -> dict:
    """Walk the library and report sidecar drift for every PDF.

    Returns::

        {
          "scanned": N,
          "drifted": [{"pdf": str, "reason": str}, ...],
          "missing_sidecar": [str, ...],
          "errors": [str, ...],
        }

    A "drifted" sidecar means the stored content hash no longer
    matches the first 1MB of the PDF on disk -- most commonly the
    user re-OCRed or re-saved the file (benign; refresh the hash),
    but it could also mean Dropbox restored an older revision or two
    files swapped sidecars somehow.

    Best-effort: per-PDF failures land in ``errors`` rather than
    aborting the walk.  Safe to call on the full library; reads
    sidecars and 1MB of each PDF, so on a 28k-paper library
    expect ~85s of I/O.
    """
    summary: dict = {
        "scanned": 0,
        "drifted": [],
        "missing_sidecar": [],
        "errors": [],
    }
    for pdf in iter_pdfs(root):
        summary["scanned"] += 1
        try:
            sc = sidecar_path(pdf)
            if not sc.exists():
                summary["missing_sidecar"].append(str(pdf))
                continue
            identity = PaperIdentity.load(pdf)
            drift = identity.drift_check(pdf)
            if drift is not None:
                summary["drifted"].append({"pdf": str(pdf), "reason": drift})
        except Exception as exc:
            summary["errors"].append(f"{pdf}: {exc}")
        if limit is not None and summary["scanned"] >= limit:
            break
    return summary


def backfill_directory(
    root: Path,
    *,
    limit: Optional[int] = None,
    overwrite: bool = False,
    verbose: bool = False,
) -> dict:
    """Walk a library tree and backfill sidecars for every PDF.

    Returns a summary dict::

        {"scanned": N, "written": M, "skipped": K, "errors": E}
    """
    summary = {"scanned": 0, "written": 0, "skipped": 0, "errors": 0}
    for pdf in iter_pdfs(root):
        summary["scanned"] += 1
        try:
            if backfill_sidecar(pdf, overwrite=overwrite):
                summary["written"] += 1
                if verbose:
                    print(f"  wrote sidecar for {pdf}")
            else:
                summary["skipped"] += 1
        except (OSError, ValueError) as exc:
            summary["errors"] += 1
            logger.warning("backfill failed for %s: %s", pdf, exc)
        if limit is not None and summary["scanned"] >= limit:
            break
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Paper-identity sidecar utilities",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # backfill
    bf = sub.add_parser(
        "backfill",
        help="Create sidecars for every PDF under a directory",
    )
    bf.add_argument("root", type=Path, help="Library root to scan")
    bf.add_argument("--limit", type=int, default=None)
    bf.add_argument("--overwrite", action="store_true")
    bf.add_argument("--verbose", action="store_true")

    # show
    sh = sub.add_parser("show", help="Print the sidecar for a PDF")
    sh.add_argument("pdf", type=Path)

    # drift
    dr = sub.add_parser("drift", help="Check sidecar drift against current file")
    dr.add_argument("pdf", type=Path)

    args = parser.parse_args(argv)

    if args.command == "backfill":
        if not args.root.exists():
            parser.error(f"root does not exist: {args.root}")
        s = backfill_directory(
            args.root,
            limit=args.limit,
            overwrite=args.overwrite,
            verbose=args.verbose,
        )
        print(
            f"Scanned {s['scanned']} PDFs: wrote {s['written']}, "
            f"skipped {s['skipped']}, errors {s['errors']}"
        )
    elif args.command == "show":
        ident = PaperIdentity.load(args.pdf)
        if ident.is_new():
            print(f"No sidecar at {sidecar_path(args.pdf)}")
        else:
            print(json.dumps(asdict(ident), indent=2, default=str, sort_keys=True))
    elif args.command == "drift":
        ident = PaperIdentity.load(args.pdf)
        if ident.is_new():
            print(f"No sidecar at {sidecar_path(args.pdf)}; nothing to check")
            return
        drift = ident.drift_check(args.pdf)
        if drift is None:
            print("OK — content matches stored hash")
        else:
            print(f"DRIFT: {drift}")


if __name__ == "__main__":
    main()
