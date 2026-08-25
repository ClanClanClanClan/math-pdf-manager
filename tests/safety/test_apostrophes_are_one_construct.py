"""The two apostrophes must behave alike, and a capital after one is a name.

THE ORIGINAL DEFECT. ``_SEGMENT_RE``'s character class, in BOTH
core/math_tokenization.py and core/tokenization.py, read ``['']`` -- which
is U+0027 twice and U+2019 never. So "don't" was one WORD token and "don’t"
was three. 1,116 library titles use U+0027 and 444 use U+2019, so the same
construct cased two different ways depending on which key was pressed.

WHY THE OBVIOUS FIX WAS REJECTED FIRST. Adding U+2019 to the class was
measured as a NET REGRESSION -- 27 filename proposals better, 21 worse. It
was not the class fix that was wrong. Joining "BSDE’s" into one token hid
the acronym from the acronym branch, which looked at the whole token; and
joining "d’Iwasawa" exposed it to a lowercasing rule that had never had to
handle it. Two latent bugs, revealed rather than caused.

WHAT THE LIBRARY ACTUALLY CONTAINS, measured over 25,049 in-scope titles:

    1,645  apostrophe + lower-case tail     user's, Itô's, König's
      104  apostrophe + Capitalised word    d'Azéma, l'Hôpital, 'Tis
        4  apostrophe + single capital      l'X, d'A. Garsia, 'N
        3  apostrophe + ALL-CAPS run        d'EDP, d'EDS
        0  apostrophe + capital S           (the English possessive)
        0  all-capitals titles

Every one of the 111 capitals is a name or a quoted title. And of the 702
capitalised-head possessives, 154 were being lowercased outright --
könig's, varadhan's, zvonkin's, gronwall's, tsirel'son, possamaï's.

RESULT, measured through core.sentence_case.to_sentence_case_academic over
all 25,049: 287 original capitals recovered, 0 lost, 0 titles destroyed.
"""
import json
import pathlib
import unicodedata

import pytest

from core.sentence_case import to_sentence_case_academic
from core.math_tokenization import robust_tokenize_with_math
from core import tokenization as _plain_tokenization


def _cased(title):
    out = to_sentence_case_academic(title)
    return out[0] if isinstance(out, tuple) else out


STRAIGHT, CURLY = "'", "’"


# ---------------------------------------------------- the class itself

@pytest.mark.parametrize("word", [
    "don{a}t", "D{a}Alembert", "d{a}Itô", "König{a}s",
    "l{a}Hôpital", "Solov{a}ev", "BSDE{a}s",
])
def test_both_apostrophes_tokenise_identically(word):
    """THE REGRESSION. The same construct, two spellings, one answer."""
    a = robust_tokenize_with_math(word.format(a=STRAIGHT), set())
    b = robust_tokenize_with_math(word.format(a=CURLY), set())
    assert [t.kind for t in a] == [t.kind for t in b], (
        f"{word.format(a=STRAIGHT)!r} and {word.format(a=CURLY)!r} tokenise "
        f"differently: {[(t.kind, t.value) for t in a]} vs "
        f"{[(t.kind, t.value) for t in b]}"
    )
    assert len(a) == 1 and a[0].kind == "WORD"


def test_the_character_class_holds_both_apostrophes_in_both_modules():
    """A grep-level guard: the duplicate was invisible by eye.

    ``['']`` and ``['’']`` look nearly identical in a terminal. The bug
    survived because nobody could see it, so this asserts on codepoints.
    """
    import re as _re
    for mod in (robust_tokenize_with_math.__module__, _plain_tokenization.__name__):
        src = pathlib.Path("src/" + mod.replace(".", "/") + ".py").read_text()
        for line in src.splitlines():
            if "?P<WORD>" in line or "?P<PUNCT>" in line:
                # Only the pattern, not the trailing comment -- the comment
                # says "that's", and counting its apostrophe made the first
                # version of this test fail against correct code.
                pattern = line.split("#", 1)[0]
                cps = [ord(c) for c in pattern if ord(c) in (0x27, 0x2019)]
                assert 0x2019 in cps, f"U+2019 missing in {mod}: {line.strip()}"
                assert cps.count(0x27) == 1, (
                    f"U+0027 appears {cps.count(0x27)} times in {mod} -- the "
                    f"original bug was the same character listed twice"
                )


def test_a_non_ascii_tail_survives_the_word():
    """The tail class was ``[a-zA-Z]+``, so "d'Itô" split at the "ô"."""
    toks = robust_tokenize_with_math("d" + STRAIGHT + "Itô", set())
    assert len(toks) == 1 and toks[0].value == "d" + STRAIGHT + "Itô"


# ------------------------------------------- a capital after an apostrophe

