# Cockpit: where the screen and the filesystem disagree

Recorded 2026-08-24, from a six-probe audit with adversarial
re-measurement. Every number below was measured against the real
library; where a probe and its verifier disagreed, the verifier's figure
is used.

These are **open**. They are grouped by what a wrong screen costs you,
not by which file they live in. Each entry says what you see, what
actually happens, where it lives, and what the fix is.

Two related items were fixed on 2026-08-24 and are recorded at the
bottom so the list stays honest about what changed.

---

## 1. The name you approve is not the name you get

**Severity: high — this is the screen you use most.**

The Sort Queue shows the filename produced by
`cmo.get_canonical_filename()` (`src/ui/paper_preview.py:64`).
`ingest_paper` then re-cases the title through the sentence-case pass at
`src/processing/ingest.py:816`.

**The two differ for 943 of 2,073 inbox papers — 45.5%.**

Worse, a name you type yourself is re-cased too, despite the comment at
`ingest.py:785` reading "User override — preserve verbatim":

```
you type   Doe, J. - The Riemann Hypothesis and Brownian Motion.pdf
you get    Doe, J. - The Riemann hypothesis and Brownian motion.pdf
```

**Fix.** Show the post-casing name in the preview — call the same
function the filing path calls, rather than an earlier one. And make
`canonical_override` genuinely verbatim: if you typed it, it is the
identification, and nothing downstream should second-guess it. (The
ingest gate already treats an override that way; the caser does not.)

---

## 2. "I understand this will MOVE 10 file(s)" can move 1,415

**Severity: high — irreversible-feeling bulk action under a wrong label.**

The topic Apply confirmation renders a count taken from a *scoped*
preview, then calls `apply_topic_proposals` with neither `scope` nor
`limit` (`src/ui/cockpit.py:2856` and `:2867`).

The saved scan snapshot also drops `enrich`, `scope` and `sample`, and
the enrich checkbox is recreated with `value=True`. So after a browser
reload, a preview run with abstracts **off** (10 moves) becomes an Apply
with abstracts **on** (1,415 moves), under a label that still says 10.

**Fix.** Thread `scope` and `limit` into both apply calls. Persist
`enrich`/`scope`/`sample` in the snapshot, or disable Apply on a restored
scan until it is re-previewed. `pipeline_preview.preview_topic_filing`
already accepts all three.

---

## 3. The confidence percentage is not a probability

**Severity: medium — it is the number you use to decide whether to trust a row.**

`_confidence` is bimodal by construction: a primary keyword scores 3.0
against a full-strength score of 4.0, so one uncontested hit is exactly
0.75 and two are 1.00, with essentially nothing between. The cockpit
renders those as "100%" and "75%" (`src/ui/cockpit.py:2782`).

Measured against outcomes:

| shown | actually correct |
|---|---|
| 100% | **77.4%** |
| 75%  | **34.3%** |

**Fix.** Either calibrate (bucket the score against measured outcomes and
show the empirical rate) or stop printing a percentage and show the
evidence instead — "2 keywords matched: `\bmean.field BSDE\b`,
`\bg.expectation\b`". The second is cheaper and more useful, since the
evidence is what you would check anyway.

---

## 4. The batch-sort preview shows where the paper came from, labelled "where it goes"

**Severity: medium — trivially fixed, actively misleading.**

The preview is captioned "where it goes" and renders `r.get('subfolder')`,
which `src/processing/bulk_sort.py:156` sets to the paper's **source**
inbox folder. The real destination is computed and sits unused in the
same dict at `:176`.

**Fix.** Render the destination.

---

## 5. Approving a paper silently disables its topic routing

**Severity: medium.**

Three different text windows feed the classifier:

| path | what it sees |
|---|---|
| Sort Queue preview | 800 chars of page 1 (`paper_preview.py:31`), then sliced `[:4000]` at `cockpit.py:911` — a 4,000-char slice of an 800-char string |
| ingest | keywords + abstract + 4,000 chars of pages 1–3 (`ingest.py:939`) |

Measured over a 297-paper systematic sample they disagree for **20
(6.7%)**, always the same way. `2512.00934v1.pdf` is 07a at confidence
1.00 on the ingest path and "no topic" in the dropdown.

Because `_approve_sort` passes the dropdown value with `auto_topic=False`,
pressing **Approve** turns off a routing decision the batch button on the
same page would have applied.

**Fix.** Give the preview the same window the filing path uses — or
better, have the preview *call* the filing path's classifier rather than
approximating it.

---

## 6. A topic Apply is all-or-nothing, though the code supports exclusions

