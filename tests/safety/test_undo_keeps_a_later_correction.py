"""Undoing an older change never overwrites a correction made since.

Step-back audit, finding D4-3 (verified 3 of 3). A ``sidecar_edit`` in the
undo log records ``field -> [old, new]``, and undo put ``old`` back
whatever the field held by then. Undo an entry from last month and a DOI
corrected by hand last week went back to last month's wrong one, without
a word. (0 real cases so far: no real entry has been undone since April.)

Now undo puts the fields back only while each still holds what the edit
wrote, or already holds what it replaced; a third value is a correction
made since, and the edit is KEPT -- all its fields, so the record never
matches neither moment -- with the undo saying which field moved. The
preview says the same. ``PaperIdentity.save`` now records the values it
actually writes (fingerprint and name filled in first), so its own
bookkeeping cannot look like a correction.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as hst

from processing.identity import (PaperIdentity, enable_sidecar_mirror, patch_record,
                                 record_location)
from processing.undo_log import UndoLog


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _paper(lib, doi="10.1/A") -> Path:
    p = lib / "01 - Published papers" / "S" / "Smith, J. - Reflected BSDEs.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4 paper")
    PaperIdentity(doi=doi).save(p)
    return p


def _edit(lib, pdf, **values) -> tuple[UndoLog, str]:
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("an older change")
    patch_record(pdf, values, undo_log=log)
    log.commit()
    return log, tx


def _doi(pdf):
    return json.loads(record_location(pdf).read_text()).get("doi")


def test_a_doi_corrected_since_is_kept_and_undo_says_so(lib):
    pdf = _paper(lib)
    log, tx = _edit(lib, pdf, doi="10.1/B")
    patch_record(pdf, {"doi": "10.1/C"})          # his correction, later
    dry = log.undo_transaction(tx, dry_run=True)
    live = log.undo_transaction(tx)
    for rows in (dry, live):
        (row,) = rows
        assert row["ok"] is False
        assert row["action"].startswith("KEPT: doi changed since")
    assert _doi(pdf) == "10.1/C"


def test_with_nothing_changed_since_undo_puts_it_back(lib):
    """Pin: the guard is not simply refusing every field undo."""
    pdf = _paper(lib)
    log, tx = _edit(lib, pdf, doi="10.1/B")
    assert log.undo_transaction(tx, dry_run=True)[0]["action"].startswith("WOULD RESTORE")
    assert log.undo_transaction(tx)[0]["ok"] is True
    assert _doi(pdf) == "10.1/A"


def test_a_field_already_back_at_its_old_value_is_no_conflict(lib):
    pdf = _paper(lib)
    log, tx = _edit(lib, pdf, doi="10.1/B")
    patch_record(pdf, {"doi": "10.1/A"})          # set back by hand
    (row,) = log.undo_transaction(tx)
    assert row["ok"] is True and _doi(pdf) == "10.1/A"


def test_one_field_moved_keeps_the_whole_edit(lib):
    """Half an edit put back would leave a record matching neither moment."""
    pdf = _paper(lib)
    log, tx = _edit(lib, pdf, doi="10.1/B", arxiv_id="2401.00001")
    patch_record(pdf, {"arxiv_id": "2401.99999"})
    (row,) = log.undo_transaction(tx)
    assert row["ok"] is False and "arxiv_id" in row["action"] and "doi" not in row["action"]
    rec = json.loads(record_location(pdf).read_text())
    assert (rec["doi"], rec["arxiv_id"]) == ("10.1/B", "2401.99999")


def test_a_field_the_edit_added_and_someone_changed_counts_as_moved(lib):
    pdf = _paper(lib)
    log, tx = _edit(lib, pdf, brand_new="x")
    patch_record(pdf, {"brand_new": "y"})
    assert log.undo_transaction(tx)[0]["ok"] is False


def test_a_field_the_edit_removed_round_trips(lib):
    pdf = _paper(lib)
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("remove")
    patch_record(pdf, {}, remove=["doi"], undo_log=log)
    log.commit()
    assert _doi(pdf) is None
    assert log.undo_transaction(tx)[0]["ok"] is True
    assert _doi(pdf) == "10.1/A"


def test_the_same_field_edited_twice_in_one_change_comes_all_the_way_back(lib):
    """The preview reads the record as it is now; by the time undo reaches
    the first edit it has already undone the second."""
    pdf = _paper(lib)
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("two edits")
    patch_record(pdf, {"doi": "10.1/B"}, undo_log=log)
    patch_record(pdf, {"doi": "10.1/C"}, undo_log=log)
    log.commit()
    dry = log.undo_transaction(tx, dry_run=True)
    assert all(r["ok"] for r in dry), dry
    live = log.undo_transaction(tx)
    assert all(r["ok"] for r in live), live
    assert _doi(pdf) == "10.1/A"


def test_a_later_edit_skipped_by_an_earlier_press_is_not_assumed_undone(lib):
    from processing.undo_log import _fields_after_later_edits
    ops = [{"type": "sidecar_edit", "path": "/p.pdf", "changes": {"doi": ["A", "B"]}},
           {"type": "sidecar_edit", "path": "/p.pdf", "changes": {"doi": ["B", "C"]}}]
    assert _fields_after_later_edits(ops, 0, set(), {"doi": "C"}) == ({"doi": "B"}, set())
    # Edit 1 was undone by an earlier press (record back at B), and the DOI
    # was corrected to C since: the preview must see C, not assume edit 1
    # is still to be undone and predict B.
    assert _fields_after_later_edits(ops, 0, {1}, {"doi": "C"}) == ({"doi": "C"}, set())
    other = [ops[0], dict(ops[1], path="/renamed.pdf")]
    assert _fields_after_later_edits(other, 0, set(), {"doi": "C"}) == ({"doi": "C"}, {"doi"})


def test_saving_a_record_notes_what_it_wrote_not_what_it_meant_to(lib):
    """save() fills in the fingerprint after the edit is noted; noted
    before, the new fingerprint would look like a correction made since."""
    pdf = _paper(lib)
    old_hash = json.loads(record_location(pdf).read_text())["content_sha256"]
    pdf.write_bytes(b"%PDF-1.4 the same paper, re-downloaded")
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("re-hash")
    ident = PaperIdentity.load(pdf)
    ident.doi = "10.1/B"
    ident.save(pdf, undo_log=log)                  # recompute_hash=True
    log.commit()
    written = json.loads(record_location(pdf).read_text())["content_sha256"]
    assert written != old_hash
    ops = json.loads((log.log_dir / f"{tx}.json").read_text())["operations"]
    (edit,) = [o for o in ops if o["type"] == "sidecar_edit"]
    assert edit["changes"]["content_sha256"] == [old_hash, written]
    assert log.undo_transaction(tx)[0]["ok"] is True
    rec = json.loads(record_location(pdf).read_text())
    assert (rec["doi"], rec["content_sha256"]) == ("10.1/A", old_hash)


_V = hst.sampled_from(["A", "B", "C", "D", None, 1, ["x"]])


@settings(max_examples=80, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(old=_V, new=_V, later=_V)
def test_property_undo_restores_iff_the_field_is_old_or_new(tmp_path_factory, old, new, later):
    from processing.undo_log import edited_fields_blocker
    changes = {"doi": [old, new]}
    blocked = bool(edited_fields_blocker({"doi": later}, changes))
    assert blocked == (later not in (old, new))
