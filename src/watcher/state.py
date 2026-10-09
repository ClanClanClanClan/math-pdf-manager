"""What the running filer says it is watching — written by the daemon, read by the cockpit.

WHY THIS EXISTS. The cockpit's "Automatic filing" badge used to decide
"filing" from ``WatcherConfig.load().inbox_dir.is_dir()`` -- the folder the
COCKPIT resolves now, not the one the running daemon was started with. The
two diverge whenever the config changes after start-up, when the daemon is
launched with ``--inbox``, or when ``_migrate_inbox`` moves the default.
MEASURED on 2026-09-05: the config inbox ``~/.mathpdf/inbox`` existed while
the daemon's actual watch, ``~/Downloads/MathInbox``, had been deleted --
and the badge was green. That is the five-day outage, reproducible on
demand.

Only the daemon knows what it is watching, so it says so: on start-up and
on every 30-second health check it writes one small JSON file. The cockpit
reads it and answers in three values -- filing / not filing / UNKNOWN with
the reason -- instead of guessing.

The file lives in the watcher's configured ``log_dir`` (``~/.mathpdf`` by
default), beside ``watcher.log``. Tests construct a ``WatcherConfig`` with a
temporary ``log_dir``, so they can never write the owner's real one.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STATE_FILENAME = "watcher_state.json"

#: The daemon checks every 30 s. A report older than this means it has
#: stopped reporting, which is not the same thing as "fine".
STALE_AFTER_SECONDS = 180


def state_path(log_dir: Path) -> Path:
    return Path(log_dir) / STATE_FILENAME


def write_state(log_dir: Path, *, pid: int, inbox: Path, watching: bool,
                started_at: str, note: str = "") -> None:
    """Record what this daemon is watching. Never raises.

    A failure to write the report must not take the filer down: a filer
    that files and cannot report is better than one that does neither.
    The cockpit reads a missing or stale report as UNKNOWN, so a silent
    failure here is still visible there.
    """
    payload = {
        "pid": int(pid),
        "inbox": str(inbox),
        "watching": bool(watching),
        "started_at": started_at,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": note,
    }
    try:
        from core.io import atomic_write_text
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        atomic_write_text(state_path(log_dir),
                          json.dumps(payload, ensure_ascii=False, indent=1))
    except Exception:                               # keep filing regardless
        logger.debug("could not write the watcher state file", exc_info=True)


def read_state(log_dir: Path) -> Optional[dict]:
    """The last report, or ``None`` if there is none or it cannot be read."""
    try:
        data = json.loads(state_path(log_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def report_age_seconds(state: dict, now: Optional[datetime] = None) -> Optional[float]:
    """Seconds since the daemon last reported, or ``None`` if unreadable."""
    try:
        checked = datetime.fromisoformat(state["checked_at"])
    except (KeyError, TypeError, ValueError):
        return None
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return (now - checked).total_seconds()


def started_at_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def current_pid() -> int:
    return os.getpid()
