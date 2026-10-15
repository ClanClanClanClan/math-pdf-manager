"""Cockpit buttons that RENAME papers, pressed on a synthetic library.

Each test sets the page up as the owner would find it, presses the
button through the Streamlit double, checks the disk (the PDF AND its
saved record), reads what the page told him, and then presses ↶ Undo on
the Activity page and checks the library is exactly as it was.
``render_spelling`` (0 of 85 statements before these tests) calls
``apply_renames(dry_run=False)`` from two buttons.
"""
from __future__ import annotations

from pathlib import Path

from maintenance.typos import broken_characters
from processing.identity import PaperIdentity, iter_pdfs
from processing.library_normalize import AUTHOR, TITLE
from tests.ui.press_harness import (ck, presses, put, snapshot,  # noqa: F401
                                    transactions, undo_from_activity)


def _with_record(lib, rel: str, doi: str) -> Path:
    pdf = put(lib, rel)
    ident = PaperIdentity.load(pdf)
    ident.doi = doi
    ident.save(pdf)
    return pdf


def _proposal(old_rel: str, new_name: str, kind: str) -> dict:
    old = Path(old_rel)
    return {"old": old_rel, "new": str(old.parent / new_name), "kind": kind,
            "old_name": old.name, "name": new_name}


def _only_new_tx(lib, before: list) -> dict:
    new = [t for t in transactions(lib) if t["id"] not in {b["id"] for b in before}]
    assert len(new) == 1, new
    return new[0]


def _pdf_names(lib) -> set[str]:
    return {p.relative_to(lib).as_posix() for p in iter_pdfs(lib)}


# --------------------------------------------------------------------------
# Maintenance -> Normalize existing filenames -> Apply this batch
# --------------------------------------------------------------------------

@presses("_render_normalize_section[libnorm_apply]")
def test_normalize_apply_renames_the_batch_and_undo_brings_it_back(ck):
    lib = ck.lib
    rel = "01 - Published papers/S/Smith, J.R. - On stopping.pdf"
    _with_record(lib, rel, "10.1000/stop")
    untouched = put(lib, "01 - Published papers/T/Tan, X. - Left alone.pdf")
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["libnorm_scan_res"] = {
        "proposals": [_proposal(rel, "Smith, J. R. - On stopping.pdf", AUTHOR)],
        "by_kind": {AUTHOR: 1, TITLE: 0, "both": 0}, "total": 1,
        "pending_words": []}
    ck.st.press("libnorm_apply")

    assert ck.run("_render_normalize_section", lib) == "rerun"

    new = lib / "01 - Published papers/S/Smith, J. R. - On stopping.pdf"
    assert new.exists() and not (lib / rel).exists()
    assert PaperIdentity.load(new).doi == "10.1000/stop", "the record stayed behind"
    assert untouched.exists()
    assert ck.flashes() == [("success", "1 file(s) renamed.  Undo it from the "
                                        "Activity page.")]
    assert ck.st.session_state["libnorm_scan_res"]["total"] == 0
    tx = _only_new_tx(lib, txs)

    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


def test_normalize_apply_with_no_bucket_ticked_cannot_be_pressed(ck):
    lib = ck.lib
    rel = "01 - Published papers/S/Smith, J.R. - On stopping.pdf"
    put(lib, rel)
    before = snapshot(lib)
    ck.st.session_state["libnorm_scan_res"] = {
        "proposals": [_proposal(rel, "Smith, J. R. - On stopping.pdf", AUTHOR)],
        "by_kind": {AUTHOR: 1, TITLE: 0, "both": 0}, "total": 1,
        "pending_words": []}
    ck.st.set(libnorm_inc_author=False)
    ck.st.press("libnorm_apply")

    ck.run("_render_normalize_section", lib)

    assert snapshot(lib) == before
    assert ck.st.unused_presses() == ["libnorm_apply"]


# --------------------------------------------------------------------------
# Maintenance -> title changes grouped -> "Apply these N"
# --------------------------------------------------------------------------

@presses("_render_title_review._apply[tr_apply_{}]")
def test_title_review_apply_renames_its_group_only(ck):
    lib = ck.lib
    first = "03 - Working papers/S/Smith, J. - a note on games.pdf"
    other = "03 - Working papers/T/Tan, X. - Brownian Motion and stuff.pdf"
    _with_record(lib, first, "10.1000/games")
    put(lib, other)
    before, txs = snapshot(lib), transactions(lib)
    data = {"proposals": [
        _proposal(first, "Smith, J. - A note on games.pdf", TITLE),
        _proposal(other, "Tan, X. - Brownian motion and stuff.pdf", TITLE)]}
    ck.st.press("tr_apply_firstword")

    assert ck.run("_render_title_review", lib, data) == "rerun"

    renamed = lib / "03 - Working papers/S/Smith, J. - A note on games.pdf"
    assert renamed.exists(), _pdf_names(lib)
    assert PaperIdentity.load(renamed).doi == "10.1000/games"
    assert (lib / other).exists(), "a file outside the pressed group was renamed"
    assert [p["old"] for p in data["proposals"]] == [other]
    tx = _only_new_tx(lib, txs)

    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


# --------------------------------------------------------------------------
# Spelling -> "Fix it" (broken character) and "Rename to ..." (typo)
# --------------------------------------------------------------------------

def _spelling(broken=(), suspects=()):
    return {"scanned": 3, "oracle": "test-oracle", "learned": 0,
            "left_alone": 0, "broken": list(broken), "suspects": list(suspects)}


