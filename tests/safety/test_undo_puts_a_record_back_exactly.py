"""Undoing a move or rename puts the paper's record back exactly as it was.

``logged_move`` and ``logged_rename`` carry a paper's record with it, then
rewrite its ``copy_locations`` to name the new place. That rewrite went
through ``PaperIdentity.save`` and OUTSIDE the undo log, so:

  * after undo the record still named the place the paper had been moved
    to -- for a retirement, the trash (found 2026-10-09);
  * every move rewrote the WHOLE record, adding each field it predated:
    measured 2026-10-10, 27,130 of the 29,367 live records lack at least
    one (``title_source``, ``identification_state``, ...), so the record
    that came back from an undo was not the one that left.

Now the move changes ``copy_locations`` and nothing else
(``identity.patch_record``), records the old value, and undo restores it
the same way: byte for byte.
"""
from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from processing.identity import (
    MAX_BASENAME_BYTES, MIRROR_DIR_NAME, enable_sidecar_mirror, find_sidecar,
    patch_record, sidecar_path,
)
from processing.undo_log import UndoLog, logged_move, logged_rename

#: The shape most of the real library has: written before the four
#: identification fields existed.
OLD_SCHEMA = {
    "schema_version": 1, "content_sha256": "ab" * 32, "original_filename": "x.pdf",
    "doi": "10.1/x", "arxiv_id": "", "first_ingested_at": "2025-01-01T00:00:00",
    "first_ingest_tx_id": "", "copy_locations": [], "publication_checks": [],
    "recheck_count": 0, "last_check_date": "", "permanently_unpublished": False,
    "topic_codes": ["07a"], "topic_suggestion": "", "topic_confidence": 0.0,
    "classifier_text": "first page", "classifier_text_tried": True,
}


def _dump(d: dict) -> str:
    return json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True)


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _stem(kind: str) -> str:
    head = "Smith, J. - "
    if kind == "ordinary":
        return head + "A result"
    if kind == "nfd":
        return unicodedata.normalize("NFD", "Élie, R. - Équations rétrogrades")
    if kind == "over-long":
        return head + "x" * (250 - len(head))
    n = int(kind.rsplit("-", 1)[1])
    return head + "y" * (n - len(".meta.json") - len(head))


def _paper(lib, kind="ordinary", record=None, folder="01 - Published papers/S"):
    pdf = lib / folder / f"{_stem(kind)}.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4 " + pdf.name.encode())
    rec = (lib / MIRROR_DIR_NAME / folder / f"{pdf.stem}.meta.json"
           if kind.startswith("full-name") else sidecar_path(pdf))
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(_dump(dict(OLD_SCHEMA if record is None else record)),
                   encoding="utf-8")
    assert find_sidecar(pdf) == rec
    return pdf, rec


def _tx(lib):
    log = UndoLog(log_dir=lib / ".operation_log")
    return log, log.begin_transaction("t")


KINDS = ("ordinary", "over-long", "full-name-252", "full-name-255", "nfd")


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("how", ["move", "rename"])
def test_an_undone_move_leaves_the_record_byte_for_byte(lib, kind, how):
    pdf, rec = _paper(lib, kind)
    before = rec.read_bytes()
    log, tx = _tx(lib)
    if how == "move":
        dest = lib / "03 - Working papers" / "S" / pdf.name
        logged_move(pdf, dest, undo_log=log)
    else:
        dest = pdf.with_name("Smith, J. - Renamed.pdf")
        logged_rename(pdf, dest, undo_log=log)
    log.commit()
    assert json.loads(find_sidecar(dest).read_text())["copy_locations"] == [str(dest)]
    results = log.undo_transaction(tx)
    assert all(r["ok"] for r in results), results
    assert rec.read_bytes() == before, "the record that came back is not the one that left"


