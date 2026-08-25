#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for core.math_tokenization — the math-aware tokeniser.

WHAT THIS MODULE IS FOR, and therefore what these tests defend
--------------------------------------------------------------
``robust_tokenize_with_math`` cuts a title into tokens so that a CASER can
rewrite the prose ones and must not touch the rest.  Everything below follows
from that single sentence:

  * **one MATH token per formula.**  A formula split across two MATH tokens
    leaves the characters between them — an operator, a comma, a space — in
    the prose stream, where a caser may rewrite them.  A formula whose
    delimiters fall outside its MATH token has the same disease.
  * **the partition invariant.**  ``"".join(t.value for t in tokens) == text``
    with contiguous, non-overlapping offsets, so the caser can reassemble the
    title byte-for-byte.  There is exactly one deliberate exception (the
    suffix-duplication branch); it is tested by name below rather than avoided.
  * **no MATH token is ordinary prose.**  Protecting English is as wrong as
    failing to protect maths: "(Almost) Everything you always wanted to know"
    must reach the caser intact.

HOW THIS FILE CHANGED, and why
------------------------------
This file was rewritten when ``core/math_regions.py`` was replaced by the
delimiter-aware implementation.  Three kinds of change were made, and each
individual test says which kind it is:

  1. **Tests that still pass are kept**, most of them verbatim.  All 35 of the
     previous file's tests pass against the landing module; none was dropped.
  2. **Tests that never tested their stated subject** were rewritten against
     the MEASURED behaviour, with a docstring saying what the old expectation
     got wrong.  Seven were in this category — a "smart quote" case that used
     an ASCII apostrophe twice, a "fallback" case that never reached the
     fallback, a "priority" case where nothing had priority over anything, a
     "trailing word" case whose only assertion was discarded, and three that
     asserted ``len(...) > 0`` on output that was garbage.
  3. **Missing coverage was added**: the partition invariant over real data,
     one-token-per-formula over the corpus's 201 hand-labelled formulas, the
     179 hand-labelled NEGATIVE titles, the tokeniser's own private display-
     math rule, and the branch-by-branch well-formedness of Token.

THE LATEX DECISION: **SUPPORTED**.  ``$…$``, ``$$…$$``, ``\\[…\\]``,
``\\(…\\)``, ``\\begin{env}…\\end{env}`` and bare ``\\command{…}`` each return
exactly ONE span INCLUDING its delimiters.  The library contains no LaTeX
(measured: 0 of 25,049 unique reliable titles contain a "$", a backslash or a
"\\begin{"), but ``find_math_regions`` is read by CODE, and the titles that
code sees come from ``processing/ingest.py``, i.e. from arXiv and Crossref,
which are LaTeX sources whose ``$`` and ``\\alpha`` pass through
``ingest._unlatex`` untouched.  So the LaTeX tests are kept and EXPANDED
rather than deleted or skipped.

