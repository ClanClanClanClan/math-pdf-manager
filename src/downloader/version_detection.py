#!/usr/bin/env python3
"""
Version Detection for Academic Repositories
==========================================

Proper version detection for ArXiv, bioRxiv, medRxiv, and other repositories
that have versioning systems.
"""

import re
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class VersionInfo:
    """Information about paper version."""
    version: str
    date_submitted: Optional[str] = None
    date_updated: Optional[str] = None
    is_latest: bool = True
    available_versions: Optional[list] = None


class ArXivVersionDetector:
    """Detect and handle ArXiv versions."""
    
    @staticmethod
    def extract_version_from_url(url: str) -> Optional[str]:
        """Extract version from ArXiv URL."""
        # Pattern: https://arxiv.org/pdf/2301.07041v2.pdf
        match = re.search(r'(\d{4}\.\d{4,5})v(\d+)', url)
        if match:
            arxiv_id, version = match.groups()
            return f"v{version}"
        return None
    
    @staticmethod
    def extract_id_and_version(identifier: str) -> tuple[str, Optional[str]]:
        """Extract clean ArXiv ID and version number."""
        # Handle various formats:
        # - 2301.07041v2
        # - 2301.07041
        # - arxiv:2301.07041v2
        # - https://arxiv.org/abs/2301.07041v2
        
        # Extract the core ID and version
        match = re.search(r'(\d{4}\.\d{4,5})(?:v(\d+))?', identifier)
        if match:
            arxiv_id = match.group(1)
            version = match.group(2)
            return arxiv_id, f"v{version}" if version else None
        
        return identifier, None
    
    @staticmethod
    async def get_latest_version(arxiv_id: str, session: aiohttp.ClientSession) -> VersionInfo:
        """Get latest version info for an ArXiv paper."""
        try:
            # Check ArXiv API for version information
            api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            
            async with session.get(api_url) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    
                    # Extract version info from XML (simple parsing)
                    # Look for version pattern in the entry
                    version_match = re.search(r'v(\d+)', xml_content)
                    if version_match:
                        latest_version = f"v{version_match.group(1)}"
                        
                        # Extract submission date
                        date_match = re.search(r'<published>([^<]+)</published>', xml_content)
                        date_submitted = date_match.group(1) if date_match else None
                        
                        return VersionInfo(
                            version=latest_version,
                            date_submitted=date_submitted,
                            is_latest=True
                        )
            
            # Fallback if API doesn't work
            logger.warning(f"Could not get version info for {arxiv_id}")
            return VersionInfo(version="unknown")
            
        except Exception as e:
            logger.warning(f"ArXiv version detection failed for {arxiv_id}: {e}")
            return VersionInfo(version="unknown")
    
    @staticmethod
    def build_versioned_url(arxiv_id: str, version: Optional[str] = None) -> str:
        """Build ArXiv PDF URL with specific version."""
        base_url = f"https://arxiv.org/pdf/{arxiv_id}"
        if version and version.startswith('v'):
            return f"{base_url}{version}.pdf"
        else:
            return f"{base_url}.pdf"


class BioRxivVersionDetector:
    """Handle bioRxiv and medRxiv versions."""
    
    @staticmethod
    def extract_version_from_doi(doi: str) -> Optional[str]:
        """Extract version from bioRxiv/medRxiv DOI."""
        # Pattern: 10.1101/2023.01.01.523456
        # Sometimes includes version: 10.1101/2023.01.01.523456v1
        match = re.search(r'10\.1101/(\d{4}\.\d{2}\.\d{2}\.\d+)(?:v(\d+))?', doi)
        if match:
            paper_id = match.group(1)
            version = match.group(2)
            return f"v{version}" if version else "v1"  # Default to v1
        return None
    
    @staticmethod
    async def get_latest_version(paper_id: str, server: str, session: aiohttp.ClientSession) -> VersionInfo:
        """Get latest version for bioRxiv/medRxiv paper."""
        try:
            # Check the paper page for version information
            base_url = f"https://www.{server}.org/content/10.1101/{paper_id}"
            
            async with session.get(base_url) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Look for version information in HTML
                    version_matches = re.findall(r'v(\d+)', html)
                    if version_matches:
                        latest_version = f"v{max(int(v) for v in version_matches)}"
                        available_versions = [f"v{v}" for v in sorted(set(version_matches))]
                        
                        return VersionInfo(
                            version=latest_version,
                            is_latest=True,
                            available_versions=available_versions
                        )
            
            # Fallback
            return VersionInfo(version="v1")
            
        except Exception as e:
            logger.warning(f"{server} version detection failed for {paper_id}: {e}")
            return VersionInfo(version="v1")


