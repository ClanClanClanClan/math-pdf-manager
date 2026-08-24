"""One answer to "should this file be touched?", for the whole project.

Before this module every tool carried its own private skip list -- a
``SKIP_PREFIXES`` tuple in ``duplicate_finder``, a ``_STAGING_DIR`` string in
``library_normalize``, a ``TO_BE_SORTED`` constant in ``organization.system``,
and a hard-coded set in each ad-hoc sweep.  They did not agree, and each new
tool started by forgetting something.  The owner has had to say "leave those
alone" more than once, which is a defect in the code, not in his patience.

Scope is not a preference and it is not a tunable.  It is a fact about what
this library contains, so it lives in one place and everything asks.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

__all__ = [
    "NON_LIBRARY", "STAGING", "ARCHIVAL_COLLECTIONS",
    "exclusion_reason", "in_scope", "filter_in_scope",
]

#: Not the library at all: the code that manages it, backups, scratch.
NON_LIBRARY = (
    "Scripts",
    "archive",
    "gmnap",
    "gmnap-archive",
    "gmnap-clean",
    "gmnap-private-eval-backup",
    "unicode_utils",
    ".trash",
)

#: Staging.  These PDFs have not been renamed yet, so measuring naming
#: conformance on them measures nothing: they are *supposed* to be wrong.
STAGING = (
    "12 - To be sorted",
    "04 - Papers to be downloaded",
)

#: ARCHIVAL COLLECTIONS -- the owner's standing instruction, given more than
#: once:
#:
#:     "JEHPS and all the Comptes-rendus (actually the whole folders
#:      00 - Histoire de l'academie royale des sciences,
#:      01 - Comptes rendus hebdomadaires de l'academie des sciences,
#:      02 - Memoires presentes par divers savants ...,
#:      and 11 - Lviv Scottish book) should always be left alone: they are
#:      too different from everything else. We might at some point want to do
#:      dedicated work with those (mostly completing collections and ensuring
#:      that they are properly named), but they are orthogonal to everything
#:      else."
#:
#: These are bound volumes of 17th-to-20th-century academy proceedings and one
#: scanned notebook.  They have no author in the ordinary sense, their titles
#: are volume designations, and every naming, spelling, duplicate and topic
#: rule written for papers is wrong about them.  2,341 files.
#:
#: Excluded from sweeps -- NOT hidden.  They are still searchable, still
#: counted, still backed up.  A future dedicated pass over them is expected,
#: and should pass ``include_archival=True`` deliberately.
ARCHIVAL_COLLECTIONS = (
    "09 - Journal Électronique d'Histoire des Probabilités et de la Statistique",
    "05 - Books and lecture notes/00 - Histoire de l'académie royale des sciences",
    "05 - Books and lecture notes/01 - Comptes rendus hebdomadaires de l'académie des sciences",
    "05 - Books and lecture notes/02 - Mémoires présentés par divers savants à l'académie "
    "royale des sciences de l'institut de France",
    "05 - Books and lecture notes/11 - Lviv Scottish book",
)


def _norm(path: str) -> str:
    """NFC, forward slashes, no leading or trailing separator.

    macOS hands paths back NFD-decomposed, and every folder name in
    ARCHIVAL_COLLECTIONS is dense with accents -- "Mémoires", "académie",
    "Électronique".  Comparing a decomposed path against a precomposed
    constant silently never matches, which would make this whole module a
    no-op that looks like it is working.
    """
    return unicodedata.normalize("NFC", (path or "").replace("\\", "/")).strip("/")


def _under(path: str, prefix: str) -> bool:
    """Is ``path`` the folder ``prefix`` or something inside it?

    A plain ``startswith`` would put "05 - Books/01 - Comptes rendus TWO"
    inside "05 - Books/01 - Comptes rendus", so the boundary is explicit.
    """
    path, prefix = _norm(path), _norm(prefix)
    return path == prefix or path.startswith(prefix + "/")


def exclusion_reason(rel_path: str, *,
                     include_archival: bool = False,
                     include_staging: bool = False) -> Optional[str]:
    """Why this path is out of scope, or ``None`` when it is in scope.

    A reason rather than a bare ``False`` so a caller can report *which* rule
    excluded a file -- "skipped 2,341 files" is the kind of silent number that
    turns into a wrong conclusion three months later.
    """
    path = _norm(rel_path)
    if not path:
        return None

    first = path.split("/", 1)[0]
    if first in NON_LIBRARY or any(part in NON_LIBRARY for part in path.split("/")):
        return f"not library content ({first})"

    if not include_staging:
        for prefix in STAGING:
            if _under(path, prefix):
                return f"staging, not renamed yet ({prefix})"

    if not include_archival:
        for prefix in ARCHIVAL_COLLECTIONS:
            if _under(path, prefix):
                return ("archival collection the owner asked to leave alone "
                        f"({prefix.split('/')[-1]})")
    return None


def in_scope(rel_path: str, **kwargs) -> bool:
    """Should ordinary library tooling touch this path?"""
    return exclusion_reason(rel_path, **kwargs) is None


def filter_in_scope(rel_paths: Iterable[str], **kwargs):
    """``(kept, {reason: count})`` -- never a silent drop."""
    kept, dropped = [], {}
    for p in rel_paths:
        reason = exclusion_reason(p, **kwargs)
        if reason is None:
            kept.append(p)
        else:
            dropped[reason] = dropped.get(reason, 0) + 1
    return kept, dropped
