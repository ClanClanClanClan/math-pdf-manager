"""Home's per-item actions, pressed on a synthetic library.

Home draws one button per action of each item and dispatches on the
action id (``if not st.button(...): continue`` then ``if action_id ==
"accept_topic":`` ...), so each arm is its own write site.  Every item
here comes from the REAL collectors scanning files on disk -- a conflict
copy, a note in 04/, an old working paper, a record with a suggestion --
so the test also proves the item carries what its button needs.
"""
from __future__ import annotations

import re
from datetime import datetime

from processing.identity import PaperIdentity
from tests.harness.synth_library import _write_minimal_pdf
from tests.ui.press_harness import (ck, presses, put, snapshot,  # noqa: F401
                                    transactions, undo_from_activity)


def _press_on_home(ck, source: str, action: str) -> str:
    """Open ``source``'s pile and press ``action`` on its (only) item."""
    ck.st.session_state["attn_scan_now"] = True
    ck.st.session_state["attn_open_group"] = source
    ck.st.press(re.compile(rf"^attn_.*_{action}$"))
    return ck.run("render_attention")


def _new_txs(lib, before):
    seen = {t["id"] for t in before}
    return [t for t in transactions(lib) if t["id"] not in seen]


def _record(pdf, **fields):
    ident = PaperIdentity.load(pdf)
    for k, v in fields.items():
        setattr(ident, k, v)
    ident.save(pdf)


def _home_items(ck) -> dict:
    entry = ck.st.session_state["_attn_cache"][str(ck.lib)]
    return {it.key: it for it in entry["items"]}


@presses("render_attention[{btn_key}]<delete_conflict>")
def test_move_conflict_copy_to_trash(ck):
    lib = ck.lib
    put(lib, "01 - Published papers/S/Smith, J. - A paper.pdf")
    copy = put(lib, "01 - Published papers/S/Smith, J. - A paper "
                    "(conflicted copy 2026-01-02).pdf")
    before, txs = snapshot(lib), transactions(lib)

    assert _press_on_home(ck, "conflict_copy", "delete_conflict") == "rerun"

    assert not copy.exists()
    assert (lib / ".trash/conflict_copies" / copy.name).exists()
    assert not any(k.startswith("conflict::") for k in _home_items(ck)), (
        "the resolved row is still on Home")
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_attention[{btn_key}]<mark_flag_done>")
def test_mark_done_on_home_moves_the_note_to_the_trash(ck):
    lib = ck.lib
    flag = put(lib, "04 - Papers to be downloaded/Ann. Probab/Stopping.txt",
               b"DOI: 10.1000/stop\n")

    assert _press_on_home(ck, "upgrade_flag", "mark_flag_done") == "rerun"

    assert not flag.exists()
    assert (lib / ".trash/done_flags/Stopping.txt").read_bytes() == (
        b"DOI: 10.1000/stop\n")
    assert ck.st.session_state["activity_log"][0]["action"] == (
        "attention.mark_flag_done")


@presses("render_attention[{btn_key}]<transition_aged>")
def test_move_to_unpublished_moves_an_aged_working_paper(ck):
    lib = ck.lib
    old_year = datetime.now().year - 9
    pdf = put(lib, f"03 - Working papers/S/{old_year}/Smith, J. - Old idea.pdf")
    _record(pdf, doi="")
    before, txs = snapshot(lib), transactions(lib)

    assert _press_on_home(ck, "aging", "transition_aged") == "rerun"

    moved = lib / "02 - Unpublished papers/S/Smith, J. - Old idea.pdf"
    assert moved.exists() and not pdf.exists()
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_attention[{btn_key}]<accept_topic>")
def test_accept_moves_the_paper_into_its_suggested_topic(ck):
    lib = ck.lib
    (lib / "07a - BSDEs/01 - Published papers").mkdir(parents=True)
    pdf = put(lib, "01 - Published papers/S/Smith, J. - Reflected equations.pdf")
    _record(pdf, topic_suggestion="07a", topic_confidence=0.6)
    before, txs = snapshot(lib), transactions(lib)

    assert _press_on_home(ck, "topic_suggestion", "accept_topic") == "rerun"

    dest = lib / "07a - BSDEs/01 - Published papers/S" / pdf.name
    assert dest.exists() and not pdf.exists()
    ident = PaperIdentity.load(dest)
    assert ident.topic_codes == ["07a"] and ident.topic_suggestion == ""
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before


@presses("render_attention[{btn_key}]<reject_topic>")
def test_reject_clears_the_suggestion_and_undo_brings_it_back(ck):
    lib = ck.lib
    pdf = put(lib, "01 - Published papers/S/Smith, J. - Reflected equations.pdf")
    _record(pdf, topic_suggestion="07a", topic_confidence=0.6)
    before, txs = snapshot(lib), transactions(lib)

    assert _press_on_home(ck, "topic_suggestion", "reject_topic") == "rerun"

    assert pdf.exists()
    assert PaperIdentity.load(pdf).topic_suggestion == ""
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert snapshot(lib) == before
    assert PaperIdentity.load(pdf).topic_suggestion == "07a"


@presses("render_attention[{btn_key}]<reset_recheck>")
def test_look_again_puts_the_paper_back_in_the_queue(ck):
    lib = ck.lib
    pdf = put(lib, "02 - Unpublished papers/S/Smith, J. - Never published.pdf")
    _record(pdf, permanently_unpublished=True, recheck_count=3)

    assert _press_on_home(ck, "permanently_unpublished", "reset_recheck") == "rerun"

    ident = PaperIdentity.load(pdf)
    assert ident.permanently_unpublished is False and ident.recheck_count == 0
    assert ck.st.session_state["activity_log"][0]["action"] == (
        "attention.reset_recheck")


@presses("render_attention[{btn_key}]<watcher_retry>")
def test_retry_files_the_paper_the_filer_could_not(ck):
    lib = ck.lib
    inbox = ck.home / "inbox"
    src = inbox / "arrival.pdf"
    src.parent.mkdir(parents=True)
    _write_minimal_pdf(src, title="A theorem on stochastic differential "
                       "equations", author="Smith, J.")
    log = ck.home / ".mathpdf" / "watcher.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"2026-10-15 09:00:00,000 [ERROR] Failed to ingest {src}: "
                   f"library busy\n", encoding="utf-8")
    txs = transactions(lib)

    assert _press_on_home(ck, "watcher_failure", "watcher_retry") == "rerun"

    filed = list((lib / "03 - Working papers").rglob("*.pdf")) + list(
        (lib / "01 - Published papers").rglob("*.pdf"))
    assert len(filed) == 1, filed
    assert ck.st.session_state["activity_log"][0]["action"] == (
        "attention.watcher_retry")
    tx, = _new_txs(lib, txs)
    undo_from_activity(ck, tx["id"])
    assert not any((lib / "03 - Working papers").rglob("*.pdf"))
    assert not any((lib / "01 - Published papers").rglob("*.pdf"))
    assert src.exists(), "undo did not put the arrival back in the inbox"
