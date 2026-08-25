"""The daemon must notice its inbox vanishing and re-establish the watch.

THE OUTAGE. ~/Downloads/MathInbox was deleted. The daemon kept running --
pid 6282, up 5 days 21 hours -- and filed nothing, because watchdog does
not tear an Observer down when its directory disappears. It stays alive
and simply never delivers another event. Every screen said filing was ON.

The subtle half, which a naive fix misses: RECREATING THE FOLDER IS NOT
ENOUGH. The kernel watch is bound to the old inode. Make a new directory
at the same path and the path looks perfect while the watch still points
at the unlinked original. The watch must be RESCHEDULED, which means the
daemon has to detect identity change, not path absence.
"""
import time
from pathlib import Path

import pytest

from watcher.daemon import _current_watch


def test_identity_is_the_inode_not_the_path(tmp_path):
    """THE CORE OF THE BUG. Same path, different directory."""
    box = tmp_path / "inbox"
    box.mkdir()
    before = _current_watch(box)
    assert before is not None

    box.rmdir()
    box.mkdir()                      # same path, brand new inode
    after = _current_watch(box)

    assert after is not None
    assert after != before, (
        "recreating the folder produced an identical identity, so the daemon "
        "would never reschedule -- which is exactly the five-day outage"
    )


def test_a_missing_inbox_reads_as_gone(tmp_path):
    box = tmp_path / "inbox"
    assert _current_watch(box) is None
    box.mkdir()
    assert _current_watch(box) is not None


def test_identity_is_stable_while_nothing_changes(tmp_path):
    """It must not report a change every poll, or it reschedules forever."""
    box = tmp_path / "inbox"
    box.mkdir()
    first = _current_watch(box)
    (box / "a.pdf").write_bytes(b"%PDF")
    (box / "a.pdf").unlink()
    assert _current_watch(box) == first, "contents must not change identity"


def test_a_file_where_the_folder_was_is_not_a_usable_watch(tmp_path):
    """stat() succeeds on a regular file; that must not read as healthy."""
    box = tmp_path / "inbox"
    box.mkdir()
    as_dir = _current_watch(box)
    box.rmdir()
    box.write_text("not a folder")
    assert _current_watch(box) != as_dir


def test_the_daemon_reschedules_and_rescans(tmp_path, monkeypatch):
    """End-to-end: delete the inbox mid-run, and the daemon must recover.

    Drives run_daemon's real loop with a fake Observer so the sequence is
    observable: unschedule_all -> schedule -> scan_existing_inbox.
    """
    import watcher.daemon as d

    box = tmp_path / "inbox"
    box.mkdir()

    events = []

    class _FakeObserver:
        def __init__(self):
            self._alive = True
            self._ticks = 0

        def schedule(self, handler, path, recursive=False):
            events.append(("schedule", path))

        def unschedule_all(self):
            events.append(("unschedule_all", None))

        def start(self):
            events.append(("start", None))

        def is_alive(self):
            self._ticks += 1
            # Give the loop enough turns to pass one CHECK_EVERY window.
            return self._ticks < 8

        def stop(self):
            events.append(("stop", None))

        def join(self):
            pass

    class _FakeHandler:
        def __init__(self, *a, **k):
            self.scans = 0

        def scan_existing_inbox(self):
            self.scans += 1
            events.append(("scan", self.scans))
            return 0

        def process_settled(self):
            # Delete the inbox on the first pass through the loop.
            if box.exists() and self.scans >= 1:
                box.rmdir()

    monkeypatch.setattr(d, "Observer", _FakeObserver)
    monkeypatch.setattr(d, "PDFHandler", _FakeHandler)
    monkeypatch.setattr(d, "notify", lambda *a, **k: None)
    # Collapse the real clock so the 30s check fires immediately.
    clock = {"t": 0.0}
    monkeypatch.setattr(d.time, "monotonic", lambda: clock.__setitem__("t", clock["t"] + 60.0) or clock["t"])
    monkeypatch.setattr(d.time, "sleep", lambda _s: None)

    from watcher.config import WatcherConfig
    cfg = WatcherConfig(inbox_dir=box, library_root=tmp_path / "lib",
                        log_dir=tmp_path / "logs", notifications=False)
    (tmp_path / "lib").mkdir()

    d.run_daemon(cfg)

    kinds = [e[0] for e in events]
    assert kinds.count("schedule") >= 2, (
        f"the watch was never rescheduled after the inbox vanished: {events}"
    )
    assert "unschedule_all" in kinds, "the stale watch was never torn down"
    assert box.is_dir(), "the daemon must recreate the folder it watches"
    assert kinds.count("scan") >= 2, (
        "after recovering, the daemon must re-scan for files dropped while "
        "it was deaf -- otherwise they sit there for ever"
    )


def test_recovery_failure_is_logged_and_the_daemon_keeps_running(
    tmp_path, monkeypatch, caplog
):
    """A daemon that dies on a transient error is worse than a deaf one.

    It at least reports "not running", but the owner then has to notice.
    So: log the reason and keep looping.

    This asserts BOTH halves. An earlier draft asserted only that
    run_daemon returned without raising, which the commit gate rejected
    as a test that cannot fail -- correctly: a body that swallowed the
    error silently, or a loop that exited on the first failure, would
    both have passed it.
    """
    import watcher.daemon as d

    box = tmp_path / "inbox"
    box.mkdir()

    observer_state = {"ticks": 0, "stopped": False}

    class _FakeObserver:
        def schedule(self, *a, **k):
            if observer_state["ticks"] > 2:
                raise OSError("kernel said no")

        def unschedule_all(self):
            pass

        def start(self):
            pass

        def is_alive(self):
            observer_state["ticks"] += 1
            return observer_state["ticks"] < 8

        def stop(self):
            observer_state["stopped"] = True

        def join(self):
            pass

    class _FakeHandler:
        def __init__(self, *a, **k):
            pass

        def scan_existing_inbox(self):
            return 0

        def process_settled(self):
            if box.exists():
                box.rmdir()

    monkeypatch.setattr(d, "Observer", _FakeObserver)
    monkeypatch.setattr(d, "PDFHandler", _FakeHandler)
    monkeypatch.setattr(d, "notify", lambda *a, **k: None)
    clock = {"t": 0.0}
    monkeypatch.setattr(d.time, "monotonic", lambda: clock.__setitem__("t", clock["t"] + 60.0) or clock["t"])
    monkeypatch.setattr(d.time, "sleep", lambda _s: None)

    from watcher.config import WatcherConfig
    cfg = WatcherConfig(inbox_dir=box, library_root=tmp_path / "lib",
                        log_dir=tmp_path / "logs", notifications=False)
    (tmp_path / "lib").mkdir()

    import logging
    with caplog.at_level(logging.ERROR, logger=d.logger.name):
        d.run_daemon(cfg)

    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert any("re-establish" in m for m in errors), (
        f"the failure must be logged with its reason, not swallowed: {errors}"
    )
    assert any("kernel said no" in m for m in errors), (
        "the log must carry the underlying cause, or it is undiagnosable"
    )
    # And it must have kept going: the loop runs to its natural end and
    # shuts the observer down, rather than unwinding on the first error.
    assert observer_state["stopped"], "the daemon did not reach normal shutdown"
    assert observer_state["ticks"] >= 7, (
        f"the loop exited early after the failure (ticks={observer_state['ticks']}); "
        f"one failed reschedule must not end the daemon"
    )
