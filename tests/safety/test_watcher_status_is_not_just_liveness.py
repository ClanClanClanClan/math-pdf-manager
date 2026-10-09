"""The "Automatic filing" badge must say what the running filer is doing.

THE OUTAGE THIS ENCODES. On 19 Aug 2026 the watcher started, logged
"Watching /Users/.../Downloads/MathInbox for new PDFs...", and ran for
five days and twenty-one hours. At some point the folder was removed.
macOS does not tear down the watch when that happens -- the kqueue just
never fires again -- so the process stayed up, launchctl kept reporting
state = running, and the sidebar kept rendering

    Automatic filing: ON  (running as process 6282)

while nothing was filed. "I didn't look" and "it's fine" came back as the
same value.

TWO MORE WAYS THE BADGE LIED, both confirmed by the 2026-09 cockpit audit
and reproduced live on 2026-10-09:

1. INVERTED. ``launchctl print`` nests ``resource coalition = { state =
   active }`` and ``jetsam coalition = { state = active }`` below the
   service's own ``state = running``. The parser kept the LAST ``state =``
   line, so it answered "OFF" for a live daemon (pid 1531, that day). The
   fixture below is that real output, with the home path redacted.

2. THE WRONG FOLDER. "filing" was decided from the folder the COCKPIT
   resolves now (``WatcherConfig.load().inbox_dir.is_dir()``), not the one
   the daemon is actually watching. The configured ``~/.mathpdf/inbox``
   existed while the daemon's real watch had been deleted, and the badge
   was green. Now the daemon reports what it watches (watcher/state.py)
   and the badge reads that report, answering True / False / None -- where
   None means "cannot confirm" and carries the reason.
"""
from pathlib import Path

import pytest

from ui.cockpit_actions import _service_field, start_watcher, watcher_status
from watcher.state import write_state

FIXTURE = (Path(__file__).resolve().parents[1] / "fixtures" / "launchctl"
           / "print_watcher_running_2026-10-09.txt")


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    """A watcher config whose inbox and log folder we control."""
    box = tmp_path / "MathInbox"
    box.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()

    class _Cfg:
        inbox_dir = box
        log_dir = logs

    import watcher.config as wconfig
    monkeypatch.setattr(wconfig.WatcherConfig, "load", staticmethod(lambda: _Cfg()))
    return _Cfg


def _alive(monkeypatch, running=True, pid=6282, text=None):
    """Make the launchctl layer report a service."""
    import ui.cockpit_actions as actions

    class _Proc:
        returncode = 0
        stdout = text if text is not None else (
            f"\tstate = {'running' if running else 'not running'}\n\tpid = {pid}\n")
        stderr = ""

    monkeypatch.setattr(actions, "_launchctl", lambda *a, **k: _Proc())


def _report(cfg, *, pid=6282, watching=True, inbox=None):
    write_state(cfg.log_dir, pid=pid, inbox=inbox or cfg.inbox_dir,
                watching=watching, started_at="2026-10-09T10:00:00+00:00")


# ------------------------------------------------- 1. the inverted badge

def test_the_real_launchctl_output_reads_as_running():
    """THE REGRESSION, on the bytes launchctl actually printed that day."""
    raw = FIXTURE.read_text(encoding="utf-8")
    assert raw.count("state =") == 3, "fixture must keep the nested states"
    assert _service_field(raw, "state") == "running"
    assert _service_field(raw, "pid") == "1531"


def test_a_nested_state_never_overrides_the_service_state(cfg, monkeypatch):
    """Shallowest wins, in both directions: a nested 'running' must not
    turn a waiting service into a running one either."""
    text = ("gui/501/x = {\n\tstate = waiting\n\tsub = {\n\t\tstate = running\n"
            "\t}\n\tpid = 7\n}\n")
    _alive(monkeypatch, text=text)
    assert watcher_status()["running"] is False


def test_the_live_fixture_through_the_whole_status(cfg, monkeypatch):
    _alive(monkeypatch, text=FIXTURE.read_text(encoding="utf-8"))
    _report(cfg, pid=1531)
    s = watcher_status()
    assert (s["running"], s["pid"], s["filing"]) == (True, 1531, True)


@pytest.mark.parametrize("state,expected", [
    ("running", True), ("not running", False), ("waiting", False), ("exited", False),
])
def test_the_state_line_is_parsed_by_value_not_by_substring(
        cfg, monkeypatch, state, expected):
    """"state = not running" contains the word "running"."""
    _alive(monkeypatch, text=f"\tstate = {state}\n\tpid = 6282\n")
    assert watcher_status()["running"] is expected


# --------------------------------------- 2. filing comes from the daemon

def test_alive_and_reporting_a_live_watch_is_filing(cfg, monkeypatch):
    _alive(monkeypatch)
    _report(cfg)
    s = watcher_status()
    assert (s["running"], s["filing"], s["problem"]) == (True, True, None)


def test_alive_reporting_a_lost_watch_is_not_filing(cfg, monkeypatch):
    """The exact five-day state, as the daemon now reports it."""
    _alive(monkeypatch)
    _report(cfg, watching=False)
    s = watcher_status()
    assert s["running"] is True and s["filing"] is False
    assert str(cfg.inbox_dir) in s["problem"], "must name the folder"


