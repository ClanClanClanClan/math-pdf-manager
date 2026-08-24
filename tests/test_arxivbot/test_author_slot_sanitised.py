"""The author block must be as filesystem-safe as the title is.

Found by measurement, not by reading: scoring the extraction pipeline on a
1,753-paper stratified sample of the real library (each file reached through
an opaque symlink so the filename could not leak the answer) produced 11
proposed names containing a raw U+0010.  They came from one family of
scanned Russian PDFs whose embedded /Author is mojibake for
"Администратор".  ``_clean_for_fs`` was applied to the title and never to
the author segments.
"""
import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from arxivbot.models.cmo import CMO, Author


def _name(authors, title="A test title"):
    return CMO(external_id="x", source="test", title=title,
               authors=authors).get_canonical_filename()


CONTROL = [chr(c) for c in range(0x20)]


class TestControlCharacters:
    @pytest.mark.parametrize("ch", CONTROL, ids=[f"U+{ord(c):04X}" for c in CONTROL])
    def test_no_control_character_survives_in_a_surname(self, ch):
        out = _name([Author(family=f"Ab{ch}cd", given="John")])
        assert not any(unicodedata.category(c) == "Cc" for c in out), repr(out)
        assert "Abcd, J." in out

    @pytest.mark.parametrize("ch", CONTROL, ids=[f"U+{ord(c):04X}" for c in CONTROL])
    def test_no_control_character_survives_in_a_given_name(self, ch):
        out = _name([Author(family="Abcd", given=f"J{ch}ohn")])
        assert not any(unicodedata.category(c) == "Cc" for c in out), repr(out)

    def test_the_real_mojibake_string_from_the_library(self):
        """The actual /Author value that produced the 11 bad names."""
        out = _name([Author(family="\x104<8=8AB@0B>@", given=None)])
        assert not any(unicodedata.category(c) == "Cc" for c in out), repr(out)
        # The garbage is not silently deleted either -- only the control
        # character is stripped, so the rest stays visible for a human or
        # the conformance check to notice.
        assert "4<8=8AB@0B>@" in out


INVISIBLE = [("\u200b", "zero-width space"), ("\u00ad", "soft hyphen"),
             ("\ufeff", "byte-order mark"), ("\u200d", "zero-width joiner"),
             ("\u200e", "left-to-right mark"), ("\u2060", "word joiner")]


class TestInvisibleFormatCharacters:
    """Category Cf, the same argument as the control characters above.

    A property test found this with U+200B, months after the Cc fix: the
    sanitiser stripped Cc and stopped. Of these only the SOFT HYPHEN was
    actually reaching filenames -- the rest are caught downstream -- and no
    library filename carries one today, so this closes a hole rather than
    repairing damage.
    """

    @pytest.mark.parametrize("ch,name", INVISIBLE, ids=[n for _, n in INVISIBLE])
    def test_stripped_from_a_surname(self, ch, name):
        out = _name([Author(family=f"Ab{ch}cd", given="John")])
        assert not any(unicodedata.category(c) == "Cf" for c in out), repr(out)
        assert "Abcd, J." in out

    @pytest.mark.parametrize("ch,name", INVISIBLE, ids=[n for _, n in INVISIBLE])
    def test_stripped_from_a_title(self, ch, name):
        out = _name([Author(family="Smith", given="John")],
                    title=f"A te{ch}st title")
        assert not any(unicodedata.category(c) == "Cf" for c in out), repr(out)

    def test_a_surname_that_is_only_invisible_characters_drops_the_author(self):
        out = _name([Author(family="\u200b\u00ad", given="John")])
        assert out == "A test title.pdf", repr(out)


class TestTheOneCharacterMacosForbids:
    def test_slash_in_a_surname_becomes_a_hyphen(self):
        assert _name([Author(family="Sm/ith", given="John")]).startswith("Sm-ith, J.")

    def test_slash_in_a_given_name_becomes_a_hyphen(self):
        assert "/" not in _name([Author(family="Smith", given="Jo/hn")])

    def test_a_surname_that_is_only_slashes_does_not_leave_a_bare_comma(self):
        out = _name([Author(family="//", given="John")])
        assert not out.startswith(","), repr(out)


class TestTheAuthorBlockDoesNotCollapse:
    def test_an_author_erased_by_cleaning_is_dropped_not_blanked(self):
        out = _name([Author(family="\x10\x07", given="John")])
        assert out == "A test title.pdf", repr(out)

    def test_a_junk_author_does_not_take_a_real_one_with_it(self):
        out = _name([Author(family="\x10", given=None),
                     Author(family="Real", given="Ann")])
        assert out == "Real, A. - A test title.pdf", repr(out)

    def test_no_leading_separator_when_every_author_is_junk(self):
        out = _name([Author(family="\x00", given=None), Author(family="\x01", given=None)])
        assert not out.startswith(" - "), repr(out)
        assert not out.startswith("-"), repr(out)


class TestOrdinaryNamesAreUntouched:
    """The fix must not become a name-mangler.  These are real shapes from
    the library: nobiliary particles, multi-letter Cyrillic transliterated
    initials, hyphenated initials, accented and CJK surnames."""

    @pytest.mark.parametrize("family,given,expect", [
        ("Delarue", "François", "Delarue, F."),
        ("de Angelis", "Tiziano", "de Angelis, T."),
        ("Kabanov", "Yuri Aleksandrovich", "Kabanov, Y. A."),
        ("Bouchaud", "Jean-Pierre", "Bouchaud, J.-P."),
        ("Röckner", "Michael", "Röckner, M."),
        ("García Trillos", "Nicolás", "García Trillos, N."),
        ("Émery", "Michel", "Émery, M."),
        ("Ninomiya", "Syoiti", "Ninomiya, S."),
    ])
    def test_unchanged(self, family, given, expect):
        assert _name([Author(family=family, given=given)]).startswith(expect + " - ")

    def test_a_backslash_in_a_surname_is_left_alone(self):
        """Backslash is legal on this filesystem; rewriting it did real
        damage once already (910183f).  The author path must not
        reintroduce that."""
        assert "\\" in _name([Author(family="O\\Brien", given="Ann")])


class TestProperties:
    @settings(max_examples=300, deadline=None)
    @given(st.text(min_size=1, max_size=40), st.text(max_size=20))
    def test_output_never_contains_an_invisible_character_or_a_slash(self, family, given):
        out = _name([Author(family=family, given=given or None)])
        assert not any(unicodedata.category(c) in ("Cc", "Cf") for c in out)
        assert "/" not in out.removesuffix(".pdf")

    @settings(max_examples=150, deadline=None)
    @given(st.text(alphabet=st.characters(blacklist_categories=("Cc", "Cs"),
                                          blacklist_characters=",/"),
                   min_size=1, max_size=30).filter(lambda s: s.strip()))
    def test_cleaning_is_idempotent(self, family):
        """Commas and slashes are excluded from the generator, not because
        the code mishandles them but because this test recovers the surname
        by splitting on the comma -- with one in the name the round trip
        measures the test's own parsing, not the sanitiser."""
        once = _name([Author(family=family, given="A")])
        if "," not in once:
            # Cleaning erased the surname entirely, so the name is
            # title-only and there is no surname to feed back. That is
            # correct behaviour, not a fixpoint violation -- and hypothesis
            # found it with a zero-width space, which is exactly the class
            # of character the sanitiser was extended to strip.
            return
        surname = once.split(",")[0]
        twice = _name([Author(family=surname, given="A")])
        assert once == twice
