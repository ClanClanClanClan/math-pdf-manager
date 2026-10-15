"""Cockpit buttons that write papers' SAVED RECORDS, pressed for real.

Reconnecting stranded records (Conformance), the three backfills
(Settings, Pipeline Preview, Duplicates -> variants) and the two
publication checks (Maintenance).  A record holds a paper's DOI, arXiv
number and history; a button that writes one wrongly loses that quietly,
which is why each test reads the records back, not just the PDFs.

Two of these buttons only ADD information (a record for a paper that had
none, the cached first-page text). They did so outside the undo log until
2026-10-15; now Undo takes back exactly what they added -- a record made
from nothing goes to the record mirror's ``.trash/undone_records/``, a
field added to an existing record comes off it, byte for byte.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import fitz

from processing.identity import PaperIdentity, sidecar_path
from processing.sidecar_repair import find_orphans, plan_reconnect
from tests.ui.press_harness import (ck, presses, put, snapshot,  # noqa: F401
                                    transactions, undo_from_activity)


def _new_txs(lib, before):
    seen = {t["id"] for t in before}
    return [t for t in transactions(lib) if t["id"] not in seen]


def _record(pdf, **fields):
    ident = PaperIdentity.load(pdf)
    for k, v in fields.items():
        setattr(ident, k, v)
    ident.save(pdf)


def _pdf_with_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path


def _pdfs_and_bytes(lib) -> dict:
    return {k: v for k, v in snapshot(lib).items() if k.endswith(".pdf")}


_RETIRED = ".mathpdf-sidecars/.trash/undone_records/"


def _untrashed(lib) -> dict:
    """The snapshot less what an undo retired: a record undo took back
    is in the mirror's ``.trash/undone_records/``, never deleted."""
    return {k: v for k, v in snapshot(lib).items() if not k.startswith(_RETIRED)}


def _retired(lib, pdf) -> bytes:
    """The record undo took off ``pdf``, where it went."""
    return sidecar_path(lib / ".trash/undone_records" / pdf.name).read_bytes()


# --------------------------------------------------------------------------
# Conformance -> records that belong to no paper
# --------------------------------------------------------------------------

def _stranded(lib):
    """A paper renamed in Finder: its record keeps the OLD name."""
    old = put(lib, "01 - Published papers/S/Smith, J. - Old name.pdf")
    _record(old, doi="10.1000/strand")
    new = old.with_name("Smith, J. - New name.pdf")
    old.rename(new)
    return old, new


@presses("_render_orphan_repair[orphan_apply]")
def test_reconnect_puts_the_record_back_beside_its_paper(ck):
    lib = ck.lib
    old, new = _stranded(lib)
    assert len(find_orphans(lib)) == 1
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["orphan_plan"] = ck.module._orphan_plan_for_session(
        plan_reconnect(lib), lib)
    ck.st.set(orphan_confirm=True)
    ck.st.press("orphan_apply")

    assert ck.run("_render_orphan_repair", lib, 1) == "rerun"

    assert PaperIdentity.load(new).doi == "10.1000/strand"
    assert find_orphans(lib) == []
    assert not sidecar_path(old).exists()
    (kind, msg), = ck.flashes()
    assert kind == "success" and msg.startswith("Reconnected 1 of 1"), msg
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("_offer_records_to_trash[orphan_trash_apply]")
def test_records_join_their_papers_in_the_trash(ck):
    lib = ck.lib
    pre = put(lib, "02 - Unpublished papers/C/Cao, C. - Recursive equilibrium.pdf")
    _record(pre, arxiv_id="1801.00001")
    trash = lib / ".trash/upgraded_preprints" / pre.name
    trash.parent.mkdir(parents=True)
    shutil.move(str(pre), str(trash))          # the old, record-less retirement
    plan = plan_reconnect(lib)
    assert len(plan["to_trash"]) == 1, plan
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["orphan_plan"] = ck.module._orphan_plan_for_session(plan, lib)
    ck.st.set(orphan_trash_confirm=True)
    ck.st.press("orphan_trash_apply")

    assert ck.run("_render_orphan_repair", lib, 1) == "rerun"

    assert PaperIdentity.load(trash).arxiv_id == "1801.00001"
    assert find_orphans(lib) == []
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


def test_reconnect_needs_the_tick(ck):
    lib = ck.lib
    _stranded(lib)
    before = snapshot(lib)
    ck.st.session_state["orphan_plan"] = ck.module._orphan_plan_for_session(
        plan_reconnect(lib), lib)
    ck.st.press("orphan_apply")

    ck.run("_render_orphan_repair", lib, 1)

    assert snapshot(lib) == before
    assert ck.st.unused_presses() == ["orphan_apply"]


# --------------------------------------------------------------------------
# The backfills
# --------------------------------------------------------------------------

@presses("render_settings[bf_run]")
def test_fill_in_missing_details_adds_records_and_moves_nothing(ck):
    lib = ck.lib
    bare = put(lib, "01 - Published papers/S/Smith, J. - No record yet.pdf")
    kept = put(lib, "01 - Published papers/T/Tan, X. - Has one.pdf")
    _record(kept, doi="10.1000/kept")
    kept_record = sidecar_path(kept).read_bytes()
    pdfs, txs, before = _pdfs_and_bytes(lib), transactions(lib), snapshot(lib)
    assert PaperIdentity.load(bare).is_new()

    ck.st.press("bf_run")
    ck.run("render_settings")

    assert not PaperIdentity.load(bare).is_new(), "no record was written"
    assert sidecar_path(kept).read_bytes() == kept_record, (
        "an existing record was rewritten")
    assert _pdfs_and_bytes(lib) == pdfs
    entry = ck.st.session_state["activity_log"][0]
    assert entry["action"] == "settings.backfill"
    made = sidecar_path(bare).read_bytes()
    tx, = _new_txs(lib, txs)
    assert entry["tx_id"] == tx["id"]
    assert tx["operations_count"] == 1, "only the new record is the change"
    undo_from_activity(ck, tx["id"])
    assert PaperIdentity.load(bare).is_new(), "undo left the new record"
    assert sidecar_path(kept).read_bytes() == kept_record
    assert _untrashed(lib) == before
    assert _retired(lib, bare) == made


