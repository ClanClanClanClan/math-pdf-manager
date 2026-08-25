# find_math_regions, measured

## The corpus

345 library titles, hand-decided, drawn by seeded stratified sampling (seed
20260825) from the 25,049 unique titles that `filename_ground_truth.decompose`
returns RELIABLE for, over the 25,246 in-scope PDFs `library_scope` admits.
201 maths spans, 1,042 protected characters, 166 positive / 179 negative.

Committed as `tests/fixtures/math_regions_ground_truth.json`, carrying its own
sampling frame and its two conventions. Re-deriving it costs a day of
labelling.

## Scores, character level, on those 345 titles

| implementation | precision | recall | F1 | exact |
|---|---|---|---|---|
| `filename_checker/math_utils` (pre-20f039c) | 0.043 | 0.236 | 0.073 | 106/345 |
| `text_processing/math_detector` (pre-20f039c) | 0.495 | 0.755 | 0.598 | 195/345 |
| `validators/math_handler` | 1.000 | 0.000 | — | 179/345 |
| `core/math_regions` at 20f039c | 0.681 | 0.872 | 0.765 | 272/345 |
| **`core/math_regions` now** | **1.000** | **0.996** | **0.998** | **343/345** |

Re-scored locally against the fixture, not taken from any agent's self-report.
`tests/test_core/test_math_regions_scored.py` pins these as floors
(P ≥ 0.995, R ≥ 0.99, exact ≥ 340, claim-share ≤ 0.045) and carries a
meta-test asserting each floor strictly excludes the old scanner's score.

## A measurement that was worthless, and the one that replaced it

The earlier version of this document argued against landing on the grounds
that `processing.title_normalize.propose_title_case` produced identical
output on all 25,049 titles under either module.

**That number was real and meaningless.** `propose_title_case` never calls
`find_math_regions` — instrumented, 0 calls. Substituting `lambda t: []` gives
the same 0 differences. It measured nothing.

The consumer that *does* consult it is
`core.sentence_case.to_sentence_case_academic`. Measured through it over all
25,049 titles, before and after:

* **167 titles change.**
* **3 destroyed titles → 0** (see below).
* Lost protection, exhaustive: **1 title / 3 characters**, against the old
  module's 137 titles / 145 characters measured in the same direction.

Examples of the gain: `G-normal` no longer becomes `g-normal`; `C[0, ∞)` no
longer `c[0, ∞)`; `K–rough` no longer `k–rough`; `sin(x):xdx` no longer
`sin(x):Xdx`; `n:2` no longer `n:Two`.

## Two bugs found in the consumers, not in the detector

**`sentence_case` replaced three real titles with the single letter `X`.**
It collected WORD tokens and, finding none, returned `"X"`. A title with no
WORD tokens is not empty — it is usually a title that is *entirely*
mathematics or one whitelisted phrase. `F-processes`, `G-expectations` and
`Freefem++` were destroyed; so was `L^2`. The bug predates all of this work
and gets **worse** the better the detector is, because a more accurate
detector claims more titles whole. Fixed: no WORD tokens but some MATH or
PHRASE token means no case change is needed, so the title is returned
unchanged. `"X"` now means only "there is genuinely nothing here to case".

**The sentence-start scan walked through mathematics.** Deciding whether a
word starts a sentence means scanning back for sentence-ending punctuation and
stopping at the first content token. It stopped at a WORD but passed straight
through a MATH or PHRASE token. Because the library writes `/` as `:`,
`1/H-variation` is stored as `1:H-variation`; the scan passed through the MATH
token `H`, hit the `:`, read it as a sentence end, and capitalised
`Variation`. Fixed by treating MATH and PHRASE as content. 8 titles affected,
all 8 corrected.

## One rule, one implementation

`math_tokenization.py` kept a private `r'\$\$[^$]+\$\$'` rule and appended its
spans to whatever `find_math_regions` returned. It did not merely duplicate
the shared rule, it **overrode** it: on `$$the quick brown fox$$` the single
implementation correctly refuses four ordinary English words and the private
regex protected them anyway. Deleted. Measured safe: 0 of the 25,049 in-scope
titles contain a `$` at all. The differential tests are kept, now asserting
that every MATH token the tokeniser emits came from `find_math_regions`.

## Performance

The first landing candidate was **super-linear on brackets**: a 64-character
input of nested parentheses took 660 ms against the old module's 0.01 ms, and
grew roughly quadratically beyond. Cause: every bracket interior was re-parsed
by a fresh throw-away parser, once per enclosing start position — 36,256
tokenisations of that 64-character input.

Fixed by memoising the four pure parse functions, plus one step budget shared
across a whole call (`MAX_PARSE_STEPS`) and `MAX_INPUT_CHARS`. Measured now:

