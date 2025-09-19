import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from maintenance.system import MaintenanceSystem, TaskScheduler, UpdateMonitor


@pytest.mark.asyncio
async def test_run_update_sweep_identifies_candidates(tmp_path):
    metadata = [
        {"arxiv_id": "1234.5678", "added_at": (datetime.utcnow() - timedelta(days=400)).isoformat()},
        {"doi": "10.1/example", "added_at": datetime.utcnow().isoformat()},
    ]
    file1 = tmp_path / "paper1.pdf"
    file1.write_bytes(b"%PDF")
    file2 = tmp_path / "missing.pdf"

    maintenance = MaintenanceSystem()
    report = await maintenance.run_update_sweep(metadata, [file1, file2])

    assert "1234.5678" in report.publication_updates
    assert str(file2) in report.missing_files


@pytest.mark.asyncio
async def test_quality_report_detects_invalid_files(tmp_path):
    valid = tmp_path / "good.pdf"
    valid.write_bytes(b"%PDF")
    invalid = tmp_path / "bad.pdf"
    invalid.write_bytes(b"not pdf")

    dup_map = {"hash": [valid, invalid]}

    maintenance = MaintenanceSystem()
    report = await maintenance.audit_collection_quality([valid, invalid], dup_map)

    assert str(invalid) in report.invalid_files
    assert len(report.duplicate_groups) == 1


@pytest.mark.asyncio
async def test_run_maintenance_executes_both_reports(tmp_path):
    metadata = [{"arxiv_id": "1234", "added_at": (datetime.utcnow() - timedelta(days=400)).isoformat()}]
    file_path = tmp_path / "file.pdf"
    file_path.write_bytes(b"%PDF")

    scheduler = TaskScheduler()
    maintenance = MaintenanceSystem(scheduler=scheduler)
    summary = await maintenance.run_maintenance(metadata, [file_path], {})

    assert summary.update_report.checked_papers == 1
    assert summary.quality_report.total_files == 1
