"""A record stranded by a rename can be put back -- from the cockpit, safely.

Cockpit audit finding 21 (approved). ``processing.sidecar_repair`` was
tested and undo-logged and had NO caller, while Conformance printed the
orphans in red with no action -- as a single ``<sidecars>`` row, so he
could not even see which papers had lost their DOI. Measured on the real
library, 2026-10-09: 76 orphaned records; 37 traceable to a paper by
content (13 with a DOI, 28 with cached first-page text); 39 with no
matching paper.

What else the audit found, each pinned here:
  * the module guessed orphans from the record's NAME, so the hashed
    records of over-long names were called orphans while healthy;
  * Conformance and the repair used two rules for one question;
  * the reconnect's destination ignored the hashed location, so a paper
    with an over-long name could never get its record back;
  * Settings' "Fill in missing details" wrote a blank record into exactly
    the spot the reconnect needs, after which the stranded record could
    never return -- and, asking only ``sidecar_path``, it could write a
    SECOND record for a paper that already had one.
"""
from __future__ import annotations

import json
import os
import sys
import unicodedata
from pathlib import Path

import pytest

from processing.identity import (
    MIRROR_DIR_NAME, MAX_BASENAME_BYTES, PaperIdentity, backfill_directory,
    enable_sidecar_mirror, find_sidecar, sidecar_path,
)
from processing.sidecar_repair import apply_reconnect, find_orphans, plan_reconnect


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _paper(lib, name, body=None):
    d = lib / "01 - Published papers" / "S"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_bytes(body or f"%PDF-1.4\n{name}\n".encode())
    return p


def _strand(pdf, new_name, doi="10.1000/x"):
    """Rename a PDF the WRONG way, leaving its record behind."""
    ident = PaperIdentity()
    ident.doi = doi
    ident.save(pdf, recompute_hash=True)
    new = pdf.with_name(new_name)
    pdf.rename(new)
    return new


def _name_with_record_bytes(n: int) -> str:
    """A PDF name whose ``<stem>.meta.json`` is exactly ``n`` bytes."""
    head = "Smith, J. - "
    stem = head + "x" * (n - len(".meta.json") - len(head))
    assert len((stem + ".meta.json").encode()) == n
    return stem + ".pdf"


# ------------------------------------------------- the orphan rule itself

def test_a_hashed_record_of_an_over_long_name_is_not_an_orphan(lib):
    pdf = _paper(lib, _name_with_record_bytes(MAX_BASENAME_BYTES + 6))
    PaperIdentity().save(pdf, recompute_hash=True)
    assert ".sidecars" in sidecar_path(pdf).parts, "control: the hashed location"
    assert find_orphans(lib) == []


def test_conformance_and_the_repair_name_the_same_records(lib):
    from maintenance.conformance import check_sidecars
    from processing.identity import iter_pdfs
    a = _strand(_paper(lib, "Krylov, N.V. - Drift.pdf"), "Krylov, N. V. - Drift.pdf")
    _strand(_paper(lib, "Gone, G. - Lost.pdf"), "Gone, G. - Lost.pdf").unlink()
    _paper(lib, _name_with_record_bytes(MAX_BASENAME_BYTES + 6))
    PaperIdentity().save(next(iter_pdfs(lib / "01 - Published papers" / "S")),
                         recompute_hash=True)
    pdfs = list(iter_pdfs(lib))
    findings, stats = check_sidecars(lib, pdfs, all_pdfs=pdfs)
    named = sorted(lib / f.path for f in findings if f.reason == "orphaned-records")
    assert named == find_orphans(lib)
    assert stats["orphaned_records"] == len(named) == 2
    assert not any(f.path == "<sidecars>" for f in findings), (
        "each stranded record must be named, not summarised")
    assert a.exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="APFS folds case")
