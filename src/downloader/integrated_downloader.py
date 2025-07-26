#!/usr/bin/env python3
"""
Integrated Academic Downloader
===============================

Proper integration of existing publisher authentication system with async open access downloads.
Uses the sophisticated existing infrastructure instead of rebuilding it.
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Async imports for open access sources
import aiohttp
import aiofiles

# Existing sophisticated system imports
try:
    from publishers import publisher_registry, AuthenticationConfig, DownloadResult as PublisherDownloadResult
    from secure_credential_manager import get_credential_manager
    PUBLISHER_SYSTEM_AVAILABLE = True
except ImportError as e:
    PUBLISHER_SYSTEM_AVAILABLE = False
    print(f"Publisher system not available: {e}")

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Unified download result for both async and sync downloads."""
    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    source_used: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    file_size: int = 0
    download_time: float = 0.0


class OpenAccessDownloader:
    """Async downloader for open access sources only."""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None:
            async with self._session_lock:
                if self.session is None:
                    timeout = aiohttp.ClientTimeout(total=60, connect=10)
                    connector = aiohttp.TCPConnector(limit=10, limit_per_host=3, ttl_dns_cache=300)
                    
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
    
    async def download_arxiv(self, arxiv_id: str) -> DownloadResult:
        """Download from ArXiv."""
        start_time = time.time()
        
        try:
            # Extract clean ArXiv ID
            import re
            match = re.search(r'(\d{4}\.\d{4,5})', arxiv_id)
            if not match:
                return DownloadResult(success=False, error="Invalid ArXiv ID format")
            
            clean_id = match.group(1)
            url = f"https://arxiv.org/pdf/{clean_id}.pdf"
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    # Generate filename
                    filename = f"{clean_id}v{await self._get_arxiv_version(response)}.pdf"
                    file_path = self.download_dir / filename
                    
                    # Download file
                    file_size = 0
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            file_size += len(chunk)
                    
                    download_time = time.time() - start_time
                    
                    return DownloadResult(
                        success=True,
                        file_path=str(file_path),
                        source_used="ArXiv",
                        file_size=file_size,
                        download_time=download_time
                    )
                else:
                    return DownloadResult(success=False, error=f"ArXiv: HTTP {response.status}")
                    
        except Exception as e:
            return DownloadResult(success=False, error=f"ArXiv: {str(e)}")
    
    async def _get_arxiv_version(self, response: aiohttp.ClientResponse) -> str:
        """Extract version from ArXiv response."""
        # Try to get version from URL or default to v1
        url = str(response.url)
        import re
        version_match = re.search(r'v(\d+)', url)
        return version_match.group(1) if version_match else "2"  # Default assumption


