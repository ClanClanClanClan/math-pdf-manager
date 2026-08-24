"""The filename decomposer: books and seminaires, where the naive split lies.

23,271 of 27,160 library filenames really are "Authors - Title".  The other
3,889 put a series name, a volume number, an expose number or a page range in
the first segment, and ``stem.split(" - ", 1)`` therefore hands back a wrong
author for every one of them.

Every case below is a REAL filename from the library, and every expectation
was checked by hand.  This is a frozen corpus: if it changes, either the
parser regressed or somebody re-labelled the library, and both deserve to
stop a commit.
"""
import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from processing.filename_ground_truth import (
    Kind, Role, Reliability, Decomposition, decompose,
    looks_like_author_block, looks_like_malformed_author_block,
    looks_like_western_author_list, repair_author_block,
)

SEM = "08 - Séminaires de probabilités de Strasbourg/Séminaire 12 - 1978"
AST = "05 - Books and lecture notes/05 - Astérisque"
CR = "05 - Books and lecture notes/01 - Comptes rendus hebdomadaires de l'académie des sciences"
SMF = "05 - Books and lecture notes/03 - Mémoires de la société mathématique de France"
SF = "05 - Books and lecture notes/06 - Saint-Flour"
PUB = "01 - Published papers/R"
JEHPS = "09 - Journal Électronique d'Histoire des Probabilités et de la Statistique"


# ----------------------------------------------------------------------
# The invariant that keeps three states from collapsing into two
# ----------------------------------------------------------------------
class TestTheThreeStateInvariant:
    def test_an_unknown_without_a_reason_is_refused(self):
        with pytest.raises(ValueError, match="no reason"):
            Decomposition(stem="x", reliability=Reliability.UNKNOWN)

    def test_a_reliable_result_may_not_carry_a_reason(self):
        with pytest.raises(ValueError, match="reasons belong only"):
            Decomposition(stem="x", title="t", reliability=Reliability.RELIABLE,
                          reason="but why")

    def test_a_reliable_result_must_have_a_title(self):
        with pytest.raises(ValueError, match="empty title"):
            Decomposition(stem="x", reliability=Reliability.RELIABLE)

    def test_every_abstention_the_library_produces_explains_itself(self):
        for stem, directory in [("", ""), ("Mean_Field_Control_on_Spaces", PUB),
                                ("Document 2, curiculum vitae Marc Barbut", JEHPS)]:
            d = decompose(stem, directory)
            if not d.is_reliable:
                assert d.reason, f"{stem!r} abstained silently"