def test_a_record_reached_under_another_case_is_claimed(lib):
    pdf = _paper(lib, "Smith, J. - Title.pdf")
    rec = sidecar_path(pdf)
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.with_name(rec.name.lower()).write_text("{}")
    if not rec.exists():
        pytest.skip("this volume is case-sensitive")
    assert find_orphans(lib) == []


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS returns NFD names")
def test_a_record_spelled_nfd_is_claimed_by_an_nfc_paper(lib):
    pdf = _paper(lib, unicodedata.normalize("NFC", "Lévy, P. - Processus.pdf"))
    rec = sidecar_path(pdf)
    rec.parent.mkdir(parents=True, exist_ok=True)
    (rec.parent / unicodedata.normalize("NFD", rec.name)).write_text("{}")
    if not rec.exists():
        pytest.skip("this volume does not fold normalisation")
    assert find_orphans(lib) == []


# ----------------------------------------------------------- the reconnect

def test_an_over_long_name_can_get_its_record_back(lib):
    pdf = _paper(lib, "Smith, J. - Short.pdf")
    long_name = _name_with_record_bytes(MAX_BASENAME_BYTES + 9)
    moved = _strand(pdf, long_name)
    plan = plan_reconnect(lib)
    assert [p for _, p in plan["matched"]] == [moved]
    out = apply_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 1, out
    assert find_sidecar(moved) == sidecar_path(moved)
    assert PaperIdentity.load(moved).doi == "10.1000/x"
    assert find_orphans(lib) == []


def test_a_lookalike_name_with_other_contents_is_not_matched(lib):
    """Matching is by contents only: a homeless paper with nearly the same
    name as the stranded record is not given it."""
    moved = _strand(_paper(lib, "Smith, J. - Title.pdf", b"%PDF-1.4 one"),
                    "Smith, J. - Title (2).pdf")
    moved.unlink()                                     # its paper is gone
    _paper(lib, "Smith, J. - Title (3).pdf", b"%PDF-1.4 another paper")
    plan = plan_reconnect(lib)
    assert plan["matched"] == [] and len(plan["unmatched"]) == 1


@pytest.fixture
def stranded(lib):
    moved = _strand(_paper(lib, "Krylov, N.V. - Drift.pdf"), "Krylov, N. V. - Drift.pdf")
    return lib, moved, plan_reconnect(lib)


def test_a_record_that_moved_since_the_check_is_left_alone(stranded):
    lib, moved, plan = stranded
    sc, _ = plan["matched"][0]
    sc.rename(sc.with_name("elsewhere.meta.json"))
    out = apply_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0 and "no longer where" in out["skipped"][0]["reason"]


def test_a_paper_that_changed_since_the_check_is_left_alone(stranded):
    lib, moved, plan = stranded
    moved.write_bytes(b"%PDF-1.4 replaced by a different file")
    out = apply_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0 and "no longer match" in out["skipped"][0]["reason"]
    assert find_sidecar(moved) is None, "nothing was written for it"


def test_a_paper_that_got_a_record_since_the_check_keeps_it(stranded):
    lib, moved, plan = stranded
    mine = PaperIdentity()
    mine.doi = "10.9/mine"
    mine.save(moved, recompute_hash=True)
    out = apply_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0 and "already has a record" in out["skipped"][0]["reason"]
    assert PaperIdentity.load(moved).doi == "10.9/mine"


def test_the_reconnect_is_undoable(stranded):
    from processing.undo_log import UndoLog
    lib, moved, plan = stranded
    sc, _ = plan["matched"][0]
    out = apply_reconnect(lib, plan, dry_run=False)
    log = UndoLog(log_dir=lib / ".operation_log")
    log.undo_transaction(out["tx_id"])
    assert sc.exists() and find_sidecar(moved) is None


# ------------------------------------------------------- the backfill guard

def test_backfill_keeps_the_spot_free_for_a_stranded_record(lib):
    moved = _strand(_paper(lib, "Krylov, N.V. - Drift.pdf"), "Krylov, N. V. - Drift.pdf")
    plain = _paper(lib, "Plain, P. - Nothing stranded.pdf")
    summary = backfill_directory(lib)
    assert summary["kept_for_reconnect"] == 1
    assert find_sidecar(moved) is None, "a blank record would block the reconnect"
    assert find_sidecar(plain) is not None, "an ordinary paper still gets one"
    assert len(plan_reconnect(lib)["matched"]) == 1


