# Math-PDF Manager

Personal pipeline that maintains a mathematician's ~28,000-paper Dropbox
library: renames PDFs to a strict canonical form, files them into the right
section, finds papers that have been published since you saved a preprint,
downloads the published version from one of 21 publishers, and now ships a
Streamlit cockpit so you can review and approve everything by hand.

## What's here

```
src/
  ui/cockpit.py            ← Streamlit review UI (see "Quick start" below)
  processing/
    ingest.py              ← extract metadata → canonical name → file
    bulk_sort.py           ← process raw PDFs dropped into 12 - To be sorted/
    upgrade_to_published.py ← preprint → published version round-trip
    publication_checker.py ← Crossref scan to find newly-published papers
    aging_checker.py       ← move 03/working → 02/unpublished when too old
    duplicate_finder.py    ← exact + fuzzy duplicate detection
    paper_transition.py    ← simple file-mover when status changes
    paper_index.py         ← classify file → (status, topic, alpha-subdir)
    topic_classifier.py    ← keyword + optional-LLM topic suggestion
    undo_log.py            ← transactional undo for every move/copy/rename
    filename_normalizer.py ← one-off cleanup utility
  organization/system.py   ← FolderRouter + OrganizationSystem (routing)
  arxivbot/models/cmo.py   ← Author + CMO + canonical filename generator
  core/sentence_case.py    ← 848-entry whitelist sentence-case engine
  core/config_paths.py     ← single source of truth for config/data dirs
  validators/filename_checker/  ← 2,800-line validator (sentence-case + dashes
                                  + author format + unicode safety)
  watcher/daemon.py        ← watch ~/Downloads/MathInbox/, auto-ingest
  maintenance/weekly_report.py ← all-in-one publication/aging/duplicate scan
  downloader/
    publishers/            ← 21 publisher-specific downloaders
    doi_downloader.py      ← unified DOI → PDF strategy chain
    cloudflare_session.py  ← semi-automated Cloudflare bypass
    eth_institutional.py   ← Playwright + ETH Shibboleth auth

deploy/launchd/            ← .plist files for the watcher + weekly cron
tests/                     ← 1,692 passing tests
config/, data/             ← whitelists and config
```

## Library convention

```
{MATH_LIBRARY}/
├── 01 - Published papers/         (A-Z subfolders, has DOI)
├── 02 - Unpublished papers/       (A-Z, has ArXiv ID, no DOI)
├── 03 - Working papers/           (A-Z, year subfolders, ≥3 years old)
├── 04 - Papers to be downloaded/  (by journal, with .txt placeholders)
├── 05 - Books and lecture notes/  (flat)
├── 06 - Theses/                   (A-Z)
├── 07a-07f/                       (topic folders: BSDEs, Contract theory, etc.)
├── 08, 09, 10/                    (special collections, untouched by tools)
└── 12 - To be sorted/             (intake; bulk_sort processes from here)
    ├── 01 - Published papers/      (sources you want filed as published)
    ├── 02 - Unpublished papers/
    ├── 03 - Working papers/
    ├── 05 - Books and lecture notes/
    └── 06 - Theses/
```

The library root resolves via `MATH_LIBRARY` env var, falling back to the
Dropbox path in `src/constants.py`.

## Quick start

### 1. Install

```bash
pip install -e ".[dev]"           # editable install with dev tools
# or just:
pip install -r requirements.txt
```

### 2. Use the Streamlit cockpit (recommended)

```bash
PYTHONPATH=src streamlit run src/ui/cockpit.py
```

Five tabs in the sidebar:

| Tab | What it does |
|---|---|
| **Sort Queue** | Walks `12 - To be sorted/{01,03,05}/`. Each paper shows: extracted title/authors/DOI, proposed canonical filename (editable), proposed destination, first-page snippet, and topic suggestions. Approve → file. Skip → skip. Flag → flag for manual review. |
| **Upgrade Queue** | Reads a publication-checker JSON report. For each candidate: shows the matched DOI/journal/confidence, the preprint, and the proposed download. Approve triggers the 7-strategy downloader chain. |
| **Maintenance** | Runs the same checks as `weekly_report.py` (publications, aging, duplicates, 12/ backlog) and shows results inline. |
| **Stats** | Live counts per top-level folder + trash sizes. |
| **Activity** | Every approval in this session, with a per-transaction undo button. |

Every approval goes through the undo log; sources move to `.trash/` (never
hard-delete).

### 3. CLI alternatives

```bash
# Preview what bulk_sort would do — never touches files:
PYTHONPATH=src python3 -m processing.bulk_sort --dry-run

# Process a small batch with per-batch confirmation:
PYTHONPATH=src python3 -m processing.bulk_sort --limit 10

# Watch ~/Downloads/MathInbox/ and auto-ingest on drop:
PYTHONPATH=src python3 -m watcher.daemon

# Weekly maintenance run (publication + aging + duplicate checks):
PYTHONPATH=src python3 -m maintenance.weekly_report
```

