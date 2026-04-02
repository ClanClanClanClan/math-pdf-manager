#!/usr/bin/env python3
"""
Academic Paper Database
Fast SQLite backend for paper metadata storage and search.

Features:
- Full-text search across titles, authors, abstracts
- Efficient duplicate detection
- Version tracking (preprint → published)
- Fast bulk operations
- Schema migrations
- Async and sync interfaces
"""

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
import hashlib

import aiosqlite


logger = logging.getLogger("database")


@dataclass 
class PaperRecord:
    """Database record for an academic paper."""
    id: Optional[int] = None
    file_path: str = ""
    title: str = ""
    authors: str = ""  # JSON string of author list
    publication_date: Optional[str] = None
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    abstract: str = ""
    keywords: str = ""  # JSON string of keyword list
    research_areas: str = ""  # JSON string of area list  
    paper_type: str = "unknown"  # working_paper, published, thesis, book
    source: str = ""
    confidence: float = 0.0
    file_size: int = 0
    file_hash: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class DatabaseSchema:
    """Database schema management."""
    
    CURRENT_VERSION = 1
    
    TABLES = {
        "papers": """
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                authors TEXT NOT NULL,  -- JSON array
                publication_date TEXT,
                arxiv_id TEXT,
                doi TEXT,
                journal TEXT,
                volume TEXT, 
                pages TEXT,
                abstract TEXT,
                keywords TEXT,  -- JSON array
                research_areas TEXT,  -- JSON array
                paper_type TEXT DEFAULT 'unknown',
                source TEXT,
                confidence REAL DEFAULT 0.0,
                file_size INTEGER DEFAULT 0,
                file_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """,
        
        "duplicates": """
            CREATE TABLE duplicates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper1_id INTEGER NOT NULL,
                paper2_id INTEGER NOT NULL,
                similarity_score REAL NOT NULL,
                similarity_type TEXT NOT NULL,  -- title, author, content, hash
                created_at TEXT NOT NULL,
                FOREIGN KEY (paper1_id) REFERENCES papers (id),
                FOREIGN KEY (paper2_id) REFERENCES papers (id),
                UNIQUE (paper1_id, paper2_id, similarity_type)
            )
        """,
        
        "versions": """
            CREATE TABLE versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_paper_id INTEGER NOT NULL,
                updated_paper_id INTEGER NOT NULL,
                version_type TEXT NOT NULL,  -- preprint_to_published, revision, errata
                created_at TEXT NOT NULL,
                FOREIGN KEY (original_paper_id) REFERENCES papers (id),
                FOREIGN KEY (updated_paper_id) REFERENCES papers (id)
            )
        """,
        
        "schema_version": """
            CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """
    }
    
    INDEXES = [
        "CREATE INDEX idx_papers_title ON papers(title)",
        "CREATE INDEX idx_papers_authors ON papers(authors)",
        "CREATE INDEX idx_papers_arxiv ON papers(arxiv_id)",
        "CREATE INDEX idx_papers_doi ON papers(doi)",
        "CREATE INDEX idx_papers_hash ON papers(file_hash)",
        "CREATE INDEX idx_papers_type ON papers(paper_type)",
        "CREATE INDEX idx_duplicates_similarity ON duplicates(similarity_score DESC)",
        "CREATE INDEX idx_versions_original ON versions(original_paper_id)",
        
        # Full-text search indexes
        """CREATE VIRTUAL TABLE papers_fts USING fts5(
            title, authors, abstract, keywords, content=papers, content_rowid=id
        )""",
        
        # FTS triggers
        """CREATE TRIGGER papers_fts_insert AFTER INSERT ON papers 
           BEGIN
               INSERT INTO papers_fts(rowid, title, authors, abstract, keywords)
               VALUES (new.id, new.title, new.authors, new.abstract, new.keywords);
           END""",
           
        """CREATE TRIGGER papers_fts_update AFTER UPDATE ON papers
           BEGIN
               INSERT INTO papers_fts(papers_fts, rowid, title, authors, abstract, keywords)
               VALUES ('delete', old.id, old.title, old.authors, old.abstract, old.keywords);
               INSERT INTO papers_fts(rowid, title, authors, abstract, keywords)
               VALUES (new.id, new.title, new.authors, new.abstract, new.keywords);
           END""",

        """CREATE TRIGGER papers_fts_delete AFTER DELETE ON papers
           BEGIN
               INSERT INTO papers_fts(papers_fts, rowid, title, authors, abstract, keywords)
               VALUES ('delete', old.id, old.title, old.authors, old.abstract, old.keywords);
           END"""
    ]


