"""The local AI model: one at a time, and loaded once while reading ahead.

MEASURED 2026-10-15 on the real inbox (Apple M3, 24 GB, the 4.7 GB
fine-tuned Qwen 7B, a busy machine): with the model already loaded,
reading one paper took 7.0-68.3 s (median 36.8 s, n=12); loading it took
1.2-1.4 s more from a warm disk cache, 9.3 s otherwise (27 s seen
earlier), and it then holds 4.4 GB of memory.

Two things follow, and this module is where both are enforced.

* **One model per process.** Every read takes ``TURN``. Two readers --
  the Sort Queue page and its read-ahead thread -- never load two copies
  of a 4.7 GB file side by side, and a paper being read by one is not
  read again by the other: the second waits for the turn, then finds the
  answer already remembered (``processing.ingest._llm_extract_remembered``
  checks again once it holds the turn).
* **Loaded between papers only while someone asked for it.** Inside a
  ``kept_loaded()`` block the model stays loaded from one read to the
  next; outside one, every read loads, reads and lets go, as before. Only
  the read-ahead keeps it, and only while the owner is on the Sort Queue
  page; the watcher, bulk sort and Approve never hold 4.7 GB idle.
"""
from __future__ import annotations

import contextlib
import logging
import threading
from pathlib import Path
from typing import Iterator, Optional, Tuple

logger = logging.getLogger(__name__)

#: Held for the whole of a model read, and while the model is loaded or let
#: go. Re-entrant, so a caller may hold it around ``read`` to check a cache
#: and read as one step.
TURN = threading.RLock()

_held = None                                   # the loaded extractor
_held_for: Optional[Tuple] = None              # (class, model identity)
_keepers = 0                                   # open kept_loaded() blocks
_reading = False                               # a read is under way
#: How many times this process has loaded a model (read by tests).
loads = 0


def _identity(model_path) -> Tuple:
    """A retrained model (same name, new size or time) is a new model."""
    p = Path(model_path)
    try:
        st = p.stat()
    except OSError:
        return (str(p), None, None)
    return (str(p), st.st_size, st.st_mtime_ns)


def _let_go() -> None:
    """Release the loaded model. The caller holds ``TURN``."""
    global _held, _held_for
    held, _held, _held_for = _held, None, None
    if held is not None:
        try:
            held.close()
        except Exception as exc:        # it is going away either way
            logger.warning("closing the local model failed: %s", exc)


def read(extractor_cls, model_path, text: str):
    """Have the model read ``text`` and return its answer.

    Loads the model unless the one already loaded is the same class and
    the same file. Lets it go afterwards unless a ``kept_loaded()`` block
    is open, and always after a failed read: a model that broke mid-read
    is not handed to the next reader.
    """
    global _held, _held_for, _reading, loads
    with TURN:
        want = (extractor_cls, _identity(model_path))
        if _held is not None and _held_for != want:
            _let_go()
        if _held is None:
            _held = extractor_cls(model_path=model_path)
            _held_for = want
            loads += 1
        _reading = True
        try:
            return _held.extract(text)
        except BaseException:
            _let_go()
            raise
        finally:
            _reading = False
            if _keepers == 0:
                _let_go()


@contextlib.contextmanager
def kept_loaded() -> Iterator[None]:
    """Keep the model loaded from one read to the next, until this ends.

    Ending waits for a read in progress (by anyone) to finish, then lets
    the model go if no other block is still open.
    """
    global _keepers
    with TURN:
        _keepers += 1
    try:
        yield
    finally:
        with TURN:
            _keepers -= 1
            if _keepers == 0:
                _let_go()


def is_loaded() -> bool:
    """True while a model is loaded in this process. Never waits."""
    return _held is not None


def is_reading() -> bool:
    """True while a read is under way in this process. Never waits."""
    return _reading