# ----------------------------------------------------------------------
# The frozen corpus
# ----------------------------------------------------------------------
#: (directory, stem, series, ordinal, authors, title, kind)
CORPUS = [
    # --- the ordinary case, which must not change -----------------------
    (PUB, "Rogers, L. C. G. - Which model for term-structure of interest rates should one use",
     "", "", "Rogers, L. C. G.", "Which model for term-structure of interest rates should one use",
     Kind.ARTICLE),
    ("01 - Published papers/L", "León, J. A., Nualart, D. - An extension of the divergence operator for Gaussian processes",
     "", "", "León, J. A., Nualart, D.", "An extension of the divergence operator for Gaussian processes",
     Kind.ARTICLE),

    # --- Seminaire de probabilites: the expose number is not an author ---
    (SEM, "16-Léandre, R., Norris, J. R. - Integration by parts and Cameron-Martin formulas",
     "Séminaire 12 - 1978", "16", "Léandre, R., Norris, J. R.",
     "Integration by parts and Cameron-Martin formulas", Kind.ARTICLE),
    (SEM, "134-Lépingle, D. - Une inégalité de martingales",
     "Séminaire 12 - 1978", "134", "Lépingle, D.", "Une inégalité de martingales", Kind.ARTICLE),
    # A TWO-PART page ordinal: the second item beginning on page 740.
    (SEM, '740-1-Dellacherie, C. - Correction "Un crible généralisé"',
     "Séminaire 12 - 1978", "740-1", "Dellacherie, C.",
     'Correction "Un crible généralisé"', Kind.ARTICLE),

    # --- Asterisque: series first, then MAYBE an author -----------------
    (AST, "Astérisque 390 - Baues, O. - Symplectic Lie groups",
     "Astérisque 390", "390", "Baues, O.", "Symplectic Lie groups", Kind.ARTICLE),
    (AST, "Astérisque 426 - Biran, P., Cornea, O., Shelukhin, E. - Lagrangian shadows and triangulated categories",
     "Astérisque 426", "426", "Biran, P., Cornea, O., Shelukhin, E.",
     "Lagrangian shadows and triangulated categories", Kind.ARTICLE),
    # No author at all -- a Bourbaki volume bound as an Asterisque number.
    (AST, "Astérisque 252 - Séminaire Bourbaki, volume 1997:1998, exposés 835–849",
     "Astérisque 252", "252", "", "Séminaire Bourbaki, volume 1997:1998, exposés 835–849",
     Kind.VOLUME),
    # A THREE-part volume range is one book.
    (AST, "Astérisque 198–199–200 - Journées arithmétiques de Luminy, 17–21 juillet 1989",
     "Astérisque 198–199–200", "198–199–200", "",
     "Journées arithmétiques de Luminy, 17–21 juillet 1989", Kind.PROCEEDINGS),
    # A title that itself contains " - " must survive intact.
    (AST, "Astérisque 016 - Séminaire de géométrie analytique",
     "Astérisque 016", "016", "", "Séminaire de géométrie analytique", Kind.PROCEEDINGS),

    # --- Comptes rendus: a bound volume has no author -------------------
    (CR, "Comptes rendus hebdomadaires des séances de l'académie des sciences, tome 099, juillet–décembre 1884",
     "Comptes rendus hebdomadaires des séances de l'académie des sciences", "099", "",
     "Comptes rendus hebdomadaires des séances de l'académie des sciences, tome 099, juillet–décembre 1884",
     Kind.VOLUME),

    # --- Memoires de la SMF: the series designation contains commas -----
    (SMF, "Mémoires de la S.M.F. 2e série, tome 18 (1985) - Blondel, C. - Les représentations supercuspidales",
     "Mémoires de la S.M.F. 2e série, tome 18 (1985)", "", "Blondel, C.",
     "Les représentations supercuspidales", Kind.ARTICLE),

    # --- Saint-Flour: a zero-padded sequence number ---------------------
    (SF, "001 - Bretagnolle, J.L., Chatterji, S.D., Meyer, P.-A. - École d'été de probabilités de Saint-Flour III",
     "Saint-Flour", "001", "Bretagnolle, J.L., Chatterji, S.D., Meyer, P.-A.",
     "École d'été de probabilités de Saint-Flour III", Kind.ARTICLE),

    # --- a page range in the first slot, inside an Asterisque volume ----
    (AST, "279–298 - Bourgain, J. - Some results on the bidisc algebra",
     "Astérisque", "279–298", "Bourgain, J.", "Some results on the bidisc algebra", Kind.ARTICLE),

    # --- authors in Western order, filed before the convention settled --
    ("01 - Published papers/D", "Diego Compagna and Stefanie Steinhart - Monsters, Monstrosities",
     "", "", "Diego Compagna and Stefanie Steinhart", "Monsters, Monstrosities", Kind.ARTICLE),
]


class TestFrozenCorpus:
    @pytest.mark.parametrize(
        "directory,stem,series,ordinal,authors,title,kind", CORPUS,
        ids=[c[1][:52] for c in CORPUS])
    def test_decomposition(self, directory, stem, series, ordinal, authors, title, kind):
        d = decompose(stem, directory)
        assert d.is_reliable, f"abstained: {d.reason}"
        assert d.authors == authors
        assert d.title == title
        assert d.kind is kind
        if series:
            assert d.series == series
        assert d.ordinal == ordinal


