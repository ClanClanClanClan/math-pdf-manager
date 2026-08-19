#!/usr/bin/env python3
"""Coverage may go up. It may not go down.

A fixed ``fail_under`` is either theatre (set below where you already are)
or a roadblock (set above it). A RATCHET is neither: it records where you
are and refuses to go backwards, so every change either holds the line or
improves it, and the number climbs on its own.

Two floors are enforced, because one global number hides the thing that
matters. Overall coverage of ``src`` was 50.97% when this was written,
dragged down by CLI entry points and dead modules — while the code that
can move, rename or delete a paper sat at 75.69%. A single global floor
would let the safety-critical set rot while the average was propped up by
tests for a help message.

    python3 scripts/coverage_ratchet.py --check    # CI / pre-push
    python3 scripts/coverage_ratchet.py --update   # after a genuine rise
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

FLOOR_FILE = Path(__file__).resolve().parent.parent / "coverage-floor.json"

#: The modules that can move, rename, overwrite or delete one of the
#: owner's papers. These are held to their own, higher floor.
CRITICAL = [
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


def _pct(data: dict, files: list | None = None) -> float:
    """Statement+branch coverage over all files, or just ``files``."""
    if files is None:
        t = data["totals"]
        denom = t["num_statements"] + t.get("num_branches", 0)
        covd = (t["covered_lines"] + t.get("covered_branches", 0)) if denom else 0
        return round(100.0 * covd / denom, 2) if denom else 0.0
    num = den = 0
    for name, f in data["files"].items():
        norm = name.replace("\\", "/")
        if not any(norm.endswith(c) for c in files):
            continue
        s = f["summary"]
        den += s["num_statements"] + s.get("num_branches", 0)
        num += s["covered_lines"] + s.get("covered_branches", 0)
    return round(100.0 * num / den, 2) if den else 0.0


def measure() -> dict:
    """Read coverage.json, producing it if absent."""
    j = Path("coverage.json")
    if not j.exists():
        subprocess.run([sys.executable, "-m", "coverage", "json", "-q"],
                       check=True)
    data = json.loads(j.read_text())
    return {"overall": _pct(data), "critical": _pct(data, CRITICAL)}


def load_floor() -> dict:
    if not FLOOR_FILE.exists():
        return {"overall": 0.0, "critical": 0.0}
    return json.loads(FLOOR_FILE.read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--update", action="store_true")
    #: A hair of slack for the rounding jitter you get when a test file is
    #: added; anything larger and a real regression slips through.
    ap.add_argument("--tolerance", type=float, default=0.10)
    args = ap.parse_args()

    now, floor = measure(), load_floor()
    print(f"  overall  {now['overall']:6.2f}%   floor {floor['overall']:6.2f}%")
    print(f"  critical {now['critical']:6.2f}%   floor {floor['critical']:6.2f}%")

    if args.update:
        new = {k: max(now[k], floor.get(k, 0.0)) for k in now}
        FLOOR_FILE.write_text(json.dumps(new, indent=2) + "\n")
        print(f"floor updated -> {new}")
        return 0

    bad = [k for k in now if now[k] < floor.get(k, 0.0) - args.tolerance]
    if bad:
        for k in bad:
            print(f"REGRESSION: {k} coverage fell {floor[k]:.2f}% -> {now[k]:.2f}%")
        print("\nAdd tests for the lines you changed, or justify the drop and\n"
              "lower the floor deliberately in coverage-floor.json.")
        return 1
    print("coverage holds the line")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
