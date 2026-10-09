"""Renaming or moving ONE paper, by the owner's own choice.

Cockpit audit finding 17 (approved). Every rename in the cockpit was one
the machine proposed -- the filename tidy-up, the title review, Spelling's
suggestion, a conflict's "-v2" -- and there was no way to type a name or
pick a folder for a paper already filed. The only escape was Finder, which
leaves the paper's saved record behind under the old name: an orphan.

This module only JUDGES a requested rename; the move itself goes through
``library_normalize.apply_renames`` -- the same path, lock, undo log and
case-folding / NFD / over-long-name handling as every batch rename -- so
there is one implementation of "rename a paper", not two.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

#: macOS's per-component limit, in BYTES (an accented letter is two).
MAX_NAME_BYTES = 255


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def target_rel(folder_rel: str, stem: str) -> str:
    """The library-relative path a (folder, typed name) pair asks for."""
    stem = _nfc(stem.strip())
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4].rstrip()
    return str(Path(_nfc(folder_rel)) / f"{stem}.pdf")


def check_owner_rename(library_root: Path, old_rel: str,
                       new_rel: str) -> tuple[list, list]:
    """``(problems, warnings)`` for renaming ``old_rel`` to ``new_rel``.

    A problem blocks the rename; a warning is shown and does not. Nothing
    here touches the disk except to look.
    """
    from processing.library_scope import exclusion_reason

    problems: list[str] = []
    warnings: list[str] = []
    old_rel, new_rel = _nfc(old_rel), _nfc(new_rel)
    old, new = library_root / old_rel, library_root / new_rel
    name = new.name
    stem = name[:-4] if name.lower().endswith(".pdf") else name

    if not stem.strip():
        problems.append("The name is empty.")
    if stem != stem.strip():
        problems.append("The name starts or ends with a space.")
    if stem.startswith("."):
        problems.append("A name starting with a dot would hide the file.")
    if any(ord(c) < 32 for c in stem):
        problems.append("The name contains an invisible control character.")
    if ":" in stem:
        warnings.append("A colon shows as a slash (/) in Finder.")
    n_bytes = len(name.encode("utf-8"))
    if n_bytes > MAX_NAME_BYTES:
        problems.append(f"The name is {n_bytes} bytes long; macOS allows "
                        f"{MAX_NAME_BYTES} (an accented letter counts two).")

    # The owner's standing instruction: these collections are left alone,
    # by hand as much as by tooling. Staging is allowed -- this is his own
    # explicit action, not a sweep.
    for label, rel in (("This paper", old_rel), ("That folder", new_rel)):
        why = exclusion_reason(rel, include_staging=True)
        if why is not None:
            problems.append(f"{label} is out of scope: {why}.")

    try:
        if not old.is_file():
            problems.append("The paper is no longer where it was.")
        elif str(old) == str(new):          # both NFC since the top
            problems.append("That is its current name and folder.")
        elif not new.parent.is_dir():
            problems.append("That folder does not exist.")
        elif n_bytes > MAX_NAME_BYTES:
            pass                        # already said; exists() would raise
        elif new.exists():
            # APFS folds case: renaming "space-time" to "Space-time" finds
            # the source itself at the target. Ask the filesystem.
            try:
                same = old.samefile(new)
            except OSError:
                same = False
            if not same:
                problems.append("Another file already has that name in that "
                                "folder.")
    except OSError as exc:              # an unusable path, ENAMETOOLONG, ...
        problems.append(f"That path cannot be used: {exc}")
    return problems, warnings
