"""Every cockpit page must render SUBSTANCE, not merely fail to crash.

WHY THIS FILE EXISTS
--------------------
``tests/ui/test_cockpit_smoke.py`` drives each ``render_*`` function with
a stub streamlit and asserts only that nothing raises.  Measured against
that suite, all 14 render functions can be reduced to a bare ``return``
and 136/136 UI tests still pass: an EMPTY PAGE is indistinguishable from
a working one.  This is the owner's only interface to 29,000 files, so
"the function did not raise" is not evidence that he can see his library.

The harness here follows the smoke file's approach (stub ``streamlit``
before importing ``ui.cockpit``) but the stub RECORDS every call, so a
test can ask the only question that matters: for a library with known
contents, did the page actually put the owner's numbers and filenames on
the screen?

Each test below is a POSTCONDITION on the rendered page, not a path
assertion.  Every one of them has been shown failing against a
``return``-only version of the function it protects (see the module
docstring block at the bottom for the mutation matrix).

NOTHING in this file writes to the real library or to ``~/.mathpdf``:
``HOME`` is redirected to a tmp dir for the whole fixture, and every
library used is a synthetic ``tmp_path``.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Recording streamlit stub
# ---------------------------------------------------------------------------

_BOOL_WIDGETS = {"button", "checkbox", "toggle", "form_submit_button",
                 "download_button", "link_button"}
_TEXT_WIDGETS = {"text_input", "text_area"}
_NUM_WIDGETS = {"number_input"}
_CHOICE_WIDGETS = {"selectbox", "radio"}


class _SessionState(dict):
    """``streamlit.session_state`` supports attribute and item access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


def _pick(values: dict, args: tuple, kwargs: dict, default):
    """Return a caller-supplied widget value, keyed by widget key or label."""
    for cand in (kwargs.get("key"),
                 args[0] if args and isinstance(args[0], str) else None):
        if cand is not None and cand in values:
            return values[cand]
    return default


def _dispatch(name: str, log: list, values: dict):
    """Build the callable that stands in for ``st.<name>``."""

    def _call(*args, **kwargs):
        log.append((name, args, kwargs))
        if name == "columns":
            spec = args[0] if args else 1
            n = spec if isinstance(spec, int) else len(spec)
            return [_Rec(log, values) for _ in range(n)]
        if name == "tabs":
            labels = args[0] if args else []
            return [_Rec(log, values) for _ in labels]
        if name in _BOOL_WIDGETS:
            return bool(_pick(values, args, kwargs, False))
        if name in _TEXT_WIDGETS:
            return _pick(values, args, kwargs, "")
        if name in _NUM_WIDGETS:
            return _pick(values, args, kwargs, 0)
        if name == "slider":
            # Real streamlit returns the default; the cockpit already
            # coerces None -> its own default, which the smoke stub relies
            # on.  Keep that behaviour so we test the same code path.
            return _pick(values, args, kwargs, None)
        if name in _CHOICE_WIDGETS:
            opts = kwargs.get("options")
            if opts is None and len(args) > 1:
                opts = args[1]
            default = opts[0] if opts else None
            return _pick(values, args, kwargs, default)
        if name == "multiselect":
            return _pick(values, args, kwargs, [])
        if name == "file_uploader":
            # Real streamlit returns a LIST when accept_multiple_files=True
            # and None otherwise -- never a generic object. Returning the
            # catch-all recorder made `len(uploads)` raise TypeError, which
            # is a defect in the double, not in the page.
            if kwargs.get("accept_multiple_files") or (
                    len(args) > 1 and args[1] is True):
                return _pick(values, args, kwargs, [])
            return _pick(values, args, kwargs, None)
        return _Rec(log, values)

    return _call


class _Rec:
    """A recording stand-in for a column / container / expander / bar.

    Callable, iterable and a context manager, so ``st.columns(2)[0]``,
    ``with st.container(border=True):`` and ``slot.progress(0.0)`` all
    behave — and every call lands in the shared log.
    """

    def __init__(self, log: list, values: dict):
        self._log = log
        self._values = values

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter([])

    def __call__(self, *a, **kw):
        self._log.append(("<call>", a, kw))
        return _Rec(self._log, self._values)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _dispatch(name, self._log, self._values)