class TestTheNaiveSplitIsWrong:
    """The point of the whole module, stated as tests.

    Each of these is a name where ``split(" - ", 1)`` returns something that
    is not an author, and one of them -- the Bourbaki volume -- is the exact
    shape that put ``gt_authors: ["08"]`` into the model's eval set.
    """

    @pytest.mark.parametrize("directory,stem,naive_author", [
        (SEM, "16-Léandre, R., Norris, J. R. - Integration by parts", "16-Léandre, R., Norris, J. R."),
        (AST, "Astérisque 390 - Baues, O. - Symplectic Lie groups", "Astérisque 390"),
        (CR, "Comptes rendus hebdomadaires des séances de l'académie des sciences, tome 301, série I - Mathématique, nº12 - 20 mars 1985",
         "Comptes rendus hebdomadaires des séances de l'académie des sciences, tome 301, série I"),
        (SF, "001 - Bretagnolle, J.L. - École d'été", "001"),
        (AST, "279–298 - Bourgain, J. - Some results on the bidisc algebra", "279–298"),
    ])
    def test_the_first_segment_is_not_the_author(self, directory, stem, naive_author):
        naive = unicodedata.normalize("NFC", stem).split(" - ", 1)[0]
        assert naive == naive_author, "the naive split does not do what this test claims"
        d = decompose(stem, directory)
        assert d.authors != naive_author
        assert d.is_reliable

    def test_a_series_number_never_becomes_an_author(self):
        """gt_authors == ["08"] is what this prevents."""
        d = decompose("08 - Audin, M. - Les systèmes hamiltoniens et leur intégrabilité",
                      "05 - Books and lecture notes/04 - Cours spécialisés")
        assert d.authors == "Audin, M."
        assert d.ordinal == "08"
        assert d.title == "Les systèmes hamiltoniens et leur intégrabilité"


# ----------------------------------------------------------------------
# The primitive everything turns on
# ----------------------------------------------------------------------
class TestTheSeminaireNumberIsAPage:
    """It is the first page in the bound volume, not an expose number.

    I had this wrong in a comment and a subagent caught it.  The document
    settles it: "134-Lepingle, D. - Une inegalite de martingales" opens with
    "Seminaire de probabilites (Strasbourg), tome 12 (1978), p. 134-137."
    Volume 12 holds 62 articles numbered 1, 20, 22, 35, 47, 114 ... 740, and
    the gaps are article lengths -- 62 articles cannot carry expose numbers
    running past 700.
    """

    def test_the_number_is_kept_as_the_ordinal(self):
        d = decompose("134-Lépingle, D. - Une inégalité de martingales", SEM)
        assert d.ordinal == "134"
        assert d.authors == "Lépingle, D."

    def test_the_numbers_in_one_volume_are_not_a_dense_sequence(self):
        """If they were expose numbers they would run 1..62."""
        ordinals = [decompose(f"{n}-Meyer, P.-A. - A title", SEM).ordinal
                    for n in (1, 20, 22, 35, 47, 114, 740)]
        assert ordinals == ["1", "20", "22", "35", "47", "114", "740"]

    def test_a_second_item_on_the_same_page(self):
        d = decompose('740-1-Dellacherie, C. - Correction "Un crible généralisé"', SEM)
        assert d.ordinal == "740-1"
        assert d.authors == "Dellacherie, C."