**Severity: medium.**

`pipeline_preview.apply_topic_proposals` accepts an `exclude` set
(`:390`, `:414–421`). The cockpit never passes it, so 1,415 proposed
moves are one button. The Duplicates tab already implements exactly the
per-row checkbox pattern needed (`cockpit.py:5143–5150`).

**Fix.** Reuse that pattern and pass `exclude`.

---

## 7. Sub-subtopic routing happens at Apply although it is documented as unsupported

**Severity: medium — it is how papers end up buried.**

`publication_topic_router.py:16–21` says sub-subtopic routing "is NOT yet
supported… we deliberately stop at the top-level topic rather than
guess", and `subtopic_supported` is hard-coded `False`. But
`pipeline_preview.py:468` routes every applied move through
`_finer_routing`, where a single-keyword hit scores 0.65 against a 0.6
floor:

```
Curve following in illiquid markets                      -> Numerical methods
Model ambiguity in risk sharing with monotone mean-variance -> ESG
```

**327 of 1,427 proposed moves (23%)** are buried one level deeper this
way, at 52–69% precision.

**Fix.** Honour the flag: stop at the top-level topic on the apply path
too, until sub-buckets are actually supported.

---

## 8. There is no way to refile a paper from the cockpit

**Severity: medium — it makes every other topic decision one-way.**

`file_into_topic` has **zero UI call sites**. Moving an already-filed
paper means Finder, which the system cannot see, so the sidecar and the
filesystem drift apart.

Relatedly, a rejection is forgotten: `reject_topic_suggestion` clears the
field and writes no durable "not this topic", so the same suggestion
returns on the next scan.

**Fix.** A refile control, and topic rulings keyed on `content_sha256`
(present on 29,362 sidecars) in the same shape as
`.mathpdf-config/spelling_rulings.json`.

---

## 9. The watcher can be alive, green, and permanently deaf

**Severity: high for data flow — you would not know it had stopped.**

`scan_existing_inbox()` runs **once**, before the loop
(`src/watcher/daemon.py:403–410`); the loop only drains `self._pending`,
which nothing but filesystem events refills. Delete and recreate the
watched directory and `is_alive()` stays `True` while zero further events
arrive — reproduced independently by two agents.

The only liveness signal is `state = running` from launchctl, rendered as
a green "Automatic filing: ON". `maintenance/health.py:52–115` has no
watcher field. The live daemon has been up for days and its log's last
line is the startup message — the same evidence a wedged daemon would
produce.

**Fix.** A periodic `iterdir` of the watched directory (microseconds,
self-healing) plus a heartbeat file the cockpit reads, so "running" means
"has looked recently" rather than "the process exists".

---

## 10. Six PDFs sit in a folder no page can reach

**Severity: low, but it is silent.**

`04 - Papers to be downloaded` holds **221 PDFs and 7 `.txt` flags**. The
page named after that folder (`cockpit.py:3685`) rglobs `*.txt` and shows
the 7. Seven PDFs at its top level are reachable by no arrival path in
the app.

The downloader also has **zero arXiv support** — `grep -rn arxiv
src/downloader/` returns nothing across 26 publisher modules — while
**110 of the 222 sidecars there carry an arXiv id** against 20 with a
DOI, and the page offers a DOI box only. An arXiv PDF is one
unauthenticated GET.

---

## 11. A total outage of the title stage makes the Conformance report look better

**Severity: high — it inverts the meaning of the page.**

`src/processing/move_normalizer.py:178` swallows every exception. Make
`propose_title_case` raise and
`Smith, J. - the theory of Optimal stopping.pdf` flips from
`owner_queue/case` to `canonical`; violations go 3 → 0 and mechanical
6 → 0. The report improves because the checker stopped working.

**Fix.** Let the exception reach `examine()`, which already has a
`VIOLATION, "pipeline-raised"` branch for exactly this.

---

## 12. Seven files are named with invisible control characters

Found 2026-08-24 while measuring extraction; the code hole is fixed in
`3e26d41`, the seven existing files are NOT touched because renaming
live library data is the owner's call.

`_clean_for_fs` stripped only U+0000-U+001F, so U+007F DELETE and the
C1 block U+0080-U+009F went into filenames unnoticed. And it was never
applied to the author block at all.

