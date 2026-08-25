# Where this project is

**Measured 2026-08-25.** Every number below was computed against the live
library or the current tree; nothing is carried over from an older document.
If you change something here, re-measure it — a stale figure in this file is
worse than no file.

Read `CLAUDE.md` first for the non-negotiables. This document is the state.

---

## The library

| | |
|---|--:|
| PDFs on disk | 29,463 |
| in scope for tooling (`processing/library_scope.py`) | 25,253 |
| archival collections, deliberately excluded | 1,908 |
| staging (`12 - To be sorted`, `04 - To be downloaded`) | 2,299 |
| distinct titles | 25,005 |
| operation-log transactions / operations | 34 / 16,162 |
| still restorable today | 97.82% |
| `.trash/` (never purged) | 139 PDFs |

---

## Needs your decision, now

### 1. The watcher is deaf and every screen says it is fine

`~/Downloads/MathInbox` **does not exist**. The daemon has been running for
5 days 21 hours (pid 6282, since 19 Aug 14:13) and its log ends at that
startup line. Two independent tests confirmed watchdog's Observer gets zero
events after a watched directory is deleted and recreated — recreating the
folder is not enough.

Meanwhile the cockpit sidebar renders *"Automatic filing: ON"*, and the To
Download page says a saved PDF "is filed into your library automatically from
there." It will not be. **Anything downloaded now goes into a folder nothing
is watching.**

Fix: restart the daemon, then give it a periodic `iterdir` that re-`mkdir`s
and reschedules when the inode changes, and give `watcher_status()` a second
predicate so "running" means "has looked recently".

### 2. The Monday sweep has never run under current code

Only the watcher plist is installed; there is no weekly agent. The newest
report is **144 days old** and predates the current naming scheme, so it was
produced by older code. The "▶ Run weekly now" button has never been pressed
either (0 hits across the activity log, May–Aug).

Do **not** install it as shipped: the plist runs `/usr/bin/env python3`, which
under launchd resolves to the Command Line Tools Python where `rapidfuzz` is
missing, and `weekly_report.py:513` calls `check_duplicates` unguarded — the
job would die before writing anything. Pin `.venv/bin/python` first. Treat
`--auto-apply-safe` as a separate decision: it renames and moves unattended.

Consequence already paid: the Upgrade Queue has been serving April data, and
Crossref decisions were taken on it in August.

### 3. A second, invisible undo log — and one paper that survived by accident

`Scripts/.operation_log/` holds 6 transactions the cockpit cannot see. One of
them, `9b9d5b2f584e`, records a move to `/dev/null` of

> `03 - Working papers/A/2023/Abraham, R., Delmas, J.-F., Weibel, J. -
> Probability-graphons, limits of large dense weighted graphs.pdf`

That file is gone from its shelf and from its intended home in
`01 - Published papers/Z`. **The only reason the paper still exists is an
accidental copy under `07e - Optimal control on networks`.**

The branch that did it is fixed (see below). The log is **not** folded into
the visible one yet, deliberately: transaction `0c2b96e0e3af` has three live
published destinations whose sources are long-gone temp directories, so
exposing an Undo button on it before the fix would have deleted three real
PDFs. Order matters — fix first, fold second.

---

## Fixed in the last two days

| what | evidence |
|---|---|
| Undoing a copy retires to `.trash/` and refuses when the original is gone | the only hard delete of a library PDF in `src/`; a test now forbids a bare `unlink()` in the undo path |
| One initial-spacing rule (`core/initials.py`) | three implementations, none complete; 9 blocks fixed, 0 titles harmed |
| One maths-region rule (`core/math_regions.py`) | three implementations, **all wrong**; the incumbent called `é` mathematics 4,331 times |
| One filename decomposer (`processing/filename_ground_truth.py`) | 99.86% of names; 0 titles ever mistaken for an author block |
| One scope rule (`processing/library_scope.py`) | replaced three disagreeing private skip lists |
| Author blocks corrected in the library | **210 renamed**, txs `20dce78dc107` and `d839a68c1955`, reversible |
| Control and format characters kept out of filenames | 7 live files still carry them; listed in `known-issues-cockpit.md` |

---

## Known and open, ranked

1. **10 library-changing cockpit callbacks have never been executed by a
   test** — `_undo_transaction` 0 of 25 statements, `_apply` 0/10,
   `render_spelling` 0/85 (and it calls `apply_renames(dry_run=False)`).
   Reintroducing the exact bug commit `323cdc1` fixed leaves the suite green.
2. **Three slow screens**: Sort Queue 10–11 s per paper (a failed arXiv
   lookup is never cached), Home/Attention 12–76 s, Conformance ~3.5 min
   against a label saying "about a minute".
3. **`filename_ground_truth` has no production caller.** 27 sites still split
   on `" - "` naively. The rename path produces 0 wrong proposals today, so
   this is latent, not active — but it is the module the docs call the owner
   of that split.
4. **`docs/FILENAME_CONVENTION.md` is actively wrong** — it prescribes an
   author-initial format the code deliberately rewrites and the library
   contradicts 3,844 to 1. Delete or rewrite it.
5. **31 stranded paper-identity records**, with a 150-line repair that has no
   cockpit surface.
6. **12 cockpit issues** in `docs/known-issues-cockpit.md`, unfixed by design.
7. **23% of `src/` is unreachable** — 62 modules, 12,205 lines, concentrated
   in `core/` (59% dead) and an abandoned `auth/` package that imports a
   module which does not exist.

---

## Where to look

| question | file |
|---|---|
| the rules, the traps, how to run things | `CLAUDE.md` |
| what the library contains, extraction accuracy by population | `docs/extraction-populations.md` |
| cockpit issues | `docs/known-issues-cockpit.md` |
| duplicated rules: what was merged and what deliberately wasn't | `docs/rival-implementations.md`, `docs/duplicated-rules-review.md` |
| what may be touched | `src/processing/library_scope.py` |
| how a filename decomposes | `src/processing/filename_ground_truth.py` |
