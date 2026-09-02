"""Typo detection — and the ways a spell check lies.

The module this replaces answered "spelled correctly" for every word of
two or more characters, because its dictionary had been removed from the
dependencies and the no-backend branch returned ``len(word) == 1``. It
was not detected for months, because a checker that always says "fine"
is indistinguishable from a clean library.

So the tests below are mostly about the ways a checker can APPEAR to
work: an oracle that answers without looking, a normalisation that folds
a corruption into a real word, a case variant that blesses gibberish.
Each "must not" is a real failure mode measured on this corpus.
"""
from __future__ import annotations

import unicodedata

import pytest

from maintenance import typos as T
from maintenance.typos import (
    CorpusStats,
    Suspect,
    TypoOracleUnavailable,
    TypoReport,
    Verdict,
    broken_characters,
    build_corpus_stats,
    examine_title,
    max_distance,
    oracle_verdict,
    self_check,
)


@pytest.fixture
def corpus():
    """A miniature library: enough repetition to make partners frequent."""
    names = [f"Author, A. - American mathematics paper number {i}"
             for i in range(25)]
    names += [f"Writer, B. - On stochastic processes and control {i}"
              for i in range(25)]
    names += [f"Third, C. - Markov chains under weak conditions {i}"
              for i in range(25)]
    names += [f"Fourth, D. - Brownian motion and its paths {i}"
              for i in range(25)]
    names += ["Smith, J. - Amererican mathematics revisited",
              "Jones, K. - On browniam motion and its paths",
              "Brown, L. - More browniam motion results here",
              "White, D. - On makov chains and their limits"]
    return build_corpus_stats(names)


class TestTheOracleIsHonestAboutNotLooking:
    """NSSpellChecker accepts ANY all-caps string of six characters or
    fewer — "WIITH", "CONTOL", and pure gibberish like "QZXVQZ" all come
    back correct, while the same string one character longer is
    rejected. That is a verdict returned without looking, and it must
    never be reported as CLEAN.
    """

    @pytest.mark.parametrize("word", ["WIITH", "CONTOL", "UNBER", "QZXVQZ",
                                      "QQ", "ABCDE"])
    def test_short_all_caps_is_unknown_not_clean(self, word):
        assert oracle_verdict(word) is Verdict.UNKNOWN

    def test_one_character_past_the_blind_zone_is_actually_judged(self):
        """The boundary is real and measured: 6 accepted, 7 rejected."""
        assert oracle_verdict("QZXVQZX") is Verdict.TYPO

    @pytest.mark.parametrize("word", ["wiith", "contol", "unber"])
    def test_the_lowercase_form_is_still_caught(self, word):
        """A tempting "normalise by uppercasing" would drop these into
        the blind zone and silently bless them."""
        assert oracle_verdict(word) is Verdict.TYPO

    @pytest.mark.parametrize("word", ["", "  ", "123", "..."])
    def test_nothing_to_judge_is_unknown_not_clean(self, word):
        assert oracle_verdict(word) is Verdict.UNKNOWN


class TestTheOracleKnowsThisLibrarysLanguages:

    @pytest.mark.parametrize("word", [
        "American", "Volterra", "McKean", "Vlasov",
        "behaviour", "behavior", "modelling", "modeling",   # US and UK
        "probabilités", "Wahrscheinlichkeit", "matematica",  # fr, de, it
    ])
    def test_real_words_are_clean(self, word):
        assert oracle_verdict(word) is Verdict.CLEAN

    @pytest.mark.parametrize("word", ["Amererican", "teh", "qqqqzzzz",
                                      "recieve", "seperate"])
    def test_misspellings_are_typos(self, word):
        assert oracle_verdict(word) is Verdict.TYPO

    def test_case_matters_to_the_oracle(self):
        """"american" lowercase is REJECTED while "American" is accepted,
        so querying only the lowercase form manufactures false positives
        — it produced 377 of them over the real library."""
        assert oracle_verdict("American") is Verdict.CLEAN
        assert oracle_verdict("american") is Verdict.CLEAN

    @pytest.mark.parametrize("word", ["xAmererican", "MeanFeild",
                                      "stochasticContol"])
    def test_a_corruption_glued_to_a_word_is_still_caught(self, word):
        """No camelCase splitting is needed for this: the oracle already
        rejects these whole. Splitting was tried and removed — it turned
        "McKean" into "Mc" + "Kean" and flagged every Mc- surname."""
        assert oracle_verdict(word) is Verdict.TYPO

    @pytest.mark.parametrize("word", ["McKean", "MacDonald", "LeCam"])
    def test_internal_capital_surnames_survive(self, word):
        assert oracle_verdict(word) is Verdict.CLEAN

    def test_a_compound_of_two_REAL_words_is_not_caught(self):
        """Stated as a limitation, not an accident: "MeanField" is
        accepted because both halves are real. That is not a typo."""
        assert oracle_verdict("MeanField") is Verdict.CLEAN


