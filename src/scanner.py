#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scanner.py — robust, paranoid, and platform-aware directory scanner.

Highlights
~~~~~~~~~~
* 🔒  Deduplicates hard links (inode+device) or absolute path on Windows.
* 🪢  Optionally follows symlinks while guarding against cycles.
* 😎  Clean logging (no bare *print*), tqdm progress, JSON output option.
* 📂  Folder-structure audit + CSV report.
* 🛠️  100 % typed, **Pathlib-first**, zero global side-effects.

© 2025, released under the MIT Licence.

FIXED: Handle non-existent paths gracefully by returning empty list instead of raising FileNotFoundError.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

try:
    from tqdm import tqdm  # type: ignore
except ImportError:                          # pragma: no cover
    def tqdm(x: Iterable, **kwargs):         # type: ignore
        """Poor-man fallback when *tqdm* is not installed."""
        return x

__all__ = [
    "is_hidden",
    "is_symlink",
    "get_file_metadata",
    "scan_directory",
    "audit_folder_structure",
    "write_audit_report",
]

# --------------------------------------------------------------------------- #
#  Logging                                                                     #
# --------------------------------------------------------------------------- #

logger = logging.getLogger("scanner")
if not logger.handlers:  # respectful of re-importing in test runs
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )

# --------------------------------------------------------------------------- #
#  Helpers                                                                     #
# --------------------------------------------------------------------------- #

def is_hidden(filepath: os.PathLike | str) -> bool:
    """
    Return *True* iff *filepath* **or one of its ancestors** begins with a dot
    ( '.' ) **and** is not the literal "." or "..".

    This definition matches the common POSIX notion of *hidden* while avoiding
    mis-flagging path elements produced by "..".
    """
    return any(
        part.startswith(".") and part not in (".", "..")
        for part in Path(filepath).parts
    )


def is_symlink(path: os.PathLike | str) -> bool:
    """
    Lightweight wrapper around :py:meth:`Path.is_symlink`.

    On some network file-systems or Windows without developer-mode, calling
    :pymeth:`Path.is_symlink` may raise ; we swallow such exceptions and report
    *False* instead of crashing.
    """
    try:
        return Path(path).is_symlink()
    except Exception:
        return False


def _unique_key(stat_result: os.stat_result, abs_path: Path) -> Tuple[int | str, int | None]:
    """
    Construct a deduplication key.

    * **POSIX**: ``(st_ino, st_dev)``
    * **Windows**: ``st_ino`` is always 0 – fall back to the absolute path string.
    """
    if getattr(stat_result, "st_ino", 0):
        return stat_result.st_ino, stat_result.st_dev
    return abs_path.as_posix(), None


def get_file_metadata(path: os.PathLike | str) -> Dict[str, Any]:
    """
    Extract metadata for *path*. **Never** raises – on error the ``"error"``
    field is populated and all numeric metadata set to *None*.
    """
    p = Path(path).expanduser()
    meta: Dict[str, Any] = {
        "path": str(p.resolve()),
        "name": p.name,
        "folder": str(p.parent.resolve()),
        "ext": p.suffix.lower(),
        "size": None,
        "is_symlink": False,
        "error": None,
        "inode": None,
        "device": None,
    }
    try:
        st = p.stat()
        meta["is_symlink"] = p.is_symlink()
        meta["size"] = st.st_size
        meta["inode"] = getattr(st, "st_ino", None)
        meta["device"] = getattr(st, "st_dev", None)
    except Exception as exc:  # pragma: no cover (hard to reach deterministically)
        meta["error"] = f"Error accessing file: {exc}"
        logger.warning("Could not stat %s: %s", p, exc)
    return meta

# --------------------------------------------------------------------------- #
#  Core scanning routine                                                       #
# --------------------------------------------------------------------------- #

