# What the library actually contains, and what extraction achieves on each part

Measured 2026-08-24 on the live library, read-only, at commit `3e26d41`.
Raw data: `census.jsonl` (27,160 rows), `baseline_out.jsonl` and
`reach_out.jsonl` (1,753 rows each) in the session scratchpad.

## Why this document exists

Every accuracy figure quoted for extraction in this project so far has
been measured on **arXiv-named arrivals in the inbox** — recent,
born-digital, with embedded metadata and a registry entry. That is the
easiest slice of the collection, and it is not the slice that needs
help. The owner's objection, in his words:

> arXiv papers are the EASY ones, because we have the API, and we can
> parse to check and make sure. But there are PLENTY of non-arXiv
> papers: older ones that were scanned, books, published papers with
> completely different layouts, sometimes with the title page not even
> being the first page.

He is right, and the numbers below are how right.

## Method

27,160 PDFs, excluding `Scripts`, `archive`, `gmnap*`, `.trash`,
`04 - Papers to be downloaded`, and `12 - To be sorted` (not renamed
yet, so no ground truth).

The filename is the ground truth, which means the pipeline must not be
allowed to see it. Each sampled file is opened through a **symlink named
`unknown_NNNNN.pdf`** in a scratch directory. The extractor therefore
sees the document and nothing else — the condition a new arrival is
actually in. Nothing in the library is opened for writing.

The local LLM fallback is stubbed out (34 s/doc, and it is not what is
being measured). arXiv and Crossref lookups are left **on**, so any
registry id the extractor can find *in the document text* still helps it.

Verdicts are three-valued — CORRECT / WRONG / ABSTAIN — never two.

### Ground truth is not free

The naive "split the filename on the first ` - `" is **wrong for 11.8%**
of the library (3,106 of 26,377). Two shapes:

| shape | count | example |
|---|---|---|
| series/volume/page-range in the author slot | 1,395 | `Astérisque 390 - Baues, O. - Symplectic Lie groups` |
| exposé number glued with a hyphen | 1,711 | `16-Léandre, R., Norris, J. R. - Integration by parts…` |

Those rows are **excluded from scoring**, not silently mixed in. Scoring
against them marks a correct extraction wrong — which is exactly what
happened in `ml/pdf-meta-llm/results/eval_llm_100_v2.json`, see below.

## The population

|              | good text | thin text | no text layer | total |
|--------------|----------:|----------:|--------------:|------:|
| article      |    19,767 |        71 |           432 | 20,270 |
| book/notes   |     1,522 |       146 |           512 |  2,180 |
| thesis       |       533 |        42 |             9 |    584 |
| séminaire    |       194 |         1 |            42 |    237 |
| **total**    | **22,016**| **260**   |     **995**   | **23,271** |