class TestWhoTheNamesAre:
    """A filename says WHICH names; it does not say what they did."""

    def test_a_checked_edited_series_is_marked_editor(self):
        d = decompose("017-Glaisher, J. W. L. - Messenger of mathematics, volume XVII, May, 1887–April, 1888",
                      "05 - Books and lecture notes/09 - Messenger of mathematics")
        assert d.name_role is Role.EDITOR
        assert d.authors == "Glaisher, J. W. L."   # the names are kept either way

    def test_an_unchecked_collected_works_is_marked_uncertain_not_editor(self):
        """Cauchy wrote his Oeuvres completes.  The shape is identical to the
        Messenger one, so guessing "editor" from the shape would be wrong for
        a few hundred files."""
        d = decompose("Cauchy, A.-L. - Œuvres complètes d'Augustin Cauchy, tome I",
                      "05 - Books and lecture notes/C")
        assert d.name_role is Role.UNCERTAIN
        assert d.authors == "Cauchy, A.-L."

    def test_an_ordinary_paper_is_not_dragged_in_by_the_word_volume(self):
        """The first version of the volume pattern was case-insensitive, so
        the "i" of "in" was a Roman numeral and "The role of volume in order
        book dynamics" made its three authors editors.  204 files."""
        d = decompose("Rambaldi, M., Bacry, E., Lillo, F. - The role of volume in order book dynamics",
                      "01 - Published papers/R")
        assert d.name_role is Role.AUTHOR
        assert d.authors == "Rambaldi, M., Bacry, E., Lillo, F."

    @pytest.mark.parametrize("stem,author", [
        ("Fremlin, D. H. - Measure theory volume 3, measure algebras", "Fremlin, D. H."),
        ("Schwartz, L. - Cours d'analyse volume 1", "Schwartz, L."),
        ("Dieudonné, J. - Eléments d'analyse volume 1", "Dieudonné, J."),
    ])
    def test_an_author_who_wrote_a_multi_volume_book_is_still_an_author(self, stem, author):
        """Fremlin WROTE Measure Theory; the volume number is part of his
        title, not a journal designation.

        This is what the "(?:^|,)" anchor buys, and it is the only thing that
        does: the volume designation of an edited journal follows a comma
        (", volume XVII, May 1887-April 1888"), an author's own volume number
        does not. 24 books in the library depend on it. My first test here
        used "The role of volume in order book dynamics", which the anchor
        does not decide -- so a mutant that deleted the anchor survived."""
        d = decompose(stem, "05 - Books and lecture notes/F")
        assert d.name_role is Role.AUTHOR
        assert d.authors == author

    def test_a_volume_with_no_names_has_role_none(self):
        d = decompose("Comptes rendus hebdomadaires des séances de l'académie des sciences, tome 099, juillet–décembre 1884", CR)
        assert d.name_role is Role.NONE
        assert d.authors == ""


class TestAbsenceOfANameIsNotAbsenceOfAnAuthor:
    """The distinction the whole three-state design exists for.

    A subagent opened eight authorless-LOOKING Asterisque volumes and found
    two were single works whose authors appear only on the title page.  So
    "no name block" establishes "this work has no author" ONLY when the title
    announces a collective work.
    """

    def test_a_collective_work_reliably_has_no_author(self):
        d = decompose("Astérisque 252 - Séminaire Bourbaki, volume 1997:1998, exposés 835–849", AST)
        assert d.is_reliable
        assert d.authors == ""
        assert d.rule.endswith("collective")

    def test_a_monograph_with_no_name_block_abstains(self):
        d = decompose("Astérisque 375 - Pseudofunctions and Helson sets", AST)
        assert not d.is_reliable
        assert "monograph" in d.reason

    def test_the_two_are_not_the_same_answer(self):
        collective = decompose("Astérisque 016 - Séminaire de géométrie analytique", AST)
        monograph = decompose("Astérisque 375 - Pseudofunctions and Helson sets", AST)
        assert collective.authors == monograph.authors == ""
        assert collective.is_reliable and not monograph.is_reliable


