"""Which titles the caser reads as German -- and therefore leaves alone.

German capitalises every noun, so the caser lowers nothing in a title it
reads as German. That guard has two failure modes and they cost different
things:

  * a German title NOT recognised has a noun lowered -- "vorkommendes
    Problem" becomes "vorkommendes problem", a real error in the filename;
  * a title WRONGLY recognised is never sentence-cased. Quiet, and safe,
    but it was the common case: "des" was a German marker, and it is just
    as much French. Measured 2026-10-15 over the 25,196 in-scope titles,
    619 read as German; "des" was the only marker in 581 of them, every
    one French ("Théorie des ensembles"), and none of the 34 German titles
    needed it -- each also carries über, für, und, zur, eine or similar.

So "des" is no longer a German marker, and these tests pin both sides:
French with "des" is cased, German with "des" is still left alone.
"""
from __future__ import annotations

import json
import tempfile
import unicodedata
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from processing.title_normalize import _is_probably_german, propose_title_case

# Every German marker, written out rather than read from the module: a
# marker silently dropped from the set must fail here, not pass by
# iterating whatever the set now holds.
GERMAN_MARKERS = (
    "und", "über", "für", "auf", "eine", "einer", "einem", "einen",
    "dem", "den", "zur", "zum", "mit", "durch", "nicht", "ist",
    "sind", "werden", "wird", "vom", "beim", "im", "aus", "nach",
    "theorie", "anwendung", "beitrag", "untersuchungen", "bemerkungen",
    "grundlagen", "einführung", "wahrscheinlichkeitsrechnung",
)

# Real library titles (in scope, 2026-10-15) that "des" alone made German.
FRENCH_WITH_DES = (
    "Théorie des ensembles",
    "Caractérisation des semimartingales",
    "Des valeurs moyennes",
    "Une propriété des temps prévisibles",
    "Sur la convergence des martingales indexées par NxN",
    "Dloussky, G. - Structure des surfaces de Kato",
    "Analyse des systèmes (Bordeaux, 11–16 septembre 1978)",
    "Questions de théorie des flots (VII)",
)

# Every real German library title that contains "des" -- each must still
# read as German without it.
GERMAN_WITH_DES = (
    "Über das Gesetz des iterierten Logarithmus",
    "Eine neue Herleitung des Exponentialgesetzes in der "
    "Wahrscheinlichkeitsrechnung",
    "Zur Theorie des Doppel-Integrals",
    "Zur Theorie des Doppel-Integrals, des Green’schen und Cauchy’schen "
    "Integralsatzes",
)


def _library(common) -> Path:
    """A throwaway library whose vocabulary rules ``common`` ordinary.

    The caser lowers only what it can PROVE common; a bare tmp library
    proves only the built-in English list, so without these rulings a
    French test would just watch the safe default keep every capital.
    """
    root = Path(tempfile.mkdtemp(prefix="german-des-lib-"))
    cfg = root / ".mathpdf-config"
    cfg.mkdir(parents=True)
    (cfg / "title_vocab.json").write_text(json.dumps({
        "proper": [], "common": sorted(common), "pending": {},
    }))
    return root


FRENCH_COMMON = ("des", "les", "et", "sur", "processus", "temps", "lois")
_LIB = _library(FRENCH_COMMON)


class TestDesIsNotGerman:
    @pytest.mark.parametrize("title", FRENCH_WITH_DES)
    def test_a_french_title_with_des_does_not_read_as_german(self, title):
        assert _is_probably_german(title) is False

    @pytest.mark.parametrize("title", ["des", "Des", "DES", "Des des DES"])
    def test_des_on_its_own_is_not_german(self, title):
        assert _is_probably_german(title) is False

    def test_the_cipher_is_not_german_either(self):
        # "DES" lower-cases to the marker; it used to freeze every title
        # about the Data Encryption Standard.
        title = "Attacks on DES and Applications"
        assert _is_probably_german(title) is False
        assert propose_title_case(title).proposed == "Attacks on DES and applications"

    def test_a_title_cased_french_arrival_is_sentence_cased(self):
        # What the fix is for: a publisher's Title Case. Before it, every
        # capital here was kept because of the "Des".
        p = propose_title_case("Sur Les Martingales Des Processus", _LIB)
        assert p.proposed == "Sur les martingales des processus"
        assert p.changed

    def test_built_in_vocabulary_alone_is_enough_for_english_words(self):
        # No library at all: "applications"/"solutions" are built-in common.
        p = propose_title_case("Sur les Applications des Solutions")
        assert p.proposed == "Sur les applications des solutions"