("good text" = ≥1,500 characters over the first five pages; "no text
layer" = <200.)

Signals available across the scorable set:

| signal | share |
|---|---|
| arXiv marker anywhere in the first three pages | 22.4% |
| embedded `/Title` | 55.6% |
| embedded `/Author` | 42.0% |
| **neither title nor author** | **43.1%** |

## What the current pipeline achieves

Whole-filename exact, per population, filename hidden:

| population | n | title ok | wrong | abstain | authors ok | **full name** |
|---|--:|--:|--:|--:|--:|--:|
| article / good text   | 220 | 64% | 17% | 15% | 54% | **50%** |
| article / thin text   |  71 | 27% | 30% | 39% | 27% | **20%** |
| article / no text     | 220 |  7% | 29% | 63% |  3% | **3%** |
| book/notes / good text| 217 | 12% | 24% | 60% | 12% | **7%** |
| book/notes / thin text| 146 | 16% | 27% | 53% | 18% | **12%** |
| book/notes / no text  | 220 |  0% |  7% | 92% |  2% | **0%** |
| thesis / good text    | 220 | 30% | 21% | 45% | 40% | **25%** |
| thesis / thin text    |  42 | 21% | 19% | 60% | 24% | **19%** |
| séminaire / good text |  25 |  0% | 32% | 68% |  0% | **0%** |

**Population-weighted: 43.7%.** Weighted by the real library, not by the
sample.

Two things to read off this table.

1. **Books are not articles with more pages.** 50% against 7% is not a
   difference of degree. The same code, the same document quality, one
   seventh of the result.
2. **The pipeline mostly abstains rather than inventing** — 60% abstain
   on books, 92% on scanned books. That is the correct failure mode and
   worth protecting. Whatever replaces it must abstain too.

## The ceiling on any text-in model

Is the title even inside the window a text model is shown? (The shipped
dataset feeds 6,000 characters; its quality filter rejects any paper
whose title is not within 8,000.)

| population | n | ≤6k | ≤8k | ≤25k | anywhere | **never found** |
|---|--:|--:|--:|--:|--:|--:|
| article / good text    | 220 | 100% | 100% | 100% | 100% | 0% |
| article / thin text    |  71 |  86% |  86% |  86% |  86% | 14% |
| article / no text      | 220 |   1% |   1% |   1% |   1% | **99%** |
| book/notes / good text | 217 |  96% |  96% |  96% |  96% | 4% |
| book/notes / thin text | 146 |  99% |  99% |  99% |  99% | 1% |
| book/notes / no text   | 220 |   4% |   4% |   4% |   4% | **96%** |
| thesis / good text     | 220 |  98% |  98% |  98% |  98% | 2% |
| séminaire / no text    |  42 |   0% |   0% |   0% |   0% | **100%** |

**This corrects an assumption I had been repeating.** I expected the
6,000-character window to be the binding constraint on books, because
their title page is often page 3–5. It is not: 96% of good-text books
have the title inside 6,000 characters, precisely *because* their front
matter is sparse — six thousand characters of a book reaches page six.
Page number was the wrong unit. Character offset is the right one, and
by that measure the window is fine.

The real ceiling is the **995 documents with no text layer** (4.3% of
the scorable library, and 23% of all books). For those, a text-in model
returns nothing no matter how well it is trained. **There is no OCR
anywhere in this codebase** — `pyproject.toml` declares an `ocr` extra
and nothing imports it, though `tesseract` is installed on this machine
and PyMuPDF can see its tessdata.

## What is wrong with the existing model pipeline

`ml/pdf-meta-llm/`, 25,278 rows mined from the library.

1. **The quality filter removes the hard cases, and it removes them
   *because* they are hard.** `prepare_dataset.py:165` rejects any paper
   whose title is not within the first 8,000 characters — 861 rows.
   `authors_are_metadata` drops 1,441 more. 2,737 of 25,278 (10.8%) are
   filtered out, and the filter is correlated with difficulty. The test
   split is therefore easier than the library.
2. **Documents with no text layer never enter the corpus at all** — they
   are dropped upstream at extraction, silently. That is the 995.
3. **The eval's ground truth is corrupted on 9 of 100 samples**, all
   séminaires and books, from the same naive ` - ` split described
   above. One sample has `gt_authors: ["08"]` — a series number — and
   the model scored 1.0 for reproducing it. Another has
   `gt_title: "nº1 - 5 juillet 1971"`, scored exact.

       reported title_exact overall     0.85
       on the 91 clean-ground-truth      0.89
       on the 9 corrupted-ground-truth   0.44

4. `Results.md` is a pasted Colab `PermissionError` traceback.

## Defects this measurement found

- **Author segments were never sanitised for the filesystem** — fixed in
  `3e26d41`, with the U+007F/C1 hole in `_clean_for_fs` that a property
  test found. Seven live files are named through it; listed in
  `known-issues-cockpit.md`, not repaired.
- **The author parser collapses some embedded `/Author` strings.**
  `Léandre, R., Norris, J. R.` → `Norris, R. L. J. R.`;
  `Doléans-Dade, C., Dellacherie, C., Meyer, P.-A.` →
  `Meyer, C. D.-D. C. D. P.-A.`. Same failure shape as the `", and "`
  bug fixed in `f126489` — the segment heuristic bails and the whole
  list collapses into one author. Not yet fixed.

## What this implies for the model question

The owner's proposal — train on the 20k+ correctly-named papers — is
sound, and the corpus is real. What this measurement changes is the
*target* and the *evaluation*, not the idea:

- The bar is **not** 93.8%. Per population it is 50% (articles), 25%
  (theses), 7% (books), 0% (scanned anything).
- Any evaluation that reports one number across the library is
  reporting the article number, because articles are 87% of it. Report
  per stratum or do not report.
- The 995 no-text documents are an **OCR** problem, not a model problem,
  and they are 23% of the books.
- Ground truth for books and séminaires has to be repaired before it can
  be trained or tested on — 11.8% of filenames do not mean what the
  naive split says they mean.
- Abstention must be scored. The current pipeline's 60–92% abstain rate
  on books is a feature; a model that replaces abstention with a
  confident wrong answer is worse than what exists, at any accuracy.
