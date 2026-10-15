"""A new paper's title: an apostrophe is U+2019, a prime is left alone.

THE RULING (processing/apostrophes.py; docs/FILENAME_CONVENTION.md 3.4).
The title is prose, so its punctuation apostrophe is U+2019; the author
block is a key and keeps U+0027. A mathematical prime is not an apostrophe
and must never be written as one. The library agrees: of the 25,251
in-scope names, 1,699 titles carry U+2019.

THE DEFECT, found 2026-10-15. Arrival -- ``check_filename`` ->
``convert_straight_quotes_to_proper`` -- disagreed three ways:

  * A contraction stayed U+0027. Its converter ran only when the title
    ALSO held a straight double quote, and even then kept "l'équation" and
    "Itô's" straight on purpose. So every arXiv title with an apostrophe
    arrived as "Itô's formula".
  * When it did run, everything else became U+2019, a prime included:
    "f'(x)" -> "f’(x)", "X'_t" -> "X’_t".
  * And so did both ends of a quoted word: "'hot hand'" -> "’hot hand’",
    two closing marks.

Its contraction test, ``is_contraction_apostrophe``, is deleted: the rule
now lives in ``processing.apostrophes.is_title_apostrophe``, which says
"apostrophe" only when it is sure and leaves everything else as it is.

Every pathology case below is a real title -- a library name, or the
original filename a paper arrived with -- unless marked synthetic.
"""
from __future__ import annotations

import re
import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from arxivbot.models.cmo import CMO, Author
from processing.apostrophes import (TITLE_APOSTROPHE, fold_marks,
                                    is_title_apostrophe, title_apostrophes)
from validators.filename_checker.text_processing import (
    convert_straight_quotes_to_proper, fix_and_flag_quotes)

A = TITLE_APOSTROPHE


# ------------------------------------------------------------ the pathology

@pytest.mark.parametrize("title,expected", [
    # letter ' letter: elision, possessive, contraction
    ("Itô's formula for jump processes", f"Itô{A}s formula for jump processes"),
    ("Sur la constante d'Euler", f"Sur la constante d{A}Euler"),
    ("Don't panic", f"Don{A}t panic"),                                # synthetic
    ("Tsirel'son's equation in discrete time", f"Tsirel{A}son{A}s equation in discrete time"),
    ("Mean-field limit for SDE's singular in time", f"Mean-field limit for SDE{A}s singular in time"),
    ("L'Hôpital's rule revisited", f"L{A}Hôpital{A}s rule revisited"),  # synthetic
    ("Construction de solutions d'EDP", f"Construction de solutions d{A}EDP"),
    # elision straight into a quotation (library: l’« inégalité »)
    ('Présentation de l\'"inégalité de Hardy"', f'Présentation de l{A}"inégalité de Hardy"'),
    ("Présentation de l'« inégalité »", f"Présentation de l{A}« inégalité »"),
    # possessive after -s, with no quotation open
    ("On a conjecture in Komlós' theorem", f"On a conjecture in Komlós{A} theorem"),
    ("A Bayesian version of Robbins' problem", f"A Bayesian version of Robbins{A} problem"),
    ("‘Théorie de la spéculation’, the missing piece in Walras' general equilibrium",
     f"‘Théorie de la spéculation’, the missing piece in Walras{A} general equilibrium"),
    ("ON ROBBINS' PROBLEM", f"ON ROBBINS{A} PROBLEM"),                  # synthetic: capitals
    # an earlier word-initial mark that does not open a quotation ('90s)
    ("From the '90s to Walras' law", f"From the '90s to Walras{A} law"),  # synthetic
    # possessive after a bracket or a digit
    ("Calibration of Heston (2008)'s model", f"Calibration of Heston (2008){A}s model"),
    ("Kolmogorov [1933]'s axioms", f"Kolmogorov [1933]{A}s axioms"),  # synthetic
    ("Finance in the 1990's", f"Finance in the 1990{A}s"),            # synthetic
    ("FINANCE IN THE 1990'S", f"FINANCE IN THE 1990{A}S"),            # synthetic: capitals
    # word-initial elision
    ("'Tis an equity puzzle", f"{A}Tis an equity puzzle"),
    ("So 'tis an equity puzzle", f"So {A}tis an equity puzzle"),      # synthetic
    # a quotation that has closed does not hide a possessive after it
    ("Itô's lemma and Walras' law", f"Itô{A}s lemma and Walras{A} law"),   # synthetic
])
def test_an_apostrophe_becomes_u2019(title, expected):
    assert title_apostrophes(title) == expected