class TestSelfCheckRefusesADegradedOracle:
    """A bridge that cannot tell "American" from "Amererican" is not a
    bridge. It must RAISE, not return an object that answers anyway.
    """

    def test_an_oracle_that_rejects_real_words_is_refused(self):
        class AlwaysNo:
            def known(self, word): return False
        with pytest.raises(TypoOracleUnavailable, match="American"):
            self_check(AlwaysNo())

    def test_an_oracle_that_accepts_everything_is_refused(self):
        """The precise shape of the bug being replaced: the old checker
        answered "spelled correctly" for every word of 2+ characters."""
        class AlwaysYes:
            def known(self, word): return True
        with pytest.raises(TypoOracleUnavailable, match="Amererican"):
            self_check(AlwaysYes())

    def test_the_real_oracle_passes(self):
        """"self_check() did not raise" is not a postcondition — assert
        the sentinel verdicts the real bridge must produce, so a bridge
        that answers uniformly cannot slip through here."""
        self_check()
        assert oracle_verdict("American") is Verdict.CLEAN
        assert oracle_verdict("Amererican") is Verdict.TYPO
        assert oracle_verdict("behaviour") is Verdict.CLEAN


class TestNoOracleNeverMeansClean:
    """THE property this module exists for."""

    def test_a_dead_bridge_raises_rather_than_answering(self, monkeypatch):
        def dead():
            raise TypoOracleUnavailable("no dictionary")
        monkeypatch.setattr(T, "_oracle", dead)
        oracle_verdict.cache_clear()
        with pytest.raises(TypoOracleUnavailable):
            oracle_verdict("Amererican")
        oracle_verdict.cache_clear()

    def test_an_unknown_report_must_say_why(self):
        with pytest.raises(ValueError):
            TypoReport(Verdict.UNKNOWN)          # no reason
        with pytest.raises(ValueError):
            TypoReport(Verdict.CLEAN, unknown_reason="but why")
        assert TypoReport(Verdict.UNKNOWN, unknown_reason="no dict")


class TestNormalisationTraps:

    def test_casefold_would_hide_every_ligature_corruption(self):
        """str.casefold() maps U+FB00 to "ff", so "diﬀerential" folds to
        the correctly-spelled, frequent word "differential" and the
        corruption becomes invisible. The corpus key must use .lower()."""
        assert "diﬀerential".casefold() == "differential"
        assert "diﬀerential".lower() != "differential"
        stats = build_corpus_stats(["A. - diﬀerential study"] +
                                   [f"B. - differential equations {i}"
                                    for i in range(25)])
        assert "diﬀerential" in stats.title_df
        assert stats.title_df["diﬀerential"] == 1

    def test_decomposed_input_counts_as_the_composed_word(self):
        """23% of these filenames arrive NFD. Without normalising, the
        tokenizer manufactures phantom words — "vy" for Lévy."""
        nfd = unicodedata.normalize("NFD", "Lévy")
        stats = build_corpus_stats([f"A. - {nfd} processes"])
        assert "lévy" in stats.title_df
        assert "vy" not in stats.title_df


