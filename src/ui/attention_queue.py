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


def human_label(pdf: Path, *, width: int = 90) -> str:
    """A label a HUMAN can decide from — never a bare identifier.

    Freshly-dropped arXiv papers are named ``2607.13547v1.pdf``, which
    tells the owner nothing: he cannot judge where a paper belongs from
    its arXiv id, so every such row was a dead end.

    Cheapest source first, and none of them touch the network:
      1. an already-canonical ``Author - Title`` stem;
      2. the sidecar's cached first-page text (``classifier_text``) —
         present for ~85% of the staging backlog, so this is free;
      3. the raw stem, as a last resort.
    """
    stem = pdf.stem
    if " - " in stem:                      # already canonical
        return stem[:width]
    try:
        from processing.identity import PaperIdentity
        text = (PaperIdentity.load(pdf).classifier_text or "").strip()
    except Exception:                      # never break the queue over a label
        text = ""
    if text:
        # The first line of a paper's first page is its title often
        # enough to identify it; collapse whitespace so the row is one
        # tidy line rather than a wrapped block.
        flat = " ".join(text.split())
        if flat:
            return f"{flat[:width]}…" if len(flat) > width else flat
    return stem[:width]
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
    # Atomic + concurrency-safe (audit-10/11): the cockpit may write
    # dismissals while another process reads them.
    from core.io import atomic_write_text
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True))


def dismiss(key: str, *, days: int = 7, path: Path = DISMISSALS_PATH) -> None:
    """Snooze an attention item for ``days`` days."""
    if days <= 0:
        raise ValueError("days must be positive")
    until = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
    data = _load_dismissals(path)
    data[key] = until
    _save_dismissals(data, path)


def list_dismissals(path: Path = DISMISSALS_PATH) -> dict[str, str]:
    """Public read of the snooze store — ``{key: dismissed_until_iso}``.

    The cockpit needs this to show WHICH items are snoozed.  Without it
    the only un-dismiss affordance was a text box asking for an internal
    item key that is never displayed anywhere in the UI, so snoozing was
    a one-way door.
    """
    return _load_dismissals(path)


def list_dismissals(path: Path = DISMISSALS_PATH) -> dict[str, str]:
    """Public read of the snooze store — ``{key: dismissed_until_iso}``.

    The cockpit needs this to show WHICH items are snoozed.  Without it
    the only un-dismiss affordance was a text box asking for an internal
    item key that is never displayed anywhere in the UI, so snoozing was
    a one-way door.
    """
    return _load_dismissals(path)


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
        # The watcher logs paths as the daemon sees them (relative to
        # the inbox).  If a user ever runs two daemons with overlapping
        # inboxes the same basename could appear twice; key on the full
        # path so they don't collapse into one Attention item.
        key = f"watcher_failure::{filename}"
        # ...but when the log only carries a basename (older daemon
        # format) we lose nothing -- the key just falls back to that.
        latest[key] = AttentionItem(
            key=key,
            source="watcher_failure",
            severity=SEVERITY_ERROR if m.group("level") == "ERROR" else SEVERITY_WARNING,
            title=f"Couldn't be filed automatically: {Path(filename).name}",
            detail=(
                f"Path: `{filename}`\n\n"
                f"Last error: `{reason}`"
            ),
            created_at=ts,
            payload={"file": filename, "reason": reason},
            actions=[
                ("How do I retry?", "watcher_retry"),
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
    from processing.identity import iter_pdfs
    items: list[AttentionItem] = []
    if not library_root.exists():
        return items
    for pdf in iter_pdfs(library_root):
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
                    ("Move conflict copy to trash", "delete_conflict"),
                    ("Dismiss 7d", "dismiss_7d"),
                ],
            )
        )
    return items


