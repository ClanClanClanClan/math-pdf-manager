#!/usr/bin/env python3
"""Transaction log for reversible file operations.

Every move/rename/copy operation is recorded in a JSON log file so it
can be undone with ``python -m processing.undo_log undo``.

Usage::

    # Undo the last batch of operations
    python -m processing.undo_log undo

    # Undo a specific transaction
    python -m processing.undo_log undo --transaction abc123

    # List all transactions
    python -m processing.undo_log list

    # Show details of a transaction
    python -m processing.undo_log show abc123
"""
from __future__ import annotations


import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default log location.
#
# Live-trial fix: this used to resolve to ``Scripts/.operation_log``
# (inside the code repo), so the undo history did NOT travel with the
# Dropbox library to another machine and a fresh clone of the repo
# started with an empty log.  Now it lives at
# ``<library>/.operation_log`` so it syncs alongside the papers and
# the sidecar mirror, and every process (cockpit, CLI, watcher,
# weekly plist) shares one log.  Tests pass an explicit ``log_dir``
# so they are unaffected.
def _default_log_dir() -> Path:
    try:
        from core.config_paths import get_library_root
        root = get_library_root()
        if root and root.exists():
            return root / ".operation_log"
    except Exception:
        pass
    # Fallback (library unavailable, e.g. partial install): keep the
    # historical repo-local location so nothing crashes.
    return Path(__file__).resolve().parent.parent.parent / ".operation_log"


LOG_DIR = _default_log_dir()


def _restore(dst: Path, src: Path, verb: str) -> dict:
    """Put ``dst`` back at ``src``, refusing to overwrite an occupant.

    ONE implementation for every restore branch, on purpose.  The guard
    was first added to the ``move`` branch only, while the ``rename``
    branch kept a bare ``shutil.move`` — and renames are 14,697 of the
    15,314 operations in the real log, so 96% of the owner's undo
    history was still able to destroy whatever file now sits at the
    original name.  A guard that has to be remembered twice is a guard
    that will be forgotten once.
    """
    blocker = restore_blocker(dst, src)
    if blocker:
        return {"action": blocker, "ok": False}
    src.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dst), str(src))
    return {"action": f"{verb}: {dst.name} → {src.name}", "ok": True}


def restore_blocker(dst: Path, src: Path) -> str:
    """Why putting ``dst`` back at ``src`` would fail, or "" if it would work.

    Split out of _restore so the DRY RUN can ask the same question.  It
    could not before: the dry-run branches simply printed "WOULD MOVE
    BACK" for every operation without touching the filesystem, so the
    preview of the oldest transaction showed 15,588 clean rows while the
    real thing fails on 10 of them.  A preview that cannot fail is not a
    preview.
    """
    if not dst.exists():
        return f"SKIP: file gone: {dst}"
    if src.exists() and not _is_same_file(src, dst):
        return (f"CANNOT UNDO: {src} is occupied by a different file; "
                f"refusing to overwrite it")
    return ""


