"""The Monday sweep and "Run weekly now" never file, move or trash a paper by themselves.

Step-back audit, findings G4-1 and G4-2 (each verified 3 of 3):

  * with "Also file the safe ones" ticked, the sweep's first Monday would
    have downloaded the FIRST-order Zhou paper (Automatica 2022, a 96.4%
    Crossref match) and moved the owner's second-order preprint to the
    trash -- one author, over 95%, so it passed every gate there is;
  * it moves "old" working papers on misses that were replayed from saved
    answers rather than asked again;
  * "Run weekly now" cannot finish inside its 30 minutes at the default
    limit, and a run stopped part-way had already rewritten records while
    the page said "Nothing in your library was changed".

The refusal lives in the weekly job (``AUTO_FILE_BLOCKED``), not only in
the cockpit, because an old Monday service file may still pass
``--auto-apply-safe``. The cockpit shows the tick and the button switched
off, with the reason, rather than hiding them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import maintenance.weekly_report as W
from tests.ui.test_cockpit_renders_content import cockpit, home, lib  # noqa: F401 -- fixtures


# ------------------------------------------------------ the job refuses

def _never(*a, **k):
    raise AssertionError("the sweep tried to file papers by itself")


def test_an_old_service_asking_to_file_is_refused_and_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "auto_apply_safe_transitions", _never)
    out = W.run_maintenance(tmp_path, skip={"publications", "aging", "duplicates"},
                            auto_apply_safe=True)
    assert out["auto_applied"]["skipped"] == W.AUTO_FILE_BLOCKED
    assert out["auto_applied"]["upgraded"] == out["auto_applied"]["aged_moved"] == []
    assert any(line.startswith("nothing was filed automatically — filing by itself "
                               "is switched off") for line in out["problems"]), out["problems"]


def test_the_lock_is_the_only_thing_in_the_way(tmp_path, monkeypatch):
    """Pin the other direction: with the reason removed the old path runs,
    so the test above passes because of the lock, not because the path is
    dead."""
    called = []
    monkeypatch.setattr(W, "AUTO_FILE_BLOCKED", None)
    monkeypatch.setattr(W, "auto_apply_safe_transitions",
                        lambda results, root, **k: called.append(root) or {
                            "upgraded": [], "aged_moved": [],
                            "skipped_borderline": [], "errors": []})
    W.run_maintenance(tmp_path, skip={"publications", "aging", "duplicates"},
                      auto_apply_safe=True)
    assert called == [tmp_path]


def test_a_report_only_run_is_not_told_it_was_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "auto_apply_safe_transitions", _never)
    out = W.run_maintenance(tmp_path, skip={"publications", "aging", "duplicates"},
                            auto_apply_safe=False)
    assert "skipped" not in out["auto_applied"]
    assert not any("switched off" in line for line in out["problems"])


def test_the_reason_names_what_would_have_happened():
    assert "Zhou" in W.AUTO_FILE_BLOCKED and "switched off" in W.AUTO_FILE_BLOCKED


# ------------------------------------------- the page shows it switched off

def _calls(cockpit, name, key=None, label=None):
    out = []
    for n, args, kwargs in cockpit.st.calls:
        if n != name:
            continue
        if key is not None and kwargs.get("key") != key:
            continue
        if label is not None and not (args and args[0] == label):
            continue
        out.append(kwargs)
    return out


def _weekly(cockpit, monkeypatch, status):
    import ui.cockpit_actions as acts
    started = []
    monkeypatch.setattr(cockpit, "_weekly_status_cached", type("F", (), {
        "__call__": lambda self: status, "clear": lambda self: None})())
    monkeypatch.setattr(acts, "start_weekly",
                        lambda **k: started.append(k) or (True, "on"))
    monkeypatch.setattr(acts, "stop_weekly", lambda: (True, "off"))
    monkeypatch.setattr(cockpit.st, "rerun", lambda: None, raising=False)
    return started


@pytest.mark.parametrize("on", [False, True])
def test_the_tick_is_drawn_switched_off_with_the_reason(cockpit, monkeypatch, on):
    from tests.ui.test_cockpit_renders_content import rendered_text
    _weekly(cockpit, monkeypatch, {"on": on})
    cockpit._render_weekly_service()
    ticks = _calls(cockpit, "checkbox", key="weekly_auto")
    assert ticks and all(k.get("disabled") is True for k in ticks), ticks
    assert "Zhou" in rendered_text(cockpit.st)


def test_turning_the_sweep_on_never_asks_it_to_file(cockpit, monkeypatch):
    """Even if the tick somehow reads as ticked."""
    started = _weekly(cockpit, monkeypatch, {"on": False})
    cockpit.st.values.update({"weekly_auto": True, "weekly_on": True})
    cockpit._render_weekly_service()
    assert started == [{"auto_apply_safe": False}]


def test_a_sweep_installed_to_file_is_told_and_can_be_made_report_only(cockpit, monkeypatch):
    from tests.ui.test_cockpit_renders_content import rendered_text
    started = _weekly(cockpit, monkeypatch, {"on": True, "auto_apply": True})
    cockpit._render_weekly_service()
    assert "It no longer does — it only reports" in rendered_text(cockpit.st)
    assert started == []
    cockpit.st.calls.clear()
    cockpit.st.values["weekly_resave"] = True
    cockpit._render_weekly_service()
    assert started == [{"auto_apply_safe": False}]


def test_a_report_only_sweep_is_not_warned(cockpit, monkeypatch):
    from tests.ui.test_cockpit_renders_content import rendered_text
    _weekly(cockpit, monkeypatch, {"on": True, "auto_apply": False})
    cockpit._render_weekly_service()
    assert "It no longer does" not in rendered_text(cockpit.st)
    assert not _calls(cockpit, "button", key="weekly_resave")


def test_run_weekly_now_is_switched_off_and_says_why(cockpit):
    from tests.ui.test_cockpit_renders_content import rendered_text
    cockpit.render_maintenance()
    buttons = _calls(cockpit, "button", key="run_weekly_now")
    assert buttons and buttons[0].get("disabled") is True
    assert "Switched off for now" in rendered_text(cockpit.st)
    assert not _calls(cockpit, "checkbox", label="Also file the safe ones for me (this changes files)")


def test_the_page_no_longer_promises_a_tick_that_files():
    src = (Path(__file__).resolve().parents[2] / "src" / "ui" / "cockpit.py"
           ).read_text(encoding="utf-8")
    assert "and the full weekly run *if* you tick" not in src
    assert "Nothing in your library was changed.  The usual cause" not in src


# ------------------------------------- the button register agrees with it

@pytest.mark.parametrize("src,site", [
    ('st.button("Run", key="k")', True),
    ('st.button("Run", key="k", disabled=True)', False),
    ('st.button("Run", key="k", disabled=False)', True),
    ('st.button("Run", key="k", disabled=busy)', True),   # may be pressable
    ('cols[2].form_submit_button("Go", disabled=True)', False),
])
def test_a_button_switched_off_in_the_source_is_not_a_write_site(src, site):
    """The register of library-writing buttons is read from the code. A
    button drawn with a literal disabled=True can never be pressed, so a
    test claiming to press it would be pressing nothing."""
    import ast
    from tests.ui.library_write_sites import _button_call
    call = ast.parse(src, mode="eval").body
    assert (_button_call(call) is not None) is site


# ------------------------------------------- and never opens a browser tab

def test_the_job_opens_no_browser_when_the_cockpit_or_a_test_runs_it(tmp_path, monkeypatch):
    """Owner, 2026-11-05: "Stop opening tabs on my chrome". The job ended by
    `open`ing its HTML report; run from a test, that was a tab per run."""
    import subprocess
    opened = []
    real = subprocess.run
    monkeypatch.setattr(subprocess, "run", lambda cmd, *a, **k: (
        opened.append(cmd) if cmd and cmd[0] == "open" else real(cmd, *a, **k)))
    monkeypatch.setattr(W, "run_maintenance", lambda *a, **k: {
        "timestamp": "t", "problems": [], "auto_applied": {}, "publications": {}})
    monkeypatch.setattr(W, "generate_html_report", lambda *a, **k: "<html></html>", raising=False)
    monkeypatch.setattr(W, "REPORT_DIR", tmp_path, raising=False)
    for argv in (["--no-open"], []):   # the second relies on MATHPDF_NO_OPEN
        monkeypatch.setattr("sys.argv", ["weekly_report", "--library", str(tmp_path),
                                         "--no-notify", *argv])
        try:
            W.main()
        except SystemExit:
            pass
    assert opened == []
    # Pin: a run started by hand in a terminal still opens its report (the
    # open is patched above, so no tab appears) -- the guard is what stops
    # it, not a job that never gets that far.
    monkeypatch.delenv("MATHPDF_NO_OPEN")
    monkeypatch.setattr("sys.argv", ["weekly_report", "--library", str(tmp_path),
                                     "--no-notify"])
    W.main()
    assert len(opened) == 1 and opened[0][0] == "open"


def test_every_test_run_has_the_browser_switched_off():
    import os
    assert os.environ.get("MATHPDF_NO_OPEN") == "1"


def test_the_cockpit_and_the_monday_service_ask_for_no_tab():
    root = Path(__file__).resolve().parents[2]
    assert '"--no-open",' in (root / "src/ui/cockpit_actions.py").read_text()
    assert "<string>--no-open</string>" in (
        root / "deploy/launchd/ch.ethz.dpossamai.mathpdf.weekly.plist").read_text()


def test_no_test_can_open_anything_on_his_screen():
    import subprocess
    import webbrowser
    assert webbrowser.open("https://example.org") is False
    r = subprocess.run(["open", "https://example.org"], capture_output=True)
    assert r.returncode == 0 and r.args == ["/usr/bin/true"]
    r = subprocess.run(["osascript", "-e", 'display dialog "x"'], capture_output=True)
    assert r.returncode == 0 and r.args == ["/usr/bin/true"]
    # A grandchild that looks the command up by name finds the stand-in.
    import shutil
    for cmd in ("open", "osascript"):
        assert "quiet-bin" in (shutil.which(cmd) or ""), cmd
    r = subprocess.run(["sh", "-c", "command -v osascript"], capture_output=True, text=True)
    assert "quiet-bin" in r.stdout
    assert subprocess.run(["echo", "x"], capture_output=True, text=True).stdout == "x\n"
