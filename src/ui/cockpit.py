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
    # "auto", not "expanded": the owner often runs this in a ~343px side
    # panel, where an expanded sidebar covers the ENTIRE width — he could
    # see the navigation or the page, never both.  "auto" keeps it open
    # on a wide window and collapsed (one tap away) on a narrow one.
    initial_sidebar_state="auto",
)

# --- Narrow-pane stylesheet -------------------------------------------------
# The owner drives this from a ~343px side panel.  Streamlit already stacks
# st.columns below a 640px viewport, so the damage at that width is not
# squashed columns -- it is (a) st.code blocks that never wrap (measured:
# a 1,595px destination path inside a 279px box, 82% of it unreachable, and
# both sides of a conflict showing the same visible prefix) and (b) the sheer
# height of default chrome (the 12-item nav measured 1,471px in a 900px-tall
# panel, leaving Stats/Activity/Settings and the watcher switch below the
# fold).  Measured with this block applied: sidebar 1,471px -> 941px,
# every code path fully visible (scrollWidth == clientWidth), metric rows -24%.
st.markdown(
    """
    <style>
    /* Long paths, DOIs and flag bodies wrap instead of scrolling out of view. */
    [data-testid="stCode"] pre, [data-testid="stCode"] code {
        white-space: pre-wrap !important;
        overflow-wrap: anywhere !important;
        word-break: break-word !important;
    }
    /* Fit the whole nav + watcher control inside one panel height. */
    [data-testid="stSidebar"] [data-testid="stButton"] button {
        min-height: 2.1rem; padding-top: 0.1rem; padding-bottom: 0.1rem;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.3rem; }
    [data-testid="stSidebar"] hr { margin: 0.35rem 0 !important; }
    [data-testid="stSidebar"] h1 {
        font-size: 1.35rem !important; padding: 0.25rem 0 !important;
    }
    /* Stacked columns in a narrow pane: smaller counters, tighter gaps. */
    @media (max-width: 640px) {
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important; line-height: 1.25 !important;
        }
        [data-testid="stMetricValue"] div { font-size: 1.5rem !important; }
        [data-testid="stMetricLabel"] p { font-size: 0.8rem !important; }
        [data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

from core.config_paths import get_library_root  # noqa: E402
from organization.system import TO_BE_SORTED  # noqa: E402
from ui.cockpit_actions import apply_env_overrides  # noqa: E402

# Settings the CLI reads from the environment (Unpaywall email, …) are
# saved by the Settings page and pushed into this process here — before
# any downloader module is imported, since those snapshot the variables
# at import time.
apply_env_overrides()
from ui.cockpit_actions import apply_env_overrides  # noqa: E402

# Settings the CLI reads from the environment (Unpaywall email, …) are
# saved by the Settings page and pushed into this process here — before
# any downloader module is imported, since those snapshot the variables
# at import time.
apply_env_overrides()

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

class _PersistentSkips(set):
    """A ``set`` that writes itself to disk whenever it changes.

    Both review queues always show ``candidates[0]`` and remembered
    skips only in ``st.session_state``, so a browser reload put the
    owner back on the very item he had just decided he could not deal
    with.  With ~1,900 papers to sort and ~1,600 upgrades to review,
    one stubborn head-of-queue item blocked the whole backlog forever.
    Sub-classing ``set`` keeps every call site (``.add`` / ``.clear`` /
    ``in`` / ``len``) untouched.
    """

    def __init__(self, path: Path, values=()):
        super().__init__(values)
        self._path = path

    def _flush(self) -> None:
        try:
            from core.io import atomic_write_text
            atomic_write_text(self._path, json.dumps(sorted(self)))
        except Exception as exc:   # bookkeeping must never break a click
            logger.warning("could not persist skip list %s: %s",
                           self._path, exc)

    def add(self, value) -> None:
        super().add(value)
        self._flush()

    def discard(self, value) -> None:
        super().discard(value)
        self._flush()

    def clear(self) -> None:
        super().clear()
        self._flush()


def _load_skips(kind: str) -> _PersistentSkips:
    """Load the persisted skip list for ``kind`` ("sort" | "upgrade")."""
    path = Path.home() / ".mathpdf" / f"{kind}_skipped.json"
    values: list[str] = []
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                values = [str(v) for v in raw]
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("skip list unreadable %s: %s", path, exc)
    return _PersistentSkips(path, values)


def _init_state() -> None:
    if "library_root" not in st.session_state:
        st.session_state.library_root = str(get_library_root())
    if "sort_skipped" not in st.session_state:
        st.session_state.sort_skipped = _load_skips("sort")

    if "upgrade_skipped" not in st.session_state:
        st.session_state.upgrade_skipped = _load_skips("upgrade")
    # The queue reads a STATIC report file: approving a paper does not
    # remove its entry, so without a separate record of what has been
    # handled the same paper stays at the head of the queue forever.
    # Kept apart from the skip list so "put back the ones I skipped"
    # cannot resurrect a paper whose preprint is already in .trash/.
    if "upgrade_done" not in st.session_state:
        st.session_state.upgrade_done = _load_skips("upgrade_done")
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


def _flash(kind: str, msg: str) -> None:
    """Queue a message that survives the ``st.rerun()`` after an action.

    Action handlers draw a result and then rerun unconditionally, which
    throws the freshly-drawn page away: ``st.toast`` survives that,
    ``st.error`` / ``st.warning`` / ``st.info`` do not.  So every
    failure explanation in the cockpit was invisible and a failed click
    looked exactly like a dead button.  Messages parked here are drawn
    at the top of the next render.
    """
    st.session_state.setdefault("flash", []).append((kind, msg))


def _render_flashes() -> None:
    """Draw and clear anything queued by ``_flash``."""
    for kind, msg in st.session_state.pop("flash", []):
        {"error": st.error, "warning": st.warning}.get(kind, st.info)(msg)


def _reversible_note(detail: str = "") -> None:
    """The single reversibility affordance, used under every writing control.

    Every mutation in this app moves files into ``.trash/`` and records a
    transaction in the operation log, so all of them can be put back from
    the Activity page.  Almost no button said so, and the route to Undo
    was a page the owner had no reason to open.  One caption, identical
    wording, under everything that writes.
    """
    st.caption("↩ Reversible — undo it from the **Activity** page"
               + (f".  {detail}" if detail else "."))


def _irreversible_note(detail: str) -> None:
    """Counterpart for the handful of actions that genuinely cannot be undone.

    Honest labelling is the point: a user who trusts "everything is
    reversible" everywhere must be told, in the same visual slot, where
    that stops being true.
    """
    st.caption(f"⚠ This one cannot be undone from Activity.  {detail}")


def _library() -> Path:
    return Path(st.session_state.library_root)


def _page_header(
    icon: str,
    title: str,
    summary: str,
    how_it_works: str = "",
    counts: Optional[list] = None,
) -> None:
    """One page-opening shape for every page.

    Order is always: title -> ONE plain sentence saying what this page is
    -> the mechanism, folded away -> the numbers -> (then the page's own
    actions and detail).  Twelve pages previously opened in six different
    shapes, and three of them opened with configuration widgets before
    the user had seen a single number.

    ``summary`` is rendered as body text, not ``st.caption``: it is the
    one sentence that has to be readable, and caption is Streamlit's
    60%-alpha grey (~3.7:1, below the WCAG AA floor).

    ``counts`` is a list of ``(label, value)`` pairs rendered as metrics,
    so "how much work is here" always looks the same and always sits in
    the same place.
    """
    st.header(f"{icon} {title}" if icon else title)
    st.markdown(f"**{summary}**")
    if how_it_works:
        with st.expander("How this works", expanded=False):
            st.markdown(how_it_works)
    if counts:
        cols = st.columns(len(counts))
        for col, (label, value) in zip(cols, counts):
            col.metric(label, value)
    st.divider()


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
        # doesn't silently break every subsequent operation.  It is set
        # once and never touched again, so it lives in a collapsed
        # expander: shown open it cost ~250px of a 343px-wide sidebar,
        # pushing the navigation below the fold.
        lib = _library()
        ok_root = lib.exists()
        with st.expander(
            "📁 Library" if ok_root else "⚠ Library not found", expanded=not ok_root
        ):
            new_root = st.text_input(
                "Folder", value=st.session_state.library_root,
                help="Absolute path or ~ for home. Defaults to $MATH_LIBRARY.",
            )
            if new_root != st.session_state.library_root:
                ok, msg = _validate_library_root(new_root)
                if ok:
                    st.session_state.library_root = msg  # resolved path
                else:
                    st.error(f"That folder can't be used: {msg}")
                    # Don't update session_state — keep the previous valid one.
            lib = _library()
            if lib.exists():
                st.caption(f"Using {lib}")
            else:
                st.error(f"Not found: {lib}")

        st.divider()
        # The badge reads the LAST computed count from session state and
        # never scans (see _attention_badge): the sidebar renders on
        # every page, so scanning here made Search/Stats/Settings block
        # on a 45-113s library walk they never needed.
        attention_label = _attention_badge()

        # Grouped by the owner's JOBS, not by subsystem.  The flat
        # 12-item radio made him the router: he had to know which
        # module owned his problem before he could start.
        _GROUPS = [
            ("Do", [attention_label, "Sort Queue", "Upgrade Queue", "To Download"]),
            ("Fix", ["Conflicts", "Duplicates", "Spelling", "Maintenance"]),
            ("Look", ["Search", "Pipeline Preview", "Conformance", "Stats",
                      "Activity"]),
            ("Setup", ["Settings"]),
        ]
        current = st.session_state.get("page", "Attention")
        for group_name, pages in _GROUPS:
            st.caption(group_name)
            for label in pages:
                canonical = "Attention" if label.startswith("Home") else label
                if st.button(
                    label,
                    key=f"nav_{canonical}",
                    use_container_width=True,
                    type="primary" if canonical == current else "secondary",
                ):
                    st.session_state.page = canonical
                    st.rerun()
        st.session_state.setdefault("page", "Attention")

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
                    f"Automatic filing: ON  "
                    f"(running as process {wstatus.get('pid') or '?'})"
                )
                if st.button("Turn off automatic filing",
                             use_container_width=True,
                             key="sidebar_stop_watcher"):
                    ok, msg = stop_watcher()
                    st.toast(msg)
                    # Invalidate the cache so the badge flips
                    # immediately rather than after the 10s TTL.
                    _watcher_status_cached.clear()
                    st.rerun()
            else:
                st.warning("Automatic filing: OFF — new PDFs dropped in your "
                           "inbox folder will just sit there")
                if st.button("Turn on automatic filing",
                             use_container_width=True,
                             key="sidebar_start_watcher"):
                    ok, msg = start_watcher()
                    st.toast(msg)
                    if not ok:
                        # A toast is gone in seconds.  When automatic
                        # filing refuses to start, the REASON is the only
                        # useful thing on screen — keep it until the next
                        # attempt rather than making him retry to re-read it.
                        st.session_state["watcher_start_error"] = msg
                    else:
                        st.session_state.pop("watcher_start_error", None)
                    _watcher_status_cached.clear()
                    st.rerun()
                if st.session_state.get("watcher_start_error"):
                    # start_watcher installs the background service itself
                    # when it is missing (he cannot run install.sh), so an
                    # error here is a real failure worth keeping on screen
                    # rather than a missing-setup step he could fix.
                    st.error(st.session_state["watcher_start_error"])
        except Exception as exc:  # pragma: no cover -- never break the sidebar
            st.caption(f"Watcher status unavailable: {exc}")

        st.divider()
        st.caption(
            "Nothing in this app deletes a file. Anything you approve can "
            "be put back."
        )
        # The standing promise was static text naming a folder he never
        # sees (`.trash/`) and never naming the page where undo lives.
        # This is navigation only — it changes nothing.
        if st.button("↩ Undo a recent change", key="nav_undo_shortcut",
                     use_container_width=True):
            st.session_state.page = "Activity"
            st.rerun()


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


class _Null:
    """No-op stand-in for a Streamlit column that should not render.

    Lets a block of widget code stay in one piece while being hidden in
    a context where it would only be noise (see the Home snooze bar).
    """

    def button(self, *a, **k) -> bool:      # noqa: D102 - trivial
        return False


def _fmt_eta(seconds: float) -> str:
    """'4m 20s' / '38s' — a wait the owner can decide about."""
    s = int(max(0, seconds))
    return f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


def _progress_ui(verb: str, *, show_eta: bool = True):
    """A throttled progress bar for one long, synchronous operation.

    Returns ``(tick, done)``.  ``tick(i, n, label)`` updates a real bar
    with a count and an ETA; ``n == 0`` means the total isn't known, so
    it shows a live counter instead of a percentage.  ``done(msg)``
    removes the bar and optionally leaves a one-line result.

    Every expensive operation in this cockpit is synchronous — Streamlit
    runs the whole page script on one thread — so an ``st.spinner`` told
    the owner nothing at all for runs MEASURED at 85s (normalize scan),
    ~6 min (bulk sort of the 1,933-paper inbox) and ~10 min (whole-
    library pipeline preview).  Updates are throttled to ~4/second
    because each one is a browser round-trip and the callback fires
    tens of thousands of times.
    """
    slot = st.empty()
    state: dict = {"bar": None, "t0": time.time(), "last": 0.0}

    def tick(i: int, n: int = 0, label: str = "") -> None:
        now = time.time()
        final = bool(n) and i >= n
        if now - state["last"] < 0.25 and not final:
            return
        state["last"] = now
        if state["bar"] is None:
            state["bar"] = slot.progress(0.0)
        if n:
            text = f"{verb} {i:,} of {n:,}"
            if show_eta and i:
                eta = (now - state["t0"]) / i * (n - i)
                text += f" — about {_fmt_eta(eta)} left"
            frac = min(1.0, i / n)
        else:
            text = f"{verb} {i:,}…  ({_fmt_eta(now - state['t0'])} elapsed)"
            frac = 0.0
        if label:
            text += f"  ·  {label[:60]}"
        state["bar"].progress(frac, text=text)

    def done(msg: str = "") -> None:
        slot.empty()
        if msg:
            st.caption(msg)

    return tick, done


def _render_batch_sort(lib: Path, pending: int) -> None:
    """File many papers in one reversible batch.

    ``processing.bulk_sort`` has always existed, is covered by tests and
    records ONE undo transaction for the whole run — but nothing in the
    UI ever called it, so the only way to clear the inbox was the
    one-paper-at-a-time reviewer below.  At ~1,900 papers that is hours
    of clicking, which is why the backlog never shrank.

    Dry-run first, always: the owner sees exactly what would move, and
    only then can he apply.  The batch is bounded so a first run is a
    small, easily-inspected commitment.
    """
    from processing.bulk_sort import bulk_sort

    with st.expander(f"⚡ Sort many at once  ({pending} waiting)", expanded=False):
        st.caption(
            "Files every paper it is confident about, using exactly the "
            "same rules as the one-by-one review below. The original files "
            "go to the trash rather than being deleted, and the whole batch "
            "is a single Undo on the **Activity** page. Anything it is "
            "unsure about is left here for you."
        )
        c1, c2 = st.columns([0.4, 0.6])
        size = c1.selectbox("How many", ["25", "100", "500", "All"], index=0,
                            key="bulk_sort_size")
        limit = None if size == "All" else int(size)

        if c2.button("👁 Preview (changes nothing)", use_container_width=True,
                     key="bulk_sort_preview"):
            # MEASURED >=0.20s/paper (metadata extraction alone), so
            # "All" over the 1,933-paper inbox is a >6-minute dry run.
            tick, done = _progress_ui("Reading paper")
            st.session_state["bulk_sort_preview_res"] = bulk_sort(
                lib, limit=limit, dry_run=True, progress=tick,
                exclude=set(st.session_state.sort_skipped))
            _save_scan("bulk_sort_preview",
                       st.session_state["bulk_sort_preview_res"])
            done("Preview ready — nothing has been moved.")

        res = st.session_state.get("bulk_sort_preview_res")
        if res is None:
            # MEASURED >=0.20s/paper: previewing the whole 1,933-paper
            # inbox is a >6-minute run, and Apply only appears while the
            # preview is held.  A reload in between charged him twice.
            res, _age_h = _load_scan("bulk_sort_preview")
            if res:
                st.session_state["bulk_sort_preview_res"] = res
                st.caption(
                    f"Showing the preview you ran {_age_h:.1f} h ago. "
                    "Re-preview if papers have arrived since."
                )
        if not res:
            return

        ok = [r for r in res["results"] if r.get("ok")]
        bad = [r for r in res["results"] if not r.get("ok")]
        m1, m2 = st.columns(2)
        m1.metric("Would be filed", len(ok))
        m2.metric("Left for you", len(bad))

        def _name(r: dict) -> str:
            return Path(str(r.get("source", "?"))).name[:52]

        if ok:
            # Show the NEW canonical name, not just the destination path —
            # that is the part worth checking before agreeing to a batch.
            # st.dataframe does not stack -- it scrolls inside itself.  Three
            # columns of long filenames inside the measured 311px content
            # width leaves ~100px each, about a dozen readable characters.
            # The new name and its folder are what he must check before
            # agreeing to a batch; the source names are listed above.
            st.caption("What each paper would be renamed to, and where it goes:")
            st.dataframe(
                [{"New name": str(r.get("filename", "?"))[:64],
                  "Folder": str(r.get("subfolder", "?"))[:26]} for r in ok[:200]],
                use_container_width=True, hide_index=True,
            )
            if len(ok) > 200:
                st.caption(f"…and {len(ok) - 200} more, not shown.")
        if bad:
            with st.expander(f"{len(bad)} it won't guess at — left for you"):
                def _why(r: dict) -> str:
                    # The per-file `actions` trail carries the REAL reason
                    # ("destination already exists with different content");
                    # `error` is often just "ingest failed".
                    for a in r.get("actions") or []:
                        if str(a).startswith("ERROR"):
                            return str(a)[6:].lstrip(": ")[:90]
                    return str(r.get("error", "?"))[:90]
                st.dataframe(
                    [{"paper": _name(r), "why": _why(r)} for r in bad[:200]],
                    use_container_width=True, hide_index=True,
                )

        if not ok:
            st.info("Nothing here can be filed automatically.")
            return
        st.warning(
            f"**File {len(ok)} papers now?** They move out of the inbox. "
            "Reversible in one click from Activity."
        )
        if st.checkbox("Yes, I've read the list above", key="bulk_sort_confirm"):
            if st.button(f"✅ File these {len(ok)} papers", type="primary",
                         use_container_width=True, key="bulk_sort_apply"):
                # The apply pass repeats the same per-paper work as the
                # preview (>=0.20s each) AND moves files.  Watching the
                # count climb is the difference between "it's working"
                # and "I should force-reload and hope".
                tick, done = _progress_ui("Filing paper")
                out = bulk_sort(lib, limit=limit, dry_run=False,
                                progress=tick,
                                exclude=set(st.session_state.sort_skipped))
                done()
                _log_activity("sort.bulk", f"{out['filed']} papers",
                              f"{out['failed']} left",
                              out.get("transaction_id") or "")
                st.session_state.pop("bulk_sort_preview_res", None)
                _save_scan("bulk_sort_preview", None)
                st.success(
                    f"Filed {out['filed']} papers "
                    f"({out['failed']} left for you). Undo in Activity."
                )
                _attention_count_cached.clear()
                st.rerun()


@st.cache_data(ttl=3600, show_spinner=False)
def _preview_pdf_cached(pdf_str: str, mtime: float, size: int):
    """Cached ``preview_pdf``, keyed on the file's identity.

    ``preview_pdf`` re-parses the PDF and re-runs the metadata pipeline;
    measured at 0.25–1.22 s per call on real inbox files.  It ran on
    EVERY Streamlit rerun, so changing the topic dropdown, editing the
    proposed filename or pressing Skip each paid another full extraction
    of the SAME paper.  ``mtime``/``size`` are part of the cache key, so
    a file that actually changes is re-extracted.
    """
    from ui.paper_preview import preview_pdf
    return preview_pdf(Path(pdf_str))


def render_sort_queue() -> None:
    st.header("📥 Sort Queue")
    st.caption(
        "Papers that have arrived but are not filed yet. For each one you "
        "see the title and authors read out of the PDF, the filename it "
        "would be given, and the folder it would go to — all editable. "
        "Approve files it; Skip leaves it here for later."
    )

    lib = _library()
    # ``_iter_sort_candidates`` returns [] both when the queue is clear and
    # when the staging folder cannot be found at all, and the empty state
    # below celebrates.  A wrong library folder, or Dropbox mid-sync, made
    # this page announce that the inbox was clear when it was not.
    if not (lib / TO_BE_SORTED).is_dir():
        st.error(f"Cannot find `{TO_BE_SORTED}` inside `{lib}`.")
        st.caption(
            "That is the folder new papers arrive in.  Either the library "
            "folder in the sidebar points somewhere else, or Dropbox has "
            "not synced it yet.  An empty queue here would not mean your "
            "inbox is clear, so nothing is shown."
        )
        return
    candidates = _iter_sort_candidates(lib)

    # One line, not four st.metric blocks: below a 640px viewport the columns
    # stack and this header measured 4 x 76px = ~350px of giant zeros above
    # the paper he actually came here to look at.
    _filed_now = sum(1 for a in st.session_state.activity_log
                     if a["action"] == "sort.approve")
    st.caption(
        f"**{len(candidates)}** waiting  ·  "
        f"{len(st.session_state.sort_skipped)} skipped this session  ·  "
        f"{_filed_now} filed this session  ·  "
        f"{_count_trash(lib, 'sorted_originals')} recoverable in the trash"
    )

    # Skips are remembered across sessions now, so the way back must be
    # reachable at any time -- the existing "re-include" button lives in
    # the empty-queue branch below, which he can only reach once there is
    # nothing left to un-skip.
    if st.session_state.sort_skipped and st.button(
        f"↻ Put back the {len(st.session_state.sort_skipped)} paper(s) "
        f"I skipped",
        key="sort_unskip_all",
    ):
        st.session_state.sort_skipped.clear()
        st.rerun()

    if not candidates:
        st.success("🎉 Sort queue is empty — nothing left in `12 - To be sorted/`.")
        if st.session_state.sort_skipped:
            if st.button("↻ Re-include skipped papers"):
                st.session_state.sort_skipped.clear()
                st.rerun()
        return

    _render_batch_sort(lib, len(candidates))

    # Take the first candidate the user hasn't skipped
    pdf, status = candidates[0]

    try:
        _st = pdf.stat()
        prev = _preview_pdf_cached(str(pdf), _st.st_mtime, _st.st_size)
    except OSError:
        from ui.paper_preview import preview_pdf
        prev = preview_pdf(pdf)

    st.subheader(f"{len(candidates)} left to sort — reviewing the next one")
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
        st.markdown("**Kind of paper** _(taken from the folder it arrived in)_")
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
        # A bare code ("07b") tells the reader nothing.  Read the real
        # folder names off disk so the dropdown says "07b — Contract
        # theory"; fall back to the code if a folder is missing, and keep
        # the codes themselves as the option VALUES so the routing and
        # the saved decision are unchanged.
        _CODES = ("07a", "07b", "07c", "07d", "07e", "07f")
        _disk = {d.name[:3]: d.name.replace(" - ", " — ", 1)
                 for d in lib.glob("07? - *") if d.is_dir()}
        _TOPIC_NAMES = {c: _disk.get(c, c) for c in _CODES}
        _topic_codes = list(_CODES)
        _opts = ["(standard — no topic)"] + _topic_codes

        def _topic_label(code: str) -> str:
            return _TOPIC_NAMES.get(code, code)

        if _decision.auto:
            _default = _decision.topic_code
            _hint = (f"auto → **{_topic_label(_decision.topic_code)}** "
                     f"({_decision.confidence:.0%})")
        elif _decision.needs_review:
            _default = _decision.suggested_code
            _hint = (f"suggested **{_topic_label(_decision.suggested_code)}** "
                     f"({_decision.confidence:.0%}) — confirm or change")
        else:
            _default = None
            _hint = "no topic match → files into the standard folders"
        st.markdown("**Topic destination**")
        st.caption(_hint)
        _sel = st.selectbox(
            "Topic destination",
            _opts,
            index=(_opts.index(_default) if _default in _opts else 0),
            format_func=_topic_label,
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
            # 400px of raw first-page text is a full screen of a 343px panel;
            # 240 still shows the title block, which is what it is for.
            height=240, label_visibility="collapsed", key=f"snip_{pdf}",
        )

    # Action row
    st.markdown("---")
    # Approve is taken ~90% of the time on the highest-volume page in the
    # app; it was the same width as Skip/Flag/Open with half the row left
    # empty.
    _reversible_note("Approve moves this PDF into the folder shown above and "
                     "puts the original in the trash — nothing is deleted.")
    cols = st.columns([2, 1, 1, 1, 3])

    if cols[0].button("✅ Approve", key=f"approve_{pdf}", type="primary"):
        # MOVE model: file into the chosen topic folder (or standard).
        ok, msg = _approve_sort(pdf, edited_name, status, lib,
                                topic=chosen_topic, preview=prev)
        if ok:
            st.toast(f"Filed → {destination.relative_to(lib)}  ·  "
                     f"undo from Activity")
        else:
            st.toast(f"Failed: {msg}", icon="⚠️")
        st.rerun()

    if cols[1].button("⏭ Skip", key=f"skip2_{pdf}"):
        st.session_state.sort_skipped.add(str(pdf))
        st.rerun()

    if cols[2].button("🚩 Set aside — I'll handle this one myself",
                      key=f"flag_{pdf}"):
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
            # Commit whatever DID happen before reporting the failure.
            # Returning here left the transaction uncommitted, so any file
            # already copied into the library had no undo record at all —
            # measured at roughly 8% of approvals.  discard() now refuses
            # to drop recorded work, but the explicit commit keeps the
            # failure path honest rather than relying on that.
            if undo_log.has_operations():
                undo_log.commit()
            else:
                undo_log.discard()
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

def _find_publication_reports() -> list[Path]:
    """Newest-first list of publication-check reports on this machine.

    The Upgrade Queue used to open with a text box asking for the
    filesystem path of a JSON file produced by a terminal command the
    owner cannot run — so 1,672 real decisions sat behind a gate he had
    no way through.  Every report this app can produce lands in one of
    two known places; find them instead of asking.
    """
    cands: list[Path] = []
    repo_report = Path(__file__).resolve().parents[2] / "publication_report.json"
    if repo_report.exists():
        cands.append(repo_report)
    reports_dir = Path.home() / ".mathpdf" / "reports"
    if reports_dir.is_dir():
        cands += [p for p in reports_dir.glob("*.json") if p.is_file()]
    seen: set[str] = set()
    out: list[Path] = []
    for p in sorted(cands, key=lambda q: q.stat().st_mtime, reverse=True):
        if str(p) in seen:
            continue
        seen.add(str(p))
        out.append(p)
    return out


def _report_candidates(report: dict) -> list[dict]:
    """Matched entries from EITHER report shape.

    ``processing.publication_checker`` writes ``{"published": [...]}``;
    ``maintenance.weekly_report`` writes the same entries nested under
    ``{"publications": {"unpublished": [...], "working": [...]}}``.  The
    queue only understood the first, so the report the cockpit's own
    "Run weekly now" button produces was unusable here.
    """
    if isinstance(report.get("published"), list):
        return [e for e in report["published"] if isinstance(e, dict)]
    pubs = report.get("publications") or {}
    out: list[dict] = []
    if isinstance(pubs, dict):
        for bucket in ("unpublished", "working"):
            out += [e for e in (pubs.get(bucket) or []) if isinstance(e, dict)]
    return out


def render_upgrade_queue() -> None:
    st.header("⬆ Upgrade Queue")
    st.caption(
        "Preprints in Unpublished papers and Working papers for which a "
        "published version has been found. Approving downloads the "
        "published PDF, files it, and moves the preprint to the trash — "
        "reversible from the Activity page."
    )

    lib = _library()
    found = _find_publication_reports()
    if not found:
        st.warning(
            "No publication check has been run yet, so there is nothing to "
            "review here. Run one from **Maintenance → Full weekly run**; "
            "when it finishes, its results appear on this page."
        )
        if st.button("Go to Maintenance", key="upg_goto_maintenance",
                     type="primary"):
            st.session_state.page = "Maintenance"
            st.rerun()
        return

    remembered = st.session_state.upgrade_report_path
    labels = {
        str(p): (f"{p.name} — checked "
                 f"{datetime.fromtimestamp(p.stat().st_mtime):%Y-%m-%d %H:%M}")
        for p in found
    }
    options = [str(p) for p in found]
    default_i = options.index(remembered) if remembered in options else 0
    report_path = st.selectbox(
        "Which publication check?", options, index=default_i,
        format_func=lambda s: labels.get(s, s),
        help="Newest first. These are the checks this app has run for you.",
    )
    st.session_state.upgrade_report_path = report_path

    rp = Path(report_path)
    try:
        report = json.loads(rp.read_text())
    except Exception as exc:
        st.error(f"That results file could not be read: {exc}")
        st.caption(
            "It was probably still being written when the run was "
            "interrupted.  Pick an older check from the list above, or run "
            "a fresh one from **Maintenance → Full weekly run**."
        )
        return

    published = _report_candidates(report)
    # Coerce: a widget can hand back None (no value yet, or a stubbed
    # runtime), and comparing a float against None raises rather than
    # simply showing an unfiltered list.
    min_conf = st.slider(
        "Only show matches at least this certain", 0.5, 1.0, 0.85, 0.01,
        help="1.00 means the publication lookup is certain it is the same paper.",
    )
    try:
        min_conf = float(min_conf)
    except (TypeError, ValueError):
        min_conf = 0.85

    _done = st.session_state.upgrade_done
    candidates = [
        p for p in published
        if p.get("match", {}).get("confidence", 0) >= min_conf
        and str(p.get("file", "")) not in st.session_state.upgrade_skipped
        and str(p.get("file", "")) not in _done
    ]

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Left to review", len(candidates))
    col_b.metric("Already handled", len(_done))
    col_c.metric("Skipped (remembered)", len(st.session_state.upgrade_skipped))
    col_d.metric("Upgraded this session", sum(1 for a in st.session_state.activity_log if a["action"] == "upgrade.approve"))

    if st.session_state.upgrade_skipped and st.button(
        f"↻ Put back the {len(st.session_state.upgrade_skipped)} paper(s) "
        f"I skipped",
        key="upgrade_unskip_all",
    ):
        st.session_state.upgrade_skipped.clear()
        st.rerun()

    if _done and st.button(
        f"↻ List the {len(_done)} paper(s) already handled again",
        key="upgrade_relist_done",
        help="Only puts them back in this list. It does not undo anything "
             "— undoing an upgrade lives on the Activity page.",
    ):
        _done.clear()
        st.rerun()

    if not candidates:
        if not published:
            st.info(
                "This check did not find a published version for any of "
                "your preprints, so there is nothing to upgrade."
            )
            st.caption(
                "Run a fresh check from **Maintenance → Full weekly run** "
                "when you want to look again."
            )
        else:
            st.success(
                f"None of the {len(published)} match(es) in this check "
                f"reach {min_conf:.0%} certainty."
            )
            st.caption(
                "Drag the slider above further to the left to see the less "
                "certain ones."
            )
        if st.session_state.upgrade_skipped:
            if st.button("↻ Bring back the "
                         f"{len(st.session_state.upgrade_skipped)} you set aside",
                         key="upg_unskip_all"):
                st.session_state.upgrade_skipped.clear()
                st.rerun()
        return

    _render_batch_upgrade(lib, rp, candidates, min_conf, len(candidates))

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
    _reversible_note("Upgrading downloads the published PDF, files it, and "
                     "moves this preprint to the trash — not deleted.")
    cols = st.columns([1, 1, 1, 1, 4])

    if cols[0].button("✅ Download + Upgrade", key=f"upg_approve_{entry['file']}", type="primary"):
        ok, msg = _approve_upgrade(entry, lib)
        if ok:
            # The report file is a snapshot and still lists this paper.
            # Without this line the rerun below puts the paper we just
            # upgraded straight back at the head of the queue — with its
            # preprint now in .trash/, so it reads "Preprint missing" —
            # and the queue never reaches candidate 2.
            st.session_state.upgrade_done.add(str(entry.get("file", "")))
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


def _render_batch_upgrade(lib: Path, report_path: Path, candidates: list,
                          min_conf: float, pending: int) -> None:
    """Upgrade many preprints in one reversible batch.

    ``processing.upgrade_to_published.process_report`` has always
    existed, is covered by tests, records ONE undo transaction for the
    whole run and already supports a dry run — but nothing in the UI
    ever called it.  The only way through 1,672 candidates was the
    one-at-a-time reviewer below, where every single approval also waits
    on a network download.  That is not a queue anyone can finish.

    Dry-run first, always, and bounded: the batch really does download
    from publishers, so a small first run is a small commitment.
    """
    import tempfile
    from processing.upgrade_to_published import process_report

    # ALWAYS run from a scratch copy built out of the LIVE candidate list,
    # never from the report file.  ``process_report`` re-reads the file and
    # takes the top N by confidence every time it is called, so batching
    # off the original repeats the same papers on every run: batch 2
    # re-downloads everything batch 1 already did (~30s of publisher
    # traffic each) and counts it as progress.  The candidate list has
    # skipped and already-handled papers filtered out, so every batch is
    # fresh work — and it is layout-agnostic, which is what the old
    # weekly-report special case was for.
    run_path = Path(tempfile.gettempdir()) / "mathpdf_upgrade_batch.json"
    try:
        run_path.write_text(json.dumps({"published": candidates}),
                            encoding="utf-8")
    except OSError as exc:
        st.caption(f"Batch unavailable for this results file: {exc}")
        return

    with st.expander(f"⚡ Do several at once  ({pending} waiting)",
                     expanded=False):
        st.caption(
            "Downloads the published version, files it, and moves the "
            "preprint to `.trash/upgraded_preprints/` — the same steps as "
            "the reviewer below, for several papers in a row.  Anything "
            "that can't be downloaded is queued in **To Download** instead. "
            "The whole batch is a single undo in **Activity**."
        )
        c1, c2 = st.columns([0.4, 0.6])
        size = c1.selectbox("How many", ["5", "10", "25", "50"], index=1,
                            key="bulk_upg_size")
        n = int(size)
        queue_only = c2.checkbox(
            "Don't download — just add them to **To Download**",
            value=False, key="bulk_upg_manual",
            help="Much faster (no publisher requests). Use this to build a "
                 "fetch list you work through yourself.",
        )
        st.caption(
            "Downloading takes roughly half a minute per paper, so a batch "
            "of 25 can take ~15 minutes. Leave the tab open while it runs."
        )

        if c1.button("👁 Preview (changes nothing)", use_container_width=True,
                     key="bulk_upg_preview"):
            with st.spinner("Checking which papers would be upgraded…"):
                st.session_state["bulk_upg_preview_res"] = process_report(
                    run_path, library_root=lib, min_confidence=min_conf,
                    dry_run=True, max_papers=n,
                )

        res = st.session_state.get("bulk_upg_preview_res")
        if not res:
            return
        rows = res.get("results", [])
        st.dataframe(
            [{"paper": str(r.get("filename")
                           or Path(str(r.get("file", "?"))).name)[:60],
              "DOI": str(r.get("doi", ""))[:40]} for r in rows[:200]],
            use_container_width=True, hide_index=True,
        )
        st.warning(
            f"**Upgrade these {len(rows)} papers now?** Each preprint moves "
            "to `.trash/upgraded_preprints/`. Reversible in one click from "
            "Activity."
        )
        if st.checkbox("Yes, I've read the list above", key="bulk_upg_confirm"):
            if st.button(f"✅ Upgrade these {len(rows)} papers",
                         type="primary", use_container_width=True,
                         key="bulk_upg_apply"):
                with st.spinner(f"Working through {len(rows)} papers…"):
                    out = process_report(
                        run_path, library_root=lib,
                        min_confidence=min_conf, dry_run=False,
                        manual_only=queue_only, max_papers=n,
                    )
                _log_activity(
                    "upgrade.bulk",
                    f"{out['downloaded']} upgraded",
                    f"{out['flagged']} queued for manual, "
                    f"{out['skipped']} skipped",
                )
                # Every paper the batch reached is resolved one way or the
                # other — upgraded, queued in To Download, or skipped for
                # want of a DOI.  Record them all, or the next batch takes
                # the same top-N off the report and does it again.
                for _r in out.get("results", []):
                    _f = str(_r.get("file", ""))
                    if _f:
                        st.session_state.upgrade_done.add(_f)
                st.session_state.pop("bulk_upg_preview_res", None)
                st.success(
                    f"Upgraded {out['downloaded']} · queued "
                    f"{out['flagged']} in To Download · skipped "
                    f"{out['skipped']}. Undo in Activity."
                )
                _attention_count_cached.clear()
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
            # Transaction hygiene (same rule as the watcher and the
            # variant retirer): a failed upgrade may already have
            # RECORDED operations.  Those must be persisted to stay
            # reversible from Activity; an empty tx is discarded.
            if undo_log.has_operations():
                undo_log.commit()
            else:
                undo_log.discard()
            return False, r.get("action", "unknown failure")
        except Exception as exc:
            try:
                if undo_log.has_operations():
                    undo_log.commit()
                else:
                    undo_log.discard()
            except Exception:  # pragma: no cover -- never mask the error
                pass
            return False, str(exc)


# ---------------------------------------------------------------------------
# Page: Maintenance
# ---------------------------------------------------------------------------

def _render_title_review(lib: Path, data: dict) -> None:
    """Review a thousand title renames as a handful of decisions.

    The bucket checkbox below is all-or-nothing: tick "Title casing" and
    every one of ~1,000 proposals goes.  That is not a review.  Here the
    same proposals are split by WHAT they change, so the mechanical ones
    are one approval each and only the genuine judgement calls — about a
    hundred files, grouped by the word being re-cased — are put in front
    of him.
    """
    from processing.library_normalize import apply_renames
    from processing.title_review import (
        COSMETIC, FIRSTWORD, CASE, REWRITE, split_titles, word_decisions,
        proposals_for_words,
    )

    titles = [p for p in data["proposals"] if p["kind"] in ("title", "both")]
    if not titles:
        return
    groups = split_titles(titles)

    st.markdown("---")
    st.markdown("### Title changes, grouped by what they actually change")
    st.caption(
        f"{len(titles)} proposed title changes. Most are mechanical; the "
        "review below is only the part that needs your judgement."
    )

    def _apply(rows: list, label: str, key: str) -> None:
        """Shared reversible apply for one group."""
        if st.button(f"✅ Apply these {len(rows)}", key=f"tr_apply_{key}",
                     type="primary", use_container_width=True):
            with st.spinner(f"Renaming {len(rows)} file(s)…"):
                res = apply_renames(lib, rows, dry_run=False)
            st.success(
                f"Renamed {res['renamed']}"
                + (f" · left alone {len(res['skipped'])}" if res["skipped"] else "")
                + ". Undo the whole batch from Activity."
            )
            if res.get("tx_id"):
                _log_activity(f"normalize.{key}", str(lib),
                              f"{res['renamed']} renamed", res["tx_id"])
            done = {p["old"] for p in rows}
            data["proposals"] = [p for p in data["proposals"]
                                 if p["old"] not in done]
            _save_scan("normalize", data)
            st.rerun()

    # ---- the two mechanical groups: one approval each -------------------
    safe = [
        (FIRSTWORD, "Capitalise the first word of the title",
         "Sentence case starts with a capital. Nothing else in the name changes."),
        (COSMETIC, "Spacing, punctuation and accents only",
         "No word changes — things like “(0,π)” → “(0, π)” or a stray leading space."),
    ]
    for kind, title, why in safe:
        rows = groups[kind]
        if not rows:
            continue
        with st.container(border=True):
            st.markdown(f"**{title}** &nbsp; `{len(rows)}`")
            st.caption(why)
            with st.expander("See examples", expanded=False):
                for p in rows[:25]:
                    st.markdown(f"`{p['old_name'][:90]}`\n\n→ **{p['name'][:90]}**")
                if len(rows) > 25:
                    st.caption(f"…and {len(rows) - 25} more of the same shape.")
            _apply(rows, title, kind)
            st.caption("↩ Reversible — undo from Activity.")

    # ---- the real review: one ruling per WORD ---------------------------
    case_rows = groups[CASE]
    if case_rows:
        decisions = word_decisions(case_rows)
        approved = set(
            tuple(x) for x in st.session_state.setdefault("tr_approved", [])
        )
        with st.container(border=True):
            st.markdown(
                f"**Words to rule on** &nbsp; `{len(decisions)}` "
                f"(covering {len(case_rows)} files)"
            )
            st.caption(
                "Each row is one decision about one word. Approving it "
                "settles every file containing that word; a file is only "
                "renamed once you have approved ALL of its changes."
            )
            shown = st.session_state.setdefault("tr_shown", 20)
            ordered = sorted(decisions.items(), key=lambda kv: -kv[1]["count"])
            for (old_w, new_w), info in ordered[:shown]:
                cols = st.columns([0.55, 0.45])
                with cols[0]:
                    st.markdown(f"`{old_w}` → **{new_w}**  ·  {info['count']} file(s)")
                    st.caption(info["examples"][0][:88] if info["examples"] else "")
                with cols[1]:
                    on = (old_w, new_w) in approved
                    if st.checkbox("Accept this change", value=on,
                                   key=f"tr_w_{old_w}_{new_w}"):
                        approved.add((old_w, new_w))
                    else:
                        approved.discard((old_w, new_w))
            st.session_state["tr_approved"] = [list(t) for t in approved]
            if len(ordered) > shown:
                if st.button(f"Show 20 more ({len(ordered) - shown} left)",
                             key="tr_more", use_container_width=True):
                    st.session_state["tr_shown"] = shown + 20
                    st.rerun()

            ready = proposals_for_words(case_rows, approved)
            st.markdown(
                f"**{len(ready)}** file(s) have every one of their changes approved."
            )
            if ready:
                _apply(ready, "approved word changes", "case")
                st.caption("↩ Reversible — undo from Activity.")

    # ---- anything that genuinely rewrites text --------------------------
    if groups[REWRITE]:
        with st.expander(
            f"⚠ {len(groups[REWRITE])} change the text itself — look before applying",
            expanded=False,
        ):
            for p in groups[REWRITE][:25]:
                st.markdown(f"`{p['old_name'][:90]}`\n\n→ **{p['name'][:90]}**")
            st.caption("These are not simple re-casings; check them by eye.")


def _render_normalize_section(lib: Path) -> None:
    """Bring EXISTING filenames up to the canonical standard.

    Naming is fixed automatically at ingest and on every move; this brings
    the back-catalogue to the same standard as a dry-run-first, reversible,
    gated batch.  The mechanical author-initial spacing ("R.C."→"R. C.")
    is separated from safe-default title casing so the trusted bucket can
    be applied without reading every row.
    """
    from processing.library_normalize import AUTHOR, TITLE, BOTH, apply_renames

    _KIND_LABEL = {AUTHOR: "author spacing", TITLE: "title casing",
                   BOTH: "author + title"}

    with st.expander("✏️ Normalize existing filenames (reversible)",
                     expanded=False):
        st.caption(
            "Applies the SAME canonical rules used at ingest/move to files "
            "already in the library: author-initial spacing (`R.C.`→`R. C.`) "
            "and safe-default title casing (only words the corpus proves are "
            "ordinary get lowercased — proper nouns are preserved and "
            "uncertain ones queued for review).  Scan first; every rename is "
            "reversible via the operation log."
        )
        if st.button("🔍 Scan existing filenames", key="libnorm_scan"):
            from processing.library_normalize import scan
            # The result must NOT be stored under "libnorm_scan": that is
            # this button's own widget key, and Streamlit raises
            # StreamlitAPIException when you assign to the key of a
            # widget instantiated in the same run — so an 85-second scan
            # (MEASURED: 5.79s per 2,000 of 29,393 names) ended in a red
            # error with nothing kept.
            tick, done = _progress_ui("Checked")
            st.session_state["libnorm_scan_res"] = scan(lib, progress=tick)
            _save_scan("normalize", st.session_state["libnorm_scan_res"])
            n = st.session_state["libnorm_scan_res"]["total"]
            done(f"{n} filename(s) differ from the canonical form.")
            st.toast(f"{n} filename(s) differ from canonical.")

        data = st.session_state.get("libnorm_scan_res")
        if data is None:
            # MEASURED 85s over the 29,393 names.  Held only in
            # session_state it died on every browser reload, so he paid it
            # again before he could carry on applying batches.
            data, _age_h = _load_scan("normalize")
            if data is not None:
                st.session_state["libnorm_scan_res"] = data
                st.caption(
                    f"Showing your last scan, from {_age_h:.1f} h ago — pick "
                    "up where you left off, or rescan for fresh results."
                )
        if not data:
            st.info("Click **Scan existing filenames** to see what would change.")
            return
        if data["total"] == 0:
            st.success("Every existing filename is already canonical. ✓")
            return

        bk = data["by_kind"]
        m = st.columns(4)
        m[0].metric("Author spacing", bk[AUTHOR])
        m[1].metric("Title casing", bk[TITLE])
        m[2].metric("Both", bk[BOTH])
        m[3].metric("Uncertain words", len(data["pending_words"]))

        # Per-bucket preview.
        for kind in (AUTHOR, TITLE, BOTH):
            rows = [p for p in data["proposals"] if p["kind"] == kind]
            if not rows:
                continue
            with st.expander(f"Preview — {_KIND_LABEL[kind]} ({len(rows)})",
                             expanded=False):
                for p in rows[:60]:
                    st.markdown(
                        f"`{p['old_name']}`  →  **{p['name']}**"
                    )
                if len(rows) > 60:
                    st.caption(f"…and {len(rows) - 60} more.")

        _render_title_review(lib, data)

        st.divider()
        st.markdown("**Apply a batch** (reversible)")
        c = st.columns(3)
        inc_author = c[0].checkbox("Author spacing", value=True,
                                   key="libnorm_inc_author",
                                   help="Mechanical + safe; low-risk bucket.")
        inc_title = c[1].checkbox("Title casing", value=False,
                                  key="libnorm_inc_title",
                                  help="Review the preview first.")
        inc_both = c[2].checkbox("Both", value=False, key="libnorm_inc_both")
        c2 = st.columns([2, 2])
        batch_n = c2[0].number_input(
            "Max files this batch", min_value=1, max_value=100_000,
            value=500, step=100, key="libnorm_batch",
            help="Apply incrementally — smaller batches are easier to undo.",
        )
        queue_words = c2[1].checkbox(
            "Queue uncertain words for review", value=True,
            key="libnorm_queue",
            help="Adds surfaced words to the Settings vocabulary panel.",
        )

        sel_kinds = {k for k, on in
                     ((AUTHOR, inc_author), (TITLE, inc_title), (BOTH, inc_both))
                     if on}
        chosen = [p for p in data["proposals"] if p["kind"] in sel_kinds]
        st.caption(f"{len(chosen)} match the selected buckets; "
                   f"this batch will apply up to {int(batch_n)}.")

        if st.button("✅ Apply this batch (reversible)", type="primary",
                     key="libnorm_apply", disabled=not chosen):
            batch = chosen[:int(batch_n)]
            with st.spinner(f"Renaming {len(batch)} file(s)…"):
                res = apply_renames(
                    lib, batch, dry_run=False,
                    pending_words=(data["pending_words"] if queue_words else None),
                )
            st.success(
                f"Renamed {res['renamed']} · left alone {len(res['skipped'])}."
                + ("  You can undo this whole batch from the Activity page."
                   if res.get("tx_id") else "")
            )
            if res["skipped"]:
                with st.expander(f"{len(res['skipped'])} left alone "
                                 "(that name is already taken, or the file "
                                 "has moved)"):
                    for s in res["skipped"][:50]:
                        st.caption(f"`{s['old']}` — {s['reason']}")
            if res.get("tx_id"):
                _log_activity("normalize.apply", str(lib),
                              f"{res['renamed']} renamed", res["tx_id"])
            # Drop everything we just attempted from the pending scan so the
            # view shrinks; a fresh scan reflects the true remaining set.
            done = {p["old"] for p in batch}
            data["proposals"] = [p for p in data["proposals"]
                                 if p["old"] not in done]
            data["by_kind"] = {
                k: sum(1 for p in data["proposals"] if p["kind"] == k)
                for k in (AUTHOR, TITLE, BOTH)
            }
            data["total"] = len(data["proposals"])
            st.session_state["libnorm_scan_res"] = data
            _save_scan("normalize", data)
            st.rerun()


def render_maintenance() -> None:
    st.header("🧹 Maintenance")
    st.caption(
        "**Run checks** at the bottom only looks and reports — it changes "
        "nothing.  Two things on this page DO write: the filename tidy-up "
        "just below, and the full weekly run *if* you tick “also file the "
        "safe ones for me”.  Both are reversible from the Activity page."
    )

    lib = _library()

    _render_normalize_section(lib)

    # Phase 5: one-click full weekly run (the Monday plist's equivalent)
    # via the cockpit so users don't need a terminal to trigger it.
    with st.expander("Full weekly run (subprocess + report)", expanded=False):
        cols_full = st.columns([2, 2, 1])
        auto_apply = cols_full[0].checkbox(
            "Also file the safe ones for me (this changes files)",
            value=False,
            help=(
                "Off = look and report only.  On = papers whose published "
                "version is a near-certain match (single author, 95%+ "
                "confidence) are upgraded, and working papers old enough "
                "are moved to Unpublished papers."
            ),
        )
        if auto_apply:
            _reversible_note("With this ticked, the run will move and rename "
                             "files in your library.")
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
                st.success("Done — the results are summarised below.")
                if out.summary:
                    st.session_state.maintenance_results = out.summary
                if out.report_path and Path(out.report_path).exists():
                    st.session_state["weekly_report_path"] = out.report_path
                _log_activity("maintenance.run_full", str(lib),
                              out.report_path or "")
            else:
                # The failure branch used to hang off the "Open the full
                # report" button instead of off ``out.ok``: a SUCCESSFUL
                # run painted a red box reading "check complete", and a
                # real failure was swallowed whenever an old report path
                # happened to be in session state.
                st.error(f"The weekly run did not finish: {out.message}")
                st.caption(
                    "Nothing in your library was changed.  The usual cause "
                    "is the network dropping part-way through the Crossref "
                    "lookups — try again, or set **Crossref query limit** "
                    "to 100 for a shorter run."
                )
        # Drawn outside the click branch so it survives the rerun that
        # pressing it causes.
        _wr = st.session_state.get("weekly_report_path")
        if _wr and Path(_wr).exists():
            if st.button("📄 Open the full report", key="open_weekly"):
                import subprocess as _sp
                _sp.run(["open", str(_wr)], capture_output=True)

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

        # Four checks whose costs differ by orders of magnitude (the
        # backlog count is MEASURED at 0.02s; the Crossref one makes one
        # network call per paper and runs for minutes).  A single opaque
        # spinner made them indistinguishable, so the owner had no way to
        # judge whether waiting was reasonable.
        with st.status("Running checks…", expanded=True) as box:
            if do_count:
                box.update(label="Counting what is waiting in the inbox…")
                results["to_be_sorted"] = count_to_be_sorted(lib)
                st.write("✓ inbox backlog counted")
            if do_age:
                box.update(label="Finding working papers old enough to re-check…")
                results["aging"] = check_aging(lib, verbose=False)
                st.write("✓ aging check done")
            if do_dup:
                box.update(label="Looking for duplicate copies…")
                results["duplicates"] = check_duplicates(lib, verbose=False)
                st.write("✓ duplicate check done")
            if do_pub:
                box.update(label="Asking Crossref about up to 100 papers — "
                                 "this is the slow one, expect minutes…")
                st.write("… Crossref lookups running (one network call per paper)")
                try:
                    results["publications"] = check_publications(
                        lib, limit=100, verbose=False)
                    st.write("✓ publication check done")
                except Exception as exc:
                    # The only check that needs the network.  Losing the
                    # other three to a dropped connection — and showing a
                    # traceback instead of their results — is not
                    # acceptable for a run that takes minutes.
                    logger.warning("publication check failed: %s", exc)
                    st.write(f"✗ publication check could not finish: {exc}")
                    st.write(
                        "Check your internet connection and run it again. "
                        "The other results below are unaffected."
                    )
            box.update(label="All selected checks finished", state="complete")

        # The Crossref pass costs minutes and finds real upgrade
        # candidates — but this button only ever put them in session_state,
        # where a reload erased them and the Upgrade Queue (which reads
        # report FILES) could never see them.  Write them where that page
        # already looks.  Nothing is written inside the library.
        _pubs = results.get("publications") or {}
        _n_found = (len(_pubs.get("unpublished") or [])
                    + len(_pubs.get("working") or []))
        if _n_found:
            try:
                _rp = (Path.home() / ".mathpdf" / "reports"
                       / f"checks_{datetime.now():%Y-%m-%d_%H%M%S}.json")
                _rp.parent.mkdir(parents=True, exist_ok=True)
                _rp.write_text(json.dumps({"publications": _pubs}),
                               encoding="utf-8")
                st.session_state["upgrade_report_path"] = str(_rp)
                st.info(
                    f"{_n_found} newly-published paper(s) found — review "
                    f"them on the **Upgrade Queue** page, where this run is "
                    f"now selected for you."
                )
            except (OSError, TypeError) as exc:
                st.warning("Could not save these results for the Upgrade "
                           f"Queue: {exc}")
        st.success("Done.")
        st.session_state.maintenance_results = results

    # Display previous results if any
    res = st.session_state.get("maintenance_results")
    if not res:
        st.info(
            "No checks have been run yet.  Tick the ones you want above and "
            "press **▶ Run checks** — they only look and report; nothing "
            "in your library is changed."
        )
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


_ATTENTION_TTL_SECONDS = 1800


def _gather_attention_cached(library_str: str, include_dismissed: bool,
                             _progress=None) -> list:
    """Cache the FULL attention list for 30 minutes, WITH live progress.

    The TTL used to be 60s — but this scan MEASURES 45-113s on a 29k
    library (three collectors each walk every PDF and load every
    sidecar).  A TTL shorter than the computation means the cache can
    never be warm: every human-paced click paid a full library scan,
    which is what made the whole cockpit feel broken.  The underlying
    facts change on the timescale of a watcher run, not a click, so
    30 minutes is honest; the Home page offers an explicit "Rescan".

    Cached in session_state rather than with ``@st.cache_data``: a
    cached function may NOT draw Streamlit elements, so the decorator
    and the progress bar are mutually exclusive — with both, the whole
    landing page failed with "a streamlit element is called on some
    layout block created outside the function".  On a scan this long a
    progress bar is the difference between "working" and "frozen", so
    the cache is the part that moves.
    """
    import time
    store = st.session_state.setdefault("_attn_cache", {})
    key = (library_str, include_dismissed)
    hit = store.get(key)
    if hit is not None and (time.time() - hit[0]) < _ATTENTION_TTL_SECONDS:
        return hit[1]
    from ui.attention_queue import gather_attention_items
    items = gather_attention_items(
        Path(library_str), include_dismissed=include_dismissed,
        progress=_progress,
    )
    store[key] = (time.time(), items)
    return items


def _clear_attention_cache() -> None:
    """Drop the cached scan — same contract as ``.clear()`` had."""
    st.session_state.pop("_attn_cache", None)


# Callers (and the post-mutation invalidator) still say `.clear()`.
_gather_attention_cached.clear = _clear_attention_cache  # type: ignore[attr-defined]


def _attention_count_cached(library_str: str) -> int:
    """Thin wrapper that returns the length of the cached attention list."""
    return len(_gather_attention_cached(library_str, False))


def _attention_badge() -> str:
    """Sidebar badge text — NEVER triggers the scan.

    The sidebar renders on every page, so calling the scanner here made
    Search/Stats/Settings pay a full-library walk they had no use for.
    We only report the last count the Home page actually computed.
    """
    n = st.session_state.get("attn_count_last")
    return f"Home ({n})" if n else "Home"


# Expose ``.clear()`` for action handlers that want to invalidate the
# cache after a destructive op (so the sidebar badge updates instantly
# rather than waiting for the TTL).
def _clear_scan_caches() -> None:
    """Invalidate EVERY whole-library scan cache after a mutation.

    Any action that changes files on disk can change the attention
    queue, the conflict list AND the search index at once, so all three
    are invalidated together.  ``_conflicts_cached`` and
    ``_search_index_cached`` are defined further down the module; the
    names resolve at call time, so this can live here, next to the
    handle that ~20 existing action handlers already call.
    """
    _gather_attention_cached.clear()
    _conflicts_cached.clear()
    _search_index_cached.clear()


_attention_count_cached.clear = _clear_scan_caches  # type: ignore[attr-defined]


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


@st.cache_data(ttl=600, show_spinner="Measuring library health (~8s)…")
def _library_health_cached(lib_str: str) -> dict:
    """Cached health snapshot (10-min TTL; walks metadata surfaces only).

    MEASURED 8.3s on the 29k library — long enough that a silent cache
    miss reads as a frozen Stats page."""
    from maintenance.health import collect_library_health
    return collect_library_health(Path(lib_str))


@st.cache_data(ttl=300, show_spinner=False)
def _to_be_sorted_backlog_cached(lib_str: str) -> dict:
    """Cached ``count_to_be_sorted`` — same 5-min TTL as the folder counts.

    The backlog scan rglobs the whole ``12 - To be sorted`` tree; uncached
    it re-ran on every Stats rerun (audit perf finding).
    """
    from maintenance.weekly_report import count_to_be_sorted
    return count_to_be_sorted(Path(lib_str))


def _spelling_scan(lib):
    """Scan the library for suspected misspellings and broken characters.

    Cached in session state because it walks 27,000 filenames and queries
    the system dictionary; the owner presses Rescan when he wants it
    redone.
    """
    import unicodedata as U
    from maintenance.typos import (Verdict, broken_characters,
                                   build_corpus_stats, examine_title,
                                   learned_words_in_play, oracle_fingerprint,
                                   self_check)
    from processing.identity import iter_pdfs
    from processing.spelling_vocab import accepted_words

    self_check()          # raises rather than returning a mute oracle
    names, broken = [], []
    for pdf in iter_pdfs(lib):
        rel = pdf.relative_to(lib)
        if rel.parts and rel.parts[0].startswith("12 - "):
            continue
        name = U.normalize("NFC", pdf.name)
        names.append((name, str(rel)))
        faults = broken_characters(name)
        if faults:
            broken.append({"name": name, "rel": str(rel), "faults": faults})
    stats = build_corpus_stats((n for n, _ in names),
                               ruled_correct=accepted_words(lib))
    suspects = []
    for name, rel in names:
        rep = examine_title(name, stats)
        if rep.verdict is Verdict.TYPO:
            suspects.append({"name": name, "rel": str(rel),
                             "suspects": [s.__dict__ for s in rep.suspects]})
    suspects.sort(key=lambda r: -max(s["suggestion_freq"] for s in r["suspects"]))
    return {"suspects": suspects, "broken": broken,
            "scanned": len(names), "oracle": oracle_fingerprint(),
            "learned": learned_words_in_play()}


def render_spelling() -> None:
    """Suspected misspellings — review only, never automatic.

    Modelled on the title-vocabulary screen rather than the title-review
    one: that screen keeps its approvals in Streamlit session state, so a
    browser reload loses them and the identical proposal returns on the
    next sweep. Every button here writes to the Dropbox-synced ruling
    store before it returns, and every ruling has a route back.
    """
    from processing.library_normalize import apply_renames
    from processing.spelling_vocab import (CORRECT, DEFERRED, clear_ruling,
                                           load_rulings, rule)

    lib = _library()
    _page_header("🔤", "Spelling",
                 "Words that look wrong. Nothing is corrected automatically.")

    if st.button("↻ Rescan", key="sp_rescan") or "spelling" not in st.session_state:
        with st.spinner("Reading every filename and asking the dictionary…"):
            try:
                st.session_state["spelling"] = _spelling_scan(lib)
            except Exception as exc:
                st.error(
                    f"The spelling oracle is unavailable, so NOTHING was "
                    f"checked — this is not a clean result: {exc}")
                return
    data = st.session_state.get("spelling")
    if not data:
        return

    rulings = load_rulings(lib)
    deferred = rulings[DEFERRED]

    st.caption(
        f"{data['scanned']:,} filenames · oracle `{data['oracle']}` · "
        f"{data['learned']:,} words you have taught macOS are treated as "
        "correct without appearing here.")

    # ---- the certain ones first: no dictionary, no threshold ------------
    if data["broken"]:
        st.markdown(f"#### Certain — {len(data['broken'])} broken character(s)")
        st.caption(
            "An f-ligature means text was lifted from a PDF without "
            "normalising; a control character means the name is corrupted. "
            "No dictionary is involved, so there is no false positive here.")
        for row in data["broken"]:
            kinds = ", ".join(sorted({f[2] for f in row["faults"]}))
            fixed = row["name"]
            for _i, ch, kind, expansion in row["faults"]:
                fixed = fixed.replace(ch, expansion if kind == "f-ligature" else "")
            c = st.columns([6, 2])
            c[0].write(f"`{row['rel']}`")
            c[0].caption(f"{kinds} → `{fixed}`")
            if c[1].button("Fix it", key=f"sp_brk_{row['rel']}",
                           use_container_width=True):
                res = apply_renames(
                    lib, [{"old": row["rel"],
                           "new": str(Path(row["rel"]).parent / fixed)}],
                    dry_run=False)
                if res.get("renamed"):
                    _log_activity("spelling.character", str(lib),
                                  row["name"][:60], res.get("tx_id") or "")
                    st.toast("Renamed — undo it from Activity.")
                    st.session_state.pop("spelling", None)
                    st.rerun()
                else:
                    st.warning(res.get("error") or f"Not renamed: {res.get('skipped')}")

    # ---- the judgement calls --------------------------------------------
    active = [r for r in data["suspects"]
              if not all(s["lower"] in deferred for s in r["suspects"])]
    st.markdown(f"#### Suspected — {len(active)} file(s)")
    if deferred:
        st.caption(f"{len(deferred)} word(s) set aside. They still count as "
                   "suspect in the Conformance report; putting one off does "
                   "not make it right.")
    st.caption(
        "Ranked by how often the suggested word appears elsewhere. Precision "
        "falls down the list, so the rank tells you when you have passed the "
        "productive part. **The suggestion is evidence, not an instruction** — "
        "measured on this library it is wrong for several entries: *lobal* is "
        "suggested as *local* but means **global**.")

    shown = active[:60]
    for rank, row in enumerate(shown, 1):
        for s in row["suspects"]:
            if s["lower"] in deferred:
                continue
            key = f"{row['rel']}::{s['lower']}"
            with st.container(border=True):
                st.markdown(
                    f"**{rank}. {s['word']}** → *{s['suggestion']}* "
                    f"<span style='opacity:.6'>({s['distance']} edit"
                    f"{'s' if s['distance'] > 1 else ''}, the suggestion "
                    f"appears in {s['suggestion_freq']:,} files)</span>",
                    unsafe_allow_html=True)
                st.caption(f"`{row['rel']}`")
                b = st.columns(3)
                if b[0].button(f"Rename to “{s['suggestion']}”",
                               key=f"sp_fix_{key}", use_container_width=True):
                    new = row["name"].replace(s["word"], s["suggestion"], 1)
                    res = apply_renames(
                        lib, [{"old": row["rel"],
                               "new": str(Path(row["rel"]).parent / new)}],
                        dry_run=False)
                    if res.get("renamed"):
                        rule(lib, s["lower"], "typo", s["suggestion"])
                        _log_activity("spelling.fix", str(lib),
                                      f"{s['word']} → {s['suggestion']}",
                                      res.get("tx_id") or "")
                        st.toast("Renamed — undo it from Activity.")
                        st.session_state.pop("spelling", None)
                        st.rerun()
                    else:
                        st.warning(res.get("error") or f"Not renamed: {res.get('skipped')}")
                if b[1].button("It's a real word", key=f"sp_ok_{key}",
                               use_container_width=True):
                    rule(lib, s["lower"], CORRECT)
                    st.toast(f"'{s['word']}' will not be raised again.")
                    st.session_state.pop("spelling", None)
                    st.rerun()
                if b[2].button("Not now", key=f"sp_skip_{key}",
                               use_container_width=True):
                    rule(lib, s["lower"], DEFERRED)
                    st.rerun()
    if len(active) > len(shown):
        st.caption(f"… and {len(active) - len(shown):,} more. The whole queue "
                   "is ranked; this shows the top 60.")

    # ---- no ruling is a one-way door ------------------------------------
    ruled = ([(w, "a real word") for w in sorted(rulings[CORRECT])]
             + [(w, f"a typo for '{c}'") for w, c in sorted(rulings["typo"].items())]
             + [(w, "set aside") for w in sorted(deferred)])
    if ruled:
        with st.expander(f"↩ Change a ruling you already made ({len(ruled)})"):
            q = st.text_input("Find a word", key="sp_find",
                              placeholder="type part of the word")
            hits = [(w, d) for w, d in ruled if not q or q.lower() in w][:30]
            for w, desc in hits:
                c = st.columns([3, 2])
                c[0].markdown(f"**{w}** — currently {desc}")
                if c[1].button("Put it back in the queue", key=f"sp_undo_{w}",
                               use_container_width=True):
                    clear_ruling(lib, w)
                    st.session_state.pop("spelling", None)
                    st.rerun()
            if not hits:
                st.caption("No ruling matches that.")


def render_conformance() -> None:
    """Does the library match what the rules say it should be?

    Deliberately NOT another list of files to read.  The whole point is
    to separate the work the owner owes (a title ruling) from the work
    the CODE owes (a file no rule ever examined), so that the second
    kind is loud and the first kind is quiet however large it grows.
    """
    from maintenance import conformance as C

    _page_header(
        "🩺", "Conformance",
        "Whether the 29k files on disk are actually in the state the "
        "rules describe.",
        how_it_works=(
            "Runs the naming pipeline over every filename and checks that "
            "it is a **fixpoint** — that the rules would change nothing. "
            "A file the pipeline cannot even reach a verdict on is a bug, "
            "not a backlog item, and shows up red. Takes about a minute; "
            "nothing is written to your library."
        ),
    )

    rep = st.session_state.get("conformance_report")
    if st.button("▶ Run the check", type="primary"):
        bar = st.progress(0.0, text="Examining filenames…")

        def _p(i, n):
            bar.progress(min(1.0, i / max(n, 1)), text=f"{i:,} / {n:,}")
        rep = C.run(_library(), progress=_p)
        bar.empty()
        st.session_state["conformance_report"] = rep
        st.session_state["conformance_prev"] = C.load_previous(_library())

    if rep is None:
        st.info("Not run yet. Press **Run the check**.")
        return

    delta = C.diff_against(rep, st.session_state.get("conformance_prev"))

    st.markdown("#### Your queue — not a problem")
    a, b, sp = st.columns(3)
    sp.metric("Suspected misspellings", f"{rep.counts.get(C.TYPO, 0):,}",
              delta=delta.get(C.TYPO), delta_color="off",
              help="A word that appears once in the library while a near "
                   "neighbour appears many times. Review them on the "
                   "Spelling page; nothing is ever corrected automatically.")
    a.metric("Awaiting your ruling", f"{rep.counts[C.OWNER_QUEUE]:,}",
             delta=delta.get(C.OWNER_QUEUE), delta_color="off",
             help="The code has an opinion and wants you to settle it. "
                  "This can be any size; it is not a fault.")
    b.metric("Mechanical, not yet applied", f"{rep.counts[C.MECHANICAL]:,}",
             delta=delta.get(C.MECHANICAL), delta_color="off",
             help="Unambiguous changes waiting for an Apply. Should fall "
                  "to zero after one; if it doesn't, the apply path is broken.")

    st.markdown("#### The code is wrong")
    c, d, e = st.columns(3)
    c.metric("Never examined", f"{rep.counts[C.NOT_EXAMINED]:,}",
             delta=delta.get(C.NOT_EXAMINED),
             help="No rule reached a verdict. This is the bucket that hid "
                  "every defect found by eye.")
    d.metric("Invariant violations", f"{rep.counts[C.VIOLATION]:,}",
             delta=delta.get(C.VIOLATION),
             help="A postcondition failed. Always a bug.")
    e.metric("Canonical", f"{rep.counts[C.CANONICAL]:,}",
             delta=delta.get(C.CANONICAL), delta_color="off")

    if rep.scanned == 0:
        # "Nothing was examined" is not "everything is fine".  An empty
        # library, an unreadable folder or a mistyped root all reported
        # all-clear — the same lie as the banner this page replaced.
        st.error(
            "No documents were examined. That is not a clean bill of "
            "health — check the library path and folder permissions.")
    elif rep.is_all_clear():
        st.success("Every file reached a verdict and every invariant holds. ✓")
    else:
        st.warning(
            f"{rep.red_count():,} file(s) the code cannot account for. "
            "These are not waiting on you.")

    oos = rep.globals_.get("documents_out_of_scope", 0)
    if oos:
        st.info(
            f"{oos:,} document(s) are OUT OF SCOPE — .djvu, .epub and "
            "extension-less files. This check globs *.pdf, so it cannot "
            "speak for them either way.")
    _fp = rep.globals_.get("typo_oracle")
    if _fp:
        st.caption(
            f"Spelling oracle fingerprint `{_fp}` — macOS's dictionaries are "
            "mutable (words you have taught it, plus a file the OS rewrites "
            "as it goes), so two reports with different fingerprints were "
            "produced by different oracles and a change in the spelling "
            "count between them is not by itself evidence about the library.")
    st.caption(
        f"{rep.scanned:,} scanned in {rep.duration_s}s · "
        f"{rep.globals_.get('inbox_skipped', 0):,} inbox papers not judged "
        "(they are not named yet by design) · sidecar coverage "
        f"{rep.globals_.get('coverage_pct', 0)}%")

    st.markdown("##### Why, grouped")
    for key, n in rep.reasons.items():
        bucket, _, reason = key.partition(":")
        icon = "🔴" if bucket in C.RED else "•"
        with st.expander(f"{icon} {n:,} — {reason.replace('-', ' ')}"):
            rows = [f for f in rep.findings
                    if f"{f.bucket}:{f.reason}" == key][:200]
            for f in rows:
                st.write(f"`{f.path}`")
                if f.detail:
                    st.caption(f.detail)
            if n > len(rows):
                st.caption(f"… and {n - len(rows):,} more (showing 200)")

    if st.button("💾 Save this report (so tomorrow shows a diff)"):
        p = C.save(_library(), rep)
        st.success(f"Saved {p.name}")


def render_stats() -> None:
    _hdr, _btn = st.columns([0.75, 0.25])
    with _hdr:
        _page_header(
            "📊", "Library Stats",
            "How big your library is, and where it is healthy or falling "
            "behind.",
            how_it_works=(
                "Counts are re-used for 5 minutes so the page stays instant; "
                "press **Recompute now** straight after filing a batch to "
                "see fresh numbers."
            ),
        )
    with _btn:
        if st.button("↻ Recompute now", use_container_width=True):
            _count_pdfs_cached.clear()
            _to_be_sorted_backlog_cached.clear()
            # The health strip has its own 10-minute cache; without this
            # the button silently redrew the SAME health numbers, which
            # is worse than having no button at all.
            _library_health_cached.clear()
            st.rerun()

    lib = _library()
    if not lib.exists():
        st.error(f"That library folder does not exist: `{lib}`")
        st.caption(
            "Open **📁 Library** at the top of the sidebar and point it at "
            "your Maths folder.  Nothing is broken — the cockpit simply "
            "cannot see your papers from here."
        )
        return

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
    # st.columns(6) stacks into six 76px metric blocks (~460px, measured) in a
    # narrow pane -- half a screen of scrolling for six numbers.  A list reads
    # the same at 343px and at 1280px and costs ~24px per row.
    for f in folders:
        n = _count_pdfs_cached(str(lib / f))
        _label = f.split(" - ")[1] if " - " in f else f
        st.markdown(f"- **{n:,}** &nbsp; {_label}")

    st.divider()
    st.subheader("Waiting to be sorted")
    st.caption("Papers that have arrived but are not filed anywhere yet. "
               "Clear them from the Sort Queue page.")
    backlog = _to_be_sorted_backlog_cached(str(lib))
    st.metric("Waiting", backlog["total"])
    for sub, n in backlog["by_subfolder"].items():
        st.markdown(f"- {sub}: **{n}**")

    st.divider()
    st.subheader("Library health")
    st.caption("A quick check that the library's bookkeeping is in good "
               "shape. Nothing here changes anything; refreshed every "
               "10 minutes.")
    try:
        h = _library_health_cached(str(lib))
    except Exception as exc:
        # An 8.3s metadata walk that raises used to end the page in a
        # traceback and take the trash counts with it.
        logger.exception("library health scan failed")
        st.warning(f"The health figures could not be measured: {exc}")
        st.caption(
            "The counts above are still correct — only this strip is "
            "missing.  It usually means a file is mid-sync; press "
            "**↻ Recompute now** in a minute."
        )
        st.divider()
        st.subheader("Trash (recoverable)")
        _tc = st.columns(2)
        _tc[0].metric("Sorted originals", _count_trash(lib, "sorted_originals"))
        _tc[1].metric("Upgraded preprints",
                      _count_trash(lib, "upgraded_preprints"))
        return
    hc = st.columns(4)
    hc[0].metric("Papers with details saved",
                 f"{h['sidecar_coverage']:.1%}",
                 help=f"{h['sidecars']} of {h['pdfs']} PDFs have their title, "
                      f"authors and DOI stored alongside them. That is what "
                      f"search and duplicate-detection read. Fill in the "
                      f"missing ones from Settings.")
    hc[1].metric("Words awaiting your ruling", h["vocab_pending"],
                 help=f"Words the renamer cannot tell how to capitalise. "
                      f"You have already ruled on {h['vocab_ruled']}. "
                      f"Decide the rest in Settings → Title vocabulary.")
    hc[2].metric("Changes you can still undo", h["undo_transactions"],
                 help="Every batch of changes ever made is still reversible "
                      f"from the Activity page (the most recent was "
                      f"{h['last_tx_age_days']} days ago).")
    hc[3].metric("Files in the trash", h["trash_pdfs"],
                 help="Nothing is ever deleted outright. These can be put "
                      "back from the Activity page or straight from Finder.")
    notes = []
    if h["model_trained_on"]:
        notes.append(
            f"Capitalisation helper: learned from {h['model_trained_on']} of "
            f"your own filenames, and gets {h['model_accuracy']:.0%} right on "
            f"names it had never seen; last updated "
            f"{h['model_age_days']} days ago")
    else:
        notes.append("Capitalisation helper: not trained yet — train it in "
                     "Settings → Title vocabulary")
    if h["corpus_stats_age_days"] >= 0:
        notes.append("word statistics taken from your own library: "
                     f"{h['corpus_stats_age_days']} days old")
    st.caption(" · ".join(notes))

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
        # MEASURED 21.6s per 1,000 papers with cached abstracts — i.e.
        # ~636s (>10 minutes) for the DEFAULT "Whole library / All".
        # A bare spinner for that long is indistinguishable from a hang.
        tick, done = _progress_ui("Read")
        try:
            summary, proposals = preview_topic_filing(
                lib, scope=scope, limit=limit, enrich=enrich, progress=tick,
            )
        except Exception as exc:
            done()
            logger.exception("pipeline preview failed")
            st.error(f"The preview stopped early: {exc}")
            st.caption(
                "Nothing was moved or renamed — this screen never changes "
                "your library.  Try a smaller **Sample** (1000), or one "
                "folder in **Scope** instead of the whole library; if it "
                "keeps stopping, that folder holds a PDF that cannot be "
                "read."
            )
            return
        done(f"Classified {summary.scanned:,} papers (nothing was moved).")
        if summary.scanned == 0:
            st.warning(
                "There were no PDFs to look at in that scope — pick a "
                "different folder, or 'Whole library'."
            )
        st.session_state["preview_summary"] = summary.to_dict()
        st.session_state["preview_proposals"] = [p.to_dict() for p in proposals]
        _save_scan("pipeline_preview", {
            "summary": st.session_state["preview_summary"],
            "proposals": st.session_state["preview_proposals"],
        })

    s = st.session_state.get("preview_summary")
    proposals = st.session_state.get("preview_proposals")
    if s is None:
        # MEASURED ~636s for the default "Whole library / All".  A browser
        # reload used to throw away all of it — including the trust
        # metrics this page exists to produce and the apply step gated
        # behind them.
        _snap, _age_h = _load_scan("pipeline_preview")
        if _snap:
            s = st.session_state["preview_summary"] = _snap.get("summary")
            proposals = st.session_state["preview_proposals"] = \
                _snap.get("proposals")
            st.caption(
                f"Showing your last preview, from {_age_h:.1f} h ago — "
                "rerun it for fresh numbers."
            )
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
    with st.expander("📄 Read the abstracts (makes the guesses much better)"):
        st.caption(
            "Reads the abstract and first pages out of each PDF and stores "
            "the text, so the classifier can judge a paper by its content "
            "instead of its title alone. It only reads your PDFs — nothing "
            "is moved or renamed — and you can stop and pick up where you "
            "left off. The whole library takes 30–60 minutes, so start with "
            "a small batch here to see the difference.")
        cbf = st.columns([1, 1])
        # NB: keys must be unique across ALL pages — "bf_limit"/"bf_run" are
        # taken by the Settings sidecar-backfill widgets; sharing them would
        # bleed state between the two pages via st.session_state.
        bf_n = cbf[0].selectbox("Batch", ["100", "500", "2000", "All"], index=0,
                                key="abstracts_bf_limit")
        if cbf[1].button("Cache abstracts now", key="abstracts_bf_run"):
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
                # Five columns inside the measured 311px content width is
                # ~60px each -- nothing is legible.  "path" duplicates the
                # filename plus the topic already shown in "move".
                "paper": Path(p["path"]).name,
                "move": f"{p['current_topic'] or '—'} → "
                        f"{p['proposed_topic'] or p['suggested_topic'] or '—'}",
                "confidence": f"{p['confidence']:.0%}",
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
        if ca.button("Show me the list first (changes nothing)",
                     key="preview_apply_dryrun"):
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
            dup_n = len(res.get("duplicates", []))
            if res.get("tx_id"):
                _log_activity("topic.bulk_apply", f"{ok_n} moved",
                              f"{fail_n} failed", res["tx_id"])
            st.success(f"Filed {ok_n} paper(s); {fail_n} failed. "
                       f"Undo from the Activity tab (one transaction).")
            if dup_n:
                st.info(
                    f"{dup_n} paper(s) are already filed in their topic "
                    f"(the source is a redundant duplicate). Clean them up "
                    f"reversibly in the **Duplicates** tab."
                )
                st.dataframe(
                    [{"paper": Path(d["path"]).name, "why": d["msg"]}
                     for d in res["duplicates"][:200]],
                    use_container_width=True, hide_index=True,
                )
            if res["failed"]:
                st.dataframe(
                    [{"paper": Path(f["path"]).name, "why": f["msg"]}
                     for f in res["failed"][:200]],
                    use_container_width=True, hide_index=True,
                )
            # Fresh numbers next render.
            for k in ("preview_summary", "preview_proposals"):
                st.session_state.pop(k, None)
            # …and the on-disk copy, or a reload would resurrect numbers
            # describing a library state that no longer exists.
            _save_scan("pipeline_preview", None)
            _count_pdfs_cached.clear()


# ---------------------------------------------------------------------------
# Page: Activity
# ---------------------------------------------------------------------------

# Internal transaction descriptions -> plain English.  MEASURED against the
# real log (314 transactions): the commonest strings the owner sees on the
# only page that offers Undo are 'bulk_sort: 12 papers' (58), 'Watcher:
# ingest …' (114), 'bulk conflict keep_canonical (3)' (7) and 'dedup' (5).
# Longest prefix first so 'dedup (manual):' wins over 'dedup'.
_TX_PHRASES = [
    ("bulk_sort:", "Filed papers from the inbox —"),
    ("Cockpit sort:", "Filed a paper —"),
    ("Watcher: ingest", "Filed automatically —"),
    ("dedup (manual):", "Removed duplicate copies —"),
    ("dedup review batch", "Removed duplicate copies (reviewed batch)"),
    ("dedup", "Removed duplicate copies"),
    ("bulk conflict keep_canonical", "Kept the original of Dropbox conflict copies"),
    ("bulk conflict keep_conflict", "Kept the conflicted copy instead of the original"),
    ("bulk conflict keep_both", "Kept both versions of Dropbox conflicts"),
    ("conflict keep_canonical:", "Kept the original, trashed the conflict copy —"),
    ("conflict keep_conflict:", "Kept the conflict copy, trashed the original —"),
    ("conflict keep_both:", "Kept both versions —"),
    ("Cockpit upgrade:", "Replaced a preprint with its published version —"),
    ("normalize existing filenames", "Tidied existing filenames"),
    ("Bulk topic apply", "Moved papers into topic folders"),
    ("Accept topic", "Moved a paper into its topic folder —"),
    ("Reject topic", "Cleared a topic suggestion —"),
    ("attention: trash conflict", "Moved a conflict copy to the trash —"),
]


def _humanize_tx(desc: str) -> str:
    """Turn an internal transaction description into something readable.

    He has to understand what a row IS before he can decide to reverse it,
    and the log is written by the pipeline, not for him.  Anything with no
    known prefix is passed through unchanged rather than mangled.
    """
    d = (desc or "").strip()
    for prefix, human in _TX_PHRASES:
        if d.startswith(prefix):
            rest = d[len(prefix):].strip()
            return f"{human} {rest}".strip() if rest else human
    return d or "(no description)"


def render_activity() -> None:
    st.header("🕐 Recent activity")
    st.caption(
        "Everything that has ever changed your library, newest first — "
        "including changes made automatically in the background while you "
        "were away, not only the ones you approved on these pages. Each "
        "entry can be put back with its Undo button."
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
        # Do NOT fall through to the "Nothing has changed your library
        # yet" empty state below: that is a factual claim about his
        # library, and all that happened here is that the history could
        # not be read.
        st.error(f"The history of changes could not be read: {exc}")
        st.caption(
            f"It is kept in `{LOG_DIR}`.  Your papers are unaffected and "
            "nothing has been lost.  If that folder is on Dropbox, wait "
            "for the sync to finish and reload this page — the undo "
            "history will come back on its own."
        )
        return

    # Map tx_id -> the richest session label we have, for nicer display.
    session_by_tx = {
        e["tx_id"]: e for e in st.session_state.get("activity_log", [])
        if e.get("tx_id")
    }

    st.caption(f"{len(transactions)} change(s) on record  ·  the history "
               f"itself is kept in `{LOG_DIR}`")

    if not transactions:
        st.info("Nothing has changed your library yet.")
        return

    # Newest first, paginated.  The shared undo log holds 307 transactions
    # against the real library and every one of them was rendered as an
    # expander containing two buttons (~600 widgets) -- the same failure
    # already fixed on Home.  20 rows covers "undo what I just did", which
    # is what this page is for.
    _ordered = list(reversed(transactions))
    _shown = st.session_state.setdefault("activity_shown", 20)
    st.caption(
        f"Showing the {min(_shown, len(_ordered))} most recent "
        f"of {len(_ordered)}."
    )
    if len(_ordered) > _shown and st.button(
        f"Show 20 older  ({len(_ordered) - _shown} not shown)",
        key="activity_more",
        use_container_width=True,
    ):
        st.session_state["activity_shown"] = _shown + 20
        st.rerun()
    for i, tx in enumerate(_ordered[:_shown]):
        tx_id = tx.get("id", "")
        desc = tx.get("description", "(no description)")
        when = tx.get("timestamp", "")[:19].replace("T", " ")
        n_ops = tx.get("operations_count", "?")
        undone = tx.get("undone", False)
        label = f"{when}  ·  {_humanize_tx(desc)}  ·  {n_ops} change(s)" + (
            "  ·  ALREADY UNDONE" if undone else "")
        # The Undo button lived inside a collapsed expander, so the one
        # control this page exists for was invisible until the user guessed
        # to click a row.  Open the newest still-undoable entry — that is
        # the row he came here for after a mistaken click.
        with st.expander(label, expanded=(i == 0 and not undone)):
            st.markdown(f"**Reference**: `{tx_id}`")
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
                if col1.button("Show what Undo would do",
                               key=f"prev_{i}_{tx_id}"):
                    _preview_undo(tx_id)
                if col2.button("↶ Undo", key=f"undo_{i}_{tx_id}", type="primary"):
                    if _undo_transaction(tx_id):
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


def _undo_transaction(tx_id: str) -> bool:
    """Reverse a transaction.  Returns True only if it actually worked.

    The caller must not rerun on failure: a rerun throws away the error
    message, so a failed undo looked identical to a successful one --
    the most dangerous possible confusion in this app.
    """
    from processing.undo_log import UndoLog
    log = UndoLog()
    try:
        results = log.undo_transaction(tx_id, dry_run=False)
        # Count what actually came back, not how many rows were produced.
        # results includes SKIP and CANNOT UNDO entries, so a completely
        # REFUSED undo used to toast "Undid 8514 ops" — the most dangerous
        # sentence this app can show, because the owner then believes the
        # library is in a state it is not in.
        done = sum(1 for r in results if r.get("ok"))
        refused = [r for r in results if not r.get("ok")]
        if done:
            st.toast(f"Undid {done} of {len(results)} ops in {tx_id}", icon="↶")
        if refused:
            st.warning(
                f"{len(refused)} of {len(results)} operations could NOT be "
                f"undone and were left alone. The transaction stays in the "
                f"list so you can retry after resolving them.")
            with st.expander(f"What was refused ({len(refused)})"):
                for r in refused[:200]:
                    st.write(r["action"])
                if len(refused) > 200:
                    st.caption(f"… and {len(refused) - 200:,} more")
        if not done:
            st.error(
                "Nothing was undone. The files are exactly where they were "
                "before this click.")
            return False
        _log_activity("undo", tx_id, f"{done}/{len(results)} ops", tx_id)
        _attention_count_cached.clear()
        return True
    except Exception as exc:
        logger.exception("undo of %s failed", tx_id)
        st.error(
            f"Undo did not work: {exc}\n\nNothing has been changed by this "
            f"click.  The files are still where they are, and the entry "
            f"stays in the list so you can try again."
        )
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Page: Attention Queue (unified "needs your attention" inbox)
# ---------------------------------------------------------------------------

def _attention_severity_emoji(sev: str) -> str:
    """Severity marker for an attention row.

    Returns symbol AND word.  A bare 🛑/⚠/ℹ carries the entire severity
    system on Home, which is unreadable to anyone who does not already
    know the convention and silent to a screen reader.  The trailing
    separator matches the single call site, which renders
    ``f"{marker} **{title}**"``.
    """
    return {
        "error": "🛑 Blocked ·",
        "warning": "⚠ Needs a look ·",
        "info": "ℹ For information ·",
    }.get(sev, "•")


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

    st.header("🏠 Home")
    st.caption(
        "What needs you, grouped. Nothing here changes your library until "
        "you press a button, and every change can be undone from Activity."
    )
    _render_flashes()
    _hc = st.columns([0.75, 0.25])
    with _hc[1]:
        # The scan is genuinely expensive (a full library walk), so it is
        # cached for 30 min and refreshed on demand rather than on a
        # timer the owner cannot see.
        if st.button("↻ Rescan", use_container_width=True, key="attn_rescan"):
            _gather_attention_cached.clear()
            st.rerun()

    lib = _library()
    # ``Path("...")`` is always truthy, so the old ``if not lib`` could
    # never fire.  With a wrong or half-synced folder every collector
    # returned nothing and this page showed the green "Nothing needs your
    # attention right now ✓" — the most misleading screen in the app.
    if not lib.exists():
        st.error(f"That library folder does not exist: `{lib}`")
        st.caption(
            "Open **📁 Library** at the top of the sidebar and point it at "
            "your Maths folder.  If it is on Dropbox and still syncing, "
            "wait for Dropbox to finish, then press ↻ Rescan.  Until then "
            "this page cannot tell 'nothing to do' from 'cannot look'."
        )
        return

    # Allow the user to toggle dismissed items on/off so they can
    # un-snooze something they hid in haste.
    show_dismissed = st.checkbox("Show dismissed items", value=False)

    # Use the same 60s cache the sidebar count uses so clicking around
    # the Attention tab doesn't re-glob the library on every rerun.
    # MEASURED 111s before the shared sidecar cache, 44s after — either
    # way far too long to sit behind an unchanging spinner line.  Show
    # which of the eight checks is running.  No ETA: the checks differ by
    # three orders of magnitude (0.02s .. 36s), so a linear estimate
    # would be a lie.
    _attn_labels = {
        "watcher_failure": "files the watcher could not file",
        "upgrade_flag": "papers you asked to download",
        "aging": "working papers old enough to re-check",
        "conflict_copy": "Dropbox conflict copies",
        "borderline_match": "borderline publication matches (slow)",
        "topic_suggestion": "topic suggestions (slow)",
        "permanently_unpublished": "papers marked never-to-be-published (slow)",
        "unsorted_backlog": "papers waiting in the inbox",
    }
    _tick, _done = _progress_ui("Check", show_eta=False)
    try:
        items = _gather_attention_cached(
            str(lib), show_dismissed,
            lambda i, n, name: _tick(i, n, _attn_labels.get(name, name.replace("_", " "))),
        )
    except Exception as exc:
        # This is the landing page and the scan walks every PDF; a raw
        # traceback here is the first thing he sees after a minute of
        # waiting.
        _done()
        logger.exception("attention scan failed")
        st.error(f"The check of your library could not finish: {exc}")
        st.caption(
            "Nothing was changed.  Press ↻ Rescan to try again — the most "
            "common cause is a file Dropbox has not finished downloading "
            "yet, which fixes itself once the sync completes."
        )
        return
    _done()
    # Publish the count for the sidebar badge.  The sidebar must never
    # run this scan itself — that made every page pay for it.
    st.session_state["attn_count_last"] = len(items)
    if not items:
        st.success("Nothing needs your attention right now. ✓")
        return

    # Group by source for visual chunking.
    by_source: dict[str, list] = {}
    for it in items:
        by_source.setdefault(it.source, []).append(it)

    source_labels = {
        "collector_error": "Checks that could not run",
        "watcher_failure": "Watcher failures",
        "upgrade_flag": "Manual download requests",
        "aging": "Aging working papers",
        "conflict_copy": "Dropbox conflict copies",
        "borderline_match": "Probably published — worth a look",
        "topic_suggestion": "Suggested topic folders to confirm",
        "permanently_unpublished": "Gave up looking for a published version",
        # Was missing, so the BIGGEST group on the page was headed with
        # the raw internal key "unsorted_backlog (1861)".
        "unsorted_backlog": "Waiting to be filed",
    }
    # One plain sentence per group, so a count means something.
    source_blurbs = {
        "collector_error": "A check failed, so some of the counts below are "
                           "incomplete.",
        "watcher_failure": "Files the watcher could not ingest.",
        "upgrade_flag": "You asked for the published PDF; fetch it.",
        "aging": "Working papers old enough to check for publication.",
        "conflict_copy": "Dropbox made a second copy of the same file.",
        "borderline_match": "A likely published version was found, but not "
                            "certainly the same paper — check it, then "
                            "upgrade it from the Upgrade Queue.",
        "topic_suggestion": "A topic folder was guessed for these; say yes or no.",
        "permanently_unpublished": "Searched over and over and never found a "
                                   "published version, so the search stopped. "
                                   "Nothing to do unless you know one exists.",
        "unsorted_backlog": "Sitting in the inbox, not yet filed anywhere.",
    }
    # Genuinely-blocked work first; bulk backlogs last.  Previously the
    # order was dict-insertion, so the 8 items actually waiting on a
    # decision sat below ~2,900 informational rows.
    source_order = [
        "collector_error",
        "watcher_failure", "conflict_copy", "upgrade_flag", "topic_suggestion",
        "borderline_match", "aging", "permanently_unpublished", "unsorted_backlog",
    ]

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
    # The snooze bar only makes sense once a pile is open — on the
    # summary it read "Dismiss 0 for 7 days" above everything, which is
    # noise before the owner has chosen anything to act on.
    _open_now = st.session_state.get("attn_open_group")
    bar = st.columns([1, 1, 2, 2]) if _open_now else [_Null()] * 4
    if bar[0].button(
        f"Select all {len(by_source.get(_open_now) or [])} in this pile",
        key="attn_sel_all",
        use_container_width=True,
    ):
        # Scoped to the OPEN group.  `live_keys` spans every pile, so this
        # used to arm the neighbouring "Dismiss N for 30 days" over all
        # ~3,261 items — including the handful of genuinely-blocked ones —
        # from inside a screen that shows only one pile.
        st.session_state[attn_sel_key] = {
            it.key for it in (by_source.get(_open_now) or [])}
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

    # ---- Summary first: what needs you, at a glance -------------------
    # The page used to open straight into ~3,261 individual rows, which
    # is state, not a decision.  These cards say what each pile IS and
    # how big, and let him open just the one he wants.
    st.subheader("What needs you")
    ordered = [(k, by_source[k]) for k in source_order if k in by_source]
    ordered += [(k, v) for k, v in by_source.items() if k not in source_order]
    open_key = st.session_state.get("attn_open_group")
    for i in range(0, len(ordered), 2):
        for col, (skey, sitems) in zip(st.columns(2), ordered[i:i + 2]):
            with col, st.container(border=True):
                # The count IS the card -- it was rendered as an inline
                # code span, smaller than its own label.  st.metric puts
                # the number at ~2rem and matches how counts are shown on
                # Sort Queue, Duplicates and Stats.
                st.metric(source_labels.get(skey, skey), len(sitems))
                st.caption(source_blurbs.get(skey, ""))
                is_open = open_key == skey
                if st.button(
                    "Hide" if is_open else "Review these",
                    key=f"attn_open_{skey}",
                    use_container_width=True,
                    type="secondary" if is_open else "primary",
                ):
                    st.session_state["attn_open_group"] = None if is_open else skey
                    st.rerun()
    st.divider()

    if not open_key or open_key not in by_source:
        st.info("Pick a pile above to review it. Nothing is changed until you act.")
        return

    # ---- Only the chosen group, and only a page of it ------------------
    for source_key, source_items in [(open_key, by_source[open_key])]:
        st.subheader(f"{source_labels.get(source_key, source_key)} ({len(source_items)})")
        # Pagination: rendering every item emitted ~13,000 widgets and
        # made a single click take ~20s.  25 rows keeps it instant.
        shown_key = f"attn_shown_{source_key}"
        shown = st.session_state.setdefault(shown_key, 25)
        page_items = source_items[:shown]
        for it in page_items:
            with st.container(border=True):
                # Per-item checkbox in front of the existing content
                # column.  Toggles fold into the session_state set.
                # "select" as the label meant 25 identically-named
                # checkboxes in the accessibility tree, in front of a bulk
                # action that dismisses real work for 30 days.
                # The label names the ITEM, so 25 tick boxes are not 25
                # identical "select"s in the accessibility tree — in front
                # of a bulk action that snoozes real work for 30 days.
                # Collapsed keeps it out of the visual noise; Streamlit
                # still exposes the text to assistive tech.
                ck = st.checkbox(
                    f"Select: {it.title}",
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
                                # This called ``fp.unlink()`` -- the one hard
                                # delete in an app whose whole promise is that
                                # nothing is ever deleted.  The note now goes
                                # to ``.trash/done_flags/`` through the same
                                # helper the To Download page already uses.
                                from ui.cockpit_actions import (
                                    mark_flag_done as _mark_flag_done,
                                )
                                fp = Path(it.payload.get("flag_file", ""))
                                if fp.exists() and _mark_flag_done(fp, lib):
                                    _log_activity("attention.mark_flag_done",
                                                  fp.name, ".trash/done_flags/")
                                    st.toast(
                                        "Marked done — the note was moved "
                                        "to the trash folder, not deleted."
                                    )
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
                                    # Move to .trash/ through the undo log so the
                                    # removal is reversible from the Activity tab
                                    # (not just recoverable by hand in Finder).
                                    from processing.undo_log import (
                                        UndoLog, logged_move,
                                    )
                                    trash = lib / ".trash" / "conflict_copies"
                                    trash.mkdir(parents=True, exist_ok=True)
                                    dest = trash / p.name
                                    n = 1
                                    while dest.exists():
                                        dest = trash / f"{p.stem} ({n}){p.suffix}"
                                        n += 1
                                    _log = UndoLog()
                                    _tx = _log.begin_transaction(
                                        f"attention: trash conflict {p.name}")
                                    try:
                                        logged_move(p, dest, undo_log=_log)
                                        _log.commit()
                                        _log_activity(
                                            "attention.delete_conflict",
                                            str(p.relative_to(lib)),
                                            str(dest.relative_to(lib)), _tx)
                                        st.toast("Moved conflict copy to .trash/ "
                                                 "— undo from the Activity tab")
                                        _attention_count_cached.clear()
                                    except Exception as exc:
                                        _log.discard()
                                        st.warning(
                                            f"Could not move conflict copy: {exc}")
                            elif action_id == "watcher_retry":
                                # Was a pure no-op: it printed an instruction
                                # that the st.rerun() below immediately wiped,
                                # so the only action on the highest-severity
                                # pile did nothing at all.  The failed file is
                                # still sitting in the inbox (the daemon leaves
                                # it there), so run the very same ingest the
                                # watcher would have run -- one click, and
                                # reversible from Activity like every other
                                # filing.
                                from processing.ingest import ingest_paper
                                from processing.undo_log import UndoLog
                                src = Path(it.payload.get("file", ""))
                                if not src.exists():
                                    _flash("warning",
                                           f"{src.name} is no longer in the "
                                           f"inbox — nothing to retry.")
                                else:
                                    _ulog = UndoLog()
                                    _tx = _ulog.begin_transaction(
                                        f"Retry ingest: {src.name}")
                                    try:
                                        r = ingest_paper(
                                            src, library_root=lib,
                                            dry_run=False, undo_log=_ulog,
                                            dedup_check=True,
                                            variant_check=True,
                                        )
                                    except Exception as exc:
                                        r = {"success": False,
                                             "error": str(exc)}
                                    if _ulog.has_operations():
                                        _ulog.commit()
                                    else:
                                        _ulog.discard()
                                    if r.get("success"):
                                        _log_activity(
                                            "attention.watcher_retry",
                                            src.name,
                                            r.get("destination", ""), _tx)
                                        st.toast(f"Filed {src.name}",
                                                 icon="✅")
                                        _attention_count_cached.clear()
                                    elif r.get("duplicate_of"):
                                        _flash(
                                            "info",
                                            f"{src.name} is already in your "
                                            f"library — nothing to file.")
                                    else:
                                        _flash(
                                            "error",
                                            f"Still cannot file {src.name}: "
                                            f"{r.get('error', 'unknown reason')}"
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
                                    _flash(
                                        "warning",
                                        "That paper is no longer in the aging "
                                        "list — press ↻ Rescan and try again."
                                    )
                                else:
                                    # transition_aged_papers records its own
                                    # reversible undo tx (visible in Activity);
                                    # log the action to the activity feed too.
                                    results = transition_aged_papers([match], dry_run=False)
                                    status = results[0]["status"] if results else "no-op"
                                    _log_activity("attention.transition_aged",
                                                  Path(target_path).name, status)
                                    st.toast(
                                        f"Moved to Unpublished papers "
                                        f"({status}) — undo it from the "
                                        f"Activity page."
                                    )
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
                                        _log_activity("attention.reset_recheck",
                                                      str(p.relative_to(lib)))
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
                                    ulog.discard()
                                    _flash("warning", msg)
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
                            logger.exception("attention action %s failed",
                                             action_id)
                            _flash("error", f"That didn't work: {exc}")
                        st.rerun()

        remaining = len(source_items) - len(page_items)
        if remaining > 0:
            if st.button(
                f"Show 25 more  ({remaining} still hidden)",
                key=f"attn_more_{source_key}",
                use_container_width=True,
            ):
                st.session_state[shown_key] = shown + 25
                st.rerun()

    if show_dismissed:
        # The old version asked him to TYPE the internal key of the item
        # ("upgrade_flag::04 - Papers to be downloaded/…"), which the UI
        # never shows anywhere -- so nothing could ever be brought back.
        from ui.attention_queue import list_dismissals
        snoozed = list_dismissals()
        title_by_key = {i.key: i.title for i in items}
        live = {k: v for k, v in snoozed.items() if k in title_by_key}
        with st.expander(f"Snoozed items ({len(live)})", expanded=bool(live)):
            if not live:
                st.caption("Nothing is snoozed right now.")
            for k, until in sorted(live.items(), key=lambda kv: kv[1]):
                c = st.columns([4, 1])
                c[0].markdown(title_by_key.get(k, k))
                c[0].caption(f"hidden until {str(until)[:10]}")
                if c[1].button("Bring back", key=f"undismiss_{k}",
                               use_container_width=True):
                    undismiss(k)
                    _attention_count_cached.clear()
                    st.rerun()


# ---------------------------------------------------------------------------
# Page: To Download (04/ browser + DOI form) -- Phase 5
# ---------------------------------------------------------------------------

def _show_download_hint(doi: str) -> None:
    """After a failed download, explain WHY (Cloudflare / not-signed-in /
    paywalled) and, when it's a sign-in gap, offer the publisher login link."""
    try:
        from downloader import browser_session as _bs
        diag = _bs.last_diagnosis(doi)
    except Exception as exc:
        logger.debug("download diagnosis unavailable for %s: %s", doi, exc)
        diag = None
    if not diag:
        # No specific diagnosis is still no excuse for a bare red error:
        # say what fixes this most of the time.
        st.caption(
            "What usually fixes this: turn your **VPN off**, make sure you "
            "are signed in to the publisher in Chrome and press **Settings "
            "→ 🔄 Refresh from Chrome**, then try again.  Otherwise open "
            "the DOI above and save the PDF into your inbox folder "
            "yourself — it will be filed from there."
        )
        return
    st.info(f"ℹ️ Why: {diag['message']}")
    if diag.get("login_url") and diag.get("publisher"):
        st.link_button(
            f"Open {diag['publisher']} to sign in (then Settings → 🔄 Refresh from Chrome)",
            diag["login_url"],
        )


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
        "Papers whose published version exists but could not be downloaded "
        "automatically — usually a paywall. Fetch them here, or paste any "
        "DOI below to download that paper right away."
    )

    lib = _library()

    # Inbox is where downloaded PDFs land for the watcher to pick up.
    try:
        inbox = WatcherConfig.load().inbox_dir
    except Exception as exc:
        # Swallowing this meant downloads landed in a GUESSED folder that
        # the watcher may not be watching — the PDF arrives, nothing
        # files it, and no screen ever explains why.
        inbox = Path.home() / "Downloads" / "MathInbox"
        st.warning(
            f"Your watcher settings could not be read ({exc}), so downloads "
            f"will be saved to `{inbox}`.  If they are not filed "
            f"automatically, check **Settings → Watcher settings** and make "
            f"sure the inbox folder there is this one."
        )

    # --- DOI download form -----------------------------------------
    with st.container(border=True):
        st.subheader("Download by DOI")
        st.caption(f"The PDF is saved to `{inbox}` and filed into your "
                   f"library automatically from there.")
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
                    _show_download_hint(doi.strip())

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
                        _show_download_hint(flag["doi"])
                if st.button(
                    "Mark done", key=f"flag_done_{flag['flag']}",
                    use_container_width=True,
                    help="Takes this off the list. The note is moved to the "
                         "library's trash folder, not deleted.",
                ):
                    if mark_flag_done(flag["flag"], lib):
                        _log_activity("download.flag_done", flag["title"],
                                      ".trash/done_flags/")
                        st.toast("Marked done — the note moved to the "
                                 "trash folder, not deleted.")
                        _attention_count_cached.clear()
                        st.rerun()


