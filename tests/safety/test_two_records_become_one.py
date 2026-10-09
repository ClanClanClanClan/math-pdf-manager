"""A paper with two saved records gets one, losing nothing -- and no new pairs form.

The owner's decision 4A, 2026-10-09. Eight papers had two records: an
older one under the full name and a newer one at the coded location
used for names near the length limit. The app read only the coded one,
so it could not see paper 4's DOI or papers 3-6's cached text. Every
pair was the same paper (same fingerprint); each copy merely held
fields the other lacked.

Cause: ``PaperIdentity.load`` and ``save`` looked only where a NEW record
would go. When only the full-name record existed, load returned a blank
identity and the next save wrote a second record beside it.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from processing.identity import (
    MAX_BASENAME_BYTES, MIRROR_DIR_NAME, PaperIdentity, enable_sidecar_mirror,
    find_sidecar, record_location, sidecar_path,
)
from processing.sidecar_repair import apply_record_merges, plan_record_merges


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _pdf(lib, extra=2):
    """A name whose record name is 251+extra bytes: allowed on disk under
    its full name, but beyond sidecar_path's limit, so primary = coded."""
    head = "Smith, J. - "
    stem = head + "x" * (MAX_BASENAME_BYTES + extra - len(".meta.json") - len(head))
    p = lib / "01 - Published papers" / "S" / f"{stem}.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4 the paper")
    return p


def _full_name_record(lib, pdf) -> Path:
    return lib / MIRROR_DIR_NAME / pdf.relative_to(lib).parent / (pdf.stem + ".meta.json")


def _write(path: Path, data: dict, age_days: float = 0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, **data}))
    t = time.time() - age_days * 86400
    os.utime(path, (t, t))


def _records(lib):
    return sorted(p for p in (lib / MIRROR_DIR_NAME).rglob("*.meta.json"))


# ------------------------------------------------------ the reader / writer

def test_a_record_only_at_the_full_name_is_read_not_blank(lib):
    pdf = _pdf(lib)
    full = _full_name_record(lib, pdf)
    _write(full, {"doi": "10.1/kept"})
    assert sidecar_path(pdf) != full, "control: the primary place is the coded one"
    assert record_location(pdf) == full
    assert PaperIdentity.load(pdf).doi == "10.1/kept"


def test_saving_it_does_not_create_a_second_record(lib):
    """The mechanism behind all eight pairs."""
    pdf = _pdf(lib)
    full = _full_name_record(lib, pdf)
    _write(full, {"doi": "10.1/kept"})
    ident = PaperIdentity.load(pdf)
    ident.arxiv_id = "2401.00001"
    ident.save(pdf, recompute_hash=False)
    assert _records(lib) == [full], "a second record was written"
    d = json.loads(full.read_text())
    assert d["doi"] == "10.1/kept" and d["arxiv_id"] == "2401.00001"


def test_the_common_case_is_unchanged(lib):
    pdf = lib / "01 - Published papers" / "S" / "Smith, J. - Short.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4")
    assert record_location(pdf) == sidecar_path(pdf)
    PaperIdentity().save(pdf, recompute_hash=True)
    assert _records(lib) == [sidecar_path(pdf)]


# ---------------------------------------------------------------- the merge

@pytest.fixture
def pair(lib):
    pdf = _pdf(lib)
    coded = sidecar_path(pdf)
    full = _full_name_record(lib, pdf)
    _write(full, {"content_sha256": "abc", "doi": "10.3934/x", "classifier_text": "first pages",
                  "original_filename": "Smith, J.-the arrival name.pdf",
                  "first_ingested_at": "2022-03-08T13:14:33+00:00"}, age_days=60)
    _write(coded, {"content_sha256": "abc", "arxiv_id": "2406.10876",
                   "original_filename": "Smith, J. - the later name.pdf",
                   "first_ingested_at": "2022-03-08T13:14:33+00:00"}, age_days=1)
    return lib, pdf, coded, full


def test_the_plan_fills_gaps_and_takes_arrival_from_the_older_copy(pair):
    lib, pdf, coded, full = pair
    (item,) = plan_record_merges(lib)
    assert item["fill"] == {"doi": "10.3934/x", "classifier_text": "first pages"}
    assert item["arrival"] == {"original_filename": "Smith, J.-the arrival name.pdf"}
    assert item["conflicts"] == [] and item["refused"] is None


