"""A topic filing gives a paper with no record the same first record every
writer gives it -- and leaves alone one whose older record a rename left
behind.

Found 2026-10-15: ``file_into_topic`` (Pipeline Preview "Apply now") wrote
a paper with no record a BLANK one -- no content fingerprint, so the
reconnect could never find it again after a Finder rename, and no filing
date -- and "Fill in missing details" then passed it over, since it had a
record. "Cache abstracts" did the same until 8f8a374; both now go through
``identity.backfill_sidecar``.

And it never asked whether the paper's record was stranded under an older
name: a fresh record fills the very spot the reconnect needs, and the old
one (DOI, filing date and all) can then never go back. Such a paper is now
not filed at all -- nothing written, nothing moved -- and the bulk apply
says so. Measured 2026-10-16, read-only: 0 of the 466 routable papers with
no record match one of the 36 stranded records.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings, strategies as st

import processing.sidecar_repair as sr
from processing.identity import (PaperIdentity, compute_content_hash,
                                 enable_sidecar_mirror, filing_date,
                                 find_sidecar, missing_from_the_file,
                                 record_location)
from processing.publication_topic_router import (KEPT_FOR_RECONNECT,
                                                 file_into_topic)
from processing.undo_log import UndoLog
from tests.harness.synth_library import _write_minimal_pdf

SHELF = "01 - Published papers/S"
TOPIC_SHELF = "07a - BSDEs/01 - Published papers/S"
TITLE = "Reflected BSDEs and backward stochastic equations"


def _library(root: Path) -> Path:
    for d in (SHELF, TOPIC_SHELF):
        (root / d).mkdir(parents=True, exist_ok=True)
    enable_sidecar_mirror(root)
    return root


@pytest.fixture
def lib(tmp_path, monkeypatch):
    root = _library(tmp_path / "lib")
    monkeypatch.setenv("MATH_LIBRARY", str(root))
    return root


def _paper(lib: Path, name: str = f"Smith, J. - {TITLE}.pdf",
           body: str = "t") -> Path:
    p = lib / SHELF / name
    _write_minimal_pdf(p, title=body, author="Smith, J.")
    return p


def _strand(p: Path, doi: str = "10.1000/stranded") -> Path:
    """Renamed in Finder: its record stays under the old name, fingerprint
    and all. Returns the paper's new path."""
    ident = PaperIdentity()
    ident.doi = doi
    ident.save(p, recompute_hash=True)
    new = p.with_name(p.name.replace(" - ", " - Renamed ", 1))
    p.rename(new)
    assert find_sidecar(new) is None
    return new


def _snapshot(lib: Path) -> dict:
    """Every file under the library but the undo log, by digest."""
    return {p.relative_to(lib).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(lib.rglob("*")) if p.is_file()
            and ".operation_log" not in p.relative_to(lib).parts}


#: The app's own bookkeeping, as in tests/ui/press_harness.py: a filing
#: builds the caser's word counts there, which no undo takes back.
_BOOKKEEPING = (".mathpdf-config/", ".mathpdf.lock", ".mathpdf-lock")


def _shelves(lib: Path) -> dict:
    return {k: v for k, v in _snapshot(lib).items()
            if not k.startswith((".trash/", ".mathpdf-sidecars/.trash/")
                                + _BOOKKEEPING)}


def _retired(lib: Path) -> list:
    """Records undo retired -- a coded one into a ``.sidecars/`` below."""
    trash = lib / ".mathpdf-sidecars/.trash/undone_records"
    return sorted(p for p in trash.rglob("*.meta.json") if p.is_file())


def _log(lib: Path) -> UndoLog:
    log = UndoLog(log_dir=lib / ".operation_log")
    log.begin_transaction("Bulk topic apply")
    return log


def _fields(record: Path) -> dict:
    return json.loads(record.read_text(encoding="utf-8"))


def _dest(lib: Path, msg: str) -> Path:
    assert msg.startswith("moved to "), msg
    return lib / msg.removeprefix("moved to ")


# --------------------------------------------------------------------------
# the record made
# --------------------------------------------------------------------------

_NAMES = {
    "ordinary": f"Smith, J. - {TITLE}.pdf",
    # The filing re-spaces the initials: the record keeps the name the
    # paper ARRIVED with.
    "renamed by the filing": f"Smith, J.R. - {TITLE}.pdf",
    "decomposed accents": unicodedata.normalize(
        "NFD", "Smith, J. - Équations rétrogrades réfléchies.pdf"),
    # 255 bytes: its record is coded, under .sidecars/.
    "longest": ("Smith, J. - BSDEs " + "reflexion stochastic games " * 10)[:251]
               .rstrip() + ".pdf",
}


