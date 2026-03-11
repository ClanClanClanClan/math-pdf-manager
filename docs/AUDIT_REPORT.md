# Math-PDF Manager - Full Audit Report

**Date:** 2026-03-05
**Audit scope:** All components of the academic paper management system
**Test suite:** 822 tests across 10 audit test files, 0 failures, 130 audit warnings

---

## Executive Summary

The Math-PDF Manager is a substantial academic paper management system (~10,000 lines of Python + React frontend) with discovery, acquisition, processing, maintenance, and API layers. While the architecture is well-structured and many individual components function correctly, the audit uncovered **critical issues** that prevent the system from operating as documented:

1. **Sentence case is completely dead code** -- none of the three implementations are wired into the validation pipeline
2. **Processing pipeline uses mock metadata** -- no actual PDF parsing occurs
3. **Frontend is 61% phantom code** -- 11 of 18 API endpoints called by the frontend don't exist
4. **No authentication** on any API endpoint
5. **Generator exhaustion bugs** cause maintenance reports to return incorrect counts

---

## Findings by Severity

### CRITICAL (Core functionality broken)

| # | Component | Finding | Location |
|---|-----------|---------|----------|
| C1 | Title Validation | All three sentence case implementations are **dead code**. The `sentence_case=True` parameter is a no-op throughout the entire pipeline. `to_sentence_case_academic()` in `core/sentence_case.py` is never called. The filename checker has a placeholder `sent_case = title_after`. The title_normalizer uses **title case** rules instead. | `core/sentence_case.py`, `validators/filename_checker/core.py:280`, `validators/title_normalizer.py:125` |
| C2 | Processing | `process_file()` returns **fabricated metadata**. Title = filename stem, authors = "Unknown Author", year = 2024, abstract = "Abstract not available". No PDF parsing occurs. This mock data feeds into enrichment, organization, and the database. | `processing/main_processing.py:67` |
| C3 | Processing | `asyncio.run()` called inside a for-loop creates a new event loop per file. Crashes if an event loop is already running. | `processing/main_processing.py:428` |
| C4 | Maintenance | Generator exhaustion in `run_update_sweep()` and `audit_collection_quality()`. The iterables are consumed during processing, then `len(list(...))` returns 0, producing incorrect `checked_papers` and `total_files` counts. | `maintenance/system.py` |
| C5 | API | Calls `db.list_papers()` which **does not exist** on `AsyncPaperDatabase`. Results in `AttributeError` at runtime. | `api/app.py` -> `database.py` |
| C6 | Frontend | 11 of 18 frontend API methods call endpoints that don't exist on the backend. The auth, search, paper detail, download, feedback, summarize, and stats endpoints are phantom code. | `frontend/src/services/api.js` |

### MAJOR (Significant gaps)

