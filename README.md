# Math-PDF Manager

Personal pipeline that maintains a mathematician's ~28,000-paper Dropbox
library: renames PDFs to a strict canonical form, files them into the
right section, tracks per-paper identity in a sidecar JSON, finds papers
that have been published since you saved a preprint, downloads the
published version from one of 21 publishers, surfaces every actionable
event in one **Attention Queue**, and now ships a Streamlit cockpit with
nine task-focused tabs so you never have to drop to a terminal.

## What's here

```
src/
  ui/
    cockpit.py             ← Streamlit review UI (nine tabs; see below)
    cockpit_actions.py     ← DOI download, watcher launchctl, config editor
    attention_queue.py     ← unified "needs your attention" collector layer
  processing/
    ingest.py              ← extract metadata → canonical name → file
    identity.py            ← per-paper .meta.json sidecar (DOI, hash, history)
    publication_state.py   ← state machine: misses → permanently_unpublished
    topic_router.py        ← classify + hardlink into 07a-07f folders
    conflict_resolver.py   ← Dropbox conflict-copy diff/keep/promote
    bulk_sort.py           ← process raw PDFs dropped into 12 - To be sorted/
    upgrade_to_published.py ← preprint → published version round-trip
    publication_checker.py ← Crossref scan to find newly-published papers
    aging_checker.py       ← move 03/working → 02/unpublished when too old
    duplicate_finder.py    ← exact + fuzzy duplicate detection
    paper_transition.py    ← simple file-mover when status changes
    paper_index.py         ← classify file → (status, topic, alpha-subdir)
    topic_classifier.py    ← keyword + optional-LLM topic suggestion
    undo_log.py            ← transactional undo (sidecar-aware moves)
    filename_normalizer.py ← one-off cleanup utility
  organization/system.py   ← FolderRouter + OrganizationSystem (age-aware)
  arxivbot/models/cmo.py   ← Author + CMO + canonical filename generator
  core/sentence_case.py    ← 848-entry whitelist sentence-case engine
  core/config_paths.py     ← single source of truth for config/data dirs
  utils/browser_window.py  ← quiet-window helper: park headful Chromium offscreen
  validators/filename_checker/  ← 2,800-line validator (sentence-case + dashes
                                  + author format + unicode safety)
  watcher/daemon.py        ← watch ~/Downloads/MathInbox/, auto-ingest
  maintenance/weekly_report.py ← all-in-one publication/aging/duplicate scan
                                  + --auto-apply-safe for the Monday plist
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

Nine tabs in the sidebar:

| Tab | What it does |
|---|---|
| **Attention** | Unified inbox of things that want your eyes: watcher ingest failures, manual-download requests from the upgrade pipeline, aging working papers, borderline (0.75-0.95 confidence) Crossref matches, papers the state machine has given up on, and Dropbox conflict copies. The label shows a count badge (cached 60s). Each item exposes per-source actions (Reset recheck, Open DOI, Dismiss N days, …). |
| **Sort Queue** | Walks `12 - To be sorted/{01,03,05}/`. Each paper shows: extracted title/authors/DOI, proposed canonical filename (editable), proposed destination, first-page snippet, and topic suggestions with **checkboxes** so a single approve click both files the paper AND hardlinks it into the selected `07a-07f/` folders. |
| **Upgrade Queue** | Reads a publication-checker JSON report. For each candidate: shows the matched DOI/journal/confidence, the preprint, and the proposed download. Approve triggers the 7-strategy downloader chain. |
| **To Download** | Manual-download queue + DOI form. Type a DOI (or paste a `https://doi.org/…` URL) and the full strategy chain runs; the resulting PDF lands in the watcher inbox. The 04/ flag browser below lets you download or mark-done each pending flag inline. |
| **Conflicts** | Side-by-side resolver for Dropbox conflict copies. Shows bytes/pages/mtime for both files and offers Keep canonical / Keep conflict / Keep both (rename to `-v2`) / Open both. The suggested action is starred. |
| **Maintenance** | One-click "Run weekly now" (subprocess to `maintenance.weekly_report` with optional `--auto-apply-safe`) plus the same in-process check toggles the previous version had. |
| **Stats** | Live counts per top-level folder + trash sizes. |
| **Activity** | Every approval in this session, with a per-transaction undo button. Persistent across cockpit restarts (`~/.mathpdf/cockpit_activity.jsonl`). |
| **Settings** | Form-driven editor for the watcher YAML config (library root, inbox folder, default status, settle seconds, notifications). |

