"""A paper retired to the trash takes its saved record with it -- and both come back.

Measured 2026-10-09: 76 saved records belonged to no paper. Three of them
are the records of preprints the June pilot upgrade (tx 0c2b96e0e3af) moved
to ``.trash/upgraded_preprints`` with a bare ``shutil.move``: the PDF went,
the record stayed at the old name. Three paths retired a PDF that way --
``upgrade_paper``, ``bulk_sort`` and undoing a copy -- while every other
trash path already went through ``logged_move``, which carries the record
and logs both moves in one transaction. All three now use it.

Each is checked for every place a record can be:

  ordinary    the mirror path under the full name;
  over-long   ``<stem>.meta.json`` would exceed 255 bytes, so the record
              has a coded ``.sidecars/<sha1>`` name;
  full-name   a record name of 252-255 bytes: beyond ``sidecar_path``'s
              251-byte budget, but stored under its full name by older
              code, so it is NOT where ``sidecar_path`` points;
  nfd         an accented name decomposed, as macOS hands names back.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unicodedata
from dataclasses import asdict
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from processing.identity import (
    MIRROR_DIR_NAME, PaperIdentity, enable_sidecar_mirror, find_sidecar,
    sidecar_candidates, sidecar_path,
)
from processing.sidecar_repair import find_orphans
from processing.undo_log import UndoLog, logged_copy, trash_slot_taken

HEAD = "Smith, J. - "
KINDS = ("ordinary", "over-long", "full-name-252", "full-name-255", "nfd")
PREPRINT = b"%PDF-1.4 preprint"


def _stem(kind: str) -> str:
    if kind == "ordinary":
        return HEAD + "A result on Markov chains"
    if kind == "nfd":
        return unicodedata.normalize("NFD", "Élie, R. - Équations rétrogrades")
    if kind == "over-long":
        # PDF name 254 bytes (allowed); its record name would be 260.
        return HEAD + "x" * (250 - len(HEAD))
    n = int(kind.rsplit("-", 1)[1])             # the record name's bytes
    return HEAD + "y" * (n - len(".meta.json") - len(HEAD))


def _record_path(lib: Path, pdf: Path, kind: str) -> Path:
    if kind.startswith("full-name"):
        return (lib / MIRROR_DIR_NAME / pdf.relative_to(lib).parent
                / (pdf.stem + ".meta.json"))
    return sidecar_path(pdf)


def _write_record(path: Path, ident: PaperIdentity) -> None:
    """Write ``ident`` exactly as ``PaperIdentity.save`` would, but at
    ``path`` -- which is how a full-name record can be put in place."""
    payload = {k: v for k, v in asdict(ident).items() if not k.startswith("_")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False,
                               sort_keys=True), encoding="utf-8")


def _paper(lib: Path, folder: str, kind: str):
    """A PDF and its saved record, stored where ``kind`` says."""
    pdf = lib / folder / f"{_stem(kind)}.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(PREPRINT)
    record = _record_path(lib, pdf, kind)
    _write_record(record, PaperIdentity(
        doi="10.1/preprint", arxiv_id="2401.00001", original_filename=pdf.name,
        classifier_text="first page of " + kind, topic_codes=["07a"],
        publication_checks=[{"date": "2026-01-01", "result": "unpublished"}]))
    # The fixture is what it claims to be.
    assert find_sidecar(pdf) == record
    if kind.startswith("full-name"):
        assert len(record.name.encode()) == int(kind.rsplit("-", 1)[1])
        assert record != sidecar_path(pdf), "full-name records are off the primary path"
    if kind == "over-long":
        assert record.parent.name == ".sidecars"
    return pdf, record


def _identity(record: Path) -> dict:
    """The record's content, minus ``copy_locations`` (see the xfail below)."""
    d = json.loads(record.read_text(encoding="utf-8"))
    d.pop("copy_locations", None)
    return d


def _no_record_left_at(pdf: Path) -> bool:
    """No record answers to ``pdf`` at ANY of the places one could be."""
    assert len(sidecar_candidates(pdf)) >= 2
    return find_sidecar(pdf) is None


# ------------------------------------------------------------- the retirers

