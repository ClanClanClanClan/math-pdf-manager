# Phase 1 Implementation Plan: Large File Refactoring

## Overview
This plan details the immediate steps to begin refactoring the three largest files in the codebase, focusing on breaking down monolithic files into smaller, focused modules.

## Priority 1: pdf_parser.py Refactoring

### Current State Analysis
- **Estimated 1,500+ lines**
- **Multiple responsibilities**: PDF parsing, text extraction, format-specific extractors, API integration, mock implementations
- **Four major extractor classes**: AdvancedSSRNExtractor, AdvancedArxivExtractor, AdvancedJournalExtractor, UltraEnhancedPDFParser
- **Embedded mocks**: Test implementations within production code

### Refactoring Strategy

#### Step 1: Extract Extractor Classes (Day 1-2)
```bash
# Create new directory structure
mkdir -p core/extractors
mkdir -p core/api
mkdir -p core/parsing
mkdir -p tests/mocks/pdf_parsing
```

#### Step 2: Move AdvancedSSRNExtractor
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/extractors/ssrn_extractor.py`

**Extract this class and its dependencies**:
- SSRN-specific patterns and constants
- Title and author extraction methods
- SSRN validation logic

**Interface to maintain**:
```python
class SSRNExtractor:
    def extract_title(self, text: str, text_blocks: List[TextBlock]) -> Tuple[Optional[str], float]
    def extract_authors(self, text: str, text_blocks: List[TextBlock]) -> Tuple[Optional[str], float]
```

#### Step 3: Move AdvancedArxivExtractor
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/extractors/arxiv_extractor.py`

**Extract this class and its dependencies**:
- ArXiv-specific patterns and metadata
- Category handling logic
- ArXiv ID extraction

#### Step 4: Move AdvancedJournalExtractor
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/extractors/journal_extractor.py`

**Extract this class and its dependencies**:
- Journal-specific metadata patterns
- Academic format handling
- Journal validation logic

#### Step 5: Create ArXiv API Client
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/api/arxiv_api_client.py`

**Extract from pdf_parser.py**:
```python
class ArxivAPIClient:
    def query_arxiv_api(self, arxiv_id: str, *, verbose: bool = False) -> Optional[ArxivMetadata]
    def fetch_arxiv_metadata(self, arxiv_id: str) -> Optional[dict]
```

#### Step 6: Create Core PDF Parser
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/parsing/pdf_parser.py`

**Simplified main parser**:
```python
class PDFParser:
    def __init__(self, extractors: List[BaseExtractor]):
        self.extractors = extractors
    
    def parse_pdf(self, pdf_path: str) -> ParsedMetadata:
        # Coordinate between different extractors
        # Return consolidated metadata
```

#### Step 7: Extract Test Mocks
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/tests/mocks/pdf_parser_mocks.py`

**Move all mock implementations**:
- `_FakeGrobidClient`
- `_fake_image_to_string`
- Test utility functions

## Priority 2: metadata_fetcher.py Refactoring

### Current State Analysis
- **Estimated 800+ lines**
- **Multiple providers**: ArXiv, Crossref, Google Scholar, Unpaywall
- **HTTP client management**: Retry logic, session management
- **Caching system**: File-based caching with thread safety
- **Data transformation**: Normalization and validation

### Refactoring Strategy

#### Step 1: Extract Provider Classes (Day 3-4)
```bash
mkdir -p core/providers
mkdir -p core/http
mkdir -p core/metadata
```

#### Step 2: Create ArXiv Provider
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/providers/arxiv_provider.py`

**Extract functions**:
- `query_arxiv_api()`
- `fetch_arxiv_metadata()`
- `check_arxiv_updates()`

#### Step 3: Create Crossref Provider
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/providers/crossref_provider.py`

**Extract functions**:
- `query_crossref()`
- DOI validation logic
- Crossref-specific error handling

