"""Moving a paper into a topic folder must not damage its name.

Three findings from an audit of every rename path, after the owner reported
that capitals are dropped systematically.

1. A COSMETIC RULE UPPER-CASED WHATEVER FOLLOWED IT. filename_normalizer
   rewrites "?—X" to "? X" and used ``m.group(2).upper()`` on the letter
   after the punctuation. It runs on EVERY ingest and every move, inside the
   bucket labelled "cosmetic — no word changes" that is ticked by default,
   and it corrupted exactly the identifiers the caser works hardest to keep:

       "work?—mlOSP"   ->  "work? MlOSP"
       "Really?—iOS"   ->  "Really? IOS"
       "cap!—p-adic"   ->  "cap! P-adic"

   MEASURED: 0 of the 25,252 in-scope filenames match the pattern today, so
   the exposure was on future arrivals — which is precisely the kind of bug
   that is cheap now and expensive later.

2. A MULTI-WORD PLACE NAME LOST ITS FIRST WORD. The casing census is
   per-word: it lowers "New" (233 lower-case uses in the library) while
   keeping "Brunswick". MEASURED on the current library: exactly 1 title of
   25,040 is damaged by a move, and this is it.

3. THE DOCSTRING DENIED THE BEHAVIOUR. file_into_topic said "The title is
   left untouched (title re-casing is unsafe to auto-apply)" while the code
   re-cased it — stale since 0efa47f. An audit looking for silent renames
   would have cleared the function on its word.
"""
import pytest

from processing.filename_normalizer import normalize_filename


def _lib():
    from core.config_paths import get_library_root
    return get_library_root()


# ------------------------------------------------- the cosmetic upper-case

@pytest.mark.parametrize("name,must_keep", [
    ("Smith, J. - Does it work?—mlOSP for American options.pdf", "mlOSP"),
    ("Smith, J. - Really?—iOS applications.pdf", "iOS"),
    ("Smith, J. - Mind the cap!—p-adic methods.pdf", "p-adic"),
    ("Smith, J. - Why?—q-Gaussian processes.pdf", "q-Gaussian"),
])
def test_the_punctuation_rule_does_not_raise_the_next_letter(name, must_keep):
    out = normalize_filename(name)
    assert must_keep in out, (
        f"a cosmetic rule upper-cased an identifier: {out!r}"
    )


def test_the_punctuation_rule_still_does_its_job():
    """The dash after ? or ! is still replaced by a space."""
    out = normalize_filename("Smith, J. - Does it work?—mlOSP now.pdf")
    assert "work? mlOSP" in out, out
    assert "—" not in out.split(" - ", 1)[1], out


def test_ordinary_prose_after_the_mark_IS_still_capitalised():
    """The rule was RIGHT for prose and only wrong for identifiers.

    "!" ends a sentence, so the next word begins one. An existing test has
    asserted this since the rule was written, and removing the capital
    outright broke it — the fix is a guard, not a deletion.
    """
    out = normalize_filename(
        "E. - Mind the cap!—constrained portfolio optimisation.pdf")
    assert "cap! Constrained portfolio" in out, out


def test_an_ordinary_sentence_is_unaffected():
    name = "Smith, J. - Does it work? A study of methods.pdf"
    assert normalize_filename(name) == name


# ------------------------------------------------ the multi-word place name

def test_the_one_title_a_move_used_to_damage():
    """THE REGRESSION, verbatim from the library."""
    from processing.move_normalizer import normalize_full_name
    n = ("Karatzas, I., Ocone, D. L. - Applied stochastic analysis. "
         "Proceedings of a US–French workshop, Rutgers university, "
         "New Brunswick, N.J., April 29–May 2, 1991.pdf")
    out, changed, _ = normalize_full_name(n, _lib())
    assert "New Brunswick" in out, out
    assert not changed, f"a move should now leave this name alone: {out!r}"


def test_the_phrase_entry_does_not_fire_on_ordinary_prose():
    """A phrase entry matches the phrase, not its first word.

    "New" alone must stay lower case — it is an ordinary word 233 times in
    this library, and a bare entry would have imposed a capital on all of
    them. That is the failure mode five shipped entries already had.
    """
    from processing.move_normalizer import normalize_full_name
    for name in ("A, B. - A new approach to pricing.pdf",
                 "A, B. - Some new methods in analysis.pdf"):
        out, _, _ = normalize_full_name(name, _lib())
        assert " new " in out, (
            f"a phrase entry must not raise its first word on its own: {out!r}"
        )
        assert " New " not in out, out


# ------------------------------------------------------ the stale docstring

def test_the_docstring_no_longer_denies_the_re_casing():
    """A docstring that contradicts the code is worse than none.

    It is what an auditor reads before deciding a function is safe.
    """
    import pathlib
    src = pathlib.Path("src/processing/publication_topic_router.py").read_text()
    i = src.index("def file_into_topic")
    doc = src[i:i + 3000]
    assert "The title is left untouched (title re-casing is unsafe to" not in doc, (
        "the docstring claims the title is untouched; the code re-cases it"
    )
    assert "re-cased where the safe-default caser is" in doc