class UndoLog:
    """Records file operations and provides undo functionality."""

    def __init__(self, log_dir: Optional[Path] = None):
        # Resolved HERE, not bound to the module-level LOG_DIR at
        # definition time.  The old signature froze the real library's
        # log directory at import, so pointing MATH_LIBRARY somewhere
        # else afterwards had no effect — which is how a test run wrote
        # 342 transactions into the owner's real undo history, burying
        # the 15 genuine ones.
        self.log_dir = Path(log_dir) if log_dir is not None else _default_log_dir()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_tx: Optional[dict] = None
        self._tx_id: Optional[str] = None

    def begin_transaction(self, description: str) -> str:
        """Start a new transaction. Returns the transaction ID.

        Audit-10: the id must be unique even when two processes (the
        watcher, the weekly job, the cockpit) begin a transaction in
        the same millisecond with the same description.  The old id was
        ``md5(time-description)`` which collides under exactly that
        case, and the second committer would clobber the first's
        ``<id>.json`` — silently destroying an undo record.  Mixing in
        the pid and a uuid4 makes a collision astronomically unlikely.
        """
        self._tx_id = hashlib.md5(
            f"{time.time()}-{os.getpid()}-{uuid.uuid4().hex}-{description}".encode()
        ).hexdigest()[:12]
        self._current_tx = {
            "id": self._tx_id,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operations": [],
            "undone": False,
        }
        return self._tx_id

    def _append(self, op: dict) -> None:
        """Record one operation, in memory AND on disk immediately.

        Operations used to accumulate in memory until ``commit()``, which
        was the only writer.  A SIGKILL, an OOM or a power cut mid-batch
        therefore left every file already moved and the undo record
        EMPTY — and the exposure window was the whole batch: the largest
        real transaction holds 8,514 operations.  The class docstring
        claimed crash-safety; it was not true.

        Now each operation is appended to a write-ahead journal as it
        happens, so an interrupted batch is still undoable up to the last
        completed operation.  ``commit()`` folds the journal into the
        final record.  Best-effort: a journal write that fails must not
        abort the caller's work, because a file already moved with no
        record is strictly worse than a slow one.
        """
        self._current_tx["operations"].append(op)
        try:
            self._journal_path().open("a", encoding="utf-8").write(
                json.dumps(op, ensure_ascii=False) + "\n")
        except OSError as exc:                      # pragma: no cover
            logger.warning("could not write undo journal: %s", exc)

    def _journal_path(self) -> Path:
        return self.log_dir / f"{self._tx_id}.journal.jsonl"

    def record_move(self, source: Path, destination: Path) -> None:
        """Record a file move/rename operation."""
        if self._current_tx is None:
            raise RuntimeError("No active transaction — call begin_transaction() first")
        self._append({
            "type": "move",
            "source": str(source),
            "destination": str(destination),
        })

    def record_copy(self, source: Path, destination: Path) -> None:
        """Record a file copy operation."""
        if self._current_tx is None:
            raise RuntimeError("No active transaction — call begin_transaction() first")
        self._append({
            "type": "copy",
            "source": str(source),
            "destination": str(destination),
        })

    def record_rename(self, old_path: Path, new_path: Path) -> None:
        """Record a file rename operation."""
        if self._current_tx is None:
            raise RuntimeError("No active transaction — call begin_transaction() first")
        self._append({
            "type": "rename",
            "source": str(old_path),
            "destination": str(new_path),
        })

    def record_sidecar_edit(self, pdf_path: Path, changes: dict) -> None:
        """Record a reversible edit to a paper's sidecar fields.

        Audit-11b: some actions change sidecar *fields* rather than
        moving files — accepting a topic suggestion (clears the
        suggestion, appends a topic code) and rejecting one (clears the
        suggestion).  Without recording these, undoing the action left
        the sidecar inconsistent with the file's location, so the paper
        neither reappeared as a suggestion nor matched its folder.

        ``changes`` maps ``field -> [old_value, new_value]``.  Undo
        restores each ``old_value``.  Record this AFTER any file move in
        the same transaction so that, on undo (reverse order), the field
        is restored while the file is still at the post-move location.
        """
        if self._current_tx is None:
            raise RuntimeError("No active transaction — call begin_transaction() first")
        self._append({
            "type": "sidecar_edit",
            "path": str(pdf_path),
            "changes": changes,
        })

    def has_operations(self) -> bool:
        """True if the current transaction has recorded at least one operation.

        Lets batch callers decide between ``commit()`` (something to persist and
        reverse) and ``discard()`` (a begun-but-empty tx) without reaching into
        ``_current_tx``.  Returns False when there is no open transaction.
        """
        return bool(self._current_tx and self._current_tx.get("operations"))

    def discard(self) -> None:
        """Drop the current (in-memory) transaction without writing anything.

        Use instead of ``commit()`` when a transaction turned out to do no
        work (e.g. the watcher began an ingest tx but the arrival was a
        duplicate and nothing moved).  Committing such a tx would litter
        the log and the cockpit Activity tab with a 0-op entry that has
        live Undo buttons.  Nothing is on disk until ``commit()``, so
        discarding is just clearing the in-memory state.

        REFUSES to discard work that actually happened.  Several callers
        do ``except: log.discard()``, which threw away the record of
        files already moved — the operations were real, only the record
        vanished.  A transaction with operations is committed instead,
        marked as failed, so the work stays reversible.
        """
        if self.has_operations():
            logger.warning(
                "discard() called on a transaction with %d recorded "
                "operation(s); committing it instead so the work stays "
                "undoable", len(self._current_tx["operations"]))
            self._current_tx["description"] += " [INCOMPLETE: discarded after partial work]"
            self.commit()
            return
        jp = self._journal_path() if self._tx_id else None
        self._current_tx = None
        self._tx_id = None
        if jp is not None:
            jp.unlink(missing_ok=True)

    def commit(self) -> Path:
        """Commit the current transaction to disk. Returns the log file path."""
        if self._current_tx is None:
            raise RuntimeError("No active transaction to commit")

        log_file = self.log_dir / f"{self._tx_id}.json"
        # Atomic: the log lives on a Dropbox-synced path, and a raw
        # write_text of a 4.2 MB record can be torn by a crash or by sync
        # picking it up mid-write.  A torn record is listed as undoable
        # and raises JSONDecodeError when clicked.  core.io already had
        # this helper; this file simply never used it.
        from core.io import atomic_write_text
        atomic_write_text(
            log_file, json.dumps(self._current_tx, indent=2, ensure_ascii=False))

        # Also append to the master index
        index_file = self.log_dir / "index.jsonl"
        with open(index_file, "a") as f:
            summary = {
                "id": self._tx_id,
                "timestamp": self._current_tx["timestamp"],
                "description": self._current_tx["description"],
                "operations_count": len(self._current_tx["operations"]),
            }
            f.write(json.dumps(summary) + "\n")

        # The journal has served its purpose now that the full record is
        # on disk.
        self._journal_path().unlink(missing_ok=True)
        self._current_tx = None
        self._tx_id = None
        return log_file

    def recover_journals(self) -> list[str]:
        """Turn write-ahead journals from crashed runs into real records.

        A journal that still exists has no committed ``<id>.json``, which
        means the process died between the first operation and the
        commit.  The operations in it DID happen, so they must become an
        undoable transaction rather than being discarded — that is the
        whole point of writing them ahead.

        Returns the transaction ids recovered.  Safe to call at startup.
        """
        recovered: list[str] = []
        for jp in sorted(self.log_dir.glob("*.journal.jsonl")):
            tx_id = jp.name.split(".journal")[0]
            if (self.log_dir / f"{tx_id}.json").exists():
                jp.unlink(missing_ok=True)          # committed; stale journal
                continue
            ops = []
            try:
                for line in jp.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ops.append(json.loads(line))
                    except ValueError:
                        # A torn final line is expected after a hard kill.
                        logger.warning("undo journal %s: dropping torn line", jp.name)
            except OSError:                         # pragma: no cover
                continue
            if not ops:
                jp.unlink(missing_ok=True)
                continue
            tx = {
                "id": tx_id,
                "description": f"RECOVERED from an interrupted run ({len(ops)} ops)",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operations": ops,
                "undone": False,
            }
            from core.io import atomic_write_text
            atomic_write_text(self.log_dir / f"{tx_id}.json",
                              json.dumps(tx, indent=2, ensure_ascii=False))
            with open(self.log_dir / "index.jsonl", "a") as f:
                f.write(json.dumps({
                    "id": tx_id, "timestamp": tx["timestamp"],
                    "description": tx["description"],
                    "operations_count": len(ops)}) + "\n")
            jp.unlink(missing_ok=True)
            recovered.append(tx_id)
        return recovered

    def undo_transaction(
        self, tx_id: str, *, dry_run: bool = False
    ) -> list[dict]:
        """Undo all operations in a transaction (in reverse order).

        Returns a list of undo actions taken.
        """
        log_file = self.log_dir / f"{tx_id}.json"
        if not log_file.exists():
            raise FileNotFoundError(f"Transaction not found: {tx_id}")

        tx = json.loads(log_file.read_text())
        if tx.get("undone"):
            raise ValueError(f"Transaction {tx_id} has already been undone")

        # Refuse to "restore" from special device files. Historical bug:
        # callers used to record deletions as moves to /dev/null, which made
        # undo try to move the device file and destroy the source.
        SPECIAL_DEVICES = {"/dev/null", "/dev/zero", "/dev/random", "/dev/urandom"}

        results = []
        # Undo in reverse order
        for op in reversed(tx["operations"]):
            # Sidecar-field edits (audit-11b) carry their own shape
            # (path + changes), not source/destination.  Handle first.
            if op["type"] == "sidecar_edit":
                pdf = Path(op["path"])
                changes = op.get("changes", {})
                if dry_run:
                    results.append({
                        "action": f"WOULD RESTORE sidecar fields {list(changes)} on {pdf.name}",
                        "ok": True,
                    })
                    continue
                try:
                    from processing.identity import PaperIdentity
                    ident = PaperIdentity.load(pdf)
                    if ident.is_new():
                        results.append({"action": f"SKIP: no sidecar to restore: {pdf}", "ok": False})
                        continue
                    for field, (old_val, _new_val) in changes.items():
                        setattr(ident, field, old_val)
                    ident.save(pdf, recompute_hash=False)
                    results.append({
                        "action": f"RESTORED sidecar fields {list(changes)} on {pdf.name}",
                        "ok": True,
                    })
                except Exception as exc:  # pragma: no cover -- defensive
                    results.append({"action": f"FAILED to restore sidecar on {pdf}: {exc}", "ok": False})
                continue

            src = Path(op["source"])
            dst = Path(op["destination"])

            if op["type"] == "move":
                # Undo move: move destination back to source
                if str(dst) in SPECIAL_DEVICES:
                    results.append({
                        "action": f"CANNOT UNDO: file was deleted (recorded as move to {dst}); "
                                  f"source path {src} is unrecoverable from this log",
                        "ok": False,
                    })
                    continue
                if dry_run:
                    blocker = restore_blocker(dst, src)
                    results.append(
                        {"action": blocker or f"WOULD MOVE BACK: {dst.name} → {src}",
                         "ok": not blocker})
                else:
                    results.append(_restore(dst, src, "MOVED BACK"))

            elif op["type"] == "copy":
                # Undo copy: remove the copy
                if dry_run:
                    gone = not dst.exists()
                    results.append(
                        {"action": (f"SKIP: copy already gone: {dst}" if gone
                                    else f"WOULD DELETE COPY: {dst}"),
                         "ok": not gone})
                else:
                    # DO NOT UNLINK. This is the only hard delete of a
                    # library PDF in src/, and it has already cost a paper:
                    # transaction 9b9d5b2f584e recorded
                    # "move ... Abraham, R., Delmas, J.-F., Weibel, J. -
                    # Probability-graphons ... -> /dev/null". That file is
                    # gone from 03 - Working papers/A/2023 and from its
                    # intended home in 01 - Published papers/Z; the only
                    # reason the paper still exists is an accidental copy
                    # under 07e - Optimal control on networks.
                    #
                    # Undoing a copy is a deletion, and this project does not
                    # hard-delete. It retires.
                    #
                    # It also REFUSES when the original is gone. Undoing a
                    # copy is only safe if the thing it was copied from
                    # survives; otherwise "remove the duplicate" removes the
                    # last remaining version.
                    if dst.exists() and not src.exists():
                        results.append(
                            {"action": (f"REFUSED: the original is gone, so this "
                                        f"copy is the only version left: {dst}"),
                             "ok": False})
                    elif dst.exists():
                        retired = _retire_to_trash(dst, "undone_copies")
                        results.append({"action": f"RETIRED COPY: {dst} → {retired}",
                                        "ok": True})
                        # When the undone copy was a topic-router
                        # hardlink, the canonical's sidecar still
                        # advertises the now-dead path in
                        # ``copy_locations`` (and probably has the
                        # topic code in ``topic_codes``).  Walk back to
                        # the canonical (the original ``src`` of the
                        # copy op) and clean up so the sidecar matches
                        # filesystem reality.  Best-effort: a missing
                        # canonical sidecar is logged and skipped.
                        try:
                            from processing.identity import remove_dead_location
                            if src.exists():
                                # Topic code is the prefix of the
                                # destination's parent (e.g.
                                # "07a - BSDEs" -> "07a").
                                parent_name = dst.parent.name
                                topic_code = (
                                    parent_name.split(" ", 1)[0]
                                    if " " in parent_name
                                    else None
                                )
                                remove_dead_location(
                                    src, dst,
                                    also_remove_topic_code=topic_code,
                                )
                        except Exception as exc:  # pragma: no cover
                            logger.warning(
                                "could not clean dead location %s "
                                "from %s sidecar: %s", dst, src, exc,
                            )
                    else:
                        results.append({"action": f"SKIP: copy already gone: {dst}", "ok": False})

            elif op["type"] == "rename":
                # Undo rename: rename back
                if dry_run:
                    blocker = restore_blocker(dst, src)
                    results.append(
                        {"action": blocker or
                         f"WOULD RENAME BACK: {dst.name} → {src.name}",
                         "ok": not blocker})
                else:
                    results.append(_restore(dst, src, "RENAMED BACK"))

        # Mark transaction as undone — but ONLY if everything came back.
        #
        # It used to set undone=True unconditionally, and line 319 then
        # refuses to touch an undone transaction ever again. So a single
        # SKIP (destination gone, source occupied, undone out of order)
        # burned the whole record: the remaining operations became
        # permanently unreversible. 122 operations across 4 real
        # transactions are already stranded that way, 89 of them among
        # the 6,180 author renames.
        #
        # A partial undo now stays RETRYABLE, and remembers which
        # operations already came back so a retry is not a double-undo.
        if not dry_run:
            failed = [r for r in results
                      if str(r.get("action", "")).startswith(("SKIP", "CANNOT"))]
            tx["undone"] = not failed
            tx["undone_at"] = datetime.now(timezone.utc).isoformat()
            if failed:
                tx["partial_undo"] = {
                    "at": tx["undone_at"],
                    "reversed": len(results) - len(failed),
                    "not_reversed": [str(r.get("action")) for r in failed],
                }
                logger.warning(
                    "transaction %s only partially undone (%d of %d); it "
                    "stays retryable", tx_id, len(results) - len(failed),
                    len(results))
            from core.io import atomic_write_text
            atomic_write_text(log_file,
                              json.dumps(tx, indent=2, ensure_ascii=False))

        return results

    def list_transactions(self) -> list[dict]:
        """List all transactions.

        The ``index.jsonl`` is a fast-path summary cache.  Audit-10
        hardens this two ways:

        * **Tolerant parse** — a single malformed line (e.g. a torn
          append from a crash, or a Dropbox-synced partial line from
          another machine) no longer raises and hides *every*
          transaction; the bad line is skipped with a warning.
        * **Self-heal** — ``commit()`` writes ``<id>.json`` *then*
          appends to the index.  A crash in that window leaves an
          orphaned ``<id>.json`` that the index never references, so it
          would be invisible (and un-undoable).  We glob the per-tx
          files and fold in any not present in the index, so every
          recorded transaction is always listable and reversible.
        """
        seen_ids: set[str] = set()
        transactions: list[dict] = []

        index_file = self.log_dir / "index.jsonl"
        if index_file.exists():
            for line in index_file.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    tx = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    logger.warning("skipping malformed index line: %r", line[:80])
                    continue
                tx_id = tx.get("id")
                if not tx_id or tx_id in seen_ids:
                    continue
                seen_ids.add(tx_id)
                log_file = self.log_dir / f"{tx_id}.json"
                if log_file.exists():
                    try:
                        full_tx = json.loads(log_file.read_text())
                        tx["undone"] = full_tx.get("undone", False)
                    except (json.JSONDecodeError, ValueError, OSError):
                        pass
                transactions.append(tx)

        # Self-heal: surface orphaned transaction files missing from the
        # index (crash between writing <id>.json and appending the
        # summary).  Reconstruct a summary from the full record.
        try:
            orphans = sorted(self.log_dir.glob("*.json"))
        except OSError:
            orphans = []
        for log_file in orphans:
            tx_id = log_file.stem
            if tx_id in seen_ids:
                continue
            try:
                full_tx = json.loads(log_file.read_text())
            except (json.JSONDecodeError, ValueError, OSError):
                continue
            if full_tx.get("id") != tx_id:
                continue  # not one of our transaction records
            seen_ids.add(tx_id)
            transactions.append({
                "id": tx_id,
                "timestamp": full_tx.get("timestamp", ""),
                "description": full_tx.get("description", "(recovered)"),
                "operations_count": len(full_tx.get("operations", [])),
                "undone": full_tx.get("undone", False),
            })

        # Stable chronological order regardless of index vs orphan source.
        transactions.sort(key=lambda t: t.get("timestamp", ""))
        return transactions

    def get_latest_transaction_id(self) -> Optional[str]:
        """Get the ID of the most recent non-undone transaction."""
        transactions = self.list_transactions()
        for tx in reversed(transactions):
            if not tx.get("undone"):
                return tx["id"]
        return None


