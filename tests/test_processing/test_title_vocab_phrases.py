"""The owner's ruling on a multi-word name — and the "no" the store lacked.

Before ``decide_phrase`` existed the only durable primitive was
``decide(word, "proper"|"common")``: a POSITIVE ruling on a SINGLE word.
A refusal was modelled as an unticked Streamlit checkbox living in
session state, so it evaporated on reload and the identical proposal came
back on the next sweep.  The fifteen phrase rulings already on disk had
no writer at all — they could only be maintained by hand-editing JSON.

Every "must not" below is a way that store can lose a decision.
"""
from __future__ import annotations

import json
import unicodedata

import pytest

from processing.title_vocab import (
    decide,
    decide_phrase,
    load_vocab,
    phrase_rulings,
    record_pending,
    vocab_path,
)


@pytest.fixture
def lib(tmp_path):
    """A library whose vocabulary already holds rulings of every kind."""
    p = vocab_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "proper": ["Brownian"],
        "common": ["session"],
        "phrases": ["American Mathematical Monthly",
                    "Centro Internazionale Matematico Estivo",
                    "Euro-Par", "S-Plus"],
        "pending": {"Radon": {"count": 3, "example": "a title"}},
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def on_disk(lib) -> dict:
    """Read the file itself — not the API, which could be lying."""
    return json.loads(vocab_path(lib).read_text(encoding="utf-8"))


class TestARulingIsRecorded:

    def test_keeping_a_phrase_puts_it_on_disk(self, lib):
        assert decide_phrase(lib, "Lévy Matters", keep=True) is True
        assert "Lévy Matters" in on_disk(lib)["phrases"]
        assert "Lévy Matters" in phrase_rulings(lib)

    def test_revoking_a_phrase_removes_it_from_disk(self, lib):
        assert decide_phrase(lib, "Euro-Par", keep=False) is True
        assert "Euro-Par" not in on_disk(lib)["phrases"]

    def test_the_return_value_is_not_the_evidence(self, lib):
        """A neutered implementation could return True and write nothing.

        Assert against the bytes on disk, every time.
        """
        before = vocab_path(lib).read_text(encoding="utf-8")
        decide_phrase(lib, "New Journal Of Physics", keep=True)
        assert vocab_path(lib).read_text(encoding="utf-8") != before

    def test_a_no_op_reports_no_change(self, lib):
        assert decide_phrase(lib, "S-Plus", keep=True) is False
        assert decide_phrase(lib, "Never Ruled Before", keep=False) is False


class TestRevocationIsCaseInsensitive:
    """The whole point of a phrase ruling is to fix its CASING, so the
    phrase and its lowercase form are the same ruling with opposite
    answers.  Matching case-sensitively would leave both on disk and the
    owner's reversal would appear to do nothing.
    """

    @pytest.mark.parametrize("spelling", [
        "centro internazionale matematico estivo",
        "CENTRO INTERNAZIONALE MATEMATICO ESTIVO",
        "Centro Internazionale Matematico Estivo",
    ])
    def test_any_casing_revokes_the_one_ruling(self, lib, spelling):
        assert decide_phrase(lib, spelling, keep=False) is True
        assert not [x for x in on_disk(lib)["phrases"]
                    if x.lower().startswith("centro")]

    def test_re_ruling_replaces_rather_than_duplicates(self, lib):
        decide_phrase(lib, "euro-par", keep=True)
        phrases = on_disk(lib)["phrases"]
        assert [x for x in phrases if x.lower() == "euro-par"] == ["euro-par"]


class TestIdempotence:

    def test_keeping_twice_is_keeping_once(self, lib):
        decide_phrase(lib, "Annals Of Mathematics", keep=True)
        first = on_disk(lib)
        assert decide_phrase(lib, "Annals Of Mathematics", keep=True) is False
        assert on_disk(lib) == first

    def test_revoking_twice_is_revoking_once(self, lib):
        decide_phrase(lib, "S-Plus", keep=False)
        first = on_disk(lib)
        assert decide_phrase(lib, "S-Plus", keep=False) is False
        assert on_disk(lib) == first

    def test_keep_then_revoke_returns_to_the_start(self, lib):
        before = on_disk(lib)
        decide_phrase(lib, "Some Named Series", keep=True)
        decide_phrase(lib, "Some Named Series", keep=False)
        assert on_disk(lib) == before


