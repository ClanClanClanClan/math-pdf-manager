"""A mathematician's name in a title must survive sentence-casing.

THE PROBLEM. ``to_sentence_case_academic`` lowercases every capitalised word
it does not recognise, and no hand-curated whitelist holds every
mathematician. MEASURED over the 25,043 in-scope titles: 2,964 mid-title
capitals destroyed — Bourbaki 64, Fock 22, Landau 15, Azéma 13, Hartree 12,
Paley 12, Doeblin 9, Gronwall 8, plus Saint-Flour, Paris, Tōhoku and the
months.

THE SOURCE. The library already knows these names: every filename carries an
author block. ``processing.author_vocabulary`` mines 11,779 surnames from
them read-only, so a new eponym arrives with its first paper rather than with
a hand-edited config entry.

WHY IT IS NOT A WHITELIST ENTRY, which is the whole design. A
``capitalization_whitelist`` entry does not preserve — it IMPOSES. Matching is
case-insensitive and the entry's own spelling is emitted. Measured: the
shipped 848-entry list already imposes 263 wrong capitals ("sur le
grossissement" → "sur Le grossissement", 103 times), and feeding it the
11,779 mined surnames was measured at 5,823 imposed capitals. The rule here
is PRESERVE-ONLY: it fires only on an already-capitalised word and emits it
verbatim, so it cannot impose, cannot alter a character, cannot destroy a
title. That is structural, not a measurement to redo.

RESULT, measured end-to-end over all 25,043 titles: 1,042 capitals recovered
across 771 titles, 0 imposed, 0 newly lost, 0 titles destroyed, 0 errors.
"""
import json
import pathlib
import re
import unicodedata

import pytest

from core.sentence_case import to_sentence_case_academic
from processing.author_vocabulary import surnames, _NOT_SURNAMES, VOCAB_PATH


def _cased(title):
    out = to_sentence_case_academic(title)
    return out[0] if isinstance(out, tuple) else out


# ------------------------------------------------------------- the vocabulary

def test_the_vocabulary_exists_and_is_substantial():
    """A silently empty vocabulary would make every test below vacuous."""
    names = surnames()
    assert len(names) > 8000, len(names)
    assert all(n == n.lower() for n in names), "entries must be lowercase"


def test_a_missing_vocabulary_degrades_and_does_not_raise():
    """This runs inside a live Streamlit page.

    Missing vocabulary must mean "fewer capitals recovered", which is the
    behaviour before the rule existed — not a traceback that takes the
    cockpit down.
    """
    import processing.author_vocabulary as av
    saved, av._CACHE = av._CACHE, None          # bypass the module cache
    try:
        assert av.surnames(pathlib.Path("/nonexistent/nope.txt")) == set()
    finally:
        av._CACHE = saved

    # and the caser must still work, just without the recoveries
    saved, av._CACHE = av._CACHE, set()
    try:
        out = _cased("A note on the Doeblin condition")
    finally:
        av._CACHE = saved
    assert out == "A note on the doeblin condition", (
        f"an absent vocabulary must degrade to the old behaviour, not to a "
        f"traceback or to something new: {out!r}"
    )


@pytest.mark.parametrize("month", ["juillet", "mai", "août", "settembre",
                                   "dezember", "octubre"])
def test_foreign_months_are_not_in_the_surname_set(month):
    """"Juillet" is a real probabilist AND French for July.

    It produced 3 of the 4 measured errors of an earlier draft. An English
    dictionary cannot find these, which is why they are listed by hand.
    """
    assert month in _NOT_SURNAMES
    assert month not in surnames()


# ------------------------------------------------------------------ the rule

@pytest.mark.parametrize("title", [
    "The Bourbaki seminar on algebraic geometry",
    "A note on the Doeblin condition",
    "A Komlós dichotomy for the Émery topology",
    "A Morse theory for Hamiltonian systems",
    "Improved bounds on Bell numbers and moments of sums",
    "A new approach to optimal stopping for Hunt processes",
])
def test_an_eponym_keeps_its_capital(title):
    assert _cased(title) == title