# ---------------------------------------------------------------------------
# Helper: wrap shutil operations with logging
# ---------------------------------------------------------------------------

def _maybe_sidecar_pair(source: Path, destination: Path) -> Optional[tuple[Path, Path]]:
    """Return ``(src_sidecar, dst_sidecar)`` if a sidecar should travel
    with this move, otherwise ``None``.

    Conditions:
    * the source is a .pdf (we only attach identity sidecars to PDFs);
    * the sidecar resolved by ``sidecar_path()`` actually exists;
    * we're not moving the sidecar itself (avoid sidecar-of-sidecar).

    Delegates to ``processing.identity.sidecar_path`` so the same
    resolution logic (natural sibling vs. mirror tree vs. overlong
    fallback) applies everywhere.
    """
    if source.suffix.lower() != ".pdf":
        return None
    from processing.identity import find_sidecar, sidecar_path
    # WHERE IT IS, not where it should be.  Asking sidecar_path() for the
    # source meant a sidecar stored under an older convention was invisible,
    # so the PDF moved and its identity stayed behind -- silently, because
    # "no sidecar" and "sidecar I could not find" returned the same None.
    src_sidecar = find_sidecar(source)
    if src_sidecar is None:
        return None
    dst_sidecar = sidecar_path(destination)
    return src_sidecar, dst_sidecar


