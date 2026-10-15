""""Cache abstracts now": the batch reads papers still to read, and a paper
with no record gets a whole one.

Two faults measured on the real library, 2026-10-15 (read-only):

* the batch counted every paper it LOOKED AT, done or not, so "100" read
  3 papers, "500" 4 and "2000" 6 of the 758 waiting; only "All" got there;
* a paper with no record got one holding the text alone -- no fingerprint,
  no filing date -- and "Fill in missing details" then passed it over for
  good. 147 such records; 20 of them sit on papers whose older record,
  left behind by a rename, can now never be put back.

The walk order is fixed here (``_in_name_order``): on APFS ``rglob`` comes
back in no promised order, and the first fault only shows when papers
already done come FIRST.
"""
from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

import processing.classifier_text as ct
import processing.identity as identity
from processing.classifier_text import backfill_classifier_text, describe_run
from processing.identity import (PaperIdentity, compute_content_hash,
                                 enable_sidecar_mirror, filing_date,
                                 find_sidecar, record_location, sidecar_path)
from processing.sidecar_repair import plan_reconnect
from processing.undo_log import UndoLog

FAST = settings(max_examples=40, deadline=None,
                suppress_health_check=[HealthCheck.function_scoped_fixture])

SHELF = "01 - Published papers/S"


@contextmanager
def _library():
    """A fresh library, pointed at the way production code finds it."""
    old = os.environ.get("MATH_LIBRARY")
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "Maths"
        (root / SHELF).mkdir(parents=True)
        enable_sidecar_mirror(root)
        os.environ["MATH_LIBRARY"] = str(root)
        try:
            yield root
        finally:
            if old is None:
                os.environ.pop("MATH_LIBRARY", None)
            else:
                os.environ["MATH_LIBRARY"] = old


@pytest.fixture
def lib():
    with _library() as root:
        yield root


@pytest.fixture(autouse=True)
def _in_name_order(monkeypatch):
    """Walk the library in name order, so a test can put papers first."""
    real = identity.iter_pdfs
    monkeypatch.setattr(identity, "iter_pdfs",
                        lambda root, **kw: iter(sorted(real(root, **kw))))


@pytest.fixture(autouse=True)
def reads(monkeypatch):
    """The text "read" from each PDF, and how often each was read. A
    paper named ``... - image.pdf`` has no text layer."""
    seen: Counter = Counter()

    def extract(pdf, **_kw):
        seen[pdf.name] += 1
        return "" if pdf.stem.endswith("image") else f"first pages of {pdf.stem}"

    monkeypatch.setattr(ct, "extract_classifier_text", extract)
    return seen


def _pdf(root: Path, name: str) -> Path:
    p = root / SHELF / name
    p.write_bytes(f"%PDF-1.4\n% {name}\n".encode())
    return p


def _record(pdf: Path, **fields) -> Path:
    path = sidecar_path(pdf)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": 1, "content_sha256": "ab" * 32,
            "first_ingested_at": "2025-01-01T00:00:00+00:00",
            "original_filename": pdf.name, **fields}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False,
                               sort_keys=True), encoding="utf-8")
    return path


def _strand(pdf: Path) -> Path:
    """Renamed in Finder: its record keeps the old name, fingerprint and all."""
    ident = PaperIdentity()
    ident.doi = "10.1000/stranded"
    ident.save(pdf, recompute_hash=True)
    new = pdf.with_name(pdf.name.replace(" - ", " - renamed ", 1))
    pdf.rename(new)
    return new


def _log(root: Path) -> UndoLog:
    log = UndoLog(log_dir=root / ".operation_log")
    log.begin_transaction("cache abstracts")
    return log


def _tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()
            and ".operation_log" not in p.relative_to(root).parts
            and "undone_records" not in p.relative_to(root).parts}


# --------------------------------------------------------------------------
# the batch
# --------------------------------------------------------------------------

KINDS = st.sampled_from(["done", "tried", "record", "bare", "image"])


@FAST
@given(kinds=st.lists(KINDS, max_size=8),
       limit=st.one_of(st.none(), st.integers(0, 4)))