@pytest.mark.parametrize("title", [
    "from a square root boundary condition",
    "the class of bell-shaped functions",
    "a toy model on a random graph",
    "un courant positif fermé",
])
def test_the_same_word_in_lower_case_is_left_alone(title):
    """PRESERVE-ONLY is what makes the surname list safe.

    "Root barrier" keeps its capital; "square root" never gains one. A
    whitelist entry could not do this — it would impose "Root" on both.
    """
    out = _cased(title)
    assert out.lower() == title.lower()
    assert out[1:] == title[1:], f"a capital was imposed: {out}"


def test_the_rule_cannot_impose_a_capital_on_a_name_it_knows():
    """The structural guarantee, scoped to the words this rule governs.

    Every word below is IN the mined surname set and appears here in lower
    case. Preserve-only means the rule must not touch them.

    Scoped deliberately: the shipped capitalization_whitelist separately
    imposes 263 capitals of its own ("sur le grossissement" -> "sur Le
    grossissement" 103 times, from a bare "Le" entry meant for Le Cam and
    Le Gall). That is a real pre-existing defect, it is recorded in
    docs/proper-nouns-measured.md, and it is NOT this rule's doing --
    asserting over it here would make this test fail for someone else's bug.
    """
    known = surnames()
    probes = [w for w in ("hunt", "root", "bell", "may", "ray", "price",
                          "gross", "abel", "lee", "morse") if w in known]
    assert len(probes) >= 5, f"vocabulary too thin to test: {probes}"
    for w in probes:
        t = f"a study of the {w} bound in probability"
        out = _cased(t)
        i = t.index(w)
        assert out[i] == w[0], f"imposed a capital on {w!r}: {out!r}"


# ------------------------------------------------------------------ the gate

def test_a_title_cased_input_is_not_rescued_by_the_rule():
    """THE HAZARD. On Title Cased input every word carries a capital and
    removing them is the caser's whole job.

    Measured on an oracle of 4,000 stored sentence-case titles, Title-Cased
    back: the rule ungated scored 3,179/4,000 with 997 wrong capitals; with
    this gate, 3,763/4,000 with 193 — the baseline exactly, +0 errors.
    """
    out = _cased("A Study Of The Wang Equation And The He Process In Sun Space")
    assert " he " in out, out
    assert " sun " in out, out


def test_a_title_whose_capitals_are_all_names_is_not_called_title_cased():
    """The "at least two non-surname capitals" clause.

    Without it, "Euler, Pisot, Prouhet–Thue–Morse, Wallis and the duplication
    of sines" reads as Title Cased — a title whose capitals are ALL names —
    and 29 correct recoveries were blocked.
    """
    from core.sentence_case import _title_is_title_cased
    from core.math_tokenization import robust_tokenize_with_math as tok
    t = "Euler, Pisot, Prouhet–Thue–Morse, Wallis and the duplication of sines"
    assert _title_is_title_cased(tok(t, set())) is not True, (
        "a title whose capitals are all names must not read as Title Cased"
    )
    # and the names the vocabulary knows are therefore recovered
    assert "Euler" in _cased(t), _cased(t)


def test_the_gate_reports_three_states():
    from core.sentence_case import _title_is_title_cased
    from core.math_tokenization import robust_tokenize_with_math as tok
    short = tok("Brownian motion", set())
    assert _title_is_title_cased(short) is None, "too short to judge"
    sent = tok("A note on the ergodic theorem for stationary processes", set())
    assert _title_is_title_cased(sent) is False
    titled = tok("A Study Of The Ergodic Theorem For Stationary Processes", set())
    assert _title_is_title_cased(titled) is True


# -------------------------------------------------------------- the compound

