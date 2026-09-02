"""What a phrase ruling would target — measured on text, not guessed.

A phrase ruling is the only vocabulary decision that can rewrite names
already in the library, so the count shown next to it before the owner
clicks has to be exactly right about what it claims, and silent about
what it does not.

The pathologies below are all failure modes this repository has actually
shipped at least once:

* reaching into the AUTHOR block (a fix for the title once rewrote
  "Makovski" to "Markovski" because it searched the whole filename)
* comparing NFD input against NFC entries (macOS hands out NFD)
* treating "-", "–" and "—" as different names
* matching inside a longer word
"""
import unicodedata

import pytest
from hypothesis import given, strategies as st

from processing.phrase_impact import (
    already_correct,
    impact,
    occurrences,
    title_of,
    would_change,
)


# --------------------------------------------------------- the basic claim

def test_a_differently_spelled_name_is_reported():
    n = "Ishii, H. - Lecture notes, Brown university.pdf"
    assert impact([n], "Brown University") == [n]


def test_the_ruled_spelling_is_not_reported():
    n = "X, Y. - Held at Brown University today.pdf"
    assert impact([n], "Brown University") == []
    assert already_correct([n], "Brown University") == 1


def test_a_name_that_does_not_occur_is_not_reported():
    n = "A, B. - On the ergodic theorem.pdf"
    assert impact([n], "Brown University") == []
    assert already_correct([n], "Brown University") == 0


def test_nothing_to_fix_and_does_not_occur_are_DIFFERENT_states():
    """The reason already_correct exists at all.

    Both give an impact of 0. Showing only that number would make "this
    ruling is already satisfied" and "this phrase is not in your library"
    the same answer -- the exact conflation this project forbids.
    """
    have = "X, Y. - At Brown University.pdf"
    havent = "A, B. - On the ergodic theorem.pdf"
    assert impact([have], "Brown University") == []
    assert impact([havent], "Brown University") == []
    assert already_correct([have], "Brown University") == 1
    assert already_correct([havent], "Brown University") == 0


# ------------------------------------------------- the author-block trap

@pytest.mark.parametrize("name", [
    "Brown, university of somewhere - On the ergodic theorem.pdf",
    "New, York A. - A study of measure theory.pdf",
])
def test_the_author_block_is_never_searched(name):
    """A title rule that reads the author block corrupts people's names.

    This is not hypothetical: a spelling fix searched the whole filename
    and rewrote the author "Makovski" to "Markovski".
    """
    assert impact([name], "Brown University") == []
    assert impact([name], "New York") == []


def test_the_split_is_on_the_FIRST_separator():
    """normalize_full_name splits once; so must this, or the two disagree.

    A title containing " - " would otherwise be truncated differently
    here than in the code whose behaviour this is reporting on.
    """
    n = "A, B. - Brown university - a history of the place.pdf"
    assert title_of(n) == "Brown university - a history of the place.pdf"
    assert impact([n], "Brown University") == [n]


def test_a_name_with_NO_separator_is_never_reported():
    """THE REGRESSION, measured on the real library.

    normalize_full_name returns before any title work when the name has
    no " - ", so a ruling cannot change these files. Counting them said
    "17 files to fix" for Tōhoku Imperial University where the renamer
    fixes zero -- every one an un-separated scan name of the form
    "09-The science reports of the Tōhoku imperial university...".
    """
    n = "09-The science reports of the Tōhoku imperial university.pdf"
    assert title_of(n) == ""
    assert impact([n], "Tōhoku Imperial University") == []
    assert already_correct([n], "Tōhoku Imperial University") == 0


def test_a_separated_name_with_the_same_text_IS_reported():
    """The control: it is the separator that decides, not the words."""
    n = "Anon. - The science reports of the Tōhoku imperial university.pdf"
    assert impact([n], "Tōhoku Imperial University") == [n]


# ------------------------------------------------------- word boundaries

