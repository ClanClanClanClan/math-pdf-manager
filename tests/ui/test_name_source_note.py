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


# The local model could not name the paper (processing/model_input.py):
# that is "could not tell", and must never read like a name.
_JSTOR_WHY = ("page 1 is JSTOR's cover sheet, which names only the journal, and "
              "the other pages have no text to read (a scan without a text layer)")


def test_a_model_that_could_not_tell_is_a_warning_with_its_reason():
    lvl, text = name_source_note(prev("", model=("unknown", _JSTOR_WHY)))
    assert lvl == "warning"
    assert text == (
        "No title in the PDF or the registries, and the local AI model could "
        f"not name it: {_JSTOR_WHY}. This name comes from the file name (no "
        "title was found); check it before approving, or type the real one.")


def test_could_not_tell_outranks_no_record():
    # arXiv's "no such paper" would otherwise be the whole story, worded
    # as a plain caption.
    lvl, text = name_source_note(prev("", arxiv=("absent", ""),
                                      model=("unknown", _JSTOR_WHY)))
    assert lvl == "warning" and text.startswith("No title in the PDF or the registries")


def test_a_registry_that_could_not_be_asked_still_comes_first():
    # Asking again may yet give the title; that advice must not be lost.
    lvl, text = name_source_note(prev("", arxiv=("unknown", "no connection"),
                                      model=("unknown", _JSTOR_WHY)))
    assert lvl == "warning" and text.startswith("arXiv could not be checked: no connection.")


def test_a_model_answer_that_was_used_is_flagged_as_before():
    assert name_source_note(prev("llm", model=("found", ""))) == name_source_note(prev("llm"))


def test_the_model_is_not_a_registry_to_ask_again():
    assert unsettled_lookups(prev("", model=("unknown", _JSTOR_WHY))) == []


def test_the_preview_carries_the_models_verdict(tmp_path, monkeypatch):
    import pdf_processing.llm_extractor as llm_mod
    from tests.test_processing.test_model_input import JSTOR_SHEET, Model, pages_pdf
    from ui.paper_preview import preview_pdf

    Model.texts = []
    Model.model_file = tmp_path / "model.gguf"
    Model.model_file.write_bytes(b"weights")
    monkeypatch.setattr(llm_mod, "LLMMetadataExtractor", Model)
    p = preview_pdf(pages_pdf(tmp_path / "Download (1).pdf", [JSTOR_SHEET, ""]))
    assert p.canonical_filename == "Download (1).pdf"
    assert p.lookups["model"] == {"state": "unknown", "reason": _JSTOR_WHY}
    assert name_source_note(p)[0] == "warning" and Model.texts == []
