"""Unified "needs your attention" queue.

The math-PDF system has several channels that can produce work for the
user (watcher ingest failures, "please download manually" flags from the
upgrade-to-published pipeline, aging working papers that should move to
unpublished, Dropbox conflict copies, etc.).  Historically each lived in
a different place — a notification, a folder, a log file — and the user
had to remember which channel to check.

This module unifies them.  ``gather_attention_items()`` runs every
collector and returns a deduplicated list of ``AttentionItem`` objects
ready for rendering in the cockpit.

Dismissals are persisted to ``~/.mathpdf/attention_dismissals.json``;
an item dismissed for N days reappears once the snooze expires.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

logger = logging.getLogger(__name__)

# Where dismissals are persisted.  Living under ~/.mathpdf keeps it next
# to the cockpit activity log and watcher log for easy backup.
DISMISSALS_PATH = Path.home() / ".mathpdf" / "attention_dismissals.json"

# Severities — used both for badge colour in the UI and for sort order.
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"
_SEVERITY_RANK = {SEVERITY_ERROR: 0, SEVERITY_WARNING: 1, SEVERITY_INFO: 2}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AttentionItem:
    """One thing the user might want to act on.

    Fields
    ------
    key
        Stable identifier across runs.  Used for dedup, dismissal
        bookkeeping, and as Streamlit's widget key.  Construct from
        immutable inputs (path, DOI, etc.) — not timestamps.
    source
        Which collector produced this item.  One of
        ``"watcher_failure" | "upgrade_flag" | "aging" | "conflict_copy"``.
    severity
        ``"error" | "warning" | "info"``.
    title
        One-line headline (kept under ~80 chars).
    detail
        Longer markdown-flavoured description.  May span several lines.
    created_at
        ISO timestamp the underlying event was first detected.
    payload
        Source-specific data (paths, DOIs, etc.) that the action
        callbacks need.  Always JSON-serialisable.
    actions
        Ordered list of ``(label, action_id)`` tuples.  The cockpit
        layer maps ``action_id`` to a real callable.  Keeping the
        action as a string keeps this dataclass pickleable and easy to
        snapshot in tests.
    """

    key: str
    source: str
    severity: str
    title: str
    detail: str = ""
    created_at: str = ""
    payload: dict = field(default_factory=dict)
    actions: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        # asdict turns tuples into lists; Streamlit doesn't care but
        # tests assert on round-trip equality.
        d["actions"] = [list(a) for a in self.actions]
        return d


# ---------------------------------------------------------------------------
# Dismissals store
# ---------------------------------------------------------------------------

def _load_dismissals(path: Path = DISMISSALS_PATH) -> dict[str, str]:
    """Read the dismissals file.

    Returns a ``{key: dismissed_until_iso}`` mapping.  Missing or
    unreadable files yield an empty dict — dismissals are an
    optimisation, never a correctness requirement.
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("dismissals file unreadable %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _save_dismissals(data: dict[str, str], path: Path = DISMISSALS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    import os
    os.replace(tmp, path)


def dismiss(key: str, *, days: int = 7, path: Path = DISMISSALS_PATH) -> None:
    """Snooze an attention item for ``days`` days."""
    if days <= 0:
        raise ValueError("days must be positive")
    until = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
    data = _load_dismissals(path)
    data[key] = until
    _save_dismissals(data, path)


def undismiss(key: str, *, path: Path = DISMISSALS_PATH) -> None:
    """Remove a dismissal (force the item to reappear)."""
    data = _load_dismissals(path)
    if key in data:
        del data[key]
        _save_dismissals(data, path)


def _filter_dismissed(items: list[AttentionItem], dismissals: dict[str, str]) -> list[AttentionItem]:
    """Drop items whose dismissal hasn't expired yet.

    Expired dismissals are kept in the file — they're harmless and let
    us show the user "last snoozed X days ago" if we ever want to.
    """
    now = datetime.now(timezone.utc)
    out = []
    for it in items:
        until_iso = dismissals.get(it.key)
        if until_iso:
            try:
                until = datetime.fromisoformat(until_iso)
            except ValueError:
                until = now  # bogus — treat as expired
            if until > now:
                continue
        out.append(it)
    return out


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

# Pattern to extract structured info from watcher.log ERROR/WARNING
# lines.  Format used by ``src/watcher/daemon.py``:
#   logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
# Default ``asctime`` is ``YYYY-MM-DD HH:MM:SS,mmm``.  Example:
#   2026-05-17 12:34:56,789 [ERROR] Failed to ingest foo.pdf: bad metadata
# We accept both ``Failed to ingest <file>: <reason>`` (warning path,
# ingest returned False) and ``Error ingesting <file>: <exc>`` (error
# path, exception escaped) — the two messages daemon.py emits.
_WATCHER_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,.]?\d*)\s+"
    r"\[(?P<level>ERROR|WARNING)\]\s+"
    r"(?P<msg>Failed to ingest|Error ingesting)\s+(?P<file>\S+):\s*(?P<reason>.+)$"
)