class AsyncPaperDatabase:
    """Async interface to the paper database."""
    
    def __init__(self, db_path: str = "papers.db"):
        self.db_path = Path(db_path)
        self._init_lock = asyncio.Lock()
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure database is initialized with proper schema."""
        if self._initialized:
            return
        
        async with self._init_lock:
            if self._initialized:
                return
            
            async with aiosqlite.connect(self.db_path) as db:
                # Enable foreign keys
                await db.execute("PRAGMA foreign_keys = ON")
                
                # Check current schema version
                try:
                    async with db.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1") as cursor:
                        row = await cursor.fetchone()
                        current_version = row[0] if row else 0
                except sqlite3.OperationalError:
                    current_version = 0
                
                # Create tables if needed
                if current_version < DatabaseSchema.CURRENT_VERSION:
                    await self._create_schema(db)
                    
                    # Update schema version
                    await db.execute(
                        "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                        (DatabaseSchema.CURRENT_VERSION, datetime.now().isoformat())
                    )
                    await db.commit()
            
            self._initialized = True
    
    async def _create_schema(self, db: aiosqlite.Connection):
        """Create database schema."""
        # Create tables
        for table_name, table_sql in DatabaseSchema.TABLES.items():
            await db.execute(table_sql)
        
        # Create indexes
        for index_sql in DatabaseSchema.INDEXES:
            try:
                await db.execute(index_sql)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    raise
    
    async def add_paper(self, paper: PaperRecord) -> int:
        """Add a paper to the database."""
        await self._ensure_initialized()
        
        # Generate file hash if not provided
        if not paper.file_hash and paper.file_path:
            paper.file_hash = await self._calculate_file_hash(paper.file_path)
        
        paper.updated_at = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            
            cursor = await db.execute("""
                INSERT INTO papers (
                    file_path, title, authors, publication_date, arxiv_id, doi,
                    journal, volume, pages, abstract, keywords, research_areas,
                    paper_type, source, confidence, file_size, file_hash,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.file_path, paper.title, paper.authors, paper.publication_date,
                paper.arxiv_id, paper.doi, paper.journal, paper.volume, paper.pages,
                paper.abstract, paper.keywords, paper.research_areas, paper.paper_type,
                paper.source, paper.confidence, paper.file_size, paper.file_hash,
                paper.created_at, paper.updated_at
            ))
            
            await db.commit()
            return cursor.lastrowid
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file."""
        try:
            import aiofiles
            hash_sha256 = hashlib.sha256()
            async with aiofiles.open(file_path, 'rb') as f:
                async for chunk in f:
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""
    
    async def get_paper(self, paper_id: int) -> Optional[PaperRecord]:
        """Get a paper by ID."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_paper(row)
        return None
    
    async def get_paper_by_path(self, file_path: str) -> Optional[PaperRecord]:
        """Get a paper by file path."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM papers WHERE file_path = ?", (file_path,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_paper(row)
        return None
    
    async def search_papers(self, query: str, limit: int = 50) -> List[PaperRecord]:
        """Full-text search across papers."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Use FTS5 for full-text search
            async with db.execute("""
                SELECT papers.* FROM papers 
                JOIN papers_fts ON papers.id = papers_fts.rowid
                WHERE papers_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_paper(row) for row in rows]
    
    async def find_duplicates(self, similarity_threshold: float = 0.8) -> List[Tuple[PaperRecord, PaperRecord, float]]:
        """Find potential duplicate papers."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT p1.*, p2.*, d.similarity_score
                FROM duplicates d
                JOIN papers p1 ON d.paper1_id = p1.id
                JOIN papers p2 ON d.paper2_id = p2.id
                WHERE d.similarity_score >= ?
                ORDER BY d.similarity_score DESC
            """, (similarity_threshold,)) as cursor:
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    # Split row into two paper records and similarity score
                    mid = len(row) // 2
                    paper1 = self._row_to_paper(row[:mid])
                    paper2 = self._row_to_paper(row[mid:-1])
                    similarity = row[-1]
                    results.append((paper1, paper2, similarity))
                
                return results
    
    async def get_papers_by_type(self, paper_type: str) -> List[PaperRecord]:
        """Get papers by type (working_paper, published, etc.)."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM papers WHERE paper_type = ?", (paper_type,)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_paper(row) for row in rows]
    
    async def update_paper(self, paper: PaperRecord):
        """Update an existing paper."""
        await self._ensure_initialized()
        
        paper.updated_at = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE papers SET
                    title = ?, authors = ?, publication_date = ?, arxiv_id = ?, doi = ?,
                    journal = ?, volume = ?, pages = ?, abstract = ?, keywords = ?,
                    research_areas = ?, paper_type = ?, source = ?, confidence = ?,
                    file_size = ?, file_hash = ?, updated_at = ?
                WHERE id = ?
            """, (
                paper.title, paper.authors, paper.publication_date, paper.arxiv_id,
                paper.doi, paper.journal, paper.volume, paper.pages, paper.abstract,
                paper.keywords, paper.research_areas, paper.paper_type, paper.source,
                paper.confidence, paper.file_size, paper.file_hash, paper.updated_at,
                paper.id
            ))
            await db.commit()
    
    async def list_papers(self, limit: int = 100, offset: int = 0) -> List[PaperRecord]:
        """List papers with pagination."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM papers ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_paper(row) for row in rows]

    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Total papers
            async with db.execute("SELECT COUNT(*) FROM papers") as cursor:
                stats['total_papers'] = (await cursor.fetchone())[0]
            
            # Papers by type
            async with db.execute("""
                SELECT paper_type, COUNT(*) FROM papers GROUP BY paper_type
            """) as cursor:
                stats['by_type'] = dict(await cursor.fetchall())
            
            # Total duplicates
            async with db.execute("SELECT COUNT(*) FROM duplicates") as cursor:
                stats['total_duplicates'] = (await cursor.fetchone())[0]
            
            # Recent additions (last 30 days)
            async with db.execute("""
                SELECT COUNT(*) FROM papers 
                WHERE created_at > datetime('now', '-30 days')
            """) as cursor:
                stats['recent_additions'] = (await cursor.fetchone())[0]
            
            return stats
    
    # Column order for positional (tuple) rows — must match CREATE TABLE.
    _PAPER_COLUMNS = (
        "id", "file_path", "title", "authors", "publication_date",
        "arxiv_id", "doi", "journal", "volume", "pages", "abstract",
        "keywords", "research_areas", "paper_type", "source", "confidence",
        "file_size", "file_hash", "created_at", "updated_at",
    )

    def _row_to_paper(self, row) -> PaperRecord:
        """Convert database row to PaperRecord.

        Accepts both ``aiosqlite.Row`` (dict-like) objects and plain tuples.
        """
        # If the row supports dict-style key access use column names directly.
        if hasattr(row, "keys"):
            return PaperRecord(**{col: row[col] for col in self._PAPER_COLUMNS if col in row.keys()})
        # Fall back to positional mapping for plain tuples.
        return PaperRecord(**dict(zip(self._PAPER_COLUMNS, row)))


