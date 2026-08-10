"""The golden corpus: what the naming pipeline DOES, frozen in the repo.

The unit tests check that each rule does what it says. They cannot catch
the failure that actually keeps happening here — a change somewhere in
the pipeline quietly altering the output for a class of real filenames
nobody thought to write a test for. The library holds ~380 filenames
with mathematics in about two shapes, so sweeping it proves little, and
by the time a defect is visible it is already on disk.

So: every input below is run through the real pipeline and its output is
compared against a checked-in expectation file. Any change to any rule
that alters ANY of these fails loudly, and the only way to make it pass
is to edit the expectations — which puts the diff in front of a human in
the pull request, where it belongs.

    regenerate:  PYTHONPATH=src python3.12 -m tests.harness.golden --bless

Cases come from three places, and all three matter:
  * ``library`` — real filenames from the owner's 29k collection.
  * ``pathology`` — inputs no real file has yet: empty scripts, RTL,
    combining marks, nesting, 255-byte boundaries.
  * ``incident`` — every bug actually shipped, kept forever so it cannot
    return. Each carries the story of what went wrong.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

GOLDEN_PATH = Path(__file__).with_name("golden_expectations.json")


_FIXTURE_LIB = None


def _fixture_library() -> Path:
    """A throwaway library carrying the owner's FROZEN vocabulary.

    Running the pipeline with ``library_root=None`` is the mistake this
    project keeps making: the rulings live in the library, so a test
    without one silently exercises a different code path than production.
    It is exactly why the caser tests once passed while the phrase pass
    was inert, and the first version of this corpus froze "Euro–Par"
    unconverted without noticing.

    The vocabulary is COPIED into the repo rather than read from the real
    library, so the corpus stays hermetic and deterministic. The corpus
    word-statistics are deliberately absent — they change as the library
    grows, and drift there is the conformance check's job, not this one's.
    """
    global _FIXTURE_LIB
    if _FIXTURE_LIB is None:
        import tempfile
        d = Path(tempfile.mkdtemp(prefix="golden-lib-"))
        (d / ".mathpdf-config").mkdir(parents=True, exist_ok=True)
        src = Path(__file__).with_name("golden_vocab.json")
        if src.exists():
            (d / ".mathpdf-config" / "title_vocab.json").write_text(
                src.read_text())
        _FIXTURE_LIB = d
    return _FIXTURE_LIB


def pipeline(name: str) -> str:
    """The one true naming pipeline, exactly as a move or ingest runs it."""
    from processing.move_normalizer import normalize_full_name
    out, _changed, _pending = normalize_full_name(
        unicodedata.normalize("NFC", name), _fixture_library())
    return out


# ---------------------------------------------------------------------------
# Cases that are NOT drawn from the library
# ---------------------------------------------------------------------------
PATHOLOGIES: list = [
    # (input, why it is here)
    ("A, B. - L^2 estimates.pdf", "the simplest conversion"),
    ("A, B. - L^{2} estimates.pdf", "braces dropped for a single character"),
    ("A, B. - L^p solutions.pdf", "letter exponent"),
    ("A, B. - X_n converges.pdf", "subscript"),
    ("A, B. - Spaces \\mathbb{R}^d and \\mathbb{N}.pdf", "mathbb then exponent"),
    ("A, B. - The Kreps–Yan theorem for L^∞.pdf", "no superscript infinity"),
    ("A, B. - Local C^{0, α} estimates.pdf", "space stripped, alpha keeps LaTeX"),
    ("A, B. - A counterexample to C^{2, 1} regularity.pdf",
     "digits ARE representable but the comma is not: all-or-nothing"),
    ("A, B. - Σ_{i=1}^∞ expansions.pdf",
     "sibling scripts are atomic; ^∞ blocks the subscript from rising"),
    ("A, B. - Estimates in L^q spaces.pdf", "q has no superscript form"),
    ("A, B. - Another proof of e^{x:y}.pdf", "colon has no superscript form"),
    ("A, B. - On the expansion Σq^{−n_i}.pdf", "nested script: refuse"),
    ("A, B. - L_{exp_q}-summing norms.pdf", "nested script: refuse"),
    ("A, B. - C^{1, β) and W^{2, p} regularity.pdf",
     "brackets do not pair up: refuse the whole title"),
    ("A, B. - H_infty control theory.pdf",
     "bare _x must not eat one character of a longer word"),
    ("A, B. - PDEs on H²(e^(|x|²):4, ℝᵈ).pdf",
     "( opens a group, it is not a one-character exponent"),
    ("A, B. - HAL-A_stochastic_maximum_principle.pdf",
     "underscore as a word separator in a raw download name"),
    ("A, B. - Itô's formula for C^2 functions.pdf",
     "C^2 is a differentiability class; ℂ would be wrong"),
    ("A, B. - A lower bound for the Ramsey numbers R(3, k).pdf",
     "bare R is Ramsey, never ℝ"),
    ("A, B. - Monetary utility functions on C_b(X) spaces.pdf",
     "C_b is bounded continuous functions"),
    ("A, B. - Fractal properties with independent Q^*-digits.pdf",
     "star exponent has no Unicode form"),
    ("A, B. - Lᵖ-variation of BSDEs.pdf", "already Unicode: must be stable"),
    ("A, B. - A(t, Bₜ) is not a semimartingale.pdf",
     "space after a comma in a function argument is CORRECT typography"),
    ("A, B. - A bipolar theorem in L⁰(ℝᵈ;Ω, ℱ, ℙ).pdf",
     "the probability triple keeps its spaces"),
    ("A, B. - .pdf", "empty title"),
    ("A, B. - ^.pdf", "a lone caret"),
    ("A, B. - L^.pdf", "a base with a dangling caret"),
    ("A, B. - L^{}.pdf", "empty braces"),
    ("A, B. - L^{{2}}.pdf", "doubled braces"),
    ("A, B. - a^1^ dangling.pdf",
     "a dangling script mark after an expression: 'a¹^' put a script "
     "character against a caret. Found by fuzzing; no real file has it."),
    ("A, B. - a^1^2 combined.pdf", "…but two real scripts still combine"),
    ("A, B. - L^2" + "x" * 200 + ".pdf", "long title, near the byte limit"),
    ("A, B. - " + "L^2 " * 60 + "end.pdf", "many expressions in one title"),
    ("A, B. - עברית L^2 טקסט.pdf", "RTL text around an expression"),
    ("A, B. - L^2 ​ spaces.pdf", "zero-width space"),
    ("A, B. - Café L^2 naïve.pdf", "combining marks nearby"),
    ("A, B. - 10,000 samples in dimension 3.pdf",
     "a thousands separator must never gain a space"),
    ("A, B. - Coefficients in (y,z) and f(x,y).pdf",
     "author-block comma rule must not reach the title"),
    ("Possamaï,D. - A note on BSDEs.pdf",
     "…but it MUST still fix the author block"),
    ("Shiryaev, A.N.- Stochastic disorder problems.pdf",
     "separator with its space eaten, then author spacing"),
    ("Jourdain, B., Reygner, J. - , Propagation of chaos.pdf",
     "stray comma opening the title; the separator must survive"),
    ("Lewis, A.D. - Should we fly in the airplane?—The correct defence.pdf",
     "a dash after ? is a second separator"),
    ("Cox, A.M.G. - Robust pricing -- An empirical study.pdf",
     "spaced -- is a subtitle break, not a range"),
    ("Guarracino, M.R. - Euro–Par 2010 parallel processing.pdf",
     "ruled phrase: Euro-Par takes a hyphen"),
    ("Carmona, R.A. - Statistical analysis in S–Plus.pdf",
     "ruled phrase: S-Plus takes a hyphen"),
]


def load_cases() -> list:
    """Library cases + pathologies, as ``(input, why)`` pairs."""
    lib_file = Path(__file__).with_name("golden_library_inputs.json")
    cases = []
    if lib_file.exists():
        for name in json.loads(lib_file.read_text()):
            cases.append((name, "library"))
    cases.extend(PATHOLOGIES)
    return cases


def compute() -> dict:
    return {inp: pipeline(inp) for inp, _why in load_cases()}


def load_expected() -> dict:
    if not GOLDEN_PATH.exists():
        return {}
    return json.loads(GOLDEN_PATH.read_text())


def bless() -> int:
    got = compute()
    GOLDEN_PATH.write_text(json.dumps(got, indent=1, ensure_ascii=False,
                                      sort_keys=True) + "\n")
    print(f"blessed {len(got)} cases -> {GOLDEN_PATH}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    if "--bless" in sys.argv:
        raise SystemExit(bless())
    exp, got = load_expected(), compute()
    bad = [k for k in got if exp.get(k) != got[k]]
    for k in bad[:20]:
        print(f"DRIFT\n  in : {k}\n  was: {exp.get(k)}\n  now: {got[k]}")
    print(f"{len(got) - len(bad)}/{len(got)} match")
    raise SystemExit(1 if bad else 0)