class TestAuthorBlockRecogniser:
    @pytest.mark.parametrize("block", [
        "Meyer, P.-A.",
        "Rogers, L. C. G.",
        "Kabanov, Yu. A.",                     # multi-letter Cyrillic initial
        "Bouchaud, J.-P.",                     # hyphenated given name
        "Chaudru de Raynal, P.-É.",            # particle inside the surname
        "da Prato, G.",                        # surname opening with a particle
        "dell'Antonio, G.",                    # elided article
        "in t'Hout, K., Toivanen, J.",         # the spelling the library uses
        "in 't Hout, K., Toivanen, J.",        # and the correct Dutch one
        "Şengül, B.",                          # S-cedilla
        "Baňas, Ľ.",                           # L-caron, as surname AND initial
        "Leutscher de las Nieves, M.",
        "abd Ellah, A. E.",
        "Seifried (née Müller), S.",           # parenthetical maiden name
        "Harvey, F.R., Lawson, Jr., H.B.",     # generational suffix
        "Neufeld, A., et al.",
        "Émery, M., Yor, M.",
    ])
    def test_accepted(self, block):
        assert looks_like_author_block(block)

    @pytest.mark.parametrize("not_a_block", [
        "Astérisque 390",
        "Comptes rendus hebdomadaires des séances de l'académie des sciences",
        "Séminaire de probabilités II",
        "279–298",
        "16",
        "Local collapsing, orbifolds, and geometrization",
        "Exponential functionals of Brownian motion, I, probability laws at fixed time",
        "Analysis I",
        "Table des comptes rendus des séances de l'académie des sciences, tome 293",
        "",
    ])
    def test_rejected(self, not_a_block):
        assert not looks_like_author_block(not_a_block)

    def test_no_title_in_the_library_is_mistaken_for_an_author_block(self):
        """Measured: 0 of 23,271 real titles.  The asymmetry is deliberate --
        accepting a title INVENTS an author, which is the corruption being
        removed; refusing an author block only produces an abstention."""
        for title in ["Robust financial calibration, a Bayesian approach for neural SDEs",
                      "Optimal trading strategies and the Bessel process",
                      "On the saddle point of a zero-sum stopper vs. singular-controller game",
                      "Δ, Γ and bucket hedging of interest rate derivatives",
                      "Ginzburg-Landau equation and motion by mean curvature, I, convergence"]:
            assert not looks_like_author_block(title)


class TestMalformedBlocks:
    @pytest.mark.parametrize("broken,repaired", [
        ("Almgren, R, Chriss, N. A.", "Almgren, R., Chriss, N. A."),
        ("Zhang. Y.", "Zhang, Y."),
        ("van Handel R.", "van Handel, R."),
        ("Reitich, F. Soner, H. M.", "Reitich, F., Soner, H. M."),
        ("Bouchaud, J, -P.", "Bouchaud, J.-P."),
    ])
    def test_a_typo_is_recognised_and_repaired(self, broken, repaired):
        assert looks_like_malformed_author_block(broken)
        assert repair_author_block(broken) == repaired

    def test_a_malformed_block_is_not_reported_as_western_order(self):
        """It was, for 154 blocks.  The decomposition was right and the
        provenance was a lie, and the provenance is what a human sees."""
        assert not looks_like_western_author_list("Almgren, R, Chriss, N. A.")
        d = decompose("Almgren, R, Chriss, N. A. - Optimal execution of portfolio transactions",
                      "01 - Published papers/A")
        assert d.rule.endswith("malformed-block")
        assert d.authors == "Almgren, R, Chriss, N. A."

    @pytest.mark.parametrize("title", [
        "Analysis I",
        "Exponential functionals of Brownian motion, I, probability laws at fixed time",
        "Ginzburg-Landau equation and motion by mean curvature, I, convergence",
        "Stochastic games for fuel follower problem, N versus mean field game",
        "Penalizing a Bes(d) process (0<d<2) with a function of its local time, V",
    ])
    def test_a_title_does_not_repair_into_an_author(self, title):
        """The first version of this test failed on all five.  A pattern for
        'looks a bit broken' matched ", I," in a title; asking whether a short
        list of repairs reaches a canonical block does not."""
        assert not looks_like_malformed_author_block(title)