@pytest.mark.parametrize("how", ["move", "rename"])
def test_a_move_changes_copy_locations_and_nothing_else(lib, how):
    """No field the record predates is added; nothing it holds is dropped."""
    record = dict(OLD_SCHEMA, a_field_from_a_newer_app="kept")
    pdf, rec = _paper(lib, record=record)
    log, tx = _tx(lib)
    dest = (lib / "03 - Working papers" / "S" / pdf.name if how == "move"
            else pdf.with_name("Smith, J. - Renamed.pdf"))
    (logged_move if how == "move" else logged_rename)(pdf, dest, undo_log=log)
    after = json.loads(find_sidecar(dest).read_text())
    assert {k for k in set(after) | set(record) if after.get(k) != record.get(k)} \
        == {"copy_locations"}
    edits = [op for op in log._current_tx["operations"] if op["type"] == "sidecar_edit"]
    assert [list(op["changes"]) for op in edits] == [["copy_locations"]]
    assert edits[0]["path"] == str(dest), "recorded where the record is after the move"


def test_a_record_without_copy_locations_gets_none_back_on_undo(lib):
    record = {k: v for k, v in OLD_SCHEMA.items() if k != "copy_locations"}
    pdf, rec = _paper(lib, record=record)
    before = rec.read_bytes()
    log, tx = _tx(lib)
    dest = pdf.with_name("Smith, J. - Renamed.pdf")
    logged_rename(pdf, dest, undo_log=log)
    log.commit()
    ops = json.loads((lib / ".operation_log" / f"{tx}.json").read_text())["operations"]
    [edit] = [op for op in ops if op["type"] == "sidecar_edit"]
    assert edit["absent"] == ["copy_locations"]
    log.undo_transaction(tx)
    assert rec.read_bytes() == before and "copy_locations" not in json.loads(before)


def test_topic_copies_renamed_with_the_paper_come_back_with_the_record(lib):
    pdf, rec = _paper(lib)
    topic = lib / "07a - BSDEs" / pdf.name
    topic.parent.mkdir(parents=True)
    os.link(pdf, topic)
    record = dict(OLD_SCHEMA, copy_locations=[str(pdf), str(topic)])
    rec.write_text(_dump(record), encoding="utf-8")
    before = rec.read_bytes()
    log, tx = _tx(lib)
    new = pdf.with_name("Smith, J. - Renamed.pdf")
    logged_rename(pdf, new, undo_log=log)
    log.commit()
    assert (topic.parent / new.name).exists() and not topic.exists()
    assert json.loads(find_sidecar(new).read_text())["copy_locations"] == [
        str(new), str(topic.parent / new.name)]
    results = log.undo_transaction(tx)
    assert all(r["ok"] for r in results), results
    assert topic.exists() and rec.read_bytes() == before


def test_a_topic_copy_rename_alone_is_undone_too(lib):
    """The record already lists the new name, so the canonical entry needs
    no change and only the topic copy's entry moves -- that edit alone
    has to be in the log."""
    pdf, rec = _paper(lib)
    new = pdf.with_name("Smith, J. - Renamed.pdf")
    topic = lib / "07a - BSDEs" / pdf.name
    topic.parent.mkdir(parents=True)
    os.link(pdf, topic)
    rec.write_text(_dump(dict(OLD_SCHEMA, copy_locations=[str(new), str(topic)])),
                   encoding="utf-8")
    before = rec.read_bytes()
    log, tx = _tx(lib)
    logged_rename(pdf, new, undo_log=log)
    log.commit()
    assert json.loads(find_sidecar(new).read_text())["copy_locations"] == [
        str(new), str(topic.parent / new.name)]
    assert all(r["ok"] for r in log.undo_transaction(tx))
    assert topic.exists() and rec.read_bytes() == before


def test_an_undo_whose_record_has_gone_says_so_and_stays_retryable(lib):
    pdf, rec = _paper(lib)
    log, tx = _tx(lib)
    dest = pdf.with_name("Smith, J. - Renamed.pdf")
    logged_rename(pdf, dest, undo_log=log)
    log.commit()
    find_sidecar(dest).unlink()
    results = log.undo_transaction(tx)
    assert results[0]["action"].startswith("SKIP: no sidecar to restore")
    stored = json.loads((lib / ".operation_log" / f"{tx}.json").read_text())
    assert stored["undone"] is False and stored["partial_undo"]


