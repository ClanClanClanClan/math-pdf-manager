"""A new paper's single-quoted passage: paired when certain, else left and said why.

THE RULING (processing/quote_marks.py, the owner's of 2026-10-14):
English ‘outer’ “inner”, French « outer » ‹ inner ›, any other or unknown
language left as it is. The library agrees: 175 in-scope titles write a
single quotation, every one as ‘…’.

THE DEFECT, found 2026-10-15 (docs/FILENAME_CONVENTION.md §6 item 3).
``requote`` converted double marks only, so "the 'hot hand' paradox"
arrived with its straight marks -- and "the ‘large' investor", the form
publishers' metadata often carries, arrived half-converted.

THE HARD PART. After a word in -s, a closing quote and a plural possessive
are the same character in the same place: "the 'reversals' and" against
"Walras' law". Where a single quotation opens and closes is defined once,
in processing/apostrophes.py (which needs it to judge a mark after "s");
the pairing in quote_marks uses the same definitions. It pairs when the
first mark that ends a word after the opener can be nothing but a closing
quote, or when no other mark could close instead. Anything else stays as
it arrived, and the importer says why.

Every pathology case is a real title -- the original filename a paper
arrived with, or a library title with its marks made straight -- unless
marked synthetic.
"""
from __future__ import annotations

import re
import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from arxivbot.models.cmo import CMO, Author
from processing.apostrophes import _quotation_open_at, fold_marks, title_apostrophes
from processing.quote_marks import (fold_quotes, holds_straight_quotation,
                                    quotation_language, requote)
from validators.filename_checker.text_processing import (
    convert_straight_quotes_to_proper, fix_and_flag_quotes)


def _convert(text: str, lang="en", regions=()) -> str:
    return convert_straight_quotes_to_proper(text, lang, list(regions), [])


def _arrive(title: str) -> str:
    name = CMO(external_id="x", source="t", title=title,
               authors=[Author("Smith", "J.")]).get_canonical_filename()
    return name[len("Smith, J. - "):-len(".pdf")]


# ------------------------------------------------------------ paired

# (as the paper arrived, as the library writes it)
PAIRED = [
    # straight, as arrived (records' original filenames)
    ("A comment on the article 'The harmonic descent chain' by D.J. Aldous, S. Janson and X. Li",
     "A comment on the article ‘The harmonic descent chain’ by D.J. Aldous, S. Janson and X. Li"),
    ("The not-so-hidden risks of 'hidden-to-maturity' accounting, on depositor runs and bank resilience",
     "The not-so-hidden risks of ‘hidden-to-maturity’ accounting, on depositor runs and bank resilience"),
    ("Dynamic programming for the stochastic matching model on general graphs, the case of the 'N-graph'",
     "Dynamic programming for the stochastic matching model on general graphs, the case of the ‘N-graph’"),
    ("'Choose your opponent', a new knockout format for sports tournaments",
     "‘Choose your opponent’, a new knockout format for sports tournaments"),
    ("'Finem Lauda' or the risks in swaps", "‘Finem Lauda’ or the risks in swaps"),
    ("A remark on Gatheral's 'most-likely path approximation' of implied volatility",
     "A remark on Gatheral’s ‘most-likely path approximation’ of implied volatility"),
    ("Does God practice a random walk? The 'financial physics' of a nineteenth-century forerunner, Jules Regnault",
     "Does God practice a random walk? The ‘financial physics’ of a nineteenth-century forerunner, Jules Regnault"),
    # the closer follows a word in -s, and nothing else could close
    ("lecture notes of the XV 'Jacques-Louis Lions' Spanish–French school",
     "lecture notes of the XV ‘Jacques-Louis Lions’ Spanish–French school"),
    ("Correction 'Generalizations of Gross's and Minlos's theorems'",       # library, made straight
     "Correction ‘Generalizations of Gross’s and Minlos’s theorems’"),
    ("Dynamic preference 'reversals' and time inconsistency",             # library, made straight
     "Dynamic preference ‘reversals’ and time inconsistency"),
    # a possessive in -s AFTER the quotation has closed
    ("Louis Bachelier's 'Théorie de la spéculation', the missing piece in Walras' general equilibrium",
     "Louis Bachelier’s ‘Théorie de la spéculation’, the missing piece in Walras’ general equilibrium"),
    # publishers' half-converted form: the opener curly, the closer straight
    ("Differentiating ‘the user' in DSR, developing demand side response in advanced economies",
     "Differentiating ‘the user’ in DSR, developing demand side response in advanced economies"),
    ("Optimal consumption choices for a ‘large' investor", "Optimal consumption choices for a ‘large’ investor"),
    ("Principals vs. principals, the twilight of the ‘agency theory'",
     "Principals vs. principals, the twilight of the ‘agency theory’"),
    ("Indeterminateness and ‘the' universe of sets, multiversism, potentialism, and pluralism",  # in To be sorted
     "Indeterminateness and ‘the’ universe of sets, multiversism, potentialism, and pluralism"),
    ("Corrigendum to ‘Applications of Strassen's theorem and Choquet theory to optimal transport "
     "problems, to uniformly convex functions and to uniformly smooth functions' [Nonlinear Anal., 232 (2023) 113267]",
     "Corrigendum to ‘Applications of Strassen’s theorem and Choquet theory to optimal transport "
     "problems, to uniformly convex functions and to uniformly smooth functions’ [Nonlinear Anal., 232 (2023) 113267]"),
    ("The 'hot hand' and f'(x)", "The ‘hot hand’ and f'(x)"),               # synthetic: a prime stays
    ("The 'large’ investor", "The ‘large’ investor"),                        # synthetic: the reverse half
]


