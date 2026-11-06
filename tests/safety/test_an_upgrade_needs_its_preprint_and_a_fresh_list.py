"""An upgrade needs the preprint it replaces, and a list fresh enough to act on.

Step-back audit, findings D9-3 and G4-1 (verified 3 of 3). The Upgrade
Queue worked from a publication check made in April (about 211 days old
on the day of the audit): papers it names have moved, been renamed or been
upgraded since, and in 278 of its 1,672 entries an upgrade would have
filed a second copy, most under an outdated name. ``upgrade_paper`` never
looked for the preprint before downloading: a missing one gave
"DOWNLOADED + FILED (preprint already gone)" with success=True.

Now ``upgrade_paper`` refuses, before any download, when the preprint is
not where the list says; and on a list older than a week the queue's
upgrade buttons -- one at a time and the batch -- are drawn switched off,
with the reason.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

import processing.upgrade_to_published as up
from tests.ui.test_cockpit_renders_content import cockpit, home, lib  # noqa: F401 -- fixtures


def _entry(path: Path) -> dict:
    return {"file": str(path), "filename": path.name, "parsed_title": "Optimal stopping",
            "parsed_authors": ["Smith"], "published": True,
            "match": {"doi": "10.1007/s00440-020-01000-0", "confidence": 0.99,
                      "author_count": 1, "journal": "PTRF", "year": 2020,
                      "matched_title": "Optimal stopping"}}


def _no_download(*a, **k):
    raise AssertionError("downloaded for a preprint that is not there")


# --------------------------------------------------------------- the rule

@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("where", ["gone", "a folder", "empty path"])
def test_no_preprint_no_download(tmp_path, monkeypatch, dry_run, where):
    monkeypatch.setattr(up, "try_download_by_doi", _no_download)
    target = {"gone": tmp_path / "02 - Unpublished papers" / "Smith, J. - Gone.pdf",
              "a folder": tmp_path,
              "empty path": Path("")}[where]
    entry = _entry(target)
    if where == "empty path":
        entry["file"] = ""
    out = up.upgrade_paper(entry, tmp_path, tmp_path / "dl", dry_run=dry_run)
    assert out["success"] is False
    assert out["action"].startswith("SKIP: the preprint is no longer at")


def test_a_preprint_that_is_there_still_goes_on_to_download(tmp_path, monkeypatch):
    """Pin: the refusal is about the missing file, not every upgrade."""
    pre = tmp_path / "02 - Unpublished papers" / "S" / "Smith, J. - Optimal stopping.pdf"
    pre.parent.mkdir(parents=True)
    pre.write_bytes(b"%PDF-1.4 preprint")
    asked = []
    monkeypatch.setattr(up, "try_download_by_doi",
                        lambda doi, d: asked.append(doi) or None)
    monkeypatch.setattr(up, "flag_for_manual_download", lambda *a, **k: tmp_path / "flag")
    up.upgrade_paper(_entry(pre), tmp_path, tmp_path / "dl")
    assert asked == ["10.1007/s00440-020-01000-0"]


def test_a_missing_preprint_without_a_doi_still_says_no_doi(tmp_path):
    """The DOI is asked first, as before: nothing else to do without one."""
    e = _entry(tmp_path / "gone.pdf")
    e["match"] = {}
    assert up.upgrade_paper(e, tmp_path, tmp_path / "dl")["action"] == "SKIP: no DOI"


def test_a_batch_counts_it_as_skipped_not_upgraded(tmp_path, monkeypatch):
    monkeypatch.setattr(up, "try_download_by_doi", _no_download)
    out = up.upgrade_entries([_entry(tmp_path / "gone.pdf")], tmp_path, dry_run=False)
    assert out["downloaded"] == 0 and out["skipped"] == 1


# ----------------------------------------------------------------- the page

def _queue(cockpit, tmp_path, monkeypatch, *, days, preprint_there=True):
    pre = tmp_path / "Maths" / "02 - Unpublished papers" / "S" / "Smith, J. - Optimal stopping.pdf"
    if preprint_there:
        pre.parent.mkdir(parents=True, exist_ok=True)
        pre.write_bytes(b"%PDF-1.4 preprint")
    rep = tmp_path / "report.json"
    rep.write_text(json.dumps({"published": [_entry(pre)]}))
    t = time.time() - days * 86400
    os.utime(rep, (t, t))
    monkeypatch.setattr(cockpit, "_find_publication_reports", lambda: [rep])
    cockpit.st.session_state["upgrade_report_path"] = None
    cockpit.st.values["bulk_upg_confirm"] = True       # past the confirm tick
    cockpit.st.session_state["bulk_upg_preview_res"] = {
        "results": [{"file": str(pre), "doi": "10.1/x"}],
        # The double answers a selectbox with its first option, "5".
        "_previewed": {"n": 5, "min_conf": 0.85}}
    cockpit.st.calls.clear()
    cockpit.render_upgrade_queue()


def _buttons(cockpit, prefix):
    return [k for n, a, k in cockpit.st.calls
            if n == "button" and str(k.get("key", "")).startswith(prefix)]


def test_an_old_list_switches_every_upgrade_button_off(cockpit, tmp_path, monkeypatch):
    from tests.ui.test_cockpit_renders_content import rendered_text
    _queue(cockpit, tmp_path, monkeypatch, days=211)
    for key in ("upg_approve_", "bulk_upg_preview", "bulk_upg_apply"):
        got = _buttons(cockpit, key)
        assert got and all(k.get("disabled") for k in got), (key, got)
    text = rendered_text(cockpit.st)
    assert "211 days old" in text and "upgrading from it is switched off" in text


def test_a_fresh_list_leaves_them_on(cockpit, tmp_path, monkeypatch):
    _queue(cockpit, tmp_path, monkeypatch, days=2)
    for key in ("upg_approve_", "bulk_upg_preview", "bulk_upg_apply"):
        got = _buttons(cockpit, key)
        assert got and not any(k.get("disabled") for k in got), (key, got)


def test_on_a_fresh_list_a_moved_preprint_switches_its_own_button_off(cockpit, tmp_path, monkeypatch):
    _queue(cockpit, tmp_path, monkeypatch, days=2, preprint_there=False)
    (approve,) = _buttons(cockpit, "upg_approve_")
    assert approve.get("disabled") is True
    assert "not where this list says" in approve.get("help", "")
