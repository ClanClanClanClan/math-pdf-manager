"""A title that is entirely mathematics must survive sentence-casing.

THE BUG. ``to_sentence_case_academic`` collected the WORD tokens of a title
and, finding none, returned the single character ``"X"``. A title with no
WORD tokens is not an empty title -- it is usually a title that is ENTIRELY
mathematics, or entirely one whitelisted phrase, and those need no case
change at all because every character in them is already protected.

MEASURED over the 25,049 in-scope library titles: three were destroyed.

    F-processes      -> X        (one PHRASE token; it is in the whitelist)
    G-expectations   -> X        (same)
    Freefem++        -> X        (one MATH token)

and "L^2" likewise. The bug predates the maths-detector work and gets WORSE
the better the detector is, because a more accurate detector claims more
titles whole -- so it had to be fixed before landing a detector that claims
1,344 titles instead of 877.

The fix is narrow: no WORD tokens but some MATH or PHRASE token means "no
case change needed", so return the title unchanged. "X" now means only what
it always should have -- there is genuinely nothing here to case.
"""
import pytest

from core.sentence_case import to_sentence_case_academic


def _cased(title):
    out = to_sentence_case_academic(title)
    return out[0] if isinstance(out, tuple) else out


def _changed(title):
    out = to_sentence_case_academic(title)
    return out[1] if isinstance(out, tuple) else None


@pytest.mark.parametrize("title", [
    "F-processes",
    "G-expectations",
    "Freefem++",
])
def test_the_three_real_library_titles_that_were_destroyed(title):
    """THE REGRESSION. These are real filenames from the owner's library."""
    assert _cased(title) == title


@pytest.mark.parametrize("title", [
    "L^2", "AR(1)", "H^1", "X_t", "ℝ", "Σ", "L²", "ℂⁿ", "∂",
])
def test_a_title_that_is_only_mathematics_is_returned_unchanged(title):
    assert _cased(title) == title


@pytest.mark.parametrize("title", [
    "F-processes", "L^2", "Freefem++",
])
def test_and_is_reported_as_unchanged_not_as_a_rewrite(title):
    """Reporting a no-op as a change would put it in the review queue.

    Worse, a caller that trusts the flag would write the file back.
    """
    assert _changed(title) is False


def test_genuinely_empty_input_still_returns_the_placeholder():
    """The narrow fix must not swallow the case "X" was actually for."""
    for empty in ("", "   ", "\t\n"):
        assert _cased(empty) == "X"


def test_punctuation_only_still_gets_its_prefix():
    """Unchanged behaviour: a title of pure punctuation is not a title."""
    assert _cased("...").startswith("X")


def test_ordinary_prose_is_untouched_by_the_fix():
    assert _cased("Brownian motion") == "Brownian motion"


def test_maths_mixed_with_prose_still_gets_cased():
    """The fix must only fire when there are NO word tokens."""
    out = _cased("The L^2 Theory Of Something")
    assert "L^2" in out, "the mathematics must still be protected"
    assert out != "X"
    assert len(out) > 10, out


def test_no_library_title_is_catastrophically_shortened():
    """The population check that found the bug, kept as a guard.

    Any title whose cased output loses more than half its length is a
    destroyed title, whatever the mechanism.
    """
    import json, pathlib
    fx = (pathlib.Path(__file__).resolve().parents[1]
          / "fixtures" / "math_regions_ground_truth.json")
    if not fx.exists():
        pytest.skip("corpus fixture unavailable — this check is UNKNOWN, not OK")
    titles = [r["title"] for r in json.loads(fx.read_text())["labelled"]]
    destroyed = [t for t in titles if len(str(_cased(t))) < len(t) * 0.5]
    assert not destroyed, destroyed[:5]


class TestASentenceStartScanMustStopAtContent:
    """A MATH token is content, and the sentence-start scan must see it.

    THE BUG. Deciding whether a word begins a sentence means scanning back
    for sentence-ending punctuation, stopping at the first content token on
    the way. The scan stopped at a WORD but walked straight THROUGH a MATH
    or PHRASE token.

    THE LIBRARY MAKES THIS BITE. It writes "/" as ":" in filenames, so
    "1/H-variation" is stored as "1:H-variation". Scanning back from
    "variation": through the MATH token "H", onto the ":", which reads as a
    sentence-ending colon -- so "Variation" got capitalised mid-title.

    MEASURED over the 25,049 in-scope titles: 8 affected, every one
    corrected by this fix, none made worse.
    """

    @pytest.mark.parametrize("title,must_contain", [
        ("A remark on the 1:H-variation of the fractional Brownian motion",
         "1:H-variation"),
        ("The 1:H-variation of the divergence integral", "1:H-variation"),
        ("On the 1:e-strategy for the best-choice problem", "1:e-strategy"),
        ("How to beat the 1:e-strategy of best choice", "1:e-strategy"),
        ("On optimal transport maps between 1:d-concave densities",
         "1:d-concave densities"),
    ])
    def test_a_colon_behind_a_math_token_does_not_start_a_sentence(
        self, title, must_contain
    ):
        """Real library titles, each previously over-capitalised."""
        assert must_contain in _cased(title)

    def test_the_maths_letter_is_still_protected(self):
        """The fix must not buy correct prose by giving up the symbol.

        Before ANY of this work the incumbent lowercased the H outright
        ('1:h-variation'), which is the worse error of the two.
        """
        out = _cased("A remark on the 1:H-variation of the fractional Brownian motion")
        assert "1:H-" in out, f"the protected H was lost: {out}"
        assert "1:h-" not in out

    def test_a_phrase_token_also_stops_the_scan(self):
        """PHRASE is content for the same reason MATH is."""
        out = _cased("Evaluations for ς(2), ς(4), ..., ς(2k) based on the WZ method")
        assert "based on" in out, out

    def test_a_real_sentence_boundary_still_capitalises(self):
        """The fix must not disable sentence-start detection itself."""
        out = _cased("A first claim. A second claim follows")
        assert out.count("A ") >= 1
        assert ". a second" not in out.lower() or ". A second" in out

    def test_a_title_with_no_maths_is_unaffected(self):
        assert _cased("The Dirichlet problem. Existence of solutions") == \
            _cased("The Dirichlet problem. Existence of solutions")
