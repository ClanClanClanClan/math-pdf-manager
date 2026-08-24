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

### `fix_initial_spacing` — two implementations, neither dominant

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
