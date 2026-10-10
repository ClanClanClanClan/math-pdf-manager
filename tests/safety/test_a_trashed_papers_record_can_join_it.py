"""A record left behind when its paper went to the trash can join it there.

Owner's decision, 2026-10-09 ("ok to them all"). Until commit 5561635,
upgrading a preprint and filing from the inbox moved the PDF into
``.trash`` and left its record at the old name, belonging to no paper.
Measured that day: 76 orphaned records; 37 match a paper on the shelves;
of the other 39, three match a PDF in ``.trash/upgraded_preprints`` by
content -- the preprints of the June pilot upgrade (tx 0c2b96e0e3af).

The reconnect already matched records to papers by content, under the
lock and in one undoable transaction. It now also looks in the trash --
only after the shelves, only among trashed PDFs with no record, never
guessing between two, never for an archival collection -- and lists what
it finds separately, behind its own checkbox and button, so "Reconnect
37" and this are two decisions, not one.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from processing.identity import (
    MAX_BASENAME_BYTES, MIRROR_DIR_NAME, PaperIdentity, compute_content_hash,
    enable_sidecar_mirror, find_sidecar, sidecar_path,
)
from processing.sidecar_repair import (
    _former_place, apply_reconnect, apply_trash_reconnect, find_orphans,
    plan_reconnect,
)
from processing.undo_log import UndoLog

PRE = "02 - Unpublished papers/C"
UPG = ".trash/upgraded_preprints"
JEHPS = "09 - Journal Électronique d'Histoire des Probabilités et de la Statistique"


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _name(record_bytes: int) -> str:
    head = "Cao, C. - "
    return head + "q" * (record_bytes - len(".meta.json") - len(head)) + ".pdf"


def _stranded_in_trash(lib, name="Cao, C. - Recursive equilibrium.pdf", *,
                       folder=PRE, body=None, full_name=False, control=True):
    """A paper with a record, retired the OLD way: the PDF alone moved."""
    pdf = lib / folder / name
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(body or f"%PDF-1.4 {name}".encode())
    if full_name:
        record = lib / MIRROR_DIR_NAME / folder / (pdf.stem + ".meta.json")
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"doi": "10.1/pre",
                                      "content_sha256": compute_content_hash(pdf)}))
    else:
        PaperIdentity(doi="10.1/pre").save(pdf, recompute_hash=True)
        record = sidecar_path(pdf)
    trashed = lib / UPG / name
    trashed.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(pdf), str(trashed))
    if control:
        assert find_orphans(lib) == [record], "control: the old move made an orphan"
    return record, trashed


def _stranded_by_rename(lib, name="Krylov, N.V. - Drift.pdf"):
    pdf = lib / "01 - Published papers" / "K" / name
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(f"%PDF-1.4 {name}".encode())
    PaperIdentity(doi="10.1/shelf").save(pdf, recompute_hash=True)
    record = sidecar_path(pdf)
    moved = pdf.with_name("Krylov, N. V. - Drift.pdf")
    pdf.rename(moved)
    return record, moved


# ------------------------------------------------------------- the plan

@pytest.mark.parametrize("name,full", [
    ("Cao, C. - Recursive equilibrium.pdf", False),          # ordinary
    (_name(MAX_BASENAME_BYTES + 9), False),                  # coded .sidecars
    (_name(MAX_BASENAME_BYTES + 4), True),                   # full name, 255 B
])
def test_a_record_left_by_an_old_trash_move_is_found(lib, name, full):
    record, trashed = _stranded_in_trash(lib, name, full_name=full)
    plan = plan_reconnect(lib)
    assert plan["to_trash"] == [(record, trashed)]
    assert plan["matched"] == [] and plan["unmatched"] == []
    assert plan["trash_candidates"] == 1


def test_a_paper_on_the_shelves_always_comes_first(lib):
    body = b"%PDF-1.4 same contents"
    record, trashed = _stranded_in_trash(lib, body=body)
    shelf = lib / "01 - Published papers" / "C" / "Cao, C. - Recursive equilibrium.pdf"
    shelf.parent.mkdir(parents=True)
    shelf.write_bytes(body)
    plan = plan_reconnect(lib)
    assert plan["matched"] == [(record, shelf)] and plan["to_trash"] == []


def test_two_trashed_papers_with_its_contents_are_not_guessed_between(lib):
    record, trashed = _stranded_in_trash(lib)
    twin = lib / ".trash" / "duplicates" / trashed.name
    twin.parent.mkdir(parents=True)
    twin.write_bytes(trashed.read_bytes())
    plan = plan_reconnect(lib)
    assert plan["to_trash"] == [] and plan["unmatched"] == [record]


def test_two_records_wanting_one_trashed_paper_are_not_chosen_between(lib):
    """The standing ruling: two records for one paper are merged, never
    picked from. Neither is offered; both stay where they are."""
    record, trashed = _stranded_in_trash(lib)
    second = lib / MIRROR_DIR_NAME / PRE / "Cao, C. - Recursive equilibrium (copy).meta.json"
    second.write_text(record.read_text())
    plan = plan_reconnect(lib)
    assert plan["to_trash"] == []
    assert sorted(plan["unmatched"]) == sorted([record, second])
    assert apply_trash_reconnect(lib, plan, dry_run=False)["reconnected"] == 0


def test_a_trashed_paper_with_a_record_of_its_own_is_not_offered_another(lib):
    record, trashed = _stranded_in_trash(lib)
    PaperIdentity(doi="10.1/its-own").save(trashed, recompute_hash=False)
    plan = plan_reconnect(lib)
    assert plan["to_trash"] == [] and plan["unmatched"] == [record]
    assert plan["trash_candidates"] == 0


def test_an_archival_record_is_left_alone_and_says_why(lib):
    record, trashed = _stranded_in_trash(lib, "Vol 3.pdf", folder=f"{JEHPS}/2007")
    plan = plan_reconnect(lib)
    assert plan["to_trash"] == []
    assert plan["unmatched"] == [record]
    [(r, why)] = plan["to_trash_refused"]
    assert r == record and "archival" in why


def test_without_a_trash_nothing_is_offered(lib):
    record, moved = _stranded_by_rename(lib)
    moved.unlink()
    plan = plan_reconnect(lib)
    assert plan["to_trash"] == [] and plan["trash_candidates"] == 0
    assert plan["unmatched"] == [record]


def test_a_record_without_a_fingerprint_matches_nothing(lib):
    record, trashed = _stranded_in_trash(lib)
    data = json.loads(record.read_text())
    data.pop("content_sha256")
    record.write_text(json.dumps(data))
    assert plan_reconnect(lib)["to_trash"] == []


def test_the_former_place_of_a_coded_record_is_its_folder(lib):
    rec = lib / MIRROR_DIR_NAME / PRE / ".sidecars" / ("a" * 16 + ".meta.json")
    assert _former_place(lib, rec).parent == lib / PRE
    plain = lib / MIRROR_DIR_NAME / PRE / "Cao, C. - X.meta.json"
    assert _former_place(lib, plain) == lib / PRE / "Cao, C. - X.pdf"


# ------------------------------------------------------------- the apply

def test_the_record_joins_its_paper_and_one_undo_brings_it_back(lib):
    record, trashed = _stranded_in_trash(lib)
    before = record.read_bytes()
    out = apply_trash_reconnect(lib, plan_reconnect(lib), dry_run=False)
    assert out["reconnected"] == 1 and out["skipped"] == []
    assert out["moved"] == [{"sidecar": record.name, "paper": trashed.name,
                             "still": []}]
    assert find_sidecar(trashed) == sidecar_path(trashed)
    moved = json.loads(sidecar_path(trashed).read_text())
    assert moved == {**json.loads(before), "copy_locations": [str(trashed)]}, (
        "the record names its paper where it is now, and nothing else changed")
    assert not record.exists() and find_orphans(lib) == []
    log = UndoLog(log_dir=lib / ".operation_log")
    [tx] = log.list_transactions()
    assert tx["description"] == "Put 1 saved record(s) with their papers in the trash"
    log.undo_transaction(out["tx_id"])
    assert record.read_bytes() == before and find_sidecar(trashed) is None


def test_each_button_moves_only_its_own_list(lib):
    trash_record, trashed = _stranded_in_trash(lib)
    shelf_record, shelf_pdf = _stranded_by_rename(lib)
    plan = plan_reconnect(lib)
    assert len(plan["matched"]) == 1 and len(plan["to_trash"]) == 1
    apply_trash_reconnect(lib, plan, dry_run=False)
    assert shelf_record.exists(), "the trash button touched a shelf record"
    assert find_sidecar(shelf_pdf) is None
    assert find_sidecar(trashed) is not None
    apply_reconnect(lib, plan_reconnect(lib), dry_run=False)
    assert find_sidecar(shelf_pdf) is not None


def test_a_dry_run_moves_nothing(lib):
    record, trashed = _stranded_in_trash(lib)
    out = apply_trash_reconnect(lib, plan_reconnect(lib))
    assert out == {"dry_run": True, "would_reconnect": 1}
    assert record.exists() and find_sidecar(trashed) is None
    assert not (lib / ".operation_log").exists() or not list(
        (lib / ".operation_log").glob("*.json"))


def test_a_paper_put_back_on_the_shelf_since_the_check_keeps_its_record(lib):
    """The undo of the move that stranded it, run after the check."""
    record, trashed = _stranded_in_trash(lib)
    plan = plan_reconnect(lib)
    shutil.move(str(trashed), str(lib / PRE / trashed.name))
    out = apply_trash_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0
    assert out["skipped"][0]["reason"] == "the paper is no longer where the check found it"
    assert record.exists()


@pytest.mark.parametrize("name", ["Cao, C. - Recursive equilibrium.pdf",
                                  _name(MAX_BASENAME_BYTES + 9)])
def test_a_record_a_shelf_paper_reads_again_is_not_taken_from_it(lib, name):
    """A copy of the paper came back to the record's old place since the
    check (the trashed one is still there): the record is no orphan now."""
    record, trashed = _stranded_in_trash(lib, name)
    plan = plan_reconnect(lib)
    shutil.copy2(trashed, lib / PRE / trashed.name)
    assert find_sidecar(lib / PRE / trashed.name) == record
    out = apply_trash_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0
    assert out["skipped"][0]["reason"] == "a paper in the library reads this record again"
    assert record.exists() and find_sidecar(trashed) is None


def test_a_record_another_paper_in_that_folder_would_not_read_is_still_moved(lib):
    """The re-check asks whether the record is READ, not whether its folder
    has papers in it."""
    record, trashed = _stranded_in_trash(lib)
    other = lib / PRE / "Cao, C. - Something else.pdf"
    other.write_bytes(b"%PDF-1.4 other")
    PaperIdentity(doi="10.1/other").save(other, recompute_hash=True)
    out = apply_trash_reconnect(lib, plan_reconnect(lib), dry_run=False)
    assert out["reconnected"] == 1


def test_a_trashed_paper_that_got_a_record_since_keeps_it(lib):
    record, trashed = _stranded_in_trash(lib)
    plan = plan_reconnect(lib)
    PaperIdentity(doi="10.1/arrived").save(trashed, recompute_hash=False)
    out = apply_trash_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0 and "already has a record" in out["skipped"][0]["reason"]
    assert PaperIdentity.load(trashed).doi == "10.1/arrived"


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


def _press(C, monkeypatch, *, tick=(), press=()):
    """Tick the checkboxes and press the buttons named by key; record calls."""
    calls = []

    def checkbox(label, *a, key=None, **k):
        calls.append(("checkbox", key, label))
        return key in tick

    def button(label, *a, key=None, disabled=False, **k):
        calls.append(("button", key, label, disabled))
        return key in press and not disabled

    monkeypatch.setattr(C.st, "checkbox", checkbox)
    monkeypatch.setattr(C.st, "button", button)
    monkeypatch.setattr(C.st, "rerun", lambda: None)
    return calls


def _activity(tmp_path):
    p = tmp_path / "home" / ".mathpdf" / "cockpit_activity.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_the_page_lists_them_apart_and_offers_their_own_button(C, lib, monkeypatch):
    _stranded_in_trash(lib)
    _stranded_by_rename(lib)
    shown = []
    monkeypatch.setattr(C.st, "markdown", lambda t, *a, **k: shown.append(t))
    monkeypatch.setattr(C.st, "expander",
                        lambda label, *a, **k: shown.append(label) or C.st.container())
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    calls = _press(C, monkeypatch)
    C._render_orphan_repair(lib, 2)
    assert any("**1** belong to papers already in the trash" in s for s in shown), shown
    assert any("whose paper is already in the trash" in s for s in shown)
    buttons = {c[1]: c for c in calls if c[0] == "button"}
    assert set(buttons) == {"orphan_plan_run", "orphan_trash_apply", "orphan_apply"}
    assert buttons["orphan_trash_apply"][3] is True, "enabled before the list was read"


def test_with_nothing_to_reconnect_the_trash_ones_are_still_offered(C, lib, monkeypatch):
    _stranded_in_trash(lib)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    calls = _press(C, monkeypatch)
    C._render_orphan_repair(lib, 1)
    assert [c[1] for c in calls if c[0] == "button"] == ["orphan_plan_run",
                                                         "orphan_trash_apply"]


def test_pressing_it_runs_under_the_lock_logs_and_reports(C, lib, monkeypatch, tmp_path):
    record, trashed = _stranded_in_trash(lib)
    shelf_record, _ = _stranded_by_rename(lib)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    _press(C, monkeypatch, tick={"orphan_trash_confirm"}, press={"orphan_trash_apply"})
    locked, cleared = [], []
    real = C._locked_call
    monkeypatch.setattr(C, "_locked_call", lambda lib_, action, fn, *a, **k:
                        locked.append(action) or real(lib_, action, fn, *a, **k))
    monkeypatch.setattr(C, "_clear_scan_caches", lambda: cleared.append(1))
    C._render_orphan_repair(lib, 2)
    assert locked == ["Put records with their papers in the trash"]
    assert cleared == [1], "the scans cached before the move would still count them"
    assert find_sidecar(trashed) is not None and not record.exists()
    assert shelf_record.exists(), "Reconnect's records are not this button's"
    kind, msg, details = C.st.session_state["flash"][-1][:3]
    assert kind == "success" and "Put 1 of 1 record(s)" in msg and "Undo" in msg
    assert details == [f"moved: {record.name[:-len('.meta.json')]} — now beside "
                       f"{trashed.name} in the trash"]
    [entry] = _activity(tmp_path)
    assert entry["action"] == "conformance.records_to_trash" and entry["tx_id"]
    assert "put with their papers in the trash" in C.st.session_state["conformance_outdated"]
    assert "orphan_plan" not in C.st.session_state


def test_unticked_it_does_nothing(C, lib, monkeypatch, tmp_path):
    record, trashed = _stranded_in_trash(lib)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    _press(C, monkeypatch, press={"orphan_trash_apply"})
    C._render_orphan_repair(lib, 1)
    assert record.exists() and _activity(tmp_path) == []


def test_what_was_left_is_named_with_its_reason(C, lib, monkeypatch, tmp_path):
    a, ta = _stranded_in_trash(lib, "A, A. - One.pdf")
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    ta.unlink()
    _press(C, monkeypatch, tick={"orphan_trash_confirm"}, press={"orphan_trash_apply"})
    C._render_orphan_repair(lib, 1)
    kind, msg, details = C.st.session_state["flash"][-1][:3]
    assert kind == "error" and "Put 0 of 1" in msg and "Undo" not in msg
    assert details == ["left as it was: A, A. - One — the paper is no longer "
                       "where the check found it"]
    assert _activity(tmp_path) == [] and a.exists()


def test_a_partial_run_is_a_warning(C, lib, monkeypatch):
    a, ta = _stranded_in_trash(lib, "A, A. - One.pdf")
    (lib / PRE / "B, B. - Two.pdf").write_bytes(b"%PDF-1.4 two")
    PaperIdentity(doi="10.1/b").save(lib / PRE / "B, B. - Two.pdf", recompute_hash=True)
    rb = sidecar_path(lib / PRE / "B, B. - Two.pdf")
    tb = lib / UPG / "B, B. - Two.pdf"
    shutil.move(str(lib / PRE / "B, B. - Two.pdf"), str(tb))
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    assert len(C.st.session_state["orphan_plan"]["to_trash"]) == 2
    tb.unlink()
    _press(C, monkeypatch, tick={"orphan_trash_confirm"}, press={"orphan_trash_apply"})
    C._render_orphan_repair(lib, 2)
    kind, msg, details = C.st.session_state["flash"][-1][:3]
    assert kind == "warning" and "Put 1 of 2" in msg and "1 were left" in msg
    assert len(details) == 2 and rb.exists() and not a.exists()


def test_a_refused_archival_match_is_named_on_the_page(C, lib, monkeypatch):
    _stranded_in_trash(lib, "Vol 3.pdf", folder=f"{JEHPS}/2007")
    captions = []
    monkeypatch.setattr(C.st, "caption", lambda t, *a, **k: captions.append(t))
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    calls = _press(C, monkeypatch)
    C._render_orphan_repair(lib, 1)
    assert any("Vol 3" in c and "left alone" in c and "archival" in c for c in captions)
    assert [c[1] for c in calls if c[0] == "button"] == ["orphan_plan_run"]


# ------------------------------------------------------------ the property

def _files(lib: Path) -> dict:
    return {p.relative_to(lib): p.read_bytes() for p in lib.rglob("*")
            if p.is_file() and ".operation_log" not in p.parts}


@settings(max_examples=30, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.lists(st.sampled_from(["trash", "twin", "rename", "archival", "gone",
                                 "trash-own"]), min_size=1, max_size=6))
def test_the_plan_partitions_the_orphans_and_the_trash_apply_takes_only_its_own(
        tmp_path, kinds):
    """For any mix of stranded records: every orphan is in exactly one list;
    only lone, record-less, non-archival trash matches are offered; the
    apply moves exactly those, and one undo puts every file back."""
    import tempfile
    lib = Path(tempfile.mkdtemp(dir=tmp_path))
    enable_sidecar_mirror(lib)
    expect_trash = set()
    for i, kind in enumerate(kinds):
        name, body = f"P{i}, A. - Paper {i}.pdf", f"%PDF-1.4 paper {i}".encode()
        folder = f"{JEHPS}/2007" if kind == "archival" else PRE
        if kind == "rename":
            pdf = lib / "01 - Published papers" / "P" / name
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(body)
            PaperIdentity(doi=f"10.1/{i}").save(pdf, recompute_hash=True)
            pdf.rename(pdf.with_name(f"P{i}, A. - Paper {i} v2.pdf"))
            continue
        record, trashed = _stranded_in_trash(lib, name, folder=folder, body=body,
                                             control=False)
        if kind == "trash":
            expect_trash.add(record)
        elif kind == "twin":
            twin = lib / ".trash" / "duplicates" / name
            twin.parent.mkdir(parents=True, exist_ok=True)
            twin.write_bytes(body)
        elif kind == "gone":
            trashed.unlink()
        elif kind == "trash-own":
            PaperIdentity(doi="own").save(trashed, recompute_hash=False)

    orphans = find_orphans(lib)
    plan = plan_reconnect(lib)
    lists = ([s for s, _ in plan["matched"]] + plan["ambiguous"]
             + [s for s, _ in plan["to_trash"]] + plan["unmatched"])
    assert sorted(lists) == orphans, "an orphan is in no list, or in two"
    assert {s for s, _ in plan["to_trash"]} == expect_trash
    for s, pdf in plan["to_trash"]:
        assert pdf.is_relative_to(lib / ".trash") and find_sidecar(pdf) is None
        assert json.loads(s.read_text())["content_sha256"] == compute_content_hash(pdf)

    before = _files(lib)
    out = apply_trash_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == len(expect_trash) and out["skipped"] == []
    assert find_orphans(lib) == sorted(set(orphans) - expect_trash)
    if out["tx_id"]:
        UndoLog(log_dir=lib / ".operation_log").undo_transaction(out["tx_id"])
    assert _files(lib) == before