def _upgrade(lib: Path, pdf: Path, log, monkeypatch):
    """Run the real ``upgrade_paper``; only the download and filing are faked."""
    import processing.ingest as ingest
    import processing.upgrade_to_published as up
    seen: dict = {}

    def _download(doi, download_dir):
        f = Path(download_dir) / "published.pdf"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"%PDF-1.4 the published version, rather longer than that")
        return f

    def _ingest(src, *, library_root, canonical_override, topic=None, **k):
        seen["topic"] = topic
        dest = library_root / "01 - Published papers" / "S" / f"{canonical_override}.pdf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        PaperIdentity(doi="10.1/published").save(dest, recompute_hash=False)
        return {"success": True, "destination": str(dest)}

    monkeypatch.setattr(up, "try_download_by_doi", _download)
    monkeypatch.setattr(ingest, "ingest_paper", _ingest)
    body = pdf.read_bytes()
    entry = {"file": str(pdf), "match": {"doi": "10.1/published"}}
    res = up.upgrade_paper(entry, lib, lib.parent / "dl", dry_run=False, undo_log=log)
    trash = lib / ".trash" / "upgraded_preprints"
    hits = ([p for p in trash.iterdir() if p.suffix == ".pdf" and p.read_bytes() == body]
            if trash.is_dir() else [])
    return res, (hits[0] if len(hits) == 1 else None), seen


def _sort(lib: Path, pdf: Path, log, monkeypatch):
    """Run the real ``sort_one``; only the ingest is faked."""
    import processing.ingest as ingest
    from processing.bulk_sort import sort_one
    monkeypatch.setattr(ingest, "ingest_paper", lambda p, **k: {
        "success": True, "filename": p.name, "title_from_metadata": True,
        "destination": str(lib / "01 - Published papers" / p.name)})
    res = sort_one(pdf, "published", library_root=lib, dry_run=False, undo_log=log)
    return res, (Path(res["moved_source_to"]) if res.get("ok") else None), {}


RETIRERS = {
    "upgrade": ("02 - Unpublished papers/S", ".trash/upgraded_preprints", _upgrade),
    "bulk_sort": ("12 - To be sorted/01 - Published papers",
                  ".trash/sorted_originals/01 - Published papers", _sort),
}


def _run(lib, retirer, pdf, monkeypatch):
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction(f"retire {pdf.name[:20]}")
    res, trashed, seen = RETIRERS[retirer][2](lib, pdf, log, monkeypatch)
    log.commit()
    return log, tx, res, trashed, seen


def _retire(lib, retirer, kind, monkeypatch):
    pdf, record = _paper(lib, RETIRERS[retirer][0], kind)
    return (pdf, record, *_run(lib, retirer, pdf, monkeypatch))


@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "lib"
    root.mkdir()
    enable_sidecar_mirror(root)
    return root


# ------------------------------------------------- the record goes, and returns

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("retirer", sorted(RETIRERS))
def test_the_record_goes_into_the_trash_with_its_paper(lib, retirer, kind, monkeypatch):
    pdf, record = _paper(lib, RETIRERS[retirer][0], kind)
    original = _identity(record)
    log, tx, res, trashed, _ = _run(lib, retirer, pdf, monkeypatch)
    assert trashed is not None and trashed.is_file(), res
    assert trashed.parent == lib / RETIRERS[retirer][1]
    assert not pdf.exists()
    assert _no_record_left_at(pdf), "the record stayed behind, belonging to no paper"
    moved = find_sidecar(trashed)
    assert moved is not None, "the paper is in the trash without its record"
    assert moved.is_relative_to(lib / MIRROR_DIR_NAME / ".trash")
    assert _identity(moved) == original
    assert find_orphans(lib) == [], "trashing a paper made an orphan"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("retirer", sorted(RETIRERS))
def test_one_undo_brings_back_both_exactly_where_they_were(lib, retirer, kind, monkeypatch):
    pdf, record = _paper(lib, RETIRERS[retirer][0], kind)
    original = _identity(record)
    log, tx, res, trashed, _ = _run(lib, retirer, pdf, monkeypatch)
    results = log.undo_transaction(tx)
    assert [r["ok"] for r in results] == [True, True], results
    assert all(r["action"].startswith("MOVED BACK") for r in results), results
    assert pdf.read_bytes() == PREPRINT
    assert record.is_file(), "the record did not return to the place it was in"
    assert find_sidecar(pdf) == record
    assert _identity(record) == original
    assert not trashed.exists() and find_sidecar(trashed) is None
    assert find_orphans(lib) == []