def test_each_press_reads_a_batch_of_papers_still_to_read(kinds, limit, reads):
    """Whatever comes first in the walk: a press reads ``min(limit, still
    waiting)`` papers, says how many are left, and presses enough of them
    read every paper exactly once while the ones done are never touched."""
    reads.clear()
    with _library() as root:
        waiting, done = [], {}
        for i, kind in enumerate(kinds):
            name = f"P{i:02d}, A. - " + ("image" if kind == "image" else "paper") + ".pdf"
            pdf = _pdf(root, name)
            if kind == "done":
                done[pdf] = _record(pdf, classifier_text="cached before")
            elif kind == "tried":
                done[pdf] = _record(pdf, classifier_text_tried=True)
            elif kind == "record":
                _record(pdf, doi=f"10.1/{i}")
                waiting.append(pdf)
            else:
                waiting.append(pdf)
        before = {p: r.read_bytes() for p, r in done.items()}

        left, presses = len(waiting), 0
        while True:
            s = backfill_classifier_text(root, limit=limit)
            presses += 1
            expect = left if limit is None else min(limit, left)
            assert s["read"] == expect, (s, kinds)
            assert s["still_waiting"] == left - expect, (s, kinds)
            assert s["skipped"] == len(kinds) - left
            assert s["read"] == s["extracted"] + s["empty"]
            left -= expect
            if left == 0 or limit == 0:
                break
            assert presses <= len(kinds), "the presses never finished"

        if limit == 0:
            assert not reads, "a batch of none read something"
            return
        assert dict(reads) == {p.name: 1 for p in waiting}
        for pdf in waiting:
            ident = PaperIdentity.load(pdf)
            assert ident.classifier_text_tried
            assert ident.classifier_text == (
                "" if pdf.stem.endswith("image") else f"first pages of {pdf.stem}")
        assert {p: r.read_bytes() for p, r in done.items()} == before


def test_a_hundred_papers_done_first_do_not_use_up_a_batch_of_100(lib, reads):
    """The page's smallest batch, as measured: every paper ahead of the
    waiting ones already done."""
    for i in range(100):
        _record(_pdf(lib, f"A{i:03d}, A. - done.pdf"), classifier_text="cached")
    late = [_pdf(lib, f"Z{i}, Z. - late.pdf") for i in range(2)]

    s = backfill_classifier_text(lib, limit=100)

    assert s["read"] == 2 and s["still_waiting"] == 0
    assert sorted(reads) == sorted(p.name for p in late)


def test_a_batch_of_none_only_counts(lib, reads):
    for i in range(3):
        _pdf(lib, f"P{i}, A. - paper.pdf")
    s = backfill_classifier_text(lib, limit=0)
    assert (s["read"], s["still_waiting"]) == (0, 3)
    assert not reads and not list((lib / identity.MIRROR_DIR_NAME).rglob("*.json"))


def test_overwrite_counts_the_papers_it_reads_again(lib, reads):
    for i in range(3):
        _record(_pdf(lib, f"P{i}, A. - paper.pdf"), classifier_text="old")
    s = backfill_classifier_text(lib, limit=2, overwrite=True)
    assert (s["read"], s["still_waiting"], s["skipped"]) == (2, 1, 0)


@FAST
@given(order=st.permutations(["bad", "bad", "kept", "kept", "wait", "wait", "wait"]),
       limit=st.integers(1, 3))
def test_papers_it_cannot_read_never_take_a_place_in_the_batch(order, limit, reads):
    """An unreadable record and a paper whose older record is stranded are
    neither read nor written -- and, whatever their number or place in
    the walk, a batch still reads ``limit`` papers. Counted against the
    batch, two of either at the front would hold a batch of 2 back for
    ever."""
    reads.clear()
    with _library() as root:
        bad, kept, wait = [], [], []
        # Half synced, and not UTF-8 at all (that one used to raise out of
        # PaperIdentity.load and end the run).
        bodies = iter([b'{"doi": "10.1000/half-synced", ', b"\xff\xfe\x00{\x00}"])
        for i, kind in enumerate(order):
            pdf = _pdf(root, f"P{i:02d}, A. - {kind}.pdf")
            if kind == "bad":
                rec = sidecar_path(pdf)
                rec.parent.mkdir(parents=True, exist_ok=True)
                body = next(bodies)
                rec.write_bytes(body)
                bad.append((pdf, rec, body))
            elif kind == "kept":
                kept.append(_strand(pdf))
            else:
                wait.append(pdf)

        s = backfill_classifier_text(root, limit=limit)

        assert s["read"] == min(limit, len(wait)), (s, order)
        assert s["still_waiting"] == len(wait) - s["read"]
        assert (s["unreadable"], s["kept_for_reconnect"]) == (2, 2)
        assert sorted(s["unreadable_papers"]) == sorted(p.name for p, _r, _b in bad)
        assert set(reads) <= {p.name for p in wait}
        for _pdf_, rec, body in bad:
            assert rec.read_bytes() == body
        assert all(find_sidecar(p) is None for p in kept)
        assert len(plan_reconnect(root)["matched"]) == 2, (
            "a record made for the paper took the reconnect's spot")