Every number quoted in a docstring below was measured by running this module
against the landing implementation; none is an estimate.
"""

from __future__ import annotations

import json
import os
import re as _stdlib_re
from pathlib import Path

import pytest
import regex as re

from core.math_tokenization import (
    robust_tokenize_with_math,
    DASH_CHARS,
    _SEGMENT_RE,
)
from core.math_regions import find_math_regions


# ────────────────────────────────────────────────────────────── the corpus ──
#
# tests/fixtures/math_regions_ground_truth.json: 345 library titles drawn by
# seeded stratified sampling from the 25,049 unique reliable titles, hand
# labelled — 201 spans, 1,042 protected characters, 166 positive / 179
# negative.  It is the only oracle in this file that is not a hand-written
# example, and it is the reason the corpus tests below are worth more than
# the literal ones.

_FIXTURE_NAME = "math_regions_ground_truth.json"


def _find_fixture() -> Path | None:
    """Locate the ground-truth corpus, or return None with the reason visible.

    From ``tests/core/`` this resolves to ``tests/fixtures/``.  The env var
    exists so the file can also be run from a scratch directory during a
    landing rehearsal.  If it resolves to nothing the corpus tests SKIP with a
    reason rather than passing vacuously — "I didn't look" and "it's fine"
    must not be the same result.
    """
    env = os.environ.get("MATH_REGIONS_GROUND_TRUTH")
    if env:
        p = Path(env)
        return p if p.is_file() else None
    here = Path(__file__).resolve()
    for anc in (here.parent, *here.parents):
        for cand in (anc / "fixtures" / _FIXTURE_NAME,
                     anc / "tests" / "fixtures" / _FIXTURE_NAME):
            if cand.is_file():
                return cand
    return None


_FIXTURE_PATH = _find_fixture()

if _FIXTURE_PATH is not None:
    _GROUND_TRUTH = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    LABELLED = _GROUND_TRUTH["labelled"]
else:                                                    # pragma: no cover
    LABELLED = []

POSITIVES = [it for it in LABELLED if it["math_spans"]]
NEGATIVES = [it for it in LABELLED if not it["math_spans"]]

needs_corpus = pytest.mark.skipif(
    _FIXTURE_PATH is None,
    reason=(
        "ground-truth corpus not found: expected tests/fixtures/"
        f"{_FIXTURE_NAME} or $MATH_REGIONS_GROUND_TRUTH. The corpus-level "
        "properties are UNKNOWN in this run, not OK."
    ),
)


# ───────────────────────────────────────────────────────────────── helpers ──

def kinds(tokens):
    return [t.kind for t in tokens]


def values(tokens):
    return [t.value for t in tokens]


def math_values(tokens):
    return [t.value for t in tokens if t.kind == "MATH"]


def phrase_values(tokens):
    return [t.value for t in tokens if t.kind == "PHRASE"]


def assert_partition(text, tokens, *, allow_suffix_duplicates=False):
    """The invariant the caser depends on: tokens tile *text* exactly.

    Contiguous, non-overlapping, non-empty, ``value == text[start:end]``, and
    reassembling in order gives back the input byte-for-byte.

    ``allow_suffix_duplicates`` covers the ONE deliberate exception — the
    suffix-duplication branch at math_tokenization.py:168 emits a WORD token
    that overlaps the PHRASE token before it.  See
    ``TestSuffixDuplicationBranch``.
    """
    stream = []
    for tok in tokens:
        assert tok.end > tok.start, f"empty-width token {tok!r} in {text!r}"
        assert 0 <= tok.start < tok.end <= len(text), f"out of range {tok!r}"
        assert tok.value == text[tok.start:tok.end], f"value/offset skew {tok!r}"
        if allow_suffix_duplicates and stream and tok.start < stream[-1].end:
            # the duplicate suffix WORD: must sit strictly inside its
            # predecessor and must not advance the cursor
            assert tok.kind == "WORD" and stream[-1].kind == "PHRASE"
            assert stream[-1].start <= tok.start and tok.end == stream[-1].end
            continue
        stream.append(tok)

    prev = 0
    for tok in stream:
        assert tok.start == prev, f"gap/overlap before {tok!r} in {text!r}"
        prev = tok.end
    assert prev == len(text) if text else stream == [], f"short tokenisation of {text!r}"
    assert "".join(t.value for t in stream) == text


# The dash characters DASH_CHARS actually stands for.  DASH_CHARS itself is a
# regex-character-class FRAGMENT whose first character is a backslash escaping
# the ASCII hyphen — see TestDashChars — so it cannot be iterated naively.
REAL_DASHES = ("-", "–", "—", "‐", "−")


# ══════════════════════════════════════════════════════════════════════════
class TestDashChars:
    """DASH_CHARS — the dash alphabet the phrase matcher works over.

    docs/reference_dash_convention.md records en dash vs hyphen as a real,
    measured library distinction (en dash = two co-equal entities,
    Hamilton–Jacobi; hyphen = one word from parts, mean-field).  The constant
    is therefore load-bearing: a dash spelling missing from it would make one
    written form of a compound a different token from another.
    """

    def test_dash_chars_content(self):
        """KEPT.  Every dash spelling the library uses is in the constant."""
        for dash in REAL_DASHES:
            assert dash in DASH_CHARS

    def test_dash_chars_is_a_regex_class_fragment_not_a_dash_alphabet(self):
        """NEW.  DASH_CHARS is source text for ``[...]``, not a set of dashes.

        MEASURED: ``DASH_CHARS == '\\\\-–—‐−'`` — six characters, of which the
        first is U+005C REVERSE SOLIDUS, present only to escape the ASCII
        hyphen that follows it so the class cannot be read as a range.  It is
        NOT a dash, and the class it is spliced into does not match it.

        This matters beyond pedantry.  math_tokenization.py:44 asks
        ``any(d in ph for d in DASH_CHARS)`` to decide whether a caller's
        phrase is dash-separated, and that membership test iterates the escape
        character too — so a phrase containing a backslash is misrouted to the
        dash branch.  The consequence is pinned in
        ``TestPhraseRegexLimitations::test_backslash_in_dash_chars_misroutes_a_latex_phrase``.
        """
        assert DASH_CHARS[0] == "\\", "the escape must lead, or '-' opens a range"
        assert DASH_CHARS[1] == "-"
        assert set(DASH_CHARS) - {"\\"} == set(REAL_DASHES)

        klass = re.compile(rf"[{DASH_CHARS}]+")
        assert klass.search("\\") is None, (
            "the backslash is an escape, not a member of the class"
        )

    def test_dash_chars_regex_usage(self):
        """REWRITTEN.  Drive the check from the constant, not a hand copy.

        The old version compiled ``[{DASH_CHARS}]+`` and searched four
        hand-written strings, so U+2010 HYPHEN — asserted present by
        ``test_dash_chars_content`` — was never once compiled or matched.  A
        sixth dash added to the constant would have gone unexercised in the
        same way.  Iterating the constant closes that.
        """
        klass = re.compile(rf"[{DASH_CHARS}]+")
        for ch in DASH_CHARS:
            if ch == "\\":
                continue
            assert klass.fullmatch(ch), f"U+{ord(ch):04X} not matched by its own class"
            assert klass.search(f"left{ch}right"), f"U+{ord(ch):04X} unmatched in situ"

    @pytest.mark.parametrize("text_dash", REAL_DASHES, ids=lambda c: f"text-U+{ord(c):04X}")
    @pytest.mark.parametrize("phrase_dash", REAL_DASHES, ids=lambda c: f"phrase-U+{ord(c):04X}")
    def test_every_dash_spelling_gives_the_same_phrase_boundaries(
        self, text_dash, phrase_dash
    ):
        """NEW.  The co-variance the constant exists to provide.

        A phrase written with any dash must match a title written with any
        other dash, and the token must carry the text AS FOUND, not as
        whitelisted — otherwise "Black–Scholes" in a title would silently be a
        different token from "Black-Scholes" and one of them would go
        unprotected.  All 25 combinations are exercised; MEASURED: all 25 match.
        """
        text = f"The Black{text_dash}Scholes model works"
        tokens = robust_tokenize_with_math(text, [f"Black{phrase_dash}Scholes"])
        assert phrase_values(tokens) == [f"Black{text_dash}Scholes"]
        assert_partition(text, tokens)

    @pytest.mark.parametrize("dash", REAL_DASHES, ids=lambda c: f"U+{ord(c):04X}")
    def test_space_separated_phrase_matches_every_dash_spelling(self, dash):
        """NEW.  The hyphen-variant pass must cover the whole dash alphabet.

        math_tokenization.py:99-109 hard-codes its own dash class
        ``[‐\\-–—−]`` rather than reusing DASH_CHARS.  MEASURED: it does in
        fact cover all five, but nothing said so, and the duplication is
        exactly the "one rule, one implementation" shape that drifts.
        """
        text = f"The Black{dash}Scholes model works"
        tokens = robust_tokenize_with_math(text, ["Black Scholes"])
        assert phrase_values(tokens) == [f"Black{dash}Scholes"]


# ══════════════════════════════════════════════════════════════════════════
class TestSegmentRegex:
    """_SEGMENT_RE — the ordinary-text scanner underneath the tokeniser."""

    def test_space_matching(self):
        """KEPT.  A maximal whitespace run is ONE SPACE segment."""
        text = "   \t\n  "
        match = _SEGMENT_RE.match(text)
        assert match is not None
        assert match.lastgroup == "SPACE"
        assert match.group() == text

    def test_punct_matching(self):
        """KEPT.  Every non-word non-space character is PUNCT, one at a time.

        Punctuation can therefore never be absorbed into a WORD.  Note that
        ``\\`` and ``$`` are in this list: they are the characters that would
        leak into the prose stream if a LaTeX formula's delimiters ever fell
        outside its MATH token.  See ``TestLatexIsOneSpanWithItsDelimiters``.
        """
        punctuation = "!@#$%^&*()[]{}|\\:;\"<>?,./"
        for char in punctuation:
            match = _SEGMENT_RE.match(char)
            assert match is not None
            assert match.lastgroup == "PUNCT"
            assert match.group() == char

    def test_ascii_apostrophe_is_deliberately_not_punct(self):
        """NEW.  The negative half of the PUNCT class, which nothing stated.

        The pattern is ``[^\\w\\s'']`` — the apostrophes are EXCLUDED so that
        ``don't`` can be held together by the WORD alternative.  The cost is
        that a bare U+0027 matches nothing at all; that is the one input that
        reaches the single-character fallback, and it is tested below.
        """
        assert _SEGMENT_RE.match("'") is None

    def test_word_matching_plain(self):
        """KEPT."""
        match = _SEGMENT_RE.match("hello")
        assert match is not None
        assert match.lastgroup == "WORD"
        assert match.group() == "hello"

    def test_word_matching_ascii_apostrophe_suffix(self):
        """KEPT.  ``don't`` is ONE WORD, not three tokens a caser recases."""
        for word in ("don't", "won't", "Ito's"):
            match = _SEGMENT_RE.match(word)
            assert match is not None
            assert match.lastgroup == "WORD"
            assert match.group() == word

    def test_word_matching_typographic_apostrophe_holds_together(self):
        """PINNED THE BUG, NOW PINS THE FIX.

        The original third case here was labelled "Word with smart quote"
        and used an ASCII apostrophe again — a byte-for-byte duplicate of
        the case above it. So the file claimed coverage of a construct it
        had never once run, which is how ``['']`` (U+0027 twice, U+2019
        never) survived in the pattern.

        This test then deliberately PINNED the broken answer, so that "the
        day the class is fixed this test fails and points at the change".
        That is exactly what happened. 1,116 of the 25,049 real library
        titles contain U+0027 and 444 contain U+2019; both now tokenise
        the same way.
        """
        match = _SEGMENT_RE.match("don’t")
        assert match is not None
        assert match.lastgroup == "WORD"
        assert match.group() == "don’t", (
            "the typographic apostrophe must hold the word together, exactly "
            "as the ASCII one does"
        )

        text = "Itô’s formula"
        tokens = robust_tokenize_with_math(text)
        assert values(tokens) == ["Itô’s", " ", "formula"]
        assert_partition(text, tokens)

    def test_both_apostrophes_should_tokenise_alike(self):
        """THE CO-VARIANCE PROPERTY, now holding.

        Two spellings of a possessive must not produce different token
        boundaries — the same reason "-" and U+2212 must decompose alike.
        Was xfail(strict) until the character class was fixed to hold
        U+0027 once and U+2019 once, instead of U+0027 twice.
        """
        ascii_tokens = robust_tokenize_with_math("Ito's formula")
        smart_tokens = robust_tokenize_with_math("Ito’s formula")
        assert kinds(ascii_tokens) == kinds(smart_tokens)

    def test_the_only_no_match_input_is_the_ascii_apostrophe(self):
        """REWRITTEN.  The old test's only executed assertion was that the
        empty string does not match; the rest of it was a comment reading
        "Most characters should match one of the patterns".  It therefore did
        not test the property in its name.

        MEASURED: there is exactly one reachable no-match character.  U+0027
        is excluded from PUNCT, is not ``\\w`` and is not ``\\s``, so
        ``_SEGMENT_RE.match("'")`` is None and the single-character fallback
        at math_tokenization.py:182-185 fires.  That branch had NO test.
        """
        assert _SEGMENT_RE.match("") is None
        assert _SEGMENT_RE.match("'") is None

        tokens = robust_tokenize_with_math("'")
        assert len(tokens) == 1
        assert (tokens[0].kind, tokens[0].value, tokens[0].start, tokens[0].end) == (
            "PUNCT", "'", 0, 1
        )

    def test_fallback_advances_the_scan_and_preserves_the_partition(self):
        """NEW.  The fallback must advance ``i`` or the tokeniser loops.

        Termination on adversarial input was asserted nowhere in the old file.
        A trailing apostrophe is the shortest input that both reaches the
        fallback and has something after it to get wrong.
        """
        for text in ("a'", "'a", "''", "Ito' 'Ito", "'" * 50):
            tokens = robust_tokenize_with_math(text)
            assert_partition(text, tokens)

    def test_zero_width_space_goes_through_punct_not_the_fallback(self):
        """NEW.  Records the fact the old ``test_fallback_tokenization`` got
        wrong.  It fed U+200B ZERO WIDTH SPACE believing it reached the
        fallback; MEASURED, U+200B has Unicode category Cf, so it is neither
        ``\\w`` nor ``\\s`` and DOES match the PUNCT alternative.  The old
        assertion (``len(tokens) >= 3``) was loose enough to pass either way.
        """
        match = _SEGMENT_RE.match("​")
        assert match is not None and match.lastgroup == "PUNCT"

        text = "a​b"
        tokens = robust_tokenize_with_math(text)
        assert kinds(tokens) == ["WORD", "PUNCT", "WORD"]
        assert values(tokens) == ["a", "​", "b"]
        assert_partition(text, tokens)


# ══════════════════════════════════════════════════════════════════════════
class TestPartitionInvariant:
    """The tokens must tile the input exactly.

    This is the property the caser's correctness rests on: it reassembles the
    title from the token stream, so a gap, an overlap or a value/offset skew
    silently corrupts a filename.  MEASURED over all 25,049 real library
    titles: 25,049/25,049 hold.  The old file checked it once, on
    ``"Hello world"``, inside a test whose real subject was ``$x$``.
    """

    @pytest.mark.parametrize(
        "text,phrases",
        [
            ("", None),
            ("Hello world", None),
            ("Hello, world!", None),
            ("$x + y = z$", None),
            ("\\[f(x) = x^2\\]", None),
            ("A variant on (2Jₛ-Rₛ, s≥0) for processes", None),
            ("L^∞:L¹ duality results in optimal control problems", None),
            ("The α-stable process", ["α-stable"]),
            ("The Black  Scholes model", ["Black Scholes"]),
            ("Hello $x$ world", None),
            ("a'", None),
            ("a​b", None),
            ("Itô’s formula", None),
            ("   ", None),
            ("Nested: $a + \\frac{$b$}{c}$ complex", None),
        ],
    )
    def test_partition_holds_on_every_branch(self, text, phrases):
        """NEW.  One input per branch of the linear scan: phrase, math,
        word, space, punct, and the single-character fallback."""
        assert_partition(text, robust_tokenize_with_math(text, phrases))

    @needs_corpus
    def test_partition_holds_on_every_corpus_title(self):
        """NEW.  The honest version: 345 real hand-labelled library titles.

        MEASURED: 345/345 hold, with 0 round-trip failures, 0 gaps, 0
        overlaps and 0 value/offset skews.  This was cheap and was never done.
        """
        broken = []
        for item in LABELLED:
            title = item["title"]
            try:
                assert_partition(title, robust_tokenize_with_math(title))
            except AssertionError as exc:              # pragma: no cover
                broken.append((title, str(exc)))
        assert not broken, f"{len(broken)} of {len(LABELLED)} titles: {broken[:3]}"

    @pytest.mark.parametrize(
        "text",
        [
            "word " * 1000,
            "x^2 " * 400,
            "(" * 500 + "a" + ")" * 500,
            "$" * 800,
            "\\begin{a}" * 200,
            "L_∞^2" * 300,
            "α_i + β^j = γ, " * 200,
            "a_" * 1000,
            "  a  ^ 2  " * 300,
            "−" * 600,
            "'" * 600,
        ],
        ids=[
            "plain-words", "dense-scripts", "nested-brackets", "dollars-only",
            "begin-envs", "glued-scripts", "greek-relations", "trailing-underscores",
            "spaced-carets", "minus-run", "apostrophe-run",
        ],
    )
    def test_partition_and_termination_on_adversarial_length(self, text):
        """NEW.  The old length test was ``"word " * 1000`` — no math, no
        phrases, no punctuation.  That is a length test, not a stress test.

        core/math_regions.py carries an explicit 400-character notation bound
        and a six-space chain budget; none of them was exercised by plain
        words.  These inputs are long AND dense in anchors.  MEASURED: every
        one terminates in under 20 ms and tiles exactly.
        """
        assert_partition(text, robust_tokenize_with_math(text))


