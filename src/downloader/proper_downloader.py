#!/usr/bin/env python3
"""
Proper Academic Downloader
==========================

Uses ONLY working implementations:
1. Real open access sources (ArXiv, SSRN, HAL, bioRxiv, PMC)
2. Existing institutional authentication system (IEEE, SIAM via Shibboleth)
3. NO placeholder implementations

This is the honest, working system.
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Async imports
import aiohttp
import aiofiles

# Import real open access sources
from .open_access_sources import get_open_access_sources, SourceInterface

# Import existing institutional system
try:
    from publishers import publisher_registry, AuthenticationConfig
    from secure_credential_manager import get_credential_manager
    INSTITUTIONAL_AVAILABLE = True
except ImportError as e:
    INSTITUTIONAL_AVAILABLE = False
    logging.warning(f"Institutional system not available: {e}")

logger = logging.getLogger(__name__)


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


class OpenAccessDownloader:
    """Downloads from legitimate open access sources."""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get HTTP session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            )
        return self.session
    
    async def close(self):
        """Close session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def download(self, identifier: str) -> DownloadResult:
        """Download from open access sources."""
        start_time = time.time()
        
        # Get applicable sources
        sources = get_open_access_sources(identifier)
        if not sources:
            return DownloadResult(
                success=False,
                error="No open access sources found for this identifier"
            )
        
        logger.info(f"Found {len(sources)} open access sources for: {identifier}")
        session = await self._get_session()
        
        # Try each source
        for source in sources:
            try:
                # Rate limiting
                await asyncio.sleep(source.info.rate_limit)
                
                logger.info(f"Trying {source.info.name}...")
                pdf_url = await source.get_pdf_url(identifier, session)
                
                if pdf_url:
                    logger.info(f"Found PDF URL: {pdf_url}")
                    result = await self._download_pdf(pdf_url, identifier, source.info.name)
                    
                    if result.success:
                        result.download_time = time.time() - start_time
                        return result
                    else:
                        logger.warning(f"Failed to download from {source.info.name}: {result.error}")
                else:
                    logger.warning(f"{source.info.name}: No PDF URL found")
                    
            except Exception as e:
                logger.warning(f"{source.info.name} error: {str(e)}")
        
        return DownloadResult(
            success=False,
            error="All open access sources failed",
            download_time=time.time() - start_time
        )
    
    async def _download_pdf(self, pdf_url: str, identifier: str, source_name: str) -> DownloadResult:
        """Download PDF from URL."""
        try:
            session = await self._get_session()
            async with session.get(pdf_url) as response:
                if response.status == 200:
                    # Generate filename
                    filename = self._generate_filename(identifier, source_name, response)
                    file_path = self.download_dir / filename
                    
                    # Download
                    file_size = 0
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            file_size += len(chunk)
                    
                    return DownloadResult(
                        success=True,
                        file_path=str(file_path),
                        source_used=source_name,
                        file_size=file_size
                    )
                else:
                    return DownloadResult(
                        success=False,
                        error=f"HTTP {response.status}",
                        source_used=source_name
                    )
        
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source_used=source_name
            )
    
    def _generate_filename(self, identifier: str, source_name: str, response) -> str:
        """Generate filename for downloaded paper."""
        import hashlib
        
        # Try to extract from Content-Disposition
        content_disp = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disp:
            import re
            match = re.search(r'filename="?([^"]+)"?', content_disp)
            if match:
                return match.group(1)
        
        # Extract meaningful parts from identifier
        if 'arxiv' in source_name.lower():
            import re
            match = re.search(r'(\d{4}\.\d{4,5})', identifier)
            if match:
                return f"arxiv_{match.group(1)}.pdf"
        
        # Fallback: source + hash
        id_hash = hashlib.sha256(identifier.encode()).hexdigest()[:8]
        return f"{source_name.lower()}_{id_hash}.pdf"


