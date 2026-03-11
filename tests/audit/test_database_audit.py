"""Phase 2: Database layer audit."""
import asyncio
import json
import os
import tempfile

from pathlib import Path

import pytest

aiosqlite = pytest.importorskip("aiosqlite")

from core.database import AsyncPaperDatabase, PaperRecord, PaperDatabase, DatabaseSchema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_paper(**overrides) -> PaperRecord:
    """Create a PaperRecord with sensible defaults, allowing overrides."""
    defaults = dict(
        file_path="/tmp/test/paper.pdf",
        title="Test Paper on Stochastic Analysis",
        authors='["Smith, John", "Doe, Jane"]',
        publication_date="2024-01-15",
        arxiv_id="2401.00001",
        doi="10.1000/test.2024",
        journal="Journal of Testing",
        volume="42",
        pages="1-20",
        abstract="This paper studies stochastic processes in testing environments.",
        keywords='["stochastic", "testing"]',
        research_areas='["mathematics", "statistics"]',
        paper_type="published",
        source="arxiv",
        confidence=0.95,
        file_size=1024000,
        file_hash="abc123def456",
    )
    defaults.update(overrides)
    return PaperRecord(**defaults)


@pytest.fixture
def tmp_db_path(tmp_path):
    """Return a path to a fresh temporary database file."""
    return str(tmp_path / "test_papers.db")


@pytest.fixture
def async_db(tmp_db_path):
    """Return an uninitialised AsyncPaperDatabase pointed at a temp file."""
    return AsyncPaperDatabase(tmp_db_path)


# =========================================================================
# 1. Schema creation
# =========================================================================


class TestSchemaCreation:
    """Verify that _ensure_initialized creates all expected schema objects."""

    @pytest.mark.asyncio
    async def test_tables_exist(self, async_db):
        """All four core tables must be created."""
        await async_db._ensure_initialized()

        async with aiosqlite.connect(async_db.db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in await cursor.fetchall()}

        for expected in ("papers", "duplicates", "versions", "schema_version"):
            assert expected in tables, f"Table '{expected}' missing from schema"

    @pytest.mark.asyncio
    async def test_indexes_exist(self, async_db):
        """All expected indexes must be present."""
        await async_db._ensure_initialized()

        async with aiosqlite.connect(async_db.db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = {row[0] for row in await cursor.fetchall()}

        expected_indexes = {
            "idx_papers_title",
            "idx_papers_authors",
            "idx_papers_arxiv",
            "idx_papers_doi",
            "idx_papers_hash",
            "idx_papers_type",
            "idx_duplicates_similarity",
            "idx_versions_original",
        }
        for idx in expected_indexes:
            assert idx in indexes, f"Index '{idx}' missing from schema"

    @pytest.mark.asyncio
    async def test_fts5_virtual_table_exists(self, async_db):
        """FTS5 virtual table papers_fts must be present."""
        await async_db._ensure_initialized()

        async with aiosqlite.connect(async_db.db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='papers_fts'"
            )
            row = await cursor.fetchone()

        assert row is not None, "FTS5 virtual table 'papers_fts' not found"

    @pytest.mark.asyncio
    async def test_schema_version_recorded(self, async_db):
        """Schema version must be written after initialisation."""
        await async_db._ensure_initialized()

        async with aiosqlite.connect(async_db.db_path) as db:
            cursor = await db.execute("SELECT version FROM schema_version")
            row = await cursor.fetchone()

        assert row is not None, "schema_version table is empty"
        assert row[0] == DatabaseSchema.CURRENT_VERSION

    @pytest.mark.asyncio
    async def test_idempotent_init(self, async_db):
        """Calling _ensure_initialized twice must not raise."""
        await async_db._ensure_initialized()
        await async_db._ensure_initialized()  # should be a no-op


# =========================================================================
# 2. add_paper + get_paper round-trip
# =========================================================================


class TestAddAndGetPaper:
    """Insert a PaperRecord, retrieve by ID, verify all fields."""

    @pytest.mark.asyncio
    async def test_add_and_get_round_trip(self, async_db):
        paper = _make_paper()
        paper_id = await async_db.add_paper(paper)

        assert isinstance(paper_id, int)
        assert paper_id >= 1

        retrieved = await async_db.get_paper(paper_id)
        assert retrieved is not None

        # Verify every field that was explicitly set
        assert retrieved.id == paper_id
        assert retrieved.file_path == "/tmp/test/paper.pdf"
        assert retrieved.title == "Test Paper on Stochastic Analysis"
        assert retrieved.authors == '["Smith, John", "Doe, Jane"]'
        assert retrieved.publication_date == "2024-01-15"
        assert retrieved.arxiv_id == "2401.00001"
        assert retrieved.doi == "10.1000/test.2024"
        assert retrieved.journal == "Journal of Testing"
        assert retrieved.volume == "42"
        assert retrieved.pages == "1-20"
        assert "stochastic processes" in retrieved.abstract
        assert retrieved.keywords == '["stochastic", "testing"]'
        assert retrieved.research_areas == '["mathematics", "statistics"]'
        assert retrieved.paper_type == "published"
        assert retrieved.source == "arxiv"
        assert retrieved.confidence == pytest.approx(0.95)
        assert retrieved.file_size == 1024000
        assert retrieved.file_hash == "abc123def456"
        assert retrieved.created_at != ""
        assert retrieved.updated_at != ""

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, async_db):
        await async_db._ensure_initialized()
        result = await async_db.get_paper(9999)
        assert result is None