def test_backfill_does_not_write_a_second_record(lib):
    """``<stem>.meta.json`` of 253 bytes: allowed on disk, but over the
    251-byte limit sidecar_path keeps -- so the old full-name record and a
    new hashed one could both exist."""
    pdf = _paper(lib, _name_with_record_bytes(MAX_BASENAME_BYTES + 2))
    naive = lib / MIRROR_DIR_NAME / pdf.relative_to(lib).with_suffix(".meta.json")
    naive.parent.mkdir(parents=True, exist_ok=True)
    naive.write_text(json.dumps({"doi": "10.1/old"}))
    assert sidecar_path(pdf) != naive, "control: a different place"
    backfill_directory(lib)
    assert not sidecar_path(pdf).exists()


# ---------------------------------------------------------- the cockpit

@pytest.fixture
def C(monkeypatch, tmp_path):
    from tests.ui.test_cockpit_smoke import _StreamlitModule
    fake = _StreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as cockpit
    return cockpit


def test_the_page_states_what_it_will_not_fix(C, lib, monkeypatch):
    shown = []
    monkeypatch.setattr(C.st, "expander",
                        lambda label, *a, **k: shown.append(label) or C.st.container())
    C.st.session_state["orphan_plan"] = {
        "library": str(lib), "orphans": 3, "candidates": 5,
        "matched": [["a.meta.json", "01/a.pdf"]], "ambiguous": [],
        "unmatched": ["b.meta.json", "c.meta.json"]}
    C._render_orphan_repair(lib, 3)
    assert any("2 that no paper" in s and "stay in red" in s for s in shown), shown


def test_reconnect_from_the_page_runs_under_the_lock_and_marks_the_report(C, lib, monkeypatch):
    moved = _strand(_paper(lib, "Krylov, N.V. - Drift.pdf"), "Krylov, N. V. - Drift.pdf")
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    monkeypatch.setattr(C.st, "checkbox", lambda *a, **k: True)
    monkeypatch.setattr(C.st, "button", lambda label, *a, **k: label.startswith("Reconnect"))
    monkeypatch.setattr(C.st, "rerun", lambda: None)
    locked = []
    real = C._locked_call
    monkeypatch.setattr(C, "_locked_call",
                        lambda lib_, action, fn, *a, **k: locked.append(action) or real(lib_, action, fn, *a, **k))
    C._render_orphan_repair(lib, 1)
    assert locked == ["Reconnect records"]
    assert PaperIdentity.load(moved).doi == "10.1000/x"
    assert "before 1 record(s) were reconnected" in C.st.session_state["conformance_outdated"]
    kind, msg = C.st.session_state["flash"][-1][:2]
    assert kind == "success" and "Reconnected 1 of 1" in msg


def test_a_plan_for_another_library_is_not_offered(C, lib, tmp_path, monkeypatch):
    offered = []
    monkeypatch.setattr(C.st, "checkbox", lambda label, *a, **k: offered.append(label) or False)
    C.st.session_state["orphan_plan"] = {
        "library": str(tmp_path / "other"), "orphans": 1, "candidates": 1,
        "matched": [["a.meta.json", "01/a.pdf"]], "ambiguous": [], "unmatched": []}
    C._render_orphan_repair(lib, 1)
    assert offered == []


# ------------------------------------- names whose record is 252-255 bytes
#
# Such a record can exist on disk under its full name, yet sidecar_path
# answers with the hashed location (its limit is 251). The real library
# has them: of 27 papers on the hashed path, 14 also had a full-name record.

def _mid_length_with_naive_record(lib, doi="10.1/naive"):
    pdf = _paper(lib, _name_with_record_bytes(MAX_BASENAME_BYTES + 2))
    naive = lib / MIRROR_DIR_NAME / pdf.relative_to(lib).with_suffix(".meta.json")
    naive.parent.mkdir(parents=True, exist_ok=True)
    naive.write_text(json.dumps({"doi": doi}))
    return pdf, naive


def test_a_full_name_record_is_claimed_by_its_paper(lib):
    pdf, naive = _mid_length_with_naive_record(lib)
    assert sidecar_path(pdf) != naive
    assert find_orphans(lib) == []
    assert plan_reconnect(lib)["candidates"] == 0, "it is not homeless"