### 4. Install as launchd agents (optional)

```bash
bash deploy/launchd/install.sh
```

This installs two agents in `~/Library/LaunchAgents/`:
- `ch.ethz.dpossamai.mathpdf.watcher` — runs the inbox watcher continuously
- `ch.ethz.dpossamai.mathpdf.weekly` — runs maintenance every Monday at 09:00

Logs land in `~/.mathpdf/`.

## Environment variables

| Name | Purpose | Default |
|---|---|---|
| `MATH_LIBRARY` | Library root | `~/Library/CloudStorage/Dropbox/Work/Maths` |
| `UNPAYWALL_EMAIL` | Used by Unpaywall API in DOIDownloader | (unset → strategy skipped) |
| `ETH_USERNAME` | ETH Shibboleth username for paywalled downloads | (unset → strategy skipped) |
| `ETH_PASSWORD` | ETH Shibboleth password | (unset → strategy skipped) |

## Filename convention

The full spec is `docs/FILENAME_CONVENTION.md`. In short:

```
{Family1, I., Family2, I., ... - Title.pdf}
```

- Sentence case for the title (848-entry whitelist of canonical
  capitalisations like LaTeX, BSDEs, Lévy, etc.)
- En-dash between compound surnames (McKean–Vlasov via 305-entry whitelist)
- "et al." truncation when the filesystem byte limit (255 on macOS) would
  otherwise be exceeded
- NFC Unicode normalisation
- Colon → comma (subtitle convention)
- Dashes, ligatures, ellipses, quotation marks normalised
- LaTeX commands in PDF metadata (`\^o`, `\'e`, `\v{S}`, …) decoded to Unicode
  before sentence-case processing

## Publisher coverage

21 publishers registered in `src/downloader/publishers/`, covering ~91%
(1,601 of 1,769 high-confidence) of published papers in a typical scan:

| Tier | Publishers | Strategy |
|---|---|---|
| Direct OA | Springer, Project Euclid, Centre Mersenne, EDP Sciences, EMS Press, Cambridge, VTeX, ALEA, MDPI | Resolve DOI → direct PDF URL |
| ETH auth | AMS, AIMS, IOP, Oxford, IEEE, De Gruyter | ETH Shibboleth via Playwright |
| Cloudflare | SIAM, Elsevier, Wiley (+10.1112 LMS), Taylor & Francis, INFORMS, World Scientific | Semi-automated cookie capture |

`DOIDownloader.download(doi)` tries Unpaywall → publisher-specific → direct
DOI → Sci-Hub (pre-2021) → Cloudflare session → Anna's Archive → ETH auth.

## Testing

```bash
PYTHONPATH=src python -m pytest tests/test_processing/ tests/test_organization/ tests/test_watcher/ tests/test_maintenance/ tests/test_downloader/ -v
```

1,692 passing tests as of the current state. See `tests/test_*/` for unit
suites and `tests/audit/` for code-quality audits.

## Safety guarantees

- **No silent deletes.** Every "delete" is actually a move to
  `.trash/{sub}/`, recoverable.
- **Transactional undo.** Every move/copy/rename is logged in
  `.operation_log/{tx_id}.json` and reversible via
  `python -m processing.undo_log undo --transaction {tx_id}`.
- **Dry-run everywhere.** Every CLI has `--dry-run`. The cockpit's preview
  is read-only; nothing happens without an explicit approve click.
- **Quality gate.** `bulk_sort` refuses to file a paper whose canonical
  name would be the raw source stem (i.e. no metadata was successfully
  extracted) — it's flagged for manual review instead.
- **`/dev/null` safety.** The undo log refuses to "restore" from special
  device files, fixing an old data-loss bug where deletions were recorded
  as moves to `/dev/null`.

## Development

```bash
# Set up a worktree for safe experimentation:
git worktree add ../mathpdf-experiment -b experiment

# Run the full test suite:
PYTHONPATH=src pytest --timeout=60

# Run just the modules you changed:
PYTHONPATH=src pytest tests/test_processing/test_ingest_authors.py -v

# The launchd agents can be triggered manually for testing:
launchctl start ch.ethz.dpossamai.mathpdf.weekly
```

## Known limitations

- ETH Shibboleth flows tested with Springer only; other auth-required
  publishers (AMS, AIMS, IOP, Oxford, IEEE, De Gruyter) work in theory
  but haven't been exercised at scale.
- Cloudflare publishers need a manual "session start" (you solve one
  CAPTCHA, cookies are saved for ~60 min, batch downloads run with those).
- LLM-based metadata extraction and topic classification require a local
  GGUF model (`~/.mathpdf_models/gguf/qwen2.5-7b-pdfmeta-q4_k_m.gguf`) or
  fall back to heuristics.
- Project Euclid recently added Imperva bot detection; the integration
  test for it is marked `xfail`.