# ══════════════════════════════════════════════════════════════════════════
class TestSuffixDuplicationBranch:
    """math_tokenization.py:143-149 and :160-168 — ``_appears_outside``.

    When the last word of a PHRASE also occurs OUTSIDE every phrase, a
    duplicate WORD token is emitted for it so a downstream vocabulary pass can
    still see the word.  This branch deliberately BREAKS the partition
    invariant: the emitted WORD overlaps the PHRASE it follows.

    The old ``test_trailing_word_detection`` named this branch, then computed
    a list comprehension and threw the result away; the two comments beneath
    it described assertions that were never written.  The branch had no
    assertion anywhere in the file, and the exception it makes to the
    partition invariant was an accident rather than a written-down decision.
    """

    PHRASE = "Black-Scholes model"

    def test_suffix_is_duplicated_when_it_recurs_outside_every_phrase(self):
        """REWRITTEN, and with the input corrected.

        The old test used ``"Black-Scholes model and more Black-Scholes
        stuff"``, where the trailing word of the phrase is "model" and "model"
        does NOT recur — so even a correct assertion would have exercised the
        negative side while claiming the positive.  MEASURED with a text where
        "model" really does recur, the branch fires.
        """
        text = "Black-Scholes model and the binomial model"
        tokens = robust_tokenize_with_math(text, [self.PHRASE])

        assert phrase_values(tokens) == ["Black-Scholes model"]
        assert (tokens[0].start, tokens[0].end) == (0, 19)

        # the duplicate, overlapping its own phrase
        assert tokens[1].kind == "WORD"
        assert tokens[1].value == "model"
        assert (tokens[1].start, tokens[1].end) == (14, 19)

        assert_partition(text, tokens, allow_suffix_duplicates=True)

    def test_suffix_is_not_duplicated_when_it_does_not_recur(self):
        """NEW.  The refusal half — "when and ONLY when"."""
        text = "Black-Scholes model and the binomial tree"
        tokens = robust_tokenize_with_math(text, [self.PHRASE])

        assert phrase_values(tokens) == ["Black-Scholes model"]
        assert [t.value for t in tokens if t.kind == "WORD"] == [
            "and", "the", "binomial", "tree"
        ]
        assert_partition(text, tokens)

    def test_a_recurrence_inside_another_phrase_does_not_count(self):
        """NEW.  ``_appears_outside`` requires the recurrence to be outside
        ALL phrases; a second copy that is itself inside a phrase must not
        trigger the duplicate."""
        text = "Black-Scholes model and Heston model too"
        tokens = robust_tokenize_with_math(text, [self.PHRASE, "Heston model"])
        assert phrase_values(tokens) == ["Black-Scholes model", "Heston model"]
        assert [t.value for t in tokens if t.kind == "WORD"] == ["and", "too"]

    def test_the_duplicate_is_the_only_exception_to_the_partition(self):
        """NEW.  Nail the exception down so it cannot widen quietly: the
        overlapping token is a WORD, it sits at the END of its PHRASE, and it
        never advances the scan."""
        text = "Black-Scholes model and the binomial model"
        tokens = robust_tokenize_with_math(text, [self.PHRASE])
        overlaps = [
            (a, b) for a, b in zip(tokens, tokens[1:]) if b.start < a.end
        ]
        assert len(overlaps) == 1
        phrase_tok, dup = overlaps[0]
        assert phrase_tok.kind == "PHRASE" and dup.kind == "WORD"
        assert dup.end == phrase_tok.end
        assert phrase_tok.value.endswith(dup.value)


