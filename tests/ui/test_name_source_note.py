"""What the Sort Queue says about where a proposed name came from.

"Could not be checked" is retried and must stand out; "has no record" is
an answer and must not be worded like a failure; a title the local model
guessed must be flagged before it is approved.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.paper_preview import PaperPreview, name_source_note, unsettled_lookups


def prev(source="", **lookups):
    return PaperPreview(Path("x.pdf"), title_source=source,
                        lookups={k: {"state": s, "reason": r}
                                 for k, (s, r) in lookups.items()})


def test_unreachable_arxiv_is_a_warning_with_its_reason():
    lvl, text = name_source_note(prev("embedded", arxiv=("unknown", "no connection")))
    assert lvl == "warning"
    assert text.startswith("arXiv could not be checked: no connection.")
    assert "the PDF's own metadata" in text


def test_unreachable_crossref_is_a_warning_too():
    lvl, text = name_source_note(prev("embedded", crossref=("unknown", "it answered HTTP 503")))
    assert lvl == "warning" and text.startswith("Crossref could not be checked")


def test_arxiv_down_but_crossref_answered_names_crossref():
    lvl, text = name_source_note(prev("crossref", arxiv=("unknown", "no connection"),
                                      crossref=("found", "")))
    assert lvl == "warning"
    assert "This name comes from Crossref instead" in text


@pytest.mark.parametrize("svc, word", [("arxiv", "arXiv"), ("crossref", "Crossref")])
def test_no_such_paper_is_a_plain_statement(svc, word):
    lvl, text = name_source_note(prev("embedded", **{svc: ("absent", "x")}))
    assert lvl == "caption"
    assert text == f"{word} has no record of this paper, so this name comes " \
                   "from the PDF's own metadata."


def test_a_model_guess_is_flagged():
    lvl, text = name_source_note(prev("llm"))
    assert lvl == "warning" and "local AI model" in text and "Check it" in text


@pytest.mark.parametrize("src, word", [("arxiv", "arXiv"), ("crossref", "Crossref"),
                                       ("hal", "HAL")])
def test_a_registry_title_says_which(src, word):
    assert name_source_note(prev(src)) == ("caption", f"Title and authors from {word}.")


def test_embedded_and_nothing():
    assert name_source_note(prev("embedded")) == (
        "caption", "Name from the PDF's own metadata.")
    assert name_source_note(prev("")) == (
        "caption", "Name from the file name (no title was found).")


def test_only_unknown_is_unsettled():
    p = prev("embedded", arxiv=("absent", ""), crossref=("unknown", "x"))
    assert unsettled_lookups(p) == ["crossref"]
    assert unsettled_lookups(prev("arxiv", arxiv=("found", ""))) == []