#### Step 4: Create Google Scholar Provider
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/providers/google_scholar_provider.py`

**Extract functions**:
- `_serpapi_request()`
- `query_google_scholar_serpapi()`
- Scholar-specific parsing

#### Step 5: Create HTTP Client
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/http/http_client.py`

**Extract HTTP functionality**:
- Session management
- Retry logic
- Rate limiting
- Error handling

#### Step 6: Create Metadata Cache
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/metadata/metadata_cache.py`

**Extract caching functions**:
- `_read_cache()`
- `_write_cache()`
- Cache invalidation logic

## Priority 3: duplicate_detector.py Refactoring

### Current State Analysis
- **Estimated 700+ lines**
- **Text normalization**: Complex Unicode handling, LaTeX processing
- **Duplicate detection**: Similarity algorithms, metadata comparison
- **File processing**: Path handling, metadata extraction

### Refactoring Strategy

#### Step 1: Extract Text Processing (Day 5-6)
```bash
mkdir -p core/text_processing
mkdir -p core/duplicate_detection
```

#### Step 2: Create Text Normalizer
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/text_processing/text_normalizer.py`

**Extract functions**:
- `robust_normalize()`
- `_clean_basic()`
- `_strip_accents()`
- `_canonical_dash()`
- `_latex_scrub()`

#### Step 3: Create Title Processor
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/text_processing/title_processor.py`

**Extract functions**:
- `robust_normalize_title()`
- `_series_scrub()`
- `_drop_number_prefix()`
- Title-specific normalization

#### Step 4: Create Author Processor
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/text_processing/author_processor.py`

**Extract functions**:
- `robust_normalize_authors()`
- Author name parsing
- Surname prefix handling

#### Step 5: Create Duplicate Detector
**Target**: `/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/core/duplicate_detection/duplicate_detector.py`

**Extract functions**:
- `find_duplicates()`
- Similarity calculation
- Metadata comparison logic

## Implementation Schedule

### Day 1-2: PDF Parser Refactoring
- [ ] Create directory structure
- [ ] Extract AdvancedSSRNExtractor
- [ ] Extract AdvancedArxivExtractor
- [ ] Test extracted components
- [ ] Update imports in main files

### Day 3-4: Metadata Fetcher Refactoring
- [ ] Create provider directory structure
- [ ] Extract ArXiv provider
- [ ] Extract Crossref provider
- [ ] Create HTTP client
- [ ] Test provider components

### Day 5-6: Duplicate Detector Refactoring
- [ ] Create text processing modules
- [ ] Extract text normalizer
- [ ] Extract title processor
- [ ] Extract duplicate detector
- [ ] Test all components

### Day 7: Integration and Testing
- [ ] Update all import statements
- [ ] Run comprehensive tests
- [ ] Fix any integration issues
- [ ] Update documentation

## Testing Strategy

### Unit Tests for Each New Module
```python
# Example test structure
tests/unit/
├── test_ssrn_extractor.py
├── test_arxiv_extractor.py
├── test_journal_extractor.py
├── test_arxiv_provider.py
├── test_crossref_provider.py
├── test_text_normalizer.py
├── test_title_processor.py
└── test_duplicate_detector.py
```

### Integration Tests
```python
# Test that refactored components work together
tests/integration/
├── test_pdf_parsing_integration.py
├── test_metadata_fetching_integration.py
└── test_duplicate_detection_integration.py
```

## Risk Mitigation

### Backup Strategy
1. **Create branch** for refactoring work
2. **Commit frequently** after each extraction
3. **Test after each step** to ensure functionality

### Rollback Plan
- Keep original files until refactoring is complete
- Maintain backward compatibility during transition
- Use feature flags to switch between old and new implementations

### Success Criteria
- [ ] All existing tests pass
- [ ] No functionality regression
- [ ] Improved code organization
- [ ] Reduced file sizes
- [ ] Better separation of concerns

This plan provides a concrete roadmap for the first phase of refactoring, with specific files, targets, and timelines for implementation.