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


class TestIngestPerfectNaming:
    """The first filing applies the same safe formatting as a move."""

    def test_ingest_cases_title_and_queues_unknowns(self, tmp_path):
        from processing.identity import enable_sidecar_mirror
        from processing.ingest import ingest_paper
        for d in ["01 - Published papers", "12 - To be sorted"]:
            (tmp_path / d).mkdir(parents=True)
        enable_sidecar_mirror(tmp_path)
        src = tmp_path / "12 - To be sorted" / "drop.pdf"
        # Metadata title in Title Case with one unknown proper noun.
        _write_minimal_pdf(
            src, title="On The Existence Of Zorglub Solutions",
            author="Dalang, Robert Charles")
        r = ingest_paper(src, library_root=tmp_path, status="published",
                         dry_run=False, auto_topic=False)
        assert r["success"], r
        name = r["filename"]
        assert "R. C." in name                       # spaced initials at birth
        assert "the existence of" in name            # confident words downcased
        assert "Zorglub" in name                     # unknown preserved
        assert "Zorglub" in load_vocab(tmp_path)["pending"]   # ...and queued


class TestContextAwareCasing:
    """Stage 2.5 — context guards the unigram oracle cannot express.

    Every case below is a real shape mined from the owner's library (or the
    exact regression it caused), so the thresholds stay pinned to evidence
    rather than to taste.
    """

    # --- mixed-case identifiers: upcasing the first letter CORRUPTS a name
    @pytest.mark.parametrize("title", [
        "mlOSP, towards a unified implementation of regression Monte Carlo",
        "iOS and Android numerical libraries",
        "arXiv preprints and their citation half-life",
    ])
    def test_mixed_case_first_word_never_upcased(self, title):
        assert propose_title_case(title).proposed == title

    def test_lowercase_first_word_still_upcased(self):
        # The guard must not disable ordinary sentence-start capitalisation.
        p = propose_title_case("space–time stochastic calculus and white noise")
        assert p.proposed == "Space–time stochastic calculus and white noise"

    # --- embedded titles opened by a SPACE-SEPARATED quote ("« Notes …")
    def test_spaced_opening_quote_preserves_embedded_title(self):
        t = "Présentation du texte « Notes historiques sur le calcul » de Cauchy"
        assert propose_title_case(t).proposed == t

    def test_hugging_opening_quote_still_preserves(self):
        # The word right after the quote opens an embedded title and keeps its
        # capital; the REST of that title is sentence-cased as usual.
        p = propose_title_case("On the “Existence Theorem” of Peano")
        assert "“Existence" in p.proposed

    # --- capital-run coherence: never half-lowercase a possible proper phrase
    def test_run_with_unknown_neighbour_is_preserved_whole(self):
        # "Calculus" is unknown, so lowercasing only "Stochastic" would emit
        # the incoherent "and stochastic Calculus".
        t = "Brownian Motion and Stochastic Calculus"
        p = propose_title_case(t)
        assert p.proposed == t
        assert "Stochastic" in p.uncertain          # queued for one ruling

    def test_french_institution_run_preserved(self):
        t = "Mathematics and the École des Hautes Études en Sciences Sociales"
        assert propose_title_case(t).proposed == t

    def test_known_name_plus_common_noun_still_downcases(self):
        # The dominant maths shape: a KNOWN proper noun followed by ordinary
        # nouns must keep lowercasing — this is what the run rule must not eat.
        assert propose_title_case(
            "Lectures on Hilbert Space Methods"
        ).proposed == "Lectures on Hilbert space methods"
        assert propose_title_case(
            "Optimal transport on Wasserstein Space"
        ).proposed == "Optimal transport on Wasserstein space"

    def test_long_title_cased_run_is_not_treated_as_a_phrase(self):
        # One unknown word must not veto casing a Title-Cased sentence.
        p = propose_title_case("On The Existence Of Zorglub Solutions")
        assert p.proposed == "On the existence of Zorglub solutions"

    def test_function_words_downcase_even_inside_a_run(self):
        # Function words are lowercase inside genuine proper names too
        # ("United States of America"), so the run rule never promotes them.
        p = propose_title_case("A study of The Zorglub Of Mathematics")
        assert " of " in p.proposed and " The " not in p.proposed

    def test_united_states_not_broken(self):
        t = "Optimal investment in the United States"
        assert propose_title_case(t).proposed == t