@pytest.mark.parametrize("title", [
    "The Brown universitys of the world",   # trailing letter
    "XBrown university",                    # leading letter
    "aBrown universityz",                   # both
])
def test_a_longer_word_is_not_a_match(title):
    """The casing MUST differ inside the longer word, or this proves nothing.

    The first draft used "XBrown University" -- the exact ruled spelling.
    Dropping the boundary check then still reported nothing, because the
    span it matched was already spelled correctly, so the test passed
    against a mutant that had deleted the very rule it named. Both
    boundary mutants survived until the fixtures were changed to differ
    in case.
    """
    assert impact([f"A, B. - {title}.pdf"], "Brown University") == []


def test_a_phrase_with_no_space_still_respects_boundaries():
    """Single-token phrases like "Euro-Par" have boundaries too."""
    assert impact(["A, B. - The euro-parallel algorithm.pdf"], "Euro-Par") == []
    assert impact(["A, B. - The euro-par workshop.pdf"], "Euro-Par")


@pytest.mark.parametrize("title", [
    "at brown university.pdf",
    "at brown university, Rhode Island.pdf",
    "(brown university)",
    "at brown university—1991",
])
def test_punctuation_around_the_phrase_still_matches(title):
    assert impact([f"A, B. - {title}"], "Brown University")


# ------------------------------------------------------- unicode and dashes

def test_NFD_input_matches_an_NFC_ruling():
    """macOS hands out decomposed filenames; the ruling is composed."""
    nfd = unicodedata.normalize(
        "NFD", "A, B. - The tōhoku imperial university reports.pdf")
    assert impact([nfd], "Tōhoku Imperial University") == [nfd]


@pytest.mark.parametrize("dash", ["-", "–", "—", "−"])
def test_matching_is_dash_blind(dash):
    n = f"A, B. - The takagi{dash}van der waerden function.pdf"
    assert impact([n], "Takagi–van der Waerden")


def test_a_dash_difference_ALONE_still_counts_as_needing_a_fix():
    """The ruling settles the dash too, not only the capitals."""
    n = "A, B. - The Takagi-van der Waerden function.pdf"
    assert impact([n], "Takagi–van der Waerden") == [n]


# ------------------------------------------------------------- degenerate

@pytest.mark.parametrize("phrase", ["", "   ", "\t"])
def test_an_empty_phrase_reports_nothing(phrase):
    n = "A, B. - Anything at all.pdf"
    assert impact([n], phrase) == []
    assert already_correct([n], phrase) == 0


def test_a_phrase_typed_with_stray_whitespace_is_stripped(self=None):
    """Reachable: the phrase can arrive from a text box.

    Without the strip, " Brown University " only matches when the title
    happens to have a space on BOTH sides, so "at brown university." --
    the ordinary case, ending in a full stop -- silently reports nothing.
    """
    n = "A, B. - Held at brown university.pdf"
    assert impact([n], "  Brown University  ") == [n]
    assert already_correct(["A, B. - Held at Brown University.pdf"],
                           "  Brown University  ") == 1


def test_occurrences_normalises_NFD_input_on_its_own():
    """occurrences() is public and may be called without title_of().

    Its callers here hand it NFC text, so the normalisation inside _fold
    is invisible from impact()/would_change() -- a mutant deleting it
    survived the whole file. It is kept because a direct caller with a
    raw macOS filename is a real use, and it is tested at that entry
    point rather than through a path that has already normalised.
    """
    nfd_title = unicodedata.normalize("NFD", "The tōhoku imperial reports")
    assert occurrences(nfd_title, "Tōhoku Imperial")
    assert occurrences(nfd_title,
                       unicodedata.normalize("NFD", "Tōhoku Imperial"))


def test_a_sharp_s_before_the_phrase_does_not_shift_the_span():
    """THE REGRESSION. "ß".casefold() is "ss" -- one character becomes two.

    The first implementation folded both strings and indexed the result
    into the original, so every character after a ß was reported one
    position early: the span sliced out of the title was not the text
    that matched, and "already correct" and "needs fixing" could swap.
    German ß is kept verbatim in this library by convention, so titles
    carrying one are ordinary, not exotic.
    """
    correct = "Weiß, A. - Maßtheorie at Brown University.pdf"
    wrong = "Weiß, A. - Maßtheorie at Brown university.pdf"
    assert impact([correct], "Brown University") == []
    assert already_correct([correct], "Brown University") == 1
    assert impact([wrong], "Brown University") == [wrong]