def test_a_full_name_record_that_appears_after_the_check_is_kept(lib):
    """The plan is minutes old. If the paper got a record at its full-name
    path meanwhile, the reconnect must not add a second at the hashed one."""
    pdf = _paper(lib, "Smith, J. - Short.pdf")
    moved = _strand(pdf, _name_with_record_bytes(MAX_BASENAME_BYTES + 2))
    plan = plan_reconnect(lib)
    assert len(plan["matched"]) == 1
    naive = lib / MIRROR_DIR_NAME / moved.relative_to(lib).with_suffix(".meta.json")
    naive.write_text(json.dumps({"doi": "10.1/arrived-meanwhile"}))
    out = apply_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0 and "already has a record" in out["skipped"][0]["reason"]
    assert not sidecar_path(moved).exists(), "a second record was written"


def test_a_paper_deleted_since_the_check_is_named_as_such(stranded):
    lib, moved, plan = stranded
    moved.unlink()
    out = apply_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0
    assert "the paper is no longer where the check found it" == out["skipped"][0]["reason"]


# ------------------------------------------------- the cockpit, continued

def _press_reconnect(C, monkeypatch):
    monkeypatch.setattr(C.st, "checkbox", lambda *a, **k: True)
    monkeypatch.setattr(C.st, "button", lambda label, *a, **k: label.startswith("Reconnect"))
    monkeypatch.setattr(C.st, "rerun", lambda: None)


def test_a_partial_reconnect_is_a_warning_and_none_is_an_error(C, lib, monkeypatch):
    a = _strand(_paper(lib, "A, A. - One.pdf"), "A, A. - One v2.pdf")
    b = _strand(_paper(lib, "B, B. - Two.pdf"), "B, B. - Two v2.pdf")
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    b.write_bytes(b"%PDF-1.4 replaced")
    _press_reconnect(C, monkeypatch)
    C._render_orphan_repair(lib, 2)
    kind, msg, details = C.st.session_state["flash"][-1][:3]
    assert kind == "warning" and "Reconnected 1 of 2" in msg
    assert any("no longer match" in d for d in details)

    c = _strand(_paper(lib, "C, C. - Three.pdf"), "C, C. - Three v2.pdf")
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    c.unlink()
    C._render_orphan_repair(lib, 1)
    kind, msg = C.st.session_state["flash"][-1][:2]
    assert kind == "error" and "Reconnected 0 of 1" in msg
    assert a.exists()


def test_running_the_check_again_clears_the_outdated_note(C, lib, monkeypatch):
    import maintenance.conformance as MC
    rep = MC.ConformanceReport()
    rep.scanned, rep.reasons, rep.findings = 1, {}, []
    rep.counts = {b: 0 for b in (MC.CANONICAL, MC.OWNER_QUEUE, MC.MECHANICAL,
                                 MC.TYPO, MC.NOT_EXAMINED, MC.VIOLATION)}
    rep.globals_ = {}
    monkeypatch.setattr(MC, "run", lambda *a, **k: rep)
    monkeypatch.setattr(MC, "load_previous", lambda *a, **k: None)
    monkeypatch.setattr(C, "_page_header", lambda *a, **k: None)
    monkeypatch.setattr(C.st, "button", lambda label, *a, **k: label == "▶ Run the check")
    from unittest.mock import MagicMock
    monkeypatch.setattr(C.st, "progress", lambda *a, **k: MagicMock())
    C.st.session_state["conformance_outdated"] = "old"
    C.render_conformance()
    assert "conformance_outdated" not in C.st.session_state


def test_settings_says_which_papers_backfill_left_for_the_reconnect(monkeypatch, tmp_path):
    from tests.ui.test_cockpit_renders_content import _RecStreamlit, rendered_text
    stub = _RecStreamlit([], {"bf_run": True})
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as C
    import processing.identity as ident
    import core.config.secure_config as sc
    monkeypatch.setattr(sc, "get_secure_credential", lambda *a, **k: None)
    monkeypatch.setattr(ident, "backfill_directory", lambda *a, **k: {
        "scanned": 9, "written": 5, "skipped": 2, "errors": 0,
        "kept_for_reconnect": 2})
    C.render_settings()
    text = rendered_text(stub)
    assert "2 paper(s) were NOT given a new record" in text and "Conformance" in text