# ══════════════════════════════════════════════════════════════════════════
class TestLatexIsOneSpanWithItsDelimiters:
    """THE LATEX DECISION IS **SUPPORTED**.  See the module docstring.

    A delimited formula is ONE MATH token INCLUDING its delimiters, and the
    grammar does not see inside it.  The alternative that was rejected —
    parsing the payload and leaving the delimiters outside — is WORSE than
    refusing: ``\\[f(x) = x^2\\]`` produced one span ``f(x) = x^2`` and
    spilled ``\\``, ``[`` and ``]`` into the prose stream, which is precisely
    the stream a caser rewrites.

    Population, measured, and stated so the decision is not mistaken for
    evidence: 0 of the 25,049 unique reliable library titles, 0 of the 25,187
    unique in-scope raw stems and 0 of the 345 corpus titles contain a "$", a
    backslash or a "\\begin{".  The justification is the CODE path
    (processing/move_normalizer.py -> validators/filename_checker/core.py ->
    core/sentence_case.py -> this module), whose inputs come from arXiv and
    Crossref via processing/ingest.py, not the library.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "$x + y = z$",
            "$$E = mc^2$$",
            "\\[f(x) = x^2\\]",
            "\\(a+b\\)",
            "\\begin{equation} E = mc^2 \\end{equation}",
            "\\begin{align} a &= b \\end{align}",
            "$\\alpha \\leq \\beta$",
            "\\mathbb{R}^n",
            "\\alpha_i",
            "$\\sum_{i=1}^{n} x_i$",
        ],
    )
    def test_a_whole_formula_input_is_exactly_one_math_token(self, text):
        """KEPT AND EXPANDED from ``test_only_math``.

        No leading or trailing residue: the token IS the input.  MEASURED: all
        ten forms give exactly one token.
        """
        tokens = robust_tokenize_with_math(text)
        assert len(tokens) == 1
        assert tokens[0].kind == "MATH"
        assert tokens[0].value == text
        assert (tokens[0].start, tokens[0].end) == (0, len(text))

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("The formula $x + y = z$ is simple", "$x + y = z$"),
            ("Display math: $$E = mc^2$$ is famous", "$$E = mc^2$$"),
            ("Equation: \\[f(x) = x^2\\] shown", "\\[f(x) = x^2\\]"),
            ("Inline \\(a+b\\) here", "\\(a+b\\)"),
            ("Set \\begin{equation} E = mc^2 \\end{equation} done",
             "\\begin{equation} E = mc^2 \\end{equation}"),
            ("The set \\mathbb{R} here", "\\mathbb{R}"),
        ],
    )
    def test_embedded_formula_keeps_its_delimiters_inside_the_token(self, text, expected):
        """KEPT (``test_math_detection``, ``test_bracket_math_detection``) and
        EXPANDED.  The value assertion is the point: ``len == 1`` alone passed
        even when the delimiters had been left outside."""
        tokens = robust_tokenize_with_math(text)
        assert math_values(tokens) == [expected]
        assert_partition(text, tokens)

    @pytest.mark.parametrize(
        "text",
        [
            "Equation: \\[f(x) = x^2\\] shown",
            "The formula $x + y = z$ is simple",
            "Set \\begin{equation} E = mc^2 \\end{equation} done",
            "The set \\mathbb{R} here",
        ],
    )
    def test_no_delimiter_character_reaches_the_prose_stream(self, text):
        """NEW.  The property the delimiter-inclusion rule exists to buy.

        Every ``$``, ``\\``, ``[``, ``]``, ``(``, ``)``, ``{`` and ``}`` that
        belongs to a formula must be inside a MATH token, because the caser
        reads the tokens that are not MATH.  The old bracket test asserted
        this only through one string comparison; this asserts it as a property
        of the whole non-MATH stream.
        """
        tokens = robust_tokenize_with_math(text)
        prose = "".join(t.value for t in tokens if t.kind != "MATH")
        assert "$" not in prose
        assert "\\" not in prose

    def test_two_formulas_are_two_tokens_not_one(self):
        """NEW.  Delimiter pairing must not run greedily across a gap."""
        text = "$2 \\times 2$ and $3 \\times 3$"
        tokens = robust_tokenize_with_math(text)
        assert math_values(tokens) == ["$2 \\times 2$", "$3 \\times 3$"]
        assert_partition(text, tokens)

    def test_a_long_formula_is_not_split_by_a_length_bound(self):
        """NEW.  The Black-Scholes PDE, 96 characters.

        REPLACES the assertion in the old ``test_mixed_content_tokenization``.
        core/math_regions.py's own comment records that an 80-character bound
        once returned this formula as six spans; one MATH token is the
        contract, and the surrounding prose must tokenise normally around it.
        """
        formula = (
            "$\\frac{\\partial V}{\\partial t} + \\frac{1}{2}\\sigma^2 S^2 "
            "\\frac{\\partial^2 V}{\\partial S^2} = rV$"
        )
        text = f"The Black-Scholes formula {formula} is fundamental."
        tokens = robust_tokenize_with_math(text, ["Black-Scholes"])

        assert math_values(tokens) == [formula]
        assert phrase_values(tokens) == ["Black-Scholes"]
        word_values = [t.value for t in tokens if t.kind == "WORD"]
        assert "formula" in word_values
        assert "fundamental" in word_values
        assert "partial" not in word_values, "formula interior leaked into prose"
        assert_partition(text, tokens)

    @pytest.mark.parametrize(
        "text",
        [
            "The $5 trillion question and the $100 answer",
            "A $100 bill and a $50 note",
            "Pricing at $50 per share",
        ],
    )
    def test_dollars_that_are_money_are_refused(self, text):
        """NEW.  ``$`` is the one delimiter with a competing reading, and this
        is a mathematical FINANCE library.  A dollar pair whose payload reads
        as ordinary English words is refused; the backslash forms have no
        competing reading and carry no such guard.

        Without this, a caser would be forbidden from touching a sentence
        about money — the mirror image of the failure the whole module exists
        to prevent.
        """
        assert math_values(robust_tokenize_with_math(text)) == []


# ══════════════════════════════════════════════════════════════════════════
class TestOneMathTokenPerFormula:
    """The tokeniser's central contract, stated on the population that exists.

    The old file stated it on LaTeX, which the library does not contain.  The
    corpus contains 201 hand-labelled formulas; that is the right oracle.

    MEASURED against the landing implementation, through the tokeniser: 199 of
    201 gold formulas give exactly one full MATH token, 0 partial, 0 split, 2
    missed — and both misses are documented REFUSALS in the module docstring.
    (For comparison, recorded so the ratchet is visible: the implementation
    this replaced gave 111 full, 58 partial, 9 split and 23 missed.)
    """

    #: Both are refusals decided in core/math_regions.py's REFUSALS section,
    #: not oversights.  "1:2" meaning one half is lexically identical to
    #: "Séminaire Bourbaki, volume 2012:2013"; a bare "e" for Euler's number
    #: cannot be told from an article without semantics.
    EXPECTED_MISSES = {
        ("New Wallis- and Catalan-type infinite products for π, e, "
         "and sqrt{2 + sqrt{2}}", 54, 55),
        ("Differential equations driven by Hölder continuous functions "
         "of order greater than 1:2", 83, 86),
    }

    @needs_corpus
    def test_every_gold_formula_is_exactly_one_full_math_token(self):
        """NEW.  One MATH token per formula, over 201 real formulas.

        A formula that arrives as two MATH tokens has left the characters
        between them in the prose stream; one that arrives as a partial token
        has left its edges there.  Both are reported separately from a miss,
        because they are different failures.
        """
        split, partial, missed = [], [], []
        full = 0
        for item in LABELLED:
            title = item["title"]
            got = [(t.start, t.end) for t in robust_tokenize_with_math(title)
                   if t.kind == "MATH"]
            for gs, ge in item["math_spans"]:
                touching = [(s, e) for s, e in got if s < ge and e > gs]
                if len(touching) == 1 and touching[0] == (gs, ge):
                    full += 1
                elif not touching:
                    missed.append((title, gs, ge))
                elif len(touching) > 1:
                    split.append((title, title[gs:ge], [title[s:e] for s, e in touching]))
                else:
                    partial.append((title, title[gs:ge], title[touching[0][0]:touching[0][1]]))

        assert not split, f"{len(split)} formulas torn across MATH tokens: {split[:3]}"
        assert not partial, f"{len(partial)} formulas partially claimed: {partial[:3]}"
        assert set(missed) == self.EXPECTED_MISSES, (
            "the set of refused formulas changed; if a refusal was fixed, "
            "remove it from EXPECTED_MISSES and say so.\n"
            f"  unexpected misses: {sorted(set(missed) - self.EXPECTED_MISSES)}\n"
            f"  no longer missed:  {sorted(self.EXPECTED_MISSES - set(missed))}"
        )
        assert full == 199, f"expected 199 exact formulas, measured {full}"

    @needs_corpus
    def test_no_hand_labelled_negative_title_gets_a_math_token(self):
        """NEW.  The negative side of the operational definition, on real data.

        The corpus holds 179 hand-labelled NEGATIVE titles — parenthesised
        English glosses, lexical acronyms (BSDE, PDE, BMO), Roman numerals,
        year ranges, en-dashed proper-name compounds.  None of them appeared
        anywhere in the old file, which stated the negative side once, on
        ``"Hello world"``.

        MEASURED: 0 of 179 produce a MATH token.
        """
        offenders = [
            (item["title"], math_values(robust_tokenize_with_math(item["title"])))
            for item in NEGATIVES
            if math_values(robust_tokenize_with_math(item["title"]))
        ]
        assert not offenders, f"{len(offenders)} of {len(NEGATIVES)}: {offenders[:5]}"

    @pytest.mark.parametrize(
        "text",
        [
            "(Almost) Everything you always wanted to know",
            "(Almost) Everything you always wanted to know about the (Almost) English",
            "Backward stochastic differential equations (slides)",
            "Probability theory, tome VII",
            "Bulletin 1897-1898",
            "Hamilton-Jacobi-Bellman equations for mean-field games",
        ],
        ids=["almost", "almost-twice", "slides", "roman", "year-range", "eponym"],
    )
    def test_ordinary_english_is_never_protected(self, text):
        """NEW.  The canonical negatives as literals, so the property survives
        even if the corpus file is ever unavailable."""
        assert math_values(robust_tokenize_with_math(text)) == []

    @needs_corpus
    def test_no_math_token_is_a_run_of_ordinary_english_words(self):
        """NEW.  "I found something" must not be able to masquerade as "it is
        fine".  A MATH token whose payload is two or more plain ASCII-letter
        words separated by spaces is prose that has been protected, which is
        as wrong as failing to protect maths.

        MEASURED over the 345 corpus titles: 0 offenders.  Single letters
        (``N``, ``X``, ``p``, ``L``) and glued notational heads (``GARCH(p,
        q)``, ``RCD(K, ∞)``, ``CAT(0)``, ``Lexp(...)``) are genuine and
        are deliberately not caught by this shape.
        """
        prose = _stdlib_re.compile(r"[A-Za-z]{2,}(?: +[A-Za-z]{2,})+")
        offenders = []
        for item in LABELLED:
            for tok in robust_tokenize_with_math(item["title"]):
                if tok.kind == "MATH" and prose.fullmatch(tok.value.strip("$").strip()):
                    offenders.append((item["title"], tok.value))
        assert not offenders, offenders[:5]

    @needs_corpus
    def test_no_math_token_is_a_bare_multi_letter_english_word(self):
        """NEW.  The tighter shape: a MATH token that is nothing but two or
        more ASCII letters carries no evidence of notation at all.

        MEASURED over the 345: the set is empty.  Bare single letters DO
        occur and are correct — the corpus labels 19 of them ("N" in
        "N-player games", "X" in "Les filtrations de |X|") as maths.
        """
        offenders = {
            tok.value
            for item in LABELLED
            for tok in robust_tokenize_with_math(item["title"])
            if tok.kind == "MATH" and _stdlib_re.fullmatch(r"[A-Za-z]{2,}", tok.value)
        }
        assert offenders == set(), sorted(offenders)

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("L^∞:L¹ duality results in optimal control problems", "L^∞:L¹"),
            ("A note on the equality π²:6=Σ_{n≥1}1:n²",
             "π²:6=Σ_{n≥1}1:n²"),
            ("A variant on (2Jₛ-Rₛ, s≥0) for processes", "2Jₛ-Rₛ, s≥0"),
            ("Bounds when 0<d<2 hold", "0<d<2"),
            ("Bounds when 0 < d < 2 hold", "0 < d < 2"),
        ],
        ids=["colon-spaces", "sigma-sum", "tuple-with-comma", "chain", "spaced-chain"],
    )
    def test_a_formula_containing_operators_and_spaces_is_one_token(self, text, expected):
        """REPLACES the LaTeX half of ``test_mixed_content_tokenization`` with
        the same property on constructs the library actually contains.

        All five are real library shapes taken from the corpus.  Each contains
        an operator, and three of them contain a space or a comma — the
        characters a torn formula leaves behind.
        """
        tokens = robust_tokenize_with_math(text)
        assert math_values(tokens) == [expected]
        assert_partition(text, tokens)

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("An AR(1) model of volatility", "AR(1)"),
            ("Congruence subgroups of SL(2, Z) and modular forms", "SL(2, Z)"),
            ("The space L^2 is complete", "L^2"),
            ("A continuous time GARCH(p, q) process with delay", "GARCH(p, q)"),
            ("Viscosity solutions in RCD(K, ∞) spaces", "RCD(K, ∞)"),
        ],
        ids=["AR(1)", "SL(2,Z)", "L^2", "GARCH", "RCD"],
    )
    def test_a_glued_designator_keeps_its_brackets_inside_one_token(self, text, expected):
        """NEW.  The operational definition's own worked examples.

        "L^2" must not become "l^2"; "AR(1)" must not become "Ar(1)" or
        "AR(one)".  Each is ONE MATH token INCLUDING its enclosing brackets,
        the space and the comma — the same delimiter-containment property the
        LaTeX tests assert, on the constructs the library actually contains.
        The corpus's span convention already encodes this: "AR(1)" keeps its
        brackets while "(Ap) condition" gives the bare "Ap".
        """
        tokens = robust_tokenize_with_math(text)
        assert math_values(tokens) == [expected]
        assert_partition(text, tokens)

    @pytest.mark.parametrize(
        "text",
        ["Heston (2008) and the smile", "Bulletin 155(3), pages 1105-1123"],
        ids=["citation-year", "volume-issue"],
    )
    def test_a_bracket_that_is_not_glued_to_notation_is_refused(self, text):
        """NEW.  The refusal that makes the test above mean something.

        A head GLUED to a parenthesised argument list is what separates
        "AR(1)" from "Heston (2008)", and the lenience gate is what stops a
        bare number dragging in the next bracket so that "155(3)" — a journal
        volume and issue — becomes mathematics.  Without this half, a
        tokeniser that claimed every bracket would pass the previous test.
        """
        assert math_values(robust_tokenize_with_math(text)) == []

    @pytest.mark.parametrize(
        "hyphen_form",
        ["L²-L¹", "x_1-y_1", "2Jₛ-Rₛ", "aᵢ-bᵢ",
         "α-β", "ℝⁿ-ℝᵐ", "Bₜ-Bₛ"],
    )
    def test_hyphen_and_minus_spellings_decompose_alike(self, hyphen_form):
        """NEW.  The co-variance contract, and the fix for the defect that
        ASCII hyphen-minus was missing from the operator tables.

        Two spellings of one expression must leave the SAME prose behind,
        because maintenance/conformance.py runs the detector on an old title
        and a new title separately and compares the residues to decide whether
        a rewrite was "confined to mathematics".  If "2J_s-R_s" split where
        "2J_s−R_s" did not, one rewrite would be judged confined and the
        other not, for the same edit.

        MEASURED: all seven pairs now agree.  U+002D is a LINK the parser may
        cross but never EVIDENCE — which is what keeps "mean-field" and
        "1105-1123" prose.
        """
        minus_form = hyphen_form.replace("-", "−")
        hyphen_tokens = robust_tokenize_with_math(hyphen_form)
        minus_tokens = robust_tokenize_with_math(minus_form)
        assert kinds(hyphen_tokens) == kinds(minus_tokens)
        assert [(t.start, t.end) for t in hyphen_tokens] == [
            (t.start, t.end) for t in minus_tokens
        ]

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "KNOWN RESIDUAL DIVERGENCE, measured: '2J_s-R_s, s>=0' yields two "
            "MATH tokens ('2J_s-R_s', 's≥0') while '2J_s−R_s, s≥0' "
            "yields one, so the two spellings leave different prose residues "
            "(', ' vs nothing) and conformance.py would judge the same edit "
            "differently. The subscript spelling of the same real library title "
            "-- '(2Jₛ-Rₛ, s≥0)', the form the library actually uses -- "
            "agrees under both, so no library title is affected today. Remove "
            "this xfail when the comma link is made hyphen-neutral."
        ),
    )
    def test_hyphen_and_minus_agree_across_a_comma_link(self):
        """NEW (expected to fail).  The one input found where co-variance
        still breaks.  Recorded as a test rather than as a comment so it
        cannot be forgotten, and strict so it announces itself when fixed."""
        hyphen = "2J_s-R_s, s≥0"
        minus = "2J_s−R_s, s≥0"
        assert kinds(robust_tokenize_with_math(hyphen)) == kinds(
            robust_tokenize_with_math(minus)
        )


# ══════════════════════════════════════════════════════════════════════════
class TestTheTokenisersPrivateDisplayMathRule:
    """math_tokenization.py:126-128 WAS a second math rule. It is gone.

    ``robust_tokenize_with_math`` does not only ask ``find_math_regions``.  It
    also runs its own ``r'\\$\\$[^$]+\\$\\$'`` and appends those spans
    directly, bypassing the single implementation.  The old
    ``test_display_math_detection`` was the only thing exercising that rule,
    and by passing it hid the duplication rather than recording it.

    "One rule, one implementation" (CLAUDE.md) says a rule that exists twice
    must be differential-tested before either copy is deleted. These tests
    ARE that differential test, and they are kept after the deletion so the
    rule cannot quietly come back: they now assert that every MATH token the
    tokeniser emits came from find_math_regions.
    """

    PRIVATE_RULE = _stdlib_re.compile(r"\$\$[^$]+\$\$")

    @pytest.mark.parametrize(
        "text",
        [
            "Display math: $$E = mc^2$$ is famous",
            "$$x$$",
            "a $$ b $$ c",
            "$$5 trillion$$",
            "$$a$$b$$c$$",
        ],
    )
    def test_the_two_rules_agree_on_well_formed_display_math(self, text):
        """NEW.  KEEPS the old ``test_display_math_detection`` assertion and
        adds what it was actually pinning.

        MEASURED: the landing implementation now returns the ``$$…$$`` span
        itself, with both pairs of dollars, so the private rule contributes
        nothing on these inputs and could be deleted without changing them.
        """
        from_single = set(find_math_regions(text))
        from_private = {m.span() for m in self.PRIVATE_RULE.finditer(text)}
        assert from_private <= from_single, (
            "the private rule claims a span the single implementation does not"
        )
        emitted = {(t.start, t.end) for t in robust_tokenize_with_math(text)
                   if t.kind == "MATH"}
        assert emitted == from_single

    def test_display_math_detection(self):
        """KEPT verbatim from the old file — the exact assertion, unchanged,
        so nothing that used to be covered stops being covered."""
        text = "Display math: $$E = mc^2$$ is famous"
        tokens = robust_tokenize_with_math(text)
        assert math_values(tokens) == ["$$E = mc^2$$"]

    def test_the_deleted_private_rule_no_longer_claims_prose(self):
        """THE DISAGREEMENT, now resolved in the right direction.

        This test used to assert the OPPOSITE, deliberately: it pinned the
        broken behaviour so that "the day the private rule is deleted this
        test fails and points at the change". That is exactly what happened,
        and this is that change.

        MEASURED, before: find_math_regions("$$the quick brown fox$$")
        returned [] -- the payload reads as ordinary English, so the money
        guard refuses it -- while the private regex claimed the whole string,
        so the tokeniser emitted a MATH token containing four English words.
        A second opinion that always wins is not a safety net, it is a shadow
        rule. After: the tokeniser emits no MATH token here at all.
        """
        text = "$$the quick brown fox$$"
        assert find_math_regions(text) == [], (
            "the single implementation must still refuse English between dollars"
        )
        assert math_values(robust_tokenize_with_math(text)) == [], (
            "the tokeniser must not protect four English words that the single "
            "implementation refused"
        )

    def test_every_math_token_comes_from_find_math_regions(self):
        """THE PROPERTY, now holding. Was xfail(strict) until the private
        rule was deleted; the deletion is what makes this pass.

        The tokeniser is a CONSUMER of the single implementation, not a
        second source of math spans.
        """
        text = "$$the quick brown fox$$"
        regions = set(find_math_regions(text))
        emitted = {(t.start, t.end) for t in robust_tokenize_with_math(text)
                   if t.kind == "MATH"}
        assert emitted <= regions

    @needs_corpus
    def test_no_extra_math_span_appears_on_any_corpus_title(self):
        """NEW.  The same property over 345 real titles, where it HOLDS.

        MEASURED: 0 extra spans.  The private rule is inert on real library
        text — which is exactly why the disagreement above went unnoticed.
        """
        extras = []
        for item in LABELLED:
            title = item["title"]
            regions = set(find_math_regions(title))
            for tok in robust_tokenize_with_math(title):
                if tok.kind == "MATH" and (tok.start, tok.end) not in regions:
                    extras.append((title, tok.value))
        assert not extras, extras[:5]


# ══════════════════════════════════════════════════════════════════════════
class TestPhrasesWinOverMath:
    """math_tokenization.py:137 — a math span overlapping a phrase is dropped.

    A whitelisted phrase is a decision someone made on purpose; a math span is
    inferred.  When they collide the decision wins.  The old file exercised
    this branch twice, both times by accident, and its one test NAMED for
    priority never reached the branch at all.
    """

    def test_math_like_phrase_beats_a_coinciding_math_span(self):
        """KEPT.  ``C^∞(M)`` is claimed by the phrase branch, not the
        math branch.  This was the only test in the old file that exercised
        the suppression on a non-LaTeX construct."""
        text = "The function C^∞(M) is smooth"
        tokens = robust_tokenize_with_math(text, ["C^∞(M)"])
        assert phrase_values(tokens) == ["C^∞(M)"]
        assert math_values(tokens) == []
        assert_partition(text, tokens)

    def test_unicode_phrase_beats_a_coinciding_math_span(self):
        """KEPT from ``test_unicode_handling``, with the mechanism now stated.

        MEASURED: ``find_math_regions`` claims ``α`` at [4,5) here, the
        phrase span [4,12) covers it, the suppression fires and the PHRASE
        token survives whole.  The second Greek letter, outside any phrase,
        stays a MATH token — so the test also shows the suppression is local.

        This is the shape the incumbent/landing convention difference bears
        on: the old implementation claimed ``α-stable`` as one maths span,
        the landing one claims the bare ``α``.  The hand-labelled corpus
        settles it for the landing convention — every adjectival compound in
        it is labelled with the bare Greek letter only.
        """
        text = "The α-stable process with β-distribution"
        tokens = robust_tokenize_with_math(text, ["α-stable"])
        assert phrase_values(tokens) == ["α-stable"]
        assert math_values(tokens) == ["β"]
        assert_partition(text, tokens)

    def test_phrase_beats_a_math_span_that_only_partially_overlaps_it(self):
        """NEW.  The crossing case, which nothing tested.

        MEASURED: for ``"The space L^2(Ω) of things"`` with the phrase
        ``"L^2"``, the math span is ``L^2(Ω)`` at [10,16) and the phrase
        is [10,13).  They cross rather than coincide.  The suppression drops
        the math span ENTIRELY, so ``(Ω)`` — part of a formula — reaches
        the prose stream as PUNCT/WORD/PUNCT.

        That is a real consequence for a caser and it is pinned here rather
        than left to be discovered.  The alternative designs (truncate the
        math span, or keep both) are decisions nobody has made; this test
        records which one is in force.
        """
        text = "The space L^2(Ω) of things"
        assert find_math_regions(text) == [(10, 16)]

        tokens = robust_tokenize_with_math(text, ["L^2"])
        assert phrase_values(tokens) == ["L^2"]
        assert math_values(tokens) == []
        assert [(t.kind, t.value) for t in tokens[4:8]] == [
            ("PHRASE", "L^2"), ("PUNCT", "("), ("WORD", "Ω"), ("PUNCT", ")"),
        ]
        assert_partition(text, tokens)

    def test_a_math_span_that_starts_before_a_phrase_is_dropped(self):
        """NEW, and it is the case the suppression actually EXISTS for.

        When a math span and a phrase share a start, the linear scan tries
        phrases first and the suppression is redundant.  The suppression only
        decides anything when the math span starts EARLIER and runs past the
        phrase's start: then the scan reaches the math start first, consumes
        past the phrase, and the phrase is never emitted at all.

        MEASURED on ``"The C^∞(M) space"`` with the phrase ``"(M)"``:
        ``find_math_regions`` claims ``C^∞(M)`` at [4,10) and the phrase sits
        at [7,10).  With the suppression the PHRASE survives; without it the
        whitelisted entry disappears silently.

        This test was written because two mutants — deleting the suppression
        entirely, and narrowing it to exactly-coinciding spans — both survived
        the rest of this file.
        """
        text = "The C^∞(M) space"
        assert find_math_regions(text) == [(4, 10)]

        tokens = robust_tokenize_with_math(text, ["(M)"])
        assert phrase_values(tokens) == ["(M)"]
        assert math_values(tokens) == []
        phrase = next(t for t in tokens if t.kind == "PHRASE")
        assert (phrase.start, phrase.end) == (7, 10)
        assert_partition(text, tokens)

    def test_a_math_span_outside_every_phrase_survives(self):
        """NEW.  The refusal half: suppression must not be global."""
        text = "The α-stable case of L^2"
        tokens = robust_tokenize_with_math(text, ["α-stable"])
        assert phrase_values(tokens) == ["α-stable"]
        assert math_values(tokens) == ["L^2"]


# ══════════════════════════════════════════════════════════════════════════
class TestPhraseRegexLimitations:
    """What the phrase matcher CANNOT match, stated instead of implied.

    The old ``test_phrase_priority_over_math`` passed a phrase the matcher can
    never match, then asserted the outcome as if priority had decided it.
    Maths won by walkover.  These tests state the limitation directly, because
    a caller who passes such a phrase gets no protection and no error.
    """

    def test_a_phrase_starting_with_a_non_word_character_never_matches(self):
        """NEW.  The defect the old priority test silently proved.

        Every phrase branch anchors on ``\\b``.  A phrase beginning with
        ``$`` or ``\\`` is preceded in the title by a space, and ``\\b``
        cannot match between a space and a non-word character — so the phrase
        regex never fires.  MEASURED: 0 PHRASE tokens for
        ``"$\\alpha$-stable"``, and the whole thing is decided by the math
        branch instead.
        """
        text = "The $\\alpha$-stable process"
        tokens = robust_tokenize_with_math(text, ["$\\alpha$-stable"])
        assert phrase_values(tokens) == []
        assert math_values(tokens) == ["$\\alpha$"]
        assert [t.value for t in tokens if t.kind == "WORD" and t.value == "stable"] == [
            "stable"
        ]
        assert_partition(text, tokens)

    def test_backslash_in_dash_chars_misroutes_a_latex_phrase(self):
        """NEW.  A second, independent consequence of the escape character
        leaking into a membership test (see ``TestDashChars``).

        math_tokenization.py:44 classifies a phrase as multi-word if
        ``any(d in ph for d in DASH_CHARS)``, and DASH_CHARS contains the
        backslash escape.  So ``"\\alpha(x)"`` — which has no space and no
        dash — is routed to the DASH branch and its ``\\b`` anchor fails,
        instead of to the math-like branch whose lookaround anchors would have
        matched it.

        MEASURED, the two phrases differing only by the backslash:
        ``"alpha(x)"``   -> PHRASE token, no MATH token
        ``"\\alpha(x)"`` -> no PHRASE token, MATH token ``"\\alpha"``
        """
        plain = robust_tokenize_with_math("The alpha(x) term", ["alpha(x)"])
        assert phrase_values(plain) == ["alpha(x)"]
        assert math_values(plain) == []

        latex = robust_tokenize_with_math("The \\alpha(x) term", ["\\alpha(x)"])
        assert phrase_values(latex) == []
        assert math_values(latex) == ["\\alpha"]


# ══════════════════════════════════════════════════════════════════════════
class TestRobustTokenizeWithMath:
    """The behaviours that were already covered and still are."""

    def test_empty_input(self):
        """KEPT."""
        assert robust_tokenize_with_math("") == []

    def test_simple_text(self):
        """KEPT.  Nothing is protected when nothing is mathematics."""
        text = "Hello world"
        tokens = robust_tokenize_with_math(text)
        assert [(t.kind, t.value, t.start, t.end) for t in tokens] == [
            ("WORD", "Hello", 0, 5),
            ("SPACE", " ", 5, 6),
            ("WORD", "world", 6, 11),
        ]

    def test_math_token_positions(self):
        """SPLIT OUT of the old ``test_token_positions``.

        The old test conflated two properties — the partition invariant and
        "``$x$`` is one MATH token at [6,9)" — and addressed both by index, so
        when the math token vanished the index assertions slid and one of them
        passed by coincidence (the PUNCT ``$`` happened to start where the
        MATH token would have).  The partition half now lives in
        ``TestPartitionInvariant``; this half is stated by kind and value, not
        by position in the list.
        """
        text = "Hello $x$ world"
        tokens = robust_tokenize_with_math(text)
        assert [(t.kind, t.value, t.start, t.end) for t in tokens] == [
            ("WORD", "Hello", 0, 5),
            ("SPACE", " ", 5, 6),
            ("MATH", "$x$", 6, 9),
            ("SPACE", " ", 9, 10),
            ("WORD", "world", 10, 15),
        ]

    def test_math_token_positions_on_a_real_construct(self):
        """NEW.  The same property on something the library contains."""
        text = "Hello L² world"
        tokens = robust_tokenize_with_math(text)
        assert [(t.kind, t.value, t.start, t.end) for t in tokens] == [
            ("WORD", "Hello", 0, 5),
            ("SPACE", " ", 5, 6),
            ("MATH", "L²", 6, 8),
            ("SPACE", " ", 8, 9),
            ("WORD", "world", 9, 14),
        ]

    def test_phrase_detection_multi_word(self):
        """KEPT.  Space-only phrase branch (math_tokenization.py:60-64)."""
        text = "The Black Scholes model is important"
        tokens = robust_tokenize_with_math(text, ["Black Scholes"])
        assert phrase_values(tokens) == ["Black Scholes"]

    def test_phrase_detection_dash_separated(self):
        """KEPT.  Dash-only phrase branch (math_tokenization.py:65-69)."""
        text = "The Black-Scholes model works"
        tokens = robust_tokenize_with_math(text, ["Black-Scholes"])
        assert phrase_values(tokens) == ["Black-Scholes"]

    def test_phrase_detection_case_insensitive(self):
        """KEPT.  The token carries the text AS FOUND, not as whitelisted."""
        tokens = robust_tokenize_with_math("The BLACK SCHOLES model", ["Black Scholes"])
        assert phrase_values(tokens) == ["BLACK SCHOLES"]

    def test_phrase_detection_flexible_spacing(self):
        """KEPT, ASSERTION TIGHTENED.

        The old version asserted only ``"Black" in value`` and ``"Scholes" in
        value`` — substring membership, which would have passed on a match
        that grabbed extra text on either side.  The exact value and offsets
        are asserted instead.
        """
        text = "The Black  Scholes   model"
        tokens = robust_tokenize_with_math(text, ["Black Scholes"])
        assert phrase_values(tokens) == ["Black  Scholes"]
        phrase = next(t for t in tokens if t.kind == "PHRASE")
        assert (phrase.start, phrase.end) == (4, 18)
        assert_partition(text, tokens)

    def test_phrase_detection_hyphenated_variants(self):
        """KEPT.  Hyphen-variant pass (math_tokenization.py:99-109) and the
        document order of the hits."""
        text = "Both Black-Scholes and Black—Scholes work"
        tokens = robust_tokenize_with_math(text, ["Black Scholes"])
        assert phrase_values(tokens) == ["Black-Scholes", "Black—Scholes"]

    def test_overlapping_phrases_longest_wins(self):
        """KEPT.  Sort-and-occupy loop (math_tokenization.py:111-118)."""
        tokens = robust_tokenize_with_math(
            "Monte Carlo Methods in Finance", ["Monte Carlo", "Monte Carlo Methods"]
        )
        assert phrase_values(tokens) == ["Monte Carlo Methods"]

    def test_excessive_spacing_rejection(self):
        """KEPT.  A refusal test: flexible spacing must not be stretchable
        into protecting a run of unrelated words (math_tokenization.py:88-91)."""
        tokens = robust_tokenize_with_math("Black   Scholes", ["Black Scholes"])
        assert phrase_values(tokens) == []

    def test_word_sequence_must_match_the_phrase(self):
        """NEW.  The other half of the same guard: the matched words must be
        the phrase's words, case-folded, not merely something the flexible
        pattern happened to reach."""
        tokens = robust_tokenize_with_math("Black and Scholes", ["Black Scholes"])
        assert phrase_values(tokens) == []

    def test_a_match_that_glues_the_phrase_into_one_word_is_refused(self):
        """NEW.  The word-sequence guard at math_tokenization.py:96-98, which
        had no test — deleting it left this whole file green.

        A phrase containing BOTH a space and a dash goes through
        ``_phrase_regex``, whose separator class is ``[\\s\\-–—]+`` — one or
        MORE.  So ``"Black-Scholes model"`` can match ``"Black-Scholes--model"``,
        whose word sequence is a single hyphenated word, not the two words the
        phrase names.  The guard refuses it; without the guard the tokeniser
        would protect a compound nobody whitelisted.

        The single-dash spelling IS accepted, by the hyphen-variant pass — so
        the control case below is what stops this test from passing for the
        wrong reason.
        """
        glued = "The Black-Scholes--model is famous"
        assert phrase_values(robust_tokenize_with_math(glued, ["Black-Scholes model"])) == []

        control = "The Black-Scholes-model is famous"
        assert phrase_values(
            robust_tokenize_with_math(control, ["Black-Scholes model"])
        ) == ["Black-Scholes-model"]

    def test_punctuation_tokenization(self):
        """KEPT."""
        tokens = robust_tokenize_with_math("Hello, world!")
        assert [t.value for t in tokens if t.kind == "PUNCT"] == [",", "!"]

    def test_empty_phrases_list(self):
        """KEPT."""
        tokens = robust_tokenize_with_math("Regular text without special phrases", [])
        assert [t.value for t in tokens if t.kind == "WORD"]
        assert phrase_values(tokens) == []

    def test_none_phrases_list(self):
        """KEPT.  ``phrases or ()`` guard: "I was given nothing" and "I was
        given an empty list" must not diverge."""
        text = "Regular text without special phrases"
        assert [
            (t.kind, t.value, t.start, t.end)
            for t in robust_tokenize_with_math(text, None)
        ] == [
            (t.kind, t.value, t.start, t.end)
            for t in robust_tokenize_with_math(text, [])
        ]

    def test_single_ordinary_word_is_not_a_phrase(self):
        """NEW.  math_tokenization.py:41-50 deliberately drops single
        non-math words from the whitelist, so a common word in the vocabulary
        cannot start protecting itself everywhere.  Nothing said so."""
        tokens = robust_tokenize_with_math("The model is fine", ["model"])
        assert phrase_values(tokens) == []
        assert [t.value for t in tokens if t.kind == "WORD"] == [
            "The", "model", "is", "fine"
        ]


