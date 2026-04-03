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
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from watcher.config import WatcherConfig
from watcher.notifier import notify

logger = logging.getLogger(__name__)


class PDFHandler(FileSystemEventHandler):
    """Handles new PDF files appearing in the inbox."""

    def __init__(self, config: WatcherConfig, *, dry_run: bool = False):
        super().__init__()
        self.config = config
        self.dry_run = dry_run
        self._pending: dict[str, float] = {}  # path → first_seen_time

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".pdf":
            return
        # Track as pending — wait for file to finish writing
        self._pending[str(path)] = time.time()
        logger.info("Detected new PDF: %s", path.name)

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".pdf":
            return
        # Reset the settle timer
        self._pending[str(path)] = time.time()

    def process_settled(self) -> None:
        """Process PDFs that have been stable for settle_seconds."""
        now = time.time()
        settled = [
            p for p, t in self._pending.items()
            if now - t >= self.config.settle_seconds
        ]

        for path_str in settled:
            del self._pending[path_str]
            path = Path(path_str)
            if path.exists():
                self._ingest(path)

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

                    # Commit undo log
                    if undo_log:
                        undo_log.commit()

                    # Optionally delete source
                    if self.config.delete_source and path.exists():
                        path.unlink()
                        logger.info("Deleted source: %s", path.name)
            else:
                error = result.get("error", "Unknown error")
                logger.warning("Failed to ingest %s: %s", path.name, error)
                if self.config.notifications:
                    notify("Ingestion Failed", f"{path.name}\n{error}", sound="Basso")

        except Exception as exc:
            logger.error("Error ingesting %s: %s", path.name, exc, exc_info=True)
            if self.config.notifications:
                notify("Ingestion Error", f"{path.name}\n{exc}", sound="Basso")


def run_daemon(config: WatcherConfig, *, dry_run: bool = False) -> None:
    """Run the filesystem watcher daemon."""
    config.ensure_dirs()

    handler = PDFHandler(config, dry_run=dry_run)
    observer = Observer()
    observer.schedule(handler, str(config.inbox_dir), recursive=False)

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

    # Also log to file
    config.ensure_dirs()
    log_file = config.log_dir / "watcher.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)

    run_daemon(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