@pytest.mark.parametrize("kind", KINDS)
def test_an_upgrade_keeps_the_topic_and_history_of_any_record(lib, kind, monkeypatch):
    """Topic and check history were read only where a record SHOULD be, so
    a full-name record's paper was re-filed without either."""
    pdf, record, log, tx, res, trashed, seen = _retire(lib, "upgrade", kind, monkeypatch)
    assert seen["topic"] == "07a"
    published = lib / "01 - Published papers" / "S" / pdf.name
    checks = PaperIdentity.load(published).publication_checks
    assert {"date": "2026-01-01", "result": "unpublished"} in checks


@pytest.mark.xfail(strict=True, reason=(
    "logged_move rewrites the record's copy_locations to the trash path "
    "outside the undo log, so after undo the record still names the trash. "
    "Pre-existing in every logged_move/logged_rename; separate follow-up."))
@pytest.mark.parametrize("retirer", sorted(RETIRERS))
def test_undo_restores_the_record_byte_for_byte(lib, retirer, monkeypatch):
    pdf, record = _paper(lib, RETIRERS[retirer][0], "ordinary")
    before = record.read_bytes()
    log, tx, *_ = _run(lib, retirer, pdf, monkeypatch)
    log.undo_transaction(tx)
    assert record.read_bytes() == before


# ------------------------------------------------------------- pathologies

@pytest.mark.parametrize("retirer,suffix", [("upgrade", " (2)"), ("bulk_sort", ".1")])
def test_a_stale_record_at_the_trash_name_is_neither_clobbered_nor_blocking(
        lib, retirer, suffix, monkeypatch):
    """A record already answering to the trash name (its PDF dragged out of
    the trash by hand) made logged_move refuse; the name is skipped instead."""
    folder, trash, _ = RETIRERS[retirer]
    stem = _stem("ordinary")
    squatter = sidecar_path(lib / trash / f"{stem}.pdf")
    squatter.parent.mkdir(parents=True, exist_ok=True)
    squatter.write_text('{"doi": "10.1/someone-else"}')
    pdf, record, log, tx, res, trashed, _ = _retire(lib, retirer, "ordinary", monkeypatch)
    assert trashed is not None and trashed.name == f"{stem}{suffix}.pdf", res
    assert squatter.read_text() == '{"doi": "10.1/someone-else"}'
    assert _identity(find_sidecar(trashed))["doi"] == "10.1/preprint"
    assert _no_record_left_at(pdf)


@pytest.mark.parametrize("own_record", [True, False])
@pytest.mark.parametrize("retirer,suffix", [("upgrade", " (2)"), ("bulk_sort", ".1")])
def test_a_stale_full_name_record_at_the_trash_name_is_skipped(
        lib, retirer, suffix, own_record, monkeypatch):
    """The squatter sits at the trash name's FULL-NAME location, not where
    sidecar_path points (its name is 255 bytes). logged_move would not
    refuse -- it writes only to the primary place -- so the name looks free
    unless every place a record could be is asked. Used anyway, the trashed
    paper is answered by a stranger's record: its own, if it has none."""
    folder, trash, run = RETIRERS[retirer]
    stem = _stem("full-name-255")
    squatter = _record_path(lib, lib / trash / f"{stem}.pdf", "full-name-255")
    _write_record(squatter, PaperIdentity(doi="10.1/someone-else"))
    if own_record:
        pdf, record = _paper(lib, folder, "full-name-255")
    else:
        pdf = lib / folder / f"{stem}.pdf"
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(PREPRINT)
    log, tx, res, trashed, _ = _run(lib, retirer, pdf, monkeypatch)
    assert trashed is not None and trashed.name == f"{stem}{suffix}.pdf", res
    assert json.loads(squatter.read_text())["doi"] == "10.1/someone-else"
    found = find_sidecar(trashed)
    if own_record:
        assert _identity(found)["doi"] == "10.1/preprint"
    else:
        assert found is None, "a stranger's record answers for the trashed paper"


@pytest.mark.parametrize("retirer,suffix", [("upgrade", " (2)"), ("bulk_sort", ".1")])
def test_an_occupied_trash_name_keeps_its_own_record(lib, retirer, suffix, monkeypatch):
    folder, trash, _ = RETIRERS[retirer]
    stem = _stem("ordinary")
    occupant = lib / trash / f"{stem}.pdf"
    occupant.parent.mkdir(parents=True, exist_ok=True)
    occupant.write_bytes(b"%PDF-1.4 retired last year")
    occ_record = sidecar_path(occupant)
    occ_record.parent.mkdir(parents=True, exist_ok=True)
    occ_record.write_text('{"doi": "10.1/last-year"}')
    pdf, record, log, tx, res, trashed, _ = _retire(lib, retirer, "ordinary", monkeypatch)
    assert trashed is not None and trashed.name == f"{stem}{suffix}.pdf", res
    assert occupant.read_bytes() == b"%PDF-1.4 retired last year"
    assert occ_record.read_text() == '{"doi": "10.1/last-year"}'
    assert _identity(find_sidecar(trashed))["doi"] == "10.1/preprint"
    log.undo_transaction(tx)
    assert occupant.is_file() and occ_record.read_text() == '{"doi": "10.1/last-year"}'
    assert find_sidecar(pdf) == record


