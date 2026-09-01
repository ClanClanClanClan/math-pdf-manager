"""A spelling fix must not lower-case the word it corrects.

THIS ONE DAMAGED A REAL FILE. The owner reported it after using the cockpit:

    "it proposed to replace things like Browniam, which is incorrect, by
     brownian, which is not correct, it should be Brownian. Same thing with
     Makov --> markov. ... even if they start the title and should be
     capitalised (it made me fuck up one title, find it again and put the
     capital letter back)"

THE MECHANISM. Suggestions come from ``maintenance.typos.nearest_frequent``,
which looks them up in a corpus keyed on LOWER-CASE words, so every suggestion
arrives in lower case. The Spelling page then did

    new = row["name"].replace(s["word"], s["suggestion"], 1)

substituting it verbatim. A misspelled proper noun therefore lost its capital,
and a misspelled word at the START of the title lost the title's capital —
which is the version that actually cost him a file.

The fix carries the original's case onto the suggestion, and forces a capital
in title-initial position whatever the original carried, because a lower-case
first word is itself the error and must not be propagated.
"""
import pytest

from processing.spelling_vocab import apply_case_of, replace_preserving_case


# ------------------------------------------------------- the reported cases

@pytest.mark.parametrize("name,word,suggestion,expected", [
    # THE REGRESSIONS, verbatim from the report.
    ("Bouchard, B. - Browniam motion.pdf", "Browniam", "brownian",
     "Bouchard, B. - Brownian motion.pdf"),
    ("Bouchard, B. - A note on Makov chains.pdf", "Makov", "markov",
     "Bouchard, B. - A note on Markov chains.pdf"),
    # THE ONE THAT DAMAGED A FILE: the misspelling starts the title.
    ("Bouchard, B. - Makov chains revisited.pdf", "Makov", "markov",
     "Bouchard, B. - Markov chains revisited.pdf"),
])
def test_the_reported_damage(name, word, suggestion, expected):
    assert replace_preserving_case(name, word, suggestion) == expected


def test_an_acronym_stays_an_acronym():
    assert replace_preserving_case(
        "A, B. - On BROWNIAM motion.pdf", "BROWNIAM", "brownian"
    ) == "A, B. - On BROWNIAN motion.pdf"


def test_ordinary_prose_stays_lower_case():
    """The fix must not start capitalising ordinary words."""
    assert replace_preserving_case(
        "A, B. - A note on teh method.pdf", "teh", "the"
    ) == "A, B. - A note on the method.pdf"


def test_a_lower_case_word_starting_the_title_is_raised():
    """A title's first word is capitalised by convention.

    A lower-case original there is itself the error, so its case must not be
    propagated — this is the one place the original is overruled.
    """
    assert replace_preserving_case(
        "A, B. - teh method explained.pdf", "teh", "the"
    ) == "A, B. - The method explained.pdf"


# ------------------------------------------------------------ the case rule

@pytest.mark.parametrize("original,replacement,expected", [
    ("Browniam", "brownian", "Brownian"),
    ("BROWNIAM", "brownian", "BROWNIAN"),
    ("browniam", "brownian", "brownian"),
    ("Makov", "markov", "Markov"),
    ("Ito", "itô", "Itô"),
])
def test_the_shape_is_carried_over(original, replacement, expected):
    assert apply_case_of(original, replacement) == expected


def test_a_mixed_shape_is_left_to_the_suggestion():
    """"McDonald" must not become "Mcdonald".

    Guessing an interior capital is how "MacKean" becomes "Mckean". The
    suggestion's own spelling is trusted for anything that is not plainly
    Xxxx or XXXX.
    """
    assert apply_case_of("McDonlad", "McDonald") == "McDonald"


def test_a_single_capital_letter_is_not_treated_as_an_acronym():
    """"I" is upper-case and one letter; upper-casing the whole suggestion
    from it would be wrong."""
    assert apply_case_of("A", "a") == "A"


@pytest.mark.parametrize("bad", ["", None])
def test_empty_input_is_survived(bad):
    assert apply_case_of(bad or "", "x") == "x"
    assert apply_case_of("Word", "") == ""


