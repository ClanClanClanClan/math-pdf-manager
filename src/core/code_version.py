"""Which commit the code on disk is at.

Read from ``.git`` directly, because what asks is a Dock icon and a
background service: neither may depend on a ``git`` binary being on their
PATH. Two things need the answer: the icon, to restart a cockpit running
older code, and the filer, to restart itself (audit G1-4: after a fix, only
Claude or a reboot restarted anything).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def repo_root() -> Path:
    """``Scripts/``: this file is ``Scripts/src/core/code_version.py``."""
    return Path(__file__).resolve().parents[2]


def code_version(repo: Optional[Path] = None) -> str:
    """The commit the code at ``repo`` is at, or "" when it cannot be told."""
    git = (repo or repo_root()) / ".git"
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
