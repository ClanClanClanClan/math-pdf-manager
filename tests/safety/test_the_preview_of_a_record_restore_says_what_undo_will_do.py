"""The preview of putting a record's fields back says what the press does.

Found 2026-10-15: Activity's "Show what Undo would do" answered "WOULD
RESTORE sidecar fields ..." for every record edit, whatever was on disk,
and the press then said "SKIP: no sidecar to restore" whenever the paper
had no readable record by then. The fault a75aa01 fixed for copies: a
preview that cannot fail is not a preview.

Now the preview asks what the press will find. The record can be somewhere
else while the preview runs -- this transaction's own later moves have not
been reversed yet -- so it is followed through them, as the preview of
retiring a created record already was.

Found on the way: when one of those moves back was refused because another
paper's record sat in the way, the press wrote this paper's old values onto
THAT record and counted the edit as come back -- so the retry that brought
the record home left it with the new values and called the undo done. The
press now refuses that edit, and its preview says so.
"""
from __future__ import annotations

import json
import shutil
import unicodedata
from pathlib import Path

import pytest

from processing.identity import (PaperIdentity, enable_sidecar_mirror,
                                 find_sidecar, patch_record, sidecar_path)
from processing.undo_log import UndoLog, logged_move, logged_rename

OLD, NEW = "10.1000/old", "10.1000/new"

_LONGEST = ("Smith, J. - BSDEs " + "réflexion stochastic games " * 10)[:251]
NAMES = {
    "ordinary": "Smith, J. - Reflected BSDEs.pdf",
    "decomposed accents": unicodedata.normalize(
        "NFD", "Smith, J. - Équations rétrogrades réfléchies.pdf"),
    # 255 bytes: its record name would be 261, so the record is coded.
    "longest": _LONGEST.encode()[:251].decode(errors="ignore").rstrip() + ".pdf",
    # 255 letters: the other two places a record of it could be are names
    # too long to ask the disk about -- on macOS too, which counts the
    # accented one above in characters and lets it through.
    "longest, plain letters": (
        "Smith, J. - BSDEs " + "stochastic games " * 15)[:251] + ".pdf",
}


@pytest.fixture
def lib(tmp_path, monkeypatch):
    root = tmp_path / "lib"
    (root / "01 - Published papers").mkdir(parents=True)
    enable_sidecar_mirror(root)
    monkeypatch.setenv("MATH_LIBRARY", str(root))
    return root


def _paper(lib: Path, name: str, body: bytes = b"%PDF-1.4 paper") -> Path:
    p = lib / "01 - Published papers" / "S" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    return p


def _with_doi(p: Path, doi: str) -> None:
    ident = PaperIdentity.load(p)
    ident.doi = doi
    ident.save(p)


def _begin(lib: Path) -> tuple[UndoLog, str]:
    log = UndoLog(log_dir=lib / ".operation_log")
    return log, log.begin_transaction("edit")


def _edited(lib: Path, name: str = NAMES["ordinary"]):
    """A paper whose DOI a transaction changed OLD -> NEW: (log, tx, paper),
    the transaction still open."""
    p = _paper(lib, name)
    _with_doi(p, OLD)
    log, tx = _begin(lib)
    assert patch_record(p, {"doi": NEW}, undo_log=log) is True
    return log, tx, p


def _both(log: UndoLog, tx: str, *, kinds=None):
    """The preview, then the press, which must agree row for row -- on the
    rows of ``kinds`` of change only, if given."""
    dry = log.undo_transaction(tx, dry_run=True)
    live = log.undo_transaction(tx)
    assert [r["op"] for r in dry] == [r["op"] for r in live]
    ops = _stored(log, tx)["operations"]
    pick = [r["op"] for r in live if kinds is None or ops[r["op"]]["type"] in kinds]
    assert [(r["op"], r["ok"]) for r in dry if r["op"] in pick] == [
        (r["op"], r["ok"]) for r in live if r["op"] in pick], (dry, live)
    return dry, live


