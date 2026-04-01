# Project Guide

This guide is the starting point for contributors and operators of the Academic Paper Companion system.

## Quick Links

- [General Audience Overview](../../GENERAL_AUDIENCE_OVERVIEW.md) — goals, users, and value proposition.
- [Refactor Master Plan](../REFACTOR_MASTER_PLAN.md) — ongoing restructuring roadmap.
- [Architecture Notes](../history/ARCHITECTURE.md) — detailed component breakdown prior to the current reorganisation.

## Getting Started

1. **Set up Python**: use 3.12+ and create a virtual environment.
2. **Install dependencies**: `pip install -r config/requirements.txt`.
3. **Prepare credentials**: run the secure credential manager to create the encrypted store before attempting publisher automation.
4. **Run a smoke test**: `pytest tests/unit --maxfail=1` confirms the baseline environment.
5. **Process sample PDFs**: `python -m src.main ~/Papers --dry-run --strict` to exercise the validation pipeline without making changes.

## Repository Layout (2025 refresh)

```
project/
├── archive/legacy_scripts/      # Historical automation scripts (manual reference)
├── config/                      # Configuration templates and requirement lists
├── docs/                        # Guides, history, reports (see sections below)
│   ├── guide/                   # Living documentation you are reading now
│   └── history/                 # Previous audits, roadmaps, and summaries
├── scripts/                     # Maintained shell/python helpers
│   └── manual/                  # Migrated one-off debug and test scripts
├── src/                         # Application source code
├── tests/                       # Unit, integration, and e2e test suites
├── tools/                       # Developer utilities
└── GENERAL_AUDIENCE_OVERVIEW.md # External-facing explainer
```

## Documentation Map

- **Operational**: this guide and the general overview.
- **Historical context**: `docs/history/` contains previous audits, reports, and exploratory notes. Consult them when you need background but keep them out of day-to-day workflows.
- **Refactor tracking**: `docs/REFACTOR_MASTER_PLAN.md` captures decisions, progress, and next actions for the modernisation effort.

## Contributing Workflow

1. Branch from `master` and ensure the unit suite is green.
2. Follow the phased plan in the refactor blueprint; update the progress table as you finish tasks.
3. Keep cross-cutting changes small and well tested. Use the new `scripts/manual/` area for any ad-hoc experiments instead of dropping files at the repository root.
4. Update documentation with every behavioural change to avoid drift.

For additional questions, check the decision log (if present) or open a discussion in the repository tracker.
