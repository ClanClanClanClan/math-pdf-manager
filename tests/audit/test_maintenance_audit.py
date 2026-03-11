"""Phase 6: Maintenance system audit."""
import asyncio
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from maintenance.system import (
    UpdateMonitor, QualityAuditor, MaintenanceSystem,
    TaskScheduler, UpdateReport, QualityReport, MaintenanceSummary,
)


# ============================================================================
# Section 6A: UpdateMonitor.check_working_papers_for_publication()
# ============================================================================

class TestUpdateMonitorCheckWorkingPapers:
    """Audit: Verify working-paper-to-publication detection."""

    def test_old_arxiv_paper_without_doi_flagged(self):
        """Paper with arxiv_id, no DOI, and older than max_age should be flagged."""
        monitor = UpdateMonitor(max_age_days=365)
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400)).isoformat()

        metadata = [
            {"arxiv_id": "2301.12345", "added_at": old_date},
        ]

        candidates = monitor.check_working_papers_for_publication(metadata)

        assert "2301.12345" in candidates

    def test_recent_arxiv_paper_without_doi_not_flagged(self):
        """Paper with arxiv_id, no DOI, but recent should NOT be flagged."""
        monitor = UpdateMonitor(max_age_days=365)
        recent_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)).isoformat()

        metadata = [
            {"arxiv_id": "2501.99999", "added_at": recent_date},
        ]

        candidates = monitor.check_working_papers_for_publication(metadata)

        assert candidates == []

    def test_paper_with_doi_not_flagged(self):
        """Paper with both arxiv_id and DOI should NOT be flagged (already published)."""
        monitor = UpdateMonitor(max_age_days=365)
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=500)).isoformat()

        metadata = [
            {"arxiv_id": "2301.12345", "doi": "10.1234/test", "added_at": old_date},
        ]

        candidates = monitor.check_working_papers_for_publication(metadata)

        assert candidates == []

    def test_paper_without_arxiv_id_not_flagged(self):
        """Paper without arxiv_id should NOT be flagged."""
        monitor = UpdateMonitor(max_age_days=365)
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=500)).isoformat()

        metadata = [
            {"title": "Local Paper", "added_at": old_date},
        ]

        candidates = monitor.check_working_papers_for_publication(metadata)

        assert candidates == []

    def test_paper_without_added_at_not_flagged(self):
        """Paper without added_at date should NOT be flagged (no date to compare)."""
        monitor = UpdateMonitor(max_age_days=365)

        metadata = [
            {"arxiv_id": "2301.12345"},
        ]

        candidates = monitor.check_working_papers_for_publication(metadata)

        assert candidates == []

    def test_custom_max_age_days(self):
        """Custom max_age_days should be respected."""
        monitor = UpdateMonitor(max_age_days=30)
        date_40_days_ago = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=40)).isoformat()

        metadata = [
            {"arxiv_id": "2501.00001", "added_at": date_40_days_ago},
        ]

        candidates = monitor.check_working_papers_for_publication(metadata)

        assert "2501.00001" in candidates

    def test_multiple_papers_mixed(self):
        """Should correctly filter a mixed set of papers."""
        monitor = UpdateMonitor(max_age_days=365)
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400)).isoformat()
        recent_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)).isoformat()

        metadata = [
            {"arxiv_id": "old_no_doi", "added_at": old_date},
            {"arxiv_id": "old_has_doi", "doi": "10.1234/x", "added_at": old_date},
            {"arxiv_id": "recent_no_doi", "added_at": recent_date},
            {"title": "no_arxiv", "added_at": old_date},
        ]

        candidates = monitor.check_working_papers_for_publication(metadata)

        assert candidates == ["old_no_doi"]

    def test_empty_metadata_list(self):
        """Empty input should return empty candidates."""
        monitor = UpdateMonitor()
        assert monitor.check_working_papers_for_publication([]) == []

    def test_invalid_date_format_skipped(self):
        """Papers with unparseable dates should be silently skipped."""
        monitor = UpdateMonitor(max_age_days=365)

        metadata = [
            {"arxiv_id": "2301.12345", "added_at": "not-a-date"},
        ]

        candidates = monitor.check_working_papers_for_publication(metadata)

        assert candidates == []