#: A paper moved twice in one change: the preview of its MOVES is wrong (see
#: the xfail below), so only the edit's row is compared for those.
EDITS_ONLY = {"rename": None, "move, then rename": {"sidecar_edit"}}


def _stored(log: UndoLog, tx: str) -> dict:
    return json.loads((log.log_dir / f"{tx}.json").read_text())


def _edit_row(rows: list) -> dict:
    """The row of the edit under test -- always the transaction's first
    operation. (A logged rename adds its own later edit, of the record's
    ``copy_locations``.)"""
    row, = [r for r in rows if r["op"] == 0]
    return row


def _doi(p: Path):
    return json.loads(find_sidecar(p).read_text(encoding="utf-8")).get("doi")


def _renamed(p: Path) -> Path:
    return p.with_name("Z" + p.name[1:])          # as long as the original


# --------------------------------------------------------------------------
# a record moved aside
# --------------------------------------------------------------------------

@pytest.mark.parametrize("kind", list(NAMES))
def test_a_record_moved_aside_is_previewed_as_not_there(lib, kind):
    log, tx, p = _edited(lib, NAMES[kind])
    log.commit()
    rec = find_sidecar(p)
    assert ("/.sidecars/" in str(rec)) is kind.startswith("longest")
    aside = lib.parent / "aside.json"
    shutil.move(str(rec), str(aside))
    held = aside.read_bytes()

    dry, live = _both(log, tx)

    assert [r["ok"] for r in live] == [False]
    assert dry[0]["action"] == live[0]["action"]
    assert live[0]["action"].startswith("SKIP: no sidecar to restore")
    assert aside.read_bytes() == held and find_sidecar(p) is None
    assert _stored(log, tx)["undone"] is False

    shutil.move(str(aside), str(rec))           # he puts it back
    dry, live = _both(log, tx)

    assert [r["ok"] for r in live] == [True]
    assert dry[0]["action"].startswith("WOULD RESTORE")
    assert _doi(p) == OLD and _stored(log, tx)["undone"] is True


# --------------------------------------------------------------------------
# an unreadable record
# --------------------------------------------------------------------------

UNREADABLE = {
    "torn": b'{"doi": "10.10',
    # Not UTF-8 at all: reading it raised, and the preview -- of this edit,
    # and of retiring a created record -- crashed instead of answering.
    "not text": b"\xff\xfe\x00{\x00}",
    "a list": b"[]",
    "null": b"null",
}


@pytest.mark.parametrize("moved_on", [False, True],
                         ids=["in its place", "moved on by the same change"])
@pytest.mark.parametrize("bad", list(UNREADABLE))
def test_an_unreadable_record_is_previewed_as_unreadable(lib, bad, moved_on):
    log, tx, p = _edited(lib)
    q = _renamed(p)
    if moved_on:
        logged_rename(p, q, undo_log=log)
    log.commit()
    rec = find_sidecar(q if moved_on else p)
    rec.write_bytes(UNREADABLE[bad])

    dry, live = _both(log, tx)

    edit = _edit_row(live)
    assert edit["ok"] is False
    assert _edit_row(dry)["action"] == edit["action"]
    assert edit["action"].startswith("SKIP: no sidecar to restore")
    assert find_sidecar(p).read_bytes() == UNREADABLE[bad]


def test_a_directory_where_the_record_should_be(lib):
    log, tx, p = _edited(lib)
    log.commit()
    rec = find_sidecar(p)
    rec.unlink()
    rec.mkdir()

    dry, live = _both(log, tx)

    assert [r["ok"] for r in live] == [False]
    assert dry[0]["action"] == live[0]["action"]
    assert rec.is_dir()


def test_a_created_record_that_is_not_text_is_kept_not_a_crash(lib):
    """``_read_record`` is shared with the preview -- and the press -- of
    retiring a record a change made. Both raised on bytes that are not
    UTF-8, half-way through the undo, before any bookkeeping was saved."""
    p = _paper(lib, NAMES["ordinary"])
    log, tx = _begin(lib)
    record = sidecar_path(p)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"title": "t"}))
    log.record_new_record(p, record)
    log.commit()
    record.write_bytes(UNREADABLE["not text"])

    dry, live = _both(log, tx)

    assert dry[0]["action"] == live[0]["action"]
    assert live[0]["action"].startswith("KEPT")
    assert record.read_bytes() == UNREADABLE["not text"]
    assert _stored(log, tx)["undone"] is False


