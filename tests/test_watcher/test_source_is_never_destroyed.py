"""The inbox original must survive ingestion.

The daemon ran `path.unlink()` on the source after filing it: no trash
copy, no undo record. The filed copy became the only one in existence —
and because an ingest is recorded as a `copy`, undoing it removes that
copy too, leaving ZERO copies of the paper.

It was armed: delete_source: true in config/watcher.yaml, the daemon
running, and a 3-second settle that will file a file still being written
by cp/curl/scp/a scanner.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402


@pytest.fixture()
def daemon(tmp_path):
    from watcher.daemon import PDFHandler
    from watcher.config import WatcherConfig
    lib = tmp_path / "lib"
    (lib / "01 - Published papers").mkdir(parents=True)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    cfg = WatcherConfig(inbox_dir=inbox, library_root=lib,
                        log_dir=tmp_path / "logs",
                        delete_source=True, settle_seconds=0.0)
    return PDFHandler(cfg), lib, inbox


def test_the_source_goes_to_trash_not_to_nothing(daemon):
    d, lib, inbox = daemon
    src = inbox / "main.pdf"
    _write_minimal_pdf(src, title="t", author="Smith, J.")
    dest = d._retire_source(src, None)
    assert not src.exists(), "the inbox is still cleared"
    assert dest.exists(), "…but the original survives"
    assert ".trash" in str(dest)
    assert dest.read_bytes(), "and it is the real bytes, not a stub"


def test_two_drops_of_the_same_name_do_not_clobber(daemon):
    """"main.pdf" and "1-s2.0-....pdf" are shared by many papers; one
    overwriting another INSIDE the trash defeats the point of a trash."""
    d, lib, inbox = daemon
    first = inbox / "main.pdf"
    _write_minimal_pdf(first, title="one", author="A, A.")
    a = d._retire_source(first, None)
    second = inbox / "main.pdf"
    _write_minimal_pdf(second, title="two", author="B, B.")
    b = d._retire_source(second, None)
    assert a != b
    assert a.exists() and b.exists()
    assert a.read_bytes() != b.read_bytes()


def test_retirement_is_recorded_and_reversible(daemon):
    from processing.undo_log import UndoLog
    d, lib, inbox = daemon
    src = inbox / "paper.pdf"
    _write_minimal_pdf(src, title="t", author="Smith, J.")
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("ingest")
    d._retire_source(src, log)
    log.commit()
    assert not src.exists()
    res = log.undo_transaction(tx)
    assert src.exists(), f"undo must bring the original back: {res}"


def test_a_failure_to_retire_leaves_the_original_alone(daemon, monkeypatch):
    """Keeping the original is always safer than losing it."""
    from processing import undo_log as ul
    d, lib, inbox = daemon
    src = inbox / "paper.pdf"
    _write_minimal_pdf(src, title="t", author="Smith, J.")
    monkeypatch.setattr(ul, "logged_move",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        d._retire_source(src, None)
    assert src.exists()