@presses("render_spelling[sp_brk_{}]")
def test_fix_it_removes_a_ligature_and_undo_puts_it_back(ck):
    lib = ck.lib
    name = "Smith, J. - Eﬃcient markets.pdf"          # U+FB03 'ffi'
    rel = f"01 - Published papers/S/{name}"
    _with_record(lib, rel, "10.1000/eff")
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["spelling"] = _spelling(broken=[
        {"name": name, "rel": rel, "faults": broken_characters(name)}])
    ck.st.press(f"sp_brk_{rel}")

    assert ck.run("render_spelling") == "rerun"

    fixed = lib / "01 - Published papers/S/Smith, J. - Efficient markets.pdf"
    # The directory listing, not exists(): APFS case-folds U+FB03 to "ffi",
    # so the OLD name still "exists" -- it is the same file.
    assert _pdf_names(lib) == {fixed.relative_to(lib).as_posix()}
    assert PaperIdentity.load(fixed).doi == "10.1000/eff"
    assert ck.st.session_state["spelling"]["broken"] == []
    tx = _only_new_tx(lib, txs)

    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_spelling[sp_fix_{}]")
def test_rename_to_the_suggestion_keeps_the_case_and_can_be_undone(ck):
    lib = ck.lib
    name = "Smith, J. - Brwonian motion.pdf"
    rel = f"01 - Published papers/S/{name}"
    _with_record(lib, rel, "10.1000/bm")
    before, txs = snapshot(lib), transactions(lib)
    ck.st.session_state["spelling"] = _spelling(suspects=[{
        "name": name, "rel": rel, "suspects": [{
            "word": "Brwonian", "lower": "brwonian", "suggestion": "brownian",
            "distance": 1, "suggestion_freq": 40}]}])
    ck.st.press(f"sp_fix_{rel}::brwonian")

    assert ck.run("render_spelling") == "rerun"

    fixed = lib / "01 - Published papers/S/Smith, J. - Brownian motion.pdf"
    assert fixed.exists(), _pdf_names(lib)
    assert PaperIdentity.load(fixed).doi == "10.1000/bm"
    assert ck.st.session_state["spelling"]["suspects"] == []
    from processing.spelling_vocab import load_rulings
    assert load_rulings(lib)["typo"] == {"brwonian": "brownian"}, (
        "the ruling that keeps the word from coming back was not written")
    tx = _only_new_tx(lib, txs)

    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


def test_a_refused_spelling_fix_says_so_and_changes_nothing(ck):
    """The corrected name is already taken by another paper."""
    lib = ck.lib
    name = "Smith, J. - Brwonian motion.pdf"
    rel = f"01 - Published papers/S/{name}"
    put(lib, rel)
    put(lib, "01 - Published papers/S/Smith, J. - Brownian motion.pdf",
        b"%PDF-1.4\n% the other paper\n%%EOF\n")
    before = snapshot(lib)
    ck.st.session_state["spelling"] = _spelling(suspects=[{
        "name": name, "rel": rel, "suspects": [{
            "word": "Brwonian", "lower": "brwonian", "suggestion": "brownian",
            "distance": 1, "suggestion_freq": 40}]}])
    ck.st.press(f"sp_fix_{rel}::brwonian")

    assert ck.run("render_spelling") == "done"

    assert snapshot(lib) == before
    warned = [a[0] for n, a, _ in ck.st.calls if n == "warning"]
    assert any("Not renamed" in w for w in warned), warned


# --------------------------------------------------------------------------
# Search -> a paper -> "Rename or move this paper" -> Rename
# --------------------------------------------------------------------------

@presses("_render_paper_editor[edit_apply::{}]")
def test_the_paper_editor_renames_and_moves_one_paper(ck):
    from ui.search_page import build_index
    lib = ck.lib
    rel = "03 - Working papers/S/Smith, J. - Old title.pdf"
    _with_record(lib, rel, "10.1000/old")
    put(lib, "01 - Published papers/S/Smith, J. - Something else.pdf")
    before, txs = snapshot(lib), transactions(lib)
    ck.st.set(**{f"edit_name::{rel}": "Smith, J. - New title",
                 f"edit_folder::{rel}": "01 - Published papers/S"})
    ck.st.press(f"edit_apply::{rel}")

    assert ck.run("_render_paper_editor", lib, rel, build_index(lib)) == "rerun"

    new = lib / "01 - Published papers/S/Smith, J. - New title.pdf"
    assert new.exists() and not (lib / rel).exists(), _pdf_names(lib)
    assert PaperIdentity.load(new).doi == "10.1000/old"
    (kind, msg), = ck.flashes()
    assert kind == "success" and "Undo it from Activity" in msg, msg
    tx = _only_new_tx(lib, txs)

    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


def test_the_paper_editor_will_not_rename_onto_another_paper(ck):
    from ui.search_page import build_index
    lib = ck.lib
    rel = "01 - Published papers/S/Smith, J. - Old title.pdf"
    put(lib, rel)
    put(lib, "01 - Published papers/S/Smith, J. - Taken.pdf",
        b"%PDF-1.4\n% another paper\n%%EOF\n")
    before = snapshot(lib)
    ck.st.set(**{f"edit_name::{rel}": "Smith, J. - Taken"})
    ck.st.press(f"edit_apply::{rel}")

    ck.run("_render_paper_editor", lib, rel, build_index(lib))

    assert snapshot(lib) == before
    assert ck.st.unused_presses() == [f"edit_apply::{rel}"], (
        "the Rename button could be pressed onto an existing paper")
