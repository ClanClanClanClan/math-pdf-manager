#!/usr/bin/env python3
"""Coverage may go up. It may not go down. And a new module that can
delete a paper may not arrive untested.

A fixed ``fail_under`` is either theatre (set below where you already are)
or a roadblock (set above it). A RATCHET is neither: it records where you
are and refuses to go backwards, so every change either holds the line or
improves it, and the number climbs on its own.

THREE rules are enforced, because the first two versions of this file
could both be walked straight past.

  1. OVERALL floor.  Statement+branch coverage of ``src``, from
     ``coverage-floor.json``.  No tolerance — see ``TOLERANCE`` below.

  2. CRITICAL floor.  The naming/undo core: modules whose *output* is a
     path, so a wrong answer moves a paper somewhere it will never be
     found again.  Nothing in an AST can detect that property, so this
     set is seeded by hand — but it is a seed, not the whole set, and it
     is only ever added to (see rule 3).

  3. DANGEROUS per-file minimum.  Every module that touches a
     filesystem-destructive API — ``shutil``, ``os.replace``,
     ``os.unlink``, ``Path.unlink``, ``Path.rename``, ``rmtree`` — must
     individually clear ``DANGEROUS_MIN``, unless it is named in
     ``KNOWN_DEBT`` with a reason.  This set is DERIVED from the source
     at check time, so a module written tomorrow is policed tomorrow.

Rule 3 exists because rules 1 and 2 could both be satisfied by a module
that does not exist yet.  Measured on this repo, at 31,449 covered units:
a brand-new file with 61 uncovered statements moved the overall number by
0.0987 points — under the old ``--tolerance 0.10`` — and was invisible to
the critical floor because the critical set was a hardcoded list of
twelve paths it was not on.  Both floors green, exit 0, new untested
``shutil.move`` in the tree.  An aggregate can always be diluted; a
per-file minimum cannot.

The derived scan also found what the hand-written list had missed:
(``src/processing/paper_transition.py`` was the example here: it
imported ``shutil``, could move papers, had no importer anywhere and sat at
0.00% coverage. It had never been on any list.

    python3 scripts/coverage_ratchet.py --check     # CI / pre-push
    python3 scripts/coverage_ratchet.py --update    # after a genuine rise
    python3 scripts/coverage_ratchet.py --explain   # who is in which set
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FLOOR_FILE = REPO / "coverage-floor.json"

#: No slack. The previous default was ``--tolerance 0.10`` percentage
#: points, described in the source as "a hair of slack for rounding
#: jitter". It is not a hair: at this repo's size one percentage point is
#: 314 covered units, so 0.10 buys 31 uncovered statements per run, every
#: run, forever — which is exactly how a 61-statement module walked in
#: (it moved the number by 0.0987). The flag is gone, not merely
#: defaulted to zero, so it cannot be handed back on a command line.
#:
#: Rounding jitter is handled the honest way instead: the floor file
#: stores two decimals, the measurement is compared at the same two
#: decimals, and ``--update`` truncates DOWNWARDS so a stored floor is
#: never above the measurement it came from. The residual slack is the
#: last digit — about three statements — instead of thirty-one.
TOLERANCE = 0.0
PRECISION = 2

#: Seed for the CRITICAL set. These modules do not necessarily call a
#: destructive API themselves — they DECIDE the destination path, and a
#: wrong decision loses the paper just as thoroughly as an ``unlink``.
#: ``watcher/daemon.py`` is the proof that this cannot be derived: the
#: ``path.unlink()`` that made it obviously dangerous was removed, and
#: the module is no less critical for it.
CRITICAL_SEED = [
    "src/processing/undo_log.py",
    "src/processing/identity.py",
    "src/processing/filename_normalizer.py",
    "src/processing/move_normalizer.py",
    "src/processing/title_normalize.py",
    "src/processing/math_typography.py",
    "src/processing/library_normalize.py",
    "src/processing/duplicate_scan.py",
    "src/processing/upgrade_to_published.py",
    "src/processing/publication_topic_router.py",
    "src/maintenance/conformance.py",
    "src/watcher/daemon.py",
]

#: Any module carrying this marker in a comment or docstring joins the
#: dangerous set regardless of what its AST looks like. The escape hatch
#: for "this is dangerous for a reason a linter cannot see".
MARKER = "coverage: critical"

#: Every module that touches one of these must clear DANGEROUS_MIN.
DANGEROUS_MIN = 60.0

#: Modules that were already below DANGEROUS_MIN when rule 3 was written,
#: with the measurement at that moment and why they are tolerated. This
#: list is DEBT, printed on every run so it cannot be forgotten. Adding
#: to it is a deliberate, reviewable act; a new module cannot be added to
#: it by accident, which is the whole point.
KNOWN_DEBT: dict[str, str] = {
    "src/core/io.py":
        "59.14% — atomic-write helper; the untested half is error paths",
    "src/core/security/secure_file_ops.py":
        "45.25% — used only by the downloader, never by the library mover",
    "src/core/utils/cache.py":
        "41.40% — unlinks cache entries under ~/.mathpdf, never a paper",
    "src/downloader/browser_session.py":
        "35.43% — network-bound; deletes only its own temp profile dir",
    "src/downloader/cloudflare_session.py":
        "6.89% — network-bound, effectively untestable offline",
    "src/downloader/doi_downloader.py":
        "27.94% — network-bound; renames only freshly downloaded files",
    "src/downloader/eth_institutional.py":
        "10.84% — Shibboleth session, network-bound",
    "src/downloader/publishers/base.py":
        "34.67% — network-bound publisher adapters",
    # src/processing/paper_transition.py was here at 0.00% — FOUND BY THIS
    # RULE, which is what the derived scan is for. It has been DELETED
    # rather than tested: 170 statements that could move papers, with no
    # importer anywhere in the tree. Untested dangerous code you do not
    # need is not debt to pay down, it is a hazard to remove.
    "src/processing/upgrade_to_published.py":
        "35.55% — moves preprints aside; covered by tests/safety "
        "conservation laws but not by unit tests",
    "src/maintenance/weekly_report.py":
        "52.82% — write_text() of an HTML/JSON report under ~/.mathpdf, "
        "never into the library",
    "src/processing/duplicate_finder.py":
        "49.09% — write_text() to a CLI --output path; superseded for "
        "library work by duplicate_scan.py",
    "src/processing/publication_checker.py":
        "32.76% — write_text() to a CLI --output path and an atomic sidecar "
        "write",
    "src/reporter.py":
        "0.00% — FOUND BY THIS RULE. write_text() of a report to a "
        "caller-supplied path, and not one test imports it",
    "src/ui/cockpit.py":
        "36.83% — 3,204 units of Streamlit rendering; the audit showed all "
        "14 render_* can be stubbed with 136/136 UI tests still green, so "
        "this number is optimistic as well as low",
    "src/processing/filename_normalizer.py":
        "26.71% — CRITICAL_SEED member; held to the critical floor too",
    # src/watcher/daemon.py was here at 59.83%. The watcher-branch tests
    # took it to 84.83%, above the 60% minimum, so the debt is PAID and
    # the entry is gone. Debt that is never removed stops being debt and
    # becomes wallpaper.
}

#: Directories excluded from coverage in pyproject.toml; keep in step.
OMIT_DIRS = ("/grobid/", "/unicode_utils/")

_OS_DESTRUCTIVE = {"replace", "rename", "remove", "unlink", "rmdir",
                   "removedirs", "truncate"}
_METHOD_DESTRUCTIVE = {"unlink", "rmdir", "rmtree", "move", "write_bytes",
                       "write_text"}
_DANGEROUS_IMPORTS = {"shutil", "send2trash"}


# ---------------------------------------------------------------------------
# deriving the dangerous set
# ---------------------------------------------------------------------------

def _reasons(path: Path) -> list[str]:
    """Why this module can destroy or relocate a file on disk. Empty = it
    cannot, as far as the AST can tell."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:                                       # pragma: no cover
        return []
    hits: set[str] = set()
    if MARKER in text:
        hits.add(f"marker `{MARKER}`")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        # A module that will not parse cannot be shown safe. Fail towards
        # inclusion.
        return sorted(hits | {"unparseable"})
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in _DANGEROUS_IMPORTS:
                    hits.add(f"import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in _DANGEROUS_IMPORTS:
                hits.add(f"from {node.module}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            f = node.func
            base = f.value
            basename = (base.id if isinstance(base, ast.Name)
                        else base.attr if isinstance(base, ast.Attribute)
                        else None)
            if basename == "os" and f.attr in _OS_DESTRUCTIVE:
                hits.add(f"os.{f.attr}()")
            elif f.attr in _METHOD_DESTRUCTIVE:
                hits.add(f".{f.attr}()")
            elif f.attr in ("replace", "rename") and len(node.args) == 1 \
                    and not node.keywords:
                # ``str.replace`` takes two arguments; ``Path.replace``
                # and ``Path.rename`` take one. The arity is the only
                # discriminator available without type inference.
                hits.add(f".{f.attr}(one arg) — path move")
    return sorted(hits)


def dangerous_set() -> dict[str, list[str]]:
    """Repo-relative path -> why it is dangerous. Derived, every run."""
    out: dict[str, list[str]] = {}
    for p in sorted((REPO / "src").rglob("*.py")):
        rel = p.relative_to(REPO).as_posix()
        if any(d in "/" + rel for d in OMIT_DIRS):
            continue
        why = _reasons(p)
        if why:
            out[rel] = why
    for seed in CRITICAL_SEED:
        out.setdefault(seed, []).append("CRITICAL_SEED (decides a destination path)")
    return out


def critical_set() -> list[str]:
    """The seed plus anything explicitly marked. Held to the critical floor."""
    marked = [rel for rel, why in dangerous_set().items()
              if any(w.startswith("marker") for w in why)]
    return sorted(set(CRITICAL_SEED) | set(marked))


# ---------------------------------------------------------------------------
# measuring
# ---------------------------------------------------------------------------

def _units(summary: dict) -> tuple[int, int]:
    den = summary["num_statements"] + summary.get("num_branches", 0)
    num = summary["covered_lines"] + summary.get("covered_branches", 0)
    return num, den


def _index(data: dict) -> dict[str, dict]:
    return {name.replace("\\", "/"): f for name, f in data["files"].items()}


def _pct_total(data: dict) -> float:
    t = data["totals"]
    den = t["num_statements"] + t.get("num_branches", 0)
    num = t["covered_lines"] + t.get("covered_branches", 0)
    return 100.0 * num / den if den else 0.0


def _pct_of(data: dict, paths: list[str]) -> float:
    idx, num, den = _index(data), 0, 0
    for want in paths:
        f = idx.get(want)
        if f is None:
            # Not in the report at all. coverage.py lists unexecuted files
            # when ``source = ["src"]``, so absence means the module is
            # gone or excluded — either way it contributes nothing.
            continue
        n, d = _units(f["summary"])
        num += n
        den += d
    return 100.0 * num / den if den else 0.0


def _pct_file(data: dict, path: str) -> float | None:
    """None means 'no coverage data', which is NOT the same as 0% and is
    never allowed to read as a pass."""
    f = _index(data).get(path)
    if f is None:
        return None
    n, d = _units(f["summary"])
    return 100.0 * n / d if d else 100.0


def load_coverage() -> dict:
    """Read coverage.json — REGENERATED, never trusted as found.

    The first version regenerated it only when absent, so a stale file
    from an earlier run certified whatever was last measured: the gate
    would print "coverage holds the line" in 1.7 seconds having executed
    no tests at all. A check that can pass without measuring is not a
    check.
    """
    if not Path(".coverage").exists():
        raise SystemExit(
            "no .coverage data file: run the suite with --cov=src first.\n"
            "  PYTHONPATH=src python3.12 -m pytest --cov=src "
            "--deselect tests/integration/test_network_unified.py")
    j = Path("coverage.json")
    before = j.stat().st_mtime if j.exists() else 0.0
    subprocess.run([sys.executable, "-m", "coverage", "json", "-q"], check=True)
    if j.stat().st_mtime <= before and before:      # pragma: no cover
        raise SystemExit("coverage json did not regenerate; refusing to "
                         "certify a stale measurement")
    return json.loads(j.read_text())


def load_floor() -> dict:
    if not FLOOR_FILE.exists():
        return {"overall": 0.0, "critical": 0.0}
    return json.loads(FLOOR_FILE.read_text())


def _trunc(x: float, places: int = PRECISION) -> float:
    """Round DOWN. A floor rounded up is a floor you fail on the next run
    without changing anything."""
    scale = 10 ** places
    return math.floor(x * scale) / scale


# ---------------------------------------------------------------------------

def check(data: dict, floor: dict) -> int:
    crit = critical_set()
    now = {"overall": _pct_total(data), "critical": _pct_of(data, crit)}
    danger = dangerous_set()

    print(f"  overall  {now['overall']:6.2f}%   floor {floor.get('overall', 0.0):6.2f}%")
    print(f"  critical {now['critical']:6.2f}%   floor {floor.get('critical', 0.0):6.2f}%"
          f"   ({len(crit)} modules)")
    print(f"  dangerous set: {len(danger)} modules, derived from source, "
          f"per-file minimum {DANGEROUS_MIN:.0f}%")

    failures: list[str] = []

    for key in ("overall", "critical"):
        want = floor.get(key, 0.0)
        # Compared at the precision the floor is stored at; see TOLERANCE.
        if round(now[key], PRECISION) < want - TOLERANCE:
            failures.append(
                f"REGRESSION: {key} coverage fell {want:.2f}% -> {now[key]:.2f}%")

    paid, stale = [], []
    for rel in sorted(danger):
        pct = _pct_file(data, rel)
        debt = KNOWN_DEBT.get(rel)
        if pct is None:
            failures.append(
                f"NO DATA: {rel} touches the filesystem ({', '.join(danger[rel])}) "
                "but does not appear in coverage.json at all. A module that was "
                "never even imported cannot be assumed safe.")
            continue
        if debt is not None:
            if pct >= DANGEROUS_MIN:
                paid.append(f"    {rel}  now {pct:.2f}% — remove it from KNOWN_DEBT")
            continue
        if pct < DANGEROUS_MIN:
            failures.append(
                f"UNTESTED DANGEROUS MODULE: {rel} is at {pct:.2f}%, below the "
                f"{DANGEROUS_MIN:.0f}% minimum for code that can move or delete a "
                f"file ({', '.join(danger[rel])}).\n"
                "    Add tests, or add it to KNOWN_DEBT in scripts/"
                "coverage_ratchet.py with a reason someone will read.")

    # A KNOWN_DEBT entry naming a module the derived scan no longer
    # returns means one of two things: the module changed and the entry
    # should go, or THE DETECTOR STOPPED DETECTING. The second is the
    # exact failure this whole file exists to prevent — a check that
    # quietly stopped looking and kept printing green — so it is fatal,
    # not a warning. Verified: stubbing out the AST scan trips this even
    # when every floor is satisfied.
    for rel in sorted(KNOWN_DEBT):
        if rel not in danger:
            stale.append(rel)
            failures.append(
                f"STALE KNOWN_DEBT: {rel} is on the debt list but the derived "
                "scan no longer calls it dangerous. Either delete the entry, or "
                "find out why the scan stopped seeing it.")

    if KNOWN_DEBT:
        print(f"  known debt: {len(KNOWN_DEBT)} modules below "
              f"{DANGEROUS_MIN:.0f}% (listed, not forgotten)")
    if paid:
        print("  DEBT PAID — these have climbed above the minimum:")
        for line in paid:
            print(line)
    if stale:
        print(f"  {len(stale)} stale KNOWN_DEBT entries (see below)")

    if failures:
        print()
        for f in failures:
            print(f)
        print("\nAdd tests for the lines you changed, or justify the drop and\n"
              "lower the floor deliberately in coverage-floor.json.")
        return 1
    print("coverage holds the line")
    return 0


def update(data: dict, floor: dict) -> int:
    now = {"overall": _pct_total(data),
           "critical": _pct_of(data, critical_set())}
    new = {k: max(_trunc(now[k]), floor.get(k, 0.0)) for k in now}
    FLOOR_FILE.write_text(json.dumps(new, indent=2) + "\n")
    print(f"floor updated -> {new}")
    return 0


def explain(data: dict | None) -> int:
    danger = dangerous_set()
    crit = set(critical_set())
    print(f"CRITICAL set ({len(crit)}) — held to the critical floor:")
    for rel in sorted(crit):
        print(f"    {rel}")
    print(f"\nDANGEROUS set ({len(danger)}) — derived; each must clear "
          f"{DANGEROUS_MIN:.0f}%:")
    for rel, why in sorted(danger.items()):
        pct = _pct_file(data, rel) if data else None
        shown = f"{pct:6.2f}%" if pct is not None else "  n/a "
        debt = "  [DEBT]" if rel in KNOWN_DEBT else ""
        print(f"  {shown}  {rel}{debt}\n            {', '.join(why)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--explain", action="store_true",
                    help="print the two sets and each module's coverage")
    ap.add_argument("--coverage-json", default=None,
                    help="read this coverage report instead of regenerating "
                         "one (for testing THIS script; --check always "
                         "regenerates)")
    args = ap.parse_args(argv)

    if args.coverage_json:
        print("!! --coverage-json: reading a SUPPLIED report. This is NOT a "
              "measurement.\n!! CI runs `--check` with no arguments, which "
              "regenerates from .coverage.", file=sys.stderr)
        data = json.loads(Path(args.coverage_json).read_text())
    elif args.explain and not Path(".coverage").exists():
        data = None
    else:
        data = load_coverage()

    if args.explain:
        return explain(data)
    if args.update:
        return update(data, load_floor())
    return check(data, load_floor())


if __name__ == "__main__":
    raise SystemExit(main())