@pytest.mark.parametrize("arrived,shelved", PAIRED)
def test_a_certain_single_quotation_takes_the_english_outer_marks(arrived, shelved):
    assert _convert(arrived) == shelved


@pytest.mark.parametrize("arrived,shelved", [
    # a library title, its straight double marks written as single ones
    ("Une preuve 'standard' du principe d'invariance de Stoll",
     "Une preuve « standard » du principe d’invariance de Stoll"),
    ("Sur l'équation de 'Burgers' et la chaleur", "Sur l’équation de « Burgers » et la chaleur"),  # synthetic
])
def test_french_takes_guillemets_with_ordinary_spaces(arrived, shelved):
    assert _convert(arrived, "fr") == shelved


@pytest.mark.parametrize("arrived,shelved", [
    ("A comment on the article 'The harmonic descent chain' by D.J. Aldous, S. Janson and X. Li",
     "A comment on the article ‘The harmonic descent chain’ by D.J. Aldous, S. Janson and X. Li"),
    ("Optimal consumption choices for a ‘large' investor", "Optimal consumption choices for a ‘large’ investor"),
    ("Louis Bachelier's 'Théorie de la spéculation', the missing piece in Walras' general equilibrium",
     "Louis Bachelier’s ‘Théorie de la spéculation’, the missing piece in Walras’ general equilibrium"),
    ("Sur l'équation de 'Burgers' et les ondes de choc", "Sur l’équation de « Burgers » et les ondes de choc"),
])
def test_arrival_names_it_end_to_end(arrived, shelved):
    """Through the call that names every new paper: the language is found
    for a single quotation too, from the words around it."""
    assert _arrive(arrived) == shelved


# ------------------------------------------------------------ left, and why

