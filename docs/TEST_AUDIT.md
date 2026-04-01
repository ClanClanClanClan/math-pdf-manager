# Test Audit: Filename and Renaming Pipeline

Comprehensive audit of all tests related to the paper renaming pipeline.
Conducted April 2026.

## Test Inventory

| File | Tests | Category | Status |
|------|-------|----------|--------|
| `tests/audit/test_title_validation_audit.py` | 113 | Sentence case, authors, Unicode, dashes, end-to-end validation, config integrity | **186/186 pass** |
| `tests/core/test_sentence_case.py` | 41 | Sentence case conversion, whitelists, possessives, technical prefixes | All pass |
| `tests/core/test_text_canonicalization.py` | 31 | Unicode normalisation, dash normalisation, BOM removal, ligatures | All pass |
| `tests/core/test_tokenization.py` | 54 | Token dataclass, segment regex, phrase regex, math masking | All pass |
| `tests/core/test_math_tokenization.py` | 33 | DASH_CHARS, phrase matching with all dash types, math detection | All pass |
| `tests/core/test_latex_processing.py` | 38 | LaTeX stripping, dash normalisation for comparison, title comparison | All pass |
| `tests/core/test_models.py` | 39 | Author model, PDFMetadata, ValidationResult, enums | All pass |
| `tests/core/test_comprehensive_validation.py` | 19 | Path validation, filename sanitisation, language detection, security | All pass |
| `tests/core/test_pdf_processing_core.py` | 33 | Parser init, multi-engine extraction, text quality, repository detection | All pass |
| `tests/core/test_pdf_processing_targeted.py` | 20 | Duplicate of core tests with slight variations | All pass |
| `tests/core/test_enhanced_pdf_processing_hell.py` | 29 | Dash spacing, compound terms, sentence case integration, author processing | **Issues found** |
| `tests/core/test_paranoid_edge_cases.py` | 25 | Exceptions, DI, security, memory, resources | **Issues found** |
| **Total** | **475** | | |

## Critical Issues Found

### 1. Dummy `fix_author_block` in test_enhanced_pdf_processing_hell.py

**Severity: HIGH**

5 author-processing tests (lines 445-594) use a dummy function that
returns input unchanged.  `test_author_processing_semicolon_lists`
likely fails because expected output differs from input.  The
diacritics, memory, and concurrency author tests are no-ops.

**Affected tests:**
- `test_author_processing_diacritics_preservation`
- `test_author_processing_semicolon_lists`
- `test_author_processing_extreme_unicode`
- `test_author_processing_memory_bomb_prevention`
- `test_author_processing_concurrent_safety`

### 2. No-op tests in test_paranoid_edge_cases.py

**Severity: MEDIUM**

- `test_fork_bomb_prevention`: `assert True` — tests nothing
- `test_password_entropy_edge_cases`: bare `except: pass` swallows
  all assertion failures — always passes regardless

### 3. Tests with no assertions in test_pdf_processing_core.py

**Severity: MEDIUM**

- `test_extraction_with_corrupted_pdf`: calls function, never asserts
- `test_extraction_with_password_protected_pdf`: same

### 4. Repository detection strictness mismatch

**Severity: LOW**

`test_pdf_processing_core.py` uses strict `== "arxiv"` while
`test_pdf_processing_targeted.py` uses lenient `in ["arxiv", "journal"]`
for the same inputs.

## Coverage Gaps

### Author model (test_models.py)

| What | Tested? |
|------|---------|
| Basic author (given + family) | Yes |
| Multiple given names (initials) | Yes |
| Hyphenated given names (J.-P.) | **No** |
| Name particles (van, de, el) | **No** |
| Accented names (Possamai, Elie) | **No** |
| NFC/NFD normalisation in Author | **No** |
| Hyphenated surnames (Barndorff-Nielsen) | **No** |

### Filename generation

| What | Tested? |
|------|---------|
| `CMO.get_canonical_filename()` | **No tests exist** |
| Author formatting in filenames | **No** |
| "et al." dynamic truncation | **No** |
| Colon-to-comma conversion | **No** |
| Sentence case applied in filename | **No** |
| Filesystem byte limit (255) | **No** |
| En-dash for compound names in output | **No** |

### Unicode in filenames

| What | Tested? |
|------|---------|
| NFC normalisation in titles | Yes (test_title_validation_audit) |
| Dangerous Unicode removal | Yes (test_title_validation_audit) |
| Non-breaking space normalisation (U+00A0) | **No** |
| Ligature expansion in filenames | Yes (test_text_canonicalization) |
| Mixed-script detection | Yes (test_title_validation_audit) |

### Dash handling

| What | Tested? |
|------|---------|
| All dash types in tokenisation | Yes (test_math_tokenization) |
| Dash normalisation for comparison | Yes (test_latex_processing) |
| En-dash from whitelist in output | Yes (test_title_validation_audit) |
| Hyphen vs en-dash distinction | Yes (test_title_validation_audit) |
| G-Brownian (hyphen) vs G-Brownian motion (en-dash) | **No** |
| `--` to en-dash normalisation | Yes (test_title_validation_audit) |

### Sentence case

| What | Tested? |
|------|---------|
| Basic sentence case | Yes (41 + 10 + 23 tests) |
| Proper adjectives (Bayesian etc.) | Yes |
| Acronyms (BSDE, PDE) | Yes |
| Mixed-case brands (LaTeX, PyTorch) | Yes |
| Technical prefixes (g-expectation) | Yes |
| Colon triggers capitalisation | Yes |
| Whitelist matching with dash normalisation | Yes |
| French/German rules | **No** |
| Subtitle after comma (no capitalisation) | **No** |

## Recommendations

### Must-add tests

1. **`CMO.get_canonical_filename()`** — the single most important
   function has zero dedicated tests.  Need tests for:
   - Single author, multi-author, et al. truncation
   - Colon-to-comma conversion
   - Sentence case integration
   - Filesystem byte limit
   - Accented authors
   - En-dash compound names in output

2. **Author model with particles and accents** — `Author("Nicole",
   "el Karoui")` should produce correct initials and full name.

3. **Non-breaking space normalisation** — verify U+00A0 becomes
   regular space in filenames.

4. **G-compound dash distinction** — `G-expectation` (hyphen) vs
   `G-Brownian motion` (en-dash) should be tested.

### Should-fix tests

5. Remove or fix the 5 dummy author-processing tests in
   `test_enhanced_pdf_processing_hell.py`.

6. Remove `test_fork_bomb_prevention` (no-op) and fix
   `test_password_entropy_edge_cases` (bare except).

7. Add assertions to the 2 PDF extraction tests.