class TestTheThresholdsBite:

    def test_the_motivating_case_needs_two_edits(self, corpus):
        """editdistance("amererican", "american") == 2, so any fixed
        max-distance-1 design misses the exact case this was built for."""
        assert max_distance("amererican") == 2
        report = examine_title(
            "Smith, J. - Amererican mathematics revisited", corpus)
        assert report.verdict is Verdict.TYPO
        assert [s.lower for s in report.suspects] == ["amererican"]
        assert report.suspects[0].suggestion == "american"
        assert report.suspects[0].distance == 2

    def test_short_words_get_only_one_edit(self):
        assert max_distance("cat") == 1
        assert max_distance("control") == 1        # 7 chars
        assert max_distance("controll") == 2       # 8 chars

    def test_a_word_in_two_files_is_never_flagged(self, corpus):
        """df == 1 is blind to recurring typos BY CONSTRUCTION — a bad
        habit, a copy-paste or a mis-ingested series is exactly what this
        design cannot see. Stated plainly so nobody mistakes silence for
        absence.

        The case has to be chosen carefully. My first version used
        "undre"/"under", which is edit-distance 2 on a 5-letter word and
        so was already excluded by the distance limit — the hapax rule
        could be loosened all the way to df <= 3 and the test still
        passed. "browniam"/"brownian" is 8 letters at distance 1, inside
        every other filter, so the hapax rule is the ONLY thing keeping
        it out of the queue.
        """
        assert corpus.title_df["browniam"] == 2
        assert corpus.title_df["brownian"] >= T.MIN_PARTNER_FREQ
        assert T._within("browniam", "brownian", max_distance("browniam")) == 1
        report = examine_title(
            "Jones, K. - On browniam motion and its paths", corpus)
        assert report.verdict is Verdict.CLEAN

    def test_a_word_below_the_length_floor_is_not_flagged(self, corpus):
        stats = build_corpus_stats(
            [f"A. - the control of systems {i}" for i in range(25)] +
            ["B. - the cotr of systems"])
        assert examine_title("B. - the cotr of systems",
                             stats).verdict is Verdict.CLEAN

    def test_a_five_letter_typo_IS_caught(self, corpus):
        """Pins the floor from below. Raising MIN_LEN to 6 costs ten real
        typos measured on this library — makov, wiith, unber, lobal,
        conex, metod, simpe, ageny, ation, intego — and this is one of
        them, so the threshold cannot drift upward unnoticed."""
        report = examine_title("White, D. - On makov chains and their limits",
                               corpus)
        assert report.verdict is Verdict.TYPO
        assert [s.lower for s in report.suspects] == ["makov"]
        assert report.suspects[0].suggestion == "markov"

    def test_a_rare_partner_is_not_evidence(self):
        """The partner must be FREQUENT; a rare neighbour proves nothing."""
        stats = build_corpus_stats(
            ["A. - scattering theory here", "B. - scatterign theory there"])
        assert examine_title("B. - scatterign theory there",
                             stats).verdict is Verdict.CLEAN

    def test_a_partner_with_a_different_first_letter_is_rejected(self):
        stats = build_corpus_stats(
            [f"A. - the American paper {i}" for i in range(25)] +
            ["B. - the qmerican paper"])
        report = examine_title("B. - the qmerican paper", stats)
        assert report.verdict is Verdict.CLEAN


class TestScope:

    def test_the_author_block_is_not_spell_checked(self):
        """Deliberate: the best oracle knows only 41.75% of author-block
        tokens, so checking the whole name flags 57% of the library."""
        stats = build_corpus_stats(
            [f"American, A. - a paper on american topics {i}"
             for i in range(25)] + ["Amererican, Z. - a study"])
        assert examine_title("Amererican, Z. - a study",
                             stats).verdict is Verdict.CLEAN

    def test_a_word_used_as_an_author_name_is_not_flagged_in_titles(self):
        stats = build_corpus_stats(
            [f"A. - the American paper {i}" for i in range(25)] +
            ["Amererican, Q. - unrelated",
             "B. - a tribute to Amererican and friends"])
        assert examine_title("B. - a tribute to Amererican and friends",
                             stats).verdict is Verdict.CLEAN


class TestDeterminism:

    def test_the_same_name_gives_the_same_answer(self, corpus):
        name = "Smith, J. - Amererican mathematics revisited"
        first = examine_title(name, corpus)
        for _ in range(5):
            again = examine_title(name, corpus)
            assert again.verdict is first.verdict
            assert [s.lower for s in again.suspects] == \
                   [s.lower for s in first.suspects]

    def test_corpus_stats_do_not_depend_on_input_order(self):
        names = [f"A. - word number {i}" for i in range(20)]
        assert build_corpus_stats(names).title_df == \
               build_corpus_stats(list(reversed(names))).title_df


