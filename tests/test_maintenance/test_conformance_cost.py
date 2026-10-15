"""Conformance got faster without changing a single answer.

Measured on the real library, read-only, 2026-10-15: a run took 4 min 49 s
against a page that said "about a minute". Three costs dominated, none of
them the naming rules themselves:

  * the count of non-PDF documents walked and stat()ed all ~220,000
    entries under the library, the code checkout and the record mirror
    included, to count 220 files (143 s);
  * the sidecar check stat()ed the same record path twice per paper and
    then a third time in the orphan pass (88,954 stats), and spent most
    of its time in Python 3.12's ``Path.relative_to``;
  * the progress bar heard only about filenames, so it stood at 100% for
    the last three minutes.

Each fix below is checked against the code it replaced, kept here verbatim
as the oracle, over generated libraries and over the pathologies the old
code handled in a particular way (symlink loops, unreadable folders,
names that end in a dot, a FILE called "Scripts").
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

from maintenance import conformance as C  # noqa: E402
import processing.sidecar_repair as SR  # noqa: E402


# ---------------------------------------------------------------------------
# The oracles: the replaced code, verbatim
# ---------------------------------------------------------------------------
def _old_out_of_scope(library_root: Path) -> int:
    from processing.identity import _NON_LIBRARY_DIRS
    n = 0
    try:
        for p in library_root.rglob("*"):
            if not p.is_file() or p.suffix.lower() == ".pdf":
                continue
            rel = p.relative_to(library_root)
            if any(x in _NON_LIBRARY_DIRS or x.startswith(".") for x in rel.parts):
                continue
            if p.suffix.lower() in (".djvu", ".epub", ".ps", ".dvi", ".chm") \
                    or not p.suffix:
                n += 1
    except OSError:
        return -1
    return n


def _old_check_sidecars(library_root: Path, pdfs: list, all_pdfs: list):
    """The pairing as it was: two stats per paper, a third per record."""
    from processing.identity import sidecar_path
    mirror = library_root / ".mathpdf-sidecars"
    findings, paired, missing, claimed = [], 0, 0, set()
    judged = {str(p) for p in pdfs}
    for pdf in all_pdfs:
        rel = pdf.relative_to(library_root)
        canonical = sidecar_path(pdf)
        naive = mirror / rel.parent / (pdf.stem + ".meta.json")
        id_c, id_n = SR._file_id(canonical), SR._file_id(naive)
        have_c, have_n = id_c is not None, id_n is not None
        claimed.update(i for i in (id_c, id_n) if i is not None)
        if str(pdf) not in judged:
            continue
        if have_c and have_n and id_c != id_n:
            findings.append((str(rel), "two-sidecar-records"))
        elif have_c or have_n:
            paired += 1
        else:
            missing += 1
    stranded = SR.unclaimed_records(library_root, claimed)
    findings += [(str(sc.relative_to(library_root)), "orphaned-records")
                 for sc in stranded]
    return sorted(findings), {"papers_with_a_record": paired,
                              "papers_without_a_record": missing,
                              "orphaned_records": len(stranded)}


# ---------------------------------------------------------------------------
# 1. The count of documents that are not PDFs
# ---------------------------------------------------------------------------
_DIRS = ["a", "B c", "Scripts", ".trash", ".git", "venv", ".mathpdf-sidecars",
         ".hidden", "node_modules", "05 - Books", "x.djvu"]
_FILES = ["p.djvu", "Q.DJVU", "e.epub", "w.pdf", "V.PDF", "noext", "dot.",
          ".dot.djvu", "Scripts", "venv", "t.ps", "u.dvi", "c.chm", "r.txt",
          "a.tar.gz", "m.Ps", ".DS_Store", "README"]

_tree = st.lists(
    st.tuples(st.lists(st.sampled_from(_DIRS), max_size=3),
              st.sampled_from(_FILES)),
    max_size=25)


def _build(root: Path, spec) -> None:
    for dirs, fname in spec:
        d = root.joinpath(*dirs)
        try:
            d.mkdir(parents=True, exist_ok=True)
            p = d / fname
            if not p.exists():
                p.write_bytes(b"x")
        except (FileExistsError, NotADirectoryError, IsADirectoryError):
            pass            # a file and a folder wanted the same name


@settings(max_examples=150, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(spec=_tree)
def test_the_count_matches_the_old_walk_on_any_tree(tmp_path_factory, spec):
    root = tmp_path_factory.mktemp("lib")
    _build(root, spec)
    assert C._out_of_scope(root) == _old_out_of_scope(root)


def test_the_counted_population_is_what_the_old_walk_counted(tmp_path):
    """A worked example, so a failure names the file at fault."""
    for rel in ["05/a.djvu", "05/b.EPUB", "05/README", "05/dot.", "05/x.pdf",
                "05/notes.txt", ".trash/c.djvu", "Scripts/d.djvu",
                ".mathpdf-sidecars/e", "05/.f.djvu", "05/Scripts",
                "05/venv/g.djvu", "05/h.chm"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    # a.djvu, b.EPUB, README, "dot." (no suffix by pathlib's rule), h.chm
    assert C._out_of_scope(tmp_path) == 5 == _old_out_of_scope(tmp_path)


def test_symlinks_are_judged_as_the_old_walk_judged_them(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "a.djvu").write_bytes(b"x")
    (tmp_path / "link-to-dir").symlink_to(tmp_path / "real")      # not entered
    (tmp_path / "link.djvu").symlink_to(tmp_path / "real" / "a.djvu")   # counts
    (tmp_path / "broken.djvu").symlink_to(tmp_path / "nowhere")   # does not
    (tmp_path / "loop").symlink_to(tmp_path / "loop")             # ELOOP: does not
    (tmp_path / "loop.epub").symlink_to(tmp_path / "loop.epub")
    assert _old_out_of_scope(tmp_path) == 2
    assert C._out_of_scope(tmp_path) == 2


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any folder")
def test_an_unreadable_folder_is_skipped_as_before(tmp_path):
    (tmp_path / "ok").mkdir()
    (tmp_path / "ok" / "a.djvu").write_bytes(b"x")
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "b.djvu").write_bytes(b"x")
    locked.chmod(0)
    try:
        assert C._out_of_scope(tmp_path) == _old_out_of_scope(tmp_path) == 1
    finally:
        locked.chmod(0o755)


def test_a_folder_the_count_excludes_is_never_entered(tmp_path, monkeypatch):
    """The cost was walking what the filter then threw away."""
    for rel in ["Scripts/.venv/lib/x.djvu", ".trash/y.djvu",
                ".mathpdf-sidecars/01/z.meta.json", "05/keep.djvu"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    listed = []
    real = os.scandir

    def spy(path="."):
        listed.append(Path(path))
        return real(path)
    monkeypatch.setattr(os, "scandir", spy)
    assert C._out_of_scope(tmp_path) == 1
    assert listed, "the count did not walk at all"
    assert not [p for p in listed
                if any(part in ("Scripts", ".trash", ".mathpdf-sidecars")
                       for part in p.relative_to(tmp_path).parts)]


def test_an_ordinary_file_is_never_stat_ed(tmp_path, monkeypatch):
    """220,000 stats were the 143 seconds. The listing says file-or-folder."""
    for i in range(30):
        (tmp_path / "05").mkdir(exist_ok=True)
        (tmp_path / "05" / f"{i}.djvu").write_bytes(b"x")
        (tmp_path / "05" / f"{i}.pdf").write_bytes(b"x")
    calls = []
    real = os.stat

    def spy(*a, **k):
        calls.append(a[0] if a else k)
        return real(*a, **k)
    monkeypatch.setattr(os, "stat", spy)
    assert C._out_of_scope(tmp_path) == 30
    assert calls == []


# ---------------------------------------------------------------------------
# 2. The sidecar pairing
# ---------------------------------------------------------------------------
def _library(root: Path, n_with: int, n_without: int, orphans: int,
             long_name: bool, double: bool) -> list:
    from processing.identity import enable_sidecar_mirror, sidecar_path
    enable_sidecar_mirror(root)
    pdfs = []
    for i in range(n_with + n_without):
        p = root / "01 - Published papers" / "S" / f"Smith, J. - Paper {i}.pdf"
        _write_minimal_pdf(p, title="t", author="Smith, J.")
        pdfs.append(p)
        if i < n_with:
            sc = sidecar_path(p)
            sc.parent.mkdir(parents=True, exist_ok=True)
            sc.write_text(json.dumps({"i": i}))
    if long_name:
        # stem 243 bytes: its record name (253) is over the mirror's 251
        # budget, so it is hashed -- yet a naive record (253 <= 255) can
        # still exist beside it, which is the two-records case.
        p = root / "01 - Published papers" / "L" / ("Long, A. - " + "x" * 232 + ".pdf")
        _write_minimal_pdf(p, title="t", author="Long, A.")
        pdfs.append(p)
        sc = sidecar_path(p)                    # the hashed fallback
        sc.parent.mkdir(parents=True, exist_ok=True)
        sc.write_text("{}")
        if double:                              # and a naive one as well
            naive = (root / ".mathpdf-sidecars" / "01 - Published papers" / "L"
                     / (p.stem + ".meta.json"))
            try:
                naive.write_text("{}")
            except OSError:
                pass                            # over 255 bytes: cannot exist
    for k in range(orphans):
        o = root / ".mathpdf-sidecars" / "01 - Published papers" / "S" / f"Gone {k}.meta.json"
        o.parent.mkdir(parents=True, exist_ok=True)
        o.write_text("{}")
    t = root / ".mathpdf-sidecars" / ".trash" / "retired.meta.json"
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text("{}")                          # never an orphan
    return pdfs


@settings(max_examples=25, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(n_with=st.integers(0, 4), n_without=st.integers(0, 3),
       orphans=st.integers(0, 3), long_name=st.booleans(),
       double=st.booleans(), judge_all=st.booleans())
def test_the_pairing_matches_the_old_one(tmp_path_factory, n_with, n_without,
                                         orphans, long_name, double, judge_all):
    root = tmp_path_factory.mktemp("lib")
    pdfs = _library(root, n_with, n_without, orphans, long_name, double)
    judged = pdfs if judge_all else pdfs[::2]
    findings, stats = C.check_sidecars(root, judged, all_pdfs=pdfs)
    old_findings, old_stats = _old_check_sidecars(root, judged, pdfs)
    assert sorted((f.path, f.reason) for f in findings) == old_findings
    assert {k: stats[k] for k in old_stats} == old_stats


def test_every_path_is_stat_ed_once(tmp_path, monkeypatch):
    """88,954 stats for 29,855 distinct paths was the waste."""
    pdfs = _library(tmp_path, n_with=5, n_without=2, orphans=2,
                    long_name=True, double=False)
    seen = []
    real = SR._file_id

    def spy(p):
        seen.append(str(p))
        return real(p)
    monkeypatch.setattr(SR, "_file_id", spy)
    findings, stats = C.check_sidecars(tmp_path, pdfs, all_pdfs=pdfs)
    assert stats["papers_with_a_record"] == 6 and stats["orphaned_records"] == 2
    assert len(seen) == len(set(seen)), \
        [p for p in set(seen) if seen.count(p) > 1]


def test_finding_a_record_never_calls_path_relative_to(tmp_path, monkeypatch):
    """The cost contract of identity.lexical_relative: Python 3.12's
    relative_to rebuilt the root's ancestors on every one of 89,000 calls.
    Same answers either way -- this is what makes the sweep cheap."""
    from processing.identity import enable_sidecar_mirror, sidecar_path
    enable_sidecar_mirror(tmp_path)
    pdf = tmp_path / "01 - Published papers" / "S" / "Smith, J. - A note.pdf"
    sidecar_path(pdf)                       # warm the root cache
    called = []
    real = Path.relative_to

    def spy(self, *a, **k):
        called.append(self)
        return real(self, *a, **k)
    monkeypatch.setattr(Path, "relative_to", spy)
    got = sidecar_path(pdf)
    assert got == (tmp_path / ".mathpdf-sidecars" / "01 - Published papers"
                   / "S" / "Smith, J. - A note.meta.json")
    assert called == []


def test_a_record_first_seen_missing_is_looked_at_again(tmp_path):
    """Only a FOUND identity is reused. A path the first pass saw as absent
    but the mirror now lists must be read, or an orphan goes unreported."""
    from processing.identity import enable_sidecar_mirror
    enable_sidecar_mirror(tmp_path)
    sc = tmp_path / ".mathpdf-sidecars" / "01" / "Gone.meta.json"
    sc.parent.mkdir(parents=True)
    sc.write_text("{}")
    assert SR.unclaimed_records(tmp_path, set(), known_ids={str(sc): None}) == [sc]
    # and a known identity IS used: claimed, so not an orphan
    fid = SR._file_id(sc)
    assert SR.unclaimed_records(tmp_path, {fid}, known_ids={str(sc): fid}) == []


# ---------------------------------------------------------------------------
# 3. The page hears about every stage, not just the filenames
# ---------------------------------------------------------------------------
def test_run_reports_each_stage_to_its_end(tmp_path, monkeypatch):
    from processing.identity import enable_sidecar_mirror
    enable_sidecar_mirror(tmp_path)
    for i in range(3):
        _write_minimal_pdf(tmp_path / "01 - Published papers" / "S"
                           / f"Smith, J. - Paper {i}.pdf", title="t", author="S")
    _write_minimal_pdf(tmp_path / "12 - To be sorted" / "Doe, A. - Inbox.pdf",
                       title="t", author="D")
    monkeypatch.setattr(C, "_LISTING_TICK", 1)   # tick on every paper found
    calls = []
    rep = C.run(tmp_path, progress=lambda i, n, s: calls.append((i, n, s)))
    stages = [s for _, _, s in calls]
    order = list(dict.fromkeys(stages))
    assert order == [C.STAGE_LISTING, C.STAGE_EXAMINING, C.STAGE_RECORDS]
    # Listing does not know its total yet; it says so with 0, and counts up.
    listing = [(i, n) for i, n, s in calls if s == C.STAGE_LISTING]
    assert listing == [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
    exam = [(i, n) for i, n, s in calls if s == C.STAGE_EXAMINING]
    assert exam[-1] == (rep.scanned, rep.scanned) == (3, 3)
    recs = [(i, n) for i, n, s in calls if s == C.STAGE_RECORDS]
    assert recs[-1] == (4, 4)       # every paper is paired, the inbox's too
