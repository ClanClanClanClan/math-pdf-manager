"""The author-surname authority: what it must fix, and what it must not touch.

A particle is capitalised when it is part of the surname and lower case
when it is a preposition ("Le Gall" is never "Gall"; "de Tocqueville" is
"Tocqueville").  The list lives in config/author_surnames.yaml and was
researched per person, because nationality is not recoverable from the
particle -- "da Prato" is Italian and takes a capital, "da Silva" is
Portuguese and does not.

THE PATHOLOGIES BELOW ARE ALL REAL FAILURE MODES OF THIS REPOSITORY:

* A rule reaching across the " - " separator. A spelling fix once searched
  the whole filename and rewrote the mathematician "Makovski" to
  "Markovski". An author rule that touched titles would be the same bug
  mirrored: "de", "le" and "van" are ordinary words in French and Dutch
  prose, and "le Monde" is a newspaper.
* Being derived from the particle instead of the person. "de Feo" and
  "de Vries" were both PROPOSED as changes by research and then refuted
  on re-checking -- the people here are Filippo de Feo and Casper/Martijn
  de Vries, who publish lower case. A rule keyed on "de" gets them wrong.
* Silent failure. A missing or broken config must disable the rule, not
  raise, and not half-apply.
"""
import unicodedata

import pytest

from processing.author_surnames import (
    canonicalise_authors,
    canonicalise_filename,
    load_map,
)
from processing.move_normalizer import normalize_authors_in_name


def _lib():
    from core.config_paths import get_library_root
    return get_library_root()


# ------------------------------------------------------- it does its job

@pytest.mark.parametrize("before,after", [
    ("el Karoui, N. - Backward SDEs.pdf", "El Karoui, N. - Backward SDEs.pdf"),
    ("le Gall, J.-F. - Random trees.pdf", "Le Gall, J.-F. - Random trees.pdf"),
    ("di Nunno, G. - Malliavin calculus.pdf", "Di Nunno, G. - Malliavin calculus.pdf"),
    ("da Prato, G. - Stochastic equations.pdf", "Da Prato, G. - Stochastic equations.pdf"),
    ("ben Arous, G. - Aging in spin glasses.pdf", "Ben Arous, G. - Aging in spin glasses.pdf"),
    ("del Moral, P. - Feynman-Kac formulae.pdf", "Del Moral, P. - Feynman-Kac formulae.pdf"),
])
def test_a_ruled_surname_is_capitalised(before, after):
    assert canonicalise_filename(before)[0] == after


def test_every_author_in_the_block_is_fixed():
    got, changed = canonicalise_filename(
        "el Karoui, N., le Gall, J.-F., di Nunno, G. - Three authors.pdf")
    assert changed
    assert got == "El Karoui, N., Le Gall, J.-F., Di Nunno, G. - Three authors.pdf"


def test_matching_ignores_case_and_emits_the_ruled_form():
    for variant in ("el karoui", "EL KAROUI", "El karoui", "eL kArOuI"):
        got, _ = canonicalise_filename(f"{variant}, N. - Paper.pdf")
        assert got.startswith("El Karoui, N."), got


def test_NFD_input_is_matched():
    """macOS hands out decomposed filenames."""
    nfd = unicodedata.normalize("NFD", "le Guével, T. - A paper.pdf")
    got, changed = canonicalise_filename(nfd)
    assert changed and got.startswith("Le Guével"), got


# --------------------------------------------- THE TITLE IS NEVER TOUCHED

@pytest.mark.parametrize("name", [
    "Smith, J. - A study of le Gall trees and el Karoui theory.pdf",
    "Smith, J. - On de Rham cohomology and van der Waerden's theorem.pdf",
    "Smith, J. - Analyse de la mesure de le Cam.pdf",
    "Smith, J. - le Monde and other newspapers.pdf",
])
def test_the_title_is_never_rewritten(name):
    got, changed = canonicalise_filename(name)
    assert got == name, f"an author rule reached into the title: {got!r}"
    assert not changed


def test_the_same_name_is_fixed_in_the_author_block_and_left_in_the_title():
    """The scope IS the rule. Both halves in one filename."""
    got, _ = canonicalise_filename(
        "le Gall, J.-F. - A remark on le Gall trees.pdf")
    assert got == "Le Gall, J.-F. - A remark on le Gall trees.pdf", got


# ------------------------------------------- prepositions must not change