@pytest.mark.parametrize("title", [
    "A new proof of the Hartman-Wintner law of the iterated logarithm",
    "A game-theoretic proof of the Kolmogorov-Petrowsky test",
    "Another note on the Borel-Cantellu lemma",
    "A discussion of the papers by Pierre-André Chiappori",
    "On the Littlewood-Paley-Stein theory",
])
def test_a_name_compound_survives_whole(title):
    """Preserving only the recognised half is worse than preserving neither.

    MEASURED: the eponym rule alone took the count of compounds emerging as
    "Xxx-yyy" from 113 to 30 — but only because this rule was added. Without
    it the count rose instead, to 97: "Kolmogorov-petrowsky",
    "Hartman-wintner", "Pierre-andré". A half-cased name reads as a typo in
    a way an all-lowercase one does not.
    """
    assert _cased(title) == title


@pytest.mark.parametrize("title", [
    "A study of mean-field games and time-dependent controls",
    "On non-linear and semi-continuous operators",
])
def test_an_ordinary_hyphenated_phrase_is_untouched(title):
    """The dash signal is UNUSABLE alone — on any two capitals it fires on
    "Mean-Field", "Time-Dependent", "Non-Linear" and was measured at 3,029
    wrong capitals. It is safe here only because a component must be a known
    surname AND the title-case gate must also pass.
    """
    assert _cased(title) == title


def test_a_name_compound_in_a_title_cased_input_is_still_lowered():
    out = _cased("A Study Of The Mean-Field Wang Equation In Sun Space")
    assert "mean-field" in out, out


# ------------------------------------------------------------- the population

@pytest.mark.parametrize("word", ["Gaussiens", "Hamiltoniens"])
def test_french_adjectives_from_names_stay_lower_case(word):
    """"gaussiens" is a French adjective, not the name Gauss.

    These are the class the ANY-word variant of this rule would get wrong,
    and the reason it was not taken.
    """
    out = _cased(f"Processus {word.lower()} et martingales")
    assert word.lower() in out, out


def test_no_title_in_the_corpus_loses_a_character():
    fx = (pathlib.Path(__file__).resolve().parents[1]
          / "fixtures" / "math_regions_ground_truth.json")
    if not fx.exists():
        pytest.skip("corpus fixture unavailable — UNKNOWN, not OK")
    bad = []
    for row in json.loads(fx.read_text())["labelled"]:
        t = unicodedata.normalize("NFC", row["title"])
        if len(str(_cased(t))) < len(t):
            bad.append(t)
    assert not bad, bad[:5]


def test_this_rule_imposes_no_capital_anywhere_in_the_corpus():
    """The structural guarantee over 345 real titles.

    Compared against the caser WITHOUT the rule, not against the input, so
    the pre-existing whitelist impositions are not attributed here.
    """
    fx = (pathlib.Path(__file__).resolve().parents[1]
          / "fixtures" / "math_regions_ground_truth.json")
    if not fx.exists():
        pytest.skip("corpus fixture unavailable — UNKNOWN, not OK")
    import processing.author_vocabulary as av
    bad = []
    for row in json.loads(fx.read_text())["labelled"]:
        t = unicodedata.normalize("NFC", row["title"])
        with_rule = str(_cased(t))
        saved, av._CACHE = av._CACHE, set()          # disable the rule
        try:
            without = str(_cased(t))
        finally:
            av._CACHE = saved
        if not (len(with_rule) == len(without) == len(t)):
            continue
        # IMPOSED means the INPUT was lower case and we emitted upper. A
        # RECOVERED capital also reads lower->upper against the rule-disabled
        # output, which is why the input is the reference and not `without`.
        for i, (src, a, b) in enumerate(zip(t, without, with_rule)):
            if i == 0 or a == b:
                continue
            if src.islower() and src.upper() != src and b == src.upper():
                bad.append((t, with_rule, i))
                break
    assert not bad, bad[:5]