def logged_move(
    source: Path, destination: Path, *, undo_log: Optional[UndoLog] = None
) -> None:
    """Move a file and record the operation in the undo log.

    Records the operation BEFORE moving so that a crash mid-move
    still leaves a recoverable undo entry.

    If the source is a PDF with a ``<stem>.meta.json`` sidecar next to
    it, the sidecar moves with it as part of the same transaction.
    The PDF op is recorded first; the undo loop reverses the order so
    the sidecar is restored before the PDF, keeping the pair
    consistent throughout.
    """
    if not source.exists():
        raise FileNotFoundError(f"Source does not exist: {source}")
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")

    pair = _maybe_sidecar_pair(source, destination)
    if pair and pair[1].exists():
        raise FileExistsError(
            f"Destination sidecar already exists: {pair[1]}; refusing to "
            f"clobber another paper's identity"
        )

    if undo_log:
        undo_log.record_move(source, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))

    if pair:
        src_sidecar, dst_sidecar = pair
        if undo_log:
            undo_log.record_move(src_sidecar, dst_sidecar)
        # Mirror-tree dest may not exist yet -- create it.  No-op
        # for the natural-sibling case (the parent is the PDF's
        # parent which already exists post-move).
        dst_sidecar.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_sidecar), str(dst_sidecar))
        # Rewrite the sidecar's ``copy_locations`` so the recorded
        # primary path matches the move's destination.  Without this
        # the sidecar would still claim the paper lives at the OLD
        # location, leaking lies to the topic router and the
        # cockpit Activity tab.  Best-effort: failure here logs and
        # continues since the move itself already succeeded.
        try:
            from processing.identity import repath_copy_locations, repath_topic_copies
            repath_copy_locations(destination, old_path=source, new_path=destination)
            # If the basename changed, also rename the topic-folder
            # hardlinks so users browsing 07a/ don't see the old
            # filename forever.
            repath_topic_copies(
                destination, old_path=source, new_path=destination,
                undo_log=undo_log,
            )
        except Exception as exc:  # pragma: no cover -- defensive
            logger.warning(
                "could not repath copy_locations for %s: %s", destination, exc
            )


