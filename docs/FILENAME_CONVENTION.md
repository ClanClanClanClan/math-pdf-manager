# Filename Convention

This document specifies the canonical filename format used throughout the
PDF library.  All filename generation code must conform to this spec.

## Format

```
Author1, I., Author2, I. - Title.pdf
```

### Components

1. **Author section** — all authors in `Lastname, Initials.` format,
   separated by `, ` (comma + space).
2. **Separator** — always ` - ` (space-dash-space).
3. **Title section** — full title as it appears on the paper.
4. **Extension** — `.pdf`.

## Author Rules

### Initials

Each given name produces one initial.  Hyphenated given names produce
hyphenated initials.

| Given name | Initials |
|------------|----------|
| Jean | J. |
| Jean-Pierre | J.-P. |
| Paul André | P.A. |
| Karl Theodor Hans | K.T.H. |
| S. C. P. (already initials) | S.C.P. |

### Name particles

Particles stay with the family name.  They are NOT capitalised unless
the author conventionally capitalises them.

| Full name | Formatted |
|-----------|-----------|
| Nicole el Karoui | el Karoui, N. |
| Thomas de Angelis | de Angelis, T. |
| Kees in 't Hout | in 't Hout, K. |

### Accented characters

Always preserved.  NFC Unicode normalisation is used (not NFD).

| Name | Formatted |
|------|-----------|
| Dylan Possamaï | Possamaï, D. |
| Romuald Élie | Élie, R. |
| Leszek Słomiński | Słomiński, L. |

### "et al." truncation

As many authors as possible are listed while keeping the total
filename within the filesystem limit (255 bytes UTF-8).  When not all
authors fit, the listed authors are followed by `, et al.`.

The algorithm is:
1. Try listing all authors.  If the filename fits → done.
2. Otherwise, binary-search for the largest *k* such that
   ``Author1, …, Authork, et al. - Title.pdf`` fits within 255 bytes.

This means short titles allow more authors and long titles force
earlier truncation — the title is never shortened.

### Multiple authors: separator

Authors are separated by `, ` (comma + space).  This is the same
separator used between a lastname and its initials, so the author
section is a flat comma-separated list:

```
Dupont, J.-P., Martin, G., Krée, P.A. - Title.pdf
```

## Title Rules

### Capitalisation: sentence case

Titles use **sentence case**: capitalise the first word and proper
nouns only.  This is applied by `to_sentence_case_academic()` in
`src/core/sentence_case.py`.

**English titles:**
- First word capitalised.
- Proper nouns and adjectives derived from proper nouns capitalised
  (Bayesian, Gaussian, Markovian, Euclidean, Laplacian, …).
- Acronyms preserved (BSDE, PDE, SDE, LIBOR, CVA, …).
- Mixed-case terms preserved exactly (LaTeX, macOS, PyTorch, …).
- Compound names with dashes preserved from the name-dash whitelist
  (Black–Scholes, McKean–Vlasov, Fokker–Planck, Itô–McKean, …).
- Technical single-letter prefixes stay lowercase even at the start
  of a title (g-expectation, p-variation, α-stable, …).

**French titles:**
- Sentence case: ``Les systèmes hamiltoniens et leur intégrabilité``
- Proper nouns capitalised: ``… d'après Bourbaki``

**German titles:**
- All nouns capitalised per German rules: ``Stochastik für das Lehramt``

**Russian/other languages:**
- Follow the capitalisation conventions of that language.

### Preserve content

- Mathematical symbols: ℝ, ℤ, ≤, ∞, Γ, ζ, ^, etc.
- Parentheses and brackets: `(0 < d < 2)`, `[d'après ...]`
- Punctuation: commas, semicolons, en-dashes (–), apostrophes

### Dashes in titles

Three types of dash, each with a specific role:

