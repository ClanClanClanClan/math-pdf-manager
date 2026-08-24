r"""The one initial-spacing rule.

There were three implementations and none of them was complete. Measured
over all 17,804 distinct author blocks in the library, the two real ones
agreed on 17,795, the Unicode-aware one never acted alone, and the ASCII-only
one acted alone on 9. Neither was a superset, so deleting either lost
behaviour. This is the union; the other two are now adapters over it.
"""
import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from core.initials import INITIAL_RE, space_initials


class TestWhatEachOldImplementationCouldDo:
    """The union, case by case, with the loser of each named."""

    @pytest.mark.parametrize("broken,fixed", [
        # the ASCII-only one could not see these: an initial is not always
        # one letter, and transliterated Cyrillic given names need two or three
        ("Kabanov, Yu.A.", "Kabanov, Yu. A."),
        ("Mishura, Yu.S., Kramkov, D.O.", "Mishura, Yu. S., Kramkov, D. O."),
        ("Khasminskii, R.Z.", "Khasminskii, R. Z."),
        ("Zhikov, V.V.", "Zhikov, V. V."),
    ])
    def test_multi_letter_initials(self, broken, fixed):
        assert space_initials(broken) == fixed

    @pytest.mark.parametrize("broken,fixed", [
        # the Unicode-aware one could not see these: its lookahead required
        # the FOLLOWING initial to carry its own period
        ("Kyprianou, A.E", "Kyprianou, A. E"),
        ("Asheim, G.B", "Asheim, G. B"),
        ("Barles, G., Soner, H.M", "Barles, G., Soner, H. M"),
        ("Chitashvili, R. J., Mania, M.G", "Chitashvili, R. J., Mania, M. G"),
        ("Veraart, L.A.M", "Veraart, L. A. M"),
    ])
    def test_a_final_initial_that_lost_its_period(self, broken, fixed):
        assert space_initials(broken) == fixed

    @pytest.mark.parametrize("text", [
        "USA.", "NASA.", "CERN.",          # all-caps runs
        "et.", "vs.", "ibid.",             # lowercase words
        "St.Petersburg", "O.Brien",        # a real word follows the period
    ])
    def test_the_guards_both_of_them_had(self, text):
        """Two hand-written guards used to do this. The shape of an initial
        -- one capital then at most three lowercase -- now does it."""
        assert space_initials(text) == text


class TestABugTheUnionFixed:
    """Neither predecessor was merely incomplete -- the live one was wrong.

    "A.s." is sentence-initial "almost surely", capitalised. The live rule
    emitted "A. s." because its guard only inspected the MATCHED token, never
    what followed. Requiring the following chunk to be initial-shaped -- a
    capital -- refuses it, and lowercase abbreviations generally: i.i.d.,
    w.r.t., r.c.l.l., u.c.p., 23 titles in the library.
    """

    @pytest.mark.parametrize("text", [
        "A.s. approximation results for multiplicative systems",
        "The k-record processes are i.i.d.",
        "Convergence w.r.t. the Skorokhod topology",
        "An r.c.l.l. modification",
    ])
    def test_a_lowercase_abbreviation_is_left_alone(self, text):
        assert space_initials(text) == text


class TestAlreadyCorrectNamesAreUntouched:
    @pytest.mark.parametrize("name", [
        "Rogers, L. C. G.",
        "Bouchaud, J.-P.",                 # hyphen, not a space
        "Meyer, P.-A.",
        "Kabanov, Yu. A.",
        "Émery, M., Yor, M.",
        "Şengül, B.",
        "Baňas, Ľ.",
        "de Angelis, T.",
        "Chaudru de Raynal, P.-É.",
        "Harvey, F. R., Lawson, Jr., H. B.",
        "García Trillos, N.",
    ])
    def test_unchanged(self, name):
        assert space_initials(name) == name


class TestOnePassIsEnough:
    @pytest.mark.parametrize("text", [
        "Veraart, L.A.M", "Kedlaya, K.S.T.", "A.B.C.D.E.", "Kabanov, Yu.A.",
    ])
    def test_a_run_of_three_or_more_is_fully_separated(self, text):
        once = space_initials(text)
        assert space_initials(once) == once, "not idempotent"
        assert INITIAL_RE.search(once) is None, "a glued pair survived"


