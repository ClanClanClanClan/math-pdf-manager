#!/usr/bin/env python3
"""Simple maintenance scheduler that periodically runs maintenance sweeps."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from core.database import AsyncPaperDatabase
from maintenance.system import MaintenanceSystem

DEFAULT_INTERVAL = 60 * 60 * 24  # 24 hours


async def run_once(database: AsyncPaperDatabase, maintenance: MaintenanceSystem) -> None:
    papers = await database.list_papers()
    metadata_list = [
        {
            'doi': record.doi,
            'arxiv_id': record.arxiv_id,
            'added_at': record.created_at,
        }
        for record in papers
    ]
    file_paths = [Path(record.file_path) for record in papers]

    duplicates = await database.find_duplicates(similarity_threshold=0.8)
    duplicate_map = {}
    for paper1, paper2, score in duplicates:
        key = f"{paper1.id}-{paper2.id}"
        duplicate_map[key] = [Path(paper1.file_path), Path(paper2.file_path)]

    summary = await maintenance.run_maintenance(metadata_list, file_paths, duplicate_map)
    print("Maintenance summary:")
    print("  Checked Papers:", summary.update_report.checked_papers)
    print("  Publication Updates:", summary.update_report.publication_updates)
    print("  Missing Files:", summary.update_report.missing_files)
    print("  Invalid Files:", summary.quality_report.invalid_files)
    print("  Duplicate Groups:", summary.quality_report.duplicate_groups)


async def main() -> None:
    interval = int(os.getenv("MAINTENANCE_INTERVAL_SECONDS", DEFAULT_INTERVAL))
    db_path = os.getenv("DATABASE_PATH", "papers.db")
    database = AsyncPaperDatabase(db_path)
    maintenance = MaintenanceSystem()

    while True:
        await run_once(database, maintenance)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