| # | Component | Finding | Location |
|---|-----------|---------|----------|
| M1 | Database | FTS5 UPDATE trigger doesn't remove stale entries. After updating a paper's title, the old title is still searchable. | `database.py` FTS triggers |
| M2 | Database | `find_duplicates()` queries a `duplicates` table that is never populated. Always returns empty. | `database.py` |
| M3 | Database | Fragile 20-column positional row mapping (`row[0]` through `row[19]`). Any schema change will silently corrupt data. | `database.py` |
| M4 | Discovery | ArXiv published year regex `<published>(\d{4})-\d{2}-\d{2}</published>` never matches real ArXiv data which includes time component (`2021-01-01T00:00:00Z`). Published year is always `None`. | `discovery/engine.py` |
| M5 | Discovery | ArXiv XML parsing uses regex instead of `defusedxml`. Vulnerable to XXE attacks if processing untrusted XML. | `discovery/engine.py` |
| M6 | Acquisition | `AlternativeStrategy` is a non-functional stub that always returns failure. | `acquisition/engine.py` |
| M7 | API | CORS configured with `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. Any website can make API calls. | `api/app.py` |
| M8 | API | No authentication, authorization, rate limiting, or CSRF protection on any endpoint. | `api/app.py` |
| M9 | Metadata | `_enrich_from_orcid()` is a stub that always returns `None`. ORCID integration is non-functional. | `metadata/enhanced_sources.py:771` |
| M10 | Metadata | `SourceRankingSystem.update_source_ranking()` calls `defaultdict(int).most_common()` which raises `AttributeError`. Should use `collections.Counter`. | `metadata/quality_scoring.py:764` |
| M11 | Downloader | DOI-to-publisher mapping uses substring matching (`'1007' in doi`) which produces false positives. | `downloader/orchestrator.py:226` |
| M12 | Downloader | `EnhancedSciHubDownloader` is always added with no configuration toggle. | `downloader/orchestrator.py:147` |
| M13 | Title Validation | `title_normalizer.py` uses **title case** rules (capitalize words >3 chars) instead of sentence case. Produces false warnings on correctly sentence-cased titles. | `validators/title_normalizer.py:125` |

### MINOR (Cosmetic / documentation)

| # | Component | Finding | Location |
|---|-----------|---------|----------|
| m1 | Config | 5 case-insensitive duplicates in capitalization_whitelist (G-expectation/g-expectation, q-learning/Q-learning, etc.) | `config/config.yaml` |
| m2 | Config | `name_dash_whitelist.txt` has only 1 entry (Weierstrass, which doesn't even have a dash). File is non-functional. | `data/name_dash_whitelist.txt` |
| m3 | API | Uses deprecated `@app.on_event("startup")` instead of lifespan handlers. | `api/app.py:65` |
| m4 | Enrichment | Only 3 math concept patterns (laplacian, fourier, markov) and 5 topic categories. Very minimal. | `metadata/enrichment.py` |
| m5 | Quality Scoring | Title quality patterns penalize titles starting with articles ("the", "a", "an") which is wrong for sentence case. | `metadata/quality_scoring.py:137` |
| m6 | Downloader | User-agent rotation uses outdated Chrome 91 strings (2021). | `downloader/credentials.py` |
| m7 | Frontend | 401 interceptor references non-existent `/login` page and `arxivbot_token` localStorage key. | `frontend/src/services/api.js:33-36` |
| m8 | Downloader | Shibboleth/SAML authentication not implemented (returns False). | `downloader/credentials.py:317` |

---

## Component-by-Component Status

### Database Layer (`src/core/database.py`)
- **Schema creation:** WORKS -- tables, indexes, FTS5 all created correctly
- **CRUD operations:** WORKS -- add/get/update/search all functional
- **FTS5 search:** PARTIALLY WORKS -- INSERT triggers work, UPDATE triggers don't remove stale data
- **Duplicate detection:** BROKEN -- queries always-empty table
- **`list_papers()`:** MISSING -- API calls it but method doesn't exist
- **Tests:** 49 tests passing

### Discovery Engine (`src/discovery/engine.py`)
- **ArXiv search:** WORKS -- XML parsing extracts title, authors, abstract, arXiv ID
- **Crossref search:** WORKS -- JSON parsing extracts DOI, title, authors
- **Published year:** BROKEN -- regex never matches real ArXiv datetime format
- **BibTeX import:** WORKS
- **Security:** CONCERN -- regex XML parsing, no defusedxml
- **Tests:** 70+ tests passing

### Acquisition Engine (`src/acquisition/engine.py`)
- **OpenAccessStrategy:** WORKS -- Unpaywall API integration functional
- **PreprintStrategy:** WORKS -- arXiv PDF URL construction correct
- **PublisherStrategy:** WORKS -- DOI resolution functional
- **InstitutionalStrategy:** WORKS -- dynamic import functional
- **AlternativeStrategy:** STUB -- always returns failure
- **Strategy fallback:** WORKS -- tries strategies in sequence
- **Tests:** 60+ tests passing

### Processing Pipeline (`src/processing/main_processing.py`)
- **File collection:** WORKS -- finds PDFs recursively
- **File hashing:** WORKS -- SHA-256 correctly computed
- **Metadata extraction:** BROKEN -- returns mock data, never parses PDFs
- **Batch processing:** WORKS structurally, but feeds mock data downstream
- **Event loop:** BROKEN -- `asyncio.run()` inside for-loop
- **Tests:** 50 tests passing

### Maintenance System (`src/maintenance/system.py`)
- **Working paper detection:** WORKS -- correctly identifies papers >365 days old
- **PDF validation:** WORKS -- checks `%PDF` header
- **Missing file detection:** WORKS
- **Report generation:** BROKEN -- generator exhaustion produces count=0
- **Tests:** 46 tests passing

### API (`src/api/app.py`)
- **GET /health:** WORKS
- **POST /discovery/query:** WORKS (depends on discovery engine)
- **POST /acquisition/acquire:** WORKS (depends on acquisition engine)
- **POST /maintenance/run:** WORKS (depends on maintenance system)
- **GET /organization/duplicates:** BROKEN -- depends on missing `list_papers()` + empty duplicates table
- **GET /collection/summary:** PARTIALLY WORKS -- depends on database methods
- **GET /metrics:** WORKS
- **Security:** NO AUTH, open CORS, no rate limiting
- **Tests:** 50+ tests passing

### Title Validation (`src/validators/`)
- **Author parsing:** WORKS -- normalization, spacing, suffix handling all functional
- **Unicode handling:** WORKS -- NFC, dangerous chars, mixed scripts all correct
- **Mathematical context:** WORKS -- Greek letters, operators detected correctly
- **Title capitalization:** BROKEN -- uses title case instead of user's sentence case
- **Sentence case conversion:** DEAD CODE -- never called in any pipeline
- **Pattern matching:** WORKS -- tokenization and dash detection functional
- **Tests:** 63 tests passing

### Metadata Enrichment (`src/metadata/`)
- **Semantic Scholar API:** WORKS -- parsing, quality scoring, rate limiting all correct
- **OpenAlex API:** WORKS -- parsing, abstract reconstruction, ORCID extraction all correct
- **Orchestrator:** WORKS -- deduplication, merging, concurrent search functional
- **ORCID integration:** STUB -- always returns None
- **Enrichment:** MINIMAL -- only 3 math concepts, 5 topic categories
- **Quality scoring:** WORKS -- comprehensive metrics, weighted scoring functional
- **Source ranking:** PARTIALLY WORKS -- `update_source_ranking()` has Counter bug
- **Tests:** 140 tests passing

### Downloader (`src/downloader/`)
- **Orchestrator:** WORKS -- batch downloads, concurrency control, statistics
- **Credential management:** WORKS -- PBKDF2+Fernet encryption, secure sessions
- **Publisher downloaders:** EXIST -- 6 publisher-specific implementations
- **Path traversal protection:** WORKS -- defense-in-depth validation
- **DOI mapping:** FLAWED -- substring matching produces false positives
- **Tests:** 106 tests passing

### Frontend (`frontend/src/`)
- **API client:** 39% FUNCTIONAL -- only 7 of 18 methods connect to real endpoints
- **StatsPage:** PARTIALLY WORKS -- connected to real endpoints but expects response shapes that may not match
- **Auth system:** PHANTOM CODE -- login/token/refresh are dead code
- **Tests:** 106 tests passing (documenting gaps)

### CLI (`src/main.py`)
- **Argument parsing:** WORKS -- all flags parse correctly
- **Input validation:** WORKS -- path validation, directory creation
- **Service setup:** DEPENDS -- requires DI container to initialize
- **Discovery mode:** WORKS structurally -- calls `discover_papers_cli()`
- **Processing mode:** WORKS structurally -- but feeds mock metadata downstream
- **Tests:** Covered in integration audit

---

## Positive Findings

These security and design choices are commendable:

1. **Parameterized SQL queries** throughout the database layer (no SQL injection)
2. **SHA-256 file hashing** for integrity verification
3. **PBKDF2 + Fernet encryption** for credential storage at rest
4. **SSL verification** with certifi in all HTTP sessions
5. **Path traversal protection** with defense-in-depth (resolve + substring check)
6. **Filename length limits** (5000 chars) to prevent DoS
7. **Rate limiting** on all external API clients
8. **Concurrent download control** via asyncio.Semaphore

---

## Prioritized Fix List

### Priority 1: Must fix (system doesn't work as designed)
1. Wire `to_sentence_case_academic()` into the validation pipeline (C1)
2. Implement real PDF metadata extraction to replace mock data (C2)
3. Fix `asyncio.run()` inside for-loop -- use single event loop (C3)
4. Materialize generators into lists in maintenance system (C4)
5. Add `list_papers()` method to AsyncPaperDatabase (C5)

### Priority 2: Should fix (significant functionality gaps)
6. Fix FTS5 UPDATE trigger to remove stale entries (M1)
7. Implement or remove `find_duplicates()` (M2)
8. Fix ArXiv published year regex to handle ISO 8601 with time (M4)
9. Use defusedxml for ArXiv XML parsing (M5)
10. Fix `SourceRankingSystem.update_source_ranking()` Counter bug (M10)
11. Fix DOI-to-publisher substring matching to use prefix (M11)

### Priority 3: Should address (security/frontend)
12. Add authentication to API (M8)
13. Restrict CORS origins (M7)
14. Remove or implement the 11 phantom frontend endpoints (C6)
15. Add rate limiting middleware to API
16. Add toggle for Sci-Hub downloader (M12)

### Priority 4: Nice to have
17. Replace fragile positional row mapping with named columns (M3)
18. Expand math concept and topic detection (m4)
19. Fix title quality scorer to not penalize article-start titles (m5)
20. Update user-agent strings (m6)
21. Clean up config duplicates (m1)
22. Populate name_dash_whitelist.txt properly (m2)

---

## Test Suite Summary

| Test File | Tests | Status | Component |
|-----------|-------|--------|-----------|
| `test_title_validation_audit.py` | 63 | ALL PASS | Title/filename validation (Phase 8) |
| `test_database_audit.py` | 49 | ALL PASS | Database layer (Phase 2) |
| `test_discovery_audit.py` | 70+ | ALL PASS | Discovery engine (Phase 3) |
| `test_acquisition_audit.py` | 60+ | ALL PASS | Acquisition engine (Phase 4) |
| `test_processing_audit.py` | 50 | ALL PASS | Processing pipeline (Phase 5) |
| `test_maintenance_audit.py` | 46 | ALL PASS | Maintenance system (Phase 6) |
| `test_api_audit.py` | 50+ | ALL PASS | API endpoints (Phase 7) |
| `test_metadata_audit.py` | 140 | ALL PASS | Metadata enrichment (Phase 9) |
| `test_downloader_audit.py` | 106 | ALL PASS | Downloader system (Phase 10) |
| `test_integration_audit.py` | 106 | ALL PASS | CLI/frontend/security (Phase 11-12) |
| **TOTAL** | **822** | **ALL PASS** | |

All 130 audit warnings are emitted via `warnings.warn()` and can be collected with `pytest -W all`.

To re-run the full audit: `python3 -m pytest tests/audit/ -v`