def collect_watcher_failures(
    log_path: Optional[Path] = None,
    *,
    lookback_lines: int = 2000,
) -> list[AttentionItem]:
    """Tail the watcher log for ingest failures.

    Each ERROR/WARNING line that matches the daemon's "Failed to
    ingest" / "Error ingesting" format becomes one item.  The most
    recent line per failed-file wins (a file that failed three times
    in a row produces one item, not three).
    """
    if log_path is None:
        log_path = Path.home() / ".mathpdf" / "watcher.log"
    if not log_path.exists():
        return []
    try:
        # Last N lines is plenty — RotatingFileHandler keeps the
        # current file <10MB by default which is ~50k lines.
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("cannot read watcher log %s: %s", log_path, exc)
        return []
    lines = text.splitlines()[-lookback_lines:]

    latest: dict[str, AttentionItem] = {}
    for line in lines:
        m = _WATCHER_LINE_RE.match(line)
        if not m:
            continue
        filename = m.group("file")
        reason = m.group("reason").strip()
        ts = m.group("ts").replace(",", ".")
        key = f"watcher_failure::{filename}"
        latest[key] = AttentionItem(
            key=key,
            source="watcher_failure",
            severity=SEVERITY_ERROR if m.group("level") == "ERROR" else SEVERITY_WARNING,
            title=f"Watcher failed to ingest {filename}",
            detail=f"Last error: `{reason}`",
            created_at=ts,
            payload={"file": filename, "reason": reason},
            actions=[
                ("Retry now", "watcher_retry"),
                ("Dismiss 7d", "dismiss_7d"),
            ],
        )
    return list(latest.values())


def collect_upgrade_flags(library_root: Path) -> list[AttentionItem]:
    """Scan ``04 - Papers to be downloaded/`` for manual-download flags.

    Each ``.txt`` file under that folder is one item.  The flag-file
    format is whatever ``upgrade_to_published.flag_for_manual_download``
    writes; we don't need to parse it deeply — the title comes from the
    filename and the detail is the whole file.
    """
    flags_root = library_root / "04 - Papers to be downloaded"
    if not flags_root.exists():
        return []
    items: list[AttentionItem] = []
    for txt in flags_root.rglob("*.txt"):
        try:
            body = txt.read_text(encoding="utf-8", errors="replace")
        except OSError:
            body = ""
        # Parse DOI if present
        doi_match = re.search(r"^DOI:\s*(\S+)", body, flags=re.MULTILINE)
        doi = doi_match.group(1) if doi_match else ""
        journal = txt.parent.name
        # Stable key based on flag path
        key = f"upgrade_flag::{txt.relative_to(library_root)}"
        # If there's a DOI we always include the "Open DOI" action so
        # the cockpit can render it as a focus-safe st.link_button; the
        # "show_flag" placeholder action (which just re-rendered the
        # body we already show in the Details expander) is gone.
        actions = []
        if doi:
            actions.append(("Open DOI", "open_doi"))
        actions.append(("Mark done", "mark_flag_done"))
        actions.append(("Dismiss 7d", "dismiss_7d"))

        items.append(
            AttentionItem(
                key=key,
                source="upgrade_flag",
                severity=SEVERITY_WARNING,
                title=f"Manual download needed: {txt.stem}",
                detail=f"**Journal**: {journal}\n\n```\n{body.strip()}\n```",
                created_at=datetime.fromtimestamp(
                    txt.stat().st_mtime, tz=timezone.utc
                ).isoformat(timespec="seconds"),
                payload={
                    "flag_file": str(txt),
                    "doi": doi,
                    "journal": journal,
                },
                actions=actions,
            )
        )
    return items


def collect_aging_candidates(library_root: Path, *, max_age_years: int = 5) -> list[AttentionItem]:
    """Working papers that should move to unpublished (aged out).

    Wraps ``maintenance.weekly_report.check_aging``.  If the import
    fails (e.g. in a stripped test env) the collector yields nothing
    rather than raising.
    """
    try:
        from maintenance.weekly_report import check_aging
    except ImportError as exc:
        logger.warning("aging check unavailable: %s", exc)
        return []
    try:
        candidates = check_aging(library_root, max_age_years=max_age_years)
    except Exception as exc:
        logger.warning("aging check raised: %s", exc)
        return []

    items: list[AttentionItem] = []
    for cand in candidates:
        path = cand.get("path") or cand.get("file") or ""
        age = cand.get("age_years") or cand.get("years") or "?"
        key = f"aging::{path}"
        items.append(
            AttentionItem(
                key=key,
                source="aging",
                severity=SEVERITY_INFO,
                title=f"Working paper aged {age}y: {Path(path).stem}",
                detail=f"Path: `{path}` — older than {max_age_years} years, "
                       f"consider moving to Unpublished.",
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                payload={"path": path, "age_years": age},
                actions=[
                    ("Move to Unpublished", "transition_aged"),
                    ("Dismiss 30d", "dismiss_30d"),
                ],
            )
        )
    return items