# ----------------------------------------------------------------------
# Pathologies
# ----------------------------------------------------------------------
class TestNormalisation:
    def test_nfd_and_nfc_decompose_identically(self):
        """macOS hands filenames back DECOMPOSED.  335 Asterisque files were
        misclassified because a regex spelled the accent precomposed."""
        stem = "Astérisque 390 - Baues, O. - Symplectic Lie groups"
        nfd = unicodedata.normalize("NFD", stem)
        assert nfd != stem, "this test needs a genuinely decomposed input"
        a, b = decompose(stem, AST), decompose(nfd, AST)
        assert (a.series, a.authors, a.title) == (b.series, b.authors, b.title)

    def test_the_directory_is_normalised_too(self):
        nfd_dir = unicodedata.normalize("NFD", AST)
        d = decompose("279–298 - Bourgain, J. - Some results", nfd_dir)
        assert d.is_reliable and d.authors == "Bourgain, J."


class TestPathologies:
    @pytest.mark.parametrize("stem", [
        "", "   ", " - ", "-", "---", ".", "..", "0", "1-", "- - -",
        "\x00", "\x1d", "a" * 400, "16-", "Astérisque", "Astérisque 390 - ",
    ])
    def test_never_raises_and_never_lies(self, stem):
        d = decompose(stem, AST)
        assert isinstance(d, Decomposition)
        if not d.is_reliable:
            assert d.reason
        else:
            assert d.title

    def test_a_title_containing_the_separator_is_not_split_again(self):
        d = decompose(
            "Astérisque 065 - Journées de géométrie algébrique de Rennes - (Juillet 1978) (III)",
            AST)
        assert d.authors == ""
        assert d.title == "Journées de géométrie algébrique de Rennes - (Juillet 1978) (III)"

    def test_an_author_block_never_comes_back_containing_the_separator(self):
        for directory, stem, *_ in CORPUS:
            assert " - " not in decompose(stem, directory).authors


class TestProperties:
    @settings(max_examples=250, deadline=None)
    @given(st.text(max_size=120))
    def test_total_and_honest(self, stem):
        """Any string at all: a Decomposition comes back, and it is either
        reliable with a title or unknown with a reason.  Never neither."""
        d = decompose(stem, AST)
        assert (d.is_reliable and d.title) or (not d.is_reliable and d.reason)

    @settings(max_examples=200, deadline=None)
    @given(st.sampled_from([c[4] for c in CORPUS if c[4]]),
           st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Zs")),
                   min_size=5, max_size=60).filter(lambda s: s.strip() and " - " not in s))
    def test_a_reconstructed_name_decomposes_back(self, authors, title):
        d = decompose(f"{authors} - {title.strip()}", PUB)
        assert d.is_reliable
        assert d.authors == authors
        # NFC, because decompose normalises and some generated codepoints
        # have a composed equivalent (U+1FDB -> U+038A).
        assert d.title == unicodedata.normalize("NFC", title.strip())

    @settings(max_examples=150, deadline=None)
    @given(st.integers(min_value=0, max_value=9999),
           st.sampled_from([c[4] for c in CORPUS if c[4]]))
    def test_any_expose_number_is_peeled_off_the_author(self, number, authors):
        d = decompose(f"{number}-{authors} - Some title about martingales", SEM)
        assert d.is_reliable
        assert d.ordinal == str(number)
        assert d.authors == authors


class TestWhatItStillDoesNotDo:
    """Known limits, written so they FAIL if they start working.

    A stale "we cannot do this" comment is worse than no comment, so each of
    these will break the build the day somebody fixes it, and the fixer will
    be told to delete the test rather than discovering the note was wrong.
    """

    def test_an_author_missing_from_the_filename_is_not_invented(self):
        """JEHPS archival documents have an author; the filename omits them.
        Answering "" would assert the document HAS no author, which is a
        different and false claim -- so this abstains, and must keep
        abstaining until there is real evidence to use."""
        d = decompose("An autobiographical note by Paul Lévy, written for Takeyuki Hida in 1969",
                      JEHPS)
        assert not d.is_reliable
        assert "no ' - ' separator" in d.reason

    def test_a_corporate_author_is_not_resolved(self):
        d = decompose("Center for the commercialization of electric technologies - Technology solutions",
                      "02 - Unpublished papers/C")
        assert not d.is_reliable

    def test_an_en_dash_used_as_the_separator_is_not_understood(self):
        """One file in the library separates with " – " instead of " - "."""
        d = decompose("Zame, W.R. – Incentives, contracts, and markets", PUB)
        assert not d.is_reliable


