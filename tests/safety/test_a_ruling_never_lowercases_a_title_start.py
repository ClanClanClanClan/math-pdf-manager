"""A phrase ruling spelled in lower case must not lower-case a title's start.

THE DEFECT, measured through the real renamer before the fix (2026-10-07).
With "de Rham" ruled, ``normalize_full_name`` turned

    De Rham–Hodge–Kodaira’s decomposition on an abstract Wiener space
 -> de Rham–Hodge–Kodaira’s decomposition on an abstract Wiener space

and "“De Rham” revisited" into "“de Rham” revisited". The caser's own
first-word capitalisation does NOT rescue it: a ruled span is protected
from re-casing, which is right everywhere except the one place where
sentence case outranks the ruling. That had to be measured rather than
assumed -- the original "1 file would break" figure came from the
cockpit's preview function, not from the renamer.

The preview was wrong in the same direction (it offered that file as
needing a fix), and it was a SEPARATE copy of the matching rule: the
renamer lowercased by hand and folded eight dashes, the preview used
re.IGNORECASE and folded three. Fixing one would not have fixed the
other. There is now one matcher, ``processing.phrase_impact.occurrences``,
and ``test_there_is_one_matcher_not_two`` fails if the namer grows its
own again.

DIFFERENTIAL before shipping: the renamer's output for all 25,247
in-scope filenames was byte-identical before and after (no ruling in
force today starts in lower case), and 116 of those names pass through
the phrase pass, so the comparison exercised it rather than skipping it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from processing import phrase_impact, title_normalize
from processing.move_normalizer import normalize_full_name
from processing.phrase_impact import (
    DASH_FOLD_SET,
    already_correct,
    impact,
    occurrences,
    would_change,
)
from processing.title_vocab import vocab_path

RULINGS = ["de Rham", "van der Waerden", "Takagi–van der Waerden", "Euro-Par"]


@pytest.fixture
def lib(tmp_path):
    """A library whose owner has ruled on the phrases above.

    The census is empty, so nothing is provably common and the caser
    preserves every capital it is not told to change -- which makes these
    tests about the PHRASE pass alone.

    MEASURED on the pre-fix code, through normalize_full_name:
      * "De Rham–Hodge…"         -> "de Rham–Hodge…"          (broken)
      * "“De Rham” revisited"     -> "“de Rham” revisited"      (broken)
      * "Van der Waerden’s …"     -> "van der Waerden’s …"      (broken)
      * "İstanbul … takagi-van der waerden …" -> UNCHANGED: the ruling
        silently did nothing, because the hand-lowercased copy was one
        code point longer than the title and the boundary check read
        the wrong character
      * U+2010/2011/2012/2015 in "Euro‑Par": renamer rewrote, preview
        said "nothing to fix" -- the two copies disagreed
    The mid-title and capital-initial tests PASS on the old code too, by
    design: they pin what the fix must not take away.
    """
    p = vocab_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"proper": [], "common": [], "phrases": RULINGS}),
                 encoding="utf-8")
    return tmp_path


def _title(name: str, lib) -> str:
    new, _, _ = normalize_full_name(name, lib)
    return new.split(" - ", 1)[1]


# ------------------------------------------------------------ the defect

def test_the_measured_file_keeps_its_capital(lib):
    n = ("Aida, S. - De Rham–Hodge–Kodaira’s decomposition on an abstract "
         "Wiener space.pdf")
    assert _title(n, lib).startswith("De Rham–Hodge"), _title(n, lib)


@pytest.mark.parametrize("opener,closer", [("", ""), ("“", "”"), ("‘", "’")])
def test_an_opening_quote_does_not_make_the_start_mid_title(lib, opener, closer):
    """Sentence-initial means "no letter or digit before it", so a title
    opening with a quotation is still at its start."""
    n = f"Aida, S. - {opener}De Rham{closer} revisited.pdf"
    out = _title(n, lib)
    assert "De Rham" in out and "de Rham" not in out, out


def test_a_number_before_the_phrase_means_it_is_NOT_the_start(lib):
    """"Start" means no LETTER OR DIGIT precedes it. In "2 De Rham
    currents" the sentence begins with "2", so the name keeps its own
    lower case -- a guard that only looked for letters would exempt it."""
    assert _title("Aida, S. - 2 De Rham currents.pdf", lib) == "2 de Rham currents.pdf"


def test_another_lowercase_ruling_is_protected_the_same_way(lib):
    n = "Aida, S. - Van der Waerden’s theorem on arithmetic progressions.pdf"
    out = _title(n, lib)
    assert out.startswith("Van der Waerden"), out


# ------------------------------------------------- what must NOT change

@pytest.mark.parametrize("lead", ["On ", "A note on ", "Remarks on "])
def test_mid_title_the_lowercase_ruling_still_governs(lib, lead):
    """The guard is an exemption at the START, not a weakening of the
    ruling. "On De Rham cohomology" is still corrected."""
    n = f"Aida, S. - {lead}De Rham cohomology.pdf"
    assert f"{lead}de Rham cohomology" in _title(n, lib)


def test_a_capital_initial_ruling_still_applies_at_the_start(lib):
    """The guard is for rulings spelled in lower case ONLY. A guard that
    exempted every title start would leave this broken."""
    n = "Aida, S. - takagi-van der waerden function.pdf"
    assert _title(n, lib).startswith("Takagi–van der Waerden"), _title(n, lib)


# ------------------------------------------- the preview agrees with it

def test_the_preview_does_not_offer_a_title_start_as_a_fix(lib):
    n = "Aida, S. - De Rham–Hodge–Kodaira’s decomposition.pdf"
    assert not would_change(n, "de Rham")
    assert impact([n], "de Rham") == []
    # Exempt: neither wrong nor "already correct" -- the ruling does not
    # govern that span at all.
    assert already_correct([n], "de Rham") == 0


#: Written out by hand, NOT drawn from DASH_FOLD_SET. A first draft
#: parametrised over the constant itself, and a mutation that narrowed the
#: constant back to the old three marks did not fail a single test: it
#: silently deleted four test cases (25 -> 21) instead. A test whose cases
#: come from the thing it tests cannot notice that thing shrinking.
EVERY_DASH_SEEN = ["-", "\u2013", "\u2014", "\u2010", "\u2011", "\u2012",
                   "\u2015", "\u2212"]


def test_the_shared_dash_set_covers_every_mark_the_library_has_used():
    assert set(EVERY_DASH_SEEN) <= set(DASH_FOLD_SET), (
        f"missing: {sorted(f'U+{ord(c):04X}' for c in set(EVERY_DASH_SEEN) - set(DASH_FOLD_SET))}")


@pytest.mark.parametrize("dash", EVERY_DASH_SEEN)
def test_every_dash_the_renamer_folds_the_preview_folds_too(lib, dash):
    """Before unification the renamer folded eight dashes and the preview
    three, so a ruled phrase written with U+2010 HYPHEN was rewritten by
    one and invisible to the other."""
    n = f"Aida, S. - The Euro{dash}Par proceedings.pdf"
    renamer_changes = _title(n, lib) != n.split(" - ", 1)[1]
    preview_changes = would_change(n, "Euro-Par")
    assert renamer_changes == preview_changes == (dash != "-"), (
        f"dash U+{ord(dash):04X}: renamer={renamer_changes} "
        f"preview={preview_changes}")


def test_a_character_whose_lowercase_is_longer_does_not_shift_the_span(lib):
    """The renamer's old copy lowercased by hand. "İ".lower() is TWO code
    points, so every index after it was off by one and the rewrite landed
    on the wrong slice. The shared matcher uses re.IGNORECASE and never
    changes a length."""
    n = "Aida, S. - İstanbul lectures on the takagi-van der waerden function.pdf"
    out = _title(n, lib)
    assert "the Takagi–van der Waerden function" in out, out
    assert out.startswith("İstanbul lectures on the "), out


# ------------------------------------------------------------- structure

def test_there_is_one_matcher_not_two():
    """One rule, one implementation. The preview and the renamer must not
    be able to disagree about which spans a ruling governs."""
    assert title_normalize._ruling_spans is phrase_impact.occurrences
    assert title_normalize._DASH_FOLD_SET is phrase_impact.DASH_FOLD_SET
    src = Path(title_normalize.__file__).read_text(encoding="utf-8")
    assert "_dash_fold(" not in src, "the hand-lowercasing copy is back"


@pytest.mark.parametrize("prefix", ["", "“", "(", "« "])
def test_the_matcher_itself_exempts_only_lowercase_rulings_at_the_start(prefix):
    t = f"{prefix}De Rham and Takagi–van der Waerden"
    assert occurrences(t, "de Rham") == []
    assert occurrences(t, "Takagi–van der Waerden"), "capital ruling must match"
    mid = f"On {t}"
    assert occurrences(mid, "de Rham"), "mid-title the ruling governs"
