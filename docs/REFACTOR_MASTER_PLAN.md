# System Modernisation & Reorganisation Blueprint

_Last updated: 2025-09-22_

## 1. Guiding Principles

1. **Protect working functionality** – every structural change must keep existing entry points (`src/main.py`, automation scripts, and publisher workflows) operational.
2. **Iterate in small, reversible steps** – use feature branches, frequent commits, and keep diffs reviewable.
3. **Automate verification** – run linting and targeted tests after each step; add mocks when live credentials or services are unavailable.
4. **Document as you go** – update this blueprint and accompanying changelog after each milestone.
5. **Respect access policies** – confirm institutional automation remains compliant after refactors.

## 2. Current Pain Points (Recap)

- Root directory cluttered with historical automation scripts and reports.
- Two download stacks (`src/downloader/*` vs `src/publishers/*`) duplicating logic and causing drift.
- Mixed documentation quality; newcomers receive conflicting status signals.
- Tests for publisher flows depend on institutional secrets and are hard to run locally.
- Configuration and tooling spread across multiple files without a single authoritative entry.

## 3. High-Level Goals

1. **Clarify project layout** with a clean root structure and clearly scoped packages under `src/`.
2. **Unify download orchestration** so one strategy powers all publisher integrations.
3. **Harden automation & tests** with reproducible, credential-free verification where possible.
4. **Streamline onboarding** through refreshed documentation and scripted setup.
5. **Enable future extensions** (API services, monitoring) via modular boundaries.

## 4. Phase Plan

| Phase | Focus | Key Outcomes | Success Signals |
|-------|-------|--------------|-----------------|
| P0 | Prep & Safety Nets | Branching strategy, baseline test run, dependency audit | CI green on current main; inventory captured |
| P1 | Root & Docs Cleanup | Root contains only active artefacts; legacy moved to `archive/` with manifest; docs landing page updated | `tree` output matches target structure; README links to new overview |
| P2 | Downloader Consolidation | Single orchestrator module; legacy adapters shimmed/deprecated; coverage for Springer/Elsevier stubbed | New orchestrator passes integration smoke tests; old imports emit deprecation warnings |
| P3 | Authentication & Security Hardening | Centralised auth helpers; credential flows documented; compliance checklist added | Playwright-based flows scripted; security checklist signed off |
| P4 | Testing & Tooling Upgrade | Deterministic test suite; added mocks; CI matrix (lint, unit, integration) | Tests run without secrets; coverage reported |
| P5 | Documentation & Release | MkDocs/Sphinx site; user & dev guides aligned; changelog summarises migration | Docs build artefact published; version tagged |

## 5. Task Breakdown & Dependencies

### Phase P0 – Preparation
- Capture current dependency list (`pip freeze > build/baseline_requirements.txt`).
- Run existing test targets (unit + selected integration) and store logs in `build/baselines/`.
- Enable CI (GitHub Actions or equivalent) with status badge.

### Phase P1 – Structure & Docs
1. Inventory scripts in root; classify into `keep`, `archive`, `delete`.
2. Create `archive/legacy_scripts/` with README describing contents and usage notes.
3. Move actively maintained helpers into `scripts/maintenance/`.
4. Update top-level `README.md` to reflect new structure and link to `GENERAL_AUDIENCE_OVERVIEW.md`.
5. Create `docs/guide/README.md` as the official landing page; relocate historical reports to `docs/history/`.

### Phase P2 – Downloader Consolidation
1. Audit overlaps between `src/downloader/` and `src/publishers/`.
2. Decide canonical orchestrator API (proposal: async orchestrator in `src/downloader/orchestrator.py`).
3. For each publisher:
   - Extract stable logic from `src/publishers/*`.
   - Port into `src/downloader/strategies/` modules.
   - Provide compatibility wrapper in old location importing from new module and emitting warning.
4. Update unit tests to cover ported logic.
5. Delete or archive obsolete modules after two release cycles.

