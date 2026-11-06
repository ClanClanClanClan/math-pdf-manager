"""Every background run leaves one line: OK, a problem, or unknown.

Step-back audit G1-3 and D12-3. The hourly "put back saved details" failed
38 times by 2026-11-06, each on a test's temporary folder, and no screen
knew; a quiet pass logged nothing, so "ran, nothing to do" could not be
told from "did not run"; and it read up to 1 MB of each of 575 papers that
have never been filed, every hour.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, strategies as hst

from maintenance import job_runs as J
from processing.identity import PaperIdentity, enable_sidecar_mirror, sidecar_path
from processing import sidecar_repair as R
import watcher.daemon as D
from watcher.config import WatcherConfig


@pytest.fixture
def logs(tmp_path):
    return tmp_path / "logs"


# ----------------------------------------------------------- the one line

def test_a_run_is_noted_and_read_back(logs):
    J.record_run(J.PUT_BACK, J.OK, "0 put back", log_dir=logs)
    row = J.last_run(J.PUT_BACK, log_dir=logs)
    assert (row["state"], row["text"]) == (J.OK, "0 put back") and row["time"]


def test_jobs_keep_to_their_own_lines(logs):
    J.record_run("a", J.OK, "x", log_dir=logs)
    J.record_run("b", J.PROBLEM, "y", log_dir=logs)
    assert J.last_run("a", log_dir=logs)["text"] == "x"
    assert J.last_run("c", log_dir=logs) is None


def test_no_note_yet_is_none_not_fine(logs):
    assert J.last_run(J.PUT_BACK, log_dir=logs) is None and J.runs("x", log_dir=logs) == []


def test_a_damaged_line_is_passed_over(logs):
    J.record_run("a", J.OK, "x", log_dir=logs)
    with open(J.runs_path(logs), "a") as f:
        f.write("{ torn\n[1]\n")
    J.record_run("a", J.OK, "y", log_dir=logs)
    assert [r["text"] for r in J.runs("a", log_dir=logs)] == ["x", "y"]


def test_the_file_stays_small(logs, monkeypatch):
    monkeypatch.setattr(J, "KEEP_LINES", 3)
    for n in range(7):
        J.record_run("a", J.OK, str(n), log_dir=logs)
    assert [r["text"] for r in J.runs("a", log_dir=logs)] == ["4", "5", "6"]


def test_a_note_that_cannot_be_written_never_stops_the_job(tmp_path):
    blocked = tmp_path / "a-file"
    blocked.write_text("x")
    J.record_run("a", J.OK, "x", log_dir=blocked)        # no exception
    assert blocked.read_text() == "x" and J.last_run("a", log_dir=blocked) is None


@given(hst.lists(hst.sampled_from([J.OK, J.PROBLEM, J.UNKNOWN]), max_size=8))
def test_property_exactly_two_failures_running(tmp_path_factory, states):
    logs = tmp_path_factory.mktemp("l")
    for s in states:
        J.record_run("a", s, "t", log_dir=logs)
    want = (len(states) >= 2 and states[-2:] == [J.PROBLEM, J.PROBLEM]
            and (len(states) == 2 or states[-3] != J.PROBLEM))
    assert J.just_failed_twice("a", log_dir=logs) is want


# ------------------------------------------------- what the hourly job notes

def _config(tmp_path, notifications=True):
    return WatcherConfig(inbox_dir=tmp_path / "inbox", library_root=tmp_path / "lib",
                         log_dir=tmp_path / "logs", notifications=notifications)


@pytest.mark.parametrize("result,state,words", [
    ({"orphans": 3, "reconnected": 2, "tx_id": "t", "left": [], "skipped": []}, J.OK,
     "2 put back, 3 record(s)"),
    ({"orphans": 0, "reconnected": 0}, J.OK, "0 put back"),
    ({"busy": True}, J.UNKNOWN, "busy"),
    ({"unreadable": 4}, J.UNKNOWN, "4 paper(s) or folder(s)"),
])
def test_each_outcome_is_noted_as_what_it_was(tmp_path, monkeypatch, result, state, words):
    monkeypatch.setattr(R, "auto_reconnect", lambda root: result)
    cfg = _config(tmp_path)
    D._auto_reconnect(cfg.library_root, cfg)
    row = J.last_run(J.PUT_BACK, log_dir=cfg.log_dir)
    assert row["state"] == state and words in row["text"]


def test_a_failure_is_a_problem_with_the_reason(tmp_path, monkeypatch):
    def _boom(root):
        raise OSError("Resource deadlock avoided")
    monkeypatch.setattr(R, "auto_reconnect", _boom)
    cfg = _config(tmp_path)
    assert "error" in D._auto_reconnect(cfg.library_root, cfg)
    row = J.last_run(J.PUT_BACK, log_dir=cfg.log_dir)
    assert row["state"] == J.PROBLEM and "Resource deadlock avoided" in row["text"]


def _fail_n(tmp_path, monkeypatch, n, *, notifications=True):
    told = []
    monkeypatch.setattr(D, "notify", lambda title, msg, **k: told.append(msg))
    monkeypatch.setattr(R, "auto_reconnect", lambda root: 1 / 0)
    cfg = _config(tmp_path, notifications)
    for _ in range(n):
        D._auto_reconnect(cfg.library_root, cfg)
    return told


def test_one_failure_says_nothing_on_screen(tmp_path, monkeypatch):
    assert _fail_n(tmp_path, monkeypatch, 1) == []


def test_the_second_tells_him_and_the_third_does_not(tmp_path, monkeypatch):
    told = _fail_n(tmp_path, monkeypatch, 3)
    assert len(told) == 1 and "failed twice" in told[0] and "Home" in told[0]


def test_with_notifications_off_it_stays_quiet(tmp_path, monkeypatch):
    assert _fail_n(tmp_path, monkeypatch, 2, notifications=False) == []


def test_it_works_with_no_config_as_before(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "auto_reconnect", lambda root: {"orphans": 0})
    assert D._auto_reconnect(tmp_path) == {"orphans": 0}


# ---------------------------------------------- what the hourly plan reads

@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _shelf(lib, rel, body=b"%PDF-1.4 paper"):
    p = lib / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    return p


def _orphan_for(lib, body=b"%PDF-1.4 stranded"):
    """A record left behind by a rename, whose paper now has another name."""
    from processing.identity import compute_content_hash
    gone = _shelf(lib, "01 - Published papers/S/Old name.pdf", body)
    PaperIdentity(doi="10.1/x").save(gone)
    h = json.loads(sidecar_path(gone).read_text())["content_sha256"]
    gone.unlink()
    return h


def test_the_hourly_plan_never_reads_a_paper_not_filed_yet(lib, monkeypatch):
    _orphan_for(lib)
    _shelf(lib, "12 - To be sorted/03 - Working papers/new.pdf", b"%PDF other")
    read = []
    import processing.identity as I
    real = I.compute_content_hash
    monkeypatch.setattr(I, "compute_content_hash",
                        lambda p: read.append(Path(p).name) or real(p))
    R.plan_reconnect(lib, hourly=True)
    assert "new.pdf" not in read
    read.clear()
    R.plan_reconnect(lib)
    assert "new.pdf" in read, "the page's own plan still looks there"


def test_the_hourly_plan_leaves_the_trash_alone(lib):
    _orphan_for(lib)
    _shelf(lib, ".trash/old/x.pdf", b"%PDF-1.4 stranded")
    assert R.plan_reconnect(lib, hourly=True)["to_trash"] == []
    assert R.plan_reconnect(lib)["to_trash"] != []


def test_a_paper_that_cannot_be_read_stops_the_hour(lib, monkeypatch):
    """"One candidate only" is not known while one could not be read."""
    _orphan_for(lib)
    match = _shelf(lib, "01 - Published papers/S/New name.pdf", b"%PDF-1.4 stranded")
    _shelf(lib, "01 - Published papers/S/Unread.pdf", b"%PDF other")
    import processing.identity as I
    real = I.compute_content_hash
    monkeypatch.setattr(I, "compute_content_hash",
                        lambda p: "" if Path(p).name == "Unread.pdf" else real(p))
    res = R.auto_reconnect(lib)
    assert res["unreadable"] == 1 and res["reconnected"] == 0
    assert PaperIdentity.load(match).is_new(), "nothing was put back on a guess"


def test_with_everything_readable_it_puts_the_record_back(lib):
    _orphan_for(lib)
    match = _shelf(lib, "01 - Published papers/S/New name.pdf", b"%PDF-1.4 stranded")
    res = R.auto_reconnect(lib)
    assert res["reconnected"] == 1 and res["unreadable"] == 0
    assert PaperIdentity.load(match).doi == "10.1/x"


def test_a_folder_that_cannot_be_listed_counts_too(lib, monkeypatch):
    import os
    import processing.identity as I
    _orphan_for(lib)
    bad = lib / "01 - Published papers"
    real = os.scandir

    def _scan(path):
        if str(path) == str(bad):
            raise PermissionError("no")
        return real(path)

    monkeypatch.setattr(I.os, "scandir", _scan)
    assert str(bad) in R.plan_reconnect(lib, hourly=True)["unreadable"]


def test_the_real_hourly_job_leaves_unfiled_papers_alone(lib, monkeypatch):
    """The wire itself: an unfiled paper it cannot read must not stop it,
    because it never tries to read one."""
    import processing.identity as I
    _orphan_for(lib)
    match = _shelf(lib, "01 - Published papers/S/New name.pdf", b"%PDF-1.4 stranded")
    _shelf(lib, "12 - To be sorted/03 - Working papers/new.pdf", b"%PDF other")
    real = I.compute_content_hash

    def _hash(p):
        assert "12 - To be sorted" not in str(p), "read a paper not filed yet"
        return real(p)

    monkeypatch.setattr(I, "compute_content_hash", _hash)
    res = R.auto_reconnect(lib)
    assert res["reconnected"] == 1 and res["unreadable"] == 0
    assert PaperIdentity.load(match).doi == "10.1/x"