@pytest.mark.parametrize("retirer", sorted(RETIRERS))
def test_a_paper_without_a_record_is_retired_and_none_is_invented(lib, retirer, monkeypatch):
    pdf = lib / RETIRERS[retirer][0] / f"{_stem('ordinary')}.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(PREPRINT)
    log, tx, res, trashed, _ = _run(lib, retirer, pdf, monkeypatch)
    assert trashed is not None and trashed.is_file(), res
    assert find_sidecar(trashed) is None
    results = log.undo_transaction(tx)
    assert [r["ok"] for r in results] == [True], results
    assert pdf.is_file() and find_sidecar(pdf) is None


@pytest.mark.parametrize("retirer", sorted(RETIRERS))
def test_a_name_that_cannot_take_a_suffix_fails_and_moves_nothing(lib, retirer, monkeypatch):
    """A 254-byte name whose trash slot is taken: every suffixed name is over
    255 bytes. The retirement must say so and leave the paper and its record
    where they are -- never loop, never half-move."""
    folder, trash, _ = RETIRERS[retirer]
    occupant = lib / trash / f"{_stem('over-long')}.pdf"
    occupant.parent.mkdir(parents=True, exist_ok=True)
    occupant.write_bytes(b"%PDF-1.4 occupant")
    pdf, record, log, tx, res, trashed, _ = _retire(lib, retirer, "over-long", monkeypatch)
    assert trashed is None
    assert pdf.read_bytes() == PREPRINT and find_sidecar(pdf) == record
    assert occupant.read_bytes() == b"%PDF-1.4 occupant"
    msg = res.get("error") or res.get("action") or ""
    assert ("preprint move error" in msg) or ("trashing source failed" in msg), res
    assert find_orphans(lib) == []


def test_a_sorted_original_is_logged_before_it_moves(lib, monkeypatch):
    """``bulk_sort`` recorded its trash move AFTER moving, so a crash in the
    gap left a file in the trash with no undo entry. Now the move fails,
    and the entry is already there; the source stays put."""
    import processing.undo_log as ul
    pdf, record = _paper(lib, RETIRERS["bulk_sort"][0], "ordinary")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(ul.shutil, "move", boom)
    log = UndoLog(log_dir=lib / ".operation_log")
    log.begin_transaction("sort")
    res, trashed, _ = _sort(lib, pdf, log, monkeypatch)
    assert "trashing source failed" in res.get("error", ""), res
    assert pdf.is_file() and find_sidecar(pdf) == record
    ops = [(op["type"], Path(op["source"]).name) for op in log._current_tx["operations"]]
    assert ops == [("move", pdf.name)], ops


def test_the_slot_rule(lib):
    dest = lib / ".trash" / "x" / "Smith, J. - A.pdf"
    assert trash_slot_taken(dest) is False
    rec = sidecar_path(dest)
    rec.parent.mkdir(parents=True)
    rec.write_text("{}")
    assert trash_slot_taken(dest) is True, "a record answering to the name takes it"
    rec.unlink()
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"%PDF")
    assert trash_slot_taken(dest) is True
    with pytest.raises(OSError):
        trash_slot_taken(dest.parent / ("z" * 300 + ".pdf"))


# --------------------------------------------------- undoing a copy retires it

@pytest.fixture
def home_lib():
    """The library ``_retire_to_trash`` resolves: MATH_LIBRARY, per test."""
    root = Path(os.environ["MATH_LIBRARY"])
    root.mkdir(parents=True, exist_ok=True)
    enable_sidecar_mirror(root)
    return root


def _copy_with_record(lib: Path, name: str, kind: str):
    original = lib / "01 - Published papers" / "S" / name
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(b"%PDF-1.4 original")
    copy = lib / "07a - BSDEs" / name
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("copy")
    logged_copy(original, copy, undo_log=log)
    log.commit()
    rec = _record_path(lib, copy, kind)
    _write_record(rec, PaperIdentity(doi="10.1/the-copy", original_filename=name))
    assert find_sidecar(copy) == rec
    return log, tx, copy, rec