# ══════════════════════════════════════════════════════════════════════════
class TestTokenProperties:
    """Every Token is well-formed, on inputs that reach every branch.

    The old version asserted this on ONE input, ``"Hello world"`` — three
    tokens, no math, no phrases, no fallback.  The strongest property in the
    file was only ever checked on the easiest possible token stream.
    """

    CASES = [
        ("Hello world", None, {"WORD", "SPACE"}),
        ("Hello, world!", None, {"WORD", "SPACE", "PUNCT"}),
        ("$x + y = z$", None, {"MATH"}),
        ("L^∞:L¹ duality", None, {"MATH", "SPACE", "WORD"}),
        ("A variant on (2Jₛ-Rₛ, s≥0) for processes", None,
         {"MATH", "PUNCT", "SPACE", "WORD"}),
        ("The α-stable process", ["α-stable"], {"PHRASE", "SPACE", "WORD"}),
        ("a'", None, {"WORD", "PUNCT"}),
    ]

    @pytest.mark.parametrize(
        "text,phrases,expected_kinds", CASES,
        ids=["words", "punct", "math-only", "math-prose", "math-punct",
             "phrase", "fallback"],
    )
    def test_token_creation(self, text, phrases, expected_kinds):
        """KEPT AND WIDENED.  Types, ranges and value/offset consistency."""
        tokens = robust_tokenize_with_math(text, phrases)
        assert {t.kind for t in tokens} == expected_kinds

        for token in tokens:
            assert isinstance(token.kind, str)
            assert isinstance(token.value, str)
            assert isinstance(token.start, int)
            assert isinstance(token.end, int)
            assert token.kind in {"PHRASE", "MATH", "WORD", "SPACE", "PUNCT"}
            assert token.start >= 0
            assert token.end > token.start
            assert token.end <= len(text)
            assert token.value == text[token.start:token.end]

    def test_every_branch_of_the_scan_is_reached_by_this_class(self):
        """NEW.  Guards the guard: if a case above stops reaching its branch,
        the coverage claim in this class's docstring becomes false silently."""
        reached = set()
        for text, phrases, _ in self.CASES:
            reached |= {t.kind for t in robust_tokenize_with_math(text, phrases)}
        assert reached == {"PHRASE", "MATH", "WORD", "SPACE", "PUNCT"}


