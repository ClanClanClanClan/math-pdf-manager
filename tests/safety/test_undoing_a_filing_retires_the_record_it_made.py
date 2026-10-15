"""Undoing a topic filing takes away the record the filing made.

Found 2026-10-15 by pressing Pipeline Preview's "Apply now" and then Undo:
the paper went back to its shelf and the record's topic fields went back,
but a paper that had arrived with NO record came back with one -- blank,
no topic -- because writing the record was never logged; only its later
field edit was.

Now ``file_into_topic`` writes such a record blank, logs its creation
(``record_created``, with what it then holds), and undo -- after putting
back the fields the filing set -- retires the record to the trash while it
holds exactly that. A record that has gained anything since (a DOI found
later) belongs to the paper: it is KEPT, and the undo says so. A record
that was already there is never part of this.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import unicodedata
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings, strategies as st

from processing.identity import (PaperIdentity, enable_sidecar_mirror,
                                 find_sidecar)
from processing.publication_topic_router import file_into_topic
from processing.undo_log import UndoLog
from tests.harness.synth_library import _write_minimal_pdf

TITLE = "Reflected BSDEs and backward stochastic equations"
TRASHED = ".mathpdf-sidecars/.trash/undone_records/"


def _library(root: Path) -> Path:
    for d in ("01 - Published papers", "07a - BSDEs/01 - Published papers"):
        (root / d).mkdir(parents=True, exist_ok=True)
    enable_sidecar_mirror(root)
    return root


@pytest.fixture
def lib(tmp_path, monkeypatch):
    root = _library(tmp_path / "lib")
    monkeypatch.setenv("MATH_LIBRARY", str(root))
    return root


def _paper(lib: Path, name: str = f"Smith, J. - {TITLE}.pdf") -> Path:
    p = lib / "01 - Published papers" / "S" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title="t", author="Smith, J.")
    return p


#: The app's own bookkeeping, as in tests/ui/press_harness.py.
_BOOKKEEPING = (".operation_log", ".mathpdf-config", ".mathpdf.lock",
                ".mathpdf-lock")


def _snapshot(lib: Path) -> dict:
    out = {}
    for p in sorted(lib.rglob("*")):
        rel = p.relative_to(lib).as_posix()
        if p.is_file() and rel.split("/", 1)[0] not in _BOOKKEEPING:
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _shelves(lib: Path) -> dict:
    return {k: v for k, v in _snapshot(lib).items()
            if not k.startswith((".trash/", ".mathpdf-sidecars/.trash/"))}


def _trashed_records(lib: Path) -> list[str]:
    return sorted(k for k in _snapshot(lib) if k.startswith(TRASHED))


def _file(lib: Path, p: Path) -> tuple[UndoLog, str, Path]:
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("Bulk topic apply: 1 paper(s)")
    ok, msg = file_into_topic(p, "07a", lib, undo_log=log)
    assert ok, msg
    log.commit()
    dest = lib / msg.removeprefix("moved to ")
    assert dest.exists()
    return log, tx, dest


def _ops(log, tx) -> list[dict]:
    return json.loads((log.log_dir / f"{tx}.json").read_text())["operations"]


def _stored(log, tx) -> dict:
    return json.loads((log.log_dir / f"{tx}.json").read_text())


# --------------------------------------------------------------------------
# pathologies
# --------------------------------------------------------------------------

_LONGEST = ("Smith, J. - BSDEs " + "réflexion stochastic games " * 10)[:251]
_NAMES = {
    "ordinary": f"Smith, J. - {TITLE}.pdf",
    "decomposed accents": unicodedata.normalize(
        "NFD", "Smith, J. - Équations rétrogrades réfléchies.pdf"),
    # 255 bytes: its record name would be 261, so the record is coded.
    "longest": _LONGEST.encode()[:251].decode(errors="ignore").rstrip() + ".pdf",
}


@pytest.mark.parametrize("kind", list(_NAMES))
def test_a_paper_that_had_no_record_goes_back_without_one(lib, kind):
    p = _paper(lib, _NAMES[kind])
    assert find_sidecar(p) is None
    before = _shelves(lib)

    log, tx, dest = _file(lib, p)
    created = _ops(log, tx)[0]
    assert created["type"] == "record_created"
    assert ("/.sidecars/" in created["destination"]) is (kind == "longest")
    assert "07a" in PaperIdentity.load(dest).topic_codes
    rows = log.undo_transaction(tx)

    assert all(r["ok"] for r in rows), rows
    assert rows[-1]["action"].startswith("RETIRED RECORD")
    assert _stored(log, tx)["undone"] is True
    assert find_sidecar(p) is None, "undo left a record the paper never had"
    assert _shelves(lib) == before
    retired, = _trashed_records(lib)
    fields = json.loads((lib / retired).read_text())
    assert fields["topic_codes"] == [] and fields["original_filename"] == p.name


def test_a_paper_that_had_a_record_gets_exactly_that_record_back(lib):
    p = _paper(lib)
    ident = PaperIdentity.load(p)
    ident.doi = "10.1000/had-one"
    ident.save(p)
    record_before = find_sidecar(p).read_bytes()
    before = _shelves(lib)

    log, tx, _dest = _file(lib, p)
    assert "record_created" not in {op["type"] for op in _ops(log, tx)}
    log.undo_transaction(tx)

    assert find_sidecar(p).read_bytes() == record_before
    assert _shelves(lib) == before
    assert _trashed_records(lib) == []


def test_a_record_that_gained_details_since_is_kept_and_the_undo_says_so(lib):
    p = _paper(lib)
    log, tx, dest = _file(lib, p)
    ident = PaperIdentity.load(dest)
    ident.doi = "10.1000/found-later"       # e.g. "Fill in missing details"
    ident.save(dest, recompute_hash=False)

    dry = log.undo_transaction(tx, dry_run=True)
    rows = log.undo_transaction(tx)

    assert [r["ok"] for r in dry] == [r["ok"] for r in rows]
    assert rows[-1]["ok"] is False and rows[-1]["action"].startswith("KEPT")
    assert dry[-1]["action"].startswith("KEPT")
    assert all(r["ok"] for r in rows[:-1])
    assert p.exists() and not dest.exists()
    back = PaperIdentity.load(p)
    assert back.doi == "10.1000/found-later" and back.topic_codes == []
    assert _trashed_records(lib) == []
    assert _stored(log, tx)["undone"] is False


def test_the_preview_says_the_record_will_be_retired(lib):
    p = _paper(lib)
    log, tx, _dest = _file(lib, p)
    dry = log.undo_transaction(tx, dry_run=True)
    live = log.undo_transaction(tx)
    assert [(r["op"], r["ok"]) for r in dry] == [(r["op"], r["ok"]) for r in live]
    assert dry[-1]["action"].startswith("WOULD RETIRE the saved record")


def test_a_strangers_record_in_its_place_is_never_retired(lib):
    """Someone else's record sits where this one has to come back to: the
    record's move back is refused, and undo must not retire the stranger."""
    p = _paper(lib)
    log, tx, _dest = _file(lib, p)
    created = Path(_ops(log, tx)[0]["destination"])
    created.write_text(json.dumps({"doi": "10.1000/stranger"}))
    stranger = created.read_bytes()

    dry = log.undo_transaction(tx, dry_run=True)
    rows = log.undo_transaction(tx)

    assert [(r["op"], r["ok"]) for r in dry] == [(r["op"], r["ok"]) for r in rows]
    assert created.read_bytes() == stranger
    assert rows[-1]["action"].startswith("KEPT")
    assert _trashed_records(lib) == []