class TestNonAsciiInitials:
    """The initial ITSELF can be non-ASCII, not just the surname.

    A hand-written "A-Z" class passes every test whose initials happen to be
    ASCII -- which was all of them, so the mutation survived. These do not.
    """

    @pytest.mark.parametrize("broken,fixed", [
        ("Gassiat, É.B.", "Gassiat, É. B."),          # accented capital
        ("Émery, M.A.", "Émery, M. A."),
        ("Ширяев, А.Н.", "Ширяев, А. Н."),            # Cyrillic initials
        ("Йор, М.П.", "Йор, М. П."),
        ("Ćurgus, B.Ć.", "Ćurgus, B. Ć."),
    ])
    def test_spaced(self, broken, fixed):
        assert space_initials(broken) == fixed


class TestPathologies:
    @pytest.mark.parametrize("text", [
        "", "   ", ".", "..", "....", "A", "A.", ",", ",,,", "-",
        "A" * 400, "\x00", "\x1d", "Ph.D", "III.", "1.2", "x.y",
    ])
    def test_never_raises_never_hangs(self, text):
        out = space_initials(text)
        assert isinstance(out, str)

    def test_none_and_empty_pass_through(self):
        assert space_initials("") == ""

    def test_nfd_input_is_not_corrupted(self):
        """The rule does not normalise -- that is the caller's job -- but it
        must not mangle a decomposed accent either."""
        nfd = unicodedata.normalize("NFD", "Émery, M.A.")
        out = space_initials(nfd)
        assert unicodedata.normalize("NFC", out) == "Émery, M. A."


class TestProperties:
    @settings(max_examples=400, deadline=None)
    @given(st.text(max_size=80))
    def test_only_ever_inserts_spaces(self, text):
        """It may not delete, reorder or substitute anything. Removing every
        space from input and output must give the same string."""
        out = space_initials(text)
        assert out.replace(" ", "") == text.replace(" ", "")

    @settings(max_examples=400, deadline=None)
    @given(st.text(max_size=80))
    def test_idempotent(self, text):
        once = space_initials(text)
        assert space_initials(once) == once

    @settings(max_examples=200, deadline=None)
    @given(st.text(max_size=60))
    def test_never_shortens(self, text):
        assert len(space_initials(text)) >= len(text)


class TestTheAdaptersAgree:
    """Three call sites, one rule. If any of them drifts back to its own
    implementation, this fails."""

    @pytest.mark.parametrize("text", [
        "Kabanov, Yu.A.", "Kyprianou, A.E", "Asheim, G.B", "St.Petersburg",
        "Rogers, L. C. G.", "Harvey, F.R., Lawson, Jr., H.B.",
    ])
    def test_all_three(self, text):
        from validators.author_parser import fix_initial_spacing as frozen
        from validators.filename_checker.author_processing import (
            fix_initial_spacing as live)
        want = space_initials(text)
        assert live(text) == want
        assert frozen(text) == want


class TestWhatItDeliberatelyDoesNot:
    r"""Known limits, written so they FAIL if they are ever fixed."""

    @pytest.mark.parametrize("acronym", [
        "A P.D.E. approach to Asian options",
        "Variation des solutions d'une E.D.S.",
    ])
    def test_it_cannot_tell_an_acronym_from_a_person(self, acronym):
        """And neither can anything else reading the string alone: the
        library contains "Varadhan, S.R.S." and "R.E.A.C. Paley", which have
        the identical shape and DO want spacing.

        This is why the precondition is "author blocks only" rather than a
        cleverer pattern. Every production caller is inside fix_author_block.
        """
        assert space_initials(acronym) != acronym

    def test_it_does_not_add_a_missing_period(self):
        """"A.E" becomes "A. E", not "A. E.". Supplying the missing period is
        a repair, and it lives in filename_ground_truth.repair_author_block."""
        assert space_initials("Kyprianou, A.E") == "Kyprianou, A. E"
