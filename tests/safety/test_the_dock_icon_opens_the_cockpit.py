"""The "Maths Library" Dock icon opens the cockpit with no Claude session.

Step-back audit, findings D2-2 and G1-1 (verified 3 of 3): the cockpit
could be opened only by a Claude session -- no icon, no launcher, every
start after 2026-09-05 was Claude's -- and after a code fix only Claude or
a reboot restarted anything (G1-4). The owner said yes to a Dock icon on
2026-11-05. ``ui.launcher`` is what it runs.

Nothing here starts a real server or shows anything on his screen: the
server, the browser and the dialog are replaced, and tests/conftest.py
turns ``open`` and ``osascript`` into ``true`` besides.
"""
from __future__ import annotations

import json
import plistlib
import subprocess
from pathlib import Path

import pytest

import ui.launcher as L


@pytest.fixture(autouse=True)
def _own_home(tmp_path, monkeypatch):
    """Each test its own ~/.mathpdf, so its notes of openings are its own."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "Scripts"
    (r / ".git" / "refs" / "heads").mkdir(parents=True)
    (r / ".git" / "HEAD").write_text("ref: refs/heads/master\n")
    (r / ".git" / "refs" / "heads" / "master").write_text("a" * 40 + "\n")
    (r / ".venv" / "bin").mkdir(parents=True)
    (r / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
    return r


class _Fake:
    """The server, as the launcher sees it."""

    def __init__(self, monkeypatch, *, up=False, ours=True, comes_up_after=1,
                 start_error=None):
        self.up, self.ours, self.after, self.error = up, ours, comes_up_after, start_error
        self.started, self.stopped, self.polls = [], [], 0
        monkeypatch.setattr(L, "server_answers", self.answers)
        monkeypatch.setattr(L, "start_server", self.start)
        monkeypatch.setattr(L, "stop_server", self.stop)

    def answers(self, port=L.PORT, timeout=1.0):
        if self.started and not self.up:
            self.polls += 1
            if self.after is not None and self.polls >= self.after:
                self.up = True
        return self.up

    def start(self, repo, port=L.PORT):
        if self.error:
            raise self.error
        self.started.append(repo)
        self.up = False
        return 4242

    def stop(self, pid, *, port=L.PORT, wait=15.0):
        self.stopped.append(pid)
        if self.ours:
            self.up = False
        return self.ours


def _state(version, pid=777):
    L.server_state_path().write_text(json.dumps({"pid": pid, "code_version": version}))


def _no_sleep(_):
    pass


# --------------------------------------------------------- which code

def test_the_code_version_is_read_from_git_without_git(repo):
    assert L.code_version(repo) == "a" * 40


def test_a_detached_head_and_packed_refs_are_read_too(repo):
    (repo / ".git" / "HEAD").write_text("b" * 40 + "\n")
    assert L.code_version(repo) == "b" * 40
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/other\n")
    (repo / ".git" / "packed-refs").write_text(
        "# pack-refs with: peeled\n" + "c" * 40 + " refs/heads/other\n")
    assert L.code_version(repo) == "c" * 40


def test_no_git_means_an_unknown_version_not_a_crash(tmp_path):
    assert L.code_version(tmp_path) == ""


# ------------------------------------------------- the four outcomes

def test_a_cockpit_on_current_code_is_reused(repo, monkeypatch):
    f = _Fake(monkeypatch, up=True)
    _state("a" * 40)
    out = L.ensure_running(repo, _sleep=_no_sleep)
    assert (out.ok, out.what) == (True, "reused") and not f.started and not f.stopped


def test_one_started_by_someone_else_is_reused_and_left_alone(repo, monkeypatch):
    f = _Fake(monkeypatch, up=True)
    out = L.ensure_running(repo, _sleep=_no_sleep)        # no state file
    assert out.what == "reused" and not f.stopped


def test_a_cockpit_on_older_code_is_restarted(repo, monkeypatch):
    """A fix landed since it started: it must not take a Claude session to
    pick it up (G1-4)."""
    f = _Fake(monkeypatch, up=True)
    _state("0" * 40, pid=777)
    out = L.ensure_running(repo, _sleep=_no_sleep)
    assert (out.ok, out.what) == (True, "restarted")
    assert f.stopped == [777] and f.started == [repo]
    assert L.read_state()["code_version"] == "a" * 40 and L.read_state()["pid"] == 4242


def test_one_that_will_not_stop_is_opened_and_he_is_told(repo, monkeypatch):
    f = _Fake(monkeypatch, up=True, ours=False)
    _state("0" * 40)
    out = L.ensure_running(repo, _sleep=_no_sleep)
    assert out.ok and out.what == "reused" and "newest code" in out.reason
    assert not f.started


def test_none_running_is_started_on_the_projects_python(repo, monkeypatch):
    f = _Fake(monkeypatch, up=False, comes_up_after=3)
    out = L.ensure_running(repo, _sleep=_no_sleep)
    assert (out.ok, out.what, out.url) == (True, "started", f"http://127.0.0.1:{L.PORT}")
    assert f.started == [repo] and L.read_state()["code_version"] == "a" * 40


def test_one_that_never_answers_is_a_failure_with_a_reason(repo, monkeypatch):
    _Fake(monkeypatch, up=False, comes_up_after=None)
    out = L.ensure_running(repo, wait=0.05, _sleep=_no_sleep)
    assert (out.ok, out.what) == (False, "failed")
    assert out.reason.startswith("it did not answer within")


def test_one_that_cannot_start_says_why(repo, monkeypatch):
    _Fake(monkeypatch, up=False, start_error=FileNotFoundError("the project's Python is missing"))
    out = L.ensure_running(repo, _sleep=_no_sleep)
    assert not out.ok and "the project's Python is missing" in out.reason


# --------------------------------------------------- what he sees

def _screen(monkeypatch):
    shown = {"told": [], "opened": []}
    monkeypatch.setattr(L, "tell", lambda m: shown["told"].append(m))
    monkeypatch.setattr(L, "open_in_browser", lambda u: shown["opened"].append(u))
    return shown


def _openings():
    return [json.loads(l) for l in L.openings_path().read_text().splitlines()]


def test_a_click_opens_the_cockpit_once_and_is_noted(repo, monkeypatch):
    shown = _screen(monkeypatch)
    _Fake(monkeypatch, up=True)
    _state("a" * 40)
    assert L.main(repo) == 0
    assert shown == {"told": [], "opened": [f"http://127.0.0.1:{L.PORT}"]}
    (row,) = _openings()
    assert (row["what"], row["ok"], row["code_version"]) == ("reused", True, "a" * 40)


def test_a_failed_click_says_why_opens_nothing_and_is_noted(repo, monkeypatch):
    shown = _screen(monkeypatch)
    _Fake(monkeypatch, up=False, start_error=OSError("no room"))
    L.log_path().write_text("line 1\nTraceback: boom\n")
    assert L.main(repo) == 1
    assert shown["opened"] == []
    (msg,) = shown["told"]
    assert "could not be opened: it could not be started: no room" in msg
    assert "Traceback: boom" in msg and str(L.log_path()) in msg
    (row,) = _openings()
    assert row["ok"] is False and "no room" in row["reason"]


def test_every_click_is_its_own_line(repo, monkeypatch):
    _screen(monkeypatch)
    _Fake(monkeypatch, up=True)
    for _ in range(3):
        L.main(repo)
    assert len(_openings()) == 3


# ------------------------------------------------- the real pieces

def test_the_server_is_started_detached_on_the_projects_python(repo, monkeypatch):
    seen = {}

    class _P:
        pid = 99

        def __init__(self, args, **k):
            seen["args"], seen["k"] = args, k

    monkeypatch.setattr(L.subprocess, "Popen", _P)
    assert L.start_server(repo, 8599) == 99
    assert seen["args"][:5] == [str(repo / ".venv/bin/python"), "-m", "streamlit",
                                "run", "src/ui/cockpit.py"]
    assert seen["args"][-6:] == ["--server.headless", "true", "--server.port", "8599",
                                 "--server.address", "127.0.0.1"], (
        "only this Mac may reach a page that moves his files")
    assert seen["k"]["cwd"] == str(repo) and seen["k"]["env"]["PYTHONPATH"] == "src"
    assert seen["k"]["start_new_session"] is True


def test_without_the_projects_python_nothing_is_started(repo, monkeypatch):
    (repo / ".venv/bin/python").unlink()
    monkeypatch.setattr(L.subprocess, "Popen", lambda *a, **k: pytest.fail("started"))
    with pytest.raises(FileNotFoundError, match="Python is missing"):
        L.start_server(repo)


@pytest.mark.parametrize("pid,cmd,ours", [
    (0, "", False),
    ("7", "", False),
    (7, "/x/python -m streamlit run src/ui/cockpit.py --server.port 8501", True),
    (7, "/usr/bin/vim notes.txt", False),
    (7, "python -m streamlit run other_app.py", False),
])
def test_only_our_cockpit_is_ever_stopped(monkeypatch, pid, cmd, ours):
    monkeypatch.setattr(L.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 0, stdout=cmd + "\n", stderr=""))
    assert L._is_our_cockpit(pid) is ours


def test_stop_never_signals_a_process_that_is_not_ours(monkeypatch):
    monkeypatch.setattr(L, "_is_our_cockpit", lambda pid: False)
    monkeypatch.setattr(L.os, "kill", lambda *a: pytest.fail("signalled a stranger"))
    assert L.stop_server(1234) is False


def test_the_health_check_says_no_when_nothing_listens():
    assert L.server_answers(port=9, timeout=0.2) is False


# --------------------------------------------------------- the icon

def test_the_icon_is_an_app_that_runs_the_launcher(tmp_path, repo):
    app = L.install_app(tmp_path / "Applications", repo)
    assert app.name == "Maths Library.app"
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleExecutable"] == "Maths Library"
    assert info["CFBundlePackageType"] == "APPL"
    exe = app / "Contents" / "MacOS" / "Maths Library"
    assert exe.stat().st_mode & 0o111, "not executable"
    text = exe.read_text()
    assert str(repo) in text and "-m ui.launcher" in text and ".venv/bin/python" in text
    assert subprocess.run(["sh", "-n", str(exe)]).returncode == 0, "the script does not parse"


def test_installing_again_replaces_it(tmp_path, repo):
    a = L.install_app(tmp_path, repo)
    (a / "Contents" / "MacOS" / "Maths Library").write_text("old")
    L.install_app(tmp_path, repo)
    assert "-m ui.launcher" in (a / "Contents" / "MacOS" / "Maths Library").read_text()


def test_the_icon_says_so_when_its_folder_or_python_is_gone(tmp_path, monkeypatch):
    """Run for real, with a stand-in osascript that only writes down what it
    was asked to show -- the first version of this test left a real dialog
    on his screen. The conftest stand-in is asserted too, as a second wall."""
    import os
    import shutil
    assert "quiet-bin" in (shutil.which("osascript") or "")
    rec_bin = tmp_path / "rec-bin"
    rec_bin.mkdir()
    said = tmp_path / "said.txt"
    (rec_bin / "osascript").write_text(f'#!/bin/sh\necho "$@" >> "{said}"\nexit 0\n')
    (rec_bin / "osascript").chmod(0o755)
    env = dict(os.environ, PATH=f"{rec_bin}{os.pathsep}{os.environ['PATH']}")
    gone = tmp_path / "nowhere" / "Scripts"
    exe = L.install_app(tmp_path / "Applications", gone) / "Contents" / "MacOS" / "Maths Library"
    assert subprocess.run(["sh", str(exe)], capture_output=True, env=env).returncode == 1
    assert "folder could not be found" in said.read_text()
    said.unlink()
    gone.mkdir(parents=True)
    assert subprocess.run(["sh", str(exe)], capture_output=True, env=env).returncode == 1
    assert "its Python is missing" in said.read_text()


def test_a_cockpit_that_could_not_be_restarted_opens_and_he_is_told(repo, monkeypatch):
    shown = _screen(monkeypatch)
    _Fake(monkeypatch, up=True, ours=False)
    _state("0" * 40)
    assert L.main(repo) == 0
    assert shown["opened"] == [f"http://127.0.0.1:{L.PORT}"]
    (msg,) = shown["told"]
    assert "could not be restarted onto the newest code" in msg


def test_the_cockpits_own_settings_keep_it_on_this_mac():
    """Whoever starts it -- the icon, the README's command, a Claude
    session -- Streamlit reads this file from Scripts/."""
    import tomllib
    cfg = tomllib.loads((L.repo_root() / ".streamlit" / "config.toml").read_text())
    assert cfg["server"]["address"] == "127.0.0.1"
