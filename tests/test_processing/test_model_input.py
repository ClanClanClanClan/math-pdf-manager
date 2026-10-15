"""What the local model reads, and which of its answers count as a name.

MEASURED 2026-10-15, read-only, on the real "12 - To be sorted": five
different scans (Download (1).pdf, Download2/4/6/8.pdf) carry one page
of text -- JSTOR's sheet "Institute of Mathematical Statistics is
collaborating with JSTOR to digitize, preserve, and extend access to The
Annals of Probability." -- and the model named all five "The Annals of
probability" by "000-00". A Birkhäuser book whose only text was its
series description was named "Modern Birkhäuser classics". Every other
cover sheet there (ResearchGate, HAL, Taylor & Francis, DML-CZ) names the
paper and was read correctly, and JSTOR's later sheets carry the paper's
title on all 330 in the library whose filename has one; those must be
left alone.

The texts below are the real ones, verbatim.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as hst

from processing import model_input as mi

#: Page 1 of each of the five inbox scans, byte for byte.
JSTOR_SHEET = ("Institute of Mathematical Statistics is collaborating with "
               "JSTOR to digitize, preserve, and extend access to\n"
               "The Annals of Probability.\nwww.jstor.org\n®\n")

#: A later JSTOR sheet (shape of the library's 2009 Annals sheet): the
#: same sentence, below the paper's own title, authors and source.
JSTOR_LATER_SHEET = (
    "HIDING A DRIFT\nAuthor(s): Miklós Rásonyi, Walter Schachermayer and "
    "Richard Warnung\nSource: The Annals of Probability, Vol. 37, No. 6 "
    "(November 2009), pp. 2459-2479\nPublished by: Institute of Mathematical "
    "Statistics\nStable URL: http://www.jstor.org/stable/25662210\n"
    "Accessed: 05/03/2013 11:08\nYour use of the JSTOR archive indicates your "
    "acceptance of the Terms & Conditions of Use, available at.\n"
    "http://www.jstor.org/page/info/about/policies/terms.jsp\n.\n"
    "JSTOR is a not-for-profit service that helps scholars, researchers, and "
    "students discover, use, and build upon a wide range of\ncontent in a "
    "trusted digital archive.\n.\nInstitute of Mathematical Statistics is "
    "collaborating with JSTOR to digitize, preserve and extend access to The "
    "Annals of Probability.\nhttp://www.jstor.org\n")

#: Page 3 of the inbox's Lunardi book (pages 1-2 are images), verbatim.
MBC_BLURB = (
    "Modern Birkh¨auser Classics\nMany of the original research and survey "
    "monographs in pure and \napplied mathematics published by Birkhäuser in "
    "recent decades have \nbeen groundbreaking and have come to be regarded "
    "as foundational to \nthe subject. Through the MBC Series, a select "
    "number of these modern \nclassics, entirely uncorrected, are being "
    "re-released in paperback (and as \neBooks) to ensure that these "
    "treasures remain accessible to new \ngenerations of students, scholars, "
    "and researchers.  \n")

#: The same description in the library's Triebel (words broken over lines)
#: and Hörmander (a scan: no umlaut, "In"), verbatim.
MBC_TRIEBEL = (
    "Modern Birkhäuser Classics\nMany of the original research and survey "
    "monographs in pure and \napplied mathematics published by Birkhäuser in "
    "recent decades \nhave been groundbreaking and have come to be regarded as "
    "found-\national to the subject. Through the MBC Series, a select number "
    "of \nthese modern classics, entirely uncorrected, are being re-released "
    "\nin paperback (and as eBooks) to ensure that these treasures remain "
    "\naccessible to new generations of students, scholars, and resear-\n"
    "chers.\n")
MBC_HORMANDER = (
    "Modern Birkhauser Classics \nMany of the original research and survey "
    "monographs In pure and \napplied mathematics published by Birkhauser in "
    "recent decades \nhave been groundbreaking and have come to be regarded as "
    "foun-\ndational to the subject. Through the MBC Series, a select number "
    "of \nthese modern classics, entirely uncorrected, are being re-released in "
    "\npaperback (and as eBooks) to ensure that these treasures remain ac-\n"
    "cessible to new generations of students, scholars, and researchers. \n")
HORMANDER_TITLE = "Notions of Convexity \nLars Hormander \nReprint of the 1994 Edition \nBirkhauser \n"

RESEARCHGATE_SHEET = (
    "See discussions, stats, and author profiles for this publication at: "
    "https://www.researchgate.net/publication/394450840\nReﬁned Expansions of "
    "the Skew-Stickiness Ratio in Stochastic Volatility\nModels\nPreprint · "
    "August 2025\nDOI: 10.13140/RG.2.2.20177.65125\nCITATIONS\n0\nREADS\n8\n")

TITLE_PAGE = ("On the law of the iterated logarithm\nHenry Teicher\n"
              "Rutgers University\nAbstract. We prove a law of the iterated "
              "logarithm for weighted sums of independent random variables.\n")


# ---------------------------------------------------------------------------
# The page rule
# ---------------------------------------------------------------------------

def test_the_inbox_jstor_sheet_is_furniture():
    assert mi.furniture(JSTOR_SHEET) == "JSTOR's cover sheet, which names only the journal"


@pytest.mark.parametrize("page", [MBC_BLURB, MBC_TRIEBEL, MBC_HORMANDER,
                                  MBC_TRIEBEL.replace("resear-\n", "resear- \n  ")])
def test_the_birkhauser_series_description_is_furniture(page):
    assert mi.furniture(page) == "the Modern Birkhäuser Classics series description"


def test_hormander_is_read_from_his_title_page():
    # The library's copy: blank, the description, then the title page.
    assert mi.text_for_model(["", MBC_HORMANDER, HORMANDER_TITLE]) == (
        HORMANDER_TITLE, ["page 2 is the Modern Birkhäuser Classics series description"])


def test_the_model_still_reads_the_page_with_its_line_breaks_and_hyphens():
    page = "A treatise on Hamilton-\nJacobi equations\nBy A. Author\n"
    assert mi.text_for_model([MBC_TRIEBEL, page]) == (page, [
        "page 1 is the Modern Birkhäuser Classics series description"])


@pytest.mark.parametrize("page", [JSTOR_LATER_SHEET, RESEARCHGATE_SHEET, TITLE_PAGE,
                                  MBC_BLURB + "Analytic Semigroups and Optimal "
                                              "Regularity in Parabolic Problems\n",
                                  JSTOR_SHEET + "On the law of the iterated logarithm\n"])
def test_a_sheet_that_names_the_paper_is_kept(page):
    assert mi.furniture(page) is None


def test_one_word_left_over_keeps_the_page():
    # Leaving a page out is the risky direction: anything that could be a
    # title, even a one-word one, keeps it.
    assert mi.furniture(JSTOR_SHEET + "Funktionalanalysis\n") is None


@pytest.mark.parametrize("scrap", ["(R)\n", "p. 1\n", "1\n", "©\n", "— ii —\n"])
def test_scraps_of_one_or_two_letters_do_not_keep_the_sheet(scrap):
    assert mi.furniture(JSTOR_SHEET.replace("®\n", scrap)) is not None


@pytest.mark.parametrize("page", ["", "   \n", "®", "www.jstor.org\n"])
def test_a_page_with_no_furniture_sentence_is_never_furniture(page):
    # An empty page gives the model nothing either way; only a page that
    # carries an archive's or publisher's own sentence is left out.
    assert mi.furniture(page) is None


@pytest.mark.parametrize("form", ["NFD", "NFC"])
def test_the_decision_does_not_depend_on_how_accents_are_stored(form):
    page = unicodedata.normalize(form, MBC_BLURB.replace("Birkh¨auser", "Birkhäuser"))
    assert mi.furniture(page) == "the Modern Birkhäuser Classics series description"


@pytest.mark.parametrize("org, journal", [
    ("American Mathematical Society", "Transactions of the American\nMathematical Society."),
    ("Société Mathématique de France", "Bulletin de la S. M. F."),
    ("Institute of Mathematical Statistics", "The Annals of Applied Probability"),
])
def test_the_jstor_sheet_for_any_publisher_and_journal(org, journal):
    page = (f"{org} is collaborating with JSTOR to digitise, preserve and "
            f"extend access to\n{journal}\nhttp://www.jstor.org\n")
    assert mi.furniture(page) == "JSTOR's cover sheet, which names only the journal"


def test_a_cover_then_the_title_page_reads_the_title_page_only():
    text, left_out = mi.text_for_model([JSTOR_SHEET, TITLE_PAGE, "Body text.\n"])
    assert text == TITLE_PAGE + "Body text.\n"
    assert left_out == ["page 1 is JSTOR's cover sheet, which names only the journal"]


def test_a_paper_whose_header_names_its_journal_is_read_unchanged():
    page = ("The Annals of Probability\n1995, Vol. 23, No. 2, 511–535\n"
            "A HISTORY OF THE ANNALS OF PROBABILITY\nBy John Smith\n")
    assert mi.text_for_model([page]) == (page, [])


# Text that can never contain a furniture sentence: no "JSTOR", no
# "Birkh". Lines of words, numbers and punctuation like real front matter.
_page_text = hst.text(
    alphabet=hst.characters(blacklist_categories=("Cs",),
                            blacklist_characters="JjBb"),
    max_size=1800)


@given(hst.lists(_page_text, max_size=3))
def test_without_furniture_the_model_reads_exactly_what_it_always_read(pages):
    # The property that keeps every remembered answer valid: for a paper
    # with no furniture page the text -- hence the cache key -- is the
    # old one, byte for byte.
    assert mi.text_for_model(pages) == ("".join(pages)[:mi.LIMIT], [])


@given(hst.lists(_page_text, max_size=2),
       hst.sampled_from([JSTOR_SHEET, MBC_BLURB]),
       hst.integers(min_value=0, max_value=2))
def test_a_furniture_page_anywhere_is_left_out_and_the_rest_kept(rest, sheet, where):
    where = min(where, len(rest))
    pages = rest[:where] + [sheet] + rest[where:]
    text, left_out = mi.text_for_model(pages)
    assert text == "".join(rest)[:mi.LIMIT]
    assert len(left_out) == 1 and left_out[0].startswith(f"page {where + 1} is ")


_wrap = hst.sampled_from([" ", "\n", "  ", " \n"])


@given(_wrap, _wrap, _wrap, hst.sampled_from(["digitize", "digi-\ntize", "digi- \n tize"]))
def test_the_jstor_sheet_is_found_however_its_lines_are_broken(a, b, c, word):
    page = (f"Institute of Mathematical Statistics is collaborating{a}with JSTOR "
            f"to {word},{b}preserve, and extend access to{c}The Annals of "
            f"Probability.\nwww.jstor.org\n®\n")
    assert mi.furniture(page) is not None


_title = hst.lists(hst.text(alphabet="abcdefghijklmnopqrstuvwxyzéü", min_size=3,
                            max_size=12), min_size=2, max_size=8).map(" ".join)


@given(_title, hst.sampled_from([JSTOR_SHEET, MBC_BLURB]), hst.booleans())
def test_any_title_on_a_furniture_page_keeps_the_page(title, sheet, before):
    page = f"{title}\n{sheet}" if before else f"{sheet}{title}\n"
    assert mi.furniture(page) is None


def test_nothing_to_read_says_why_and_never_on_enough_text():
    assert mi.nothing_to_read("x" * mi.MIN_CHARS, []) is None
    assert mi.nothing_to_read("x" * mi.MIN_CHARS, ["page 1 is a sheet"]) is None
    assert mi.nothing_to_read("", ["page 1 is a sheet"]) == (
        "page 1 is a sheet, and the other pages have no text to read "
        "(a scan without a text layer)")
    assert mi.nothing_to_read("short", ["page 1 is a sheet"]) == (
        "page 1 is a sheet, and the other pages have almost no text")
    assert mi.nothing_to_read("", []) == (
        "the first pages have no text to read (a scan without a text layer)")
    assert mi.nothing_to_read("x" * (mi.MIN_CHARS - 1), []) == (
        "the first pages have almost no text")


# ---------------------------------------------------------------------------
# The answer rule
# ---------------------------------------------------------------------------

def test_the_measured_answer_is_refused():
    why = mi.answer_problem({"title": "The Annals of probability", "authors": ["000-00"]})
    assert why == ("it gave '000-00' as an author, which is not a name, so its "
                   "title 'The Annals of probability' is not trusted either")


@pytest.mark.parametrize("answer", [
    {"title": "A simple proof of the characteristic function of Student’s "
              "t-distribution", "authors": ["Gaunt", "R.E."]},     # measured
    {"title": "Principles of random walk", "authors": ["Spitzer", "F."]},  # measured
    {"title": "Funktionalanalysis", "authors": []},
    {"title": "О мартингалах", "authors": ["Ширяев", "А. Н."]},
    {"title": "A history of the Annals of Probability", "authors": ["John Smith"]},
])
def test_a_name_is_used(answer):
    assert mi.answer_problem(answer) is None


@pytest.mark.parametrize("answer, why", [
    (None, "it gave no answer"),
    ({"title": "", "authors": []}, "it read the first pages and found no title"),
    ({"title": "   ", "authors": ["A B"]}, "it read the first pages and found no title"),
    ({"authors": ["A B"]}, "it read the first pages and found no title"),
    ({"title": "2019", "authors": ["A B"]}, "it gave '2019' as the title, which has no words"),
    ({"title": "Real title", "authors": ["Smith", "—"]},
     "it gave '—' as an author, which is not a name, so its title 'Real title' "
     "is not trusted either"),
])
def test_not_a_name(answer, why):
    assert mi.answer_problem(answer) == why


def test_authors_given_as_one_string_or_not_at_all_are_judged_as_names():
    # The extractor always hands back a list, but the judge takes any
    # answer: a remembered one, or one from another extractor.
    assert mi.answer_problem({"title": "A real title", "authors": "John Smith"}) is None
    assert mi.answer_problem({"title": "A real title", "authors": None}) is None
    assert mi.answer_problem({"title": "A real title", "authors": "000-00"}) is not None


@given(hst.text(alphabet="0123456789-.,;:()[]/ *†‡§", min_size=1, max_size=12),
       hst.lists(hst.sampled_from(["Smith", "J.", "Ширяев", "李"]), max_size=4),
       hst.integers(min_value=0, max_value=4))
def test_any_author_without_a_letter_refuses_the_whole_answer(junk, names, at):
    authors = names[:at] + [junk] + names[at:]
    why = mi.answer_problem({"title": "A real title", "authors": authors})
    assert why is not None and repr(junk.strip()) in why


# ---------------------------------------------------------------------------
# Through the real extraction, with a stand-in model
# ---------------------------------------------------------------------------

def pages_pdf(path: Path, pages) -> Path:
    """A PDF whose pages carry exactly these lines ("" = an image-only page)."""
    import fitz

    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        y = 72
        for line in text.split("\n"):
            if line:
                page.insert_text((72, y), line, fontsize=9)
            y += 12
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


class Model:
    """Stands in for the local model; remembers what it was handed."""

    texts: list = []
    answer = {"title": "Read it", "authors": ["Ann Author"]}
    model_file = Path("/nonexistent")
    fail = False

    def __init__(self, model_path):
        pass

    def extract(self, text):
        Model.texts.append(text)
        if Model.fail:
            raise RuntimeError("the model fell over")
        return dict(Model.answer)

    def close(self):
        pass

    @staticmethod
    def local_model_path():
        return Model.model_file

    @staticmethod
    def is_available():
        return True


@pytest.fixture
def model(tmp_path, monkeypatch):
    import pdf_processing.llm_extractor as llm_mod

    Model.texts = []
    Model.answer = {"title": "Read it", "authors": ["Ann Author"]}
    Model.fail = False
    Model.model_file = tmp_path / "model.gguf"
    Model.model_file.write_bytes(b"weights")
    monkeypatch.setattr(llm_mod, "LLMMetadataExtractor", Model)
    return Model


def extract(path):
    from processing.ingest import extract_metadata_from_pdf
    return extract_metadata_from_pdf(path)


def fitz_text(path):
    import fitz
    doc = fitz.open(path)
    try:
        return [doc[i].get_text() for i in range(min(3, len(doc)))]
    finally:
        doc.close()


def test_five_different_scans_behind_one_sheet_are_not_named(model, tmp_path):
    # Different papers (page counts 2-9, as in the inbox), same sheet.
    metas = []
    for i, n_pages in enumerate([7, 9, 2, 4, 3]):
        pdf = pages_pdf(tmp_path / f"Download{i}.pdf", [JSTOR_SHEET] + [""] * (n_pages - 1))
        metas.append(extract(pdf))
    assert model.texts == []                      # not even asked
    for m in metas:
        assert m["title"] == "" and m.get("title_source") is None
        assert m["lookups"]["model"]["state"] == "unknown"
        assert m["lookups"]["model"]["reason"].startswith(
            "page 1 is JSTOR's cover sheet, which names only the journal, and "
            "the other pages have no text to read")


def test_one_sheet_in_front_of_different_papers_gives_each_its_own_text(model, tmp_path):
    bodies = [f"Paper number {w} on {w} processes\nBy {w.title()} Author\n"
              + f"We study {w} processes at length. " * 5 for w in
              ("alpha", "beta", "gamma", "delta", "epsilon")]
    for i, body in enumerate(bodies):
        extract(pages_pdf(tmp_path / f"D{i}.pdf", [JSTOR_SHEET, body]))
    assert len(model.texts) == 5 and len(set(model.texts)) == 5
    for t in model.texts:
        assert "JSTOR" not in t and "Annals" not in t


def test_the_title_page_after_a_sheet_is_what_the_model_reads(model, tmp_path):
    pdf = pages_pdf(tmp_path / "x.pdf", [JSTOR_SHEET, TITLE_PAGE, "More text " * 20])
    meta = extract(pdf)
    pages = fitz_text(pdf)
    assert model.texts == ["".join(pages[1:])[:mi.LIMIT]]
    assert meta["title"] == "Read it" and meta["title_source"] == "llm"
    assert meta["lookups"]["model"] == {"state": "found", "reason": ""}


_LONG_PAGE = "\n".join(f"Line {i} of a long page of body text, set in nine point." for i in range(60))


def test_a_paper_without_furniture_is_read_from_the_same_text_as_before(model, tmp_path):
    # Three full pages, far over 4,000 characters: the cut is the old one.
    pdf = pages_pdf(tmp_path / "x.pdf", [RESEARCHGATE_SHEET, TITLE_PAGE + _LONG_PAGE, _LONG_PAGE])
    meta = extract(pdf)
    assert len("".join(fitz_text(pdf))) > 4000
    assert model.texts == ["".join(fitz_text(pdf))[:4000]]
    assert meta["fulltext_sample"] == model.texts[0]


def test_after_a_sheet_the_cut_is_still_4000_characters(model, tmp_path):
    pdf = pages_pdf(tmp_path / "x.pdf", [JSTOR_SHEET, _LONG_PAGE * 2, _LONG_PAGE])
    extract(pdf)
    rest = "".join(fitz_text(pdf)[1:])
    assert len(rest) > 4000 and model.texts == [rest[:4000]]


def test_a_genuine_title_that_mentions_a_journal_is_used(model, tmp_path):
    model.answer = {"title": "A history of the Annals of Probability",
                    "authors": ["John Smith"]}
    pdf = pages_pdf(tmp_path / "x.pdf", [
        "The Annals of Probability\n1995, Vol. 23, No. 2, 511–535\n"
        "A HISTORY OF THE ANNALS OF PROBABILITY\nBy John Smith\n" + "Text. " * 40])
    meta = extract(pdf)
    assert meta["title"] == "A history of the Annals of Probability"
    assert meta["authors"] == ["John Smith"]
    assert meta["lookups"]["model"]["state"] == "found"


def test_a_wrong_answer_remembered_before_the_rule_is_refused(model, tmp_path):
    # The cache key is the exact text. A paper whose text did NOT change
    # still finds its old answer -- and it must not be used.
    from processing import ingest, lookup_cache as lc

    page = "Some front matter that the model misread. " * 5
    pdf = pages_pdf(tmp_path / "x.pdf", [page])
    text = "".join(fitz_text(pdf))[:4000]
    lc.put("llm", ingest._llm_key(model.model_file, text),
           lc.Answer(lc.FOUND, {"title": "The Annals of probability", "authors": ["000-00"]}))
    meta = extract(pdf)
    assert model.texts == []                      # the remembered answer was found
    assert meta["title"] == ""
    assert meta["lookups"]["model"]["state"] == "unknown"
    assert "'000-00' as an author" in meta["lookups"]["model"]["reason"]


def test_the_old_key_of_a_changed_text_is_never_looked_up(model, tmp_path, monkeypatch):
    from processing import ingest, lookup_cache as lc

    pdf = pages_pdf(tmp_path / "x.pdf", [JSTOR_SHEET, TITLE_PAGE])
    old_text = "".join(fitz_text(pdf))[:4000]     # what the model used to get
    lc.put("llm", ingest._llm_key(model.model_file, old_text),
           lc.Answer(lc.FOUND, {"title": "The Annals of probability", "authors": ["Old"]}))
    asked = []
    real_get = lc.get
    monkeypatch.setattr(lc, "get", lambda ns, key, **k: asked.append((ns, key)) or real_get(ns, key, **k))
    meta = extract(pdf)
    assert ("llm", ingest._llm_key(model.model_file, old_text)) not in asked
    assert meta["title"] == "Read it"


def test_a_model_that_fails_is_unknown_and_not_remembered(model, tmp_path):
    from processing import ingest, lookup_cache as lc

    model.fail = True
    pdf = pages_pdf(tmp_path / "x.pdf", [TITLE_PAGE + "Body text. " * 20])
    meta = extract(pdf)
    assert meta["title"] == ""
    assert meta["lookups"]["model"] == {
        "state": "unknown",
        "reason": "it failed (RuntimeError); it will be asked again next time"}
    text = "".join(fitz_text(pdf))[:4000]
    assert lc.get("llm", ingest._llm_key(model.model_file, text)) is None


def test_an_empty_answer_says_the_model_found_no_title(model, tmp_path):
    model.answer = {"title": "", "authors": []}
    meta = extract(pages_pdf(tmp_path / "x.pdf", [TITLE_PAGE + "Body text. " * 20]))
    assert meta["lookups"]["model"] == {
        "state": "unknown", "reason": "it read the first pages and found no title"}


def test_a_page_too_short_to_read_does_not_load_the_model(model, tmp_path, monkeypatch):
    from processing import local_model

    loads = local_model.loads
    meta = extract(pages_pdf(tmp_path / "x.pdf", ["IMU, ICM, Medals, Prizes,\nand Laureates\n"]))
    assert model.texts == [] and local_model.loads == loads
    assert meta["lookups"]["model"] == {
        "state": "unknown", "reason": "the first pages have almost no text"}


def test_with_no_model_on_this_machine_nothing_is_claimed(tmp_path, monkeypatch):
    import pdf_processing.llm_extractor as llm_mod

    class NoModel(Model):
        @staticmethod
        def local_model_path():
            return None

    monkeypatch.setattr(llm_mod, "LLMMetadataExtractor", NoModel)
    meta = extract(pages_pdf(tmp_path / "x.pdf", [JSTOR_SHEET]))
    assert "model" not in (meta.get("lookups") or {})


def test_with_the_model_file_but_not_the_software_nothing_is_asked(model, tmp_path, monkeypatch):
    monkeypatch.setattr(Model, "is_available", staticmethod(lambda: False))
    meta = extract(pages_pdf(tmp_path / "x.pdf", [TITLE_PAGE + "Body text. " * 20]))
    assert model.texts == [] and "model" not in (meta.get("lookups") or {})
    assert meta["title"] == ""


def test_the_batch_sort_says_why_too(model, tmp_path):
    from processing.ingest import ingest_paper

    lib = tmp_path / "lib"
    lib.mkdir()
    pdf = pages_pdf(tmp_path / "inbox" / "Download (1).pdf", [JSTOR_SHEET, "", ""])
    res = ingest_paper(pdf, library_root=lib, dry_run=True)
    assert res["identification_state"] != "identified"
    assert res["identification_note"].endswith(
        "; the local AI model could not name it: page 1 is JSTOR's cover sheet, "
        "which names only the journal, and the other pages have no text to read "
        "(a scan without a text layer)")
