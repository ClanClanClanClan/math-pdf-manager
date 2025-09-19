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
| Topic enrichment, subject classification, journal assessment | ⚠️ | `metadata.enrichment` provides heuristic topics/quality scoring; advanced models outstanding. |
| External data integrations (OpenAlex, Unpaywall, DOAJ, impact factors) | ❌ | No calls or adapters exist. |
| Relationship & consistency validation | ❌ | Duplicate/version relationships not analysed; metadata validation limited to filename checks. |

## 3. Acquisition Engine

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Strategy-based acquisition (Open Access → Institutional → Publisher → Preprint → Alternative) | ⚠️ | `src/acquisition/engine.py` coordinates strategies; institutional/alternative layers still to be implemented. |
| Unpaywall integration | ⚠️ | Implemented in `OpenAccessStrategy`; requires configuration. |
| Institutional proxy/Shibboleth automation | ⚠️ | Institutional Playwright flows exist but not wired into the new engine. |
| Publisher-specific downloaders (Springer, Elsevier, IEEE, ACM, Wiley, …) | ⚠️ | `PublisherStrategy` now delegates to `UnifiedDownloader`; robust adapters pending. |
| Preprint and alternative source handling | ⚠️ | arXiv handled; other preprint/alternative sources not yet automated. |
| Download queue/monitoring | ❌ | No job queue or persistent acquisition state. |

## 4. Validation Pipeline

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Filename validation (existing) | ✅ | Production-grade and widely tested. |
| Content validation (PDF integrity, metadata matching) | ⚠️ | PDF signature checks in place; deep metadata validation pending. |
| Duplicate detection (hash/content/versions) | ⚠️ | Exact duplicate hashing implemented; semantic/version comparisons outstanding. |
| Metadata validation | ⚠️ | Limited to config sanity warnings added recently; full spec not met. |

## 5. Smart Organization System

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Subject classification & routing | ⚠️ | `OrganizationSystem` uses heuristic classifier/router. |
| Publication status detection | ⚠️ | Basic status detection implemented. |
| Version management | ⚠️ | Metadata tagged with version keys; reconciliation still needed. |
| Collection reorganization | ❌ | Full reorganization process not yet built. |

## 6. Maintenance & Monitoring

| Requirement | Status | Notes |
|-------------|:------:|-------|
| Scheduler integration (TaskScheduler, UpdateMonitor, QualityAuditor) | ⚠️ | `maintenance.system` provides async scheduler and monitors; periodic execution wiring pending. |
| Update sweeps & quality reports | ⚠️ | Automated sweeps produce reports; integration with CLI/DB outstanding. |
| ArXiv version monitoring | ❌ | Specific version polling still to be implemented. |

## 7. Data Layer & Persistence

| Requirement | Status | Notes |
|-------------|:------:|-------|
| SQLite paper database with full-text search | ⚠️ | `core/database.py` defines models but is not integrated with CLI or pipelines; lacks migrations/tests. |
| Duplicate/version tables populated | ❌ | Schema exists but there is no code writing to it. |
| Task queue / Redis | ❌ | No queue components present. |

## 8. API & UI Surface

| Requirement | Status | Notes |
|-------------|:------:|-------|
| REST/GraphQL API server exposing core operations | ⚠️ | FastAPI server exposes health, discovery, and acquisition endpoints; expanded coverage required. |
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

1. **Institutional Strategy Integration** – connect ETH Playwright flows to the acquisition engine and persist session handling.  
2. **Advanced Metadata & Validation** – enhance enrichment with ML classifiers and deep PDF/content validation.  
3. **Database & Automation** – wire results into the SQLite backend and schedule maintenance routines via CLI/API.  
4. **API Surface Expansion** – expose additional endpoints (organization, maintenance reports) and link the React frontend.  
5. **Monitoring & Deployment** – integrate tracing/metrics, provide deployment scripts, and ensure cron/queue orchestration.

Each of these tracks will require significant architectural work; see the Implementation Roadmap (to be produced) for detailed milestones.