# ============================================================================
# Section 6B: UpdateMonitor.detect_missing_files()
# ============================================================================

class TestUpdateMonitorDetectMissingFiles:
    """Audit: Verify detection of missing files."""

    def test_missing_files_detected(self, tmp_path):
        """Non-existent paths should be returned."""
        paths = [
            tmp_path / "gone_1.pdf",
            tmp_path / "gone_2.pdf",
        ]

        monitor = UpdateMonitor()
        missing = monitor.detect_missing_files(paths)

        assert len(missing) == 2
        assert str(paths[0]) in missing
        assert str(paths[1]) in missing

    def test_existing_files_not_flagged(self, tmp_path):
        """Existing files should NOT appear in the missing list."""
        existing = tmp_path / "exists.pdf"
        existing.write_bytes(b"%PDF")

        monitor = UpdateMonitor()
        missing = monitor.detect_missing_files([existing])

        assert missing == []

    def test_mixed_existing_and_missing(self, tmp_path):
        """Should return only the non-existent paths."""
        existing = tmp_path / "here.pdf"
        existing.write_bytes(b"%PDF")
        gone = tmp_path / "gone.pdf"

        monitor = UpdateMonitor()
        missing = monitor.detect_missing_files([existing, gone])

        assert len(missing) == 1
        assert str(gone) in missing

    def test_empty_list(self):
        """Empty input should produce empty output."""
        monitor = UpdateMonitor()
        assert monitor.detect_missing_files([]) == []


# ============================================================================
# Section 6C: QualityAuditor.validate_integrity()
# ============================================================================

class TestQualityAuditorValidateIntegrity:
    """Audit: Verify PDF integrity validation."""

    def test_valid_pdf_header(self, tmp_path):
        """File with %PDF header should pass integrity check."""
        pdf = tmp_path / "valid.pdf"
        pdf.write_bytes(b"%PDF-1.4 content\n%%EOF")

        auditor = QualityAuditor()
        assert auditor.validate_integrity(pdf) is True

    def test_minimal_pdf_header(self, tmp_path):
        """File with exactly %PDF (4 bytes) should pass."""
        pdf = tmp_path / "minimal.pdf"
        pdf.write_bytes(b"%PDF")

        auditor = QualityAuditor()
        assert auditor.validate_integrity(pdf) is True

    def test_invalid_header(self, tmp_path):
        """File without %PDF header should fail integrity check."""
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"This is not a PDF file at all")

        auditor = QualityAuditor()
        assert auditor.validate_integrity(bad) is False

    def test_empty_file(self, tmp_path):
        """Empty file should fail integrity check."""
        empty = tmp_path / "empty.pdf"
        empty.write_bytes(b"")

        auditor = QualityAuditor()
        assert auditor.validate_integrity(empty) is False

    def test_missing_file(self, tmp_path):
        """Non-existent file should fail integrity check."""
        auditor = QualityAuditor()
        assert auditor.validate_integrity(tmp_path / "missing.pdf") is False

    def test_png_file_fails(self, tmp_path):
        """A PNG file should fail the PDF integrity check."""
        png = tmp_path / "image.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n")

        auditor = QualityAuditor()
        assert auditor.validate_integrity(png) is False

    def test_header_almost_pdf(self, tmp_path):
        """File with '%PD' (truncated header) should fail."""
        bad = tmp_path / "truncated.pdf"
        bad.write_bytes(b"%PD")

        auditor = QualityAuditor()
        assert auditor.validate_integrity(bad) is False