def collect_borderline_matches(library_root: Path) -> list[AttentionItem]:
    """Papers stuck in the 0.75-0.95 confidence band.

    The state machine treats these as hits (so they never tip
    permanent), but auto-apply ignores them (confidence below 0.95).
    Without this collector they'd quietly accumulate.  Surface them
    here with an "Open DOI" action so the user can decide whether to
    upgrade manually.
    """
    try:
        from processing.publication_state import list_borderline_matches
    except ImportError as exc:
        logger.warning("publication_state unavailable: %s", exc)
        return []
    try:
        rows = list_borderline_matches(library_root)
    except Exception as exc:
        logger.warning("borderline scan raised: %s", exc)
        return []
    items: list[AttentionItem] = []
    for row in rows:
        pdf_path = Path(row["path"])
        conf = row["confidence"]
        doi = row["doi"]
        key = f"borderline::{pdf_path.relative_to(library_root)}"
        actions: list[tuple[str, str]] = []
        if doi:
            actions.append(("Open DOI", "open_doi"))
        actions.extend([
            ("Reveal in Finder", "reveal_in_finder"),
            ("Dismiss 30d", "dismiss_30d"),
        ])
        items.append(
            AttentionItem(
                key=key,
                source="borderline_match",
                severity=SEVERITY_INFO,
                title=f"Probably published ({conf:.0%} sure): {pdf_path.stem}",
                detail=(
                    f"Path: `{pdf_path}`\n\n"
                    f"A published version was found that matches this paper "
                    f"{conf:.0%} — likely the same paper, but not certain "
                    f"enough to swap in automatically.  Open the DOI to "
                    f"check; if it is the same paper, upgrade it from the "
                    f"Upgrade Queue."
                ),
                created_at=row.get("last_check_date", ""),
                payload={"path": str(pdf_path), "doi": doi, "confidence": conf},
                actions=actions,
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
                title=f"No published version found — stopped looking: {pdf.stem}",
                detail=(
                    f"Path: `{pdf}`\n\n"
                    f"This paper was searched for a published version "
                    f"several times over and none was ever found, so the "
                    f"search was stopped.  If you know it has since been "
                    f"published, click **Look again** to put it back in "
                    f"the queue."
                ),
                created_at=datetime.fromtimestamp(
                    pdf.stat().st_mtime, tz=timezone.utc
                ).isoformat(timespec="seconds"),
                payload={"path": str(pdf)},
                actions=[
                    ("Look again", "reset_recheck"),
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
def collect_topic_suggestions(library_root: Path) -> list[AttentionItem]:
    """Papers the classifier thinks belong to a topic but wasn't sure
    enough to auto-file -- the user confirms or rejects the move.

    These are the medium-confidence band (review) from
    ``publication_topic_router.resolve_topic``.  Accepting moves the
    paper into ``<topic>/<status>/`` via the undo log (reversible);
    rejecting clears the suggestion.
    """
    try:
        from processing.publication_topic_router import list_topic_suggestions
    except ImportError as exc:
        logger.warning("topic router unavailable: %s", exc)
        return []
    try:
        rows = list_topic_suggestions(library_root)
    except Exception as exc:
        logger.warning("topic-suggestion scan raised: %s", exc)
        return []
    # A bare code ("07b") means nothing in a list of suggestions -- show
    # the folder name the owner actually files by hand.  ``code`` is used
    # for display in the title/detail and for the undo-transaction
    # description only; the move itself is driven by the paper's sidecar.
    _names = {d.name[:3]: d.name
              for d in library_root.glob("07? - *") if d.is_dir()}
    items: list[AttentionItem] = []
    for row in rows:
        pdf = Path(row["path"])
        code = _names.get(row["topic"], row["topic"])
        conf = row["confidence"]
        key = f"topic_suggestion::{pdf.relative_to(library_root)}"
        items.append(
            AttentionItem(
                key=key,
                source="topic_suggestion",
                severity=SEVERITY_INFO,
                title=f"Topic? {code} ({conf:.0%}): {pdf.stem}",
                detail=(
                    f"Path: `{pdf}`\n\n"
                    f"The classifier suggests this belongs in topic "
                    f"**{code}** with {conf:.0%} confidence -- below the "
                    f"auto-file threshold, so it's in a standard folder "
                    f"pending your call.  Accept to move it into the "
                    f"topic folder (reversible via Activity), or reject "
                    f"to keep it where it is."
                ),
                created_at="",
                payload={"path": str(pdf), "topic": code, "confidence": conf},
                actions=[
                    ("Accept -> move to topic", "accept_topic"),
                    ("Reject suggestion", "reject_topic"),
                    ("Reveal in Finder", "reveal_in_finder"),
                ],
            )
        )
    return items


def collect_unsorted_backlog(
    library_root: Path, *, max_age_days: int = 14,
) -> list[AttentionItem]:
    """Papers parked in "12 - To be sorted" longer than ``max_age_days``.

    Audit-11c: a PDF can land in the staging area and sit there
    forever — the classifier couldn't place it, the user skipped it in
    the Sort Queue, or a corrupt file failed preview (the Sort Queue's
    only option there was Skip).  Nothing surfaced it, so it was a
    silent dead end.  This collector nags about anything that's been
    waiting too long so it can't be forgotten.
    """
    from organization.system import TO_BE_SORTED
    from processing.identity import iter_pdfs
    items: list[AttentionItem] = []
    base = library_root / TO_BE_SORTED
    if not base.exists():
        return items
    now = datetime.now(timezone.utc)
    for pdf in iter_pdfs(base):
        try:
            mtime = datetime.fromtimestamp(pdf.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        age_days = (now - mtime).days
        if age_days < max_age_days:
            continue
        key = f"unsorted::{pdf.relative_to(library_root)}"
        items.append(
            AttentionItem(
                key=key,
                source="unsorted_backlog",
                # INFO, not WARNING: a backlog is not a fault.  As a
                # warning it sorted ABOVE the handful of genuinely
                # blocked items and buried them under ~1.9k rows.
                severity=SEVERITY_INFO,
                title=f"{human_label(pdf)}  ·  waiting {age_days}d",
                detail=(
                    f"Path: `{pdf}`\n\n"
                    f"This paper has sat in **{TO_BE_SORTED}** for "
                    f"{age_days} days without being filed.  Open the Sort "
                    f"Queue to file it, or reveal it in Finder to inspect "
                    f"(it may have failed text extraction)."
                ),
                created_at=mtime.isoformat(timespec="seconds"),
                payload={"path": str(pdf), "age_days": age_days},
                actions=[
                    ("Reveal in Finder", "reveal_in_finder"),
                    ("Dismiss 30d", "dismiss_30d"),
                ],
            )
        )
    return items


COLLECTORS: list[tuple[str, Callable[[Path], list[AttentionItem]]]] = [
    ("watcher_failure", lambda root: collect_watcher_failures()),
    ("upgrade_flag", collect_upgrade_flags),
    ("aging", collect_aging_candidates),
    ("conflict_copy", collect_conflict_copies),
    ("borderline_match", collect_borderline_matches),
    ("topic_suggestion", collect_topic_suggestions),
    ("permanently_unpublished", collect_permanently_unpublished),
    ("unsorted_backlog", collect_unsorted_backlog),
]


def gather_attention_items(
    library_root: Path,
    *,
    include_dismissed: bool = False,
    dismissals_path: Path = DISMISSALS_PATH,
    collectors: Optional[Iterable[tuple[str, Callable[[Path], list[AttentionItem]]]]] = None,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> list[AttentionItem]:
    """Run every collector, filter dismissed items, sort, and return.

    ``progress``, if given, is called as ``(step, total, collector_name)``
    before each collector runs, so a UI can name the check in flight
    during what is MEASURED as a ~44s sweep.

    Sort order: severity (errors first), then ``created_at`` newest
    first.  Items missing ``created_at`` sort to the bottom of their
    severity bucket.
    """
    use_collectors = list(collectors) if collectors is not None else COLLECTORS

    all_items: list[AttentionItem] = []
    # ONE shared sidecar read cache for the whole sweep.  Three of the
    # collectors independently PaperIdentity.load() every PDF in the
    # library; MEASURED, that made this function 111s on 29k papers, of
    # which ~60s was the same JSON parsed a second and third time.  With
    # the shared cache: 43.8s, identical output.  Every collector is
    # read-only, which is the precondition the cache documents.
    from processing.identity import sidecar_read_cache
    with sidecar_read_cache():
        for i, (name, fn) in enumerate(use_collectors, 1):
            # ``progress`` lets the UI show WHICH check is running during
            # a scan that takes the better part of a minute.  Reporting
            # must never be able to break the scan.
            if progress is not None:
                try:
                    progress(i, len(use_collectors), name)
                except Exception:  # pragma: no cover - UI feedback only
                    logger.debug("progress callback raised", exc_info=True)
            try:
                all_items.extend(fn(library_root))
            except Exception as exc:
                # A dropped collector was invisible in the UI.  Two of
                # them (conflict copies, inbox backlog) have no internal
                # guard, so a single unreadable file could delete a whole
                # pile of real work from Home and leave the green
                # "Nothing needs your attention" in its place.
                logger.warning("collector %s failed: %s", name, exc)
                all_items.append(AttentionItem(
                    key=f"collector_error::{name}",
                    source="collector_error",
                    severity=SEVERITY_ERROR,
                    title=f"One of the checks could not run: {name}",
                    detail=(
                        f"`{name}` stopped with: `{exc}`\n\n"
                        "Anything it would have listed is **not** shown on "
                        "this page, so the counts here are incomplete.  "
                        "Press ↻ Rescan; if it keeps happening, the usual "
                        "cause is a file Dropbox has not finished "
                        "downloading."
                    ),
                    actions=[("Dismiss 7d", "dismiss_7d")],
                ))

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
