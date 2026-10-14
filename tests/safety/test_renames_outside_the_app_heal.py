"""A paper renamed outside the app gets its saved details back by itself.

The owner's decision 6, 2026-10-14 ("automatic"). That morning at 09:22 a
paper was renamed in Finder (Beneš et al., "explicit solution or" -> "of
Mortensen's equation"); its saved details (the sidecar record) stayed under
the old name and became an orphan -- the 74th. The auto-filer now runs the
reconnect on a timer, only for CERTAIN matches: same contents, one
candidate, the paper has no record of its own -- and never in the archival
collections, never where the plan predicts something would still be wrong.
"""
from __future__ import annotations

import ast
import json
import logging
import os
from pathlib import Path

import pytest

from processing.identity import PaperIdentity, enable_sidecar_mirror, find_sidecar
from processing.library_scope import ARCHIVAL_COLLECTIONS
from processing.sidecar_repair import AUTO_RECONNECT_DESCRIPTION, auto_reconnect, find_orphans


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _paper(lib, folder, name, body=None, doi="10.1/x"):
    p = lib / folder / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body or f"%PDF-1.4 {name}".encode())
    ident = PaperIdentity()
    ident.doi = doi
    ident.save(p, recompute_hash=True)
    return p


def _finder_rename(p, new_name):
    """What Finder does: the PDF moves, nothing else does."""
    new = p.with_name(new_name)
    os.rename(p, new)
    return new


OLD = "Beneš, V. E., Karatzas, I. - Control, an explicit solution or Mortensen’s equation.pdf"
NEW = "Beneš, V. E., Karatzas, I. - Control, an explicit solution of Mortensen’s equation.pdf"


def test_a_finder_rename_heals_and_can_be_undone(lib):
    from processing.undo_log import UndoLog
    p = _finder_rename(_paper(lib, "01 - Published papers/B", OLD), NEW)
    assert len(find_orphans(lib)) == 1 and find_sidecar(p) is None
    res = auto_reconnect(lib)
    assert res["reconnected"] == 1 and res["tx_id"]
    assert PaperIdentity.load(p).doi == "10.1/x"
    assert find_orphans(lib) == []
    locs = PaperIdentity.load(p).copy_locations
    assert all(Path(l).exists() for l in locs), "the record must name the paper where it is now"
    tx = json.loads((lib / ".operation_log" / f"{res['tx_id']}.json").read_text())
    assert "put back after a rename outside the app" in json.dumps(tx, ensure_ascii=False)
    UndoLog(log_dir=lib / ".operation_log").undo_transaction(res["tx_id"])
    assert find_sidecar(p) is None and len(find_orphans(lib)) == 1


def test_two_papers_with_the_same_contents_are_not_guessed_between(lib):
    body = b"%PDF-1.4 the same bytes"
    _finder_rename(_paper(lib, "01 - Published papers/B", OLD, body), NEW)
    twin = lib / "01 - Published papers/B" / "Beneš, V. E. - A copy.pdf"
    twin.write_bytes(body)
    res = auto_reconnect(lib)
    assert res["reconnected"] == 0 and len(find_orphans(lib)) == 1


def test_a_paper_that_already_has_a_record_keeps_it(lib):
    p = _finder_rename(_paper(lib, "01 - Published papers/B", OLD), NEW)
    mine = PaperIdentity()
    mine.doi = "10.9/mine"
    mine.save(p, recompute_hash=True)
    res = auto_reconnect(lib)
    assert res["reconnected"] == 0 and PaperIdentity.load(p).doi == "10.9/mine"


@pytest.mark.parametrize("folder", ARCHIVAL_COLLECTIONS)
def test_nothing_is_done_in_the_archival_collections(lib, folder):
    _finder_rename(_paper(lib, folder, "Volume 1.pdf"), "Volume one.pdf")
    res = auto_reconnect(lib)
    assert res["reconnected"] == 0
    assert res["left"] and "archival" in res["left"][0][1]
    assert len(find_orphans(lib)) == 1, "left for Conformance, untouched"


def test_a_busy_library_is_left_alone_and_said_so(lib):
    from processing.locking import LibraryLock
    _finder_rename(_paper(lib, "01 - Published papers/B", OLD), NEW)
    other = LibraryLock(lib)
    assert other.acquire(blocking=False)
    try:
        res = auto_reconnect(lib)
    finally:
        other.release()
    assert res["busy"] and res["reconnected"] == 0 and len(find_orphans(lib)) == 1


