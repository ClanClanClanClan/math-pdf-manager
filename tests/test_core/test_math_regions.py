"""Which spans of a title are mathematics.

Three implementations preceded this one and all three were wrong. The tests
below are organised around HOW each was wrong, so a regression reintroduces a
named failure rather than an anonymous one.
"""
import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from core.math_regions import find_math_regions


def spans(text):
    return [text[s:e] for s, e in find_math_regions(text)]


class TestAccentedLettersAreNotMathematics:
    """The detector's defect. It claimed 'e-acute' 4,331 times; 3,614 of the
    4,238 titles it flagged (85%) contain no mathematics at all. Downstream,
    conformance asked it which part of a title was prose and was handed
    "Prcis d'analyse relle" -- 15% of titles affected."""

    @pytest.mark.parametrize("title", [
        "Théorie du potentiel et probabilités à Rennes",
        "Précis d'analyse réelle, volume 2",
        "Économétrie de la finance",
        "Wie K. Itô den stochastischen Kalkül revolutionierte",
        "Über die Grundlagen der Wahrscheinlichkeitsrechnung",
        "Sur les inégalités de Sobolev logarithmiques",
    ])
    def test_no_regions(self, title):
        assert find_math_regions(title) == []


class TestProseIsNotMathematics:
    """The scanner's defect. MATHEMATICAL_VARIABLES was the whole ASCII
    alphabet, so one operator -- and "-" is one -- ran the region through
    letters, digits AND SPACES to the end of the sentence. It claimed 49.6%
    of a title on average and one span covered 186 of 189 characters."""

    @pytest.mark.parametrize("title", [
        "On square-root boundaries for Bessel processes, and pole-seeking Brownian motion",
        "(Almost) Everything you always wanted to know about deterministic control",
        "Non-asymptotic convergence analysis of the stochastic gradient method",
        "Mean-field limit of a stochastic particle system",
        "A P.D.E. approach to Asian options",
        "Dupire (1994) revisited",
    ])
    def test_no_regions(self, title):
        assert find_math_regions(title) == []

    def test_never_a_span_of_plain_english(self):
        """The invariant, stated directly: whatever led us there, a span of
        nothing but ASCII letters and spaces is prose."""
        for title in ["a - b", "x + y is fine", "signal + noise", "P vs NP"]:
            for s in spans(title):
                assert not all(c.isascii() and (c.isalpha() or c.isspace())
                               for c in s), (title, s)


class TestUnicodeMathematicsIsFound:
    """What the library actually contains: no LaTeX at all, ~800 mathematical
    characters across 25,005 titles, written in Unicode."""

    @pytest.mark.parametrize("title,expected", [
        ("L² and H¹ estimates", ["L²", "H¹"]),
        ("Lᵖ estimates", ["Lᵖ"]),
        ("Bₜ martingales", ["Bₜ"]),
        ("Γ-convergence of the functional", ["Γ-convergence"]),
        ("The ∂-Neumann problem on ℂⁿ", ["∂-Neumann", "ℂⁿ"]),
        ("σ-algebras and π-systems", ["σ-algebras", "π-systems"]),
        ("Filtering and ⅓ power law", ["⅓"]),
        ("Small-time asymptotics as H→0", ["H→0"]),
    ])
    def test_found(self, title, expected):
        assert spans(title) == expected

    @pytest.mark.parametrize("title,expected", [
        # the subscript letters live in three different Unicode blocks, which
        # is why the rule asks Unicode for the NAME rather than the block
        ("lᵣ spaces", ["lᵣ"]),       # U+1D63 Phonetic Extensions
        ("εᵢ convergence", ["εᵢ"]),  # U+1D62 Phonetic Extensions
        ("Bₜ paths", ["Bₜ"]),        # U+209C Superscripts and Subscripts
    ])
    def test_subscripts_from_any_block(self, title, expected):
        assert spans(title) == expected


class TestNotationalShapes:
    @pytest.mark.parametrize("title,expected", [
        ("A C^{0,1}-functional Itô's formula", ["C^{0,1}"]),
        ("L^2 estimates", ["L^2"]),
        ("X_t is adapted", ["X_t"]),
        ("SL(2, ℤ) representations", ["SL(2, ℤ)"]),
        ("AR(1) processes", ["AR(1)"]),
    ])
    def test_found(self, title, expected):
        assert spans(title) == expected

    @pytest.mark.parametrize("title,expected", [
        # real notation the FIRST version of the guard wrongly rejected: it
        # demanded a digit or a maths character inside, and these have
        # neither. 13 in the library, every one mathematics -- "Gl(n)" would
        # be wrong.
        ("sin(x) dx", ["sin(x)"]),
        ("GL(n) representations", ["GL(n)"]),
        ("f(x) and f(n)", ["f(x)", "f(n)"]),
        ("GL(N, F) orbital integrals", ["GL(N, F)"]),
        ("Bes(d) process", ["Bes(d)"]),
        ("R(3, k) Ramsey numbers", ["R(3, k)"]),
    ])
    def test_arguments_without_a_digit_still_count(self, title, expected):
        assert spans(title) == expected

    @pytest.mark.parametrize("title", [
        "(Almost) Everything you wanted",     # no identifier before the bracket
        "Dupire (1994) revisited",            # a space before the bracket
        "The part(one) of it",                # a real word inside
        "See note(also) below",
    ])
    def test_a_bracket_holding_prose_is_left_alone(self, title):
        assert find_math_regions(title) == []


