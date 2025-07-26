#!/usr/bin/env python3
"""
Download Orchestrator
High-level interface for managing all download sources and strategies.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import json
import time
from dataclasses import dataclass, asdict

from .universal_downloader import UniversalDownloader, DownloadResult, SearchResult
from .publisher_downloaders import (
    WileyDownloader, TaylorFrancisDownloader, SageDownloader,
    CambridgeDownloader, ACMDownloader, EnhancedSciHubDownloader
)
from .credentials import CredentialManager, SessionManager, DownloaderConfig

logger = logging.getLogger(__name__)

@dataclass
class DownloadPlan:
    """Plan for downloading a paper with fallback sources"""
    query: str
    primary_sources: List[str]
    fallback_sources: List[str]
    estimated_success_rate: float
    priority: int = 1

@dataclass
class BatchDownloadResult:
    """Result from batch download operation"""
    total_papers: int
    successful_downloads: int
    failed_downloads: int
    total_size_mb: float
    total_time_seconds: float
    source_breakdown: Dict[str, int]
    error_summary: Dict[str, int]
    results: List[DownloadResult]
    
    @property
    def success_rate(self) -> float:
        return self.successful_downloads / self.total_papers if self.total_papers > 0 else 0.0
    
    @property
    def throughput_papers_per_minute(self) -> float:
        return (self.successful_downloads / self.total_time_seconds * 60) if self.total_time_seconds > 0 else 0.0

class DownloadOrchestrator:
    """
    Master orchestrator for all download operations.
    
    Provides intelligent source selection, automatic fallbacks,
    batch optimization, and comprehensive reporting.
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.credential_manager = CredentialManager(str(self.config_dir / "credentials.enc"))
        self.config = DownloaderConfig(str(self.config_dir / "downloader_config.json"))
        self.session_manager = None
        self.universal_downloader = None
        
        # Statistics
        self.stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'source_usage': {},
            'error_counts': {},
            'total_bandwidth_mb': 0.0
        }
        
        # Load statistics if they exist
        self._load_stats()
    
    async def initialize(self, master_password: str):
        """Initialize the orchestrator with master password"""
        try:
            self.credential_manager.initialize_encryption(master_password)
            self.session_manager = SessionManager(self.credential_manager)
            
            # Initialize universal downloader with enhanced strategies
            await self._initialize_universal_downloader()
            
            logger.info("Download orchestrator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    async def _initialize_universal_downloader(self):
        """Initialize universal downloader with all strategies"""
        config_dict = {
            'credentials': {},
            'preference_order': self.config.get('download_preferences', [
                'springer', 'elsevier', 'wiley', 'ieee', 
                'enhanced-sci-hub', 'anna-archive', 'libgen'
            ])
        }
        
        # Add credentials from credential manager
        for publisher in self.credential_manager.list_publishers():
            config_dict['credentials'][publisher] = self.credential_manager.get_publisher_credentials(publisher)
        
        self.universal_downloader = UniversalDownloader(config_dict)
        
        # Add enhanced strategies
        self._add_enhanced_strategies()
    
    def _add_enhanced_strategies(self):
        """Add publisher-specific enhanced strategies"""
        try:
            # Add Wiley
            if 'wiley' in self.credential_manager.list_publishers():
                wiley_creds = self.credential_manager.get_publisher_credentials('wiley')
                self.universal_downloader.strategies['wiley'] = WileyDownloader(wiley_creds)
            
            # Add Taylor & Francis
            if 'taylor-francis' in self.credential_manager.list_publishers():
                tf_creds = self.credential_manager.get_publisher_credentials('taylor-francis')
                self.universal_downloader.strategies['taylor-francis'] = TaylorFrancisDownloader(tf_creds)
            
            # Add SAGE
            if 'sage' in self.credential_manager.list_publishers():
                sage_creds = self.credential_manager.get_publisher_credentials('sage')
                self.universal_downloader.strategies['sage'] = SageDownloader(sage_creds)
            
            # Add Cambridge
            if 'cambridge' in self.credential_manager.list_publishers():
                cam_creds = self.credential_manager.get_publisher_credentials('cambridge')
                self.universal_downloader.strategies['cambridge'] = CambridgeDownloader(cam_creds)
            
            # Add ACM
            if 'acm' in self.credential_manager.list_publishers():
                acm_creds = self.credential_manager.get_publisher_credentials('acm')
                self.universal_downloader.strategies['acm'] = ACMDownloader(acm_creds)
            
            # Always add enhanced Sci-Hub
            self.universal_downloader.strategies['enhanced-sci-hub'] = EnhancedSciHubDownloader()
            
            logger.info(f"Initialized {len(self.universal_downloader.strategies)} download strategies")
            
        except Exception as e:
            logger.error(f"Failed to add enhanced strategies: {e}")
    
    async def search_papers(self, queries: List[str], max_results_per_query: int = 10) -> List[SearchResult]:
        """Search for papers across all sources"""
        if not self.universal_downloader:
            raise RuntimeError("Orchestrator not initialized")
        
        all_results = []
        
        for query in queries:
            try:
                results = await self.universal_downloader.search_all(query, max_results_per_query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")
        
        # Deduplicate and sort by confidence
        seen_dois = set()
        unique_results = []
        
        for result in all_results:
            identifier = result.doi or result.title
            if identifier and identifier not in seen_dois:
                seen_dois.add(identifier)
                unique_results.append(result)
        
        unique_results.sort(key=lambda x: x.confidence, reverse=True)
        return unique_results
    
    async def create_download_plan(self, papers: List[Union[str, SearchResult]]) -> List[DownloadPlan]:
        """Create optimal download plans for papers"""
        plans = []
        
        for paper in papers:
            if isinstance(paper, str):
                query = paper
                paper_obj = SearchResult(title=paper, confidence=0.5)
            else:
                query = paper.doi or paper.title or str(paper)
                paper_obj = paper
            
            # Analyze paper to determine best sources
            primary_sources, fallback_sources = self._analyze_paper_sources(paper_obj)
            
            # Estimate success rate based on source availability and paper type
            success_rate = self._estimate_success_rate(paper_obj, primary_sources)
            
            plan = DownloadPlan(
                query=query,
                primary_sources=primary_sources,
                fallback_sources=fallback_sources,
                estimated_success_rate=success_rate
            )
            
            plans.append(plan)
        
        # Sort by estimated success rate (highest first)
        plans.sort(key=lambda x: x.estimated_success_rate, reverse=True)
        
        return plans
    
    def _analyze_paper_sources(self, paper: SearchResult) -> tuple[List[str], List[str]]:
        """Analyze paper to determine optimal download sources"""
        primary_sources = []
        fallback_sources = []
        
        # Check paper characteristics
        if paper.source:
            # If we know the original source, prioritize it
            if paper.source in self.universal_downloader.strategies:
                primary_sources.append(paper.source)
        
        # Publisher detection based on DOI or URL
        if paper.doi:
            if '1007' in paper.doi:  # Springer
                primary_sources.append('springer')
            elif '1016' in paper.doi:  # Elsevier
                primary_sources.append('elsevier')
            elif '1002' in paper.doi or '1111' in paper.doi:  # Wiley
                primary_sources.append('wiley')
            elif '1109' in paper.doi:  # IEEE
                primary_sources.append('ieee')
        
        # Add institutional sources based on availability
        available_institutional = [
            name for name in ['springer', 'elsevier', 'wiley', 'ieee', 'taylor-francis', 'sage', 'cambridge', 'acm']
            if name in self.universal_downloader.strategies and name not in primary_sources
        ]
        primary_sources.extend(available_institutional[:2])  # Limit to top 2
        
        # Fallback to alternative sources
        fallback_sources = ['enhanced-sci-hub', 'anna-archive', 'libgen']
        
        return primary_sources, fallback_sources
    
    def _estimate_success_rate(self, paper: SearchResult, primary_sources: List[str]) -> float:
        """Estimate likelihood of successful download"""
        base_rate = 0.3  # Base success rate
        
        # Boost for institutional access
        if any(source in ['springer', 'elsevier', 'wiley', 'ieee'] for source in primary_sources):
            base_rate += 0.4
        
        # Boost for DOI availability
        if paper.doi:
            base_rate += 0.2
        
        # Boost for recent papers
        if paper.year and paper.year >= 2010:
            base_rate += 0.1
        
        return min(0.95, base_rate)  # Cap at 95%
    
    async def download_single(self, paper: Union[str, SearchResult], 
                            preferred_sources: Optional[List[str]] = None,
                            save_path: Optional[str] = None) -> DownloadResult:
        """Download a single paper with comprehensive error handling"""
        if not self.universal_downloader:
            raise RuntimeError("Orchestrator not initialized")
        
        start_time = time.time()
        
        try:
            # Create download plan if no preferred sources
            if not preferred_sources:
                plans = await self.create_download_plan([paper])
                if plans:
                    plan = plans[0]
                    preferred_sources = plan.primary_sources + plan.fallback_sources
            
            # Attempt download
            result = await self.universal_downloader.download_paper(paper, preferred_sources)
            
            # Update statistics
            self._update_stats(result)
            
            # Save file if requested and successful
            if result.success and save_path and result.pdf_data:
                # Security: Validate save path to prevent path traversal
                save_path_obj = Path(save_path).resolve()
                
                # Ensure the resolved path is within allowed directories
                # Get the base directory (parent of the requested path)
                base_dir = Path(save_path).parent.resolve() if Path(save_path).parent.exists() else Path.cwd()
                
                # Check if resolved path is within base directory
                try:
                    save_path_obj.relative_to(base_dir)
                except ValueError:
                    raise ValueError(f"Invalid save path: Path traversal detected")
                
                # Additional security checks
                if '..' in str(save_path) or save_path.startswith('/etc') or save_path.startswith('/root'):
                    raise ValueError(f"Invalid save path: Suspicious path pattern")
                
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                with open(save_path_obj, 'wb') as f:
                    f.write(result.pdf_data)
                
                result.metadata['saved_path'] = str(save_path_obj)
                logger.info(f"Paper saved to {save_path_obj}")
            
            return result
            
        except Exception as e:
            logger.error(f"Download failed with exception: {e}")
            return DownloadResult(
                success=False,
                error=str(e),
                source="orchestrator",
                download_time=time.time() - start_time
            )
    
    async def download_batch(self, papers: List[Union[str, SearchResult]],
                           max_concurrent: int = 5,
                           save_directory: Optional[str] = None) -> BatchDownloadResult:
        """Download multiple papers with intelligent batching"""
        if not self.universal_downloader:
            raise RuntimeError("Orchestrator not initialized")
        
        start_time = time.time()
        
        # Create download plans
        logger.info(f"Creating download plans for {len(papers)} papers...")
        plans = await self.create_download_plan(papers)
        
        # Prepare save directory
        save_dir = None
        if save_directory:
            # Security: Validate save directory to prevent path traversal
            save_dir = Path(save_directory).resolve()
            
            # Ensure the directory is not in sensitive locations
            sensitive_paths = ['/etc', '/root', '/sys', '/proc', '/dev', '/var/log']
            if any(str(save_dir).startswith(path) for path in sensitive_paths):
                raise ValueError(f"Invalid save directory: Cannot save to system directories")
            
            # Check for path traversal attempts
            if '..' in save_directory:
                raise ValueError(f"Invalid save directory: Path traversal detected")
            
            save_dir.mkdir(parents=True, exist_ok=True)
        
        # Execute downloads with concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_plan(plan: DownloadPlan, index: int):
            async with semaphore:
                try:
                    # Determine save path
                    save_path = None
                    if save_dir:
                        # Create safe filename from query
                        safe_filename = self._create_safe_filename(plan.query, index)
                        save_path = save_dir / safe_filename
                    
                    # Download with plan's source preferences
                    preferred_sources = plan.primary_sources + plan.fallback_sources
                    result = await self.download_single(plan.query, preferred_sources, save_path)
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Batch download failed for plan {index}: {e}")
                    return DownloadResult(
                        success=False,
                        error=str(e),
                        source="batch_orchestrator"
                    )
        
        # Execute all downloads
        logger.info(f"Executing batch download with {max_concurrent} concurrent downloads...")
        tasks = [download_with_plan(plan, i) for i, plan in enumerate(plans)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        total_time = time.time() - start_time
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        # Calculate statistics
        total_size_bytes = sum(r.file_size for r in successful if r.file_size)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        # Source breakdown
        source_breakdown = {}
        for result in successful:
            source = result.source or 'unknown'
            source_breakdown[source] = source_breakdown.get(source, 0) + 1
        
        # Error breakdown
        error_summary = {}
        for result in failed:
            error = result.error or 'unknown_error'
            # Categorize common errors
            error_category = self._categorize_error(error)
            error_summary[error_category] = error_summary.get(error_category, 0) + 1
        
        batch_result = BatchDownloadResult(
            total_papers=len(papers),
            successful_downloads=len(successful),
            failed_downloads=len(failed),
            total_size_mb=total_size_mb,
            total_time_seconds=total_time,
            source_breakdown=source_breakdown,
            error_summary=error_summary,
            results=results
        )
        
        # Log summary
        logger.info(f"Batch download complete:")
        logger.info(f"  Success rate: {batch_result.success_rate:.1%}")
        logger.info(f"  Total size: {total_size_mb:.1f} MB")
        logger.info(f"  Throughput: {batch_result.throughput_papers_per_minute:.1f} papers/min")
        logger.info(f"  Source breakdown: {source_breakdown}")
        
        return batch_result
    
    def _create_safe_filename(self, query: str, index: int) -> str:
        """Create safe filename from query"""
        import re
        
        # Remove/replace unsafe characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', query)
        safe_name = safe_name.strip()
        
        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100] + "..."
        
        # Add index to avoid conflicts
        return f"{index:04d}_{safe_name}.pdf"
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error for reporting"""
        error_lower = error.lower()
        
        if 'timeout' in error_lower:
            return 'timeout'
        elif 'http' in error_lower and any(code in error_lower for code in ['404', '403', '401']):
            return 'access_denied'
        elif 'mirror' in error_lower or 'connection' in error_lower:
            return 'connection_error'  
        elif 'pdf' in error_lower:
            return 'invalid_pdf'
        elif 'all' in error_lower and 'failed' in error_lower:
            return 'all_sources_failed'
        else:
            return 'other'
    
    def _update_stats(self, result: DownloadResult):
        """Update internal statistics"""
        self.stats['total_downloads'] += 1
        
        if result.success:
            self.stats['successful_downloads'] += 1
            
            source = result.source or 'unknown'
            self.stats['source_usage'][source] = self.stats['source_usage'].get(source, 0) + 1
            
            if result.file_size:
                self.stats['total_bandwidth_mb'] += result.file_size / (1024 * 1024)
        else:
            error_category = self._categorize_error(result.error or 'unknown')
            self.stats['error_counts'][error_category] = self.stats['error_counts'].get(error_category, 0) + 1
        
        # Periodically save stats
        if self.stats['total_downloads'] % 10 == 0:
            self._save_stats()
    
    def _save_stats(self):
        """Save statistics to file"""
        stats_file = self.config_dir / "download_stats.json"
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
    
    def _load_stats(self):
        """Load statistics from file"""
        stats_file = self.config_dir / "download_stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    loaded_stats = json.load(f)
                    self.stats.update(loaded_stats)
            except Exception as e:
                logger.error(f"Failed to load stats: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive download statistics"""
        total_downloads = self.stats['total_downloads']
        success_rate = (self.stats['successful_downloads'] / total_downloads) if total_downloads > 0 else 0
        
        return {
            'total_downloads': total_downloads,
            'successful_downloads': self.stats['successful_downloads'],
            'success_rate': success_rate,
            'total_bandwidth_mb': self.stats['total_bandwidth_mb'],
            'source_usage': self.stats['source_usage'],
            'error_breakdown': self.stats['error_counts'],
            'available_sources': list(self.universal_downloader.strategies.keys()) if self.universal_downloader else []
        }
    
    def add_publisher_credentials(self, publisher: str, credentials: Dict[str, str]):
        """Add credentials for a publisher"""
        self.credential_manager.set_publisher_credentials(publisher, credentials)
        logger.info(f"Added credentials for {publisher}")
    
    async def test_source_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all configured sources"""
        if not self.universal_downloader:
            return {'error': 'Orchestrator not initialized'}
        
        connectivity = {}
        test_query = "10.1038/nature12373"  # Test DOI
        
        for source_name, strategy in self.universal_downloader.strategies.items():
            try:
                # Test with a simple search
                results = await strategy.search(test_query)
                connectivity[source_name] = len(results) > 0
            except Exception as e:
                logger.debug(f"Connectivity test failed for {source_name}: {e}")
                connectivity[source_name] = False
        
        return connectivity
    
    async def close(self):
        """Clean up resources"""
        self._save_stats()
        
        if self.universal_downloader:
            await self.universal_downloader.close()
        
        if self.session_manager:
            await self.session_manager.close_all_sessions()

# Example usage
async def main():
    """Example orchestrator usage"""
    orchestrator = DownloadOrchestrator()
    
    # Initialize (you'd get this password securely in real usage)
    master_password = "your_secure_password"
    if not await orchestrator.initialize(master_password):
        print("Failed to initialize orchestrator")
        return
    
    try:
        # Test connectivity
        print("Testing source connectivity...")
        connectivity = await orchestrator.test_source_connectivity()
        for source, status in connectivity.items():
            print(f"  {source}: {'✓' if status else '✗'}")
        
        # Search for papers
        queries = ["machine learning", "quantum computing"]
        print(f"\nSearching for papers...")
        papers = await orchestrator.search_papers(queries, max_results_per_query=2)
        print(f"Found {len(papers)} papers")
        
        # Download papers
        if papers:
            print("\nDownloading papers...")
            batch_result = await orchestrator.download_batch(papers[:3], save_directory="downloads")
            print(f"Downloaded {batch_result.successful_downloads}/{batch_result.total_papers} papers")
            print(f"Success rate: {batch_result.success_rate:.1%}")
        
        # Show statistics
        stats = orchestrator.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total downloads: {stats['total_downloads']}")
        print(f"  Success rate: {stats['success_rate']:.1%}")
        print(f"  Available sources: {len(stats['available_sources'])}")
    
    finally:
        await orchestrator.close()

if __name__ == "__main__":
    asyncio.run(main())