class InstitutionalDownloader:
    """Uses existing publisher system for institutional access."""
    
    def __init__(self):
        if not PUBLISHER_SYSTEM_AVAILABLE:
            raise ImportError("Publisher system not available")
        
        self.credential_manager = get_credential_manager()
        self._setup_publishers()
    
    def _setup_publishers(self):
        """Setup available publishers with credentials."""
        self.available_publishers = {}
        
        # Register existing publishers
        try:
            from publishers.ieee_publisher import IEEEPublisher
            publisher_registry.register('ieee', IEEEPublisher)
            self.available_publishers['ieee'] = {
                'class': IEEEPublisher,
                'patterns': ['ieee', '10.1109']
            }
        except ImportError:
            pass
        
        try:
            from publishers.siam_publisher import SIAMPublisher
            publisher_registry.register('siam', SIAMPublisher)
            self.available_publishers['siam'] = {
                'class': SIAMPublisher, 
                'patterns': ['siam', 'epubs.siam.org']
            }
        except ImportError:
            pass
    
    def _get_auth_config(self, publisher: str) -> AuthenticationConfig:
        """Get authentication config for a publisher."""
        # Get ETH credentials
        eth_username = self.credential_manager.get_credential('eth_username') or os.environ.get('ETH_USERNAME', '')
        eth_password = self.credential_manager.get_credential('eth_password') or os.environ.get('ETH_PASSWORD', '')
        
        return AuthenticationConfig(
            username=eth_username,
            password=eth_password,
            institutional_login='eth'
        )
    
    def can_handle(self, identifier: str) -> Optional[str]:
        """Check if any publisher can handle this identifier."""
        identifier_lower = identifier.lower()
        
        for pub_name, pub_info in self.available_publishers.items():
            for pattern in pub_info['patterns']:
                if pattern in identifier_lower:
                    return pub_name
        return None
    
    def download(self, identifier: str, output_dir: Path) -> DownloadResult:
        """Download using appropriate publisher."""
        start_time = time.time()
        
        publisher_name = self.can_handle(identifier)
        if not publisher_name:
            return DownloadResult(success=False, error="No suitable publisher found")
        
        try:
            # Get publisher instance
            auth_config = self._get_auth_config(publisher_name)
            publisher = publisher_registry.get_publisher(publisher_name, auth_config)
            
            # Authenticate
            if not publisher.authenticate():
                return DownloadResult(
                    success=False, 
                    error=f"{publisher_name}: Authentication failed",
                    source_used=publisher_name
                )
            
            # Generate output path
            import hashlib
            safe_id = hashlib.sha256(identifier.encode()).hexdigest()[:8]
            output_path = output_dir / f"{publisher_name}_{safe_id}.pdf"
            
            # Download
            result = publisher.download_paper(identifier, output_path)
            
            download_time = time.time() - start_time
            
            if result.success:
                file_size = output_path.stat().st_size if output_path.exists() else 0
                return DownloadResult(
                    success=True,
                    file_path=str(result.file_path),
                    source_used=publisher_name,
                    file_size=file_size,
                    download_time=download_time
                )
            else:
                return DownloadResult(
                    success=False,
                    error=f"{publisher_name}: {result.error_message}",
                    source_used=publisher_name
                )
                
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"{publisher_name}: {str(e)}",
                source_used=publisher_name
            )


class IntegratedAcademicDownloader:
    """
    Integrated downloader using both async open access and existing publisher systems.
    This is the main interface that properly uses existing infrastructure.
    """
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Initialize subsystems
        self.open_access = OpenAccessDownloader(download_dir)
        
        try:
            self.institutional = InstitutionalDownloader()
            self.institutional_available = True
        except ImportError:
            self.institutional_available = False
            logger.warning("Institutional downloads not available")
    
    async def download(self, identifier: str) -> DownloadResult:
        """Download paper using appropriate method."""
        
        # 1. Try ArXiv first (fastest, most reliable)
        if self._is_arxiv(identifier):
            logger.info(f"Detected ArXiv paper: {identifier}")
            return await self.open_access.download_arxiv(identifier)
        
        # 2. Try institutional publishers if available
        if self.institutional_available:
            publisher = self.institutional.can_handle(identifier)
            if publisher:
                logger.info(f"Detected {publisher} paper: {identifier}")
                # Run sync method in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, 
                    self.institutional.download, 
                    identifier, 
                    self.download_dir
                )
        
        # 3. No suitable method found
        return DownloadResult(
            success=False,
            error=f"No download method available for: {identifier}"
        )
    
    def _is_arxiv(self, identifier: str) -> bool:
        """Check if identifier is ArXiv."""
        import re
        return bool(re.search(r'(arxiv|(\d{4}\.\d{4,5}))', identifier.lower()))
    
    async def close(self):
        """Close all connections."""
        await self.open_access.close()


# Synchronous wrapper for backward compatibility
class Downloader:
    """Sync wrapper for the integrated downloader."""
    
    def __init__(self, download_dir: str = "downloads"):
        self.async_downloader = IntegratedAcademicDownloader(download_dir)
        self._loop = None
    
    def _get_loop(self):
        """Get or create event loop."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop
    
    def download(self, identifier: str) -> DownloadResult:
        """Sync version of download."""
        loop = self._get_loop()
        return loop.run_until_complete(self.async_downloader.download(identifier))
    
    def close(self):
        """Close the downloader."""
        if self._loop:
            self._loop.run_until_complete(self.async_downloader.close())