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


class UndoLog:
    """Records file operations and provides undo functionality."""

    def __init__(self, log_dir: Path = LOG_DIR):
        self.log_dir = log_dir
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

    def record_move(self, source: Path, destination: Path) -> None:
        """Record a file move/rename operation."""
        if self._current_tx is None:
            raise RuntimeError("No active transaction — call begin_transaction() first")
        self._current_tx["operations"].append({
            "type": "move",
            "source": str(source),
            "destination": str(destination),
        })

    def record_copy(self, source: Path, destination: Path) -> None:
        """Record a file copy operation."""
        if self._current_tx is None:
            raise RuntimeError("No active transaction — call begin_transaction() first")
        self._current_tx["operations"].append({
            "type": "copy",
            "source": str(source),
            "destination": str(destination),
        })

    def record_rename(self, old_path: Path, new_path: Path) -> None:
        """Record a file rename operation."""
        if self._current_tx is None:
            raise RuntimeError("No active transaction — call begin_transaction() first")
        self._current_tx["operations"].append({
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
        self._current_tx["operations"].append({
            "type": "sidecar_edit",
            "path": str(pdf_path),
            "changes": changes,
        })

    def discard(self) -> None:
        """Drop the current (in-memory) transaction without writing anything.

        Use instead of ``commit()`` when a transaction turned out to do no
        work (e.g. the watcher began an ingest tx but the arrival was a
        duplicate and nothing moved).  Committing such a tx would litter
        the log and the cockpit Activity tab with a 0-op entry that has
        live Undo buttons.  Nothing is on disk until ``commit()``, so
        discarding is just clearing the in-memory state.
        """
        self._current_tx = None
        self._tx_id = None

    def commit(self) -> Path:
        """Commit the current transaction to disk. Returns the log file path."""
        if self._current_tx is None:
            raise RuntimeError("No active transaction to commit")

        log_file = self.log_dir / f"{self._tx_id}.json"
        log_file.write_text(json.dumps(self._current_tx, indent=2, ensure_ascii=False))

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

        tx_id = self._tx_id
        self._current_tx = None
        self._tx_id = None
        return log_file

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
                        "action": f"WOULD RESTORE sidecar fields {list(changes)} on {pdf.name}"
                    })
                    continue
                try:
                    from processing.identity import PaperIdentity
                    ident = PaperIdentity.load(pdf)
                    if ident.is_new():
                        results.append({"action": f"SKIP: no sidecar to restore: {pdf}"})
                        continue
                    for field, (old_val, _new_val) in changes.items():
                        setattr(ident, field, old_val)
                    ident.save(pdf, recompute_hash=False)
                    results.append({
                        "action": f"RESTORED sidecar fields {list(changes)} on {pdf.name}"
                    })
                except Exception as exc:  # pragma: no cover -- defensive
                    results.append({"action": f"FAILED to restore sidecar on {pdf}: {exc}"})
                continue

            src = Path(op["source"])
            dst = Path(op["destination"])

            if op["type"] == "move":
                # Undo move: move destination back to source
                if str(dst) in SPECIAL_DEVICES:
                    results.append({
                        "action": f"CANNOT UNDO: file was deleted (recorded as move to {dst}); "
                                  f"source path {src} is unrecoverable from this log"
                    })
                    continue
                if dry_run:
                    results.append({"action": f"WOULD MOVE BACK: {dst.name} → {src}"})
                else:
                    if dst.exists():
                        src.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(dst), str(src))
                        results.append({"action": f"MOVED BACK: {dst.name} → {src}"})
                    else:
                        results.append({"action": f"SKIP: destination gone: {dst}"})

            elif op["type"] == "copy":
                # Undo copy: remove the copy
                if dry_run:
                    results.append({"action": f"WOULD DELETE COPY: {dst}"})
                else:
                    if dst.exists():
                        dst.unlink()
                        results.append({"action": f"DELETED COPY: {dst}"})
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
                        results.append({"action": f"SKIP: copy already gone: {dst}"})

            elif op["type"] == "rename":
                # Undo rename: rename back
                if dry_run:
                    results.append({"action": f"WOULD RENAME BACK: {dst.name} → {src.name}"})
                else:
                    if dst.exists():
                        shutil.move(str(dst), str(src))
                        results.append({"action": f"RENAMED BACK: {dst.name} → {src.name}"})
                    else:
                        results.append({"action": f"SKIP: file gone: {dst}"})

        # Mark transaction as undone
        if not dry_run:
            tx["undone"] = True
            tx["undone_at"] = datetime.now(timezone.utc).isoformat()
            log_file.write_text(json.dumps(tx, indent=2, ensure_ascii=False))

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
    from processing.identity import sidecar_path
    src_sidecar = sidecar_path(source)
    try:
        if not src_sidecar.exists():
            return None
    except OSError:
        return None  # path too long etc -- treat as no sidecar
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


def logged_rename(
    old_path: Path, new_path: Path, *, undo_log: Optional[UndoLog] = None
) -> None:
    """Rename a file and record the operation in the undo log.

    Same sidecar-attachment semantics as ``logged_move``: a PDF rename
    carries its sidecar along.
    """
    if not old_path.exists():
        raise FileNotFoundError(f"Source does not exist: {old_path}")
    if new_path.exists() and old_path != new_path:
        raise FileExistsError(f"Destination already exists: {new_path}")

    pair = _maybe_sidecar_pair(old_path, new_path)
    if pair and pair[1].exists() and pair[0] != pair[1]:
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