class TestConservation:
    """A ruling must never cost a different ruling.  These are
    postconditions over the file, not over the code path taken.
    """

    def test_a_phrase_ruling_leaves_every_word_ruling_alone(self, lib):
        before = on_disk(lib)
        decide_phrase(lib, "Journal Of Fake Studies", keep=True)
        after = on_disk(lib)
        assert after["proper"] == before["proper"]
        assert after["common"] == before["common"]
        assert after["pending"] == before["pending"]

    def test_a_word_ruling_leaves_every_phrase_ruling_alone(self, lib):
        """``_save`` rebuilds the whole payload from the in-memory dict.

        If ``load_vocab`` ever stops returning "phrases", this write path
        silently rewrites the file with ``"phrases": []`` and fifteen of
        the owner's decisions are gone with no error anywhere.
        """
        before = on_disk(lib)["phrases"]
        decide(lib, "Radon", "proper")
        assert on_disk(lib)["phrases"] == before

    def test_recording_pending_words_leaves_phrase_rulings_alone(self, lib):
        before = on_disk(lib)["phrases"]
        record_pending(lib, ["Wiener", "Doob"], example="some title")
        assert on_disk(lib)["phrases"] == before

    def test_every_ruling_in_a_long_run_is_still_there_at_the_end(self, lib):
        """Twelve consecutive atomic rewrites of the same file.

        Reading it back as JSON each time only proves nothing raised, so
        assert the accumulating CONTENT: every phrase ruled so far must
        be present after every write, and the word rulings must survive
        all twelve.
        """
        expected = set(on_disk(lib)["phrases"])
        for i in range(12):
            decide_phrase(lib, f"Series Number {i}", keep=True)
            expected.add(f"Series Number {i}")
            payload = json.loads(vocab_path(lib).read_text(encoding="utf-8"))
            assert set(payload["phrases"]) == expected, f"lost a ruling at step {i}"
            assert payload["proper"] == ["Brownian"]
            assert payload["common"] == ["session"]


class TestItRefusesRatherThanPretending:

    @pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
    def test_an_empty_phrase_raises_for_BEING_EMPTY(self, lib, bad):
        """Asserting only that ValueError came out lets the empty guard be
        deleted with the suite still green: an empty string has zero
        letter-runs, so the single-word guard raises in its place and the
        owner is told his empty input is "a single word".

        Same trap as ``problems()`` in math_typography — "it said
        something" is not "it said the right thing".
        """
        with pytest.raises(ValueError, match="empty"):
            decide_phrase(lib, bad, keep=True)

    @pytest.mark.parametrize("bad", ["Brownian", "  Radon ", "Mathematik"])
    def test_a_single_word_raises_and_names_the_right_api(self, lib, bad):
        with pytest.raises(ValueError, match="single word"):
            decide_phrase(lib, bad, keep=True)

    @pytest.mark.parametrize("ok", ["Euro-Par", "S-Plus", "New York",
                                    "Lévy Matters", "Crux Mathematicorum"])
    def test_two_letter_runs_is_enough_even_without_a_space(self, lib, ok):
        """Counting SPACES would reject "Euro-Par" and "S-Plus" — the two
        rulings that settle the hyphen-versus-en-dash question, i.e. the
        exact cases this store exists for."""
        decide_phrase(lib, ok, keep=True)
        assert ok in phrase_rulings(lib)

    def test_a_phrase_spanning_the_author_title_separator_raises(self, lib):
        with pytest.raises(ValueError, match="separator"):
            decide_phrase(lib, "Carmona, R. A. - Statistical analysis",
                          keep=True)

    def test_a_bad_phrase_changes_nothing_on_disk(self, lib):
        before = vocab_path(lib).read_text(encoding="utf-8")
        for bad in ("", "Brownian", "A - B"):
            with pytest.raises(ValueError):
                decide_phrase(lib, bad, keep=True)
        assert vocab_path(lib).read_text(encoding="utf-8") == before


class TestUnicodeAndCaching:

    def test_decomposed_input_rules_the_composed_phrase(self, lib):
        """macOS hands filenames over in NFD.  A ruling entered from a
        filename must match one entered by typing, or the owner rules the
        same name twice and neither fires."""
        nfd = unicodedata.normalize("NFD", "Lévy Matters")
        decide_phrase(lib, nfd, keep=True)
        stored = on_disk(lib)["phrases"]
        assert "Lévy Matters" in stored
        assert unicodedata.normalize("NFC", "Lévy Matters") in stored
        assert decide_phrase(lib, "Lévy Matters", keep=True) is False

    def test_two_rulings_in_the_same_mtime_tick_both_survive(self, lib):
        """``load_vocab`` caches on (path, mtime).  A coarse filesystem
        timestamp means a second write inside the same tick can be served
        a STALE cache and silently drop the first ruling."""
        decide_phrase(lib, "First Ruling Here", keep=True)
        decide_phrase(lib, "Second Ruling Here", keep=True)
        stored = on_disk(lib)["phrases"]
        assert "First Ruling Here" in stored, "the first ruling was lost"
        assert "Second Ruling Here" in stored

    def test_a_revocation_survives_a_reload(self, lib):
        """The bug this whole API exists to fix: a refusal that lives in
        memory is not a refusal."""
        decide_phrase(lib, "Centro Internazionale Matematico Estivo",
                      keep=False)
        import processing.title_vocab as tv
        tv._VOCAB_CACHE.clear()
        assert not [x for x in load_vocab(lib)["phrases"]
                    if x.lower().startswith("centro")]


class TestMissingOrCorruptStore:

    def test_a_ruling_can_be_made_in_a_library_with_no_vocab_file(self, tmp_path):
        assert decide_phrase(tmp_path, "Brand New Series", keep=True) is True
        assert phrase_rulings(tmp_path) == ["Brand New Series"]

    def test_a_corrupt_store_does_not_swallow_the_ruling(self, tmp_path):
        p = vocab_path(tmp_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{not json at all", encoding="utf-8")
        decide_phrase(tmp_path, "Recovered Series", keep=True)
        assert "Recovered Series" in phrase_rulings(tmp_path)
