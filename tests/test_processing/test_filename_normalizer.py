
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


class TestStrayCommaOpeningTheTitle:
    """"Reygner, J. - , Propagation of chaos" — the space-before-comma
    rule ate the separator's own space and produced "J. -, Propagation".

    That is the worst possible failure for this codebase: destroying the
    " - " boundary hides the file from every rule that splits on it,
    which is exactly how "Shiryaev, A.N.-" sat out a 6,180-file author
    sweep.  A cosmetic rule must never be able to cause that.
    """

    def test_the_separator_survives_and_the_comma_goes(self):
        assert normalize_filename(
            "Jourdain, B., Reygner, J. - , Propagation of chaos.pdf"
        ) == "Jourdain, B., Reygner, J. - Propagation of chaos.pdf"

    def test_a_real_space_before_comma_is_still_fixed(self):
        assert normalize_filename(
            "Possamaï , D. - A note on BSDEs.pdf"
        ) == "Possamaï, D. - A note on BSDEs.pdf"

    @pytest.mark.parametrize("name", [
        "Bouchard, B., Touzi, N. - Weak dynamic programming, a survey.pdf",
        "Karatzas, I. - Lectures on finance - Volume II.pdf",
        "El Karoui, N., Peng, S., Quenez, M. C. - BSDEs in finance.pdf",
    ])
    def test_ordinary_names_are_untouched(self, name):
        import unicodedata
        assert normalize_filename(name) == unicodedata.normalize("NFC", name)


class TestMathematicsIsNotProse:
    """The author block and the title are different languages: one is
    names, the other is prose AND MATHEMATICS.  Applying a name rule to a
    formula is a category error.

    The missing-space-after-comma rule was applied to the whole filename
    and rewrote the notation of 86 real papers — "C^{0,1}" became
    "C^{0, 1}" — in a batch labelled "cosmetic, no letters changed".  No
    letters had changed; the notation had.
    """

    @pytest.mark.parametrize("name", [
        "Fießinger, F. - The C^{0,1} Itô–Ventzell formula.pdf",
        "Winter, N. - W^{2,p} and W^{1,p}-estimates at the boundary.pdf",
        "Nie, A. - A continuous time GARCH(p,q) process with delay.pdf",
        "Harris, P. E. - Probabilistic (m,n)–parking functions.pdf",
        "Zagier, D. - Evaluation of the multiple ζ values ζ(2,...,2,3,2).pdf",
        "Smith, J. - Coefficients in (y,z) and the map f(x,y).pdf",
        "Smith, J. - A bound of 10,000 samples in dimension 3.pdf",
        "Smith, J. - The 1,000,000 dollar problem.pdf",
        "Drapeau, S. - Li–Yau estimate on RCD^∗(K,N) spaces.pdf",
    ])
    def test_a_title_formula_is_never_respaced(self, name):
        import unicodedata
        assert normalize_filename(name) == unicodedata.normalize("NFC", name)

    @pytest.mark.parametrize("name,expected", [
        ("Possamaï,D. - A note on BSDEs.pdf",
         "Possamaï, D. - A note on BSDEs.pdf"),
        ("Possamaï,D.,Touzi,N. - Second order BSDEs.pdf",
         "Possamaï, D., Touzi, N. - Second order BSDEs.pdf"),
        # The separator must be repaired FIRST, or there is no author block
        # to scope the rule to.
        ("Itô,K.- Poisson point processes.pdf",
         "Itô, K. - Poisson point processes.pdf"),
    ])
    def test_the_author_block_still_gets_its_spaces(self, name, expected):
        assert normalize_filename(name) == expected


class TestDoubleDashIsAmbiguous:
    """"--" is a range between digits and a subtitle break when spaced.
    Blanket-replacing it with an en dash got both wrong: an en dash joins
    two co-equal entities, which a title and its subtitle are not."""

    def test_spaced_double_dash_is_a_subtitle_break(self):
        assert normalize_filename(
            "C, A. - Robust option pricing -- An empirical study.pdf"
        ) == "C, A. - Robust option pricing, An empirical study.pdf"

    def test_between_digits_it_is_a_range(self):
        assert normalize_filename(
            "S, J. - Collected papers pp. 10--20 of volume III.pdf"
        ) == "S, J. - Collected papers pp. 10–20 of volume III.pdf"

    def test_the_subtitle_word_then_lowercases(self):
        """The comma is only half the fix — "An empirical study" is not a
        new sentence, so the caser must take the capital off."""
        from processing.title_normalize import propose_title_case
        stem = normalize_filename(
            "C, A. - Robust option pricing -- An empirical study.pdf")[:-4]
        title = stem.split(" - ", 1)[1]
        assert propose_title_case(title).proposed == (
            "Robust option pricing, an empirical study")