class TestContextGuardsWithVocabulary:
    """Guards exercised through the PRODUCTION path (a real library_root).

    The plain ``propose_title_case(title)`` calls above classify with only the
    built-in lists; the sweep always passes a library so the owner's vocabulary
    and the corpus oracle take part.  Several real regressions were invisible
    until the vocabulary was in play, so these pin that path explicitly.
    """

    @staticmethod
    def _lib(tmp_path, *, common=(), proper=()):
        import json
        cfg = tmp_path / ".mathpdf-config"
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "title_vocab.json").write_text(json.dumps({
            "proper": list(proper), "common": list(common), "pending": {},
        }))
        return tmp_path

    def test_name_particle_is_never_promoted_by_a_capital_run(self, tmp_path):
        # "von/de/van" are lowercase INSIDE a genuine proper name, exactly like
        # "of" in "United States of America".  A run with an unknown surname
        # ("Mises") must not promote the particle back to a capital.
        lib = self._lib(tmp_path, common=["von"])
        p = propose_title_case("Using Von Mises' axiom of randomness", lib)
        assert "von Mises" in p.proposed

    def test_known_proper_member_vetoes_run_preservation(self, tmp_path):
        # Hilbert is a KNOWN name, so the phrase is the ordinary
        # <Name> + <common nouns> shape and must still sentence-case, even
        # though "Reproducing"/"Kernel" are unknown.
        lib = self._lib(tmp_path, common=["space"], proper=["Hilbert"])
        p = propose_title_case("Studies on Reproducing Kernel Hilbert Space", lib)
        assert p.proposed.endswith("Hilbert space")

    def test_acronym_first_word_does_not_block_subtitle_casing(self, tmp_path):
        # "HANK," must not read as a proper phrase to the comma-adjacency rule,
        # or the subtitle after the comma stops being sentence-cased.
        lib = self._lib(tmp_path, common=["heterogeneous"])
        p = propose_title_case("HANK, Heterogeneous agent new Keynesian models", lib)
        assert p.proposed.startswith("HANK, heterogeneous")

    def test_closing_straight_quote_does_not_preserve_next_word(self, tmp_path):
        # A token-final straight quote is nearly always the CLOSING one.
        lib = self._lib(tmp_path, common=["estimates"])
        p = propose_title_case('A note on the "local time" Estimates for X', lib)
        assert '"local time" estimates' in p.proposed


class TestCasingIsReproducible:
    """Filename casing must not depend on PYTHONHASHSEED.

    The whitelist stores case variants of the same term ("G-expectation" and
    "g-expectation"); picking the winner by set-iteration order made the result
    differ between PROCESSES, so a rename preview and the later apply could
    disagree.  The owner's own spelling wins, deterministically.
    """

    def test_author_spelling_wins_over_other_case_variant(self):
        from core.sentence_case import to_sentence_case_academic
        assert to_sentence_case_academic("g-expectation theory")[0] == "g-expectation theory"
        assert to_sentence_case_academic("G-expectation theory")[0] == "G-expectation theory"

    def test_repeated_calls_agree(self):
        from core.sentence_case import to_sentence_case_academic
        out = {to_sentence_case_academic("Peng g-expectations and BSDEs")[0] for _ in range(25)}
        assert len(out) == 1


class TestPublisherBoilerplate:
    """A PDF saved from a publisher's landing page carries THAT PAGE's
    title in its metadata, so the journal/volume/publisher tail would be
    baked straight into the filename.  Measured on the real staging
    inbox: 15% of proposed names carried such a tail before this guard.
    """

    @pytest.mark.parametrize("raw,expected", [
        ("Optimal control of the running max | SIAM Journal on Control and "
         "Optimization | Vol. 29, No. 4 | Society for Industrial and Applied "
         "Mathematics", "Optimal control of the running max"),
        ("On the asymptotic behavior of local times | Theory of Probability "
         "& Its Applications", "On the asymptotic behavior of local times"),
        ("Conditional systemic risk measures | SIAM Journal on Financial "
         "Mathematics | Vol. 12, No. 4", "Conditional systemic risk measures"),
    ])
    def test_journal_tail_is_dropped(self, raw, expected):
        from processing.ingest import _strip_publisher_boilerplate
        assert _strip_publisher_boilerplate(raw) == expected

    @pytest.mark.parametrize("title", [
        "A simple proof of the theorem",                 # no pipe at all
        "Estimating P | Q divergence in high dimensions",  # maths, not a journal
        "P | Q",                                          # head too short
    ])
    def test_genuine_titles_survive(self, title):
        from processing.ingest import _strip_publisher_boilerplate
        assert _strip_publisher_boilerplate(title) == title


class TestAttentionHumanLabel:
    """The attention queue showed bare arXiv ids ("2607.13547v1"), which a
    human cannot make a filing decision from."""

    def test_canonical_stem_is_used_as_is(self, tmp_path):
        from ui.attention_queue import human_label
        p = tmp_path / "Dalang, R. C. - Level sets of the Brownian sheet.pdf"
        p.write_bytes(b"%PDF-1.4\n")
        assert human_label(p).startswith("Dalang, R. C. - ")

    def test_bare_identifier_falls_back_to_stem_not_crash(self, tmp_path):
        # No sidecar and no canonical stem: must still return something
        # printable rather than raising inside the queue.
        from ui.attention_queue import human_label
        p = tmp_path / "2607.13547v1.pdf"
        p.write_bytes(b"%PDF-1.4\n")
        assert human_label(p) == "2607.13547v1"