@pytest.mark.parametrize("kind", list(_NAMES))
def test_a_paper_with_no_record_is_filed_with_a_whole_one(lib, kind):
    p = _paper(lib, _NAMES[kind])
    arrived, digest, when = p.name, compute_content_hash(p), filing_date(p)
    before = _shelves(lib)
    log = _log(lib)

    ok, msg = file_into_topic(p, "07a", lib, undo_log=log)

    assert ok, msg
    dest = _dest(lib, msg)
    if kind == "renamed by the filing":
        assert dest.name != arrived
    data = _fields(record_location(dest))
    assert data["content_sha256"] == digest != ""
    assert data["first_ingested_at"] == when
    assert data["original_filename"] == arrived
    assert data["topic_codes"] == ["07a"]
    assert missing_from_the_file(dest) == [], (
        "Fill in missing details would still find something to fill in")
    assert PaperIdentity.load(dest).drift_check(dest) is None
    kinds = [op["type"] for op in log._current_tx["operations"]]
    assert kinds[0] == "record_created" and kinds.count("record_created") == 1
    assert kinds[-1] == "sidecar_edit"
    tx = log._tx_id
    log.commit()

    rows = log.undo_transaction(tx)

    assert all(r["ok"] for r in rows), rows
    assert _shelves(lib) == before
    assert find_sidecar(p) is None
    retired, = _retired(lib)
    back = _fields(retired)
    assert back["content_sha256"] == digest and back["topic_codes"] == []


def test_filing_without_a_log_makes_the_same_whole_record(lib):
    p = _paper(lib)
    digest, when = compute_content_hash(p), filing_date(p)
    ok, msg = file_into_topic(p, "07a", lib)
    assert ok, msg
    data = _fields(record_location(_dest(lib, msg)))
    assert (data["content_sha256"], data["first_ingested_at"]) == (digest, when)
    assert data["topic_codes"] == ["07a"]


def test_a_paper_that_had_a_record_keeps_every_field_but_the_topic(lib):
    p = _paper(lib)
    ident = PaperIdentity()
    ident.doi = "10.1000/had-one"
    ident.save(p, recompute_hash=False)       # no fingerprint, no date
    before = _fields(record_location(p))
    log = _log(lib)

    ok, msg = file_into_topic(p, "07a", lib, undo_log=log)

    assert ok, msg
    after = _fields(record_location(_dest(lib, msg)))
    moved = ("topic_codes", "copy_locations")       # what a filing changes
    assert {k: v for k, v in after.items() if k not in moved} == \
        {k: v for k, v in before.items() if k not in moved}, (
        "filing filled in a record it did not make -- that is Fill in "
        "missing details' job, through its own undo entry")
    assert "record_created" not in {op["type"]
                                    for op in log._current_tx["operations"]}


def test_a_record_made_meanwhile_is_kept_not_written_over(lib, monkeypatch):
    """The watcher (or another tab) may give the paper its first record
    between the look and the write: that record is kept, the topic added
    to it, and nothing is logged as made."""
    import processing.move_normalizer as mn
    p = _paper(lib)
    real = mn.normalize_full_name

    def meanwhile(name, root):
        ident = PaperIdentity()
        ident.doi = "10.1000/meanwhile"
        ident.save(p, recompute_hash=False)
        return real(name, root)

    monkeypatch.setattr(mn, "normalize_full_name", meanwhile)
    log = _log(lib)

    ok, msg = file_into_topic(p, "07a", lib, undo_log=log)

    assert ok, msg
    dest = _dest(lib, msg)
    ident = PaperIdentity.load(dest)
    assert ident.doi == "10.1000/meanwhile" and ident.topic_codes == ["07a"]
    assert "record_created" not in {op["type"]
                                    for op in log._current_tx["operations"]}
    tx = log._tx_id
    log.commit()
    log.undo_transaction(tx)
    assert PaperIdentity.load(p).doi == "10.1000/meanwhile", (
        "undo retired a record the filing did not make")
    assert _retired(lib) == []


# --------------------------------------------------------------------------
# the paper whose older record is stranded
# --------------------------------------------------------------------------

def test_a_paper_whose_older_record_is_stranded_is_left_exactly_as_it_was(lib):
    # "Franscini" is a word the caser is unsure of: a filing queues it for
    # his ruling. Left alone, the paper must not queue it either.
    p = _strand(_paper(lib, "Smith, J. - Reflected BSDEs at the Franscini "
                            "institute.pdf"))
    before = _snapshot(lib)
    log = _log(lib)

    ok, msg = file_into_topic(p, "07a", lib, undo_log=log)

    assert not ok and msg.startswith(KEPT_FOR_RECONNECT), msg
    assert "Conformance" in msg
    assert _snapshot(lib) == before, "a paper left alone was changed"
    assert not log.has_operations()
    plan = sr.plan_reconnect(lib)
    assert [pdf for _sc, pdf in plan["matched"]] == [p], (
        "the reconnect's spot was taken")