def scan_directory(
    base_path: os.PathLike | str,
    *,
    allowed_extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    include_hidden: bool = False,
    follow_symlinks: bool = False,
    min_size_bytes: Optional[int] = None,
    log_errors: bool = True,
    file_limit: Optional[int] = None,
    show_progress: bool = True,
) -> List[Dict[str, Any]]:
    """
    Recursively scan *base_path* and return a **list** of file-metadata dicts.

    Parameters
    ----------
    base_path
        Folder to start the walk from.
    allowed_extensions
        List of extensions (case-insensitive, leading dot required). Defaults
        to ``[".pdf"]``.
    exclude_dirs
        Directory names (not paths) to skip regardless of depth.
    include_hidden
        If *False*, ignore dot-files and dot-folders.
    follow_symlinks
        Follow directory symlinks / junctions; a guard prevents infinite loops.
    min_size_bytes
        Skip files smaller than this threshold.
    file_limit
        Hard stop after N files.
    show_progress
        Display a tqdm progress bar (one "unit" per directory).
    """
    root = Path(base_path).expanduser()

    # FIXED: Return empty list instead of raising FileNotFoundError for non-existent paths
    if not root.exists():
        msg = f"Base path does not exist: {root}"
        if log_errors:
            logger.error(msg)
        return []

    allowed_exts: Set[str] = {e.lower() for e in (allowed_extensions or [".pdf"])}
    exclude_dir_set: Set[str] = set(exclude_dirs or [])

    seen: Set[Tuple[int | str, int | None]] = set()
    visited_real_dirs: Set[str] = set()
    out: List[Dict[str, Any]] = []
    n_files = 0

    walker: Iterable[Tuple[str, List[str], List[str]]] = os.walk(
        root, followlinks=follow_symlinks
    )
    if show_progress:
        walker = tqdm(walker, desc="Scanning", unit="dir", ncols=88)

    for dirpath, subdirs, filenames in walker:
        dir_path = Path(dirpath)
        real_dir = dir_path.resolve()

        # ----- Symlink-cycle guard ----------------------------------------- #
        if follow_symlinks:
            if str(real_dir) in visited_real_dirs:
                subdirs[:] = []  # prune descent
                continue
            visited_real_dirs.add(str(real_dir))

        # ----- In-place directory filter ----------------------------------- #
        original_subdirs = list(subdirs)
        subdirs[:] = [
            d for d in subdirs
            if d not in exclude_dir_set and (include_hidden or not d.startswith("."))
        ]
        if original_subdirs != subdirs and logger.isEnabledFor(logging.DEBUG):
            skipped = set(original_subdirs) - set(subdirs)
            logger.debug("Skipping directories in %s: %s", dir_path, ", ".join(skipped))

        # ----- File loop ---------------------------------------------------- #
        for fname in filenames:
            file_path = dir_path / fname
            ext = file_path.suffix.lower()

            if (  # hidden filters
                (not include_hidden and fname.startswith(".")) or
                (not include_hidden and is_hidden(file_path))
            ):
                continue

            if ext not in allowed_exts:
                continue

            # Robust metadata collection
            meta = get_file_metadata(file_path)

            # Size threshold
            if (
                min_size_bytes is not None
                and meta["size"] is not None
                and meta["size"] < min_size_bytes
            ):
                continue

            # Deduplication
            try:
                st = file_path.stat()
            except Exception:
                st = file_path.lstat()
            key = _unique_key(st, file_path)
            if key in seen:
                continue
            seen.add(key)

            out.append(meta)
            n_files += 1
            if file_limit and n_files >= file_limit:
                logger.info("File scan limit reached (%s)", file_limit)
                return out

    logger.info("Scanned %s unique files in %s", n_files, root)
    return out

# --------------------------------------------------------------------------- #
#  Folder-audit utilities                                                      #
# --------------------------------------------------------------------------- #

