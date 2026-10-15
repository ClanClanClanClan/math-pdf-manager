# Filename convention — what the code enforces

**Rewritten 2026-10-15 from the code.** The previous version of this file
prescribed rules the code does not apply and, in places, rewrites the other
way (it asked for `Krée, P.A.`; the code writes `Krée, P. A.`, and the library
agrees with the code). This version states only what a module enforces, names
that module, and gives the library's agreement with each rule.

Every number below was measured on 2026-10-15, read-only, over the
**25,251 PDFs the tools may touch**: `processing/library_scope.py` leaves out
the archival collections and the two staging folders. Each count comes from the
module's own function, not a re-implementation, run on the filename alone.
Where code and this file disagree, the code is what happens: fix one of them.

---

## 0. When a name is made, and by what

| moment | what builds or checks the name |
|---|---|
| a new paper arrives (watcher, *File these papers*, the name the Sort Queue suggests) | `arxivbot/models/cmo.py` `CMO.get_canonical_filename`, which runs `validators/filename_checker/core.check_filename` with `sentence_case=False`; then `processing/move_normalizer.normalize_full_name` (`processing/ingest.py`) |
| a name the owner typed in the Sort Queue box, or an upgrade that keeps the preprint's name | **taken as typed**: none of the rules below is applied (`ingest.py`, `canonical_override`) |
| an existing paper is filed into a topic | `normalize_full_name` (`processing/publication_topic_router.file_into_topic`) |
| an existing name is tidied | Maintenance → *Normalize existing filenames*: `processing/library_normalize.propose_renames` → `normalize_full_name`, applied only when the owner presses Apply |
| checked | Conformance: `maintenance/conformance.examine` runs the same `normalize_full_name` |

So there are two kinds of rule:

- **Every path**: inside `normalize_full_name`. It applies, in order,
  `filename_normalizer.normalize_filename`,
  `author_surnames.canonicalise_filename`, the initials fix,
  `math_typography.canonicalise` and `title_normalize.propose_title_case`.
- **Arrival only**: inside `cmo.py` and `check_filename`. Nothing re-applies
  these to a name already on a shelf.

**Measured.** `normalize_full_name` leaves **25,249 of 25,251** names
unchanged. The two it would change are in §2.4 and §3.1.

---

## 1. Shape

**`Author block - Title.pdf`**, split at the **first** `" - "`. A paper with
no author is `Title.pdf`. Every tool that reads a name splits it this way
(`move_normalizer.normalize_full_name`, `author_surnames.canonicalise_filename`,
`phrase_impact.title_of`). A series prefix in front of the authors
(`Astérisque 281 - Authors - Title`) is tolerated.

Repairs to the separator itself, on every path
(`processing/filename_normalizer.normalize_filename`):

- a separator with its space eaten is restored (`Itô, K.- Poisson` →
  `Itô, K. - Poisson`), but a compound initial is left alone (`Zou, H.-F.`);
- the spaces around the separator become exactly one on each side;
- a title that opens with the separator's own punctuation loses it
  (`J. - , Propagation` → `J. - Propagation`);
- a dangling comma before the separator is removed.

**Measured.** 25,196 names have the separator; **55 do not**.
Conformance reports those 55 as *Never examined*, because no author rule can
reach them. `normalize_filename` leaves **25,251 of 25,251** names unchanged.

---

## 2. The author block

### 2.1 `Surname, A. B.` — one space between initials

Each author is `Surname, Initials`. Initials are separated by one space, and
hyphenated given names keep their hyphen: `Lions, P.-L.`, `Bouchaud, J.-P.`.

- **At arrival**, `cmo.Author.initials` joins initials with `". "`.
- **On existing names**, `core/initials.space_initials` respaces glued
  initials (`Rogers, L.C.G.` → `Rogers, L. C. G.`). It runs through
  `move_normalizer`, only when `_has_unspaced_initials` sees a full stop
  glued to a capital.

**Measured.**
- 24,666 author blocks carry an initial. The live author path would respace
  **none** of them.
