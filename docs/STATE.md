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

### 0. 148 words are waiting for you to say name-or-word

The caser now learns which words this library capitalises from the library
itself -- a census over every mid-title word, which covers mathematicians,
places, months and Roman numerals with no lists at all (2,388 capitals
recovered, 0 imposed, 0 lost, 0 titles damaged).

Where the evidence is genuinely mixed it does NOT guess: **124 words are held
back** until you decide, and 24 more are **flagged** -- French adjectives built
from a name, where the library is unanimous but French may disagree. They are
on the cockpit's **Spelling** page, closest call first, with the counts, a note
saying whether the word is an author in your library, and a Name / Word button
each.

Your answers go to `config/casing_decisions.json`, survive a re-mine, and beat
the evidence. When the library's usage later crosses the rule, the word comes
back marked *changed since you decided*. See `docs/proper-nouns-measured.md`.



### 1. Automatic filing — FIXED, needs one click from you

**Was:** `~/Downloads/MathInbox` did not exist. The daemon had been running
5 days 21 hours (pid 6282, since 19 Aug 14:13) with its log ending at the
startup line, filing nothing, while the sidebar said *"Automatic filing: ON"*.

**Root cause, two layers.** `watcher_status()` answered "is a process alive?"
and the badge presented it as "are my PDFs being filed?". Underneath, the
launchd state line was parsed as `"running" in line`, which is also true of
`state = not running`.

**Now:**

* The inbox is **`~/.mathpdf/inbox`**, not `~/Downloads`. The owner deleted the
  Downloads folder because it cluttered Downloads, which is a reasonable thing
  to do to a folder nobody told you was load-bearing. The inbox is plumbing and
  now lives with the logs and reports. A config still naming the old default is
  migrated automatically — unless it still holds files, which is refused rather
  than stranding them.
* The cockpit has an **"Add PDFs" uploader** (Papers to download → Add PDFs).
  That is the supported way in; the folder is no longer something to visit.
  Uploads never overwrite, reject non-PDFs, strip path components from the
  supplied name, and write-then-rename so the watcher never sees a partial file.
* `watcher_status()` returns `filing` (process AND folder) and `problem`. The
  badge has a third state that says BROKEN and names the missing folder.
* `start_watcher()` recreates the inbox before bootstrapping, so the recovery
  the badge recommends actually works.
* **The daemon self-heals.** It re-checks its watch every 30 s by device+inode,
  not by path — recreating a folder gives a new inode and the kernel watch stays
  bound to the old one, so a path check would have missed exactly this outage.
  On a change it remakes the folder, reschedules the watch and re-scans for
  anything dropped while it was deaf.

**Still yours to do:** the running daemon (pid 6282) predates all of this.
Toggle *Automatic filing* off then on in the sidebar to pick up the new code
and the new inbox path.

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

**Update 2026-10-09 (cockpit audit, finding 16).** Maintenance now has a
*Monday sweep* section (on/off, last run, its problems, the last report) and
the sidebar a one-line status. Turning it on installs ONLY the weekly agent,
pinned to the cockpit's interpreter, **without** `--auto-apply-safe` unless he
ticks "also file the safe ones". The filer's switch no longer installs it as a
side effect. Before it was offered: its auto-apply called `upgrade_paper`
without `download_dir` (TypeError per paper, never reported) and without an
undo log — now through `upgrade_entries`, one transaction per run; its
publication check now runs under the library lock in a transaction; a run
that falls short says INCOMPLETE and why. Still not switched on — his call.
Newest report on this Mac: 2026-04-03.

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

### 4. Undoing an upgrade leaves the published PDF on the shelf

When you undo an upgrade (Upgrade Queue → "Download + Upgrade", or
"Upgrade these papers"), the preprint comes back from the trash with its
record, but the published PDF the upgrade filed **stays** in
`01 - Published papers`. Activity says so — "Undone in part … REFUSED: the
original is gone, so this copy is the only version left" — and pressing
Undo again can never finish it.

Why: the published PDF is filed by *copying* the download, and the download
is deleted straight after. Undo refuses to take away a copy whose original
is gone, because that copy is then the only version — the rule that came in
after the Abraham–Delmas–Weibel paper was lost.

