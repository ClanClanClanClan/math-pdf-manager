#!/usr/bin/env python3
"""
Universal Paper Downloader Framework
Comprehensive system for downloading papers from all major publishers and alternative sources.
"""

import asyncio
import aiohttp
import re
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Union, Any
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote

# Import secure session creator
try:
    from .credentials import create_secure_session
except ImportError:
    # Fallback if credentials module not available
    def create_secure_session(**kwargs):
        return aiohttp.ClientSession(**kwargs)
import random
import hashlib

logger = logging.getLogger(__name__)

@dataclass 
class DownloadResult:
    """Result from download attempt"""
    success: bool
    pdf_data: Optional[bytes] = None
    source: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    download_time: float = 0.0
    file_size: int = 0

@dataclass
class SearchResult:
    """Result from search operation"""
    title: str
    authors: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    url: Optional[str] = None
    year: Optional[int] = None
    source: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class DownloadStrategy(ABC):
    """Abstract base for download strategies"""
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        pass
    
    @abstractmethod 
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        pass
    
    @abstractmethod
    def can_handle(self, query: str, **kwargs) -> float:
        """Return confidence score (0-1) for handling this query"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

class SpringerDownloader(DownloadStrategy):
    """Springer Nature download with institutional access"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.session = None
        self.base_urls = [
            "https://link.springer.com",
            "https://rd.springer.com", 
            "https://springerlink.com"
        ]
    
    async def authenticate(self):
        """Authenticate with Springer via institutional access"""
        if not self.session:
            self.session = create_secure_session()
        
        # Implementation depends on your institution's SSO
        # This is a template - adapt for your specific setup
        auth_url = "https://link.springer.com/openurl"  
        
        try:
            # Your specific authentication flow here
            # Could be Shibboleth, SAML, or direct credentials
            pass
        except Exception as e:
            logger.error(f"Springer authentication failed: {e}")
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        await self.authenticate()
        
        search_url = "https://link.springer.com/search"
        params = {
            'query': query,
            'search-within': 'Journal',
            'facet-content-type': 'Article'
        }
        
        try:
            async with self.session.get(search_url, params=params) as response:
                html = await response.text()
                return self._parse_springer_search(html)
        except Exception as e:
            logger.error(f"Springer search failed: {e}")
            return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        await self.authenticate()
        
        if isinstance(paper_info, str):
            # Assume DOI
            pdf_url = f"https://link.springer.com/content/pdf/{paper_info}.pdf"
        else:
            pdf_url = paper_info.url.replace('/article/', '/content/pdf/').replace('/', '.pdf', 1) + '.pdf'
        
        try:
            async with self.session.get(pdf_url) as response:
                if response.status == 200:
                    pdf_data = await response.read()
                    return DownloadResult(
                        success=True,
                        pdf_data=pdf_data,
                        source="springer",
                        url=pdf_url,
                        download_time=time.time() - start_time,
                        file_size=len(pdf_data)
                    )
                else:
                    return DownloadResult(
                        success=False,
                        error=f"HTTP {response.status}",
                        source="springer",
                        download_time=time.time() - start_time
                    )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="springer",
                download_time=time.time() - start_time
            )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'springer' in query.lower() or 'doi.org' in query:
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "springer"
    
    def _parse_springer_search(self, html: str) -> List[SearchResult]:
        # Parse Springer search results HTML
        results = []
        # Implementation depends on Springer's current HTML structure
        return results