@pytest.mark.parametrize("title,lang,why", [
    # TeX's doubled singles, as Crossref sent them (real, arrived this way)
    ("Is no news bad news? Information transmission and the role of ‘‘early warning'' in the principal–agent model",
     "en", "more than one mark opens"),
    # a single quotation inside a double one (real, arrived this way)
    ('"Option pricing theory, is \'risk-free\' hedging feasible?"', "en", "nesting"),
    # "Walras'" may close it, or be a possessive inside it            (synthetic)
    ("'Walras' law' revisited", "en", "after a word in -s"),
    ("The 'reversals' and Walras' law", "en", "after a word in -s"),
    ("The 'S' and S' processes", "en", "more than one mark could close"),   # a lone letter
    ("'Is it?' and f' bounded", "en", "more than one mark could close"),    # after "?"
    ("'THE REVERSALS' AND WALRAS' LAW", "en", "more than one mark could close"),  # capital S
    # a prime before a digit is still a mark that could close
    ("Preference 'reversals' and the norm f'2", "en", "more than one mark could close"),
    ("The 'hot hand fallacy", "en", "nothing closes it"),                   # synthetic
    ("On 'a' and 'b'", "en", "more than one mark opens"),                    # synthetic
    ("Über die 'heiße Hand'", "de", "language not known (de)"),              # synthetic
    ("The 'hot hand' fallacy", None, "language not known (none)"),
    ("Le ‘standard’ et f'(x)", "fr", "another convention"),                 # curly ‘…’ in French
])
def test_what_is_not_certain_is_left_as_it_is_and_says_why(title, lang, why):
    out, flags = fix_and_flag_quotes(title, lang, [], [])
    assert out == title_apostrophes(title)
    assert any(f.startswith("quotation marks left as they are: ") and why in f
               for f in flags), flags


def test_a_quotation_mark_inside_mathematics_is_not_ours():
    title = "The 'hot hand' paradox"
    assert _convert(title, regions=[(4, 5)]) == title
    assert _convert(title, regions=[(13, 14)]) == title
    assert _convert(title, regions=[(5, 13)]) == "The ‘hot hand’ paradox"
    _, flags = fix_and_flag_quotes(title, "en", [(4, 5)], [])
    assert flags == ["quotation marks left as they are: a quotation mark inside "
                     "mathematics or a protected phrase",
                     # the closer, outside it, is still a straight mark left behind
                     "straight single quote left as it is: not an apostrophe "
                     "(a quotation mark or a prime)"]


def test_a_quotation_mark_inside_a_protected_phrase_is_not_ours():
    """As for double marks: a whitelisted phrase holding the mark is left
    whole."""
    title = "The 'hot hand' paradox"
    assert convert_straight_quotes_to_proper(title, "en", [], [(4, 9)]) == title
    assert convert_straight_quotes_to_proper(title, "en", [], [(5, 9)]) == "The ‘hot hand’ paradox"


def test_the_language_is_judged_on_the_title_the_converter_sees(monkeypatch):
    """"'Tis" is an elision: settled first, it opens nothing, and the one
    quotation left is set aside so the words around it pick English --
    whatever the detector says. Judged on the raw title, the two
    opener-shaped marks would leave the detector's French standing."""
    import validators.filename_checker.core as core
    monkeypatch.setattr(core, "detect", lambda t: "fr")
    res = core.check_filename("Smith, J. - 'Tis the 'hot hand' of chance.pdf", auto_fix_nfc=True)
    assert res.corrected_filename == "Smith, J. - ’Tis the ‘hot hand’ of chance.pdf"


def test_tis_is_an_elision_not_a_quotation():
    assert _convert("'Tis an equity puzzlement") == "’Tis an equity puzzlement"


def test_quotation_marks_that_arrived_curly_are_left_as_they_arrived():
    """Arrival converts STRAIGHT marks. A ‘…’ in French, or “…” with only a
    prime beside it, is not weighed at all -- as before."""
    for t, lang in (("Le ‘standard’ modèle", "fr"), ("Yule’s “nonsense” for f'(x)", "en")):
        assert not holds_straight_quotation(t)
        assert _convert(t, lang) == t


def test_the_flags_say_what_was_done_and_only_that():
    _, flags = fix_and_flag_quotes("The 'hot hand' paradox", "en", [], [])
    assert flags == [], "a paired quotation is not a problem left behind"
    _, flags = fix_and_flag_quotes("The 'hot hand' and f'(x)", "en", [], [])
    assert flags == ["straight single quote left as it is: not an apostrophe "
                     "(a quotation mark or a prime)"], "the prime is still there"
    _, flags = fix_and_flag_quotes("The ‘large' investor", "en", [], [])
    assert flags == []


