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
within the filesystem byte limit (255 bytes UTF-8).  When not all
authors fit, the listed authors are followed by `, et al.`.

Algorithm:
1. Try all authors.  If the filename fits → done.
2. Binary-search for the largest *k* such that
   `Author1, …, Authork, et al. - Title.pdf` ≤ 255 bytes.

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

#### Other languages (Russian, Spanish, Italian, …)

Follow the capitalisation conventions of that language.

#### Language detection

Language is detected automatically via `langdetect` (imported in
`src/validators/filename_checker/core.py`) to apply language-specific
rules for capitalisation and quotation marks.

### 3.2 Dashes in titles

| Character | Unicode | Use | Example |
|-----------|---------|-----|---------|
| Hyphen `-` | U+002D | Compound adjectives, prefixes | `mean-field`, `long-time`, `path-dependent` |
| En-dash `–` | U+2013 | Between proper names (Name–Name) | `McKean–Vlasov`, `Black–Scholes` |
| Em-dash `—` | U+2014 | Parenthetical breaks (rare) | `…theory — a new approach` |

The name-dash whitelist (`data/name_dash_whitelist.txt`, 52 entries)
specifies the correct dash for each compound mathematician name.

**Rule:** `--` (double hyphen) is always normalised to en-dash `–`.

### 3.3 Quotation marks (language-specific)

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

### 3.4 Ellipsis

Three consecutive dots `...` are normalised to horizontal ellipsis `…`
(U+2026).  Implemented in `fix_ellipsis()`.

### 3.5 Small numbers

Isolated digits 0–9 in non-mathematical context are spelled out:
`2-dimensional` stays, but a lone `2` in text becomes `two`.
Implemented in `spell_out_small_numbers()`.

### 3.6 Title preservation

The following are always preserved as-is:

- Mathematical symbols: ℝ, ℤ, ≤, ∞, Γ, ζ, ^, ₜ, etc.
- Parentheses and brackets: `(0 < d < 2)`, `[d'après …]`
- Punctuation: commas, semicolons, apostrophes
- Superscript/subscript Unicode: ⁰¹²³⁴⁵⁶⁷⁸⁹, ₀₁₂₃₄₅₆₇₈₉

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

---

## 5. Filesystem Safety

### 5.1 Character replacements

Only filesystem-unsafe characters are replaced:

| Character | Replacement | Reason |
|-----------|-------------|--------|
| `/` | `–` (en-dash) | Path separator on Unix |
| `\` | `–` (en-dash) | Path separator on Windows |
| `:` | ` –` (space + en-dash) | Illegal on macOS HFS+/APFS |
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
