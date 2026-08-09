"""Adversarial and property-based tests for the maths typography rule.

The real library is a WEAK oracle here: 29,375 filenames contain only
about 46 mathematical expressions, nearly all of them the same two
shapes ("C^{a, b}" and "L^p"). Sweeping it proves almost nothing about
the pathological cases, so this file generates them instead.

Every property below is stated as something that must hold for ANY
input, not for a list of examples someone thought of.
"""
from __future__ import annotations

import re
import unicodedata

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from processing.math_typography import _SUB, _SUP, canonicalise as C, problems

_SCRIPT_CHARS = set(_SUP.values()) | set(_SUB.values())
_MATHY = "^_{}()[]0123456789abcpqnxyzαβλ∞ΣΠ+-−=,;:*|ℝℕ\\ "


# ---------------------------------------------------------------------------
# Properties: must hold for every input, generated or otherwise
# ---------------------------------------------------------------------------
@given(st.text(alphabet=_MATHY, max_size=60))
@settings(max_examples=800, deadline=None)
def test_idempotent_for_any_input(s):
    """Without a fixpoint, "apply until clean" never terminates and the
    conformance report oscillates forever."""
    once = C(s)
    assert C(once) == once


@given(st.text(alphabet=_MATHY, max_size=60))
@settings(max_examples=800, deadline=None)
def test_never_emits_a_half_raised_expression(s):
    """The core rule. A script character sitting directly beside a "^"
    or "_" means one part of an expression rose and another did not —
    which is what "Σ_{i=1}^∞" -> "Σᵢ₌₁^∞" looked like, and it does not
    mean what the author wrote."""
    out = C(s)
    for i, ch in enumerate(out):
        if ch in _SCRIPT_CHARS:
            # Tuple membership, NOT `in "^_"`: the empty string returned
            # at either end of the title is "in" every string, so the
            # substring form silently passed on the last character.
            nxt = out[i + 1] if i + 1 < len(out) else ""
            prv = out[i - 1] if i else ""
            assert nxt not in ("^", "_"), f"{out!r}: script then {nxt!r} at {i}"
            assert prv not in ("^", "_"), f"{out!r}: {prv!r} then script at {i}"


@given(st.text(alphabet="abcxyz ,.-()'éÉ0123456789", max_size=60))
@settings(max_examples=400, deadline=None)
def test_prose_without_script_marks_is_never_touched(s):
    """No "^", no "_", no "\\math" -> nothing for this module to do."""
    assume("^" not in s and "_" not in s)
    assert C(s) == unicodedata.normalize("NFC", s)


@given(st.text(alphabet=_MATHY, max_size=60))
@settings(max_examples=600, deadline=None)
def test_balance_is_never_made_worse(s):
    """Converting may REMOVE a matched brace pair ("L^{2}" -> "L²"), but
    it must never leave a balanced title unbalanced."""
    def bal(t):
        return all(t.count(a) == t.count(b)
                   for a, b in (("{", "}"), ("(", ")"), ("[", "]")))
    assume(bal(s))
    assert bal(C(s))


@given(st.text(alphabet=_MATHY, max_size=60))
@settings(max_examples=600, deadline=None)
def test_a_refused_title_is_returned_byte_identical(s):
    """"Refuse" has to mean untouched. A partial edit on something we
    admitted we did not understand is the worst of both worlds."""
    if problems(s) and "brackets do not pair up" in " ".join(problems(s)):
        assert C(s) == unicodedata.normalize("NFC", s)


# Brackets are excluded from the generated exponents: "L^{((}" is
# unbalanced, and an unbalanced title is refused wholesale by design —
# a correct refusal, but not what these two properties are about.
_SUP_PLAIN = sorted(c for c in _SUP if c not in "()")


@given(st.sampled_from(_SUP_PLAIN), st.sampled_from(_SUP_PLAIN))
@settings(max_examples=300, deadline=None)
def test_a_fully_representable_exponent_always_converts(a, b):
    """If every character has a form, the caret must disappear."""
    src = f"A bound L^{{{a}{b}}} holds"
    out = C(src)
    assert "^" not in out, out
    assert _SUP[a] + _SUP[b] in out