class TestParameterFreeScanners:
    """No dictionary, no threshold, and no false positive is possible."""

    @pytest.mark.parametrize("name,kind", [
        ("A. - diﬀerential equations", "f-ligature"),
        ("A. - the ﬁrst passage time", "f-ligature"),
        ("A. - quanti\x1cation optimale", "control character"),
        ("A. - a title\x7fwith a delete", "control character"),
    ])
    def test_a_broken_character_is_found(self, name, kind):
        faults = broken_characters(name)
        assert faults, name
        assert any(f[2] == kind for f in faults), faults

    def test_a_ligature_reports_its_expansion(self):
        assert broken_characters("A. - diﬀerential")[0][3] == "ff"

    @pytest.mark.parametrize("name", [
        "Possamaï, D. - Stochastic control and BSDEs",
        "Itô, K. - On stochastic differential equations",
        "Lévy, P. - Théorie de l'addition des variables aléatoires",
        "A. - C^{1,α} regularity and Σ_{i=1}^∞ sums",
        "Başar, T. - Team-optimal closed-loop Stackelberg strategies",
    ])
    def test_ordinary_names_are_untouched(self, name):
        assert broken_characters(name) == []

    def test_it_finds_what_the_word_detector_cannot(self):
        """These two scanners exist separately because the statistical
        detector sees only 3 of the 20 real cases in the library: a
        ligature word is a hapax whose partner is often not frequent
        enough, and a control character does not break a word at all."""
        name = "A. - quanti\x1cation optimale et appliations"
        assert broken_characters(name)


class TestSuspectIsEvidenceNotAnInstruction:
    """Measured on the real library, the suggestion is WRONG for several
    entries: "lobal" suggests "local" but means global; "netral"
    suggests "neural" but means neutral; "expaction" suggests "expansion"
    but means expectation. Nothing may auto-apply these.
    """

    def test_a_suspect_carries_its_evidence(self, corpus):
        s = examine_title("Smith, J. - Amererican mathematics revisited",
                          corpus).suspects[0]
        assert isinstance(s, Suspect)
        assert s.suggestion_freq >= T.MIN_PARTNER_FREQ
        assert s.distance >= 1

    def test_the_module_exposes_no_way_to_apply_a_suggestion(self):
        applyish = [n for n in dir(T)
                    if any(k in n.lower()
                           for k in ("apply", "correct", "fix", "rename",
                                     "write", "save"))]
        assert applyish == [], applyish


class TestTheTitlesOwnLanguageDecides:
    """A word unknown to every dictionary is only evidence of a typo when
    the rest of the title is English.

    "Stochastik" is missing from macOS's German dictionary and sits one
    edit from "stochastic", which appears 3,817 times in this library —
    so the statistics were emphatic and completely wrong. The title is
    "Stochastik für das Lehramt". The answer was in the next three words.
    """

    @pytest.fixture
    def mixed(self):
        """Titles must be REALISTIC to exercise the classifier.

        My first fixture used "Quelques aspets de la finance moderne",
        which the rule correctly declined to call French: "finance" and
        "moderne" are both in the English dictionary, so the title has
        more English-accepted words than French-only ones. The gate never
        fired and the test passed for the wrong reason.
        """
        names = [f"A. - stochastic processes and control {i}" for i in range(30)]
        names += [f"B. - aspects of applications in analysis {i}" for i in range(30)]
        names += [f"C. - problems in analysis and geometry {i}" for i in range(30)]
        names += ["Beiglböck, M. - Stochastik für das Lehramt",
                  "Dupont, J. - Quelques résultats sur les aspets des "
                  "mesures aléatoires",
                  "Vorovka, K. - Poznámka k problemu ruinováni hrácu"]
        return build_corpus_stats(names)

    def test_a_german_word_in_a_german_title_is_not_a_typo(self, mixed):
        report = examine_title("Beiglböck, M. - Stochastik für das Lehramt",
                               mixed)
        assert report.verdict is not Verdict.TYPO
        assert "Stochastik" in report.unjudged, report

    def test_a_french_typo_in_a_french_title_IS_still_caught(self, mixed):
        """The gate has to be this narrow. Suppressing every unknown word
        in a foreign title was tried and measured: it removed 20 false
        positives but took ten real ones with it, because a French title
        can perfectly well contain a French typo."""
        report = examine_title(
            "Dupont, J. - Quelques résultats sur les aspets des "
            "mesures aléatoires", mixed)
        assert report.verdict is Verdict.TYPO
        assert [s.lower for s in report.suspects] == ["aspets"]

    def test_a_language_with_no_dictionary_at_all_is_unjudged(self, mixed):
        """Latin and Czech have no macOS dictionary, so there is no
        language to compare a suggestion against and the cross-language
        rule cannot fire. The share of words no dictionary knows is the
        signal instead."""
        report = examine_title(
            "Vorovka, K. - Poznámka k problemu ruinováni hrácu", mixed)
        assert report.verdict is not Verdict.TYPO

    def test_an_english_title_is_unaffected_by_any_of_this(self, corpus):
        report = examine_title("White, D. - On makov chains and their limits",
                               corpus)
        assert report.verdict is Verdict.TYPO


