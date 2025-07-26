#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publishers/unified_downloader.py - Unified Download Manager
Provides a single interface for downloading papers from multiple publishers
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

from . import publisher_registry, AuthenticationConfig, DownloadResult

logger = logging.getLogger(__name__)


class UnifiedDownloader:
    """Unified interface for downloading papers from multiple publishers"""
    
    def __init__(self):
        self.publishers: Dict[str, Any] = {}
        self.auth_configs: Dict[str, AuthenticationConfig] = {}
    
    def configure_publisher(self, publisher_name: str, auth_config: AuthenticationConfig):
        """Configure authentication for a publisher"""
        self.auth_configs[publisher_name] = auth_config
        logger.info(f"Configured authentication for {publisher_name}")
    
    def get_publisher(self, publisher_name: str):
        """Get or create a publisher instance"""
        if publisher_name not in self.publishers:
            auth_config = self.auth_configs.get(publisher_name, AuthenticationConfig())
            self.publishers[publisher_name] = publisher_registry.get_publisher(publisher_name, auth_config)
        return self.publishers[publisher_name]
    
    def search_all_publishers(self, title: str, authors: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Search for papers across all configured publishers"""
        results = {}
        
        for publisher_name in publisher_registry.list_publishers():
            try:
                publisher = self.get_publisher(publisher_name)
                search_results = publisher.search_paper(title, authors)
                results[publisher_name] = search_results
                logger.info(f"Found {len(search_results)} results from {publisher_name}")
            except Exception as e:
                logger.error(f"Search failed for {publisher_name}: {e}")
                results[publisher_name] = []
        
        return results
    
    def download_from_publisher(self, publisher_name: str, paper_id: str, download_path: Path) -> DownloadResult:
        """Download a paper from a specific publisher"""
        try:
            publisher = self.get_publisher(publisher_name)
            return publisher.download_paper(paper_id, download_path)
        except Exception as e:
            error_msg = f"Download failed from {publisher_name}: {e}"
            logger.error(error_msg)
            return DownloadResult(False, error_message=error_msg)
    
    def download_best_match(self, title: str, authors: Optional[List[str]] = None, 
                           download_dir: Path = Path('.')) -> DownloadResult:
        """Search all publishers and download the best match"""
        search_results = self.search_all_publishers(title, authors)
        
        # Find the best match across all publishers
        best_match = None
        best_publisher = None
        
        for publisher_name, results in search_results.items():
            if results:
                # For now, just take the first result
                # In a real implementation, we'd score matches
                best_match = results[0]
                best_publisher = publisher_name
                break
        
        if best_match and best_publisher:
            paper_id = best_match.get('id') or best_match.get('arnumber') or best_match.get('doi')
            if paper_id:
                filename = f"{title[:50]}.pdf"  # Truncate long titles
                download_path = download_dir / filename
                return self.download_from_publisher(best_publisher, paper_id, download_path)
        
        return DownloadResult(False, error_message="No suitable paper found")
    
    def get_publisher_status(self) -> Dict[str, bool]:
        """Get authentication status for all publishers"""
        status = {}
        for publisher_name in publisher_registry.list_publishers():
            try:
                publisher = self.get_publisher(publisher_name)
                status[publisher_name] = publisher.is_authenticated()
            except Exception as e:
                logger.error(f"Failed to check status for {publisher_name}: {e}")
                status[publisher_name] = False
        return status
    
    def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate with all configured publishers"""
        results = {}
        for publisher_name in publisher_registry.list_publishers():
            try:
                publisher = self.get_publisher(publisher_name)
                results[publisher_name] = publisher.authenticate()
            except Exception as e:
                logger.error(f"Authentication failed for {publisher_name}: {e}")
                results[publisher_name] = False
        return results
    
    def logout_all(self):
        """Logout from all publishers"""
        for publisher_name, publisher in self.publishers.items():
            try:
                publisher.logout()
                logger.info(f"Logged out from {publisher_name}")
            except Exception as e:
                logger.error(f"Logout failed for {publisher_name}: {e}")
        
        self.publishers.clear()


# Export the class
__all__ = ['UnifiedDownloader']