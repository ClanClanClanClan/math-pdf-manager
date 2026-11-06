"""A paper's record that cannot be read just now is never written over.

Step-back audit, finding D4-2 (verified 3 of 3). ``PaperIdentity.load``
returns the same blank identity for "no record" and for "a record that
cannot be read" -- damaged bytes, not a JSON object, fields of the wrong
type, or a read error such as a Dropbox file not yet on this Mac. Five
writers loaded, changed a field and saved: the blank went over the real
record, its DOI, arrival date and original name were gone, and Undo then
reported "RESTORED" because it had recorded nothing to restore. Measured
in a synthetic library: filing a paper into a topic while its record was
unreadable erased the DOI and the arrival date.

Now ``save`` raises :class:`RecordUnreadable` and writes nothing when an
identity built from no readable record would land on a record that is
there. Each writer turns that into its own plain "left untouched": the
topic filing refuses before it moves anything, the publication check
lists it as an error, the record merge skips the pair, an arrival keeps
its filing and says so, and a conflict promotion skips the merge.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as hst

from processing.identity import (PaperIdentity, RecordUnreadable, enable_sidecar_mirror,
                                 find_sidecar, record_is_unreadable, record_location,
                                 sidecar_path)

UNREADABLE = {
    "not json": b"{ torn",
    "not utf-8": b"\xff\xfe\x00{\x00}",
    "a list": b"[1, 2, 3]",
    "a string": b'"just a string"',
    "empty file": b"",
}


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _paper(lib, rel="02 - Unpublished papers/S/Smith, J. - Optimal stopping.pdf",
           **fields) -> Path:
    p = lib / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4 " + rel.encode())
    ident = PaperIdentity(doi="10.1/real", first_ingested_at="2019-04-01T00:00:00+00:00",
                          original_filename="Smith, J.-arrival name.pdf", **fields)
    ident.save(p, recompute_hash=True)
    return p


def _spoil(pdf, raw: bytes) -> bytes:
    record_location(pdf).write_bytes(raw)
    return raw


# ------------------------------------------------------------- the rule

@pytest.mark.parametrize("kind", sorted(UNREADABLE))
def test_a_blank_is_never_saved_over_an_unreadable_record(lib, kind):
    pdf = _paper(lib)
    raw = _spoil(pdf, UNREADABLE[kind])
    assert record_is_unreadable(pdf)
    blank = PaperIdentity.load(pdf)
    assert blank.is_new()
    blank.topic_codes.append("07a")
    with pytest.raises(RecordUnreadable, match="left exactly as they were"):
        blank.save(pdf, recompute_hash=False)
    assert record_location(pdf).read_bytes() == raw


def test_it_is_refused_with_an_undo_log_too_and_nothing_is_recorded(lib):
    from processing.undo_log import UndoLog
    pdf = _paper(lib)
    raw = _spoil(pdf, b"{ torn")
    log = UndoLog(log_dir=lib / ".operation_log")
    log.begin_transaction("t")
    with pytest.raises(RecordUnreadable):
        PaperIdentity.load(pdf).save(pdf, recompute_hash=False, undo_log=log)
    assert not log.has_operations()
    log.discard()
    assert record_location(pdf).read_bytes() == raw


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads anything")
def test_a_record_that_cannot_be_opened_is_unreadable_too(lib):
    """The Dropbox case: the file is there, reading it fails."""
    pdf = _paper(lib)
    rec = record_location(pdf)
    before = rec.read_bytes()
    rec.chmod(0)
    try:
        assert record_is_unreadable(pdf)
        with pytest.raises(RecordUnreadable):
            PaperIdentity.load(pdf).save(pdf, recompute_hash=False)
    finally:
        rec.chmod(stat.S_IRUSR | stat.S_IWUSR)
    assert rec.read_bytes() == before


def test_a_paper_with_no_record_still_gets_one(lib):
    """The other side of the same blank: here there is nothing to lose."""
    p = lib / "03 - Working papers" / "A" / "Abel, N. - Elliptic functions.pdf"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"%PDF-1.4 x")
    assert not record_is_unreadable(p)
    PaperIdentity.load(p).save(p)
    assert PaperIdentity.load(p).original_filename == p.name


def test_a_record_read_whole_is_saved_over_as_always(lib):
    pdf = _paper(lib)
    ident = PaperIdentity.load(pdf)
    assert not ident.is_new()
    ident.arxiv_id = "2401.00001"
    ident.save(pdf, recompute_hash=False)
    back = PaperIdentity.load(pdf)
    assert (back.doi, back.arxiv_id) == ("10.1/real", "2401.00001")


def test_an_identity_read_whole_may_repair_a_record_spoiled_since(lib):
    """Read before the record went bad, it carries the real details:
    writing them back loses nothing (and is the only way back)."""
    pdf = _paper(lib)
    ident = PaperIdentity.load(pdf)
    _spoil(pdf, b"{ torn")
    ident.save(pdf, recompute_hash=False)
    assert PaperIdentity.load(pdf).doi == "10.1/real"


@settings(max_examples=80, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(raw=hst.binary(max_size=200))
def test_property_whatever_the_bytes_a_blank_never_replaces_them(tmp_path_factory, raw):
    """Any bytes at all in the record: either load() reads them (and the
    identity is not blank), or save() of the blank leaves them as they
    are."""
    lib = tmp_path_factory.mktemp("lib")
    enable_sidecar_mirror(lib)
    pdf = _paper(lib)
    _spoil(pdf, raw)
    ident = PaperIdentity.load(pdf)
    if ident.is_new():
        with pytest.raises(RecordUnreadable):
            ident.save(pdf, recompute_hash=False)
        assert record_location(pdf).read_bytes() == raw
    else:
        ident.save(pdf, recompute_hash=False)   # it was readable: fine


# ------------------------------------------------------- the five writers

def test_filing_into_a_topic_refuses_before_it_moves_anything(lib):
    from processing.publication_topic_router import file_into_topic
    from processing.undo_log import UndoLog
    pdf = _paper(lib)
    (lib / "07a - BSDEs").mkdir()
    raw = _spoil(pdf, b"{ torn")
    log = UndoLog(log_dir=lib / ".operation_log")
    log.begin_transaction("Bulk topic apply: 1 paper(s)")
    ok, msg = file_into_topic(pdf, "07a", lib, undo_log=log)
    assert not ok and "could not be read just now" in msg
    assert not log.has_operations()
    log.discard()
    assert pdf.exists() and record_location(pdf).read_bytes() == raw
    assert not (lib / ".mathpdf-config").exists() or not any(
        (lib / ".mathpdf-config").rglob("*pending*")), "the vocabulary queue was written"


def test_the_publication_check_lists_it_and_leaves_it(lib):
    from processing.publication_state import update_publication_state
    pdf = _paper(lib)
    raw = _spoil(pdf, b"{ torn")
    s = update_publication_state([{"file": str(pdf), "published": False}])
    assert s.errors and "could not be read just now" in s.errors[0]
    assert not s.checked
    assert record_location(pdf).read_bytes() == raw


def test_the_record_merge_skips_a_record_spoiled_since_the_plan(lib):
    from tests.safety.test_two_records_become_one import _full_name_record, _pdf, _write
    from processing.sidecar_repair import apply_record_merges, plan_record_merges
    pdf = _pdf(lib)
    coded, full = sidecar_path(pdf), _full_name_record(lib, pdf)
    _write(full, {"content_sha256": "abc", "doi": "10.3934/x",
                  "first_ingested_at": "2022-03-08T13:14:33+00:00"}, age_days=60)
    _write(coded, {"content_sha256": "abc", "arxiv_id": "2406.10876",
                   "first_ingested_at": "2022-03-08T13:14:33+00:00"}, age_days=1)
    plan = plan_record_merges(lib)
    assert len(plan) == 1
    coded.write_bytes(b"{ torn")
    res = apply_record_merges(lib, plan)
    assert res["merged"] == []
    assert res["skipped"] == [{"pdf": pdf.name, "reason": "its record could not be "
                               "read just now; left untouched"}]
    assert coded.read_bytes() == b"{ torn" and full.exists()


def test_an_arrival_keeps_its_filing_and_says_its_record_was_left(lib, monkeypatch):
    """Arrival files the PDF first and writes its record after; a record it
    cannot read at that moment is left, and the result says so."""
    from processing import ingest
    from tests.test_processing.test_corroboration_and_registry import pdf_with_body
    for d in ("01 - Published papers", "03 - Working papers", "12 - To be sorted"):
        (lib / d).mkdir(parents=True, exist_ok=True)
    src = pdf_with_body(lib / "12 - To be sorted" / "drop.pdf",
                        title="Random matrix theory and free probability",
                        author="Roland Speicher",
                        body="\n".join(["Roland Speicher studies free probability."] * 14))
    real_save = PaperIdentity.save

    def _unreadable_at_the_shelf(self, pdf_path, **k):
        if "12 - To be sorted" not in Path(pdf_path).parts:
            raise RecordUnreadable(f"the saved details of {Path(pdf_path).name} could "
                                   f"not be read just now, so they were left exactly "
                                   f"as they were")
        return real_save(self, pdf_path, **k)

    monkeypatch.setattr(PaperIdentity, "save", _unreadable_at_the_shelf)
    res = ingest.ingest_paper(src, library_root=lib, status="working", dry_run=False)
    assert res["success"], res.get("error")
    assert any(a.startswith("WARNING: the saved details of") for a in res["actions"])


def test_promoting_a_conflict_copy_skips_the_merge_and_keeps_both_records(lib):
    from processing.conflict_resolver import resolve_keep_conflict
    canonical = _paper(lib)
    conflict = canonical.with_name(canonical.stem + " (conflicted copy).pdf")
    conflict.write_bytes(b"%PDF-1.4 the other copy")
    sidecar_path(conflict).write_bytes(b"{ torn")
    ok, _msg = resolve_keep_conflict(conflict, lib, canonical=canonical)
    assert ok
    assert canonical.read_bytes() == b"%PDF-1.4 the other copy"
    assert record_location(canonical).read_bytes() == b"{ torn", (
        "the promoted copy's own record travelled with it, untouched")
    trashed = [t for t in lib.rglob("*.meta.json") if ".trash" in t.parts]
    assert any(json.loads(t.read_text()).get("doi") == "10.1/real" for t in trashed), (
        f"the retired canonical's record went to the trash, readable: {trashed}")
