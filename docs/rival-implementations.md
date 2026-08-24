# One rule, several implementations

Measured 2026-08-24. The question asked was: where the same rule is
implemented more than once, and **one implementation is better in every
respect**, delete the others.

The important word is *every*. Two of these turned out not to meet it, and
saying so is more useful than picking a winner and losing a behaviour.

## Removed

### 13 byte-identical shadowed definitions

Python keeps the **last** definition of a name. A shadowed first copy is
worse than dead code: you can read it, edit it, satisfy yourself the change
is right, run the tests green, and have changed nothing — because the file
defines the name again forty lines later.

| file | names |
|---|---|
| `src/ui/cockpit.py` | `_flash`, `_render_flashes`, `_preview_pdf_cached`, `_find_publication_reports`, `_report_candidates`, `_scan_conflicts_cached`, `_scan_snapshot_path`, `_save_scan`, `_load_scan` |
| `src/ui/cockpit_actions.py` | `load_env_overrides`, `apply_env_overrides`, `_save_env_override` |
| `src/ui/attention_queue.py` | `list_dismissals` |

All 13 verified byte-identical **including decorators**, and each surviving
definition verified byte-identical to the one Python was already using — so
the removal is behaviour-preserving by construction, not by hope.
`tests/audit/test_no_shadowed_definitions.py` now fails if any come back.

### `core.text_processing.split_filename`

Zero callers, and a fourth implementation of "split a filename into author
and title" — the rule that
`processing.filename_ground_truth.decompose` now owns, and that the naive
version gets wrong for 3,889 files.

## Kept, deliberately

### `fix_initial_spacing` — RESOLVED: one implementation, three adapters

`src/core/initials.py` is now the only implementation. The two functions in
`validators` and the wrapper in `processing.filename_ground_truth` are thin
adapters over it. Import cost 4 ms, against 154 ms for the route through the
validator package.

It is the **union**, not a choice between them:

| case | live | frozen | unified |
|---|---|---|---|
| `Kabanov, Yu.A.` → `Yu. A.` | ✓ | ✗ ASCII-only | ✓ |
| `Kyprianou, A.E` → `A. E` | ✗ | ✓ | ✓ |
| `St.Petersburg` unchanged | ✓ | ✓ | ✓ |
| `A.s. approximation…` unchanged | **✗ emits `A. s.`** | ✓ | ✓ |

The last row is a bug the live one had, not a gap: its guard inspected the
matched token and never what followed. Requiring the *following* chunk to be
initial-shaped refuses it, and every lowercase abbreviation with it —
`i.i.d.`, `w.r.t.`, `r.c.l.l.`, 23 titles.

Two hand-written guards went away with it. An initial is now defined by its
shape — one capital, then at most three lowercase — and that single fact
rejects all-caps runs (`USA.`), lowercase words (`et.`) and real words after
a period (`St.Petersburg`, `O.Brien`) without a special case for any of them.

**Measured against the old live rule over the whole library: it changes
exactly 9 more author blocks — the nine the frozen one caught — and ZERO more
titles.** No new damage.

The fixpoint loop both predecessors carried is gone. `re.sub` replaces every
non-overlapping match and inserting a space never creates a new adjacency, so
one pass always suffices: checked over every author block and filename in the
library and over 200,000 synthetic strings, one pass and the fixpoint never
disagree. Keeping it would have been a branch no test could reach.

**The precondition survives and is the real answer.** Apply this to an author
block, never a title. `S.M.F.`, `C.I.M.E.`, `U.S.`, `P.D.E.` are acronyms and
would be spaced; `Varadhan, S.R.S.` and `R.E.A.C. Paley` are people and should
be. No rule reading the string alone separates them. Every production caller
is inside `fix_author_block`, traced over all 29,678 PDFs.

### The two implementations before this (kept for the record)

* `validators/filename_checker/author_processing.py` — live, Unicode-aware,
  knows an initial can be several letters (`Kabanov, Yu.A.` → `Yu. A.`).
* `validators/author_parser.py` — the frozen 2025-07 layer, ASCII-only.

Differential-tested over all **17,804** distinct author blocks in the
library:

```
agree                     17,795
only the LIVE one acts         0
only the FROZEN one acts       9      <-- "Kyprianou, A.E", "Asheim, G.B"
both act, differently          0
```

The frozen one wins those nine because it does not require the *second*
initial to carry its period. So neither is superior in every aspect, and the
brief's condition is not met.

Making the live one dominant is a four-character change to its lookahead,
and it is **not** free: measured over the library it would also rewrite one
title, `Sur la méthode de L. Schwartz pour les E.D.S` → `… E. D. S`, which
is an acronym, not initials. Changing a production naming rule with known
collateral belongs in its own reviewed pass, not in a cleanup.

Nothing in production calls the frozen one — only
`tests/audit/test_title_validation_audit.py`, which asserts it exists.
`processing.filename_ground_truth` already composes the complete behaviour
from the live helper plus its own repair for the missing trailing period,
so the gap is covered where it matters.

### Names that look duplicated and are not

`_get_pdf_url` (23×) and `download` (17×) are one per publisher; `main`
(18×) is one per entry point; `get`/`set`/`load`/`save`/`priority` under
`core/unified_config/` are a protocol implemented by each source. These are
polymorphism, and collapsing them would be the mistake.

## Still open

`normalize_for_comparison` (5), `sanitize_filename` (5), `canonicalize` (6)
and `debug_print` (5) each have several implementations that are **not**
interchangeable — they differ in what they strip and for which caller. Each
needs the same differential treatment `fix_initial_spacing` got before
anything is deleted. Not done here.