@pytest.mark.parametrize("name", [
    "von Neumann, J. - Theory of games.pdf",          # German
    "van der Vaart, A. W. - Asymptotic statistics.pdf",  # Netherlands Dutch
    "dos Reis, G. - Some results on BSDEs.pdf",       # Portuguese
    "da Silva, A. - A paper.pdf",                     # Portuguese
    "de la Peña, V. H. - Decoupling.pdf",             # Spanish
    "de Finetti, B. - Theory of probability.pdf",     # Italian noble predicate
])
def test_a_preposition_is_left_alone(name):
    assert canonicalise_filename(name)[0] == name


@pytest.mark.parametrize("name", [
    "de Feo, F. - Optimal control of delayed SDEs.pdf",
    "de Vries, C. G. - Tail estimation.pdf",
])
def test_the_two_REFUTED_names_are_not_in_the_list(name):
    """Research proposed both and adversarial re-checking killed both.

    Keeping them out is the whole value of the verify pass; a regression
    here means someone re-derived the list from the particle.
    """
    assert canonicalise_filename(name)[0] == name


# --------------------------------------------------------- shape and scope

def test_a_surname_not_followed_by_initials_is_not_a_surname_here():
    """The library's shape is "Surname, I. I.". Without initials it is prose."""
    got, changed = canonicalise_filename("le Gall and friends - A paper.pdf")
    assert got == "le Gall and friends - A paper.pdf"
    assert not changed


def test_a_name_with_no_separator_is_untouched():
    n = "el Karoui lecture notes.pdf"
    assert canonicalise_filename(n) == (n, False)


def test_a_longer_surname_is_not_matched_by_a_shorter_ruling():
    n = "le Gallois, P. - A paper.pdf"
    assert canonicalise_filename(n)[0] == n


def test_applying_it_twice_changes_nothing_more():
    once, c1 = canonicalise_filename("el Karoui, N. - Paper.pdf")
    twice, c2 = canonicalise_filename(once)
    assert c1 and not c2 and once == twice


# ------------------------------------------------------- failure is silent

def test_a_missing_config_disables_the_rule_rather_than_raising(tmp_path):
    assert load_map(tmp_path / "nope.yaml") == {}
    assert canonicalise_authors("el Karoui, N.", table={}) == ("el Karoui, N.", False)


