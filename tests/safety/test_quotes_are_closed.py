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


# ------------------------------------- whose language: the title's, not the quote's

from processing.quote_marks import quotation_language  # noqa: E402

# Real titles, 2026-10-15. The first four were filed with « » because the
# quoted French pulled the detector to French; the owner ruled them English.
ENGLISH_AROUND_FRENCH = [
    'Louis Bachelier’s "Théorie de la spéculation", the missing piece in Walras’ general equilibrium',
    "Desargues and the “trait à preuves“",
    "Yule’s “nonsense correlation”, moments and density",
    'A remark on the paper "Une martingale d’opérateurs bornés, non représentable en '
    'intégrale stochastique", by J.-L. Journé and P.-A. Meyer',
    'Louis Bachelier on the centenary of "Théorie de la spéculation"',
]


@pytest.mark.parametrize("title", ENGLISH_AROUND_FRENCH)
def test_an_english_title_quoting_french_takes_english_marks(title):
    assert quotation_language(title, "fr") == "en"


@pytest.mark.parametrize("title,want", [
    ('Les "principes d’invariance" en probabilité sur l’espace de Wiener', "fr"),
    ('Erratum et addendum "les dérivations en théorie descriptive des ensembles"', "fr"),
    ('Remarques sur "Optimal stopping and free boundaries"', "fr"),
    ('Présentation de l’"inégalité de Doob" de Métivier et Pellaumail', "fr"),
    ('Erratum to "Some remarks on mutual windings"', "en"),
    ('Comment on “Optimal contract to induce continued effort”', "en"),
    ('The "bébé Fock"', "en"),                          # capitalised, first word
    ('Le "standard model"', "fr"),
])
def test_the_words_around_the_quotation_decide(title, want):
    other = "en" if want == "fr" else "fr"
    assert quotation_language(title, other) == want


@pytest.mark.parametrize("title", [
    'Correction "Sur un théorème de C. Stricker"',       # one word around: no evidence
    'Erratum "Optimal stopping time problem in a general framework"',
    '"Lebesgue measure"',                                 # nothing around at all
    'Addendum to the paper "X" by de Finetti',           # both languages around
])
@pytest.mark.parametrize("detected", ["en", "fr"])
def test_without_evidence_around_it_the_detector_stands(title, detected):
    assert quotation_language(title, detected) == detected


@pytest.mark.parametrize("detected", [None, "de", "it", "es", "no", "tl"])
def test_another_language_is_never_turned_into_english_or_french(detected):
    """"in", "la", "un" are German, Spanish, Italian words too."""
    t = '"Butterfly effect" vs chaos in the energy future markets'
    assert quotation_language(t, detected) == detected


def test_an_english_possessive_is_not_a_french_elision():
    assert quotation_language('Yule’s "nonsense correlation"', "fr") == "fr", \
        "Yule’s is no evidence either way: nothing else around"
    assert quotation_language('l’"inégalité de Doob"', "en") == "fr"


def test_no_quotation_means_nothing_to_arbitrate():
    """No quotation to set aside: the detector's answer stands, whatever
    small words the title has."""
    assert quotation_language("Sur la théorie des jeux de Borel", "en") == "en"
    assert quotation_language("Sur la théorie des jeux de Borel", "fr") == "fr"


def test_a_single_quotation_is_set_aside_too():
    """Since 2026-10-15 a single quotation is one ``requote`` pairs, so
    the words around it arbitrate exactly as around a double one. (This
    test used to pin the opposite: "On the ‘hot hand’ and the crowd" kept
    the detector's "fr".)"""
    assert quotation_language("On the ‘hot hand’ and the crowd", "fr") == "en"
    assert quotation_language("On the 'hot hand' and the crowd", "fr") == "en"
    assert quotation_language("Sur la 'main chaude' et les joueurs", "en") == "fr"


def test_unpairable_marks_leave_the_detector_alone():
    t = 'On "a" and "b" in the plane'
    assert quotation_language(t, "fr") == "fr"


_FRAME_EN = st.lists(st.sampled_from(["the", "and", "of", "to", "with", "Supplement", "Erratum"]),
                     min_size=1, max_size=4).filter(lambda ws: any(w.islower() for w in ws))
_FRAME_FR = st.lists(st.sampled_from(["les", "et", "sur", "pour", "Correction", "Appendice"]),
                     min_size=1, max_size=4).filter(lambda ws: any(w.islower() for w in ws))
_INSIDE = st.lists(st.sampled_from(["the", "and", "les", "et", "sur", "of", "martingale", "l’espace"]),
                   min_size=1, max_size=6)


@given(_FRAME_EN, _INSIDE, st.sampled_from(["en", "fr"]))
def test_words_inside_the_quotation_never_count_en(frame, inside, detected):
    t = f'{" ".join(frame)} "{" ".join(inside)}"'
    assert quotation_language(t, detected) == "en"


@given(_FRAME_FR, _INSIDE, st.sampled_from(["en", "fr"]))
def test_words_inside_the_quotation_never_count_fr(frame, inside, detected):
    t = f'{" ".join(inside)}: "{" ".join(inside)}" {" ".join(frame)}'.replace(
        f'{" ".join(inside)}: ', "", 1)
    assert quotation_language(t, detected) == "fr"


@pytest.mark.parametrize("family,given,title,want", [
    ("Ernst", "P. A.", 'Yule’s "nonsense correlation", moments and density', "‘nonsense correlation’"),
    ("Bouleau", "N.", 'Desargues and the "trait à preuves"', "‘trait à preuves’"),
    ("Meyer", "P.-A.", 'Correction "Sur un théorème de C. Stricker"', "« Sur un théorème de C. Stricker »"),
])
def test_a_new_arrival_is_named_by_the_title_around_the_quotation(family, given, title, want):
    """Through the call that names every new arrival (ingest -> CMO)."""
    from arxivbot.models.cmo import Author, CMO
    cmo = CMO(external_id="t", source="test", title=title,
              authors=[Author(family=family, given=given)])
    name = cmo.get_canonical_filename(max_bytes=251)
    assert want in name, name


def test_the_importer_asks_only_when_a_title_has_a_straight_double_mark(monkeypatch):
    """No extra detector call for the 29k titles with no quotation."""
    import validators.filename_checker.core as core
    calls = []
    real = core.detect
    monkeypatch.setattr(core, "detect", lambda t: calls.append(t) or real(t))
    core.check_filename("Smith, J. - On the heat equation.pdf", auto_fix_nfc=True)
    assert len(calls) == 1, calls
    calls.clear()
    core.check_filename('Smith, J. - On the "heat" equation.pdf', auto_fix_nfc=True)
    assert calls[-1] == 'On the "heat" equation', calls
