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
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default log location
LOG_DIR = Path(__file__).resolve().parent.parent.parent / ".operation_log"


class UndoLog:
    """Records file operations and provides undo functionality."""

    def __init__(self, log_dir: Path = LOG_DIR):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_tx: Optional[dict] = None
        self._tx_id: Optional[str] = None

    def begin_transaction(self, description: str) -> str:
        """Start a new transaction. Returns the transaction ID."""
        self._tx_id = hashlib.md5(
            f"{time.time()}-{description}".encode()
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

        results = []
        # Undo in reverse order
        for op in reversed(tx["operations"]):
            src = Path(op["source"])
            dst = Path(op["destination"])

            if op["type"] == "move":
                # Undo move: move destination back to source
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
        """List all transactions from the index."""
        index_file = self.log_dir / "index.jsonl"
        if not index_file.exists():
            return []

        transactions = []
        for line in index_file.read_text().splitlines():
            if line.strip():
                tx = json.loads(line)
                # Check if undone
                log_file = self.log_dir / f"{tx['id']}.json"
                if log_file.exists():
                    full_tx = json.loads(log_file.read_text())
                    tx["undone"] = full_tx.get("undone", False)
                transactions.append(tx)

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
def logged_move(
    source: Path, destination: Path, *, undo_log: Optional[UndoLog] = None
) -> None:
    """Move a file and record the operation in the undo log.

    Records the operation BEFORE moving so that a crash mid-move
    still leaves a recoverable undo entry.
    """
    if not source.exists():
        raise FileNotFoundError(f"Source does not exist: {source}")
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    if undo_log:
        undo_log.record_move(source, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def logged_copy(
    source: Path, destination: Path, *, undo_log: Optional[UndoLog] = None
) -> None:
    """Copy a file and record the operation in the undo log."""
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
    """Rename a file and record the operation in the undo log."""
    if not old_path.exists():
        raise FileNotFoundError(f"Source does not exist: {old_path}")
    if new_path.exists() and old_path != new_path:
        raise FileExistsError(f"Destination already exists: {new_path}")
    if undo_log:
        undo_log.record_rename(old_path, new_path)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.rename(new_path)


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
