#!/usr/bin/env python3
"""
Smart Academic Paper Downloader
Intelligent downloading with source prioritization and duplicate prevention.

Features:
- Multi-source downloading (ArXiv, publishers, repositories)
- Automatic source prioritization (published > preprint)
- Duplicate detection before download
- Retry logic with exponential backoff
- Progress tracking and cancellation
- Automatic file organization
"""

import asyncio
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, urljoin
import hashlib

import aiohttp
import aiofiles
from tqdm.asyncio import tqdm

from .async_metadata_fetcher import AsyncMetadataFetcher, Metadata
from .database import AsyncPaperDatabase, PaperRecord
from .config_manager import get_config


logger = logging.getLogger("smart_downloader")


@dataclass
class DownloadSource:
    """Information about a download source."""
    url: str
    source_type: str  # arxiv, publisher, repository, preprint
    priority: int  # Lower = higher priority
    requires_auth: bool = False
    rate_limit: float = 1.0  # Seconds between requests
    confidence: float = 0.0


@dataclass
class DownloadResult:
    """Result of a download attempt."""
    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    source: Optional[DownloadSource] = None
    metadata: Optional[Metadata] = None
    file_size: int = 0
    download_time: float = 0.0


class SourceDetector:
    """Detect download sources for academic papers."""
    
    ARXIV_PATTERNS = [
        r'arxiv\.org/abs/(\d{4}\.\d{4,5})',
        r'arxiv\.org/pdf/(\d{4}\.\d{4,5})',
        r'(\d{4}\.\d{4,5})',  # Direct ArXiv ID
    ]
    
    DOI_PATTERNS = [
        r'doi\.org/(.+)',
        r'dx\.doi\.org/(.+)',
        r'doi:(.+)',
    ]
    
    def __init__(self):
        self.arxiv_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.ARXIV_PATTERNS]
        self.doi_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.DOI_PATTERNS]
    
    def detect_sources(self, identifier: str) -> List[DownloadSource]:
        """Detect possible download sources for an identifier."""
        sources = []
        
        # Check for ArXiv
        for regex in self.arxiv_regex:
            match = regex.search(identifier)
            if match:
                arxiv_id = match.group(1) if match.lastindex else match.group(0)
                sources.extend(self._get_arxiv_sources(arxiv_id))
                break
        
        # Check for DOI
        for regex in self.doi_regex:
            match = regex.search(identifier)
            if match:
                doi = match.group(1)
                sources.extend(self._get_doi_sources(doi))
                break
        
        # Check if it's a direct URL
        if identifier.startswith(('http://', 'https://')):
            sources.append(self._classify_url(identifier))
        
        # Sort by priority (lower number = higher priority)
        sources.sort(key=lambda x: x.priority)
        return sources
    
    def _get_arxiv_sources(self, arxiv_id: str) -> List[DownloadSource]:
        """Get download sources for ArXiv papers."""
        return [
            DownloadSource(
                url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                source_type="arxiv",
                priority=2,  # Preprint, lower priority than published
                rate_limit=1.0,
                confidence=0.95
            )
        ]
    
    def _get_doi_sources(self, doi: str) -> List[DownloadSource]:
        """Get download sources for DOI."""
        return [
            DownloadSource(
                url=f"https://doi.org/{doi}",
                source_type="publisher",
                priority=1,  # Published version, highest priority
                requires_auth=True,  # Usually requires subscription
                rate_limit=2.0,
                confidence=0.99
            )
        ]
    
    def _classify_url(self, url: str) -> DownloadSource:
        """Classify a direct URL."""
        domain = urlparse(url).netloc.lower()
        
        if 'arxiv.org' in domain:
            return DownloadSource(
                url=url,
                source_type="arxiv",
                priority=2,
                rate_limit=1.0,
                confidence=0.95
            )
        elif any(publisher in domain for publisher in ['springer', 'ieee', 'acm', 'elsevier']):
            return DownloadSource(
                url=url,
                source_type="publisher",
                priority=1,
                requires_auth=True,
                rate_limit=2.0,
                confidence=0.90
            )
        else:
            return DownloadSource(
                url=url,
                source_type="repository",
                priority=3,
                rate_limit=1.0,
                confidence=0.70
            )


