#!/usr/bin/env python3
"""Same-host advisory locking for library write operations.

Audit-11: three writers can touch the library at once — the watcher
daemon (continuous), the weekly maintenance job (Mondays), and the
interactive cockpit.  With no coordination, two destructive batches can
interleave file moves and corrupt each other's state, and two
overlapping weekly runs can reorganize the same papers twice.

This module provides a ``flock``-based advisory lock.  ``flock`` is
*host-local kernel state*: it works reliably between processes on the
same Mac regardless of where the lock file lives, and — crucially — it
is **released automatically when the holding process dies**, so a crash
never leaves a stale lock.  (It does NOT coordinate across machines via
Dropbox; cross-machine writes remain the user's responsibility, but the
realistic concurrency here is same-host.)

The lock file lives under ``<library>/.operation_log/`` next to the undo
log — a hidden infra directory that already exists for every process.

Usage::

    lock = LibraryLock(library_root)
    if not lock.acquire(blocking=False):
        return  # someone else holds it; skip this run
    try:
        ... destructive batch ...
    finally:
        lock.release()

or as a context manager that blocks (with an optional timeout)::

    with LibraryLock(library_root):
        ... destructive batch ...
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import fcntl  # POSIX only (macOS/Linux)
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover -- Windows fallback
    fcntl = None  # type: ignore
    _HAVE_FCNTL = False

DEFAULT_LOCK_NAME = "library-write"


class LibraryLock:
    """An advisory, same-host, auto-released file lock.

    On platforms without ``fcntl`` (Windows) every acquire succeeds and
    the lock is a no-op, preserving single-process behavior.
    """

    def __init__(self, library_root: Path, name: str = DEFAULT_LOCK_NAME):
        self.path = Path(library_root) / ".operation_log" / f"{name}.lock"
        self._fd: Optional[int] = None

    def acquire(self, *, blocking: bool = False, timeout: float = 0.0) -> bool:
        """Try to take the lock.

        * ``blocking=False`` (default): one attempt; return ``True`` if
          acquired, ``False`` if another process holds it.
        * ``blocking=True``: keep retrying until acquired or ``timeout``
          seconds elapse (``timeout=0`` means wait forever).

        Returns whether the lock is now held by this instance.
        """
        if self._fd is not None:
            return True  # already held by us
        if not _HAVE_FCNTL:
            self._fd = -1  # sentinel "held" on unsupported platforms
            return True

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        flags = fcntl.LOCK_EX | fcntl.LOCK_NB
        deadline = time.time() + timeout if (blocking and timeout > 0) else None
        while True:
            try:
                fcntl.flock(fd, flags)
                self._fd = fd
                return True
            except OSError:
                if not blocking:
                    os.close(fd)
                    return False
                if deadline is not None and time.time() >= deadline:
                    os.close(fd)
                    return False
                time.sleep(0.2)

    def release(self) -> None:
        """Release the lock if held.  Safe to call repeatedly."""
        if self._fd is None:
            return
        if self._fd != -1 and _HAVE_FCNTL:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._fd)
            except OSError:
                pass
        self._fd = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def __enter__(self) -> "LibraryLock":
        if not self.acquire(blocking=True, timeout=0):
            raise TimeoutError(f"could not acquire library lock: {self.path}")
        return self

    def __exit__(self, *exc) -> None:
        self.release()