# ---------------------------------------------------------------------------
# Page: Settings (config editor) -- Phase 5
# ---------------------------------------------------------------------------

def _render_title_vocabulary(lib: Path) -> None:
    """Owner review of uncertain title words (the learning loop).

    The safe-default title caser preserves any capitalized word it cannot
    prove common and queues it here.  One click settles the word
    library-wide: Proper (keep capitalized) or Common (lowercase on the
    next move).  Decisions persist in the Dropbox-synced vocabulary.
    """
    from processing.title_vocab import decide, load_vocab

    vocab = load_vocab(lib)
    pending = vocab["pending"]
    with st.expander(
        f"📖 Title vocabulary — {len(pending)} word(s) awaiting review",
        expanded=bool(pending) and len(pending) <= 12,
    ):
        st.caption(
            f"Ruled so far: {len(vocab['proper'])} kept capitalised · "
            f"{len(vocab['common'])} lowercased.  A ruling applies to every "
            "future move/filing; it never renames files retroactively."
        )

        # A ruling was the one decision in this app with no route back: the
        # word leaves the pending list and no screen ever showed it again,
        # yet it silently shapes every future filename.  ``decide()`` already
        # supports the opposite ruling; nothing in the UI reached it.
        _ruled = ([(w, "proper") for w in sorted(vocab["proper"])]
                  + [(w, "common") for w in sorted(vocab["common"])])
        if _ruled:
            with st.expander(
                f"↩ Change a ruling you already made ({len(_ruled)})",
                expanded=False,
            ):
                _q = st.text_input("Find a word", key="vocab_ruled_find",
                                   placeholder="type part of the word")
                _hits = [(w, k) for w, k in _ruled
                         if not _q or _q.lower() in w.lower()][:30]
                if not _hits:
                    st.caption("No ruling matches that.")
                for _w, _k in _hits:
                    _c = st.columns([3, 2])
                    _c[0].markdown(
                        f"**{_w}** — currently "
                        + ("kept capitalised" if _k == "proper"
                           else "lowercased"))
                    _flip = "common" if _k == "proper" else "proper"
                    if _c[1].button(
                        ("Lowercase it instead" if _flip == "common"
                         else "Keep it capitalised instead"),
                        key=f"vocab_flip_{_k}_{_w}",
                        use_container_width=True,
                    ):
                        decide(lib, _w, _flip)
                        st.toast(f"'{_w}' is now "
                                 + ("lowercased." if _flip == "common"
                                    else "kept capitalised."))
                        st.rerun()
                if len(_hits) == 30:
                    st.caption("Showing the first 30 — type more to narrow it.")
                st.caption("Changing a ruling affects future filings only — "
                           "it never renames files you already have.")

        # Self-trained assist model (Stage 2): suggests a ruling per pending
        # word.  Trained ONLY on the owner's own data (corpus casing stats,
        # author surnames, GOLD titles, prior rulings) — no third parties.
        from processing.title_model import load_model, suggest, train_model
        model = load_model(lib)
        mcols = st.columns([3, 2])
        if model:
            met = model.get("metrics", {})
            mcols[0].caption(
                f"Assist model: {model.get('trained_on', '?')} examples · "
                f"held-out accuracy {met.get('accuracy', 0):.0%} · proper-"
                f"precision {met.get('proper_precision', 0):.0%}"
            )
        else:
            mcols[0].caption("Assist model not trained yet.")
        if mcols[1].button("↻ (Re)train assist model", key="vocab_train"):
            with st.spinner("Training on your corpus…"):
                try:
                    model = train_model(lib)
                    st.toast("Model trained.")
                except Exception as exc:
                    st.warning(f"Training failed: {exc}")
            st.rerun()

        if not pending:
            st.success("No uncertain title words. ✓")
            return

        # Most-seen first; cap the render so a huge backlog stays snappy.
        ranked = sorted(pending.items(), key=lambda kv: -kv[1].get("count", 1))
        items = ranked[:50]
        # Score EVERY pending word, not just the 50 on screen.  The
        # bulk-accept button below was built from this dict, so it could
        # only ever settle 50 words at a time: on the 1,552-word backlog
        # a filename sweep produces, 1,044 of which the model calls
        # "proper" at >=0.99, that turned one click into twenty-one.
        # Scoring the whole queue costs ~35 ms (measured: 2,000 calls in
        # 0.046 s), so there is nothing to save by truncating.
        suggestions = {}
        if model:
            for word, _ in ranked:
                suggestions[word] = suggest(word, model)

        # One-click bulk accept for the model's highest-confidence PROPER
        # calls (the pending queue is dominated by eponyms).  Common-side
        # suggestions are shown as hints but applied only individually —
        # a wrong "common" ruling would downcase a name on the next move.
        strong_proper = [w for w, (r, c) in suggestions.items()
                         if r == "proper" and c >= 0.99]
        if strong_proper and st.button(
            f"✓ Accept {len(strong_proper)} strong 'Proper' suggestion(s)",
            key="vocab_bulk_proper",
            help=", ".join(strong_proper[:12]) + ("…" if len(strong_proper) > 12 else ""),
        ):
            # Each ruling rewrites the vocabulary file, so accepting a
            # full queue takes ~20 s for ~1,000 words (measured).  Show
            # progress instead of a page that looks frozen.
            _prog = st.progress(0.0, text="Recording your rulings…")
            for _i, w in enumerate(strong_proper, 1):
                decide(lib, w, "proper")
                if _i % 25 == 0 or _i == len(strong_proper):
                    _prog.progress(
                        _i / len(strong_proper),
                        text=f"Recording your rulings… {_i}/{len(strong_proper)}")
            _prog.empty()
            st.toast(f"Ruled {len(strong_proper)} words Proper.")
            st.rerun()

        for word, info in items:
            # "Proper" vs "common" differed only by a capital letter, in two
            # adjacent 1/8-width buttons, for a decision that lowercases a
            # word across the whole library.  Widen them and say what they do.
            cols = st.columns([3, 2, 2, 2])
            sug = suggestions.get(word)
            badge = ""
            if sug:
                badge = f"  ·  model: **{sug[0]}** {sug[1]:.0%}"
            cols[0].markdown(
                f"**{word}**  ·  seen {info.get('count', 1)}×{badge}")
            cols[1].caption(info.get("example", "")[:70])
            if cols[2].button("Keep capital", key=f"vocab_p_{word}",
                              use_container_width=True,
                              help="A name, place or proper term — always "
                                   "keep it capitalised"):
                decide(lib, word, "proper")
                st.rerun()
            if cols[3].button("make lower case", key=f"vocab_c_{word}",
                              use_container_width=True,
                              help="Ordinary word — lowercase it mid-title"):
                decide(lib, word, "common")
                st.rerun()
        if len(pending) > 50:
            st.caption(f"…and {len(pending) - 50} more (highest-count 50 shown).")