| Character | Unicode | Use in titles | Example |
|-----------|---------|---------------|---------|
| Hyphen `-` | U+002D | Compound adjectives, prefixes | `mean-field`, `long-time`, `path-dependent` |
| En-dash `–` | U+2013 | Between proper names (Name–Name) | `McKean–Vlasov`, `Black–Scholes`, `Fokker–Planck` |
| Em-dash `—` | U+2014 | Parenthetical breaks (rare in titles) | — |

The name-dash whitelist (`data/name_dash_whitelist.txt`) specifies
the correct dash for each compound mathematician name.

### No truncation

The title is never truncated.  The author list is compressed (via
"et al.") instead when the filename would exceed filesystem limits.

### Exceptions and whitelists

The following data files control capitalisation:

| File | Purpose |
|------|---------|
| `config/config.yaml` → `capitalization_whitelist` | 500+ mathematician/scientist names with exact capitalisation |
| `data/name_dash_whitelist.txt` | Compound names with correct dash type |
| `src/core/sentence_case.py` → `MATH_TECHNICAL_PREFIXES` | Single-letter prefixes that stay lowercase |
| `src/core/sentence_case.py` → `mixed_case_words` | Terms like LaTeX, PyTorch |
| `src/core/sentence_case.py` → `proper_adjectives` | Bayesian, Gaussian, etc. |

### Character replacements

Only filesystem-unsafe characters are replaced:

| Character | Replacement | Reason |
|-----------|-------------|--------|
| `/` | `–` (en-dash) | Path separator |
| `\` | `–` (en-dash) | Path separator |
| `:` | ` –` (space + en-dash) | Illegal on some FS |
| Control chars (U+0000–U+001F) | removed | Invisible |

All other characters are kept as-is, including `( ) [ ] & * + = < > ' "`.

## Filesystem limits

- Maximum total filename: **254 bytes** UTF-8 (250 + `.pdf`).
- If exceeded: title is truncated from the end, keeping whole UTF-8
  characters.

## Examples

```
Touzi, N. - A note on BSDEs.pdf
el Karoui, N., Rouge, R. - Pricing via utility maximization and entropy.pdf
Dupont, J.-P., Martin, G., Krée, P.A. - On the convergence of SGD in ℝ^d.pdf
Achdou, Y., Lasry, J.-M., Lions, P.-L., Moll, B. - Income and wealth distribution in macroeconomics, a continuous-time approach.pdf
Rogers, L.C.G., Walsh, J.B. - A(t,Bₜ) is not a semimartingale.pdf
Roynette, B., Vallois, P., Yor, M. - Asymptotics for the distribution of lengths of excursions of a d-dimensional Bessel process (0<d<2).pdf
Omidshafiei, S., Hennes, D., Garnelo, M., et al. - Multiagent off-screen behavior prediction in football.pdf
```

## Implementation

The canonical implementation is `CMO.get_canonical_filename()` in
`src/arxivbot/models/cmo.py`.  All other filename generators should
either delegate to this method or be treated as temporary/fallback
names that will be corrected during ingestion.

### Filename generators in the codebase

| Generator | File | Purpose | Matches convention? |
|-----------|------|---------|-------------------|
| `CMO.get_canonical_filename()` | `src/arxivbot/models/cmo.py` | **Primary** — library filing | Yes |
| `enhanced_parser._generate_filename_from_metadata()` | `src/pdf_processing/parsers/enhanced_parser.py` | Deprecated fallback | No (first author only) |
| `academic_downloader._generate_filename()` | `src/downloader/academic_downloader.py` | Temporary download name | No |
| `version_detection.generate_filename_with_version()` | `src/downloader/version_detection.py` | Versioned download name | No |
| `proper_downloader._generate_filename()` | `src/downloader/proper_downloader.py` | Temporary download name | No |
| `discovery.generate_filename()` | `src/discovery/integration.py` | Temporary download name | No |

### Inverse operation (parsing)

Filenames are parsed back into (title, authors) by `parse_filename()`
in `ml/pdf-meta-llm/scripts/extract_text.py`.  This is used for
training data generation and evaluation.
