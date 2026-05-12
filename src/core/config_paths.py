"""Single source of truth for locating config and data files.

Historically ``sentence_case.py`` and ``arxivbot/models/cmo.py`` independently
hunted for ``config/config.yaml`` and ``data/name_dash_whitelist.txt`` along
slightly different search paths. When the cwd differed from the project root,
they could load different whitelists, producing inconsistent sentence-case
output between the validator and the canonical-filename generator.

This module exposes one ``find_project_root()`` plus helpers that always look
relative to that root (never cwd).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable, Optional, Set

logger = logging.getLogger(__name__)


def get_library_root() -> Path:
    """Return the math-PDF library root.

    Resolution order:
      1. ``$MATH_LIBRARY`` environment variable (expanduser applied).
      2. ``DEFAULT_LIBRARY_ROOT`` from :mod:`constants` (the user's Dropbox
         path on their main machine).

    This indirection keeps the user-specific Dropbox path out of every
    module — it's only mentioned in ``constants.py`` (which is allow-listed
    by the ``test_no_dropbox_paths_in_src`` security audit).
    """
    env = os.environ.get("MATH_LIBRARY", "").strip()
    if env:
        return Path(env).expanduser()
    try:
        from constants import DEFAULT_LIBRARY_ROOT
        return DEFAULT_LIBRARY_ROOT
    except ImportError:
        # Fallback if constants module is unavailable (e.g. partial install)
        return Path.home() / "Maths"


def find_project_root() -> Path:
    """Return the math-pdf project root (the dir that contains ``src/``).

    Detection: this file lives at ``src/core/config_paths.py``, so the project
    root is three ``parent`` hops up.
    """
    return Path(__file__).resolve().parent.parent.parent


def config_path(filename: str = "config.yaml") -> Optional[Path]:
    """Return the absolute path to a file under ``config/``, or None."""
    p = find_project_root() / "config" / filename
    return p if p.exists() else None


def data_path(filename: str) -> Optional[Path]:
    """Return the absolute path to a file under ``data/``, or None."""
    p = find_project_root() / "data" / filename
    return p if p.exists() else None


def load_set_from_files(*filenames: str) -> Set[str]:
    """Load newline-delimited entries from one or more files under ``data/``.

    Comments (``#``) and blank lines are ignored. The union of all files is
    returned. Files that don't exist are silently skipped.
    """
    out: Set[str] = set()
    root = find_project_root()
    for fname in filenames:
        p = root / "data" / fname
        if not p.exists():
            logger.debug("Optional data file not found: %s", p)
            continue
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    out.add(line)
        except OSError as exc:
            logger.warning("Cannot read %s: %s", p, exc)
    return out


def load_yaml_section(*keys: str, filename: str = "config.yaml") -> object:
    """Load a (possibly nested) section from ``config/<filename>``.

    ``load_yaml_section("capitalization_whitelist")`` returns the top-level
    key. ``load_yaml_section("exceptions", "capitalization_whitelist")``
    walks into nested sections. Returns ``None`` if any step is missing or
    the file is unreadable.
    """
    p = config_path(filename)
    if p is None:
        logger.debug("Config file not found: %s", filename)
        return None
    try:
        import yaml
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning("Cannot load YAML from %s: %s", p, exc)
        return None
    cur: object = data
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur
