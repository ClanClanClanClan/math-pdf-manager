"""Cockpit buttons that FILE papers, pressed on a synthetic library.

Sort Queue (one paper, and many at once), Upgrade Queue (one, many, and
"flag for manual") and the Pipeline Preview's "Apply now".  Filing COPIES
the paper into its folder and retires the original; undoing a copy
retires the filed copy to ``.trash/undone_copies/`` rather than deleting
it.  So after Undo the shelves must be exactly as they were, and every
file that left a shelf must be in the trash, not gone.
"""
from __future__ import annotations

import json
from pathlib import Path

from processing.identity import PaperIdentity, iter_pdfs
from tests.harness.synth_library import _write_minimal_pdf
from tests.ui.press_harness import (ck, presses, put, snapshot,  # noqa: F401
                                    transactions, undo_from_activity)


def _new_txs(lib, before):
    seen = {t["id"] for t in before}
    return [t for t in transactions(lib) if t["id"] not in seen]


_TRASH = (".trash/", ".mathpdf-sidecars/.trash/")


def _shelves(lib) -> dict:
    """The snapshot without the trash (papers AND the records that shadow
    them there): what the owner sees in Finder, and what is filed."""
    return {k: v for k, v in snapshot(lib).items() if not k.startswith(_TRASH)}


def _trashed(lib) -> set:
    return {k for k in snapshot(lib) if k.startswith(_TRASH)}


def _pdfs(lib, under: str) -> set:
    return {p.relative_to(lib).as_posix() for p in iter_pdfs(lib / under)}


def _inbox_paper(lib, name="paper001.pdf", *, title="A theorem on stochastic "
                 "differential equations", author="Smith, J.") -> Path:
    p = lib / "12 - To be sorted/01 - Published papers" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title=title, author=author)
    return p


def _assert_undo_restores_the_shelves(ck, tx_id, shelves_before, trash_before):
    undo_from_activity(ck, tx_id)
    assert _shelves(ck.lib) == shelves_before, "undo did not restore the shelves"
    gone = set(shelves_before) - set(_shelves(ck.lib))
    assert not gone
    # Nothing that was on a shelf during the run has been deleted: what
    # undo took off a shelf is in the trash.
    assert _trashed(ck.lib) >= trash_before


# --------------------------------------------------------------------------
# Sort Queue
# --------------------------------------------------------------------------

@presses("render_sort_queue[approve_{}]")
def test_approve_files_the_paper_under_the_name_he_saw(ck):
    lib = ck.lib
    pdf = _inbox_paper(lib)
    body = pdf.read_bytes()
    shelves, trash, txs = _shelves(lib), _trashed(lib), transactions(lib)
    # He edited the proposed name; the file must get HIS name, not the one
    # the metadata would have produced.
    name = "Smith, J. - A theorem on SDEs.pdf"
    ck.st.set(**{f"name_{pdf}": name})
    ck.st.press(f"approve_{pdf}")

    assert ck.run("render_sort_queue") == "rerun"

    filed = lib / "01 - Published papers/S" / name
    assert filed.read_bytes() == body
    assert not pdf.exists()
    assert (lib / ".trash/sorted_originals/01 - Published papers"
            / pdf.name).read_bytes() == body
    assert ck.st.session_state["activity_log"][0]["action"] == "sort.approve"
    tx, = _new_txs(lib, txs)
    _assert_undo_restores_the_shelves(ck, tx["id"], shelves, trash)
    assert pdf.read_bytes() == body


@presses("_render_batch_sort[bulk_sort_apply]")
def test_file_these_papers_files_exactly_the_previewed_ones(ck):
    from processing.bulk_sort import bulk_sort
    lib = ck.lib
    a = _inbox_paper(lib, "paper001.pdf")
    b = _inbox_paper(lib, "paper012.pdf", title="Optimal control of stochastic "
                     "processes", author="Pham, H.")
    preview = bulk_sort(lib, limit=25, dry_run=True)
    assert sum(1 for r in preview["results"] if r.get("ok")) == 2, preview
    preview["_previewed_size"] = "25"
    # A paper that arrives AFTER the preview must not be swept up.
    late = _inbox_paper(lib, "late.pdf", title="Late arrival on Markov chains",
                        author="Brown, A.")
    shelves, trash, txs = _shelves(lib), _trashed(lib), transactions(lib)
    ck.st.session_state["bulk_sort_preview_res"] = preview
    ck.st.set(bulk_sort_confirm=True)
    ck.st.press("bulk_sort_apply")

    assert ck.run("_render_batch_sort", lib, 3) == "rerun"

    assert not a.exists() and not b.exists()
    assert late.exists(), "a paper that was not previewed was filed"
    assert len(_pdfs(lib, "01 - Published papers")) == 2
    assert ck.flashes()[0][0] == "success", ck.flashes()
    tx, = _new_txs(lib, txs)
    _assert_undo_restores_the_shelves(ck, tx["id"], shelves, trash)


def test_file_these_papers_needs_the_tick(ck):
    from processing.bulk_sort import bulk_sort
    lib = ck.lib
    _inbox_paper(lib)
    preview = bulk_sort(lib, limit=25, dry_run=True)
    preview["_previewed_size"] = "25"
    before = snapshot(lib)
    ck.st.session_state["bulk_sort_preview_res"] = preview
    ck.st.press("bulk_sort_apply")

    ck.run("_render_batch_sort", lib, 1)

    assert snapshot(lib) == before
    assert ck.st.unused_presses() == ["bulk_sort_apply"]


# --------------------------------------------------------------------------
# Upgrade Queue
# --------------------------------------------------------------------------

def _preprint_and_report(lib, home: Path, *, confidence=0.95) -> tuple:
    rel = "02 - Unpublished papers/S/Smith, J. - Optimal stopping games.pdf"
    pre = lib / rel
    pre.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(pre, title="Optimal stopping games", author="Smith, J.")
    ident = PaperIdentity.load(pre)
    ident.arxiv_id = "2401.00001"
    ident.save(pre)
    entry = {"file": str(pre), "filename": pre.name,
             "parsed_title": "Optimal stopping games",
             "parsed_authors": ["Smith, J."],
             "match": {"doi": "10.1000/games", "journal": "Ann. Probab.",
                       "year": 2025, "confidence": confidence,
                       "matched_title": "Optimal stopping games"}}
    reports = home / ".mathpdf" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "checks_2026-10-15.json").write_text(
        json.dumps({"published": [entry]}), encoding="utf-8")
    return pre, entry


def _fake_publisher(monkeypatch, calls: list):
    """The network is the one thing replaced: the 'download' is a real PDF
    written where the downloader would have written it."""
    import processing.upgrade_to_published as up

    def download(doi, out_dir):
        calls.append(doi)
        out = Path(out_dir) / "published.pdf"
        _write_minimal_pdf(out, title="Optimal stopping games (journal)",
                           author="Smith, J.", keywords="x" * 400)
        return out

    monkeypatch.setattr(up, "try_download_by_doi", download)


@presses("render_upgrade_queue[upg_approve_{}]")
def test_download_and_upgrade_replaces_the_preprint(ck, monkeypatch):
    lib = ck.lib
    pre, entry = _preprint_and_report(lib, ck.home)
    pre_body = pre.read_bytes()
    calls: list = []
    _fake_publisher(monkeypatch, calls)
    shelves, txs = _shelves(lib), transactions(lib)
    ck.st.press(f"upg_approve_{entry['file']}")

    assert ck.run("render_upgrade_queue") == "rerun"

    assert calls == ["10.1000/games"]
    published = _pdfs(lib, "01 - Published papers")
    assert published == {"01 - Published papers/S/Smith, J. - Optimal stopping "
                         "games.pdf"}, published
    assert not pre.exists()
    assert (lib / ".trash/upgraded_preprints" / pre.name).read_bytes() == pre_body
    assert str(pre) in ck.st.session_state["upgrade_done"]
    tx, = _new_txs(lib, txs)
    _assert_undoing_an_upgrade_is_partial_and_says_so(ck, tx["id"], pre,
                                                      pre_body, shelves)


def _assert_undoing_an_upgrade_is_partial_and_says_so(ck, tx_id, pre,
                                                      pre_body, shelves):
    """Undo brings the preprint and its record back -- but NOT the removal
    of the published copy: the copy's source was the download, which is
    gone, and undoing a copy whose original is gone is refused (it could
    be the only copy).  Measured 2026-10-15; the page says so, as a
    partial undo, rather than claiming the upgrade was reversed."""
    lib = ck.lib
    undo_from_activity(ck, tx_id)
    assert pre.read_bytes() == pre_body
    assert PaperIdentity.load(pre).arxiv_id == "2401.00001"
    published = "01 - Published papers/S/Smith, J. - Optimal stopping games.pdf"
    assert set(_shelves(lib)) - set(shelves) == {
        published,
        f".mathpdf-sidecars/{published[:-4]}.meta.json"}
    (kind, msg), = ck.flashes()
    assert kind == "warning" and msg.startswith("Undone in part:"), msg
    row = next(t for t in transactions(lib) if t["id"] == tx_id)
    assert row["undone"] is False, "a partial undo was marked complete"


@presses("render_upgrade_queue[upg_flag_{}]")
def test_flag_for_manual_writes_a_note_in_04(ck):
    lib = ck.lib
    pre, entry = _preprint_and_report(lib, ck.home)
    shelves, trash, txs = _shelves(lib), _trashed(lib), transactions(lib)
    ck.st.press(f"upg_flag_{entry['file']}")

    assert ck.run("render_upgrade_queue") == "rerun"

    note = lib / "04 - Papers to be downloaded/Ann. Probab./Optimal stopping games.txt"
    body = note.read_bytes()
    assert b"DOI: 10.1000/games" in body
    assert pre.exists(), "flagging must not touch the preprint"
    assert str(pre) in ck.st.session_state["upgrade_skipped"]
    # Undo takes the note off the To Download list -- into the trash, not
    # gone -- and leaves everything else as it was.
    tx, = _new_txs(lib, txs)
    assert ck.st.session_state["activity_log"][0]["tx_id"] == tx["id"]
    _assert_undo_restores_the_shelves(ck, tx["id"], shelves, trash)
    assert not note.exists()
    assert (lib / ".trash/undone_creations" / note.name).read_bytes() == body
    assert _trashed(lib) - trash == {f".trash/undone_creations/{note.name}"}


def test_flag_for_manual_twice_writes_one_note_and_one_entry(ck):
    lib = ck.lib
    pre, entry = _preprint_and_report(lib, ck.home)
    ck.st.press(f"upg_flag_{entry['file']}")
    ck.run("render_upgrade_queue")
    txs, shelves = transactions(lib), _shelves(lib)
    ck.st.session_state.upgrade_skipped.clear()      # back in the queue
    ck.st.press(f"upg_flag_{entry['file']}")

    assert ck.run("render_upgrade_queue") == "rerun"

    assert _shelves(lib) == shelves, "a second note, or the first rewritten"
    assert _new_txs(lib, txs) == []
    assert ck.st.session_state["activity_log"][0]["tx_id"] == ""


def test_flag_for_manual_when_the_library_is_busy_changes_nothing(ck):
    from processing.locking import LibraryLock
    lib = ck.lib
    pre, entry = _preprint_and_report(lib, ck.home)
    shelves, txs = _shelves(lib), transactions(lib)
    other = LibraryLock(lib)
    assert other.acquire(blocking=False)
    try:
        ck.st.press(f"upg_flag_{entry['file']}")
        assert ck.run("render_upgrade_queue") == "rerun"
    finally:
        other.release()
    assert _shelves(lib) == shelves and _new_txs(lib, txs) == []
    assert str(pre) not in ck.st.session_state["upgrade_skipped"], (
        "the paper left the queue although no note was written")
    (kind, msg), = ck.flashes()
    assert kind == "error" and "Flag for manual" in msg, msg


@presses("_render_batch_upgrade[bulk_upg_apply]")
def test_upgrade_these_papers_after_a_preview(ck, monkeypatch):
    lib = ck.lib
    pre, entry = _preprint_and_report(lib, ck.home)
    pre_body = pre.read_bytes()
    calls: list = []
    _fake_publisher(monkeypatch, calls)
    shelves, txs = _shelves(lib), transactions(lib)

    # Run 1: Preview (changes nothing).  Run 2: tick, Upgrade.
    ck.st.press("bulk_upg_preview")
    ck.run("render_upgrade_queue")
    assert ck.st.session_state["bulk_upg_preview_res"]["results"]
    assert _shelves(lib) == shelves and calls == []
    ck.st.set(bulk_upg_confirm=True)
    ck.st.press("bulk_upg_apply")

    assert ck.run("render_upgrade_queue") == "rerun"

    assert calls == ["10.1000/games"]
    assert not pre.exists()
    assert len(_pdfs(lib, "01 - Published papers")) == 1
    (kind, msg), = ck.flashes()
    assert kind == "success" and msg.startswith("Upgraded 1 "), msg
    ck.st.session_state.pop("flash")
    tx, = _new_txs(lib, txs)
    _assert_undoing_an_upgrade_is_partial_and_says_so(ck, tx["id"], pre,
                                                      pre_body, shelves)


# --------------------------------------------------------------------------
# Pipeline Preview -> Apply now
# --------------------------------------------------------------------------

@presses("render_pipeline_preview[preview_apply_now]")
def test_apply_now_files_the_previewed_papers_into_their_topic(ck):
    lib = ck.lib
    (lib / "07a - BSDEs" / "01 - Published papers").mkdir(parents=True)
    p = lib / ("01 - Published papers/S/Smith, J. - Reflected BSDEs and "
               "backward stochastic equations.pdf")
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title="t", author="Smith, J.")
    shelves, trash, txs = _shelves(lib), _trashed(lib), transactions(lib)

    ck.st.press("▶ Run preview")
    ck.run("render_pipeline_preview")
    assert ck.st.session_state["preview_summary"]["proposed_moves"] == 1
    ck.st.set(preview_apply_confirm=True)
    ck.st.press("preview_apply_now")

    ck.run("render_pipeline_preview")

    dest = lib / "07a - BSDEs/01 - Published papers/S" / p.name
    assert dest.exists() and not p.exists()
    assert "07a" in PaperIdentity.load(dest).topic_codes
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert ck.flashes()[-1][0] == "success"
    # The paper is back where it was, and so is its ABSENCE of a record:
    # filing wrote one, and undo used to leave it behind, blank (measured
    # 2026-10-15). Now the filing logs making it, and undo retires it.
    assert _shelves(lib) == shelves
    assert not dest.exists()
    new_in_trash, = _trashed(lib) - trash
    assert new_in_trash.startswith(".mathpdf-sidecars/.trash/undone_records/")
