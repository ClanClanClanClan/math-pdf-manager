"""The Monday sweep has a switch, a status and a last run -- and runs safely.

Cockpit audit finding 16 (approved). ``WEEKLY_LABEL`` had exactly one
occurrence in the tree: its definition. No switch, no status, no last
run; the newest report on this Mac is from 2026-04-03. And the sweep,
had anyone turned it on, was not fit to run unattended:

  * "file the safe ones" called ``upgrade_paper`` without the
    ``download_dir`` it requires -- a TypeError per paper, collected into
    a list the printed summary never mentioned -- and with no undo log,
    so had it worked, the preprints it trashed could not come back. Its
    tests stubbed ``upgrade_paper`` with a mock that accepts anything;
  * its publication check rewrote every paper's record unlocked and
    outside the undo log (fixed for the cockpit's own button in finding 2);
  * turning on automatic filing, whenever the filer's service file was
    missing, also installed the sweep WITH auto-apply, and launchd starts
    it at login -- unattended moves nobody had switched on.
"""
from __future__ import annotations

import json
import os
import plistlib
import sys
import time
from pathlib import Path

import pytest

import ui.cockpit_actions as A


# ------------------------------------------------- the sweep's own safety

@pytest.fixture
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    root = tmp_path / "lib"
    root.mkdir()
    enable_sidecar_mirror(root)
    return root


def _preprint(lib):
    p = lib / "02 - Unpublished papers" / "S" / "Smith, J. - A result.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4 preprint")
    return p


def _safe_hit(pdf):
    return {"file": str(pdf), "filename": pdf.name, "parsed_authors": ["Smith"],
            "published": True,
            "match": {"doi": "10.1/x", "confidence": 0.99, "author_count": 1}}


def test_file_the_safe_ones_runs_the_real_upgrader_reversibly(lib, monkeypatch):
    """No stub of upgrade_paper here: the call itself is what was broken."""
    import processing.upgrade_to_published as up
    import processing.ingest as ingest
    from maintenance.weekly_report import auto_apply_safe_transitions
    from processing.undo_log import UndoLog
    pre = _preprint(lib)
    seen_dirs = []

    def _download(doi, download_dir):
        seen_dirs.append(Path(download_dir))
        f = Path(download_dir) / "published.pdf"
        f.write_bytes(b"%PDF-1.4 the published version, a little longer")
        return f

    def _ingest(pdf, *, library_root, undo_log=None, canonical_override, **k):
        # Like the real one: a COPY into the library, logged.
        import shutil
        dest = library_root / "01 - Published papers" / "S" / f"{canonical_override}.pdf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        undo_log.record_copy(pdf, dest)
        shutil.copy2(pdf, dest)
        return {"success": True, "destination": str(dest)}

    monkeypatch.setattr(up, "try_download_by_doi", _download)
    monkeypatch.setattr(ingest, "ingest_paper", _ingest)
    results = {"publications": {"unpublished": [_safe_hit(pre)], "working": []}}
    summary = auto_apply_safe_transitions(results, lib, dry_run=False)
    assert summary["errors"] == [], summary["errors"]
    assert summary["upgraded"] == [str(pre)]
    assert seen_dirs and not seen_dirs[0].exists(), "a download folder, cleaned up after"
    assert not pre.exists(), "the preprint went to the trash"
    tx = summary["upgrade_tx_id"]
    assert tx and (lib / ".operation_log" / f"{tx}.json").exists(), (
        "the run must be one Activity entry in the library's own log")
    UndoLog(log_dir=lib / ".operation_log").undo_transaction(tx)
    assert pre.exists(), "and it can be put back"


def test_an_upgrade_that_raises_is_a_problem_not_a_success(lib, monkeypatch):
    import processing.upgrade_to_published as up
    from maintenance.weekly_report import auto_apply_safe_transitions, run_problems
    pre = _preprint(lib)
    monkeypatch.setattr(up, "try_download_by_doi",
                        lambda doi, d: (_ for _ in ()).throw(OSError("network down")))
    results = {"publications": {"unpublished": [_safe_hit(pre)], "working": []}}
    results["auto_applied"] = auto_apply_safe_transitions(results, lib, dry_run=False)
    assert results["auto_applied"]["upgraded"] == []
    problems = run_problems(results)
    assert any("network down" in p for p in problems), problems
    assert pre.exists()


@pytest.mark.parametrize("pubs,auto,needle", [
    ({"_not_checked": ["publications: lock"]}, {}, "not checked"),
    ({"_errors": [{"step": "check/02", "error": "boom"}]}, {}, "boom"),
    ({"unchecked": ["a.pdf", "b.pdf"]}, {}, "2 paper(s) could not be looked up"),
    ({}, {"skipped": "another process holds the lock"}, "nothing was filed"),
    ({}, {"errors": ["x.pdf: ERROR: y"]}, "auto-apply"),
])
def test_every_way_a_run_falls_short_is_named(pubs, auto, needle):
    from maintenance.weekly_report import run_problems
    assert any(needle in p for p in run_problems({"publications": pubs,
                                                  "auto_applied": auto}))