@pytest.mark.parametrize("kind", KINDS)
def test_undoing_a_copy_retires_the_copy_with_its_record(home_lib, kind):
    log, tx, copy, rec = _copy_with_record(home_lib, f"{_stem(kind)}.pdf", kind)
    original = _identity(rec)
    results = log.undo_transaction(tx)
    assert [r["ok"] for r in results] == [True], results
    retired = home_lib / ".trash" / "undone_copies" / copy.name
    assert retired.read_bytes() == b"%PDF-1.4 original" and not copy.exists()
    assert _no_record_left_at(copy), "the copy's record stayed, belonging to no paper"
    assert _identity(find_sidecar(retired)) == original
    assert find_orphans(home_lib) == []


def test_undoing_a_copy_skips_a_trash_name_held_by_a_stale_record(home_lib):
    squatter = sidecar_path(home_lib / ".trash" / "undone_copies" / "Smith, J. - A.pdf")
    squatter.parent.mkdir(parents=True, exist_ok=True)
    squatter.write_text('{"doi": "10.1/someone-else"}')
    log, tx, copy, rec = _copy_with_record(home_lib, "Smith, J. - A.pdf", "ordinary")
    results = log.undo_transaction(tx)
    assert [r["ok"] for r in results] == [True], results
    retired = home_lib / ".trash" / "undone_copies" / "Smith, J. - A (1).pdf"
    assert retired.is_file()
    assert squatter.read_text() == '{"doi": "10.1/someone-else"}'
    assert _identity(find_sidecar(retired))["doi"] == "10.1/the-copy"


# ------------------------------------------------------------ the property

def _snapshot(lib: Path) -> dict:
    return {p.relative_to(lib): p.read_bytes() for p in lib.rglob("*")
            if p.is_file() and ".operation_log" not in p.parts}


@settings(max_examples=40, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(retirer=st.sampled_from(sorted(RETIRERS)),
       kind=st.sampled_from([k for k in KINDS if k != "over-long"]),
       slots=st.lists(st.sampled_from(["pdf", "record", "both"]), max_size=4))
def test_retiring_never_orphans_never_clobbers_and_undoes_cleanly(
        tmp_path, monkeypatch, retirer, kind, slots):
    """For any record location, and a trash already holding PDFs and/or
    records under the names the retirement would try: no record is
    orphaned, nothing already there changes, and one undo puts back every
    file that was there before (the record's copy_locations aside)."""
    lib = Path(tempfile.mkdtemp(dir=tmp_path)) / "lib"
    lib.mkdir()
    enable_sidecar_mirror(lib)
    folder, trash, _ = RETIRERS[retirer]
    stem = _stem(kind)
    names = [f"{stem}.pdf"] + [
        f"{stem} ({n + 1}).pdf" if retirer == "upgrade" else f"{stem}.{n}.pdf"
        for n in range(1, len(slots) + 1)]
    for state, name in zip(slots, names):
        p = lib / trash / name
        if state in ("pdf", "both"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"%PDF-1.4 occupant " + name.encode())
        if state in ("record", "both"):
            r = sidecar_path(p)
            r.parent.mkdir(parents=True, exist_ok=True)
            r.write_text(json.dumps({"doi": "occupant " + name}))
    pdf, record = _paper(lib, folder, kind)
    original = _identity(record)
    before = _snapshot(lib)
    paper_keys = {pdf.relative_to(lib), record.relative_to(lib)}

    log, tx, res, trashed, _ = _run(lib, retirer, pdf, monkeypatch)
    assert trashed is not None, res
    assert trashed.name == names[len(slots)], "the first name free of PDF and record"
    assert find_orphans(lib) == []
    assert _no_record_left_at(pdf)
    assert _identity(find_sidecar(trashed)) == original
    during = _snapshot(lib)
    for k, v in before.items():
        if k not in paper_keys:
            assert during.get(k) == v, f"something already there changed: {k}"
    created = {trashed.relative_to(lib), find_sidecar(trashed).relative_to(lib)}
    side_effects = set(during) - set(before) - created   # e.g. the published copy

    log.undo_transaction(tx)
    after = _snapshot(lib)
    assert set(after) == set(before) | side_effects
    for k, v in before.items():
        if k == record.relative_to(lib):
            assert _identity(record) == original
        else:
            assert after[k] == v, f"not restored: {k}"
    assert find_orphans(lib) == []