# --------------------------------------------------------------------------
# a record moved on by a later operation of the same transaction
# --------------------------------------------------------------------------

def _move_on(log, lib, p: Path, hops: str) -> Path:
    """Move the paper -- its record goes with it -- once or twice."""
    if hops == "rename":
        q = _renamed(p)
        logged_rename(p, q, undo_log=log)
        return q
    m = lib / "01 - Published papers" / "T" / p.name
    logged_move(p, m, undo_log=log)
    q = _renamed(m)
    logged_rename(m, q, undo_log=log)
    return q


@pytest.mark.parametrize("hops", ["rename", "move, then rename"])
@pytest.mark.parametrize("kind", list(NAMES))
def test_a_record_moved_on_by_the_same_change_is_followed(lib, kind, hops):
    log, tx, p = _edited(lib, NAMES[kind])
    q = _move_on(log, lib, p, hops)
    log.commit()
    assert find_sidecar(p) is None, "the record is not where the edit was"
    assert _doi(q) == NEW

    dry, live = _both(log, tx, kinds=EDITS_ONLY[hops])

    assert all(r["ok"] for r in live), live
    assert dry[-1]["action"].startswith("WOULD RESTORE")
    assert _doi(p) == OLD and not q.exists()
    assert _stored(log, tx)["undone"] is True


@pytest.mark.parametrize("hops", ["rename", "move, then rename"])
def test_a_moved_on_record_that_vanished_is_not_promised(lib, hops):
    log, tx, p = _edited(lib)
    q = _move_on(log, lib, p, hops)
    log.commit()
    find_sidecar(q).unlink()

    dry, live = _both(log, tx, kinds=EDITS_ONLY[hops])

    edit = _edit_row(live)
    assert _edit_row(dry)["action"] == edit["action"]
    assert edit["ok"] is False and edit["action"].startswith(
        "SKIP: the record of")
    assert p.exists() and find_sidecar(p) is None


def test_another_papers_record_in_the_way_is_left_alone(lib):
    """The paper was renamed; another paper then arrived under its old name,
    with a record of its own. Undo cannot bring this record home -- and must
    not write this paper's old DOI onto the other's record instead."""
    log, tx, p = _edited(lib)
    q = _renamed(p)
    logged_rename(p, q, undo_log=log)
    log.commit()
    _paper(lib, p.name, b"%PDF-1.4 another paper")
    _with_doi(p, "10.1000/the-other-papers")
    other = find_sidecar(p).read_bytes()

    dry, live = _both(log, tx)

    edit = _edit_row(live)
    assert _edit_row(dry)["action"] == edit["action"]
    assert edit["ok"] is False and edit["action"].startswith(
        "SKIP: the record of")
    assert find_sidecar(p).read_bytes() == other, (
        "the other paper's record was given this paper's fields")
    assert _doi(q) == NEW

    # He moves the other paper away; the retry brings this one home with
    # its record, and its fields back.
    aside = lib.parent / "aside"
    aside.mkdir()
    shutil.move(str(find_sidecar(p)), str(aside / "other.meta.json"))
    shutil.move(str(p), str(aside / "other.pdf"))
    dry, live = _both(log, tx)

    assert all(r["ok"] for r in live), live
    assert _doi(p) == OLD
    assert _stored(log, tx)["undone"] is True


def test_the_record_comes_back_to_another_of_its_places(lib):
    """The shape of the real "merge two saved records" entry (a7051bcc41e7):
    the kept record is edited, then the other one retired to the trash. With
    the kept one gone since, undo brings the other back and restores onto
    it -- and the preview, with no record at either place now, says so."""
    log, tx, p = _edited(lib)
    natural = p.with_suffix(".meta.json")       # the pre-mirror place
    natural.write_text(json.dumps({"doi": OLD, "title": "older copy"}))
    trashed = lib / ".trash" / "duplicate_records" / natural.name
    logged_move(natural, trashed, undo_log=log)
    log.commit()
    sidecar_path(p).unlink()                    # the kept record, gone since
    assert find_sidecar(p) is None

    dry, live = _both(log, tx)

    assert all(r["ok"] for r in live), live
    assert dry[-1]["action"].startswith("WOULD RESTORE")
    assert find_sidecar(p) == natural and _doi(p) == OLD


