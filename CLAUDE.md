# Working in this repository

You are almost certainly a fresh session with no context. Read this file and
then `docs/STATE.md`. That is the whole orientation.

Anything in `docs/` dated 2025 describes a system that no longer exists — 16
of the 24 top-level docs are in that category, and 15 more are byte-identical
duplicates of files in `docs/history/`. Do not cite them. `docs/` files dated
2026-08 are current and measured.

## What this is

A library manager for one mathematician's ~29,500-PDF collection at
`$MATH_LIBRARY` (default
`/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths`). This
repository is `Scripts/` inside it.

**The owner does not use a terminal.** A Streamlit cockpit is his entire
interface. A capability reachable only from a CLI does not exist for him — if
you build something and it has no cockpit surface, you have not shipped it.

```bash
PYTHONPATH=src streamlit run src/ui/cockpit.py
```

## Non-negotiables

Each was bought with damage.

1. **The library is real, irreplaceable data.** Never run a probe, script or
   one-off that WRITES under `$MATH_LIBRARY`. A probe once polluted 228
   sidecars and the cleanup was its own project. Tests are walled off;
   ad-hoc `python -m ...` commands are not.

2. **Nothing is hard-deleted.** Every destructive operation goes through
   `processing/undo_log.py` into `<library>/.trash/`. "Delete" means "retire,
   reversibly". The one branch that ever unlinked a library PDF cost a paper
   (see `docs/STATE.md`); there is now a test asserting no bare `unlink()`
   survives in the undo path.

3. **Never go live without asking.** Renames, moves and bulk applies are the
   owner's call. Measure, present, wait.

4. **"I didn't look" and "it's fine" must never be the same return value.**
   Every check is three-valued: OK / problem / UNKNOWN-with-a-reason.

5. **Never state a number you did not measure.** Two commits in the last
   month exist only to correct figures given from hand-picked examples.
   Numbers here have been measured on the wrong population more than once.

6. **Some collections are out of scope.** `processing/library_scope.py` is the
   single answer to "may tooling touch this?" — JEHPS and the academy folders
   `05/00`, `05/01`, `05/02`, `05/11` are excluded on the owner's standing
   instruction. Never write another private skip list.

7. **APFS folds case.** Never test "does the target exist" with a string
   compare or a bare `Path.exists()` on a rename target — use `samefile`.
   This silently refused 771 legitimate renames.

8. **macOS returns filenames NFD-decomposed.** Normalise to NFC before
   matching, or your precomposed accent silently never matches. This has
   caused at least four separate bugs.

## House rules for changes

- **Every fix ships with property and pathology tests.** The library is a
  weak oracle; a test can pass by accident here.
- **Mutate your own fix and report the survivors.** Do not pick only mutants
  you know your code catches. When a mutant survives, find out whether the
  branch is even reachable before writing a test for it — three "defensive"
  branches turned out to be dead and were deleted or annotated.
- **Set `PYTHONDONTWRITEBYTECODE=1` in any mutation harness** and purge
  `__pycache__` between mutants. Rewriting a source file twice inside one
  filesystem mtime tick makes CPython reuse the mutant's bytecode, and the
  run silently becomes a coin flip.
- **One rule, one implementation.** See `docs/rival-implementations.md` and
  `docs/duplicated-rules-review.md`. Where a rule exists twice, differential-
  test both over the real library before deleting either — two of them turned
  out to have complementary gaps, and one "obviously redundant" copy was the
  only one handling a real case.

## The gate

Three tiers, installed by `scripts/install_hooks.sh`:

| tier | what | runs |
|---|---|---|
| pre-commit | safety tests + golden corpus + test-quality check | ~20 s |
| pre-push | full suite, `-m "not network"` | ~4 min |
| CI | full suite + coverage ratchet | — |

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q -m "not network"
```

Use the absolute venv interpreter: `.venv/bin/python`. The hooks call bare
`python3.12`, which resolves correctly only when direnv has loaded `.envrc`.

## Traps already paid for

- `src/validators/` has **two** layers. `validators/filename_checker/` is
  live; the flat layer beside it is frozen at 2025-07 and has drifted. Its
  modules import each other, so "nothing uses it" is false even when nothing
  outside does.
- `src/core/` is 59% unreachable, including four rival config systems that
  live code replaced with the 67-line `core/config_paths.py`.
- Importing anything from `validators` executes `validators/__init__.py`,
  which loads the whole flat layer — 58% of a 37 ms import cost.
