#!/usr/bin/env python3
"""Maintenance and monitoring utilities for the Academic Paper Manager."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UpdateReport:
    checked_papers: int
    publication_updates: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    total_files: int
    invalid_files: List[str]
    duplicate_groups: List[List[str]]


@dataclass
class MaintenanceSummary:
    update_report: UpdateReport
    quality_report: QualityReport


class TaskScheduler:
    """Minimal async scheduler to run maintenance jobs."""

    def __init__(self):
        self._tasks: List[asyncio.Task] = []

    def schedule(self, coro, *, name: Optional[str] = None) -> asyncio.Task:
        task = asyncio.create_task(coro, name=name)
        self._tasks.append(task)
        return task

    async def wait(self):
        if not self._tasks:
            return
        await asyncio.gather(*self._tasks)
        self._tasks.clear()


class UpdateMonitor:
    """Scans local collection for potential updates."""

    def __init__(self, *, max_age_days: int = 365):
        self.max_age = timedelta(days=max_age_days)

    def check_working_papers_for_publication(self, metadata_list: Iterable[dict]) -> List[str]:
        candidates = []
        for item in metadata_list:
            if not item.get('doi') and item.get('arxiv_id'):
                added_at = self._parse_datetime(item.get('added_at'))
                if added_at and datetime.now(timezone.utc).replace(tzinfo=None) - added_at > self.max_age:
                    candidates.append(item['arxiv_id'])
        return candidates

    def detect_missing_files(self, files: Iterable[Path]) -> List[str]:
        missing = [str(path) for path in files if not path.exists()]
        return missing

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


class QualityAuditor:
    """Performs simple quality checks on PDF files."""

    def validate_integrity(self, file_path: Path) -> bool:
        if not file_path.exists():
            return False
        try:
            with open(file_path, 'rb') as handle:
                header = handle.read(4)
            return header == b'%PDF'
        except OSError:
            return False

    def find_invalid_files(self, files: Iterable[Path]) -> List[str]:
        return [str(path) for path in files if not self.validate_integrity(path)]


class MaintenanceSystem:
    """High-level interface for running maintenance sweeps."""

    def __init__(self, scheduler: Optional[TaskScheduler] = None):
        self.scheduler = scheduler or TaskScheduler()
        self.update_monitor = UpdateMonitor()
        self.quality_auditor = QualityAuditor()

    async def run_update_sweep(self, metadata_list: Iterable[dict], files: Iterable[Path]) -> UpdateReport:
        # Materialize iterables upfront to avoid generator exhaustion —
        # previously the generators were consumed by the helper methods and
        # then len(list(...)) was called on the empty iterator.
        metadata_items = list(metadata_list)
        file_items = list(files)
        publication_updates = self.update_monitor.check_working_papers_for_publication(metadata_items)
        missing_files = self.update_monitor.detect_missing_files(file_items)
        return UpdateReport(
            checked_papers=len(metadata_items),
            publication_updates=publication_updates,
            missing_files=missing_files,
        )

    async def audit_collection_quality(self, files: Iterable[Path], duplicate_map: dict[str, List[Path]]) -> QualityReport:
        # Materialize iterable upfront to avoid generator exhaustion.
        file_items = list(files)
        invalid_files = self.quality_auditor.find_invalid_files(file_items)
        duplicate_groups = [[str(path) for path in paths] for paths in duplicate_map.values() if len(paths) > 1]
        return QualityReport(
            total_files=len(file_items),
            invalid_files=invalid_files,
            duplicate_groups=duplicate_groups,
        )

    async def run_maintenance(self, metadata_list: Iterable[dict], files: Iterable[Path],
                              duplicate_map: dict[str, List[Path]]) -> MaintenanceSummary:
        # Materialize once so both sub-tasks see the full data.
        metadata_items = list(metadata_list)
        file_items = list(files)
        update_task = self.scheduler.schedule(
            self.run_update_sweep(metadata_items, file_items),
            name="update_sweep",
        )
        quality_task = self.scheduler.schedule(
            self.audit_collection_quality(file_items, duplicate_map),
            name="quality_audit",
        )
        await self.scheduler.wait()
        update_report = await update_task
        quality_report = await quality_task
        return MaintenanceSummary(update_report=update_report, quality_report=quality_report)


__all__ = [
    "MaintenanceSystem",
    "TaskScheduler",
    "UpdateReport",
    "QualityReport",
]