@presses("render_pipeline_preview[abstracts_bf_run]")
def test_cache_abstracts_now_stores_the_first_page_text(ck):
    lib = ck.lib
    pdf = _pdf_with_text(
        lib / "01 - Published papers/S/Smith, J. - Reflected BSDEs.pdf",
        "Abstract. We study reflected backward stochastic differential equations.")
    _record(pdf, doi="10.1000/rbsde")
    bare = _pdf_with_text(
        lib / "01 - Published papers/T/Tan, X. - No record yet.pdf",
        "Abstract. Optimal stopping of diffusions.")
    pdfs, txs, before = _pdfs_and_bytes(lib), transactions(lib), snapshot(lib)

    ck.st.press("▶ Run preview")             # the expander lives under a preview
    ck.run("render_pipeline_preview")
    ck.st.press("abstracts_bf_run")
    ck.run("render_pipeline_preview")

    ident = PaperIdentity.load(pdf)
    assert "reflected backward stochastic" in ident.classifier_text.lower()
    assert ident.doi == "10.1000/rbsde", "the backfill lost a field"
    assert _pdfs_and_bytes(lib) == pdfs
    bare_record = sidecar_path(bare).read_bytes()
    assert PaperIdentity.load(bare).classifier_text_tried
    entry = ck.st.session_state["activity_log"][0]
    assert entry["action"] == "pipeline.abstracts"
    tx, = _new_txs(lib, txs)
    assert entry["tx_id"] == tx["id"]
    undo_from_activity(ck, tx["id"])
    # The existing record back byte for byte; the one made from nothing
    # retired, not deleted.
    assert _untrashed(lib) == before
    assert _retired(lib, bare) == bare_record


@presses("_render_variant_section[var_scan]")
def test_scan_for_variants_mines_identifiers_reversibly(ck):
    lib = ck.lib
    pdf = put(lib, "02 - Unpublished papers/S/Smith, J. - Stopping.pdf")
    _record(pdf, classifier_text="Smith. Stopping. arXiv:2401.00001 "
                                 "doi:10.1000/stop.2024 Abstract ...")
    before, txs = snapshot(lib), transactions(lib)
    ck.st.press("var_scan")

    ck.run("_render_variant_section", lib)

    ident = PaperIdentity.load(pdf)
    assert ident.doi == "10.1000/stop.2024"
    assert ident.arxiv_id == "2401.00001"
    assert ck.st.session_state["variant_pairs"] == []
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before
    assert PaperIdentity.load(pdf).doi == ""


# --------------------------------------------------------------------------
# Maintenance -> the publication checks
# --------------------------------------------------------------------------

@presses("render_maintenance[▶ Run checks]")
def test_run_checks_records_crossrefs_answer_reversibly(ck, monkeypatch):
    """Crossref is the one thing replaced: it answers "not published" for
    the one preprint.  That advances the paper's recheck counter -- a
    record write -- which must be one undoable transaction."""
    from processing import publication_checker as pc
    lib = ck.lib
    pre = put(lib, "02 - Unpublished papers/S/Smith, J. - Optimal stopping games.pdf")
    _record(pre, arxiv_id="2401.00001", recheck_count=1)
    asked = []

    def check_title(self, title, lastnames):
        asked.append((title, tuple(lastnames)))
        self.last_lookup_failed = False
        return None

    monkeypatch.setattr(pc.CrossrefChecker, "check_title", check_title)
    before_pdfs, txs = _pdfs_and_bytes(lib), transactions(lib)
    before_record = sidecar_path(pre).read_bytes()
    ck.st.press("▶ Run checks")

    ck.run("render_maintenance")

    assert asked and asked[0][0] == "Optimal stopping games", asked
    assert PaperIdentity.load(pre).recheck_count == 2
    assert _pdfs_and_bytes(lib) == before_pdfs
    tx, = _new_txs(lib, txs)
    assert tx["description"].startswith("publication check")
    undo_from_activity(ck, tx["id"])
    assert sidecar_path(pre).read_bytes() == before_record


@presses("render_maintenance[run_weekly_now]")
def test_run_weekly_now_runs_the_real_job_on_this_library(ck, monkeypatch):
    """The real ``maintenance.weekly_report`` subprocess, pointed at THIS
    library, with the network made unreachable: a run Crossref cannot
    answer must change nothing in the library and still finish."""
    lib = ck.lib
    pre = put(lib, "02 - Unpublished papers/S/Smith, J. - Optimal stopping games.pdf")
    _record(pre, arxiv_id="2401.00001", recheck_count=1)
    before = snapshot(lib)
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.setenv(var, "http://127.0.0.1:9")
    for var in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(var, raising=False)
    assert os.environ["HOME"] == str(ck.home)
    ck.st.press("run_weekly_now")

    ck.run("render_maintenance")

    errors = [a[0] for n, a, _ in ck.st.calls if n == "error"]
    assert not errors, errors
    assert ck.st.session_state["activity_log"][0]["action"] == "maintenance.run_full"
    reports = list((ck.home / ".mathpdf").rglob("*.json"))
    assert reports, "the run wrote no report where the cockpit reads them"
    assert snapshot(lib) == before, "an unanswered check changed the library"