def test_once_its_record_is_back_it_files_with_that_record(lib):
    p = _strand(_paper(lib))
    sr.apply_reconnect(lib, sr.plan_reconnect(lib), dry_run=False)
    reconnected = _fields(record_location(p))
    assert reconnected["doi"] == "10.1000/stranded"
    log = _log(lib)

    ok, msg = file_into_topic(p, "07a", lib, undo_log=log)

    assert ok, msg
    dest = _dest(lib, msg)
    ident = PaperIdentity.load(dest)
    assert ident.doi == "10.1000/stranded" and ident.topic_codes == ["07a"]
    tx = log._tx_id
    log.commit()
    log.undo_transaction(tx)
    assert _fields(record_location(p)) == reconnected
    assert _retired(lib) == []


def test_a_paper_with_its_own_record_is_filed_though_a_copy_is_stranded(lib):
    """One of the 20 measured pairs: the paper has a record AND an older one
    is stranded. The spot is taken already; filing loses nothing, and the
    stranded record stays exactly where it is."""
    p = _strand(_paper(lib))
    PaperIdentity().save(p)                   # its own record since
    orphan, = sr.find_orphans(lib)
    held = orphan.read_bytes()

    ok, msg = file_into_topic(p, "07a", lib)

    assert ok, msg
    assert orphan.read_bytes() == held


def test_the_stranded_records_are_looked_for_only_for_a_paper_with_none(
        lib, monkeypatch):
    """Finding them walks the whole library (18 s on his, measured): never
    for a paper with a record, and not again when the caller found them."""
    calls = []
    real = sr.stranded_fingerprints
    monkeypatch.setattr(sr, "stranded_fingerprints",
                        lambda root: calls.append(root) or real(root))
    recorded = _paper(lib, "Adams, A. - Recorded BSDEs.pdf", body="a")
    PaperIdentity().save(recorded)
    assert file_into_topic(recorded, "07a", lib)[0]
    assert calls == []

    assert file_into_topic(_paper(lib, "Brown, B. - Bare BSDEs.pdf",
                                  body="b"), "07a", lib)[0]
    assert calls == [lib]

    held = _strand(_paper(lib, "Clark, C. - Held BSDEs.pdf", body="c"))
    stranded = real(lib)
    ok, msg = file_into_topic(held, "07a", lib, stranded=stranded)
    assert not ok and msg.startswith(KEPT_FOR_RECONNECT)
    ok, msg = file_into_topic(_paper(lib, "Davis, D. - Bare BSDEs.pdf",
                                     body="d"), "07a", lib, stranded=stranded)
    assert ok, msg
    assert calls == [lib], "looked for again though the caller had them"


def test_the_paper_is_read_once_for_both_the_match_and_its_record(
        lib, monkeypatch):
    """The fingerprint the stranded records were matched against is the
    one written into the record: the paper is not read a second time."""
    import processing.identity as identity
    _strand(_paper(lib, "Other, O. - Elsewhere.pdf", body="o"))
    p = _paper(lib)
    reads = []
    real = identity.compute_content_hash
    monkeypatch.setattr(identity, "compute_content_hash",
                        lambda path: reads.append(Path(path).name) or real(path))
    ok, msg = file_into_topic(p, "07a", lib, stranded=sr.stranded_fingerprints(lib))
    assert ok, msg
    assert reads.count(p.name) == 1, reads
    assert _fields(record_location(_dest(lib, msg)))["content_sha256"] != ""


def test_a_stranded_record_without_a_fingerprint_holds_back_nothing(lib):
    """An orphan with no fingerprint cannot be matched to anything -- in
    particular not to every paper whose contents cannot be read."""
    gone = _paper(lib, "Old, O. - Gone.pdf", body="o")
    PaperIdentity().save(gone, recompute_hash=False)
    gone.unlink()
    assert sr.find_orphans(lib) and sr.stranded_fingerprints(lib) == set()
    ok, msg = file_into_topic(_paper(lib), "07a", lib)
    assert ok, msg


# --------------------------------------------------------------------------
# the bulk apply (Pipeline Preview "Apply now")
# --------------------------------------------------------------------------

def _bsde(lib: Path, surname: str) -> Path:
    return _paper(lib, f"{surname}, J. - {TITLE}.pdf", body=surname)