# ----------------------------------------------------------------------
# The override table
# ----------------------------------------------------------------------
class TestTheOverrideTable:
    """Ground truth for names the rules cannot settle, each with evidence.

    The danger with any override table is that it becomes the place parser
    bugs go to hide.  This one cannot: ``decompose`` consults it only after
    the rules have already abstained, so there is no code path from a working
    rule into it.  The tests below hold that guarantee in place.
    """

    @staticmethod
    def _entries():
        import json
        from processing.filename_ground_truth import _OVERRIDES_PATH
        with _OVERRIDES_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)["entries"]

    def test_every_override_is_for_a_name_the_rules_abstain_on(self):
        """If a rule starts handling one of these, the entry is dead weight
        and must be deleted -- and this test says so rather than letting it
        sit there quietly disagreeing with the parser."""
        shadowing = []
        for e in self._entries():
            d = decompose(e["stem"], e.get("directory", ""), use_overrides=False)
            if d.is_reliable:
                shadowing.append((e["stem"], d.rule))
        assert shadowing == [], (
            "these overrides now shadow a working rule and should be removed: "
            f"{shadowing}")

    def test_every_override_carries_its_evidence(self):
        for e in self._entries():
            assert e.get("evidence"), f"{e['stem']!r} has no evidence"
            assert e.get("confidence") in {"high", "medium", "review"}

    def test_an_override_result_is_marked_as_one(self):
        d = decompose("Astérisque 010 - Prolongement analytique et algèbres de Banach ultramétriques", AST)
        assert d.is_reliable
        assert d.rule.startswith("override(")
        assert d.evidence
        assert d.authors == "Escassut, A., Robba, P."

    def test_the_rules_are_measured_without_the_table(self):
        """use_overrides=False must actually change the answer, or every
        measurement of 'what the rules achieve' is quietly inflated."""
        with_table = decompose("Astérisque 010 - Prolongement analytique et algèbres de Banach ultramétriques", AST)
        rules_only = decompose("Astérisque 010 - Prolongement analytique et algèbres de Banach ultramétriques",
                               AST, use_overrides=False)
        assert with_table.is_reliable
        assert not rules_only.is_reliable

    def test_the_table_cannot_shadow_a_rule_even_if_someone_adds_one(self):
        """The invariant, proved rather than asserted.

        test_every_override_is_for_a_name_the_rules_abstain_on only checks
        today's table -- it passes even if the guard is deleted, because no
        entry currently collides. This plants a colliding entry and shows the
        rules still win. A mutation that removes the guard survives the other
        test and dies on this one."""
        import processing.filename_ground_truth as m
        name = "Rogers, L. C. G. - Which model for term-structure of interest rates should one use"
        colliding = {name: {"stem": name, "authors": "Fabricated, A.",
                            "name_role": "author", "title": "Not the real title",
                            "kind": "article", "confidence": "high",
                            "evidence": "planted by a test"}}
        original = m._overrides
        try:
            m._overrides = lambda: colliding
            d = decompose(name, PUB)
            assert d.authors == "Rogers, L. C. G."
            assert d.title == "Which model for term-structure of interest rates should one use"
            assert not d.rule.startswith("override")
        finally:
            m._overrides = original

    def test_a_missing_table_does_not_break_decomposition(self):
        """The table is data.  Losing it must degrade to abstention, never to
        an exception in the middle of an ingest."""
        import processing.filename_ground_truth as m
        m._overrides.cache_clear()
        original = m._OVERRIDES_PATH
        try:
            m._OVERRIDES_PATH = original.with_name("does-not-exist.json")
            m._overrides.cache_clear()
            d = decompose("Astérisque 010 - Prolongement analytique et algèbres de Banach ultramétriques", AST)
            assert not d.is_reliable and d.reason
        finally:
            m._OVERRIDES_PATH = original
            m._overrides.cache_clear()
