"""The lines at the top of Home: what is waiting, and is everything running?

Step-back audit D8-4, G1-2, G1-3: failures reached only log files, and the
sidebar said "Automatic filing: ON" over a filer that has never filed a real
paper while the pile grew. Each line here says OK, a problem, or that it
cannot tell and why; "note" is for what is simply so (papers waiting is not
a fault). Reads only; nothing here writes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from maintenance import job_runs as J

NOTE = "note"
#: The put-back runs hourly; a note older than this means it has stopped.
PUT_BACK_STALE_HOURS = 3
WEEK_SECONDS = 7 * 86400


@dataclass
class StatusLine:
    name: str
    state: str          # J.OK, J.PROBLEM, J.UNKNOWN or NOTE
    text: str


def waiting(library_root: Path, *, now: Optional[float] = None) -> dict:
    """``{"count", "this_week", "unread"}`` for "12 - To be sorted". ``count``
    is None when the folder is not there. ``unread``: folders and files it
    could not look at, so a count that is not the whole answer says so."""
    from organization.system import TO_BE_SORTED
    from processing.identity import iter_pdfs
    base = Path(library_root) / TO_BE_SORTED
    if not base.is_dir():
        return {"count": None, "this_week": 0, "unread": 0}
    now = time.time() if now is None else now
    unread: list = []
    count = recent = 0
    for pdf in iter_pdfs(base, on_unreadable=lambda folder, _exc: unread.append(folder)):
        count += 1
        try:
            st = pdf.stat()
        except OSError:
            unread.append(pdf)
            continue
        if now - getattr(st, "st_birthtime", st.st_mtime) < WEEK_SECONDS:
            recent += 1
    return {"count": count, "this_week": recent, "unread": len(unread)}


def _waiting_line(library_root: Path, now: Optional[float]) -> StatusLine:
    w = waiting(library_root, now=now)
    name = "Papers waiting"
    if w["count"] is None:
        return StatusLine(name, J.UNKNOWN, 'the folder "12 - To be sorted" was not found')
    text = f'{w["count"]:,} in "12 - To be sorted", {w["this_week"]} arrived this week'
    if w["unread"]:
        return StatusLine(name, J.UNKNOWN, f'{text}; {w["unread"]} could not be looked at')
    return StatusLine(name, NOTE if w["count"] else J.OK, text)


def _filer_line(watcher: dict, running_code: str, code_now: str) -> StatusLine:
    name = "Filer"
    if not watcher.get("running"):
        return StatusLine(name, J.PROBLEM, "it is not running")
    filing = watcher.get("filing")
    if filing is False:
        return StatusLine(name, J.PROBLEM, watcher.get("problem") or "it is not filing")
    if filing is None:
        return StatusLine(name, J.UNKNOWN, watcher.get("problem") or "no report from it")
    if running_code and code_now and running_code != code_now:
        return StatusLine(name, NOTE, "running; it restarts itself onto the new code "
                                      "within a minute")
    return StatusLine(name, J.OK, 'running on the current code. It files only what '
                                  'reaches its own folder, not "12 - To be sorted"')


def _ago(seconds: float) -> str:
    if seconds < 3600:
        return f"{max(int(seconds // 60), 1)} min ago"
    if seconds < 2 * 86400:
        return f"{int(seconds // 3600)} h ago"
    return f"{int(seconds // 86400)} days ago"


def _put_back_line(log_dir: Optional[Path], now: Optional[float]) -> StatusLine:
    name = "Putting back saved details"
    run = J.last_run(J.PUT_BACK, log_dir=log_dir)
    if run is None:
        return StatusLine(name, J.UNKNOWN, "no run noted yet (it runs hourly)")
    try:
        when = datetime.fromisoformat(run["time"])
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        age = (time.time() if now is None else now) - when.timestamp()
    except (KeyError, TypeError, ValueError):
        return StatusLine(name, J.UNKNOWN, "its last note cannot be read")
    if age > PUT_BACK_STALE_HOURS * 3600:
        return StatusLine(name, J.UNKNOWN, f"last ran {_ago(age)}, so it may have stopped")
    return StatusLine(name, run.get("state", J.UNKNOWN),
                      f"{_ago(age)}: {run.get('text', '')}")


def gather(library_root: Path, *, watcher: dict, running_code: str, code_now: str,
           sweep: StatusLine, log_dir: Optional[Path] = None,
           now: Optional[float] = None) -> list:
    """The lines, in the order they show. ``watcher``, the filer's code and
    ``sweep`` come from the caller, which already has them cached."""
    return [_waiting_line(library_root, now),
            _filer_line(watcher, running_code, code_now),
            _put_back_line(log_dir, now),
            sweep]