| input | old | now |
|---|---|---|
| the 64-char bracket pathology | 0.01 ms | 1.34 ms |
| worst 251-char nested `()` | — | 2.50 ms |
| typical library title | — | 0.021 ms |

251 bytes is the enforced filename cap. The longest real library title is 229
characters, so `MAX_INPUT_CHARS` (1,000) is not reachable from a filename.

## The apostrophe bug, fixed properly

The character class in `core/math_tokenization.py` and `core/tokenization.py`
read `['']` — **U+0027 twice and U+2019 never**. So `don't` was one WORD token
and `don't` was three. 1,116 in-scope titles use U+0027 and 444 use U+2019.

The obvious one-character fix measured as a **net regression**: 27 filename
proposals better, 21 worse. It was not the class fix that was wrong. Joining
the token revealed two bugs that had been hiding behind the split:

1. **The acronym branch looked at the whole token.** `BSDE's` arrived whole
   and stopped being recognised, so it lowercased to `bsde's`. The 2–3 letter
   check already had `word.split("'")[0]` with the comment *"For possessives,
   check the base word without apostrophe"* — but only for U+0027, and the
   known-acronym and mixed-case checks did not do it at all.
2. **A capital after an apostrophe was being lowercased.** Measured over the
   25,049 in-scope titles, the apostrophe is followed by a capital in 111
   places and **98 were damaged**: `Calcul d'Itô` → `d'itô`, `théorèmes
   d'Abel` → `d'abel`, `théorie d'Iwasawa` → `d'iwasawa`.

Both are now fixed, and with them a third that the work uncovered: of 702
capitalised-head possessives, **154 were being lowercased outright** —
`könig's`, `varadhan's`, `zvonkin's`, `gronwall's`, `yosida's`, `tsirel'son`,
and `possamaï's`. Of the 122 distinct words the new rule preserves, **121 are
surnames**; the single exception is `Planner's advices` in one economics
title. A dictionary test was considered and rejected: Abel, Baker, Clark,
Engel, Gross, James, Lee, Root and Tong are all dictionary words *and*
surnames here, so a dictionary would lowercase the very names it is for.

The English possessive is the one place preserving would be wrong —
`THE AUTHOR'S THEOREM` must lowercase to `the author's theorem`, not
`author'S`. Measured: this library contains no `'S` and no all-capitals
title, so the exception fires nowhere today. It is there because ingest takes
titles from Crossref and arXiv.

**Result over all 25,049 titles: 287 original capitals recovered, 0 lost, 0
titles destroyed, 0 errors.**

## Leading punctuation was being deleted

Found while fixing the above. A branch meant to strip a leading emoji asked
`ord(first_punct[0]) > 127` and deleted the character when true. That is not
an emoji test, it is a "not ASCII" test, and it destroyed three real titles:

* `"Choose your opponent", a new knockout design …` — opening quote deleted,
  closing quote left behind, so the title came out **unbalanced**
* `"Lion-Man" and the fixed point property` — same
* `…And justice for all!` — the ellipsis deleted

Unicode already draws the line: emoji and pictographs are category `So`,
quotation marks are `Pi`/`Pf`, an ellipsis is `Po`. A real emoji is still
stripped.

## Still open, recorded rather than implied

* **A hyphen/minus residual**: `2J_s-R_s, s≥0` yields two MATH tokens where
  the U+2212 spelling yields one, so the two leave different prose residues
  and `conformance.py` would judge the same edit differently. The subscript
  spelling the library actually uses agrees under both, so no real title is
  affected. Strict `xfail`.
* **`A(H1N1)` → `a(h1n1)`** on one title. The detector refuses it
  deliberately: a virus strain designation is a name, not notation. It
  belongs to the acronym branch, whose rule (2–3 letters, `isupper`) does not
  cover a four-character mixed alphanumeric token.
* **`D-modules` → `D-Modules`** on one title: the detector protects the
  letter and the sentence-case rule then capitalises the following word.
  The `1:H-variation` class of this was fixed by making the sentence-start
  scan stop at MATH tokens; this one is not reached by that fix.
* **Eponyms without a possessive** are still lowercased — `«Le théorème de
  Fermat»` gives `fermat`. The possessive rule above only sees `Fermat's`.
  Names carrying no apostrophe depend on the capitalisation whitelist, and
  that population has not been measured.

## Mutation

89 mutants across 89 distinct decision points, 84 killed. Of the 5 survivors,
2 are provably dead branches and 3 are reachable but change none of the 25,049
real titles. The module's own 184-case expectation table is now wired into
pytest as individual test ids — it was previously reachable only under
`if __name__ == "__main__"` and was the sole thing catching 13 mutants.

## Caveat on the 1.000

Precision 1.000 is measured on the 345 titles the design was tuned against. It
is an upper bound, not a generalisation estimate, and no second hand-labelled
sample exists.