# ============================================================================
# Section 6D: QualityAuditor.find_invalid_files()
# ============================================================================

class TestQualityAuditorFindInvalidFiles:
    """Audit: Verify batch file validation."""

    def test_batch_with_valid_and_invalid(self, tmp_path):
        """Should return only invalid files."""
        valid = tmp_path / "good.pdf"
        valid.write_bytes(b"%PDF-1.7 content")

        invalid = tmp_path / "bad.pdf"
        invalid.write_bytes(b"NOT A PDF")

        missing = tmp_path / "ghost.pdf"

        auditor = QualityAuditor()
        invalid_files = auditor.find_invalid_files([valid, invalid, missing])

        assert str(valid) not in invalid_files
        assert str(invalid) in invalid_files
        assert str(missing) in invalid_files

    def test_all_valid(self, tmp_path):
        """All valid files should return empty list."""
        files = []
        for i in range(3):
            f = tmp_path / f"paper_{i}.pdf"
            f.write_bytes(b"%PDF-1.4 content")
            files.append(f)

        auditor = QualityAuditor()
        assert auditor.find_invalid_files(files) == []

    def test_empty_list(self):
        """Empty input should produce empty output."""
        auditor = QualityAuditor()
        assert auditor.find_invalid_files([]) == []


# ============================================================================
# Section 6E: MaintenanceSystem.run_update_sweep()
# ============================================================================

class TestMaintenanceSystemRunUpdateSweep:
    """Audit: Verify update sweep orchestration."""

    @pytest.mark.asyncio
    async def test_run_update_sweep_with_lists(self, tmp_path):
        """run_update_sweep with concrete lists should work (no generator issues)."""
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400)).isoformat()
        metadata_list = [
            {"arxiv_id": "2301.12345", "added_at": old_date},
        ]

        missing_path = tmp_path / "gone.pdf"
        files = [missing_path]

        system = MaintenanceSystem()
        report = await system.run_update_sweep(metadata_list, files)

        assert isinstance(report, UpdateReport)
        assert "2301.12345" in report.publication_updates
        assert str(missing_path) in report.missing_files

    # ------------------------------------------------------------------
    # CRITICAL AUDIT FINDING: Generator exhaustion in run_update_sweep()
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_generator_exhaustion_metadata_fixed(self, tmp_path):
        """FIXED: run_update_sweep() now materializes generators upfront."""
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400)).isoformat()

        def metadata_generator():
            yield {"arxiv_id": "2301.11111", "added_at": old_date}
            yield {"arxiv_id": "2301.22222", "added_at": old_date}
            yield {"arxiv_id": "2301.33333", "added_at": old_date}

        system = MaintenanceSystem()
        report = await system.run_update_sweep(metadata_generator(), [])

        # Generator is now materialized upfront, so count is correct
        assert report.checked_papers == 3
        assert len(report.publication_updates) == 3

    @pytest.mark.asyncio
    async def test_list_input_does_not_suffer_generator_bug(self, tmp_path):
        """With a concrete list, run_update_sweep correctly counts papers."""
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400)).isoformat()
        metadata_list = [
            {"arxiv_id": "2301.11111", "added_at": old_date},
            {"arxiv_id": "2301.22222", "added_at": old_date},
        ]

        system = MaintenanceSystem()
        report = await system.run_update_sweep(metadata_list, [])

        # With a concrete list, re-iteration works
        assert report.checked_papers == 2


# ============================================================================
# Section 6F: MaintenanceSystem.audit_collection_quality()
# ============================================================================

