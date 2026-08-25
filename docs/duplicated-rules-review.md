# Duplicated rules: a second pass

Measured 2026-08-24 over the live library (25,253 in-scope PDFs, 25,005
distinct titles, 18,342 author-slot heads) and the whole of `src/`.

The first pass unified `fix_initial_spacing` and removed 13 shadowed
definitions. This one looks for the rest.

## Method

Three sweeps, because each catches what the others miss.

1. **Structural.** Every function body normalised (names and short literals
   erased) and hashed, to catch a copy that was *renamed*. Result: **3 groups
   spanning more than one file**, all benign — a three-way `download` across
   publisher adapters, and two small validation helpers. There is no
   copy-paste problem in this repository.

2. **By domain.** Function names matched against nine rule families —
   normalisation, sanitisation, author parsing, maths detection, title casing,
   identifier extraction, hashing. This is what found everything below.

3. **Differential, on real data.** For each family, every implementation run
   over the library and compared pairwise. A count, not an opinion.

## Removed

### `validators/manual_validation.py` — 149 lines, worse than dead

It runs its checks **at import time** and every one of the seven fails: it
imports `validators.math_utils`, `validators.debug_utils`,
`validators.unicode_constants`, `validators.filename_checker_compatibility`
and `test_refactoring`, none of which exist. Importing it prints a
`FINAL VERDICT: NEEDS ATTENTION` banner. A leftover from the 2025 refactor;
nothing imports it.

### `filename_checker/text_processing.to_sentence_case_academic` and `to_sentence_case` — 56 lines

Zero callers, including in tests. The live casing path
(`filename_checker/core.py:345`) imports the function from
**`core.sentence_case`**, not from the module next to it.

That matters, because these two disagree on **38.7% of library titles**, and
the dead one is the one that looks right at a glance:

```
in    Robust preferences and convex measures of risk
core  robust preferences and convex measures of risk     <- the LIVE one
dead  Robust preferences and convex measures of risk
```

The live one lowercases the first letter when called without its
whitelists — which is not how `core.py` calls it. Both facts are worth
knowing; neither is a reason to keep an unreachable copy.

## Measured, and deliberately not merged

### `find_math_regions` — RESOLVED: one implementation

`src/core/math_regions.py` is now the only one; the three below delegate to
it. It is not a merge of opinions — **all three were wrong**, and the
scoping measurement is why the replacement is 170 lines rather than 724.

**What the library actually contains.** Across 25,005 titles: **no `$…$` at
all**, **no `\mathbb` at all**, 39 titles with an `L^2`-style caret, 25 with
`X_t`, 8 with `AR(1)`. The whole mathematical surface is about **800
characters** — 416 Greek, 190 super/subscript, 116 operators, 80 letterlike.
The 724 lines of LaTeX machinery were built for a library that has none.

| | flags | mean claim | accent spans | English spans |
|---|--:|--:|--:|--:|
| `math_detector` | 4,238 | 5.5% | **2,988** | 20 |
| `math_utils` | 6,954 | **49.6%** | 0 | **3,921** |
| **`core/math_regions`** | **877** | 9.4% | **0** | **0** |

The detector treated **accented Latin letters** as mathematics — 4,331 hits
on `é` alone, and 85% of the titles it flagged contain none. Downstream,
conformance asks it which part of a title is prose and was handed
`Prcis d'analyse relle` for *Précis d'analyse réelle*: **15% of titles**.

Anchors are now derived from Unicode properties, not a hand list — the same
lesson as the uppercase class in `core/initials.py`. Blocks turned out to be
the wrong index too: `U+209C` is *"LATIN SUBSCRIPT SMALL LETTER T"* (the t of
`Bₜ`) and sits in Superscripts, while `U+1D63` (the r of `lᵣ`) sits in
Phonetic Extensions. Asking for the **name** catches both.

Three things measurement forced that reading would not have:

- A period is a **decimal point**, not a connector. Letting it through meant
  an anchor at the end of a stem swallowed `.pdf`, so `lᵣ.pdf` was one span
  and `l_r` was not — the prose differed and conformance called a pure
  typeface change a REWRITE, its loudest bucket.
- The bracket rule first demanded a digit or maths character inside, which
  **rejected real notation**: `sin(x)`, `GL(n)`, `f(x)`, `GL(N, F)`,
  `Bes(d)` — 13 in the library. `Gl(n)` would be wrong.
