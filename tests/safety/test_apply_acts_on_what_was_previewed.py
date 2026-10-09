"""An apply must act on exactly what the preview showed -- never on the live controls.

Cockpit audit findings 8 and 9, both approved.

8.  Sort Queue's batch filer and Upgrade Queue's batch upgrader re-ran with
    the "How many" dropdown's CURRENT value. Preview 25, switch to "All",
    and a primary button still reading "File these 25 papers" filed the
    whole inbox -- about 1,900 papers of which 25 had been shown. The
    previewed 25 are a prefix of the "All" run, so the divergence is a
    strict escalation, not just a mismatch.

9.  Pipeline Preview's "Apply now" re-scanned the WHOLE library with no
    scope, sample or list: the audit measured 348 confident moves in the
    preview and an apply population of 1,243.

The fix has two halves, both needed. The back-ends take an explicit list
("only these files"), intersected with their own fresh safety re-scan --
so a paper no longer eligible is still left alone. And the cockpit
records what each preview was run WITH; if a control changes afterwards
it withdraws the apply button and asks for a fresh preview.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

COCKPIT = Path(__file__).resolve().parents[2] / "src" / "ui" / "cockpit.py"


def _pdf(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return p


# --------------------------------------------------------- bulk_sort(paths=)

def test_bulk_sort_files_only_the_listed_papers(tmp_path, monkeypatch):
    import processing.bulk_sort as bs
    inbox = tmp_path / "12 - To be sorted" / "01 - Published papers"
    a, b, c = (_pdf(inbox / f"{n}.pdf") for n in "abc")
    seen = []
    monkeypatch.setattr(bs, "sort_one",
                        lambda pdf, status, **k: seen.append(Path(pdf).name)
                        or {"ok": True, "file": str(pdf)})
    bs.bulk_sort(tmp_path, dry_run=True, paths={str(b)})
    assert seen == ["b.pdf"], "only the previewed paper may be processed"


def test_a_listed_paper_that_has_gone_is_simply_skipped(tmp_path, monkeypatch):
    """Intersection with the fresh scan, not trust in the list."""
    import processing.bulk_sort as bs
    inbox = tmp_path / "12 - To be sorted" / "01 - Published papers"
    a = _pdf(inbox / "a.pdf")
    seen = []
    monkeypatch.setattr(bs, "sort_one",
                        lambda pdf, status, **k: seen.append(Path(pdf).name)
                        or {"ok": True, "file": str(pdf)})
    bs.bulk_sort(tmp_path, dry_run=True, paths={str(inbox / "vanished.pdf"), str(a)})
    assert seen == ["a.pdf"]


def test_a_listed_paper_with_an_accent_still_matches_after_macos_decomposes_it(tmp_path, monkeypatch):
    import unicodedata
    import processing.bulk_sort as bs
    inbox = tmp_path / "12 - To be sorted" / "01 - Published papers"
    p = _pdf(inbox / "Lévy, P. - Processus.pdf")
    seen = []
    monkeypatch.setattr(bs, "sort_one",
                        lambda pdf, status, **k: seen.append(pdf) or {"ok": True, "file": str(pdf)})
    bs.bulk_sort(tmp_path, dry_run=True, paths={unicodedata.normalize("NFD", str(p))})
    assert len(seen) == 1


# ------------------------------------------------- process_report(only_files=)

def test_process_report_upgrades_only_the_listed_papers(tmp_path, monkeypatch):
    import processing.upgrade_to_published as up
    entries = [{"file": str(tmp_path / f"{n}.pdf"), "filename": f"{n}.pdf",
                "match": {"doi": f"10.1/{n}", "confidence": 0.99}} for n in "abc"]
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"published": entries}))
    seen = []
    monkeypatch.setattr(up, "upgrade_paper",
                        lambda entry, *a, **k: seen.append(entry["filename"])
                        or {"action": "DRY RUN", "filename": entry["filename"]})
    up.process_report(report, library_root=tmp_path, dry_run=True,
                      only_files={entries[1]["file"]})
    assert seen == ["b.pdf"]


# ------------------------------------------- apply_topic_proposals(only=)

def test_apply_topic_proposals_moves_only_the_listed_papers(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
    from synth_library import _write_minimal_pdf
    from processing.identity import enable_sidecar_mirror
    from processing.pipeline_preview import apply_topic_proposals
    for d in ["01 - Published papers", "07a - BSDEs/01 - Published papers"]:
        (tmp_path / d).mkdir(parents=True)
    enable_sidecar_mirror(tmp_path)
    papers = []
    for who in ("Smith, J.", "Jones, K."):
        p = (tmp_path / "01 - Published papers" / who[0]
             / f"{who} - Reflected BSDEs and backward stochastic equations.pdf")
        p.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(p, title="t", author=who)
        papers.append(p)
    everything = apply_topic_proposals(tmp_path, dry_run=True)
    assert everything["selected"] == 2, "control: both are confident moves"
    one = apply_topic_proposals(tmp_path, dry_run=True, only={str(papers[1])})
    assert one["selected"] == 1
    assert Path(one["would_apply"][0]["path"]).name == papers[1].name


# ------------------------------------------------- the cockpit's apply calls

def _fname(node):
    return getattr(node, "id", None) or getattr(node, "attr", None)


def _calls(name: str) -> list:
    """Calls to ``name`` -- directly, or through the library lock as
    ``_locked_call(lib, action, name, ...)``, whose keywords are the call's
    own. (Since finding 10 every writing call goes through the lock, and a
    finder that only saw direct calls checked nothing.)"""
    tree = ast.parse(COCKPIT.read_text(encoding="utf-8"))
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        if _fname(n.func) == name:
            out.append(n)
        elif (_fname(n.func) == "_locked_call" and len(n.args) >= 3
              and _fname(n.args[2]) == name):
            out.append(n)
    return out


def _kw(call) -> dict:
    return {k.arg: k.value for k in call.keywords}


def _is_false(node) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def test_the_batch_filer_applies_the_previewed_list_not_a_count():
    applies = [c for c in _calls("bulk_sort") if _is_false(_kw(c).get("dry_run"))]
    assert applies, "no applying bulk_sort call found"
    for c in applies:
        assert "paths" in _kw(c), "the apply must name the previewed papers"
        assert "limit" not in _kw(c), "a count re-reads the live dropdown"


def test_the_batch_upgrader_applies_the_previewed_list_not_a_count():
    applies = [c for c in _calls("process_report") if _is_false(_kw(c).get("dry_run"))]
    assert applies
    for c in applies:
        assert "only_files" in _kw(c)
        assert "max_papers" not in _kw(c)


def test_pipeline_apply_and_its_dry_run_use_the_previews_scope_and_list():
    calls = _calls("apply_topic_proposals")
    assert len(calls) >= 2, "expected the dry-run and the apply"
    for c in calls:
        assert "only" in _kw(c) and "scope" in _kw(c), ast.unparse(c)


# ------------------------------------------- the stale-preview guard, live

def test_changing_how_many_after_the_preview_withdraws_the_apply(monkeypatch, tmp_path):
    from tests.ui.test_cockpit_smoke import _StreamlitModule
    import tests.ui.test_cockpit_smoke as smoke
    fake = _StreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as C

    shown, offered = [], []
    monkeypatch.setattr(fake, "warning", lambda m="", *a, **k: shown.append(str(m)))
    orig = smoke._NullCM.__getattr__

    def _cm(self, name):
        if name == "selectbox":
            return lambda label, opts, *a, **k: "All"      # he switched to All
        if name == "button":
            return lambda *a, **k: False
        return orig(self, name)

    monkeypatch.setattr(smoke._NullCM, "__getattr__", _cm)
    monkeypatch.setattr(fake, "checkbox",
                        lambda label, *a, **k: offered.append(str(label)) or False)
    fake.session_state["sort_skipped"] = set()
    fake.session_state["bulk_sort_preview_res"] = {
        "_previewed_size": "25",
        "results": [{"ok": True, "source": str(tmp_path / "a.pdf"),
                     "filename": "A, B. - T.pdf", "subfolder": "01"}] * 25}
    C._render_batch_sort(tmp_path, 1900)
    assert any("How many" in m and "25" in m and "All" in m for m in shown), shown
    assert not any("read the list" in o for o in offered), (
        "the confirm-and-apply controls must not be offered on a stale preview")


def test_preview_staleness_semantics():
    from ui.cockpit import _preview_is_stale
    assert _preview_is_stale("25", "All")
    assert not _preview_is_stale("25", "25")
    assert not _preview_is_stale(None, "All"), (
        "an old snapshot without recorded settings is not 'stale' -- the "
        "apply is restricted to its listed papers regardless")
