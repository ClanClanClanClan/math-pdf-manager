# Compliance Gap Analysis – Academic Paper Management System

_Last updated: $(date '+%Y-%m-%d %H:%M %Z')_

This document maps the requirements in `docs/SYSTEM_SPECIFICATIONS_1.md` against the repository’s current implementation (commit 4bc6726f) to identify the remaining work needed for full compliance.

## Legend

- ✅  Implemented and working
- ⚠️  Partially implemented / prototype exists
- ❌  Missing or non-functional

---

## 1. Discovery Engine

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Multi-source paper search (arXiv, Crossref, Semantic Scholar, MathSciNet, zbMATH, Google Scholar, DBLP) | ❌ | Current code wraps only the arXiv harvester. No generic discovery interface, no support for other sources or cross-source queries. |
| DOI / arXiv / author search APIs | ⚠️ | `ProductionOptimizedHarvester` supports arXiv category harvesting; no generic search-by-DOI or author search endpoints. |
| Bibliography import (BibTeX/RIS/EndNote) | ❌ | No import pipeline present. |
| Conference scraping (robots-aware) | ❌ | No implementation. |
| Discovery task orchestration | ⚠️ | CLI can trigger arXiv discovery, but lacks queueing, monitoring, or persistence of results. |

## 2. Metadata Manager Enhancements

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Existing multi-provider metadata fetch | ⚠️ | `metadata_fetcher.py` covers several providers but is tightly coupled; enrichment hooks in spec absent. |
| Topic enrichment, subject classification, journal assessment | ❌ | No enrichment layer or subject classifiers are implemented. |
| External data integrations (OpenAlex, Unpaywall, DOAJ, impact factors) | ❌ | No calls or adapters exist. |
| Relationship & consistency validation | ❌ | Duplicate/version relationships not analysed; metadata validation limited to filename checks. |

## 3. Acquisition Engine

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Strategy-based acquisition (Open Access → Institutional → Publisher → Preprint → Alternative) | ❌ | `UnifiedDownloader` handles single downloads; no strategy pipeline or ranked fallbacks. |
| Unpaywall integration | ❌ | Not present. |
| Institutional proxy/Shibboleth automation | ⚠️ | `src/publishers/institutional/` contains ETH login logic, but integration into acquisition flow is incomplete. |
| Publisher-specific downloaders (Springer, Elsevier, IEEE, ACM, Wiley, …) | ⚠️ | Some Playwright scripts exist, but they are ad-hoc; no unified API. |
| Preprint and alternative source handling | ❌ | No automated fallback beyond manual scripts. |
| Download queue/monitoring | ❌ | No job queue or persistent acquisition state. |

## 4. Validation Pipeline

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Filename validation (existing) | ✅ | Production-grade and widely tested. |
| Content validation (PDF integrity, metadata matching) | ❌ | No PDF content validator. |
| Duplicate detection (hash/content/versions) | ❌ | Only stub analytics; no implemented duplicate detector. |
| Metadata validation | ⚠️ | Limited to config sanity warnings added recently; full spec not met. |

## 5. Smart Organization System

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Subject classification & routing | ❌ | No classifier or folder router; `process_files` returns mock metadata. |
| Publication status detection | ❌ | Not implemented. |
| Version management | ❌ | No mechanism to correlate versions or merge metadata. |
| Collection reorganization | ❌ | Absent. |

## 6. Maintenance & Monitoring

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Scheduler integration (TaskScheduler, UpdateMonitor, QualityAuditor) | ❌ | No scheduler or long-running maintenance jobs. |
| Update sweeps & quality reports | ❌ | Some audit scripts exist but are manual and static. |
| ArXiv version monitoring | ❌ | No automated process. |

## 7. Data Layer & Persistence

| Requirement | Status | Notes |
|-------------|:------:|-------|
| SQLite paper database with full-text search | ⚠️ | `core/database.py` defines models but is not integrated with CLI or pipelines; lacks migrations/tests. |
| Duplicate/version tables populated | ❌ | Schema exists but there is no code writing to it. |
| Task queue / Redis | ❌ | No queue components present. |

## 8. API & UI Surface

| Requirement | Status | Notes |
|-------------|:------:|-------|
| REST/GraphQL API server exposing core operations | ❌ | No backend service implemented (`api/` is empty). |
| Web dashboard with monitoring | ⚠️ | React frontend scaffold exists but backend APIs and live data are missing. |
| CLI parity with specification | ⚠️ | CLI now runs basic processing and arXiv discovery but lacks most advanced flags/workflows described in specs. |

## 9. Automation & Deployment

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Scheduler / cron integration | ❌ | No automation entrypoints. |
| Deployment-ready containers/scripts | ⚠️ | Various scripts exist, but no cohesive deployment story. |
| Monitoring/Observability (Prometheus traces) | ❌ | Harvester mentions tracing but no end-to-end setup. |

---

## Immediate Priorities

1. **Environment Readiness** – ensure all runtime dependencies (e.g., PyYAML for config, Playwright browsers, aiohttp) are installed and working; establish reproducible setup scripts.  
2. **Discovery Engine MVP** – factor existing arXiv harvester into a pluggable discovery interface; add at least one additional source (Crossref) and DOI/author search endpoints.  
3. **Acquisition Strategy Pipeline** – design and implement the strategy orchestration layer, integrating existing institutional automations and adding Unpaywall/open-access checks.  
4. **Validation & Organization Foundations** – build real metadata ingestion and PDF validation so filenames, metadata, and database records stay in sync.  
5. **Persistence & APIs** – wire the SQLite backend into CLI/processors and surface operations through a consistent API layer to unlock frontend/automation work.

Each of these tracks will require significant architectural work; see the Implementation Roadmap (to be produced) for detailed milestones.

