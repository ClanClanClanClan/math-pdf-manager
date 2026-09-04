# Filename Convention

This document is the authoritative specification for PDF filenames in the
library.  All filename generation, validation, and normalisation code must
conform to these rules.

**Canonical implementation:** `CMO.get_canonical_filename()` in
`src/arxivbot/models/cmo.py`.

**Validation:** `check_filename()` in
`src/validators/filename_checker/core.py`.

---

## 1. Format

```
Author1, I., Author2, I. - Title.pdf
```

| Component | Rule |
|-----------|------|
| Author section | All authors, `Lastname, Initials.` format, separated by `, ` |
| Separator | ` - ` (space + hyphen + space) |
| Title | Sentence case, full length, original language |
| Extension | `.pdf` |

---

## 2. Author Rules

### 2.1 Format: `Lastname, Initials.`

Each given name produces one initial (first letter, uppercase, followed
by a period).  Initials are concatenated with periods.

| Given name | Initials | Full format |
|------------|----------|-------------|
| Jean | J. | Dupont, J. |
| Jean-Pierre | J.-P. | Dupont, J.-P. |
| Paul André | P.A. | Krée, P.A. |
| Karl Theodor Hans | K.T.H. | Zheng, K.T.H. |
| S. C. P. (already initials) | S.C.P. | Yam, S.C.P. |

### 2.2 Name particles