#### Phase P2 Audit Notes (2025-09-22)
- `src/downloader/orchestrator.py` already instantiates async-aware strategies and batches via `UniversalDownloader`; however Springer/Elsevier entries are templates.
- `src/publishers/unified_downloader.py` drives the legacy synchronous adapters (`wiley_publisher.py`, `siam_publisher.py`, etc.) that still contain the production-ready logic.
- Immediate shim approach: introduce thin wrappers inside each legacy publisher module that expose the new async implementations while maintaining the existing method signatures. The `unified_downloader.py` facade can emit `DeprecationWarning` and delegate to the async orchestrator via `asyncio.run` for compatibility during migration.
- Shared utilities (credential handling, filename validation) should be lifted into `src/infrastructure/` and imported from both paths until the legacy wrapper is removed.
- Testing impact: legacy tests in `tests/unit/test_unified_downloader_*` expect synchronous mocks; add async test coverage in the `downloader` suite and convert old tests to run against the shim to avoid duplication.

### Phase P3 – Authentication & Security
1. Centralise session handling in `infrastructure/auth/session_manager.py`.
2. Implement Springer & Elsevier flows (SSO templates, fallback flows) with pluggable handlers.
3. Document authentication configuration in `docs/guide/authentication.md` including compliance notes.
4. Add automated health checks for credential encryption and SSL enforcement.

### Phase P4 – Testing & Tooling
1. Add `pyproject.toml` with tooling (ruff, mypy, black, pytest).
2. Introduce mock servers or recorded fixtures for publisher endpoints (e.g., `tests/fixtures/publisher_mocks/`).
3. Split test suite into `unit`, `integration`, `e2e`; ensure CI can skip network-dependent tests without credentials.
4. Track coverage; gate merges on lint + unit tests.

### Phase P5 – Documentation & Release
1. Configure MkDocs/Sphinx, generate architecture diagrams (PlantUML / Mermaid).
2. Publish developer runbook, API reference, and operations manual.
3. Record migration notes: old module paths → new paths, CLI command changes, environment setup.
4. Tag release, update `CHANGELOG.md`, and circulate announcement.

## 6. Validation Checklist (Per Task)

- ✔️ Unit tests covering changed modules run locally.
- ✔️ Integration smoke test (download + validation pipeline) executed or mocked.
- ✔️ Linting passes (ruff/flake8) with no new warnings.
- ✔️ Documentation updated (README, guide, CHANGELOG entries).
- ✔️ Blueprint status table updated with progress notes.

## 7. Progress Tracker

| Date | Phase | Task | Status | Notes |
|------|-------|------|--------|-------|
| 2025-09-22 | P0 | Capture dependency snapshot and unit-test baseline | Completed with known failure | `pip freeze` stored; unit tests logged (`tests/unit` failure: missing `strict_category_filter` arg) |
| 2025-09-22 | P0 | Restore green unit suite (strict category filter, async DB fallback) | Completed | Added strict category filtering + CMO collection (`src/discovery/integration.py`), implemented async SQLite shim when `aiosqlite` missing (`src/core/database.py`); `pytest tests/unit` all pass |
| 2025-09-22 | P1 | Establish clean root layout & doc structure | Completed | Moved legacy scripts to `archive/legacy_scripts/` and `scripts/manual/`, centralised reports under `docs/history/`, added onboarding guide, refreshed `README.md` |

Usage: append a row after completing or starting a task; keep short but specific notes (e.g., “Ported Wiley downloader to new strategy module; compatibility shim shipped”).

## 8. Communication & Ownership

- **Primary maintainers**: _(populate with names/contacts)_
- **Code review rule**: at least one reviewer familiar with publisher flows.
- **Weekly sync**: dedicate 30 minutes to review progress tracker and unblock tasks.
- **Decision log**: create `docs/DECISION_LOG.md` to capture trade-offs (e.g., dropping legacy adapters).

## 9. Appendix – Target Directory Layout

```
project/
├── archive/
│   └── legacy_scripts/
├── config/
├── docs/
│   ├── guide/
│   ├── history/
│   └── DECISION_LOG.md
├── scripts/
│   └── maintenance/
├── src/
│   ├── automation/        # CLI, schedulers, monitoring entry points
│   ├── domain/            # metadata models, validation logic
│   ├── infrastructure/    # downloaders, auth, storage
│   ├── presentation/      # templates, report generators
│   └── shared/            # utilities, constants
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── tools/
├── GENERAL_AUDIENCE_OVERVIEW.md
├── README.md
└── pyproject.toml
```

Keep this layout as the north star; adjust details as implementation findings arise.

---

_Update this blueprint at the end of each session so future contributors can resume without context loss._
