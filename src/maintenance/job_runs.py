"""One line per background run: OK, a problem in plain words, or unknown.

Step-back audit G1-3 and D12-3: the hourly job failed 21 times in a row (38
by 2026-11-06) and no screen knew, because failures went only to a log file
he never sees; and a quiet pass logged nothing at all, so "ran, nothing to
do" could not be told from "did not run". Each background job now writes one
line here after every run, and Home reads them.

Three values, never two (non-negotiable 4): ``unknown`` is "could not tell",
with the reason, and is not "ok".
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OK, PROBLEM, UNKNOWN = "ok", "problem", "unknown"
FILENAME = "job_runs.jsonl"
#: Enough history for a streak and a look back, and no more.
KEEP_LINES = 500

PUT_BACK = "put-back"
MONDAY_SWEEP = "monday-sweep"


def runs_path(log_dir: Optional[Path] = None) -> Path:
    return Path(log_dir or Path.home() / ".mathpdf") / FILENAME


def record_run(job: str, state: str, text: str, *,
               log_dir: Optional[Path] = None) -> None:
    """Note one run. Never raises: a job that worked must not fail because
    its note could not be written (Home then shows the last note's age)."""
    path = runs_path(log_dir)
    line = json.dumps({
        "job": job, "state": state, "text": text,
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        old = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        from core.io import atomic_write_text
        atomic_write_text(path, "\n".join((old + [line])[-KEEP_LINES:]) + "\n",
                          encoding="utf-8")
    except (OSError, ValueError) as exc:
        logger.warning("could not note the run of %s: %s", job, exc)


def runs(job: str, *, log_dir: Optional[Path] = None) -> list:
    """This job's runs, oldest first. A damaged line is passed over."""
    try:
        lines = runs_path(log_dir).read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return []
    out = []
    for raw in lines:
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("job") == job:
            out.append(row)
    return out


def last_run(job: str, *, log_dir: Optional[Path] = None) -> Optional[dict]:
    found = runs(job, log_dir=log_dir)
    return found[-1] if found else None


def just_failed_twice(job: str, *, log_dir: Optional[Path] = None) -> bool:
    """Has this job failed exactly twice in a row, just now? Exactly: a notice
    on every later failure would be a pop-up an hour."""
    states = [r.get("state") for r in runs(job, log_dir=log_dir)]
    return (len(states) >= 2 and states[-2:] == [PROBLEM, PROBLEM]
            and (len(states) == 2 or states[-3] != PROBLEM))
