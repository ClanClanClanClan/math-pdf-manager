"""The filer runs on the project's own Python, and restarts itself after a fix.

Step-back audit, findings D6-4 and G1-4 (verified 3 of 3). The installed
filer ran on a python.org Python shared with another project: it could not
run the local model, and nothing recorded that; three installers picked
three different Pythons; and after a code fix only Claude or a reboot
restarted anything. The owner said yes to moving it on 2026-11-06.

Now one installer pins ``.venv``, the filer reports which code and which
Python it runs, and when the code on disk moves on it leaves between two
papers, which under launchd's KeepAlive IS restarting onto the new code.
"""
from __future__ import annotations

import json
import os
import plistlib
import sys
from pathlib import Path

import pytest
from hypothesis import given, strategies as hst

import core.code_version as CV
import ui.cockpit_actions as A
import watcher.daemon as D
from watcher import state as S


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


# ----------------------------------------------------------- which Python

def test_the_project_python_is_the_venv_when_there_is_one(tmp_path):
    py = tmp_path / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("")
    assert A.project_python(tmp_path) == str(py)


def test_a_checkout_without_one_has_only_the_running_python(tmp_path):
    assert A.project_python(tmp_path) == sys.executable


def test_the_default_is_this_project(monkeypatch):
    seen = A.project_python()
    root = Path(A.__file__).resolve().parents[2]
    assert seen == A.project_python(root)


@pytest.mark.parametrize("label,start", [(A.WATCHER_LABEL, A.start_watcher),
                                         (A.WEEKLY_LABEL, A.start_weekly)])
def test_each_service_is_installed_on_the_project_python(home, monkeypatch, label, start):
    """Whatever Python happens to be running the cockpit."""
    import subprocess
    monkeypatch.setattr(A, "_launchctl", lambda *a, **k: subprocess.CompletedProcess(
        ["launchctl"], 0, stdout="", stderr=""))
    monkeypatch.setattr(A.sys, "executable", "/some/other/python")
    monkeypatch.setattr(A, "project_python", lambda root=None: "/the/project/.venv/bin/python")
    ok, msg = start()
    assert ok, msg
    plist = plistlib.loads((home / "Library/LaunchAgents" / f"{label}.plist").read_bytes())
    assert "/the/project/.venv/bin/python" in plist["ProgramArguments"]
    assert "/some/other/python" not in plist["ProgramArguments"]


