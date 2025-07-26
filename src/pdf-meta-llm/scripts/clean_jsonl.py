#!/usr/bin/env python3
"""
Drop lines whose JSON is broken OR whose "prompt" is missing/blank.
Keeps everything else intact.

Usage:
    python scripts/clean_jsonl.py <raw_in> <clean_out>
"""
import sys
import json
import tqdm
from pathlib import Path

src, dst = map(Path, sys.argv[1:3])

with src.open() as inp, dst.open("w") as out:
    for line in tqdm.tqdm(inp, desc="cleaning"):
        try:
            row = json.loads(line)
            if not row.get("prompt") or not row["prompt"].strip():
                continue
        except Exception:
            continue
        out.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"✅  wrote clean dataset → {dst}")