def test_the_preview_of_a_retry_ignores_what_the_first_press_brought_back(lib):
    """The first press brought the record home torn, so its fields could
    not go back; he repairs it. The retry attempts only the edit -- and its
    preview must look for the record at home, not follow it along a rename
    the first press already undid."""
    log, tx, p = _edited(lib)
    q = _renamed(p)
    logged_rename(p, q, undo_log=log)
    log.commit()
    find_sidecar(q).write_text("{ torn")
    first = log.undo_transaction(tx)
    assert _edit_row(first)["ok"] is False and p.exists()
    renames = [r["op"] for r in first if r["action"].startswith("RENAMED")]
    assert len(renames) == 2 and set(renames) <= set(
        _stored(log, tx)["reversed_ops"])
    find_sidecar(p).write_text(json.dumps({"doi": NEW}))

    dry, live = _both(log, tx)

    assert not set(r["op"] for r in live) & set(renames)
    assert _edit_row(live)["ok"] is True
    assert _edit_row(dry)["action"].startswith("WOULD RESTORE")
    assert _doi(p) == OLD


@pytest.mark.xfail(strict=True, reason=(
    "Not fixed here: the preview of a MOVE asks today's disk one move at a "
    "time, so the first move back of a file moved on twice in one change "
    "says 'file gone' -- the second has not been undone yet -- and the press "
    "then succeeds. No pending entry in the real log moves a file twice "
    "(measured 2026-10-15). The record previews follow the whole trail."))
def test_the_preview_of_a_paper_moved_twice_in_one_change(lib):
    p = _paper(lib, NAMES["ordinary"])
    log, tx = _begin(lib)
    _move_on(log, lib, p, "move, then rename")
    log.commit()
    _both(log, tx)


def test_a_rename_that_only_changed_case(lib):
    """On a disk that folds case (APFS) the record's old name answers for
    the renamed record itself: that is the record, not another in its way
    (non-negotiable 7). The same file, so its way back is free."""
    log, tx, p = _edited(lib, "Smith, J. - reflected BSDEs.pdf")
    q = p.with_name("Smith, J. - Reflected BSDEs.pdf")
    logged_rename(p, q, undo_log=log)
    log.commit()

    dry, live = _both(log, tx)

    assert all(r["ok"] for r in live), live
    assert _edit_row(dry)["action"].startswith("WOULD RESTORE")
    assert _doi(p) == OLD
    assert [c.name for c in p.parent.iterdir()] == [p.name]


def test_another_papers_record_in_the_place_of_a_lost_one(lib):
    """The renamed record is lost since, another paper now has the old name
    and a record there, and an older copy of this paper's record (from
    before the record mirror; Conformance found such pairs) sits at another
    of its places. The press looks at the first place holding a record --
    the other paper's -- and refuses; the preview must not answer with the
    older copy further down the list."""
    log, tx, p = _edited(lib)
    q = _renamed(p)
    logged_rename(p, q, undo_log=log)
    log.commit()
    find_sidecar(q).unlink()
    _paper(lib, p.name, b"%PDF-1.4 another paper")
    _with_doi(p, "10.1000/the-other-papers")
    other = find_sidecar(p).read_bytes()
    older = p.with_suffix(".meta.json")
    older.write_text(json.dumps({"doi": NEW}))

    dry, live = _both(log, tx)

    edit = _edit_row(live)
    assert edit["ok"] is False and edit["action"].startswith(
        "SKIP: the record of")
    assert _edit_row(dry)["action"] == edit["action"]
    assert find_sidecar(p).read_bytes() == other
    assert json.loads(older.read_text()) == {"doi": NEW}