def test_a_retry_finishes_once_the_records_place_is_free(lib):
    p = _paper(lib)
    before = _shelves(lib)
    log, tx, _dest = _file(lib, p)
    created = Path(_ops(log, tx)[0]["destination"])
    created.write_text(json.dumps({"doi": "10.1000/stranger"}))
    log.undo_transaction(tx)
    assert _stored(log, tx)["undone"] is False

    aside = lib.parent / "aside.json"
    shutil.move(str(created), str(aside))      # the owner clears it
    rows = log.undo_transaction(tx)

    assert [r["ok"] for r in rows] == [True, True], rows
    assert _stored(log, tx)["undone"] is True
    assert _shelves(lib) == before
    assert len(_trashed_records(lib)) == 1


def test_a_retry_after_the_paper_itself_was_blocked(lib):
    """The record comes back before the paper does (reverse order), and is
    retired even while the paper's way home is blocked: it holds nothing.
    The retry then brings the paper home and the transaction is done."""
    p = _paper(lib)
    before = _shelves(lib)
    log, tx, _dest = _file(lib, p)
    p.write_bytes(b"%PDF someone else")

    first = log.undo_transaction(tx)
    assert [r["ok"] for r in first].count(False) == 1
    p.unlink()
    second = log.undo_transaction(tx)

    assert [r["ok"] for r in second] == [True]
    assert _stored(log, tx)["undone"] is True
    assert _shelves(lib) == before


