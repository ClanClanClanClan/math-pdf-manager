"""The ingest namer must close every quotation it opens.

THE DEFECT. ``QUOTE_CONVERSIONS`` in
``validators/filename_checker/text_processing.py`` held only OPENING
marks, and ``convert_straight_quotes_to_proper`` assigned that opener to
EVERY straight double quote in the string. No closing mark could ever be
emitted, in any language. Verified live on the real function before the
fix:

    'Commentary on "Longest increasing subsequences" by Aldous'
      -> 'Commentary on “Longest increasing subsequences“ by Aldous'
    'Correction "Quelques resultats de mecanique stochastique"'
      -> 'Correction «Quelques resultats de mecanique stochastique«'

REACHABLE, and on the path that matters most: arxivbot
``CMO.get_canonical_filename`` -> ``_validate_filename`` ->
``check_filename`` -> ``fix_and_flag_quotes`` -> here. That is how every
newly ingested paper is named.

The MOVE path never used it -- ``processing/move_normalizer`` takes only
the corrected author block and keeps the title verbatim -- which is why
exactly ONE malformed filename reached the library (measured across
25,252 in-scope names) rather than hundreds.

These tests are about BALANCE only. They deliberately do not assert
which pair a language should use: that policy question is open, and two
independent reviewers refuted the proposed answer. An opener standing
where a closer belongs is wrong under every convention, so it can be
fixed without settling any of it.
"""
from __future__ import annotations

import pytest

from validators.filename_checker.text_processing import (
    QUOTE_CLOSERS,
    QUOTE_CONVERSIONS,
    convert_straight_quotes_to_proper,
)

OPENERS = {"“", "«", "„"}
CLOSERS = {"”", "»"}


def _convert(text: str, lang: str) -> str:
    return convert_straight_quotes_to_proper(text, lang, [], [])


def _counts(out: str, lang: str) -> tuple:
    """(openers, closers) for THIS language's own pair.

    Counted per language, not against a global set: German closes with
    U+201C, which is English's OPENING mark. A global tally would call a
    correct German string unbalanced and a broken one fine.
    """
    op, cl = QUOTE_CONVERSIONS[lang]['"'], QUOTE_CLOSERS[lang]
    if op == cl:                                   # no language here does this
        return out.count(op), out.count(cl)
    return out.count(op), out.count(cl)


@pytest.mark.parametrize("lang", sorted(QUOTE_CONVERSIONS))
def test_every_language_has_a_closing_mark(lang):
    """The table itself was the bug: openers only."""
    assert lang in QUOTE_CLOSERS, (
        f"{lang!r} can open a quotation and never close one"
    )
    assert QUOTE_CLOSERS[lang], f"{lang!r} has an empty closing mark"


@pytest.mark.parametrize("lang", sorted(QUOTE_CONVERSIONS))
def test_a_quoted_phrase_is_opened_and_closed(lang):
    out = _convert('Commentary on "a paper title" by someone', lang)
    op, cl = _counts(out, lang)
    assert (op, cl) == (1, 1), (
        f"{lang}: expected one opener and one closer, got {op}/{cl} in {out!r}"
    )


@pytest.mark.parametrize("lang", sorted(QUOTE_CONVERSIONS))
def test_two_quotations_in_one_title_both_close(lang):
    """The single-toggle bug's other face: a stateful fix that forgets to
    flip back opens the second quotation with a closing mark."""
    out = _convert('A "first" and a "second" quotation', lang)
    op, cl = _counts(out, lang)
    assert (op, cl) == (2, 2), f"{lang}: got {op}/{cl} in {out!r}"


@pytest.mark.parametrize("lang", sorted(QUOTE_CONVERSIONS))
def test_no_straight_double_quote_survives(lang):
    out = _convert('He said "hello" twice', lang)
    assert '"' not in out


def test_german_closes_with_the_left_mark_not_the_right_one():
    """German is the case a naive "swap in U+201D" fix gets wrong:
    it opens with U+201E and closes with U+201C."""
    out = _convert('Bemerkung "uber die Gleichung"', "de")
    assert out == "Bemerkung „uber die Gleichung“", out


def test_an_odd_number_of_quotes_still_opens_first():
    """Malformed input must not silently become a closer-first string --
    that would be a new way to produce the very shape being fixed."""
    out = _convert('An "unclosed quotation', "en")
    assert out.startswith("An “unclosed"), out
    assert "”" not in out


def test_quotes_inside_a_math_region_are_left_alone():
    """Regions are the caller's promise that this span is not prose."""
    text = 'A title with "quoted" text'
    start = text.index('"')
    out = convert_straight_quotes_to_proper(text, "en", [(start, len(text))], [])
    assert out == text, out


def test_a_region_skip_does_not_desynchronise_the_following_pair():
    """PATHOLOGY. A quote inside a protected span must not advance the
    open/close toggle -- if it did, the next real quotation would come
    out closer-first.

    A WHOLE quotation is protected here, not a single mark. Protecting
    just one of a pair leaves an odd number of convertible quotes, which
    cannot balance by arithmetic; an earlier draft of this test asserted
    that it could and was wrong, not the code.
    """
    text = 'Say "one" then "two"'
    a = text.index('"')
    b = text.index('"', a + 1) + 1                 # through the closing mark
    out = convert_straight_quotes_to_proper(text, "en", [(a, b)], [])
    assert out.count('"') == 2, (
        f"both protected quotes must survive untouched: {out!r}"
    )
    rest = out[b:]
    assert rest.count("“") == 1 and rest.count("”") == 1, (
        f"the unprotected quotation must open AND close: {out!r}"
    )


@pytest.mark.parametrize("n", [0, 1, 2, 3, 4, 6, 8])
def test_balance_is_a_property_not_a_fixture(n):
    """For an EVEN number of straight doubles the output is balanced; for
    an odd number there is exactly one more opener than closer."""
    text = "word " + " ".join('"q%d"' % i for i in range(n // 2))
    if n % 2:
        text += ' "dangling'
    out = _convert(text, "en")
    op, cl = _counts(out, "en")
    assert op == (n + 1) // 2 and cl == n // 2, (
        f"n={n}: got {op} openers / {cl} closers in {out!r}"
    )


def test_a_protected_quote_does_not_change_the_alternation_state():
    """The mutation that survived the test above.

    Protecting a PAIR flips the toggle twice, so a bug that advances the
    state on a skipped quote cancels itself out and stays invisible.
    Protect exactly ONE, and the next convertible quote reveals it: if
    the skipped mark moved the state, the following quotation OPENS with
    a closing mark.

    Asserting balance here would be wrong -- three convertible quotes
    cannot balance -- so this asserts the property that actually holds:
    the first convertible quote after a protected one still OPENS.
    """
    text = 'Say "one" then "two"'
    a = text.index('"')
    out = convert_straight_quotes_to_proper(text, "en", [(a, a + 1)], [])

    assert out[a] == '"', f"the protected quote must survive: {out!r}"
    converted = [c for c in out[a + 1:] if c in OPENERS | CLOSERS]
    assert converted, f"nothing after it was converted: {out!r}"
    assert converted[0] in OPENERS, (
        "the first convertible quote after a protected one opened with a "
        f"CLOSING mark -- the skipped quote moved the state: {out!r}"
    )
