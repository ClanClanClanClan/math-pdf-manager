"""Remembered answers from slow lookups: arXiv, Crossref, the local model.

Why this exists. MEASURED 2026-10-15 on the real "12 - To be sorted"
(2,414 PDFs; 85.5% of them ask arXiv): with arXiv unreachable, a Sort
Queue paper took 10.2-10.9 s to show and 10.1 s more to approve, because
a lookup that failed was never remembered and Approve extracts the paper
again. A paper that then had no title at all went to the local model:
47-72 s to show, 43-66 s again on Approve. With arXiv healthy a paper
took 0.62 s (median), most of it the network.

Every answer has one of three states, never two:

``found``
    The registry knows the paper (or the model answered). Kept
    ``FOUND_TTL`` (30 days).
``absent``
    The registry ANSWERED and has no such paper (arXiv: an empty feed or
    "incorrect id format"; Crossref: 404). Kept ``ABSENT_TTL`` (1 day):
    long enough to cover a sitting, short enough that a transient empty
    reply cannot hide a real paper for long.
``unknown``
    We could not ask, or could not read the reply: offline, timeout,
    server error, rate limit, an answer about some other paper. NEVER
    stored per id -- it must be retried, and it must never be read back
    as "not on arXiv".

A network failure additionally marks the whole service unreachable for
``UNREACHABLE_FOR`` seconds, in this process only, so the next papers
answer ``unknown`` at once instead of each waiting out its own 10 s
timeout. After that window the next lookup asks again.

The store is one JSON file under ``~/.mathpdf/cache/`` -- plumbing, like
the logs and the inbox, never under the library. A file that cannot be
read is treated as empty and replaced on the next write; it is a cache,
and losing it costs only the time to ask again.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

logger = logging.getLogger(__name__)

FOUND = "found"
ABSENT = "absent"
UNKNOWN = "unknown"

FOUND_TTL = 30 * 86400
ABSENT_TTL = 1 * 86400
UNREACHABLE_FOR = 5 * 60

#: A stored timestamp this far in the future is not believed: the clock
#: moved, or the entry is damaged. Either way, ask again.
_CLOCK_SLACK = 300

_TTL = {FOUND: FOUND_TTL, ABSENT: ABSENT_TTL}


@dataclass(frozen=True)
class Answer:
    """One lookup's outcome. ``record`` is empty unless ``state == FOUND``."""

    state: str
    record: dict = field(default_factory=dict)
    reason: str = ""
    cached: bool = False

    @property
    def found(self) -> bool:
        return self.state == FOUND


def cache_path() -> Path:
    """Where the answers live. ``$MATHPDF_LOOKUP_CACHE`` overrides it."""
    env = os.environ.get("MATHPDF_LOOKUP_CACHE", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".mathpdf" / "cache" / "lookups.json"


_LOCK = threading.Lock()
# (path, mtime_ns, size) -> parsed store; one entry, re-read when the file
# changes so a second process's answers are picked up.
_LOADED: Dict[Tuple[str, int, int], dict] = {}
_DOWN: Dict[str, Tuple[float, str]] = {}


def _load(path: Path) -> dict:
    try:
        st = path.stat()
    except OSError:
        return {}
    key = (str(path), st.st_mtime_ns, st.st_size)
    hit = _LOADED.get(key)
    if hit is not None:
        return hit
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        logger.warning("lookup cache %s unreadable, ignoring it: %s", path, exc)
        data = {}
    if not isinstance(data, dict):
        logger.warning("lookup cache %s is not a mapping, ignoring it", path)
        data = {}
    _LOADED.clear()
    _LOADED[key] = data
    return data


def _valid(entry, now: float) -> Optional[Answer]:
    """A stored entry as an Answer, or None if expired or malformed."""
    if not isinstance(entry, dict):
        return None
    state, at, rec = entry.get("state"), entry.get("at"), entry.get("rec", {})
    # (A bool is an int here: True reads as 1 s after 1970, so it expires.)
    if state not in _TTL or not isinstance(at, (int, float)) \
            or not isinstance(rec, dict):
        return None
    if at > now + _CLOCK_SLACK or now - at >= _TTL[state]:
        return None
    if state == FOUND and not rec:
        return None
    return Answer(state, dict(rec) if state == FOUND else {},
                  str(entry.get("reason", "")), cached=True)


def get(namespace: str, key: str, *, now: Optional[float] = None) -> Optional[Answer]:
    """The remembered answer for ``namespace:key``, or None to go and ask."""
    now = time.time() if now is None else now
    with _LOCK:
        return _valid(_load(cache_path()).get(f"{namespace}:{key}"), now)


def put_many(namespace: str, answers: Iterable[Tuple[str, Answer]],
             *, now: Optional[float] = None) -> None:
    """Remember conclusive answers. ``unknown`` ones are refused, by design."""
    now = time.time() if now is None else now
    rows = {}
    for key, ans in answers:
        if ans.state not in _TTL:
            continue                     # unknown is never remembered
        if ans.state == FOUND and not ans.record:
            continue
        rows[f"{namespace}:{key}"] = {
            "state": ans.state, "at": now,
            "rec": dict(ans.record) if ans.state == FOUND else {},
            "reason": ans.reason,
        }
    if not rows:
        return
    path = cache_path()
    with _LOCK:
        data = dict(_load(path))
        # Drop what has expired while we are rewriting anyway, so the file
        # cannot grow without bound.
        data = {k: v for k, v in data.items() if _valid(v, now) is not None}
        data.update(rows)
        try:
            from core.io import atomic_write_text
            atomic_write_text(path, json.dumps(data, ensure_ascii=False))
        except OSError as exc:      # a cache that cannot be written is only slow
            logger.warning("could not save lookup cache %s: %s", path, exc)


def put(namespace: str, key: str, ans: Answer, *, now: Optional[float] = None) -> None:
    put_many(namespace, [(key, ans)], now=now)


def mark_unreachable(service: str, reason: str, *, now: Optional[float] = None) -> None:
    """Stop asking ``service`` for ``UNREACHABLE_FOR`` seconds."""
    now = time.time() if now is None else now
    _DOWN[service] = (now + UNREACHABLE_FOR, reason)


def unreachable(service: str, *, now: Optional[float] = None) -> Optional[str]:
    """Why ``service`` is not being asked right now, or None to go ahead."""
    now = time.time() if now is None else now
    hit = _DOWN.get(service)
    if hit is None:
        return None
    until, reason = hit
    if now >= until:
        _DOWN.pop(service, None)
        return None
    return f"{reason}; next try after {time.strftime('%H:%M', time.localtime(until))}"


def forget_unreachable(service: Optional[str] = None) -> None:
    """Ask again on the next lookup (the owner pressed "try again")."""
    if service is None:
        _DOWN.clear()
    else:
        _DOWN.pop(service, None)


def is_network_failure(exc: BaseException) -> bool:
    """True for failures that say the service could not be reached."""
    try:
        import requests
    except ImportError:              # pragma: no cover - requests is a dependency
        return False
    return isinstance(exc, (requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout))


def plain_failure(exc: BaseException) -> str:
    """Why a request failed, in words the owner can read."""
    try:
        import requests
        if isinstance(exc, requests.exceptions.Timeout):
            return "it did not answer in time"
        if isinstance(exc, requests.exceptions.ConnectionError):
            return "no connection"
    except ImportError:              # pragma: no cover - requests is a dependency
        pass
    return f"the request failed ({type(exc).__name__})"


def is_service_trouble(status_code: int) -> bool:
    """HTTP answers that mean "not now", not "no such paper"."""
    return status_code == 429 or status_code >= 500
