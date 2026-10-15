"""The Sort Queue asks arXiv once per 25 papers, and says when it could not.

MEASURED 2026-10-15 on the real inbox: 2,065 of 2,414 waiting papers
(85.5%) ask arXiv, one request per paper, 0.3-2.3 s each when arXiv is
healthy and 10 s each (twice, with Approve) when it is not. The page now
asks for the next 25 together, and tells the owner in words when a name
was built without arXiv's answer -- "could not be checked" (asked again
later) is never worded like "has no record" (an answer).
"""
from __future__ import annotations

import pytest
import requests

from processing import lookup_cache as lc
from tests.test_processing.test_stage0_fixes import write_pdf
from tests.ui.test_cockpit_renders_content import (  # noqa: F401  (fixtures)
    cockpit, home, lib, rendered_text)

ATOM = ('xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"')


class Resp:
    def __init__(self, status=200, content=b""):
        self.status_code = status
        self.content = content


def feed(ids):
    body = "".join(f"<entry><id>http://arxiv.org/abs/{i}v1</id>"
                   f"<title>Registry title {i}</title>"
                   f"<author><name>Author {i}</name></author></entry>"
                   for i in ids)
    return (f'<?xml version="1.0"?><feed {ATOM}><opensearch:totalResults>'
            f'{len(ids)}</opensearch:totalResults>{body}</feed>').encode()


def _inbox(lib, n):
    staging = lib / "12 - To be sorted" / "03 - Working papers"
    ids = [f"2401.{i:05d}" for i in range(1, n + 1)]
    for i in ids:
        write_pdf(staging / f"{i}v1.pdf", title=f"Embedded title {i}",
                  author="Embedded, A.")
    return ids


@pytest.fixture
def arxiv(monkeypatch):
    """Answers every id it is asked about, unless told otherwise."""
    state = {"calls": [], "mode": "answer"}

    def fake_get(url, *a, **k):
        ids = url.split("id_list=")[1].split("&")[0].split(",")
        state["calls"].append(ids)
        mode = state["mode"]
        if mode == "down":
            raise requests.exceptions.ConnectTimeout("no route")
        if mode == "garbage":
            return Resp(200, b"<feed")
        if mode == "none":
            return Resp(200, feed([]))
        return Resp(200, feed(ids))

    monkeypatch.setattr(requests, "get", fake_get)
    return state


def _batches(calls):
    return [c for c in calls if len(c) > 1]


def test_one_request_covers_the_next_25_papers(cockpit, lib, arxiv):
    ids = _inbox(lib, 30)
    cockpit.render_sort_queue()
    assert len(arxiv["calls"]) == 1, arxiv["calls"]
    assert arxiv["calls"][0] == ids[:25]
    # Clicking around the same paper asks nothing more.
    cockpit.render_sort_queue()
    assert len(arxiv["calls"]) == 1


def test_the_paper_shown_uses_the_answer(cockpit, lib, arxiv):
    _inbox(lib, 3)
    cockpit.render_sort_queue()
    text = rendered_text(cockpit.st)
    assert "Registry title 2401.00001" in text
    assert "Title and authors from arXiv." in text
    from tests.ui.test_cockpit_renders_content import text_of
    assert "Reading the next paper" in text_of(cockpit.st, "spinner"), (
        "the wait (up to a minute when the local model reads) must show")


def test_the_window_moves_on_after_25(cockpit, lib, arxiv):
    ids = _inbox(lib, 30)
    cockpit.render_sort_queue()
    staging = lib / "12 - To be sorted" / "03 - Working papers"
    for i in ids[:25]:          # the owner works through the first 25
        cockpit.st.session_state.sort_skipped.add(str(staging / f"{i}v1.pdf"))
    cockpit.render_sort_queue()
    assert arxiv["calls"][1] == ids[25:]
    assert len(arxiv["calls"]) == 2


def test_working_through_the_queue_one_by_one_asks_nothing_more(
        cockpit, lib, arxiv):
    """Paper 2 must not trigger a request for paper 26: a window that
    slides by one would turn the batch back into one request per paper."""
    ids = _inbox(lib, 30)
    staging = lib / "12 - To be sorted" / "03 - Working papers"
    for i in ids[:10]:
        cockpit.render_sort_queue()
        cockpit.st.session_state.sort_skipped.add(str(staging / f"{i}v1.pdf"))
    assert len(arxiv["calls"]) == 1, arxiv["calls"]


def test_a_window_that_settles_nothing_is_not_asked_on_every_click(
        cockpit, lib, arxiv):
    _inbox(lib, 5)
    arxiv["mode"] = "garbage"
    for _ in range(4):
        cockpit.render_sort_queue()
    assert len(_batches(arxiv["calls"])) == 1, arxiv["calls"]


def test_a_window_is_asked_again_once_the_pause_is_over(
        cockpit, lib, arxiv, monkeypatch):
    _inbox(lib, 5)
    arxiv["mode"] = "garbage"
    cockpit.render_sort_queue()
    asked = cockpit.st.session_state["sort_arxiv_asked"]
    for k in asked:
        asked[k] -= lc.UNREACHABLE_FOR + 1
    arxiv["mode"] = "answer"
    cockpit.render_sort_queue()
    assert len(_batches(arxiv["calls"])) == 2


def test_an_outage_costs_one_wait_and_is_said_plainly(cockpit, lib, arxiv):
    _inbox(lib, 5)
    arxiv["mode"] = "down"
    cockpit.render_sort_queue()
    cockpit.render_sort_queue()
    assert len(arxiv["calls"]) == 1, (
        f"an unreachable arXiv was asked {len(arxiv['calls'])} times")
    text = rendered_text(cockpit.st)
    assert "arXiv could not be checked" in text
    assert "the PDF's own metadata" in text
    assert "Embedded title 2401.00001" in text
    assert "Ask again now" in text
    assert "has no record" not in text
    from tests.ui.test_cockpit_renders_content import text_of
    assert "arXiv could not be checked" in text_of(cockpit.st, "warning"), (
        "an unchecked name must stand out, not sit in grey small print")


def test_ask_again_stops_waiting_for_the_pause(cockpit, lib, arxiv):
    ids = _inbox(lib, 2)
    arxiv["mode"] = "down"
    cockpit.render_sort_queue()
    assert lc.unreachable("arxiv")
    staging = lib / "12 - To be sorted" / "03 - Working papers"
    cockpit.st.values[f"reask_{staging / (ids[0] + 'v1.pdf')}"] = True
    cockpit.render_sort_queue()
    assert lc.unreachable("arxiv") is None


def test_no_such_paper_is_an_answer_not_a_failure(cockpit, lib, arxiv):
    _inbox(lib, 1)
    arxiv["mode"] = "none"
    cockpit.render_sort_queue()
    text = rendered_text(cockpit.st)
    assert "arXiv has no record of this paper" in text
    assert "could not be checked" not in text
    assert "Ask again now" not in text
