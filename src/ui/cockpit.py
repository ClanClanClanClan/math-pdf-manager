"""Math-PDF Library Cockpit — Streamlit UI.

Usage::

    PYTHONPATH=src streamlit run src/ui/cockpit.py

Tabs:
  - Sort Queue       review and approve papers in "12 - To be sorted/"
  - Upgrade Queue    review and approve preprint → published upgrades
  - Maintenance      run weekly checks (publications, aging, duplicates)
  - Stats            library counts and recent activity

DESIGN INVARIANTS:
- Nothing happens without an explicit user click. Every approve / undo
  button corresponds to exactly one filesystem operation.
- All operations go through the existing undo_log; the Recent Activity
  panel shows them and offers per-transaction undo.
- Source files in 12/ move to .trash/sorted_originals/ on approval, not
  deleted. Preprints displaced by upgrades go to .trash/upgraded_preprints/.
- We never silently skip a quality-gate failure — it surfaces as a
  warning the user can override or leave for manual handling.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st
from processing.identity import iter_pdfs

# Make src/ importable when streamlit invokes this file directly
_THIS_FILE = Path(__file__).resolve()
_SRC = _THIS_FILE.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Math-PDF Library Cockpit",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.config_paths import get_library_root  # noqa: E402
from organization.system import TO_BE_SORTED  # noqa: E402

# Subfolder → status hint for bulk_sort
SORT_SUBFOLDER_STATUS = {
    "01 - Published papers": "published",
    "02 - Unpublished papers": "unpublished",
    "03 - Working papers": "working",
    "05 - Books and lecture notes": "book",
    "06 - Theses": "thesis",
}


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

def _init_state() -> None:
    if "library_root" not in st.session_state:
        st.session_state.library_root = str(get_library_root())
    if "sort_skipped" not in st.session_state:
        st.session_state.sort_skipped = set()   # source paths the user skipped this session
    if "sort_cursor" not in st.session_state:
        st.session_state.sort_cursor = 0
    if "upgrade_skipped" not in st.session_state:
        st.session_state.upgrade_skipped = set()
    if "upgrade_report_path" not in st.session_state:
        st.session_state.upgrade_report_path = ""
    if "activity_log" not in st.session_state:
        st.session_state.activity_log = _load_activity_log()


# ---------------------------------------------------------------------------
# Activity log: in-memory + disk persistence so a browser reload doesn't
# lose the undo handles for transactions whose effects are already on disk.
# ---------------------------------------------------------------------------

def _activity_log_path() -> Path:
    """The on-disk JSONL file the cockpit appends every action to."""
    p = Path.home() / ".mathpdf" / "cockpit_activity.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_activity_log() -> list[dict]:
    """Load up to 100 most-recent entries from disk on cold start.

    Returned newest-first so it slots straight into ``session_state``.

    Audit-8: previously read EVERY line of the (potentially 10MB)
    log file before truncating to 100.  At ~100 bytes per entry
    that's ~100k JSON parses for a result the user discards 99% of.
    Now we read the file once with ``readlines()`` (a single syscall)
    and walk the bottom backwards, stopping after we've parsed 100
    valid entries.
    """
    path = _activity_log_path()
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            raw_lines = f.readlines()
    except OSError:
        return []
    entries: list[dict] = []
    # Walk from the newest line backwards, only parsing as many as
    # we need.  Most of the file gets ignored without ever paying
    # the JSON cost.
    for raw in reversed(raw_lines):
        line = raw.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # skip corrupt lines
        if len(entries) >= 100:
            break
    return entries


def _log_activity(action: str, source: str, destination: str = "", tx_id: str = "") -> None:
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "source": source,
        "destination": destination,
        "tx_id": tx_id,
    }
    # Append to disk first — if the session dies, the user still has the
    # entry and can undo from a later session.
    try:
        path = _activity_log_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # Cheap rotation: when the file passes ~10MB (roughly 50-100k
        # entries depending on action density), rotate to ``.1`` and
        # start fresh.  Keeps the activity log unbounded over years
        # without forcing the user to manually prune.  Audit-6 #9.
        #
        # Audit-7 #5: not atomic across multiple cockpit instances
        # writing the same file -- between ``rename`` and the next
        # append, a second writer would land in the freshly-renamed
        # ``.1`` file.  The cockpit is single-user-single-process
        # by design (Streamlit serves one tab from one venv); if
        # you ever run two instances in parallel, the activity log
        # could lose entries during rotation.  Documented limit.
        try:
            if path.stat().st_size > 10 * 1024 * 1024:
                rotated = path.with_suffix(path.suffix + ".1")
                if rotated.exists():
                    rotated.unlink()
                path.rename(rotated)
        except OSError:
            pass
    except OSError as exc:
        logger.warning("Failed to persist activity log entry: %s", exc)

    # Then update the in-session view
    st.session_state.activity_log.insert(0, entry)
    st.session_state.activity_log = st.session_state.activity_log[:100]


def _library() -> Path:
    return Path(st.session_state.library_root)


# ---------------------------------------------------------------------------
# Sidebar — global controls and stats
# ---------------------------------------------------------------------------

def _validate_library_root(raw: str) -> tuple[bool, str]:
    """Validate that ``raw`` is a safe absolute path to an existing
    directory. Returns (ok, message_or_resolved_path).

    Rejects empty strings, control characters, and anything that doesn't
    resolve to an existing directory after ``expanduser``/``resolve``.
    Doesn't enforce "must live under home" because some users have their
    library outside ~ — but we DO require the resolved path to exist.
    """
    s = (raw or "").strip()
    if not s:
        return False, "Library root is empty"
    if any(ch in s for ch in ("\x00", "\n", "\r")):
        return False, "Library root contains control characters"
    try:
        p = Path(s).expanduser().resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        return False, f"Cannot resolve path: {exc}"
    if not p.exists():
        return False, f"Path does not exist: {p}"
    if not p.is_dir():
        return False, f"Path is not a directory: {p}"
    return True, str(p)


def render_sidebar() -> None:
    with st.sidebar:
        st.title("📚 Library Cockpit")
        st.caption("Math-PDF management — review & act")

        # Library root — validated each rerun so an obviously-bad path
        # doesn't silently break every subsequent operation.
        new_root = st.text_input(
            "Library root", value=st.session_state.library_root,
            help="Absolute path or ~ for home. Defaults to $MATH_LIBRARY env var.",
        )
        if new_root != st.session_state.library_root:
            ok, msg = _validate_library_root(new_root)
            if ok:
                st.session_state.library_root = msg  # resolved path
            else:
                st.error(f"Library root rejected: {msg}")
                # Don't update session_state — keep the previous valid one.

        lib = _library()
        if not lib.exists():
            st.error(f"Library not found: {lib}")
        else:
            st.success(f"📁 {lib}")

        st.divider()
        # The Attention tab shows a count badge so the user can tell at
        # a glance whether anything wants their attention right now.
        # Streamlit reruns the sidebar on every interaction so we cache
        # the count for 60s — collectors glob the whole library and a
        # 28k-PDF rglob would dominate the UI loop otherwise.
        try:
            _attn_count = _attention_count_cached(str(lib)) if lib else 0
        except Exception:  # pragma: no cover -- never break the sidebar
            _attn_count = 0
        attention_label = (
            f"Attention ({_attn_count})" if _attn_count else "Attention"
        )

        page = st.radio(
            "Page",
            [
                attention_label,
                "Sort Queue",
                "Upgrade Queue",
                "To Download",
                "Conflicts",
                "Maintenance",
                "Pipeline Preview",
                "Stats",
                "Activity",
                "Settings",
            ],
            label_visibility="collapsed",
        )
        # Normalise the label back to a canonical page name so the
        # router below doesn't have to do string matching on the count.
        if page.startswith("Attention"):
            page = "Attention"
        st.session_state.page = page

        st.divider()
        # Phase 5: watcher controls live in the sidebar so they're one
        # click away from anywhere in the cockpit.  Status is read on
        # every rerun (it's cheap -- a single launchctl print) so the
        # badge stays accurate.
        try:
            from ui.cockpit_actions import start_watcher, stop_watcher
            wstatus = _watcher_status_cached()
            if wstatus.get("running"):
                st.success(
                    f"Watcher: ON  (pid {wstatus.get('pid') or '?'})"
                )
                if st.button("Stop watcher", use_container_width=True,
                             key="sidebar_stop_watcher"):
                    ok, msg = stop_watcher()
                    st.toast(msg)
                    # Invalidate the cache so the badge flips
                    # immediately rather than after the 10s TTL.
                    _watcher_status_cached.clear()
                    st.rerun()
            else:
                st.warning("Watcher: OFF")
                if st.button("Start watcher", use_container_width=True,
                             key="sidebar_start_watcher"):
                    ok, msg = start_watcher()
                    st.toast(msg)
                    _watcher_status_cached.clear()
                    st.rerun()
        except Exception as exc:  # pragma: no cover -- never break the sidebar
            st.caption(f"Watcher status unavailable: {exc}")

        st.divider()
        st.caption(
            "⚠ Approvals write to your library. "
            "Sources move to `.trash/` and can be recovered or undone."
        )


# ---------------------------------------------------------------------------
# Page: Sort Queue
# ---------------------------------------------------------------------------

def _iter_sort_candidates(lib: Path) -> list[tuple[Path, str]]:
    """List PDFs in 12/{sub}/ paired with their status hint, sorted alpha."""
    staging = lib / TO_BE_SORTED
    out: list[tuple[Path, str]] = []
    if not staging.exists():
        return out
    for sub_name, status in SORT_SUBFOLDER_STATUS.items():
        sub = staging / sub_name
        if not sub.is_dir():
            continue
        for pdf in sorted(iter_pdfs(sub)):
            if pdf.name.startswith("."):
                continue
            if str(pdf) in st.session_state.sort_skipped:
                continue
            out.append((pdf, status))
    return out


def render_sort_queue() -> None:
    st.header("📥 Sort Queue")
    st.caption(
        "PDFs in `12 - To be sorted/{subfolder}/`. The subfolder tells us the "
        "status hint; the pipeline extracts metadata and proposes a canonical "
        "filename. Approve to file, Skip to leave for later, Flag for manual."
    )

    lib = _library()
    candidates = _iter_sort_candidates(lib)

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Pending", len(candidates))
    col_b.metric("Skipped this session", len(st.session_state.sort_skipped))
    col_c.metric("Filed this session", sum(1 for a in st.session_state.activity_log if a["action"] == "sort.approve"))
    col_d.metric("Trash (recoverable)", _count_trash(lib, "sorted_originals"))

    if not candidates:
        st.success("🎉 Sort queue is empty — nothing left in `12 - To be sorted/`.")
        if st.session_state.sort_skipped:
            if st.button("↻ Re-include skipped papers"):
                st.session_state.sort_skipped.clear()
                st.rerun()
        return

    # Take the first candidate the user hasn't skipped
    pdf, status = candidates[0]

    from ui.paper_preview import preview_pdf
    prev = preview_pdf(pdf)

    st.subheader(f"Paper {1} of {len(candidates)} pending")
    st.code(str(pdf.relative_to(lib)), language=None)

    if prev.error:
        st.error(f"Preview failed: {prev.error}")
        st.caption(
            "This PDF couldn't be parsed (corrupt, encrypted, or a "
            "cloud-only placeholder). Open it to inspect/repair, or skip "
            "it — it will resurface in the Attention Queue once it has sat "
            "in *To be sorted* past the backlog window, so it won't be "
            "silently forgotten."
        )
        cols = st.columns(3)
        if cols[0].button("🔍 Open file", key=f"openfail_{pdf}"):
            import subprocess
            subprocess.run(["open", str(pdf)], capture_output=True)
        if cols[1].button("📁 Reveal in Finder", key=f"revealfail_{pdf}"):
            import subprocess
            subprocess.run(["open", "-R", str(pdf)], capture_output=True)
        if cols[2].button("⏭ Skip", key=f"skip_{pdf}"):
            st.session_state.sort_skipped.add(str(pdf))
            st.rerun()
        return

    # Two-column layout: metadata on left, first-page text on right
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Status hint**")
        st.code(status, language=None)
        st.markdown("**Extracted title**")
        st.write(prev.title or "_(none)_")
        st.markdown("**Extracted authors**")
        st.write(prev.authors or "_(none)_")
        if prev.doi:
            st.markdown(f"**DOI** &nbsp; `{prev.doi}`")
        if prev.arxiv_id:
            st.markdown(f"**ArXiv** &nbsp; `{prev.arxiv_id}`")
        if prev.year:
            st.markdown(f"**Year** &nbsp; `{prev.year}`")

        # Topic decision (MOVE model): the paper LIVES in one topic
        # folder if the classifier is confident, else the standard
        # tree.  We show the decision and let the user override it.
        # (Phase-4 hardlink "topic copies" were retired -- the library
        # uses one-home-per-paper, confirmed by 1% main/topic overlap.)
        from processing.publication_topic_router import resolve_topic
        _decision = resolve_topic(
            prev.title, prev.first_page_text[:4000]
        )
        _topic_codes = ["07a", "07b", "07c", "07d", "07e", "07f"]
        _opts = ["(standard — no topic)"] + _topic_codes
        if _decision.auto:
            _default = _decision.topic_code
            _hint = f"auto → **{_decision.topic_code}** ({_decision.confidence:.0%})"
        elif _decision.needs_review:
            _default = _decision.suggested_code
            _hint = (f"suggested **{_decision.suggested_code}** "
                     f"({_decision.confidence:.0%}) — confirm or change")
        else:
            _default = None
            _hint = "no topic match → standard tree"
        st.markdown("**Topic destination**")
        st.caption(_hint)
        _sel = st.selectbox(
            "Topic destination",
            _opts,
            index=(_opts.index(_default) if _default in _opts else 0),
            label_visibility="collapsed",
            key=f"topicsel_{pdf}",
        )
        chosen_topic = None if _sel.startswith("(standard") else _sel

        st.markdown("---")
        st.markdown("**Proposed canonical filename**")
        # Allow editing the canonical filename before approval
        edited_name = st.text_input(
            "Canonical filename",
            value=prev.canonical_filename,
            label_visibility="collapsed",
            key=f"name_{pdf}",
        )
        # Destination preview -- reflects the chosen topic so what the
        # user sees is exactly where the file lands.
        destination = _proposed_destination(lib, edited_name, status,
                                            topic=chosen_topic)
        st.markdown("**Proposed destination**")
        st.code(str(destination.relative_to(lib)), language=None)

    with right:
        st.markdown("**First-page text** _(read-only preview)_")
        st.text_area(
            "snippet", value=prev.first_page_text or "_(no text extracted)_",
            height=400, label_visibility="collapsed", key=f"snip_{pdf}",
        )

    # Action row
    st.markdown("---")
    cols = st.columns([1, 1, 1, 1, 4])

    if cols[0].button("✅ Approve", key=f"approve_{pdf}", type="primary"):
        # MOVE model: file into the chosen topic folder (or standard).
        ok, msg = _approve_sort(pdf, edited_name, status, lib,
                                topic=chosen_topic, preview=prev)
        if ok:
            st.toast(f"Filed → {destination.relative_to(lib)}")
        else:
            st.toast(f"Failed: {msg}", icon="⚠️")
        st.rerun()

    if cols[1].button("⏭ Skip", key=f"skip2_{pdf}"):
        st.session_state.sort_skipped.add(str(pdf))
        st.rerun()

    if cols[2].button("🚩 Flag for manual", key=f"flag_{pdf}"):
        # Same as skip; documents intent
        st.session_state.sort_skipped.add(str(pdf))
        _log_activity("sort.flag", str(pdf.relative_to(lib)))
        st.rerun()

    if cols[3].button("🔍 Open file", key=f"open_{pdf}"):
        import subprocess
        subprocess.run(["open", str(pdf)], capture_output=True)


def _proposed_destination(
    lib: Path, canonical_name: str, status: str, *, topic: Optional[str] = None,
) -> Path:
    """Replicate the routing preview without touching disk.

    ``topic`` (07a-07f or None) selects the topic subtree so the
    preview matches where the MOVE-model ingest will actually file the
    paper.
    """
    from organization.system import OrganizationSystem

    # Build minimal metadata the router needs
    if status == "book":
        meta = {"document_type": "book"}
    elif status == "thesis":
        meta = {"document_type": "thesis"}
    elif status == "published":
        meta = {"doi": "preview"}
    elif status == "unpublished":
        meta = {"arxiv_id": "preview"}
    else:
        meta = {}

    # Extract first author from canonical name "Last, F., Last, F. - Title.pdf"
    if " - " in canonical_name:
        authors_part = canonical_name.split(" - ", 1)[0]
        first = authors_part.split(",")[0].strip()
        meta["authors"] = [{"family": first, "given": ""}]

    org = OrganizationSystem(lib, topic=topic)
    return org.router.route(meta, canonical_name)


def _approve_sort(
    pdf: Path,
    canonical_name: str,
    status: str,
    lib: Path,
    *,
    topic: Optional[str] = None,
    preview=None,
) -> tuple[bool, str]:
    """Actually file the paper. Returns (ok, message).

    ``canonical_name`` is what the user saw and approved. It's passed
    through to ``ingest_paper`` as a canonical_override so the user's
    edits are honoured (the pipeline no longer re-derives the name from
    metadata and silently overwrites the user's choice).

    ``topic`` (07a-07f or None) is the user's chosen topic destination
    from the Sort Queue dropdown.  MOVE model: the paper LIVES in that
    topic's subtree (or the standard tree when None).  Passing it
    explicitly to ``sort_one``/``ingest_paper`` also short-circuits the
    auto-classifier (Step 4.5), so the user's choice always wins.
    The old Phase-4 hardlink cross-filing was retired -- the library
    is one-home-per-paper.
    """
    from processing.bulk_sort import sort_one
    from processing.undo_log import UndoLog

    # Guard against the file vanishing between listing and approval
    if not pdf.exists():
        return False, f"source disappeared: {pdf}"

    undo_log = UndoLog()
    tx_id = undo_log.begin_transaction(f"Cockpit sort: {pdf.name}")

    try:
        result = sort_one(
            pdf, status,
            library_root=lib,
            dry_run=False,
            undo_log=undo_log,
            canonical_override=canonical_name,
            topic=topic,
            # The user already decided the topic via the dropdown
            # (default = the auto decision); don't let Step 4.5
            # re-classify and override an explicit "standard" choice.
            auto_topic=False,
        )
        if not result.get("ok"):
            return False, result.get("error", "unknown")

        undo_log.commit()
        _log_activity(
            "sort.approve",
            str(pdf.relative_to(lib)),
            result.get("destination", ""),
            tx_id,
        )
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _count_trash(lib: Path, sub: str) -> int:
    p = lib / ".trash" / sub
    if not p.exists():
        return 0
    return sum(1 for _ in iter_pdfs(p))


# ---------------------------------------------------------------------------
# Page: Upgrade Queue (preprint → published)
# ---------------------------------------------------------------------------

def render_upgrade_queue() -> None:
    st.header("⬆ Upgrade Queue")
    st.caption(
        "Preprints in `02/`/`03/` for which the publication-checker found a "
        "published version. Approve to download + file + move preprint to trash."
    )

    lib = _library()
    # Report path
    default_report = Path(__file__).resolve().parents[2] / "publication_report.json"
    report_path = st.text_input(
        "Publication report JSON",
        value=st.session_state.upgrade_report_path or str(default_report),
        help="Output of `python -m processing.publication_checker --json`",
    )
    st.session_state.upgrade_report_path = report_path

    rp = Path(report_path)
    if not rp.exists():
        st.warning(f"Report not found at {rp}. Run the publication checker first.")
        return

    try:
        report = json.loads(rp.read_text())
    except Exception as exc:
        st.error(f"Failed to parse report: {exc}")
        return

    published = report.get("published", [])
    min_conf = st.slider("Minimum confidence", 0.5, 1.0, 0.85, 0.01)

    candidates = [
        p for p in published
        if p.get("match", {}).get("confidence", 0) >= min_conf
        and str(p.get("file", "")) not in st.session_state.upgrade_skipped
    ]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Above threshold", len(candidates))
    col_b.metric("Skipped this session", len(st.session_state.upgrade_skipped))
    col_c.metric("Upgraded this session", sum(1 for a in st.session_state.activity_log if a["action"] == "upgrade.approve"))

    if not candidates:
        st.success(f"🎉 No candidates above confidence {min_conf:.0%}")
        return

    entry = candidates[0]
    match = entry.get("match", {})
    file_path = Path(entry.get("file", ""))

    st.subheader(f"Candidate 1 of {len(candidates)}")

    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Preprint file**")
        if file_path.exists():
            try:
                rel = file_path.relative_to(lib)
                st.code(str(rel), language=None)
            except ValueError:
                st.code(str(file_path), language=None)
        else:
            st.warning(f"Preprint missing: {file_path}")

        st.markdown(f"**DOI** &nbsp; `{match.get('doi', '?')}`")
        st.markdown(f"**Journal** &nbsp; {match.get('journal', '?')}")
        st.markdown(f"**Year** &nbsp; {match.get('year', '?')}")
        st.markdown(f"**Confidence** &nbsp; {match.get('confidence', 0):.0%}")

    with right:
        st.markdown("**Crossref title**")
        st.write(match.get("matched_title", "_(none)_"))
        st.markdown("**Parsed title**")
        st.write(entry.get("parsed_title", "_(none)_"))
        st.markdown("**Parsed authors**")
        st.write(", ".join(entry.get("parsed_authors", [])) or "_(none)_")

    st.markdown("---")
    cols = st.columns([1, 1, 1, 1, 4])

    if cols[0].button("✅ Download + Upgrade", key=f"upg_approve_{entry['file']}", type="primary"):
        ok, msg = _approve_upgrade(entry, lib)
        if ok:
            st.toast(msg, icon="✅")
        else:
            st.toast(f"Failed: {msg}", icon="⚠️")
        st.rerun()

    if cols[1].button("⏭ Skip", key=f"upg_skip_{entry['file']}"):
        st.session_state.upgrade_skipped.add(str(entry["file"]))
        st.rerun()

    if cols[2].button("🚩 Flag for manual", key=f"upg_flag_{entry['file']}"):
        st.session_state.upgrade_skipped.add(str(entry["file"]))
        from processing.upgrade_to_published import flag_for_manual_download
        try:
            flag_path = flag_for_manual_download(entry, lib)
            _log_activity("upgrade.flag", str(file_path.name), str(flag_path))
            st.toast(f"Flagged → {flag_path.parent.name}/", icon="🚩")
        except Exception as exc:
            st.error(f"Flag failed: {exc}")
        st.rerun()


def _approve_upgrade(entry: dict, lib: Path) -> tuple[bool, str]:
    """Download published version + file + move preprint to trash."""
    import tempfile
    from processing.undo_log import UndoLog
    from processing.upgrade_to_published import upgrade_paper

    undo_log = UndoLog()
    tx_id = undo_log.begin_transaction(f"Cockpit upgrade: {entry.get('filename', '?')}")

    with tempfile.TemporaryDirectory(prefix="cockpit_upgrade_") as d:
        try:
            r = upgrade_paper(
                entry,
                library_root=lib,
                download_dir=Path(d),
                dry_run=False,
                undo_log=undo_log,
            )
            if r.get("success"):
                undo_log.commit()
                _log_activity(
                    "upgrade.approve",
                    entry.get("file", ""),
                    r.get("destination", ""),
                    tx_id,
                )
                return True, r.get("action", "ok")
            return False, r.get("action", "unknown failure")
        except Exception as exc:
            return False, str(exc)


# ---------------------------------------------------------------------------
# Page: Maintenance
# ---------------------------------------------------------------------------

def render_maintenance() -> None:
    st.header("🧹 Maintenance")
    st.caption(
        "Run the same checks as `python -m maintenance.weekly_report`. "
        "Read-only — these just produce reports, no files moved."
    )

    lib = _library()

    # Phase 5: one-click full weekly run (the Monday plist's equivalent)
    # via the cockpit so users don't need a terminal to trigger it.
    with st.expander("Full weekly run (subprocess + report)", expanded=False):
        cols_full = st.columns([2, 2, 1])
        auto_apply = cols_full[0].checkbox(
            "Auto-apply safe transitions",
            value=False,
            help=(
                "Single-author Crossref hits at >= 0.95 confidence get "
                "upgraded; aged + permanently-unpublished get moved to 02."
            ),
        )
        limit = cols_full[1].number_input(
            "Crossref query limit (0 = no limit)",
            min_value=0, value=0,
        )
        if cols_full[2].button("▶ Run weekly now", key="run_weekly_now"):
            from ui.cockpit_actions import run_publication_check
            with st.spinner("Running weekly maintenance (may take a few minutes)..."):
                out = run_publication_check(
                    lib,
                    auto_apply_safe=auto_apply,
                    limit=(limit or None),
                )
            if out.ok:
                st.success(f"Done.  Report: `{out.report_path}`")
                if out.summary:
                    st.session_state.maintenance_results = out.summary
                _log_activity("maintenance.run_full", str(lib),
                              out.report_path or "")
            else:
                st.error(out.message)

    st.divider()

    cols = st.columns(4)
    do_pub = cols[0].checkbox("Publications", value=True)
    do_age = cols[1].checkbox("Aging", value=True)
    do_dup = cols[2].checkbox("Duplicates", value=True)
    do_count = cols[3].checkbox("12/ backlog", value=True)

    if st.button("▶ Run checks", type="primary"):
        from maintenance.weekly_report import (
            check_publications, check_aging, check_duplicates, count_to_be_sorted
        )
        results = {}

        with st.spinner("Running checks..."):
            if do_count:
                results["to_be_sorted"] = count_to_be_sorted(lib)
            if do_age:
                results["aging"] = check_aging(lib, verbose=False)
            if do_dup:
                results["duplicates"] = check_duplicates(lib, verbose=False)
            if do_pub:
                # This is slow (Crossref API per paper) — give the user a heads-up
                st.warning("Publication check hits Crossref API — may take minutes")
                results["publications"] = check_publications(lib, limit=100, verbose=False)

        st.success("Done.")
        st.session_state.maintenance_results = results

    # Display previous results if any
    res = st.session_state.get("maintenance_results")
    if not res:
        return

    st.subheader("Results")

    if "to_be_sorted" in res:
        c = res["to_be_sorted"]
        st.markdown(f"**12 - To be sorted/ backlog**: {c['total']} PDFs")
        for sub, n in c["by_subfolder"].items():
            st.markdown(f"&nbsp;&nbsp;&nbsp;{sub}: **{n}**")

    if "aging" in res:
        st.markdown(f"**Aging working papers (> 5y)**: {len(res['aging'])}")

    if "duplicates" in res:
        st.markdown(f"**Potential duplicate clusters**: {len(res['duplicates'])}")
        for c in res["duplicates"][:10]:
            st.markdown(
                f"&nbsp;&nbsp;&nbsp;[{c.get('title_similarity', 0):.0f}%] "
                + " ↔ ".join(f.get("filename", "?")[:60] for f in c.get("files", []))
            )

    if "publications" in res:
        pubs = res["publications"]
        total = len(pubs.get("unpublished", [])) + len(pubs.get("working", []))
        st.markdown(f"**Newly-published papers found**: {total}")


# ---------------------------------------------------------------------------
# Page: Stats
# ---------------------------------------------------------------------------

@st.cache_data(ttl=1800, show_spinner=False)
def _classify_cached(title: str, text_snippet: str) -> list[dict]:
    """Cached topic classifier (30-minute TTL). Skips work when the user
    stares at the same paper across multiple Streamlit reruns."""
    if not title:
        return []
    try:
        from processing.topic_classifier import classify_by_keywords
        return classify_by_keywords(title, text_snippet)
    except Exception as exc:
        logger.debug("topic classify failed: %s", exc)
        return []


@st.cache_data(ttl=10, show_spinner=False)
def _watcher_status_cached() -> dict:
    """Cache ``launchctl print`` output for 10s.

    The sidebar re-renders on every Streamlit interaction and the
    subprocess spawn is ~50-100ms.  10s is short enough that a user
    who just clicked Start sees the new state on the next rerun, but
    long enough that clicking other buttons doesn't pay the
    subprocess cost each time.
    """
    from ui.cockpit_actions import watcher_status
    return watcher_status()


@st.cache_data(ttl=60, show_spinner=False)
def _gather_attention_cached(library_str: str, include_dismissed: bool) -> list:
    """Cache the FULL attention list for 60s.

    The sidebar count and the Attention tab body both call into this,
    so without caching every interaction in the tab re-globs the
    library.  Returning the full list (rather than just the count)
    means the tab body reuses the same data and stays snappy on a
    28k-PDF library.
    """
    from ui.attention_queue import gather_attention_items
    return gather_attention_items(
        Path(library_str), include_dismissed=include_dismissed
    )


def _attention_count_cached(library_str: str) -> int:
    """Thin wrapper that returns the length of the cached attention list."""
    return len(_gather_attention_cached(library_str, False))


# Expose ``.clear()`` for action handlers that want to invalidate the
# cache after a destructive op (so the sidebar badge updates instantly
# rather than waiting for the TTL).
_attention_count_cached.clear = _gather_attention_cached.clear  # type: ignore[attr-defined]


@st.cache_data(ttl=300, show_spinner=False)
def _count_pdfs_cached(folder_str: str) -> int:
    """Cached count of PDFs under a folder. TTL = 5 minutes.

    rglob over a 28k-paper library takes seconds; we don't want it to run
    on every Streamlit rerun. The folder path is keyed as a string because
    ``st.cache_data`` only hashes JSON-able args.
    """
    p = Path(folder_str)
    if not p.exists():
        return 0
    return sum(1 for _ in iter_pdfs(p))


def render_stats() -> None:
    st.header("📊 Library Stats")
    st.caption(
        "Counts are cached for 5 minutes. Use the button to recompute "
        "immediately after a batch of approvals."
    )

    if st.button("↻ Recompute now"):
        _count_pdfs_cached.clear()
        st.rerun()

    lib = _library()
    if not lib.exists():
        st.error("Library not found.")
        return

    from maintenance.weekly_report import count_to_be_sorted

    # Folder counts (cached)
    folders = [
        "01 - Published papers",
        "02 - Unpublished papers",
        "03 - Working papers",
        "04 - Papers to be downloaded",
        "05 - Books and lecture notes",
        "06 - Theses",
    ]
    st.subheader("Folder counts")
    cols = st.columns(len(folders))
    for col, f in zip(cols, folders):
        n = _count_pdfs_cached(str(lib / f))
        col.metric(f.split(" - ")[1] if " - " in f else f, n)

    st.divider()
    st.subheader("12 - To be sorted/ backlog")
    backlog = count_to_be_sorted(lib)
    st.metric("Total pending", backlog["total"])
    for sub, n in backlog["by_subfolder"].items():
        st.markdown(f"- {sub}: **{n}**")

    st.divider()
    st.subheader("Trash (recoverable)")
    cols = st.columns(2)
    cols[0].metric("Sorted originals", _count_trash(lib, "sorted_originals"))
    cols[1].metric("Upgraded preprints", _count_trash(lib, "upgraded_preprints"))


# ---------------------------------------------------------------------------
# Page: Pipeline Preview
# ---------------------------------------------------------------------------

def render_pipeline_preview() -> None:
    st.header("🔭 Pipeline Preview")
    st.caption(
        "Read-only. Runs the topic classifier across the library and shows "
        "what it *would* do — compared against where each paper currently "
        "lives (your hand-filing = ground truth). **Nothing is moved.** "
        "This is the evidence for deciding whether to trust a bulk classify."
    )

    lib = _library()
    if not lib.exists():
        st.error("Library not found.")
        return

    # Scope + sample controls.  A full 29k scan runs the (fast, keyword-
    # based) classifier per paper; still, offer a sample for a quick look.
    topic_dirs = [d.name for d in sorted(lib.iterdir())
                  if d.is_dir() and d.name[:3] in (
                      "01 ", "02 ", "03 ", "05 ", "06 ", "07")] if lib.exists() else []
    scope_opts = ["Whole library"] + topic_dirs
    c1, c2, c3 = st.columns([2, 1, 1])
    scope_sel = c1.selectbox("Scope", scope_opts, index=0)
    sample = c2.selectbox("Sample", ["All", "200", "1000", "5000"], index=0)
    enrich = c3.checkbox(
        "Use cached abstracts", value=True,
        help="Classify on the abstract/first-pages text cached in sidecars "
             "(run the backfill below first). Lifts recall ~63%→~91% at "
             "unchanged precision. Falls back to title-only where no text "
             "is cached.")

    if st.button("▶ Run preview", type="primary"):
        from processing.pipeline_preview import preview_topic_filing
        scope = None if scope_sel == "Whole library" else lib / scope_sel
        limit = None if sample == "All" else int(sample)
        with st.spinner("Classifying… (read-only)"):
            summary, proposals = preview_topic_filing(
                lib, scope=scope, limit=limit, enrich=enrich,
            )
        st.session_state["preview_summary"] = summary.to_dict()
        st.session_state["preview_proposals"] = [p.to_dict() for p in proposals]

    s = st.session_state.get("preview_summary")
    proposals = st.session_state.get("preview_proposals")
    if not s:
        st.info("Choose a scope and click **Run preview**.")
        return

    # Trust metrics.
    st.subheader("Trust metrics")
    m = st.columns(4)
    m[0].metric("Scanned", s["scanned"])
    m[1].metric("Agreement", f"{s['agreement_rate']:.0%}",
                help="Of hand-filed papers the classifier is confident "
                     "about, how often it picks the SAME topic you did.")
    m[2].metric("Topic recall", f"{s['topic_recall']:.0%}",
                help="Of hand-filed topic papers, how many the classifier "
                     "is confident enough to auto-file at all.")
    m[3].metric("Disagreements", s["disagree"],
                help="Hand-filed papers the classifier would send elsewhere "
                     "— the spot-check list (misfilings OR classifier errors).")
    m2 = st.columns(4)
    m2[0].metric("Would newly file", s["proposed_moves"])
    m2[1].metric("Would suggest", s["proposed_suggestions"])
    m2[2].metric("Recall misses", s["recall_miss"])
    m2[3].metric("In a topic now", s["in_topic"])
    m3 = st.columns(4)
    m3[0].metric("Book/thesis misfiled", s.get("doctype_mismatches", 0),
                 help="Books or theses detected in an article folder (01/02/03).")
    m3[1].metric("Sub-subtopic fits", s.get("subtopic_suggestions", 0),
                 help="Papers a finer sub-subtopic (e.g. 07a Numerical methods) fits.")

    st.caption(
        f"Agreement {s['agreement_rate']:.0%} on {s['agree'] + s['disagree']} "
        f"confident hand-filed papers. The higher this is, the safer a "
        f"gated bulk-apply becomes. (Apply is a separate, explicitly-"
        f"approved step — this screen never changes the library.)"
    )

    # Abstract backfill: caches abstract/first-pages text into sidecars so
    # the classifier reads content, not just titles (the recall lever).
    with st.expander("📄 Cache abstracts (improves recall)"):
        st.caption(
            "Extracts the abstract/first pages of each PDF into its sidecar "
            "(one-time, resumable, safe — metadata only). The classifier "
            "then reads content. The full library is best run headless: "
            "`python -m processing.classifier_text` (≈30–60 min). Use a "
            "small batch here to try it.")
        cbf = st.columns([1, 1])
        bf_n = cbf[0].selectbox("Batch", ["100", "500", "2000", "All"], index=0,
                                key="bf_limit")
        if cbf[1].button("Cache abstracts now", key="bf_run"):
            from processing.classifier_text import backfill_classifier_text
            lim = None if bf_n == "All" else int(bf_n)
            with st.spinner("Extracting abstracts…"):
                bstats = backfill_classifier_text(lib, limit=lim)
            st.success(f"Cached: {bstats}")

    # Reviewable band lists.
    def _rows(status):
        rel = []
        for p in proposals or []:
            if p["status"] != status:
                continue
            rel.append({
                "paper": Path(p["path"]).name,
                "current": p["current_topic"] or "—",
                "proposed": p["proposed_topic"] or p["suggested_topic"] or "—",
                "confidence": f"{p['confidence']:.0%}",
                "path": str(Path(p["path"]).relative_to(lib)),
            })
        return rel

    st.divider()
    for label, status, hint in [
        ("🚩 Disagreements (spot-check first)", "disagree",
         "Classifier would auto-file these to a DIFFERENT topic than where "
         "you put them. Either a misfiling worth fixing or a classifier miss."),
        ("➕ Would newly file (confident)", "move",
         "Not in any topic folder; classifier is confident enough to auto-file."),
        ("❓ Would suggest (needs your call)", "suggest",
         "Medium-confidence guesses for un-topiced papers."),
        ("🕳 Recall misses", "recall_miss",
         "Hand-filed in a topic, but the classifier wouldn't auto-file them "
         "— shows where its recall still lags your judgement."),
    ]:
        rows = _rows(status)
        with st.expander(f"{label} — {len(rows)}"):
            st.caption(hint)
            if rows:
                st.dataframe(rows[:500], use_container_width=True,
                             hide_index=True)
                if len(rows) > 500:
                    st.caption(f"Showing first 500 of {len(rows)}.")
            else:
                st.write("_none_")

    # Document-type mismatches (books/theses in article folders).
    doc_rows = [{
        "paper": Path(p["path"]).name,
        "detected": p.get("doc_kind", "?"),
        "path": str(Path(p["path"]).relative_to(lib)),
    } for p in (proposals or []) if p.get("doc_mismatch")]
    with st.expander(f"📕 Book/thesis in an article folder — {len(doc_rows)}"):
        st.caption("Detected as a book or thesis (by title) but sitting in "
                   "01/02/03. Candidates for 05 - Books / 06 - Theses.")
        st.dataframe(doc_rows[:500], use_container_width=True, hide_index=True) \
            if doc_rows else st.write("_none_")

    # Sub-subtopic suggestions (finer routing within a topic).
    sub_rows = [{
        "paper": Path(p["path"]).name,
        "topic": p.get("current_topic") or p.get("proposed_topic") or "—",
        "subtopic": p.get("subtopic"),
        "currently_in": p.get("current_subtopic") or "(topic root)",
        "path": str(Path(p["path"]).relative_to(lib)),
    } for p in (proposals or [])
        if p.get("subtopic") and p.get("subtopic") != p.get("current_subtopic")]
    with st.expander(f"🗂 Sub-subtopic fits — {len(sub_rows)}"):
        st.caption("A finer sub-subtopic (e.g. 07a Numerical methods, 07a "
                   "G-BSDEs, 07b ESG) matches; the paper is at the topic root.")
        st.dataframe(sub_rows[:500], use_container_width=True, hide_index=True) \
            if sub_rows else st.write("_none_")

    # ----- Gated bulk apply (the only place this screen can change files) ---
    st.divider()
    st.subheader("⚙ Apply confident moves")
    n_moves = s.get("proposed_moves", 0)
    st.caption(
        f"Files the **{n_moves}** confident *“would newly file”* papers into "
        f"their topic folders — one undoable transaction, reversible from the "
        f"Activity tab. Only confident moves are applied; disagreements, "
        f"suggestions and recall-misses are left for you. Re-scans fresh "
        f"before moving."
    )
    if n_moves == 0:
        st.info("No confident moves to apply.")
    else:
        confirm = st.checkbox(
            f"I understand this will MOVE {n_moves} file(s).",
            key="preview_apply_confirm",
        )
        ca, cb = st.columns(2)
        if ca.button("Dry-run (list only)", key="preview_apply_dryrun"):
            from processing.pipeline_preview import apply_topic_proposals
            res = apply_topic_proposals(lib, dry_run=True, enrich=enrich)
            st.write(f"Would apply **{res['selected']}** move(s).")
            st.dataframe(
                [{"paper": Path(w["path"]).name, "topic": w["topic"]}
                 for w in res["would_apply"][:500]],
                use_container_width=True, hide_index=True,
            )
        if cb.button("✅ Apply now", type="primary", disabled=not confirm,
                     key="preview_apply_now"):
            from processing.pipeline_preview import apply_topic_proposals
            with st.spinner("Filing…"):
                res = apply_topic_proposals(lib, statuses=("move",), enrich=enrich)
            ok_n, fail_n = len(res["applied"]), len(res["failed"])
            if res.get("tx_id"):
                _log_activity("topic.bulk_apply", f"{ok_n} moved",
                              f"{fail_n} failed", res["tx_id"])
            st.success(f"Filed {ok_n} paper(s); {fail_n} failed. "
                       f"Undo from the Activity tab (one transaction).")
            if res["failed"]:
                st.dataframe(
                    [{"paper": Path(f["path"]).name, "why": f["msg"]}
                     for f in res["failed"][:200]],
                    use_container_width=True, hide_index=True,
                )
            # Fresh numbers next render.
            for k in ("preview_summary", "preview_proposals"):
                st.session_state.pop(k, None)
            _count_pdfs_cached.clear()


# ---------------------------------------------------------------------------
# Page: Activity
# ---------------------------------------------------------------------------

def render_activity() -> None:
    st.header("🕐 Recent activity")
    st.caption(
        "Every reversible operation on the library is listed here -- not "
        "only cockpit approvals, but ALSO anything done from the CLI, the "
        "watcher, or the weekly task (they all share one undo log in the "
        "library). Each transaction has an Undo button."
    )

    # Primary source of truth: the shared undo log on disk.  This makes
    # operations performed OUTSIDE this cockpit session (CLI upgrades,
    # the Monday plist, the watcher) visible and reversible here -- the
    # user asked for traceability + cancellability that isn't
    # CLI-only.  The session activity_log still feeds the human-readable
    # action labels.
    from processing.undo_log import UndoLog, LOG_DIR
    log = UndoLog()
    try:
        transactions = log.list_transactions()
    except Exception as exc:
        transactions = []
        st.warning(f"Could not read the undo log at {LOG_DIR}: {exc}")

    # Map tx_id -> the richest session label we have, for nicer display.
    session_by_tx = {
        e["tx_id"]: e for e in st.session_state.get("activity_log", [])
        if e.get("tx_id")
    }

    st.caption(f"Undo log: `{LOG_DIR}`  ·  {len(transactions)} transaction(s)")

    if not transactions:
        st.info("No reversible transactions recorded yet.")
        return

    # Newest first.
    for i, tx in enumerate(reversed(transactions)):
        tx_id = tx.get("id", "")
        desc = tx.get("description", "(no description)")
        when = tx.get("timestamp", "")[:19].replace("T", " ")
        n_ops = tx.get("operations_count", "?")
        undone = tx.get("undone", False)
        label = f"{when}  ·  {desc}  ·  {n_ops} ops" + ("  ·  UNDONE" if undone else "")
        with st.expander(label, expanded=False):
            st.markdown(f"**Transaction**: `{tx_id}`")
            sess = session_by_tx.get(tx_id)
            if sess:
                st.markdown(f"**Action**: {sess.get('action', '')}")
                if sess.get("source"):
                    st.markdown(f"**Source**: `{sess['source']}`")
                if sess.get("destination"):
                    st.markdown(f"**Destination**: `{sess['destination']}`")
            if undone:
                st.caption("Already undone.")
            else:
                col1, col2 = st.columns([1, 1])
                if col1.button("Preview undo", key=f"prev_{i}_{tx_id}"):
                    _preview_undo(tx_id)
                if col2.button("↶ Undo", key=f"undo_{i}_{tx_id}", type="primary"):
                    _undo_transaction(tx_id)
                    st.rerun()


def _preview_undo(tx_id: str) -> None:
    """Dry-run the undo so the user sees exactly what would be reversed
    before committing to it."""
    from processing.undo_log import UndoLog
    log = UndoLog()
    try:
        results = log.undo_transaction(tx_id, dry_run=True)
        st.info(
            f"Undo would perform {len(results)} action(s):\n"
            + "\n".join(f"- {r.get('action', '?')}" for r in results[:30])
        )
    except Exception as exc:
        st.error(f"Undo preview failed: {exc}")


def _undo_transaction(tx_id: str) -> None:
    from processing.undo_log import UndoLog
    log = UndoLog()
    try:
        results = log.undo_transaction(tx_id, dry_run=False)
        st.toast(f"Undid {len(results)} ops in {tx_id}", icon="↶")
        _log_activity("undo", tx_id, "", tx_id)
        _attention_count_cached.clear()
    except Exception as exc:
        st.error(f"Undo failed: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Page: Attention Queue (unified "needs your attention" inbox)
# ---------------------------------------------------------------------------

def _attention_severity_emoji(sev: str) -> str:
    return {"error": "🛑", "warning": "⚠", "info": "ℹ"}.get(sev, "•")


def render_attention() -> None:
    """Show the unified attention queue.

    Pulls items from every collector (watcher failures, upgrade flags,
    aging candidates, conflict copies) and lets the user act on each
    one in place.  All destructive actions still go through
    ``undo_log`` so the Activity tab can reverse them.
    """
    import subprocess
    import webbrowser
    from ui.attention_queue import (
        dismiss,
        gather_attention_items,
        undismiss,
    )

    st.header("📬 Attention Queue")
    st.caption(
        "Everything across the pipeline that wants your eyes. "
        "Dismissed items disappear for the snooze window and reappear after."
    )

    lib = _library()
    if not lib:
        st.warning("Library root not set — see sidebar.")
        return

    # Allow the user to toggle dismissed items on/off so they can
    # un-snooze something they hid in haste.
    show_dismissed = st.checkbox("Show dismissed items", value=False)

    # Use the same 60s cache the sidebar count uses so clicking around
    # the Attention tab doesn't re-glob the library on every rerun.
    items = _gather_attention_cached(str(lib), show_dismissed)
    if not items:
        st.success("Nothing needs your attention right now. ✓")
        return

    # Group by source for visual chunking.
    by_source: dict[str, list] = {}
    for it in items:
        by_source.setdefault(it.source, []).append(it)

    source_labels = {
        "watcher_failure": "Watcher failures",
        "upgrade_flag": "Manual download requests",
        "aging": "Aging working papers",
        "conflict_copy": "Dropbox conflict copies",
        "borderline_match": "Borderline Crossref matches",
        "topic_suggestion": "Topic suggestions to confirm",
        "permanently_unpublished": "Marked permanently unpublished",
    }

    # Bulk dismiss bar: a session-state set of keys the user has
    # checked.  Pruned to live items each render so a previously-
    # selected key that no longer exists doesn't pollute the bulk
    # action.
    attn_sel_key = "attention_selected"
    if attn_sel_key not in st.session_state:
        st.session_state[attn_sel_key] = set()
    live_keys = {it.key for it in items}
    st.session_state[attn_sel_key] &= live_keys
    attn_selected: set[str] = st.session_state[attn_sel_key]
    bar = st.columns([1, 1, 2, 2])
    if bar[0].button("Select all", key="attn_sel_all",
                     use_container_width=True):
        st.session_state[attn_sel_key] = set(live_keys)
        st.rerun()
    if bar[1].button("Clear", key="attn_sel_clear",
                     use_container_width=True,
                     disabled=not attn_selected):
        st.session_state[attn_sel_key] = set()
        st.rerun()
    if bar[2].button(
        f"Dismiss {len(attn_selected)} for 7 days",
        key="attn_bulk_dismiss_7d",
        use_container_width=True,
        disabled=not attn_selected,
    ):
        from ui.attention_queue import dismiss as _dismiss
        for k in list(attn_selected):
            _dismiss(k, days=7)
        st.toast(f"Dismissed {len(attn_selected)} for 7 days")
        st.session_state[attn_sel_key] = set()
        _attention_count_cached.clear()
        st.rerun()
    if bar[3].button(
        f"Dismiss {len(attn_selected)} for 30 days",
        key="attn_bulk_dismiss_30d",
        use_container_width=True,
        disabled=not attn_selected,
    ):
        from ui.attention_queue import dismiss as _dismiss
        for k in list(attn_selected):
            _dismiss(k, days=30)
        st.toast(f"Dismissed {len(attn_selected)} for 30 days")
        st.session_state[attn_sel_key] = set()
        _attention_count_cached.clear()
        st.rerun()
    st.divider()

    for source_key, source_items in by_source.items():
        st.subheader(f"{source_labels.get(source_key, source_key)} ({len(source_items)})")
        for it in source_items:
            with st.container(border=True):
                # Per-item checkbox in front of the existing content
                # column.  Toggles fold into the session_state set.
                ck = st.checkbox(
                    "select",
                    value=it.key in attn_selected,
                    key=f"attn_sel_{it.key}",
                    label_visibility="collapsed",
                )
                if ck:
                    attn_selected.add(it.key)
                else:
                    attn_selected.discard(it.key)
                cols = st.columns([0.7, 0.3])
                with cols[0]:
                    st.markdown(
                        f"{_attention_severity_emoji(it.severity)} **{it.title}**"
                    )
                    if it.detail:
                        with st.expander("Details", expanded=False):
                            st.markdown(it.detail)
                    if it.created_at:
                        st.caption(f"first seen: {it.created_at}")
                with cols[1]:
                    # "Open DOI" gets rendered as a real link_button so
                    # macOS doesn't steal focus the way webbrowser.open
                    # would; everything else stays an action button.
                    doi_for_link = it.payload.get("doi", "")
                    if any(a_id == "open_doi" for _, a_id in it.actions) and doi_for_link:
                        st.link_button(
                            "Open DOI",
                            f"https://doi.org/{doi_for_link}",
                            use_container_width=True,
                        )
                    for label, action_id in it.actions:
                        if action_id == "open_doi":
                            continue  # already rendered as link above
                        btn_key = f"attn_{it.key}_{action_id}"
                        if not st.button(label, key=btn_key, use_container_width=True):
                            continue
                        # Dispatch
                        try:
                            if action_id == "dismiss_7d":
                                dismiss(it.key, days=7)
                                st.toast(f"Dismissed for 7 days: {it.title}")
                            elif action_id == "dismiss_30d":
                                dismiss(it.key, days=30)
                                st.toast(f"Dismissed for 30 days: {it.title}")
                            elif action_id == "mark_flag_done":
                                fp = Path(it.payload.get("flag_file", ""))
                                if fp.exists():
                                    fp.unlink()
                                    st.toast(f"Removed flag {fp.name}")
                                    # Invalidate cached count so the
                                    # sidebar badge updates immediately
                                    # rather than after the 60s TTL.
                                    _attention_count_cached.clear()
                            elif action_id == "reveal_in_finder":
                                p = it.payload.get("path", "")
                                if p:
                                    subprocess.run(["open", "-R", p], check=False)
                            elif action_id == "delete_conflict":
                                p = Path(it.payload.get("path", ""))
                                if p.exists():
                                    # Move to .trash/ rather than hard-delete so
                                    # the user can undo via Finder.
                                    trash = lib / ".trash" / "conflict_copies"
                                    trash.mkdir(parents=True, exist_ok=True)
                                    p.rename(trash / p.name)
                                    st.toast("Moved conflict copy to .trash/")
                                    _attention_count_cached.clear()
                            elif action_id == "watcher_retry":
                                st.info(
                                    "Drop the failing file back into the inbox to "
                                    "retry — the watcher will re-ingest it."
                                )
                            elif action_id == "transition_aged":
                                # Actually do the move via aging_checker.
                                # Single-paper transition: build a minimal
                                # candidate dict the way find_aged_papers
                                # does and call transition_aged_papers.
                                from processing.aging_checker import (
                                    find_aged_papers, transition_aged_papers,
                                )
                                # Find this paper in the global candidate
                                # list — safer than reconstructing the
                                # destination by hand because the alpha
                                # routing has edge cases (nobiliary
                                # particles, Greek/Cyrillic, …).
                                all_aged = find_aged_papers(lib)
                                target_path = it.payload.get("path", "")
                                match = next(
                                    (c for c in all_aged if c["path"] == target_path),
                                    None,
                                )
                                if match is None:
                                    st.warning(
                                        "Paper no longer in aging set; refresh and retry."
                                    )
                                else:
                                    results = transition_aged_papers([match], dry_run=False)
                                    status = results[0]["status"] if results else "no-op"
                                    st.toast(f"Aging: {status}")
                                    _attention_count_cached.clear()
                            elif action_id == "reset_recheck":
                                # Restore a paper the state machine
                                # gave up on.  Backs the Phase 2
                                # publication_state.reset_recheck_state.
                                from processing.publication_state import (
                                    reset_recheck_state,
                                )
                                p = Path(it.payload.get("path", ""))
                                if p.exists():
                                    out = reset_recheck_state(p)
                                    if out is None:
                                        st.warning("No sidecar — nothing to reset.")
                                    else:
                                        st.toast(f"Recheck state reset for {p.name}")
                                        _attention_count_cached.clear()
                            elif action_id == "accept_topic":
                                # Move the paper into its suggested
                                # topic folder via the undo log
                                # (reversible from the Activity tab).
                                from processing.publication_topic_router import (
                                    accept_topic_suggestion,
                                )
                                from processing.undo_log import UndoLog
                                p = Path(it.payload.get("path", ""))
                                ulog = UndoLog()
                                tx = ulog.begin_transaction(
                                    f"Accept topic {it.payload.get('topic')}: {p.name}"
                                )
                                ok, msg = accept_topic_suggestion(p, lib, undo_log=ulog)
                                if ok:
                                    ulog.commit()
                                    _log_activity("topic.accept",
                                                  str(p), msg, tx)
                                    st.toast(msg)
                                    _attention_count_cached.clear()
                                else:
                                    st.warning(msg)
                            elif action_id == "reject_topic":
                                # Reject through the undo log so it's
                                # reversible from the Activity tab (a
                                # rejected suggestion is not lost forever).
                                from processing.publication_topic_router import (
                                    reject_topic_suggestion,
                                )
                                from processing.undo_log import UndoLog
                                p = Path(it.payload.get("path", ""))
                                ulog = UndoLog()
                                tx = ulog.begin_transaction(
                                    f"Reject topic {it.payload.get('topic')}: {p.name}"
                                )
                                if reject_topic_suggestion(p, undo_log=ulog):
                                    ulog.commit()
                                    _log_activity("topic.reject",
                                                  str(p), "suggestion cleared", tx)
                                    st.toast(f"Cleared topic suggestion for {p.name}")
                                    _attention_count_cached.clear()
                            else:
                                st.warning(f"Unknown action: {action_id}")
                        except Exception as exc:
                            st.error(f"Action failed: {exc}")
                        st.rerun()

    if show_dismissed:
        with st.expander("Un-dismiss an item", expanded=False):
            key_to_undo = st.text_input("Key to un-dismiss", key="undismiss_key")
            if st.button("Un-dismiss", key="undismiss_btn"):
                if key_to_undo:
                    undismiss(key_to_undo)
                    st.toast(f"Un-dismissed {key_to_undo}")
                    st.rerun()


# ---------------------------------------------------------------------------
# Page: To Download (04/ browser + DOI form) -- Phase 5
# ---------------------------------------------------------------------------

def render_to_download() -> None:
    """Browse the manual-download queue and download papers by DOI."""
    from ui.cockpit_actions import (
        download_doi_to_inbox,
        list_download_flags,
        mark_flag_done,
    )
    from watcher.config import WatcherConfig

    st.header("⬇ To Download")
    st.caption(
        "Papers the upgrade pipeline flagged for manual download, plus a "
        "one-shot form for resolving a known DOI right now."
    )

    lib = _library()

    # Inbox is where downloaded PDFs land for the watcher to pick up.
    try:
        inbox = WatcherConfig.load().inbox_dir
    except Exception:
        inbox = Path.home() / "Downloads" / "MathInbox"

    # --- DOI download form -----------------------------------------
    with st.container(border=True):
        st.subheader("Download by DOI")
        st.caption(f"PDF will be saved to `{inbox}` for the watcher to ingest.")
        cols = st.columns([4, 1])
        doi = cols[0].text_input(
            "DOI or https://doi.org/... URL", key="doi_form_input"
        )
        if cols[1].button("Download", key="doi_form_go", type="primary",
                          use_container_width=True):
            if not doi.strip():
                st.warning("Enter a DOI first.")
            else:
                with st.spinner("Trying download strategies..."):
                    result = download_doi_to_inbox(doi.strip(), inbox)
                if result.ok:
                    st.success(f"Saved: {result.pdf_path}")
                    _log_activity("download.doi", doi, result.pdf_path or "")
                    _attention_count_cached.clear()
                else:
                    st.error(result.message)

    # --- Flag browser ---------------------------------------------
    flags = list_download_flags(lib)
    st.subheader(f"Manual-download queue ({len(flags)})")
    if not flags:
        st.success("Nothing pending — the upgrade pipeline didn't queue anything.")
        return

    for flag in flags:
        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"**{flag['title']}**")
                st.caption(f"Journal: {flag['journal']}")
                if flag["doi"]:
                    st.code(f"DOI: {flag['doi']}", language=None)
                with st.expander("Flag body", expanded=False):
                    st.code(flag["body"], language=None)
            with cols[1]:
                if flag["doi"]:
                    st.link_button(
                        "Open DOI",
                        f"https://doi.org/{flag['doi']}",
                        use_container_width=True,
                    )
                if flag["doi"] and st.button(
                    "Download now", key=f"flag_dl_{flag['flag']}",
                    use_container_width=True,
                ):
                    with st.spinner("Downloading..."):
                        result = download_doi_to_inbox(flag["doi"], inbox)
                    if result.ok:
                        st.toast(f"Saved → {result.pdf_path}")
                        _log_activity("download.flag", flag["doi"],
                                      result.pdf_path or "")
                        # Auto-clear the flag now that the download
                        # succeeded -- otherwise the user has to click
                        # Mark done as a separate step and the
                        # Attention badge stays stuck on this item.
                        if mark_flag_done(flag["flag"], lib):
                            _attention_count_cached.clear()
                        st.rerun()
                    else:
                        st.error(result.message)
                if st.button(
                    "Mark done", key=f"flag_done_{flag['flag']}",
                    use_container_width=True,
                ):
                    if mark_flag_done(flag["flag"], lib):
                        st.toast(f"Cleared flag {flag['flag'].name}")
                        _attention_count_cached.clear()
                        st.rerun()


# ---------------------------------------------------------------------------
# Page: Settings (config editor) -- Phase 5
# ---------------------------------------------------------------------------

def render_settings() -> None:
    """Form-driven editor for the watcher config + Unpaywall email."""
    from ui.cockpit_actions import (
        EDITABLE_CONFIG_KEYS,
        load_cockpit_config,
        save_cockpit_config,
    )

    st.header("⚙ Settings")
    st.caption(
        "Persists watcher config to YAML.  ``UNPAYWALL_EMAIL`` is an "
        "environment variable -- the cockpit prints the export line so you "
        "can paste it into your shell rc."
    )

    current = load_cockpit_config()
    with st.form(key="settings_form"):
        new_values: dict = {}
        for key, label, kind in EDITABLE_CONFIG_KEYS:
            cur = current.get(key, "")
            if kind is bool:
                new_values[key] = st.checkbox(label, value=bool(cur), key=f"set_{key}")
            elif kind is float:
                try:
                    fcur = float(cur) if cur != "" else 0.0
                except (TypeError, ValueError):
                    fcur = 0.0
                new_values[key] = st.number_input(
                    label, value=fcur, step=0.5, key=f"set_{key}",
                )
            else:
                new_values[key] = st.text_input(
                    label, value=str(cur), key=f"set_{key}",
                )
        submitted = st.form_submit_button("Save", type="primary")
    if submitted:
        ok, msg = save_cockpit_config(new_values)
        if ok:
            st.success(msg)
            _log_activity("settings.save", "", "")
            # Sync the sidebar's library_root text input with the new
            # value so a tab-switch immediately after save doesn't
            # operate on the stale path.  Force rerun to refresh.
            if "library_root" in new_values:
                st.session_state.library_root = str(
                    Path(new_values["library_root"]).expanduser().resolve()
                )
            st.rerun()
        else:
            st.error(msg)

    st.divider()

    # Library-wide identity-sidecar tools.  Backfill is the
    # one-shot bootstrap for the existing 28k papers (Phase 2's state
    # machine has nothing to chew on until sidecars exist for the
    # corpus).  Verify runs drift_check against every PDF so the
    # user can catch Dropbox resync corruption.
    lib = _library()
    st.subheader("Identity sidecars")
    st.caption(
        f"Library: `{lib}`.  Backfill creates a minimal `.meta.json` "
        f"sidecar next to every PDF that doesn't have one yet.  Verify "
        f"recomputes the content hash and reports drift."
    )
    bf_cols = st.columns([1, 1, 2])
    bf_limit = bf_cols[2].number_input(
        "Limit (0 = no cap)", min_value=0, value=0, key="bf_limit",
    )
    if bf_cols[0].button("Backfill sidecars", key="bf_run",
                         use_container_width=True):
        from processing.identity import backfill_directory
        with st.spinner("Walking the library..."):
            summary = backfill_directory(
                lib, limit=(bf_limit or None), verbose=False,
            )
        st.success(
            f"Scanned {summary['scanned']} · wrote {summary['written']} · "
            f"skipped {summary['skipped']} · errors {summary['errors']}"
        )
        _log_activity("settings.backfill", str(lib),
                      f"wrote={summary['written']}")
    if bf_cols[1].button("Verify sidecars", key="bf_verify",
                         use_container_width=True):
        from processing.identity import verify_all_sidecars, list_hash_collisions
        with st.spinner("Verifying every sidecar (reads 1MB per PDF)..."):
            summary = verify_all_sidecars(lib, limit=(bf_limit or None))
            # Audit-7 #8: also surface content-hash collisions so
            # the user knows when two PDFs share the same 1MB
            # prefix (template-heavy publishers can do this
            # legitimately, but it's also how duplicate PDFs
            # masquerading as distinct papers would slip past
            # drift detection).
            collisions = list_hash_collisions(lib)
            summary["hash_collisions"] = collisions
        st.success(
            f"Scanned {summary['scanned']} · "
            f"drifted {len(summary['drifted'])} · "
            f"missing sidecar {len(summary['missing_sidecar'])} · "
            f"errors {len(summary['errors'])}"
        )
        if summary["drifted"]:
            with st.expander(f"{len(summary['drifted'])} drifted PDF(s)",
                             expanded=True):
                for d in summary["drifted"][:50]:
                    st.markdown(
                        f"- `{Path(d['pdf']).relative_to(lib)}` — {d['reason']}"
                    )
                if len(summary["drifted"]) > 50:
                    st.caption(f"... and {len(summary['drifted']) - 50} more")
        if summary["missing_sidecar"]:
            with st.expander(
                f"{len(summary['missing_sidecar'])} PDF(s) without a sidecar",
                expanded=False,
            ):
                for p in summary["missing_sidecar"][:50]:
                    st.markdown(f"- `{Path(p).relative_to(lib)}`")
                if len(summary["missing_sidecar"]) > 50:
                    st.caption(
                        f"... and {len(summary['missing_sidecar']) - 50} more"
                    )
        if summary.get("hash_collisions"):
            n_colls = len(summary["hash_collisions"])
            with st.expander(
                f"{n_colls} content-hash collision(s) "
                f"(template boilerplate or duplicates?)",
                expanded=False,
            ):
                st.caption(
                    "The first 1MB of these PDFs is byte-identical.  "
                    "Often this is just publisher boilerplate (Elsevier, "
                    "Springer ...) on distinct papers; sometimes it's a "
                    "real duplicate.  Compare the files to be sure."
                )
                for h, paths in list(summary["hash_collisions"].items())[:20]:
                    st.markdown(f"**`{h[:12]}…`** — {len(paths)} files")
                    for p in paths[:6]:
                        st.markdown(f"  - `{Path(p).relative_to(lib)}`")
                    if len(paths) > 6:
                        st.caption(f"    ... and {len(paths) - 6} more")
        _log_activity("settings.verify", str(lib),
                      f"drifted={len(summary['drifted'])}")


# ---------------------------------------------------------------------------
# Page: Conflicts (Phase 6 -- Dropbox conflict-copy diff/decide)
# ---------------------------------------------------------------------------

def _conflicts_bulk_apply(conflicts, paths, library_root, action: str):
    """Apply one resolver across many conflicts in a single undo transaction.

    ``action`` is one of ``"keep_canonical" | "keep_conflict" | "keep_both" |
    "suggested"``.  ``suggested`` dispatches per item according to the
    resolver's own heuristic.

    Returns ``(n_ok, n_fail, errors)``.
    """
    from processing.conflict_resolver import (
        resolve_keep_both,
        resolve_keep_canonical,
        resolve_keep_conflict,
    )
    from processing.undo_log import UndoLog
    by_path = {c.conflict: c for c in conflicts}
    log = UndoLog()
    tx_id = log.begin_transaction(
        f"bulk conflict {action} ({len(paths)})"
    )
    n_ok = n_fail = 0
    errors: list[str] = []
    for path in sorted(paths):
        c = by_path.get(path)
        if c is None:
            continue
        chosen = c.suggested if action == "suggested" else action
        conflict_p = Path(c.conflict)
        canonical_p = Path(c.canonical) if c.canonical else None
        try:
            if chosen == "keep_canonical":
                ok, msg = resolve_keep_canonical(
                    conflict_p, library_root, undo_log=log,
                )
            elif chosen == "keep_conflict":
                ok, msg = resolve_keep_conflict(
                    conflict_p, library_root, canonical=canonical_p, undo_log=log,
                )
            elif chosen == "keep_both":
                ok, msg = resolve_keep_both(
                    conflict_p, library_root, undo_log=log,
                )
            else:
                ok, msg = False, f"no suggested action for {conflict_p.name}"
            if ok:
                n_ok += 1
            else:
                n_fail += 1
                errors.append(f"{conflict_p.name}: {msg}")
        except Exception as exc:
            n_fail += 1
            errors.append(f"{conflict_p.name}: {exc}")
    log.commit()
    _log_activity(
        f"conflict.bulk_{action}", "",
        f"ok={n_ok} fail={n_fail}", tx_id,
    )
    return n_ok, n_fail, errors


def render_conflicts() -> None:
    """Side-by-side conflict-copy resolver."""
    from processing.conflict_resolver import (
        resolve_keep_both,
        resolve_keep_canonical,
        resolve_keep_conflict,
        scan_conflicts,
    )
    from processing.undo_log import UndoLog

    st.header("🌪 Conflicts")
    st.caption(
        "Dropbox conflict copies, paired with their canonical for "
        "side-by-side comparison.  Every resolution goes through the "
        "undo log so the Activity tab can reverse it."
    )

    lib = _library()
    conflicts = scan_conflicts(lib)
    if not conflicts:
        st.session_state.pop("conflicts_selected", None)
        st.success("No conflict copies detected. ✓")
        return

    # Multi-select bookkeeping: a session-state set keyed by the
    # conflict's path string.  Selections survive Streamlit reruns
    # but reset when no conflicts remain.
    sel_key = "conflicts_selected"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = set()
    all_paths = {c.conflict for c in conflicts}
    # Prune stale selections (a previously-selected conflict that has
    # since been resolved no longer appears in the new scan).
    st.session_state[sel_key] &= all_paths
    selected: set[str] = st.session_state[sel_key]

    st.caption(f"{len(conflicts)} conflict(s) found  ·  {len(selected)} selected")
    bar = st.columns([1, 1, 2, 2, 2])
    if bar[0].button("Select all", key="conf_sel_all",
                     use_container_width=True):
        st.session_state[sel_key] = set(all_paths)
        st.rerun()
    if bar[1].button("Clear", key="conf_clear",
                     use_container_width=True,
                     disabled=not selected):
        st.session_state[sel_key] = set()
        st.rerun()
    # Bulk actions live in the same bar.  Disabled when no selection.
    if bar[2].button(
        f"Apply suggested to {len(selected)}",
        key="conf_bulk_suggested",
        use_container_width=True,
        disabled=not selected,
    ):
        n_ok, n_fail, errors = _conflicts_bulk_apply(
            conflicts, selected, lib, "suggested",
        )
        st.toast(f"bulk suggested: ok={n_ok} fail={n_fail}")
        if errors:
            st.warning("Errors:\n  - " + "\n  - ".join(errors[:8]))
        st.session_state[sel_key] = set()
        _attention_count_cached.clear()
        st.rerun()
    if bar[3].button(
        f"Keep canonical for {len(selected)}",
        key="conf_bulk_kc",
        use_container_width=True,
        disabled=not selected,
    ):
        n_ok, n_fail, errors = _conflicts_bulk_apply(
            conflicts, selected, lib, "keep_canonical",
        )
        st.toast(f"bulk keep canonical: ok={n_ok} fail={n_fail}")
        if errors:
            st.warning("Errors:\n  - " + "\n  - ".join(errors[:8]))
        st.session_state[sel_key] = set()
        _attention_count_cached.clear()
        st.rerun()
    if bar[4].button(
        f"Keep conflict for {len(selected)}",
        key="conf_bulk_kf",
        use_container_width=True,
        disabled=not selected,
    ):
        n_ok, n_fail, errors = _conflicts_bulk_apply(
            conflicts, selected, lib, "keep_conflict",
        )
        st.toast(f"bulk keep conflict: ok={n_ok} fail={n_fail}")
        if errors:
            st.warning("Errors:\n  - " + "\n  - ".join(errors[:8]))
        st.session_state[sel_key] = set()
        _attention_count_cached.clear()
        st.rerun()

    st.divider()

    for c in conflicts:
        with st.container(border=True):
            conflict_p = Path(c.conflict)
            canonical_p = Path(c.canonical) if c.canonical else None
            # Header row: checkbox + filename.  The checkbox key is
            # tied to the conflict path so toggles persist across
            # Streamlit reruns.
            head = st.columns([0.05, 0.95])
            checked = head[0].checkbox(
                "select", value=c.conflict in selected,
                key=f"conf_sel_{c.conflict}",
                label_visibility="collapsed",
            )
            if checked:
                selected.add(c.conflict)
            else:
                selected.discard(c.conflict)
            head[1].markdown(f"**{conflict_p.name}**")
            cols = st.columns(2)
            with cols[0]:
                st.markdown("**Conflict copy**")
                st.code(str(conflict_p.relative_to(lib)), language=None)
                st.caption(
                    f"size: {c.conflict_size:,} bytes · "
                    f"pages: {c.conflict_pages if c.conflict_pages is not None else '?'} · "
                    f"mtime: {c.conflict_mtime}"
                )
            with cols[1]:
                st.markdown("**Canonical**")
                if canonical_p:
                    st.code(str(canonical_p.relative_to(lib)), language=None)
                    if c.canonical_exists:
                        st.caption(
                            f"size: {c.canonical_size:,} bytes · "
                            f"pages: {c.canonical_pages if c.canonical_pages is not None else '?'} · "
                            f"mtime: {c.canonical_mtime}"
                        )
                    else:
                        st.warning("Canonical does not exist on disk.")
                else:
                    st.warning("Could not derive a canonical filename.")

            # Heuristic hint -- nudges the user without removing
            # agency.
            if c.notes:
                st.info(" ".join(c.notes))
            suggested = c.suggested

            def _do(verb: str, fn, *args, **kwargs):
                undo_log = UndoLog()
                tx_id = undo_log.begin_transaction(f"conflict {verb}: {conflict_p.name}")
                ok, msg = fn(*args, undo_log=undo_log, **kwargs)
                if ok:
                    undo_log.commit()
                    st.toast(msg)
                    _log_activity(f"conflict.{verb}", str(conflict_p.relative_to(lib)),
                                  msg, tx_id)
                    _attention_count_cached.clear()
                else:
                    st.error(msg)
                st.rerun()

            act_cols = st.columns(4)
            kc_label = "Keep canonical" + (" ⭐" if suggested == "keep_canonical" else "")
            kf_label = "Keep conflict" + (" ⭐" if suggested == "keep_conflict" else "")
            if act_cols[0].button(
                kc_label, key=f"kc_{c.conflict}", use_container_width=True
            ):
                _do("keep_canonical", resolve_keep_canonical, conflict_p, lib)
            if act_cols[1].button(
                kf_label, key=f"kf_{c.conflict}", use_container_width=True
            ):
                _do("keep_conflict", resolve_keep_conflict, conflict_p, lib,
                    canonical=canonical_p)
            if act_cols[2].button(
                "Keep both (rename -v2)",
                key=f"kb_{c.conflict}", use_container_width=True
            ):
                _do("keep_both", resolve_keep_both, conflict_p, lib)
            if act_cols[3].button(
                "Open both", key=f"open_{c.conflict}", use_container_width=True
            ):
                import subprocess as _sp
                _sp.run(["open", str(conflict_p)], capture_output=True)
                if canonical_p and canonical_p.exists():
                    _sp.run(["open", str(canonical_p)], capture_output=True)


def main() -> None:
    _init_state()
    render_sidebar()

    page = st.session_state.get("page", "Sort Queue")
    if page == "Attention":
        render_attention()
    elif page == "Sort Queue":
        render_sort_queue()
    elif page == "Upgrade Queue":
        render_upgrade_queue()
    elif page == "To Download":
        render_to_download()
    elif page == "Conflicts":
        render_conflicts()
    elif page == "Maintenance":
        render_maintenance()
    elif page == "Pipeline Preview":
        render_pipeline_preview()
    elif page == "Stats":
        render_stats()
    elif page == "Activity":
        render_activity()
    elif page == "Settings":
        render_settings()


main()