# Dropbox creates files like:
#   Smith, J. - Paper (DESKTOP-XYZ's conflicted copy 2024-05-13).pdf
_CONFLICT_RE = re.compile(r"conflicted copy", re.IGNORECASE)


def collect_conflict_copies(library_root: Path) -> list[AttentionItem]:
    """Find Dropbox conflict copies in the library."""
    items: list[AttentionItem] = []
    if not library_root.exists():
        return items
    for pdf in library_root.rglob("*.pdf"):
        if ".trash" in pdf.parts:
            continue
        if not _CONFLICT_RE.search(pdf.name):
            continue
        key = f"conflict::{pdf.relative_to(library_root)}"
        items.append(
            AttentionItem(
                key=key,
                source="conflict_copy",
                severity=SEVERITY_WARNING,
                title=f"Dropbox conflict copy: {pdf.name}",
                detail=f"Path: `{pdf}`\n\nDropbox detected concurrent edits.  "
                       f"Compare the conflict copy with the canonical file and "
                       f"keep the right one.",
                created_at=datetime.fromtimestamp(
                    pdf.stat().st_mtime, tz=timezone.utc
                ).isoformat(timespec="seconds"),
                payload={"path": str(pdf), "size": pdf.stat().st_size},
                actions=[
                    ("Open in Finder", "reveal_in_finder"),
                    ("Delete conflict copy", "delete_conflict"),
                    ("Dismiss 7d", "dismiss_7d"),
                ],
            )
        )
    return items


def collect_permanently_unpublished(library_root: Path) -> list[AttentionItem]:
    """Surface papers the state machine has given up on.

    These are not "errors" — they're decisions the system made on the
    user's behalf that the user might want to review or override.  We
    show them as INFO severity (sorted last) with a one-click "reset
    recheck" action that drops them back into the live queue.
    """
    try:
        from processing.publication_state import list_permanently_unpublished
    except ImportError as exc:
        logger.warning("publication_state unavailable: %s", exc)
        return []
    try:
        paths = list_permanently_unpublished(library_root)
    except Exception as exc:
        logger.warning("permanently-unpublished scan raised: %s", exc)
        return []
    items: list[AttentionItem] = []
    for pdf in paths:
        key = f"permanent::{pdf.relative_to(library_root)}"
        items.append(
            AttentionItem(
                key=key,
                source="permanently_unpublished",
                severity=SEVERITY_INFO,
                title=f"Stopped checking: {pdf.stem}",
                detail=(
                    f"Path: `{pdf}`\n\n"
                    f"The publication-state machine ran out its recheck "
                    f"budget on this paper with zero Crossref hits and "
                    f"marked it as permanently unpublished.  Click "
                    f"**Reset recheck** to drop it back into the live "
                    f"queue (e.g. you have new information that it was "
                    f"in fact published)."
                ),
                created_at=datetime.fromtimestamp(
                    pdf.stat().st_mtime, tz=timezone.utc
                ).isoformat(timespec="seconds"),
                payload={"path": str(pdf)},
                actions=[
                    ("Reset recheck", "reset_recheck"),
                    ("Dismiss 30d", "dismiss_30d"),
                ],
            )
        )
    return items


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

# Registry of collectors -- (name, callable that takes library_root) pairs.
# Kept as a list (not a dict) so the order is deterministic and the UI
# can sort by severity within each source.
COLLECTORS: list[tuple[str, Callable[[Path], list[AttentionItem]]]] = [
    ("watcher_failure", lambda root: collect_watcher_failures()),
    ("upgrade_flag", collect_upgrade_flags),
    ("aging", collect_aging_candidates),
    ("conflict_copy", collect_conflict_copies),
    ("permanently_unpublished", collect_permanently_unpublished),
]


def gather_attention_items(
    library_root: Path,
    *,
    include_dismissed: bool = False,
    dismissals_path: Path = DISMISSALS_PATH,
    collectors: Optional[Iterable[tuple[str, Callable[[Path], list[AttentionItem]]]]] = None,
) -> list[AttentionItem]:
    """Run every collector, filter dismissed items, sort, and return.

    Sort order: severity (errors first), then ``created_at`` newest
    first.  Items missing ``created_at`` sort to the bottom of their
    severity bucket.
    """
    use_collectors = list(collectors) if collectors is not None else COLLECTORS

    all_items: list[AttentionItem] = []
    for name, fn in use_collectors:
        try:
            all_items.extend(fn(library_root))
        except Exception as exc:
            logger.warning("collector %s failed: %s", name, exc)

    if not include_dismissed:
        dismissals = _load_dismissals(dismissals_path)
        all_items = _filter_dismissed(all_items, dismissals)

    def sort_key(it: AttentionItem):
        return (
            _SEVERITY_RANK.get(it.severity, 99),
            -_iso_to_epoch(it.created_at),  # newer first
        )

    all_items.sort(key=sort_key)
    return all_items


def _iso_to_epoch(iso: str) -> float:
    """Best-effort ISO → epoch.  Returns 0 for unparseable strings."""
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0.0
