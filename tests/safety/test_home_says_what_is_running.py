"""Home says what is waiting and whether everything is running.

Step-back audit D8-4, G1-2 and G1-3 (verified 3 of 3). Failures reached only
log files; four of Home's checks caught their own failure and returned
nothing, so a failed check read as a clean one; and the sidebar said
"Automatic filing: ON" over a filer that has never filed a real paper, with
2,529 papers waiting and no word of them beside it.

Every line here is OK, a problem, or "cannot tell" with the reason.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from maintenance import job_runs as J
from maintenance import status as S
from maintenance.status import StatusLine
from tests.ui.test_cockpit_renders_content import cockpit, home, lib, rendered_text  # noqa: F401
import ui.attention_queue as Q
import ui.cockpit_actions as A


def _paper(root: Path, rel="03 - Working papers/a.pdf") -> Path:
    p = root / "12 - To be sorted" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF")
    return p


# ---------------------------------------------------------- papers waiting

def test_waiting_counts_the_pile_and_this_weeks_arrivals(tmp_path):
    _paper(tmp_path, "03 - Working papers/a.pdf")
    _paper(tmp_path, "01 - Published papers/b.pdf")
    assert S.waiting(tmp_path) == {"count": 2, "this_week": 2, "unread": 0}
    later = time.time() + 8 * 86400
    assert S.waiting(tmp_path, now=later) == {"count": 2, "this_week": 0, "unread": 0}


def test_no_folder_is_unknown_not_zero(tmp_path):
    line = S._waiting_line(tmp_path, None)
    assert line.state == J.UNKNOWN and "not found" in line.text


def test_an_empty_pile_is_ok(tmp_path):
    (tmp_path / "12 - To be sorted").mkdir()
    assert S._waiting_line(tmp_path, None).state == J.OK


def test_a_pile_is_a_note_not_a_fault(tmp_path):
    _paper(tmp_path)
    line = S._waiting_line(tmp_path, None)
    assert line.state == S.NOTE and line.text.startswith('1 in "12 - To be sorted"')


def test_a_folder_it_cannot_list_means_the_count_is_not_the_whole_answer(tmp_path, monkeypatch):
    import processing.identity as I
    _paper(tmp_path)
    bad = tmp_path / "12 - To be sorted" / "05 - Books"
    bad.mkdir()
    real = os.scandir

    def _scan(path):
        if str(path) == str(bad):
            raise PermissionError("no")
        return real(path)

    monkeypatch.setattr(I.os, "scandir", _scan)
    line = S._waiting_line(tmp_path, None)
    assert line.state == J.UNKNOWN and "1 could not be looked at" in line.text


def test_a_paper_it_cannot_stat_counts_as_not_looked_at(tmp_path, monkeypatch):
    p = _paper(tmp_path)
    real = Path.stat

    def _stat(self, **k):
        if self == p:
            raise OSError("gone")
        return real(self, **k)

    monkeypatch.setattr(Path, "stat", _stat)
    assert S.waiting(tmp_path)["unread"] == 1


# ------------------------------------------------------------------ the filer

@pytest.mark.parametrize("watcher,running,now,state,words", [
    ({"running": False}, "", "a", J.PROBLEM, "not running"),
    ({"running": True, "filing": False, "problem": "folder gone"}, "a", "a", J.PROBLEM, "folder gone"),
    ({"running": True, "filing": False}, "a", "a", J.PROBLEM, "not filing"),
    ({"running": True, "filing": None, "problem": "no report for 9 min"}, "a", "a", J.UNKNOWN, "9 min"),
    ({"running": True, "filing": None}, "a", "a", J.UNKNOWN, "no report"),
    ({"running": True, "filing": True}, "a", "b", S.NOTE, "restarts itself"),
    ({"running": True, "filing": True}, "a", "a", J.OK, "current code"),
    ({"running": True, "filing": True}, "", "a", J.OK, "current code"),
    ({"running": True, "filing": True}, "a", "", J.OK, "current code"),
])
def test_the_filer_line(watcher, running, now, state, words):
    line = S._filer_line(watcher, running, now)
    assert line.state == state and words in line.text


def test_ok_still_says_what_it_does_not_do():
    """ "ON" over a pile it never touches was the finding."""
    assert '"12 - To be sorted"' in S._filer_line({"running": True, "filing": True}, "a", "a").text


# ------------------------------------------------------------ the hourly job

def _noted(logs, state, text, hours_ago):
    J.record_run(J.PUT_BACK, state, text, log_dir=logs)
    rows = J.runs_path(logs).read_text().splitlines()
    row = json.loads(rows[-1])
    row["time"] = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    J.runs_path(logs).write_text(json.dumps(row) + "\n")


def test_no_run_noted_is_unknown_not_ok(tmp_path):
    line = S._put_back_line(tmp_path, None)
    assert line.state == J.UNKNOWN and "no run noted" in line.text


@pytest.mark.parametrize("state", [J.OK, J.PROBLEM, J.UNKNOWN])
def test_a_recent_run_says_what_it_said(tmp_path, state):
    _noted(tmp_path, state, "2 put back", 1)
    line = S._put_back_line(tmp_path, None)
    assert line.state == state and "2 put back" in line.text and "1 h ago" in line.text


def test_a_run_long_ago_means_it_may_have_stopped(tmp_path):
    """An OK from yesterday is not an OK today."""
    _noted(tmp_path, J.OK, "0 put back", 4)
    line = S._put_back_line(tmp_path, None)
    assert line.state == J.UNKNOWN and "may have stopped" in line.text


def test_an_unreadable_note_is_unknown(tmp_path):
    J.runs_path(tmp_path).write_text(json.dumps({"job": J.PUT_BACK, "time": "yesterday"}) + "\n")
    assert S._put_back_line(tmp_path, None).state == J.UNKNOWN


@pytest.mark.parametrize("seconds,words", [(30, "1 min ago"), (600, "10 min ago"),
                                           (7200, "2 h ago"), (3 * 86400, "3 days ago")])
def test_ages_read_naturally(seconds, words):
    assert S._ago(seconds) == words


def test_the_lines_come_in_order(tmp_path):
    sweep = StatusLine("Monday sweep", S.NOTE, "off")
    got = S.gather(tmp_path, watcher={}, running_code="", code_now="", sweep=sweep, log_dir=tmp_path)
    assert [l.name for l in got] == ["Papers waiting", "Filer", "Putting back saved details",
                                     "Monday sweep"]


# ---------------------------------------------------------------- on the page

def _page(cockpit, monkeypatch, *, watcher=None, weekly=None):
    monkeypatch.setattr(cockpit, "_watcher_status_cached",
                        lambda: watcher or {"running": True, "filing": True})
    monkeypatch.setattr(cockpit, "_weekly_status_cached", lambda: weekly or {"on": False})


def test_home_opens_with_the_strip(cockpit, lib, monkeypatch):
    _paper(lib)
    _page(cockpit, monkeypatch)
    cockpit._render_status_strip(lib)
    text = rendered_text(cockpit.st)
    assert '📌 **Papers waiting:** 1 in "12 - To be sorted"' in text
    assert "✅ **Filer:**" in text
    assert "❓ **Putting back saved details:**" in text
    assert "📌 **Monday sweep:** off" in text


def test_the_real_home_page_draws_it_first(cockpit, lib, monkeypatch):
    _paper(lib)
    _page(cockpit, monkeypatch)
    cockpit.render_attention()
    text = rendered_text(cockpit.st)
    assert text.index("**Papers waiting:**") < text.index("Show dismissed items")


def test_a_broken_strip_says_so_and_leaves_home_standing(cockpit, lib, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("cannot read the settings")
    monkeypatch.setattr(S, "gather", _boom)
    cockpit._render_status_strip(lib)
    assert "could not be read: cannot read the settings" in rendered_text(cockpit.st)


@pytest.mark.parametrize("weekly,state", [
    ({"on": False}, S.NOTE),
    ({"on": True, "last_run": "2026-11-02T09:00", "age_days": 3}, J.OK),
    ({"on": None}, J.UNKNOWN),
    ({"on": True, "last_error": "Traceback"}, J.PROBLEM),
    ({"on": True, "last_run": "2026-11-02", "age_days": 3, "problems": ["x"]}, J.PROBLEM),
    ({"on": True, "last_run": "2026-09-02", "age_days": 60}, J.UNKNOWN),
])
def test_the_sweeps_line_keeps_its_three_values(cockpit, monkeypatch, weekly, state):
    _page(cockpit, monkeypatch, weekly=weekly)
    line = cockpit._sweep_status_line()
    assert line.state == state and "🗓" not in line.text and "Monday sweep:" not in line.text


def test_the_sidebar_names_the_pile_beside_on(cockpit, lib, monkeypatch):
    """ "Automatic filing: ON" stood alone over 2,529 papers it never touches."""
    _paper(lib)
    _page(cockpit, monkeypatch)
    cockpit._waiting_cached.clear()
    cockpit.render_sidebar()
    text = rendered_text(cockpit.st)
    assert "Automatic filing: ON" in text
    assert "1 papers wait in “12 - To be sorted”; it does not file those yet." in text


def test_an_empty_pile_is_not_mentioned_there(cockpit, lib, monkeypatch):
    (lib / "12 - To be sorted").mkdir()
    _page(cockpit, monkeypatch)
    cockpit._waiting_cached.clear()
    cockpit.render_sidebar()
    assert "papers wait in" not in rendered_text(cockpit.st)


# -------------------------------- a check that fails says so, it is not empty

@pytest.mark.parametrize("collector,where,name", [
    (Q.collect_aging_candidates, "maintenance.weekly_report", "check_aging"),
    (Q.collect_borderline_matches, "processing.publication_state", "list_borderline_matches"),
    (Q.collect_permanently_unpublished, "processing.publication_state", "list_permanently_unpublished"),
    (Q.collect_topic_suggestions, "processing.publication_topic_router", "list_topic_suggestions"),
])
def test_each_of_the_four_shows_as_could_not_run(tmp_path, monkeypatch, collector, where, name):
    """THE FINDING: these caught their own failure, so the "could not run"
    row could never appear for them and Home stayed green."""
    import importlib

    def _boom(*a, **k):
        raise OSError("a file Dropbox has not brought down")

    monkeypatch.setattr(importlib.import_module(where), name, _boom)
    items = Q.gather_attention_items(tmp_path, collectors=[("the check", collector)],
                                     dismissals_path=tmp_path / "d.json")
    assert [i.source for i in items] == ["collector_error"]
    assert "a file Dropbox has not brought down" in items[0].detail


def test_a_watcher_log_that_cannot_be_read_says_so_too(tmp_path):
    unreadable = tmp_path / "watcher.log"
    unreadable.mkdir()
    items = Q.gather_attention_items(
        tmp_path, collectors=[("log", lambda _root: Q.collect_watcher_failures(unreadable))],
        dismissals_path=tmp_path / "d.json")
    assert [i.source for i in items] == ["collector_error"]


# ---------------------------------------------------- restarting from the page

class _P:
    def __init__(self, rc, err=""):
        self.returncode, self.stderr, self.stdout = rc, err, ""


@pytest.fixture
def filer(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "Library/LaunchAgents").mkdir(parents=True)
    (tmp_path / f"Library/LaunchAgents/{A.WATCHER_LABEL}.plist").write_text("x")
    slept = []
    monkeypatch.setattr(A.time, "sleep", slept.append)
    return slept


def _answers(monkeypatch, *procs):
    left = list(procs)
    asked = []

    def _run(*a, **k):
        asked.append(a)
        return left.pop(0) if len(left) > 1 else left[0]

    monkeypatch.setattr(A, "_launchctl", _run)
    return asked


IO = "Bootstrap failed: 5: Input/output error"


def test_right_after_a_stop_it_tries_again(filer, monkeypatch):
    """launchd needs a moment after a bootout; moving the filer hit this."""
    asked = _answers(monkeypatch, _P(5, IO), _P(0))
    assert A.start_watcher() == (True, "watcher started")
    assert len(asked) == 2 and filer == [1]


def test_it_gives_up_after_its_tries_and_says_why(filer, monkeypatch):
    asked = _answers(monkeypatch, _P(5, IO))
    ok, msg = A.start_watcher()
    assert not ok and "Input/output" in msg
    assert len(asked) == A.BOOTSTRAP_TRIES and len(filer) == A.BOOTSTRAP_TRIES - 1


def test_any_other_failure_is_not_retried(filer, monkeypatch):
    asked = _answers(monkeypatch, _P(1, "Load failed: bad plist"))
    ok, msg = A.start_watcher()
    assert not ok and "bad plist" in msg and len(asked) == 1 and filer == []


def test_already_loaded_is_fine(filer, monkeypatch):
    _answers(monkeypatch, _P(5, "service already loaded"))
    assert A.start_watcher() == (True, "already running")
