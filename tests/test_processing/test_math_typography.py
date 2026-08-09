"""The house convention for mathematics in a title.

Unicode where it exists, LaTeX-like where it doesn't, and — the rule
that matters — all-or-nothing per expression.  Every "must not" below is
a real mangling the sweep produced against the 29k library before the
rule was tightened.
"""
from __future__ import annotations

import pytest

from processing.math_typography import canonicalise as C, problems, verify_maps


def test_the_glyph_maps_are_real_script_characters():
    """Deriving these from Unicode decompositions maps "a" to "ª"
    FEMININE ORDINAL INDICATOR, which is not a superscript at all."""
    assert verify_maps() == []


class TestUnicodeWhereItExists:

    @pytest.mark.parametrize("src,want", [
        ("L^2 estimates in elliptic equations", "L² estimates"),
        ("L^p solutions of one-dimensional BSDEs", "Lᵖ solutions"),
        ("Itô's formula for C^2 functions", "C² functions"),
        ("The process X_n converges", "Xₙ converges"),
        ("Notes on e^{-x} decay", "e⁻ˣ decay"),
        ("Sums Σq^{-n} over the integers", "Σq⁻ⁿ"),
        ("The needle problem in \\mathbb{R}^d", "in ℝᵈ"),
        ("Measures on \\mathbb{N} and \\mathbb{Q}", "on ℕ and ℚ"),
        # already Unicode: unchanged, and a second pass is a no-op
        ("Lᵖ-variation of BSDEs", "Lᵖ-variation"),
    ])
    def test_converted(self, src, want):
        assert want in C(src)


class TestLatexWhereUnicodeCannot:

    @pytest.mark.parametrize("src,want", [
        # no superscript infinity exists
        ("The Kreps–Yan theorem for L^∞", "L^∞"),
        ("H^∞ type optimal control problems", "H^∞"),
        # no superscript comma, and no superscript alpha/lambda
        ("Local C^{0, α} estimates for viscosity solutions", "C^{0,α}"),
        ("Interior C^{2, α} regularity theory", "C^{2,α}"),
        ("Itô's formula for C^{1, λ}-functions", "C^{1,λ}"),
        # representable individually, but the COMMA is not — so the whole
        # expression stays.  Character-by-character gave "C², ¹".
        ("A counterexample to C^{2, 1} regularity", "C^{2,1}"),
        ("W^{2, p} and W^{1, p}-estimates at the boundary", "W^{2,p}"),
        # no superscript q
        ("Estimates in L^q spaces", "L^q"),
        ("Another proof of e^{x:y} being irrational", "e^{x:y}"),
    ])
    def test_kept_as_latex_and_tidied(self, src, want):
        assert want in C(src)

    def test_braces_only_for_multi_character_scripts(self):
        assert C("A bound in L^{2} spaces") == "A bound in L² spaces"
        assert "C^{1,α}" in C("C^{1,α} regularity")

    def test_no_space_inside_the_braces(self):
        assert "C^{1,1}" in C("C^{1, 1} regularity for obstacle problems")


class TestAllOrNothing:
    """A single unrepresentable character keeps the WHOLE expression in
    LaTeX form.  Half-raised output does not mean what the author wrote."""

    def test_a_base_with_both_scripts_is_atomic(self):
        # "^∞" cannot be rendered, so the subscript must not rise either.
        out = C("Characterization of Σ_{i=1}^∞ expansions")
        assert "Σ_{i=1}^∞" in out
        assert "ᵢ" not in out

    def test_partial_conversion_never_happens(self):
        out = C("Local C^{0, α} estimates")
        assert "C⁰" not in out, "only the digit rose; that changes the meaning"


class TestRefusesRatherThanGuesses:

    @pytest.mark.parametrize("src", [
        "On the expansion 1 = Σq^{−n_i}",                    # nested script
        "Absolutely L_{exp_q}-summing norms of diagonal operators",
        "Σ_{i=1}^∞ q^(−n_i} and related problems",           # brackets broken
        "C^{1, β) and W^{2, p} regularity",                  # brackets broken
    ])
    def test_malformed_or_nested_is_left_exactly_alone(self, src):
        assert C(src) == src
        assert problems(src), "and it must be reported, not silently skipped"


class TestProseIsNotMathematics:
    """Each of these was mangled by an earlier version of this module."""

    @pytest.mark.parametrize("src", [
        # "_" as a word separator in a raw download name
        "HAL-A_stochastic_maximum_principle_for_min_max_mean_field",
        "Mean_Field_Control_on_Spaces_of_Measures",
        # a bare "_x" that is really the start of a longer word
        "H₂:H_infty control for continuous-time mean-field systems",
        # "(" opens a group; it is not a one-character exponent
        "Constructive proofs for some semilinear PDEs on H²(e^(|x|²):4, ℝᵈ)",
        # ordinary prose that merely contains letters and digits
        "A note on p-adic numbers and q-series",
        "Optimal control 1 - Lecture 2",
        "Il_2 and the theory of quadratic forms",
        "Séminaire de probabilités XLVII",
    ])
    def test_untouched(self, src):
        assert C(src) == src


class TestIdempotence:
    """The sweep must converge, or "apply until clean" never terminates."""

    @pytest.mark.parametrize("src", [
        "L^2 estimates", "C^{1, α} regularity", "\\mathbb{R}^d spaces",
        "Σ_{i=1}^∞ sums", "L^∞ bounds", "X_n converges",
    ])
    def test_twice_is_the_same_as_once(self, src):
        once = C(src)
        assert C(once) == once


class TestBlackboardBoldIsNotInferred:
    """Measured on the real library: of 30 bare-capital-plus-script
    occurrences, ZERO mean a double-struck letter.  25 are "C^2"/"C^{1,α}"
    — Hölder and differentiability classes, where ℂ would be flatly
    wrong — 3 are C_b (bounded continuous functions), one D^{1,2} is a
    Malliavin space and one H_infty is H-infinity control.

    So the inference is not implemented, and this test exists to stop
    someone adding it later on plausibility alone.
    """

    @pytest.mark.parametrize("src", [
        "Itô's formula for noncommutative C^2 functions of free Itô processes",
        "A total variation version of Breuer–Major CLT under D^{1, 2}",
        "Monetary utility functions on C_b(X) spaces",
        "A new lower bound for the Ramsey numbers R(3, k)",
        "Fractal properties with independent Q^*-digits",
    ])
    def test_a_bare_capital_is_never_promoted(self, src):
        out = C(src)
        assert not (set("ℝℕℤℚℂ𝔼𝔽𝕊𝕋𝔻ℍℙ") & set(out)), out

    def test_an_explicit_mathbb_still_converts(self):
        """The owner writing it explicitly is not a guess."""
        assert "ℝ" in C("Estimates in \\mathbb{R}")
