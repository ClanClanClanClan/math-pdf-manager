# Filename Checker Refactoring Strategy

## Current State Analysis

### Large Files Status:
- **filename_checker.py: 3,149 lines** - Core validation logic, heavily used
- **metadata_fetcher.py: ~800-1,000 lines** - API integrations
- **auth_manager.py: ~400-600 lines** - Authentication handling
- **pdf_parser.py: 2,576 lines** - ✅ ALREADY REFACTORED into modules

### Key Dependencies:
1. **main.py** imports: `from filename_checker import enable_debug`
2. **main_processing.py** imports: `from filename_checker import batch_check_filenames, enable_debug`
3. **validators/filename.py** imports: `from filename_checker import FilenameCheckResult, check_filename`
4. **tests/test_filename_checker.py** - 47 comprehensive tests

## Refactoring Strategy: Phase-by-Phase

### Phase 1: Extract Core Components (Safe)
Extract independent components that don't break existing imports:

1. **Extract Constants and Unicode Data**
   - Move SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP to `validators/unicode_constants.py`
   - Move German language indicators to `validators/language_data.py`
   - Move Greek letters to `validators/greek_letters.py`

2. **Extract Utility Functions**
   - Move debug functions to `validators/debug_utils.py`
   - Move math region detection to `validators/math_utils.py`
   - Move text transformation to `validators/text_transform.py`

### Phase 2: Create Backwards-Compatible Modules
Keep the original filename_checker.py but import from new modules:

1. **Create `validators/tokenizer.py`**
   - Extract tokenization logic
   - Import back into filename_checker.py for compatibility

2. **Create `validators/author_processor.py`**
   - Extract author string processing
   - Import back into filename_checker.py

3. **Create `validators/unicode_processor.py`**
   - Extract Unicode processing
   - Import back into filename_checker.py

### Phase 3: Gradual Migration
Update consumers to use new modules:

1. **Update main.py and main_processing.py**
   - Change imports to use new modules
   - Test functionality

2. **Update validators/filename.py**
   - Use new modules directly
   - Remove dependency on filename_checker.py

### Phase 4: Test and Cleanup
1. **Run comprehensive tests**
2. **Remove original filename_checker.py**
3. **Clean up any remaining imports**

## Implementation Order

### Week 1: Extract Safe Components
- Extract constants and data (non-breaking)
- Extract utility functions (non-breaking)
- All imports still work

### Week 2: Core Logic Extraction
- Extract tokenizer (backwards-compatible)
- Extract author processor (backwards-compatible)
- Extract unicode processor (backwards-compatible)

### Week 3: Migration
- Update main application files
- Update validator files
- Comprehensive testing

### Week 4: Cleanup
- Remove original filename_checker.py
- Clean up imports
- Final testing

## Benefits of This Approach

1. **Zero Breaking Changes** during extraction
2. **Gradual Migration** with testing at each step
3. **Rollback Capability** if issues arise
4. **Maintained Functionality** throughout process

## Success Metrics

- **Target**: filename_checker.py reduced from 3,149 to <200 lines
- **Modules Created**: 6-8 focused modules
- **Test Coverage**: All 47 tests still pass
- **No Breaking Changes**: All imports continue working during transition