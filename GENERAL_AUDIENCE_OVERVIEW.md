# Academic Paper Companion

## 1. What This Project Wants to Achieve

Researchers spend a surprising amount of time doing housekeeping: hunting down articles across publisher websites, coping with stubborn log‑ins, fixing mangled filenames, and filing PDFs so they can be found again. This project sets out to be a digital assistant for that job. It aims to:

- **Find** relevant papers across public indexes such as ArXiv, Semantic Scholar, and OpenAlex.
- **Retrieve** paywalled copies through legitimate institutional logins (for example, ETH Zürich) when the user has access rights.
- **Store** the downloaded PDFs with clean, human‑friendly names and rich metadata so building a personal library becomes painless.
- **Protect** the user by treating credentials carefully, encrypting stored secrets, and validating filenames for security issues.

The long‑term vision is simple: let researchers focus on thinking, while the system handles the downloads, organisation, and tedium in the background.

## 2. Who It Helps

Although the codebase grew out of mathematics research, the tooling is useful to anyone who curates many academic papers:

- **Individual researchers** who keep private PDF archives.
- **Graduate students** who are new to literature reviews and want a dependable helper.
- **Research groups** juggling shared folders and wanting consistent naming rules.
- **Librarians or support staff** who assist academics with publisher access and compliance.

## 3. How the System Is Organised (Human Terms)

You can think of the project as four layers that cooperate:

1. **Discovery Layer** – scans public data sources for papers that match topics, author names, or identifiers like DOIs. It can run quick searches or continuous “watch” jobs when new papers appear.
2. **Access Layer** – knows how to talk to publishers. It first tries open copies, then uses institutional authentication if the user is entitled, and finally taps approved fallback sources for archived versions when permitted.
3. **Processing Layer** – once a PDF arrives, this layer checks that the file is complete, extracts metadata, and generates tidy filenames (for example, `Meyn, Tweedie - Markov Chains and Stochastic Stability.pdf`).
4. **Safety Net** – handles encryption of credentials, enforces secure network connections, and runs hundreds of automated checks so filenames cannot hide malicious tricks.

Everything is wrapped in a command‑line application (`src/main.py`) that ties the pieces together. A service registry (`src/core/services.py`) loads components on demand so the tool can be extended without rewriting the entry point.

## 4. Current Capabilities

| Capability | What Works Today | Notes |
|------------|------------------|-------|
| Open research discovery | ✅ | ArXiv, Semantic Scholar, OpenAlex, ORCID integration. |
| Institutional downloads | 🟡 | Strong support for Wiley, IEEE, SIAM in the legacy adapters; Springer & Elsevier flows still being finalised in the new async downloader. |
| Filename & metadata cleanup | ✅ | Unicode‑aware validator, large mathematician name list, metadata scoring. |
| Automation scripts | ✅ | Scheduler‑ready batch scripts, stress tests, monitoring hooks. |
| Security controls | ✅ | Credentials encrypted with PBKDF2 + Fernet, HTTPS enforced, filename sanitisation. |
| Documentation & onboarding | 🟡 | Many technical reports exist; newcomer guide is still being streamlined into one source. |

Legend: ✅ ready for everyday use • 🟡 partially complete • ❌ not yet available.

## 5. Why It Matters

- **Saves time:** Automated searches and downloads can process dozens of papers in the time it takes to click through one manual login.
- **Reduces errors:** Normalised filenames and metadata prevent duplicate storage, lost references, and confusing titles like `SpringerLink (5).pdf`.
- **Respects access rules:** All publisher interactions rely on the user’s authorised credentials—no scraping shortcuts or terms‑of‑service violations.
- **Keeps libraries tidy:** Consistent naming and metadata make it easier to sync with reference managers or share folders with collaborators.
- **Maintains security:** Sensitive passwords are never stored in plain text, and downloads are checked for basic integrity before they land in the user’s archive.

