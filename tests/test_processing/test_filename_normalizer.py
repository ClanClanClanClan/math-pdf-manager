
import pytest

from processing.filename_normalizer import normalize_filename


class TestSanitisedColon:
    """":" is illegal in a macOS filename, so download tools save
    "Title: Subtitle" as "Title- Subtitle".  The house convention turns a
    subtitle colon into ", ", so the hyphen has to be restored — otherwise
    sentence-casing the subtitle leaves "equations- when", which is
    neither convention.  Measured: 4 files in the real library.
    """

    @pytest.mark.parametrize("raw,expected", [
        ("B, I. - Neutral delay-differential equations- When delay-systems meet zeros.pdf",
         "B, I. - Neutral delay-differential equations, When delay-systems meet zeros.pdf"),
        ("H, Y. - Risk sharing in equity-linked products- Stackelberg equilibrium.pdf",
         "H, Y. - Risk sharing in equity-linked products, Stackelberg equilibrium.pdf"),
    ])
    def test_a_sanitised_colon_becomes_a_comma(self, raw, expected):
        from processing.filename_normalizer import normalize_filename
        assert normalize_filename(raw) == expected

    @pytest.mark.parametrize("name", [
        # The author/title separator has a space on BOTH sides.
        "Dalang, R. C. - Level sets and excursions of the Brownian sheet.pdf",
        # A real hyphenated word has no space at all.
        "Smith, J. - Infinite-Dimensional analysis on Wiener space.pdf",
        # A segment separator is spaced on both sides too.
        "Aïd, R. - An introduction - Lecture 1 - Electricity markets.pdf",
        # A hyphenated initial must survive.
        "Lions, J.-P. - Some analysis.pdf",
    ])
    def test_real_hyphens_are_untouched(self, name):
        from processing.filename_normalizer import normalize_filename
        assert normalize_filename(name) == name


class TestSentenceMarkFollowedByADash:
    """A dash straight after "?" or "!" is redundant — the mark has
    already closed the sentence, so the two are stacked separators.

    Both real cases were checked against the documents: the Lewis paper
    really prints "airplane?—The", the Escobar-Anel one prints
    "Mind the Cap! - Constrained".  They disagree, which is the evidence
    that the construction is noise rather than a convention.
    """

    @pytest.mark.parametrize("name,expected", [
        ("L. - Should we fly in the airplane?—The correct defence.pdf",
         "L. - Should we fly in the airplane? The correct defence.pdf"),
        # …and the next word is re-capitalised, because it starts a
        # sentence now.  The caser only PRESERVES a capital after a
        # sentence mark, it never invents one, so this must happen here.
        ("E. - Mind the cap!—constrained portfolio optimisation.pdf",
         "E. - Mind the cap! Constrained portfolio optimisation.pdf"),
        ("E. - Mind the cap! - Constrained portfolio optimisation.pdf",
         "E. - Mind the cap! Constrained portfolio optimisation.pdf"),
    ])
    def test_the_redundant_dash_is_dropped(self, name, expected):
        assert normalize_filename(name) == expected

    @pytest.mark.parametrize("name", [
        # A period ends abbreviations as well as sentences, and there the
        # dash is a real author-title separator.  Restricting the rule to
        # "?" and "!" is what makes these safe — no abbreviation ends in
        # a question or exclamation mark.
        'Jarrow, R. A. - Review of John E. Gilster, Jr. - "Option pricing".pdf',
        "Helffer, B., Gallot, S., et al. - Première classe de Chern.pdf",
        "Yoeurp, Ch. - Compléments sur les temps locaux.pdf",
    ])
    def test_a_period_is_not_a_question_mark(self, name):
        import unicodedata
        assert normalize_filename(name) == unicodedata.normalize("NFC", name)


class TestSeparatorWithItsSpaceEaten:
    """"Itô, K.- Poisson point processes" — the author-title separator
    lost the space before it.  The other dash rules all require a space
    on one side already, so this fell through every one of them."""

    @pytest.mark.parametrize("name,expected", [
        ("Itô, K.- Poisson point processes.pdf",
         "Itô, K. - Poisson point processes.pdf"),
        ("Barucci, E., Fontana, C.- Financial markets theory.pdf",
         "Barucci, E., Fontana, C. - Financial markets theory.pdf"),
        # A compound initial keeps its own hyphen: that dash has no space
        # after it, so only the trailing one is repaired.
        ("Zou, H.-F.- Power accumulation and growth.pdf",
         "Zou, H.-F. - Power accumulation and growth.pdf"),
    ])
    def test_the_space_is_restored(self, name, expected):
        assert normalize_filename(name) == expected

    @pytest.mark.parametrize("name", [
        "Lehalle, C.-A., Laruelle, S. - Market microstructure in practice.pdf",
        "Zou, H.-F. - Power accumulation and endogenous growth.pdf",
        "Delarue, F. - Mean-field games and master equations.pdf",
    ])
    def test_a_correct_name_is_left_alone(self, name):
        import unicodedata
        assert normalize_filename(name) == unicodedata.normalize("NFC", name)
