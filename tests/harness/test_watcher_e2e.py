"""End-to-end test of the watcher daemon.

We don't spawn an actual subprocess — that would couple the test to OS
event timing. Instead we drive the PDFHandler directly with the same
events watchdog would generate, then call process_settled() to simulate
the timer loop, and verify ingest_paper actually filed the dropped file.

This catches the kinds of bugs that the unit tests (which mock
process_settled internals) miss: integration between event handlers,
settle timer, and the real ingest pipeline.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from synth_library import _write_minimal_pdf, build_synth_library  # noqa: E402


@pytest.fixture
def lib_and_inbox(tmp_path):
    """A synthetic library with a separate inbox the watcher would watch."""
    pytest.importorskip("watchdog")

    lib = build_synth_library(tmp_path / "lib", specs=[])  # empty 12/
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return lib, inbox, log_dir


def _make_handler(lib: Path, inbox: Path, log_dir: Path, *, default_status: str = "working"):
    from watcher.config import WatcherConfig
    from watcher.daemon import PDFHandler

    cfg = WatcherConfig(
        inbox_dir=inbox,
        library_root=lib,
        log_dir=log_dir,
        default_status=default_status,
        settle_seconds=0.01,  # near-instant for tests
        notifications=False,
    )
    return PDFHandler(cfg, dry_run=False)


# ---------------------------------------------------------------------------
# 1. The basic flow: create event → settle → ingest → file appears in lib
# ---------------------------------------------------------------------------

def test_create_then_settle_then_file(lib_and_inbox):
    lib, inbox, log_dir = lib_and_inbox
    handler = _make_handler(lib, inbox, log_dir, default_status="working")

    # Drop a PDF whose metadata lets the pipeline succeed
    pdf = inbox / "drop1.pdf"
    _write_minimal_pdf(pdf, title="An ingested paper", author="Smith, J.")

    # Simulate watchdog firing on_created, then enough time passes that
    # the settle timer expires.
    event = MagicMock(is_directory=False, src_path=str(pdf))
    handler.on_created(event)
    assert str(pdf) in handler._pending

    # Force the timer to be old enough
    size, _ = handler._pending[str(pdf)]
    handler._pending[str(pdf)] = (size, time.time() - 1.0)

    # process_settled triggers _ingest, which calls ingest_paper for real
    handler.process_settled()

    # The original is moved/copied — for working status the source stays
    # by default (delete_source=False), but it gets ingested into the library.
    # Look for it under 03 - Working papers/{S}/.
    target_root = lib / "03 - Working papers" / "S"
    filed = list(target_root.rglob("*.pdf")) if target_root.exists() else []
    assert any("Smith" in p.name for p in filed), (
        f"Expected a Smith-named file under {target_root}; found: {filed}"
    )


# ---------------------------------------------------------------------------
# 2. Moved-into-inbox (browser .crdownload → .pdf rename)
# ---------------------------------------------------------------------------

def test_moved_into_inbox_handled(lib_and_inbox):
    lib, inbox, log_dir = lib_and_inbox
    handler = _make_handler(lib, inbox, log_dir, default_status="working")

    pdf = inbox / "renamed.pdf"
    _write_minimal_pdf(pdf, title="Renamed in", author="Brown, A.")

    # Simulate browser pattern: file was renamed FROM something else INTO
    # the inbox with .pdf suffix. That's on_moved, not on_created.
    event = MagicMock(
        is_directory=False,
        src_path=str(inbox / "renamed.crdownload"),
        dest_path=str(pdf),
    )
    handler.on_moved(event)
    assert str(pdf) in handler._pending

    # Same settle dance
    size, _ = handler._pending[str(pdf)]
    handler._pending[str(pdf)] = (size, time.time() - 1.0)
    handler.process_settled()

    target_root = lib / "03 - Working papers" / "B"
    filed = list(target_root.rglob("*.pdf")) if target_root.exists() else []
    assert any("Brown" in p.name for p in filed), (
        f"Expected a Brown-named file under {target_root}; found: {filed}"
    )


# ---------------------------------------------------------------------------
# 3. Non-PDF files in inbox are ignored
# ---------------------------------------------------------------------------

def test_non_pdf_files_ignored(lib_and_inbox):
    lib, inbox, log_dir = lib_and_inbox
    handler = _make_handler(lib, inbox, log_dir)

    junk = inbox / "notes.txt"
    junk.write_text("not a PDF")

    event = MagicMock(is_directory=False, src_path=str(junk))
    handler.on_created(event)

    assert str(junk) not in handler._pending


# ---------------------------------------------------------------------------
# 4. Directory events are ignored
# ---------------------------------------------------------------------------

def test_directory_events_ignored(lib_and_inbox):
    lib, inbox, log_dir = lib_and_inbox
    handler = _make_handler(lib, inbox, log_dir)

    sub = inbox / "subdir"
    sub.mkdir()
    event = MagicMock(is_directory=True, src_path=str(sub))
    handler.on_created(event)
    assert str(sub) not in handler._pending


# ---------------------------------------------------------------------------
# 5. PDF that disappears between event and settle is dropped without crash
# ---------------------------------------------------------------------------

def test_disappeared_file_dropped(lib_and_inbox):
    lib, inbox, log_dir = lib_and_inbox
    handler = _make_handler(lib, inbox, log_dir)

    pdf = inbox / "ghost.pdf"
    _write_minimal_pdf(pdf, title="x", author="y")
    event = MagicMock(is_directory=False, src_path=str(pdf))
    handler.on_created(event)
    assert str(pdf) in handler._pending

    # File vanishes
    pdf.unlink()

    handler._pending[str(pdf)] = (handler._pending[str(pdf)][0], time.time() - 1.0)
    handler.process_settled()
    # Must not crash, must remove from pending
    assert str(pdf) not in handler._pending
