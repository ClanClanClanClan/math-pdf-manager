# find_math_regions, measured against a hand-labelled corpus

## The corpus

345 library titles, hand-decided, drawn by seeded stratified sampling
(seed 20260825) from the 25,049 unique titles that
`filename_ground_truth.decompose` returns RELIABLE for, over the 25,246
in-scope PDFs `library_scope` admits. 201 maths spans, 1,042 protected
characters, 166 positive / 179 negative titles.

Every offset was verified by slicing the NFC title and reading the
result. Labels were authored as inline `⟦⟧` markers and the de-marked
text was confirmed byte-identical to the library title before offsets
were computed, so a transcription slip cannot silently shift an offset.

Stored at `scratchpad/gtlane/gt_final.json` during the run. **It is not
in the repo** — it lives in a session scratchpad and will be deleted.
Re-deriving it costs a day of labelling. If it matters, it should be
committed as a test fixture; that has not been done.

## Scores, character level, all on those 345 titles

| implementation | precision | recall | F1 | exact |
|---|---|---|---|---|
| `validators/filename_checker/math_utils` (pre-20f039c) | 0.043 | 0.236 | 0.073 | 106/345 |
| `core/text_processing/math_detector` (pre-20f039c) | 0.495 | 0.755 | 0.598 | 195/345 |
| `validators/math_handler` | 1.000 | 0.000 | — | 179/345 |
| **`core/math_regions` (committed, 20f039c)** | **0.681** | **0.872** | **0.765** | **272/345** |
| candidate synthesis (not landed) | 1.000 | 0.996 | 0.998 | 343/345 |

Both rows for the committed and candidate modules were re-scored
locally against the same corpus, not taken from the agents' self-reports.

## Why the candidate is not landed

**It changes nothing the owner would see.** Proposing a title-case for
all 25,049 library titles under each module gives **identical output on
all 25,049** — zero differing proposals, zero errors either side. The
caser's own acronym / mixed-case / accented branches already cover the
cases where the two detectors disagree, so the detector's extra accuracy
does not reach a filename.

It also breaks 13 existing tests (not the 6 the reviewing agent
reported — they ran one of the two suites):

* 7 in `tests/core/test_math_tokenization.py` — LaTeX. `\[...\]` and
  `\(...\)` return no regions, so the tokeniser's one-MATH-token-per-
  formula contract fails. The library contains zero LaTeX titles, so
  this is a contract for a consumer, not for the library.
* 3 convention — `Γ-convergence` yields `Γ`, not `Γ-convergence`. This
  is arguably the better answer (the word "convergence" is ordinary
  English and title-casing may legitimately touch it), and the caser
  handles the mid-word span correctly, but it is a deliberate
  convention change and the tests encode the old one.
* 1 ASCII hyphen-minus is not in the operator tables, so `2Jₛ-Rₛ`
  splits where `2Jₛ−Rₛ` would not. Real, 9 titles.
* 2 LaTeX partial spans.

**Recommendation: land it only alongside a consumer that needs it.**
Today the accuracy is unbanked. The gap it would close is real but
latent.

## What the committed module gets wrong, measured

It misses 561 titles, all ASCII notation. Per-construct recall: Unicode
blackboard-bold, superscript, subscript, Greek, calculus operators and
brace groups all 100%; caret-after-capital 98.3%; `C_b` underscore 95%.
Then it falls off: BMO 7/27, UMD 0/8, VMO 0/8, 2D|3D 0/12, GL|SL|SU(...)
2/9, Q-learning 0/24, N-player 1/28, p-adic 11/54, G-expectation 3/72.

The shape of the gap is precise: **it knows a Greek letter before a
hyphen is mathematics (σ-algebra, 31/31) but not that a Latin one is.**

Unbanked as above — `title_normalize` protects these anyway today. The
exposure is if that branch ever changes.

## A redundancy that unification removed

`maintenance/conformance.py::_prose_outside_maths` imported
`math_detector.find_math_regions` *because it was a different
implementation*, and said so. Commit 20f039c pointed that name at
`core.math_regions`, so the check now compares the converter against
itself. Nothing failed — the redundancy just stopped existing. The
docstring has been corrected to say what the check now actually buys.

## Acronyms

`title_normalize.propose_title_case` was checked directly: BMO, UMD,
VMO, BV, BSDE and PDE are all preserved unchanged. The open worry that
"~2,000 case-sensitive occurrences are protected by nobody" does not
materialise.

## Caveat on the 1.000

Precision 1.000 is measured on the 345 titles the candidate was tuned
against. It is an upper bound, not a generalisation guarantee, and no
second hand-labelled sample exists.