class TestMaintenanceSystemAuditCollectionQuality:
    """Audit: Verify collection quality audit."""

    @pytest.mark.asyncio
    async def test_audit_quality_with_lists(self, tmp_path):
        """audit_collection_quality with concrete lists should work."""
        valid = tmp_path / "good.pdf"
        valid.write_bytes(b"%PDF-1.4 content")

        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"NOT PDF")

        files = [valid, bad]
        dup_map = {"hash1": [valid, bad]}  # pretend they're duplicates

        system = MaintenanceSystem()
        report = await system.audit_collection_quality(files, dup_map)

        assert isinstance(report, QualityReport)
        assert str(bad) in report.invalid_files
        assert str(valid) not in report.invalid_files
        assert len(report.duplicate_groups) == 1

    # ------------------------------------------------------------------
    # CRITICAL AUDIT FINDING: Generator exhaustion in audit_collection_quality()
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_generator_exhaustion_files_fixed(self, tmp_path):
        """FIXED: audit_collection_quality() now materializes generators upfront."""
        valid = tmp_path / "good.pdf"
        valid.write_bytes(b"%PDF-1.4 content")
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"NOT PDF")

        def files_generator():
            yield valid
            yield bad

        system = MaintenanceSystem()
        report = await system.audit_collection_quality(files_generator(), {})

        # Generator is now materialized upfront, so count is correct
        assert report.total_files == 2
        assert len(report.invalid_files) == 1  # bad.pdf

    @pytest.mark.asyncio
    async def test_list_input_does_not_suffer_generator_bug(self, tmp_path):
        """With a concrete list, total_files is counted correctly."""
        valid = tmp_path / "good.pdf"
        valid.write_bytes(b"%PDF-1.4 content")
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"NOT PDF")

        system = MaintenanceSystem()
        report = await system.audit_collection_quality([valid, bad], {})

        assert report.total_files == 2

    @pytest.mark.asyncio
    async def test_no_duplicates(self, tmp_path):
        """Empty duplicate map should produce no duplicate groups."""
        f = tmp_path / "paper.pdf"
        f.write_bytes(b"%PDF")

        system = MaintenanceSystem()
        report = await system.audit_collection_quality([f], {})

        assert report.duplicate_groups == []

    @pytest.mark.asyncio
    async def test_single_file_not_a_duplicate_group(self, tmp_path):
        """A duplicate group with only 1 file should not be reported."""
        f = tmp_path / "only.pdf"
        f.write_bytes(b"%PDF")

        system = MaintenanceSystem()
        dup_map = {"hash_unique": [f]}
        report = await system.audit_collection_quality([f], dup_map)

        assert report.duplicate_groups == [], (
            "Groups with only 1 file should be excluded"
        )


# ============================================================================
# Section 6G: MaintenanceSystem.run_maintenance()
# ============================================================================

class TestMaintenanceSystemRunMaintenance:
    """Audit: Verify full maintenance orchestration."""

    @pytest.mark.asyncio
    async def test_run_maintenance_with_lists(self, tmp_path):
        """run_maintenance with concrete lists should complete successfully."""
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400)).isoformat()
        metadata_list = [
            {"arxiv_id": "2301.12345", "added_at": old_date},
        ]

        valid = tmp_path / "good.pdf"
        valid.write_bytes(b"%PDF-1.4 content")
        missing = tmp_path / "gone.pdf"

        files = [valid, missing]
        dup_map = {}

        system = MaintenanceSystem()
        summary = await system.run_maintenance(metadata_list, files, dup_map)

        assert isinstance(summary, MaintenanceSummary)
        assert isinstance(summary.update_report, UpdateReport)
        assert isinstance(summary.quality_report, QualityReport)

    @pytest.mark.asyncio
    async def test_run_maintenance_generators_fixed(self, tmp_path):
        """FIXED: run_maintenance() now materializes generators before sharing."""
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400)).isoformat()

        def meta_gen():
            yield {"arxiv_id": "2301.12345", "added_at": old_date}

        valid = tmp_path / "good.pdf"
        valid.write_bytes(b"%PDF-1.4 content")

        def files_gen():
            yield valid

        system = MaintenanceSystem()
        summary = await system.run_maintenance(meta_gen(), files_gen(), {})

        assert isinstance(summary, MaintenanceSummary)
        # Both tasks now get the correct data
        assert summary.update_report.checked_papers == 1
        assert summary.quality_report.total_files == 1