class ElsevierDownloader(DownloadStrategy):
    """Elsevier/ScienceDirect downloader"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.session = None
        self.api_key = credentials.get('api_key')
    
    async def authenticate(self):
        if not self.session:
            self.session = create_secure_session()
            
        # Elsevier institutional authentication
        # Implement based on your institution's access method
        pass
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        if self.api_key:
            return await self._api_search(query)
        else:
            return await self._web_search(query)
    
    async def _api_search(self, query: str) -> List[SearchResult]:
        """Search using Elsevier's Scopus API"""
        url = "https://api.elsevier.com/content/search/scopus"
        headers = {'X-ELS-APIKey': self.api_key}
        params = {
            'query': query,
            'count': 25,
            'start': 0
        }
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_scopus_results(data)
        except Exception as e:
            logger.error(f"Elsevier API search failed: {e}")
        
        return []
    
    async def _web_search(self, query: str) -> List[SearchResult]:
        """Fallback web search"""
        # Implement ScienceDirect web search
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        await self.authenticate()
        
        # Elsevier download logic
        # This would involve navigating their paywall system
        # Using institutional credentials
        
        return DownloadResult(
            success=False,
            error="Not implemented",
            source="elsevier",
            download_time=time.time() - start_time
        )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'sciencedirect' in query.lower() or 'elsevier' in query.lower():
            return 0.9
        return 0.2
    
    @property
    def name(self) -> str:
        return "elsevier"
    
    def _parse_scopus_results(self, data: Dict) -> List[SearchResult]:
        results = []
        entries = data.get('search-results', {}).get('entry', [])
        
        for entry in entries:
            result = SearchResult(
                title=entry.get('dc:title', ''),
                authors=[],  # Parse from entry
                doi=entry.get('prism:doi'),
                source="elsevier",
                confidence=0.8
            )
            results.append(result)
        
        return results