class TestGermanIsStillLeftAlone:
    @pytest.mark.parametrize("title", GERMAN_WITH_DES)
    def test_every_german_library_title_with_des_still_reads_as_german(self, title):
        assert _is_probably_german(title) is True
        assert propose_title_case(title, _LIB).proposed == title

    @pytest.mark.parametrize("marker", GERMAN_MARKERS)
    def test_each_marker_alone_protects_a_lowerable_noun(self, marker):
        # "Problem" and "Martingale" are words the caser CAN prove common
        # (built-in list), so without the guard they would be lowered.
        title = f"Martingale {marker} Problem"
        assert _is_probably_german(title) is True
        assert propose_title_case(title, _LIB).proposed == title

    @pytest.mark.parametrize("marker", GERMAN_MARKERS)
    def test_a_marker_opening_the_title_counts(self, marker):
        # Title-initial German is capitalised: "Über …", "Zur …".
        title = f"{marker.capitalize()} Martingale Problem"
        assert _is_probably_german(title) is True
        assert propose_title_case(title, _LIB).proposed == title

    def test_a_marker_next_to_punctuation_counts(self):
        assert _is_probably_german("Martingale (und) Problem") is True
        assert _is_probably_german("Problem, über Martingale") is True

    def test_sharp_s_alone_is_german(self):
        title = "Die Größe als Problem"
        assert _is_probably_german(title) is True
        assert propose_title_case(title, _LIB).proposed == title

    def test_a_decomposed_title_is_recognised(self):
        # macOS hands filenames back NFD; "Über" then arrives as U + a
        # combining mark, which no word pattern sees as one letter. The
        # caser must compose first or it lowers the noun.
        nfc = "Über Martingale Problem"
        nfd = unicodedata.normalize("NFD", nfc)
        assert nfd != nfc
        assert propose_title_case(nfd, _LIB).proposed == nfc

    def test_a_german_title_whose_only_sign_was_des_keeps_its_nouns(self):
        # The measured cost of the fix: "Das Gesetz des iterierten
        # Logarithmus" no longer reads as German. Its nouns are not words
        # the caser can prove common, so it still changes nothing -- but a
        # title like this with a built-in English noun would lose it.
        title = "Das Gesetz des iterierten Logarithmus"
        assert _is_probably_german(title) is False
        assert propose_title_case(title, _LIB).proposed == title


# --- properties ------------------------------------------------------------

_WORDS = st.sampled_from(
    ("sur", "la", "théorie", "martingales", "processus", "Problem", "of",
     "the", "équations", "Lévy", "Gauss", "le", "et", "de", "Markov")
    + GERMAN_MARKERS)
_TITLES = st.lists(_WORDS, min_size=0, max_size=8)
_DES = st.sampled_from(("des", "Des", "DES"))


@settings(max_examples=300, deadline=None)
@given(_TITLES, _DES, st.integers(min_value=0, max_value=8))
@example(["théorie", "martingales"], "des", 1)
def test_adding_des_never_changes_the_verdict(words, des, at):
    at = min(at, len(words))
    with_des = words[:at] + [des] + words[at:]
    assert _is_probably_german(" ".join(with_des)) == \
        _is_probably_german(" ".join(words))


@settings(max_examples=300, deadline=None)
@given(_TITLES, st.sampled_from(GERMAN_MARKERS), st.integers(min_value=0, max_value=8))
def test_adding_a_marker_always_makes_it_german(words, marker, at):
    at = min(at, len(words))
    assert _is_probably_german(" ".join(words[:at] + [marker] + words[at:]))


@settings(max_examples=300, deadline=None)
@given(_TITLES)
def test_the_verdict_does_not_depend_on_letter_case(words):
    # Arrivals come in Title Case, ALL CAPS or lower case; the shelf
    # holds the same title in sentence case. One title, one verdict.
    title = " ".join(words)
    assert _is_probably_german(title) == _is_probably_german(title.lower()) \
        == _is_probably_german(title.title()) == _is_probably_german(title.upper())


# Words the caser can prove common in _LIB, and that no other rule protects
# (no particle, month, place, whitelist entry or German marker).
_COMMON = st.sampled_from(
    ("des", "les", "et", "sur", "processus", "temps", "lois",
     "martingales", "solutions", "applications", "equations", "theory"))


@settings(max_examples=200, deadline=None)
@given(st.lists(_COMMON, min_size=2, max_size=7))
@example(["sur", "des", "martingales"])
def test_a_title_cased_title_of_common_words_is_sentence_cased(words):
    # The regression in one line: with "des" a German marker, any such
    # title containing it came back with every capital kept.
    arrived = " ".join(w.capitalize() for w in words)
    expected = words[0].capitalize() + "".join(" " + w for w in words[1:])
    assert propose_title_case(arrived, _LIB).proposed == expected


@settings(max_examples=200, deadline=None)
@given(st.lists(_COMMON, min_size=1, max_size=6), st.sampled_from(GERMAN_MARKERS))
def test_one_german_marker_freezes_the_whole_title(words, marker):
    # The other side: the same words with one German marker are left
    # exactly as they arrived, "des" or not.
    arrived = " ".join(w.capitalize() for w in [*words, marker, "Problem"])
    assert propose_title_case(arrived, _LIB).proposed == arrived


def test_the_word_pattern_sees_des_inside_no_other_word():
    # "Descartes", "designs": a marker is a whole word, never a fragment.
    for title in ("Descartes und Martingale", "Designs, über alles"):
        assert _is_probably_german(title) is True
    for title in ("Descartes et les martingales", "Designs for des tests"):
        assert _is_probably_german(title) is False