class VersionAwareDownloader:
    """Downloader that handles versions properly."""
    
    def __init__(self):
        self.arxiv_detector = ArXivVersionDetector()
        self.biorxiv_detector = BioRxivVersionDetector()
    
    async def get_best_download_url(self, identifier: str, session: aiohttp.ClientSession) -> tuple[str, VersionInfo]:
        """Get the best download URL with version information."""
        
        # ArXiv papers
        if re.search(r'\d{4}\.\d{4,5}', identifier):
            arxiv_id, requested_version = self.arxiv_detector.extract_id_and_version(identifier)
            
            if requested_version:
                # User requested specific version
                url = self.arxiv_detector.build_versioned_url(arxiv_id, requested_version)
                version_info = VersionInfo(version=requested_version, is_latest=False)
            else:
                # Get latest version
                version_info = await self.arxiv_detector.get_latest_version(arxiv_id, session)
                url = self.arxiv_detector.build_versioned_url(arxiv_id, version_info.version)
            
            return url, version_info
        
        # bioRxiv/medRxiv papers
        elif '10.1101' in identifier:
            server = 'biorxiv' if 'biorxiv' in identifier.lower() else 'medrxiv'
            match = re.search(r'10\.1101/(\d{4}\.\d{2}\.\d{2}\.\d+)', identifier)
            
            if match:
                paper_id = match.group(1)
                version_info = await self.biorxiv_detector.get_latest_version(paper_id, server, session)
                url = f"https://www.{server}.org/content/10.1101/{paper_id}{version_info.version}.full.pdf"
                return url, version_info
        
        # Fallback - no version detection
        return identifier, VersionInfo(version="unknown")
    
    def generate_filename_with_version(self, identifier: str, version_info: VersionInfo, source_name: str) -> str:
        """Generate filename that includes version information."""
        import hashlib
        
        # ArXiv papers
        if re.search(r'\d{4}\.\d{4,5}', identifier):
            arxiv_id, _ = self.arxiv_detector.extract_id_and_version(identifier)
            return f"arxiv_{arxiv_id}_{version_info.version}.pdf"
        
        # bioRxiv/medRxiv papers  
        elif '10.1101' in identifier:
            match = re.search(r'10\.1101/(\d{4}\.\d{2}\.\d{2}\.\d+)', identifier)
            if match:
                paper_id = match.group(1).replace('.', '_')
                return f"{source_name.lower()}_{paper_id}_{version_info.version}.pdf"
        
        # Fallback
        id_hash = hashlib.sha256(identifier.encode()).hexdigest()[:8]
        return f"{source_name.lower()}_{id_hash}_{version_info.version}.pdf"


# Example usage and testing
async def test_version_detection():
    """Test version detection with various identifiers."""
    test_cases = [
        "2301.07041",           # Latest version
        "2301.07041v1",         # Specific version
        "arxiv:2301.07041v2",   # With prefix
        "10.1101/2023.01.01.523456",  # bioRxiv
        "10.1101/2023.01.01.523456v2", # bioRxiv with version
    ]
    
    detector = VersionAwareDownloader()
    
    async with aiohttp.ClientSession() as session:
        for identifier in test_cases:
            print(f"\nTesting: {identifier}")
            url, version_info = await detector.get_best_download_url(identifier, session)
            filename = detector.generate_filename_with_version(identifier, version_info, "test")
            
            print(f"  URL: {url}")
            print(f"  Version: {version_info.version}")
            print(f"  Filename: {filename}")


if __name__ == "__main__":
    asyncio.run(test_version_detection())