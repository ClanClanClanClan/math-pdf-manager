#!/usr/bin/env python3
"""Filesystem watcher daemon for automatic paper ingestion.

Watches an inbox directory for new PDF files, extracts metadata,
generates canonical filenames, and files papers in the library.
Sends macOS notifications on success/failure.

Usage::

    # Start the watcher (foreground)
    python -m watcher.daemon

    # With custom config
    python -m watcher.daemon --config ~/.mathpdf/watcher.yaml

    # Dry run (process but don't move files)
    python -m watcher.daemon --dry-run
"""
from __future__ import annotations


import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Ensure src/ is on path
from watcher.config import WatcherConfig
from watcher.notifier import notify

logger = logging.getLogger(__name__)


def _is_ingestable_pdf(path: Path) -> bool:
    """True for a real PDF the watcher should ingest.

    Audit-10: on a Dropbox-synced inbox, editing the same paper from
    two machines produces a sibling like
    ``Paper (machine's conflicted copy 2026-06-15).pdf``.  The watcher
    used to treat that as a brand-new paper and ingest a duplicate.
    Conflict copies are NOT auto-ingested — they're left for the
    cockpit Conflicts tab to adjudicate against the canonical.
    """
    if path.suffix.lower() != ".pdf":
        return False
    try:
        from processing.conflict_resolver import find_canonical_for_conflict
        if find_canonical_for_conflict(path) is not None:
            logger.info("Skipping Dropbox conflict copy (left for review): %s", path.name)
            return False
    except Exception:
        # Detection is best-effort; never let it block a real ingest.
        pass
    return True