@pytest.mark.parametrize("title", [
    # mathematical primes
    "On the sample continuity of S'-processes",
    "Decompositions of semimartingales on S'",
    "Solutions of f'(x) = g(x)",                                       # synthetic
    "The process X'_t revisited",                                      # synthetic
    "Oscillation of u'' + q u = 0",                                    # synthetic
    "Estimates for s' and t'",                                         # synthetic: a lone s
    # quotation marks: never an apostrophe, and never half-converted
    "A fresh look at the 'hot hand' paradox",
    "Dynamic preference 'reversals' and time inconsistency",
    "'Choose your opponent', a new knot",
    "Comment on the article 'The harmonic explorer'",
    # TeX's '' closer
    "Commentary on ``Longest increasing subsequences'' by Aldous",
    "Gauss' disquisitiones generales circa superficies curvas''",
    # a bracket closing without a possessive
    "Estimates for (fg)' in L²",                                       # synthetic
    "A note on (uv)'",                                                 # synthetic
    # a word-initial mark opens a quotation unless it is 'tis
    "'Tissue growth', a model",                                        # synthetic
    # a quotation still open: "s'" may close it; ’ inside it does not
    "Economic preference ‘reversals' and time",                        # synthetic
    "On ‘Itô’s reversals' and more",                                   # synthetic
    "'Walras' equilibria', a note",                                    # synthetic: opens at 0
    "On ‘the '90s and Walras' law",                                    # synthetic: '90s closes nothing
    # a single quotation closing inside a double one
    '"The \'hot hand\'" fallacy',                                      # synthetic
])
def test_what_is_not_certainly_an_apostrophe_is_left_as_it_is(title):
    out = title_apostrophes(title)
    # "Gauss'" in the second TeX case IS a possessive; everything else stays.
    expected = title.replace("Gauss'", f"Gauss{A}")
    assert out == expected


def test_decomposed_input_is_judged_like_composed():
    """macOS returns names NFD: "Itô's" arrives as o + U+0302 + '."""
    nfd = unicodedata.normalize("NFD", "Itô's formula")
    assert unicodedata.normalize("NFC", title_apostrophes(nfd)) == f"Itô{A}s formula"


@pytest.mark.parametrize("opener", list("«‹“‘„"))
def test_an_elision_runs_into_any_opening_mark(opener):
    assert title_apostrophes(f"Sur l'{opener}x") == f"Sur l{A}{opener}x"


def test_mathematics_is_protected():
    title = "Bounds for f's derivative"
    assert title_apostrophes(title, [(11, 14)]) == title
    assert title_apostrophes(title) == f"Bounds for f{A}s derivative"
    # the span ends where it says: a mark just after it is not protected
    assert title_apostrophes("Itô's", [(0, 3)]) == f"Itô{A}s"
    assert title_apostrophes("Itô's", [(3, 4)]) == "Itô's"


def test_arrival_protects_mathematics_too():
    title = "Bounds for f's derivative"
    assert convert_straight_quotes_to_proper(title, "en", [(11, 14)], []) == title


def test_a_whitelisted_phrase_protects_casing_not_this_mark():
    """"Solov'ev" is a capitalisation-whitelist entry; the title spells the
    soft sign U+2019, as in "Tsirel’son"."""
    assert convert_straight_quotes_to_proper("Solov'ev", "en", [], [(0, 8)]) == f"Solov{A}ev"


def test_only_a_straight_mark_can_be_judged():
    for t, i in (("Itô’s", 3), ("Itô's", 2), ("Itô's", -1), ("Itô's", 5), ("", 0)):
        assert is_title_apostrophe(t, i) is False


# ------------------------------------------------------------ at arrival

def _arrive(title: str, authors=(Author("Smith", "J."),)) -> str:
    return CMO(external_id="x", source="t", title=title,
               authors=list(authors)).get_canonical_filename()


@pytest.mark.parametrize("title,expected", [
    # no straight double quote: the old path converted NOTHING here
    ("Itô's formula and l'équation de la chaleur",
     f"Smith, J. - Itô{A}s formula and l{A}équation de la chaleur.pdf"),
    ("Solutions of f'(x) = g(x)", "Smith, J. - Solutions of f'(x) = g(x).pdf"),
    # a single quotation is paired since 2026-10-15
    # (tests/safety/test_single_quotations_at_arrival.py)
    ("The 'hot hand' fallacy", "Smith, J. - The ‘hot hand’ fallacy.pdf"),
    # with one: the old path kept the contraction straight and broke the rest
    ('The "hot hand" and Itô\'s formula', f"Smith, J. - The ‘hot hand’ and Itô{A}s formula.pdf"),
    ('The "hot hand" and f\'(x)', "Smith, J. - The ‘hot hand’ and f'(x).pdf"),
    ('Sur l\'équation de "Burgers"', f"Smith, J. - Sur l{A}équation de « Burgers ».pdf"),
])
def test_arrival_names_the_title_by_the_ruling(title, expected):
    assert _arrive(title) == expected