# ============================================================================
# Section 6H: TaskScheduler
# ============================================================================

class TestTaskScheduler:
    """Audit: Verify async task scheduling."""

    @pytest.mark.asyncio
    async def test_schedule_and_wait(self):
        """Scheduled coroutine should be executed after wait()."""
        results = []

        async def work():
            results.append("done")

        scheduler = TaskScheduler()
        scheduler.schedule(work(), name="test_work")
        await scheduler.wait()

        assert results == ["done"]

    @pytest.mark.asyncio
    async def test_multiple_tasks(self):
        """Multiple scheduled tasks should all complete."""
        results = []

        async def work(val):
            results.append(val)

        scheduler = TaskScheduler()
        scheduler.schedule(work(1), name="t1")
        scheduler.schedule(work(2), name="t2")
        scheduler.schedule(work(3), name="t3")
        await scheduler.wait()

        assert sorted(results) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_wait_with_no_tasks(self):
        """wait() with no scheduled tasks should be a no-op."""
        scheduler = TaskScheduler()
        await scheduler.wait()  # should not raise

    @pytest.mark.asyncio
    async def test_tasks_cleared_after_wait(self):
        """Task list should be cleared after wait()."""
        async def noop():
            pass

        scheduler = TaskScheduler()
        scheduler.schedule(noop(), name="t")
        await scheduler.wait()

        assert scheduler._tasks == []

    @pytest.mark.asyncio
    async def test_schedule_returns_task(self):
        """schedule() should return an asyncio.Task."""
        async def noop():
            pass

        scheduler = TaskScheduler()
        task = scheduler.schedule(noop(), name="t")

        assert isinstance(task, asyncio.Task)
        await scheduler.wait()

    @pytest.mark.asyncio
    async def test_task_name_preserved(self):
        """Task name should be preserved."""
        async def noop():
            pass

        scheduler = TaskScheduler()
        task = scheduler.schedule(noop(), name="my_task")

        assert task.get_name() == "my_task"
        await scheduler.wait()


# ============================================================================
# Section 6I: Dataclass Structure Verification
# ============================================================================

class TestDataclassStructures:
    """Audit: Verify dataclass fields and defaults."""

    def test_update_report_fields(self):
        """UpdateReport should have expected fields with correct defaults."""
        report = UpdateReport(checked_papers=10)

        assert report.checked_papers == 10
        assert report.publication_updates == []
        assert report.missing_files == []

    def test_update_report_with_data(self):
        """UpdateReport should accept all fields."""
        report = UpdateReport(
            checked_papers=5,
            publication_updates=["2301.12345"],
            missing_files=["/tmp/a.pdf"],
        )

        assert report.checked_papers == 5
        assert report.publication_updates == ["2301.12345"]
        assert report.missing_files == ["/tmp/a.pdf"]

    def test_quality_report_fields(self):
        """QualityReport should require total_files, invalid_files, duplicate_groups."""
        report = QualityReport(
            total_files=100,
            invalid_files=["/tmp/bad.pdf"],
            duplicate_groups=[["/tmp/a.pdf", "/tmp/b.pdf"]],
        )

        assert report.total_files == 100
        assert len(report.invalid_files) == 1
        assert len(report.duplicate_groups) == 1

    def test_quality_report_no_defaults_for_lists(self):
        """QualityReport requires explicit invalid_files and duplicate_groups."""
        # QualityReport does NOT use field(default_factory=list) for
        # invalid_files and duplicate_groups, so they are required.
        with pytest.raises(TypeError):
            QualityReport(total_files=10)

    def test_maintenance_summary_fields(self):
        """MaintenanceSummary should hold an UpdateReport and a QualityReport."""
        update = UpdateReport(checked_papers=5)
        quality = QualityReport(total_files=10, invalid_files=[], duplicate_groups=[])
        summary = MaintenanceSummary(update_report=update, quality_report=quality)

        assert summary.update_report is update
        assert summary.quality_report is quality

    def test_update_report_default_factory_independence(self):
        """Default list fields should be independent between instances."""
        r1 = UpdateReport(checked_papers=1)
        r2 = UpdateReport(checked_papers=2)

        r1.publication_updates.append("x")

        assert r2.publication_updates == [], (
            "Default factory lists should be independent"
        )


