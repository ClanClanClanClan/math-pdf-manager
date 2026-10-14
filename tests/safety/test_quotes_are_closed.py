"""Quotation marks: the owner's convention, closed, and never set on a guess.

HISTORY. ``QUOTE_CONVERSIONS`` once held only OPENING marks and
``convert_straight_quotes_to_proper`` gave that opener to EVERY straight
double quote, so the ingest namer produced
'Commentary on “Longest increasing subsequences“ by Aldous'. That was
fixed by alternating opener/closer while the policy was still open.

THE POLICY, settled 2026-10-14 ("1B", on his instruction "typographically
correct, ALWAYS"):

    English   ‘ outer ’  (“ inner ”)      French   « outer »  (‹ inner ›),
    with an ordinary space inside each guillemet.
    Any other or undetected language: the marks are left as they are.

It lives in processing/quote_marks.py, and the ingest path
(check_filename -> fix_and_flag_quotes -> convert_straight_quotes_to_proper)
now calls it. Before, English got the American “…” and German, Spanish and
Italian titles were converted on a detector that disagrees with itself on
at least 12 of the library's 184 straight-quoted titles.
"""
from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from processing.quote_marks import fold_quotes, requote
from validators.filename_checker.text_processing import convert_straight_quotes_to_proper

TITLE = 'Commentary on "a paper title" by someone'


def _convert(text: str, lang) -> str:
    return convert_straight_quotes_to_proper(text, lang, [], [])


# ------------------------------------------------------------ the convention

def test_english_takes_single_outer_quotes():
    assert _convert(TITLE, "en") == "Commentary on ‘a paper title’ by someone"


def test_french_takes_guillemets_with_ordinary_spaces():
    assert _convert(TITLE, "fr") == "Commentary on « a paper title » by someone"
    assert " " not in _convert(TITLE, "fr") and " " not in _convert(TITLE, "fr")


@pytest.mark.parametrize("lang", ["de", "es", "it", "ca", None])
def test_any_other_language_is_left_alone(lang):
    """Never set on a guess: the detector routes French titles to es/it/ca."""
    assert _convert(TITLE, lang) == TITLE


def test_an_undetectable_language_is_not_treated_as_english():
    """check_filename used to fall back to "en" when detection failed."""
    from validators.filename_checker.core import check_filename
    res = check_filename('X, Y. - "ab" cd.pdf', auto_fix_nfc=True)
    out = res.corrected_filename or ""
    assert "‘" not in out and "“" not in out


def test_american_doubles_already_in_a_title_become_english_singles():
    assert requote("A fresh look at the “hot hand” paradox", "en").title == \
        "A fresh look at the ‘hot hand’ paradox"


def test_the_ingest_malformed_signature_is_closed():
    """'“…“' -- two openers -- is the on-disk signature of the old defect."""
    assert requote("Commentary on “Longest increasing subsequences“ by Aldous", "en").title == \
        "Commentary on ‘Longest increasing subsequences’ by Aldous"


# ----------------------------------------------- what is never mark-by-mark

@pytest.mark.parametrize("title,why", [
    ('On "a" and "b"', "paired"),                       # two quotations, or one nested
    ('Correction "Quelques résultats de "mécanique stochastique""', "paired"),
    ('An odd "count', "paired"),
    ('A 3"5 rule', "paired"),                           # an inch mark, letter-flanked
    ("Smith’s ‘good’ and “bad” cases", "single"),      # mixed: nesting or convention
])
def test_what_cannot_be_paired_with_certainty_goes_to_review(title, why):
    r = requote(title, "en")
    assert r.status == "review" and why in r.why and r.title == title


def test_an_unknown_language_goes_to_review_with_the_reason():
    r = requote(TITLE, None)
    assert r.status == "review" and "language not known" in r.why


def test_apostrophes_are_not_quotes():
    for t in ("Itô’s formula", "Kolmogorov's equation", "l’intégrale"):
        assert requote(t, "en") == requote(t, "en").__class__(t, "unchanged")


def test_a_top_level_english_single_pair_is_already_right():
    assert requote("The ‘hot hand’ paradox", "en").status == "unchanged"


def test_quotes_inside_a_math_region_are_left_alone():
    text = 'A "b" c'
    assert convert_straight_quotes_to_proper(text, "en", [(2, 5)], []) == text


# ---------------------------------------------------------------- properties

_WORDS = st.text(alphabet=st.sampled_from("abc xyz"), min_size=1, max_size=12) \
    .filter(lambda s: s.strip() and s == s.strip())


@given(_WORDS, _WORDS, _WORDS, st.sampled_from(["en", "fr"]))
def test_a_balanced_pair_becomes_exactly_one_opener_and_one_closer(a, b, c, lang):
    out = requote(f'{a} "{b}" {c}', lang).title
    o, cl = ("‘", "’") if lang == "en" else ("«", "»")
    assert out.count(o) == 1 and out.count(cl) == 1 and '"' not in out
    assert out.index(o) < out.index(cl)
    assert requote(out, lang).title == out, "a fixpoint"


@given(_WORDS, _WORDS, _WORDS)
def test_every_form_of_the_same_quotation_folds_to_one_key(a, b, c):
    """Search and same-paper detection must not split on the conversion."""
    forms = [f'{a} "{b}" {c}', f"{a} “{b}” {c}", f"{a} ‘{b}’ {c}", f"{a} « {b} » {c}",
             f"{a} «{b}» {c}"]
    assert len({fold_quotes(f) for f in forms}) == 1


def test_the_fold_keeps_apostrophes():
    assert fold_quotes("Itô’s ‘lemma’") == "Itô’s lemma"


def test_a_straight_mark_used_as_an_apostrophe_is_never_paired():
    """Two letter-flanked marks would otherwise pair into ‘s and l’."""
    r = requote('Itô"s formula and l"intégrale', "en")
    assert r.status == "review" and r.title == 'Itô"s formula and l"intégrale'


def test_when_detection_fails_the_importer_leaves_quotes_straight(monkeypatch):
    import validators.filename_checker.core as core
    from langdetect import LangDetectException

    def _fail(text):
        raise LangDetectException(0, "no features")
    monkeypatch.setattr(core, "detect", _fail)
    res = core.check_filename('Smith, J. - On "hot hand" effects.pdf', auto_fix_nfc=True)
    out = res.corrected_filename or 'Smith, J. - On "hot hand" effects.pdf'
    assert '"hot hand"' in out, out


def test_search_finds_a_title_whatever_quote_marks_were_typed(tmp_path):
    from ui.search_page import build_index, search_index
    p = tmp_path / "01 - Published papers" / "S" / "Smith, J. - A fresh look at the ‘hot hand’ paradox.pdf"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"%PDF")
    index = build_index(tmp_path)
    for q in ('"hot hand"', "“hot hand”", "« hot hand »", "‘hot hand’"):
        assert search_index(index, q), q


def test_same_paper_detection_sees_through_quote_forms():
    from processing.preprint_variants import _fold, _title_ratio
    a, b = 'A fresh look at the "hot hand" paradox', "A fresh look at the ‘hot hand’ paradox"
    assert _fold(a) == _fold(b)
    assert _title_ratio(a, b) == 100.0