def test_the_stranded_records_are_looked_for_once_and_only_when_needed(
        lib, monkeypatch):
    """Finding them walks the whole library (9 s on his, measured): once a
    run, and not at all when every paper has a record."""
    import processing.sidecar_repair as sr
    calls = []
    real = sr.stranded_fingerprints
    monkeypatch.setattr(sr, "stranded_fingerprints",
                        lambda root: calls.append(root) or real(root))
    for i in range(2):
        _record(_pdf(lib, f"R{i}, A. - recorded.pdf"))
    backfill_classifier_text(lib)
    assert calls == []
    for i in range(3):
        _pdf(lib, f"S{i}, A. - bare.pdf")
    backfill_classifier_text(lib)
    assert calls == [lib]


def test_max_seconds_also_bounds_the_count(lib, monkeypatch):
    """The batch full, the walk goes on to count; the time budget still
    holds there, and what was not counted is ``None``, never a short
    number."""
    import time
    for i in range(4):
        _pdf(lib, f"P{i}, A. - paper.pdf")

    def slow(pdf, **_kw):
        time.sleep(0.25)
        return "text"

    monkeypatch.setattr(ct, "extract_classifier_text", slow)
    s = backfill_classifier_text(lib, limit=1, max_seconds=0.1)
    assert s["read"] == 1 and s["stopped_early"]
    assert s["still_waiting"] is None


# --------------------------------------------------------------------------
# the record a paper with none is given
# --------------------------------------------------------------------------

def test_a_paper_with_no_record_gets_a_whole_one(lib):
    pdf = _pdf(lib, "Smith, J. - Bare.pdf")
    before = _tree(lib)
    log = _log(lib)

    s = backfill_classifier_text(lib, undo_log=log)

    data = json.loads(record_location(pdf).read_text(encoding="utf-8"))
    assert data["content_sha256"] == compute_content_hash(pdf) != ""
    assert data["first_ingested_at"] == filing_date(pdf)
    assert data["original_filename"] == pdf.name
    assert data["classifier_text"] == f"first pages of {pdf.stem}"
    assert data["classifier_text_tried"] is True
    assert s["records_made"] == 1 and s["extracted"] == 1
    (op,) = log._current_tx["operations"]
    assert op["type"] == "record_created", "one change: the record made"
    tx = log._tx_id
    log.commit()
    rows = log.undo_transaction(tx)
    assert all(r["ok"] for r in rows), rows
    assert find_sidecar(pdf) is None
    assert _tree(lib) == before


def test_a_record_made_while_the_text_was_read_is_patched_not_lost(
        lib, monkeypatch):
    """Reading is the slow part; the watcher or another tab may write the
    paper's first record meanwhile. That record is kept and given the
    text -- never passed over, never written over."""
    pdf = _pdf(lib, "Smith, J. - Raced.pdf")

    def extract(p, **_kw):
        _record(p, doi="10.1000/meanwhile")
        return "first pages"

    monkeypatch.setattr(ct, "extract_classifier_text", extract)
    log = _log(lib)

    s = backfill_classifier_text(lib, undo_log=log)

    ident = PaperIdentity.load(pdf)
    assert ident.doi == "10.1000/meanwhile"
    assert ident.classifier_text == "first pages"
    assert (s["extracted"], s["records_made"], s["failed"]) == (1, 0, 0)
    assert [op["type"] for op in log._current_tx["operations"]] == ["sidecar_edit"]