- 127 blocks do contain glued capitals, and every one is a series name,
  `Mémoires de la S.M.F. …`, which the path rightly leaves alone.
- 1,923 blocks carry a hyphenated initial.

### 2.2 Initials of more than one letter

Transliterated initials keep all their letters: `Kabanov, Yu. M.`,
`Neretin, Yu. A.`, `Rutickii, Ya. B.`. An initial is a capital plus up to three lower-case letters
(`core/initials.INITIAL`), so `Yu.A.` is respaced to `Yu. A.` and never cut
to `Y.`.

**At arrival**, `cmo.Author.initials` keeps a given name that is already
written as initials whole (`core/initials.letters_of_initial`): `Yu. M.`
stays `Yu. M.`, and a glued `Yu.A.` is spaced first, so it becomes
`Yu. A.`. The full stop is what marks an initial, so a name in full is
still cut to its first letter: `Yuri` and `Yu` give `Y.`. Turning a full
name into `Yu.` would need its language (`Zhang` is Chinese and takes `Z.`).
The over-length refit `library_normalize._fit_to_limit` rebuilds author
blocks through the same method.

Until 2026-10-15 arrival kept only the first letter of each token:
`Yu. M.` became `Y. M.`, and `Yu.A.` became `Y.`, losing the `A.` too.

**Measured.**
- 174 author blocks carry one. By occurrence: `Yu.` 154, `Ya.` 12, `Kh.`,
  `Ch.`, `Th.`, `Ph.` 2 each, and `Ts.`, `Sh.`, `Sz.` 1 each.
- Each of those 174 blocks, parsed and rebuilt by the arrival namer, comes
  out exactly as it is on the shelf: **174 of 174** (the old code managed 1).
- The refit, run on every name with an author block, rebuilds the name
  exactly for 24,683 of 25,196 (the old code: 24,510). It gained 173 and
  lost none.

### 2.3 Commas

There is one space after each comma, **in the author block only**. In a
title, a comma is often mathematics (`C^{0,1}`, `CARMA(p,q)`), and a rule
that crossed the separator once damaged 86 titles. No space goes before a
comma, except straight after a dash. Every path applies this
(`filename_normalizer.normalize_filename`).

### 2.4 Surnames, and the particles in them

A particle takes a capital **when it is part of the surname** and stays
lower case **when it is a preposition**. The test is whether it can be
dropped: Tocqueville is "Tocqueville", so his `de` is a link word, but Le Gall
is never "Gall", so `Le` is part of the name.

Nationality cannot be recovered from the particle: `da Prato` is Italian
and takes a capital, `da Silva` is Portuguese and does not. So the rule is a
**per-person list**, `config/author_surnames.yaml`, and its header carries
the sources. The owner can switch any entry off at Settings → Author
surnames; those vetoes are stored with the library
(`<library>/.mathpdf-config/author_surname_vetoes.json`).

How it is applied:
- by `processing/author_surnames.canonicalise_filename`, on every path;
- to the author block only, including behind an exposé number (`103-le Gall`
  → `103-Le Gall`);
- the same letters in a title are ordinary words and are never touched.

**Measured.**
- 163 rulings are in force.
- 646 author blocks name a ruled surname. **645** spell it as ruled.
- One does not: `Prats'ovytyĭ`. The ruling writes `Pratsiovytyi`, so the
  next Normalize would rename that one file.

### 2.5 The apostrophe in a surname: U+0027

The author block is a **key**, not prose. Search, the sort order, the
duplicate detector, and every comparison with zbMATH, arXiv, ORCID and Crossref
run on it, and those authorities write U+0027. The reasoning is in
`processing/apostrophes.py`.

No naming path enforces this as a general rule. It holds only where a surname
ruling spells it (`D'Amato`).

**Measured.** 91 author blocks contain U+0027, and **0** contain U+2019.

### 2.6 Too many authors: `, et al.`

When the full name would be over the byte limit (§4.4), authors are dropped
from the end until it fits, the title is kept whole, and `, et al.` is
appended. The code is `cmo.build_with_max_authors`, used at arrival and by
the sweep's `library_normalize._fit_to_limit`.