class TestCapitalisingMakesEveryCheckerPermissive:
    """The trap that made the first version of the language gate useless.

    A capitalised unknown word reads as a proper noun, so the checker
    accepts it: "Measure" passes the GERMAN, FRENCH, ITALIAN and SPANISH
    dictionaries while "measure" passes none of them. Asking "is this a
    word of language L" with a capitalised form therefore answers yes for
    almost anything, and the cross-language rule silently never fired.

    WHICH words show it is the OS's business and changes between macOS
    releases -- "Stochastic" demonstrated it when this was written and no
    longer does on 26.6 -- so the tests below assert the property and
    merely report the examples.
    """

    # The population the trap is measured on. Ordinary English maths
    # vocabulary -- the words that actually appear in these titles.
    PROBE = ("Stochastic", "Ergodic", "Martingale", "Diffusion", "Filtering",
             "Random", "Brownian", "Optimal", "Portfolio", "Hedging",
             "Viscosity", "Backward", "Convex", "Measure", "Process",
             "Kernel", "Lattice", "Sampling")
    FOREIGN = ("de", "fr", "it", "es")

    def test_the_trap_still_exists(self):
        """At least one word is accepted capitalised and rejected lower.

        This used to assert ``accepts("Stochastic", "de") is True``, and
        macOS 26.6 now rejects that one word -- so a REAL property was
        pinned to an example the OS was free to change its mind about,
        and the suite went red without anything in this repository
        moving. The property is what matters, so the property is what is
        asserted; the examples are reported, not required.

        MEASURED 2026-09-02, macOS 26.6, over the 18 words in PROBE:
            de: Diffusion, Filtering, Measure, Process, Sampling
            fr: Measure
            it: Optimal, Measure
            es: Optimal, Measure
        """
        oracle = T._oracle()
        found = {
            lang: [w for w in self.PROBE
                   if oracle.accepts(w, lang)
                   and not oracle.accepts(w.lower(), lang)]
            for lang in self.FOREIGN
        }
        assert any(found.values()), (
            "no word is accepted capitalised but rejected lower-case, in any "
            f"of {self.FOREIGN}. Either the trap is gone -- in which case "
            "_accepts_lowercase's reason for existing needs rewriting, not "
            f"deleting -- or the oracle is not answering. Found: {found}"
        )

    def test_capitalising_never_makes_the_checker_STRICTER(self):
        """The trap is one-directional, which is why lowering is the fix.

        If some word were accepted lower-case but rejected capitalised,
        then lowering would introduce false accepts of its own and
        _accepts_lowercase would be trading one bias for another.
        MEASURED: zero such words, in all four languages.
        """
        oracle = T._oracle()
        backwards = {
            lang: [w for w in self.PROBE
                   if oracle.accepts(w.lower(), lang)
                   and not oracle.accepts(w, lang)]
            for lang in self.FOREIGN
        }
        assert not any(backwards.values()), (
            "a word is accepted lower-case but rejected capitalised, so "
            "lowering is not a strictly-safer question to ask: "
            f"{backwards}"
        )

    def test_the_code_never_asks_the_checker_about_a_capitalised_form(self,
                                                                      monkeypatch):
        """The defence itself, pinned WITHOUT depending on the OS.

        The two tests above describe the world; this one describes our
        code, so it keeps testing the thing that matters on a machine
        whose dictionaries answer differently.
        """
        asked: list = []

        class _Spy:
            def accepts(self, word, lang):
                asked.append(word)
                return False

        monkeypatch.setattr(T, "_ORACLE", _Spy())
        T._accepts_lowercase("Stochastic", ("de", "fr"))
        T._accepts_lowercase("MARTINGALE", ("de",))
        T._accepts_lowercase("Brownian", T.ENGLISH)
        assert asked, "the spy was never consulted; the test proves nothing"
        assert all(w == w.lower() for w in asked), (
            f"the checker was asked about a capitalised form: {asked}"
        )

    @pytest.mark.parametrize("word", [
        "behavior", "behaviour", "modeling", "modelling", "color", "colour",
        "analyse",
    ])
    def test_a_word_in_ONE_english_variant_counts_as_english(self, word):
        """ENGLISH is ('en', 'en_GB'), so the quantifier over it matters.

        Found by mutating _accepts_lowercase: changing ``any`` to ``all``
        survived the whole suite. It is not a dead branch -- MEASURED,
        macOS 26.6, every transatlantic pair splits across the two
        dictionaries:

            behavior   en=True  en_GB=False
            behaviour  en=False en_GB=True

        so under ``all`` NEITHER spelling is English, and
        suggestion_is_cross_language stops firing for precisely the words
        _SENTINELS_CLEAN was built from. The rule would go quiet rather
        than go wrong, which is the failure mode this suite exists for.
        """
        assert T._accepts_lowercase(word, T.ENGLISH) is True

    def test_membership_uses_the_lowercase_form_only(self):
        assert T._accepts_lowercase("stochastic", ("de",)) is False
        assert T._accepts_lowercase("Stochastic", ("de",)) is False
        assert T._accepts_lowercase("stochastic", T.ENGLISH) is True

    @pytest.mark.parametrize("word,suggestion,langs,cross", [
        ("stochastik", "stochastic", {"de"}, True),
        ("bayésien", "bayesian", {"fr"}, True),
        ("multivariée", "multivariate", {"fr"}, True),
        ("ergodicité", "ergodicity", {"fr"}, True),
        # ...but these partners are themselves French, so the pair is a
        # misspelling and not a language correspondence
        ("aspets", "aspects", {"fr"}, False),
        ("inforamtion", "information", {"fr"}, False),
        ("oprérateurs", "opérateurs", {"fr"}, False),
        # an English title has no foreign language to appeal to
        ("wiith", "with", set(), False),
    ])
    def test_cross_language_is_judged_on_the_suggestion(self, word, suggestion,
                                                        langs, cross):
        assert T.suggestion_is_cross_language(
            word, suggestion, frozenset(langs)) is cross