def logged_copy(
    source: Path, destination: Path, *, undo_log: Optional[UndoLog] = None
) -> None:
    """Copy a file and record the operation in the undo log.

    Sidecars are *not* copied automatically: a copy creates a new
    identity (different physical PDF) which deserves its own sidecar
    written by the caller.  Copying the sidecar would point at the
    wrong file's history.
    """
    if not source.exists():
        raise FileNotFoundError(f"Source does not exist: {source}")
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    if undo_log:
        undo_log.record_copy(source, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _is_same_file(a: Path, b: Path) -> bool:
    """Do these two paths name the SAME file on disk?

    Not a path comparison: macOS/APFS is case-insensitive, so a rename
    that only changes capitalisation ("space–time" -> "Space–time") has a
    "destination that already exists" which IS the source.  Comparing
    paths made every such rename look like a clobber and refuse — the
    guard is meant to stop one paper overwriting ANOTHER, so ask the
    filesystem, not the string.
    """
    try:
        return a.samefile(b)
    except OSError:          # one of them vanished, or is unreadable
        return False


def _retire_to_trash(path: Path, reason: str) -> Path:
    """Move ``path`` into ``<library>/.trash/<reason>/`` instead of deleting it.

    Nothing in this project hard-deletes a library PDF. The one branch that
    did -- undoing a copy -- is the branch that lost a paper.

    The name is made unique rather than overwritten: two undone copies of the
    same paper must not silently become one.
    """
    from core.config_paths import get_library_root
    try:
        root = Path(get_library_root())
    except Exception:                                   # pragma: no cover
        root = path.parent
    trash = root / ".trash" / reason
    trash.mkdir(parents=True, exist_ok=True)
    target = trash / path.name
    n = 1
    while target.exists():
        target = trash / f"{path.stem} ({n}){path.suffix}"
        n += 1
    path.rename(target)
    return target


def logged_rename(
    old_path: Path, new_path: Path, *, undo_log: Optional[UndoLog] = None
) -> None:
    """Rename a file and record the operation in the undo log.

    Same sidecar-attachment semantics as ``logged_move``: a PDF rename
    carries its sidecar along.
    """
    if not old_path.exists():
        raise FileNotFoundError(f"Source does not exist: {old_path}")
    if new_path.exists() and not _is_same_file(old_path, new_path):
        raise FileExistsError(f"Destination already exists: {new_path}")

    pair = _maybe_sidecar_pair(old_path, new_path)
    if pair and pair[1].exists() and not _is_same_file(pair[0], pair[1]):
        raise FileExistsError(
            f"Destination sidecar already exists: {pair[1]}; refusing to "
            f"clobber another paper's identity"
        )

    if undo_log:
        undo_log.record_rename(old_path, new_path)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.rename(new_path)

    if pair and pair[0] != pair[1]:
        src_sidecar, dst_sidecar = pair
        if undo_log:
            undo_log.record_rename(src_sidecar, dst_sidecar)
        # Mirror-tree dest may not exist yet -- create it.
        dst_sidecar.parent.mkdir(parents=True, exist_ok=True)
        src_sidecar.rename(dst_sidecar)
        # See logged_move above -- keep copy_locations honest AND
        # rename the topic-folder hardlinks.
        try:
            from processing.identity import repath_copy_locations, repath_topic_copies
            repath_copy_locations(new_path, old_path=old_path, new_path=new_path)
            repath_topic_copies(
                new_path, old_path=old_path, new_path=new_path,
                undo_log=undo_log,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "could not repath copy_locations for %s: %s", new_path, exc
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Manage the file operation undo log")
    sub = parser.add_subparsers(dest="command")

    # List transactions
    sub.add_parser("list", help="List all transactions")

    # Show a transaction
    show_p = sub.add_parser("show", help="Show transaction details")
    show_p.add_argument("transaction", help="Transaction ID")

    # Undo a transaction
    undo_p = sub.add_parser("undo", help="Undo a transaction")
    undo_p.add_argument("--transaction", help="Transaction ID (default: most recent)")
    undo_p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    log = UndoLog()

    if args.command == "list":
        transactions = log.list_transactions()
        if not transactions:
            print("No transactions recorded.")
            return
        print(f"{'ID':14s} {'Date':22s} {'Ops':>4s} {'Status':8s} Description")
        print("-" * 80)
        for tx in transactions:
            status = "UNDONE" if tx.get("undone") else "active"
            ts = tx["timestamp"][:19].replace("T", " ")
            print(f"{tx['id']:14s} {ts:22s} {tx['operations_count']:4d} {status:8s} {tx['description']}")

    elif args.command == "show":
        log_file = log.log_dir / f"{args.transaction}.json"
        if not log_file.exists():
            print(f"Transaction not found: {args.transaction}", file=sys.stderr)
            sys.exit(1)
        tx = json.loads(log_file.read_text())
        print(json.dumps(tx, indent=2, ensure_ascii=False))

    elif args.command == "undo":
        tx_id = args.transaction or log.get_latest_transaction_id()
        if not tx_id:
            print("No transactions to undo.", file=sys.stderr)
            sys.exit(1)

        print(f"Undoing transaction {tx_id}...")
        results = log.undo_transaction(tx_id, dry_run=args.dry_run)
        for r in results:
            print(f"  {r['action']}")
        print(f"\n{'Would undo' if args.dry_run else 'Undone'} {len(results)} operations")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