def test_nothing_to_do_costs_no_hashing_and_no_transaction(lib, monkeypatch):
    import processing.identity as ident
    _paper(lib, "01 - Published papers/B", OLD)
    monkeypatch.setattr(ident, "compute_content_hash",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("hashed")))
    res = auto_reconnect(lib)
    assert res == {"orphans": 0, "reconnected": 0, "left": [], "skipped": [],
                   "tx_id": None, "busy": False}
    assert not (lib / ".operation_log").exists() or not list((lib / ".operation_log").glob("*.json"))


def test_a_pair_the_plan_warns_about_is_left_for_conformance(lib, monkeypatch):
    import processing.sidecar_repair as R
    _finder_rename(_paper(lib, "01 - Published papers/B", OLD), NEW)
    real = R.plan_reconnect

    def _warned(root):
        plan = real(root)
        plan["still"] = [(sc, ["it still lists a place where no file is: x"])
                         for sc, _ in plan["matched"]]
        return plan
    monkeypatch.setattr(R, "plan_reconnect", _warned)
    res = R.auto_reconnect(lib)
    assert res["reconnected"] == 0 and "still be wrong" in res["left"][0][1]


def test_the_description_names_the_count():
    assert AUTO_RECONNECT_DESCRIPTION.format(n=3).endswith("3 paper(s)")


# ----------------------------------------------------------- the auto-filer

def test_the_filer_runs_it_on_a_timer_and_not_in_a_dry_run():
    src = (Path(__file__).resolve().parents[2] / "src/watcher/daemon.py").read_text()
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "run_daemon")
    body = ast.unparse(fn)
    assert "_auto_reconnect(config.library_root)" in body
    assert "not dry_run" in body.split("_auto_reconnect(config.library_root)")[0][-400:]
    assert "RECONNECT_EVERY = 3600.0" in body


def test_a_failure_never_takes_the_filer_down(monkeypatch, caplog):
    import processing.sidecar_repair as R
    from watcher.daemon import _auto_reconnect
    monkeypatch.setattr(R, "auto_reconnect",
                        lambda root: (_ for _ in ()).throw(OSError("disk went away")))
    with caplog.at_level(logging.ERROR):
        res = _auto_reconnect(Path("/nowhere"))
    assert "disk went away" in res["error"] and "disk went away" in caplog.text


def test_what_it_did_is_logged_in_words(lib, caplog):
    from watcher.daemon import _auto_reconnect
    _finder_rename(_paper(lib, "01 - Published papers/B", OLD), NEW)
    with caplog.at_level(logging.INFO):
        res = _auto_reconnect(lib)
    assert res["reconnected"] == 1
    assert "put back for 1 paper(s)" in caplog.text


def _finder_move(p, folder):
    folder.mkdir(parents=True, exist_ok=True)
    new = folder / p.name
    os.rename(p, new)
    return new


def test_a_paper_moved_out_of_an_archival_collection_is_left_alone(lib):
    """The record's old place is archival: it is not this tool's to move."""
    p = _paper(lib, ARCHIVAL_COLLECTIONS[1], "Mémoire, tome 3.pdf")
    _finder_move(p, lib / "05 - Books and lecture notes" / "M")
    res = auto_reconnect(lib)
    assert res["reconnected"] == 0 and "archival" in res["left"][0][1]


def test_a_paper_moved_into_an_archival_collection_is_left_alone(lib):
    p = _paper(lib, "01 - Published papers/B", OLD)
    _finder_move(p, lib / ARCHIVAL_COLLECTIONS[1])
    res = auto_reconnect(lib)
    assert res["reconnected"] == 0 and "archival" in res["left"][0][1]


def test_a_quiet_hour_does_not_report_a_busy_library(lib):
    """Nothing to put back: the lock is not even asked for, so a filer
    mid-ingest does not produce an hourly "busy" line for nothing."""
    from processing.locking import LibraryLock
    _paper(lib, "01 - Published papers/B", OLD)
    other = LibraryLock(lib)
    assert other.acquire(blocking=False)
    try:
        assert auto_reconnect(lib)["busy"] is False
    finally:
        other.release()