class InstitutionalDownloader:
    """Uses existing institutional authentication system."""
    
    def __init__(self):
        if not INSTITUTIONAL_AVAILABLE:
            raise ImportError("Institutional system not available")
        
        self.credential_manager = get_credential_manager()
        self._register_publishers()
    
    def _register_publishers(self):
        """Register working publishers."""
        self.working_publishers = {}
        
        # IEEE - confirmed working
        try:
            from publishers.ieee_publisher import IEEEPublisher
            publisher_registry.register('ieee', IEEEPublisher)
            self.working_publishers['ieee'] = {
                'class': IEEEPublisher,
                'patterns': ['ieee', '10.1109', 'ieeexplore.ieee.org'],
                'auth_method': 'shibboleth'  # Uses Playwright automation
            }
            logger.info("✅ IEEE publisher registered")
        except ImportError:
            logger.warning("IEEE publisher not available")
        
        # SIAM - confirmed working  
        try:
            from publishers.siam_publisher import SIAMPublisher
            publisher_registry.register('siam', SIAMPublisher)
            self.working_publishers['siam'] = {
                'class': SIAMPublisher,
                'patterns': ['siam', 'epubs.siam.org', '10.1137'],  # Added DOI pattern
                'auth_method': 'institutional'
            }
            logger.info("✅ SIAM publisher registered")
        except ImportError:
            logger.warning("SIAM publisher not available")
        
        # Springer - basic implementation ready
        try:
            from publishers.springer_publisher import SpringerPublisher
            publisher_registry.register('springer', SpringerPublisher)
            self.working_publishers['springer'] = {
                'class': SpringerPublisher,
                'patterns': ['springer', 'link.springer.com', '10.1007'],
                'auth_method': 'shibboleth'  # Requires browser automation
            }
            logger.info("✅ Springer publisher registered")
        except ImportError:
            logger.warning("Springer publisher not available")
    
    def can_handle(self, identifier: str) -> Optional[str]:
        """Check if we can handle this identifier."""
        identifier_lower = identifier.lower()
        
        for pub_name, pub_info in self.working_publishers.items():
            for pattern in pub_info['patterns']:
                if pattern in identifier_lower:
                    return pub_name
        return None
    
    def download(self, identifier: str, output_dir: Path) -> DownloadResult:
        """Download using institutional access."""
        start_time = time.time()
        
        publisher_name = self.can_handle(identifier)
        if not publisher_name:
            return DownloadResult(
                success=False,
                error="No suitable publisher found"
            )
        
        logger.info(f"Using {publisher_name} for: {identifier}")
        
        try:
            # Get authentication config
            auth_config = self._get_auth_config(publisher_name)
            
            # Get publisher instance
            publisher = publisher_registry.get_publisher(publisher_name, auth_config)
            
            # Authenticate (this uses the existing Shibboleth/SAML system)
            if not publisher.authenticate():
                return DownloadResult(
                    success=False,
                    error=f"{publisher_name}: Institutional authentication failed",
                    source_used=publisher_name
                )
            
            # Generate output path
            import hashlib
            safe_id = hashlib.sha256(identifier.encode()).hexdigest()[:8]
            output_path = output_dir / f"{publisher_name}_{safe_id}.pdf"
            
            # Download using publisher's method
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
    
    def _get_auth_config(self, publisher: str) -> AuthenticationConfig:
        """Get authentication config for publisher."""
        # Get ETH credentials
        eth_username = (self.credential_manager.get_credential('eth_username') or 
                       os.environ.get('ETH_USERNAME', ''))
        eth_password = (self.credential_manager.get_credential('eth_password') or 
                       os.environ.get('ETH_PASSWORD', ''))
        
        return AuthenticationConfig(
            username=eth_username,
            password=eth_password,
            institutional_login='eth'
        )


class ProperAcademicDownloader:
    """
    The honest academic downloader that only uses working implementations.
    
    1. Open access sources: ArXiv, SSRN, HAL, bioRxiv, PMC (real implementations)
    2. Institutional publishers: IEEE, SIAM (using existing Shibboleth authentication)
    3. No placeholders, no fake sources
    """
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Initialize open access downloader
        self.open_access = OpenAccessDownloader(download_dir)
        
        # Initialize institutional downloader if available
        try:
            self.institutional = InstitutionalDownloader()
            self.institutional_available = True
            logger.info(f"Institutional publishers available: {list(self.institutional.working_publishers.keys())}")
        except ImportError:
            self.institutional_available = False
            logger.warning("Institutional downloads not available")
    
    async def download(self, identifier: str) -> DownloadResult:
        """Download using the best available method."""
        
        # 1. Check if we have institutional access for this identifier first
        institutional_publisher = None
        if self.institutional_available:
            institutional_publisher = self.institutional.can_handle(identifier)
        
        # 2. Try institutional first if available (often more reliable for paywalled papers)
        if institutional_publisher:
            logger.info(f"Detected {institutional_publisher} paper, trying institutional access")
            
            # Run sync institutional download in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.institutional.download,
                identifier,
                self.download_dir
            )
            
            if result.success:
                logger.info(f"✅ Downloaded via institutional access: {institutional_publisher}")
                return result
            else:
                logger.warning(f"Institutional access failed: {result.error}")
        
        # 3. Try open access as fallback (or first choice if no institutional match)
        logger.info(f"Checking open access sources for: {identifier}")
        result = await self.open_access.download(identifier)
        
        if result.success:
            logger.info(f"✅ Downloaded from {result.source_used}")
            return result
        
        logger.info(f"Open access also failed: {result.error}")
        
        # 4. All methods failed
        error_msg = "No working download method found for this identifier"
        if institutional_publisher:
            error_msg += f" (tried {institutional_publisher} + open access)"
        
        return DownloadResult(
            success=False,
            error=error_msg
        )
    
    async def close(self):
        """Close all connections."""
        await self.open_access.close()


# Sync wrapper
class Downloader:
    """Synchronous wrapper for the proper downloader."""
    
    def __init__(self, download_dir: str = "downloads"):
        self.async_downloader = ProperAcademicDownloader(download_dir)
    
    def download(self, identifier: str) -> DownloadResult:
        """Sync download."""
        from src.core.utils.async_compat import run_sync
        return run_sync(self.async_downloader.download(identifier))

    def close(self):
        """Close downloader."""
        from src.core.utils.async_compat import run_sync
        run_sync(self.async_downloader.close())