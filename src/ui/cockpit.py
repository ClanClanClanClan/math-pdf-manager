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
    """
    path = _activity_log_path()
    if not path.exists():
        return []
    entries: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip corrupt lines
    except OSError:
        return []
    # File is append-only chronological; flip to newest-first and bound it.
    return list(reversed(entries))[:100]


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
        with open(_activity_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
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
        page = st.radio(
            "Page",
            ["Sort Queue", "Upgrade Queue", "Maintenance", "Stats", "Activity"],
            label_visibility="collapsed",
        )
        st.session_state.page = page

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
        for pdf in sorted(sub.rglob("*.pdf")):
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
        cols = st.columns(2)
        if cols[0].button("⏭ Skip", key=f"skip_{pdf}"):
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

        # Topic-classifier suggestions (heuristic, no LLM needed).
        # Cached per-(title, first 1500 chars) so we don't re-classify on
        # every Streamlit rerun while the user is staring at the same paper.
        topics = _classify_cached(prev.title, prev.first_page_text[:1500])
        if topics:
            st.markdown("**Topic suggestions**")
            for t in topics[:3]:
                st.markdown(
                    f"&nbsp;&nbsp;`{t['topic_code']}` {t['topic_name']} "
                    f"_(score {t['score']:.1f})_"
                )

        st.markdown("---")
        st.markdown("**Proposed canonical filename**")
        # Allow editing the canonical filename before approval
        edited_name = st.text_input(
            "Canonical filename",
            value=prev.canonical_filename,
            label_visibility="collapsed",
            key=f"name_{pdf}",
        )
        # Destination preview
        destination = _proposed_destination(lib, edited_name, status)
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
        ok, msg = _approve_sort(pdf, edited_name, status, lib)
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


def _proposed_destination(lib: Path, canonical_name: str, status: str) -> Path:
    """Replicate FolderRouter.route() preview without touching disk."""
    from organization.system import FolderRouter

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

    router = FolderRouter(lib)
    return router.route(meta, canonical_name)


def _approve_sort(pdf: Path, canonical_name: str, status: str, lib: Path) -> tuple[bool, str]:
    """Actually file the paper. Returns (ok, message).

    ``canonical_name`` is what the user saw and approved. It's passed
    through to ``ingest_paper`` as a canonical_override so the user's
    edits are honoured (the pipeline no longer re-derives the name from
    metadata and silently overwrites the user's choice).
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
        )
        if result.get("ok"):
            undo_log.commit()
            _log_activity(
                "sort.approve",
                str(pdf.relative_to(lib)),
                result.get("destination", ""),
                tx_id,
            )
            return True, "ok"
        else:
            return False, result.get("error", "unknown")
    except Exception as exc:
        return False, str(exc)


def _count_trash(lib: Path, sub: str) -> int:
    p = lib / ".trash" / sub
    if not p.exists():
        return 0
    return sum(1 for _ in p.rglob("*.pdf"))


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
    return sum(1 for _ in p.rglob("*.pdf"))


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
# Page: Activity
# ---------------------------------------------------------------------------

def render_activity() -> None:
    st.header("🕐 Recent activity")
    st.caption(
        "Every approval in this session is logged here. Each entry has an "
        "undo button that reverses the corresponding transaction."
    )

    if not st.session_state.activity_log:
        st.info("No activity yet this session.")
        return

    for i, entry in enumerate(st.session_state.activity_log):
        with st.expander(f"{entry['time']}  {entry['action']}  {Path(entry['source']).name}"):
            st.markdown(f"**Source**: `{entry['source']}`")
            if entry.get("destination"):
                st.markdown(f"**Destination**: `{entry['destination']}`")
            if entry.get("tx_id"):
                st.markdown(f"**Transaction**: `{entry['tx_id']}`")
                if st.button("↶ Undo", key=f"undo_{i}_{entry['tx_id']}"):
                    _undo_transaction(entry["tx_id"])
                    st.rerun()


def _undo_transaction(tx_id: str) -> None:
    from processing.undo_log import UndoLog
    log = UndoLog()
    try:
        results = log.undo_transaction(tx_id, dry_run=False)
        st.toast(f"Undid {len(results)} ops in {tx_id}", icon="↶")
    except Exception as exc:
        st.error(f"Undo failed: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _init_state()
    render_sidebar()

    page = st.session_state.get("page", "Sort Queue")
    if page == "Sort Queue":
        render_sort_queue()
    elif page == "Upgrade Queue":
        render_upgrade_queue()
    elif page == "Maintenance":
        render_maintenance()
    elif page == "Stats":
        render_stats()
    elif page == "Activity":
        render_activity()


main()
