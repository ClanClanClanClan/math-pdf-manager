# Math-PDF Manager

Management system for a ~28,000 paper mathematics research library.
Handles filename validation, metadata extraction, publication
tracking, and library organisation.

## What it does

### Working features

**Filename validation and generation** — the core feature. Enforces
ultra-pedantic academic naming conventions:
- Sentence case with 848-entry capitalisation whitelist
- En-dash for compound names (McKean–Vlasov, Black–Scholes) via
  305-entry dash whitelist
- Ligature expansion, ellipsis normalisation, quotation mark
  typography
- NFC Unicode normalisation, dangerous character removal
- Dynamic "et al." truncation within filesystem byte limits
- See `docs/FILENAME_CONVENTION.md` for the full specification

**Paper ingestion** — extract metadata from a PDF and file it:
```bash
python -m processing.ingest paper.pdf --dry-run -v
```
Tries PyMuPDF embedded metadata → ArXiv API → Crossref DOI lookup →
LLM extraction. Generates canonical filename, files in correct
directory, logs all operations for undo.

**Publication checking** — verify if working papers have been published:
```bash
python -m processing.publication_checker "02 - Unpublished papers/" -v
```
Queries Crossref by title, scores matches on title similarity + author
overlap.  Found 21/23 "not fully published" papers had been published.

**Paper transitions** — move papers between status folders:
```bash
python -m processing.paper_transition report.json --dry-run
```
Interactive approval mode. Every file operation logged for undo.

**Duplicate detection** — find duplicates across the library:
```bash
python -m processing.duplicate_finder /path/to/library -v
```

**Topic classification** — classify papers into topic folders (07a–07f):
```bash
python -m processing.topic_classifier "McKean-Vlasov optimal control"
```
Two-tier: keyword matching (80% of cases) + LLM zero-shot.

**Batch validation** — validate all filenames in the library:
```bash
python main.py /path/to/library --dry-run
```

### In development

- **LLM fine-tuning** — Qwen2.5-7B fine-tuned on 20K papers for
  metadata extraction.  Training data generated, model trained once
  (74% title exact match), improvements prepared for retrain.
  See `ml/pdf-meta-llm/README.md`.

- **ArXiv discovery** — code exists in `src/discovery/` but uses
  stub implementations.  Not yet functional end-to-end.

- **Publisher downloaders** — IEEE, SIAM, Springer, Wiley, Nature,
  Oxford, JSTOR, AMS, AIMS, Project Euclid modules exist in
  `src/publishers/`.  Need full audit.

## Library structure

```
Maths/
├── 01 - Published papers/{A-Z}/
├── 02 - Unpublished papers/{A-Z}/        (old, unlikely to publish)
├── 03 - Working papers/{A-Z}/{year}/     (recent, likely to publish)
├── 04 - Papers to be downloaded/
├── 05 - Books and lecture notes/
├── 06 - Theses/
├── 07a - BSDEs/                          (mirrors 01-06 structure)
├── 07b - Contract theory/
├── 07c - Time-inconsistent stochastic control/
├── 07d - Stackelberg games/
├── 07e - Optimal control on networks/
├── 07f - Non-commutative stochastic calculus/
├── 08 - Séminaires de probabilités/
├── 09 - JEHPS/
└── 10 - Math slides/
```

## Setup

```bash
# Python 3.12 recommended
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# For LLM metadata extraction (optional)
pip install llama-cpp-python
```

## Tests

```bash
pytest tests/core/ tests/audit/ tests/pdf_processing/ tests/security/ tests/utils/ --no-cov -q
# 1022 passed
```

## Project structure

```
src/
├── arxivbot/models/cmo.py     # Canonical filename generation (CMO)
├── validators/filename_checker/ # 2,800-line filename validator
├── core/sentence_case.py       # Academic sentence case conversion
├── processing/                  # Ingest, publication checker, transitions
├── organization/system.py       # Library folder routing
├── pdf_processing/              # Multi-tier metadata extraction
├── publishers/                  # Publisher-specific downloaders
└── main.py                      # Batch processing CLI

ml/pdf-meta-llm/                 # LLM training pipeline
docs/                            # Specifications and audits
config/config.yaml               # 848-entry capitalisation whitelist
data/                            # Name whitelists, known words
```

## Key documentation

- `docs/FILENAME_CONVENTION.md` — authoritative filename spec
- `docs/TEST_AUDIT.md` — test coverage analysis
- `docs/PROJECT_OVERVIEW.md` — detailed feature description
- `docs/ARCHITECTURE.md` — technical architecture