**Measured.** 12 author blocks end in `, et al.`. One writes `et al.` without
the comma and one writes `etal`. Nothing rewrites the spelling on an existing
name.

---

## 3. The title

### 3.1 Casing: the safe default

`processing/title_normalize.propose_title_case`, on every path, **word by
word**:

- **The first word** is capitalised. It is left alone when it is:
  - a single letter followed by a hyphen (`p-adic`);
  - a lower-case particle (`de Finetti`);
  - mixed-case, an acronym, or accented.
- **A mid-title word** is lowered only when it is a plain `Xxxx` in ASCII
  and **provably ordinary**. That means one of:
  - the owner marked it common in `<library>/.mathpdf-config/title_vocab.json`;
  - it is in the built-in list;
  - the library itself writes it lower case at least 5 times, and at least 5×
    as often as capitalised (`processing/title_corpus.corpus_says_common`).
- **Never lowered:**
  - a word inside quotation marks, nested ones included (§3.3);
  - a word inside a bibliographic bracket (`[Stochastic Process. Appl. 107 (2003)]`);
  - a multi-word name from the whitelists in `config/config.yaml` or the
    owner's vocabulary;
  - `University`, `Institute` and similar in `<Noun> of <Name>`;
  - a month next to a year, or a known place;
  - a word after a lower-case particle;
  - a word after an internal `. ! ? …`;
  - a short capitalised run that may be a name.
- **A German title**, recognised by a marker word or by `ß`, has **no** word
  lowered.
- **A mid-title word is never capitalised.** A whitelist entry can only keep a
  capital that is already there. The owner's **phrase rulings** are the only
  thing that imposes a spelling, dash included: `title_vocab.json` "phrases",
  set at Settings → Name phrases, matched regardless of case and dash.
- A word it cannot prove is kept as written and listed for the owner. It
  never guesses.

**Measured.** **25,195 of 25,196** titles are already what the caser
proposes. The one exception is a mistaken proposal,
`…Euclid’s Elements` → `…Euclid’s elements`: the book's title is not a name
the caser knows. Conformance lists it for the owner.

**Not live.** The *Name or ordinary word?* answers on the Spelling page are
saved to `config/casing_decisions.json`. Only
`core/sentence_case.to_sentence_case_academic` reads that file, and no live
path calls it: both call sites of `check_filename` pass `sentence_case=False`.
So those answers do not change any filename today. See §6.

### 3.2 Mathematics

`processing/math_typography.canonicalise`, on every path, title only:

- A sub- or superscript is written in **Unicode** when every character of it
  has a Unicode form (`L^2` → `L²`, `X_n` → `Xₙ`).
- Otherwise it is written in **LaTeX** form, with braces only for more than
  one character (`C^{1,α}`).
- `\mathbb{X}` becomes the double-struck letter, for the 15 letters that have
  one.
- Unbalanced brackets, nested scripts and empty scripts are **refused**
  (`math_typography.problems`) and left as they are.

The author block is never touched: `X_n` is a subscript in a title but an
initial in an author block.

**Measured.** 476 titles carry scripts. **471** are already canonical,
**5** are refused (Conformance: *maths refused*), and **0** would change.

### 3.3 Quotation marks

This is the owner's ruling of 2026-10-14, kept in one place,
`processing/quote_marks.requote`:

| language | outer | inner |
|---|---|---|
| English | `‘…’` | `“…”` |
| French | `« … »` | `‹ … ›` |
| any other, or not known | left as they are | |

Details:

- In French, the space inside the guillemets is an ordinary U+0020.
- One pair of double marks is converted. An odd number of marks, nesting, or
  marks that cannot be paired are left as they are.
- A straight `"` between two letters is an inch mark, not a quote.
- The language is that of the **title around the quotation**, not of the
  quoted words or the authors' names (`quote_marks.quotation_language`,
  since 2026-10-15). The seeded detector reads the title; then small words
  outside the quotation that only English or only French uses decide between
  those two. Any other answer, or none, leaves the marks as they are.