def test_the_importer_asks_the_language_only_for_a_quotation(monkeypatch):
    """No detector call for a title whose only straight marks are
    apostrophes; one for a single quotation."""
    import validators.filename_checker.core as core
    calls = []
    real = core.detect
    monkeypatch.setattr(core, "detect", lambda t: calls.append(t) or real(t))
    core.check_filename("Smith, J. - Itô's formula for f'(x).pdf", auto_fix_nfc=True)
    assert len(calls) == 1, calls
    calls.clear()
    res = core.check_filename("Smith, J. - On the 'hot hand' paradox.pdf", auto_fix_nfc=True)
    assert calls[-1] == "On the 'hot hand' paradox", calls
    assert res.corrected_filename == "Smith, J. - On the ‘hot hand’ paradox.pdf"


# ------------------------------------------------------------ whose language

def test_the_words_around_a_single_quotation_decide_its_language():
    assert quotation_language("Sur la 'main chaude' et les joueurs", "en") == "fr"
    assert quotation_language("'Théorie de la spéculation', the missing piece", "fr") == "en"
    # mixed kinds are never paired, so nothing is set aside
    assert quotation_language('The "x" and the \'y\'', "fr") == "fr"


# ------------------------------------------------------------ matching keys

def _variant_key(s: str) -> str:
    from processing.preprint_variants import _fold
    return _fold(s)


@pytest.mark.parametrize("arrived,shelved", PAIRED)
def test_the_name_given_folds_like_the_name_it_arrived_with(arrived, shelved):
    """NAMING-RULING 1.3: a quote change must not fork the keys Search and
    same-paper detection compare."""
    assert _variant_key(arrived) == _variant_key(shelved)


def test_a_mark_that_only_looks_like_an_opener_is_kept_by_the_fold():
    """Real author block: "in 't Hout, K." A word-initial straight mark
    before a letter has an opener's shape, but nothing closes it, so it is
    an elision and must fold like "in ’t Hout". (A first version of this
    change stripped it, and the duplicate detector lost the pair.)"""
    assert _variant_key("in 't Hout") == _variant_key("in ’t Hout")
    assert fold_quotes("in 't Hout, K.") == "in 't Hout, K."
    # once it is certainly a quotation, it goes
    assert fold_quotes("On the 'hot hand'") == "On the hot hand"


@pytest.mark.parametrize("text,folded", [
    # two quotations: each ‘ goes with the ’ that closes it, as always
    ("On ‘a’ and ‘b’ cases", "On a and b cases"),                         # synthetic
    # the first ’ that ends a word closes it; an apostrophe inside stays
    ("‘Itô’s ‘lemma’", "Itô’s lemma"),                                     # synthetic
    ("the ‘reversals’ and Walras’ law", "the reversals and Walras’ law"),  # synthetic
    # a straight mark in a quotation the pairing cannot settle stays
    ("the ‘reversals' and Walras' law", "the reversals' and Walras' law"),  # synthetic
])
def test_where_the_pairing_is_not_certain_the_fold_keeps_its_old_rule(text, folded):
    """Only a ‘ opens, and the ’ that ends a word closes it -- the keys of
    the 175 names already on a shelf do not move."""
    assert fold_quotes(text) == folded


def test_search_finds_a_title_whatever_single_quotes_were_typed(tmp_path):
    from ui.search_page import build_index, search_index
    p = tmp_path / "01 - Published papers" / "S" / "Smith, J. - Le « standard » et la main.pdf"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"%PDF")
    index = build_index(tmp_path)
    for q in ("'standard'", "‘standard'", "« standard »", '"standard"'):
        assert search_index(index, q), q


# ---------------------------------------------------------------- properties

_WORD = st.text(alphabet=st.sampled_from("abcdeéxyz-"), min_size=2, max_size=8) \
    .filter(lambda w: w[0].isalpha() and w[-1].isalpha())
_WORDS = st.lists(_WORD, min_size=1, max_size=4).map(" ".join)


@settings(max_examples=300, deadline=None)
@given(_WORDS, _WORDS, _WORDS, st.sampled_from(["en", "fr"]),
       st.sampled_from(["'", "‘"]), st.sampled_from(["'", "’"]))