# ══════════════════════════════════════════════════════════════════════════
class TestEdgeCases:
    """Malformed and adversarial input."""

    def test_very_long_text(self):
        """KEPT.  (The adversarial variants live in
        ``TestPartitionInvariant::test_partition_and_termination_on_adversarial_length``.)"""
        text = "word " * 1000
        tokens = robust_tokenize_with_math(text)
        assert tokens
        for token in tokens:
            assert 0 <= token.start < token.end <= len(text)

    def test_only_phrases(self):
        """KEPT.  Adjacent phrases do not merge across the gap between them."""
        text = "Black-Scholes Monte-Carlo"
        tokens = robust_tokenize_with_math(text, ["Black-Scholes", "Monte-Carlo"])
        assert phrase_values(tokens) == ["Black-Scholes", "Monte-Carlo"]
        assert [t.value for t in tokens if t.kind == "SPACE"] == [" "]
        assert_partition(text, tokens)

    def test_nested_math_patterns(self):
        """REWRITTEN.  The old assertion was ``len(math_tokens) > 0``, which
        encodes the belief that finding SOMETHING is better than finding
        nothing — precisely the "I didn't look and it's fine are the same
        return value" failure this project forbids.

        MEASURED on ``"Nested: $a + \\frac{$b$}{c}$ complex"``: the greedy
        dollar alternative pairs the wrong dollars and returns two spans,
        ``"$a + \\frac{$"`` and ``"$}{c}$"``, neither of which is a formula.
        The old expectation was satisfied by that garbage.

        For malformed delimiters the correct number of spans is UNDEFINED, so
        nothing is asserted about the count.  What is asserted is what must
        hold whatever the parse does: it terminates, it tiles the input, and
        it does not protect English.
        """
        text = "Nested: $a + \\frac{$b$}{c}$ complex"
        tokens = robust_tokenize_with_math(text)

        assert_partition(text, tokens)

        prose = _stdlib_re.compile(r"[A-Za-z]{2,}(?: +[A-Za-z]{2,})+")
        for tok in tokens:
            if tok.kind == "MATH":
                assert not prose.fullmatch(tok.value.strip("$").strip())

        # the ordinary words on either side must survive as prose
        assert "Nested" in [t.value for t in tokens if t.kind == "WORD"]
        assert "complex" in [t.value for t in tokens if t.kind == "WORD"]

    def test_malformed_math(self):
        """REWRITTEN.  The old assertion was ``len(tokens) > 0`` — too weak to
        distinguish a real improvement from a regression.

        MEASURED: the implementation this replaced returned a MATH token whose
        value was the single character ``"+"`` for this input — a spurious
        span in the middle of an ordinary English sentence.  The old test
        could not tell that apart from the correct answer.

        The honest assertion is the negative one: an unclosed delimiter
        yields NO span at all, and every English word reaches the prose
        stream where a caser can see it.
        """
        text = "Unclosed math: $x + y and more text"
        tokens = robust_tokenize_with_math(text)

        assert math_values(tokens) == []
        assert [t.value for t in tokens if t.kind == "WORD"] == [
            "Unclosed", "math", "x", "y", "and", "more", "text"
        ]
        assert_partition(text, tokens)

    @pytest.mark.parametrize(
        "text",
        ["$", "$$", "$$$", "\\", "\\[", "\\begin{", "\\begin{a}", "}", "$x", "x$"],
    )
    def test_lone_and_unpaired_delimiters_do_not_crash(self, text):
        """NEW.  Degenerate delimiter inputs.  No count is asserted — only
        termination and the partition invariant."""
        assert_partition(text, robust_tokenize_with_math(text))

    def test_special_characters_round_trip(self):
        """KEPT.  The one round-trip assertion the old file made on a
        math-bearing input."""
        text = "Special: α, β, γ, ∑, ∏, ∫, ∂, ∆, ∇"
        tokens = robust_tokenize_with_math(text)
        assert tokens
        assert "".join(t.value for t in tokens) == text
        assert_partition(text, tokens)

    @pytest.mark.parametrize(
        "char", list("αβγ∑∏∫∂∆∇"),
        ids=lambda c: f"U+{ord(c):04X}",
    )
    def test_each_special_character_alone_is_claimed_as_mathematics(self, char):
        """NEW.  What the old ``test_special_characters`` stopped short of.

        It listed nine mathematical characters and asserted only that they
        survived the round trip — never that any of them was PROTECTED.  A
        tokeniser that emitted every one of them as PUNCT would have passed.

        The corpus supplies the oracle: it labels 31 bare Greek symbols as
        maths, e.g. ``γ`` in "An expanded local variance γ model",
        which is the carrier sentence used here.
        """
        text = f"An expanded local variance {char} model"
        tokens = robust_tokenize_with_math(text)
        assert math_values(tokens) == [char]
        assert_partition(text, tokens)


