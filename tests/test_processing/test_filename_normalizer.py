
import pytest

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
