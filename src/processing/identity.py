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


def sidecar_path(pdf_path: Path) -> Path:
    """Return the sidecar path for ``pdf_path``.

    Format: ``<pdf with .pdf swapped for .meta.json>``.  Living next to
    the PDF (rather than in a central index) means moves via the
    filesystem keep the pair together.
    """
    return pdf_path.with_suffix(".meta.json")


# Case-insensitive PDF glob.  ``Path.rglob("*.pdf")`` is
# case-sensitive on Linux and case-insensitive on macOS HFS+/APFS by
# default, but APFS volumes can be configured case-sensitive.  Using a
# character-class pattern matches both ``.pdf`` and ``.PDF`` everywhere
# without depending on volume settings.
PDF_GLOB = "*.[Pp][Dd][Ff]"


def iter_pdfs(root: Path):
    """Yield every PDF under ``root`` (case-insensitive suffix match).

    Skips files under any ``.trash`` directory so library scans don't
    fold trash entries back into live workflows.  Callers that *want*
    trash should iterate with ``root.rglob(PDF_GLOB)`` directly.
    """
    if not root.exists():
        return
    for pdf in root.rglob(PDF_GLOB):
        if ".trash" in pdf.parts:
            continue
        yield pdf


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
        """
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

    def save(self, pdf_path: Path, *, recompute_hash: bool = True) -> Path:
        """Atomically write the sidecar next to ``pdf_path``.

        Writes to ``<sidecar>.tmp`` then ``os.replace`` — an interrupted
        write leaves the previous sidecar intact rather than truncating
        it to zero bytes (a real failure mode under Dropbox sync).

        ``recompute_hash`` controls whether ``content_sha256`` is
        refreshed from the file on disk.  Pass ``False`` when you're
        saving after a pure metadata edit and want to preserve the
        existing hash without re-reading the PDF.
        """
        if recompute_hash and pdf_path.exists():
            self.content_sha256 = compute_content_hash(pdf_path)
        if not self.original_filename:
            self.original_filename = pdf_path.name

        path = sidecar_path(pdf_path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        # ``asdict`` includes the underscore-prefixed sentinel; strip
        # it so the on-disk schema is clean.
        payload = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        payload["schema_version"] = SCHEMA_VERSION  # enforce current
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp, path)
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
