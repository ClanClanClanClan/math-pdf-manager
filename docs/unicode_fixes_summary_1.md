# Unicode Normalization Fixes Summary

## Issues Fixed

### 1. Initial State
- 304 errors reported when running main.py on test directory
- Multiple false positives for terms that were actually in whitelists

### 2. Critical Bugs Fixed

#### A. Unicode Dash Mismatch Bug
- **Issue**: check_title_dashes was forcing EN DASH when checking, regardless of actual dash in title
- **Fix**: Check with the actual dash found in the title
```python
# OLD: cand = f"{L}–{R}"  # Forces EN DASH
# NEW: cand = f"{L}{dash}{R}"  # Uses actual dash found
```

#### B. Case Sensitivity Bug
- **Issue**: All word lists were being canonicalized (lowercased) when loaded
- **Fix**: Only canonicalize known_words.txt (case-insensitive), keep others case-sensitive

#### C. SpellChecker Initialization Bug
- **Issue**: SpellChecker was only initialized with known_words, not compound_terms
- **Fix**: Include compound_terms in SpellChecker initialization
```python
spellchecker=SpellChecker(SpellCheckerConfig(
    known_words=known_words | compound_terms,  # Now includes both
    capitalization_whitelist=capitalization_whl,
    name_dash_whitelist=name_dash_whitelist
))
```

#### D. First Word Capitalization Bug
- **Issue**: First word was being flagged for being capitalized
- **Fix**: First word should ALWAYS be capitalized in title case

#### E. Unicode Normalization Issues
- **Issue**: 5 entries in name_dash_whitelist.txt were using NFD (decomposed) form
- **Fix**: Normalized all entries to NFC form
- **Issue**: Filenames from filesystem are often in NFD form
- **Fix**: Normalize titles to NFC immediately after parsing in check_filename()

#### F. Possessive Form Handling
- **Issue**: "Itô's" was being flagged even though "Itô" was in whitelist
- **Fix**: Enhanced possessive checking to normalize Unicode when comparing

### 3. Results
- Errors reduced from 304 to 2 (99.3% reduction)
- Remaining 2 errors are legitimate: "Itô-Wentzell" uses hyphen instead of en-dash
- All Unicode normalization issues resolved
- Tests passing successfully

### 4. Key Technical Insights
- macOS filesystem often stores filenames in NFD (decomposed) form
- Python string comparisons require normalized forms for Unicode equivalence
- Different dash characters (HYPHEN-MINUS U+002D vs EN DASH U+2013) are distinct
- Combining characters (e.g., ô as o + combining circumflex) need normalization