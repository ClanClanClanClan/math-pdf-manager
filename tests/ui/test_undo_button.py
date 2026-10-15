"""The Activity page's ↶ Undo, pressed on a synthetic library.

Before these tests ``_undo_transaction`` had never been executed by the
suite (0 of 25 statements), and putting back the exact bug commit
323cdc1 fixed -- the confirmation counting REFUSED operations as undone,
so a fully refused undo said "Undid 8514 ops" -- left every test green.
Undo is the button every other one in this app leans on ("reversible
from Activity"), so it is pressed here the way the owner presses it:
tick "Reverse all N change(s)", press ↶ Undo, read what the page says.
"""
from __future__ import annotations

import json

import pytest

from processing.identity import PaperIdentity, sidecar_path
from processing.undo_log import UndoLog, logged_rename
from tests.ui.press_harness import (ck, presses, put, snapshot,  # noqa: F401
                                    transactions, undo_from_activity)

UNDO = "render_activity[undo_{}_{}]"


def _renamed_with_record(lib, n: int = 1):
    """``n`` papers renamed by the app in ONE transaction, each with a
    saved record. Returns (tx id, [(old, new)])."""
    log = UndoLog(log_dir=lib / ".operation_log")
    tx = log.begin_transaction("normalize existing filenames: test")
    moves = []
    for i in range(n):
        old = put(lib, f"01 - Published papers/S/Smith, J.R. - Paper {i}.pdf")
        ident = PaperIdentity.load(old)
        ident.doi = f"10.1000/test.{i}"
        ident.save(old)
        new = old.with_name(f"Smith, J. R. - Paper {i}.pdf")
        logged_rename(old, new, undo_log=log)
        moves.append((old, new))
    log.commit()
    return tx, moves


@presses(UNDO)
def test_undo_puts_the_paper_and_its_record_back(ck):
    lib = ck.lib
    log = UndoLog(log_dir=lib / ".operation_log")
    old = put(lib, "01 - Published papers/S/Smith, J.R. - A paper.pdf")
    ident = PaperIdentity.load(old)
    ident.doi = "10.1000/xyz"
    ident.save(old)
    before = snapshot(lib)
    tx = log.begin_transaction("normalize existing filenames: 1 file(s)")
    new = old.with_name("Smith, J. R. - A paper.pdf")
    logged_rename(old, new, undo_log=log)
    log.commit()
    assert snapshot(lib) != before

    assert undo_from_activity(ck, tx) == "rerun"

    assert snapshot(lib) == before, "undo did not give the library back"
    assert old.exists() and not new.exists()
    assert PaperIdentity.load(old).doi == "10.1000/xyz"
    tx_row = next(t for t in transactions(lib) if t["id"] == tx)
    n = tx_row["operations_count"]     # the PDF, its record, the record's path
    assert n == 3
    assert ck.flashes() == [("success", f"Undone: all {n} change(s) reversed.")]
    assert tx_row["undone"] is True


@presses(UNDO)
def test_a_fully_refused_undo_says_nothing_was_undone(ck):
    """THE regression of 323cdc1: refusals were counted as successes.

    Both renamed files have since gone (moved by hand, say): there is
    nothing to put back.  The page must say NOTHING was undone, as an
    error, and must not record an undo in the activity feed.
    """
    lib = ck.lib
    tx, moves = _renamed_with_record(lib, 2)
    for _old, new in moves:
        sidecar_path(new).unlink()
        new.unlink()
    before = snapshot(lib)

    undo_from_activity(ck, tx)

    flashes = ck.flashes()
    assert [k for k, _ in flashes] == ["error"], flashes
    assert flashes[0][1].startswith("Nothing was undone."), flashes
    assert not any("Undone" in m for _, m in flashes), (
        "a refused undo was reported as done")
    assert snapshot(lib) == before
    assert not any(e["action"] == "undo"
                   for e in ck.st.session_state["activity_log"]), (
        "a refused undo was written to the activity feed as an undo")
    row = next(t for t in transactions(lib) if t["id"] == tx)
    assert row["undone"] is False, "a refused transaction was marked undone"


@presses(UNDO)
def test_a_partly_refused_undo_counts_what_came_back(ck):
    """One paper comes back; the other's place is now taken by a
    DIFFERENT file, which undo must refuse to overwrite."""
    lib = ck.lib
    tx, moves = _renamed_with_record(lib, 2)
    (old0, _new0), (old1, _new1) = moves
    squatter = b"%PDF-1.4\n% somebody else's file\n%%EOF\n"
    old1.write_bytes(squatter)

    undo_from_activity(ck, tx)

    (kind, msg), = ck.flashes()
    assert kind == "warning", msg
    # Three operations per paper (the PDF, its record, the record's path).
    # Only paper 1's PDF is refused.
    n = next(t for t in transactions(lib) if t["id"] == tx)["operations_count"]
    assert n == 6
    assert msg.startswith(f"Undone in part: {n - 1} of {n} change(s) reversed, "
                          "1 left alone."), msg
    assert old0.exists()
    assert old1.read_bytes() == squatter, "undo overwrote a different file"
    row = next(t for t in transactions(lib) if t["id"] == tx)
    assert row["undone"] is False, "a partly refused undo was marked done"
    full = json.loads((lib / ".operation_log" / f"{tx}.json").read_text())
    assert full["partial_undo"]["reversed"] == n - 1