class TestTheCandidateNeverVotesOnItsOwnLanguage:

    def test_the_candidate_is_excluded_from_the_vote(self):
        """A title must not be able to declare itself foreign on the
        strength of the one word being questioned. "Résolution" is
        French-only, so counting it would make a single-word title
        French and suppress its own candidate."""
        assert T.title_languages(["Résolution"], "résolution") == frozenset()
        assert T.title_languages(["Résolution", "problème"],
                                 "résolution") == frozenset({"fr"})

    def test_a_foreign_tie_still_counts_as_foreign(self):
        """Equal evidence either way is not evidence of English. The
        suppression is conservative by design: it downgrades to UNKNOWN,
        never to CLEAN."""
        langs = T.title_languages(["stochastic", "Lehramt"], "stochastik")
        assert langs == frozenset({"de"})


class TestTheUnsupportedLanguageThresholdIsPinnedFromBothSides:
    """A single threshold needs two tests or it can drift either way.

    Measured on the real queue: Latin and Czech titles score 0.44-1.00 on
    "share of words no dictionary knows", while English titles carrying a
    genuine typo top out at 0.25 — and that worst case is a
    series-prefixed filename whose author block lands on the title side
    of the first " - ".
    """

    def test_a_latin_title_just_over_the_line_is_suppressed(self):
        """Latin scores 0.44, not 1.00 — the maths fragments and the few
        Latin words English happens to know drag it down. A threshold set
        loosely enough to miss this lets every Latin title through."""
        tokens = ["Methodus", "facilis", "inueniendi", "Integrale", "huius",
                  "formulae", "the", "of", "and", "integral"]
        assert T.title_is_unsupported_language(tokens, "integrationem")

    def test_an_english_title_with_several_surnames_is_NOT_suppressed(self):
        """The series-prefix case: "Astérisque 210 - Robbiano, L., Zuily,
        C. - Analytic theorry..." splits on the FIRST " - ", so the author
        surnames end up counted as title words no dictionary knows. A
        threshold set tightly enough to catch that would silence real
        typos in perfectly ordinary English titles."""
        tokens = ["Robbiano", "Zuily", "Hörmander", "Kyprianou", "Pihlsgård",
                  "Analytic", "for", "the", "quadratic", "scattering",
                  "problem", "with", "smooth", "data", "and", "some"]
        # 4 of 16 words unknown to every dictionary — 0.25, the measured
        # worst case for an English title, and the number that decides
        # where the threshold can sit. Dropping it to 0.15 silences this.
        assert not T.title_is_unsupported_language(tokens, "theorry")