@pytest.mark.parametrize("title,expected", [
    ("Calcul d{a}Itô étendu", "Calcul d{a}Itô étendu"),
    ("Deux théorèmes d{a}Abel sur la convergence",
     "Deux théorèmes d{a}Abel sur la convergence"),
    ("Théorie d{a}Iwasawa", "Théorie d{a}Iwasawa"),
    ("A propos de la formule d{a}Azéma-Yor",
     "A propos de la formule d{a}Azéma-Yor"),
    ("Les clefs pour l{a}X", "Les clefs pour l{a}X"),
    ("Les méthodes d{a}A. Garsia en théorie des martingales",
     "Les méthodes d{a}A. Garsia en théorie des martingales"),
])
@pytest.mark.parametrize("ap", [STRAIGHT, CURLY])
def test_french_elision_keeps_the_name_capital(title, expected, ap):
    """d' and l' are prepositions; the capital belongs to the mathematician."""
    assert _cased(title.format(a=ap)) == expected.format(a=ap)


@pytest.mark.parametrize("title", [
    "{a}Tis an equity puzzlement",
    "{a}Finem Lauda{a} or the risks in swaps",
])
@pytest.mark.parametrize("ap", [STRAIGHT, CURLY])
def test_an_opening_quote_keeps_the_quoted_capital(title, ap):
    t = title.format(a=ap)
    assert _cased(t)[:6] == t[:6], _cased(t)


# ------------------------------------------------ the possessive eponym

@pytest.mark.parametrize("name", [
    "König", "Varadhan", "Zvonkin", "Gronwall", "Yosida", "Alekseev",
    "Cramér", "Doeblin", "Sklar", "Zermelo", "Possamaï",
])
@pytest.mark.parametrize("ap", [STRAIGHT, CURLY])
def test_a_mathematicians_possessive_keeps_its_capital(name, ap):
    """154 of these were being lowercased, whitelist or not."""
    title = f"A note on {name}{ap}s theorem"
    assert _cased(title) == title


@pytest.mark.parametrize("ap", [STRAIGHT, CURLY])
def test_a_transliterated_soft_sign_keeps_its_capital(ap):
    for name in (f"Tsirel{ap}son", f"Solov{ap}ev"):
        title = f"The {name} equation"
        assert _cased(title) == title


@pytest.mark.parametrize("ap", [STRAIGHT, CURLY])
def test_an_acronym_possessive_keeps_its_acronym(ap):
    """Joining the token hid BSDE from the acronym branch."""
    for acr in ("BSDE", "SPDE", "PDE", "ODE"):
        title = f"On {acr}{ap}s and their applications"
        assert acr in _cased(title), _cased(title)


def test_the_english_possessive_is_not_treated_as_a_name():
    """THE ONE PLACE PRESERVING WOULD BE WRONG.

    An all-capitals title lowercases, and keeping that S would produce
    "author'S". Measured: this library has no "'S" and no all-caps title,
    so this fires nowhere today -- it is here because ingest takes titles
    from Crossref and arXiv.
    """
    assert _cased("THE AUTHOR'S THEOREM") == "The author's theorem"


def test_an_ordinary_possessive_is_untouched():
    assert _cased("Newton's law of cooling") == "Newton's law of cooling"
    assert _cased("A user's guide to the method") == \
        "A user's guide to the method"


# --------------------------------------------------------- the population

@pytest.mark.parametrize("ap", [STRAIGHT, CURLY])
def test_the_two_spellings_case_alike_on_every_corpus_title(ap):
    """The property, over 345 real titles: spelling must not change casing.

    Respelling every apostrophe one way or the other and casing both must
    give the same answer up to that respelling. This is the invariant the
    original class violated 1,560 times.
    """
    fx = (pathlib.Path(__file__).resolve().parents[1]
          / "fixtures" / "math_regions_ground_truth.json")
    if not fx.exists():
        pytest.skip("corpus fixture unavailable — UNKNOWN, not OK")
    other = CURLY if ap == STRAIGHT else STRAIGHT
    bad = []
    for row in json.loads(fx.read_text())["labelled"]:
        t = unicodedata.normalize("NFC", row["title"])
        if STRAIGHT not in t and CURLY not in t:
            continue
        one = t.replace(STRAIGHT, ap).replace(CURLY, ap)
        two = t.replace(STRAIGHT, other).replace(CURLY, other)
        if str(_cased(one)).replace(ap, "@") != str(_cased(two)).replace(other, "@"):
            bad.append(t)
    assert not bad, bad[:5]


def test_no_corpus_title_loses_a_capital_after_an_apostrophe():
    import re
    fx = (pathlib.Path(__file__).resolve().parents[1]
          / "fixtures" / "math_regions_ground_truth.json")
    if not fx.exists():
        pytest.skip("corpus fixture unavailable — UNKNOWN, not OK")
    pat = re.compile(r"['’][A-ZÀ-Þ]")
    bad = []
    for row in json.loads(fx.read_text())["labelled"]:
        t = unicodedata.normalize("NFC", row["title"])
        r = str(_cased(t))
        if len(r) != len(t):
            continue
        for m in pat.finditer(t):
            i = m.start() + 1
            if r[i] != t[i]:
                bad.append((t, r))
                break
    assert not bad, bad[:5]