- LaTeX delimiter support had to stay. The library has none, but the
  tokeniser's contract is one MATH token per formula, and dropping `\[…\]`
  returned the Black–Scholes equation as six spans.

Nine mutants, nine killed. The old asymmetry compensation in
`conformance._prose_outside_maths` is now unnecessary — the new rule returns
the whole `lᵣ`, not just the modifier — but it is harmless and left alone.

### `find_math_regions` — the three implementations, as they were

| where | used by | on library titles |
|---|---|---|
| `core/text_processing/math_detector.py` | conformance, `core/tokenization` | finds regions in 4,238 |
| `validators/filename_checker/math_utils.py` | the casing path | finds regions in 6,954 |
| `validators/math_handler.py` | only the module deleted above | finds regions in **0** |

The two live ones disagree on **9,655 of 25,005 titles**, and both are wrong
in different directions:

```
On square-root boundaries for Bessel processes…
   math_detector  no maths          <- right
   math_utils     (10,47) (57,81)   <- thinks ordinary English is maths

(Almost) Everything you always wanted to know…
   math_detector  (1,7) "Almost"    <- treats parenthesised text as maths
   math_utils     no maths          <- right
```

The third is not blind in general — it finds `$x^2$` — it is blind to **this
library's convention**, which writes maths in Unicode (`ℝ^∞`, `Bₜ`) and never
in `$…$`. Hence 0 hits on 25,005 real titles.

**Impact on renames: zero.** `move_normalizer.normalize_full_name` passes
`sentence_case=False` — *"NEVER auto-recase the title"* — so the detector
never reaches a rename decision. Verified by swapping the implementations
under 3,000 real filenames: **0 proposals changed.** The disagreement affects
what Conformance reports and what Title Review offers, not what gets renamed.

**Why not merged here.** Unifying needs an answer to "what counts as maths in
a title", and the two candidates are each right about cases the other gets
wrong. That is a design decision with a 25,005-title blast radius, and it
deserves the same treatment `fix_initial_spacing` got — evidence, a union,
adversarial verification — not a guess folded into a cleanup.

### `normalize_for_comparison` — three implementations, and they are not the same rule

| | NFC | collapse spaces | space around `,` and `-` | fold dash *types* |
|---|---|---|---|---|
| `fc/author_processing` | ✓ | ✓ | | |
| `processing/duplicate_finder` | ✓ | ✓ | ✓ | |
| `validators/unicode_handler` | ✓ | ✓ | | ✓ |

Pairwise disagreement over 25,005 titles: 12.2%, 25.2% and 34.1%.

They share a name and answer different questions. Folding `–` to `-` is
right when hunting near-duplicates and **wrong** when deciding whether a name
is already canonical, because this library treats the two as distinct — en
dash for two co-equal entities (`Hamilton–Jacobi`), hyphen for one word built
from parts (`mean-field`).

Merging them would be a bug. The defect here is the shared *name*, not the
three behaviours.

### `nfc` — seven implementations, all identical, and that is fine

Compared over 8,007 real strings: **0 disagreements**, and every one is
strictly NFC. But each is a one- or two-line call to
`unicodedata.normalize("NFC", …)`. The stdlib already *is* the single
implementation; these are local spellings of it. Routing seven modules
through a shared helper would add coupling and remove nothing.

## The structure underneath several of these

`src/validators/` holds two layers. `validators/filename_checker/` is live.
The flat layer beside it — `unicode_handler`, `math_handler`,
`title_normalizer`, `author_parser`, `pattern_matcher`, `suggestion_engine` —
is frozen at 2025-07 and has drifted, and the modules import each other, so
"nothing uses it" is false even when nothing outside uses it.

Two of the rival implementations above live in that layer, and one of them
(`math_handler`) now has no reachable consumer at all. Retiring the layer is
the change that would remove the whole class of problem. It is not a cleanup;
it is a project.

## Recommended order

1. Unify `find_math_regions`, with the same rigour as the spacing rule.
   Highest disagreement, and it decides what Conformance tells you.
2. Rename the three `normalize_for_comparison` functions to say which
   question each answers. No behaviour change.
3. Decide the fate of the frozen `validators` flat layer.