def test_a_failed_save_is_named_and_tried_again(lib, monkeypatch, reads):
    pdf = _pdf(lib, "Smith, J. - Stuck.pdf")
    real, broken = identity.save_new_record, [True]

    def save_new_record(*a, **k):
        if broken[0]:
            raise OSError("disk full")
        return real(*a, **k)

    monkeypatch.setattr(identity, "save_new_record", save_new_record)
    s = backfill_classifier_text(lib)
    assert (s["read"], s["failed"], s["failed_papers"]) == (1, 1, [pdf.name])
    assert s["still_waiting"] == 0 and find_sidecar(pdf) is None
    broken[0] = False
    s = backfill_classifier_text(lib)
    assert (s["read"], s["extracted"], s["records_made"]) == (1, 1, 1)


# --------------------------------------------------------------------------
# what the page says
# --------------------------------------------------------------------------

COUNTS = ("read", "extracted", "empty", "failed", "records_made",
          "kept_for_reconnect", "unreadable", "skipped", "scanned")


@st.composite
def run_stats(draw):
    s = {k: draw(st.integers(0, 3000)) for k in COUNTS}
    s["read"] = s["extracted"] + s["empty"] + s["failed"]
    s["records_made"] = min(s["records_made"], s["read"] - s["failed"])
    s["failed_papers"] = [f"F{i}.pdf" for i in range(min(s["failed"], 12))]
    s["unreadable_papers"] = [f"U{i}.pdf" for i in range(min(s["unreadable"], 12))]
    if draw(st.booleans()):
        s["stopped_early"], s["still_waiting"] = True, None
    else:
        s["still_waiting"] = draw(st.integers(0, 3000))
    return s


def _held(**counts):
    """A run that read some, held some back, and left none waiting."""
    s = {k: 0 for k in COUNTS}
    s.update(counts, failed_papers=["F0.pdf"] * counts.get("failed", 0),
             unreadable_papers=["U0.pdf"] * counts.get("unreadable", 0),
             still_waiting=0)
    s["read"] = s["extracted"] + s["empty"] + s["failed"]
    return s


@settings(max_examples=300, deadline=None)
@given(s=run_stats())
# Drawn too rarely to count on (a mutation run missed it on two seeds of
# three): papers held back and none waiting must not read "every paper".
@example(s=_held(extracted=3, failed=1))
@example(s=_held(unreadable=1))
@example(s=_held(kept_for_reconnect=2))
def test_the_page_says_what_was_read_in_words(s):
    out = describe_run(s)
    words = " ".join(w for _k, w in out)
    assert {k for k, _w in out} <= {"success", "info", "warning"}
    assert "{" not in words and "'" not in words and "_" not in words, words
    if s["read"]:
        assert f"Read {s['read']:,} paper" in words
    for k in ("failed", "unreadable", "kept_for_reconnect"):
        if s[k]:
            assert f"{s[k]:,} paper" in words, (k, words)
    for name in s["failed_papers"][:10] + s["unreadable_papers"][:10]:
        assert name in words
    if s.get("stopped_early"):
        assert "time limit" in words and "Press again" in words
    elif s["still_waiting"]:
        assert f"{s['still_waiting']:,} paper" in words and "Press again" in words
    held = s["failed"] + s["unreadable"] + s["kept_for_reconnect"]
    if held or s["still_waiting"] or s.get("stopped_early"):
        assert "every paper" not in words, words
    assert " 1 papers" not in words and not words.startswith("1 papers")


def test_papers_held_back_are_never_called_done():
    for s in (_held(extracted=3, failed=1), _held(unreadable=1),
              _held(kept_for_reconnect=2)):
        assert describe_run(s)[-1] == ("info", "No other paper is waiting.")


def test_one_paper_is_one_paper():
    out = describe_run({"read": 1, "extracted": 1, "still_waiting": 1})
    words = " ".join(w for _k, w in out)
    assert "Read 1 paper: 1 now has its text stored." in words
    assert "1 paper still to read" in words


def test_another_run_holding_the_lock_is_said_plainly():
    (kind, words), = describe_run({"skipped_locked": True, "still_waiting": None})
    assert kind == "warning" and "already reading" in words


def test_the_last_batch_says_so_and_a_run_with_nothing_to_do_too():
    last = describe_run({"read": 3, "extracted": 3, "still_waiting": 0})
    assert last[-1] == ("success", "That was the last of them: every paper "
                                   "has now had its first pages read.")
    idle = describe_run({"read": 0, "still_waiting": 0})
    assert idle == [("success", "Nothing to read: every paper has already "
                                "had its first pages read.")]