class _RecStreamlit(types.ModuleType):
    """Module-shaped recording stub installed as ``sys.modules['streamlit']``."""

    def __init__(self, log: list, values: dict):
        super().__init__("streamlit")
        self.session_state = _SessionState()
        self.calls = log
        self.values = values

    def cache_data(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            fn = args[0]
            fn.clear = lambda: None
            return fn

        def _wrap(fn):
            fn.clear = lambda: None
            return fn
        return _wrap

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name == "sidebar":
            # Used both as ``with st.sidebar:`` and ``st.sidebar.title(...)``.
            return _Rec(self.calls, self.values)
        if name == "rerun":
            return lambda *a, **kw: None
        return _dispatch(name, self.calls, self.values)


# ---------------------------------------------------------------------------
# What the page put on screen
# ---------------------------------------------------------------------------

def _values_of(name: str, args: tuple, kwargs: dict):
    """The parts of one recorded call that the owner actually SEES.

    ``st.download_button("⬇ CSV", to_csv(rows), ...)`` carries the whole
    result set as its second argument — a file he has to download and
    open elsewhere.  Counting that as "on screen" made a Search page that
    listed NO results still look like it had rendered them (verified: the
    ``hits[:0]`` mutant survived until this exclusion was added).
    """
    vals = list(args) + list(kwargs.values())
    if name == "download_button" and len(args) > 1:
        vals = [args[0]] + list(args[2:]) + [
            v for k, v in kwargs.items() if k != "data"]
    return vals


def rendered_text(st_stub) -> str:
    """Every string and number the page put on screen, joined into one blob.

    Deliberately generous about WHICH element carried a value (label,
    value, help text, caption): the claim under test is that the owner
    can SEE the number, not that it went through a particular widget.
    Use :func:`metrics` when the pairing of a label with its value is the
    thing that matters.
    """
    out: list[str] = []
    for name, args, kwargs in st_stub.calls:
        for v in _values_of(name, args, kwargs):
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, bool):
                continue
            elif isinstance(v, (int, float)):
                out.append(f"{v}")
    return "\n".join(out)


def text_of(st_stub, *names: str) -> str:
    """Only what the named kinds of element rendered (e.g. subheaders)."""
    out: list[str] = []
    for name, args, kwargs in st_stub.calls:
        if name not in names:
            continue
        for v in _values_of(name, args, kwargs):
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, bool):
                continue
            elif isinstance(v, (int, float)):
                out.append(f"{v}")
    return "\n".join(out)


def metrics(st_stub) -> dict:
    """``{metric label: value}`` for every ``st.metric`` the page drew.

    A blob search cannot tell "3 conflict copies" from the ``3`` inside a
    conflicted-copy datestamp; this can.
    """
    out: dict = {}
    for name, args, kwargs in st_stub.calls:
        if name != "metric":
            continue
        label = args[0] if args else kwargs.get("label")
        value = args[1] if len(args) > 1 else kwargs.get("value")
        out[label] = value
    return out


def assert_metric(st_stub, label: str, expected) -> None:
    """The metric ``label`` was drawn AND carries ``expected``."""
    got = metrics(st_stub)
    assert label in got, (
        f"the page never drew a metric labelled {label!r}; it drew "
        f"{sorted(k for k in got if isinstance(k, str))}")
    accepted = {expected, str(expected)}
    if isinstance(expected, int) and not isinstance(expected, bool):
        accepted.add(f"{expected:,}")
    assert got[label] in accepted, (
        f"metric {label!r} showed {got[label]!r}, expected one of {accepted!r}")


def shows_number(text: str, n: int) -> bool:
    """True if ``n`` appears the way a page would print it (7 or 1,234)."""
    return f"{n:,}" in text or str(n) in text


