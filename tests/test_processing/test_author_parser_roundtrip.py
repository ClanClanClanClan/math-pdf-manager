"""The author block, parsed and rendered back.

The library is the oracle: "Bertucci, C., Lasry, J.-M., Lions, P.-L." is
a correct author block by construction, so parsing it and re-rendering
it must return the same string.

Measured over all 26,590 author blocks in the library on 2026-08-24:
94.4% round-trip exactly. Of the 819 distinct blocks that do not, 803
are not author lists at all — they are series names sitting in the
author slot, because a filename like
"Astérisque 390 - Baues, O. - Symplectic Lie groups.pdf" puts the series
before the first " - ". Genuine author defects numbered about five.

The corpus below is a frozen sample of REAL blocks, so this test can be
run offline and will fail if the parser regresses. The full sweep lives
in the same directory as a marked slow test.
"""
from __future__ import annotations

import pytest

from processing.ingest import parse_authors_string


def render(authors) -> str:
    return ", ".join(a.display_name() if a.given else a.family
                     for a in authors)


#: Real blocks from the library, chosen to cover every shape it contains.
CORPUS = [
    "Bertucci, C., Lasry, J.-M., Lions, P.-L.",
    "Kabanov, Yu. A.",
    "el Karoui, N., Peng, S., Quenez, M.-C.",
    "Duquesne, T., Reichmann, O., Sato, K.-I., Schwab, C.",
    "Delmas, J.-F., Dronnier, D., Zitt, P.-A.",
    "Yor, M.",
    "Föllmer, H., Schied, A.",
    "Jacka, S. D., Hernández-Hernández, M. E.",
    "Guarracino, M. R., Vivien, F., Träff, J. L.",
    "Başar, T., Olsder, G. J.",
    "van der Vaart, A. W.",
    "de Angelis, T., Bovo, A.",
    "Cvitanić, J., Possamaï, D., Touzi, N.",
    "Obłój, J., Øksendal, B.",
]


class TestEveryShapeInTheLibraryRoundTrips:

    @pytest.mark.parametrize("block", CORPUS)
    def test_parse_then_render_is_the_identity(self, block):
        assert render(parse_authors_string(block)) == block


class TestTheOxfordAndList:
    """The bug this file was written for.

    "A, B, C, and D" is the standard English list. The strong-separator
    split cut on " and ", leaving a first segment ending in a comma —
    and _looks_like_filename_format requires an EVEN number of
    comma-separated parts, so the trailing empty part made it nine
    instead of eight, the heuristic bailed, and the entire list
    collapsed into ONE author whose surname was
    "Gray, A., Greenhalgh, D., Hu, L., Mao, X.,".

    The filename that produced was
    "Gray, A. G. D. H. L. M. X., Pan, J. - ….pdf".
    """

    @pytest.mark.parametrize("block,expected", [
        ("Gray, A., Greenhalgh, D., Hu, L., Mao, X., and Pan, J.",
         ["Gray", "Greenhalgh", "Hu", "Mao", "Pan"]),
        ("el Karoui, N., Peng, S., and Quenez, M.-C.",
         ["el Karoui", "Peng", "Quenez"]),
        ("Duquesne, T., Reichmann, O., Sato, K.-I., and Schwab, C.",
         ["Duquesne", "Reichmann", "Sato", "Schwab"]),
        ("Smith, J. and Jones, K.", ["Smith", "Jones"]),
        ("Smith, J., and Jones, K.", ["Smith", "Jones"]),
    ])
    def test_the_terminal_and_does_not_swallow_the_list(self, block,
                                                        expected):
        assert [a.family for a in parse_authors_string(block)] == expected

    def test_a_trailing_separator_anywhere_is_tolerated(self):
        """The mechanism, isolated: it was a stray comma, not the word
        "and", that broke the heuristic."""
        assert len(parse_authors_string("Smith, J., Jones, K.,")) == 2
        assert len(parse_authors_string("Smith, J., Jones, K.;")) == 2

    def test_a_nobiliary_particle_survives_the_and(self):
        got = parse_authors_string("de Angelis, T., and Bovo, A.")
        assert [a.family for a in got] == ["de Angelis", "Bovo"]

    def test_a_multi_letter_initial_survives_the_and(self):
        """"Kabanov, Yu. A." is correct — Cyrillic transliterations need
        two-letter initials, and an earlier bug truncated them."""
        got = parse_authors_string("Kabanov, Yu. A., and Safarian, M.")
        assert [a.family for a in got] == ["Kabanov", "Safarian"]
        assert got[0].given == "Yu. A."


class TestWhatItStillDoesNotDo:
    """Recorded rather than fixed, so the limits are known.

    Each was measured on the real library and is rare: two blocks with a
    period where a comma belongs, two corporate authors, one two-word
    surname. Fixing them risks the 94.4% that works.
    """

    def test_a_period_instead_of_a_comma_reverses_the_name(self):
        got = parse_authors_string("Dzhaparidze. K.")
        assert [a.family for a in got] != ["Dzhaparidze"], (
            "this now works — move it out of the known-limits class")

    def test_a_single_two_word_surname_is_handled(self):
        """This one DOES work — recorded so the limitation below is not
        mistaken for a broader one."""
        got = parse_authors_string("García Trillos, N.")
        assert [a.family for a in got] == ["García Trillos"]

    def test_but_two_of_them_in_a_row_are_not(self):
        """The pair defeats the filename-format heuristic, which counts
        comma-separated parts and expects them to alternate
        surname/initials. One real block in the library."""
        got = parse_authors_string("García Trillos, C.A, García Trillos, N.")
        assert [a.family for a in got] != ["García Trillos", "García Trillos"], (
            "this now works — move it out of the known-limits class")

    def test_et_al_is_dropped_on_purpose(self):
        got = parse_authors_string("Neufeld, A., et al.")
        assert [a.family for a in got] == ["Neufeld"]