def test_a_malformed_config_disables_the_rule_rather_than_raising(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("author_surnames: [this is not a mapping\n")
    assert load_map(bad) == {}


# ------------------------------------------------------ the wired-in path

def test_the_move_path_applies_it():
    """It must be reached by normalize_authors_in_name, not only directly.

    The commonest author block in this library is already correctly
    spaced, which takes an early return before the filename checker; a
    surname fix hung off the checker would reach almost nothing.
    """
    got, changed = normalize_authors_in_name(
        "el Karoui, N., Peng, S. - Backward SDEs in finance.pdf")
    assert changed
    assert got.startswith("El Karoui, N., Peng, S. - "), got


def test_the_move_path_still_leaves_titles_alone():
    n = "Smith, J. - A study of le Gall trees.pdf"
    got, _ = normalize_authors_in_name(n)
    assert got == n, got


# ------------------------------------------------------------- the list

def test_the_list_never_maps_a_name_to_itself():
    """A no-op entry is a rule that cannot fire — it hides a typo."""
    table = load_map()
    assert table, "the shipped config failed to load"
    bad = [(k, v) for k, v in table.items() if k == v.casefold() and k == v]
    assert not bad, f"entries that change nothing: {bad}"


#: Entries that deliberately RESPELL rather than only re-case. Each one
#: needs a reason here, because the default must stay "a capitalisation
#: authority does not silently respell people".
RESPELLINGS = {
    # "Onoforio" is a metathesis of "Onofrio" and is not a surname in any
    # authority file. The error is inherited from Elsevier's own Crossref
    # record for this exact DOI (10.1016/0362-546x(90)90131-y); the same
    # metadata batch mangled the co-authors to "Dellantonio" and
    # "Donofrrio". Person: Biancamaria D'Onofrio, Sapienza.
    "d'onoforio": "D'Onofrio",
    # The interior capital C-caron is correct in no romanisation system.
    # MathSciNet prints "Gal\\cprime chuk" (= Gal'chuk) on his
    # Russian-journal records; ASCII "ch" also matches the library's other
    # Russian names. Person: Leonid I. Gal'chuk, Moscow State / Strasbourg.
    "gal'čuk": "Gal'chuk",
    # Not a respelling of the letters but of their ARRANGEMENT: the elided
    # "het" belongs before the t. Karel in 't Hout, Antwerp -- confirmed
    # against his homepage, ORCID, arXiv, zbMATH, LC and GND.
    "in t'hout": "in 't Hout",
}


def test_every_entry_only_changes_case_or_joining_not_letters():
    """A capitalisation authority must not silently respell anyone.

    Guards against a research error becoming a spelling change: the
    letters, ignoring case, spaces and hyphens, must survive. A genuine
    correction of a misspelling is allowed, but only by being written
    down in RESPELLINGS with its evidence -- so a NEW one still fails
    here rather than slipping in behind this one.

    The apostrophe is normalised away before comparing, because U+2019 to
    U+0027 is a character-policy change (docs 3.13) and not a respelling.
    """
    from processing.apostrophes import fold_marks
    table = load_map()
    for k, v in table.items():
        if RESPELLINGS.get(k) == v:
            continue
        a = fold_marks(k).replace(" ", "").replace("-", "")
        b = fold_marks(v.casefold()).replace(" ", "").replace("-", "")
        assert a == b, (
            f"entry rewrites letters, not just case: {k!r} -> {v!r}. "
            f"If that is deliberate, add it to RESPELLINGS with the evidence.")


def test_every_declared_respelling_is_actually_in_the_list():
    """The allowlist must not outlive the entry it excuses.

    Without this, removing an entry from the YAML leaves a permanent
    licence in the test for a name that is no longer ruled.
    """
    table = load_map()
    for k, v in RESPELLINGS.items():
        assert table.get(k) == v, (
            f"RESPELLINGS excuses {k!r} -> {v!r}, which is not in the "
            f"shipped list any more (found {table.get(k)!r})")


# ---------------------------------------------------------------------------
# The three mutants that survived the first version of this file.
# Each one is a rule the file NAMED but did not actually exercise.
# ---------------------------------------------------------------------------

def test_a_title_that_ITSELF_contains_a_surname_and_initials_is_untouched():
    """M1. The " - " split is load-bearing, and nothing here proved it.

    Every title fixture above happened to contain no "Surname, I." shape,
    so the surname regex found nothing in them and the tests passed even
    when the rule was applied to the WHOLE filename. A festschrift or a
    memorial title carries exactly that shape, and there the split is the
    only thing standing between the rule and the title.
    """
    # The title must contain the FULL shape the surname regex looks for:
    # a comma-space, then the name, then trailing initials. "a tribute to
    # le Gall, J.-F." is NOT enough -- "le Gall" there is preceded by
    # "to ", so the regex never matches it and the mutant survives. It
    # took two attempts to write a fixture that actually reaches the
    # guard; the shape below is verbatim what a Selecta or a memorial
    # volume title looks like.
    n = "Smith, J. - Essays for Yor, M., le Gall, J.-F. and others.pdf"
    got, changed = canonicalise_filename(n)
    assert got == n, f"the rule rewrote a name inside the TITLE: {got!r}"
    assert not changed


def test_the_author_block_is_fixed_even_when_the_title_holds_the_same_shape():
    """The other half: the split must not disable the rule either."""
    got, changed = canonicalise_filename(
        "le Gall, J.-F. - In memory of le Cam, L. and his work.pdf")
    assert changed
    assert got == "Le Gall, J.-F. - In memory of le Cam, L. and his work.pdf", got


def test_a_comma_alone_does_not_make_something_a_surname():
    """M2. The trailing-initials lookahead is what defines "a surname here".

    The earlier fixture ("le Gall and friends") contained no comma at
    all, so a mutant that dropped the lookahead still matched nothing.
    A comma followed by ordinary prose is the case that distinguishes.
    """
    # Tested on canonicalise_authors directly: inside a title the " - "
    # split already protects it, which masked the missing lookahead.
    block = "Yor, M., le Gall, and others"
    got, changed = canonicalise_authors(block)
    assert got == block, f"a comma was mistaken for an author boundary: {got!r}"
    assert not changed


def test_a_config_key_written_in_NFD_still_matches(tmp_path):
    """M5. macOS makes NFD easy to introduce by hand-editing the config.

    The shipped file is NFC throughout, so dropping the normalisation of
    the KEYS changed nothing and the mutant survived. The guard exists
    for the next person who edits the list in a macOS editor.
    """
    cfg = tmp_path / "surnames.yaml"
    nfd_key = unicodedata.normalize("NFD", "le guével")
    cfg.write_text(f'author_surnames:\n  "{nfd_key}": "Le Guével"\n',
                   encoding="utf-8")
    table = load_map(cfg)
    assert table, "the temp config did not load"
    got, changed = canonicalise_authors("le Guével, T.", table=table)
    assert changed and got == "Le Guével, T.", got
