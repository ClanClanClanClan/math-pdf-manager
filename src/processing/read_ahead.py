"""Read the next Sort Queue papers while the owner looks at this one.

Why. MEASURED 2026-10-15 on the real inbox (2,414 papers): 68 papers
always reach the local AI model, and 216 when arXiv is unreachable; the
first is the 59th paper in queue order. With the model already loaded a
read took 7.0-68.3 s (median 36.8 s, n=12), so each of those papers kept
the owner looking at a spinner. They come in runs: 29 of the 67 gaps
between them are 1, and 17 of them sit together among the books.

What. The page calls ``want(next_papers)`` each time it shows a paper,
and ``stop()`` from every other page. One background thread reads them
in order through the same ``extract_metadata_from_pdf`` the page uses.
Its answers land in the lookup cache (``processing.lookup_cache``), so
when a paper comes up the page finds them there instead of reading.

Guarantees, each pressed by a test:

* never blocks the page -- ``want``, ``stop`` and ``status`` hold a lock
  for a few list operations; all reading happens on the thread;
* one thread per process, however many reruns or tabs call ``want`` at
  once; state lives in this imported module, so a rerun of the page
  script finds the same thread;
* one model at a time (``processing.local_model``); a paper this thread
  is reading is not read again by the page, which waits for the answer;
* a paper that vanishes or fails is noted and passed over, never retried
  in a loop; a thread that dies is replaced by the next ``want``;
* ``stop()``: the paper being read is finished (a model read cannot be
  interrupted), nothing more is started, and the model is let go.
  Without ``stop`` (the browser tab was closed), the thread lets the
  model go after ``IDLE_FOR`` seconds with nothing to read.

Reads only. Nothing here writes anywhere but the lookup cache under
``~/.mathpdf/cache``.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from processing import local_model

logger = logging.getLogger(__name__)

#: How many papers past the one on screen are read ahead. The same 25 the
#: page already asks arXiv about in one request, so the papers in between
#: cost ~0.1 s each to pass. A simulation over the real queue order and the
#: measured read times (docs/STATE.md, "the local model reads ahead") put
#: 25 ahead of 10, 5, 3 and 1 at every pace from 5 to 40 s a paper.
WINDOW = 25

#: With nothing to read for this long, the thread ends and the model is
#: let go -- the case where the owner closed the tab instead of leaving
#: the page.
IDLE_FOR = 120.0

_COND = threading.Condition()
_wanted: List[Path] = []
#: (path, mtime_ns, size) -> what reading it gave: a title source
#: ("llm", "arxiv", ...), "no title", or "failed: why".
_finished: Dict[Tuple[str, int, int], str] = {}
_reading: Optional[Path] = None
_thread: Optional[threading.Thread] = None
_stopped = False
_version = 0


def _identity(path: Path) -> Optional[Tuple[str, int, int]]:
    """The file as it is now, or None if it is not there."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (str(path), st.st_mtime_ns, st.st_size)


def enabled() -> bool:
    """``MATHPDF_READ_AHEAD=0`` switches it off (the test suite does)."""
    return os.environ.get("MATHPDF_READ_AHEAD", "").strip() != "0"


def want(paths: Iterable) -> None:
    """Read these papers next, in this order. Returns at once."""
    global _thread, _stopped, _version
    if not enabled():
        return
    paths = [Path(p) for p in paths]
    with _COND:
        _wanted[:] = paths
        _stopped = False
        _version += 1
        _COND.notify_all()
        if paths and (_thread is None or not _thread.is_alive()):
            _thread = threading.Thread(
                target=_work, name="sort-queue-read-ahead", daemon=True)
            _thread.start()


def stop() -> None:
    """The owner left the page: start nothing more. Returns at once."""
    global _stopped, _version
    with _COND:
        _wanted.clear()
        _stopped = True
        _version += 1
        _COND.notify_all()


def status() -> dict:
    """What the page may say about it. Never waits for a read."""
    with _COND:
        wanted = list(_wanted)
        reading = _reading
        running = _thread is not None and _thread.is_alive()
        finished = dict(_finished)
    ready = sum(1 for p in wanted if _identity(p) in finished)
    return {"running": running, "reading": reading, "ready": ready,
            "window": len(wanted), "model_reading": local_model.is_reading()}


def _next() -> Tuple[Optional[Path], Optional[Tuple[str, int, int]]]:
    """The first wanted paper not yet read in its current state."""
    with _COND:
        wanted = list(_wanted)
    for p in wanted:
        ident = _identity(p)
        if ident is None:
            continue                     # gone (filed, moved, synced away)
        with _COND:
            if ident in _finished:
                continue
        return p, ident
    return None, None


def _read(path: Path) -> str:
    """Read one paper exactly as the page would. Never raises Exception."""
    from processing.ingest import extract_metadata_from_pdf

    try:
        meta = extract_metadata_from_pdf(path)
    except Exception as exc:
        logger.warning("read-ahead of %s failed: %s", path.name, exc)
        return f"failed: {exc}"
    if meta.get("extraction_error"):
        return f"failed: {meta['extraction_error']}"
    return meta.get("title_source") or "no title"


def _work() -> None:
    global _thread, _reading
    me = threading.current_thread()
    try:
        with local_model.kept_loaded():
            while True:
                with _COND:
                    seen = _version
                path, ident = _next()
                if path is None:
                    with _COND:
                        if _version != seen:
                            continue     # new papers arrived meanwhile
                        if not _stopped:
                            _COND.wait(timeout=IDLE_FOR)
                        if _version == seen:
                            # Stopped, or idle too long. Decided under the
                            # lock, so a ``want`` after this starts afresh.
                            if _thread is me:
                                _thread = None
                            return
                    continue
                with _COND:
                    _reading = path
                outcome = "failed: the read-ahead thread stopped mid-read"
                try:
                    outcome = _read(path)
                finally:
                    with _COND:
                        _reading = None
                        _finished[ident] = outcome
    finally:
        with _COND:
            _reading = None
            if _thread is me:
                _thread = None