def test_undone_filings_of_one_paper_keep_every_record(lib):
    p = _paper(lib)
    for _ in range(3):
        log, tx, _dest = _file(lib, p)
        log.undo_transaction(tx)
        assert find_sidecar(p) is None
    assert len(_trashed_records(lib)) == 3, "a retired record overwrote another"


def test_the_record_goes_to_its_own_librarys_trash(lib, tmp_path, monkeypatch):
    """Not to whichever library is configured: the paper's."""
    elsewhere = tmp_path / "configured"
    elsewhere.mkdir()
    monkeypatch.setenv("MATH_LIBRARY", str(elsewhere))
    p = _paper(lib)
    log, tx, _dest = _file(lib, p)
    log.undo_transaction(tx)
    assert len(_trashed_records(lib)) == 1
    assert not any(elsewhere.rglob("*.json"))


def test_any_caller_may_log_a_record_it_made(tmp_path, monkeypatch):
    """``record_new_record`` is not tied to topic filing: a record written
    with few fields, then given one it lacked (logged as ``absent``), is
    retired once undo has taken that field away again -- and the preview
    says so too. Written with its keys out of order: undo rewrites a record
    sorted, and what it holds, not its layout, is what must match."""
    from processing.identity import patch_record
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(b"%PDF")
    record = pdf.with_suffix(".meta.json")
    log = UndoLog(log_dir=tmp_path / "log")
    tx = log.begin_transaction("made a record")
    record.write_text(json.dumps({"title": "t", "doi": "10.1/x"}))
    log.record_new_record(pdf, record)
    patch_record(pdf, {"arxiv_id": "2101.00001"}, undo_log=log)
    log.commit()

    dry = log.undo_transaction(tx, dry_run=True)
    rows = log.undo_transaction(tx)

    assert [r["ok"] for r in dry] == [r["ok"] for r in rows] == [True, True]
    assert not record.exists()
    retired, = tmp_path.rglob(".trash/undone_records/*.meta.json")
    assert json.loads(retired.read_text()) == {"doi": "10.1/x", "title": "t"}


def test_filing_without_a_log_still_writes_the_record(lib):
    p = _paper(lib)
    ok, msg = file_into_topic(p, "07a", lib)
    assert ok, msg
    assert PaperIdentity.load(lib / msg.removeprefix("moved to ")).topic_codes == ["07a"]


def test_an_older_undo_loop_passes_over_the_new_kind_of_change(lib):
    """The undo loop before this change read ``source`` and ``destination``
    of every operation that is not a ``sidecar_edit``; a type it did not
    know then produced no row. A cockpit still running that code must not
    fail half-way through a filing logged by this one."""
    p = _paper(lib)
    log, tx, _dest = _file(lib, p)
    ops = _ops(log, tx)
    assert "record_created" in {op["type"] for op in ops}
    for op in ops:
        if op["type"] != "sidecar_edit":
            assert {"source", "destination"} <= op.keys(), op


def test_an_unreadable_record_is_not_counted_as_created(lib):
    """A record that is there but unreadable is not "no record": nothing
    may log its creation, or undo would retire what was there before."""
    p = _paper(lib)
    ident = PaperIdentity.load(p)
    ident.save(p)
    find_sidecar(p).write_text("{ torn")
    log, tx, _dest = _file(lib, p)
    assert "record_created" not in {op["type"] for op in _ops(log, tx)}


def test_the_preview_of_a_retry_ignores_what_a_first_press_undid(lib):
    """The first press brought the paper and its record home but KEPT the
    record (a DOI had been added). He then files the paper into the topic
    again, by hand, and clears the DOI. The record the retry is about is
    no longer where the filing made it: the retry finds nothing there, and
    its preview must say the same -- not follow the record along moves the
    first press already undid."""
    from processing.identity import patch_record, sidecar_path
    p = _paper(lib)
    log, tx, dest = _file(lib, p)
    ident = PaperIdentity.load(dest)
    ident.doi = "10.1000/found-later"
    ident.save(dest, recompute_hash=False)
    first = log.undo_transaction(tx)
    assert first[-1]["action"].startswith("KEPT")
    shutil.move(str(p), str(dest))
    shutil.move(str(find_sidecar(p)), str(sidecar_path(dest)))
    patch_record(dest, {"doi": ""})     # exactly what the filing made, again

    dry = log.undo_transaction(tx, dry_run=True)
    live = log.undo_transaction(tx)

    assert [(r["op"], r["ok"]) for r in dry] == [(r["op"], r["ok"]) for r in live]
    assert live[-1]["action"].startswith("SKIP: no saved record")
    assert find_sidecar(dest) is not None, "the re-filed paper lost its record"