@presses(UNDO)
def test_a_partly_undone_entry_pressed_again_finishes(ck):
    """The owner's retry, end to end (measured stuck 2026-10-15): the first
    press brings one paper back and refuses the other, whose old name is
    taken; he moves the stranger away and presses Undo again. The second
    press must attempt only what is left, and the entry must end UNDONE."""
    from tests.ui.streamlit_double import said
    lib = ck.lib
    tx, moves = _renamed_with_record(lib, 2)
    (old0, _new0), (old1, _new1) = moves
    stranger = old1.parent.parent / "elsewhere.pdf"
    old1.write_bytes(b"%PDF-1.4\n% somebody else's file\n%%EOF\n")
    n = next(t for t in transactions(lib) if t["id"] == tx)["operations_count"]

    undo_from_activity(ck, tx)
    assert ck.flashes()[0][0] == "warning"
    ck.st.calls.clear()
    ck.run("render_activity")
    page = said(ck.st)
    assert f"PARTLY UNDONE ({n - 1} reversed, 1 not)" in page, (
        "the Activity row did not say the entry was partly undone")
    assert "Reverse the 1 change(s) not yet reversed" in page
    assert f"Reverse all {n} change(s)" not in page

    old1.rename(stranger)                  # he clears the way
    ck.st.session_state.pop("flash", None)  # the first message was shown
    undo_from_activity(ck, tx)

    assert ck.flashes() == [(
        "success", f"Undone: the remaining 1 change(s) reversed. With the "
                   f"{n - 1} that came back on an earlier try, all {n} are back.")]
    row = next(t for t in transactions(lib) if t["id"] == tx)
    assert row["undone"] is True and "partial_undo" not in row
    assert old0.exists() and old1.exists() and stranger.exists()
    assert PaperIdentity.load(old1).doi == "10.1000/test.1"


def test_undo_cannot_be_pressed_before_the_box_is_ticked(ck):
    """The button is disabled until "Reverse all N change(s)" is ticked;
    a press without the tick changes nothing (finding 11)."""
    lib = ck.lib
    tx, moves = _renamed_with_record(lib, 1)
    before = snapshot(lib)
    shown = list(reversed(transactions(lib)))
    i = next(n for n, t in enumerate(shown) if t["id"] == tx)
    ck.st.press(f"undo_{i}_{tx}")

    ck.run("render_activity")

    assert snapshot(lib) == before
    assert ck.flashes() == []
    assert not ck.ran(UNDO)
    assert ck.st.unused_presses() == [f"undo_{i}_{tx}"]


def test_a_test_that_claims_a_button_but_never_presses_it_fails(ck):
    """The ``@presses`` check itself: a claim is only honoured when a line
    of the button's branch that changes the library actually ran."""
    import pytest

    @presses(UNDO)
    def sets_up_but_never_presses(ck):
        _renamed_with_record(ck.lib, 1)
        ck.run("render_activity")          # the page, without the press

    with pytest.raises(AssertionError, match="claims to press"):
        sets_up_but_never_presses(ck=ck)
    assert not ck.ran(UNDO)


def test_the_snapshot_sees_a_change_to_a_record_alone(ck):
    """Undo checks compare snapshots; a snapshot blind to the records
    would pass an undo that brought the PDF back and lost its DOI."""
    from tests.ui.press_harness import snapshot as snap
    pdf = put(ck.lib, "01 - Published papers/S/Smith, J. - A paper.pdf")
    ident = PaperIdentity.load(pdf)
    ident.doi = "10.1000/a"
    ident.save(pdf)
    before = snap(ck.lib)
    ident.doi = "10.1000/b"
    ident.save(pdf)
    assert snap(ck.lib) != before
    assert any(k.startswith(".mathpdf-sidecars/") for k in before)


# --------------------------------------------------------------------------
# The cockpit's one transaction helper, used by the buttons that were
# outside the log until 2026-10-15
# --------------------------------------------------------------------------

def _note(lib):
    return put(lib, "04 - Papers to be downloaded/J/Stopping.txt", b"DOI: 10.1/s\n")


def test_a_transaction_that_recorded_nothing_leaves_no_entry(ck):
    with ck.module._Transaction("nothing happens") as tx:
        pass
    assert not tx.committed and transactions(ck.lib) == []
    assert not list((ck.lib / ".operation_log").glob("*.journal.jsonl"))


def test_work_done_before_an_error_stays_undoable(ck):
    """The work recorded did happen: committed, marked INCOMPLETE, and
    Undo puts it back."""
    from ui.cockpit_actions import mark_flag_done
    note = _note(ck.lib)
    before = snapshot(ck.lib)
    with pytest.raises(RuntimeError):
        with ck.module._Transaction("Marked a download note done") as tx:
            mark_flag_done(note, ck.lib, undo_log=tx.log)
            raise RuntimeError("the next step failed")
    assert tx.committed
    (row,) = transactions(ck.lib)
    assert "INCOMPLETE" in row["description"]
    undo_from_activity(ck, row["id"])
    assert snapshot(ck.lib) == before


def test_streamlit_stopping_the_script_does_not_lose_the_record(ck):
    """Streamlit stops a script with a BaseException, which an
    ``except Exception`` would let through with the work unrecorded."""
    from ui.cockpit_actions import mark_flag_done

    class StopException(BaseException):        # streamlit's own is one
        pass

    note = _note(ck.lib)
    with pytest.raises(StopException):
        with ck.module._Transaction("Marked a download note done") as tx:
            mark_flag_done(note, ck.lib, undo_log=tx.log)
            raise StopException()
    (row,) = transactions(ck.lib)
    assert row["id"] == tx.id and row["operations_count"] == 1
