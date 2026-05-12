"""Tests for the watcher daemon's settle-timer logic.

We don't actually start the watchdog Observer — we directly drive
PDFHandler.process_settled() with manipulated _pending state to verify
that:
  - Files whose size is still changing are NOT treated as settled.
  - Files whose size has been stable for >= settle_seconds ARE processed.
  - Disappeared files are dropped from the pending set without crashing.
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def handler(tmp_path):
    """Build a PDFHandler with a stub config that points at tmp_path."""
    pytest.importorskip("watchdog")  # skip cleanly if dep not installed

    from watcher.config import WatcherConfig
    from watcher.daemon import PDFHandler

    cfg = WatcherConfig(
        inbox_dir=tmp_path / "inbox",
        library_root=tmp_path / "lib",
        log_dir=tmp_path / "logs",
        settle_seconds=0.1,  # tight timeout so tests run fast
        notifications=False,
    )
    cfg.inbox_dir.mkdir(parents=True, exist_ok=True)
    cfg.library_root.mkdir(parents=True, exist_ok=True)
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    return PDFHandler(cfg, dry_run=True)  # dry-run: never touches files


class TestSettleTimer:
    def test_growing_file_not_settled(self, handler, tmp_path):
        pdf = tmp_path / "growing.pdf"
        pdf.write_bytes(b"start")
        handler._pending[str(pdf)] = (5, time.time() - 10)  # "old" but small

        # Simulate the file growing between polls
        pdf.write_bytes(b"start more bytes")

        # process_settled should detect the size change and reset, not ingest
        with patch("processing.ingest.ingest_paper") as mock_ingest:
            handler.process_settled()
            mock_ingest.assert_not_called()

        # File still pending, with updated size
        assert str(pdf) in handler._pending

    def test_stable_file_is_processed(self, handler, tmp_path):
        pdf = tmp_path / "stable.pdf"
        pdf.write_bytes(b"%PDF-stable")
        size = pdf.stat().st_size
        # Pretend last_change was 1 second ago, far more than settle_seconds=0.1
        handler._pending[str(pdf)] = (size, time.time() - 1.0)

        with patch.object(handler, "_ingest") as mock_ingest:
            handler.process_settled()

        mock_ingest.assert_called_once()
        # No longer pending
        assert str(pdf) not in handler._pending

    def test_missing_file_dropped(self, handler, tmp_path):
        ghost = tmp_path / "ghost.pdf"
        # File never created. Pending entry references it.
        handler._pending[str(ghost)] = (10, time.time() - 5)

        with patch.object(handler, "_ingest") as mock_ingest:
            handler.process_settled()

        mock_ingest.assert_not_called()
        assert str(ghost) not in handler._pending

    def test_zero_byte_file_eventually_settles(self, handler, tmp_path):
        pdf = tmp_path / "zero.pdf"
        pdf.write_bytes(b"")
        handler._pending[str(pdf)] = (0, time.time() - 1.0)

        with patch.object(handler, "_ingest") as mock_ingest:
            handler.process_settled()

        mock_ingest.assert_called_once()


class TestEventHandlers:
    def test_pdf_creation_adds_to_pending(self, handler, tmp_path):
        pdf = tmp_path / "new.pdf"
        pdf.write_bytes(b"%PDF-x")
        event = MagicMock(is_directory=False, src_path=str(pdf))
        handler.on_created(event)
        assert str(pdf) in handler._pending
        size, _ = handler._pending[str(pdf)]
        assert size == pdf.stat().st_size

    def test_non_pdf_ignored(self, handler, tmp_path):
        txt = tmp_path / "not_a_pdf.txt"
        txt.write_text("hi")
        event = MagicMock(is_directory=False, src_path=str(txt))
        handler.on_created(event)
        assert str(txt) not in handler._pending

    def test_directory_event_ignored(self, handler, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        event = MagicMock(is_directory=True, src_path=str(d))
        handler.on_created(event)
        assert str(d) not in handler._pending

    def test_modified_resets_timer(self, handler, tmp_path):
        pdf = tmp_path / "mod.pdf"
        pdf.write_bytes(b"%PDF-x")
        # Seed an old entry
        handler._pending[str(pdf)] = (1, 0.0)
        event = MagicMock(is_directory=False, src_path=str(pdf))
        handler.on_modified(event)
        size, last = handler._pending[str(pdf)]
        # Now reflects current size and recent time
        assert size == pdf.stat().st_size
        assert last > 1.0
