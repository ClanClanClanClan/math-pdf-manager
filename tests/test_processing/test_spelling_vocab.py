"""Rulings on suspected misspellings.

The failure this store exists to prevent is the one the title-review
screen had: an approval kept in Streamlit session state, lost on browser
reload, so the identical proposal came back on the next sweep and the
owner re-decided the same word forever.
"""
from __future__ import annotations

import json
import unicodedata

import pytest

from maintenance.typos import build_corpus_stats, examine_title, Verdict
from processing.spelling_vocab import (
    CORRECT,
    DEFERRED,
    TYPO,
    accepted_words,
    clear_ruling,
    load_rulings,
    rule,
    ruling_for,
    rulings_path,
)


def on_disk(lib) -> dict:
    """Read the file itself — not the API, which could be lying."""
    return json.loads(rulings_path(lib).read_text(encoding="utf-8"))


class TestARulingSticks:

    def test_it_reaches_the_disk_not_just_memory(self, tmp_path):
        rule(tmp_path, "Volterra", CORRECT)
        assert "volterra" in on_disk(tmp_path)[CORRECT]

    def test_it_survives_a_reload(self, tmp_path):
        rule(tmp_path, "Volterra", CORRECT)
        assert accepted_words(tmp_path) == frozenset({"volterra"})

    def test_it_lives_in_the_library_so_dropbox_syncs_it(self, tmp_path):
        rule(tmp_path, "Volterra", CORRECT)
        assert rulings_path(tmp_path).is_relative_to(tmp_path)
        assert ".mathpdf-config" in str(rulings_path(tmp_path))

    @pytest.mark.parametrize("spelling", ["Volterra", "VOLTERRA", "volterra",
                                          "  Volterra  "])
    def test_a_word_is_the_same_word_however_it_is_typed(self, tmp_path,
                                                         spelling):
        rule(tmp_path, spelling, CORRECT)
        assert ruling_for(tmp_path, "vOlTeRrA") == CORRECT

    def test_decomposed_input_rules_the_composed_word(self, tmp_path):
        """macOS hands filenames over in NFD; a ruling entered from one
        must match a ruling typed by hand, or the owner rules twice and
        neither fires."""
        rule(tmp_path, unicodedata.normalize("NFD", "zakaï"), CORRECT)
        assert ruling_for(tmp_path, "zakaï") == CORRECT


class TestOneRulingPerWord:

    def test_re_ruling_replaces_rather_than_accumulates(self, tmp_path):
        rule(tmp_path, "wiith", DEFERRED)
        rule(tmp_path, "wiith", TYPO, "with")
        d = on_disk(tmp_path)
        assert "wiith" not in d[DEFERRED]
        assert d[TYPO]["wiith"] == "with"

    def test_a_word_cannot_be_both_correct_and_a_typo(self, tmp_path):
        rule(tmp_path, "wiith", CORRECT)
        rule(tmp_path, "wiith", TYPO, "with")
        assert "wiith" not in on_disk(tmp_path)[CORRECT]
        assert ruling_for(tmp_path, "wiith") == TYPO


class TestDeferringIsNotForgiving:
    """Putting a word off does not make it right, and the conformance
    report must keep saying so. Only an explicit "this is a real word"
    silences the detector."""

    def test_deferred_words_are_not_accepted(self, tmp_path):
        rule(tmp_path, "zakaï", DEFERRED)
        assert accepted_words(tmp_path) == frozenset()

    def test_only_correct_suppresses_detection(self, tmp_path):
        names = [f"A. - stochastic processes {i}" for i in range(30)]
        names += ["B. - stochstic control theory"]
        title = "B. - stochstic control theory"

        rule(tmp_path, "stochstic", DEFERRED)
        stats = build_corpus_stats(names, accepted_words(tmp_path))
        assert examine_title(title, stats).verdict is Verdict.TYPO

        rule(tmp_path, "stochstic", CORRECT)
        stats = build_corpus_stats(names, accepted_words(tmp_path))
        assert examine_title(title, stats).verdict is Verdict.CLEAN


class TestEveryRulingHasARouteBack:

    def test_a_ruling_can_be_undone(self, tmp_path):
        rule(tmp_path, "Volterra", CORRECT)
        assert clear_ruling(tmp_path, "Volterra") is True
        assert ruling_for(tmp_path, "Volterra") == ""

    def test_undoing_something_unruled_reports_that_honestly(self, tmp_path):
        rule(tmp_path, "Volterra", CORRECT)
        assert clear_ruling(tmp_path, "never-ruled") is False

    def test_undo_leaves_other_rulings_alone(self, tmp_path):
        rule(tmp_path, "Volterra", CORRECT)
        rule(tmp_path, "wiith", TYPO, "with")
        clear_ruling(tmp_path, "Volterra")
        assert on_disk(tmp_path)[TYPO] == {"wiith": "with"}


class TestItRefusesRatherThanPretending:

    @pytest.mark.parametrize("bad", ["", "   ", "\t"])
    def test_an_empty_word_raises(self, tmp_path, bad):
        with pytest.raises(ValueError, match="empty"):
            rule(tmp_path, bad, CORRECT)

    def test_an_unknown_kind_raises(self, tmp_path):
        with pytest.raises(ValueError, match="kind"):
            rule(tmp_path, "wiith", "probably-fine")

    def test_confirming_a_typo_without_the_correction_raises(self, tmp_path):
        """"This is wrong" with no "and this is right" leaves a queue
        entry nobody can act on."""
        with pytest.raises(ValueError, match="correction"):
            rule(tmp_path, "wiith", TYPO)

    def test_a_refused_ruling_writes_nothing(self, tmp_path):
        rule(tmp_path, "Volterra", CORRECT)
        before = rulings_path(tmp_path).read_text(encoding="utf-8")
        for args in (("", CORRECT), ("x", "nonsense"), ("y", TYPO)):
            with pytest.raises(ValueError):
                rule(tmp_path, *args)
        assert rulings_path(tmp_path).read_text(encoding="utf-8") == before


class TestTheStoreDoesNotEatData:

    def test_an_unknown_key_survives_a_write(self, tmp_path):
        """_save rebuilds the whole payload. If a future version adds a
        key and an older build then writes, the key must not vanish —
        exactly the shape that would have wiped fifteen phrase rulings
        out of title_vocab."""
        p = rulings_path(tmp_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({CORRECT: ["volterra"],
                                 "future_feature": {"a": 1}}),
                     encoding="utf-8")
        rule(tmp_path, "wiith", TYPO, "with")
        assert on_disk(tmp_path)["future_feature"] == {"a": 1}
        assert "volterra" in on_disk(tmp_path)[CORRECT]

    def test_a_corrupt_store_degrades_instead_of_raising(self, tmp_path):
        """An unreadable ruling file must not stop the owner seeing his
        queue."""
        p = rulings_path(tmp_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{not json", encoding="utf-8")
        assert accepted_words(tmp_path) == frozenset()
        rule(tmp_path, "Volterra", CORRECT)
        assert accepted_words(tmp_path) == frozenset({"volterra"})

    def test_a_missing_store_is_empty_not_an_error(self, tmp_path):
        assert load_rulings(tmp_path)[CORRECT] == set()
        assert accepted_words(tmp_path) == frozenset()