- **Applied at arrival only**, and only when the title holds a straight `"`
  outside mathematics (`validators/filename_checker/text_processing.convert_straight_quotes_to_proper`).
- No sweep applies it to names already filed; the module's own docstring
  calls for a per-file review instead.
- The caser (§3.1) recognises `‘…’` and `‹…›`, nested, and never recases
  inside them.

**Measured.** 251 titles carry quotation marks. Under the rule above, their
languages are English 179, French 66 and other 6. Through `requote`:

- **226** are already in the convention.
- **6** would change, e.g. `Erratum "Optimal stopping time problem…"` →
  `Erratum ‘Optimal stopping time problem…’`, and
  `Une preuve "standard" du principe…` → `Une preuve « standard » du principe…`.
- **19** are left as they are: 6 read as a language other than English or
  French, 5 that already contain single marks (nesting), and 8 whose marks
  cannot be paired.

### 3.4 Apostrophes, and the marks that look like them

The rule is keyed on **what the mark does**, not on the language. Every
national authority prescribes the same raised comma for elision, and none
flips it. The real axis is **punctuation versus letter**:

| function | example | mark |
|---|---|---|
| elision, possessive, contraction | `l'équation`, `Itô's formula`, `don't` | punctuation apostrophe |
| anglicised prefix | `O'Connell` | punctuation apostrophe |
| German `-'sch` | `Green'schen` | punctuation apostrophe |
| transliterated Cyrillic soft sign | `Kolokol'tsov` | **a letter**, not an apostrophe |
| Breton `c'h` | `Le Floc'h` | **part of a letter** |
| mathematical prime | `f'`, `X'_t` | **a prime** (U+2032), not an apostrophe |

The full taxonomy and its sources are in `processing/apostrophes.py`.

- **Author block:** U+0027 (§2.5).
- **Title:** the settled choice is U+2019 for a punctuation apostrophe,
  because a title is prose. A prime must never become one.

**What the code does.** At arrival only, a straight `'` in the title that
is **certainly** an apostrophe becomes U+2019, in every language
(`apostrophes.title_apostrophes`, called by `convert_straight_quotes_to_proper`).
It is certainly one when it stands:

- between two letters: `l'équation`, `Itô's`, `don't`, `Tsirel'son`, `SDE's`;
- between a letter and an opening quotation mark: `l'« inégalité »`;
- after a word ending in `s`, when no single quotation is open:
  `Walras' equilibrium`;
- after `)` or a digit and before `s`: `Heston (2008)'s`;
- at the start of `'Tis`.

Everything else stays as it arrived:

- a prime: `f'(x)`, `X'_t`, `S'-processes`, `u''`;
- a quotation mark: `'hot hand'` keeps both straight marks. The quotation
  rule (§3.3) converts double marks only;
- TeX's `''` closer.

Mathematics is protected. A whitelisted phrase is not, because it guards
casing, not this mark.

Until 2026-10-15 arrival did the opposite. A contraction stayed U+0027, and
when the title also held a `"`, every other `'` became `’`: `f'(x)` became
`f’(x)`, and `'hot hand'` became `’hot hand’`.

Search and duplicate detection fold every apostrophe-like mark together
(`apostrophes.fold_marks`); the conversion leaves that fold unchanged.

**Measured.**
- **1,699** titles contain U+2019. **0** of the 25,196 names with an author
  block contain U+0027; 2 of the 55 without one do, both ICM 1893 proceedings
  (`world's`).
- Every ’, ‘ and ′ in the 25,251 titles was made straight again and the rule
  run over the result. It restores U+2019 at all 1,803 apostrophes. It turns
  none of the 175 opening and 175 closing single quotation marks, and
  neither of the 2 primes, into one. It leaves alone the 6 marks of 3 TeX
  `''` closers.