# ============================================================================
# Section 6J: UpdateMonitor._parse_datetime()
# ============================================================================

class TestParseDatetime:
    """Audit: Verify datetime parsing edge cases."""

    def test_parse_valid_iso_format(self):
        """Standard ISO datetime should parse correctly."""
        monitor = UpdateMonitor()
        result = monitor._parse_datetime("2024-01-15T10:30:00")

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_only(self):
        """Date-only string (no time component) should parse."""
        monitor = UpdateMonitor()
        result = monitor._parse_datetime("2024-06-01")

        assert result is not None
        assert result.year == 2024

    def test_parse_none_returns_none(self):
        """None input should return None."""
        monitor = UpdateMonitor()
        assert monitor._parse_datetime(None) is None

    def test_parse_empty_string_returns_none(self):
        """Empty string should return None."""
        monitor = UpdateMonitor()
        assert monitor._parse_datetime("") is None

    def test_parse_invalid_format_returns_none(self):
        """Invalid date format should return None (not raise)."""
        monitor = UpdateMonitor()
        assert monitor._parse_datetime("not-a-date") is None
        assert monitor._parse_datetime("32/13/2024") is None
        assert monitor._parse_datetime("yesterday") is None


# ============================================================================
# Section 6K: Edge Cases and Boundary Conditions
# ============================================================================

class TestEdgeCases:
    """Audit: Various edge cases across the maintenance system."""

    def test_update_monitor_default_max_age(self):
        """Default max_age should be 365 days."""
        monitor = UpdateMonitor()
        assert monitor.max_age == timedelta(days=365)

    def test_update_monitor_custom_max_age(self):
        """Custom max_age_days should be respected."""
        monitor = UpdateMonitor(max_age_days=90)
        assert monitor.max_age == timedelta(days=90)

    def test_maintenance_system_creates_default_scheduler(self):
        """MaintenanceSystem without scheduler should create one."""
        system = MaintenanceSystem()
        assert isinstance(system.scheduler, TaskScheduler)

    def test_maintenance_system_uses_provided_scheduler(self):
        """MaintenanceSystem should use provided scheduler."""
        custom = TaskScheduler()
        system = MaintenanceSystem(scheduler=custom)
        assert system.scheduler is custom

    def test_maintenance_system_has_monitor_and_auditor(self):
        """MaintenanceSystem should initialise UpdateMonitor and QualityAuditor."""
        system = MaintenanceSystem()
        assert isinstance(system.update_monitor, UpdateMonitor)
        assert isinstance(system.quality_auditor, QualityAuditor)

    @pytest.mark.asyncio
    async def test_run_update_sweep_empty_inputs(self):
        """run_update_sweep with empty lists should produce empty report."""
        system = MaintenanceSystem()
        report = await system.run_update_sweep([], [])

        assert isinstance(report, UpdateReport)
        assert report.checked_papers == 0
        assert report.publication_updates == []
        assert report.missing_files == []

    @pytest.mark.asyncio
    async def test_audit_quality_empty_inputs(self):
        """audit_collection_quality with empty inputs should produce empty report."""
        system = MaintenanceSystem()
        report = await system.audit_collection_quality([], {})

        assert isinstance(report, QualityReport)
        assert report.total_files == 0
        assert report.invalid_files == []
        assert report.duplicate_groups == []
