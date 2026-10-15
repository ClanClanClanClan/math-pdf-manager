""""Fill in missing details" completes a record that lacks its fingerprint
and filing date.

Measured 2026-10-15 on the real library (read-only): 147 records had
neither -- made with the cached text alone by the first "Cache
abstracts", and passed over by "Fill in missing details" ever since,
because the paper had a record. Without a fingerprint a record cannot be
matched to its paper again after a Finder rename, and "Check they still
match" has nothing to compare. 20 of the 147 papers also have an older
record left behind by a rename; that stays where it is.
"""
from __future__ import annotations

import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from processing.identity import (FROM_THE_FILE, PaperIdentity,
                                 backfill_directory, complete_record,
                                 compute_content_hash, enable_sidecar_mirror,
                                 filing_date, find_sidecar, sidecar_path)
from processing.sidecar_repair import find_orphans, plan_reconnect
from processing.undo_log import UndoLog

FAST = settings(max_examples=60, deadline=None,
                suppress_health_check=[HealthCheck.function_scoped_fixture])


@contextmanager
def _library():
    old = os.environ.get("MATH_LIBRARY")
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "Maths"
        (root / "01 - Published papers/S").mkdir(parents=True)
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


def _pdf(root: Path, name: str) -> Path:
    p = root / "01 - Published papers/S" / name
    p.write_bytes(f"%PDF-1.4\n% {name}\n".encode())
    return p


def _write(pdf: Path, data) -> Path:
    path = sidecar_path(pdf)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False,
                               sort_keys=True), encoding="utf-8")
    return path


#: What the first "Cache abstracts" left: every field ``save`` writes,
#: the text, and a blank fingerprint and filing date.
def _sparse(pdf: Path) -> dict:
    from dataclasses import asdict
    ident = PaperIdentity(classifier_text="first pages", arxiv_id="2401.00001",
                          original_filename=pdf.name)
    return {k: v for k, v in asdict(ident).items() if not k.startswith("_")}


def _log(root: Path) -> UndoLog:
    log = UndoLog(log_dir=root / ".operation_log")
    log.begin_transaction("fill in missing details")
    return log


def _undo(log: UndoLog) -> list:
    tx = log._tx_id
    log.commit()
    return log.undo_transaction(tx)


STATE = st.sampled_from(["absent", "blank", "set"])


@FAST
@given(hash_state=STATE, date_state=STATE,
       others=st.dictionaries(
           st.sampled_from(["doi", "arxiv_id", "classifier_text", "topic_codes",
                            "original_filename", "a_field_from_the_future"]),
           st.one_of(st.sampled_from(["", "x", "10.1/y"]), st.lists(st.just("07a"),
                                                                    max_size=2)),
           max_size=5))
def test_exactly_the_blank_ones_are_filled_and_undo_gives_the_record_back(
        hash_state, date_state, others):
    with _library() as root:
        pdf = _pdf(root, "Smith, J. - Paper.pdf")
        data = dict(others)
        for field, state, kept in (("content_sha256", hash_state, "cd" * 32),
                                   ("first_ingested_at", date_state,
                                    "2019-01-01T00:00:00+00:00")):
            if state == "blank":
                data[field] = ""
            elif state == "set":
                data[field] = kept
        rec = _write(pdf, data)
        original = rec.read_bytes()
        log = _log(root)

        changed = complete_record(pdf, undo_log=log)

        now = json.loads(rec.read_text(encoding="utf-8"))
        want = dict(data)
        if hash_state != "set":
            want["content_sha256"] = compute_content_hash(pdf)
        if date_state != "set":
            want["first_ingested_at"] = filing_date(pdf)
        assert now == want, "a field it does not own changed, or one was missed"
        assert changed is (hash_state != "set" or date_state != "set")
        assert complete_record(pdf) is False, "a second pass changed something"
        rows = _undo(log)
        assert all(r["ok"] for r in rows), rows
        assert rec.read_bytes() == original


