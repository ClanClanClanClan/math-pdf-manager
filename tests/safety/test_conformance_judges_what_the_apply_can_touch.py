"""Conformance must judge exactly the files the Apply may touch, and say what it left out.

Cockpit audit findings 3 and 5, both approved.

3.  ``conformance.run`` kept a private skip list, ``("12 - To be
    sorted",)``, and never asked ``processing.library_scope``. So it judged
    2,130 files the owner has excluded or that are still staging: measured
    2026-09-05, 728 of the 795 files in its red "Never examined -- the code
    is wrong" bucket were in the archival collections he asked to be left
    alone (JEHPS, the academy folders). The page also called .djvu/.epub
    files "OUT OF SCOPE" -- a different population under the same words --
    and showed "Invariant violations 0" above a red list of library-wide
    findings it never counted anywhere.

5.  Because the Apply (library_normalize.propose_renames) DOES ask
    library_scope, "Mechanical, not yet applied" had a floor of 11 files in
    "04 - Papers to be downloaded" that no Apply could ever clear -- and its
    help text told the owner a floor meant "the apply path is broken".
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

from maintenance.conformance import MECHANICAL, NOT_EXAMINED, run  # noqa: E402
from processing.library_scope import ARCHIVAL_COLLECTIONS  # noqa: E402

COCKPIT = Path(__file__).resolve().parents[2] / "src" / "ui" / "cockpit.py"


@pytest.fixture()
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _add(lib, folder, name):
    p = lib / folder / name
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title="t", author="Smith, J.")
    return p


MECH = "Shiryaev, A.N. - Stochastic disorder problems.pdf"        # unspaced initials
NOSEP = "Comptes rendus hebdomadaires, tome 12.pdf"                # no " - "


def _populate(lib):
    _add(lib, "01 - Published papers/S", MECH)                      # in scope
    _add(lib, "04 - Papers to be downloaded/Risk", MECH)            # staging
    _add(lib, "12 - To be sorted", "2401.07160v3.pdf")              # staging
    _add(lib, ARCHIVAL_COLLECTIONS[2], NOSEP)                       # archival
    _add(lib, ARCHIVAL_COLLECTIONS[0], NOSEP)                       # JEHPS


def test_only_in_scope_files_are_judged(lib):
    _populate(lib)
    rep = run(lib)
    assert rep.scanned == 1, f"judged {rep.scanned} files; only 1 is in scope"
    judged = {f.path for f in rep.findings if not f.path.startswith(("<", "("))}
    assert all(p.startswith("01 - Published papers") for p in judged), judged


def test_the_mechanical_floor_is_gone(lib):
    """The staging copy of a mechanical fix used to sit in the bucket for
    ever, because the Apply refuses staging."""
    _populate(lib)
    assert run(lib).counts[MECHANICAL] == 1


def test_archival_files_no_longer_fill_the_red_bucket(lib):
    _populate(lib)
    assert run(lib).counts[NOT_EXAMINED] == 0


def test_what_was_left_out_is_counted_by_reason(lib):
    _populate(lib)
    g = run(lib).globals_
    skips = g["skipped_by_reason"]
    assert g["skipped_total"] == 4 == sum(skips.values())
    assert any("archival" in why for why in skips)
    assert any("04 - Papers to be downloaded" in why for why in skips)
    assert any("12 - To be sorted" in why for why in skips)
    assert g["inbox_skipped"] == 1, "the older key keeps meaning the 12/ share"


def test_judged_population_equals_the_applys_population(lib):
    """The structural claim behind both fixes: one scope, two readers."""
    from processing.library_normalize import propose_renames
    _populate(lib)
    rep = run(lib)
    proposals, _ = propose_renames(lib)
    applyable = {p["old"] for p in proposals}
    flagged = {f.path for f in rep.findings if f.bucket == MECHANICAL}
    assert flagged <= applyable, (
        f"Conformance flags work the Apply can never do: {flagged - applyable}")


def test_an_explicit_skip_list_still_works(lib):
    _populate(lib)
    rep = run(lib, skip_dirs=("12 - To be sorted",))
    assert rep.scanned == 4, "explicit override: only 12/ skipped"


def test_library_wide_findings_are_broken_down_by_reason(lib):
    _add(lib, "01 - Published papers/S", "Smith, J. - A note on control.pdf")
    stray = lib / ".mathpdf-sidecars" / "01 - Published papers" / "S" / "ghost.meta.json"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("{}")
    g = run(lib).globals_
    assert g["library_wide_by_reason"].get("orphaned-records") == 1
    assert g["library_wide_findings"] == sum(g["library_wide_by_reason"].values())


# ------------------------------------------------------------- the page

def _conformance_strings() -> str:
    tree = ast.parse(COCKPIT.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "render_conformance")
    return " ".join(n.value for n in ast.walk(fn)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str))


def test_the_page_no_longer_calls_non_pdfs_out_of_scope_or_claims_no_writes():
    text = _conformance_strings()
    assert "OUT OF SCOPE" not in text
    assert "nothing is written to your library" not in text
    assert "the apply path is broken" not in text


def test_the_page_shows_library_wide_findings_beside_a_zero(monkeypatch, tmp_path):
    """"Invariant violations 0" above a red list of ten, and no line saying
    what the ten were."""
    from tests.ui.test_cockpit_smoke import _StreamlitModule
    from maintenance.conformance import ConformanceReport
    fake = _StreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as C
    shown = []
    for kind in ("warning", "success", "error", "info", "caption"):
        monkeypatch.setattr(fake, kind, lambda m="", *a, _k=kind, **k: shown.append((_k, str(m))))
    rep = ConformanceReport()
    rep.scanned = 100
    import maintenance.conformance as MC
    rep.counts = {MC.CANONICAL: 100, MC.OWNER_QUEUE: 0, MC.MECHANICAL: 0,
                  MC.TYPO: 0, MC.NOT_EXAMINED: 0, MC.VIOLATION: 0}
    rep.reasons, rep.findings = {}, []
    rep.globals_ = {"library_wide_findings": 10,
                    "library_wide_by_reason": {"two-sidecar-records": 9,
                                               "orphaned-records": 1},
                    "skipped_by_reason": {"archival collection the owner asked to leave alone (JEHPS)": 219}}
    fake.session_state["conformance_report"] = rep
    monkeypatch.setattr(C, "_page_header", lambda *a, **k: None)
    C.render_conformance()
    warnings = [m for k, m in shown if k == "warning"]
    assert any("Plus 10 library-wide" in m and "two sidecar records" in m for m in warnings), warnings
    assert any("0 file(s)" in m and "10 library-wide" in m for m in warnings), (
        "the banner must not call library-wide findings 'files'")
    assert any("219" in m and "JEHPS" in m for k, m in shown if k == "caption")