def test_a_complete_run_has_no_problems():
    from maintenance.weekly_report import run_problems
    assert run_problems({"publications": {"unpublished": [], "working": [],
                                          "unchecked": [], "_errors": [],
                                          "_not_checked": []},
                         "auto_applied": {"errors": []}}) == []


def test_the_printed_summary_says_incomplete(monkeypatch, tmp_path, capsys):
    import maintenance.weekly_report as W
    monkeypatch.setattr(W, "run_maintenance", lambda *a, **k: {
        "publications": {"unpublished": [], "working": []}, "aging": [],
        "duplicates": [], "problems": ["not checked — publications: lock"]})
    W.main(["--library", str(tmp_path), "--report-dir", str(tmp_path / "r"),
            "--dry-run", "--no-notify"])
    out = capsys.readouterr().out
    assert "INCOMPLETE (1 problem(s))" in out and "publications: lock" in out


def _record_for(pdf):
    from processing.identity import PaperIdentity
    PaperIdentity().save(pdf, recompute_hash=True)


def test_the_sweeps_publication_check_is_one_undoable_transaction(lib, monkeypatch):
    import processing.publication_checker as pc
    from maintenance.weekly_report import _check_publications_logged
    from processing.identity import PaperIdentity
    pre = _preprint(lib)
    _record_for(pre)
    monkeypatch.setattr(pc, "scan_directory", lambda folder, **k: [
        {"file": str(pre), "filename": pre.name, "parsed_authors": ["Smith"],
         "published": False}] if "02" in str(folder) else [])
    (lib / "03 - Working papers").mkdir()
    _check_publications_logged(lib)
    assert PaperIdentity.load(pre).recheck_count == 1
    logs = list((lib / ".operation_log").glob("*.json"))
    assert len(logs) == 1 and "Monday sweep" in logs[0].read_text()


def test_the_sweep_waits_for_the_lock_then_says_it_could_not(lib, monkeypatch):
    import maintenance.weekly_report as W
    from processing.locking import LibraryLock
    monkeypatch.setattr(W, "SWEEP_LOCK_WAIT_SECONDS", 0.2)
    other = LibraryLock(lib)
    assert other.acquire(blocking=False)
    try:
        out = W._check_publications_logged(lib)
    finally:
        other.release()
    assert out["_not_checked"] and "lock" in out["_not_checked"][0]
    assert any("not checked" in p for p in W.run_problems({"publications": out}))


# ------------------------------------------------------ installing services

class _Proc:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


@pytest.fixture
def launchctl(monkeypatch):
    """Every launchctl call recorded, none made."""
    calls = []
    monkeypatch.setattr(A, "_launchctl",
                        lambda *args, **k: calls.append(args) or _Proc())
    return calls


@pytest.fixture
def home(tmp_path, monkeypatch, launchctl):
    h = tmp_path / "home"
    h.mkdir()
    monkeypatch.setenv("HOME", str(h))
    return h


def _agents(home):
    d = home / "Library" / "LaunchAgents"
    return sorted(p.name for p in d.glob("*.plist")) if d.is_dir() else []


def _args(home, label):
    body = (home / "Library" / "LaunchAgents" / f"{label}.plist").read_bytes()
    return plistlib.loads(body)["ProgramArguments"]


def test_turning_on_filing_installs_only_the_filer(home, monkeypatch):
    from watcher.config import WatcherConfig
    monkeypatch.setattr(WatcherConfig, "load",
                        classmethod(lambda cls, *a, **k: type("C", (), {"inbox_dir": home / "inbox"})()))
    ok, msg = A.start_watcher()
    assert ok, msg
    assert _agents(home) == [f"{A.WATCHER_LABEL}.plist"], (
        "the Monday sweep must never ride in on the filer's switch")


def test_the_sweep_installs_without_auto_apply_unless_asked(home, launchctl):
    ok, _ = A.start_weekly()
    assert ok and _agents(home) == [f"{A.WEEKLY_LABEL}.plist"]
    args = _args(home, A.WEEKLY_LABEL)
    assert A.AUTO_APPLY_FLAG not in args and "maintenance.weekly_report" in args
    assert sys.executable in args, "the cockpit's interpreter, with its packages"
    ok, _ = A.start_weekly(auto_apply_safe=True)
    assert ok and A.AUTO_APPLY_FLAG in _args(home, A.WEEKLY_LABEL)
    assert ("bootstrap", f"gui/{os.getuid()}",
            str(home / "Library" / "LaunchAgents" / f"{A.WEEKLY_LABEL}.plist")) in launchctl