class PaperDatabase:
    """Sync wrapper for backward compatibility."""
    
    def __init__(self, db_path: str = "papers.db"):
        self.async_db = AsyncPaperDatabase(db_path)

    def add_paper(self, paper: PaperRecord) -> int:
        """Sync version of add_paper."""
        from core.utils.async_compat import run_sync
        return run_sync(self.async_db.add_paper(paper))

    def get_paper(self, paper_id: int) -> Optional[PaperRecord]:
        """Sync version of get_paper."""
        from core.utils.async_compat import run_sync
        return run_sync(self.async_db.get_paper(paper_id))

    def search_papers(self, query: str, limit: int = 50) -> List[PaperRecord]:
        """Sync version of search_papers."""
        from core.utils.async_compat import run_sync
        return run_sync(self.async_db.search_papers(query, limit))

    def list_papers(self, limit: int = 100, offset: int = 0) -> List[PaperRecord]:
        """Sync version of list_papers."""
        from core.utils.async_compat import run_sync
        return run_sync(self.async_db.list_papers(limit, offset))

    def get_statistics(self) -> Dict[str, Any]:
        """Sync version of get_statistics."""
        from core.utils.async_compat import run_sync
        return run_sync(self.async_db.get_statistics())


# Example usage
async def main():
    """Example usage of the database."""
    db = AsyncPaperDatabase("test_papers.db")
    
    # Add a paper
    paper = PaperRecord(
        file_path="/path/to/paper.pdf",
        title="Stochastic Calculus and Applications",
        authors='["Smith, John", "Doe, Jane"]',
        arxiv_id="2101.00001",
        paper_type="published"
    )
    
    paper_id = await db.add_paper(paper)
    print(f"Added paper with ID: {paper_id}")
    
    # Search papers
    results = await db.search_papers("stochastic calculus")
    print(f"Found {len(results)} papers")
    
    # Get statistics
    stats = await db.get_statistics()
    print(f"Database stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())