def test_no_record_or_an_unreadable_one_is_not_touched(lib):
    bare = _pdf(lib, "Smith, J. - Bare.pdf")
    assert complete_record(bare) is None and find_sidecar(bare) is None
    for body in (b'{"doi": "10.1/half", ', b'["a", "list"]'):
        pdf = _pdf(lib, "Tan, X. - Broken.pdf")
        rec = sidecar_path(pdf)
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_bytes(body)
        assert complete_record(pdf) is None
        assert rec.read_bytes() == body


def test_a_file_that_cannot_be_read_gets_its_date_and_no_blank_fingerprint(lib):
    """The fingerprint is a hash of the file; an unreadable file hashes to
    "", and writing that would only look like a value."""
    pdf = _pdf(lib, "Smith, J. - Locked.pdf")
    rec = _write(pdf, {"original_filename": pdf.name, "doi": "10.1/x"})
    os.chmod(pdf, 0)
    try:
        if os.access(pdf, os.R_OK):                    # pragma: no cover
            pytest.skip("running as a user who can read anything")
        assert complete_record(pdf) is True
        data = json.loads(rec.read_text(encoding="utf-8"))
        assert "content_sha256" not in data
        assert data["first_ingested_at"] == filing_date(pdf)
        before = rec.read_bytes()
        assert complete_record(pdf) is False
        assert rec.read_bytes() == before
    finally:
        os.chmod(pdf, stat.S_IRUSR | stat.S_IWUSR)


def test_the_two_fields_are_the_ones_a_new_record_gets():
    """One rule: what completing fills is what a record made from nothing
    is given from the file."""
    with _library() as root:
        a = _pdf(root, "Smith, J. - A.pdf")
        from processing.identity import backfill_sidecar
        backfill_sidecar(a)
        made = json.loads(sidecar_path(a).read_text(encoding="utf-8"))
        b = _pdf(root, "Smith, J. - B.pdf")
        _write(b, {"original_filename": b.name})
        complete_record(b)
        filled = json.loads(sidecar_path(b).read_text(encoding="utf-8"))
        assert set(FROM_THE_FILE) <= set(made)
        assert {k for k in filled if k != "original_filename"} == set(FROM_THE_FILE)


# --------------------------------------------------------------------------
# through the Settings button's function
# --------------------------------------------------------------------------

def test_fill_in_missing_details_completes_sparse_records_and_nothing_else(lib):
    sparse = _pdf(lib, "Smith, J. - Sparse.pdf")
    _write(sparse, _sparse(sparse))
    full = _pdf(lib, "Tan, X. - Full.pdf")
    full_rec = _write(full, dict(_sparse(full), content_sha256="ef" * 32,
                                 first_ingested_at="2020-01-01T00:00:00+00:00"))
    full_bytes = full_rec.read_bytes()
    bare = _pdf(lib, "Wu, Y. - Bare.pdf")
    before = {p: sidecar_path(p).read_bytes() for p in (sparse,)}
    log = _log(lib)

    summary = backfill_directory(lib, undo_log=log)

    assert (summary["written"], summary["completed"], summary["skipped"]) == (1, 1, 1)
    assert full_rec.read_bytes() == full_bytes
    ident = PaperIdentity.load(sparse)
    assert ident.content_sha256 == compute_content_hash(sparse)
    assert ident.first_ingested_at == filing_date(sparse)
    assert ident.classifier_text == "first pages", "the text was lost"
    assert find_sidecar(bare) is not None
    rows = _undo(log)
    assert all(r["ok"] for r in rows), rows
    assert sidecar_path(sparse).read_bytes() == before[sparse]
    assert find_sidecar(bare) is None