def assert_shows(text: str, needle, what: str = "") -> None:
    if isinstance(needle, int) and not isinstance(needle, bool):
        assert shows_number(text, needle), (
            f"page never showed the number {needle}"
            + (f" ({what})" if what else "")
            + f"\n--- rendered page ---\n{text[:3000]}"
        )
    else:
        assert needle in text, (
            f"page never showed {needle!r}"
            + (f" ({what})" if what else "")
            + f"\n--- rendered page ---\n{text[:3000]}"
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def home(tmp_path, monkeypatch):
    """Redirect ``$HOME`` so nothing can reach the owner's ~/.mathpdf.

    ``_activity_log_path``/``_load_skips``/``_scan_snapshot_path`` and
    ``attention_queue.DISMISSALS_PATH`` are all ``Path.home()``-derived;
    the suite has already written 475 junk rows into the real
    ``~/.mathpdf/cockpit_activity.jsonl`` and must never do it again.
    """
    h = tmp_path / "home"
    h.mkdir()
    monkeypatch.setenv("HOME", str(h))
    return h


@pytest.fixture
def lib(tmp_path):
    """A synthetic library root, never the real one."""
    p = tmp_path / "Maths"
    p.mkdir()
    return p


@pytest.fixture
def cockpit(monkeypatch, home, lib):
    """Import ``ui.cockpit`` under the recording stub.

    Returns the module; ``cockpit.st`` is the stub, ``cockpit.st.calls``
    is the recording, and ``cockpit.st.values`` lets a test supply widget
    return values keyed by widget key (or by label when there is no key).
    """
    log: list = []
    values: dict = {}
    stub = _RecStreamlit(log, values)
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    monkeypatch.setenv("MATH_LIBRARY", str(lib))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as _cockpit
    # cockpit runs main() at import; that render is not under test.  It
    # also warms the attention cache (which lives in session_state, not
    # in st.cache_data) against the still-empty library — drop it, or a
    # test that seeds files afterwards is scored against the empty scan.
    _cockpit.st.session_state["library_root"] = str(lib)
    _cockpit.st.session_state.pop("_attn_cache", None)
    log.clear()
    return _cockpit


def _pdf(path: Path, body: bytes = b"%PDF-1.4\n%%EOF\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


# ---------------------------------------------------------------------------
# 1. Conformance
# ---------------------------------------------------------------------------

def _conformance_report(**over):
    from maintenance import conformance as C
    kw = dict(
        generated_at="2026-08-20T10:00:00",
        duration_s=61.5,
        scanned=29393,
        counts={C.CANONICAL: 21001, C.OWNER_QUEUE: 5011,
                C.MECHANICAL: 2300, C.NOT_EXAMINED: 977,
                C.VIOLATION: 104},
        reasons={f"{C.NOT_EXAMINED}:no-rule-reached-a-verdict": 977,
                 f"{C.VIOLATION}:postcondition-failed": 104},
        findings=[C.Finding(path="07a - BSDEs/X - y.pdf",
                            bucket=C.NOT_EXAMINED,
                            reason="no-rule-reached-a-verdict",
                            detail="separator ambiguous")],
        globals_={"documents_out_of_scope": 88, "inbox_skipped": 1861,
                  "coverage_pct": 74},
    )
    kw.update(over)
    return C.ConformanceReport(**kw)


def test_conformance_shows_every_bucket_count(cockpit):
    """The five bucket counts are the whole point of the page."""
    cockpit.st.session_state["conformance_report"] = _conformance_report()
    cockpit.render_conformance()
    # Each bucket by name, with its own number: the page's whole job is
    # to separate work the OWNER owes from work the CODE owes.
    assert_metric(cockpit.st, "Awaiting your ruling", 5011)
    assert_metric(cockpit.st, "Mechanical, not yet applied", 2300)
    assert_metric(cockpit.st, "Never examined", 977)
    assert_metric(cockpit.st, "Invariant violations", 104)
    assert_metric(cockpit.st, "Canonical", 21001)
    text = rendered_text(cockpit.st)
    assert_shows(text, 29393, "how many files were examined at all")
    assert_shows(text, "1,081", "the red count the page must not hide")


def test_conformance_never_shows_all_clear_when_nothing_was_scanned(cockpit):
    """Zero scanned is "I could not look", not "everything is fine".

    This is the exact lie the page was written to kill, and a
    ``return``-only render passes any test that merely checks the banner
    is absent — so the test also demands the page SAY so.
    """
    cockpit.st.session_state["conformance_report"] = _conformance_report(
        scanned=0,
        counts={"canonical": 0, "owner_queue": 0, "mechanical_backlog": 0,
                "not_examined": 0, "invariant_violation": 0},
        reasons={},
        findings=[],
        globals_={},
    )
    cockpit.render_conformance()
    text = rendered_text(cockpit.st)
    assert "Every file reached a verdict" not in text, (
        "the all-clear banner was shown for a scan that examined nothing")
    assert_shows(text, "No documents were examined",
                 "the page must say it could not look")
    # And the error must be routed to st.error, not buried in a caption.
    assert any(name == "error" and args and "No documents were examined" in args[0]
               for name, args, _ in cockpit.st.calls), \
        "the 'nothing examined' warning was not raised as an error"


def test_conformance_all_clear_only_when_it_really_is(cockpit):
    cockpit.st.session_state["conformance_report"] = _conformance_report(
        scanned=1200,
        counts={"canonical": 1200, "owner_queue": 0, "mechanical_backlog": 0,
                "not_examined": 0, "invariant_violation": 0},
        reasons={}, findings=[], globals_={},
    )
    cockpit.render_conformance()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Every file reached a verdict")
    assert_shows(text, 1200, "scanned count")


# ---------------------------------------------------------------------------
# 2. Stats
# ---------------------------------------------------------------------------

def test_stats_shows_the_count_of_every_status_folder(cockpit, lib, monkeypatch):
    """Known contents -> the page must print those exact counts."""
    counts = {
        "01 - Published papers": 7,
        "02 - Unpublished papers": 3,
        "03 - Working papers": 11,
        "04 - Papers to be downloaded": 1,
        "05 - Books and lecture notes": 5,
        "06 - Theses": 2,
    }
    for folder, n in counts.items():
        for i in range(n):
            _pdf(lib / folder / f"A - paper {i}.pdf")
    _pdf(lib / "12 - To be sorted" / "03 - Working papers" / "drop.pdf")

    monkeypatch.setattr(
        cockpit, "_library_health_cached",
        _fake_cached({"sidecar_coverage": 0.42, "sidecars": 12, "pdfs": 29,
                      "vocab_pending": 63, "vocab_ruled": 400,
                      "undo_transactions": 17, "last_tx_age_days": 2,
                      "trash_pdfs": 9, "model_trained_on": 0,
                      "model_accuracy": 0.0, "model_age_days": 0,
                      "corpus_stats_age_days": -1}))

    cockpit.render_stats()
    text = rendered_text(cockpit.st)
    for folder, n in counts.items():
        label = folder.split(" - ")[1]
        # The label and its number must arrive together: a list of six
        # folder names with no counts is not this page.
        assert f"**{n:,}** &nbsp; {label}" in text, (
            f"'{label}' was not shown with its count {n}"
            f"\n--- rendered page ---\n{text[:3000]}")
    # The health strip's numbers are the other half of this page.
    assert_metric(cockpit.st, "Words awaiting your ruling", 63)
    assert_metric(cockpit.st, "Changes you can still undo", 17)
    assert_metric(cockpit.st, "Files in the trash", 9)
    assert_metric(cockpit.st, "Waiting", 1)          # the 12/ backlog
    assert_metric(cockpit.st, "Papers with details saved", "42.0%")


def _fake_cached(value):
    def _fn(*a, **kw):
        return value
    _fn.clear = lambda: None
    return _fn


def test_stats_says_so_when_the_library_is_not_there(cockpit, lib, tmp_path):
    """An unreachable library must not read as an empty one."""
    cockpit.st.session_state["library_root"] = str(tmp_path / "gone")
    cockpit.render_stats()
    text = rendered_text(cockpit.st)
    assert_shows(text, "does not exist")
    assert any(name == "error" for name, _, _ in cockpit.st.calls), \
        "a missing library was not reported as an error"


# ---------------------------------------------------------------------------
# 3. Sort queue
# ---------------------------------------------------------------------------

def test_sort_queue_mentions_how_many_are_waiting_and_names_the_next(cockpit, lib):
    staging = lib / "12 - To be sorted" / "03 - Working papers"
    names = ["Aaa - first.pdf", "Bbb - second.pdf", "Ccc - third.pdf",
             "Ddd - fourth.pdf", "Eee - fifth.pdf", "Fff - sixth.pdf",
             "Ggg - seventh.pdf"]
    for name in names:
        _pdf(staging / name)
    cockpit.render_sort_queue()
    # The size of the queue has to be stated in the page's own prose,
    # not merely be derivable from the number of cards drawn.
    prose = text_of(cockpit.st, "header", "subheader", "caption", "markdown")
    assert_shows(prose, len(names), "papers waiting")
    text = rendered_text(cockpit.st)
    assert_shows(text, "Aaa - first.pdf", "the paper being reviewed")
    assert "Sort queue is empty" not in text


def test_sort_queue_distinguishes_empty_from_missing(cockpit, lib):
    """An empty inbox celebrates; a MISSING inbox must not."""
    (lib / "12 - To be sorted").mkdir()
    cockpit.render_sort_queue()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Sort queue is empty")

    # Now the folder is gone: the same page must refuse to celebrate.
    log2: list = []
    cockpit.st.calls[:] = log2
    cockpit.st.session_state["library_root"] = str(lib / "nope")
    cockpit.st.calls.clear()
    cockpit.render_sort_queue()
    text2 = rendered_text(cockpit.st)
    assert "Sort queue is empty" not in text2
    assert_shows(text2, "Cannot find")


# ---------------------------------------------------------------------------
# 4. Activity
# ---------------------------------------------------------------------------

def _seed_transactions(lib: Path, n: int) -> list[str]:
    d = lib / ".operation_log"
    d.mkdir(parents=True, exist_ok=True)
    ids = []
    for i in range(n):
        tx_id = f"{i:012x}"
        ids.append(tx_id)
        (d / f"{tx_id}.json").write_text(json.dumps({
            "id": tx_id,
            "description": f"bulk sort batch {i}",
            "timestamp": f"2026-08-{10 + i:02d}T09:00:00+00:00",
            "operations": [{"type": "move"}] * (i + 2),
            "undone": False,
        }), encoding="utf-8")
    return ids


def test_activity_lists_the_transactions_on_record(cockpit, lib):
    ids = _seed_transactions(lib, 3)
    cockpit.render_activity()
    text = rendered_text(cockpit.st)
    assert_shows(text, 3, "changes on record")
    for tx_id in ids:
        assert_shows(text, tx_id, "transaction reference")
    assert_shows(text, "bulk sort batch 2", "the newest description")
    assert_shows(text, "↶ Undo", "the button this page exists for")
    assert "Nothing has changed your library yet" not in text


def test_activity_empty_state_only_when_the_log_is_readable_and_empty(cockpit, lib):
    cockpit.render_activity()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Nothing has changed your library yet")
    assert_shows(text, 0, "zero changes on record")


# ---------------------------------------------------------------------------
# 5. Conflicts
# ---------------------------------------------------------------------------

def test_conflicts_counts_and_names_every_conflict_copy(cockpit, lib):
    for stem in ("Alpha", "Beta"):
        _pdf(lib / f"{stem}.pdf", b"%PDF canonical bytes")
        _pdf(lib / f"{stem} (host's conflicted copy 2024-05-13).pdf",
             b"%PDF conflicted bytes that differ")
    cockpit.render_conflicts()
    text = rendered_text(cockpit.st)
    assert_metric(cockpit.st, "Conflict copies", 2)
    assert_shows(text, "Alpha (host's conflicted copy 2024-05-13).pdf")
    assert_shows(text, "Beta (host's conflicted copy 2024-05-13).pdf")
    assert_shows(text, "Alpha.pdf", "the canonical it is compared against")
    assert "No conflict copies detected" not in text


def test_conflicts_clean_library_says_clean(cockpit, lib):
    _pdf(lib / "Alpha.pdf")
    cockpit.render_conflicts()
    assert_shows(rendered_text(cockpit.st), "No conflict copies detected")


# ---------------------------------------------------------------------------
# 6. Duplicates
# ---------------------------------------------------------------------------

def test_duplicates_shows_group_and_copy_counts_and_the_paths(cockpit, lib):
    groups = [
        {"sha256": "a" * 64, "size": 1024,
         "paths": [str(lib / "01 - Published papers" / "A - dup one.pdf"),
                   str(lib / "01 - Published papers" / "A - dup  one.pdf")],
         "keep": str(lib / "01 - Published papers" / "A - dup one.pdf"),
         "remove": [str(lib / "01 - Published papers" / "A - dup  one.pdf")],
         "kind": "near-identical-name", "reason": "double space",
         "auto_safe": True, "notes": []},
        {"sha256": "b" * 64, "size": 2048,
         "paths": [str(lib / "05 - Books and lecture notes" / "B - book.pdf"),
                   str(lib / "06 - Theses" / "B - thesis copy.pdf")],
         "keep": str(lib / "05 - Books and lecture notes" / "B - book.pdf"),
         "remove": [str(lib / "06 - Theses" / "B - thesis copy.pdf")],
         "kind": "different-title", "reason": "possible mis-file",
         "auto_safe": False, "notes": ["different titles"]},
    ]
    cockpit.st.session_state["dup_groups"] = groups
    cockpit.render_duplicates()
    text = rendered_text(cockpit.st)
    assert_metric(cockpit.st, "Duplicate groups", 2)
    assert_metric(cockpit.st, "Auto-safe copies", 1)
    assert_metric(cockpit.st, "Need review", 1)
    assert_shows(text, "A - dup  one.pdf", "the copy that would be trashed")
    assert "No byte-identical duplicates found" not in text


def test_duplicates_empty_scan_says_none_found(cockpit, lib):
    cockpit.st.session_state["dup_groups"] = []
    cockpit.render_duplicates()
    assert_shows(rendered_text(cockpit.st), "No byte-identical duplicates found")


def test_duplicates_unscanned_is_not_the_same_as_clean(cockpit, lib):
    """No scan yet must prompt for a scan, never claim the library is clean."""
    cockpit.render_duplicates()
    text = rendered_text(cockpit.st)
    assert "No byte-identical duplicates found" not in text
    assert_shows(text, "Scan for duplicates")


# ---------------------------------------------------------------------------
# 7. Search
# ---------------------------------------------------------------------------

def test_search_shows_the_hit_count_and_the_matching_filenames(cockpit, lib):
    _pdf(lib / "01 - Published papers" / "P" /
         "Possamai, D. - Bsdes and control.pdf")
    _pdf(lib / "01 - Published papers" / "P" /
         "Possamai, D., Zhou, C. - Second order bsdes.pdf")
    _pdf(lib / "01 - Published papers" / "E" / "Ekeland, I. - Convexity.pdf")
    cockpit.st.values["search_query"] = "possamai bsde"
    cockpit.render_search()
    text = rendered_text(cockpit.st)
    assert_shows(text, "2 result(s)", "the result count")
    # The names have to be ON THE PAGE.  They are also in the CSV/BibTeX
    # download payloads, which `rendered_text` excludes on purpose — a
    # page that lists nothing but offers a download is not a search page.
    assert_shows(text, "Possamai, D. - Bsdes and control.pdf")
    assert_shows(text, "Possamai, D., Zhou, C. - Second order bsdes.pdf")
    assert "Ekeland" not in text, "a non-matching paper was listed"
    assert "Nothing in your library matches" not in text


def test_search_no_hits_says_so_rather_than_nothing(cockpit, lib):
    _pdf(lib / "01 - Published papers" / "E" / "Ekeland, I. - Convexity.pdf")
    cockpit.st.values["search_query"] = "zzzznotapaper"
    cockpit.render_search()
    assert_shows(rendered_text(cockpit.st), "Nothing in your library matches")


# ---------------------------------------------------------------------------
# 8. To Download
# ---------------------------------------------------------------------------

def test_to_download_counts_the_queue_and_names_each_paper(cockpit, lib):
    flags = lib / "04 - Papers to be downloaded" / "D"
    flags.mkdir(parents=True)
    (flags / "Doe, J. - Some paper.txt").write_text(
        "TITLE: Some paper about filtering\n"
        "JOURNAL: Annals of Probability\n"
        "DOI: 10.1214/xyz\n"
        "URL: https://doi.org/10.1214/xyz\n", encoding="utf-8")
    (flags / "Roe, R. - Another paper.txt").write_text(
        "TITLE: Another paper on control\n"
        "JOURNAL: SIAM J. Control\n"
        "DOI: 10.1137/abc\n", encoding="utf-8")

    cockpit.render_to_download()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Manual-download queue (2)", "the queue size")
    assert_shows(text, "Some paper about filtering")
    assert_shows(text, "Another paper on control")
    assert_shows(text, "10.1214/xyz", "the DOI he has to fetch")
    assert "Nothing pending" not in text


def test_to_download_empty_queue_says_nothing_pending(cockpit, lib):
    (lib / "04 - Papers to be downloaded").mkdir()
    cockpit.render_to_download()
    assert_shows(rendered_text(cockpit.st), "Nothing pending")


# ---------------------------------------------------------------------------
# 9. Upgrade queue
# ---------------------------------------------------------------------------

def _seed_report(home: Path, entries: list) -> Path:
    d = home / ".mathpdf" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "checks_2026-08-20_090000.json"
    p.write_text(json.dumps({"published": entries}), encoding="utf-8")
    return p


def test_upgrade_queue_shows_the_candidate_and_its_match(cockpit, lib, home,
                                                         monkeypatch):
    preprint = _pdf(lib / "03 - Working papers" / "Doe, J. - A preprint.pdf")
    report = _seed_report(home, [
        {"file": str(preprint), "parsed_title": "A preprint on filtering",
         "parsed_authors": ["Doe, J."],
         "match": {"doi": "10.1214/aop1234", "journal": "Annals of Probability",
                   "year": 2025, "confidence": 0.97,
                   "matched_title": "A preprint on filtering"}},
        {"file": str(lib / "03 - Working papers" / "Roe, R. - Second.pdf"),
         "parsed_title": "Second one", "parsed_authors": ["Roe, R."],
         "match": {"doi": "10.1137/siam99", "journal": "SIAM J. Control",
                   "year": 2024, "confidence": 0.95,
                   "matched_title": "Second one"}},
    ])
    # Discovery also globs the repo's own publication_report.json; pin the
    # list so the assertion is about what the PAGE renders, not what the
    # developer's machine happens to hold.
    monkeypatch.setattr(cockpit, "_find_publication_reports", lambda: [report])

    cockpit.render_upgrade_queue()
    text = rendered_text(cockpit.st)
    assert_metric(cockpit.st, "Left to review", 2)
    assert_shows(text, "Candidate 1 of 2")
    assert_shows(text, "10.1214/aop1234", "the DOI of the published version")
    assert_shows(text, "Annals of Probability")
    assert_shows(text, "A preprint on filtering")
    assert "no publication check has been run" not in text.lower()


def test_upgrade_queue_says_when_no_check_has_run(cockpit, monkeypatch):
    monkeypatch.setattr(cockpit, "_find_publication_reports", lambda: [])
    cockpit.render_upgrade_queue()
    assert_shows(rendered_text(cockpit.st),
                 "No publication check has been run yet")


# ---------------------------------------------------------------------------
# 10. Pipeline preview
# ---------------------------------------------------------------------------

def test_pipeline_preview_shows_every_trust_metric(cockpit, lib):
    cockpit.st.session_state["preview_summary"] = {
        "scanned": 4321, "agreement_rate": 0.87, "topic_recall": 0.63,
        "disagree": 55, "agree": 344, "recall_miss": 128,
        "proposed_moves": 71, "proposed_suggestions": 19, "in_topic": 902,
        "doctype_mismatches": 6, "subtopic_suggestions": 13,
    }
    cockpit.st.session_state["preview_proposals"] = []
    cockpit.render_pipeline_preview()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Trust metrics")
    for label, value in [("Scanned", 4321), ("Disagreements", 55),
                         ("Would newly file", 71), ("Would suggest", 19),
                         ("Recall misses", 128), ("In a topic now", 902),
                         ("Book/thesis misfiled", 6),
                         ("Sub-subtopic fits", 13),
                         ("Agreement", "87%"), ("Topic recall", "63%")]:
        assert_metric(cockpit.st, label, value)
    assert "Choose a scope and click" not in text


def test_pipeline_preview_unrun_prompts_instead_of_showing_zeros(cockpit, lib):
    cockpit.render_pipeline_preview()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Run preview")
    assert "Trust metrics" not in text


# ---------------------------------------------------------------------------
# 11. Attention (Home)
# ---------------------------------------------------------------------------

def test_attention_shows_a_named_pile_with_its_size(cockpit, lib):
    for stem in ("Alpha", "Beta", "Gamma"):
        _pdf(lib / f"{stem}.pdf", b"%PDF canonical")
        _pdf(lib / f"{stem} (host's conflicted copy 2024-05-13).pdf",
             b"%PDF conflicted")
    cockpit.render_attention()
    text = rendered_text(cockpit.st)
    assert_shows(text, "What needs you", "the summary heading")
    # Named in plain English AND sized: "conflict_copy (3)" was the bug
    # this card replaced, and an unsized card is no better.
    assert_metric(cockpit.st, "Dropbox conflict copies", 3)
    assert "Nothing needs your attention right now" not in text


def test_attention_opened_pile_lists_the_actual_items(cockpit, lib):
    _pdf(lib / "Alpha.pdf", b"%PDF canonical")
    _pdf(lib / "Alpha (host's conflicted copy 2024-05-13).pdf", b"%PDF other")
    cockpit.st.session_state["attn_open_group"] = "conflict_copy"
    cockpit.render_attention()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Alpha (host's conflicted copy 2024-05-13).pdf",
                 "the item in the opened pile")
    assert_shows(text, "Move conflict copy to trash", "its action")
    assert "Pick a pile above to review it" not in text


def test_attention_empty_library_is_not_a_clean_bill_of_health(cockpit, lib,
                                                               tmp_path):
    """A library that cannot be read must not read as 'nothing to do'."""
    cockpit.st.session_state["library_root"] = str(tmp_path / "not-there")
    cockpit.render_attention()
    text = rendered_text(cockpit.st)
    assert "Nothing needs your attention right now" not in text
    assert_shows(text, "does not exist")


# ---------------------------------------------------------------------------
# 12. Maintenance
# ---------------------------------------------------------------------------

def test_maintenance_shows_the_results_of_the_last_run(cockpit, lib):
    cockpit.st.session_state["maintenance_results"] = {
        "to_be_sorted": {"total": 1861,
                         "by_subfolder": {"03 - Working papers": 1200,
                                          "01 - Published papers": 661}},
        "aging": [{"file": "a.pdf"}] * 37,
        "duplicates": [{"title_similarity": 98,
                        "files": [{"filename": "Doe, J. - Paper.pdf"},
                                  {"filename": "Doe, J. - Paper (1).pdf"}]}],
        "publications": {"unpublished": [{"file": "x.pdf"}] * 4,
                         "working": [{"file": "y.pdf"}] * 5},
    }
    cockpit.render_maintenance()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Results")
    assert_shows(text, 1861, "inbox backlog")
    assert_shows(text, 1200, "backlog by subfolder")
    assert_shows(text, 37, "aging working papers")
    assert_shows(text, "Doe, J. - Paper (1).pdf", "a duplicate cluster member")
    assert_shows(text, 9, "newly-published papers found")
    assert "No checks have been run yet" not in text


def test_maintenance_unrun_says_unrun(cockpit, lib):
    cockpit.render_maintenance()
    text = rendered_text(cockpit.st)
    assert_shows(text, "No checks have been run yet")
    assert_shows(text, "Run checks", "the button that starts one")


# ---------------------------------------------------------------------------
# 13. Settings
# ---------------------------------------------------------------------------

def test_settings_shows_every_editable_key_with_its_current_value(
    cockpit, lib, monkeypatch
):
    from ui import cockpit_actions
    monkeypatch.setattr(cockpit_actions, "load_cockpit_config", lambda: {
        "library_root": str(lib),
        "inbox_dir": "/Users/owner/Downloads/MathInbox",
        "unpaywall_email": "owner@example.org",
        "default_status": "working",
        "settle_seconds": 4.5,
        "notifications": True,
    })
    import core.config.secure_config as sc
    monkeypatch.setattr(sc, "get_secure_credential", lambda *a, **k: None)

    cockpit.render_settings()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Watcher settings")
    for _key, label, _kind in cockpit_actions.EDITABLE_CONFIG_KEYS:
        assert_shows(text, label, "config field label")
    assert_shows(text, "/Users/owner/Downloads/MathInbox", "current inbox")
    assert_shows(text, "owner@example.org", "current Unpaywall email")
    assert_shows(text, str(lib), "current library root")


# ---------------------------------------------------------------------------
# 14. Sidebar
# ---------------------------------------------------------------------------

def test_sidebar_offers_every_destination_and_names_the_library(cockpit, lib):
    cockpit.render_sidebar()
    text = rendered_text(cockpit.st)
    for label in ["Sort Queue", "Upgrade Queue", "To Download", "Conflicts",
                  "Duplicates", "Maintenance", "Search", "Pipeline Preview",
                  "Conformance", "Stats", "Activity", "Settings"]:
        assert_shows(text, label, "navigation entry")
    assert_shows(text, str(lib), "which library is in use")
    assert_shows(text, "Library Cockpit", "the app title")


def test_sidebar_says_when_the_library_is_missing(cockpit, tmp_path):
    cockpit.st.session_state["library_root"] = str(tmp_path / "vanished")
    cockpit.render_sidebar()
    text = rendered_text(cockpit.st)
    assert_shows(text, "Library not found")
    assert_shows(text, "Not found:")


# ---------------------------------------------------------------------------
# The harness itself must be able to see an empty page.
# ---------------------------------------------------------------------------

def test_the_recorder_would_notice_an_empty_page(cockpit, lib):
    """Guard the guard: if `rendered_text` ever silently returned a fat
    blob regardless of what ran, every test above would pass vacuously."""
    cockpit.st.calls.clear()
    assert rendered_text(cockpit.st) == ""
    cockpit.st.write("hello")
    cockpit.st.metric("Waiting", 1861)
    text = rendered_text(cockpit.st)
    assert "hello" in text
    assert shows_number(text, 1861)