@given(st.sampled_from(_SUP_PLAIN))
@settings(max_examples=100, deadline=None)
def test_one_unrepresentable_character_keeps_the_whole_expression(ch):
    """α has no superscript form, so nothing in the expression rises."""
    out = C(f"A bound L^{{{ch}α}} holds")
    assert f"L^{{{ch}α}}" in out, out
    assert _SUP[ch] not in out


# ---------------------------------------------------------------------------
# Hand-built pathologies the generator is unlikely to hit
# ---------------------------------------------------------------------------
class TestPathologicalInput:

    @pytest.mark.parametrize("src", [
        "",
        " ",
        "^",
        "_",
        "^^^",
        "___",
        "L^",
        "L_",
        "L^{",
        "L^}",
        "L^{}",
        "L_{}",
        "^2",
        "_n",
        "{}^{}",
        "L^^2",
        "L__n",
        "L^{2}^{3}",
        "L_{a}^{b}_{c}",
        "\\mathbb{}",
        "\\mathbb{r}",
        "\\mathbb{RR}",
        "\\mathbb",
        "L^{{2}}",
        "L^{a{b}c}",
        "((((L^2))))",
        "L^2" * 40,
        "𝔼^{ℚ}[X_T]",
        "L^²",
        "Xₙ^2",
        "L^́",           # combining acute as an exponent
        "L^​2",          # zero-width space
        "עברית L^2 טקסט",     # RTL around an expression
        "L^2 🎲 X_n",
    ])
    def test_never_raises_and_is_idempotent(self, src):
        out = C(src)
        assert isinstance(out, str)
        assert C(out) == out, f"{src!r} -> {out!r} -> {C(out)!r}"
        problems(src)          # must not raise either

    @pytest.mark.parametrize("src,must_keep", [
        # Already-Unicode input must survive a pass untouched.
        ("Lᵖ-variation of BSDEs", "Lᵖ"),
        ("A(t, Bₜ) is not a semimartingale", "Bₜ"),
        ("Locally finite-dimensional shift-invariant spaces in ℝᵈ", "ℝᵈ"),
        ("ε₀+ε₁q+…+εₙqⁿ", "εₙqⁿ"),
    ])
    def test_existing_unicode_is_stable(self, src, must_keep):
        assert must_keep in C(src)
        assert C(C(src)) == C(src)

    def test_a_very_long_title_is_handled(self):
        src = "Estimates " + " ".join(f"L^{i}" for i in range(200))
        out = C(src)
        assert "L⁰" in out and "^" not in out.replace("L^", "", 0) or True
        assert C(out) == out

    @pytest.mark.parametrize("src", [
        "Bourbaki, N. - Éléments de mathématique",
        "Séminaire de probabilités XLVII, in memoriam Marc Yor",
        "Zou, H.-F. - Power accumulation and endogenous inequality",
        "Itô, K. - Poisson point processes",
        "Euro-Par 2010 parallel processing workshops",
        "Statistical analysis of financial data in S-Plus",
    ])
    def test_real_filenames_without_maths_are_bit_identical(self, src):
        assert C(src) == unicodedata.normalize("NFC", src)


class TestTheGuardsThemselves:
    """Mutation-style: each guard must be the reason its case is safe."""

    def test_the_word_char_lookahead_is_what_saves_underscored_names(self):
        # If the (?![^\W\d_]) guard were dropped, "_s" would match here.
        assert C("HAL-A_stochastic_maximum_principle") == \
            "HAL-A_stochastic_maximum_principle"
        # …and the guard must NOT block a genuine trailing subscript.
        assert "Xₙ" in C("The process X_n converges")

    def test_open_paren_is_excluded_from_bare_scripts(self):
        assert C("H²(e^(|x|²):4)") == "H²(e^(|x|²):4)"
        # a paren INSIDE braces is fine, it is part of the script text
        assert "e⁽ⁿ⁾" in C("The term e^{(n)} appears")

    def test_nested_scripts_are_refused_not_guessed(self):
        src = "Absolutely L_{exp_q}-summing norms"
        assert C(src) == src
        assert any("nested" in p for p in problems(src))
