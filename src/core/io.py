#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/io.py - File I/O Operations
Extracted from utils.py to improve modularity
"""

import os
import uuid
import logging
import yaml
from pathlib import Path
from typing import Dict, Set, Union

# Initialize logger
logger = logging.getLogger(__name__)


def atomic_write_text(
    path: Union[str, "os.PathLike[str]"],
    text: str,
    *,
    encoding: str = "utf-8",
) -> None:
    """Write ``text`` to ``path`` atomically and concurrency-safely.

    Why this exists (audit-10): several processes (the cockpit, the
    watcher daemon, the weekly job) write the SAME JSON files — paper
    sidecars and the publication cache — on a Dropbox-synced tree.  The
    old pattern ``path.with_suffix(suffix + '.tmp')`` reused a FIXED
    temp name per target, so two writers raced on the *same* temp file:
    writer B could clobber writer A's temp before A's ``os.replace``,
    yielding a corrupted or lost-update result.  A crash also left that
    fixed ``.tmp`` turd behind forever.

    This helper instead:
      * writes to a UNIQUE temp name (pid + random) in the same
        directory, so concurrent writers never collide on the temp;
      * ``os.replace`` (atomic rename on POSIX) into place;
      * removes its own temp on any failure, leaving no turds.

    Last-writer-wins on the final path is still possible across
    processes (that needs a real lock), but neither the temp nor the
    destination can ever be observed half-written.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Unique per-process, per-call temp sibling.  Keep it in the same
    # directory so ``os.replace`` stays on one filesystem (atomic).
    #
    # Bound the component to the filesystem limit (255 bytes on macOS/APFS &
    # most others): a very long sidecar name (``.<long-filename>.meta.json``)
    # plus the unique suffix can overflow -> OSError ENAMETOOLONG.  The unique
    # pid+uuid suffix is what guarantees no collision, so truncating the
    # (purely cosmetic) embedded name on a byte boundary is safe.
    suffix = f".{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    name = f".{p.name}"
    max_name_bytes = 255 - len(suffix.encode("utf-8")) - 2  # small margin
    nb = name.encode("utf-8")
    if len(nb) > max_name_bytes:
        name = nb[:max_name_bytes].decode("utf-8", "ignore")
    tmp = p.parent / (name + suffix)
    try:
        tmp.write_text(text, encoding=encoding)
        os.replace(tmp, p)
    except BaseException:
        # Best-effort cleanup: never leave a partial temp behind, even
        # on KeyboardInterrupt / SystemExit.
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def cleanup_stale_temps(directory: Union[str, "os.PathLike[str]"]) -> int:
    """Remove leftover ``atomic_write_text`` temps in ``directory``.

    A crash mid-write (before ``os.replace``) can strand a uniquely
    named ``.<name>.<pid>.<rand>.tmp`` sibling.  Call this on a
    directory to sweep them.  Returns the count removed.
    """
    d = Path(directory)
    removed = 0
    try:
        for entry in d.iterdir():
            name = entry.name
            if name.startswith(".") and name.endswith(".tmp") and entry.is_file():
                try:
                    entry.unlink()
                    removed += 1
                except OSError:
                    pass
    except OSError:
        pass
    return removed


def load_yaml_config(path: str) -> Dict:
    """Load YAML configuration file safely."""
    path = os.path.expanduser(path)
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception as exc:  # noqa: BLE001 – robust helper
        logger.error("Unable to read %s: %s", path, exc)
        return {}


def load_word_list(path: str) -> Set[str]:
    """Load word list from file with duplicate checking."""
    path = os.path.expanduser(path)
    out: Set[str] = set()
    try:
        with open(path, encoding="utf-8") as fh:
            for i, raw in enumerate(fh, 1):
                s = raw.strip()
                if not s or s.startswith("#"):
                    continue
                if s in out:
                    logger.warning("Duplicate in %s line %d: %r", path, i, s)
                out.add(s)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unable to read %s: %s", path, exc)
    return out


def debug_print(msg: str) -> None:
    """Print debug message if debugging is enabled."""
    # Import here to avoid circular dependency
    try:
        import core.sentence_case
        if hasattr(core.sentence_case, 'DEBUG_SENTENCE_CASE') and core.sentence_case.DEBUG_SENTENCE_CASE:
            print(f"[DEBUG] {msg}")
    except ImportError:
        # Fallback to utils module
        try:
            from utils import DEBUG_SENTENCE_CASE
            if DEBUG_SENTENCE_CASE:
                print(f"[DEBUG] {msg}")
        except ImportError:
            # If neither is available, don't print debug messages
            pass


# Export all functions
__all__ = [
    'load_yaml_config',
    'load_word_list',
    'debug_print',
    'atomic_write_text',
    'cleanup_stale_temps',
]