The sidebar also shows the **watcher status** (ON/OFF with pid) and
Start/Stop buttons that call `launchctl bootstrap` / `bootout` on the
installed plist.

Every approval goes through the undo log; sources move to `.trash/` (never
hard-delete). Every sidecar move/rename also carries the
`<stem>.meta.json` companion along, so a paper's identity history
travels with the file.

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
| `MATHPDF_QUIET_X` / `_Y` / `_W` / `_H` | Where to pin headful Playwright windows (Cloudflare flows, ETH login) | bottom-right 360×280 |
| `MATHPDF_QUIET_DISABLE` | Set to `1` to disable corner-pinning (debug Playwright flows) | unset |

## Per-paper identity sidecars

Every filed PDF gets a `<stem>.meta.json` sidecar:

```json
{
  "schema_version": 1,
  "content_sha256": "<first-1MB SHA-256>",
  "original_filename": "drop.pdf",
  "doi": "10.1007/...",
  "arxiv_id": "2401.01234",
  "first_ingested_at": "2026-05-17T12:34:56+00:00",
  "first_ingest_tx_id": "abc123",
  "copy_locations": ["/lib/02/U/.../Smith - Foo.pdf",
                     "/lib/07a - BSDEs/Smith - Foo.pdf"],
  "publication_checks": [
    {"date": "...", "source": "crossref", "hit": false, "confidence": 0.0}
  ],
  "recheck_count": 1,
  "last_check_date": "...",
  "permanently_unpublished": false,
  "topic_codes": ["07a"]
}
```

The sidecar travels with the PDF on every `logged_move`/`logged_rename`,
and topic-folder hardlinks recorded in `copy_locations` get renamed
along with the canonical so users browsing `07a/` never see a stale
filename.

CLI: `python -m processing.identity {backfill,show,drift} …` to backfill
legacy PDFs, inspect a sidecar, or verify the stored hash matches the
file on disk.

## Weekly auto-apply rules

The Monday launchd plist now passes `--auto-apply-safe`. Only the
strictly-safe subset of findings actually moves files:

| Rule | Trigger | Action |
|---|---|---|
| Safe upgrade | Crossref confidence ≥ 0.95 **and** filename + Crossref both report 1 author | `upgrade_to_published.upgrade_paper` (download + file + trash preprint) |
| Safe age-out | Working paper > 5y old **and** sidecar `permanently_unpublished=True` | Move 03 → 02 via `aging_checker.transition_aged_papers` |

A 6-year-old paper we've never Crossref-checked is **not** auto-aged —
it gets checked first, and only auto-ages once the state machine has
tried 3 times with zero hits.

All other findings stay in the HTML report and surface in the cockpit
**Attention** tab for user review.

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
PYTHONPATH=src python -m pytest tests/ --ignore=tests/harness -q
```

2,000+ passing tests across:

- `tests/test_processing/` — identity sidecar, state machine, topic router,
  conflict resolver, undo log, bulk sort, ingest authors, …
- `tests/test_maintenance/` — weekly check + auto-apply selection rules
- `tests/test_organization/` — folder routing + age-based status
- `tests/test_watcher/` — daemon event handling
- `tests/test_downloader/` — publisher strategies
- `tests/ui/` — cockpit smoke + cockpit_actions + attention queue
- `tests/audit/` — code-quality audits (no-empty-fstrings, no-headful-without-quiet_args,
  no-deprecated-datetime, etc.)
- `tests/harness/test_phase_integration.py` — end-to-end scenarios crossing
  ingest → sidecar → topic links → state machine → auto-apply → undo

The harness directory also contains:
- `test_empirical_batch.py` — opt-in via `MATHPDF_EMPIRICAL_BATCH=1`,
  files a random sample of real PDFs into a synth library
- `test_watcher_e2e.py` — drives the daemon's PDFHandler directly

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