def audit_folder_structure(base_path: os.PathLike | str, config_folders: List[str]) -> Dict[str, Any]:
    """
    Compare the **actual** directory tree under *base_path* with
    *config_folders* (interpreted relative to *base_path*).  Returns

    ``{"missing": [...], "extra": [...], "ok": [...]}``
    """
    root = Path(base_path).expanduser().resolve()
    expected: Set[Path] = {(root / f).resolve() for f in config_folders}

    actual: Set[Path] = set()
    for r, dirs, _ in os.walk(root):
        for d in dirs:
            actual.add((Path(r) / d).resolve())

    missing = sorted(map(str, expected - actual))
    extra = sorted(map(str, actual - expected))
    ok = sorted(map(str, expected & actual))

    if missing:
        logger.warning("Missing expected folders: %s", missing)
    if extra:
        logger.warning("Extra folders not in config: %s", extra)
    if not missing and not extra:
        logger.info("Folder structure matches the configuration.")
    return {"missing": missing, "extra": extra, "ok": ok}


def write_audit_report(
    audit: Dict[str, Any],
    output_path: os.PathLike | str = "folder_audit_report.csv",
) -> None:
    """
    Write *audit* (see :pyfunc:`audit_folder_structure`) to CSV with header
    ``Type,Folder``.  Errors propagate – callers decide how to handle them.
    """
    out = Path(output_path)
    with out.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["Type", "Folder"])
        for kind in ("missing", "extra", "ok"):
            for folder in audit[kind]:
                writer.writerow([kind, folder])
    logger.info("Audit report written to %s", out)

# --------------------------------------------------------------------------- #
#  CLI                                                                        #
# --------------------------------------------------------------------------- #

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:  # pragma: no cover
    parser = argparse.ArgumentParser(description="Scan a directory for files (robust and paranoid).")
    parser.add_argument("path", type=str, help="Root directory to scan")
    parser.add_argument("--exclude", type=str, nargs="*", default=[], help="Subfolder names to exclude")
    parser.add_argument("--ext", type=str, nargs="*", default=[".pdf"], help="File extensions (with dot, e.g. .pdf .tex)")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files and folders")
    parser.add_argument("--follow-symlinks", action="store_true", help="Follow directory symlinks")
    parser.add_argument("--min-size", type=int, default=None, help="Minimum file size in bytes")
    parser.add_argument("--audit-config", type=str, help="YAML config for folder structure audit (uses folder_categories)")
    parser.add_argument("--audit-report", type=str, help="Path for CSV audit report", default="folder_audit_report.csv")
    parser.add_argument("--file-limit", type=int, help="Max number of files to scan", default=None)
    parser.add_argument("--no-progress", action="store_true", help="Disable progress bar")
    parser.add_argument("--json", action="store_true", help="Emit scan results as JSON lines")
    return parser.parse_args(argv)


def _cli() -> None:  # pragma: no cover
    import yaml

    args = _parse_args()

    results = scan_directory(
        args.path,
        allowed_extensions=args.ext,
        exclude_dirs=args.exclude,
        include_hidden=args.include_hidden,
        follow_symlinks=args.follow_symlinks,
        min_size_bytes=args.min_size,
        file_limit=args.file_limit,
        show_progress=not args.no_progress,
    )

    if args.json:
        for rec in results:
            print(json.dumps(rec, ensure_ascii=False, sort_keys=True))
    else:
        for rec in results:
            print(rec)

    if args.audit_config:
        with open(args.audit_config, "r", encoding="utf-8") as fp:
            cfg = yaml.safe_load(fp) or {}
        cats = cfg.get("folder_categories", {})
        folders: List[str] = []
        for node in cats.values():
            if isinstance(node, list):
                folders.extend(node)
            elif isinstance(node, dict):
                for sub in node.values():
                    if isinstance(sub, list):
                        folders.extend(sub)
        base = Path(cfg.get("base_maths_folder", args.path)).expanduser()
        aud = audit_folder_structure(base, folders)
        write_audit_report(aud, args.audit_report)


if __name__ == "__main__":  # pragma: no cover
    _cli()