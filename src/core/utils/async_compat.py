#!/usr/bin/env python3
"""
Async/sync compatibility utilities.

Provides a safe ``run_sync(coro)`` helper that bridges async coroutines
into synchronous code without relying on the deprecated
``new_event_loop()`` / ``set_event_loop()`` pattern.
"""

import asyncio
import threading
from typing import TypeVar

T = TypeVar("T")


def run_sync(coro) -> T:
    """
    Run *coro* synchronously and return its result.

    * If there is **no** running event loop on the current thread, use
      ``asyncio.run()``.
    * If there **is** a running loop (e.g. inside Jupyter or a nested
      sync-from-async call), spin up a **background thread** that
      creates its own loop, avoiding the "cannot run nested event
      loop" error.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        # No running loop — the simple, modern path.
        return asyncio.run(coro)

    # A loop is already running.  Run the coroutine in a background
    # thread with its own event loop.
    result = None
    exception = None

    def _thread_target():
        nonlocal result, exception
        try:
            result = asyncio.run(coro)
        except BaseException as exc:
            exception = exc

    t = threading.Thread(target=_thread_target, daemon=True)
    t.start()
    t.join()

    if exception is not None:
        raise exception

    return result