- The library's own 1,699 apostrophe titles were passed through the whole
  arrival namer with every mark straightened. 1,513 come out exactly as they
  are on the shelf (the old code: 0).
  - Of the other 186, 169 differ only because a single-quoted passage stays
    straight where the library has `‘…’`.
  - The rest come from the colon rule (7), casing (4), TeX `''` (3) and the
    double-quote rule (3).
  - Not one differs at an apostrophe.

### 3.5 Year ranges take an en dash

This is the owner's ruling of 2026-10-09, applied by
`processing/filename_normalizer._en_dash_year_ranges` on every path, to the
whole name.

- Two years joined by `--`, `-`, `:`, `‐`, `‑`, `−` or `—` become
  `1988–1990`. The `:` is how macOS stores a `/` typed in Finder, so
  `2002/2003` on screen is `2002:2003` on disk.
- Only an increasing pair within 1500–2099 counts. A two-digit end is kept
  short: `1906–98`.
- A date (`2023-01-26`) and a piece of a DOI are left alone.

**Measured.** **106** names carry a year range, **all** with an en dash. **0**
use another mark. The 45 that did were renamed on 2026-10-09, in
transaction `91180f9880fc`.

### 3.6 Colons, slashes, double hyphens

- **At arrival** (`cmo.get_canonical_filename`):
  - a `:` in the title becomes `,`, the subtitle convention. The caser then
    treats the subtitle like the rest of the title: `BSDEs: Theory and
    Applications` arrives as `BSDEs, theory and applications`, but
    `Optimal stopping: A new approach` keeps its `A`, because a one-letter
    word is never lowered (probe, 2026-10-15);
  - a `/` becomes a **hyphen**;
  - a `\` is kept.
- **On every path** (`filename_normalizer.normalize_filename`):
  - `--` between digits becomes `–`;
  - a spaced ` -- ` becomes `, `;
  - a hyphen left by a sanitised colon (`equations- When`) becomes `, `,
    except after a script glyph (`W¹- Sobolev`);
  - a dash straight after `?` or `!` is dropped, and the next word is
    capitalised unless it is an identifier (`iOS`, `p-adic`).

**Measured.** **0** names contain `--`. **113** titles hold a `:` on disk,
which Finder shows as `/` (`small/large`, `L^∞/L¹`). Nothing rewrites those
apart from year ranges, so they stay as they are.

### 3.7 Ellipsis and ligatures — arrival only

Applied by `validators/filename_checker/text_processing.fix_ellipsis` and
`fix_ligatures`:

- `...` becomes `…`, outside mathematics.
- `ﬁ ﬂ ﬀ ﬃ ﬄ` are expanded to their letters.

**Measured.** 7 titles contain `…`. 2 contain `...`, both inside
mathematics (`ζ(2, ..., 2)`), which the rule leaves alone. **0** contain a
ligature.

---

## 4. Characters and length

### 4.1 NFC

Every path compares and writes **NFC** (`filename_normalizer`, `cmo`). The
sweep never proposes a rename that differs only in normalisation form
(`library_normalize.propose_renames`): APFS treats the two spellings as one
file.

**Measured.** 4,300 names are stored decomposed (NFD) on disk. That is
expected and harmless; every comparison normalises first.

### 4.2 Letters

All letters are kept as they are, in NFC. **`ß` is never converted to `ss`.**
No code does it, and the German guard in §3.1 relies on it.

### 4.3 Spaces and invisible characters

- **On every path**, runs of spaces collapse to one and the name is trimmed.
- **At arrival only** (`cmo._clean_for_fs`):
  - no-break, thin and other special spaces (U+00A0, U+2000–U+200A, U+202F)
    become ordinary spaces;
  - control characters (C0, DEL, C1) and every invisible format character
    (zero-width space, soft hyphen, byte-order mark, bidi marks) are removed.

**Measured.** **0** names carry a control or format character. **1**
carries a special space, and only arrival would replace it.

### 4.4 Length

- A whole name is **at most 255 bytes** in UTF-8; that is the filesystem's
  limit.
- At arrival the stem gets the limit less 4 bytes for `.pdf`. Authors go first
  (§2.6). Only if one author plus `, et al.` still does not fit is the title
  cut, at a word boundary.
- Conformance reports any proposal over 255 bytes as a violation.
- Separately, a paper's saved record is named stem + `.meta.json` and must
  fit in 251 bytes (`processing/identity.MAX_BASENAME_BYTES`). A longer one
  is stored under a hashed name.

**Measured.** The longest name is 255 bytes. 10 names are over 251 bytes,
and their records are hashed.

---

## 5. Not rules (no code enforces them)

Do not cite these as the convention:

- **The dash between co-equal names** (`Hamilton–Jacobi` with an en dash, a
  hyphen within one word) is house style, but no naming path enforces it:
  the arrival checker's `validators/filename_checker/tokenization.enforce_ndash_between_authors`
  is a placeholder that returns its input, and the dash whitelists only
  preserve. An owner phrase ruling is the only thing that sets a dash.
- **Small numbers spelled out** was removed: it turned `AR(1)` into
  `AR(one)`.
- **`core/sentence_case.to_sentence_case_academic`**, and the data it reads
  (`config/casing_decisions.json`, `config/title_casing.json`), are not on
  any live path (§3.1).
- **Bracket balance** is not checked when naming. The maths rule only refuses
  to convert inside unbalanced brackets.
- **Mixed scripts** produce a message only.
- **Per-language casing** beyond the German guard does not exist.

---

## 6. Where the code and the settled rulings disagree (open)

1. ~~Multi-letter initials collapse at arrival~~ — **fixed 2026-10-15**
   (§2.2). Arrival names no paper differently that is already on a shelf:
   `normalize_full_name` gives the same answer as before for all 25,251
   in-scope names.
2. ~~Title apostrophes at arrival~~ — **fixed 2026-10-15** (§3.4), with the
   same check over the same 25,251 names.
3. **A single-quoted passage arrives straight.** `'hot hand'` keeps its
   straight marks; the library writes `‘hot hand’` in 169 titles that
   arrived that way. The quotation rule (§3.3) converts double marks only.
   Pairing single marks needs care: after a word in `-s`, a closing quote
   and a possessive are the same character (`'reversals' and`).
4. **The Spelling page's *Name or ordinary word?* answers change no
   filename** (§3.1).
5. *By design, noted because nothing else checks it:* **a typed name is
   taken verbatim** (§0). None of the rules here is applied to it; only
   Conformance would later notice one that breaks an every-path rule.

---

## 7. Examples — real names that every path leaves unchanged

Each was checked on 2026-10-15 with `normalize_full_name`, which returned it
unchanged.

```
Averboukh, Yu. A. - Target problem for mean field type differential game.pdf     §2.2
Lions, P.-L. - Bifurcation and optimal stochastic control.pdf                     §2.1
Le Gall, J.-F. - Itô’s excursion theory and random trees.pdf                      §2.4, §3.4
Abi Jaber, E., de Carvalho, N. - Reconciling rough volatility with jumps.pdf      §2.4
Krasnosel'skii, M. A., Rutickii, Ya. B. - Convex functions and Orlicz spaces.pdf  §2.2, §2.5
Tuyls, K., Omidshafiei, S., et al. - Game plan, what AI can do for football, and what football can do for AI.pdf
                                                                                  §2.6, §3.6
0-1-Mürmann, M. G. - Erratum ‘A semi-Markovian model for the Brownian motion’.pdf §3.3
17-Assouad, P. - Démonstration de la « Conjecture de Chung » par Carleson.pdf     §3.3
1-Knight, F. B. - A transformation from prediction to past of an L²-stochastic process.pdf
                                                                                  §3.2
Andreescu, T., Feng, Z. - Mathematical olympiads 1999–2000, problems and solutions from around the world.pdf
                                                                                  §3.5
Rásonyi, M., Sayit, H. - Exponential utility maximization in small:large financial markets.pdf
                                                                                  §3.6 (Finder shows small/large)
Zagier, D. - Evaluation of the multiple ζ values ζ(2, ..., 2, 3, 2, ..., 2).pdf   §3.7
```