class PDFHandler(FileSystemEventHandler):
    """Handles new PDF files appearing in the inbox."""

    def __init__(self, config: WatcherConfig, *, dry_run: bool = False):
        super().__init__()
        self.config = config
        self.dry_run = dry_run
        # path -> (last_known_size, last_change_time). The settle check
        # requires both unchanged size AND elapsed settle_seconds.
        self._pending: dict[str, tuple[int, float]] = {}

    def _initial_pending_state(self, path: Path) -> tuple:
        """Snapshot size + time so we can detect when writes finish."""
        try:
            size = path.stat().st_size
        except OSError:
            size = -1  # placeholder; will resolve on next poll
        return (size, time.time())

    def scan_existing_inbox(self) -> int:
        """Add every PDF already in the inbox to the pending queue.

        Run once at daemon startup so files dropped while the watcher
        was offline get ingested on the next ``process_settled()`` cycle
        instead of waiting forever for a fresh on_created event that
        will never fire.  Returns the number of files added.
        """
        added = 0
        try:
            for entry in self.config.inbox_dir.iterdir():
                if entry.is_dir():
                    continue
                if not _is_ingestable_pdf(entry):
                    continue
                key = str(entry)
                if key in self._pending:
                    continue
                self._pending[key] = self._initial_pending_state(entry)
                added += 1
                logger.info("Picked up pre-existing PDF: %s", entry.name)
        except OSError as exc:
            logger.warning("scan_existing_inbox failed: %s", exc)
        return added

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if not _is_ingestable_pdf(path):
            return
        # Record (size, last_change_time). The settle check requires both
        # an unchanged size AND elapsed settle_seconds before ingesting.
        self._pending[str(path)] = self._initial_pending_state(path)
        logger.info("Detected new PDF: %s", path.name)

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if not _is_ingestable_pdf(path):
            return
        # Reset to current size/time. process_settled will compare on next tick.
        self._pending[str(path)] = self._initial_pending_state(path)

    def on_moved(self, event):
        """Files moved INTO the inbox (or renamed to .pdf after download).

        Browsers commonly download with a temporary suffix (.crdownload,
        .partial) then rename to .pdf — that's an on_moved, not on_created.
        Without this handler, those downloads would be invisible to the
        watcher and silently never ingested.
        """
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", None) or event.src_path
        path = Path(dest)
        if not _is_ingestable_pdf(path):
            return
        # Drop the old name (if any) from pending; track the new one.
        old = getattr(event, "src_path", None)
        if old and old != dest:
            self._pending.pop(old, None)
        self._pending[str(path)] = self._initial_pending_state(path)
        logger.info("Detected moved-in PDF: %s", path.name)

    def process_settled(self) -> None:
        """Process PDFs whose size has been stable for ``settle_seconds``.

        For each pending PDF we re-stat. If the size changed since last poll,
        the timer resets. Only when the size is unchanged AND
        ``settle_seconds`` have elapsed do we ingest.
        """
        now = time.time()
        ready: list[str] = []
        for path_str, info in list(self._pending.items()):
            path = Path(path_str)
            if not path.exists():
                # File was removed while we waited — drop it.
                del self._pending[path_str]
                continue
            try:
                current_size = path.stat().st_size
            except OSError:
                continue  # transient — try again next tick

            last_size, last_change = info
            # ``-1`` is the sentinel produced by _initial_pending_state when
            # the very first stat() failed. Never treat that as "settled" —
            # we have no proof the file was ever readable. Force a reset so
            # the timer only starts once we get a real size.
            if last_size < 0:
                self._pending[path_str] = (current_size, now)
                continue
            if current_size != last_size:
                # Still being written — reset timer with new size.
                self._pending[path_str] = (current_size, now)
                continue
            if now - last_change >= self.config.settle_seconds:
                ready.append(path_str)

        if not ready:
            return

        # Audit-11a: serialize against the weekly maintenance batch.
        # Take the same-host library write lock for the whole settled
        # batch.  If the weekly job (or another writer) holds it, leave
        # these files in ``_pending`` and retry next tick rather than
        # interleave file moves.  A dry run touches nothing, so it skips
        # the lock.
        lock = None
        if not self.dry_run:
            try:
                from processing.locking import LibraryLock
                from core.config_paths import get_library_root
                lock = LibraryLock(get_library_root())
                if not lock.acquire(blocking=False):
                    logger.info(
                        "Deferring %d ingest(s): library write lock held "
                        "by another process", len(ready),
                    )
                    return
            except Exception as exc:  # pragma: no cover -- defensive
                logger.warning("library lock unavailable, proceeding: %s", exc)
                lock = None
        try:
            for path_str in ready:
                self._pending.pop(path_str, None)
                self._ingest(Path(path_str))
        finally:
            if lock is not None:
                lock.release()

    def _ingest(self, path: Path) -> None:
        """Ingest a single PDF file."""
        logger.info("Ingesting: %s", path.name)

        try:
            from processing.ingest import ingest_paper
            from processing.undo_log import UndoLog

            # Set up undo log
            undo_log = None
            if not self.dry_run:
                undo_log = UndoLog()
                undo_log.begin_transaction(f"Watcher: ingest {path.name}")

            result = ingest_paper(
                path,
                library_root=self.config.library_root,
                status=self.config.default_status if self.config.default_status != "auto" else None,
                year=self.config.default_year,
                dry_run=self.dry_run,
                undo_log=undo_log,
                # The watcher is the genuine "new arrival" path, so turn on
                # the duplicate-arrival guard: a freshly-dropped PDF that is
                # byte-identical to one already in the library is NOT filed
                # as a second copy.
                dedup_check=True,
                # ...and the preprint↔published variant check: an arrival
                # whose DOI/arXiv id already lives in a different file is
                # filed anyway but flagged for review.
                variant_check=True,
            )

            if result["success"]:
                dest = result.get("destination", "")
                # Show relative destination for readability
                try:
                    rel = Path(dest).relative_to(self.config.library_root)
                    dest_short = str(rel)
                except ValueError:
                    dest_short = dest

                msg = f"{result['filename']}\n→ {dest_short}"

                if self.dry_run:
                    logger.info("DRY RUN: would file %s → %s", path.name, dest_short)
                    if self.config.notifications:
                        notify("Paper (dry run)", msg, sound="")
                else:
                    logger.info("Filed: %s → %s", result['filename'], dest_short)
                    if self.config.notifications:
                        notify("Paper Filed", msg, sound=self.config.notification_sound)
                    # Filed fine, but its DOI/arXiv id already lives in a
                    # different file — almost certainly the other side of a
                    # preprint↔published pair.  Tell the user where to look.
                    if result.get("variant_of"):
                        try:
                            twin_short = str(Path(result["variant_of"])
                                             .relative_to(self.config.library_root))
                        except ValueError:
                            twin_short = result["variant_of"]
                        logger.info("Variant suspicion: %s <-> %s",
                                    result['filename'], twin_short)
                        if self.config.notifications:
                            notify("Possible preprint/published variant",
                                   f"{result['filename']}\nmatches {twin_short}\n"
                                   f"— review in the Duplicates page", sound="")

                    # Commit undo log
                    if undo_log:
                        undo_log.commit()

                    # Optionally delete source
                    if self.config.delete_source and path.exists():
                        path.unlink()
                        logger.info("Deleted source: %s", path.name)
            elif result.get("duplicate_of"):
                # Not an error: the drop is byte-identical to a paper
                # already filed.  Leave the source in place (don't file a
                # second copy) and tell the user where the original lives.
                dup = result["duplicate_of"]
                try:
                    dup_short = str(Path(dup).relative_to(self.config.library_root))
                except ValueError:
                    dup_short = dup
                logger.info("Duplicate drop %s — already filed at %s",
                            str(path), dup_short)
                if self.config.notifications:
                    notify("Duplicate (already in library)",
                           f"{path.name}\nalready filed at {dup_short}", sound="")
                # The ingest recorded no operations (we bailed before
                # organize), so DISCARD the empty transaction rather than
                # committing a 0-op no-op into the log / Activity tab.
                if undo_log:
                    undo_log.discard()
            else:
                error = result.get("error", "Unknown error")
                # Log the *full* path so the cockpit Attention Queue
                # can dedupe across multiple inbox folders that happen
                # to contain a same-named PDF.  The notification still
                # uses the short name for readability.
                logger.warning("Failed to ingest %s: %s", str(path), error)
                if self.config.notifications:
                    notify("Ingestion Failed", f"{path.name}\n{error}", sound="Basso")
                # Transaction hygiene: a failed ingest may still have
                # RECORDED operations before the failure point (e.g. the
                # copy was recorded, then a later step refused).  Those
                # must be persisted to stay reversible; an op-less tx is
                # discarded rather than committed as a 0-op entry.
                if undo_log:
                    if undo_log.has_operations():
                        undo_log.commit()
                    else:
                        undo_log.discard()

        except Exception as exc:
            logger.error("Error ingesting %s: %s", str(path), exc, exc_info=True)
            if self.config.notifications:
                notify("Ingestion Error", f"{path.name}\n{exc}", sound="Basso")
            # Same hygiene on the crash path: never strand recorded ops in
            # a never-committed in-memory transaction.
            if undo_log:
                try:
                    if undo_log.has_operations():
                        undo_log.commit()
                    else:
                        undo_log.discard()
                except Exception:  # pragma: no cover — never mask the error
                    pass


