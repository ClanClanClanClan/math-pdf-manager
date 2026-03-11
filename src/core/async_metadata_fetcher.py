#!/usr/bin/env python3
"""
Async Metadata Fetcher
High-performance async metadata retrieval for academic papers.

Features:
- Async/await for all I/O operations
- Concurrent requests to multiple sources
- Intelligent rate limiting and retry logic
- SQLite caching with async support
- Maintains compatibility with existing sync API
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import unicodedata

import aiohttp
import aiofiles
import aiosqlite
import regex as re
from tqdm.asyncio import tqdm


# Configure logging
logger = logging.getLogger("async_metadata_fetcher")


@dataclass
class Metadata:
    """Enhanced metadata structure for academic papers."""
    title: str = ""
    authors: List[str] = None
    published: str = ""
    doi: str = ""
    arxiv_id: str = ""
    journal: str = ""
    volume: str = ""
    pages: str = ""
    year: int = 0
    abstract: str = ""
    keywords: List[str] = None
    source: str = ""
    confidence: float = 0.0
    url: str = ""
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []


class AsyncMetadataCache:
    """High-performance async SQLite cache for metadata."""
    
    def __init__(self, cache_path: str = ".metadata_cache.db"):
        self.cache_path = Path(cache_path)
        self._init_lock = asyncio.Lock()
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure database is initialized."""
        if self._initialized:
            return
        
        async with self._init_lock:
            if self._initialized:
                return
            
            async with aiosqlite.connect(self.cache_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_cache (
                        key TEXT PRIMARY KEY,
                        metadata TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        last_accessed REAL NOT NULL
                    )
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_last_accessed 
                    ON metadata_cache(last_accessed)
                """)
                await db.commit()
            
            self._initialized = True
    
    async def get(self, key: str) -> Optional[Metadata]:
        """Get metadata from cache."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.cache_path) as db:
            async with db.execute(
                "SELECT metadata FROM metadata_cache WHERE key = ?",
                (key,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    # Update last accessed time
                    await db.execute(
                        "UPDATE metadata_cache SET last_accessed = ? WHERE key = ?",
                        (time.time(), key)
                    )
                    await db.commit()
                    
                    # Parse and return metadata
                    data = json.loads(row[0])
                    return Metadata(**data)
        
        return None
    
    async def set(self, key: str, metadata: Metadata):
        """Store metadata in cache."""
        await self._ensure_initialized()
        
        now = time.time()
        data = json.dumps(asdict(metadata))
        
        async with aiosqlite.connect(self.cache_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO metadata_cache 
                (key, metadata, created_at, last_accessed) 
                VALUES (?, ?, ?, ?)
            """, (key, data, now, now))
            await db.commit()
    
    async def cleanup_old_entries(self, max_age_days: int = 30):
        """Remove old cache entries."""
        await self._ensure_initialized()
        
        cutoff = time.time() - (max_age_days * 24 * 60 * 60)
        
        async with aiosqlite.connect(self.cache_path) as db:
            await db.execute(
                "DELETE FROM metadata_cache WHERE last_accessed < ?",
                (cutoff,)
            )
            await db.commit()


class AsyncMetadataFetcher:
    """Async metadata fetcher with multiple sources."""
    
    def __init__(self, cache_path: str = ".metadata_cache.db"):
        self.cache = AsyncMetadataCache(cache_path)
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        
        # Rate limiting
        self.arxiv_semaphore = asyncio.Semaphore(3)  # ArXiv rate limit
        self.crossref_semaphore = asyncio.Semaphore(5)  # Crossref rate limit
        self.scholar_semaphore = asyncio.Semaphore(1)  # Scholar rate limit
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None:
            async with self._session_lock:
                if self.session is None:
                    timeout = aiohttp.ClientTimeout(total=30)
                    self.session = aiohttp.ClientSession(
                        timeout=timeout,
                        headers={
                            'User-Agent': 'Academic-PDF-Manager/1.0 (mailto:researcher@example.com)'
                        }
                    )
        return self.session
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _normalize_identifier(self, identifier: str) -> str:
        """Normalize identifier for consistent caching."""
        identifier = identifier.lower().strip()
        
        # Remove common prefixes
        for prefix in ["doi:", "arxiv:", "http://", "https://"]:
            if identifier.startswith(prefix):
                identifier = identifier[len(prefix):]
        
        return identifier
    
    def _create_cache_key(self, identifier: str, source: str) -> str:
        """Create cache key for identifier and source."""
        normalized = self._normalize_identifier(identifier)
        combined = f"{source}:{normalized}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def _fetch_arxiv_metadata(self, arxiv_id: str) -> Optional[Metadata]:
        """Fetch metadata from ArXiv API."""
        async with self.arxiv_semaphore:
            try:
                session = await self._get_session()
                url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
                
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    xml_content = await response.text()
                    
                    # Parse XML (simplified - would use defusedxml in production)
                    # For now, extract basic info with regex
                    title_match = re.search(r'<title>(.*?)</title>', xml_content, re.DOTALL)
                    title = title_match.group(1).strip() if title_match else ""
                    
                    author_matches = re.findall(r'<name>(.*?)</name>', xml_content)
                    authors = [name.strip() for name in author_matches]
                    
                    published_match = re.search(r'<published>(.*?)</published>', xml_content)
                    published = published_match.group(1)[:10] if published_match else ""
                    
                    abstract_match = re.search(r'<summary>(.*?)</summary>', xml_content, re.DOTALL)
                    abstract = abstract_match.group(1).strip() if abstract_match else ""
                    
                    return Metadata(
                        title=title,
                        authors=authors,
                        published=published,
                        arxiv_id=arxiv_id,
                        abstract=abstract,
                        source="arxiv",
                        confidence=0.9,
                        url=f"https://arxiv.org/abs/{arxiv_id}"
                    )
                    
            except Exception as e:
                logger.error(f"ArXiv fetch failed for {arxiv_id}: {e}")
                return None
            
            # Rate limiting
            await asyncio.sleep(0.5)
    
    async def _fetch_crossref_metadata(self, doi: str) -> Optional[Metadata]:
        """Fetch metadata from Crossref API."""
        async with self.crossref_semaphore:
            try:
                session = await self._get_session()
                url = f"https://api.crossref.org/works/{doi}"
                
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    work = data.get("message", {})
                    
                    title = ""
                    if "title" in work and work["title"]:
                        title = work["title"][0]
                    
                    authors = []
                    if "author" in work:
                        for author in work["author"]:
                            given = author.get("given", "")
                            family = author.get("family", "")
                            if family:
                                authors.append(f"{given} {family}".strip())
                    
                    published = ""
                    if "published-print" in work:
                        date_parts = work["published-print"].get("date-parts", [[]])
                        if date_parts and date_parts[0]:
                            published = f"{date_parts[0][0]}-{date_parts[0][1]:02d}-{date_parts[0][2]:02d}"
                    
                    journal = work.get("container-title", [""])[0] if work.get("container-title") else ""
                    volume = work.get("volume", "")
                    pages = work.get("page", "")
                    
                    return Metadata(
                        title=title,
                        authors=authors,
                        published=published,
                        doi=doi,
                        journal=journal,
                        volume=volume,
                        pages=pages,
                        source="crossref",
                        confidence=0.95,
                        url=work.get("URL", f"https://doi.org/{doi}")
                    )
                    
            except Exception as e:
                logger.error(f"Crossref fetch failed for {doi}: {e}")
                return None
            
            # Rate limiting
            await asyncio.sleep(0.2)
    
    async def fetch_metadata(self, identifier: str) -> Optional[Metadata]:
        """
        Fetch metadata for an identifier (DOI, ArXiv ID, etc.).
        
        Tries multiple sources concurrently and returns the best result.
        """
        # Check cache first
        sources_to_try = []
        
        # Determine what sources to try based on identifier format
        if "arxiv" in identifier.lower() or re.match(r'\d{4}\.\d{4,5}', identifier):
            # ArXiv paper
            cache_key = self._create_cache_key(identifier, "arxiv")
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
            sources_to_try.append(("arxiv", identifier))
        
        if "doi" in identifier.lower() or "/" in identifier:
            # DOI
            doi = identifier.replace("doi:", "").strip()
            cache_key = self._create_cache_key(doi, "crossref")
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
            sources_to_try.append(("crossref", doi))
        
        if not sources_to_try:
            # Try to guess the type
            if re.match(r'\d{4}\.\d{4,5}', identifier):
                sources_to_try.append(("arxiv", identifier))
            elif "/" in identifier:
                sources_to_try.append(("crossref", identifier))
        
        if not sources_to_try:
            logger.warning(f"Could not determine source for identifier: {identifier}")
            return None
        
        # Fetch from sources concurrently
        tasks = []
        for source, id_val in sources_to_try:
            if source == "arxiv":
                tasks.append(self._fetch_arxiv_metadata(id_val))
            elif source == "crossref":
                tasks.append(self._fetch_crossref_metadata(id_val))
        
        # Wait for results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Find best result
        best_result = None
        best_confidence = 0.0
        
        for result in results:
            if isinstance(result, Metadata) and result.confidence > best_confidence:
                best_result = result
                best_confidence = result.confidence
        
        # Cache the result
        if best_result:
            cache_key = self._create_cache_key(identifier, best_result.source)
            await self.cache.set(cache_key, best_result)
        
        return best_result
    
    async def fetch_multiple(self, identifiers: List[str]) -> List[Tuple[str, Optional[Metadata]]]:
        """Fetch metadata for multiple identifiers concurrently."""
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        
        async def fetch_with_semaphore(identifier: str) -> Tuple[str, Optional[Metadata]]:
            async with semaphore:
                result = await self.fetch_metadata(identifier)
                return identifier, result
        
        tasks = [fetch_with_semaphore(identifier) for identifier in identifiers]
        
        # Use tqdm for progress tracking
        results = []
        for task in tqdm.as_completed(tasks, desc="Fetching metadata"):
            result = await task
            results.append(result)
        
        return results


# Sync compatibility wrapper
class MetadataFetcher:
    """Sync wrapper for backward compatibility."""
    
    def __init__(self):
        self.async_fetcher = AsyncMetadataFetcher()

    def fetch_metadata(self, identifier: str) -> Optional[Metadata]:
        """Sync version of fetch_metadata."""
        from src.core.utils.async_compat import run_sync
        return run_sync(self.async_fetcher.fetch_metadata(identifier))

    def fetch_multiple(self, identifiers: List[str]) -> List[Tuple[str, Optional[Metadata]]]:
        """Sync version of fetch_multiple."""
        from src.core.utils.async_compat import run_sync
        return run_sync(self.async_fetcher.fetch_multiple(identifiers))

    def close(self):
        """Close the async fetcher."""
        from src.core.utils.async_compat import run_sync
        run_sync(self.async_fetcher.close())


# Example usage
async def main():
    """Example usage of async metadata fetcher."""
    fetcher = AsyncMetadataFetcher()
    
    try:
        # Single paper
        metadata = await fetcher.fetch_metadata("1901.00001")
        if metadata:
            print(f"Title: {metadata.title}")
            print(f"Authors: {', '.join(metadata.authors)}")
            print(f"Published: {metadata.published}")
        
        # Multiple papers
        identifiers = ["1901.00001", "10.1007/s00780-019-00394-1", "1902.00002"]
        results = await fetcher.fetch_multiple(identifiers)
        
        for identifier, metadata in results:
            if metadata:
                print(f"{identifier}: {metadata.title}")
            else:
                print(f"{identifier}: No metadata found")
                
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())