def test_a_torn_record_is_never_retired(lib):
    """Unreadable: what it holds cannot be shown to be only what the filing
    wrote, so it goes home with its paper and stays there."""
    p = _paper(lib)
    log, tx, dest = _file(lib, p)
    created = Path(_ops(log, tx)[0]["destination"])
    find_sidecar(dest).write_text("{ torn")

    dry = log.undo_transaction(tx, dry_run=True)
    rows = log.undo_transaction(tx)

    assert dry[-1]["action"].startswith("KEPT")
    assert rows[-1]["action"].startswith("KEPT") and rows[-1]["ok"] is False
    assert created.read_text() == "{ torn" and p.exists()
    assert _trashed_records(lib) == []


def test_a_record_that_vanished_is_reported_not_imagined(lib):
    p = _paper(lib)
    log, tx, dest = _file(lib, p)
    created = Path(_ops(log, tx)[0]["destination"])
    find_sidecar(dest).unlink()
    dry = log.undo_transaction(tx, dry_run=True)
    rows = log.undo_transaction(tx)
    assert dry[-1]["action"].startswith("SKIP: no saved record")
    assert rows[-1]["action"].startswith("SKIP: no saved record")
    assert rows[-1]["ok"] is False
    assert not created.exists() and p.exists()


# --------------------------------------------------------------------------
# the property
# --------------------------------------------------------------------------

_WORDS = st.sampled_from(["backward", "équations", "Itô", "Bellman–Isaacs",
                          "stochastic", "réflexion", "control", "games"])


@settings(max_examples=40, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
# Found by CI on Linux: decomposed after shortening, this name was 256 bytes.
@example(words=["backward"] * 25 + ["équations"], nfd=True,
         had_record=False, gained=False)
@given(words=st.lists(_WORDS, min_size=1, max_size=40),
       nfd=st.booleans(), had_record=st.booleans(),
       gained=st.booleans())
def test_undo_gives_back_exactly_the_records_there_were(
        tmp_path_factory, monkeypatch, words, nfd, had_record, gained):
    lib = _library(tmp_path_factory.mktemp("rec") / "lib")
    monkeypatch.setenv("MATH_LIBRARY", str(lib))
    title = " ".join(words)
    name = f"Smith, J. - BSDEs {title}"
    if nfd:
        name = unicodedata.normalize("NFD", name)
    # Up to the 255-byte limit of a file name, counted AFTER decomposing (an
    # "é" decomposed takes three bytes, not two): the longest have a coded
    # record, under .sidecars/.
    while len((name + ".pdf").encode()) > 255:
        name = name[:-1].rstrip()
    name += ".pdf"
    p = _paper(lib, name)
    if had_record:
        ident = PaperIdentity.load(p)
        ident.arxiv_id = "2101.00001"
        ident.save(p)
    record_before = find_sidecar(p).read_bytes() if had_record else None
    before = _shelves(lib)

    log, tx, dest = _file(lib, p)
    if gained:
        ident = PaperIdentity.load(dest)
        ident.doi = "10.1000/later"
        ident.save(dest, recompute_hash=False)
    dry = log.undo_transaction(tx, dry_run=True)
    rows = log.undo_transaction(tx)

    assert [(r["op"], r["ok"]) for r in dry] == [(r["op"], r["ok"]) for r in rows]
    assert p.exists() and not dest.exists()
    kinds = [op["type"] for op in _ops(log, tx)]
    assert ("record_created" in kinds) is (not had_record)
    if had_record and not gained:
        assert find_sidecar(p).read_bytes() == record_before
        assert _shelves(lib) == before
    if not had_record and not gained:
        assert find_sidecar(p) is None
        assert _shelves(lib) == before
        assert len(_trashed_records(lib)) == 1
        assert _stored(log, tx)["undone"] is True
    if gained:
        assert PaperIdentity.load(p).doi == "10.1000/later", (
            "a detail found after the filing was taken from the paper")
        assert _trashed_records(lib) == []
        assert _stored(log, tx)["undone"] is had_record