def render_settings() -> None:
    """Form-driven editor for the watcher config + Unpaywall email."""
    from ui.cockpit_actions import (
        EDITABLE_CONFIG_KEYS,
        load_cockpit_config,
        save_cockpit_config,
    )

    _page_header(
        "⚙", "Settings",
        "How the cockpit names your files, watches your inbox, and signs in "
        "for paywalled downloads.",
        how_it_works=(
            "Four independent sections: **Title vocabulary** teaches the "
            "namer which capitalised words are real names; **Watcher "
            "settings** control the folder watched for new PDFs; the two "
            "sign-in sections store the access used to fetch paywalled "
            "papers; **Identity sidecars** are the small metadata files kept "
            "beside each PDF."
        ),
    )
    _render_title_vocabulary(_library())
    st.divider()
    st.subheader("Watcher settings")
    st.caption(
        "Saved to the watcher's configuration file.  `UNPAYWALL_EMAIL` is a "
        "machine-wide setting rather than part of that file, so the line "
        "needed to set it is shown for reference."
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

    # Browser-session import — the primary institutional-download method.
    # A fresh SAML login can't entitle several publishers (verified against
    # Springer); access lives in the persistent session cookies the user's
    # everyday browser already holds.  We borrow those cookies (one import
    # unlocks every publisher they have access to).  Names/domains are read
    # in the clear to locate the profile; decryption (one Keychain prompt)
    # only runs on Refresh.  Values are never displayed.
    st.subheader("🔗 Institutional access via your browser")
    st.caption(
        "Reuses the session your normal browser already established, so "
        "paywalled downloads work for **every publisher you have access to** "
        "— no per-publisher login. Cookies are read only for academic "
        "publishers, stored encrypted locally, and never shown."
    )
    st.warning(
        "⚠️ **Turn your VPN OFF** before downloading from Cloudflare-protected "
        "publishers (Wiley, SIAM, Elsevier, T&F, …). A VPN exit IP triggers a "
        "Cloudflare challenge that never clears. Springer / Sci-Hub are unaffected.",
        icon="🔌",
    )
    try:
        from downloader import browser_session as _bs
        _bs_ok = True
    except Exception as exc:  # pragma: no cover
        _bs_ok = False
        st.info(f"Browser import unavailable here: {exc}")
    if _bs_ok:
        if not _bs.is_supported():
            st.warning(
                "Not supported on this machine (needs macOS + Google Chrome "
                "+ the crypto library). The ETH login below is the fallback."
            )
        else:
            status = _bs.session_status()
            detected = status.get("detected_profiles", [])
            if detected:
                top = max(detected, key=lambda d: d["count"])
                st.caption(
                    f"Detected **{top['count']}** publisher cookies in Chrome "
                    f"profile `{top['profile']}` "
                    f"({len(top['domains'])} publisher domains)."
                )
            else:
                st.caption("No publisher cookies detected in any Chrome profile yet "
                           "— log into a journal in Chrome first.")
            if status.get("has_cache"):
                import datetime as _dt
                cap = status.get("cached_at")
                when = (_dt.datetime.fromtimestamp(cap).strftime("%Y-%m-%d %H:%M")
                        if cap else "?")
                msg = (f"✅ Session connected ({len(status.get('cached_domains', []))} "
                       f"publishers, captured {when}).")
                exp = status.get("earliest_expiry")
                if exp:
                    days = int((exp - time.time()) / 86400)
                    if days < 7:
                        msg += f" ⚠️ Some cookies expire in ~{max(days,0)} day(s) — refresh soon."
                st.success(msg)
            else:
                st.caption("⚠️ Not connected yet — click Refresh to import your "
                           "current browser access.")
            _c1, _c2 = st.columns(2)
            with _c1:
                if st.button("🔄 Refresh from Chrome", key="bs_refresh", type="primary"):
                    with st.spinner("Importing (approve the Keychain prompt)…"):
                        try:
                            r = _bs.refresh_from_browser()
                            st.success(f"Imported {r['count']} cookies from "
                                       f"`{r['profile']}` across {len(r['domains'])} "
                                       f"publishers.")
                            _log_activity("settings.browser_session", "", "refreshed")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Import failed: {exc}")
            with _c2:
                if status.get("has_cache") and st.button(
                    "Forget the imported session", key="bs_clear",
                    help="Deletes the stored publisher cookies. Not undoable "
                         "— you would press 'Refresh from Chrome' again."):
                    _bs.clear_cached()
                    _log_activity("settings.browser_session", "", "cleared")
                    st.rerun()

    st.divider()

    # ETH institutional credentials — stored in the local encrypted
    # credential store (Fernet, key in the OS keychain).  This is the
    # no-terminal way to provide ETH login for paywalled downloads; the
    # download chain reads eth_username/eth_password from this store.
    st.subheader("🔑 ETH institutional login (fallback)")
    try:
        from core.config.secure_config import get_secure_credential, get_config_manager
        _store_ok = True
    except Exception as exc:  # pragma: no cover
        _store_ok = False
        st.error(f"Credential store unavailable: {exc}")
    if _store_ok:
        _has_user = bool(get_secure_credential("eth_username"))
        _has_pwd = bool(get_secure_credential("eth_password"))
        st.caption(
            ("✅ Credentials stored." if (_has_user and _has_pwd)
             else "⚠️ Not set — paywalled downloads will skip the ETH "
                  "strategy.") +
            "  Stored encrypted locally; used only for institutional PDF access."
        )
        with st.form(key="eth_creds_form"):
            eth_user = st.text_input("ETH username (nethz)", value="",
                                     placeholder="(unchanged)" if _has_user else "")
            eth_pwd = st.text_input("ETH password", value="", type="password",
                                    placeholder="(unchanged)" if _has_pwd else "")
            csave = st.form_submit_button("Save credentials", type="primary")
        if csave:
            mgr = get_config_manager()
            saved = []
            if eth_user.strip():
                mgr.set_credential("eth_username", eth_user.strip()); saved.append("username")
            if eth_pwd:
                mgr.set_credential("eth_password", eth_pwd); saved.append("password")
            if saved:
                st.success(f"Saved ETH {', '.join(saved)} (encrypted).")
                _log_activity("settings.eth_creds", "", "stored")
                st.rerun()
            else:
                st.info("Nothing entered — existing credentials unchanged.")
        if (_has_user or _has_pwd) and st.button(
                "Clear ETH credentials", key="eth_clear",
                help="Deletes the stored username and password. This cannot "
                     "be undone — you would have to type them in again."):
            mgr = get_config_manager()
            mgr.credential_manager.delete_credential("eth_username")
            mgr.credential_manager.delete_credential("eth_password")
            _log_activity("settings.eth_creds", "", "cleared")
            st.rerun()

    st.divider()

    # Library-wide identity-sidecar tools.  Backfill is the
    # one-shot bootstrap for the existing 28k papers (Phase 2's state
    # machine has nothing to chew on until sidecars exist for the
    # corpus).  Verify runs drift_check against every PDF so the
    # user can catch Dropbox resync corruption.
    lib = _library()
    st.subheader("Saved paper details")
    st.caption(
        f"Library: `{lib}`.  Each PDF can have its title, authors and DOI "
        f"saved in a small companion file next to it — that is what search, "
        f"duplicate detection and the topic classifier actually read.  "
        f"**Fill in missing details** creates one for every PDF that has "
        f"none.  **Check they still match** re-reads each PDF and reports "
        f"any whose contents have changed since (a bad sync, for instance)."
    )
    bf_cols = st.columns([1, 1, 2])
    bf_limit = bf_cols[2].number_input(
        "Stop after this many files (0 = no limit)", min_value=0, value=0,
        key="bf_limit",
    )
    if bf_cols[0].button("Fill in missing details", key="bf_run",
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
    if bf_cols[1].button("Check they still match", key="bf_verify",
                         use_container_width=True):
        from processing.identity import verify_all_sidecars, list_hash_collisions
        with st.spinner("Re-reading every PDF (about 1 MB of each)..."):
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
            f"Checked {summary['scanned']} · "
            f"contents changed since last time {len(summary['drifted'])} · "
            f"no details saved yet {len(summary['missing_sidecar'])} · "
            f"could not be read {len(summary['errors'])}"
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
    # The list is cached now; without this the resolved conflicts would
    # keep showing until the TTL expired.
    _scan_conflicts_cached.clear()
    return n_ok, n_fail, errors


@st.cache_data(ttl=1800, show_spinner="Looking for Dropbox conflict copies (~9s)…")
def _conflicts_cached(lib_str: str) -> list:
    """Cached whole-library conflict scan (30-minute TTL).

    MEASURED 8.7s cold / 3.7s warm on the 29k library.  It used to run on
    page LOAD — meaning again on every checkbox tick and every button
    click on this page, so selecting five conflicts cost five extra
    library walks.  ``_clear_scan_caches`` invalidates it after any
    mutation, so the list can never go stale behind a resolution.
    """
    from processing.conflict_resolver import scan_conflicts
    return scan_conflicts(Path(lib_str))


@st.cache_data(ttl=1800, show_spinner="Looking for Dropbox conflict copies…")
def _scan_conflicts_cached(lib_str: str) -> list:
    """Cached ``scan_conflicts`` (30-min TTL).

    Measured at 7.1 s on the real library — and it ran on page LOAD and
    then again on every rerun, i.e. on every single button press, to
    display 1 conflict.  Resolution handlers clear this cache so the
    list never shows a conflict that has already been resolved.
    """
    from processing.conflict_resolver import scan_conflicts
    return scan_conflicts(Path(lib_str))


def render_conflicts() -> None:
    """Side-by-side conflict-copy resolver."""
    from processing.conflict_resolver import (
        resolve_keep_both,
        resolve_keep_canonical,
        resolve_keep_conflict,
    )
    from processing.undo_log import UndoLog

    st.header("🌪 Conflicts")
    st.caption(
        "When Dropbox cannot merge two versions of a file it quietly keeps "
        "both, naming one a 'conflicted copy'. They are shown here next to "
        "the original so you can keep the right one. Whatever you choose "
        "can be reversed from the Activity page."
    )

    lib = _library()
    # MEASURED: scan_conflicts() on a nonexistent path returns [], so this
    # page used to print "No conflict copies detected. ✓" for a library it
    # could not read at all.
    if not lib.exists():
        st.error(f"That library folder does not exist: `{lib}`")
        st.caption(
            "Set it in **📁 Library** at the top of the sidebar.  Until "
            "then this page cannot tell 'no conflicts' from 'cannot look'."
        )
        return
    if st.button("↻ Rescan for conflict copies", key="conf_rescan",
                 help="Walks the whole library (about 9 seconds).  The "
                      "result is kept for 30 minutes and refreshes itself "
                      "after every resolution, so you rarely need this."):
        _conflicts_cached.clear()
    conflicts = _conflicts_cached(str(lib))
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

    # The count that defines this page was the smallest, lowest-contrast
    # text on it.  Metrics here match Duplicates, which does the same job.
    _m1, _m2 = st.columns(2)
    _m1.metric("Conflict copies", len(conflicts))
    _m2.metric("Selected", len(selected))
    # Five columns stack into five full-width buttons in a narrow pane, three
    # of them permanently disabled -- ~330px of dead chrome above the first
    # conflict.  Show the selection controls always and the bulk actions only
    # once something is selected (the same _Null() pattern the Home snooze
    # bar uses), 2-up so nothing becomes a sliver between 640 and 1100px.
    _sel_cols = st.columns(2)
    _bulk_a = st.columns(2) if selected else [_Null(), _Null()]
    _bulk_b = st.columns(1) if selected else [_Null()]
    bar = [_sel_cols[0], _sel_cols[1], _bulk_a[0], _bulk_a[1], _bulk_b[0]]
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
        st.toast(f"Resolved {n_ok} conflict(s) the suggested way"
                 + (f", {n_fail} could not be done" if n_fail else "")
                 + " — undo from Activity.")
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
        st.toast(f"Kept the original for {n_ok} conflict(s)"
                 + (f", {n_fail} could not be done" if n_fail else "")
                 + " — undo from Activity.")
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
        st.toast(f"Kept the conflicted copy for {n_ok} conflict(s)"
                 + (f", {n_fail} could not be done" if n_fail else "")
                 + " — undo from Activity.")
        if errors:
            st.warning("Errors:\n  - " + "\n  - ".join(errors[:8]))
        st.session_state[sel_key] = set()
        _attention_count_cached.clear()
        st.rerun()

    if selected:
        _reversible_note(
            f"Each of the {len(selected)} selected conflicts is resolved by "
            "moving the losing file to the trash — the whole batch can be "
            "put back."
        )

    st.divider()

    for c in conflicts:
        with st.container(border=True):
            conflict_p = Path(c.conflict)
            canonical_p = Path(c.canonical) if c.canonical else None
            # Header row: checkbox + filename.  The checkbox key is
            # tied to the conflict path so toggles persist across
            # Streamlit reruns.
            # A [0.05, 0.95] split stacks below a 640px viewport, which left
            # an unlabelled checkbox floating on its own line above the name
            # it selects (screenshot-verified at 343px).  Using the filename
            # as the checkbox label keeps the two together at every width.
            checked = st.checkbox(
                f"**{conflict_p.name}**", value=c.conflict in selected,
                key=f"conf_sel_{c.conflict}",
            )
            if checked:
                selected.add(c.conflict)
            else:
                selected.discard(c.conflict)
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
                    _scan_conflicts_cached.clear()
                    _scan_conflicts_cached.clear()
                    st.rerun()
                else:
                    # No rerun on failure: it erased the reason and the
                    # button looked dead.  Persist any operations the
                    # resolver did record so they stay reversible.
                    if undo_log.has_operations():
                        undo_log.commit()
                    else:
                        undo_log.discard()
                    st.error(msg)

            # 4 equal columns squeeze "Keep both (rename -v2)" into ~70px
            # between 640px and ~1100px wide (measured on the equivalent Sort
            # Queue row: 71px, label broken mid-word).  2x2 keeps every label
            # readable and stacks identically below 640px.
            _reversible_note("Whichever you keep, the other file is moved to "
                             "the trash — never deleted.")
            _res1 = st.columns(2)
            _res2 = st.columns(2)
            act_cols = [_res1[0], _res1[1], _res2[0], _res2[1]]
            # A lone ⭐ is the only thing distinguishing the recommended
            # resolution from the other two, and it announces as nothing.
            kc_label = "Keep canonical" + (
                " ⭐ suggested" if suggested == "keep_canonical" else "")
            kf_label = "Keep conflict" + (
                " ⭐ suggested" if suggested == "keep_conflict" else "")
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


@st.cache_data(
    ttl=1800,
    show_spinner="Indexing your library — about 9 seconds, first search only…",
)
def _search_index_cached(lib_str: str) -> list:
    """One cached library walk backing the Search page (30-min TTL).

    MEASURED 8.9s for 29,393 filenames.  With ``show_spinner=False`` that
    was NINE SECONDS OF BLANK PAGE after pressing Enter — the clearest
    'this app is broken' signal in the cockpit.  The old 5-minute TTL
    also meant a working session paid the 9s over and over; the index is
    now invalidated by ``_clear_scan_caches`` whenever files actually
    move, which is the only thing that can change it."""
    from ui.search_page import build_index
    return build_index(Path(lib_str))


def render_search() -> None:
    """Instant search over the 29k canonical filenames + CSV/BibTeX export."""
    from ui.search_page import row_details, search_index, to_bibtex, to_csv

    st.header("🔎 Search")
    st.caption(
        "Type any mix of author names and title words — every word you type "
        "must appear. Capitals and accents don't matter (ekeland finds "
        "Ekéland). You can download the results as a spreadsheet (CSV) or "
        "as BibTeX entries for LaTeX."
    )
    lib = _library()
    query = st.text_input(
        "Search", key="search_query",
        placeholder="e.g.  possamai bsde   ·   mckean vlasov   ·   ekeland",
    )
    if not query or not query.strip():
        st.info("Type author names and/or title words.")
        return

    if not lib.exists():
        st.error(f"That library folder does not exist: `{lib}`")
        st.caption(
            "Set it in **📁 Library** at the top of the sidebar — every "
            "search will come back empty until then."
        )
        return
    try:
        index = _search_index_cached(str(lib))
    except Exception as exc:
        logger.exception("search index build failed")
        st.error(f"The list of your papers could not be built: {exc}")
        st.caption(
            "Nothing was changed.  If your library is on Dropbox, wait for "
            "it to finish syncing and search again."
        )
        return
    hits = search_index(index, query, limit=200)
    st.caption(f"{len(hits)} result(s)"
               + (" (first 200 shown — refine the query)" if len(hits) == 200 else ""))
    if not hits:
        st.info("Nothing in your library matches all of those words.")
        st.caption(
            "This searches the **file names** (authors and title), not the "
            "text inside the PDFs.  Try fewer words, or just the author's "
            "surname, or a different spelling.  A paper that only just "
            "arrived may still be waiting in the **Sort Queue** and have "
            "no proper name yet."
        )
        return

    # [8, 1] stacks below a 640px viewport, so each hit became three stacked
    # blocks plus a full-width button -- 60 hits is a ~7,000px page with the
    # export buttons stranded at the bottom.  Page it, and say what the
    # button does now that its label is no longer next to the name.
    if st.session_state.get("search_shown_q") != query:
        st.session_state["search_shown_q"] = query
        st.session_state["search_shown"] = 25
    _shown = st.session_state.get("search_shown", 25)
    for i, (name, rel) in enumerate(hits[:_shown]):
        st.markdown(f"**{name[:95]}**")
        st.caption(str(Path(rel).parent))
        if st.button("📁 Reveal in Finder", key=f"search_open_{i}",
                     use_container_width=True):
            import subprocess
            subprocess.run(["open", "-R", str(lib / rel)], check=False)
    if len(hits) > _shown:
        if st.button(f"Show 25 more  ({len(hits) - _shown} more)",
                     key="search_more", use_container_width=True):
            st.session_state["search_shown"] = _shown + 25
            st.rerun()
        st.caption("All results are included in the CSV / BibTeX exports below.")

    st.divider()
    rows = [row_details(name, rel, lib) for name, rel in hits]
    ecols = st.columns(2)
    ecols[0].download_button(
        "⬇ CSV", to_csv(rows), file_name="library_search.csv",
        mime="text/csv", use_container_width=True,
    )
    ecols[1].download_button(
        "⬇ BibTeX", to_bibtex(rows), file_name="library_search.bib",
        mime="text/plain", use_container_width=True,
    )


# ---------------------------------------------------------------------------
# "Not a duplicate" rulings — persisted next to the variant dismissals
# ---------------------------------------------------------------------------

def _dup_keepall_path(lib: Path) -> Path:
    return lib / ".mathpdf-config" / "duplicate_keep_all.json"


def _load_dup_keepall(lib: Path) -> set:
    """SHA-256s the user has ruled 'these are all worth keeping'."""
    try:
        return set(json.loads(
            _dup_keepall_path(lib).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError):
        return set()


def _dup_keepall(lib: Path, sha256: str) -> None:
    """Record a keep-all ruling so the group stops coming back.

    The variant reviewer already has this (``dismiss_pair``); the
    byte-identical reviewer did not, so all 55 "needs review" groups
    were re-offered after every rescan with no record of the ones the
    user had already looked at and decided to keep.  Nothing is moved
    or deleted — this only hides the group from the review list.
    """
    from core.io import atomic_write_text
    keep = _load_dup_keepall(lib)
    keep.add(sha256)
    p = _dup_keepall_path(lib)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(p, json.dumps(sorted(keep)))


def _dup_keepall_undo(lib: Path, sha256: str) -> None:
    from core.io import atomic_write_text
    keep = _load_dup_keepall(lib)
    keep.discard(sha256)
    p = _dup_keepall_path(lib)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(p, json.dumps(sorted(keep)))


# ---------------------------------------------------------------------------
# Scan snapshots — expensive read-only scans survive a browser reload
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Scan snapshots — expensive read-only scans survive a browser reload
# ---------------------------------------------------------------------------

def _scan_snapshot_path(name: str) -> Path:
    p = Path.home() / ".mathpdf" / "scans" / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _save_scan(name: str, payload) -> None:
    """Persist a scan result so a reload doesn't throw the work away.

    Measured cost of re-running these: duplicates ~16 s, same-paper
    variants 53–113 s, filename normalisation ~25 s.  Keeping them only
    in ``st.session_state`` meant every browser reload charged the user
    that again before they could continue reviewing.
    """
    try:
        p = _scan_snapshot_path(name)
        tmp = p.parent / (p.name + ".tmp")
        tmp.write_text(
            json.dumps({"saved_at": time.time(), "payload": payload},
                       ensure_ascii=False),
            encoding="utf-8")
        tmp.replace(p)
    except (OSError, TypeError) as exc:
        logger.warning("Could not save %s scan snapshot: %s", name, exc)


def _load_scan(name: str, max_age_h: float = 24.0):
    """Return ``(payload, age_in_hours)``; ``(None, age)`` if absent/stale."""
    try:
        blob = json.loads(
            _scan_snapshot_path(name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None, 0.0
    try:
        age_h = (time.time() - float(blob.get("saved_at", 0))) / 3600.0
    except (TypeError, ValueError):
        return None, 0.0
    if age_h > max_age_h:
        return None, age_h
    return blob.get("payload"), age_h


def _dup_rel(path: str, lib: Path) -> str:
    """Library-relative display path; falls back to the raw string."""
    try:
        return str(Path(path).relative_to(lib))
    except (ValueError, RuntimeError):
        return path


@st.cache_data(ttl=600, show_spinner=False)
def _variant_compare_cached(pre_rel: str, pub_rel: str, lib_str: str) -> dict:
    """Cached page/byte comparison for ONE variant pair.

    ``compare_pair`` opens both PDFs with PyMuPDF (MEASURED 5ms each on
    this Dropbox-backed library).  It ran for all 40 rendered pairs on
    every rerun — 0.44s of pure re-work each time the owner touched a
    radio button while reviewing the pile.
    """
    from processing.preprint_variants import VariantPair, compare_pair
    return compare_pair(
        VariantPair(preprint=pre_rel, published=pub_rel, tier=""),
        Path(lib_str),
    )


def _render_variant_section(lib: Path) -> None:
    """Preprint ↔ published variants: same paper, different bytes.

    Content-hash dedup is blind to these (the PDFs differ); identity
    comes from DOI / arXiv-id matches (mined into sidecars from the
    cached first-pages text) plus an author+title/abstract fuzzy tier.
    Retiring a preprint is review-gated and reversible; the library
    policy is "retire unless it's an extended version", so both sides'
    page counts are shown.
    """
    from processing.preprint_variants import (
        VariantPair,
        backfill_identifiers,
        compare_pair,
        dismiss_pair,
        find_variant_pairs,
        load_dismissals,
        retire_variant,
    )
    from processing.undo_log import UndoLog

    st.divider()
    st.subheader("🔁 Same-paper variants (different bytes)")
    st.caption(
        "The same paper filed twice with DIFFERENT bytes — a preprint vs "
        "its published version, or near-duplicate re-filings the byte-hash "
        "dedup can't catch (ü/ue, author order, dashes, corrigenda).  "
        "Matched by DOI / arXiv id (author-confirmed), then a fuzzy "
        "author+title/abstract tier.  Pick which copy to keep; the other "
        "moves to `.trash/` (reversible).  Keep both if it's an extended "
        "version or genuinely distinct."
    )
    bcols = st.columns([1, 1, 3])
    if bcols[0].button("🔍 Scan for variants", key="var_scan"):
        with st.spinner("Mining identifiers + matching…"):
            bf = backfill_identifiers(lib)
            pairs = find_variant_pairs(lib)
        st.session_state["variant_pairs"] = [p.to_dict() for p in pairs]
        st.session_state["var_shown"] = 20
        _save_scan("variants", st.session_state["variant_pairs"])
        st.toast(f"IDs mined: +{bf['doi_added']} DOI, "
                 f"+{bf['arxiv_added']} arXiv · {len(pairs)} pair(s)")

    raw = st.session_state.get("variant_pairs")
    if raw is None:
        # This scan measures 53–113 s.  Losing it to a browser reload
        # meant the user had to pay it again before reviewing pair 21.
        raw, _age_h = _load_scan("variants")
        if raw is not None:
            st.session_state["variant_pairs"] = raw
            st.caption(
                f"Showing your last scan, from {_age_h:.1f} h ago — pick up "
                "where you left off, or rescan for fresh results."
            )
    if raw is None:
        st.info("Click **Scan for variants** to analyse the library.")
        return
    dismissed = load_dismissals(lib)
    pairs = [VariantPair(**d) for d in raw]
    pairs = [p for p in pairs if p.key() not in dismissed]
    if not pairs:
        st.success("No unreviewed preprint↔published variants. ✓")
        return
    st.caption(f"{len(pairs)} pair(s) awaiting review "
               f"({len(dismissed)} previously kept-both).")

    shown = st.session_state.setdefault("var_shown", 20)
    for p in pairs[:shown]:
        # Widget keys are derived from the PAIR, not its position in the
        # list.  With index keys, retiring pair #3 shifted every pair
        # below it up one slot while Streamlit kept the stored radio
        # value under the old index — so the "keep which copy?" choice
        # shown for a pair could belong to a different pair entirely.
        pk = p.key()
        with st.container(border=True):
            ev = ", ".join(f"{k}={v}" for k, v in p.evidence.items())
            st.markdown(f"**{p.tier.upper()} match**  ·  {ev}")
            cmp = _variant_compare_cached(p.preprint, p.published, str(lib))
            pre_i, pub_i = cmp["preprint"], cmp["published"]
            st.markdown(f"📄 preprint: `{p.preprint}`")
            st.caption(f"    {pre_i['pages'] or '?'} pages · "
                       f"{pre_i['bytes'] // 1024} KB")
            st.markdown(f"📗 published: `{p.published}`")
            st.caption(f"    {pub_i['pages'] or '?'} pages · "
                       f"{pub_i['bytes'] // 1024} KB")
            if (pre_i["pages"] and pub_i["pages"]
                    and abs(pre_i["pages"] - pub_i["pages"]) >= 3):
                st.warning("Notably different page counts — possibly an "
                           "extended version; consider Keep both.")
            # Default to keeping the published side when the pair is
            # cross-status; otherwise the (deeper-pathed) first side.
            options = [p.published, p.preprint]
            keep = st.radio(
                "Keep which copy?", options,
                format_func=lambda r: _dup_rel(r, lib),
                key=f"var_keep_which_{pk}",
            )
            acols = st.columns([2, 1, 1])
            if acols[0].button("🗑 Retire the other (reversible)",
                               key=f"var_retire_{pk}", type="primary"):
                drop = p.preprint if keep == p.published else p.published
                log = UndoLog(log_dir=lib / ".operation_log")
                tx = log.begin_transaction(
                    f"retire variant: {Path(drop).name}")
                ok, msg = retire_variant(p, lib, drop=drop, undo_log=log)
                if log.has_operations():
                    log.commit()
                else:
                    log.discard()
                if ok:
                    _log_activity("variant.retire", drop, keep, tx)
                    st.toast(msg)
                else:
                    st.warning(msg)
                st.session_state["variant_pairs"] = [
                    q.to_dict() for q in pairs if q.key() != p.key()]
                _save_scan("variants", st.session_state["variant_pairs"])
                st.rerun()
            if acols[1].button("Keep both", key=f"var_keepboth_{pk}",
                               help="Extended version / genuinely distinct — "
                                    "won't be shown again"):
                dismiss_pair(lib, p)
                st.rerun()
            if acols[2].button("Open both", key=f"var_open_{pk}"):
                import subprocess
                for rel in (p.preprint, p.published):
                    if (lib / rel).exists():
                        subprocess.run(["open", str(lib / rel)],
                                       capture_output=True)
    remaining = len(pairs) - min(shown, len(pairs))
    if remaining > 0:
        st.caption("Strongest evidence first.")
        if st.button(f"Show 20 more  ({remaining} still hidden)",
                     key="var_show_more", use_container_width=True):
            st.session_state["var_shown"] = shown + 20
            st.rerun()


def render_duplicates() -> None:
    """Whole-library exact-duplicate detection + reversible resolution.

    Detection is byte-identical (size prefilter -> full-file SHA-256), so
    there are no false positives.  Auto-safe groups (a paper filed twice
    under near-identical names, a staging leftover, or a status+topic
    pair) can be cleaned in one reversible batch; everything needing a
    judgment call (curated collections, different homes, or a
    byte-identical copy under a *different* title — a possible mis-file)
    is shown for manual review.
    """
    from processing.duplicate_scan import (
        apply_duplicate_resolutions,
        find_exact_duplicates,
        resolve_group,
        DuplicateGroup,
    )
    from processing.undo_log import UndoLog

    st.header("👯 Duplicates")
    st.caption(
        "Identical copies of the same PDF, anywhere in the library — "
        "compared byte for byte, so there are no false alarms. Extra "
        "copies are moved to the trash, never deleted, and can be put "
        "back from the Activity page."
    )

    lib = _library()

    # Scanning hashes every size-collision candidate (~16 s measured on
    # the 29k library), so it's gated behind a button.  The result is
    # ALSO written to disk: a browser reload used to discard it and make
    # the user pay the whole scan again before they could carry on.
    if st.button("🔍 Scan for duplicates", key="dup_scan"):
        with st.spinner("Hashing duplicate candidates…"):
            groups = find_exact_duplicates(lib)
        st.session_state["dup_groups"] = [g.to_dict() for g in groups]
        _save_scan("duplicates", st.session_state["dup_groups"])
        st.session_state.pop("dup_excluded", None)

    raw = st.session_state.get("dup_groups")
    if raw is None:
        raw, _age_h = _load_scan("duplicates")
        if raw is not None:
            st.session_state["dup_groups"] = raw
            st.caption(
                f"Showing your last scan, from {_age_h:.1f} h ago — pick up "
                "where you left off, or rescan for fresh results."
            )
    if raw is None:
        st.info("Click **Scan for duplicates** to analyse the library.")
        return

    groups = [DuplicateGroup(**d) for d in raw]
    if not groups:
        st.success("No byte-identical duplicates found. ✓")
        return

    auto = [g for g in groups if g.auto_safe]
    # Groups the user has already ruled on ("keep all") stay out of the
    # review pile permanently, so a rescan resumes instead of restarting.
    _kept_all = _load_dup_keepall(lib)
    review = [g for g in groups
              if not g.auto_safe and g.sha256 not in _kept_all]
    auto_copies = sum(len(g.remove) for g in auto)

    c1, c2, c3 = st.columns(3)
    c1.metric("Duplicate groups", len(groups))
    c2.metric("Auto-safe copies", auto_copies)
    c3.metric("Need review", len(review))
    if _kept_all:
        with st.expander(f"✓ {len(_kept_all)} group(s) you ruled "
                         f"'keep all' — bring one back"):
            st.caption("Ruling 'keep all' never moved anything; it only "
                       "hides the group here.")
            for _sha in sorted(_kept_all):
                if st.button(f"Un-hide {_sha[:12]}…", key=f"dup_unhide_{_sha}"):
                    _dup_keepall_undo(lib, _sha)
                    st.rerun()

    if not auto and not review:
        st.success(
            f"Nothing to do here — all {len(groups)} duplicate group(s) "
            f"from this scan have been resolved or ruled 'keep all'."
        )
        st.caption(
            "Use the list above to bring a ruling back, or press "
            "**🔍 Scan for duplicates** for a fresh look at the library."
        )
        return

    # ----- Auto-safe batch -------------------------------------------------
    if auto:
        st.subheader(f"Auto-safe · {len(auto)} groups, {auto_copies} redundant copies")
        st.caption(
            "These are byte-identical with near-identical names (typo / "
            "punctuation / extra initial) or staging leftovers.  Keeping one "
            "copy is loss-free."
        )
        excl_key = "dup_excluded"
        excluded: set = st.session_state.setdefault(excl_key, set())
        excluded &= {g.keep for g in auto}        # prune stale

        with st.expander("Review the auto-safe list (untick to skip a group)",
                         expanded=len(auto) <= 30):
            for g in auto:
                keep_box = st.checkbox(
                    f"KEEP  {_dup_rel(g.keep, lib)}",
                    value=g.keep not in excluded,
                    key=f"dup_auto_{g.sha256[:12]}",
                )
                if keep_box:
                    excluded.discard(g.keep)
                else:
                    excluded.add(g.keep)
                for r in g.remove:
                    # The files that are about to MOVE were the lowest-
                    # contrast text on the page, marked with a bare ✗.
                    st.markdown(
                        f"&nbsp;&nbsp;✗ Will be trashed: "
                        f"`{_dup_rel(r, lib)}`  ·  _{g.reason}_"
                    )

        _reversible_note("The extra copies move into the library's trash "
                         "folder; the one marked KEEP does not move.")
        act = len([g for g in auto if g.keep not in excluded])
        if st.button(
            f"🗑 Trash redundant copies for {act} group(s) (reversible)",
            key="dup_apply_auto",
            type="primary",
            disabled=act == 0,
        ):
            res = apply_duplicate_resolutions(
                lib, groups=auto, dry_run=False, auto_only=False,
                exclude=set(excluded),
            )
            _log_activity(
                "duplicates.bulk_trash", "",
                f"removed={res['removed']} failed={len(res['failed'])}",
                res.get("tx_id") or "",
            )
            st.toast(f"Trashed {res['removed']} copies "
                     f"(failed {len(res['failed'])})")
            if res["failed"]:
                st.warning("Some failed:\n  - " + "\n  - ".join(
                    f"{_dup_rel(f['keep'], lib)}: {f['msg']}"
                    for f in res["failed"][:8]))
            # Re-scan so the list reflects reality.
            st.session_state["dup_groups"] = [
                gg.to_dict() for gg in find_exact_duplicates(lib)
            ]
            _save_scan("duplicates", st.session_state["dup_groups"])
            st.session_state.pop(excl_key, None)
            _attention_count_cached.clear()
            st.rerun()

    # ----- Review (manual) -------------------------------------------------
    if review:
        st.divider()
        st.subheader(f"Needs review · {len(review)} groups")
        st.caption(
            "Each of these needs a human call.  Pick the copy to keep and "
            "trash the rest — or leave it.  Curated-collection copies "
            "(08/09/10/archive) are never removed automatically."
        )
        for g in review:
            with st.container(border=True):
                st.markdown(f"**{g.kind}** · {' · '.join(g.notes)}")
                # Let the user choose the keeper among all paths.
                options = list(g.paths)
                labels = {p: _dup_rel(p, lib) for p in options}
                choice = st.radio(
                    "Keep which copy?",
                    options,
                    format_func=lambda p: labels[p],
                    key=f"dup_rev_keep_{g.sha256[:12]}",
                )
                _reversible_note("The copies you don't keep move to the "
                                 "trash — nothing is deleted.")
                cols = st.columns(len(options) + 2)
                for i, p in enumerate(options):
                    if cols[i].button("Open", key=f"dup_rev_open_{g.sha256[:12]}_{i}"):
                        import subprocess as _sp
                        if Path(p).exists():
                            _sp.run(["open", str(Path(p))], capture_output=True)
                # Recording "these are both worth keeping" is a decision
                # too; without it the group came back on every rescan.
                if cols[-2].button(
                    "Keep all (not a duplicate)",
                    key=f"dup_rev_keepall_{g.sha256[:12]}",
                    help="Nothing is moved — this group stops appearing here.",
                ):
                    _dup_keepall(lib, g.sha256)
                    st.toast("Noted — kept all copies.")
                    st.rerun()
                if cols[-1].button(
                    "Trash the others",
                    key=f"dup_rev_apply_{g.sha256[:12]}",
                    type="primary",
                ):
                    manual = DuplicateGroup(
                        sha256=g.sha256, size=g.size, paths=g.paths,
                        keep=choice,
                        remove=[p for p in g.paths if p != choice],
                        kind=g.kind, reason="manual review choice",
                        auto_safe=False, notes=g.notes,
                    )
                    log = UndoLog(log_dir=lib / ".operation_log")
                    tx = log.begin_transaction(
                        f"dedup (manual): keep {Path(choice).name}")
                    results = resolve_group(manual, lib, undo_log=log)
                    log.commit()
                    ok = sum(1 for r, _ in results if r)
                    _log_activity("duplicates.manual_trash", "",
                                  f"removed={ok}", tx)
                    st.toast(f"Trashed {ok} copy/copies (reversible)")
                    st.session_state["dup_groups"] = [
                        gg.to_dict() for gg in find_exact_duplicates(lib)
                    ]
                    _attention_count_cached.clear()
                    st.rerun()


def _page_chrome() -> None:
    """Global accessibility chrome: caption contrast + a skip link.

    Streamlit renders ``st.caption`` as body text at 60% alpha
    (``fadedText60``), which measures 3.73:1 on the light theme -- below
    the WCAG AA 4.5:1 floor for normal-size text.  This cockpit uses
    caption 65 times, and much of it is load-bearing: the file sizes a
    Conflicts decision rests on, the paths about to be trashed on
    Duplicates, result counts.  85% alpha measures ~6.7:1 and still
    reads as clearly secondary.

    The skip link exists because Streamlit emits the sidebar before the
    main block, so a keyboard user tabs through the 12 nav buttons
    before reaching page content -- on every page, and again after every
    ``st.rerun()``, which this app calls after nearly every action.
    """
    st.markdown(
        """
        <style>
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p {
            color: var(--text-color, currentColor);
            color: color-mix(in srgb,
                             var(--text-color, currentColor) 85%, transparent);
        }
        a.cockpit-skip {
            position: absolute; left: -9999px; top: 0;
            padding: 0.4rem 0.7rem;
            border: 2px solid currentColor; border-radius: 6px;
            background: var(--background-color, #fff);
            color: var(--text-color, currentColor);
            text-decoration: none; font-weight: 600; z-index: 9999;
        }
        a.cockpit-skip:focus {
            position: static; display: inline-block; left: auto;
        }
        </style>
        <div id="main-content"></div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<a class="cockpit-skip" href="#main-content">Skip to page content</a>',
        unsafe_allow_html=True,
    )


def main() -> None:
    _init_state()
    # Emitted first so the #main-content anchor is the first node of the
    # main block and the skip link is the first node of the sidebar.
    _page_chrome()
    render_sidebar()

    # Must match the sidebar's own default: they disagreed ("Sort Queue"
    # here vs "Attention" there) and only worked by accident, because
    # render_sidebar runs first and seeds session_state.
    page = st.session_state.get("page", "Attention")
    if page == "Attention":
        render_attention()
    elif page == "Search":
        render_search()
    elif page == "Sort Queue":
        render_sort_queue()
    elif page == "Upgrade Queue":
        render_upgrade_queue()
    elif page == "To Download":
        render_to_download()
    elif page == "Conflicts":
        render_conflicts()
    elif page == "Duplicates":
        render_duplicates()
        # Variants are the "same paper, different bytes" sibling of the
        # byte-identical dedup above — rendered even when the dedup scan
        # finds nothing (render_duplicates may early-return).
        _render_variant_section(_library())
    elif page == "Maintenance":
        render_maintenance()
    elif page == "Pipeline Preview":
        render_pipeline_preview()
    elif page == "Spelling":
        render_spelling()
    elif page == "Conformance":
        render_conformance()
    elif page == "Stats":
        render_stats()
    elif page == "Activity":
        render_activity()
    elif page == "Settings":
        render_settings()


main()