@pytest.mark.parametrize("prefix", ["Maßtheorie", "İstanbul", "ﬁnance",
                                    "Ωmega", "naïve"])
def test_spans_survive_any_character_whose_case_changes_length(prefix):
    """Property behind the regression, over the awkward cases.

    ß->ss and Turkish dotted I->i+combining-dot both change length under
    case folding; the ligature and the accented forms change length under
    normalisation. None of them may move the reported span.
    """
    name = f"A, B. - {prefix} at brown university today.pdf"
    got = impact([name], "Brown University")
    assert got == [name]
    title = title_of(name)
    spans = occurrences(title, "Brown University")
    assert [title[a:b] for a, b in spans] == ["brown university"], (
        "the span does not slice the text that matched")


@pytest.mark.parametrize("phrase", ["", "   ", "\t\n"])
def test_occurrences_refuses_an_empty_phrase_DIRECTLY(phrase):
    """Guarded in occurrences itself, not only in its callers.

    impact() and already_correct() reject an empty phrase before they get
    here, so a mutant deleting this guard survived through them. It is
    kept rather than deleted because occurrences() is public: without it
    re.escape("") compiles to a pattern that matches at EVERY position,
    so a direct caller gets one zero-width "occurrence" per character
    instead of nothing.
    """
    # The title MUST contain two adjacent non-letters, or this proves
    # nothing: a zero-width match only clears the word-boundary checks
    # when the characters on both sides are non-alphabetic, so a tidy
    # title rejects them anyway and the mutant survives. Both of these
    # are verbatim shapes from the library -- the double space is real
    # ("Föllmer, H., Schied, A. -  Robust preferences...").
    assert occurrences("Robust preferences,  convex measures of risk",
                       phrase) == []
    assert occurrences("Volume II, part 2 (1991)", phrase) == []


def test_an_empty_name_list_is_fine():
    assert impact([], "Brown University") == []
    assert already_correct([], "Brown University") == 0


def test_several_occurrences_in_one_title_count_the_file_once():
    n = ("A, B. - brown university and Brown University and "
         "BROWN UNIVERSITY.pdf")
    assert impact([n], "Brown University") == [n]
    assert len(occurrences(title_of(n), "Brown University")) == 3


# --------------------------------------------------------------- properties

_PHRASES = ["Brown University", "New York", "Takagi–van der Waerden",
            "London Mathematical Society"]


@given(st.sampled_from(_PHRASES),
       st.text(alphabet="abcdefg ,.", min_size=0, max_size=20))
def test_a_title_spelling_it_EXACTLY_is_never_reported(phrase, filler):
    """The core invariant: impact means 'differs', never 'occurs'."""
    name = f"A, B. - {filler}{phrase}{filler}.pdf"
    assert impact([name], phrase) == []


@given(st.sampled_from(_PHRASES))
def test_reporting_is_idempotent_under_applying_the_ruling(phrase):
    """Fix the spelling and the file stops being reported. No oscillation."""
    bad = f"A, B. - held at {phrase.lower()} in 1991.pdf"
    good = bad.replace(phrase.lower(), phrase)
    assert impact([bad], phrase) == [bad]
    assert impact([good], phrase) == []


@given(st.sampled_from(_PHRASES),
       st.lists(st.text(alphabet="abc ", min_size=1, max_size=8),
                min_size=0, max_size=6))
def test_impact_is_an_order_preserving_filter_of_its_input(phrase, fillers):
    """Not a set: two folders may hold the same basename, and that is two
    files to fix, not one.  Hypothesis found this by generating a repeated
    filler -- the first draft asserted uniqueness and was simply wrong
    about what the count means."""
    names = [f"A, B. - {f} {phrase.lower()}.pdf" for f in fillers]
    got = impact(names, phrase)
    assert got == [n for n in names if n in got], "order or multiplicity lost"
    assert len(got) == len(names), "every generated name differs in spelling"


@given(st.sampled_from(_PHRASES))
def test_would_change_agrees_with_impact(phrase):
    for title in (phrase, phrase.lower(), phrase.upper(), "nothing here"):
        n = f"A, B. - x {title} y.pdf"
        assert would_change(n, phrase) == bool(impact([n], phrase))