def test_the_weekly_job_from_the_cockpit_runs_on_it_too(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(A, "project_python", lambda root=None: "/the/project/.venv/bin/python")

    def _run(cmd, **k):
        seen["cmd"] = cmd
        raise FileNotFoundError("stop here")

    monkeypatch.setattr(A.subprocess, "run", _run)
    A.run_publication_check(tmp_path)
    assert seen["cmd"][0] == "/the/project/.venv/bin/python"


def test_there_is_one_installer():
    root = Path(A.__file__).resolve().parents[2]
    for gone in ("scripts/install_watcher.sh", "deploy/launchd/install.sh",
                 "scripts/install_weekly_maintenance.sh"):
        assert not (root / gone).exists(), gone


def test_the_monday_service_asks_for_no_filing_and_no_tab():
    root = Path(A.__file__).resolve().parents[2]
    text = (root / "deploy/launchd/ch.ethz.dpossamai.mathpdf.weekly.plist").read_text()
    assert "<string>--no-open</string>" in text


def test_the_spelling_library_is_declared():
    root = Path(A.__file__).resolve().parents[2]
    assert "pyspellchecker" in (root / "pyproject.toml").read_text()
    assert "pyspellchecker" in (root / "requirements.txt").read_text()


# ------------------------------------------------------ what it reports

def test_the_report_says_which_code_and_python(tmp_path):
    S.write_state(tmp_path, pid=1, inbox=tmp_path, watching=True, started_at="t",
                  code_version="abc", python="/x/python")
    got = S.read_state(tmp_path)
    assert (got["code_version"], got["python"]) == ("abc", "/x/python")


# --------------------------------------------------- restarting after a fix

@given(hst.sampled_from(["", "aaa", "bbb"]), hst.sampled_from(["", "aaa", "bbb"]))
def test_property_it_restarts_only_on_two_known_different_versions(running, now):
    import unittest.mock as m
    with m.patch.object(CV, "code_version", return_value=now):
        assert D._code_has_moved_on(running) is (bool(running) and bool(now)
                                                 and running != now)


class _Observer:
    def __init__(self):
        self.ticks, self.stopped = 0, 0

    def schedule(self, *a, **k):
        pass

    def unschedule_all(self):
        pass

    def start(self):
        pass

    def is_alive(self):
        self.ticks += 1
        return self.ticks < 50

    def stop(self):
        self.stopped += 1

    def join(self):
        pass


class _Handler:
    settled = 0

    def __init__(self, *a, **k):
        pass

    def scan_existing_inbox(self):
        return 0

    def process_settled(self):
        type(self).settled += 1


def _run(tmp_path, monkeypatch, versions):
    """The real loop, with a fake Observer and a code version that answers
    from ``versions``, the last one for ever."""
    made = []
    monkeypatch.setattr(D, "Observer", lambda: made.append(_Observer()) or made[-1])
    monkeypatch.setattr(D, "PDFHandler", _Handler)
    monkeypatch.setattr(D, "notify", lambda *a, **k: None)
    monkeypatch.setattr(D, "_auto_reconnect", lambda root: {})
    clock = {"t": 0.0}
    monkeypatch.setattr(D.time, "monotonic",
                        lambda: clock.__setitem__("t", clock["t"] + 60.0) or clock["t"])
    monkeypatch.setattr(D.time, "sleep", lambda _s: None)
    answers = list(versions)
    monkeypatch.setattr(CV, "code_version",
                        lambda repo=None: answers.pop(0) if len(answers) > 1 else answers[0])
    from watcher.config import WatcherConfig
    box = tmp_path / "inbox"
    box.mkdir()
    (tmp_path / "lib").mkdir()
    cfg = WatcherConfig(inbox_dir=box, library_root=tmp_path / "lib",
                        log_dir=tmp_path / "logs", notifications=False)
    D.run_daemon(cfg)
    return made[0], S.read_state(tmp_path / "logs")


def test_a_fix_makes_the_filer_leave_so_launchd_restarts_it(tmp_path, monkeypatch):
    obs, state = _run(tmp_path, monkeypatch, ["aaa", "aaa", "bbb"])
    assert obs.ticks < 49, "it ran on after the code moved"
    assert obs.stopped == 1
    assert state["watching"] is False and state["note"] == "stopped"
    assert state["code_version"] == "aaa" and state["python"] == sys.executable


def test_it_stays_while_the_code_stays(tmp_path, monkeypatch):
    obs, _ = _run(tmp_path, monkeypatch, ["aaa"])
    assert obs.ticks == 50


def test_it_stays_when_the_version_cannot_be_read(tmp_path, monkeypatch):
    """A missing .git must not put it in a restart loop."""
    obs, _ = _run(tmp_path, monkeypatch, ["aaa", ""])
    assert obs.ticks == 50


def test_launchd_keeps_it_alive_so_leaving_is_restarting():
    root = Path(A.__file__).resolve().parents[2]
    plist = (root / "deploy/launchd/ch.ethz.dpossamai.mathpdf.watcher.plist").read_text()
    body = plist.replace("<string>python3</string>", "<string>p</string>")
    got = plistlib.loads(body.encode())
    assert got["KeepAlive"] is True


def test_starting_and_stopping_put_nothing_on_his_screen(tmp_path, monkeypatch):
    """It restarts itself after every fix now; a notice each time would be
    a pop-up nobody asked for. Notices about papers are another matter."""
    src = Path(D.__file__).read_text(encoding="utf-8")
    assert "Watcher Started" not in src and "Watcher Stopped" not in src