def test_the_dry_run_still_only_describes(lib):
    pdf, rec = _paper(lib)
    log, tx = _tx(lib)
    dest = pdf.with_name("Smith, J. - Renamed.pdf")
    logged_rename(pdf, dest, undo_log=log)
    log.commit()
    moved = find_sidecar(dest).read_bytes()
    actions = log.undo_transaction(tx, dry_run=True)
    assert actions[0]["action"] == "WOULD RESTORE sidecar fields ['copy_locations'] on " + dest.name
    assert find_sidecar(dest).read_bytes() == moved


# ------------------------------------------------------------ patch_record

def test_patch_record_answers_three_ways(lib):
    pdf, rec = _paper(lib)
    log, tx = _tx(lib)
    assert patch_record(pdf, {"doi": "10.1/x"}, undo_log=log) is False
    assert log._current_tx["operations"] == [], "nothing changed, nothing recorded"
    assert patch_record(pdf, {"doi": "10.1/y"}, remove=["arxiv_id"], undo_log=log) is True
    [op] = log._current_tx["operations"]
    assert op["changes"] == {"arxiv_id": ["", None], "doi": ["10.1/x", "10.1/y"]}
    assert "absent" not in op
    assert patch_record(lib / "nobody.pdf", {"doi": "z"}) is None
    rec.write_text("{ not json")
    assert patch_record(pdf, {"doi": "z"}) is None
    rec.write_text("[1, 2]")
    assert patch_record(pdf, {"doi": "z"}) is None


@pytest.mark.parametrize("kind", KINDS)
def test_patch_record_round_trips_through_undo(lib, kind):
    """In place, not after a move: a field edit undone on a paper whose
    record sits at its full-name location (252-255 bytes) must find it
    there, not where a new one would go."""
    pdf, rec = _paper(lib, kind)
    before = rec.read_bytes()
    log, tx = _tx(lib)
    patch_record(pdf, {"doi": "10.1/y", "brand_new": [1]}, remove=["arxiv_id"],
                 undo_log=log)
    log.commit()
    assert json.loads(rec.read_text())["brand_new"] == [1]
    log.undo_transaction(tx)
    assert rec.read_bytes() == before


# ------------------------------------------------------------ the property

_FIELD_VALUES = st.one_of(st.text(max_size=8), st.integers(-3, 3), st.booleans(),
                          st.lists(st.text(max_size=5), max_size=2), st.none())


@settings(max_examples=60, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(drop=st.sets(st.sampled_from(sorted(OLD_SCHEMA)), max_size=6),
       extra=st.dictionaries(st.text("abcxyz_", min_size=1, max_size=6),
                             _FIELD_VALUES, max_size=3),
       kind=st.sampled_from(KINDS),
       how=st.sampled_from(["move", "rename", "move+rename"]),
       already_listed=st.booleans())
def test_any_record_comes_back_from_any_undo_byte_for_byte(
        tmp_path, drop, extra, kind, how, already_listed):
    lib = Path(tempfile.mkdtemp(dir=tmp_path))
    enable_sidecar_mirror(lib)
    record = {k: v for k, v in OLD_SCHEMA.items() if k not in drop}
    record.update({f"x_{k}": v for k, v in extra.items()})
    pdf, rec = _paper(lib, kind, record=record)
    if already_listed:
        record["copy_locations"] = [str(pdf), "/elsewhere/a copy.pdf"]
        rec.write_text(_dump(record), encoding="utf-8")
    before = rec.read_bytes()
    log, tx = _tx(lib)
    dest = {"move": lib / "03 - Working papers" / "S" / pdf.name,
            "rename": pdf.with_name("Smith, J. - Renamed.pdf"),
            "move+rename": lib / "03 - Working papers" / "S" / "Smith, J. - B.pdf"}[how]
    (logged_rename if how == "rename" else logged_move)(pdf, dest, undo_log=log)
    log.commit()
    after = json.loads(find_sidecar(dest).read_text())
    assert {k for k in set(after) | set(record)
            if after.get(k, "ABSENT") != record.get(k, "ABSENT")} <= {"copy_locations"}
    assert str(dest) in after["copy_locations"] and str(pdf) not in after["copy_locations"]
    assert all(r["ok"] for r in log.undo_transaction(tx))
    assert rec.read_bytes() == before
