"""One fix must not re-read 27,382 filenames.

REPORTED: "pressing a button to do a replacement is laggy, and it take a
noticeable time for the page to update".

MEASURED. Every action button ended with

    st.session_state.pop("spelling", None); st.rerun()

which discards the scan of every filename in the library to learn about the
one file that just changed. The work a click actually needs is under 25 ms
(rename 0.8 ms, ruling write 0.22 ms, redraw ~22 ms). The rescan that
followed was 2,374 ms warm and **36–51 seconds** end to end in the live
cockpit — a factor of 100 to 1,500 over the work being done.

THE PROOF BY CONSTRUCTION: the "Not now" button never popped, and it was
instant (~481 ms end to end) — the same page, the same rerun. The pop was
the whole cost.

WHY DROPPING ONE ROW IS SAFE. A suspect is a hapax by construction
(maintenance/typos.py requires title_df == 1), so renaming it can only
change the document frequencies of words inside that one title; no other
row's verdict can move. The one knife-edge — a corrected word crossing
MIN_PARTNER_FREQ and becoming a new suggestion partner — could only ADD
rows that were never on screen, and Rescan is still there for that.
"""
import pathlib

import pytest


SRC = pathlib.Path("src/ui/cockpit.py").read_text()


def test_the_scan_is_not_discarded_by_a_rename():
    """The regression, asserted at source level.

    The buttons live inside a Streamlit render loop that a unit test cannot
    press, so the guard is on the code: a rename must drop its own row, not
    the whole scan.
    """
    i = SRC.index('_log_activity("spelling.character"')
    window = SRC[i:i + 500]
    assert "_drop_spelling_row(" in window, window[:300]
    assert 'pop("spelling"' not in window, (
        "a character fix must not discard the scan of every filename"
    )


def test_the_typo_fix_does_not_discard_the_scan():
    i = SRC.index('_log_activity("spelling.fix"')
    window = SRC[i:i + 500]
    assert "_drop_spelling_row(" in window
    assert 'pop("spelling"' not in window


def test_calling_a_word_real_does_not_discard_the_scan():
    i = SRC.index('will not be raised again')
    window = SRC[i:i + 300]
    assert 'pop("spelling"' not in window, (
        "the ruling filter hides the row; there is nothing to recompute"
    )


def test_exactly_one_action_still_pays_for_a_rescan():
    """"Put it back in the queue" genuinely needs the row recomputed.

    Pinned so that if someone removes it the trade-off is reconsidered
    rather than lost, and so that new pops cannot creep back in unnoticed.
    """
    body = SRC[SRC.index("def render_spelling("):]
    body = body[:body.index("\ndef ")] if "\ndef " in body[10:] else body
    assert body.count('st.session_state.pop("spelling", None)') == 1, (
        "exactly one action — restoring a ruled word — may rescan"
    )
    i = body.index('st.session_state.pop("spelling", None)')
    assert "clear_ruling" in body[max(0, i - 400):i]


def test_every_ruling_hides_its_row_not_just_a_deferral():
    """The filter that makes "it's a real word" free."""
    assert "ruled_out = deferred | set(rulings[CORRECT]) | set(rulings[\"typo\"])" in SRC
    assert 'if s["lower"] in ruled_out:' in SRC
    assert 'if s["lower"] in deferred:' not in SRC, (
        "the narrow filter left a ruled word on screen, which is why the "
        "button had to throw the scan away"
    )


class TestTheRowDropper:
    """_drop_spelling_row itself."""

    def _state(self):
        return {"suspects": [{"rel": "a.pdf"}, {"rel": "b.pdf"}],
                "broken": [{"rel": "b.pdf"}, {"rel": "c.pdf"}]}

    def test_it_drops_only_the_named_row(self, monkeypatch):
        import ui.cockpit as cockpit
        state = {"spelling": self._state()}
        monkeypatch.setattr(cockpit, "st", type("S", (), {"session_state": state})())
        cockpit._drop_spelling_row("a.pdf")
        assert [r["rel"] for r in state["spelling"]["suspects"]] == ["b.pdf"]
        assert [r["rel"] for r in state["spelling"]["broken"]] == ["b.pdf", "c.pdf"]

    def test_it_drops_from_every_list_the_row_appears_in(self, monkeypatch):
        import ui.cockpit as cockpit
        state = {"spelling": self._state()}
        monkeypatch.setattr(cockpit, "st", type("S", (), {"session_state": state})())
        cockpit._drop_spelling_row("b.pdf")
        assert [r["rel"] for r in state["spelling"]["suspects"]] == ["a.pdf"]
        assert [r["rel"] for r in state["spelling"]["broken"]] == ["c.pdf"]

    def test_an_unknown_row_changes_nothing(self, monkeypatch):
        import ui.cockpit as cockpit
        state = {"spelling": self._state()}
        monkeypatch.setattr(cockpit, "st", type("S", (), {"session_state": state})())
        cockpit._drop_spelling_row("zzz.pdf")
        assert len(state["spelling"]["suspects"]) == 2
        assert len(state["spelling"]["broken"]) == 2

    def test_no_scan_in_session_leaves_the_session_untouched(self, monkeypatch):
        """A second tab, or a fresh session, has no scan to edit.

        Asserts the session is left exactly as found, not merely that
        nothing raised — "it did not crash" is not evidence that it did
        the right thing.
        """
        import ui.cockpit as cockpit
        state = {"other": "keep me"}
        monkeypatch.setattr(cockpit, "st", type("S", (), {"session_state": state})())
        cockpit._drop_spelling_row("a.pdf")
        assert state == {"other": "keep me"}, (
            "with no scan to edit it must change nothing, and in particular "
            "must not create an empty one that later reads as 'no suspects'"
        )
        assert "spelling" not in state