def test_a_sparse_record_with_a_stranded_twin_is_completed_and_the_twin_kept(lib):
    """The measured 20: an older record, left behind by a rename, matches
    the paper, whose own record has no fingerprint. The reconnect cannot
    use the spot either way (it is taken); completing loses it nothing, and
    the stranded record is not touched."""
    old = _pdf(lib, "Deride, J., Jofre, A. - Equilibrium.pdf")
    ident = PaperIdentity()
    ident.save(old, recompute_hash=True)
    stranded = sidecar_path(old)
    stranded_bytes = stranded.read_bytes()
    new = old.with_name("Deride, J., Jofré, A. - Equilibrium.pdf")
    old.rename(new)
    _write(new, _sparse(new))
    assert find_orphans(lib) == [stranded]

    summary = backfill_directory(lib)

    assert summary["completed"] == 1 and summary["kept_for_reconnect"] == 0
    assert PaperIdentity.load(new).content_sha256 == json.loads(
        stranded_bytes)["content_sha256"]
    assert stranded.read_bytes() == stranded_bytes
    assert find_orphans(lib) == [stranded]
    assert plan_reconnect(lib)["matched"] == []


def test_a_stranded_record_without_a_fingerprint_matches_nothing(lib):
    """A record stranded before it had a fingerprint (one of the sparse
    ones, renamed in Finder) has nothing to match by. Counted as the blank
    fingerprint, it matched every paper whose file cannot be read -- which
    then never got a record, "kept for the reconnect" for ever."""
    from processing.sidecar_repair import stranded_fingerprints
    old = _pdf(lib, "Smith, J. - Old name.pdf")
    stranded = _write(old, _sparse(old))
    old.rename(old.with_name("Smith, J. - New name.pdf"))
    assert find_orphans(lib) == [stranded]
    assert stranded_fingerprints(lib) == set()
    locked = _pdf(lib, "Tan, X. - Locked.pdf")
    os.chmod(locked, 0)
    try:
        if os.access(locked, os.R_OK):                 # pragma: no cover
            pytest.skip("running as a user who can read anything")
        summary = backfill_directory(lib)
    finally:
        os.chmod(locked, stat.S_IRUSR | stat.S_IWUSR)
    assert summary["kept_for_reconnect"] == 0
    assert find_sidecar(locked) is not None


@FAST
@given(kinds=st.lists(st.sampled_from(["none", "full", "sparse", "stranded"]),
                      min_size=1, max_size=6))
def test_every_change_it_makes_is_taken_back_by_undo(kinds):
    """Records made, records completed, and records kept for the reconnect,
    in any mix: one undo gives back exactly the library there was."""
    with _library() as root:
        expect = {"written": 0, "completed": 0, "kept_for_reconnect": 0}
        for i, kind in enumerate(kinds):
            pdf = _pdf(root, f"P{i}, A. - Paper.pdf")
            if kind == "full":
                _write(pdf, dict(_sparse(pdf), content_sha256="ef" * 32,
                                 first_ingested_at="2020-01-01T00:00:00+00:00"))
            elif kind == "sparse":
                _write(pdf, _sparse(pdf))
                expect["completed"] += 1
            elif kind == "stranded":
                PaperIdentity().save(pdf, recompute_hash=True)
                pdf.rename(pdf.with_name(f"P{i}, A. - Renamed.pdf"))
                expect["kept_for_reconnect"] += 1
            else:
                expect["written"] += 1
        tree = {p.relative_to(root).as_posix(): p.read_bytes()
                for p in sorted(root.rglob("*")) if p.is_file()
                and ".operation_log" not in p.parts}
        log = _log(root)

        summary = backfill_directory(root, undo_log=log)

        assert {k: summary[k] for k in expect} == expect
        if not log.has_operations():
            assert expect["written"] == expect["completed"] == 0
            return
        rows = _undo(log)
        assert all(r["ok"] for r in rows), rows
        after = {p.relative_to(root).as_posix(): p.read_bytes()
                 for p in sorted(root.rglob("*")) if p.is_file()
                 and ".operation_log" not in p.parts
                 and "undone_records" not in p.parts}
        assert after == tree
