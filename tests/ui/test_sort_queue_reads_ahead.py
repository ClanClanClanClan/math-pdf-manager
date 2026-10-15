"""The Sort Queue page reads the next papers while the owner looks at one.

MEASURED 2026-10-15 on the real inbox: the first time the local AI model
read a paper the page showed a spinner for 26-49 s, and 68 of the 2,414
waiting papers always need it. The page now hands the next 25 papers to
``processing.read_ahead`` once its own paper is on screen, and stops it
from every other page. These tests drive the real page (under the
recording Streamlit stand-in) with a model stand-in whose reads a test can
hold open, to make each race happen rather than hope for it.
"""
from __future__ import annotations

import sys
import threading
import time

from processing import local_model, read_ahead
from tests.test_processing.test_read_ahead import (  # noqa: F401  (fixture)
    Model, model, paper, read_words, wait_until)
from tests.ui.test_cockpit_renders_content import (  # noqa: F401  (fixtures)
    cockpit, home, lib, rendered_text, text_of)


def inbox(lib, n):
    staging = lib / "12 - To be sorted" / "03 - Working papers"
    return [paper(staging, f"scan_{i:03d}.pdf", f"Word{i}") for i in range(n)]


def test_the_page_hands_over_the_next_25_once_its_own_paper_is_read(
        cockpit, lib, model, monkeypatch):
    ps = inbox(lib, 30)
    seen = {}
    real = read_ahead.want

    def recording(paths):
        paths = list(paths)
        seen["paths"] = paths
        seen["own_paper_read_first"] = "Word0" in read_words()
        real(paths)

    monkeypatch.setattr(read_ahead, "want", recording)
    cockpit.render_sort_queue()
    assert seen["paths"] == ps[1:26]
    assert seen["own_paper_read_first"], (
        "the read-ahead must not compete with the paper on screen")


def test_the_next_model_paper_is_shown_without_reading_it_again(
        cockpit, lib, model):
    ps = inbox(lib, 3)
    cockpit.render_sort_queue()
    wait_until(lambda: read_ahead.status()["ready"] == 2, what="read ahead")
    assert read_words() == ["Word0", "Word1", "Word2"]
    cockpit.st.session_state.sort_skipped.add(str(ps[0]))   # he moves on
    cockpit.st.calls.clear()
    t0 = time.perf_counter()
    cockpit.render_sort_queue()
    shown = time.perf_counter() - t0
    assert "Read: Word1" in rendered_text(cockpit.st)
    assert read_words() == ["Word0", "Word1", "Word2"], "read again on show"
    assert shown < 5, f"showing a pre-read paper took {shown:.1f} s"


def hold_at(word):
    """Hold the model inside its read of ``word`` until the gate opens."""
    def on_read(text):
        if text.split()[0] == word:
            Model.gate.clear()
    Model.on_read = on_read


def test_the_page_never_waits_for_a_read_ahead_in_progress(
        cockpit, lib, model):
    inbox(lib, 2)
    hold_at("Word1")
    cockpit.render_sort_queue()                  # paper 0 read and shown
    wait_until(local_model.is_reading, what="paper 1 being read ahead")
    t0 = time.perf_counter()
    cockpit.render_sort_queue()                  # he clicks around paper 0
    took = time.perf_counter() - t0
    Model.gate.set()
    assert took < 5, f"the page waited {took:.1f} s for a paper not on screen"
    assert "Read: Word0" in rendered_text(cockpit.st)


def test_leaving_the_page_stops_reading_ahead_and_lets_the_model_go(
        cockpit, lib, model):
    inbox(lib, 4)
    hold_at("Word1")
    cockpit.render_sort_queue()
    wait_until(local_model.is_reading, what="paper 1 being read ahead")
    cockpit.st.session_state["page"] = "Attention"
    cockpit.main()
    Model.gate.set()
    t = read_ahead._thread
    if t is not None:
        t.join(10)
    assert read_ahead._thread is None
    assert not local_model.is_loaded(), "4.4 GB kept after he left the page"
    assert read_words() == ["Word0", "Word1"], "kept reading after he left"


def test_a_rerun_of_the_page_script_finds_the_same_thread(
        cockpit, lib, model):
    inbox(lib, 3)
    hold_at("Word1")
    cockpit.render_sort_queue()
    wait_until(local_model.is_reading, what="paper 1 being read ahead")
    first = read_ahead._thread
    # What Streamlit does on every click: run the page script again from
    # the top, in a new thread, on the same page.
    cockpit.st.session_state["page"] = "Sort Queue"
    sys.modules.pop("ui.cockpit", None)
    import ui.cockpit                           # noqa: F401  (runs main())
    assert read_ahead._thread is first
    alive = [t for t in threading.enumerate()
             if t.name == "sort-queue-read-ahead"]
    assert alive == [first]
    Model.gate.set()
    wait_until(lambda: read_ahead.status()["ready"] == 2, what="read ahead")
    assert read_words() == ["Word0", "Word1", "Word2"]


def test_two_reruns_racing_read_each_paper_once_with_one_model(
        cockpit, lib, model):
    inbox(lib, 4)
    start = threading.Barrier(2)
    errors = []

    def rerun():
        try:
            start.wait(10)
            cockpit.render_sort_queue()
        except Exception as exc:            # pragma: no cover - reported below
            errors.append(exc)

    runs = [threading.Thread(target=rerun) for _ in range(2)]
    for t in runs:
        t.start()
    for t in runs:
        t.join(20)
    assert not errors
    wait_until(lambda: read_ahead.status()["ready"] == 3, what="read ahead")
    assert sorted(read_words()) == ["Word0", "Word1", "Word2", "Word3"]
    assert Model.max_live == 1, "two models were loaded at once"
    assert Model.max_reading == 1


def test_the_page_says_it_is_reading_ahead(cockpit, lib, model):
    inbox(lib, 3)
    hold_at("Word1")
    cockpit.render_sort_queue()
    wait_until(local_model.is_reading, what="paper 1 being read ahead")
    cockpit.st.calls.clear()
    cockpit.render_sort_queue()
    Model.gate.set()
    said = text_of(cockpit.st, "caption")
    assert "Reading ahead: 0 of the next 2 papers are ready; the local AI " \
           "model is reading one now." in said
