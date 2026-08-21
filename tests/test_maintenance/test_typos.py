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
