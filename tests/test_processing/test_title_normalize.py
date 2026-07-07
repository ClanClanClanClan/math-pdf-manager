"""Safe-default title casing + the owner vocabulary learning loop.

The invariant under test everywhere: NEVER lowercase a word that isn't
provably an ordinary common word — preserve and queue instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

from processing.title_normalize import propose_title_case
from processing.title_vocab import decide, load_vocab, record_pending


class TestProposer:

    def test_overcapitalized_common_words_fixed_confidently(self):
        p = propose_title_case(
            "On The Existence And Uniqueness Of Solutions")
        assert p.proposed == "On the existence and uniqueness of solutions"
        assert p.confident

    def test_unknown_names_preserved_and_queued(self):
        p = propose_title_case(
            "Seminar in honour of Stefano Franscini")
        assert "Stefano Franscini" in p.proposed        # untouched
        assert set(p.uncertain) == {"Stefano", "Franscini"}
        assert not p.confident

    def test_acronyms_and_mixed_case_never_touched(self):
        p = propose_title_case(
            "Reflected BSDEs driven by RCLL martingales and McKean–Vlasov limits")
        assert "BSDEs" in p.proposed and "RCLL" in p.proposed
        assert "McKean–Vlasov" in p.proposed

    def test_accented_words_never_touched(self):
        p = propose_title_case("Équations différentielles stochastiques")
        assert p.proposed == "Équations différentielles stochastiques"

    def test_sentence_start_after_period_is_preserved(self):
        p = propose_title_case(
            "Viscosity solutions and applications. Lectures given at the school")
        assert ". Lectures" in p.proposed               # not ". lectures"

    def test_geo_names_survive_dictionary_membership(self):
        # 'Italy'/'Germany' are dictionary words; the geo seed must keep them.
        p = propose_title_case(
            "Proceedings of the workshop, Konstanz, Germany, October 2000")
        assert "Germany" in p.proposed
        p2 = propose_title_case("Summer school held in Montecatini Terme, Italy, June 1995")
        assert "Italy" in p2.proposed

    def test_month_with_year_is_preserved(self):
        p = propose_title_case("Workshop in Ascona, May 2002")
        assert "May 2002" in p.proposed

    def test_math_prefix_first_word_stays(self):
        p = propose_title_case("p-adic Numbers")
        assert p.proposed == "p-adic numbers"

    def test_comma_adjacent_proper_phrase_promotes_to_uncertain(self):
        # 'Bath' is a dictionary word, but next to a proper neighbour across
        # a comma it must be preserved (and queued), not lowercased.
        # ('Nice, France' also survives, via the whitelist rather than the
        # promotion rule — both channels uphold the same invariant.)
        p = propose_title_case("Conference held in Bath, England")
        assert "Bath, England" in p.proposed
        assert "Bath" in p.uncertain
        p2 = propose_title_case("Conference held in Nice, France")
        assert "Nice, France" in p2.proposed


class TestVocabularyLoop:

    def test_pending_then_ruled_proper(self, tmp_path):
        record_pending(tmp_path, ["Zorglub"], example="Zorglub calculus.pdf")
        v = load_vocab(tmp_path)
        assert "Zorglub" in v["pending"]
        decide(tmp_path, "Zorglub", "proper")
        v = load_vocab(tmp_path)
        assert "Zorglub" in v["proper"] and "Zorglub" not in v["pending"]
        # Now the proposer is confident and preserves it.
        p = propose_title_case("A study of Zorglub calculus", tmp_path)
        assert "Zorglub" in p.proposed
        assert p.confident

    def test_pending_then_ruled_common(self, tmp_path):
        decide(tmp_path, "Gadget", "common")
        p = propose_title_case("Theory of the Gadget transform", tmp_path)
        assert "gadget" in p.proposed                   # ruled common -> lowered
        assert p.confident

    def test_reruling_moves_between_sets(self, tmp_path):
        decide(tmp_path, "Foo", "common")
        decide(tmp_path, "Foo", "proper")
        v = load_vocab(tmp_path)
        assert "Foo" in v["proper"] and "foo" not in v["common"]

    def test_corrupt_vocab_degrades_to_empty(self, tmp_path):
        from processing.title_vocab import vocab_path
        vp = vocab_path(tmp_path)
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text("{not json")
        v = load_vocab(tmp_path)
        assert v["proper"] == set() and v["pending"] == {}


class TestMoveIntegration:

    def test_normalize_full_name_fixes_authors_and_confident_title(self):
        from processing.move_normalizer import normalize_full_name
        new, changed, pending = normalize_full_name(
            "Dalang, R.C. - On The Existence Of Solutions.pdf")
        assert changed
        assert new == "Dalang, R. C. - On the existence of solutions.pdf"
        assert pending == []

    def test_uncertain_title_kept_verbatim_and_queued(self):
        from processing.move_normalizer import normalize_full_name
        new, changed, pending = normalize_full_name(
            "Smith, J. - Lectures at the Franscini institute.pdf")
        assert "Franscini" in new                        # preserved
        assert "Franscini" in pending

    def test_file_into_topic_applies_confident_title_fix(self, tmp_path):
        from processing.identity import enable_sidecar_mirror
        from processing.publication_topic_router import file_into_topic
        for d in ["01 - Published papers", "07a - BSDEs"]:
            (tmp_path / d).mkdir(parents=True)
        (tmp_path / "07a - BSDEs" / "01 - Published papers").mkdir(parents=True)
        enable_sidecar_mirror(tmp_path)
        src = (tmp_path / "01 - Published papers" / "S"
               / "Smith, J. - Reflected BSDEs And The Existence Of Solutions.pdf")
        src.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(src, title="t", author="Smith, J.")
        ok, msg = file_into_topic(src, "07a", tmp_path)
        assert ok, msg
        dest = (tmp_path / "07a - BSDEs" / "01 - Published papers" / "S"
                / "Smith, J. - Reflected BSDEs and the existence of solutions.pdf")
        assert dest.exists()

    def test_file_into_topic_queues_uncertain_words(self, tmp_path):
        from processing.identity import enable_sidecar_mirror
        from processing.publication_topic_router import file_into_topic
        for d in ["01 - Published papers", "07a - BSDEs"]:
            (tmp_path / d).mkdir(parents=True)
        (tmp_path / "07a - BSDEs" / "01 - Published papers").mkdir(parents=True)
        enable_sidecar_mirror(tmp_path)
        src = (tmp_path / "01 - Published papers" / "S"
               / "Smith, J. - Reflected BSDEs at the Franscini institute.pdf")
        src.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(src, title="t", author="Smith, J.")
        ok, msg = file_into_topic(src, "07a", tmp_path)
        assert ok, msg
        # Title kept verbatim (uncertain), and the word queued for review.
        dest = (tmp_path / "07a - BSDEs" / "01 - Published papers" / "S"
                / "Smith, J. - Reflected BSDEs at the Franscini institute.pdf")
        assert dest.exists()
        assert "Franscini" in load_vocab(tmp_path)["pending"]


class TestRealLibraryEdgeClasses:
    """Edge classes found by sweeping 2,500 real titles — each was a
    damage case in an earlier iteration; locked in here."""

    def test_quoted_embedded_title_preserved(self):
        p = propose_title_case(
            'A comment on the article "The harmonic descent chain" by authors')
        assert '"The harmonic' in p.proposed          # quote start untouched

    def test_leading_digits_consume_sentence_start(self):
        p = propose_title_case("25 years of local volatility and beyond")
        assert p.proposed.startswith("25 years")       # not "25 Years"

    def test_capitalized_possessive_is_eponym(self):
        # "Root's barrier": 'root' is corpus-common, but the possessive
        # capitalized form is an eponym — preserve + queue.
        p = propose_title_case("An integral equation for Root's barrier")
        assert "Root's" in p.proposed
        assert "Root" in p.uncertain

    def test_leading_particle_name_not_upcased(self):
        p = propose_title_case("de Finetti style theorems with applications")
        assert p.proposed.startswith("de Finetti")     # not "De Finetti"

    def test_internal_period_word_preserved_not_upcased(self):
        # "vs." is an abbreviation, not a sentence end — 'singular' must
        # NOT be upcased.
        p = propose_title_case("Stopper vs. singular-controller games")
        assert "vs. singular" in p.proposed
