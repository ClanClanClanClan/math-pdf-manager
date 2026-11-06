"""What the "Maths Library" Dock icon runs: the cockpit, opened with one click.

The step-back audit (D2-2, G1-1, verified 3 of 3) found the cockpit could
be opened only by a Claude session: there was no icon, no launcher, and
every start after 2026-09-05 was Claude's. The owner said yes to a Dock
icon on 2026-11-05. This module is all the icon does, so a fix to it ships
with the code:

* the cockpit already running on current code -> open it;
* not running -> start it on the project's own Python, wait until it
  answers, open it;
* running on OLDER code (a fix landed since it started) -> restart it,
  then open it, so a fix takes effect without anyone at a terminal;
* it cannot start -> say why in a small window, in plain words, and where
  the details are.

Every click is noted in ``~/.mathpdf/cockpit_opened.jsonl``, so whether the
cockpit is used can be measured instead of guessed (audit D2-2: only button
presses were recorded, never an opening).

:func:`install_app` writes the icon itself, ``~/Applications/Maths
Library.app``: a two-line shell script that runs this module.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

#: The cockpit's address on this Mac.
PORT = int(os.environ.get("MATHPDF_COCKPIT_PORT", "8501"))
#: How long a fresh start may take before the icon gives up and says so.
START_WAIT_SECONDS = 90.0
APP_NAME = "Maths Library"


def repo_root() -> Path:
    """``Scripts/``: this file is ``Scripts/src/ui/launcher.py``."""
    return Path(__file__).resolve().parents[2]


def _state_dir() -> Path:
    d = Path.home() / ".mathpdf"
    d.mkdir(parents=True, exist_ok=True)
    return d


def server_state_path() -> Path:
    """Which cockpit this launcher started: pid, port, code version."""
    return _state_dir() / "cockpit_server.json"


def openings_path() -> Path:
    return _state_dir() / "cockpit_opened.jsonl"


def log_path() -> Path:
    return _state_dir() / "cockpit.log"


# --------------------------------------------------------------- the code

def code_version(repo: Path) -> str:
    """The commit the code on disk is at, read from ``.git`` directly (no
    ``git`` binary needed), or "" when it cannot be told."""
    git = repo / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not head.startswith("ref: "):
        return head                                  # detached
    ref = head[len("ref: "):]
    try:
        return (git / ref).read_text(encoding="utf-8").strip()
    except OSError:
        pass
    try:
        for line in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    except OSError:
        pass
    return ""


# ------------------------------------------------------------- the server

def server_answers(port: int = PORT, timeout: float = 1.0) -> bool:
    """Is a cockpit answering on ``port``? Streamlit says "ok" at
    ``/_stcore/health`` once it is ready."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health",
                                    timeout=timeout) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def read_state() -> dict:
    try:
        data = json.loads(server_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _is_our_cockpit(pid: int) -> bool:
    """Is ``pid`` a running ``streamlit run src/ui/cockpit.py``? A pid in an
    old state file may since belong to anything; only ours is stopped."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        out = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    cmd = out.stdout.strip()
    return "streamlit" in cmd and "src/ui/cockpit.py" in cmd


def start_server(repo: Path, port: int = PORT) -> int:
    """Start the cockpit in the background on the project's own Python and
    return its pid. It outlives the click: it runs until stopped or the Mac
    restarts."""
    python = repo / ".venv" / "bin" / "python"
    if not python.exists():
        raise FileNotFoundError(f"the project's Python is missing ({python})")
    env = dict(os.environ, PYTHONPATH="src")
    with open(log_path(), "ab") as log:
        proc = subprocess.Popen(
            [str(python), "-m", "streamlit", "run", "src/ui/cockpit.py",
             "--server.headless", "true", "--server.port", str(port)],
            cwd=str(repo), env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    return proc.pid


def stop_server(pid: int, *, port: int = PORT, wait: float = 15.0) -> bool:
    """Stop OUR cockpit (``pid``) and wait for the port to fall quiet."""
    if not _is_our_cockpit(pid):
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if not server_answers(port, timeout=0.5):
            return True
        time.sleep(0.3)
    return not server_answers(port, timeout=0.5)


@dataclass
class Outcome:
    ok: bool
    what: str            # reused / started / restarted / failed
    reason: str = ""     # for "failed": what went wrong, in plain words
    url: str = ""


def ensure_running(repo: Path, *, port: int = PORT,
                   wait: float = START_WAIT_SECONDS,
                   _sleep: Callable[[float], None] = time.sleep) -> Outcome:
    """Make sure the cockpit is up, on current code. Three-valued at heart:
    reused / started (or restarted) / failed WITH a reason."""
    url = f"http://localhost:{port}"
    version = code_version(repo)
    state = read_state()
    what = "started"
    if server_answers(port):
        running = state.get("code_version", "")
        if not (version and running and running != version):
            return Outcome(True, "reused", url=url)
        # Running older code: a fix has landed since it started.
        if not stop_server(state.get("pid", 0), port=port):
            # Not ours to stop (or it would not stop): open what runs,
            # and say the code may be older, rather than nothing.
            return Outcome(True, "reused", reason="the cockpit could not be "
                           "restarted onto the newest code", url=url)
        what = "restarted"
    try:
        pid = start_server(repo, port)
    except (OSError, subprocess.SubprocessError) as exc:
        return Outcome(False, "failed", reason=f"it could not be started: {exc}")
    try:
        server_state_path().write_text(json.dumps({
            "pid": pid, "port": port, "code_version": version,
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }), encoding="utf-8")
    except OSError:
        pass                        # it still runs; only the restart check is lost
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if server_answers(port):
            return Outcome(True, what, url=url)
        _sleep(0.5)
    return Outcome(False, "failed", reason=(
        f"it did not answer within {int(wait)} seconds"))


# ------------------------------------------------------------ what he sees

def record_opening(outcome: Outcome, version: str) -> None:
    row = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "what": outcome.what, "ok": outcome.ok, "code_version": version}
    if outcome.reason:
        row["reason"] = outcome.reason
    try:
        with open(openings_path(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass


def _log_tail(n: int = 6) -> str:
    try:
        lines = log_path().read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-n:])


def tell(message: str) -> None:
    """A small macOS window with an OK button -- his only channel when the
    cockpit itself is what failed."""
    script = ('display dialog ' + json.dumps(message) + ' with title '
              + json.dumps(APP_NAME) + ' buttons {"OK"} default button "OK"')
    subprocess.run(["osascript", "-e", script], capture_output=True)


def open_in_browser(url: str) -> None:
    subprocess.run(["open", url], capture_output=True)


def main(repo: Optional[Path] = None) -> int:
    repo = repo or repo_root()
    outcome = ensure_running(repo)
    record_opening(outcome, code_version(repo))
    if not outcome.ok:
        tail = _log_tail()
        tell("The library cockpit could not be opened: " + outcome.reason + "."
             + ("\n\nThe last lines it wrote:\n" + tail if tail else "")
             + f"\n\nDetails are in {log_path()}.")
        return 1
    if outcome.reason:
        tell("The cockpit is open, but " + outcome.reason
             + ". Quit and reopen it later to pick up the newest version.")
    open_in_browser(outcome.url)
    return 0


# ------------------------------------------------------------ the icon

_SCRIPT = """#!/bin/sh
# Maths Library: opens the library cockpit (src/ui/launcher.py does the work).
REPO={repo}
cd "$REPO" 2>/dev/null || {{ osascript -e 'display dialog "The Maths library folder could not be found: {repo_plain}" with title "Maths Library" buttons {{"OK"}}'; exit 1; }}
if [ ! -x "$REPO/.venv/bin/python" ]; then
  osascript -e 'display dialog "The library cockpit cannot start: its Python is missing ({repo_plain}/.venv)." with title "Maths Library" buttons {{"OK"}}'
  exit 1
fi
PYTHONPATH=src exec "$REPO/.venv/bin/python" -m ui.launcher
"""

_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>{name}</string>
    <key>CFBundleDisplayName</key><string>{name}</string>
    <key>CFBundleIdentifier</key><string>ch.ethz.dpossamai.mathpdf.cockpit</string>
    <key>CFBundleExecutable</key><string>{name}</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
</dict>
</plist>
"""


def install_app(dest_dir: Optional[Path] = None, repo: Optional[Path] = None) -> Path:
    """Write ``Maths Library.app`` into ``dest_dir`` (default
    ``~/Applications``) and return it. Replaces an older copy of itself."""
    import shlex
    repo = repo or repo_root()
    dest_dir = dest_dir or (Path.home() / "Applications")
    app = dest_dir / f"{APP_NAME}.app"
    macos = app / "Contents" / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)
    (app / "Contents" / "Info.plist").write_text(
        _PLIST.format(name=APP_NAME), encoding="utf-8")
    exe = macos / APP_NAME
    exe.write_text(_SCRIPT.format(repo=shlex.quote(str(repo)),
                                  repo_plain=str(repo).replace("'", "")),
                   encoding="utf-8")
    exe.chmod(0o755)
    return app


if __name__ == "__main__":
    sys.exit(main())