# --------------------------------------------------------------- pathology

def test_a_word_that_is_not_in_the_name_leaves_it_alone():
    name = "A, B. - A title.pdf"
    assert replace_preserving_case(name, "absent", "present") == name


def test_only_the_first_occurrence_is_replaced():
    """Matching the old `.replace(..., 1)` contract exactly."""
    out = replace_preserving_case(
        "A, B. - Makov and Makov again.pdf", "Makov", "markov")
    assert out == "A, B. - Markov and Makov again.pdf"


def test_a_name_with_no_author_separator_still_works():
    """Not every filename has an author block."""
    assert replace_preserving_case("Makov chains.pdf", "Makov", "markov") == \
        "Markov chains.pdf"


def test_the_author_block_is_not_mistaken_for_the_title():
    """The title starts after the LAST " - ", as the decomposer defines it.

    A hyphenated author name must not move the boundary.
    """
    out = replace_preserving_case(
        "Ash, R.-B., Doleans-Dade, C. - teh theory.pdf", "teh", "the")
    assert out == "Ash, R.-B., Doleans-Dade, C. - The theory.pdf"


def test_a_word_only_in_the_author_block_is_not_rewritten_at_all():
    """CORRECTED. This test used to assert the author block WAS rewritten.

    That was the behaviour at the time, and it was a bug: a spelling suspect
    is a TITLE token, so a match in the author block is a coincidence, not a
    correction. Rewriting an author's surname from a title typo is exactly
    the corruption the audit found. The name is now left alone.
    """
    name = "Browniam, A. - A study of motion.pdf"
    assert replace_preserving_case(name, "Browniam", "brownian") == name


def test_unicode_survives():
    assert replace_preserving_case(
        "A, B. - Azema martingales.pdf", "Azema", "azéma"
    ) == "A, B. - Azéma martingales.pdf"


def test_the_length_of_the_name_changes_only_by_the_word():
    """A guard against the slicing being off by one."""
    name = "A, B. - Browniam motion.pdf"
    out = replace_preserving_case(name, "Browniam", "brownian")
    assert len(out) == len(name) - len("Browniam") + len("brownian")
    assert out.endswith(".pdf")