## 6. Live Example Scenarios

1. **Weekly literature sweep** – point the discovery layer at `math.PR` and `cs.LG`, let it fetch the newest abstracts, score relevance, and download selected PDFs into a dated folder.
2. **Conference preparation** – supply a list of DOIs from a conference program; the orchestrator attempts authorised downloads, leaving a structured bundle of papers for quick review.
3. **Library clean‑up day** – run the filename validator across an existing folder; it reports unsafe characters, inconsistent author formats, and can auto‑rename files safely.

## 7. What Still Needs Work

- **Springer & Elsevier completion:** The async downloader (`src/downloader/universal_downloader.py`) carries template code; authentication and full download flows need to be finished before these publishers match Wiley/IEEE reliability.
- **Dual downloader stacks:** Both the newer async strategies and the older `src/publishers` adapters are active. Consolidating them into a single maintained path will simplify troubleshooting and onboarding.
- **User onboarding:** The documentation folder is rich but sprawling. A streamlined “start here” guide with environment setup, Playwright installation, and credential configuration is underway.
- **Automated verification:** Tests cover encryption and metadata logic, but publisher flows still require institutional credentials. More mocks and integration harnesses would help contributors run checks without live accounts.

## 8. Getting Started (Non‑Developer Friendly)

1. **Install Python 3.10+** and create a virtual environment.
2. **Install dependencies**: `pip install -r config/requirements.txt` (Playwright will prompt for browser binaries on first use).
3. **Prepare credentials**: run the secure credential manager to create an encrypted store, then add institutional usernames/passwords only if your institution approves automated access.
4. **Try a dry run**: `python -m src.main --discover --categories math.PR --max-papers 5 --download-papers` to see the discovery workflow in action.
5. **Validate an existing folder**: `python -m src.main ~/MyPapers --dry-run --strict` to receive a report without making changes.

The system assumes ethical use: only download material you are licensed to access, respect publisher terms, and consult your institution before automating logins.

## 9. Roadmap Highlights

- **Complete remaining publisher connectors** with robust, tested authentication flows.
- **Unify download orchestration** so there is one canonical engine for all sources.
- **Bundle a quick‑start wizard** that bootstraps configuration, Playwright browsers, and sample runs for new researchers.
- **Expose optional APIs** (HTTP or gRPC) so external tools can trigger searches or fetch status reports.
- **Expand monitoring hooks** for labs that want dashboards of download success rates, most active sources, or failed credentials.

## 10. How to Contribute or Engage

- **Researchers:** Pilot the tool on a subset of your archive, share feedback on login flows that match or conflict with your institution’s policies.
- **Developers:** Dive into `src/downloader` and `src/publishers`, help complete missing flows, or write tests that simulate publisher responses.
- **Librarians & IT staff:** Review the security model, suggest improvements for credential handling, and advise on compliance guidelines.
- **Documentation supporters:** Help consolidate the many reports into a single public playbook so teams can adopt the system without reading dozens of historical notes.

## 11. Quick Reference of Key Components

- `src/main.py` – command‑line entry point tying configuration, validation, discovery, and processing together.
- `src/downloader/orchestrator.py` – async orchestration of download strategies with fallback logic and batch reporting.
- `src/publishers/unified_downloader.py` – legacy but battle‑tested publisher adapters (IEEE, SIAM, Wiley, and others).
- `src/validators` – comprehensive filename and Unicode safety checks.
- `tests/` – regression suite covering credential storage, metadata sources, and downloader wiring.

## 12. Final Thoughts

The “Academic Paper Companion” is already useful for automating tedious parts of literature management, especially when paired with institutions that permit scripted access. Its value grows as more publishers are fully integrated and as the onboarding experience becomes friendlier. For now, think of it as a capable assistant that still needs a bit of supervision—one that promises to give every researcher a well‑organised, trustworthy digital library without the late‑night administrative grind.