class TestOneExpressionMayContainSpaces:
    """50 real spans depend on this: an expression broken by a space is still
    one expression, and prose is never a span, so nothing but mathematics can
    be joined."""

    @pytest.mark.parametrize("title,expected", [
        ("A bipolar theorem for L⁰_+(Ω, ℱ, ℙ)", ["L⁰_+(Ω, ℱ, ℙ)"]),
        ("A variant on (2Jₛ-Rₛ, s≥0) for processes", ["(2Jₛ-Rₛ, s≥0)"]),
        ("Extrapolation on Hˢ, 0<s≤1 spaces", ["Hˢ, 0<s≤1"]),
    ])
    def test_joined(self, title, expected):
        assert spans(title) == expected

    def test_but_not_across_prose(self):
        """"L² and H¹" is two expressions with a word between them."""
        assert spans("L² and H¹ estimates") == ["L²", "H¹"]


class TestLatexIsStillUnderstood:
    """The library has none, but the tokeniser's contract is one MATH token
    per formula and other text may carry it. Dropping delimiter support
    returned the Black-Scholes equation as six spans instead of one."""

    def test_display_math(self):
        assert spans(r"Equation: \[f(x) = x^2\] shown") == [r"\[f(x) = x^2\]"]

    def test_inline_dollars_of_realistic_length(self):
        t = (r"The Black-Scholes formula $\frac{\partial V}{\partial t} + "
             r"\frac{1}{2}\sigma^2 S^2 = rV$ is fundamental.")
        got = spans(t)
        assert len(got) == 1, got
        assert got[0].startswith("$") and got[0].endswith("$")


class TestTheFileExtensionIsNotMathematics:
    """A period is a decimal point, not a general connector. Letting it
    through meant an anchor at the end of a stem swallowed ".pdf": "lᵣ.pdf"
    became one span while "l_r" did not, the prose either side of the change
    differed, and conformance called a pure typeface change a REWRITE."""

    def test_a_trailing_extension_is_excluded(self):
        assert spans("Norms of diagonal operators in lᵣ.pdf") == ["lᵣ"]
        assert spans("Norms of diagonal operators in l_r.pdf") == ["l_r"]

    def test_both_spellings_leave_the_same_prose(self):
        from maintenance.conformance import _prose_outside_maths
        a = "Norms of diagonal operators in l_r.pdf"
        b = "Norms of diagonal operators in lᵣ.pdf"
        assert _prose_outside_maths(a) == _prose_outside_maths(b)


class TestTheContract:
    @settings(max_examples=400, deadline=None)
    @given(st.text(max_size=120))
    def test_spans_are_sorted_disjoint_and_inside_the_string(self, text):
        n = len(unicodedata.normalize("NFC", text))
        got = find_math_regions(text)
        last = 0
        for s, e in got:
            assert 0 <= s < e <= n, (s, e, n)
            assert s >= last, "overlapping or unsorted"
            last = e

    @settings(max_examples=300, deadline=None)
    @given(st.text(max_size=120))
    def test_never_raises(self, text):
        assert isinstance(find_math_regions(text), list)

    @pytest.mark.parametrize("text", [
        "", " ", ".", "$", "$$", r"\[", "^", "_", "()", "((((", "A" * 4000,
        "\x00", "​", "ℝ" * 500, "→" * 200,
    ])
    def test_pathologies(self, text):
        got = find_math_regions(text)
        assert isinstance(got, list)


class TestWhatItDeliberatelyDoesNot:
    def test_it_cannot_tell_an_acronym_from_initials(self):
        """"P.D.E." and "S.R.S." have the identical shape and only one is
        mathematics. This module answers "not maths" for both, which is right
        for the acronym and a miss for nothing -- initials are the author
        block's problem, not the title's."""
        assert find_math_regions("A P.D.E. approach") == []

    def test_a_bare_decimal_is_not_protected(self):
        """"0.5-Hölder" has no anchor, so no span. Nothing in it needs
        protecting from recasing: the digits have no case and "Hölder" is a
        proper noun handled by the vocabulary."""
        assert find_math_regions("0.5-Hölder continuity") == []