def test_applying_keeps_everything_in_one_record_and_retires_the_other(pair):
    lib, pdf, coded, full = pair
    res = apply_record_merges(lib, plan_record_merges(lib))
    assert [m["pdf"] for m in res["merged"]] == [pdf.name] and res["tx_id"]
    d = json.loads(coded.read_text())
    assert (d["doi"], d["arxiv_id"], d["classifier_text"]) == ("10.3934/x", "2406.10876", "first pages")
    assert d["original_filename"] == "Smith, J.-the arrival name.pdf"
    assert not full.exists() and _records(lib) == [coded]
    retired = list((lib / ".trash" / "duplicate_records").rglob("*.meta.json"))
    assert len(retired) == 1, "retired to the trash, not deleted"
    assert plan_record_merges(lib) == []


def test_the_merge_is_undoable(pair):
    from processing.undo_log import UndoLog
    lib, pdf, coded, full = pair
    before_full, before_coded = full.read_text(), json.loads(coded.read_text())
    res = apply_record_merges(lib, plan_record_merges(lib))
    UndoLog(log_dir=lib / ".operation_log").undo_transaction(res["tx_id"])
    assert full.read_text() == before_full
    after = json.loads(coded.read_text())
    for k in ("doi", "classifier_text", "original_filename", "arxiv_id"):
        # (a saved record carries every field; "" and absent both mean empty)
        assert (after.get(k) or None) == (before_coded.get(k) or None), k


def test_a_real_conflict_keeps_the_apps_value_and_is_reported(pair):
    lib, pdf, coded, full = pair
    d = json.loads(full.read_text()); d["arxiv_id"] = "1999.99999"
    _write(full, d, age_days=60)
    (item,) = plan_record_merges(lib)
    assert item["conflicts"] == ["arxiv_id"]
    res = apply_record_merges(lib, [item])
    assert json.loads(coded.read_text())["arxiv_id"] == "2406.10876"
    assert res["merged"][0]["conflicts"] == ["arxiv_id"]


def test_two_records_of_different_contents_are_never_merged(pair):
    lib, pdf, coded, full = pair
    d = json.loads(full.read_text()); d["content_sha256"] = "zzz"
    _write(full, d, age_days=60)
    (item,) = plan_record_merges(lib)
    assert item["refused"]
    res = apply_record_merges(lib, [item])
    assert res["merged"] == [] and full.exists()


def test_arrival_comes_from_the_older_copy_whichever_it_is(pair):
    lib, pdf, coded, full = pair
    os.utime(full, None)                                   # full-name now NEWER
    t = time.time() - 90 * 86400
    os.utime(coded, (t, t))
    (item,) = plan_record_merges(lib)
    assert item["arrival"] == {}, "the coded copy is older now, so its arrival name stands"


def test_a_plan_overtaken_by_events_is_skipped(pair):
    lib, pdf, coded, full = pair
    plan = plan_record_merges(lib)
    full.unlink()
    res = apply_record_merges(lib, plan)
    assert res["merged"] == [] and "changed since" in res["skipped"][0]["reason"]


def test_conformance_stops_reporting_the_pair(pair):
    from maintenance.conformance import check_sidecars
    from processing.identity import iter_pdfs
    lib, pdf, coded, full = pair
    pdfs = list(iter_pdfs(lib))
    assert any(f.reason == "two-sidecar-records" for f in check_sidecars(lib, pdfs)[0])
    apply_record_merges(lib, plan_record_merges(lib))
    assert not any(f.reason == "two-sidecar-records" for f in check_sidecars(lib, pdfs)[0])


def test_the_common_case_does_not_pay_for_the_wider_search(lib, monkeypatch):
    """record_location tries the primary place first. Measured 2026-10-09:
    the candidate search costs 1.9 s per 29,761 PDFs against 0.95 s for
    the primary path alone, and load runs over the whole library."""
    import processing.identity as ident
    pdf = lib / "01 - Published papers" / "S" / "Smith, J. - Short.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4")
    PaperIdentity().save(pdf, recompute_hash=True)

    def _boom(*a, **k):
        raise AssertionError("searched every candidate although the record was at the primary place")
    monkeypatch.setattr(ident, "find_sidecar", _boom)
    assert PaperIdentity.load(pdf).content_sha256
