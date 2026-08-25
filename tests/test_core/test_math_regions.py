"""Which spans of a title are mathematics.

Four implementations preceded this one and all four were wrong. The tests
below are organised around HOW each was wrong, so a regression reintroduces a
named failure rather than an anonymous one.

THE OPERATIONAL DEFINITION, which decides every expectation in this file: a
span is mathematics iff REWRITING ITS CASE OR ITS WORDS WOULD BE WRONG, and it
is notation rather than a word. "L^2" must not become "l^2"; "AR(1)" must not
become "Ar(1)". "(Almost) Everything you always wanted to know" is ordinary
English in brackets and must NOT be protected.

WHAT CHANGED WHEN THE PARSER LANDED, and why the expectations here moved with
it. The scanner it replaced answered ``Γ-convergence`` for
"Γ-convergence of the functional". The parser answers ``Γ``. The difference is
not cosmetic and it is not a tie:

  * MEASURED on the hand-labelled corpus: 53 gold spans over 46 titles have
    the shape ``<span>-<word>`` (α-dimensional, α-stable, β-expansions,
    ε-Nash, Γ-martingales, N-player, ∞-order…) and every single one ends at
    the hyphen. The corpus labels the SYMBOL ALONE, without exception.
  * MEASURED on the scanner's errors over the same corpus: of its 426
    false-positive characters, 335 (79%, over 33 titles) lie in exactly that
    hyphen tail. That is the bulk of the gap between P 0.681 and P 1.000.
  * The file already held the boundary elsewhere:
    ``test_a_bare_decimal_is_not_protected`` accepts that "0.5-Hölder" gets no
    span because the proper noun after the hyphen belongs to the VOCABULARY.
    Protecting the word after "Γ-" but not the word after "0.5-" was the
    inconsistent position.
  * The coverage the wide span was providing by accident is not lost, it is
    replaced by something stronger:
    ``TestTheSymbolIsProtectedAndTheWordSurvives`` asserts the REQUIREMENT
    (the word comes back unchanged from the real casers) rather than the PROXY
    (the word sits inside a maths span).

ONE PROPERTY IS ASSERTED OVER A POPULATION RATHER THAN OVER ARBITRARY TEXT,
and the reason is a measurement, not a preference. "The answer is the same for
NFC and NFD input" is TRUE for titles -- 0 disagreements over the 345 labelled
titles, and 0 over 18 of the 20 hand-built accented probes below -- and FALSE
for arbitrary strings: 1,995 of 6,000 random strings seeded with combining
marks disagree,
because a combining mark hides the letter it sits on and a bare "E" or "s" is
then read as a lone variable. Asserting it with hypothesis over ``st.text()``
would fail. It is therefore asserted where it is true and where it matters --
over the corpus, over an explicit table of accented titles, and through the
two callers that slice raw text -- with a subset ratchet on the two shapes
that still diverge. See :class:`TestTheOffsetFrame`.

Numbers in these docstrings were measured on 2026-08-25 against
tests/fixtures/math_regions_ground_truth.json (345 titles, 201 spans, 1,042
protected characters) and against the module itself; none is quoted from a
document.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
import sys
import time
import unicodedata

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from core import math_regions as _module
from core.math_regions import find_math_regions

_FIXTURE = (pathlib.Path(__file__).resolve().parents[1]
            / "fixtures" / "math_regions_ground_truth.json")


def spans(text):
    """The spans as TEXT, sliced out of the caller's own string.

    Slicing here is not a convenience. ``find_math_regions`` returns offsets
    into the string AS PASSED, and every assertion in this file that uses
    ``spans()`` is therefore also asserting that the offset frame is the
    caller's -- see :class:`TestTheOffsetFrame`.
    """
    return [text[s:e] for s, e in find_math_regions(text)]


@pytest.fixture(scope="module")
def corpus():
    rows = json.loads(_FIXTURE.read_text())["labelled"]
    assert len(rows) == 345, (
        "the corpus changed size; re-read it before trusting anything here"
    )
    return rows


# ═══════════════════════════════════ the module's own expectation table ══
#
# ``core/math_regions.py`` ships ``_CASES``, one line per production and one
# per priced refusal. Until this section existed it executed ONLY under
# ``if __name__ == "__main__":`` -- i.e. never, in CI, in the pre-commit hook
# or in the pre-push suite. That is not a stylistic point.
#
# MEASURED, 2026-08-25, by running the same 89-mutant campaign twice against
# this file, once with these tests deselected: the rest of the suite kills 71
# of 89; with the table it kills 84 of 89. Thirteen mutants are held by
# nothing else, and SIX of those thirteen change a real library title --
# among them the one that lets "κ-gon" claim its English half, the one that
# lets "A(H1N1)" become notation, and the one that gives "a √n window" its
# article. A table that ships beside the code, is revised with the code, and
# is the densest oracle in the repository either side of the corpus was
# contributing nothing to the gate.
#
# It is wired in as one test per case rather than one test for the table so
# that a failure names the title, and so that ``-k`` can select one.

def _table_sections(module, cases):
    """Map each ``_CASES`` index to the ``# ── heading ──`` above it.

    Purely cosmetic -- it makes the test ids group as the table does
    (``positives`` / ``negatives`` / ``grafted`` / ``repairs``). Every step
    is allowed to fail into "no section": a test id is not worth a collection
    error, and the assertions below do not depend on this.
    """
    try:
        src = pathlib.Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:                                   # pragma: no cover
        return {}
    elts = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "_CASES" for t in node.targets):
            elts = getattr(node.value, "elts", None)
    if elts is None or len(elts) != len(cases):          # pragma: no cover
        return {}
    lines = src.splitlines()
    out = {}
    for i, elt in enumerate(elts):
        section = ""
        for ln in range(elt.lineno - 2, -1, -1):
            raw = lines[ln].strip()
            if raw.startswith("# ──"):
                head = re.split(r"[:,]", raw.strip("# ─"))[0]
                words = [w for w in re.split(r"[^0-9A-Za-z]+", head.lower())
                         if w and w != "the"]
                section = words[0] if words else ""
                break
            if raw and not raw.startswith("#"):
                continue
        out[i] = section
    return out


_TABLE = list(getattr(_module, "_CASES", ()))
_SECTIONS = _table_sections(_module, _TABLE) if _TABLE else {}


def _table_ids(cases):
    """A readable, unique, ASCII test id per case.

    The index leads because six titles appear TWICE in the table, deliberately
    (a title that exercises two productions is listed under both), and pytest
    ids must be unique. The title slug follows because the title is the label:
    ``046-negatives-Heston-and-Nandi-2000-closed-form-GARCH`` says what broke
    without opening the file.
    """
    ids = []
    for i, case in enumerate(cases):
        title = case[0] if case and isinstance(case[0], str) else repr(case)
        slug = re.sub(r"[^0-9A-Za-z]+", "-",
                      unicodedata.normalize("NFKD", title)).strip("-")[:44]
        section = _SECTIONS.get(i) or "case"
        ids.append(f"{i:03d}-{section}-{slug or 'blank'}")
    return ids


class TestTheModulesOwnExpectationTable:
    """``_CASES``, run.

    WHY THESE ASSERTIONS AND NOT A REWRITE OF THE TABLE INTO THIS FILE. The
    table is the module's own statement of what its grammar means, one line
    per production, written and revised beside the code it describes. Copying
    it here would create a second copy to drift -- the exact failure mode
    ``docs/rival-implementations.md`` is about. Importing it keeps one rule
    and one implementation, and makes deleting a case from the module a
    visible test deletion.
    """

    def test_the_table_is_present_and_has_not_been_gutted(self):
        """A mutation that empties ``_CASES`` would make every parametrised
        test below vanish silently -- pytest reports zero collected, not a
        failure. This is the guard that turns that into a red test.

        184 is the size measured on 2026-08-25. The floor is deliberately the
        measured size and not a round number: cases are ADDED when a defect is
        repaired, so a drop is always either a deletion or a mutation.
        """
        assert hasattr(_module, "_CASES"), (
            "core.math_regions no longer ships _CASES. It is the only oracle "
            "catching 13 of the 89 mutants this suite was measured against; "
            "if the table moved, wire its new home in here."
        )
        assert len(_TABLE) >= 184, (
            f"_CASES shrank to {len(_TABLE)} entries; it held 184."
        )

    @pytest.mark.parametrize("case", _TABLE, ids=_table_ids(_TABLE))
    def test_case(self, case):
        """One row of the module's expectation table.

        The row IS the reason: each was written when a production was added
        or a defect repaired, and the table's own section comments record
        which. A failure here means the grammar changed meaning.
        """
        title, want = case
        got = [title[s:e] for s, e in find_math_regions(title)]
        assert got == want, (
            f"\n  title: {title!r}\n  want:  {want!r}\n  got:   {got!r}"
        )

    @pytest.mark.parametrize("case", _TABLE, ids=_table_ids(_TABLE))
    def test_every_expectation_is_a_substring_of_its_own_title(self, case):
        """A typo in an expected span can never match, so the case would fail
        for a reason that has nothing to do with the grammar -- and a case
        whose expectation is ``[]`` cannot be distinguished from one whose
        expectation was lost.

        This checks the table is WELL FORMED independently of whether the
        module agrees with it: each expected span must be findable in the
        title, left to right, without overlap. It is the only test here that
        would still be meaningful if ``find_math_regions`` were deleted.
        """
        title, want = case
        assert isinstance(title, str) and isinstance(want, list), case
        at = 0
        for w in want:
            assert isinstance(w, str) and w, f"empty expectation in {title!r}"
            found = title.find(w, at)
            assert found >= 0, (
                f"expected span {w!r} does not occur in {title!r} at or after "
                f"offset {at}; the table has a typo, not the module"
            )
            at = found + len(w)


# ═══════════════════════════════════════════════════════ the four defects ══

class TestAccentedLettersAreNotMathematics:
    """The detector's defect. It claimed 'e-acute' 4,331 times; 3,614 of the
    4,238 titles it flagged (85%) contain no mathematics at all. Downstream,
    conformance asked it which part of a title was prose and was handed
    "Prcis d'analyse relle" -- 15% of titles affected.

    An accented Latin letter is a letter of a natural language. A title
    written entirely in natural-language words yields no protected span,
    whatever alphabet or diacritics it is written in."""

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

    @staticmethod
    def _accented(span):
        for ch in unicodedata.normalize("NFC", span):
            name = unicodedata.name(ch, "")
            if not ch.isascii() and ch.isalpha() and \
                    name.startswith("LATIN") and " WITH " in name:
                return ch
        return None

    def test_the_predicate_is_not_vacuous(self):
        """A population test that cannot fire is worse than no test: it
        reports "fine" for something it never looked at. So the predicate
        the next test uses is checked against a known positive and a known
        negative first."""
        assert self._accented("Théorie") == "é"
        assert self._accented("Précis") == "é"
        assert self._accented("L²") is None
        assert self._accented("AR(1)") is None

    def test_no_span_anywhere_in_the_corpus_contains_an_accented_letter(
            self, corpus):
        """Six sampled titles is a spot check; 345 is a population.

        The defect this class is named for was invisible to spot checks --
        it needed a corpus to see, which is why one exists. MEASURED: 0 of
        the module's spans over the 345 labelled titles contain an accented
        Latin letter. (Accented letters INSIDE a formula would be legitimate;
        the corpus simply contains none, so the floor is zero and any
        appearance is worth looking at by hand rather than assumed wrong.)
        """
        accented = [
            (row["title"], row["title"][s:e], self._accented(row["title"][s:e]))
            for row in corpus
            for s, e in find_math_regions(row["title"])
            if self._accented(row["title"][s:e])
        ]
        assert not accented, accented[:5]


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

    @pytest.mark.parametrize("title", [
        "a - b",
        "x + y is fine",
        "signal + noise",
        "P vs NP",
    ])
    def test_an_operator_between_two_words_is_not_a_region(self, title):
        """Strengthened, because the version this replaces could not see the
        bug it was written for.

        It asserted only that no span is made purely of ASCII letters and
        spaces. MEASURED: on "x + y is fine" and "signal + noise" the scanner
        returned ``['+']`` -- a span whose single character has no case and
        needs no protection whatsoever -- and the old predicate passed it,
        because "+" is neither a letter nor a space. The scanner's own
        docstring admitted the guard "currently fires ZERO times".

        So the expectation is now the strong one: these titles have NO
        regions at all. A span that defends nothing is not a smaller problem
        than a span that defends prose; it is the same problem, because
        ``maintenance.conformance`` diffs the prose OUTSIDE the spans and a
        stray "+" moves the boundary.
        """
        assert find_math_regions(title) == []

    def test_a_span_is_never_a_run_of_ordinary_english(self, corpus):
        """The invariant behind the four titles above, over the corpus.

        Stated so that it stays true where the loose version was vacuous: no
        span longer than one character consists of nothing but ASCII letters
        and spaces. One character is deliberately allowed -- the corpus
        labels bare Latin variables ('N' in "N-player games", 'X' in "les
        filtrations de |X|", 'C', 'p', 'G') as mathematics, and a rule that
        forbade them would contradict the ground truth.

        MEASURED: 0 violations over the 345 labelled titles, 0 over their
        1,042 GOLD characters, 0 over 30,000 randomly fuzzed strings and
        0 over 20,000 hypothesis examples.
        """
        offenders = []
        for row in corpus:
            title = row["title"]
            for s, e in find_math_regions(title):
                span = title[s:e]
                if len(span) > 1 and all(
                        c.isascii() and (c.isalpha() or c.isspace())
                        for c in span):
                    offenders.append((title, span))
        assert not offenders, offenders[:5]

    def test_a_span_is_never_only_operators_and_punctuation(self, corpus):
        """The ``['+']`` pathology as a population-level invariant.

        A span drawn only from the ASCII binary-operator and punctuation
        characters carries no case and no word: there is nothing in it a
        caser could get wrong. Brackets, "^" and "_" are excluded from the
        forbidden set on purpose -- "(*)^+" is a real axiom name and a real
        gold span in this corpus, and it is made entirely of punctuation.

        MEASURED: 0 violations over the module's corpus spans, 0 over the
        gold spans, 0 over 30,000 fuzzed strings.
        """
        forbidden = set("+-*/=<>&|~ ,;:.!?\t\n")
        # not vacuous: the pathology it names must satisfy the predicate,
        # and the legitimate all-punctuation gold span must not
        assert all(c in forbidden for c in "+")
        assert not all(c in forbidden for c in "(*)^+")
        offenders = []
        for row in corpus:
            title = row["title"]
            for s, e in find_math_regions(title):
                if all(c in forbidden for c in title[s:e]):
                    offenders.append((title, title[s:e]))
        assert not offenders, offenders[:5]


# ═════════════════════════════════════════════════ what IS mathematics ══

class TestUnicodeMathematicsIsFound:
    """What the library actually contains: no LaTeX at all, ~800 mathematical
    characters across 25,049 titles, written in Unicode."""

    @pytest.mark.parametrize("title,expected", [
        ("L² and H¹ estimates", ["L²", "H¹"]),
        ("Lᵖ estimates", ["Lᵖ"]),
        ("Bₜ martingales", ["Bₜ"]),
        ("Filtering and ⅓ power law", ["⅓"]),
        ("Small-time asymptotics as H→0", ["H→0"]),
    ])
    def test_found(self, title, expected):
        """A character that exists only for mathematics is always protected,
        and the span covers exactly the notation attached to it -- the base
        letter and its scripts -- and nothing beyond."""
        assert spans(title) == expected

    @pytest.mark.parametrize("title,expected", [
        ("Γ-convergence of the functional", ["Γ"]),
        ("The ∂-Neumann problem on ℂⁿ", ["∂", "ℂⁿ"]),
        ("σ-algebras and π-systems", ["σ", "π"]),
        ("α-stable Lévy processes", ["α"]),
        ("Δ-hedged gains and the market volatility risk premium", ["Δ"]),
    ])
    def test_the_symbol_is_the_span_not_the_word_hyphenated_to_it(
            self, title, expected):
        """CHANGED EXPECTATION. The scanner answered "Γ-convergence"; the
        parser answers "Γ". See the module docstring for the three
        measurements that decided it.

        The exact list matters in both directions and each element is a
        distinct regression this pins:

          * ``["Γ"]`` and not ``[]``       -- the symbol is still protected.
          * ``["Γ"]`` and not ``["Γ-"]``   -- the hyphen has no case and is
            not swallowed; a span ending on a dangling operator is the
            pathology ``test_no_span_ends_on_a_dangling_operator`` names.
          * ``["∂", "ℂⁿ"]`` -- TWO spans. "Neumann" is the hardest case for
            this convention because it is a proper noun and IS reachable by
            the caser; ``TestTheSymbolIsProtectedAndTheWordSurvives``
            measures what actually happens to it. Do not let the "ℂⁿ" half
            regress while attention is on the "∂" half.
          * ``["σ", "π"]`` -- TWO spans, not one. A merge across " and "
            would be ``test_but_not_across_prose`` failing in disguise.
        """
        assert spans(title) == expected

    @pytest.mark.parametrize("title,expected", [
        # the subscript letters live in three different Unicode blocks, which
        # is why the rule asks Unicode for the NAME rather than the block
        ("lᵣ spaces", ["lᵣ"]),       # U+1D63 Phonetic Extensions
        ("εᵢ convergence", ["εᵢ"]),  # U+1D62 Phonetic Extensions
        ("Bₜ paths", ["Bₜ"]),        # U+209C Superscripts and Subscripts
    ])
    def test_subscripts_from_any_block(self, title, expected):
        """A past bug, encoded: whether a character is a sub/superscript is
        decided by asking Unicode for its NAME, never by testing its block."""
        assert spans(title) == expected


class TestTheSymbolIsProtectedAndTheWordSurvives:
    """The replacement for coverage the wide span was providing by accident.

    When the span shrank from "Γ-convergence" to "Γ", the question that
    matters is not "is the word still inside a maths region" but "does the
    word still come back unchanged from the casers". This class asserts the
    requirement instead of the proxy, which is strictly stronger: it would
    catch a vocabulary regression that a span-shape assertion cannot see.

    TWO CASERS, AND THEY ARE NOT THE SAME PATH -- this was measured, not
    assumed:

      * ``core.sentence_case.to_sentence_case_academic`` DOES consume this
        module, through ``core.math_tokenization.robust_tokenize_with_math``.
        It is the live end-to-end consumer, so it is the real delegation
        test.
      * ``processing.title_normalize.propose_title_case`` does NOT. MEASURED
        by replacing ``find_math_regions`` with a stub claiming 100% of every
        title: its output on these titles was byte-identical. That is worth
        stating plainly, because it is the reason narrowing the span costs
        nothing on the filing path -- the caser that proposes renames never
        asked this module about "convergence" in the first place.
    """

    TITLES = [
        "Γ-convergence of the functional",
        "α-stable Lévy processes",
        "The ∂-Neumann problem on ℂⁿ",
        "Δ-hedged gains and the market volatility risk premium",
        "σ-algebras and π-systems",
        "L²-hedging strategies",
        "ε-Nash equilibria for mean-field games",
        "C^∞-regularization of the heat semigroup",
    ]

    @pytest.mark.parametrize("title", TITLES)
    def test_the_live_consumer_leaves_the_title_alone(self, title):
        """``to_sentence_case_academic`` reads this module's regions.

        With the span narrowed to the symbol, the tokeniser hands the caser
        ``MATH 'Γ'``, ``PUNCT '-'``, ``WORD 'convergence'`` -- and the word,
        unprotected, comes back unchanged anyway. That is the whole argument
        for the narrow convention, executed rather than asserted.
        """
        from core.sentence_case import to_sentence_case_academic
        result, _ = to_sentence_case_academic(title)
        assert result == title

    @pytest.mark.parametrize("title", TITLES)
    def test_the_filing_caser_leaves_the_title_alone_and_stays_confident(
            self, title):
        """The caser that proposes real renames.

        Two assertions, because they fail differently. ``proposed == title``
        catches a rewrite. ``uncertain == []`` catches the quieter failure:
        a word that survives only by being parked in the review bucket makes
        the owner adjudicate 25,049 titles by hand. "Neumann" is the case to
        watch -- it is Xxxx-shaped and mid-title, so it is reachable, and it
        is preserved because it is not provably common, exactly the
        vocabulary delegation this file endorses for "Hölder".
        """
        from processing.title_normalize import propose_title_case
        proposal = propose_title_case(title)
        assert proposal.proposed == title
        assert proposal.uncertain == []


class TestNotationalShapes:
    @pytest.mark.parametrize("title,expected", [
        ("A C^{0,1}-functional Itô's formula", ["C^{0,1}"]),
        ("L^2 estimates", ["L^2"]),
        ("X_t is adapted", ["X_t"]),
        ("SL(2, ℤ) representations", ["SL(2, ℤ)"]),
        ("AR(1) processes", ["AR(1)"]),
    ])
    def test_found(self, title, expected):
        """ASCII-only notation is protected on SHAPE alone, with no
        non-ASCII character anywhere: brace scripts, caret, underscore, a
        called bracket, and a caps head glued to a numeric argument. "AR(1)"
        is the module's headline example -- it must not become "Ar(1)", and
        it must not become "AR(one)" either, which ingest once wrote."""
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
        """Positive evidence comes from the GLUING plus the argument SHAPE,
        not from the contents looking mathematical. Guard against
        re-introducing the "demand a digit inside" rule."""
        assert spans(title) == expected

    @pytest.mark.parametrize("title", [
        "(Almost) Everything you wanted",     # no identifier before the bracket
        "Dupire (1994) revisited",            # a space before the bracket
        "The part(one) of it",                # a real word inside
        "See note(also) below",
        "Heston (2008) and the smile",        # a space, and a year
        "J. Finance 155(3) 2011",             # volume(issue) -- glued, but a
                                              # bare number drags in nothing
        "Report(final) of the committee",
        "See figure(two) for details",
    ])
    def test_a_bracket_holding_prose_is_left_alone(self, title):
        """Brackets alone NEVER confer protection.

        What separates "AR(1)" from "(Almost) Everything" is (i) an
        identifier flush against the opening bracket and (ii) contents that
        are not a real word. Both conditions are load-bearing: "(Almost)"
        fails (i), "part(one)" fails (ii), and "155(3)" -- a journal volume
        and issue -- fails because a bare number is not an identifier, which
        is the specific lenience that had to be withdrawn.
        """
        assert find_math_regions(title) == []


class TestABracketNeverAbsorbsAnEnglishWord:
    """Defect (c) of the parser as it was first written, now fixed.

    A "glued" flag in the bracket helper was computed AFTER a whitespace skip
    and compared against the whitespace token, so it was a tautology. A
    bracket could then absorb a short English word: "(σ, bmo)" returned
    ``['σ, bmo']`` while "(σ, BMO)" returned ``['σ']``. It never fired on a
    real library title, but it is a live hole in the principle the whole
    design rests on -- and it made the module's answer depend on the CASE of
    the very text it exists to protect from recasing.

    This class is the nearest neighbour of
    ``test_a_bracket_holding_prose_is_left_alone``; those four titles could
    not catch it because none of them has a mathematical symbol before the
    comma.
    """

    @pytest.mark.parametrize("title,expected", [
        ("(σ, bmo)", ["σ"]),
        ("(σ, BMO)", ["σ"]),
        ("(H¹, bmo)", ["H¹"]),
        ("(H¹, BMO)", ["H¹"]),
        ("(h1, bmo)", []),
        ("(H1, BMO)", []),
    ])
    def test_the_word_stays_outside(self, title, expected):
        assert spans(title) == expected

    @pytest.mark.parametrize("title,expected", [
        ("α = the answer", ["α"]),
        ("H¹ ∈ the class", ["H¹"]),
        ("Σ ⋅ the sum over i", ["Σ"]),
        ("Bounds when n ≤ the sample size", []),
        ("√n window for the case", ["√n"]),
        # the contrast, so the fix cannot be "refuse relations entirely":
        # when BOTH operands are notational the relation is still joined
        ("Bounds when n ≤ N holds", ["n ≤ N"]),
        ("Extrapolation on Hˢ, 0<s≤1 spaces", ["Hˢ, 0<s≤1"]),
    ])
    def test_it_fires_outside_brackets_too(self, title, expected):
        """The same hole, reached through a relation rather than a bracket.

        MEASURED on the unrepaired parser: "α = the answer" gave
        ``['α = the']`` and "H¹ ∈ the class" gave ``['H¹ ∈ the']`` -- both a
        dangling operator AND a claimed English word in one span.

        The last two cases are the counterweight. A relation whose two
        operands are both notational is what separates "0<d<2" from
        "slides + discussion", and it is the evidence rule the repair must
        not have thrown away while closing the hole.
        """
        assert spans(title) == expected


class TestTheVerdictDoesNotDependOnCase:
    """A module whose only job is to say what must not be RECASED cannot
    give a different answer depending on the case it is handed. That is not
    a style preference; it is a self-referential contradiction, and it is
    the general form of defect (c).

    SCOPE, stated because the naive version of this property is false: the
    case that varies must be that of a NON-NOTATIONAL word. Varying the case
    of the notational HEAD legitimately changes the answer -- see
    ``test_a_capitalised_head_is_evidence_and_that_is_deliberate``.
    """

    @pytest.mark.parametrize("variants", [
        ("(σ, bmo)", "(σ, BMO)", "(σ, Bmo)"),
        ("(H¹, bmo)", "(H¹, BMO)", "(H¹, Bmo)"),
        ("α = the answer", "α = THE answer", "α = The answer"),
        ("H¹ ∈ the class", "H¹ ∈ THE class", "H¹ ∈ The class"),
        ("Bₜ martingale", "Bₜ MARTINGALE", "Bₜ Martingale"),
        ("X_t is adapted", "X_t IS adapted", "X_t Is adapted"),
        ("(Ω, ℱ, ℙ) and bmo", "(Ω, ℱ, ℙ) and BMO", "(Ω, ℱ, ℙ) and Bmo"),
        ("AR(1) processes", "AR(1) PROCESSES", "AR(1) Processes"),
        ("The part(one) of it", "The part(ONE) of it", "The part(One) of it"),
        ("L² and bmo spaces", "L² and BMO spaces", "L² and Bmo spaces"),
        ("√n window for the case", "√n window for THE case",
         "√n window for The case"),
        ("∫ the integral", "∫ THE integral", "∫ The integral"),
    ])
    def test_span_positions_are_identical(self, variants):
        """POSITIONS, not span text -- the variants differ in their own
        characters, so comparing sliced strings would be trivially true.
        Identical ``(start, end)`` pairs is the real claim."""
        answers = {v: find_math_regions(v) for v in variants}
        assert len(set(map(tuple, answers.values()))) == 1, answers

    def test_a_capitalised_head_is_evidence_and_that_is_deliberate(self):
        """The one asymmetry that is correct, pinned so nobody "fixes" it.

        "AR(1)" is notation; "ar(1)" is not. Here the capitalisation IS the
        evidence -- a caps head glued to an argument list is what separates
        an autoregressive model from a lowercase word followed by a bracket.
        This is a property of the HEAD, not of a neighbouring English word,
        so it does not contradict the class above.
        """
        assert spans("AR(1) processes") == ["AR(1)"]
        assert find_math_regions("ar(1) processes") == []

    def test_the_one_context_where_case_still_decides(self):
        """A DECLARED PRICE, not a virtue. Read before changing.

        The parser has a short-word escape that lets an operand follow an
        operator with no whitespace at all; the module's docstring names one
        real library title that needs it ("∫₀^∞ sin(x):xdx"). MEASURED consequence: "Σ⋅the" is claimed whole,
        "Σ⋅THE" and "Σ⋅The" are not. English does not glue a word to an
        operator, so the shape is not reachable by prose, and every SPACED
        form is refused -- ``test_it_fires_outside_brackets_too`` covers
        those.

        If this test ever fails because "Σ⋅the" now returns ``['Σ']``, that
        is an IMPROVEMENT: delete the test, do not restore the behaviour.
        """
        assert spans("Σ⋅the") == ["Σ⋅the"]
        assert spans("Σ⋅THE") == ["Σ"]
        assert spans("Σ⋅The") == ["Σ"]


# ═══════════════════════════════════════════════════ extent and joining ══

class TestOneExpressionMayContainSpaces:
    """50 real spans depend on this: an expression broken by a space is still
    one expression, and prose is never a span, so nothing but mathematics can
    be joined."""

    @pytest.mark.parametrize("title,expected", [
        ("A bipolar theorem for L⁰_+(Ω, ℱ, ℙ)", ["L⁰_+(Ω, ℱ, ℙ)"]),
        ("Extrapolation on Hˢ, 0<s≤1 spaces", ["Hˢ, 0<s≤1"]),
    ])
    def test_joined(self, title, expected):
        assert spans(title) == expected

    @pytest.mark.parametrize("title,expected", [
        ("A variant on (2Jₛ-Rₛ, s≥0) for processes", ["2Jₛ-Rₛ, s≥0"]),
        ("A variant on (2Jₛ−Rₛ, s≥0) for processes", ["2Jₛ−Rₛ, s≥0"]),
    ])
    def test_a_hyphen_inside_an_expression_does_not_split_it(
            self, title, expected):
        """Two changes here, both deliberate.

        (1) The subtraction is written with ASCII HYPHEN-MINUS. The parser as
        first written had no U+002D in its operator tables, so it returned
        TWO spans ``['2Jₛ', 'Rₛ, s≥0']`` for this title and ONE span for the
        U+2212 spelling -- the same mathematics decomposing two ways. That is
        the co-variance contract broken, which is why
        ``TestTwoSpellingsDecomposeAlike`` now tests it as a table instead of
        as one hard-coded pair. MEASURED across 5 hyphen/minus pairs: the
        unrepaired parser gave a different span COUNT on 4 of them.

        (2) The expected value no longer keeps the enclosing brackets. The
        old expectation ``['(2Jₛ-Rₛ, s≥0)']`` contradicted the corpus
        convention it was scored against -- see
        ``TestEnclosingBracketsAreTrimmed`` -- and MEASURED, 0 of the 201
        gold spans keep an enclosing bracket.
        """
        assert spans(title) == expected

    def test_but_not_across_prose(self):
        """The necessary counterweight to test_joined: "L² and H¹" is two
        expressions with a word between them, not one.

        Re-run this deliberately after ANY loosening of the joining rules.
        Widening the operator table to fix the hyphen split above is exactly
        the kind of change that would bridge a word here.
        """
        assert spans("L² and H¹ estimates") == ["L²", "H¹"]
        assert spans("L² and BMO and H¹ spaces") == ["L²", "H¹"]


class TestEnclosingBracketsAreTrimmed:
    """The corpus convention, pinned rather than discovered.

    The fixture README states it: enclosing brackets are trimmed unless a
    matching opener sits inside, so "(Aₚ) condition" gives "Aₚ" but "AR(1)"
    gives "AR(1)". Nothing tested it, and one expected value in this file
    contradicted it. MEASURED: 0 of the 201 gold spans and 0 of the module's
    345-title spans start with an opening bracket and end with its matching
    closer.
    """

    @pytest.mark.parametrize("title,expected", [
        # trimmed: the bracket merely encloses
        ("Muckenhoupt's (Aₚ) condition and the optimal measure", ["Aₚ"]),
        ("Characterization of submartingales of a new class (Σʳ)", ["Σʳ"]),
        ("An {l₁, l₂, l_∞}-regularization approach", ["l₁, l₂, l_∞"]),
        ("(Ω, ℱ, ℙ) and BMO", ["Ω, ℱ, ℙ"]),
        # kept: a matching opener sits inside, or the bracket is glued to a head
        ("A bipolar theorem for L⁰_+(Ω, ℱ, ℙ)", ["L⁰_+(Ω, ℱ, ℙ)"]),
        ("AR(1) processes", ["AR(1)"]),
        ("The equivalence of axiom (*)^+ and axiom (*)^{++}",
         ["(*)^+", "(*)^{++}"]),
    ])
    def test_the_convention(self, title, expected):
        assert spans(title) == expected

    def test_no_corpus_span_keeps_its_enclosing_bracket(self, corpus):
        closer = {"(": ")", "[": "]", "{": "}"}

        def encloses(span):
            return len(span) >= 2 and span[0] in closer and \
                span[-1] == closer[span[0]]

        # not vacuous, and the exceptions the convention names still pass
        assert encloses("(Ap)") and encloses("{x}")
        assert not encloses("AR(1)") and not encloses("(*)^+")
        offenders = []
        for row in corpus:
            title = row["title"]
            for s, e in find_math_regions(title):
                if encloses(title[s:e]):
                    offenders.append((title, title[s:e]))
        assert not offenders, offenders[:5]


class TestNoSpanEndsOnADanglingOperator:
    """Untested until now, and the scanner violated it routinely.

    MEASURED on the scanner: "σ + noise" gave ``['σ +']``, "α = the answer"
    gave ``['α =']``, "H¹ ∈ the class" gave ``['H¹ ∈']``, "X⁺, lorsque" gave
    ``['X⁺,']``. An operator with no operand after it protects nothing and
    moves the prose boundary that ``maintenance.conformance`` diffs.

    NOT asserted as a fuzz property, deliberately: a superscript run can
    legitimately end in "+", as the corpus's own "(*)^+" does, and random
    strings reach shapes like "1^0+" where the reading is genuinely
    ambiguous. The property is asserted where it is decidable -- over the
    corpus and over the four measured pathologies.
    """

    _PUNCT = set(",;:")
    _OPS = set("+-−*/=<>≤≥≠∈∋⊂⊃⊆⊇·⋅×÷±∓~&|")

    @classmethod
    def _dangling(cls, span):
        if span[-1] in cls._PUNCT:
            return True
        return span[-1] in cls._OPS and not (
            len(span) >= 2 and span[-2] in "^_{")

    @pytest.mark.parametrize("title,expected", [
        ("σ + noise", ["σ"]),
        ("α = the answer", ["α"]),
        ("H¹ ∈ the class", ["H¹"]),
        # a real corpus title; the scanner returned 'X⁺,' with the comma
        ("Les filtrations de |X| et X⁺, lorsque X est une semi-martingale "
         "continue", ["X", "X⁺", "X"]),
    ])
    def test_the_four_measured_pathologies(self, title, expected):
        assert spans(title) == expected

    def test_the_predicate_is_not_vacuous(self):
        """The four measured pathologies must satisfy it and the legitimate
        superscript-plus must not, or the two population tests below report
        "fine" about something they never looked at."""
        assert self._dangling("σ +")
        assert self._dangling("α =")
        assert self._dangling("H¹ ∈")
        assert self._dangling("X⁺,")
        assert not self._dangling("(*)^+")
        assert not self._dangling("L²")

    def test_no_corpus_span_dangles(self, corpus):
        offenders = [
            (row["title"], row["title"][s:e])
            for row in corpus
            for s, e in find_math_regions(row["title"])
            if self._dangling(row["title"][s:e])
        ]
        assert not offenders, offenders[:5]

    def test_the_gold_labels_obey_the_same_rule(self, corpus):
        """A convention the corpus itself does not follow is not a
        convention. Asserted so the two cannot drift apart silently."""
        offenders = [
            (row["title"], row["title"][s:e])
            for row in corpus
            for s, e in row["math_spans"]
            if self._dangling(row["title"][s:e])
        ]
        assert not offenders, offenders[:5]


# ═══════════════════════════════════════════════════════════════ LaTeX ══

class TestLatexIsStillUnderstood:
    """The library has none, and it is still supported. That is a decision,
    not an oversight, and it was measured from both ends.

    The module's own measurement, recorded in its docstring: 0 of the 25,049
    unique reliable library titles contain a "$", a backslash or a
    "\\begin{". But this function is read by CODE, not by the
    library, and two of its readers are live on the filing path --
    ``validators/filename_checker/core.py`` calls it directly, and
    ``core/sentence_case.py`` reaches ``core/math_tokenization.py``, whose
    contract is ONE MATH TOKEN PER FORMULA. The titles those readers see come
    from ``processing/ingest.py``, i.e. from arXiv and Crossref, which are
    LaTeX sources; ``ingest._unlatex`` converts accent commands and a small
    special-character table only, so "$", "\\alpha" and "\\[" pass through it
    untouched.

    A delimited formula is therefore ONE region INCLUDING ITS DELIMITERS.
    Parsing the payload and leaving the delimiters outside is worse than
    refusing outright: MEASURED on the parser before this phase existed,
    "\\[f(x) = x^2\\]" gave one span "f(x) = x^2" and spilled "\\", "[" and
    "]" into the prose stream a caser may rewrite, and
    "\\begin{equation} E = mc^2 \\end{equation}" gave "mc^2" and dropped
    "E = " into prose. Dropping delimiter support altogether returned the
    Black-Scholes equation as six spans instead of one.
    """

    @pytest.mark.parametrize("text,expected", [
        (r"Equation: \[f(x) = x^2\] shown", r"\[f(x) = x^2\]"),
        (r"Inline \(f(x) = x^2\) shown", r"\(f(x) = x^2\)"),
        (r"Env \begin{equation}x=1\end{equation} shown",
         r"\begin{equation}x=1\end{equation}"),
        (r"\begin{align} a &= b \end{align}",
         r"\begin{align} a &= b \end{align}"),
        (r"A \mathbb{R}^n bound", r"\mathbb{R}^n"),
        (r"The \alpha_i coefficients", r"\alpha_i"),
        ("$x+y$", "$x+y$"),
        ("$$E = mc^2$$", "$$E = mc^2$$"),
        (r"$\alpha \leq \beta$", r"$\alpha \leq \beta$"),
    ])
    def test_one_span_including_the_delimiters(self, text, expected):
        """Every delimiter form is a separate case because the failure was
        uniform -- all three backslash forms broke the same way, and a
        partial fix would otherwise pass on the one form that was tested.

        "$x+y$" is here because it is the total miss the long test cannot
        reveal: MEASURED on the unrepaired parser it returned ``[]``, nothing
        at all, while the ~90-character formula below returned two spans.
        Same root cause, two very different symptoms.
        """
        assert spans(text) == [expected]

    def test_inline_dollars_of_realistic_length(self):
        """No length cutoff shorter than a real formula.

        An earlier 80-character bound silently split the Black-Scholes
        equation into SIX spans. MEASURED on the unrepaired parser: the same
        string gave two spans, ``['frac{1}{2}', 'sigma^2 S^2']``, leaving
        "partial V", "partial t" and "= rV" in the prose residue where a
        caser can reach them.
        """
        t = (r"The Black-Scholes formula $\frac{\partial V}{\partial t} + "
             r"\frac{1}{2}\sigma^2 S^2 = rV$ is fundamental.")
        got = spans(t)
        assert len(got) == 1, got
        assert got[0].startswith("$") and got[0].endswith("$")

    def test_the_whole_black_scholes_equation_is_one_span(self):
        """The 62-character formula above is shorter than the bound that
        caused the incident, so it cannot detect its return. This one is 134
        characters and is the equation as actually written."""
        t = (r"$\frac{\partial V}{\partial t} + \frac{1}{2}\sigma^2 S^2"
             r"\frac{\partial^2 V}{\partial S^2} + rS\frac{\partial V}"
             r"{\partial S} - rV = 0$")
        got = spans(t)
        assert len(got) == 1, got
        assert len(got[0]) > 80, "an 80-character bound is back"
        assert got[0] == t

    def test_two_formulas_are_two_spans(self):
        """Not one span running from the first "$" to the last."""
        assert spans(r"$2 \times 2$ and $3 \times 3$") == [
            r"$2 \times 2$", r"$3 \times 3$"]

    def test_the_payload_is_invisible_to_the_grammar(self):
        """A formula's interior must not be evidence about anything outside
        it.

        The region is masked out before the ordinary grammar runs. Without
        that mask the parser's Echo rule read "x" out of the payload of
        "The $x_i$ of x" and then claimed the bare "x" of the PROSE -- a
        reachable branch, found by search after the corresponding mutant
        survived. One span, not two.
        """
        assert spans("The $x_i$ of x") == ["$x_i$"]
        assert spans(r"The \[x_i\] of x") == [r"\[x_i\]"]

    @pytest.mark.parametrize("title", [
        "The $5 trillion question and the $100 answer",
        "A $100 bill and a $50 note",
        "$5",
    ])
    def test_money_is_not_mathematics(self, title):
        """"$" is the one delimiter with a competing reading, and this is a
        mathematical FINANCE library. A dollar pair whose payload reads as
        two or more ordinary English words is refused. The backslash forms
        have no competing reading and carry no such guard.
        """
        assert find_math_regions(title) == []


# ══════════════════════════════════════════ spelling and normalisation ══

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


class TestTwoSpellingsDecomposeAlike:
    """CO-VARIANCE, the single most important property in this file, and
    until now it was defended by exactly ONE hard-coded pair.

    ``maintenance.conformance`` runs this module on the old title and the new
    title separately and compares the PROSE RESIDUES to decide whether a
    rewrite was confined to mathematics. If two spellings of one expression
    decompose differently, a pure typeface change is reported as a REWRITE --
    conformance's loudest bucket, and the reason the lᵣ/l_r pair was
    hard-coded here in the first place.

    Defect (a) of the parser was this same property broken for a pair that
    was not in the table: ASCII hyphen-minus versus U+2212. The one-example
    test could not see it. A table can.
    """

    #: Equivalent spellings that must decompose the same way. The two
    #: strings differ by exactly one substituted character or by spacing.
    PAIRS = [
        ("Norms of diagonal operators in lᵣ.pdf",
         "Norms of diagonal operators in l_r.pdf"),
        ("A variant on (2Jₛ-Rₛ, s≥0) for processes",
         "A variant on (2Jₛ−Rₛ, s≥0) for processes"),
        ("x²-y² identity", "x²−y² identity"),
        ("α-β estimates", "α−β estimates"),
        ("Bounds for 0<d<2 processes", "Bounds for 0 < d < 2 processes"),
        ("L² and H¹ estimates", "L^2 and H^1 estimates"),
        ("An l₁ regularization", "An l_1 regularization"),
    ]

    @pytest.mark.parametrize("a,b", PAIRS)
    def test_same_number_of_spans(self, a, b):
        """The span COUNT is the coarse half of the property and the half
        that broke: MEASURED, the unrepaired parser gave two spans for the
        hyphen spelling of "2Jₛ-Rₛ, s≥0" and one for the U+2212 spelling."""
        ra, rb = find_math_regions(a), find_math_regions(b)
        assert len(ra) == len(rb), (a, [a[s:e] for s, e in ra],
                                    b, [b[s:e] for s, e in rb])

    @pytest.mark.parametrize("a,b", PAIRS)
    def test_the_prose_residue_is_the_same(self, a, b):
        """The fine half, and the one conformance actually reads.

        The residues must be identical once the substituted characters are
        accounted for -- which, for every pair here, means identical outright,
        because the character that differs is INSIDE the mathematics.
        """
        from maintenance.conformance import _prose_outside_maths
        assert _prose_outside_maths(a) == _prose_outside_maths(b)

    def test_the_one_documented_divergence(self):
        """A DECLARED PRICE. Read before changing.

        U+002D is a LINK in the grammar but never EVIDENCE, because meeting
        one proves nothing -- "1105-1123" and "Mean-field" are prose. U+2212
        is both, because English never writes U+2212. So a chain of bare
        alphanumerics joined only by a hyphen carries no evidence at all:
        "2M-X" gets no span, exactly as "2M+X" gets none, while "2M−X" gets
        one. The module's docstring records 4 library titles affected.

        Making "-" evidence was tried and measured by the module's author: it
        gains 5 genuine spans and costs 8 over-claims, because "min", "max",
        "sup", "inf" and "rank" are operator names -- "min-max control",
        "Rank-2 swaption formulae" and "SARS-CoV-2" all start claiming their
        English half.
        That unguarded reading is how the scanner came to claim 186 of the
        189 characters of an English sentence.

        If this test fails because both spellings now return one span, check
        the corpus precision before celebrating -- and update the test rather
        than the module if precision held.
        """
        assert find_math_regions("2M-X bounds") == []
        assert spans("2M−X bounds") == ["2M−X"]


class TestTheOffsetFrame:
    """THE HIGHEST-VALUE TEST IN THIS FILE, and it is new.

    Nothing pinned whether the returned offsets index the caller's string or
    an internally NFC-normalised copy, and the two implementations answered
    DIFFERENTLY. The old contract test hid it: it computed
    ``n = len(unicodedata.normalize("NFC", text))`` and asserted ``e <= n``,
    bounding the offsets against a string the caller never passed. It went
    green only because ``st.text(max_size=120)`` essentially never generates
    a decomposable combining sequence -- a pass-by-accident.

    Which frame is right is not a tie. CLAUDE.md non-negotiable #8 is that
    macOS hands back NFD, ``validators/filename_checker/core.py`` passes a
    raw filename stem straight in, and ``maintenance/conformance.py`` passes
    a title straight in. MEASURED on NFD input under the scanner, over 20
    realistic accented titles: 12 disagreed with their NFC twin, and the
    spans it returned were garbage -- "Précis L²" gave ``[' L']``, "Étude de
    σ" gave ``[' ']``, "Économétrie de la finance L²" gave ``['e ']``.
    ``mask_math_regions`` then masked the wrong characters and left the
    mathematics exposed; ``_prose_outside_maths`` put the mathematics INTO
    the prose.

    The frame is now stated in the module docstring, because two live callers
    slice raw text with these offsets.
    """

    ACCENTED = [
        "Précis d'analyse réelle L²",
        "Théorie de Bₜ",
        "Itô's L^2 formula",
        "Économétrie X_t",
        "Analyse réelle L²",
        "Sur les inégalités de Sobolev L²",
        "À propos de L²",
        "Étude de σ",
        "Über L²",
        "Kalkül L²",
        "Lévy L²",
        "L² à la Itô",
    ]

    @pytest.mark.parametrize("title", ACCENTED)
    def test_the_offsets_index_the_string_as_passed(self, title):
        """Both spellings, sliced with their own offsets, must yield the same
        mathematics. This is the assertion the old ``e <= len(NFC(text))``
        bound could not make."""
        nfc = unicodedata.normalize("NFC", title)
        nfd = unicodedata.normalize("NFD", title)
        assert nfc != nfd, "pick a title that actually decomposes"
        got_nfc = [unicodedata.normalize("NFC", nfc[s:e])
                   for s, e in find_math_regions(nfc)]
        got_nfd = [unicodedata.normalize("NFC", nfd[s:e])
                   for s, e in find_math_regions(nfd)]
        assert got_nfc == got_nfd, (got_nfc, got_nfd)
        for s, e in find_math_regions(nfd):
            assert 0 <= s < e <= len(nfd), (s, e, len(nfd))

    def test_the_whole_corpus_answers_nfd_the_same_as_nfc(self, corpus):
        """345 titles, not 12. MEASURED: 0 disagreements."""
        bad = []
        for row in corpus:
            nfc = unicodedata.normalize("NFC", row["title"])
            nfd = unicodedata.normalize("NFD", row["title"])
            a = [unicodedata.normalize("NFC", nfc[s:e])
                 for s, e in find_math_regions(nfc)]
            b = [unicodedata.normalize("NFC", nfd[s:e])
                 for s, e in find_math_regions(nfd)]
            if a != b:
                bad.append((row["title"], a, b))
        assert not bad, bad[:5]

    def test_the_two_callers_that_slice_raw_text_agree_across_forms(
            self, corpus):
        """The damage was never in this function; it was in what the callers
        did with a bad offset. So assert it where it hurt.

        ``core.tokenization.mask_math_regions`` and
        ``maintenance.conformance._prose_outside_maths`` are the two that
        slice with these offsets. MEASURED: 0 disagreements over the 345
        titles in either function.
        """
        from core.tokenization import mask_math_regions
        from maintenance.conformance import _prose_outside_maths
        n = lambda s: unicodedata.normalize("NFC", s)  # noqa: E731
        bad_mask, bad_prose = [], []
        for row in corpus:
            nfc = n(row["title"])
            nfd = unicodedata.normalize("NFD", row["title"])
            if n(mask_math_regions(nfd)) != n(mask_math_regions(nfc)):
                bad_mask.append(row["title"])
            if n(_prose_outside_maths(nfd)) != n(_prose_outside_maths(nfc)):
                bad_prose.append(row["title"])
        assert not bad_mask, bad_mask[:5]
        assert not bad_prose, bad_prose[:5]

    def test_no_span_boundary_splits_a_combining_sequence(self, corpus):
        """A span edge must not fall between a base character and its
        combining mark, in either normalisation form.

        Slicing at such an edge hands a caller a naked combining mark, which
        renders on whatever character precedes it -- the prose residue
        conformance compares would then differ for a reason that has nothing
        to do with mathematics. MEASURED over the corpus in both forms: 0
        violations, for this module and for the scanner alike.

        Deliberately corpus-level and not a hypothesis property: over 4,000
        random strings seeded with combining marks the count is 6,523 for
        this module and 7,109 for the scanner. Whether that is harmful
        depends on
        the offset frame, which is why the two are specified in the same
        class.
        """
        offenders = []
        for row in corpus:
            for form in ("NFC", "NFD"):
                t = unicodedata.normalize(form, row["title"])
                for s, e in find_math_regions(t):
                    if e < len(t) and unicodedata.combining(t[e]):
                        offenders.append((form, row["title"], t[s:e], "end"))
                    if s > 0 and unicodedata.combining(t[s]):
                        offenders.append((form, row["title"], t[s:e], "start"))
        assert not offenders, offenders[:5]

    #: Shapes where NFD and NFC still disagree, MEASURED 2026-08-25. Both
    #: need a decomposed letter within one character of a notation atom: the
    #: combining mark hides the letter it sits on, so a bare "E" or "s" is
    #: left looking like a lone variable.
    KNOWN_NFD_DIVERGENCES = {
        "σ ∂ Économétrie noyaux",
        "inégalités √n",
    }

    def test_the_known_nfd_divergences_do_not_spread(self):
        """A RATCHET on an open defect, not a lock on it.

        This asserts a SUBSET, so a fix that removes a divergence still
        passes and a regression that adds one fails. It is here because the
        property above is not universal and saying so is the honest form of
        the claim: MEASURED, 0 of the 345 real titles disagree, but 40 of
        4,000 synthesised title-shaped strings do, and the two shapes below
        are the reproductions. (The module's docstring separately claims 0
        disagreements over the 3,060 accented library titles; that figure is
        its author's, not re-measured here.)

        Consequence if it ever reaches a real filename: macOS hands NFD to
        ``validators/filename_checker/core.py``, so "inégalités √n.pdf" would
        be read as protecting "s √n" and the "s" of "inégalités" would stop
        being prose.
        """
        probes = [
            "σ ∂ Économétrie noyaux",
            "inégalités √n",
            "Économétrie L²",
            "L² Économétrie",
            "Théorie L²",
            "Précis L²",
            "Analyse réelle L²",
            "Sur les inégalités de Sobolev L²",
            "Économétrie de la finance L²",
            "À propos de L²",
            "L² à la Itô",
            "Étude de σ",
            "σ Étude",
            "Über L²",
            "L² über",
            "Kalkül L²",
            "L² Kalkül",
            "Lévy L²",
            "L² Lévy",
        ]
        diverging = set()
        for t in probes:
            nfc = unicodedata.normalize("NFC", t)
            nfd = unicodedata.normalize("NFD", t)
            a = [unicodedata.normalize("NFC", nfc[s:e])
                 for s, e in find_math_regions(nfc)]
            b = [unicodedata.normalize("NFC", nfd[s:e])
                 for s, e in find_math_regions(nfd)]
            if a != b:
                diverging.add(t)
        assert diverging <= self.KNOWN_NFD_DIVERGENCES, (
            "a NEW NFD/NFC divergence appeared: "
            f"{sorted(diverging - self.KNOWN_NFD_DIVERGENCES)}"
        )


# ═══════════════════════════════════════════════════════════ the contract ══

_MATH_ALPHABET = (
    "abcxyzXYZ 0123456789"
    "+-−*/=<>≤≥≠∈∋⊂⊆±∓·⋅×÷~&|^_"
    "(){}[]<>,;.:!?'\"$\\/@#%"
    "αβγσπΓΣΩ∂∞∫√ℝℂℤℙ²³ⁿᵖₜᵢ⅓→"
    "éÉèôüñ\u0301\u0308\u0327"          # precomposed AND combining
    "\u200b\u0000\t\n"                  # zero width, NUL, control
)

_texts = st.one_of(
    st.text(max_size=120),
    st.text(alphabet=_MATH_ALPHABET, max_size=120),
    st.text(alphabet=_MATH_ALPHABET, max_size=120).map(
        lambda t: unicodedata.normalize("NFD", t)),
    st.text(alphabet=_MATH_ALPHABET, max_size=120).map(
        lambda t: unicodedata.normalize("NFC", t)),
)


class TestTheContract:
    """What the live consumers require, in the terms they require it.

    The strategy is no longer bare ``st.text()``. The parser has operator
    tables, brace groups, backslash commands and dollar delimiters, and an
    alphabet that never emits one of them cannot reach the code that handles
    it. It also mixes NFC and NFD, which is what let the offset-frame bug sit
    green for as long as it did.
    """

    @settings(max_examples=500, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(_texts)
    def test_spans_are_sorted_disjoint_and_inside_the_string(self, text):
        """``e <= len(text)`` -- the string the CALLER passed.

        The previous bound was ``len(unicodedata.normalize("NFC", text))``,
        which is a different string. A caller must be able to slice its own
        input with these offsets; see :class:`TestTheOffsetFrame`.
        """
        got = find_math_regions(text)
        last = 0
        for s, e in got:
            assert 0 <= s < e <= len(text), (s, e, len(text))
            assert s >= last, "overlapping or unsorted"
            last = e

    @settings(max_examples=500, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(_texts)
    def test_a_span_never_starts_or_ends_on_whitespace(self, text):
        """A span that eats the space beside it moves the prose boundary
        conformance diffs, and ``core.math_tokenization`` would emit a MATH
        token with a leading blank. MEASURED: 0 violations over 30,000
        fuzzed strings before this was written."""
        for s, e in find_math_regions(text):
            span = text[s:e]
            assert span, "empty span"
            assert not span[0].isspace() and not span[-1].isspace(), repr(span)

    @settings(max_examples=500, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(_texts)
    def test_a_span_is_never_multiple_ascii_words(self, text):
        """The scanner's pathology as a property rather than a sample.

        More than one character of nothing but ASCII letters and spaces is
        prose, whatever led the parser there. Exactly one character is
        allowed because the corpus labels bare Latin variables as
        mathematics. MEASURED: 0 violations over 30,000 randomly fuzzed
        strings, 20,000 word-shaped ones, and 20,000 hypothesis examples.
        """
        for s, e in find_math_regions(text):
            span = text[s:e]
            assert not (len(span) > 1 and all(
                c.isascii() and (c.isalpha() or c.isspace()) for c in span)
            ), repr(span)

    @settings(max_examples=400, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(_texts)
    def test_never_raises(self, text):
        """A total function.

        This matters more than it used to: the implementation is a
        recursive-descent parser, not a 259-line scanner, so the space of
        inputs that could raise or recurse is far larger. The widened
        alphabet above is the point of this test, not an accessory to it.
        """
        assert isinstance(find_math_regions(text), list)

    def test_the_return_value_is_a_fresh_mutable_list_of_tuples(self):
        """``core.math_tokenization`` APPENDS to the object it is handed and
        keys a dict on the region starts. A cached list, a tuple, or a
        generator each break it in a different way."""
        a = find_math_regions("AR(1) processes")
        b = find_math_regions("AR(1) processes")
        assert a == b and a is not b
        assert isinstance(a, list)
        assert all(isinstance(x, tuple) and len(x) == 2 for x in a)
        assert all(isinstance(i, int) for x in a for i in x)
        a.append((99, 100))          # caller mutation must not persist
        assert find_math_regions("AR(1) processes") == b

    @pytest.mark.parametrize("bad", [None, 123, b"L^2", ["L^2"]])
    def test_a_non_string_raises_typeerror(self, bad):
        """"I didn't look" and "it's fine" must never be the same return
        value. Returning ``[]`` for a non-string would say "no mathematics
        here" about something that is not a title at all."""
        with pytest.raises(TypeError):
            find_math_regions(bad)

    def test_blank_input_is_empty_not_an_error(self):
        assert find_math_regions("") == []
        assert find_math_regions("   ") == []


class TestTheBoundsRefuseRatherThanGuessOrHang:
    """The other half of what ``if __name__ == "__main__":`` was holding.

    ``MAX_INPUT_CHARS`` and ``MAX_PARSE_STEPS`` are the whole of the fix for
    the super-linear blowup, and they are the kind of limit that changes
    behaviour SILENTLY: a budget that fires returns something, and if that
    something is ``[]`` the caser is told "no mathematics here" about a title
    nobody looked at -- CLAUDE.md non-negotiable 4, exactly. So what a
    refusal RETURNS is a contract, not an implementation detail, and it was
    asserted only in a block pytest never ran.

    The predecessor's guard, ``self.calls > 4000``, is the reason this class
    is emphatic: it was PER PARSER, so the 64-character bomb below built
    36,256 parsers each with a fresh allowance and the budget never fired
    once. A budget with no test is a budget that does not exist.
    """

    def test_an_over_long_input_is_refused_by_protecting_all_of_it(self):
        """A refusal is ``[(a, b)]`` over the whole STRIPPED input, and the
        stripping matters: a span with a whitespace edge violates the contract
        every other test in this file asserts, and ``core.math_tokenization``
        would emit a MATH token with a leading blank."""
        over = "  " + "x + y " * 400 + "  "
        assert len(over) > _module.MAX_INPUT_CHARS
        got = find_math_regions(over)
        assert got == [(len(over) - len(over.lstrip()), len(over.rstrip()))]
        span = over[got[0][0]:got[0][1]]
        assert not span[0].isspace() and not span[-1].isspace()

    def test_a_refusal_is_distinguishable_from_finding_nothing(self):
        """"I didn't look" and "it's fine" must never be the same return
        value. ``[]`` means looked-and-found-nothing and a caser rewrites the
        title; a refusal must not be spellable that way."""
        over = "An introduction to probability theory. " * 40
        assert len(over) > _module.MAX_INPUT_CHARS
        assert find_math_regions(over) != []
        assert find_math_regions("An introduction to probability theory") == []

    def test_the_cap_is_a_cap_and_not_an_approximation(self):
        """Exactly at ``MAX_INPUT_CHARS`` the input is still analysed. An
        off-by-one here silently refuses a whole class of real titles -- the
        longest in the library is 229 characters, so the margin is large, but
        an over-long Crossref title arriving at ingest is the case the bound
        exists for and the boundary must be the documented one."""
        at_cap = "x" * _module.MAX_INPUT_CHARS
        assert len(at_cap) == _module.MAX_INPUT_CHARS
        assert find_math_regions(at_cap) == []
        over_by_one = "x" * (_module.MAX_INPUT_CHARS + 1)
        assert find_math_regions(over_by_one) == [(0, len(over_by_one))]

    def test_an_expensive_parse_is_refused_the_same_way(self):
        """The step budget, reached by an input well INSIDE the length cap.

        The two bounds are separate decisions -- length is cheap to check and
        catches the pathological long input, steps catch the short input that
        is expensive per character -- and each needs its own test, because a
        length cap alone leaves the 64-character bomb unbounded.
        """
        hard = "(" + ",".join("a" for _ in range(120)) + ")"
        assert len(hard) <= _module.MAX_INPUT_CHARS
        assert find_math_regions(hard) == [(0, len(hard))]

    def test_no_real_title_comes_anywhere_near_the_step_budget(self, corpus):
        """A budget sized so tight that real titles trip it would silently
        stop normalising them, which is the failure this whole module exists
        to prevent. MEASURED: the worst of the 25,049 library titles spends
        52 of the 1,500 steps; over the 345-title corpus, nothing is refused.
        """
        refused = [r["title"] for r in corpus
                   if find_math_regions(r["title"])
                   == [(0, len(r["title"].strip()))]
                   and r["math_spans"] != [[0, len(r["title"].strip())]]]
        assert not refused, refused[:3]

    #: The 64-character input that cost 455-620 ms before the memo and 5 ms in
    #: the scanner it replaced. 25 ms is ~19x the measured 1.3 ms, so it will
    #: not flake on a loaded machine, and it is two orders of magnitude below
    #: the blowup it exists to catch.
    B1_BUDGET_MS = 25.0

    def test_the_bracket_bomb_does_not_blow_up(self):
        """The regression test for the super-linear parse.

        Every bracket interior was re-parsed by a fresh throw-away parser,
        once per enclosing start position AND once per production that looked
        at it: 36,256 tokenisations and 837,173 ``_classify`` calls for these
        SIXTY-FOUR characters. Growth was roughly quadratic beyond it. This
        runs inside a live Streamlit rerun.

        A wall-clock assertion is the only kind that catches it -- the answer
        was always correct, only unaffordable -- so the budget is set far
        enough above the measurement to be a blowup detector rather than a
        performance benchmark.
        """
        bomb = "(a(b(c(d(e(" * 4 + ")" * 20
        assert len(bomb) == 64
        find_math_regions(bomb)                 # warm the code paths
        started = time.perf_counter()
        for _ in range(20):
            find_math_regions(bomb)
        ms = (time.perf_counter() - started) * 1000 / 20
        assert ms < self.B1_BUDGET_MS, (
            f"B1 regression: {ms:.1f} ms for 64 characters, budget "
            f"{self.B1_BUDGET_MS} ms. Measured 1.3 ms with the memo, "
            "455-620 ms without it. Check that _sub_chainlist, _tokenize, "
            "_chain and _find_close are still memoised and that _find_close "
            "still counts an opener against its own token bound."
        )

    @pytest.mark.parametrize("n", [200, 800, 3200])
    def test_growth_is_not_super_linear_in_the_length_of_the_bomb(self, n):
        """The shape of the cost, not one point on it.

        A single timing test can be satisfied by an implementation that is
        merely fast at 64 characters and still quadratic; the predecessor
        took 1,233 ms at 3,200 characters and 66.8 s at 100,000. Beyond
        MAX_INPUT_CHARS the answer is a refusal, which is itself the bound,
        so this asserts a flat per-call cost across the whole admissible
        range and the refusal above it.
        """
        text = ("(a" * (n // 2))[:n]
        started = time.perf_counter()
        find_math_regions(text)
        elapsed_ms = (time.perf_counter() - started) * 1000
        assert elapsed_ms < 50.0, (
            f"{n} characters took {elapsed_ms:.1f} ms; every admissible "
            "length must cost about the same, and anything longer than "
            f"{_module.MAX_INPUT_CHARS} is refused outright."
        )


class TestPathologies:
    """Degenerate and adversarial input. Every case must terminate, return a
    list, and satisfy the structural contract -- and now must do so within a
    time budget, because the previous version asserted only
    ``isinstance(got, list)`` and a quadratic or exponential blowup would
    have passed it slowly.

    That gap became material when the implementation changed: the parser is
    guarded by internal call and depth ceilings, which are exactly the kind
    of limit that silently changes behaviour rather than failing loudly.
    """

    #: Generous. MEASURED worst case at the time of writing: 219 ms, on 2,000
    #: nested parentheses. The budget is ~23x that, so it cannot flake on a
    #: loaded machine, and it still catches an exponential blowup, which
    #: would not finish at all.
    BUDGET_SECONDS = 5.0

    CASES = {
        "empty": "",
        "one space": " ",
        "only spaces": "   ",
        "one character": "x",
        "one mathematical character": "ℝ",
        "only punctuation": "...,;:!?",
        "a lone period": ".",
        "a lone dollar": "$",
        "two dollars": "$$",
        "a lone display opener": "\\[",
        "a lone inline opener": "\\(",
        "a lone caret": "^",
        "a lone underscore": "_",
        "an empty bracket": "()",
        "unbalanced openers": "((((",
        "unmatched open mid-title": "A theorem on (L² spaces",
        "unmatched close mid-title": "A theorem on L²) spaces",
        "nested brackets": "((L^2))",
        "deeply nested brackets": "(" * 200 + ")" * 200,
        "deeply nested braces": "{" * 200 + "}" * 200,
        "deeply nested brackets 2000": "(" * 2000 + ")" * 2000,
        "long operator run": "x" + "+x" * 2000,
        "long link run": "ℝ" + "⋅ℝ" * 300,
        "long comma run": "1," * 2000,
        "long script run": "L" + "²" * 2000,
        "long command run": "\\alpha" * 500,
        "long dollar run": "$" * 500,
        "4000 letters": "A" * 4000,
        "500 blackboard letters": "ℝ" * 500,
        "200 arrows": "→" * 200,
        "a long real title": "L^2 (α, β) ∈ ℝⁿ " * 250,
        "NUL": "\x00",
        "zero width space": "\u200b",
        "a lone combining mark": "\u0301",
        "a combining mark on nothing, twice": "\u0301\u0308",
        "emoji": "A 😀 proof of L²",
        "emoji only": "😀😀😀",
        "RTL": "مرحبا L² بالعالم",
        "RTL only": "مرحبا بالعالم",
        "CJK": "確率論 L² 入門",
        "tab and newline": "L²\tand\nH¹",
        "500 characters of prose": (
            "Sur les inégalités de Sobolev logarithmiques et leurs "
            "applications " * 8)[:500],
        "only mathematics": "∫₀^∞ e^{-x²}dx",
        "only mathematics, short": "L²",
        "no mathematics": "An introduction to probability theory",
        "NFD input": unicodedata.normalize("NFD", "Précis d'analyse L²"),
        "NFD, no maths": unicodedata.normalize("NFD", "Précis d'analyse"),
        # the exact case that caused a real conformance bug: a span that ran
        # to the end of the stem swallowed ".pdf" in one spelling and not the
        # other, and a pure typeface change was reported as a REWRITE
        "extension after a unicode span": "Norms in lᵣ.pdf",
        "extension after an ascii span": "Norms in l_r.pdf",
        "extension and nothing else": ".pdf",
        "a windows path": r"C:\Users\name",
    }

    @pytest.mark.parametrize("name", list(CASES))
    def test_terminates_and_honours_the_contract(self, name):
        text = self.CASES[name]
        started = time.perf_counter()
        got = find_math_regions(text)
        elapsed = time.perf_counter() - started
        assert isinstance(got, list)
        last = 0
        for s, e in got:
            assert isinstance(s, int) and isinstance(e, int)
            assert 0 <= s < e <= len(text), (name, s, e, len(text))
            assert s >= last, f"{name}: overlapping or unsorted"
            last = e
            span = text[s:e]
            assert not span[0].isspace() and not span[-1].isspace(), \
                f"{name}: whitespace edge {span!r}"
        assert elapsed < self.BUDGET_SECONDS, (
            f"{name} took {elapsed:.3f}s; budget {self.BUDGET_SECONDS}s. "
            "Measured worst case when this was written: 0.219s."
        )

    @pytest.mark.parametrize("depth", [5, 20, 50, 200])
    def test_the_depth_ceiling_degrades_to_fewer_spans_not_wrong_ones(
            self, depth):
        """The parser stops at internal call and depth ceilings. What it does
        when it hits them is the question this asks: a ceiling that returns a
        WRONG span is worse than one that returns none, because a wrong span
        tells the caser to leave prose alone.

        MEASURED: the formula survives at every depth tried, and the prose
        never acquires a span.
        """
        formula = "(" * depth + "L^2" + ")" * depth
        prose = "(" * depth + "Everything you wanted" + ")" * depth
        assert spans(formula) in ([], ["L^2"]), spans(formula)
        assert find_math_regions(prose) == [], spans(prose)

    def test_the_whole_corpus_stays_fast(self, corpus):
        """A broad slowdown, as opposed to one adversarial input.

        MEASURED: 12 ms for all 345 titles. The budget is 2 s, ~165x that,
        so this fails on a real regression and not on a loaded machine.
        """
        started = time.perf_counter()
        for row in corpus:
            find_math_regions(row["title"])
        elapsed = time.perf_counter() - started
        assert elapsed < 2.0, f"345 titles took {elapsed:.3f}s; measured 0.012s"


class TestTheTokeniserGetsOneTokenPerFormula:
    """The contract ``core/math_tokenization.py`` actually depends on, tested
    through it rather than at one remove.

    It keys a dict on region STARTS and silently drops a region it never
    lands on -- so a span that begins mid-token disappears without an error.
    MEASURED over the 345 labelled titles: 0 titles where the number of MATH
    tokens differs from the number of regions, 0 where their values differ,
    and 0 where the token stream fails to reconstruct the title.
    """

    def test_every_region_becomes_exactly_one_math_token(self, corpus):
        from core.math_tokenization import robust_tokenize_with_math
        mismatched = []
        for row in corpus:
            title = row["title"]
            regions = find_math_regions(title)
            tokens = robust_tokenize_with_math(title, set())
            maths = [t.value for t in tokens if t.kind == "MATH"]
            if maths != [title[s:e] for s, e in regions]:
                mismatched.append((title, [title[s:e] for s, e in regions],
                                   maths))
        assert not mismatched, mismatched[:3]

    def test_the_token_stream_reconstructs_the_title(self, corpus):
        """No character is lost or duplicated at a region boundary."""
        from core.math_tokenization import robust_tokenize_with_math
        broken = [
            row["title"] for row in corpus
            if "".join(t.value for t in
                       robust_tokenize_with_math(row["title"], set()))
            != row["title"]
        ]
        assert not broken, broken[:3]

    def test_no_region_starts_in_the_middle_of_a_word(self, corpus):
        """The precondition for the dict key to land. MEASURED: 0
        violations over the corpus."""
        offenders = []
        for row in corpus:
            title = row["title"]
            for s, e in find_math_regions(title):
                if s > 0 and title[s - 1].isalnum():
                    offenders.append((title, title[max(0, s - 4):e]))
        assert not offenders, offenders[:5]


class TestTheAnswerIsTheSameInEveryProcess:
    """Casing must be reproducible between the PREVIEW and the APPLY.

    That is not hypothetical here: a previous bug had the caser propose one
    name in the cockpit and write another on disk, because a set's iteration
    order leaked into the decision (fixed 5fc249b). This module builds
    several module-level sets, so the same hazard exists and nothing asserted
    against it.

    MEASURED under PYTHONHASHSEED 0, 1, 12345 and 99999: an identical digest
    over all 345 corpus titles. Four subprocesses cost 0.17 s.
    """

    SNIPPET = r'''
import importlib.util, json, sys, hashlib, pathlib
spec = importlib.util.spec_from_file_location("probe", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
rows = json.loads(pathlib.Path(sys.argv[2]).read_text())["labelled"]
h = hashlib.sha256()
for r in rows:
    h.update(repr(m.find_math_regions(r["title"])).encode())
print(h.hexdigest())
'''

    def test_the_digest_is_hash_seed_independent(self):
        import os
        import core.math_regions as module_under_test

        digests = {}
        for seed in ("0", "1", "12345", "99999"):
            env = dict(os.environ)
            env["PYTHONHASHSEED"] = seed
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            done = subprocess.run(
                [sys.executable, "-c", self.SNIPPET,
                 module_under_test.__file__, str(_FIXTURE)],
                capture_output=True, text=True, env=env, timeout=120,
            )
            assert done.returncode == 0, done.stderr[-2000:]
            digests[seed] = done.stdout.strip()
        assert len(set(digests.values())) == 1, digests


# ═══════════════════════════════════════════════════ the edges of the job ══

class TestBareAcronymsAndNumeralsAreNotOurs:
    """The single largest negative class in the ground truth. Its
    construct table records 88 lexical acronyms, 36 Roman-numeral parts or
    volume numbers and 33 bare years or issue numbers among the 345 titles --
    and nothing in this file asserted anything about any of them.

    The boundary is INHERITED, not invented here: ``title_normalize`` has an
    acronym branch that already owns the decision, and double-owning it would
    penalise a correct detector. That delegation is also the argument that
    settles ``Γ-convergence``, so it deserves a test of its own rather than
    an appeal in a docstring.

    THE RISK, stated, and it is the module author's own count rather than
    one re-measured here: BMO, UMD, VMO and BV are genuine function spaces
    (46 library titles) and are lexically identical to BSDE and COVID. This
    module leaves all of them to the acronym branch. If that branch does not
    in fact protect them, roughly 2,000 case-sensitive occurrences are
    protected by nobody. That is an open question for the owner, not a defect
    of this module.
    """

    @pytest.mark.parametrize("title", [
        "BSDE methods in finance",
        "A PDE approach to Asian options",
        "SPDE limits of interacting particle systems",
        "HJB equations and viscosity solutions",
        "BMO martingales and exponential moments",
        "The SIR model of epidemics",
        "VIX futures and variance swaps",
        "LIBOR market models",
        "MATLAB implementations of GARCH",
        "COVID-19 and the SIR model",
        "2D turbulence in 3D",
        "CAPM and the cross-section of returns",
        "UMD spaces and VMO functions",
    ])
    def test_a_lexical_acronym_is_not_a_span(self, title):
        assert find_math_regions(title) == []

    @pytest.mark.parametrize("title", [
        "Séminaire Bourbaki, tome VII",
        "Annales, volume XIV",
        "Lecture notes, Part III",
        "Chapitre IX des probabilités",
        "Annales 1897-1898",
        "Séminaire Bourbaki, volume 2012:2013",
        "J. Finance 155(3) 2011",
        "Selected papers, pp. 1105-1123",
    ])
    def test_a_numeral_or_volume_number_is_not_a_span(self, title):
        """Bare digits are not notation, and a Roman numeral is a word."""
        assert find_math_regions(title) == []


class TestWhatItDeliberatelyDoesNot:
    """Non-ownership, stated as tests. A module whose job has no edges
    over-claims by construction."""

    def test_it_cannot_tell_an_acronym_from_initials(self):
        """"P.D.E." and "S.R.S." have the identical shape and only one is
        mathematics. This module answers "not maths" for both, which is right
        for the acronym and a miss for nothing -- initials are the author
        block's problem, not the title's."""
        assert find_math_regions("A P.D.E. approach") == []
        assert find_math_regions("S.R.S. Varadhan on large deviations") == []

    def test_a_bare_decimal_is_not_protected(self):
        """"0.5-Hölder" has no anchor, so no span. Nothing in it needs
        protecting from recasing: the digits have no case and "Hölder" is a
        proper noun handled by the vocabulary.

        This is the decisive internal precedent for the Γ-convergence
        convention. The file already accepts that a word attached by a hyphen
        to a non-casing token is left to the vocabulary; protecting the word
        after "Γ-" but not the word after "0.5-" was the position that could
        not be defended. The two tests now state ONE policy.
        """
        assert find_math_regions("0.5-Hölder continuity") == []
        assert spans("Γ-convergence of the functional") == ["Γ"]


class TestDeclaredPrices:
    """Behaviour that is WRONG under the operational definition and is kept
    anyway, because the alternative measured worse.

    READ THIS BEFORE "FIXING" ANYTHING BELOW. These assertions pin a cost,
    not a virtue. A failure here may well be an improvement -- check the
    corpus score first, and if precision and recall held, update the test
    rather than reverting the module. They exist so the prices are visible
    and cannot creep, not so they are permanent.
    """

    def test_a_ratio_written_with_a_colon_is_missed(self):
        """The library writes "/" as ":", so a bare digit:digit is lexically
        identical to "Séminaire Bourbaki, volume 2012:2013" and to
        "IFIP-WG 7:1", which are not mathematics. No purely lexical rule
        separates them. Cost: 3 characters of the corpus, and it is one of
        only two titles this module gets wrong."""
        assert find_math_regions(
            "Differential equations driven by Hölder continuous functions "
            "of order greater than 1:2") == []

    def test_a_bare_euler_e_is_missed(self):
        """A lone letter that is also an English word cannot be told from an
        article without semantics, and refusing it is what stops "the case of
        a √n window" from claiming the article. Cost: 1 character, and the
        other of the two titles this module gets wrong."""
        got = spans("New Wallis- and Catalan-type infinite products for "
                    "π, e, and sqrt{2 + sqrt{2}}")
        assert "e" not in got
        assert got == ["π", "sqrt{2 + sqrt{2}}"]

    def test_a_short_snake_case_identifier_is_claimed(self):
        """"top_k" and "eps_i" are the same shape and one is notation.
        Separating them needs a dictionary; a length rule cannot. The
        module's docstring records 10 hits over the 25,049 library titles,
        all genuine notation and 0 false positives -- and an identifier's
        case should be preserved anyway, so the over-claim costs nothing."""
        assert spans("top_k selection") == ["top_k"]

    def test_a_chemical_formula_is_claimed(self):
        """"CO₂" is chemistry, not mathematics. Its case must be preserved
        and it carries a Unicode subscript, so it satisfies the operational
        definition by accident. One library title."""
        assert spans("CO₂ emissions and the carbon price") == ["CO₂"]

    def test_a_windows_path_claims_its_components(self):
        """Backslash-plus-letters is a LaTeX command by the LaTeX rule, and a
        path component's case is worth preserving too, so this is left as it
        is."""
        assert spans(r"Data at C:\Users\name") == [r"\Users\name"]

    def test_a_money_pair_with_a_one_word_payload_is_claimed(self):
        """NEWLY FOUND, 2026-08-25, and not previously recorded.

        The dollar guard refuses a payload that reads as two or more ordinary
        English words. "$5 and $10" has a ONE-word payload, so the guard does
        not fire and "$5 and $" is claimed as a formula. In a mathematical
        finance library that shape is plausible ("Between $5 and $10
        trillion"), and the consequence is that the words between two money
        amounts stop being prose.

        Bounded, not endorsed: the two-word forms in
        ``test_money_is_not_mathematics`` are still refused.
        """
        assert spans("Priced at $5 and $10") == ["$5 and $"]


# ═══════════════════════════════════ what the mutants got away with ══
#
# A mutation campaign on 2026-08-25 planted 89 mutants at 89 distinct
# decision points in the module and ran this suite against each with
# PYTHONDONTWRITEBYTECODE=1 and every __pycache__ purged between mutants
# (rewriting a source file twice inside one filesystem mtime tick makes
# CPython reuse the previous mutant's bytecode, and the run silently becomes
# a coin flip). Each mutant was also written to its own path, so no two ever
# shared a filename.
#
# 56 died against the suite as it stood once the expectation table above was
# wired in. The classes below kill 28 of the 33 that did not, taking the
# score to 84 of 89.
#
# The house rule was followed for every survivor: BEFORE writing a test,
# find out whether the branch is reachable at all. Two of the 33 turned out
# to be dead code and three to be behaviourally equivalent mutations; those
# five are recorded in TestBranchesMeasuredUnreachable rather than tested,
# because a test of an unreachable branch is a test of nothing.
#
# Reachability was decided by planting a counter ON the branch in a copy of
# the module and running it over 205,614 inputs -- the 25,049 cached library
# titles, the 345 corpus titles, the 184 _CASES titles, 60,000 mutated real
# titles and 120,000 random strings from a maths-heavy alphabet -- plus, for
# each survivor separately, 300,000 further strings drawn from an alphabet
# built out of the characters that branch reads. Where a real library title
# separates the mutant from the module, the test uses THAT; only two of the
# 28 could be killed by one, which is itself the finding: these are the
# bounds and the ceilings, and no real title goes anywhere near them.


class TestABoundIsABoundBecauseItWasMeasured:
    """Every width and length in the grammar was chosen against a population,
    and each one is the only thing standing between a production and an
    English word. All eleven survived the suite as it was: widening them
    changed nothing any existing test looked at.

    None of these is reachable from a real library title -- measured, over
    all 25,049 -- which is exactly why they were unprotected. A bound nobody
    reaches is still a bound that must not move, because the input that
    reaches it arrives from Crossref, not from the shelf.
    """

    def test_a_caret_base_is_at_most_eight_ascii_characters(self):
        """M08. Widened to 40, ``Bellman equations^in bounded domains``
        claims ``equations^in``: an English word on each side of a caret,
        protected as though it were a base and an exponent. The bound exists
        because ``CVT_DG_random_grids_01_12_2025`` parses as an exponent
        without it."""
        assert spans("Bellman equations^in bounded domains") == []
        assert spans("estimates_for the operator") == []
        assert spans("L^2 estimates for the d-bar operator") == ["L^2", "d"]

    def test_a_capshead_is_at_most_six_ascii_capitals(self):
        """M09. Widened to 20, ``SEMIMARTINGALE(2)`` becomes notation. A
        long all-caps run glued to a bracket is a shouted English word or an
        acronym, and acronyms belong to title_normalize's acronym branch --
        claiming them here double-owns the decision. The six-character bound
        is what keeps GARCH, RCD and CAT in and MARTINGALE out."""
        assert spans("SEMIMARTINGALE(2)") == []
        assert spans("MARTINGALE(1) processes") == []
        assert spans("A continuous time GARCH(p, q) process with delay") \
            == ["GARCH(p, q)"]

    def test_a_symbolbracket_payload_is_at_most_four_characters(self):
        """M15. Widened to 24, ``(*+*+*)^+`` is claimed. The SymbolBracket
        production exists for the axiom names ``(*)^+`` and ``(*)^{++}`` and
        for nothing else; a longer payload of pure punctuation is a typo or
        an ASCII drawing, not a name."""
        assert spans("(*+*+*)^+") == []
        assert spans("(**/**)^{++}") == []
        assert spans("The equivalence of axiom (*)^+ and axiom (*)^{++}") \
            == ["(*)^+", "(*)^{++}"]

    def test_a_symbolbracket_payload_may_not_contain_a_letter_or_a_digit(self):
        """M16. Drop the ``not any(c.isalnum())`` test and ``(abc)^+`` is
        mathematics -- which is the ``(Almost) Everything you always wanted
        to know`` class arriving through the axiom-name door. The module
        docstring claims that no amount of "(Almost)" can reach this
        production; this is the assertion behind the claim."""
        assert spans("(abc)^+") == []
        assert spans("(xy)^2") == []
        assert spans("(T)⁺") == ["⁺"]

    def test_a_braced_script_argument_is_at_most_twenty_four_characters(self):
        """M35. Widened to 240, ``L^{superconvergentestimates}`` is claimed:
        a whole English word, protected because a brace was in front of it.
        Note the shape needed to reach this bound -- the loop's OTHER check
        stops a long argument made of many tokens one step earlier, so only
        a single long token gets here, and that is why nothing else in this
        file covers it."""
        assert spans("L^{superconvergentestimates}") == []
        assert spans("H^{alphabetagammadeltaepsilon}") == []
        assert spans("W^{2,p} and W^{1,p}-estimates at the boundary") \
            == ["W^{2,p}", "W^{1,p}"]

    def test_an_unbraced_script_index_is_a_short_token_or_a_known_name(self):
        """M36. Widened to 30, ``L^probability`` and ``eps_information`` are
        claimed. The rule is that an index is either short or one of the
        spelled-out names the library actually writes (``H_infty`` beside
        ``H^∞``); an arbitrary English word is neither, and protecting one
        stops the caser normalising the sentence it sits in."""
        assert spans("L^probability") == []
        assert spans("L_distribution") == []
        assert spans("eps_information") == []
        assert spans("H_infty control") == ["H_infty"]

    def test_a_script_run_stops_after_three_glued_tokens(self):
        """M38. Widened to 30, ``L_ⁿ3∑−`` swallows the trailing minus.
        The run is bounded so that a script cannot walk off down a chain of
        operators; the token after the third is the operator that belongs to
        the enclosing expression, not to the index."""
        assert spans("L_ⁿ3∑−") == ["L_ⁿ3∑"]
        assert spans("Sharp inequalities for martingales with values in lᴺ_∞") \
            == ["lᴺ_∞"]

    def test_the_juxtaposed_product_escape_needs_an_operator_head(self):
        """M43. Drop ``head_is_func`` and ``L(ab)`` and ``Fi(xy)`` become
        function calls. The escape exists for ``sinᵃ(px)``, ``cos(qx)``,
        ``tan(rt)`` -- a juxtaposed product of variables after an OPERATOR
        NAME. Without the gate the lowercase English head in ``FIFA world
        cup(tm)`` reaches it too."""
        assert spans("L(ab) spaces") == []
        assert spans("Fi(xy) groups") == []
        assert spans("A direct proof of the irrationality of tan²(rπ)") \
            == ["tan²(rπ)"]

    def test_find_close_gives_up_after_twenty_five_tokens_across_a_space(self):
        """M23. Widened to 2,500, a fourteen-member list of bare letters
        becomes a tuple. The bound is what stops a bracket at the start of a
        title reaching a bracket at the end of it and calling everything
        between them one expression -- the pathology that let math_utils
        claim 186 of 189 characters of an English sentence."""
        assert spans("(x, x, x, x, x, x, x, x, x, x, x, x, x, x)") == []
        assert spans("Les intervalles de constance de <X, X>") == ["X, X"]

    def test_the_bracket_nesting_ceiling_holds(self):
        """M17. Widened to 800, ``L^2`` and twelve nested brackets fuse into
        one span. The ceiling is normally invisible -- ``_trim`` unwraps a
        balanced nest back to its content whichever side of the ceiling the
        parse fell -- so it takes a nest with something OUTSIDE it to see the
        difference at all. That is why this went untested: the obvious probe
        cannot fail."""
        deep = "L^2" + "(" * 12 + "α" + ")" * 12
        assert spans(deep) == ["L^2", "α"]

    def test_a_relation_takes_at_most_a_two_letter_differential(self):
        """M49. Widened from 2 to 3, ``σ=the answer`` claims ``σ=the``.
        Three characters is the width that lets an English article through,
        and the escape exists for ``d[X, X]ₜ=dt``, which is two."""
        assert spans("σ=the answer") == ["σ"]
        assert spans("σ∈the set") == ["σ"]
        assert spans("5€per share") == []
        assert spans("α<the bound") == ["α"]


class TestEvidenceIsEarnedNotAssumed:
    """Every one of these mutants makes the parser BELIEVE something it was
    not told. They survived because the suite tested what the grammar
    accepts far more thoroughly than what makes it accept.
    """

    def test_the_short_word_escape_needs_a_symbol_to_its_left(self):
        """M47. Drop the ``ev_left & SYM`` test and ``D>ob`` is mathematics:
        two ordinary letters and a greater-than sign. The escape exists for a
        juxtaposed factor after a SYMBOL -- ``√dt``, ``∫₀^∞ sin(x):xdx`` --
        and an ASCII relation is not a symbol."""
        for text in ("D>ob", "x=to", "n<of", "N>as"):
            assert find_math_regions(text) == [], text
        assert spans("A game-theoretic explanation of the √dt effect") == ["√dt"]

    def test_the_short_word_escape_may_not_reach_across_a_space(self):
        """M56. Fix ``glue_w`` at 3 regardless of whether the operand is
        GLUED, and ``(√2 dt)`` claims ``√2 dt``. Note the bracket: at the top
        level the spaced-juxtaposition guard catches this a step later, so the
        only place the mutation shows is INSIDE a bracket, where that guard
        does not run. Nothing in the suite looked there.

        This is defect (c) from a different direction -- the same escape, the
        same space, one level down."""
        assert spans("(√2 dt)") == ["√2"]
        assert spans("(α dt)") == ["α"]
        assert spans("L²(√2 dt)") == ["L²", "√2"]
        assert spans("(∫ dt)") == ["∫"]

    def test_a_relation_is_not_by_itself_a_self_standing_side(self):
        """M58. Add REL to ``_ss`` and ``a=b c=d`` becomes ONE span across
        the space. ``_ss`` answers "does this side stand on its own?" for the
        space and dash guards, and a relation between two bare letters does
        not: nothing in ``a=b`` is a character a caser could get wrong, and
        joining two of them across a space is how a whole sentence of
        equations becomes one region."""
        assert spans("a=b c=d") == ["a=b", "c=d"]
        assert spans("x=y z=w") == ["x=y", "z=w"]
        assert spans("p=1 q=2") == ["p=1", "q=2"]

    def test_an_en_dash_needs_BOTH_sides_notational(self):
        """M51. ``and`` -> ``or`` and ``Δ–2002`` claims the year, ``L²–1973``
        claims the year, ``1915–Δ`` claims it from the other side. The dash
        production exists for ``Δ–Γ`` and ``L^q–Lᵖ``; every bibliographic
        dash in the library -- ``1915–2002``, ``1059–1073``, ``2009–10``,
        ``Erdős–Mordell``, ``Chapters (1)–(4)`` -- sits one symbol away from
        being claimed, and this ``and`` is the whole distance."""
        assert spans("Δ–2002") == ["Δ"]
        assert spans("L²–1973") == ["L²"]
        assert spans("1915–Δ") == ["Δ"]
        assert spans("Lᵖ–q") == ["Lᵖ"]
        assert spans("The tracking error rate of the Δ–Γ hedging strategy") \
            == ["Δ–Γ"]

    def test_a_bracket_carries_BRK_even_when_its_interior_carries_nothing(self):
        """M20. Drop the ``| BRK`` and ``Δ–(2M)`` loses its bracket.

        The case is narrow and that is why it survived: a bracket admitted
        LENIENTLY (because what stands to its left is already notation) can
        have an interior that parses with no evidence of its own, and then
        BRK is the only evidence the group has. It is what ``_ss`` reads when
        the group is a dash's or a space's right-hand operand."""
        assert spans("Δ–(2M)") == ["Δ–(2M)"]
        assert spans("α – (2M)") == ["α – (2M)"]
        assert spans("Σ /‖RCD‖") == ["Σ /‖RCD"]

    def test_a_nested_brackets_BRK_is_evidence_for_the_bracket_around_it(self):
        """M25. Drop BRK from the acceptance test in ``_content_evidence``
        and ``((y,z))ⁿ`` tears into ``y,z`` and ``ⁿ``. The inner bracket's
        only evidence is that it is a tuple of bare variables; if that does
        not reach the outer bracket, the outer one fails and the superscript
        is orphaned. ``_trim`` hides this on a bare ``((y,z))`` -- it unwraps
        both -- so the probe needs something glued outside."""
        assert spans("((y,z))ⁿ") == ["((y,z))ⁿ"]
        assert spans("((y,z))–Δ") == ["((y,z))–Δ"]

    def test_an_empty_bracket_interior_does_not_parse(self):
        """M30. Drop ``if terms == 0: return None`` and ``α(,)β`` becomes one
        span: a bracket containing nothing but a comma is admitted, and it
        then glues the symbol on each side of it together. A bracket must
        contain at least one TERM to be notation."""
        assert spans("α(,)β") == ["α", "β"]
        assert spans("α{,}β") == ["α", "β"]
        assert spans("L²[;]M") == ["L²"]

    def test_the_space_budget_inside_one_chain_is_finite(self):
        """M54. Widened from 6 to 600, a chain of spaced factors runs on
        forever. Reaching this at all takes the short-word escape, because
        that is the one right-hand operand which consumes a single token and
        returns, letting the chain's own loop go round again -- every other
        operand swallows the rest of the chain and the budget is never
        decremented twice. Nothing in the suite had that shape, which is why
        a 100x widening was invisible."""
        assert spans("α" + " ⋅dt" * 8) == ["α" + " ⋅dt" * 6]
        assert spans("π" + " ⋅dx" * 9) == ["π" + " ⋅dx" * 6]


class TestTheEdgesOfASpan:
    """Trimming and snapping. A span with the wrong edge is worse than no
    span: it hands the caser a boundary in the middle of a word, and
    ``core.math_tokenization`` drops a region whose start it never lands on.
    """

    def test_a_bracket_is_only_stripped_when_it_really_wraps_the_span(self):
        """M18, one of the three named must-kills. ``_wraps`` returning True
        unconditionally turns ``(α)+(β)`` into ``α)+(β`` -- the span keeps its
        interior brackets and loses its outer ones, so the caser is handed a
        boundary inside a bracket pair.

        MEASURED: two real library titles change, both Euler's integral
        formula, where the leading ``(`` and trailing ``)`` of
        ``(xⁿ⁺ᵖ-2xⁿcos(ζ)+xⁿ⁻ᵖ):(x²ⁿ-2xⁿcos(θ)+1)`` are stripped although the
        first ``(`` closes in the middle. The suite tested the case where
        stripping is CORRECT and never the case where it is not."""
        assert spans("(α)+(β)") == ["(α)+(β)"]
        assert spans("(0<d<2)") == ["0<d<2"]      # here it really does wrap

    def test_a_real_library_title_keeps_its_outer_brackets(self):
        """M18 through the population rather than the probe.

        This is the actual title, from the cached 25,049. Two of them differ
        only in language, and both are Euler; the formula is the reason the
        module has a ``_wraps`` function at all."""
        title = ("An easy method for finding the integral of the formula "
                 "int dx:x (xⁿ⁺ᵖ-2xⁿcos(ζ)+xⁿ⁻ᵖ):(x²ⁿ-2xⁿcos(θ)+1) with "
                 "upper limit of integration x=1 or x=∞")
        assert spans(title) == [
            "(xⁿ⁺ᵖ-2xⁿcos(ζ)+xⁿ⁻ᵖ):(x²ⁿ-2xⁿcos(θ)+1)", "x=1", "x=∞"]

    def test_a_span_never_keeps_a_leading_stray_closing_bracket(self):
        """M60. Delete the ``a in ")]}"`` rule and a span can begin on a
        closing bracket.

        It takes mismatched delimiters to get there, which is why 205,614
        ordinary inputs never did -- and mismatched delimiters are a shape
        this module explicitly supports, because the library writes them:
        ``C^{1, β)`` and ``q^(−n_i}`` are in the module's own comments. An
        exhaustive search over six-character strings found the minimum;
        it is unlovely, and it is the real shape.

        Why it matters: a span starting one character early does not simply
        look wrong. ``core.math_tokenization`` keys a dict on region starts
        and silently drops a region it never lands on."""
        assert spans("{)}^{2)") == ["^{2)"]
        assert spans("{)}^{*)") == ["^{*)"]

    def test_an_underscore_holds_a_word_together_when_a_span_snaps_out(self):
        """M78. Drop ``_`` from ``_wordish_runs`` and the snapping rule stops
        agreeing with the grammar about where a word ends.

        ``L_exp``, ``C_b`` and ``eps_i`` are ONE word to the grammar, so they
        must be one run here too, and the effect runs in both directions:

          * ``the _eat∑ equation`` snaps to ``eat∑`` instead of ``_eat∑``,
            leaving the underscore outside the span in the prose stream;
          * ``_numbγrs`` snaps ALL THE WAY to ``numbγrs``, because with the
            underscore excluded the run starts at ``n`` and the four-character
            absorption cap is satisfied. With it included the run starts at
            the underscore, ``_numb`` is five characters, and the cap
            correctly refuses -- which is the cap doing the job it exists for,
            stopping a span reaching out and swallowing an English word.
        """
        assert spans("the _eat∑ equation") == ["_eat∑"]
        assert spans("_numbγrs") == ["γrs"]


class TestTheCeilingsDegradeSafelyRatherThanSilently:
    """A ceiling that is reached must fail in the direction that cannot
    damage a title, and it must fail at all. Both of these survived because
    every long input in ``TestPathologies`` is over ``MAX_INPUT_CHARS`` and
    is therefore refused before the parser starts -- so nothing in the suite
    exercised a long input the parser actually parses.
    """

    def test_a_long_chain_inside_the_length_cap_does_not_recurse_to_death(self):
        """M50. Widen the ``depth > 40`` ceiling and an 801-character
        arithmetic chain -- comfortably inside ``MAX_INPUT_CHARS`` -- raises
        RecursionError. ``_chain`` recurses once per LINK through ``_rhs``,
        so a chain of N terms is N frames deep, and CPython's default limit
        is 1,000.

        The contract says find_math_regions is total. Every existing
        long-input case in this file is longer than the cap and is refused
        without parsing, so this hole was structural rather than accidental:
        the suite had no admissible long input at all.
        """
        chain = "2" + "+2" * 400
        assert len(chain) < _module.MAX_INPUT_CHARS
        got = find_math_regions(chain)          # must not raise
        assert isinstance(got, list)
        assert got == [(0, len(chain))]

    @pytest.mark.parametrize("n", [100, 250, 400, 495])
    def test_admissible_chains_of_every_length_stay_total(self, n):
        """The same hole as a family rather than one point. A ceiling that
        is safe at 400 links and not at 300 would be worse than none."""
        for chain in ("2" + "+2" * n, "α" + "⋅α" * n, "x" + ",x" * n):
            assert isinstance(find_math_regions(chain), list), (n, chain[:20])

    def test_a_chain_with_no_evidence_gives_its_tokens_back(self):
        """M80. Replace the rescan ``k += 1`` with ``k = nk`` and ``(∞>)_``
        loses its infinity sign entirely.

        The rule: a chain that PARSED but carried no evidence must not
        consume its tokens, because a token inside it may still start an
        evidenced chain of its own. Skipping is a silent loss -- the answer
        is ``[]``, which the caser reads as "no mathematics here" and
        rewrites accordingly.

        MEASURED: 12,869 of 205,614 inputs take this branch, 163 of them real
        library titles, so it is heavily exercised; it took a targeted fuzz
        over the bracket-and-symbol alphabet to find one where the skip
        actually costs a span."""
        assert spans("(∞>)_") == ["∞"]
        assert spans("<^∞>^") == ["∞"]
        assert spans("{∞*}^") == ["∞"]


class TestTheMemoisationIsInvisibleAndDoesNotAccumulate:
    """The memo tables are the whole of the B1 fix, and both of their
    failure modes are invisible to an output test: one is a slow parse that
    returns the right answer, the other is a dictionary that grows for the
    life of the process.
    """

    def test_the_per_call_memo_tables_do_not_survive_the_call(self):
        """M89. Delete the two ``.clear()`` calls and nothing observable
        changes -- the memos are pure in their keys, so the answers stay
        correct -- while a long-lived process accumulates one entry per
        distinct substring of every title it has ever seen. This module sits
        under a Streamlit page that stays up for days.

        This is the only test in this file that reads a private name for its
        own sake. It does so because the defect has no other symptom.
        """
        for i in range(50):
            find_math_regions(f"A theorem on L^{i} and (α{i}, β{i}) spaces")
        assert len(_module._TOK_CACHE) < 200, (
            f"_TOK_CACHE holds {len(_module._TOK_CACHE)} entries after 50 "
            "calls; it must be cleared at the start of each call or it grows "
            "without bound in the Streamlit process."
        )
        assert len(_module._SUB_CACHE) < 200, (
            f"_SUB_CACHE holds {len(_module._SUB_CACHE)} entries after 50 calls"
        )

    #: Length ratio between the two probes is 7.9. MEASURED cost ratio:
    #: 8.0 for this module (linear), 58.8 with the opener bug restored
    #: (quadratic). 20 sits between them with a 2.5x margin either side and
    #: is a RATIO, so it does not care how fast or how loaded the machine is.
    QUADRATIC_RATIO = 20.0

    def test_find_close_is_linear_in_a_run_of_identical_openers(self):
        """M22. Restore the ``continue`` that let an opener skip its own
        60-token bound and a run of N identical openers is scanned to its end
        from each of its own N positions: ``'\\a' + '{' * 998`` goes from
        7 ms to 38 ms here, and the module's comment records 36 ms spent in
        that loop alone before the repair.

        The answer does not change -- measured over 505,614 inputs, not one
        differs -- so only the SHAPE of the cost can catch it. An absolute
        budget would have to sit between 7 ms and 38 ms and would flake on a
        loaded machine; a ratio between two lengths of the same input does
        not, because both measurements move together.
        """
        small = "\\a" + "{" * 125
        large = "\\a" + "{" * 990
        assert len(large) <= _module.MAX_INPUT_CHARS

        def best_ms(text):
            find_math_regions(text)
            return min(_timed(text) for _ in range(9))

        def _timed(text):
            started = time.perf_counter()
            find_math_regions(text)
            return (time.perf_counter() - started) * 1000

        ratio = best_ms(large) / max(best_ms(small), 1e-6)
        assert ratio < self.QUADRATIC_RATIO, (
            f"cost grew {ratio:.1f}x for 7.9x the openers; linear is ~8x and "
            "the opener bug measured 58.8x. Check that _find_close still "
            "counts an opener against its own token bound instead of "
            "`continue`-ing past it."
        )


class TestTwoRealLibraryTitlesTheMutantsChanged:
    """Of the 33 survivors, exactly two could be killed by a title that is
    actually on the shelf -- not counting M18, which has its own test above.
    Both are in this class, because a test that fires on real data is worth
    more than the same rule asserted on a probe.
    """

    def test_a_pair_of_years_in_brackets_is_not_a_tuple(self):
        """M29. Loosen ``_TUPLE_RE`` to accept multi-character members and
        the bracket in ``Liouville's equation (1850, 1853)`` becomes a tuple
        of coordinates. The tuple production exists for ``(y,z)``, ``<X, X>``
        and ``(0, T)`` -- SINGLE characters, the shape prose never writes --
        and a pair of four-digit years is exactly the shape prose does."""
        title = ("The solution of Liouville’s equation (1850, 1853) "
                 "and its impact")
        assert find_math_regions(title) == []
        assert spans("Les intervalles de constance de <X, X>") == ["X, X"]

    def test_a_trailing_underscore_with_nothing_after_it_is_not_a_script(self):
        """M39. Delete the ``if end == glue_end: return None`` guard and the
        Cuntz algebra title claims ``O_`` -- a script marker with an empty
        argument. An empty script is not a script, and the span it produces
        ends on a dangling underscore, which is the ``no span ends on a
        dangling operator`` rule this file already asserts elsewhere."""
        title = "Stochastic integration on the Cuntz algebra O_,"
        assert find_math_regions(title) == []


class TestBranchesMeasuredUnreachable:
    """Five survivors have NO test, deliberately.

    House rule: when a mutant survives, find out whether the branch is even
    reachable before writing a test for it -- three "defensive" branches in
    this codebase have already turned out to be dead and were deleted. Two
    of the five below are dead code and three are behaviourally equivalent
    mutations, which is a different thing: the branch runs, and changing it
    cannot change an answer.

    What is asserted here is the STRUCTURAL FACT that makes each one
    unreachable or equivalent, so the claim is checkable rather than a
    comment. All five are candidates for deletion or an explicit annotation.
    """

    # ── dead: the branch never executes ──────────────────────────────────

    def test_the_tokeniser_is_gapless_so_postfixes_cannot_meet_a_gap(self):
        """DEAD CODE, deletion candidate: ``_postfixes``' ``if tk.s !=
        glue_end: break`` (M33).

        REASON: ``_tokenize_slow`` walks the string with ``i = j``, so
        ``t[k].s == t[k-1].e`` for every k -- there are no gaps to meet. And
        ``glue_end`` is always the ``.e`` of the last token consumed, with k
        the index just after it. So the test is a constant False and the
        postfix loop is terminated by its final ``break``, never by this one.

        MEASURED: a counter on the branch stayed at 0 over 205,614 inputs,
        and an exhaustive search over all 271,452 strings of length <= 5 from
        a twelve-character bracket-and-script alphabet found no input where
        the mutant disagrees.

        Asserted here structurally, over the tokeniser itself.
        """
        for text in ("L^2 estimates", "AR(1) processes", "(*)^{++}",
                     "W^{2,p}", "Cₖ^∞ dans C", "C:\\Users\\name",
                     "((y,z))ⁿ", "L_exp-summing", "  spaced  out  "):
            toks = _module._tokenize(text)
            assert toks[0].s == 0
            assert toks[-1].e == len(text)
            for a, b in zip(toks, toks[1:]):
                assert a.e == b.s, (text, a.txt, b.txt)

    def test_a_span_never_starts_or_ends_on_a_link_character(self):
        """DEAD CODE, deletion candidate: the two whitespace-and-punctuation
        pre-loops at the top of ``_trim`` (M61 sits on the first of them).

        REASON: ``_trim`` is called only from ``_regions``, with the start of
        a chain's first token and the end of its last. ``_regions`` skips
        ``_T_SP``, ``_T_OTHER`` and ``_T_CLOSE`` before starting a chain, and
        a chain begins and ends on a TERM -- ``_primary`` has no production
        for a link -- so neither edge can be whitespace, a comma, a
        semicolon, a full stop or a middle dot before trimming starts.

        MEASURED: counters on BOTH pre-loops stayed at 0 over 205,614 inputs
        and over 300,000 further strings from an alphabet built out of
        exactly those characters. The equivalent loops INSIDE the
        ``while changed`` block are live -- they fire 6, 7, 6, 4, 4 and 5
        times respectively over the same population, once a bracket has been
        stripped and a new edge exposed -- so it is the pre-loops that are
        redundant, not the rule.
        """
        for text in ("·α", "α ·β", "·L^2", ",α", "α, β", "Sur la fonction ζ de "
                     "Riemann, 2", "A P.D.E. approach to Asian options"):
            for s, e in find_math_regions(text):
                assert not text[s].isspace() and text[s] not in ",;.·", text
                assert not text[e - 1].isspace() and text[e - 1] not in ",;.·"

    # ── equivalent: the branch runs, changing it changes no answer ───────

    def test_postfixes_never_reports_SYM_without_SCRIPT(self):
        """EQUIVALENT MUTANT, no test possible: ``_term``'s
        ``ev2 & (ARGS | SCRIPT)`` widened to ``ev2 & (ARGS | SCRIPT | SYM)``
        (M45).

        REASON: ``_postfixes`` sets SYM in exactly one place, and that place
        sets SCRIPT in the same statement (``ev |= SYM | SCRIPT`` for a
        Unicode super/subscript). Every other bit it can set is SCRIPT or
        ARGS. So ``SYM`` is never present without ``SCRIPT`` and adding it to
        the test cannot change the outcome.

        MEASURED: a counter on "SYM set and SCRIPT not set" stayed at 0 over
        205,588 inputs; an exhaustive search over 271,452 short strings found
        no disagreement. Asserted here as the source fact.
        """
        source = pathlib.Path(_module.__file__).read_text(encoding="utf-8")
        body = source.split("def _postfixes")[1].split("\n    def ")[0]
        sym_lines = [ln.strip() for ln in body.splitlines()
                     if "SYM" in ln and "|=" in ln]
        assert sym_lines == ["ev |= SYM | SCRIPT"], sym_lines

    def test_the_plusplus_word_start_lookbehind_is_implied_by_greed(self):
        """EQUIVALENT MUTANT, no test possible: dropping ``(?<![^\\W_])``
        from ``_PLUSPLUS_RE`` (M72).

        REASON: ``finditer`` scans left to right and ``[^\\W_]+`` is greedy,
        so if the pattern matches from position i with a word character at
        i-1, it also matches from i-1 and the earlier match is the one
        reported. The lookbehind can therefore only ever agree with the
        scan order it duplicates.

        MEASURED: 0 disagreements over 505,614 inputs and over every one of
        the 55,986 strings of length <= 6 from ``aA1+_é``. Asserted here by
        comparing the two patterns over the shapes the argument is about.
        """
        loose = re.compile(r"[^\W_]+\+{2,}")
        for text in ("C++", "Gauss2++", "a_b++", "_C++", "x1++", "é++",
                     "abc++", "1+1", "3x+1", "The Gauss2++ model"):
            assert ([m.span() for m in _module._PLUSPLUS_RE.finditer(text)]
                    == [m.span() for m in loose.finditer(text)]), text

    def test_an_echo_inside_an_existing_span_is_absorbed_by_the_merge(self):
        """EQUIVALENT MUTANT, no test possible: dropping ``not claimed[i]``
        from ``_echo`` (M75).

        REASON: the branch IS taken -- 665 times over 205,614 inputs -- but
        ``claimed`` is built from exactly the span list ``_echo``'s result is
        merged into, so an index with ``claimed[i]`` already lies inside a
        span and ``_merge`` absorbs the duplicate ``(i, i+1)`` without
        changing anything. The guard saves work, not an answer.

        MEASURED: 0 disagreements over 505,614 inputs and over all 111,110
        strings of length <= 5 from a ten-character alphabet. Asserted here
        as the property of ``_merge`` that makes it true.
        """
        base = [(2, 9), (14, 20)]
        for i in (2, 5, 8, 14, 19):
            assert _module._merge(base + [(i, i + 1)]) == _module._merge(base)


# ══════════════════════════════════════════════════════════ the ratchet ══

class TestTheScoreDoesNotRegress:
    """Per-case tests catch a regression on a case someone thought of. They
    say nothing about the 25,049 titles nobody pointed them at. Three
    successive implementations passed their own unit tests while one called
    "é" mathematics 4,331 times and another claimed 49.6% of an average
    title. Unit tests were not the missing instrument -- a population was.

    MEASURED 2026-08-25 on the 345-title corpus: precision 1.0000, recall
    0.9962, exactly right on 343 of 345, claiming 3.91% of the corpus's
    26,555 characters against a gold 3.92%. The floors below sit just under
    those, so an improvement need not edit the test and a regression must
    fail it.

    WHERE THE RATCHET LIVES. ``tests/test_core/test_math_regions_scored.py``
    is the canonical one and carries the same floors, plus the two
    PER-STRATUM floors this class does not: 164 of the 166 positive titles
    exactly right, and 179 of the 179 negative titles clean. That file used
    to carry the SCANNER's floors (0.67 / 0.86 / 270), which pass unchanged
    at 1.000 / 0.996 / 343 -- so the whole measured gain sat unprotected and
    a regression all the way back to P 0.68 would have gone green. It was
    raised on 2026-08-25, in the same change that added this class's
    counterparts there.

    This class is kept even so, because these two files travel together and
    a suite that can be run on its own should be able to say whether the
    module still scores what it claims.
    """

    @staticmethod
    def _chars(spans_):
        out = set()
        for s, e in spans_:
            out |= set(range(s, e))
        return out

    @pytest.fixture(scope="class")
    def scored(self, corpus):
        tp = fp = fn = exact = 0
        claimed = total = 0
        for row in corpus:
            gold = self._chars(row["math_spans"])
            got = self._chars(find_math_regions(row["title"]))
            tp += len(gold & got)
            fp += len(got - gold)
            fn += len(gold - got)
            exact += gold == got
            claimed += len(got)
            total += len(row["title"])
        return {
            "precision": tp / (tp + fp) if tp + fp else 1.0,
            "recall": tp / (tp + fn) if tp + fn else 1.0,
            "exact": exact,
            "share": claimed / total,
        }

    def test_precision(self, scored):
        assert scored["precision"] >= 0.99, (
            f"precision fell to {scored['precision']:.4f}; it was 1.0000. "
            "Over-claiming means the caser is told prose is mathematics and "
            "leaves it alone -- titles silently stop being normalised."
        )

    def test_recall(self, scored):
        assert scored["recall"] >= 0.99, (
            f"recall fell to {scored['recall']:.4f}; it was 0.9962. "
            "Under-claiming means the caser RECASES REAL MATHEMATICS: "
            "'L^2' becomes 'l^2', 'AR(1)' becomes 'Ar(1)'."
        )

    def test_exactly_right_on_almost_every_title(self, scored):
        assert scored["exact"] >= 340, (
            f"exact-match titles fell to {scored['exact']}; it was 343. "
            "The two it never got are pinned in TestDeclaredPrices."
        )

    def test_the_average_claim_stays_near_the_true_coverage(self, scored):
        """The scanner averaged 49.6%. The gold labels 3.92% of the corpus's
        characters and this module claims 3.91%; a ceiling of 5% is tight
        enough to be worth having, where the previous 12% was not."""
        assert scored["share"] <= 0.05, (
            f"claims {scored['share']:.2%} of the corpus; gold is 3.92%"
        )

    def test_the_fixture_still_describes_itself(self):
        """A fixture that loses its conventions cannot be re-labelled later,
        and two tests in this file (the bracket-trimming convention and the
        acronym boundary) are only meaningful with the README beside them."""
        doc = json.loads(_FIXTURE.read_text())
        assert "_readme" in doc
        assert "acronym" in doc["_readme"].lower()
        assert "brackets are trimmed" in doc["_readme"].lower()