class TestTheBranchesMutationFound:
    """Cases the first draft could not distinguish. Each kills a survivor."""

    def test_a_single_capital_does_not_upper_case_the_whole_suggestion(self):
        """Kills: `len(original) > 1` dropped from the acronym test.

        The earlier test used apply_case_of("A", "a"), where upper-casing and
        capitalising give the same answer, so it could not tell the two apart.
        A one-letter original mapping to a LONGER suggestion can.
        """
        assert apply_case_of("I", "in") == "In", (
            "one capital letter is a capitalised word, not an acronym"
        )
        assert apply_case_of("IN", "in") == "IN"

    def test_the_title_starts_after_the_FIRST_separator(self):
        """MUTATION CORRECTED THE CODE HERE, not the test.

        The first implementation used rfind, on the guess that the title
        starts after the LAST " - ". A mutant swapping it for find was
        "killed" — and the mutant was RIGHT. filename_ground_truth.decompose
        says "A, B. - Markets - teh basics" has the title "Markets - teh
        basics", because a title may itself contain " - " ("... - Lecture 2 -
        Price models"). rfind would have forced a capital mid-title.

        The boundary now comes from the decomposer, so there is no second
        rule to disagree with.
        """
        out = replace_preserving_case(
            "A, B. - Markets - teh basics.pdf", "teh", "the")
        assert out == "A, B. - Markets - the basics.pdf", out

    def test_the_word_at_the_real_title_start_does_get_the_capital(self):
        """The mirror of the above, on the same shape of filename."""
        out = replace_preserving_case(
            "A, B. - teh markets - a study.pdf", "teh", "the")
        assert out == "A, B. - The markets - a study.pdf", out

    def test_the_boundary_comes_from_the_decomposer(self):
        """One rule, one implementation.

        If this module grows its own author/title rule again it will drift
        from filename_ground_truth, which is the project's single answer.
        """
        import pathlib as _p
        src = _p.Path("src/processing/spelling_vocab.py").read_text()
        assert "filename_ground_truth" in src, (
            "the title boundary must be asked of the decomposer, not guessed"
        )

    def test_the_cockpit_uses_the_case_preserving_replacement(self):
        """Kills: the Spelling page going back to a raw str.replace.

        The helper being correct is worth nothing if the page does not call
        it — and the page calling `.replace(word, suggestion, 1)` directly is
        exactly the bug that damaged a file.
        """
        import pathlib
        src = pathlib.Path("src/ui/cockpit.py").read_text()
        assert "replace_preserving_case(" in src, (
            "the Spelling page must go through the case-preserving helper"
        )
        assert 's["suggestion"], 1)' not in src, (
            "a raw one-shot .replace with the suggestion is the original bug"
        )
        assert '.replace(s["word"]' not in src

    def test_the_fallback_also_uses_the_first_separator(self, monkeypatch):
        """Kills: `find` -> `rfind` in the fallback branch.

        The decomposer is reliable for 99.86% of this library, so the
        fallback almost never runs — which is exactly why it would rot
        unnoticed. It must agree with the decomposer on the ordinary shape,
        not disagree with it.
        """
        import processing.filename_ground_truth as fgt

        def _boom(*_a, **_k):
            raise RuntimeError("decomposer unavailable")

        monkeypatch.setattr(fgt, "decompose", _boom)
        out = replace_preserving_case(
            "A, B. - Markets - teh basics.pdf", "teh", "the")
        assert out == "A, B. - Markets - the basics.pdf", (
            f"the fallback put the title boundary in the wrong place: {out}"
        )

    def test_the_fallback_still_capitalises_a_real_title_start(self, monkeypatch):
        import processing.filename_ground_truth as fgt
        monkeypatch.setattr(
            fgt, "decompose",
            lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("nope")))
        out = replace_preserving_case(
            "A, B. - teh markets.pdf", "teh", "the")
        assert out == "A, B. - The markets.pdf", out


class TestTheReplacementStaysInTheTitle:
    """A typo fix must never touch the author block.

    FOUND BY AN AUDIT OF THIS FUNCTION, after it shipped. The first version
    used a plain ``name.find(word)``, which reaches into the author block and
    matches inside a longer surname:

        "Makovski, D. - Makov chains for finance.pdf"
             ^^^^^ matched here
        ->  "Markovski, D. - Makov chains ..."

    The AUTHOR is corrupted and the typo survives — the worst possible
    outcome, because the file now has a wrong name AND still shows up as a
    suspect. The suspect words come from maintenance.typos, which tokenises
    the TITLE, so the title is the only place a match belongs.
    """

    def test_a_surname_containing_the_typo_is_untouched(self):
        out = replace_preserving_case(
            "Makovski, D. - Makov chains for finance.pdf", "Makov", "markov")
        assert out == "Makovski, D. - Markov chains for finance.pdf", out

    def test_a_surname_containing_the_suggestion_is_untouched(self):
        """"Theodore" contains "the"; the author must survive it."""
        out = replace_preserving_case(
            "Theodore, A. - teh method.pdf", "teh", "the")
        assert out == "Theodore, A. - The method.pdf", out

    def test_the_match_is_on_a_word_boundary(self):
        """A short typo must not match inside a longer title word."""
        out = replace_preserving_case(
            "A, B. - Theorems on teh method.pdf", "teh", "the")
        assert out == "A, B. - Theorems on the method.pdf", out
        assert "Theorems" in out, "the longer word must be left alone"

    def test_a_word_present_only_in_the_author_block_is_not_replaced(self):
        """If it is not in the title, there is nothing to fix."""
        name = "Makov, D. - A study of diffusions.pdf"
        assert replace_preserving_case(name, "Makov", "markov") == name

    def test_the_first_TITLE_occurrence_is_the_one_replaced(self):
        out = replace_preserving_case(
            "Makov, D. - Makov and Makov again.pdf", "Makov", "markov")
        assert out == "Makov, D. - Markov and Makov again.pdf", out
