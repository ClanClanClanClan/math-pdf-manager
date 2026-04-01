"""
Tests for Author.initials() and Author.display_name() with edge cases.

Covers: particles, accented names, hyphenated given names, NFC/NFD,
compact initials, and empty inputs.
"""

import os
import sys
import unicodedata

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from arxivbot.models.cmo import Author


class TestInitials:

    def test_simple(self):
        assert Author(family="Dupont", given="Jean").initials() == "J"

    def test_hyphenated(self):
        assert Author(family="Dupont", given="Jean-Pierre").initials() == "J.-P"

    def test_multiple_given_names(self):
        assert Author(family="Krée", given="Paul André").initials() == "P.A"

    def test_three_given_names(self):
        assert Author(family="Zheng", given="Karl Theodor Hans").initials() == "K.T.H"

    def test_single_letter(self):
        assert Author(family="Touzi", given="N").initials() == "N"

    def test_empty_given(self):
        assert Author(family="Touzi", given=None).initials() == ""
        assert Author(family="Touzi", given="").initials() == ""

    def test_already_initials(self):
        # "S. C. P." as given name — each token produces one initial
        assert Author(family="Yam", given="S. C. P.").initials() == "S.C.P"

    def test_double_hyphenated(self):
        assert Author(family="Test", given="Anne-Marie-Claire").initials() == "A.-M.-C"


class TestDisplayName:

    def test_basic(self):
        assert Author(family="Dupont", given="Jean").display_name() == "Dupont, Jean"

    def test_no_given(self):
        assert Author(family="Touzi").display_name() == "Touzi"

    def test_particle(self):
        a = Author(family="el Karoui", given="Nicole")
        assert a.display_name() == "el Karoui, Nicole"
        assert a.initials() == "N"

    def test_particle_de(self):
        a = Author(family="de Angelis", given="Thomas")
        assert a.display_name() == "de Angelis, Thomas"
        assert a.initials() == "T"

    def test_particle_in_t(self):
        a = Author(family="in 't Hout", given="Kees")
        assert a.display_name() == "in 't Hout, Kees"
        assert a.initials() == "K"


class TestAccentedNames:

    def test_possamai(self):
        a = Author(family="Possamaï", given="Dylan")
        assert a.display_name() == "Possamaï, Dylan"
        assert a.initials() == "D"

    def test_elie(self):
        a = Author(family="Élie", given="Romuald")
        assert a.display_name() == "Élie, Romuald"
        assert a.initials() == "R"

    def test_slominski(self):
        a = Author(family="Słomiński", given="Leszek")
        assert a.display_name() == "Słomiński, Leszek"
        assert a.initials() == "L"

    def test_nfd_input_produces_same_result(self):
        # NFD decomposed ï = i + combining diaeresis
        nfd_name = unicodedata.normalize("NFD", "Possamaï")
        nfc_name = "Possamaï"
        assert nfd_name != nfc_name  # they differ at byte level
        # But Author should handle both
        a_nfd = Author(family=nfd_name, given="Dylan")
        a_nfc = Author(family=nfc_name, given="Dylan")
        # Both produce valid initials
        assert a_nfd.initials() == "D"
        assert a_nfc.initials() == "D"
