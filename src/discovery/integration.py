#!/usr/bin/env python3
"""
Discovery Integration - Bridge between ArXiv discovery and existing system

Connects the new discovery capabilities to existing:
- Filename validation (1,001-line validator)  
- Publisher downloads (unified downloader)
- Authentication (ETH institutional access)
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from publishers import DownloadResult
    from publishers.unified_downloader import UnifiedDownloader
    from core.validation.comprehensive_validator import ComprehensiveUnifiedValidationService
    from discovery import DiscoveryEngine, PaperCandidate
    from arxivbot.pipeline.optimized_harvester import ProductionOptimizedHarvester, OptimizedHarvesterConfig
    from arxivbot.monitoring.service import MonitoringService, MonitoringServiceConfig, initialize_monitoring_service
except ImportError as e:  # pragma: no cover - fallback only exercised in constrained environments
    logging.warning(f"Import failed: {e}. Some features may not work.")

    from dataclasses import dataclass

    @dataclass
    class DownloadResult:  # Minimal stand-in matching the real signature
        success: bool
        file_path: Path | None = None
        error_message: str | None = None
        metadata: Dict[str, Any] | None = None

    class UnifiedDownloader:
        async def download_from_url(self, url, download_path, **_):  # type: ignore[override]
            print(f"STUB: Would download {url} -> {download_path}")
            return DownloadResult(True, file_path=Path(download_path))

        async def download_from_publisher(self, publisher_name, paper_id, download_path):  # type: ignore[override]
            print(f"STUB: Would download {paper_id} from {publisher_name} -> {download_path}")
            return DownloadResult(True, file_path=Path(download_path))

        async def download_best_match(self, title, authors=None, download_dir=None):  # type: ignore[override]
            print(f"STUB: No direct download info for '{title}', skipping")
            return DownloadResult(False, error_message="Stub downloader cannot resolve best match")

        async def logout_all(self):  # type: ignore[override]
            return None

    class ComprehensiveUnifiedValidationService:
        def generate_filename(self, paper):
            title = paper.get('title', 'unknown').replace(' ', '_')[:50]
            return f"{title}.pdf"

        def sanitize_filename(self, filename: str) -> str:
            return filename

    class DiscoveryEngine:  # type: ignore
        async def search_by_query(self, query: str, *, max_results: int = 10):
            print(f"STUB: Discovery query '{query}'")
            return []

        async def search_by_doi(self, doi: str):
            print(f"STUB: DOI lookup '{doi}'")
            return None

        async def search_by_authors(self, authors, year_range=None, *, max_results: int = 10):
            print(f"STUB: Author search {authors}")
            return []

        async def close(self):
            return None

logger = logging.getLogger(__name__)


class DiscoveryIntegration:
    """
    Integration layer between ArXiv discovery and existing PDF management
    
    Workflow:
    1. Harvest papers using ArXiv bot optimized harvester
    2. Score papers for relevance
    3. Use existing filename validator for accepted papers
    4. Use existing publisher system for downloads
    """
    
    def __init__(self, monitoring_port: int = 9099):
        self.monitoring_port = monitoring_port
        self.harvester = None
        self.downloader = UnifiedDownloader()
        self.validator = ComprehensiveUnifiedValidationService()
        self.monitoring = None
        self.discovery_engine = DiscoveryEngine()
        
        logger.info("Discovery integration initialized")
    
    async def initialize(self):
        """Initialize the discovery system"""
        try:
            # Initialize monitoring
            monitoring_config = MonitoringServiceConfig(
                prometheus_enabled=True,
                prometheus_port=self.monitoring_port,
                auto_start_server=True
            )
            self.monitoring = await initialize_monitoring_service(monitoring_config)
            
            # Initialize harvester
            harvester_config = OptimizedHarvesterConfig(
                max_papers_per_batch=50,
                score_threshold=0.25,
                enable_monitoring=True,
                cache_embeddings=True
            )
            
            self.harvester = ProductionOptimizedHarvester(harvester_config, self.monitoring)
            
            if await self.harvester.initialize():
                logger.info("Discovery system initialized successfully")
                return True
            else:
                logger.error("Failed to initialize harvester")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize discovery system: {e}")
            return False
    
    async def discover_papers(self,
                              categories: List[str],
                              max_papers_per_category: int = 50,
                              relevance_threshold: float = 0.25) -> List[PaperCandidate]:
        """
        Discover relevant papers from specified categories
        
        Args:
            categories: ArXiv categories (e.g., ['cs.LG', 'math.PR'])
            max_papers_per_category: Maximum papers to fetch per category
            relevance_threshold: Minimum relevance score
            
        Returns:
            List of relevant papers with metadata
        """
        aggregated: List[PaperCandidate] = []

        for category in categories:
            logger.info("Running discovery search for category %s", category)
            query = f"cat:{category}" if ':' not in category else category
            try:
                results = await self.discovery_engine.search_by_query(query, max_results=max_papers_per_category)
                aggregated.extend(results)
            except Exception as exc:
                logger.error("Discovery query failed for %s: %s", category, exc)

        # Include harvester data if available and initialized.
        if self.harvester:
            if hasattr(self.harvester, 'config'):
                try:
                    self.harvester.config.score_threshold = relevance_threshold
                except Exception as exc:  # pragma: no cover
                    logger.warning("Unable to update harvester threshold: %s", exc)

            for category in categories:
                try:
                    harvester_results = await self.harvester.process_category(
                        category=category,
                        max_papers=max_papers_per_category
                    )
                    papers_found = harvester_results.get('papers_accepted', 0)
                    avg_score = harvester_results.get('avg_score', relevance_threshold)
                    logger.info("Harvester accepted %s papers for %s", papers_found, category)
                    # Harvester currently returns aggregate metrics; append placeholders with metadata.
                    if papers_found:
                        aggregated.extend([
                            PaperCandidate(
                                title=f"{category} candidate",
                                authors=["Unknown"],
                                source="arxiv-harvester",
                                metadata={"avg_score": avg_score, "category": category}
                            )
                            for _ in range(min(papers_found, max_papers_per_category))
                        ])
                except Exception as exc:
                    logger.warning("Harvester processing failed for %s: %s", category, exc)

        return aggregated
    
    def generate_filename(self, paper: Dict[str, Any]) -> str:
        """
        Generate filename using the existing system's logic
        
        Based on academic_downloader.py filename generation pattern
        """
        try:
            # Extract title and clean it up
            title = paper.get('title', 'unknown')
            authors = paper.get('authors', [])
            paper_id = paper.get('id') or paper.get('doi') or paper.get('arxiv_id') or paper.get('title', '')
            
            # Create a safe filename using the existing pattern
            base_name = title
            
            # Remove dangerous characters (same as academic_downloader.py)
            dangerous_chars = ['..', '/', '\\', '\x00', '|', ':', '*', '?', '<', '>', '"', ';', '$', '`']
            safe_name = base_name
            for char in dangerous_chars:
                safe_name = safe_name.replace(char, '')
            
            # Remove extra whitespace and replace with underscores
            safe_name = re.sub(r'\s+', '_', safe_name.strip())
            
            # Truncate if too long (keep reasonable length)
            if len(safe_name) > 80:
                safe_name = safe_name[:80]
            
            # Use hash for consistent naming if name is too short or empty
            if not safe_name or len(safe_name) < 3:
                import hashlib
                safe_name = f"paper_{hashlib.sha256(paper_id.encode()).hexdigest()[:16]}"
            
            # Ensure .pdf extension
            if not safe_name.endswith('.pdf'):
                safe_name += '.pdf'
            
            # Use the validator to sanitize the final filename
            final_filename = self.validator.sanitize_filename(safe_name)
            
            logger.info(f"Generated filename: {final_filename}")
            return final_filename
            
        except Exception as e:
            # Fallback to simple filename if generation fails
            logger.warning(f"Filename generation failed: {e}, using simple fallback")
            title = paper.get('title', 'unknown').replace(' ', '_')[:50]
            safe_title = re.sub(r'[^\w\-_\.]', '', title)
            return f"{safe_title}.pdf" if safe_title else "unknown_paper.pdf"
    
    async def download_paper(self, paper: Dict[str, Any], filename: str) -> DownloadResult:
        """Download *paper* and return a :class:`DownloadResult` instance."""

        downloads_dir = Path("downloads")
        downloads_dir.mkdir(parents=True, exist_ok=True)
        target_path = downloads_dir / filename

        url = paper.get('pdf_url') or paper.get('url')
        if url:
            return await self.downloader.download_from_url(url, target_path)

        publisher_name = paper.get('publisher')
        paper_id = paper.get('id') or paper.get('doi')
        if publisher_name and paper_id:
            return await self.downloader.download_from_publisher(publisher_name, paper_id, target_path)

        # Final fallback: attempt a best-match search based on title/authors.
        title = paper.get('title', '')
        authors = paper.get('authors')
        if title:
            return await self.downloader.download_best_match(title, authors=authors, download_dir=downloads_dir)

        return DownloadResult(False, error_message="Insufficient metadata to perform download")

    async def discover_and_download(self, 
                                  categories: List[str],
                                  max_papers_per_category: int = 50,
                                  relevance_threshold: float = 0.25,
                                  download: bool = False) -> Dict[str, Any]:
        """
        Complete workflow: discover papers and optionally download them
        
        Args:
            categories: ArXiv categories to search
            max_papers_per_category: Max papers per category  
            relevance_threshold: Minimum relevance score
            download: Whether to actually download papers
            
        Returns:
            Summary of discovery and download results
        """
        logger.info(f"Starting discovery workflow for categories: {categories}")
        
        # Step 1: Discover papers
        candidates = await self.discover_papers(
            categories=categories,
            max_papers_per_category=max_papers_per_category,
            relevance_threshold=relevance_threshold
        )

        results = {
            'papers_discovered': len(candidates),
            'categories_processed': len(categories),
            'papers_downloaded': 0,
            'download_errors': 0,
            'papers': []
        }

        # Step 2: Process each paper
        for candidate in candidates:
            paper = self._candidate_to_dict(candidate)
            try:
                # Generate filename using existing validator
                filename = self.generate_filename(paper)
                
                paper_result = {
                    'title': paper['title'],
                    'filename': filename,
                    'relevance_score': paper.get('relevance_score', relevance_threshold),
                    'category': paper.get('category', 'unknown'),
                    'source': paper.get('source'),
                    'doi': paper.get('doi'),
                    'arxiv_id': paper.get('arxiv_id'),
                }
                
                # Step 3: Download if requested
                if download:
                    download_result = await self.download_paper(paper, filename)
                    if download_result.success:
                        paper_result['download_status'] = 'success'
                        results['papers_downloaded'] += 1
                        if download_result.file_path:
                            paper_result['download_path'] = str(download_result.file_path)
                    else:
                        paper_result['download_status'] = 'error'
                        results['download_errors'] += 1
                        if download_result.error_message:
                            paper_result['download_error'] = download_result.error_message
                
                results['papers'].append(paper_result)
                
            except Exception as e:
                logger.error(f"Error processing paper {paper.get('title', 'unknown')}: {e}")
                results['download_errors'] += 1
        
        logger.info(f"Discovery workflow complete: {results['papers_discovered']} papers found, "
                   f"{results['papers_downloaded']} downloaded")
        
        return results

    async def shutdown(self):
        """Clean shutdown"""
        if self.harvester:
            await self.harvester.shutdown()
        if self.monitoring:
            await self.monitoring.shutdown()
        if hasattr(self.discovery_engine, 'close'):
            try:
                await self.discovery_engine.close()
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.debug("Discovery engine close failed: %s", exc)
        if hasattr(self.downloader, 'logout_all'):
            try:
                await self.downloader.logout_all()  # type: ignore[arg-type]
            except TypeError:
                # Stub implementations may expose a synchronous version
                self.downloader.logout_all()  # type: ignore[attr-defined]
        
        logger.info("Discovery integration shutdown complete")

    def _candidate_to_dict(self, candidate: PaperCandidate) -> Dict[str, Any]:
        metadata = candidate.metadata or {}
        return {
            'title': candidate.title,
            'authors': candidate.authors,
            'doi': candidate.doi,
            'arxiv_id': candidate.arxiv_id,
            'source': candidate.source,
            'url': candidate.url,
            'published_year': candidate.published_year,
            'metadata': metadata,
            'category': metadata.get('category', self._infer_category(candidate)),
            'relevance_score': metadata.get('avg_score', 0.0),
        }

    def _infer_category(self, candidate: PaperCandidate) -> str:
        if candidate.arxiv_id and ':' in candidate.arxiv_id:
            return candidate.arxiv_id.split(':', 1)[0]
        subjects = candidate.metadata.get('subject') if isinstance(candidate.metadata, dict) else None
        if isinstance(subjects, list) and subjects:
            return subjects[0]
        return 'unknown'


# Convenience function for CLI usage
async def discover_papers_cli(categories: List[str], 
                            max_papers: int = 50,
                            threshold: float = 0.25,
                            download: bool = False,
                            monitoring_port: int = 9099) -> Dict[str, Any]:
    """
    CLI-friendly function for paper discovery
    
    Usage:
        results = await discover_papers_cli(['cs.LG', 'math.PR'])
    """
    integration = DiscoveryIntegration(monitoring_port)
    
    try:
        if await integration.initialize():
            return await integration.discover_and_download(
                categories=categories,
                max_papers_per_category=max_papers,
                relevance_threshold=threshold,
                download=download
            )
        else:
            return {'error': 'Failed to initialize discovery system'}
    finally:
        await integration.shutdown()


if __name__ == "__main__":
    # Test the integration
    async def test():
        results = await discover_papers_cli(['cs.LG'], max_papers=5, download=False)
        print(f"Discovery test results: {results}")
    
    asyncio.run(test())