```
03 - Working papers/B/2023/
    Bodnariu, A., Lindensj<U+007F>o, K. - A controller-stopper-game with hidden controller type.pdf
01 - Published papers/B/
    Benezet<U+0084>, C., Gobet, E., Targino, R. - Transform MCMC schemes for sampling intractable factor copula models.pdf
01 - Published papers/B/
    Buckdahn, R., Li, J. - Stochastic differential games and viscosity solutions of Hamilton-Jacobi-<U+0080><U+0093>Bellman-Isaacs equations.pdf
07b - Contract theory/02 - Unpublished papers/
    Mason, R., V<U+001D>alimaki, J. - Dynamic moral hazard and stopping.pdf
07b - Contract theory/01 - Published papers/C/
    Cvitanic<U+0087>, J., Radas, S., Sikic, H. - Co-development ventures, optimal time of entry and profit-sharing.pdf
06 - Theses/Z/
    Zheng, C. - Methode de "Malliavin-Stein" multi-dimensionelle sur l'espace de Poisson<U+0010><U+0011> - applications aux theoremes centraux limites.pdf
06 - Theses/C/
    Corlay, S. - Quelques aspets<U+001C> de la quantiation optimale et appliations<U+001C> a la finance.pdf
```

They sort wrongly, they do not match a search for the visible text, and
Finder shows nothing unusual.

Two of them need more than a strip. The Buckdahn file's
`<U+0080><U+0093>` sits where an en dash belongs — it is a UTF-8 en dash
that lost its lead byte, so the repair is "restore the dash", not
"delete two characters". And the Corlay file has real typos underneath:
"aspets", "quantiation", "appliations" are missing letters, which the
spelling check should be catching independently of the control
characters.

**What the cockpit needs:** a Maintenance row that lists files whose
names contain any category-Cc codepoint, shows the before/after, and
routes the fix through the normal reversible rename. Not an auto-apply —
two of these seven need a human to decide what the character was.

## Fixed on 2026-08-24

- **Undo reported success without checking.** The preview printed "WOULD
  MOVE BACK" for every operation without touching the filesystem, and the
  confirmation counted SKIP and CANNOT UNDO rows as successes — a wholly
  refused undo displayed "Undid 8514 ops". Both surfaces now report what
  actually happened. (`323cdc1`)
- **The cockpit renamed without the library lock.** `LibraryLock` had one
  production user, the watcher, while the cockpit produced the 8,514- and
  3,842-operation batches. The lock is now taken inside `apply_renames`,
  so all four cockpit paths inherit it, with a bounded 30-second wait.
- **The nav-coverage guard had stopped guarding.** It checked a hardcoded
  list of eleven labels and was missing `Conformance`, `Attention` and
  `Spelling`. It now derives the list from the sidebar's own `_GROUPS`.
- **Conformance hid 1,613 of its own findings** — 5.9% of the library,
  counted as settled. (`c56a492`)

---

## Appendix: what the arXiv validation measured (2026-08-24)

The audit called this the single most valuable unrun measurement in the
project. It is now run, and the batching added the same day makes it a
7-minute job rather than a 3-hour one.

**Method.** 600 of the 1,767 arXiv-named inbox papers, sampled with a
fixed seed. Resolve each id against arXiv, then run the naming pipeline
with the arXiv lookup DISABLED and compare — so the number measures
identification from the PDF alone, judged against the registry, and is
not circular.

| | |
|---|---|
| compared | 597 |
| title exact (accent- and case-folded) | **93.8%** |
| title near (Jaccard ≥ 0.8) | 95.1% |
| title badly wrong (Jaccard < 0.5) | 2.0% |
| author set exact | **93.5%** |
| author count right | 94.5% |
| no authors extracted at all | 0.3% |
| **both title and authors exact** | **88.9%** |

**Read this as moderating, not vindicating, the registry inversion.** For
arXiv-named arrivals the PDF's own embedded metadata is right about 94%
of the time — arXiv stamps its own PDFs, so this population is the
best-behaved one in the library. The lookup buys the residual ~6%, which
is roughly **106 of 1,767 papers** named from a wrong /Title. That is
worth having, and the Schnur/Speicher case is one of them, but it is not
the transformation an earlier reading suggested.

The failures are dominated by PDFs produced outside arXiv's pipeline:

```
got : Microsoft Word - for arxiv C-K BullLMS announcement Nonuniqueness…
want: Infinity of solutions to initial-boundary value problems for linear…
```

**Caveat on the first run of this measurement.** It initially reported
3.2% title accuracy. That was a defect in the batch lookup, not in the
pipeline: arXiv does not return entries in the order requested, and the
code paired them by position, so every paper received a neighbour's
record. Fixed by keying on each entry's own `<id>`. Worth recording
because no unit test could have caught it — a fake API answers in order —
and it was visible only because 600 real comparisons came back looking
like a rotated deck.
