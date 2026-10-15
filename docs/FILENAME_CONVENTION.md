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

### 2.7 Generational suffixes: `Jr.`

The library writes a suffix two ways, and both are the owner's: typed by hand
over the same years (2006–2025, by each record's original filename).

| form | blocks | people |
|---|--:|--:|
| `Cruz Jr., J. B.`: inside the surname | 32 | 11 |
| `Smith, Jr., A. A.`: its own part, between surname and initials | 9 | 8 |

Neither form follows the paper. Of the 18 papers whose first pages print the
name one way, the shelf matches the print in 5 (`Jonathan E. Ingersoll, Jr.`
is shelved `Ingersoll Jr., J. E.`). So **a name keeps the form it has**, and
no rule picks between them.

A suffix is `Jr`, `Sr`, `II`, `III` or `IV`, with or without a full stop
(`filename_ground_truth.is_generational_suffix`, the decomposer's own model
of an author block; the arrival parser asks the same function).
`Wewcomb II, R. T.` is the one numeral in the library.

- **At arrival**, `ingest.parse_authors_string` reads a suffix written apart
  into `cmo.Author.suffix`, and `cmo.author_segment` writes it back in the
  same place. A suffix inside the surname stays in `Author.family`. The
  refit `library_normalize._fit_to_limit` uses the same parser and the same
  `author_segment`, and drops an author together with the suffix.
- **On existing names**, nothing touches a suffix.

Until 2026-10-15 the parser read `Jr.` as initials (a capital, a lower-case
letter, a full stop), so the 9 blocks written apart came back as one author:
`Krusell, P., Smith, Jr., A. A.` became `Krusell, P. S. J. A. A.`, and
`Clancy, Jr., D.` became `Clancy, J. D.`.

**Measured.**
- 41 author blocks carry `Jr.`. Parsed and rebuilt by the arrival namer, each
  comes out exactly as it is on the shelf: **41 of 41** (the old code: 32).
  The `II` block does too.
- Over all 18,760 distinct author blocks, the parse changed for those 9 and
  no others.
- The refit rebuilds 24,691 of 25,196 names exactly (the old code: 24,683).
  It gained 8 and lost none. The ninth block sits behind `Astérisque 213 - `,
  which the refit does not split off.
- Where a suffix reaches arrival: 2 of the 2,206 PDFs waiting in staging with
  an /Author field carry one, both written in full (`James E. Fuson III`,
  `Danilo Jr Dela Cruz`). None writes `Surname, Jr., I.`. In practice that
  form arrives through a name typed in the Sort Queue box, which is parsed
  for its folder, and through the refit. A suffix written in full is still
  read wrongly (§6).

**`Dr. Z` is left alone.** It is a pen name (William Ziemba's column), on 3
files named by hand in 2006 and filed under `D`. Nothing in the string tells
it apart from an honorific in front of a real name (`Dr. John Smith` should
lose the `Dr.`), so a round trip would mean listing one pen name, for a
parse that no path makes. Every path leaves the three names unchanged, the
refit only touches names over 255 bytes, and the PDFs' /Author fields read
`ISDN`, `William Ziemba` and `ISDN`. The known cost: typed in the Sort Queue
box, `Dr. Z - …` would be filed under `Z`. A strict xfail in
`tests/safety/test_generational_suffix_at_arrival.py` records this.

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
- One quotation per title is converted: a pair of double marks, or a single
  quotation with at least one straight mark (`'hot hand'`, and the
  `‘hot hand'` that publishers' metadata often carries). Two quotations,
  nesting (`"… 'risk-free' …"`), an odd number of marks, or marks that cannot
  be paired with certainty are left as they are.
- A straight `"` between two letters is an inch mark, not a quote.
- **Single marks** (since 2026-10-15, `quote_marks._single`). Where a single
  quotation opens and closes is defined once, in `processing/apostrophes.py`,
  which needs it to judge a mark after `s`: it opens at a `‘`, or at a
  straight mark that starts a word before a letter; it closes at the first
  mark after it that ends a word. The trouble is that after a word in `-s`
  a closing quote and a plural possessive are the same character in the
  same place (`the 'reversals' and` against `Walras' law`). So the pair is
  made only when that first closing mark can be nothing else -- it ends a
  word of two letters or more that does not end in `s` -- or when no other
  mark after it could close instead:
  - `Dynamic preference 'reversals' and time inconsistency` → `‘reversals’`
    (the only mark that could close);
  - `Louis Bachelier's 'Théorie de la spéculation', the missing piece in
    Walras' general equilibrium` → `‘Théorie de la spéculation’`, and
    `Walras’` is a possessive (the quotation closed after `spéculation`);
  - `'Walras' law' revisited` is left as it is: `Walras'` may close the
    quotation or be a possessive inside it.
  The apostrophes are settled first (§3.4), so a straight mark still standing
  is never a certain apostrophe. `'Tis` is an elision, not an opener.
  An elision at both ends of a word (`rock 'n' roll`) would be paired; the
  library has none.
- The language is that of the **title around the quotation**, not of the
  quoted words or the authors' names (`quote_marks.quotation_language`,
  since 2026-10-15). The seeded detector reads the title; then small words
  outside the quotation that only English or only French uses decide between
  those two. Any other answer, or none, leaves the marks as they are.
- **Applied at arrival only**, and only when the title holds a straight mark
  that may belong to a quotation -- a straight `"`, or a straight `'` in a
  title where a single quotation opens (`quote_marks.holds_straight_quotation`,
  used by `check_filename` and
  `validators/filename_checker/text_processing.convert_straight_quotes_to_proper`).
  Quotation marks that all arrived curly are left as they arrived. A mark of
  the pair inside mathematics leaves the title as it is.
- Whatever is left is said: the importer adds "quotation marks left as they
  are: <why>" (`requote`'s reason) to `check_filename`'s messages.
- No sweep applies it to names already filed; the module's own docstring
  calls for a per-file review instead.
- Search and same-paper detection fold every form of a quotation to one key
  (`quote_marks.fold_quotes` takes out the pair `requote` would make), so
  `'hot hand'`, `‘hot hand'`, `‘hot hand’`, `"hot hand"` and `« hot hand »`
  all match. A straight mark that only looks like an opener is kept:
  `in 't Hout` still matches `in ’t Hout`.
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

**Measured, single quotations at arrival** (2026-10-15, read-only, old code
against new over the 25,251 in-scope names):

- **175** titles write a single quotation, one per title, every one as `‘…’`.
  76 of them close it straight after an `s`.
- Each of the 175, with every single mark made straight and passed through
  the arrival namer: **172** come out exactly as shelved (the old code: 0).
  The same 172 with the opener curly and the rest straight (`‘…'`).
  The other 3: two are the colon rule (§3.6), and one is nested
  (`"Option pricing theory, is ‘risk-free’ hedging feasible?"`), which is
  left as it arrived and says why. The old code turned its double marks
  into `‘…’` and left the inner ones straight.
- The titles papers actually arrived with (records' original filenames,
  1,282 holding a straight mark): **14** are named differently, **12** of
  them now exactly as shelved (the old code: none of the 14); the other two
  are the colon rule and the nested title above. Also left as they arrived,
  with the reason: TeX-style `‘‘early warning''` (two openers).
- Double marks: of the 234 titles whose quotation was made into straight
  double marks, 0 are named differently.
- `normalize_full_name`: 0 of the 25,251 proposals differ.
- Matching keys, over the 27,887 in-scope and To-be-sorted names: the
  same-paper title key differs for 1, `Indeterminateness and ‘the' universe
  of sets…` in To be sorted, which now folds like `‘the’`. Surname keys: 0
  differ. Of the 51 quoted shelf titles whose original filename has a
  straight mark, the two now fold alike for 47 (the old code: 33).

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
- a quotation mark. That is the quotation rule's business (§3.3), which
  runs next and pairs `'hot hand'` into `‘hot hand’` when the pairing is
  certain, and otherwise leaves both marks straight;
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
  arrival namer with every mark straightened. **1,685** come out exactly as
  they are on the shelf (before 2026-10-15: 0; with apostrophes fixed but
  single quotations still straight: 1,513).
  - The other 14 come from the colon rule (7), TeX `''` (3), two shelf
    titles that keep straight double marks the quotation rule converts
    (`Une preuve "standard" …`, §3.3), casing (1, `Euclid’s Elements`), and
    the one nested quotation (§3.3).
  - Not one differs at an apostrophe, and none at a single quotation that
    could be paired.

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
expected and harmless, because every comparison normalises first.

The arrival parser did not, until 2026-10-15. A decomposed `É.` was not an
initial to it, so `Amar, É., Matheron, É.` read as one author. That
happened to 161 of the 3,215 distinct author blocks with an accent when they
were decomposed; now it happens to none. The effect was small. A folder is
chosen by the first surname, which survived; the refit is handed composed
names; and 1 of the 2,206 /Author fields waiting in staging is decomposed,
not in initials. What was lost was the other authors, in the check of a
typed or already-canonical name against the paper's own text.

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
3. ~~A single-quoted passage arrives straight~~ — **fixed 2026-10-15**
   (§3.3): a certain single quotation takes the language's outer marks,
   `'hot hand'` → `‘hot hand’`, and an uncertain one is left as it arrived
   with the reason. 172 of the library's 175 single-quoted titles now arrive
   exactly as shelved (before: 0); `normalize_full_name` gives the same
   answer as before for all 25,251 in-scope names.
   *Still open, by the module's own rule:* a quotation nested in another
   (`"… 'risk-free' …"`, 1 title) is left as it arrived rather than written
   `‘… “risk-free” …’`.
4. **The Spelling page's *Name or ordinary word?* answers change no
   filename** (§3.1).
5. *By design, noted because nothing else checks it:* **a typed name is
   taken verbatim** (§0). None of the rules here is applied to it; only
   Conformance would later notice one that breaks an every-path rule.
6. **Where a new paper's suffix goes is unruled** (§2.7). A suffix written
   in full, as arXiv and PDF metadata write names, is taken for the surname:
   `H. Rumsey Jr.` arrives as `Jr., H. R.` (the library has `Rumsey Jr., H.`),
   `James E. Fuson III` as `III, J. E. F.`, and `Anthony A. Smith, Jr.` as
   `Anthony A. Smith, Jr.`, filed under J, I and A. Crossref gives the suffix
   as a field of its own, and arrival drops it (`Smith, A. A.`). Fixing
   either means choosing between the owner's two forms, or dropping the
   suffix, and that is his choice: neither form follows the paper (§2.7).
   Measured: 2 of the 2,206 /Author fields waiting in staging carry one.
   Related: since the multi-letter fix (§2.2) an honorific is read as an
   initial, so `Dr. John Smith` arrives as `Smith, Dr. J.` (before:
   `Smith, D. J.`; both wrong).

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
Krusell, P., Smith, Jr., A. A. - Income and wealth heterogeneity in the macroeconomy.pdf
                                                                                  §2.7
Itô, K., McKean Jr., H. P. - Diffusion processes and their sample paths.pdf       §2.7
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