class TestTheBranchesMutationFound:
    """Cases the first draft of this file could not distinguish.

    Each test below kills a mutant that all 35 tests above survived. They are
    here because a mutation run named them, not because they were imagined.
    """

    def test_a_title_of_nothing_but_names_is_not_title_cased(self):
        """Kills: `return len(non_name_caps) >= 2` -> `return True`.

        The earlier test used "Euler, Pisot, Prouhet–Thue–Morse, Wallis and
        the duplication of sines", where only 50% of content words carry a
        capital — so it returned False at the ratio check and never reached
        this clause. This title clears 70%, so the clause is what decides it.
        """
        from core.sentence_case import _title_is_title_cased
        from core.math_tokenization import robust_tokenize_with_math as tok
        t = "Euler, Morse, Bourbaki and Doeblin"
        toks = tok(t, set())
        caps = [x.value for x in toks
                if x.kind == "WORD" and x.value[:1].isupper()]
        assert len(caps) >= 3, caps
        assert all(c.lower() in surnames() for c in caps[1:]), caps
        assert _title_is_title_cased(toks) is False, (
            "every capital here is a name, so this is a sentence-cased title "
            "that happens to be dense with names — not Title Case"
        )

    def test_a_capitalised_compound_of_non_names_is_not_preserved(self):
        """Kills: `if nxt.lower() in known:` -> `if True:`.

        The compound rule needs at least ONE component to be a name it knows.
        Without that clause it fires on any Xxx-Yyy, which is the design the
        decision measured at 3,029 wrong capitals on title-cased input.
        """
        assert "time-dependent" in _cased("A note on Time-Dependent operators")

    def test_a_compound_half_in_lower_case_does_not_carry_the_capital(self):
        """Kills: `if not nxt[:1].isupper(): break` -> `if False:`.

        "Hunt-processes" is a name glued to a common noun, not a compound of
        two names. Walking past the lowercase half would let any word next to
        a surname keep a capital it should not have.
        """
        out = _cased("A study of Hunt-Processes and their Semigroups")
        assert "Semigroups" not in out, out

    def test_a_regenerated_vocabulary_is_still_swept_for_months(self, tmp_path):
        """Kills BOTH month-filter mutants.

        The shipped file already has the months removed, so dropping the
        filter changes nothing about it — the branch is MASKED, not dead.
        It matters the moment the vocabulary is regenerated, which is the
        documented way to pick up new authors. So the test writes a file that
        contains the defect and asserts the loader still refuses it.
        """
        import processing.author_vocabulary as av
        bad = tmp_path / "vocab.txt"
        bad.write_text("# generated\njuillet\nmai\nsettembre\nbourbaki\n",
                       encoding="utf-8")
        saved, av._CACHE = av._CACHE, None
        try:
            names = av.surnames(bad)
        finally:
            av._CACHE = saved
        assert "bourbaki" in names, "a real name must survive the sweep"
        for month in ("juillet", "mai", "settembre"):
            assert month not in names, (
                f"{month} is a month in some language the library uses; "
                f"'Juillet' is also a real probabilist, which is exactly why "
                f"an English dictionary cannot settle it"
            )

    def test_the_mine_step_sweeps_months_too(self):
        """The other half: mine() must not emit them either."""
        import processing.author_vocabulary as av
        assert av._NOT_SURNAMES & {"juillet", "mai", "settembre", "dezember"}
        # mine() subtracts the same set; assert the subtraction is present
        # by checking the shipped artefact, which mine() produced.
        shipped = av.surnames()
        assert not (shipped & av._NOT_SURNAMES), sorted(shipped & av._NOT_SURNAMES)[:5]

    @pytest.mark.parametrize("title", [
        "Équations aux dérivées partielles, proceedings, Saint-Jean-de-Monts, 1977",
        "A note on the van der Waerden conjecture and Saint-Jean-de-Monts",
    ])
    def test_a_lower_case_particle_does_not_end_a_name(self, title):
        """Kills: the particle branch in _in_a_name_compound.

        FOUND BY MUTATION, and the mutant was RIGHT. A mutant that removed
        the lower-case guard entirely scored better on two of the three real
        titles it changed, because the guard was breaking the walk at the
        "de" of "Saint-Jean-de-Monts" and stranding "Monts" in lower case.
        French and Dutch names are full of these particles.
        """
        assert "Saint-Jean-de-Monts" in _cased(title), _cased(title)

    def test_a_lower_case_word_that_is_not_a_particle_still_ends_the_name(self):
        """The other side of it: only PARTICLES may be walked through."""
        out = _cased("A study of Hunt-and-Semigroups theory in probability")
        assert "Semigroups" not in out, out

    def test_the_titles_own_first_word_is_excluded_from_the_gate(self):
        """Kills: `if j == 0: continue` in _title_is_title_cased.

        The first word of a title is ALWAYS capitalised and therefore carries
        no signal about whether the title is Title Cased. Counting it inflates
        the capitalised fraction and can tip a sentence-cased title over the
        0.70 threshold, which switches the eponym rule off.

        MEASURED: removing this line changes 13 real library titles, every
        one for the worse -- "US–French" becomes "US–french",
        "Littlewood-Paley" becomes "Littlewood-paley", "Paul-André Meyer"
        becomes "paul-andré Meyer".
        """
        for title, must_keep in [
            ('Correction "Inégalités de Littlewood-Paley"', "Littlewood-Paley"),
            ("Disparition de Paul-André Meyer", "Paul-André"),
        ]:
            assert must_keep in _cased(title), _cased(title)

    def test_mine_sweeps_months_out_of_a_fresh_walk(self, tmp_path):
        """Kills: `return out - _NOT_SURNAMES` in mine().

        The shipped file was generated WITH the sweep, so dropping it from
        mine() cannot be seen by loading that file. This builds a two-file
        fake library instead. It never touches the real one.
        """
        import processing.author_vocabulary as av
        lib = tmp_path / "lib" / "01 - Published papers" / "J"
        lib.mkdir(parents=True)
        (lib / "Juillet, A. - On a transport problem.pdf").write_bytes(b"%PDF")
        (lib / "Bourbaki, N. - On a seminar.pdf").write_bytes(b"%PDF")
        (lib / "van der Waerden, B. L. - On an algebra.pdf").write_bytes(b"%PDF")
        mined = av.mine(tmp_path / "lib")
        assert "bourbaki" in mined, f"the miner found nothing usable: {mined}"
        assert "waerden" in mined, mined
        for particle in ("van", "der"):
            assert particle not in mined, (
                f"'{particle}' is a name PARTICLE, not a name. As a standalone "
                f"vocabulary entry it would preserve a capital on every "
                f"stray 'Van'/'Der' in a title. The miner takes only "
                f"capitalised tokens, which is what keeps them out."
            )
        assert "juillet" not in mined, (
            "a French month reached the vocabulary through an author block; "
            "'Juillet' is also a real probabilist, which is what makes this "
            "worth sweeping by hand"
        )

    def test_a_surname_the_library_uses_as_a_common_word_is_filtered_out(self):
        """The census filter, which is what makes the vocabulary safe.

        Someone is called Law, Price, Risk, Case and Root — all real author
        surnames in this library. But the library's own TITLES use those
        words in lower case: law 0 capitalised / 240 lower, risk 0/778,
        price 1/252, case 1/211, root 4/26. So the library itself says they
        are common words here, and the miner believes it.

        Without this, "Gauss's Law in electrostatics" kept its capital L.
        """
        known = surnames()
        for common in ("law", "price", "risk", "case", "root"):
            assert common not in known, (
                f"{common!r} is used in lower case in the library's own "
                f"titles; keeping it makes the rule capitalise ordinary prose"
            )
        for name in ("hunt", "ray", "morse", "abel", "gross", "bell", "may"):
            assert name in known, (
                f"{name!r} appears capitalised in real titles and never (or "
                f"rarely) in lower case — it must survive the filter"
            )

    def test_the_price_of_the_filter_is_recorded_not_hidden(self):
        """"Root barrier" is NOT recovered, and that is deliberate.

        "root" is a real author surname and "the Root barrier for Markov
        processes" is a real title, but the library writes "square root" 26
        times against 4 capitalised Roots. The census filter believes the
        library, so this recovery is given up to avoid capitalising "square
        Root". It is 4 occurrences of the 1,043.

        Pinned so the trade-off is visible: if someone later widens the
        filter, this test fails and asks them to decide again rather than
        letting the change pass unnoticed.
        """
        out = _cased("A free boundary characterisation of the Root barrier")
        assert "root barrier" in out, out
        assert "root" not in surnames()

    def test_gauss_law_is_not_capitalised(self):
        """The regression the full suite caught, pinned here too."""
        assert _cased("Gauss's Law in electrostatics") == \
            "Gauss's law in electrostatics"

    def test_the_census_filter_is_applied_during_mining(self, tmp_path):
        """A fake library where one surname is also a common title word."""
        import processing.author_vocabulary as av
        lib = tmp_path / "lib" / "01 - Published papers" / "L"
        lib.mkdir(parents=True)
        # "Law" is an author, but the titles use "law" as a common noun.
        (lib / "Law, S. - On the law of large numbers.pdf").write_bytes(b"%PDF")
        (lib / "Law, S. - Another law of iterated logarithm.pdf").write_bytes(b"%PDF")
        (lib / "Bourbaki, N. - On a seminar.pdf").write_bytes(b"%PDF")
        saved, av._CENSUS = av._CENSUS, None
        try:
            mined = av.mine(tmp_path / "lib")
        finally:
            av._CENSUS = saved
        assert "bourbaki" in mined, mined
        assert "law" not in mined, (
            "the titles use 'law' in lower case twice and never capitalised, "
            f"so it must not enter the vocabulary: {sorted(mined)}"
        )

    def test_the_census_keeps_a_name_used_mostly_as_a_name(self, tmp_path):
        """Kills: `lo == 0 or upper > lo` -> `lo == 0`.

        A name that appears in lower case even ONCE would be thrown away by
        the stricter rule. Measured on the real library that costs "May"
        (42 capitalised against 10 lower) and "Bell" (4 against 1) — the
        month in proceedings titles and Bell numbers. The majority rule
        keeps them.

        The shipped vocabulary file was generated with the real rule, so the
        stricter variant cannot be seen by loading it; this builds a library
        where the branch decides.
        """
        import processing.author_vocabulary as av
        lib = tmp_path / "lib" / "01 - Published papers" / "B"
        lib.mkdir(parents=True)
        for n, t in enumerate([
            "On Bell numbers and their asymptotics",
            "Another look at Bell numbers",
            "A study of the bell shaped density",
        ]):
            (lib / f"Bell, E. - {t}.pdf").write_bytes(b"%PDF")
        saved, av._CENSUS = av._CENSUS, None
        try:
            mined = av.mine(tmp_path / "lib")
        finally:
            av._CENSUS = saved
        assert "bell" in mined, (
            "capitalised twice against once in lower case — the library's own "
            f"usage says this is a name: {sorted(mined)}"
        )

    def test_the_census_ignores_the_titles_own_first_word(self, tmp_path):
        """Kills: `if m.start() == 0: continue` in _title_case_census.

        The first word of a title is always capitalised, so it is not
        evidence about anything. Counting it lets a word that is only ever
        title-initial look like a name.
        """
        import processing.author_vocabulary as av
        lib = tmp_path / "lib" / "01 - Published papers" / "S"
        lib.mkdir(parents=True)
        for t in [
            "Stability of the numerical scheme",      # title-initial capital
            "Stability results for a diffusion",      # title-initial capital
            "On the stability of solutions",          # mid-title, lower case
        ]:
            (lib / f"Stability, A. - {t}.pdf").write_bytes(b"%PDF")
        saved, av._CENSUS = av._CENSUS, None
        try:
            mined = av.mine(tmp_path / "lib")
        finally:
            av._CENSUS = saved
        assert "stability" not in mined, (
            "its only capitals are title-initial, which every title has; the "
            f"one piece of real evidence is lower case: {sorted(mined)}"
        )
