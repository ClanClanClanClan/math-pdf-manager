"""Apostrophe-like marks must not hide a paper from its own author.

No Unicode normalisation form equates these characters. NFC, NFD, NFKC,
NFKD and casefold all leave U+0027 and U+2019 distinct -- which is
CATEGORICALLY UNLIKE the NFD/NFC accent trap this library already knows
about, where normalising genuinely repairs the match. So a corpus that
holds both spellings has an author findable by only half his own files;
measured, "d'Amato" and "d’Amato" are one person, Egidio D'Amato, and two
different strings.

The fold is on the MATCH side only. Nothing on disk is renamed by it, and
it deliberately folds marks that are NOT apostrophes (the Cyrillic
soft-sign prime, the Breton modifier letter) because the point is to make
them match, not to claim they mean the same thing.
"""
import unicodedata

import pytest

from processing.apostrophes import APOSTROPHE_LIKE, fold_marks
from processing.preprint_variants import _fold as dedup_fold
from ui.search_page import _fold as search_fold

PAIRS = [
    ("d'Amato", "d’Amato"),                # Italian elision, real split in this library
    ("O'Connell", "O’Connell"),            # anglicised Irish, real split
    ("Kolokol'tsov", "Kolokolʹtsov"),      # Cyrillic soft sign, U+02B9
    ("le Floc'h", "le Flocʼh"),            # Breton c'h trigraph, U+02BC
    ("in 't Hout", "in ’t Hout"),          # Dutch elision
    ("N'zi", "N’zi"),                      # French-transcribed African
]


def test_the_premise_no_normalisation_form_equates_them():
    """If this ever fails, the fold is redundant and should be deleted.

    It is the whole reason this module exists rather than leaning on the
    NFC pass that already handles accents.
    """
    a, b = "d'Amato", "d’Amato"
    for form in ("NFC", "NFD", "NFKC", "NFKD"):
        assert unicodedata.normalize(form, a) != unicodedata.normalize(form, b), form
    assert a.casefold() != b.casefold()


@pytest.mark.parametrize("a,b", PAIRS)
def test_search_matches_across_the_mark(a, b):
    assert search_fold(a) == search_fold(b)


@pytest.mark.parametrize("a,b", PAIRS)
def test_the_duplicate_detector_matches_across_the_mark(a, b):
    assert dedup_fold(a) == dedup_fold(b)


def test_the_two_folds_agree():
    """One rule, one implementation — they are the same question."""
    for a, b in PAIRS:
        assert search_fold(a) == dedup_fold(a), a
        assert search_fold(b) == dedup_fold(b), b


def test_accents_are_still_folded():
    """The apostrophe fold must not displace the accent fold."""
    assert search_fold("Möbius") == search_fold("mobius")
    assert search_fold("Itô") == search_fold("ito")


def test_a_string_with_no_mark_is_returned_unchanged():
    s = "Bertoin, J. - Levy processes"
    assert fold_marks(s) is s or fold_marks(s) == s


@pytest.mark.parametrize("mark", sorted(APOSTROPHE_LIKE))
def test_every_listed_mark_folds_to_one_character(mark):
    assert fold_marks(f"a{mark}b") == "a'b", f"{mark!r} U+{ord(mark):04X}"


def test_the_fold_does_not_touch_anything_else():
    """It must not become a general punctuation stripper."""
    for s in ("Hamilton–Jacobi", "mean-field", "L^2(Ω)", "f(x), g(y)",
              "Itô's formula".replace("'", "X")):
        assert fold_marks(s) == s, s


def test_folding_is_idempotent():
    for a, b in PAIRS:
        assert fold_marks(fold_marks(a)) == fold_marks(a)
        assert fold_marks(b) == fold_marks(fold_marks(b))


def test_the_fold_is_never_used_to_build_a_name_on_disk():
    """A guard on the SHAPE of the code, not on its behaviour.

    fold_marks destroys the punctuation/letter distinction the filename
    convention exists to preserve. It belongs in match keys only, and the
    cheapest way to keep it there is to assert that no naming path
    imports it.
    """
    import pathlib
    naming = [
        "src/processing/move_normalizer.py",
        "src/processing/filename_normalizer.py",
        "src/processing/author_surnames.py",
        "src/processing/library_normalize.py",
        "src/core/sentence_case.py",
    ]
    for f in naming:
        src = pathlib.Path(f).read_text()
        assert "fold_marks" not in src, (
            f"{f} imports the match-only apostrophe fold; a name written "
            f"through it would lose the punctuation/letter distinction")