# ══════════════════════════════════════════════════════════════════════════
class TestPropertyBased:
    """Hypothesis: the invariants must survive input nobody thought of.

    The old file had no property-based test.  Every literal example in it was
    chosen by the same person who wrote the code path it exercises.
    """

    ALPHABET = (
        "abcXYZ 012"
        "$\\{}[]()^_"
        "-–—‐−"
        "αβℝ∞∑∂≤≥"
        "²₁,;:.'’\t\n"
    )

    @pytest.mark.parametrize("_", range(1), ids=["hypothesis"])
    def test_partition_invariant_is_universal(self, _):
        """NEW.  Whatever the input, the tokens tile it exactly and the call
        returns.  Hypothesis is imported lazily so this file still collects
        where hypothesis is absent."""
        hypothesis = pytest.importorskip("hypothesis")
        from hypothesis import strategies as st

        @hypothesis.settings(
            max_examples=400, deadline=None,
            suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
        )
        @hypothesis.given(st.text(alphabet=self.ALPHABET, max_size=60))
        def check(text):
            assert_partition(text, robust_tokenize_with_math(text))

        check()

    @pytest.mark.parametrize("_", range(1), ids=["hypothesis"])
    def test_a_math_token_never_covers_only_whitespace(self, _):
        """NEW.  A span of pure whitespace protected as mathematics would stop
        a caser normalising spacing, and is meaningless under the operational
        definition — rewriting whitespace's "case" is not a thing."""
        hypothesis = pytest.importorskip("hypothesis")
        from hypothesis import strategies as st

        @hypothesis.settings(max_examples=300, deadline=None)
        @hypothesis.given(st.text(alphabet=self.ALPHABET, max_size=60))
        def check(text):
            for tok in robust_tokenize_with_math(text):
                if tok.kind == "MATH":
                    assert tok.value.strip(), f"whitespace-only MATH token in {text!r}"

        check()

    @pytest.mark.parametrize("_", range(1), ids=["hypothesis"])
    def test_phrases_none_and_empty_always_agree(self, _):
        """NEW.  The ``phrases or ()`` guard, as a property rather than on one
        hand-picked sentence."""
        hypothesis = pytest.importorskip("hypothesis")
        from hypothesis import strategies as st

        @hypothesis.settings(max_examples=200, deadline=None)
        @hypothesis.given(st.text(alphabet=self.ALPHABET, max_size=40))
        def check(text):
            assert [
                (t.kind, t.value, t.start, t.end)
                for t in robust_tokenize_with_math(text, None)
            ] == [
                (t.kind, t.value, t.start, t.end)
                for t in robust_tokenize_with_math(text, [])
            ]

        check()

    @needs_corpus
    @pytest.mark.parametrize("_", range(1), ids=["hypothesis"])
    def test_mutated_library_titles_keep_the_invariants(self, _):
        """NEW.  Fuzzing seeded from real data rather than from an alphabet:
        take a real library title, splice in a random run of characters, and
        require the invariants to hold."""
        hypothesis = pytest.importorskip("hypothesis")
        from hypothesis import strategies as st

        titles = [item["title"] for item in LABELLED]

        @hypothesis.settings(max_examples=300, deadline=None)
        @hypothesis.given(
            st.sampled_from(titles),
            st.integers(min_value=0, max_value=200),
            st.text(alphabet=self.ALPHABET, max_size=12),
        )
        def check(title, cut, insert):
            cut = min(cut, len(title))
            mutated = title[:cut] + insert + title[cut:]
            tokens = robust_tokenize_with_math(mutated)
            assert_partition(mutated, tokens)
            for tok in tokens:
                if tok.kind == "MATH":
                    assert tok.value.strip()

        check()