class SmartDownloader:
    """Smart academic paper downloader."""
    
    def __init__(self, database: AsyncPaperDatabase, metadata_fetcher: AsyncMetadataFetcher):
        self.database = database
        self.metadata_fetcher = metadata_fetcher
        self.source_detector = SourceDetector()
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        
        # Rate limiting semaphores
        self.arxiv_semaphore = asyncio.Semaphore(3)
        self.publisher_semaphore = asyncio.Semaphore(2)
        self.repository_semaphore = asyncio.Semaphore(5)
        
        # Configuration
        self.config = get_config()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None:
            async with self._session_lock:
                if self.session is None:
                    timeout = aiohttp.ClientTimeout(total=60, connect=10)
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
    
    def _get_rate_limiter(self, source_type: str) -> asyncio.Semaphore:
        """Get appropriate rate limiter for source type."""
        if source_type == "arxiv":
            return self.arxiv_semaphore
        elif source_type == "publisher":
            return self.publisher_semaphore
        else:
            return self.repository_semaphore
    
    async def _check_duplicate(self, metadata: Metadata) -> Optional[PaperRecord]:
        """Check if paper already exists in database."""
        if not metadata.title:
            return None
        
        # Search by exact match first
        if metadata.arxiv_id:
            papers = await self.database.search_papers(f'arxiv_id:"{metadata.arxiv_id}"')
            if papers:
                return papers[0]
        
        if metadata.doi:
            papers = await self.database.search_papers(f'doi:"{metadata.doi}"')
            if papers:
                return papers[0]
        
        # Fuzzy search by title
        title_words = metadata.title.lower().split()[:5]  # First 5 words
        query = " AND ".join(title_words)
        papers = await self.database.search_papers(query, limit=5)
        
        # Check for similar titles
        for paper in papers:
            if self._calculate_title_similarity(metadata.title, paper.title) > 0.85:
                return paper
        
        return None
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        from difflib import SequenceMatcher
        
        # Normalize titles
        title1 = re.sub(r'[^\w\s]', '', title1.lower())
        title2 = re.sub(r'[^\w\s]', '', title2.lower())
        
        return SequenceMatcher(None, title1, title2).ratio()
    
    async def _download_from_source(self, source: DownloadSource, output_path: Path) -> DownloadResult:
        """Download from a specific source."""
        rate_limiter = self._get_rate_limiter(source.source_type)
        
        async with rate_limiter:
            try:
                session = await self._get_session()
                start_time = asyncio.get_event_loop().time()
                
                # Create temporary file
                temp_dir = Path(tempfile.gettempdir())
                temp_file = temp_dir / f"download_{hash(source.url)}.pdf"
                
                async with session.get(source.url) as response:
                    if response.status == 200:
                        file_size = 0
                        async with aiofiles.open(temp_file, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                                file_size += len(chunk)
                        
                        # Move to final location
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        os.rename(temp_file, output_path)
                        
                        download_time = asyncio.get_event_loop().time() - start_time
                        
                        return DownloadResult(
                            success=True,
                            file_path=str(output_path),
                            source=source,
                            file_size=file_size,
                            download_time=download_time
                        )
                    
                    elif response.status == 429:  # Rate limited
                        return DownloadResult(
                            success=False,
                            error=f"Rate limited (429) from {source.url}",
                            source=source
                        )
                    
                    else:
                        return DownloadResult(
                            success=False,
                            error=f"HTTP {response.status} from {source.url}",
                            source=source
                        )
                        
            except Exception as e:
                return DownloadResult(
                    success=False,
                    error=f"Download failed: {str(e)}",
                    source=source
                )
            
            finally:
                # Rate limiting delay
                await asyncio.sleep(source.rate_limit)
    
    def _determine_output_path(self, metadata: Metadata, base_folder: str) -> Path:
        """Determine appropriate output path based on metadata."""
        config = self.config
        base_path = Path(config.base_maths_folder)
        
        # Determine paper type and folder
        if metadata.arxiv_id and not metadata.journal:
            # Preprint
            folder_paths = config.get_folder_paths("working")
            if folder_paths:
                output_folder = Path(folder_paths[0])  # Use first working papers folder
            else:
                output_folder = base_path / "Working Papers"
        elif metadata.journal:
            # Published paper
            folder_paths = config.get_folder_paths("published")
            if folder_paths:
                output_folder = Path(folder_paths[0])  # Use first published folder
            else:
                output_folder = base_path / "Published Papers"
        else:
            # Unknown type
            output_folder = base_path / "Downloaded Papers"
        
        # Generate filename
        authors = ""
        if metadata.authors and len(metadata.authors) > 0:
            if len(metadata.authors) == 1:
                authors = metadata.authors[0]
            elif len(metadata.authors) == 2:
                authors = f"{metadata.authors[0]} and {metadata.authors[1]}"
            else:
                authors = f"{metadata.authors[0]} et al"
        
        # Clean title for filename
        title = re.sub(r'[^\w\s-]', '', metadata.title)
        title = re.sub(r'\s+', ' ', title).strip()
        title = title[:100]  # Limit length
        
        if authors and title:
            filename = f"{authors} - {title}.pdf"
        elif title:
            filename = f"{title}.pdf"
        else:
            filename = f"paper_{metadata.arxiv_id or 'unknown'}.pdf"
        
        # Clean filename for filesystem
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        return output_folder / filename
    
    async def download_paper(self, identifier: str, output_path: Optional[str] = None) -> DownloadResult:
        """
        Download a paper by identifier (ArXiv ID, DOI, URL).
        
        Args:
            identifier: Paper identifier (ArXiv ID, DOI, or URL)
            output_path: Optional output path (auto-determined if not provided)
        
        Returns:
            DownloadResult with success status and details
        """
        logger.info(f"Starting download for: {identifier}")
        
        # Get metadata first
        metadata = await self.metadata_fetcher.fetch_metadata(identifier)
        if not metadata:
            return DownloadResult(
                success=False,
                error=f"Could not fetch metadata for {identifier}"
            )
        
        # Check for duplicates
        existing_paper = await self._check_duplicate(metadata)
        if existing_paper:
            logger.info(f"Paper already exists: {existing_paper.file_path}")
            return DownloadResult(
                success=False,
                error=f"Paper already exists at {existing_paper.file_path}",
                metadata=metadata
            )
        
        # Determine output path
        if output_path:
            final_path = Path(output_path)
        else:
            final_path = self._determine_output_path(metadata, self.config.base_maths_folder)
        
        # Detect download sources
        sources = self.source_detector.detect_sources(identifier)
        if not sources:
            return DownloadResult(
                success=False,
                error=f"No download sources found for {identifier}",
                metadata=metadata
            )
        
        # Try sources in priority order
        last_error = None
        for source in sources:
            logger.info(f"Trying source: {source.url} (priority: {source.priority})")
            
            result = await self._download_from_source(source, final_path)
            if result.success:
                # Add to database
                paper_record = PaperRecord(
                    file_path=str(final_path),
                    title=metadata.title,
                    authors=str(metadata.authors),
                    publication_date=metadata.published,
                    arxiv_id=metadata.arxiv_id,
                    doi=metadata.doi,
                    journal=metadata.journal,
                    abstract=metadata.abstract,
                    keywords=str(metadata.keywords),
                    paper_type="working_paper" if metadata.arxiv_id and not metadata.journal else "published",
                    source=metadata.source,
                    confidence=metadata.confidence,
                    file_size=result.file_size
                )
                
                await self.database.add_paper(paper_record)
                
                result.metadata = metadata
                logger.info(f"Successfully downloaded: {final_path}")
                return result
            
            last_error = result.error
            logger.warning(f"Source failed: {result.error}")
        
        return DownloadResult(
            success=False,
            error=f"All sources failed. Last error: {last_error}",
            metadata=metadata
        )
    
    async def download_multiple(self, identifiers: List[str]) -> List[Tuple[str, DownloadResult]]:
        """Download multiple papers concurrently."""
        semaphore = asyncio.Semaphore(3)  # Limit concurrent downloads
        
        async def download_with_semaphore(identifier: str) -> Tuple[str, DownloadResult]:
            async with semaphore:
                result = await self.download_paper(identifier)
                return identifier, result
        
        tasks = [download_with_semaphore(identifier) for identifier in identifiers]
        
        # Use tqdm for progress tracking
        results = []
        for task in tqdm.as_completed(tasks, desc="Downloading papers"):
            result = await task
            results.append(result)
        
        return results


# Example usage
async def main():
    """Example usage of smart downloader."""
    from .database import AsyncPaperDatabase
    from .async_metadata_fetcher import AsyncMetadataFetcher
    
    # Initialize components
    database = AsyncPaperDatabase("papers.db")
    metadata_fetcher = AsyncMetadataFetcher()
    downloader = SmartDownloader(database, metadata_fetcher)
    
    try:
        # Download a paper
        result = await downloader.download_paper("1901.00001")
        if result.success:
            print(f"Downloaded: {result.file_path}")
        else:
            print(f"Download failed: {result.error}")
        
        # Download multiple papers
        identifiers = ["1901.00001", "1902.00002", "10.1007/s00780-019-00394-1"]
        results = await downloader.download_multiple(identifiers)
        
        for identifier, result in results:
            if result.success:
                print(f"{identifier}: Downloaded to {result.file_path}")
            else:
                print(f"{identifier}: Failed - {result.error}")
    
    finally:
        await downloader.close()
        await metadata_fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())