def test_the_bulk_apply_keeps_back_the_stranded_and_counts_records_made(
        lib, monkeypatch):
    from processing.pipeline_preview import apply_topic_proposals
    calls = []
    real = sr.stranded_fingerprints
    monkeypatch.setattr(sr, "stranded_fingerprints",
                        lambda root: calls.append(root) or real(root))
    recorded = _bsde(lib, "Adams")
    PaperIdentity().save(recorded)
    bare = [_bsde(lib, "Brown"), _bsde(lib, "Clark")]
    held = _strand(_bsde(lib, "Davis"))
    held_before = held.read_bytes()

    res = apply_topic_proposals(lib)

    assert calls == [lib], "the stranded records were not found once a run"
    assert [Path(k["path"]) for k in res["kept_for_reconnect"]] == [held]
    assert res["kept_for_reconnect"][0]["msg"].startswith(KEPT_FOR_RECONNECT)
    assert res["failed"] == [] and len(res["applied"]) == 3
    assert res["records_made"] == 2
    assert held.read_bytes() == held_before and find_sidecar(held) is None
    for p in bare:
        dest = lib / TOPIC_SHELF / p.name
        assert _fields(record_location(dest))["content_sha256"] == \
            compute_content_hash(dest)

    log = UndoLog(log_dir=lib / ".operation_log")
    log.undo_transaction(res["tx_id"])
    assert len(_retired(lib)) == 2


def test_a_bulk_apply_of_papers_that_all_have_records_never_looks(
        lib, monkeypatch):
    from processing.pipeline_preview import apply_topic_proposals
    calls = []
    monkeypatch.setattr(sr, "stranded_fingerprints",
                        lambda root: calls.append(root) or set())
    for s in ("Adams", "Brown"):
        PaperIdentity().save(_bsde(lib, s))
    res = apply_topic_proposals(lib)
    assert len(res["applied"]) == 2 and res["records_made"] == 0
    assert calls == []


# --------------------------------------------------------------------------
# the property
# --------------------------------------------------------------------------

KINDS = st.sampled_from(["recorded", "bare", "stranded", "pair"])


@settings(max_examples=30, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@example(kinds=["stranded", "bare"], found_once=True, nfd=True)
@example(kinds=["pair", "bare", "recorded"], found_once=False, nfd=False)
@given(kinds=st.lists(KINDS, min_size=1, max_size=5),
       found_once=st.booleans(), nfd=st.booleans())
def test_what_a_filing_does_to_each_kind_of_paper(
        tmp_path_factory, monkeypatch, kinds, found_once, nfd):
    """Over any mix of papers: a paper with no record is filed with a whole
    one; a paper whose older record is stranded is not filed, and its
    record can still go back; a paper with a record keeps it; and undo
    gives back the shelves exactly, retiring exactly the records made."""
    lib = _library(tmp_path_factory.mktemp("mix") / "lib")
    monkeypatch.setenv("MATH_LIBRARY", str(lib))
    papers = []
    for i, kind in enumerate(kinds):
        name = f"Author{i}, A. - Équations {kind} {i}.pdf"
        if nfd:
            name = unicodedata.normalize("NFD", name)
        p = _paper(lib, name, body=f"{kind}{i}")
        if kind in ("stranded", "pair"):
            p = _strand(p, doi=f"10.1000/{i}")
        if kind in ("recorded", "pair"):
            ident = PaperIdentity()
            ident.arxiv_id = f"2101.{i:05d}"
            ident.save(p)
        papers.append((kind, p, compute_content_hash(p), filing_date(p),
                       find_sidecar(p) and find_sidecar(p).read_bytes()))
    orphans_before = {o: o.read_bytes() for o in sr.find_orphans(lib)}
    before = _shelves(lib)
    stranded = sr.stranded_fingerprints(lib) if found_once else None
    log = _log(lib)

    outcomes = [file_into_topic(p, "07a", lib, undo_log=log, stranded=stranded)
                for _kind, p, *_ in papers]

    for (kind, p, digest, when, _rec), (ok, msg) in zip(papers, outcomes):
        if kind == "stranded":
            assert not ok and msg.startswith(KEPT_FOR_RECONNECT), msg
            assert p.exists() and find_sidecar(p) is None
            continue
        assert ok, msg
        data = _fields(record_location(_dest(lib, msg)))
        assert data["topic_codes"] == ["07a"]
        if kind == "bare":
            assert (data["content_sha256"], data["first_ingested_at"]) == \
                (digest, when)
        else:
            assert data["arxiv_id"].startswith("2101.")
    assert {o: o.read_bytes() for o in sr.find_orphans(lib)} == orphans_before
    held = {p for kind, p, *_ in papers if kind == "stranded"}
    assert {pdf for _sc, pdf in sr.plan_reconnect(lib)["matched"]} == held
    made = [op for op in log._current_tx["operations"]
            if op["type"] == "record_created"]
    assert len(made) == kinds.count("bare")
    tx = log._tx_id
    log.commit()

    rows = log.undo_transaction(tx)

    assert all(r["ok"] for r in rows), rows
    assert _shelves(lib) == before
    assert len(_retired(lib)) == kinds.count("bare")
    for kind, p, _d, _w, rec in papers:
        if rec is not None:
            assert find_sidecar(p).read_bytes() == rec