def test_the_configured_folder_existing_proves_nothing(cfg, monkeypatch):
    """The audit's reproduction: the cockpit's folder is fine, the daemon's
    is gone. The old check said ON. Only the daemon's report counts."""
    _alive(monkeypatch)
    assert cfg.inbox_dir.is_dir()
    gone = cfg.inbox_dir.parent / "Downloads" / "MathInbox"
    _report(cfg, watching=False, inbox=gone)
    s = watcher_status()
    assert s["filing"] is False and str(gone) in s["problem"]


def test_no_report_is_UNKNOWN_not_on_and_not_off(cfg, monkeypatch):
    """A daemon started before reporting existed has said nothing.
    Silence must read as "cannot confirm", never as "fine"."""
    _alive(monkeypatch)
    s = watcher_status()
    assert s["filing"] is None
    assert "not reported" in s["problem"]


def test_a_report_from_an_earlier_run_is_UNKNOWN(cfg, monkeypatch):
    _alive(monkeypatch, pid=6282)
    _report(cfg, pid=111)
    s = watcher_status()
    assert s["filing"] is None and "earlier run" in s["problem"]


def test_a_stale_report_is_UNKNOWN(cfg, monkeypatch):
    """A hung daemon stops reporting. Old good news is not news."""
    import watcher.state as wstate
    _alive(monkeypatch)
    _report(cfg)
    monkeypatch.setattr(wstate, "STALE_AFTER_SECONDS", -1)
    s = watcher_status()
    assert s["filing"] is None and "has not reported" in s["problem"]


def test_watching_a_different_folder_than_the_settings_name_is_said(cfg, monkeypatch):
    """Filing works -- into the folder it was started on. Say which."""
    _alive(monkeypatch)
    other = cfg.inbox_dir.parent / "OldInbox"
    other.mkdir()
    _report(cfg, inbox=other)
    s = watcher_status()
    assert s["filing"] is True
    assert str(other) in s["note"] and str(cfg.inbox_dir) in s["note"]
    assert s["inbox"] == other


def test_a_dead_process_is_never_filing_and_is_not_a_fault(cfg, monkeypatch):
    _alive(monkeypatch, running=False)
    _report(cfg)                     # even with a leftover good report
    s = watcher_status()
    assert (s["running"], s["filing"], s["problem"]) == (False, False, None)


def test_filing_is_True_only_with_a_running_process_and_a_live_fresh_report(
        cfg, monkeypatch):
    """The property, over every axis at once."""
    for alive in (True, False):
        for report in ("none", "watching", "lost", "other-pid"):
            sf = cfg.log_dir / "watcher_state.json"
            if sf.exists():
                sf.unlink()
            if report == "watching":
                _report(cfg)
            elif report == "lost":
                _report(cfg, watching=False)
            elif report == "other-pid":
                _report(cfg, pid=99)
            _alive(monkeypatch, running=alive)
            s = watcher_status()
            assert (s["filing"] is True) == (alive and report == "watching"), (alive, report, s)
            if not alive:
                assert s["filing"] is False


def test_every_return_path_carries_the_verdict(cfg, monkeypatch):
    """The launchctl-list fallback and 'not loaded' too. A missing key
    reads as False at the call site -- the silent-failure shape again."""
    import ui.cockpit_actions as actions
    calls = {"n": 0}

    def _two_step(*a, **k):
        calls["n"] += 1

        class _R:
            pass
        r = _R()
        if calls["n"] == 1:
            r.returncode, r.stdout, r.stderr = 1, "", "boom"
        else:
            r.returncode, r.stdout, r.stderr = 0, f"6282\t0\t{actions.WATCHER_LABEL}\n", ""
        return r

    _report(cfg)
    monkeypatch.setattr(actions, "_launchctl", _two_step)
    s = watcher_status()
    assert "filing" in s and s["filing"] is True

    class _Fail:
        returncode, stdout, stderr = 1, "", "Could not find service"
    monkeypatch.setattr(actions, "_launchctl", lambda *a, **k: _Fail())
    s = watcher_status()
    assert "filing" in s and s["filing"] is False


def test_an_unreadable_config_is_UNKNOWN_for_a_running_filer(monkeypatch):
    """Not a crash (a traceback takes the sidebar down) and not "ON"."""
    import watcher.config as wconfig

    def _boom():
        raise OSError("config is shredded")

    monkeypatch.setattr(wconfig.WatcherConfig, "load", staticmethod(_boom))
    _alive(monkeypatch)
    s = watcher_status()
    assert s["filing"] is None
    assert "cannot read the filer's settings" in s["problem"]


def test_starting_the_watcher_rebuilds_a_missing_inbox(cfg, monkeypatch):
    """The sidebar promises restarting rebuilds the folder. Keep it."""
    import ui.cockpit_actions as actions
    cfg.inbox_dir.rmdir()
    monkeypatch.setattr(actions.Path, "home", staticmethod(lambda: cfg.inbox_dir.parent))
    agents = cfg.inbox_dir.parent / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    (agents / f"{actions.WATCHER_LABEL}.plist").write_text("<plist/>")

    class _OK:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(actions, "_launchctl", lambda *a, **k: _OK())
    ok, _ = start_watcher()
    assert ok and cfg.inbox_dir.is_dir()