def run_daemon(config: WatcherConfig, *, dry_run: bool = False) -> None:
    """Run the filesystem watcher daemon."""
    config.ensure_dirs()

    handler = PDFHandler(config, dry_run=dry_run)
    observer = Observer()
    observer.schedule(handler, str(config.inbox_dir), recursive=False)

    # If files were dropped while the daemon was offline, they
    # wouldn't trigger fresh on_created events.  Seed the pending
    # queue with whatever is sitting in the inbox right now.
    n_preexisting = handler.scan_existing_inbox()
    if n_preexisting:
        logger.info(
            "Found %d PDF(s) already in inbox; will ingest on settle.",
            n_preexisting,
        )

    logger.info("Watching %s for new PDFs...", config.inbox_dir)
    logger.info("Library root: %s", config.library_root)
    if dry_run:
        logger.info("DRY RUN mode — files will not be moved")

    if config.notifications:
        notify(
            "Math-PDF Watcher Started",
            f"Watching {config.inbox_dir.name}/ for new papers",
            sound="",
        )

    # Handle graceful shutdown
    def _shutdown(signum, frame):
        logger.info("Shutting down watcher...")
        observer.stop()
        if config.notifications:
            notify("Math-PDF Watcher Stopped", "Watcher daemon stopped", sound="")

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    observer.start()
    try:
        while observer.is_alive():
            handler.process_settled()
            time.sleep(config.poll_interval)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        logger.info("Watcher stopped.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Watch a folder for new PDFs and auto-ingest them into the library",
    )
    parser.add_argument("--config", type=Path, help="Path to watcher.yaml config file")
    parser.add_argument("--inbox", type=Path, help="Override inbox directory")
    parser.add_argument("--library", type=Path, help="Override library root")
    parser.add_argument("--dry-run", action="store_true", help="Process but don't move files")
    parser.add_argument("--no-notify", action="store_true", help="Disable macOS notifications")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args(argv)

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load config
    config = WatcherConfig.load(args.config)

    # Override from CLI
    if args.inbox:
        config.inbox_dir = args.inbox.resolve()
    if args.library:
        config.library_root = args.library.resolve()
    if args.no_notify:
        config.notifications = False

    # Also log to file (rotated: 10 MB × 5 backups = ~50 MB cap)
    config.ensure_dirs()
    log_file = config.log_dir / "watcher.log"
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)

    run_daemon(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