Measured 2026-10-15, read-only:

| | upgrades affected |
|---|--:|
| the history on Activity (153 entries) | **0** — its one upgrade entry (19 Aug) recorded no changes |
| the hidden repo log (6 entries, not on Activity) | **1** — the June pilot `0c2b96e0e3af`: Cao, Keller-Ressel, Schmidt; 3 published PDFs on the shelf, downloads gone |
| from now on | every upgrade you undo |

The choice:

* **A. Keep the rule (today's behaviour).** An undone upgrade leaves both
  versions; you retire the published one yourself, and the entry stays
  PARTLY UNDONE.
* **B. Undo moves such a copy into the trash** (`.trash/undone_copies/`,
  with its record) instead of refusing. Nothing is deleted; an undone
  upgrade gives back exactly the shelves you had and is marked undone. The
  cost: the trash then holds the only copy of that published PDF (to have it
  back: take it out of the trash, or download it again). Suggested scope:
  only copies made from a download the app itself deleted, marked when the
  upgrade is made; a copy whose original vanished for any other reason is
  still refused, since nobody knows why it vanished.

Nothing has been changed; this waits for your answer.

---

## Standing rulings, 2026-10-09

The owner's answers to four open questions. Each is enforced in code, so
treat them as rules, not suggestions.

- **Year ranges take an en dash, in every filename; anything else is an
  error.** `filename_normalizer._en_dash_year_ranges`, run by every
  naming path. This covers the Finder colon ("2002/2003" on screen is
  `2002:2003` on disk) and hyphens. 45 files were renamed (tx
  `91180f9880fc`).
- **Ruled surnames are found behind a prefix**: an exposé number
  (`103-le Gall`) or a series volume (`Astérisque 281 - …`). 34 files
  were renamed (tx `7ba3fdb68891`).
- **Archival collections: records yes, proposals never.** They may keep
  saved records (all 1,908 have one), but no tool may propose to move,
  rename, retire or re-file anything in them.
  `library_scope.why_not_proposable` is the one check, used by the topic
  pipeline, its text step, Spelling, Conflicts, variants, Home topic
  suggestions and both publication-state lists.
- **Two records for one paper are merged, never chosen between.** Fields
  missing from the kept record are filled from the other; arrival fields
  take the older copy's value; real conflicts keep the app's value and
  are reported. 8 pairs were merged (tx `a7051bcc41e7`), and
  `PaperIdentity.load/save` now use `record_location` so no new pairs
  form.

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

## Sort Queue speed — fixed 2026-10-15

Measured read-only on the real `12 - To be sorted` (2,414 PDFs: 2,065 ask
arXiv, 209 ask Crossref, 68 always reach the local AI model and up to 216
when arXiv is down), on a 42-paper sample across all of them:

| per paper | before | after, first time | after, seen before |
|---|--:|--:|--:|
| show, median | 0.63 s | 0.49 s | 0.13 s |
| Approve, median / worst | 0.14 / 43 s | 0.05 / 0.30 s | 0.05 / 0.31 s |
| arXiv unreachable: show / Approve, median | 10.3 / 10.1 s | 0.15 / 0.06 s | — |
| the local model reads it: show / Approve | 28–72 / 29–66 s | 26–49 / 0.06–0.20 s | 0.12–1.1 / 0.03–0.06 s |

The recorded "10–11 s per paper" is right only while arXiv is unreachable
(a 10 s connect timeout, paid again on Approve because a failure was never
remembered). With arXiv up it was 0.6 s. The worst case was the local
model: 30–70 s to show a paper and the same again to approve it.

Now: answers are kept in `~/.mathpdf/cache/lookups.json`
(`processing/lookup_cache.py`) — found 30 days, "no such paper" 1 day, a
failure never (instead the service is left alone for 5 minutes, then asked
again). The page asks arXiv about the next 25 papers in one request, gives
up on a dead connection after 5 s, and says where each name came from
("arXiv could not be checked: no connection … this name comes from the
PDF's own metadata"), with an "Ask again now" button.

The batch sort's Apply reuses the same remembered answers; not measured.

### The local model reads ahead — 2026-10-15

**How often he meets it.** 68 of the 2,414 waiting papers always reach the
local AI model (216 while arXiv is unreachable). The first is the 59th in
queue order, 19 are within the first 300, and they come in runs: 29 of
the 67 gaps between them are 1, and 17 sit together among the books.

**What a read costs** (Apple M3, 24 GB, a busy machine): 7.0–68.3 s with
the model already loaded (median 36.8 s, n = 12); loading it 1.2–1.4 s
from a warm disk cache, 9.3 s otherwise; 4.4 GB of memory while loaded.
The read is the cost, so keeping the model loaded saves little; reading
early is what helps.

**Now** (`processing/read_ahead.py`, `processing/local_model.py`): once the
paper on screen is read, the page hands the next 25 to one background
thread, which reads them as the page would; the answers land in the
lookup cache. One model per process, ever: a paper the thread is reading
is not read again by the page, which waits for that answer. The model
stays loaded only while reading ahead; leaving the Sort Queue starts
nothing more and lets it go (the paper in hand is finished first), and a
closed tab lets it go after 2 minutes idle. The page says "Reading ahead:
N of the next 25 papers are ready".

**Measured, read-only, on the real queue**: papers 106–156, the densest
run of model papers outside the books (9 of them; 4 share their first
pages with a fifth, so 5 need a read), owner looking at each paper for
10 s or 5 s:

| time to show | before (master 2a9eb20) | after, 10 s a paper | after, 5 s a paper |
|---|--:|--:|--:|
| the 5 papers the model reads | 14.0, 45.3, 32.3, 39.2, 38.8 s | 0.11–0.22 s | 0.10–0.59 s |
| the other 42, median / worst | 0.13 / 3.0 s | 0.17 / 2.2 s | 0.17 / 1.3 s |
| … while the model reads behind them, median | — | 0.28 s (n = 12) | 0.34 s (n = 18) |

The machine was far busier during the "after" runs (load 43 and 252
against 26). A background read costs the page the same whether it runs
in a thread or a separate process (median 0.156 vs 0.163 s, idle 0.09–0.14
s): CPU, not the interpreter lock, so a process would buy nothing.

Over the whole queue, simulated from the measured read times and the real
order (his pace is not recorded anywhere, so it is varied): at 10 s a
paper, 74% of model papers show at once and the total wait falls from
50.5 to 6.5 minutes; at 20 s, all of them; at 5 s, 38% and 19 minutes —
the 17 books in a row arrive faster than any read-ahead can read them.

Found on the way: five different papers named "The Annals of
probability" by "000-00" -- fixed, next section.

### The local model named papers after a cover sheet — fixed 2026-10-15

**What it was** (measured read-only, real `12 - To be sorted`, 2,414
PDFs; 70 always reach the model today, 216 while arXiv is unreachable).
`Download (1).pdf`, `Download2/4/6/8.pdf` are not five papers behind a
long cover page: each is a scan (2–9 pages, 129–698 KB) whose ONLY text
is JSTOR's 152-character sheet, "Institute of Mathematical Statistics is
collaborating with JSTOR to digitize, preserve, and extend access to The
Annals of Probability."; the pages after it are images. That is the one
model input shared by different files, in either population. A Birkhäuser
book whose only text is the Modern Birkhäuser Classics series
description was named "Modern Birkhäuser classics" by "Birkhäuser". Every
other cover sheet among the model's papers -- ResearchGate 3, HAL,
Taylor & Francis, DML-CZ, a university repository -- names the paper, and
the model read each correctly; so did the books' series and
editorial-board pages (GTM, Ergebnisse, Springer Series in Statistics).

**Now** (`processing/model_input.py`, the only path to the model):
* a page that says only who digitised or publishes the paper -- JSTOR's
  early sheet, the Birkhäuser series description -- is not handed to the
  model; a page that keeps any word once that sentence and its links are
  removed is handed over verbatim. JSTOR's later sheets carry the same
  sentence below the paper's title and authors and are kept;
* an answer is used only if its title has letters and every author does
  ("000-00" is not a name), judged every time it is used, remembered or
  fresh;
* the outcome is three-valued in `lookups["model"]`: found, or unknown
  with the reason. The Sort Queue warns "No title in the PDF or the
  registries, and the local AI model could not name it: page 1 is
  JSTOR's cover sheet, which names only the journal, and the other pages
  have no text to read (a scan without a text layer) …"; the batch sort's
  note says the same.

| real inbox | before | after |
|---|--:|--:|
| handed to the model (arXiv up / down) | 70 / 216 | 63 / 209 |
| … from the same text as before, byte for byte | — | 63 / 209 |
| named after a journal, series or publisher | 6 | 0 |
| one model title on several different papers | 5 papers | 0 |
| told "could not name it", with the reason | 0 | 12 |

The 12: the 5 JSTOR scans, the Birkhäuser book, a 40-character page the
model never read anyway, and 5 scans with no text at all (2
`PPN243919689_*.pdf`; Feller, Lindvall and Seneta, already named in house
form -- the note says "check it before approving, or type the real one").
The real model's answer is on record for all 63 still handed over with
arXiv up and 125 of the 209 with it down; the answer rule refuses none of
them. Over all 128 real answers
recorded (the model, read-only, on the inbox's distinct texts) it refuses
two: the "000-00" and an empty title, both from texts no longer handed
over.

**The library at large** (29,795 PDFs, first pages): 427 carry JSTOR's
sentence. The rule leaves out 96 -- 0 words left, the owner's title (from
the filename) on none of them, and no other text in their first three
pages: all scans. It keeps 331, each with 10 or more words left; 330
carry the owner's title, the 331st is an inbox file whose name is not a
title. All four Modern Birkhäuser Classics books in `05 - Books and
lecture notes` (4,341 PDFs, first three pages) are caught -- one only
after words broken over lines ("resear-\nchers", Triebel) were joined for
matching; Hörmander's is then read from its own title page.

**Remembered answers.** The cache key is the exact text. Where the text
changed (the 7), it is now not handed over at all, so the old key is
never looked up; where it did not (the 63/209), the remembered answer
applies -- and is judged, so a "000-00" remembered before the fix is
refused (tested). `~/.mathpdf/cache/lookups.json` does not exist yet on
this Mac, so nothing wrong is remembered today.

**Found, open: the model invents authors when the page has none.** Of the
128 answers, 3 name people absent from their text and wrong: "Khintchine"
for Iosifescu's *Metrical theory of continued fractions*, Kechris and
Miller for Zapletal's AMS Memoir 793 (memo0793.pdf), four names for a
paper signed "OpenAI"; a fourth adds Fornberg, rightly, to a book whose
first pages never name him; a fifth misspells "Ardjani" as "Arjdani". A
plain "is the surname in the text" check flags 11: those 5, the
"000-00", and 5 right or defensible ones ("BanÄ uelos" and "Opriúan" are
the PDFs' garbling, "Bühler" for "Buehler", "Muguruza Gonzalez" twice).
Not fixed; raw list in agent-results `authors_not_in_text.txt`.

---

## Known and open, ranked

1. **Every library-changing cockpit button is now pressed by a test
   (2026-10-15); what that turned up is still open.** Measured: 37 buttons
   move, rename, retire or rewrite something — found by AST
   (`tests/ui/library_write_sites.py`), not by eye. The suite used to execute
   the writing line of 5 of them; now 37/37, each pressed on a synthetic
   library with the disk checked and ↶ Undo pressed on Activity
   (`tests/ui/test_*buttons*.py`, `test_undo_button.py`). `cockpit.py` lines
   covered 55.4% → 72.1%. `tests/safety/test_every_library_writing_button_is_pressed.py`
   (pre-commit) fails on any new writing button that no test presses.
   (The old figures here had gone stale: `_undo_transaction` was already
   19/19 and the 323cdc1 regression already failed 2 tests, through a stubbed
   undo log; it now also fails against the real one.) Fixed on the way, in
   `undo_log`: an undo that left something behind was marked fully done when
   the leftover was a REFUSED copy (every upgrade), and the preview of undoing
   a copy could not show that refusal. *Fixed 2026-10-15:* a partly undone
   entry, pressed again, retried EVERY change, so one already back said
   "file gone" and the entry could never finish — and a reversal done twice
   could move back a paper filed again since, or overwrite a record field
   corrected since. Undo now remembers which changes came back
   (`reversed_ops`), retries only the rest and finishes; Activity actually
   shows PARTLY UNDONE (the listing had dropped it, so the row never did).
   Undoing a topic filing (Pipeline Preview "Apply now") now also retires,
   to `.trash/undone_records/`, the record the filing made for a paper that
   had none — while it holds nothing added since; otherwise it is kept and
   the undo says so. **Still open:** undoing an upgrade cannot take the
   published PDF off the shelf — your decision, "Needs your decision" §4;
   13 of the 153 entries on Activity are test runs from 10–22 Aug whose
   every path is outside the library.

   *The six buttons outside the undo log — FIXED 2026-10-15.* Mark done
   (To Download, its "Download now", Home), Home "Look again", Upgrade
   "Flag for manual", "Fill in missing details" and "Cache abstracts now"
   now each make one Activity entry, and each is pressed in a test, then
   ↶ Undo, then the library compared. A record either backfill makes for
   a paper that had none is retired by undo exactly as a topic filing's
   is (above). A download note is not a record, so the log has one more
   kind of change, `file_created`: undo retires the note to
   `.trash/undone_creations/` — never deletes it — and only while it is
   byte for byte what was written. Both backfills are logged rather than
   labelled irreversible, on measurement (read-only, real library, 29,795
   PDFs): "Fill in missing details" would make ≤467 records; "Cache
   abstracts" would touch 758 papers, 466 with no record and 292 whose
   text (3.7 KB on average) goes in the log — about 1 MB, against 4.2 MB
   for the largest transaction already there. Found and fixed on the way:
   "Flag for manual" wrote over another paper's note of the same title
   (`write_text`); "Cache abstracts" and "Look again" rewrote whole
   records (now only their own fields, so undo gives the record back
   exactly), and "Cache abstracts" saved a blank record over an
   unreadable one; a batch upgrade's "flagged for manual download" notes
   were outside its transaction; the command-line reset was unlogged.
   `tests/safety/test_every_library_writing_button_can_be_undone.py`
   (pre-commit) now fails on any writing button whose test does not press
   ↶ Undo — one exemption, the weekly run, with the tests that prove its
   writes reversible named.
   *"Cache abstracts" batch and the records it made — FIXED 2026-10-15.*
   Its batch counted the papers it looked at, done or not: "100" read 3
   papers, "500" 4, "2000" 6 — only "All" reached the 758 still waiting
   (of 26,098 routable papers in scope). The batch is now papers still to
   read; the walk then goes on, without reading, to count what is left,
   and the page says it in words ("Read 100 papers: … 658 papers still to
   read") where it printed the stats dict. A record that cannot be read
   is no longer read and counted failed — it is passed over, so a run of
   them cannot fill every batch — and one that is not UTF-8 no longer
   raises out of `PaperIdentity.load` (it ended the whole run).
   And 147 records had neither a content fingerprint nor a filing date
   (0 lacked just one; 117 hold cached text, 30 the "tried" mark, 127
   are in `12 - To be sorted`; none has a topic code, so not topic
   filing): "Cache abstracts", since it came in on 18 June, gave a paper
   with no record one holding the text alone, and "Fill in missing
   details" then passed it over for good, since it had a record.
   Without a fingerprint the reconnect cannot find a record again after
   a Finder rename. Decided, on that evidence: (a), not (b). "Cache
   abstracts" now gives a record-less paper the whole record "Fill in
   missing details" makes — one function, `identity.backfill_sidecar`,
   plus the text — and leaves alone one whose contents match a record a
   rename left behind (`sidecar_repair.stranded_match`, shared with
   "Fill in missing details"; 0 of the 466 today). Telling him to press
   a second button on another page first would have left 466 of the
   758 (61%) unread by this one. "Fill in missing details" now fills in
   the fingerprint and filing date a record lacks
   (`identity.complete_record`: those two fields only, `patch_record`
   through the undo log, so ↶ Undo gives each record back byte for
   byte). Measured with the new code on the real library, read-only
   (every writer replaced by a counter, writes to the library denied by
   the sandbox; load average 131–139): a batch of 100 reads 100 papers,
   makes 58 records and adds text to 42, 119.5 s; counting alone 81.0 s;
   "Fill in missing details" would make 467 records and complete all 147,
   0 errors, 104.6 s. Reading one paper: median 0.106 s, max 0.381 s
   (60 random waiting papers).
   **Found, still open:** 20 of the 36 stranded records belong to
   papers that have one of those 147 records; the reconnect cannot put
   them back, since the paper has a record. Each holds only a
   fingerprint, filing date and older name, and its filing date equals
   the one completion writes (20 of 20), so completing loses nothing —
   but the pair is two records for one paper, which the ruling says to
   merge, and no page does yet. Topic filing (`file_into_topic`,
   Pipeline Preview "Apply now") still makes a blank record for a paper
   with none, without the stranded-record check. "Check they still
   match" counts a record with no fingerprint as matching
   (`drift_check` returns `None`).
2. **Slow screens**: Home/Attention 12–76 s. (Sort Queue: fixed 2026-10-15,
   see "Sort Queue speed" above.)
   *Conformance — FIXED 2026-10-15.* It took ~3.5 min against a label
   saying "about a minute". Measured read-only on the real library, old and
   new code back to back on the same busy Mac: **341.6 s → 131.9 s**,
   identical report. The count of non-PDF documents stat()ed all ~220,000
   entries, Scripts/ and the record mirror included, to count 220 (78–143 s
   → under 3 s); the caser re-derived its 463 whitelist phrases per title
   (per-file loop 158 s → 78 s, 0 of 25,251 verdicts different); the
   sidecar check stat()ed each record three times. The page now states the
   measured time and shows one bar per stage with an ETA -- the old bar sat
   at 100% for the last three minutes.
3. **`filename_ground_truth` has no production caller.** 27 sites still split
   on `" - "` naively. The rename path produces 0 wrong proposals today, so
   this is latent, not active — but it is the module the docs call the owner
   of that split.
4. ~~`docs/FILENAME_CONVENTION.md` is actively wrong~~ — **rewritten
   2026-10-15 from the code**: every rule names its module and carries the
   library's measured agreement (the automatic pipeline leaves 25,249 of
   25,251 in-scope names unchanged). Rewriting it surfaced three places
   where the code disagrees with a settled ruling, listed in its §6, plus
   one gap by design:
   - ~~arrival collapses multi-letter initials~~ — **fixed 2026-10-15**:
     `Yu. M.` and `Ch.` arrive whole, and `Yu.A.` no longer loses its `A.`.
     All 174 library blocks that carry one rebuild exactly (before: 1);
   - ~~arrival keeps a title contraction as U+0027 and turns a prime into
     `’`~~ — **fixed 2026-10-15**: an apostrophe arrives as U+2019, a
     prime or quotation mark stays as it is. 1,513 of the 1,699 apostrophe
     titles now arrive exactly as shelved (before: 0); none of the rest
     differs at an apostrophe (169 of them only at quotation marks). Neither fix
     changes any proposal for a name already on a shelf (0 of 25,251);
   - ~~a single-quoted `'passage'` arrives straight~~ — **fixed
     2026-10-15**: a certain single quotation takes the language's outer
     marks (`‘…’`, `« … »`), including the `‘…'` publishers send; an
     uncertain one -- after a word in -s, a closing quote and a possessive
     are the same mark -- is left as it arrived, with the reason. 172 of
     the 175 single-quoted library titles arrive exactly as shelved
     (before: 0), and 1,685 of the 1,699 apostrophe titles (before: 1,513).
     0 of 25,251 proposals change. Left by rule: one nested quotation;
   - the Spelling page's *Name or ordinary word?* answers
     (`config/casing_decisions.json`) are read only by
     `core/sentence_case`, which no live path calls -- they change no
     filename, though the page says held words are "not being capitalised
     until you decide";
   - (by design) a name typed in the Sort Queue box is filed verbatim,
     with no rule applied and nothing checking it afterwards but Conformance.
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
