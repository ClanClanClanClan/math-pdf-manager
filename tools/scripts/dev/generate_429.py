#!/usr/bin/env python3
"""
Generate API 429s to exercise rate-limit metrics.
Requires API running locally on http://localhost:8000 and
environment variable API_RATE_LIMIT_PER_MINUTE set low (e.g., 5).
"""

import concurrent.futures
import json
import time
from typing import List

import requests


def hit_discovery(i: int) -> int:
    try:
        resp = requests.post(
            "http://localhost:8000/discovery/query",
            json={"query": "graph theory", "max_results": 2},
            timeout=3,
        )
        return resp.status_code
    except Exception:
        return 0


def main() -> None:
    codes: List[int] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futs = [ex.submit(hit_discovery, i) for i in range(200)]
        for f in concurrent.futures.as_completed(futs):
            codes.append(f.result())

    summary = {c: codes.count(c) for c in set(codes)}
    print(json.dumps({"status_codes": summary, "total": len(codes)}, indent=2))
    print("Tip: scrape /metrics and check rate_limit_rejections_total increasing.")


if __name__ == "__main__":
    main()