class SciHubDownloader(DownloadStrategy):
    """Sci-Hub integration"""
    
    def __init__(self):
        self.mirrors = [
            "https://sci-hub.se/",
            "https://sci-hub.st/",
            "https://sci-hub.ru/", 
            "https://sci-hub.wf/",
            "https://sci-hub.shop/",
        ]
        self.active_mirrors = []
        self.session = None
        self.last_mirror_check = 0
    
    async def _check_mirrors(self):
        """Check which mirrors are currently active"""
        if time.time() - self.last_mirror_check < 3600:  # Check every hour
            return
            
        if not self.session:
            self.session = create_secure_session(timeout=aiohttp.ClientTimeout(total=10))
        
        self.active_mirrors = []
        
        for mirror in self.mirrors:
            try:
                async with self.session.get(mirror) as response:
                    if response.status == 200:
                        self.active_mirrors.append(mirror)
                        logger.info(f"Active Sci-Hub mirror: {mirror}")
            except Exception as e:
                logger.debug(f"Mirror {mirror} not accessible: {e}")
        
        self.last_mirror_check = time.time()
        
        if not self.active_mirrors:
            logger.warning("No active Sci-Hub mirrors found")
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Sci-Hub doesn't have traditional search, return dummy result for DOI"""
        if self._looks_like_doi(query):
            return [SearchResult(
                title=f"Paper with DOI: {query}",
                doi=query,
                source="sci-hub",
                confidence=0.7
            )]
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        await self._check_mirrors()
        
        if not self.active_mirrors:
            return DownloadResult(
                success=False,
                error="No active Sci-Hub mirrors available",
                source="sci-hub",
                download_time=time.time() - start_time
            )
        
        doi = paper_info if isinstance(paper_info, str) else paper_info.doi
        if not doi:
            return DownloadResult(
                success=False,
                error="No DOI provided",
                source="sci-hub",
                download_time=time.time() - start_time
            )
        
        # Try each active mirror
        for mirror in self.active_mirrors:
            try:
                result = await self._download_from_mirror(mirror, doi)
                if result.success:
                    result.download_time = time.time() - start_time
                    return result
                    
                # Rate limiting between attempts
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.debug(f"Mirror {mirror} failed for DOI {doi}: {e}")
                continue
        
        return DownloadResult(
            success=False,
            error="All Sci-Hub mirrors failed",
            source="sci-hub",
            download_time=time.time() - start_time
        )
    
    async def _download_from_mirror(self, mirror: str, doi: str) -> DownloadResult:
        """Download from specific Sci-Hub mirror"""
        if not self.session:
            self.session = create_secure_session()
        
        # Clean DOI
        clean_doi = doi.replace('doi:', '').replace('https://doi.org/', '')
        url = urljoin(mirror, clean_doi)
        
        try:
            # Get the Sci-Hub page
            async with self.session.get(url) as response:
                if response.status != 200:
                    return DownloadResult(success=False, error=f"HTTP {response.status}")
                
                html = await response.text()
                pdf_url = self._extract_pdf_url(html, mirror)
                
                if not pdf_url:
                    return DownloadResult(success=False, error="PDF URL not found")
                
                # Download the PDF
                async with self.session.get(pdf_url) as pdf_response:
                    if pdf_response.status == 200:
                        pdf_data = await pdf_response.read()
                        
                        # Verify it's actually a PDF
                        if pdf_data.startswith(b'%PDF'):
                            return DownloadResult(
                                success=True,
                                pdf_data=pdf_data,
                                source="sci-hub",
                                url=pdf_url,
                                file_size=len(pdf_data)
                            )
                        else:
                            return DownloadResult(success=False, error="Downloaded file is not a PDF")
                    else:
                        return DownloadResult(success=False, error=f"PDF download failed: HTTP {pdf_response.status}")
        
        except Exception as e:
            return DownloadResult(success=False, error=str(e))
    
    def _extract_pdf_url(self, html: str, base_url: str) -> Optional[str]:
        """Extract PDF URL from Sci-Hub page HTML"""
        # Common patterns for Sci-Hub PDF links
        patterns = [
            r'<iframe[^>]+src=["\'](.*?\.pdf.*?)["\']',
            r'<embed[^>]+src=["\'](.*?\.pdf.*?)["\']',
            r'<a[^>]+href=["\'](.*?\.pdf.*?)["\'][^>]*>(?:download|pdf)',
            r'location\.href\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                pdf_url = matches[0]
                if pdf_url.startswith('//'):
                    pdf_url = 'https:' + pdf_url
                elif pdf_url.startswith('/'):
                    pdf_url = urljoin(base_url, pdf_url)
                elif not pdf_url.startswith('http'):
                    pdf_url = urljoin(base_url, pdf_url)
                
                return pdf_url
        
        return None
    
    def _looks_like_doi(self, text: str) -> bool:
        """Check if text looks like a DOI"""
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        return bool(re.search(doi_pattern, text))
    
    def can_handle(self, query: str, **kwargs) -> float:
        if self._looks_like_doi(query):
            return 0.8
        return 0.1
    
    @property
    def name(self) -> str:
        return "sci-hub"

class AnnaArchiveDownloader(DownloadStrategy):
    """Anna's Archive integration"""
    
    def __init__(self):
        self.base_urls = [
            "https://annas-archive.org/",
            "https://annas-archive.li/",
            "https://annas-archive.se/"
        ]
        self.session = None
        self.active_base_url = None
    
    async def _find_active_mirror(self):
        """Find an active Anna's Archive mirror"""
        if not self.session:
            self.session = create_secure_session(timeout=aiohttp.ClientTimeout(total=15))
        
        for base_url in self.base_urls:
            try:
                async with self.session.get(base_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        self.active_base_url = base_url
                        logger.info(f"Active Anna's Archive mirror: {base_url}")
                        return True
            except Exception as e:
                logger.debug(f"Mirror {base_url} not accessible: {e}")
                continue
        
        return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        if not self.active_base_url:
            if not await self._find_active_mirror():
                logger.error("No active Anna's Archive mirror found")
                return []
        
        try:
            search_url = urljoin(self.active_base_url, 'search')
            params = {
                'q': query,
                'ext': 'pdf',  # Focus on PDFs
                'sort': 'relevance'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            async with self.session.get(search_url, params=params, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_anna_search(html)
        except Exception as e:
            logger.error(f"Anna's Archive search failed: {e}")
            self.active_base_url = None  # Reset to try another mirror next time
        
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        
        if not self.session:
            self.session = create_secure_session()
        
        # Extract URL from search result
        if isinstance(paper_info, SearchResult) and paper_info.url:
            item_url = paper_info.url
        else:
            return DownloadResult(
                success=False,
                error="No URL available for Anna's Archive download",
                source="anna-archive",
                download_time=time.time() - start_time
            )
        
        try:
            # First, get the item page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            async with self.session.get(item_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    download_links = self._extract_download_links(html)
                    
                    # Try each download link
                    for link in download_links:
                        try:
                            result = await self._download_from_link(link, start_time)
                            if result.success:
                                return result
                            
                            # Rate limiting between attempts
                            await asyncio.sleep(random.uniform(2, 4))
                            
                        except Exception as e:
                            logger.debug(f"Download link {link} failed: {e}")
                            continue
            
            return DownloadResult(
                success=False,
                error="All download links failed",
                source="anna-archive",
                download_time=time.time() - start_time
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="anna-archive",
                download_time=time.time() - start_time
            )
    
    async def _download_from_link(self, download_url: str, start_time: float) -> DownloadResult:
        """Download from a specific link"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*',
                'Referer': self.active_base_url or self.base_urls[0]
            }
            
            async with self.session.get(download_url, headers=headers, allow_redirects=True) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower() or download_url.endswith('.pdf'):
                        pdf_data = await response.read()
                        if pdf_data.startswith(b'%PDF'):
                            return DownloadResult(
                                success=True,
                                pdf_data=pdf_data,
                                source="anna-archive",
                                url=download_url,
                                download_time=time.time() - start_time,
                                file_size=len(pdf_data)
                            )
        except Exception as e:
            logger.debug(f"Download from {download_url} failed: {e}")
        
        return DownloadResult(
            success=False,
            error="Download failed",
            source="anna-archive"
        )
    
    def _extract_download_links(self, html: str) -> List[str]:
        """Extract download links from Anna's Archive item page"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        download_links = []
        
        # Look for download buttons/links
        download_patterns = [
            {'class': re.compile(r'download|mirror')},
            {'href': re.compile(r'download|get|fetch|retrieve')},
            {'text': re.compile(r'Download|Mirror|Get', re.IGNORECASE)}
        ]
        
        for pattern in download_patterns:
            links = soup.find_all('a', pattern)
            for link in links:
                href = link.get('href')
                if href:
                    if href.startswith('/'):
                        href = urljoin(self.active_base_url, href)
                    elif not href.startswith('http'):
                        href = urljoin(self.active_base_url, href)
                    
                    if href not in download_links:
                        download_links.append(href)
        
        # Also look for external mirror links (Library Genesis, Z-Library, etc.)
        external_patterns = [
            re.compile(r'libgen|library\.lol|gen\.lib\.rus\.ec', re.IGNORECASE),
            re.compile(r'z-lib|zlibrary|b-ok', re.IGNORECASE),
            re.compile(r'ipfs\.io', re.IGNORECASE)
        ]
        
        for pattern in external_patterns:
            links = soup.find_all('a', href=pattern)
            for link in links:
                href = link.get('href')
                if href and href not in download_links:
                    download_links.append(href)
        
        return download_links
    
    def can_handle(self, query: str, **kwargs) -> float:
        # Good for general academic content
        return 0.5
    
    @property
    def name(self) -> str:
        return "anna-archive"
    
    def _parse_anna_search(self, html: str) -> List[SearchResult]:
        """Parse Anna's Archive search results - FIXED VERSION"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find search result items
        items = soup.find_all('div', class_='mb-4') or soup.find_all('div', class_='search-result-item')
        
        for item in items[:20]:
            try:
                # Extract title
                title_elem = item.find('h3') or item.find('a', class_='title') or item.find('div', class_='font-bold')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # CRITICAL FIX: Filter out non-content results
                if (title.lower().startswith('search settings') or 
                    'settings' in title.lower() or 
                    title.strip() == '' or
                    len(title) < 10):
                    continue
                
                # Extract URL - look for links to actual content
                url = None
                link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
                if not link_elem:
                    # Look for any link in the item that goes to md5 or content
                    link_elem = item.find('a', href=re.compile(r'/(md5|record)/'))
                
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        url = urljoin(self.active_base_url, href)
                    else:
                        url = href
                
                # CRITICAL FIX: Only include results with valid URLs
                if not url:
                    continue
                    
                # Additional validation: URL should point to actual content
                if not any(pattern in url for pattern in ['/md5/', '/record/', '/book/']):
                    continue
                
                # Extract metadata
                metadata = {}
                
                # Look for file type (updated to use 'string' instead of deprecated 'text')
                type_elem = item.find(string=re.compile(r'PDF|EPUB|DJVU', re.IGNORECASE))
                if type_elem:
                    metadata['file_type'] = type_elem.strip()
                
                # Look for file size (updated to use 'string' instead of deprecated 'text')
                size_elem = item.find(string=re.compile(r'\d+\.?\d*\s*(MB|KB|GB)', re.IGNORECASE))
                if size_elem:
                    metadata['file_size'] = size_elem.strip()
                
                # Extract authors (if available) (updated to use 'string' instead of deprecated 'text')
                authors = []
                author_elem = item.find('div', string=re.compile(r'Author|by', re.IGNORECASE))
                if author_elem:
                    author_text = author_elem.get_text()
                    # Try to extract author names
                    author_match = re.search(r'(?:Author|by):?\s*(.+)', author_text, re.IGNORECASE)
                    if author_match:
                        author_names = author_match.group(1)
                        authors = [a.strip() for a in re.split(r'[,;]|\s+and\s+', author_names) if a.strip()]
                
                # Only add results that have both title and URL
                if title and url:
                    results.append(SearchResult(
                        title=title,
                        authors=authors,
                        url=url,
                        source="anna-archive",
                        confidence=0.7,
                        metadata=metadata
                    ))
                
            except Exception as e:
                logger.debug(f"Failed to parse Anna's Archive result: {e}")
                continue
        
        # FINAL FIX: Remove duplicates and ensure all results have URLs
        filtered_results = []
        seen_urls = set()
        
        for result in results:
            if result.url and result.url not in seen_urls:
                seen_urls.add(result.url)
                filtered_results.append(result)
        
        return filtered_results

class LibgenDownloader(DownloadStrategy):
    """Library Genesis integration"""
    
    def __init__(self):
        self.mirrors = [
            "http://libgen.rs/",
            "http://libgen.is/",
            "http://libgen.st/",
            "http://gen.lib.rus.ec/"
        ]
        self.session = None
        self.active_mirror = None
    
    async def _find_active_mirror(self):
        """Find an active LibGen mirror"""
        if not self.session:
            self.session = create_secure_session(
                connector=aiohttp.TCPConnector(ssl=False),  # LibGen often uses HTTP
                timeout=aiohttp.ClientTimeout(total=15)
            )
        
        for mirror in self.mirrors:
            try:
                async with self.session.get(mirror, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        self.active_mirror = mirror
                        logger.info(f"Active LibGen mirror: {mirror}")
                        return True
            except Exception as e:
                logger.debug(f"Mirror {mirror} not accessible: {e}")
                continue
        
        return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        if not self.active_mirror:
            if not await self._find_active_mirror():
                logger.error("No active LibGen mirror found")
                return []
        
        try:
            search_url = urljoin(self.active_mirror, 'search.php')
            params = {
                'req': query,
                'lg_topic': 'libgen',
                'open': 0,
                'view': 'simple',
                'res': 25,
                'phrase': 1,
                'column': 'def'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(search_url, params=params, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    results = self._parse_libgen_search(html, self.active_mirror)
                    if results:
                        return results
        except Exception as e:
            logger.error(f"LibGen search failed: {e}")
            self.active_mirror = None  # Reset to try another mirror next time
        
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        
        if not self.session:
            self.session = create_secure_session(
                connector=aiohttp.TCPConnector(ssl=False),
                timeout=aiohttp.ClientTimeout(total=60)
            )
        
        # Extract MD5 hash from search result metadata
        md5_hash = None
        if isinstance(paper_info, SearchResult) and 'md5' in paper_info.metadata:
            md5_hash = paper_info.metadata['md5']
        elif isinstance(paper_info, SearchResult) and paper_info.url:
            # Try to extract MD5 from URL
            md5_match = re.search(r'md5=([A-Fa-f0-9]{32})', paper_info.url)
            if md5_match:
                md5_hash = md5_match.group(1)
        
        if not md5_hash:
            return DownloadResult(
                success=False,
                error="No MD5 hash available for LibGen download",
                source="libgen",
                download_time=time.time() - start_time
            )
        
        # Get download page
        download_page_url = urljoin(self.active_mirror or self.mirrors[0], f'book/index.php?md5={md5_hash}')
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(download_page_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    download_links = self._extract_download_links(html, md5_hash)
                    
                    # Try each download link
                    for link in download_links:
                        try:
                            result = await self._download_from_link(link, start_time)
                            if result.success:
                                return result
                            
                            # Rate limiting between attempts
                            await asyncio.sleep(random.uniform(2, 4))
                            
                        except Exception as e:
                            logger.debug(f"Download link {link} failed: {e}")
                            continue
            
            return DownloadResult(
                success=False,
                error="All download links failed",
                source="libgen",
                download_time=time.time() - start_time
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="libgen",
                download_time=time.time() - start_time
            )
    
    async def _download_from_link(self, download_url: str, start_time: float) -> DownloadResult:
        """Download from a specific LibGen mirror link"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*'
            }
            
            async with self.session.get(download_url, headers=headers, allow_redirects=True) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower() or download_url.endswith('.pdf'):
                        pdf_data = await response.read()
                        if pdf_data.startswith(b'%PDF'):
                            return DownloadResult(
                                success=True,
                                pdf_data=pdf_data,
                                source="libgen",
                                url=download_url,
                                download_time=time.time() - start_time,
                                file_size=len(pdf_data)
                            )
        except Exception as e:
            logger.debug(f"Download from {download_url} failed: {e}")
        
        return DownloadResult(
            success=False,
            error="Download failed",
            source="libgen"
        )
    
    def _extract_download_links(self, html: str, md5_hash: str) -> List[str]:
        """Extract download links from LibGen download page"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        download_links = []
        
        # LibGen download mirrors
        mirror_patterns = [
            f'library.lol/main/{md5_hash}',
            f'libgen.lc/ads.php?md5={md5_hash}',
            f'b-ok.cc/md5/{md5_hash}',
            f'bookfi.net/md5/{md5_hash}'
        ]
        
        # Look for GET links
        get_links = soup.find_all('a', text=re.compile(r'GET', re.IGNORECASE))
        for link in get_links:
            href = link.get('href')
            if href:
                if not href.startswith('http'):
                    href = 'http:' + href if href.startswith('//') else urljoin(self.active_mirror, href)
                download_links.append(href)
        
        # Look for mirror links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            for pattern in mirror_patterns:
                if pattern in href:
                    if not href.startswith('http'):
                        href = 'http:' + href if href.startswith('//') else 'http://' + href
                    if href not in download_links:
                        download_links.append(href)
        
        # CloudFlare IPFS gateway
        ipfs_links = soup.find_all('a', href=re.compile(r'cloudflare-ipfs\.com|ipfs\.io'))
        for link in ipfs_links:
            href = link.get('href')
            if href and href not in download_links:
                download_links.append(href)
        
        return download_links
    
    def can_handle(self, query: str, **kwargs) -> float:
        # Good for books and academic content
        if 'libgen' in query.lower() or 'library genesis' in query.lower():
            return 0.9
        return 0.6
    
    @property
    def name(self) -> str:
        return "libgen"
    
    def _parse_libgen_search(self, html: str, base_url: str) -> List[SearchResult]:
        """Parse LibGen search results HTML"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find the results table
        tables = soup.find_all('table')
        results_table = None
        
        for table in tables:
            if table.find('td', text=re.compile(r'Author|Title|Publisher', re.IGNORECASE)):
                results_table = table
                break
        
        if not results_table:
            return results
        
        # Parse each row (skip header)
        rows = results_table.find_all('tr')[1:]
        
        for row in rows[:25]:
            try:
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue
                
                # Extract data based on typical LibGen table structure
                # Column order may vary, so we try to identify by content
                title = None
                authors = []
                year = None
                md5_hash = None
                url = None
                
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    
                    # Title cell usually contains a link
                    title_link = cell.find('a', href=re.compile(r'book/index\.php\?md5='))
                    if title_link:
                        title = title_link.get_text(strip=True)
                        href = title_link.get('href')
                        if href:
                            url = urljoin(base_url, href)
                            # Extract MD5 from URL
                            md5_match = re.search(r'md5=([A-Fa-f0-9]{32})', href)
                            if md5_match:
                                md5_hash = md5_match.group(1)
                    
                    # Authors (usually after ID and before title)
                    elif i < 3 and ',' in text:
                        authors = [a.strip() for a in text.split(',') if a.strip()]
                    
                    # Year (4-digit number)
                    elif re.match(r'^(19|20)\d{2}$', text):
                        year = int(text)
                
                if title:
                    results.append(SearchResult(
                        title=title,
                        authors=authors,
                        year=year,
                        url=url,
                        source="libgen",
                        confidence=0.8,
                        metadata={'md5': md5_hash} if md5_hash else {}
                    ))
                
            except Exception as e:
                logger.debug(f"Failed to parse LibGen result row: {e}")
                continue
        
        return results

class UniversalDownloader:
    """Main orchestrator for all download strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.strategies: Dict[str, DownloadStrategy] = {}
        self.config = config
        self.credentials = config.get('credentials', {})
        
        # Initialize all strategies
        self._initialize_strategies()
        
        # Download preferences
        self.preference_order = config.get('preference_order', [
            'institutional',  # Try institutional access first
            'open_access',    # Then open access
            'alternative'     # Then alternative sources
        ])
    
    def _initialize_strategies(self):
        """Initialize all download strategies"""
        # Try to import browser-based downloaders first (preferred)
        try:
            from .browser_publisher_downloaders import (
                WileyBrowserDownloader, TaylorFrancisBrowserDownloader,
                SageBrowserDownloader, CambridgeBrowserDownloader, SpringerBrowserDownloader
            )
            
            # Browser-based publisher strategies (with ETH institutional access)
            if 'wiley' in self.credentials:
                self.strategies['wiley'] = WileyBrowserDownloader(self.credentials['wiley'])
            
            if 'taylor_francis' in self.credentials:
                self.strategies['taylor-francis'] = TaylorFrancisBrowserDownloader(self.credentials['taylor_francis'])
            
            if 'sage' in self.credentials:
                self.strategies['sage'] = SageBrowserDownloader(self.credentials['sage'])
            
            if 'cambridge' in self.credentials:
                self.strategies['cambridge'] = CambridgeBrowserDownloader(self.credentials['cambridge'])
            
            if 'springer' in self.credentials:
                self.strategies['springer'] = SpringerBrowserDownloader(self.credentials['springer'])
            
            logger.info("Loaded browser-based publisher downloaders")
            
        except ImportError as e:
            logger.warning(f"Browser downloaders not available, falling back to HTTP-only: {e}")
            
            # Fallback to HTTP-only implementations
            try:
                from .publisher_downloaders import (
                    WileyDownloader, TaylorFrancisDownloader, 
                    SageDownloader, CambridgeDownloader, ACMDownloader
                )
                
                if 'wiley' in self.credentials:
                    self.strategies['wiley'] = WileyDownloader(self.credentials['wiley'])
                
                if 'taylor_francis' in self.credentials:
                    self.strategies['taylor-francis'] = TaylorFrancisDownloader(self.credentials['taylor_francis'])
                
                if 'sage' in self.credentials:
                    self.strategies['sage'] = SageDownloader(self.credentials['sage'])
                
                if 'cambridge' in self.credentials:
                    self.strategies['cambridge'] = CambridgeDownloader(self.credentials['cambridge'])
                
                if 'acm' in self.credentials:
                    self.strategies['acm'] = ACMDownloader(self.credentials['acm'])
                    
            except ImportError as e2:
                logger.warning(f"Could not import any publisher downloaders: {e2}")
        
        # Legacy publishers (keep existing working implementations)
        if 'elsevier' in self.credentials:
            self.strategies['elsevier'] = ElsevierDownloader(self.credentials['elsevier'])
        
        # Alternative strategies (no credentials needed)
        self.strategies['sci-hub'] = SciHubDownloader()
        self.strategies['anna-archive'] = AnnaArchiveDownloader()
        self.strategies['libgen'] = LibgenDownloader()
    
    async def search_all(self, query: str, max_results: int = 50) -> List[SearchResult]:
        """Search across all available sources"""
        all_results = []
        
        # Run searches concurrently
        tasks = []
        for name, strategy in self.strategies.items():
            if strategy.can_handle(query) > 0.1:
                tasks.append(self._search_with_strategy(strategy, query))
        
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate results
        seen_dois = set()
        for results_list in results_lists:
            if isinstance(results_list, list):
                for result in results_list:
                    if result.doi and result.doi not in seen_dois:
                        seen_dois.add(result.doi)
                        all_results.append(result)
                    elif not result.doi:
                        all_results.append(result)
        
        # Sort by confidence score
        all_results.sort(key=lambda x: x.confidence, reverse=True)
        
        return all_results[:max_results]
    
    async def _search_with_strategy(self, strategy: DownloadStrategy, query: str) -> List[SearchResult]:
        """Search with error handling"""
        try:
            return await strategy.search(query)
        except Exception as e:
            logger.error(f"Search failed for {strategy.name}: {e}")
            return []
    
    async def download_paper(self, paper_info: Union[str, SearchResult], 
                           preferred_sources: Optional[List[str]] = None) -> DownloadResult:
        """Download paper trying sources in preference order"""
        
        sources_to_try = preferred_sources or list(self.strategies.keys())
        
        # Sort by preference and capability
        sources_to_try.sort(key=lambda x: self._get_source_priority(x, paper_info))
        
        last_error = None
        for source_name in sources_to_try:
            if source_name not in self.strategies:
                continue
                
            strategy = self.strategies[source_name]
            
            try:
                logger.info(f"Attempting download from {source_name}")
                result = await strategy.download(paper_info)
                
                if result.success:
                    logger.info(f"Successfully downloaded from {source_name}")
                    return result
                else:
                    last_error = result.error
                    logger.warning(f"Download failed from {source_name}: {result.error}")
                
                # Rate limiting between attempts
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Error downloading from {source_name}: {e}")
                continue
        
        return DownloadResult(
            success=False,
            error=f"All sources failed. Last error: {last_error}",
            source="none"
        )
    
    def _get_source_priority(self, source_name: str, paper_info: Union[str, SearchResult]) -> int:
        """Get priority score for source (lower = higher priority)"""
        base_priorities = {
            'springer': 10,
            'elsevier': 11, 
            'wiley': 12,
            'ieee': 13,
            'sci-hub': 20,
            'anna-archive': 21,
            'libgen': 22
        }
        
        base = base_priorities.get(source_name, 50)
        
        # Boost priority if source can handle this query well
        if source_name in self.strategies:
            query = paper_info if isinstance(paper_info, str) else paper_info.title or ""
            capability = self.strategies[source_name].can_handle(query)
            base -= int(capability * 10)  # Up to 10 point boost
        
        return base
    
    async def download_batch(self, papers: List[Union[str, SearchResult]], 
                           max_concurrent: int = 5) -> List[DownloadResult]:
        """Download multiple papers concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_one(paper):
            async with semaphore:
                return await self.download_paper(paper)
        
        tasks = [download_one(paper) for paper in papers]
        results = await asyncio.gather(*tasks)
        
        # Log batch statistics
        successful = sum(1 for r in results if r.success)
        total_size = sum(r.file_size for r in results if r.success)
        
        logger.info(f"Batch download complete: {successful}/{len(papers)} successful, "
                   f"total size: {total_size / 1024 / 1024:.1f} MB")
        
        return results
    
    async def close(self):
        """Clean up resources"""
        for strategy in self.strategies.values():
            if hasattr(strategy, 'session') and strategy.session:
                await strategy.session.close()

# Configuration and usage example
async def main():
    """Example usage"""
    config = {
        'credentials': {
            'springer': {
                'username': 'your_username',
                'password': 'your_password'
            },
            'elsevier': {
                'api_key': 'your_api_key'
            }
        },
        'preference_order': ['springer', 'elsevier', 'sci-hub', 'libgen']
    }
    
    downloader = UniversalDownloader(config)
    
    try:
        # Search for papers
        results = await downloader.search_all("machine learning neural networks")
        print(f"Found {len(results)} papers")
        
        # Download first result
        if results:
            download_result = await downloader.download_paper(results[0])
            if download_result.success:
                print(f"Downloaded {len(download_result.pdf_data)} bytes from {download_result.source}")
            else:
                print(f"Download failed: {download_result.error}")
    
    finally:
        await downloader.close()

if __name__ == "__main__":
    asyncio.run(main())