def test_a_lone_quotation_becomes_one_opener_and_one_closer(a, b, c, lang, op, cl):
    title = f"{a} {op}{b}{cl} {c}"
    if op == "‘" and cl == "’":
        return                                       # arrived curly: not ours
    out = requote(title, lang).title
    o, close = ("‘", "’") if lang == "en" else ("«", "»")
    inner = b if lang == "en" else f" {b} "
    assert out == f"{a} {o}{inner}{close} {c}"
    assert "'" not in out
    assert requote(out, lang).title == out, "a fixpoint"


_QUOTE_MARKS = frozenset("'\"‘’“”«»„")
_ENGLISH_OUTER = frozenset("‘’")


@settings(max_examples=300, deadline=None)
@given(st.text(alphabet=st.sampled_from(list("abs S'’‘\"«,()")), max_size=30),
       st.sampled_from(["en", "fr"]))
def test_only_the_quotation_marks_change(title, lang):
    """Letters, apostrophes and every other character keep their place;
    in English the title keeps its length."""
    r = requote(title, lang)
    if lang == "en":
        assert len(r.title) == len(title)
        for x, y in zip(title, r.title):
            assert x == y or (x in _QUOTE_MARKS and y in _ENGLISH_OUTER)
    strip = lambda s: re.sub(r"[\s'\"‘’“”«»„]", "", s)
    assert strip(r.title) == strip(title)


@settings(max_examples=300, deadline=None)
@given(st.text(alphabet=st.sampled_from(list("abs S'’‘,.?")), max_size=30),
       st.sampled_from(["en", "fr"]))
def test_converting_never_forks_the_matching_key(title, lang):
    """Single quotations. (Double marks have a quirk of their own, older
    than this: '""S' pairs into '‘’S', whose closer reads as an apostrophe.)"""
    out = requote(title, lang).title
    if out != title:
        assert fold_marks(fold_quotes(out)) == fold_marks(fold_quotes(title))


@settings(max_examples=300, deadline=None)
@given(_WORDS, _WORDS, _WORDS, st.sampled_from(["'", "’"]))
def test_a_mark_after_a_word_in_s_with_another_closer_after_it_is_never_paired(a, b, c, later):
    """'…s' x' -- the first may close, or be a possessive. Never guess."""
    title = f"'{a}s' {b}{later} {c}"
    r = requote(title, "en")
    assert r.title == title and r.status == "review"


@settings(max_examples=300, deadline=None)
@given(_WORDS, _WORDS, _WORDS, _WORDS)
def test_two_quotations_are_never_paired(a, b, c, d):
    title = f"{a} '{b}' {c} '{d}'"
    assert requote(title, "en").title == title


@settings(max_examples=300, deadline=None)
@given(st.text(alphabet=st.sampled_from(list("abcs S'’‘é,()")), max_size=30))
def test_the_pairing_and_the_apostrophe_rule_agree_where_the_quotation_is(title):
    """One definition of where a single quotation opens and closes: inside
    every pair ``requote`` makes, ``apostrophes`` sees a quotation open;
    just after it, closed."""
    from processing.quote_marks import _single
    found = _single(title)
    if found is None or found[0] is None:
        return
    a, b = found[0]
    assert all(_quotation_open_at(title, j) for j in range(a + 1, b + 1))
    assert not _quotation_open_at(title, b + 1)


@settings(max_examples=300, deadline=None)
@given(_WORDS, _WORDS, _WORDS, st.integers(min_value=0, max_value=60),
       st.integers(min_value=0, max_value=60))
def test_a_protected_mark_is_never_converted(a, b, c, x, y):
    title = f"{a} '{b}' {c}"
    x, y = sorted((x, y))
    out = requote(title, "en", [(x, y)]).title
    for i in range(x, min(y, len(title))):
        assert out[i] == title[i]


@settings(max_examples=300, deadline=None)
@given(st.text(alphabet=st.sampled_from(list("aeoôéè sS'’")), max_size=30))
def test_composed_and_decomposed_get_the_same_answer(title):
    nfc = unicodedata.normalize("NFC", title)
    nfd = unicodedata.normalize("NFD", title)
    assert unicodedata.normalize("NFC", requote(nfd, "en").title) == requote(nfc, "en").title