def test_turning_it_off_sets_the_file_aside_so_a_login_cannot_restart_it(home):
    A.start_weekly()
    ok, msg = A.stop_weekly()
    assert ok, msg
    assert _agents(home) == []
    assert (home / ".mathpdf" / "services_off" / f"{A.WEEKLY_LABEL}.plist").exists()


def test_a_failed_bootstrap_is_reported(home, monkeypatch):
    monkeypatch.setattr(A, "_launchctl", lambda *a, **k: _Proc(
        rc=5 if a[0] == "bootstrap" else 0, err="Bootstrap failed: 5"))
    ok, msg = A.start_weekly()
    assert not ok and "Bootstrap failed" in msg


# ------------------------------------------------------------ its status

def _report(home, days_ago, payload):
    d = home / ".mathpdf" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"maintenance_x{days_ago}.json"
    p.write_text(json.dumps(payload))
    t = time.time() - days_ago * 86400
    os.utime(p, (t, t))
    return p


def test_status_of_a_sweep_that_was_never_set_up(home):
    w = A.weekly_status()
    assert (w["installed"], w["on"], w["last_run"], w["problems"]) == (False, False, None, None)


def test_status_reads_the_last_report_and_its_problems(home):
    _report(home, 40, {"problems": []})
    _report(home, 3, {"problems": ["not checked — lock"]})
    w = A.weekly_status()
    assert 2.9 < w["age_days"] < 3.1
    assert w["problems"] == ["not checked — lock"]


def test_an_old_report_without_the_field_is_not_called_clean(home):
    _report(home, 3, {"publications": {}})
    assert A.weekly_status()["problems"] is None


def test_a_crash_newer_than_the_last_report_is_shown(home):
    _report(home, 3, {"problems": []})
    err = home / ".mathpdf" / "weekly.stderr"
    err.write_text("Traceback ...\nModuleNotFoundError: No module named 'rapidfuzz'\n")
    assert "rapidfuzz" in A.weekly_status()["last_error"]
    t = time.time() - 10 * 86400
    os.utime(err, (t, t))
    assert A.weekly_status()["last_error"] is None, "an OLDER error was dealt with"


@pytest.mark.parametrize("rc,text,on", [
    (0, "state = not running", True),
    (113, 'Could not find service "x" in domain', False),
    (1, "launchctl went sideways", None),
])
def test_on_is_three_valued(home, monkeypatch, rc, text, on):
    A.start_weekly()
    monkeypatch.setattr(A, "_launchctl", lambda *a, **k: _Proc(rc=rc, err=text))
    assert A.weekly_status()["on"] is on


# ------------------------------------------------------------ the cockpit

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


@pytest.mark.parametrize("w,kind,needle", [
    ({"on": False}, "caption", "off · has never run"),
    ({"on": True, "last_run": "2026-10-05T09:00", "age_days": 4}, "caption", "on · last ran 4 days ago"),
    ({"on": True, "auto_apply": True, "last_run": "2026-10-05T09:00", "age_days": 4},
     "caption", "files the safe ones"),
    ({"on": True, "last_run": "2026-04-03T09:00", "age_days": 189}, "warning", "overdue"),
    ({"on": None, "last_run": None}, "warning", "CAN'T CONFIRM"),
    ({"on": True, "last_run": "2026-10-05T09:00", "age_days": 4,
      "problems": ["x"]}, "warning", "INCOMPLETE"),
    ({"on": True, "last_error": "Traceback"}, "error", "FAILED"),
])
def test_the_one_line_status(C, w, kind, needle):
    got_kind, text = C._weekly_summary(w)
    assert got_kind == kind and needle in text, text


def _page(C, monkeypatch, status, pressed=(), ticked=False):
    import ui.cockpit_actions as acts
    calls = []
    monkeypatch.setattr(C, "_weekly_status_cached", type("F", (), {
        "__call__": lambda self: status, "clear": lambda self: None})())
    monkeypatch.setattr(acts, "start_weekly",
                        lambda **k: calls.append(("start", k)) or (True, "on"))
    monkeypatch.setattr(acts, "stop_weekly", lambda: calls.append(("stop",)) or (True, "off"))
    monkeypatch.setattr(C.st, "button", lambda label, *a, **k: label in pressed)
    monkeypatch.setattr(C.st, "checkbox", lambda label, *a, **k: ticked)
    # The controls sit in columns: hand back the module itself, so
    # cols[i].button is the patched st.button.
    monkeypatch.setattr(C.st, "columns", lambda spec, *a, **k:
                        [C.st] * (spec if isinstance(spec, int) else len(spec)))
    monkeypatch.setattr(C.st, "rerun", lambda: None)
    C._render_weekly_service()
    return calls


