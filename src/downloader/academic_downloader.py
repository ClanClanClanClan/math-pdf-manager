#!/usr/bin/env python3
"""
Academic Paper Downloader
Smart downloader with institutional login support and fallback sources.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, urljoin

import aiohttp
import aiofiles

from .sources import get_download_sources, DownloadSource, SourceType


logger = logging.getLogger("downloader")


@dataclass
class DownloadResult:
    """Result of a download attempt."""
    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    source_used: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    file_size: int = 0
    download_time: float = 0.0


class InstitutionalAuth:
    """Handle institutional authentication using existing auth system."""
    
    def __init__(self):
        self.auth_manager = None
        self.publisher_sessions = {}
        self._setup_auth_manager()
    
    def _setup_auth_manager(self):
        """Initialize the existing auth manager."""
        try:
            # Import existing auth system
            from auth.manager import AuthManager
            from publishers import publisher_registry, AuthenticationConfig
            self.auth_manager = AuthManager()
            self.publisher_registry = publisher_registry
            
            # Register available publishers
            try:
                from publishers.ieee_publisher import IEEEPublisher
                self.publisher_registry.register('ieee', IEEEPublisher)
            except ImportError:
                pass
                
            try:
                from publishers.siam_publisher import SIAMPublisher  
                self.publisher_registry.register('siam', SIAMPublisher)
            except ImportError:
                pass
                
        except ImportError as e:
            logger.warning(f"Could not load existing auth system: {e}")
            self.auth_manager = None
    
    def has_credentials(self, publisher: str = 'ieee') -> bool:
        """Check if we have credentials for a publisher."""
        if not self.auth_manager:
            return False
            
        try:
            # Check for ETH credentials via environment
            eth_username = os.environ.get('ETH_USERNAME', '')
            eth_password = os.environ.get('ETH_PASSWORD', '')
            return bool(eth_username and eth_password)
        except Exception:
            return False
    
    def get_publisher_session(self, publisher: str) -> Optional[Any]:
        """Get authenticated session for a publisher."""
        if not self.auth_manager:
            return None
            
        if publisher in self.publisher_sessions:
            return self.publisher_sessions[publisher]
            
        try:
            # Create authentication config
            from publishers import AuthenticationConfig
            auth_config = AuthenticationConfig(
                username=os.environ.get('ETH_USERNAME', ''),
                password=os.environ.get('ETH_PASSWORD', ''),
                institutional_login='eth'
            )
            
            # Get publisher instance
            if publisher in self.publisher_registry.list_publishers():
                pub_instance = self.publisher_registry.get_publisher(publisher, auth_config)
                if pub_instance.authenticate():
                    self.publisher_sessions[publisher] = pub_instance.session
                    return pub_instance.session
        except Exception as e:
            logger.warning(f"Failed to authenticate with {publisher}: {e}")
            
        return None
    
    def get_auth_headers(self, publisher: str = 'ieee') -> Dict[str, str]:
        """Get authentication headers for a publisher."""
        session = self.get_publisher_session(publisher)
        if session and hasattr(session, 'headers'):
            return dict(session.headers)
        return {}


class AcademicDownloader:
    """Smart academic paper downloader."""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        self.institutional_auth = InstitutionalAuth()
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        
        # Rate limiting
        self.last_request_time = {}
        
        # Configure logging
        self.logger = logger
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None:
            async with self._session_lock:
                if self.session is None:
                    timeout = aiohttp.ClientTimeout(total=60, connect=10)
                    
                    # Configure connector for better performance
                    connector = aiohttp.TCPConnector(
                        limit=10,
                        limit_per_host=3,
                        ttl_dns_cache=300
                    )
                    
                    self.session = aiohttp.ClientSession(
                        timeout=timeout,
                        connector=connector,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                    )
        return self.session
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _respect_rate_limit(self, source: DownloadSource):
        """Respect rate limiting for a source."""
        last_request = self.last_request_time.get(source.name, 0)
        time_since_last = time.time() - last_request
        
        if time_since_last < source.rate_limit:
            wait_time = source.rate_limit - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time[source.name] = time.time()
    
    def _extract_filename_from_headers(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract filename from Content-Disposition header."""
        content_disp = headers.get('Content-Disposition', '')
        if 'filename=' in content_disp:
            # Extract filename from header
            match = re.search(r'filename="?([^"]+)"?', content_disp)
            if match:
                return match.group(1)
        return None
    
    def _generate_filename(self, identifier: str, metadata: Optional[Dict] = None) -> str:
        """Generate a filename for the downloaded paper with security sanitization."""
        # Try to extract meaningful parts from identifier
        if metadata and metadata.get('title'):
            # Use metadata if available
            title = metadata['title'][:100]  # Limit length
            # Sanitize filename - remove path separators and dangerous characters
            title = re.sub(r'[^\w\s-]', '', title)
            title = title.replace('/', '_').replace('\\', '_').replace('..', '_')
            return f"{title}.pdf"
        
        # Try to extract ArXiv ID
        arxiv_match = re.search(r'(\d{4}\.\d{4,5})', identifier)
        if arxiv_match:
            return f"arxiv_{arxiv_match.group(1)}.pdf"
        
        # Try to extract DOI
        doi_match = re.search(r'10\.\d{4,}/[-._;()/:\w]+', identifier)
        if doi_match:
            doi_safe = doi_match.group(0).replace('/', '_')
            return f"doi_{doi_safe}.pdf"
        
        # Fallback: hash the identifier (use SHA-256 for security)
        id_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"paper_{id_hash}.pdf"
    
    async def _try_download_source(self, source: DownloadSource, identifier: str, 
                                 session: aiohttp.ClientSession) -> Optional[DownloadResult]:
        """Try to download from a specific source."""
        await self._respect_rate_limit(source)
        
        try:
            # Build URL for this source
            url = source.build_url(identifier) if hasattr(source, 'build_url') else identifier
            if not url:
                url = identifier  # Use identifier as-is
            
            self.logger.info(f"Trying {source.name}: {url}")
            
            # Add authentication if needed and available
            headers = {}
            if source.requires_auth and self.institutional_auth.has_credentials(source.name.lower()):
                # Map source names to publisher keys
                publisher_key = source.name.lower().replace(' xplore', '').replace(' digital library', '').replace(' ', '_')
                if publisher_key == 'ieee_xplore':
                    publisher_key = 'ieee'
                    
                headers.update(self.institutional_auth.get_auth_headers(publisher_key))
                
                # For publisher sources, try to use their authenticated session
                session = self.institutional_auth.get_publisher_session(publisher_key)
                if session:
                    # Use the authenticated session's cookies/headers
                    if hasattr(session, 'cookies'):
                        session.cookies.set_policy = None  # Disable cookie policy for the request
                    self.logger.info(f"Using authenticated session for {source.name}")
            
            # Special handling for Sci-Hub
            if source.name == "Sci-Hub":
                # Sci-Hub might redirect multiple times
                async with session.get(url, allow_redirects=True, headers=headers) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'pdf' in content_type.lower():
                            return await self._save_response(response, identifier, source)
                        else:
                            # Might be HTML page, try to extract PDF link
                            html = await response.text()
                            pdf_match = re.search(r'(https?://[^"]+\.pdf[^"]*)', html)
                            if pdf_match:
                                pdf_url = pdf_match.group(1)
                                async with session.get(pdf_url, headers=headers) as pdf_response:
                                    if pdf_response.status == 200:
                                        return await self._save_response(pdf_response, identifier, source)
            
            # Standard download attempt
            else:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'pdf' in content_type.lower() or response.headers.get('Content-Length', 0):
                            return await self._save_response(response, identifier, source)
                    
                    elif response.status == 404:
                        return DownloadResult(
                            success=False,
                            error=f"{source.name}: Not found (404)",
                            source_used=source.name
                        )
                    else:
                        return DownloadResult(
                            success=False,
                            error=f"{source.name}: HTTP {response.status}",
                            source_used=source.name
                        )
        
        except asyncio.TimeoutError:
            return DownloadResult(
                success=False,
                error=f"{source.name}: Timeout",
                source_used=source.name
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"{source.name}: {str(e)}",
                source_used=source.name
            )
        
        # Fallback if no conditions matched
        return DownloadResult(
            success=False,
            error=f"{source.name}: No suitable download method found",
            source_used=source.name
        )
    
    async def _save_response(self, response: aiohttp.ClientResponse, 
                           identifier: str, source: DownloadSource) -> DownloadResult:
        """Save response content to file."""
        start_time = time.time()
        
        # Determine filename
        filename = self._extract_filename_from_headers(dict(response.headers))
        if not filename:
            filename = self._generate_filename(identifier)
        
        # Sanitize filename to prevent path traversal
        filename = os.path.basename(filename)  # Remove any directory components
        filename = re.sub(r'[^\w\s.-]', '_', filename)  # Replace dangerous chars
        filename = filename.replace('..', '_')  # Prevent directory traversal
        
        # Ensure filename is not empty after sanitization
        if not filename or filename == '.pdf':
            filename = f"paper_{hashlib.sha256(identifier.encode()).hexdigest()[:16]}.pdf"
        
        # Create temporary file first
        temp_file = self.download_dir / f".tmp_{filename}"
        final_file = self.download_dir / filename
        
        # Verify paths are within download directory
        if not temp_file.resolve().is_relative_to(self.download_dir.resolve()):
            raise ValueError(f"Path traversal detected in temp file: {temp_file}")
        if not final_file.resolve().is_relative_to(self.download_dir.resolve()):
            raise ValueError(f"Path traversal detected in final file: {final_file}")
        
        try:
            file_size = 0
            async with aiofiles.open(temp_file, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    await f.write(chunk)
                    file_size += len(chunk)
            
            # Move to final location
            os.rename(temp_file, final_file)
            
            download_time = time.time() - start_time
            
            return DownloadResult(
                success=True,
                file_path=str(final_file),
                source_used=source.name,
                file_size=file_size,
                download_time=download_time
            )
        
        except Exception as e:
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()
            
            return DownloadResult(
                success=False,
                error=f"Failed to save file: {str(e)}",
                source_used=source.name
            )
    
    async def download(self, identifier: str, metadata: Optional[Dict] = None) -> DownloadResult:
        """
        Download a paper using all available sources.
        
        Args:
            identifier: ArXiv ID, DOI, URL, or paper title
            metadata: Optional metadata dict with title, authors, etc.
        
        Returns:
            DownloadResult with success status and file path
        """
        # Get prioritized sources
        sources = get_download_sources(identifier)
        
        if not sources:
            return DownloadResult(
                success=False,
                error="No download sources available for this identifier"
            )
        
        self.logger.info(f"Found {len(sources)} potential sources for: {identifier}")
        
        # Get session
        session = await self._get_session()
        
        # Try each source in priority order
        last_error = None
        for source in sources:
            # Skip publisher sources if no institutional auth (for now)
            if source.requires_auth:
                self.logger.info(f"Skipping {source.name} (institutional auth not fully integrated)")
                continue
            
            try:
                result = await self._try_download_source(source, identifier, session)
                
                if result and result.success:
                    self.logger.info(f"Successfully downloaded from {source.name}: {result.file_path}")
                    return result
                
                if result:
                    last_error = result.error
                    self.logger.warning(f"Failed: {result.error}")
                else:
                    self.logger.warning(f"Failed: {source.name} returned None")
                    
            except Exception as e:
                self.logger.warning(f"Exception with {source.name}: {str(e)}")
                last_error = str(e)
        
        # All sources failed
        return DownloadResult(
            success=False,
            error=f"All sources failed. Last error: {last_error}"
        )
    
    async def download_multiple(self, identifiers: List[str]) -> List[Tuple[str, DownloadResult]]:
        """Download multiple papers concurrently."""
        # Limit concurrent downloads
        semaphore = asyncio.Semaphore(3)
        
        async def download_with_semaphore(identifier: str) -> Tuple[str, DownloadResult]:
            async with semaphore:
                result = await self.download(identifier)
                return identifier, result
        
        tasks = [download_with_semaphore(identifier) for identifier in identifiers]
        return await asyncio.gather(*tasks)


# Synchronous wrapper for backward compatibility
class Downloader:
    """Sync wrapper for the async downloader."""
    
    def __init__(self, download_dir: str = "downloads"):
        self.async_downloader = AcademicDownloader(download_dir)

    def download(self, identifier: str, metadata: Optional[Dict] = None) -> DownloadResult:
        """Sync version of download."""
        from core.utils.async_compat import run_sync
        return run_sync(self.async_downloader.download(identifier, metadata))

    def close(self):
        """Close the downloader."""
        from core.utils.async_compat import run_sync
        run_sync(self.async_downloader.close())