# ══════════════════════════════════════════════════════════════════════════
class TestARefusalReachesTheCaserAsHandsOff:
    """What ``find_math_regions``' REFUSAL means once it gets here.

    ``core/math_regions.py`` refuses an input longer than MAX_INPUT_CHARS, or
    one whose parse runs past MAX_PARSE_STEPS, by returning the WHOLE
    stripped input as one protected region rather than ``[]``.  That choice is
    only correct if it survives this tokeniser: the point of it is that every
    live consumer leaves the title alone, and the consumer that matters is
    ``core/sentence_case.py``, which reads this tokeniser's output.

    A refusal that arrived here as several MATH tokens, or as a MATH token
    whose edges did not tile the title, would put prose back in the caser's
    hands -- so "the module returns one span" and "the caser leaves it alone"
    are two different claims and only the second one is the requirement.

    NEW, 2026-08-25.  Wired in with the bounds themselves: the refusal
    contract was asserted only inside ``if __name__ == "__main__":``, which
    pytest never runs, so the mutants that made ``_refuse`` return ``[]`` or
    keep its whitespace edges were caught by nothing on this side of the call.
    """

    #: One long enough to be refused on length, and one short enough to be
    #: admitted but expensive enough to be refused on steps.  They are
    #: different decisions in the module and must behave alike here.
    LONG = "  " + "x + y " * 400 + "  "
    EXPENSIVE = "(" + ",".join("a" for _ in range(120)) + ")"

    @pytest.mark.parametrize("kind", ["LONG", "EXPENSIVE"])
    def test_a_refused_title_becomes_exactly_one_math_token(self, kind):
        """One token, covering everything the module protected.  Two would
        leave whatever falls between them in the prose stream."""
        text = getattr(self, kind)
        regions = find_math_regions(text)
        assert len(regions) == 1, f"{kind} was not refused: {regions[:3]}"
        tokens = robust_tokenize_with_math(text)
        assert math_values(tokens) == [text[regions[0][0]:regions[0][1]]]

    @pytest.mark.parametrize("kind", ["LONG", "EXPENSIVE"])
    def test_a_refused_title_still_tiles(self, kind):
        """The partition invariant does not get an exemption for a refusal.
        The caser reassembles the title from these tokens; if a refusal
        cannot be reassembled, refusing has damaged the title it was
        protecting."""
        text = getattr(self, kind)
        assert_partition(text, robust_tokenize_with_math(text))

    @pytest.mark.parametrize("kind", ["LONG", "EXPENSIVE"])
    def test_nothing_of_a_refused_title_reaches_the_caser_as_prose(self, kind):
        """The requirement itself: apart from the outer whitespace the module
        deliberately left outside the span, every character arrives inside
        MATH.  This is what makes ``_refuse`` different from ``[]``, and it
        is the reason the module raises on a non-str instead -- a non-str has
        no offsets, so this protection is not available for it."""
        text = getattr(self, kind)
        tokens = robust_tokenize_with_math(text)
        loose = "".join(t.value for t in tokens if t.kind != "MATH")
        assert loose.strip() == "", repr(loose[:80])

    def test_an_admissible_title_is_not_refused(self):
        """The other half, or the three tests above pass on a module that
        refuses everything.  A refusal must be rare and reserved: no title
        in the library is anywhere near either bound."""
        ordinary = "An introduction to probability theory"
        assert find_math_regions(ordinary) == []
        assert math_values(robust_tokenize_with_math(ordinary)) == []


class TestBranchesMeasuredUnreachable:
    """Two branches of math_tokenization.py deliberately have no test.

    House rule: when a mutant survives, find out whether the branch is even
    reachable before writing a test for it — three "defensive" branches in
    this codebase have already turned out to be dead.  Both branches below
    survived mutation of this file and were then shown to be unreachable, so
    a test of their behaviour would be a test of nothing.  What IS asserted
    here is the structural fact that makes each one unreachable, so the claim
    stops being true out loud rather than silently.

    Both are candidates for deletion or an explicit annotation in the module.
    """

    def test_segment_re_lastgroup_is_never_none(self):
        """math_tokenization.py:196-199 falls back to ``kind = "PUNCT"`` when
        ``m.lastgroup`` is falsy.  Mutating that fallback to ``"WORD"``
        changes no observable behaviour.

        REASON: all three alternatives of _SEGMENT_RE are NAMED groups, so a
        successful match always sets ``lastgroup``.  Asserted structurally —
        the pattern has exactly three groups and all three are named — and
        empirically over every code point below U+3000.
        """
        assert _SEGMENT_RE.groups == 3
        assert len(_SEGMENT_RE.groupindex) == 3

        seen = set()
        for codepoint in range(0x3000):
            match = _SEGMENT_RE.match(chr(codepoint))
            if match is not None:
                assert match.lastgroup is not None
                seen.add(match.lastgroup)
        assert seen == {"SPACE", "PUNCT", "WORD"}

    @pytest.mark.parametrize(
        "text",
        ["The x_i and another x_i here", "x_i x_i x_i", "y_x_i and x_i",
         "L_exp then L_exp again"],
    )
    def test_a_single_token_phrase_never_emits_a_duplicate_suffix(self, text):
        """math_tokenization.py:167 guards the suffix duplication with
        ``if suffix_start >= i``.  Mutating ``>=`` to ``>`` changes no
        observable behaviour.

        REASON: ``suffix_start == i`` requires the phrase's last ``\\w+`` word
        to span the whole phrase, which happens only for a single-token
        math-like phrase such as ``"x_i"`` or ``"L_exp"``.  For those, every
        ``\\b``-delimited occurrence of the word is ALSO a phrase-regex
        occurrence (the phrase's lookarounds are strictly weaker than ``\\b``
        here), and a phrase hit dropped for overlapping always starts inside
        the hit that blocked it, because hits are processed in ascending
        start order.  So ``_appears_outside`` is always False and the guard
        never decides anything.

        MEASURED: 200,000 randomised (text, phrase-set) trials over an
        alphabet built from these shapes produced 0 cases where
        ``suffix_start == i`` and the suffix recurred outside every phrase.
        The behaviour asserted here — no duplicate token — is what follows.
        """
        tokens = robust_tokenize_with_math(text, ["x_i", "L_exp"])
        overlaps = [
            (a.kind, b.kind) for a, b in zip(tokens, tokens[1:]) if b.start < a.end
        ]
        assert overlaps == []
        assert_partition(text, tokens)


if __name__ == "__main__":                                # pragma: no cover
    pytest.main([__file__, "-v"])