# =========================================================================
# 3. get_paper_by_path
# =========================================================================


class TestGetPaperByPath:

    @pytest.mark.asyncio
    async def test_retrieve_by_file_path(self, async_db):
        paper = _make_paper(file_path="/unique/path/paper.pdf")
        paper_id = await async_db.add_paper(paper)

        retrieved = await async_db.get_paper_by_path("/unique/path/paper.pdf")
        assert retrieved is not None
        assert retrieved.id == paper_id
        assert retrieved.title == paper.title

    @pytest.mark.asyncio
    async def test_nonexistent_path_returns_none(self, async_db):
        await async_db._ensure_initialized()
        result = await async_db.get_paper_by_path("/no/such/file.pdf")
        assert result is None


# =========================================================================
# 4. search_papers (FTS5)
# =========================================================================


class TestSearchPapers:

    @pytest.mark.asyncio
    async def test_fts_search_by_title(self, async_db):
        await async_db.add_paper(
            _make_paper(
                file_path="/a.pdf",
                title="Brownian Motion in Finance",
                abstract="A study of Brownian motion.",
            )
        )
        await async_db.add_paper(
            _make_paper(
                file_path="/b.pdf",
                title="Topology of Manifolds",
                abstract="A study of manifold topology.",
            )
        )

        results = await async_db.search_papers("Brownian")
        assert len(results) >= 1
        assert any("Brownian" in r.title for r in results)

    @pytest.mark.asyncio
    async def test_fts_search_by_abstract(self, async_db):
        await async_db.add_paper(
            _make_paper(
                file_path="/c.pdf",
                title="Generic Title",
                abstract="Martingale convergence theorems are explored.",
            )
        )

        results = await async_db.search_papers("martingale")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_fts_search_respects_limit(self, async_db):
        for i in range(5):
            await async_db.add_paper(
                _make_paper(
                    file_path=f"/lim_{i}.pdf",
                    title=f"Ergodic Theory Paper {i}",
                )
            )

        results = await async_db.search_papers("Ergodic", limit=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_fts_no_results(self, async_db):
        await async_db._ensure_initialized()
        results = await async_db.search_papers("zzzznonexistentterm")
        assert results == []


# =========================================================================
# 5. CRITICAL BUG: find_duplicates always returns empty
# =========================================================================


class TestFindDuplicatesBug:
    """
    AUDIT FINDING: find_duplicates() always returns an empty list because
    no code in the entire codebase ever INSERTs rows into the ``duplicates``
    table.  The method queries the table, but it is perpetually empty.

    The /maintenance/run endpoint (app.py:137) relies on this to build a
    duplicate_map, meaning duplicate handling is completely non-functional.
    """

    @pytest.mark.asyncio
    async def test_find_duplicates_returns_empty(self, async_db):
        """Even with papers present, find_duplicates returns nothing."""
        await async_db.add_paper(_make_paper(file_path="/dup1.pdf", title="Paper A"))
        await async_db.add_paper(_make_paper(file_path="/dup2.pdf", title="Paper A"))

        result = await async_db.find_duplicates(similarity_threshold=0.0)
        assert result == [], "find_duplicates should return empty (no INSERT path exists)"

    @pytest.mark.asyncio
    async def test_duplicates_table_is_always_empty(self, async_db):
        """Directly verify the duplicates table has zero rows after adds."""
        await async_db.add_paper(_make_paper(file_path="/d1.pdf"))
        await async_db.add_paper(_make_paper(file_path="/d2.pdf"))

        async with aiosqlite.connect(async_db.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM duplicates")
            count = (await cursor.fetchone())[0]

        assert count == 0, "duplicates table should be empty (nothing populates it)"


# =========================================================================
# 6. FIXED: list_papers() now exists
# =========================================================================


class TestListPapersExists:
    """
    FIXED: AsyncPaperDatabase now has list_papers() method with pagination.
    """

    def test_list_papers_method_exists(self, async_db):
        """AsyncPaperDatabase should have a list_papers method."""
        assert hasattr(async_db, "list_papers"), (
            "list_papers should exist on AsyncPaperDatabase"
        )

    def test_list_papers_is_async(self, async_db):
        """list_papers should be an async method."""
        import asyncio
        assert asyncio.iscoroutinefunction(async_db.list_papers)

    def test_api_references_list_papers(self):
        """Confirm app.py references the missing method (documentary test)."""
        api_path = (
            Path(__file__).parent.parent.parent / "src" / "api" / "app.py"
        )
        if not api_path.exists():
            pytest.skip("app.py not found at expected location")

        source = api_path.read_text()
        assert "db.list_papers()" in source, (
            "Expected db.list_papers() call in app.py"
        )


# =========================================================================
# 7. update_paper
# =========================================================================


class TestUpdatePaper:

    @pytest.mark.asyncio
    async def test_update_changes_fields(self, async_db):
        paper = _make_paper(file_path="/upd.pdf", title="Original Title")
        paper_id = await async_db.add_paper(paper)

        paper.id = paper_id
        paper.title = "Updated Title"
        paper.journal = "New Journal"
        await async_db.update_paper(paper)

        updated = await async_db.get_paper(paper_id)
        assert updated.title == "Updated Title"
        assert updated.journal == "New Journal"

    @pytest.mark.asyncio
    async def test_update_changes_updated_at(self, async_db):
        paper = _make_paper(file_path="/upd2.pdf")
        paper_id = await async_db.add_paper(paper)

        original = await async_db.get_paper(paper_id)
        original_ts = original.updated_at

        # Small delay to ensure timestamp differs
        await asyncio.sleep(0.05)

        original.title = "Changed"
        await async_db.update_paper(original)

        after = await async_db.get_paper(paper_id)
        assert after.updated_at != original_ts, "updated_at should change on update"


# =========================================================================
# 8. get_statistics
# =========================================================================


class TestGetStatistics:

    @pytest.mark.asyncio
    async def test_empty_database_stats(self, async_db):
        await async_db._ensure_initialized()
        stats = await async_db.get_statistics()

        assert stats["total_papers"] == 0
        assert stats["by_type"] == {}
        assert stats["total_duplicates"] == 0

    @pytest.mark.asyncio
    async def test_stats_reflect_inserts(self, async_db):
        await async_db.add_paper(
            _make_paper(file_path="/s1.pdf", paper_type="published")
        )
        await async_db.add_paper(
            _make_paper(file_path="/s2.pdf", paper_type="published")
        )
        await async_db.add_paper(
            _make_paper(file_path="/s3.pdf", paper_type="working_paper")
        )

        stats = await async_db.get_statistics()
        assert stats["total_papers"] == 3
        assert stats["by_type"]["published"] == 2
        assert stats["by_type"]["working_paper"] == 1
        # duplicates is always 0 -- see audit finding #5
        assert stats["total_duplicates"] == 0


# =========================================================================
# 9. Fragile positional mapping in _row_to_paper
# =========================================================================


class TestRowToPaperFragility:
    """
    AUDIT FINDING: _row_to_paper uses hard-coded positional indexing
    (row[0]..row[19]) to map 20 columns to PaperRecord fields.  If the
    schema ever adds, removes, or reorders a column, this breaks silently
    with data assigned to wrong fields.
    """

    @pytest.mark.asyncio
    async def test_row_to_paper_maps_all_20_columns(self, async_db):
        """Insert a paper with known values, verify positional mapping works today."""
        paper = _make_paper(file_path="/pos.pdf")
        paper_id = await async_db.add_paper(paper)

        retrieved = await async_db.get_paper(paper_id)
        assert retrieved.id == paper_id
        assert retrieved.file_path == "/pos.pdf"
        # Spot-check the middle and end of the positional range
        assert retrieved.abstract != ""       # row[10]
        assert retrieved.file_hash != ""      # row[17]
        assert retrieved.updated_at != ""     # row[19]

    def test_row_to_paper_uses_named_columns(self):
        """FIXED: _row_to_paper() now uses named column mapping via zip."""
        import inspect
        source = inspect.getsource(AsyncPaperDatabase._row_to_paper)
        # Should no longer use hardcoded positional indexes
        assert "row[0]" not in source, "Should not use fragile positional indexing"
        assert "row[19]" not in source, "Should not use fragile positional indexing"
        # Should reference the column name mapping
        assert "_PAPER_COLUMNS" in source, "Should use named column mapping"


# =========================================================================
# 10. Unicode handling
# =========================================================================


class TestUnicodeHandling:

    @pytest.mark.asyncio
    async def test_unicode_title_ito(self, async_db):
        paper = _make_paper(
            file_path="/unicode_ito.pdf",
            title="It\u00f4 Calculus and Stochastic Integration",
        )
        pid = await async_db.add_paper(paper)
        retrieved = await async_db.get_paper(pid)
        assert retrieved.title == "It\u00f4 Calculus and Stochastic Integration"

    @pytest.mark.asyncio
    async def test_unicode_title_levy(self, async_db):
        paper = _make_paper(
            file_path="/unicode_levy.pdf",
            title="L\u00e9vy Processes in Finance",
        )
        pid = await async_db.add_paper(paper)
        retrieved = await async_db.get_paper(pid)
        assert retrieved.title == "L\u00e9vy Processes in Finance"

    @pytest.mark.asyncio
    async def test_unicode_title_hormander(self, async_db):
        paper = _make_paper(
            file_path="/unicode_hormander.pdf",
            title="H\u00f6rmander's Theorem on Hypoelliptic Operators",
        )
        pid = await async_db.add_paper(paper)
        retrieved = await async_db.get_paper(pid)
        assert retrieved.title == "H\u00f6rmander's Theorem on Hypoelliptic Operators"

    @pytest.mark.asyncio
    async def test_unicode_authors(self, async_db):
        paper = _make_paper(
            file_path="/unicode_auth.pdf",
            authors='["Erd\u0151s, P\u00e1l", "R\u00e9nyi, Alfr\u00e9d"]',
        )
        pid = await async_db.add_paper(paper)
        retrieved = await async_db.get_paper(pid)
        parsed = json.loads(retrieved.authors)
        assert "Erd\u0151s, P\u00e1l" in parsed

    @pytest.mark.asyncio
    async def test_fts_finds_unicode(self, async_db):
        """FTS5 should index and match Unicode content."""
        await async_db.add_paper(
            _make_paper(
                file_path="/fts_unicode.pdf",
                title="It\u00f4 Formula Revisited",
            )
        )
        results = await async_db.search_papers("It\u00f4")
        assert len(results) >= 1
        assert any("It\u00f4" in r.title for r in results)


# =========================================================================
# 11. FTS5 trigger propagation
# =========================================================================


class TestFTSTriggers:

    @pytest.mark.asyncio
    async def test_insert_propagates_to_fts(self, async_db):
        """After INSERT on papers, the FTS table should contain the new row."""
        await async_db.add_paper(
            _make_paper(file_path="/fts_ins.pdf", title="Harmonic Analysis")
        )
        results = await async_db.search_papers("Harmonic")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_update_propagates_to_fts(self, async_db):
        """After UPDATE on papers, the FTS table should reflect the change.

        FIXED: The FTS5 UPDATE trigger now does DELETE+INSERT so stale
        entries are removed correctly.
        """
        paper = _make_paper(file_path="/fts_upd.pdf", title="Old Title Wavelets")
        pid = await async_db.add_paper(paper)

        paper.id = pid
        paper.title = "New Title Semigroups"
        await async_db.update_paper(paper)

        old_results = await async_db.search_papers("Wavelets")
        new_results = await async_db.search_papers("Semigroups")

        assert len(old_results) == 0, "Old title should no longer match after FTS update"
        assert len(new_results) == 1, "New title should be findable via FTS"

    @pytest.mark.asyncio
    async def test_delete_propagates_to_fts(self, async_db):
        """After DELETE on papers, the FTS entry should be removed."""
        paper = _make_paper(file_path="/fts_del.pdf", title="Spectral Theory Unique")
        pid = await async_db.add_paper(paper)

        # Verify it is searchable
        assert len(await async_db.search_papers("Spectral")) == 1

        # Direct delete (no delete_paper method exists, use raw SQL)
        async with aiosqlite.connect(async_db.db_path) as db:
            await db.execute("DELETE FROM papers WHERE id = ?", (pid,))
            await db.commit()

        results = await async_db.search_papers("Spectral")
        assert len(results) == 0, "FTS should remove entry after DELETE trigger fires"


# =========================================================================
# 12. Duplicate file_path constraint
# =========================================================================


class TestUniqueFilePath:

    @pytest.mark.asyncio
    async def test_duplicate_file_path_raises(self, async_db):
        """file_path is UNIQUE -- inserting a duplicate must raise."""
        await async_db.add_paper(_make_paper(file_path="/unique_constraint.pdf"))

        with pytest.raises(Exception) as exc_info:
            await async_db.add_paper(
                _make_paper(file_path="/unique_constraint.pdf", title="Different Title")
            )
        # aiosqlite wraps sqlite3.IntegrityError
        assert "UNIQUE" in str(exc_info.value).upper() or "unique" in str(
            exc_info.value
        ).lower(), f"Expected UNIQUE constraint error, got: {exc_info.value}"


# =========================================================================
# 13. PaperRecord __post_init__ auto-timestamps
# =========================================================================


class TestPaperRecordPostInit:

    def test_timestamps_auto_populate(self):
        """created_at and updated_at should be auto-set when empty."""
        paper = PaperRecord(file_path="/pi.pdf", title="Test")
        assert paper.created_at != ""
        assert paper.updated_at != ""

    def test_timestamps_are_iso_format(self):
        paper = PaperRecord(file_path="/pi2.pdf", title="Test")
        # Should not raise
        from datetime import datetime
        datetime.fromisoformat(paper.created_at)
        datetime.fromisoformat(paper.updated_at)

    def test_explicit_timestamps_preserved(self):
        paper = PaperRecord(
            file_path="/pi3.pdf",
            title="Test",
            created_at="2020-01-01T00:00:00",
            updated_at="2020-06-15T12:00:00",
        )
        assert paper.created_at == "2020-01-01T00:00:00"
        assert paper.updated_at == "2020-06-15T12:00:00"

    def test_default_field_values(self):
        paper = PaperRecord()
        assert paper.id is None
        assert paper.file_path == ""
        assert paper.title == ""
        assert paper.paper_type == "unknown"
        assert paper.confidence == 0.0
        assert paper.file_size == 0


# =========================================================================
# 14. Sync wrapper PaperDatabase
# =========================================================================


class TestSyncWrapperPaperDatabase:
    """
    PaperDatabase wraps AsyncPaperDatabase for sync callers.
    This may fail if run inside an already-running event loop (e.g. Jupyter).
    """

    def test_sync_add_and_get(self, tmp_db_path):
        db = PaperDatabase(tmp_db_path)
        paper = _make_paper(file_path="/sync_test.pdf")
        paper_id = db.add_paper(paper)

        assert isinstance(paper_id, int)

        retrieved = db.get_paper(paper_id)
        assert retrieved is not None
        assert retrieved.title == paper.title

    def test_sync_search(self, tmp_db_path):
        db = PaperDatabase(tmp_db_path)
        db.add_paper(
            _make_paper(file_path="/sync_search.pdf", title="Markov Chain Monte Carlo")
        )
        results = db.search_papers("Markov")
        assert len(results) >= 1

    def test_sync_statistics(self, tmp_db_path):
        db = PaperDatabase(tmp_db_path)
        db.add_paper(_make_paper(file_path="/sync_stat.pdf"))
        stats = db.get_statistics()
        assert stats["total_papers"] == 1

    def test_sync_wrapper_has_list_papers(self, tmp_db_path):
        """FIXED: Sync wrapper now has list_papers (mirrors async)."""
        db = PaperDatabase(tmp_db_path)
        assert hasattr(db, "list_papers")


# =========================================================================
# 15. DatabaseSchema constants sanity
# =========================================================================


class TestDatabaseSchemaConstants:

    def test_current_version_is_positive(self):
        assert DatabaseSchema.CURRENT_VERSION >= 1

    def test_tables_dict_has_expected_keys(self):
        expected = {"papers", "duplicates", "versions", "schema_version"}
        assert set(DatabaseSchema.TABLES.keys()) == expected

    def test_indexes_list_is_nonempty(self):
        assert len(DatabaseSchema.INDEXES) > 0

    def test_fts5_in_indexes(self):
        fts_entries = [s for s in DatabaseSchema.INDEXES if "fts5" in s.lower()]
        assert len(fts_entries) >= 1, "Expected at least one FTS5 index definition"

    def test_trigger_definitions_present(self):
        triggers = [s for s in DatabaseSchema.INDEXES if "TRIGGER" in s.upper()]
        assert len(triggers) == 3, (
            f"Expected 3 FTS triggers (insert, update, delete), found {len(triggers)}"
        )


# =========================================================================
# 16. Edge cases and robustness
# =========================================================================


class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_empty_string_fields(self, async_db):
        """Papers with minimal / empty fields should still round-trip."""
        paper = PaperRecord(file_path="/empty.pdf", title="Minimal")
        pid = await async_db.add_paper(paper)
        retrieved = await async_db.get_paper(pid)

        assert retrieved.authors == ""
        assert retrieved.abstract == ""
        assert retrieved.doi is None

    @pytest.mark.asyncio
    async def test_very_long_abstract(self, async_db):
        long_abstract = "x" * 100_000
        paper = _make_paper(file_path="/long.pdf", abstract=long_abstract)
        pid = await async_db.add_paper(paper)
        retrieved = await async_db.get_paper(pid)
        assert len(retrieved.abstract) == 100_000

    @pytest.mark.asyncio
    async def test_get_papers_by_type(self, async_db):
        await async_db.add_paper(
            _make_paper(file_path="/type1.pdf", paper_type="thesis")
        )
        await async_db.add_paper(
            _make_paper(file_path="/type2.pdf", paper_type="thesis")
        )
        await async_db.add_paper(
            _make_paper(file_path="/type3.pdf", paper_type="published")
        )

        theses = await async_db.get_papers_by_type("thesis")
        assert len(theses) == 2
        assert all(p.paper_type == "thesis" for p in theses)

    @pytest.mark.asyncio
    async def test_concurrent_initialization(self, tmp_db_path):
        """Multiple concurrent _ensure_initialized calls should not corrupt."""
        db = AsyncPaperDatabase(tmp_db_path)

        await asyncio.gather(
            db._ensure_initialized(),
            db._ensure_initialized(),
            db._ensure_initialized(),
        )

        # Should still be functional
        pid = await db.add_paper(_make_paper(file_path="/concurrent.pdf"))
        assert pid >= 1