Particles (de, el, van, von, d', l', in 't, …) stay with the family
name and are NOT capitalised unless the author conventionally
capitalises them.

| Full name | Formatted |
|-----------|-----------|
| Nicole el Karoui | el Karoui, N. |
| Thomas de Angelis | de Angelis, T. |
| Kees in 't Hout | in 't Hout, K. |
| Eduardo Abi Jaber | Abi Jaber, E. |

Multi-word family names are listed in `data/multiword_familynames_1.txt`
(444 entries).

### 2.3 Accented and non-Latin characters

Always preserved in **NFC** form (see §6).

| Name | Formatted |
|------|-----------|
| Dylan Possamaï | Possamaï, D. |
| Romuald Élie | Élie, R. |
| Leszek Słomiński | Słomiński, L. |

### 2.4 Multiple authors

Authors are separated by `, ` (comma + space).  Because initials also
use commas, the author section is a flat comma-separated list:

```
Dupont, J.-P., Martin, G., Krée, P.A. - Title.pdf
```

### 2.5 "et al." — dynamic truncation

As many authors as possible are listed while keeping the total filename
within the byte budget.  When not all authors fit, the listed authors
are followed by `, et al.`.

**The budget is 251 bytes, not 255.**  255 is the filesystem's limit on
the PDF's own name; every paper also has a sidecar whose name is the
stem plus `.meta.json`, and that has to fit too.  The margin is not
theoretical: 11 papers in the library sit in the [252, 255] range and
3 of them errored during the first real sidecar backfill.  The constant
is `processing.identity.MAX_BASENAME_BYTES`.

Algorithm:
1. Try all authors.  If the filename fits → done.
2. Binary-search for the largest *k* such that
   `Author1, …, Authork, et al. - Title.pdf` ≤ 251 bytes.

The title is **never** truncated — only the author list compresses.

---

## 3. Title Rules

### 3.1 Capitalisation: sentence case

Titles use **sentence case**: capitalise the first word and proper nouns
only.  Applied by `to_sentence_case_academic()` in
`src/core/sentence_case.py`.

#### English

| Rule | Example |
|------|---------|
| First word capitalised | `On the convergence of…` |
| Proper nouns capitalised | `…Brownian motion…`, `…Markov chains…` |
| Proper adjectives capitalised | `Bayesian`, `Gaussian`, `Euclidean`, `Laplacian` |
| Acronyms preserved | `BSDE`, `PDE`, `SDE`, `LIBOR`, `CVA` |
| Mixed-case brands preserved | `LaTeX`, `macOS`, `PyTorch`, `GitHub` |
| Compound names preserved (with correct dash) | `McKean–Vlasov`, `Black–Scholes`, `Fokker–Planck` |
| Technical prefixes stay lowercase (even at start) | `g-expectation`, `p-variation`, `α-stable`, `f-divergence` |
| Small words lowercase (unless first) | `a`, `an`, `the`, `and`, `or`, `of`, `in`, `to`, `for`, `by`, `on`, `at`, `with` |

#### French

Sentence case.  Proper nouns capitalised.

```
Les systèmes hamiltoniens et leur intégrabilité
Décomposition des difféomorphismes du tore… d'après Bourbaki
```

#### German

Nouns capitalised per German orthographic rules.

```
Stochastik für das Lehramt
```

#### Spanish

Sentence case.  Inverted punctuation marks (`¿`, `¡`) are preserved.

```
¿Existe una solución única para el problema de control óptimo?
```

#### Italian

Sentence case.  Proper nouns capitalised.

#### Russian and other non-Latin-script languages

Titles in Latin transliteration follow the capitalisation conventions
of the target language.  No automatic transliteration from Cyrillic or
other scripts is performed; names must be provided in Latin script by
the metadata source (ArXiv, Crossref, etc.).

The capitalisation whitelist (`config/config.yaml`) contains canonical
Latin spellings for mathematician names (e.g., Chebyshev not
Tchebycheff).

#### Language detection

Language is detected automatically via `langdetect` (imported in
`src/validators/filename_checker/core.py`) to apply language-specific
rules for capitalisation and quotation marks.

#### Language-specific punctuation spacing

French typography requires a thin non-breaking space (U+202F) before
`;`, `!`, `?`, and `:`.  This is **NOT** applied in filenames because
U+202F is stripped for filesystem safety (see §4.4).  Standard English
spacing (no space before punctuation) is used for all languages in
filenames.

### 3.2 Dashes in titles

| Character | Unicode | Use | Example |
|-----------|---------|-----|---------|
| Hyphen `-` | U+002D | Compound adjectives, prefixes, prefix + single word | `mean-field`, `long-time`, `G-expectation` |
| En-dash `–` | U+2013 | Between two proper names, or prefix + multi-word compound | `McKean–Vlasov`, `Black–Scholes`, `G–Brownian motion` |
| Em-dash `—` | U+2014 | Parenthetical breaks (rare in titles) | `…theory — a new approach` |

**Key distinction for prefixes (G-, p-, etc.):**
- Prefix + **single word** → **hyphen**: `G-expectation`, `G-martingale`, `G-framework`, `G-SDE`
- Prefix + **multi-word compound** → **en-dash**: `G–Brownian motion`, `G–Lévy process`, `G–stochastic control`, `G–white noise`

The name-dash whitelist (`data/name_dash_whitelist.txt`, 305 entries)
specifies the correct dash for each compound term.

**Rule:** `--` (double hyphen) is always normalised to en-dash `–`.

### 3.3 Subtitles and colons

Many papers have a main title and subtitle separated by a colon.
The colon is replaced with a **comma**, and the subtitle follows in
**lowercase** (sentence case continues — the subtitle is not a new
sentence).

| Source | In filename |
|--------|-------------|
| `Geometry: A Story` | `Geometry, a story` |
| `Optimal stopping: A new approach` | `Optimal stopping, a new approach` |
| `BSDEs: Theory and Applications` | `BSDEs, theory and applications` |

Other separators:

| Separator | In filename | Capitalisation after |
|-----------|-------------|---------------------|
| Period `.` | Preserved | Yes — treated as new sentence |
| Em-dash `—` | Preserved | No |
| Comma `,` | Preserved | No |

### 3.5 Quotation marks (language-specific)

Straight quotes are normalised to typographic quotes based on language.
Implemented in `fix_and_flag_quotes()` in
`src/validators/filename_checker/text_processing.py`.

| Language | Double quotes | Single quote / apostrophe |
|----------|--------------|--------------------------|
| English | `"…"` (U+201C / U+201D) | `'` (U+2019) |
| French | `«…»` (U+00AB / U+00BB) | `'` (U+2019) |
| German | `„…"` (U+201E / U+201D) | `'` (U+2019) |
| Spanish, Italian | `«…»` (U+00AB / U+00BB) | `'` (U+2019) |

Apostrophes in contractions (`it's`, `d'après`, `l'équation`) are
preserved as right single quotation mark (U+2019).

### 3.6 Ellipsis

Three consecutive dots `...` are normalised to horizontal ellipsis `…`
(U+2026).  Implemented in `fix_ellipsis()`.

### 3.7 Small numbers

Isolated digits 0–9 in non-mathematical context are spelled out:
`2-dimensional` stays, but a lone `2` in text becomes `two`.
Implemented in `spell_out_small_numbers()`.

### 3.8 Title preservation

The following are always preserved as-is:

- Mathematical symbols: ℝ, ℤ, ≤, ∞, Γ, ζ, ^, ₜ, etc.
- Parentheses and brackets: `(0 < d < 2)`, `[d'après …]`
- Punctuation: commas, semicolons, apostrophes
- Superscript/subscript Unicode: ⁰¹²³⁴⁵⁶⁷⁸⁹, ₀₁₂₃₄₅₆₇₈₉

### 3.9 Mathematical notation

Mathematical notation is preserved exactly as the source provides it.
No normalisation between ASCII and Unicode representations is performed.

| Both valid | Example |
|------------|---------|
| ASCII-style | `R^d`, `L_2`, `H^1` |
| Unicode | `ℝᵈ`, `L₂`, `H¹` |

Spacing within mathematical expressions is preserved as-is.

### 3.10 Roman numerals

Roman numerals in context (Part II, Volume III, Chapter IV) are
preserved as roman numerals and treated as acronyms (uppercase).
They are NOT converted to arabic numerals.

### 3.11 Abbreviations

Common abbreviations are preserved as the source provides them:
`vs.`, `i.e.`, `e.g.`, `cf.`, `etc.` — kept with their periods.
Not expanded to full words.  Note: `et al.` in the *title* is
preserved as-is; `et al.` in the *author section* has special
truncation semantics (see §2.5).

### 3.12 Ordinals

Ordinals in compound adjectives are preserved as digits: `2nd-order`,
`1st-kind`.  The number spelling rule (§3.7) does not apply to
ordinals because the digit is not isolated.

### 3.13 Apostrophes and the marks that look like them

**The rule is keyed on what the mark DOES, not on the language.**

The obvious guess is that this works like quotation marks, which are
famously per-language (« » French, „ " German, " " English). Checked, and
it does not: CLDR gives every locale its own `quotationStart` /
`quotationEnd` and defines **no apostrophe element in any locale, ever**,
and every national authority prescribes the same 9-shaped raised comma
for elision — Imprimerie nationale (Lacroux), Accademia della Crusca,
Duden, Onze Taal, IEC, RAE, Chicago 6.117. Nobody flips it.

The real axis is **punctuation versus letter**, which Unicode encodes as
different characters (core spec §6.2.7): U+2019 where the mark is a
punctuation apostrophe, U+02BC where it is a modifier *letter*. Which
side a name falls on **is** language-dependent, and CLDR settles it in
`exemplarCharacters`: Ukrainian's and Breton's alphabets contain U+02BC,
Hawaiian's contains U+02BB (turned the other way), while French, Italian,
Irish and Dutch contain no apostrophe at all — theirs is punctuation.

| function | example | character |
|---|---|---|
| Elision (a dropped letter or article) | `d'Auria`, `dell'Antonio`, `in 't Hout`, `l'équation` | punctuation apostrophe |
| Possessive / English contraction | `Itô's formula`, `don't` | punctuation apostrophe |
| Anglicised Irish/Scottish prefix | `O'Connell`, `O'Neill` | punctuation apostrophe |
| German derivational `-'sch` (Duden §62) | `Green'schen`, `Gibbs'sche` | punctuation apostrophe |
| Flemish fused prefix (capital, no space) | `T'Joens` | punctuation apostrophe |
| **Transliterated Cyrillic soft sign ь** | `Kolokol'tsov`, `Ural'tseva` | **not an apostrophe** — a letter (U+02B9 by ISO 9 / ALA-LC) |
| **Breton `c'h` trigraph** | `Le Floc'h`, `Le Balc'h` | **not an apostrophe** — part of a letter (U+02BC officially) |
| **Mathematical prime** | `f'`, `X'_t`, `L'(θ)` | **not an apostrophe** — U+2032 |

#### What this library writes

**Author block: U+0027 APOSTROPHE.** The author block is a *key*, not
prose — Search, the sort order, the duplicate detector and every
comparison against zbMATH, arXiv, ORCID and Crossref run on it, and
uniformity beats typography there. Measured: those authorities are
**99.95% U+0027** across 1,909 name records, and Unicode's own
identifier-comparison data (UTS #39 `confusables.txt`) maps U+2019 *to*
U+0027, not the reverse. Its U+2019 preference is explicitly scoped to
"when text is set".

**Title: U+2019** for a punctuation apostrophe, because a title is set
prose and that is what every authority above prescribes. A title U+0027
is *not automatically wrong*: an unmeasured share of the 1,343 in the
corpus are mathematical primes (`f'`, `X'`), and converting those to
U+2019 would silently change their meaning. **The title rule therefore
applies to new files only; there is no retroactive sweep.**

That the two fields carry different characters is deliberate. They have
different jobs — the author block is matched by machines, the title is
read by a person.

#### Matching folds them; naming does not

No normalisation form equates these marks: NFC, NFD, NFKC, NFKD and
casefold all leave U+0027 and U+2019 distinct. That is categorically
unlike the NFD/NFC accent trap (§6), where normalising repairs the match.
So `processing.apostrophes.fold_marks` maps every apostrophe-like mark to
one key for **Search and duplicate detection only** — including the ones
that are *not* apostrophes, because the goal is to make them match, not
to claim they are the same thing. A test asserts no naming path imports
it.

#### Known defects in the corpus (measured, not swept)

- `in t'Hout` — the mark is on the wrong side; the physicist is Karel
  **in 't Hout** (elided *het*). One file.
- `dell'utilit`a` — LaTeX accent residue for `utilità`. One file.
- Seven titles open a quotation with `'` and close it with `'`, two of
  them doubled (`''…''`) where a double quotation mark belongs. These are
  unbalanced *pairs*, not stray apostrophes, and must be repaired as
  pairs — a blanket rule would destroy legitimate opening quotes.
- `Gal'Čuk` — the interior capital is title-casing damage: Python's
  `str.title()` capitalises after every apostrophe-like character, so
  `le floc'h`.title() gives `Le Floc'H`. Fix the caser, not just the file.
- ~90 files in the Cyrillic soft-sign class use U+0027. The standards
  genuinely conflict here (ISO 9 / ALA-LC / AMS say prime; BGN/PCGN says
  U+2019), so this is a policy decision and **not** a sweep. Note also
  that U+02B9 is a *fatal* error under pdflatex and unencodable in
  cp1252, which the BibTeX and CSV exports rely on.

### 2.6 Name particles (de, van, Le, Di, El, …)

**A particle takes a capital when it is part of the surname, and stays
lower case when it is a preposition.** The test is whether it can be
dropped: Alexis *de* Tocqueville is "Tocqueville", so `de` is a link
word; Jean-François Le Gall is never "Gall", so `Le` is part of the name.

| stays lower case — preposition | takes a capital — part of the name |
|---|---|
| French `de`, `d'` | French articles `Le`, `La`, `Du`, `Des` (`Du`/`Des` = *de+le*, *de+les*) |
| German `von`, `zu` | Modern Italian `De`, `Di`, `Da`, `Del`, `Della` |
| Netherlands Dutch `van`, `van der`, `de`, `den`, `ter` | Flemish, Afrikaans and American Dutch `Van`, `De` (fixed by registration) |
| Portuguese/Spanish `de`, `da`, `dos`, `das` | Latin-script Arabic/Hebrew `El`, `Al`, `Ben` |

Exceptions that are real, not sloppiness: Italian *falsi cognomi*
(`da Vinci`, `de' Medici`) are epithets rather than surnames and stay
lower case, as do Italian noble predicates — which is why **`de Finetti`
is correctly lower case**. Lower-case `al-`/`el-` is right only for
*transliterated medieval* figures, and then it carries a hyphen
(`al-Khwārizmī`); every living author has a Latin-script legal name and
publishes capitalised.

**The bearer's own usage overrides the rule** (`du Bois-Reymond` keeps a
lower-case *du* against the French rule, because the family fixed it).

**This is a per-person list, not a rule keyed on the particle**, because
nationality is not recoverable from the particle: `da Prato` is Italian
and takes a capital, `da Silva` is Portuguese and does not. The list is
`config/author_surnames.yaml`; the owner can switch any entry off from
Settings → Author surnames, and that veto is stored with the library.

**Scope: the author block only.** In a title the same letters are
ordinary words — French and Dutch prose, *le Monde*. A rule that crossed
the separator once turned the mathematician "Makovski" into "Markovski".

Researched 2026-09-03 against the LC name authority file, RDA/LC-PCC,
Chicago 8.5 / 8.7–8.11 / 14.21 / 16.71, the Imprimerie nationale via
Lacroux, the Accademia della Crusca, Taalunie/Onze Taal, zbMATH and
arXiv. Note that `Surname, I. I.` is the *inverted bibliographic entry*,
not Chicago's "surname used alone": CMOS 14.21 keeps a lower-case
particle lower case there (its own example, `du Maurier, Daphne.`), which
is why Dutch `van` and German `von` do **not** take a capital here even
though a bare surname in prose would.

Measured over the library: 118 rulings, 594 files. Two proposed changes
were refuted on re-checking and are deliberately absent — `de Feo` and
`de Vries`, where the research had found the wrong person.

Tests: `tests/safety/test_author_surname_authority.py`.

---

### 3.14 Institution names vs. descriptions

A generic word — *University*, *Society*, *Institute* — is **capitalised
when it is part of an institution's official name** and **lower-case when
it is merely descriptive** (Chicago 8.68):

| Capitalised — a name | Lower-case — a description |
|---|---|
| `Rutgers University` | `a university course` |
| `the University of Durham` | `the Lvov school of mathematics` |
| `London Mathematical Society` | `CIMPA summer school` |
| `Indian Statistical Institute` | `the French school of probability` |

The distinction is not recoverable from the text. A mechanical rule
—"capitalise the generic when the preceding word is a proper name"— was
written and **measured**: it got 3 of the 6 universities in this library
right, missed `Brown University` (because *brown* is a colour) and fired
on `Lvov school` and `French school`, which are movements rather than
places. Only knowing which institutions exist separates them, so the
knowledge is **written down** in `config/config.yaml`
(`capitalization_whitelist`) rather than guessed at.

**A config entry can only preserve, never impose.** It stops the caser
lowering a capital that is already correct; it cannot add one to
`rutgers university`. That limit is structural and deliberate — it is
what keeps a one-line config edit from becoming a bulk rename of the
library. Imposing a spelling on already-lower-case text is the separate
power of an owner *phrase ruling* (`title_vocab.decide_phrase`), which
matches case-insensitively and rewrites the span.

Measured 2026-09-02 over all 25,252 in-scope PDFs: the entries rename
nothing — they prevent damage rather than repair it. Twelve titles do
hold a lower-case institution name and would only be corrected by phrase
rulings, which are the owner's call.

**Where the owner does this.** Settings → **Name phrases** lists every
multi-word name already in the whitelist that is not yet ruled, with a
measured count of how many filenames spell it differently today, and
rules or revokes one with a click. Ruling changes only what the namer
*would* do; Maintenance → *Normalize existing filenames* is where the
resulting renames are reviewed and applied reversibly. The two are
deliberately separate steps.

Measured 2026-09-02 over 29,512 filenames: 16 phrases would fix 28 files
between them, and for every one of those phrases the count shown and the
number the renamer actually changes agree exactly.

Tests: `tests/safety/test_institution_names_keep_their_capitals.py`,
`tests/test_processing/test_phrase_impact.py`,
`tests/ui/test_phrase_rulings_section.py`.

### 3.15 German sharp-s and special letters

German `ß` is preserved as-is, never converted to `ss`.  Spanish
inverted punctuation (`¿`, `¡`) is preserved.  All diacritics and
special letters from any language are preserved in NFC form.

---

## 4. Text Normalisation Rules

### 4.1 Ligature expansion

PDF extraction sometimes produces Unicode ligatures.  These are
expanded to their component ASCII letters.  Implemented in
`fix_ligatures()` in `src/validators/filename_checker/text_processing.py`.

| Ligature | Expansion |
|----------|-----------|
| ﬁ (U+FB01) | fi |
| ﬂ (U+FB02) | fl |
| ﬀ (U+FB00) | ff |
| ﬃ (U+FB03) | ffi |
| ﬄ (U+FB04) | ffl |

### 4.2 Whitespace normalisation

- Multiple spaces → single space
- Trailing/leading spaces → removed
- Space before comma → removed (`Possamaï , D.` → `Possamaï, D.`)
- Missing space after comma → added (`Possamaï,D.` → `Possamaï, D.`)

### 4.3 Parentheses and brackets

Must be balanced.  Every opening `(`, `[`, `{` must have a matching
closing `)`, `]`, `}`.  Unmatched delimiters are flagged by validation.
Mathematical angle brackets `⟨…⟩` are also checked.

### 4.4 Non-breaking and special spaces

All spaces in filenames are regular spaces (U+0020).

| Character | Unicode | Action |
|-----------|---------|--------|
| Non-breaking space | U+00A0 | Replaced with regular space |
| Narrow no-break space | U+202F | Stripped (in dangerous Unicode list) |
| Thin space | U+2009 | Replaced with regular space |
| Em space, en space, etc. | U+2000–U+200A | Replaced with regular space |

This means French thin-space-before-punctuation is NOT preserved in
filenames.  This is by design — filesystem tools and terminal
emulators handle special spaces poorly.

---

## 5. Filesystem Safety

### 5.1 Character replacements

Only filesystem-unsafe characters are replaced:

| Character | Replacement | Reason |
|-----------|-------------|--------|
| `/` | `–` (en-dash) | Path separator on Unix |
| `\` | `–` (en-dash) | Path separator on Windows |
| `:` | `,` (comma) | Illegal on macOS HFS+/APFS; also subtitle convention (see §3.3) |
| Control chars U+0000–U+001F | removed | Invisible / illegal |

All other characters are preserved, including `( ) [ ] & * + = < > ' "`.

### 5.2 Dangerous Unicode removal

The following invisible/malicious Unicode characters are silently
removed.  Implemented in `sanitize_unicode_security()` in
`src/validators/filename_checker/unicode_utils.py`.

| Category | Characters removed |
|----------|--------------------|
| Bidirectional overrides | U+202A–U+202E (LRE, RLE, LRO, RLO, PDF) |
| Zero-width | U+200B (ZWSP), U+200C (ZWNJ), U+200D (ZWJ) |
| Direction marks | U+200E (LRM), U+200F (RLM) |
| Byte-order mark | U+FEFF (BOM) |
| Invisible operators | U+2060–U+2064 (word joiner, function application, invisible times/separator/plus) |
| Narrow no-break space | U+202F |

### 5.3 Mixed-script detection

Filenames mixing Latin with Cyrillic or other scripts are flagged
(potential homograph attack), **except** when the non-Latin characters
are mathematical symbols (Greek letters, blackboard bold, etc.).

### 5.4 Filename length

- Maximum: **255 bytes** UTF-8 (filesystem `NAME_MAX`).
- Auto-detected via `os.pathconf()`.
- Author list is compressed (→ "et al.") to fit; title is never
  truncated.

---

## 6. Unicode Normalisation

### 6.1 NFC everywhere

All text (titles, author names, filenames) uses **NFC** (Canonical
Decomposition followed by Canonical Composition).

macOS stores filenames in **NFD** (decomposed: `e` + combining accent).
All code must normalise to NFC before comparison or storage.

| Form | Example for é | Bytes |
|------|--------------|-------|
| NFC (correct) | U+00E9 (single code point) | 2 bytes |
| NFD (macOS disk) | U+0065 + U+0301 (e + combining acute) | 3 bytes |

Implemented via `unicodedata.normalize("NFC", text)` and the `nfc()`
helper in `src/validators/filename_checker/unicode_utils.py`.

---

## 7. Whitelists and Data Files

| File | Purpose | Entries |
|------|---------|--------|
| `config/config.yaml` → `capitalization_whitelist` | Mathematician/scientist names with exact capitalisation | 500+ |
| `data/name_dash_whitelist.txt` | Compound names with correct dash type (Black–Scholes, etc.) | 52 |
| `data/name_dash_whitelist_1.txt` | Extended compound name list | 100+ |
| `data/multiword_familynames_1.txt` | Multi-word family names (Abi Jaber, de Angelis, etc.) | 444 |
| `data/known_words_1.txt` | Dictionary for spell-checking | 1,228 |
| `src/core/sentence_case.py` → `MATH_TECHNICAL_PREFIXES` | Single-letter prefixes that stay lowercase | 30+ |
| `src/core/sentence_case.py` → `mixed_case_words` | Brands: LaTeX, macOS, PyTorch, etc. | 20+ |
| `src/core/sentence_case.py` → `proper_adjectives` | Bayesian, Gaussian, Markovian, etc. | 6+ |

---

## 8. Validation Pipeline

The full validation pipeline (`check_filename()` in
`src/validators/filename_checker/core.py`) applies these steps in order:

1. **NFC normalisation** — convert NFD → NFC
2. **Dangerous Unicode removal** — strip BOM, bidi overrides, zero-width
3. **Ligature expansion** — ﬁ → fi, ﬂ → fl, etc.
4. **Parse authors and title** — split on ` - ` separator
5. **Language detection** — via `langdetect`
6. **Sentence case conversion** — `to_sentence_case_academic()`
7. **Dash normalisation** — `--` → `–`, whitelist lookup for names
8. **Quotation mark conversion** — language-specific typography
9. **Ellipsis normalisation** — `...` → `…`
10. **Small number spelling** — isolated digits → words
11. **Whitespace cleanup** — collapse doubles, fix comma spacing
12. **Length check** — verify ≤ 255 bytes UTF-8

---

## 9. Implementation Map

### Filename generators

| Generator | File | Purpose | Matches spec? |
|-----------|------|---------|--------------|
| `CMO.get_canonical_filename()` | `src/arxivbot/models/cmo.py` | **Primary** — library filing | Yes |
| `enhanced_parser._generate_filename_from_metadata()` | `src/pdf_processing/parsers/enhanced_parser.py` | Deprecated fallback | No |
| `academic_downloader._generate_filename()` | `src/downloader/academic_downloader.py` | Temporary download name | No |
| `version_detection.generate_filename_with_version()` | `src/downloader/version_detection.py` | Versioned download name | No |
| `proper_downloader._generate_filename()` | `src/downloader/proper_downloader.py` | Temporary download name | No |
| `discovery.generate_filename()` | `src/discovery/integration.py` | Temporary download name | No |

### Filename parsers (inverse operation)

| Parser | File | Purpose |
|--------|------|---------|
| `parse_filename()` | `ml/pdf-meta-llm/scripts/extract_text.py` | Training data extraction |
| `parse_authors_and_title()` | `src/validators/filename_checker/author_processing.py` | Validation |

### Core modules

| Module | File | Purpose |
|--------|------|---------|
| `to_sentence_case_academic()` | `src/core/sentence_case.py` | Title capitalisation |
| `check_filename()` | `src/validators/filename_checker/core.py` | Full validation pipeline |
| `sanitize_unicode_security()` | `src/validators/filename_checker/unicode_utils.py` | Dangerous char removal |
| `fix_ellipsis()` | `src/validators/filename_checker/text_processing.py` | Ellipsis normalisation |
| `fix_ligatures()` | `src/validators/filename_checker/text_processing.py` | Ligature expansion |
| `fix_and_flag_quotes()` | `src/validators/filename_checker/text_processing.py` | Quote typography |
| `spell_out_small_numbers()` | `src/validators/filename_checker/text_processing.py` | Number spelling |
| `find_math_regions()` | `src/validators/filename_checker/math_utils.py` | Protect math from fixes |

---

## 10. Examples

```
Touzi, N. - A note on BSDEs.pdf
el Karoui, N., Rouge, R. - Pricing via utility maximization and entropy.pdf
Dupont, J.-P., Martin, G., Krée, P.A. - On the convergence of SGD in ℝ^d.pdf
Achdou, Y., Lasry, J.-M., Lions, P.-L., Moll, B. - Income and wealth distribution in macroeconomics, a continuous-time approach.pdf
Rogers, L.C.G., Walsh, J.B. - A(t,Bₜ) is not a semimartingale.pdf
Roynette, B., Yor, M. - Couples de Wald indéfiniment divisibles. Exemples liés à la fonction Γ d'Euler et à la fonction ζ de Riemann.pdf
Omidshafiei, S., Hennes, D., Garnelo, M., et al. - Multiagent off-screen behaviour prediction in football.pdf
Golse, F. - Validité de la théorie cinétique des gaz, au-delà de l'équation de Boltzmann [d'après T. Bodineau, I. Gallagher, L. Saint-Raymond, S. Simonella].pdf
```