def test_the_author_block_keeps_u0027():
    """The author block is a KEY: every authority writes U+0027."""
    out = _arrive("Convex functions and Orlicz's spaces",
                  (Author("Krasnosel'skii", "M. A."),))
    assert out == f"Krasnosel'skii, M. A. - Convex functions and Orlicz{A}s spaces.pdf"


def test_a_quoted_word_never_gets_two_closing_marks():
    for lang in ("en", "fr", None):
        out = convert_straight_quotes_to_proper(
            'The "x" and the \'hot hand\' fallacy', lang, [], [])
        assert f"{A}hot hand{A}" not in out
        assert "'hot hand'" in out


def test_the_flag_names_what_was_left_and_only_that():
    _, flags = fix_and_flag_quotes("Itô's formula", "en", [], [])
    assert flags == []
    _, flags = fix_and_flag_quotes("Itô's formula for f'(x)", "en", [], [])
    assert flags == ["straight single quote left as it is: not an apostrophe "
                     "(a quotation mark or a prime)"]
    _, flags = fix_and_flag_quotes("Itô's formula for f'(x)", "en", [(18, 23)], [])
    assert flags == [], "a prime inside mathematics is not reported"


# ------------------------------------------------------------ properties

_ALPHABET = st.sampled_from(list("abcsStoéô XY'()_^-,2’‘\"«"))
_TITLES = st.text(alphabet=_ALPHABET, max_size=40)


@settings(max_examples=400)
@given(_TITLES)
def test_only_a_straight_mark_changes_and_only_to_u2019(title):
    out = title_apostrophes(title)
    assert len(out) == len(title)
    for a, b in zip(title, out):
        assert a == b or (a == "'" and b == A)


@settings(max_examples=400)
@given(_TITLES)
def test_matching_keys_are_unchanged(title):
    """Search and duplicate detection fold every apostrophe-like mark; the
    conversion must not split a paper from its earlier copies."""
    assert fold_marks(title_apostrophes(title)) == fold_marks(title)


@settings(max_examples=400)
@given(_TITLES)
def test_a_fixpoint(title):
    once = title_apostrophes(title)
    assert title_apostrophes(once) == once


@settings(max_examples=400)
@given(_TITLES)
def test_an_opening_mark_never_becomes_a_closing_one(title):
    """The '’hot hand’' signature: a mark that starts a word is an opener,
    unless it starts 'tis."""
    out = title_apostrophes(title)
    for i, (a, b) in enumerate(zip(title, out)):
        if a == "'" and b == A and (i == 0 or title[i - 1].isspace()):
            assert re.match(r"(?i)tis(?![^\W\d_])", title[i + 1:])


@settings(max_examples=400)
@given(st.text(alphabet=st.sampled_from(list("abc oé,")), max_size=12),
       st.sampled_from(list("fguxyXYSs")),
       st.integers(min_value=1, max_value=3),
       st.sampled_from(["(", "_", "^", "-", " ", ",", "=", ")", ""]),
       st.text(alphabet=st.sampled_from(list("abc ")), max_size=12))
def test_a_prime_is_never_an_apostrophe(prefix, var, k, follower, suffix):
    """One letter standing alone, then its primes, then not a letter.

    (A letter after the mark is the shape of an elision -- "l'a" -- and
    the elision wins: of the straight marks in the filenames papers arrived
    with, 1,142 sit between two lower-case letters and none is a prime.)"""
    if not follower:
        suffix = ""          # the primes end the title
    title = f"{prefix} {var}{chr(39) * k}{follower}{suffix}"
    start = len(prefix) + 2
    out = title_apostrophes(title)
    assert out[start:start + k] == "'" * k


@settings(max_examples=300)
@given(_TITLES, st.integers(min_value=0, max_value=40), st.integers(min_value=0, max_value=40))
def test_a_protected_span_is_never_touched(title, a, b):
    a, b = sorted((a, b))
    out = title_apostrophes(title, [(a, b)])
    assert out[a:b] == title[a:b]


@settings(max_examples=300)
@given(st.text(alphabet=st.sampled_from(list("aeoôéè sS'()")), max_size=30))
def test_composed_and_decomposed_get_the_same_answer(title):
    nfc = unicodedata.normalize("NFC", title)
    nfd = unicodedata.normalize("NFD", title)
    assert unicodedata.normalize("NFC", title_apostrophes(nfd)) == title_apostrophes(nfc)