def test_turning_it_on_from_the_page_leaves_auto_apply_off_by_default(C, monkeypatch):
    calls = _page(C, monkeypatch, {"on": False}, pressed={"Turn the Monday sweep on"})
    assert calls == [("start", {"auto_apply_safe": False})]


def test_auto_apply_only_with_the_tick(C, monkeypatch):
    calls = _page(C, monkeypatch, {"on": False}, pressed={"Turn the Monday sweep on"},
                  ticked=True)
    assert calls == [("start", {"auto_apply_safe": True})]


def test_turning_it_off(C, monkeypatch):
    calls = _page(C, monkeypatch, {"on": True}, pressed={"Turn the Monday sweep off"})
    assert calls == [("stop",)]


def test_an_old_upgrade_report_says_it_is_old(monkeypatch, tmp_path):
    from tests.ui.test_cockpit_renders_content import _RecStreamlit, rendered_text
    stub = _RecStreamlit([], {})
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as C
    rep = tmp_path / "home" / ".mathpdf" / "reports" / "maintenance_old.json"
    rep.parent.mkdir(parents=True)
    rep.write_text(json.dumps({"published": []}))
    monkeypatch.setattr(C, "_find_publication_reports", lambda: [rep])
    stub.session_state["upgrade_report_path"] = None
    for days, expect in ((152, True), (2, False)):
        t = time.time() - days * 86400
        os.utime(rep, (t, t))
        stub.calls.clear()
        C.render_upgrade_queue()
        text = rendered_text(stub)
        assert ("152 days old" in text) is expect


def test_a_paper_that_fails_after_writing_still_leaves_an_undo_record(lib, monkeypatch):
    """The batch committed only when its COUNTS showed a download or a
    flag. A paper that wrote something and then raised counted as neither
    -- and what it had recorded was discarded with the transaction,
    leaving a change in the library nothing could undo."""
    import processing.upgrade_to_published as up
    pre = _preprint(lib)
    copied = lib / "01 - Published papers" / "S" / "Smith, J. - A result.pdf"

    def _writes_then_raises(entry, library_root, download_dir, *, dry_run=False,
                            manual_only=False, undo_log=None):
        copied.parent.mkdir(parents=True, exist_ok=True)
        undo_log.record_copy(Path(download_dir) / "published.pdf", copied)
        copied.write_bytes(b"%PDF-1.4 published")
        raise PermissionError("could not remove the temporary download")

    monkeypatch.setattr(up, "upgrade_paper", _writes_then_raises)
    out = up.upgrade_entries([_safe_hit(pre)], lib, dry_run=False)
    assert out["downloaded"] == out["flagged"] == 0
    assert out["tx_id"], "the recorded copy must be committed, not discarded"
    body = (lib / ".operation_log" / f"{out['tx_id']}.json").read_text()
    assert "Smith, J. - A result.pdf" in body


@pytest.mark.parametrize("result,where", [
    ({"success": True, "action": "DOWNLOADED + FILED + DELETED preprint"}, "upgraded"),
    ({"success": False, "action": "DOWNLOADED but error during filing: x"}, "errors"),
    ({"success": False, "action": "DOWNLOADED but filing failed: x"}, "errors"),
    ({"success": True, "action": "FLAGGED for manual download → J/"}, "skipped_borderline"),
    ({"success": False, "action": "SKIP: no DOI"}, "skipped_borderline"),
    ({"success": False, "action": "ERROR: boom"}, "errors"),
])
def test_each_upgrade_outcome_is_reported_as_what_it_was(lib, monkeypatch, result, where):
    import processing.upgrade_to_published as up
    from maintenance.weekly_report import auto_apply_safe_transitions
    pre = _preprint(lib)
    monkeypatch.setattr(up, "upgrade_paper",
                        lambda entry, library_root, download_dir, **k: dict(result))
    s = auto_apply_safe_transitions(
        {"publications": {"unpublished": [_safe_hit(pre)], "working": []}},
        lib, dry_run=False)
    got = [k for k in ("upgraded", "errors", "skipped_borderline") if s[k]]
    assert got == [where], s


def test_filed_but_the_preprint_stuck_is_both_an_upgrade_and_a_problem(lib, monkeypatch):
    import processing.upgrade_to_published as up
    from maintenance.weekly_report import auto_apply_safe_transitions
    pre = _preprint(lib)
    monkeypatch.setattr(up, "upgrade_paper", lambda e, l, d, **k: {
        "success": True, "action": "DOWNLOADED + FILED but preprint move error: busy"})
    s = auto_apply_safe_transitions(
        {"publications": {"unpublished": [_safe_hit(pre)], "working": []}},
        lib, dry_run=False)
    assert s["upgraded"] == [str(pre)] and "preprint move error" in s["errors"][0]
