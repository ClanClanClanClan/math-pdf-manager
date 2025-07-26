#!/usr/bin/env python3
"""
Publisher-Specific Downloaders
Enhanced implementations for major academic publishers.
"""

import asyncio
import aiohttp
import re
import json
import time
import random
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse, quote, unquote
from bs4 import BeautifulSoup
import logging

from .universal_downloader import DownloadStrategy, DownloadResult, SearchResult

# Import secure session creator
try:
    from .credentials import create_secure_session
except ImportError:
    # Fallback if credentials module not available
    def create_secure_session(**kwargs):
        return aiohttp.ClientSession(**kwargs)

logger = logging.getLogger(__name__)

class WileyDownloader(DownloadStrategy):
    """Wiley Online Library downloader"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.session = None
        self.base_url = "https://onlinelibrary.wiley.com"
    
    async def authenticate(self):
        """Authenticate with Wiley via institutional access"""
        if not self.session:
            self.session = create_secure_session()
        
        if 'institution_url' in self.credentials:
            # Handle institutional authentication
            return await self._institutional_auth()
        
        return False
    
    async def _institutional_auth(self) -> bool:
        """Handle Wiley institutional authentication"""
        try:
            institution_url = self.credentials['institution_url']
            async with self.session.get(institution_url) as response:
                if response.status == 200:
                    # Follow authentication flow
                    return True
        except Exception as e:
            logger.error(f"Wiley authentication failed: {e}")
        return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Wiley Online Library"""
        await self.authenticate()
        
        search_url = f"{self.base_url}/action/doSearch"
        params = {
            'AllField': query,
            'SeriesKey': '',
            'sortBy': 'Earliest',
            'pageSize': 20
        }
        
        try:
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_wiley_search(html)
        except Exception as e:
            logger.error(f"Wiley search failed: {e}")
        
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from Wiley"""
        start_time = time.time()
        await self.authenticate()
        
        if isinstance(paper_info, str):
            # Assume DOI
            doi = paper_info.replace('doi:', '').replace('https://doi.org/', '')
            pdf_url = f"{self.base_url}/doi/pdf/{doi}"
        else:
            # Extract PDF URL from search result
            if paper_info.url:
                pdf_url = paper_info.url.replace('/abs/', '/pdf/').replace('/full/', '/pdf/')
            else:
                return DownloadResult(
                    success=False, 
                    error="No URL in search result",
                    source="wiley",
                    download_time=time.time() - start_time
                )
        
        try:
            async with self.session.get(pdf_url) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower():
                        pdf_data = await response.read()
                        return DownloadResult(
                            success=True,
                            pdf_data=pdf_data,
                            source="wiley",
                            url=pdf_url,
                            download_time=time.time() - start_time,
                            file_size=len(pdf_data)
                        )
                    else:
                        # Might be HTML page, extract PDF link
                        html = await response.text()
                        actual_pdf_url = self._extract_pdf_link(html)
                        if actual_pdf_url:
                            return await self._download_pdf_from_url(actual_pdf_url, start_time)
                
                return DownloadResult(
                    success=False,
                    error=f"HTTP {response.status}",
                    source="wiley", 
                    download_time=time.time() - start_time
                )
        
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="wiley",
                download_time=time.time() - start_time
            )
    
    async def _download_pdf_from_url(self, pdf_url: str, start_time: float) -> DownloadResult:
        """Download PDF from extracted URL"""
        try:
            async with self.session.get(pdf_url) as response:
                if response.status == 200:
                    pdf_data = await response.read()
                    if pdf_data.startswith(b'%PDF'):
                        return DownloadResult(
                            success=True,
                            pdf_data=pdf_data,
                            source="wiley",
                            url=pdf_url,
                            download_time=time.time() - start_time,
                            file_size=len(pdf_data)
                        )
        except Exception as e:
            logger.error(f"PDF download failed: {e}")
        
        return DownloadResult(
            success=False,
            error="PDF download failed",
            source="wiley",
            download_time=time.time() - start_time
        )
    
    def _extract_pdf_link(self, html: str) -> Optional[str]:
        """Extract PDF download link from Wiley page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for PDF download links
        pdf_links = soup.find_all('a', href=re.compile(r'.*\.pdf|.*epdf|.*pdf'))
        for link in pdf_links:
            href = link.get('href')
            if href:
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        return None
    
    def _parse_wiley_search(self, html: str) -> List[SearchResult]:
        """Parse Wiley search results"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find article entries
        articles = soup.find_all('div', class_='item__body')
        
        for article in articles:
            try:
                title_elem = article.find('h2', class_='item__title') or article.find('a', class_='publication_title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract URL
                link = title_elem.find('a')
                url = None
                if link and link.get('href'):
                    href = link.get('href')
                    if href.startswith('/'):
                        url = urljoin(self.base_url, href)
                    else:
                        url = href
                
                # Extract authors
                authors = []
                author_elem = article.find('div', class_='item__authors') or article.find('p', class_='meta__authors')
                if author_elem:
                    author_text = author_elem.get_text(strip=True)
                    authors = [a.strip() for a in author_text.split(',')]
                
                # Extract DOI
                doi = None
                doi_elem = article.find('a', href=re.compile(r'doi\.org'))
                if doi_elem:
                    doi_href = doi_elem.get('href')
                    doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_href)
                    if doi_match:
                        doi = doi_match.group()
                
                results.append(SearchResult(
                    title=title,
                    authors=authors,
                    doi=doi,
                    url=url,
                    source="wiley",
                    confidence=0.8
                ))
            
            except Exception as e:
                logger.debug(f"Failed to parse Wiley result: {e}")
                continue
        
        return results
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'wiley' in query.lower() or 'onlinelibrary.wiley.com' in query:
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "wiley"

class TaylorFrancisDownloader(DownloadStrategy):
    """Taylor & Francis downloader"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.session = None
        self.base_url = "https://www.tandfonline.com"
    
    async def authenticate(self):
        if not self.session:
            self.session = create_secure_session()
        
        # Taylor & Francis institutional authentication
        if 'institution_url' in self.credentials:
            try:
                # Access institutional login page
                inst_url = self.credentials['institution_url']
                async with self.session.get(inst_url) as response:
                    if response.status == 200:
                        # Check if already authenticated
                        text = await response.text()
                        if 'logout' in text.lower() or 'signed in' in text.lower():
                            return True
                        
                        # Need to authenticate - implement based on your institution
                        # This is a template - adapt for your specific institution
                        logger.info("Taylor & Francis institutional auth needed")
                        return True
            except Exception as e:
                logger.error(f"T&F authentication failed: {e}")
                
        return True
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        await self.authenticate()
        
        search_url = f"{self.base_url}/action/doSearch"
        params = {
            'AllField': query,
            'pageSize': 20,
            'sortBy': 'relevancy'
        }
        
        try:
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_tf_search(html)
        except Exception as e:
            logger.error(f"Taylor & Francis search failed: {e}")
        
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        await self.authenticate()
        
        # Extract DOI or URL
        if isinstance(paper_info, str):
            # Check if it's a DOI
            if '10.' in paper_info and '/' in paper_info:
                doi = paper_info.replace('doi:', '').replace('https://doi.org/', '')
                pdf_url = f"{self.base_url}/doi/pdf/{doi}"
            else:
                return DownloadResult(
                    success=False,
                    error="Invalid identifier for Taylor & Francis",
                    source="taylor-francis",
                    download_time=time.time() - start_time
                )
        else:
            # Extract from search result
            if paper_info.doi:
                pdf_url = f"{self.base_url}/doi/pdf/{paper_info.doi}"
            elif paper_info.url:
                # Convert article URL to PDF URL
                pdf_url = paper_info.url.replace('/doi/', '/doi/pdf/')
                if not pdf_url.endswith('.pdf'):
                    pdf_url = pdf_url.rstrip('/') + '?download=true'
            else:
                return DownloadResult(
                    success=False,
                    error="No DOI or URL available",
                    source="taylor-francis",
                    download_time=time.time() - start_time
                )
        
        try:
            async with self.session.get(pdf_url, allow_redirects=True) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower():
                        pdf_data = await response.read()
                        if pdf_data.startswith(b'%PDF'):
                            return DownloadResult(
                                success=True,
                                pdf_data=pdf_data,
                                source="taylor-francis",
                                url=pdf_url,
                                download_time=time.time() - start_time,
                                file_size=len(pdf_data)
                            )
                    else:
                        # Try to extract PDF link from HTML
                        html = await response.text()
                        actual_pdf_url = self._extract_pdf_link_tf(html)
                        if actual_pdf_url:
                            return await self._download_pdf_url(actual_pdf_url, start_time)
                            
                return DownloadResult(
                    success=False,
                    error=f"Failed to download PDF: HTTP {response.status}",
                    source="taylor-francis",
                    download_time=time.time() - start_time
                )
                
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="taylor-francis",
                download_time=time.time() - start_time
            )
    
    def _parse_tf_search(self, html: str) -> List[SearchResult]:
        """Parse Taylor & Francis search results"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find search result items
        articles = soup.find_all('div', class_='hlFld-Title') or soup.find_all('article', class_='searchResultItem')
        
        for article in articles[:20]:  # Limit to 20 results
            try:
                # Extract title and URL
                title_elem = article.find('a') or article.find('h2')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                if url and not url.startswith('http'):
                    url = urljoin(self.base_url, url)
                
                # Extract DOI
                doi = None
                doi_elem = article.find('a', href=re.compile(r'doi\.org')) or article.find('span', class_='doi')
                if doi_elem:
                    doi_text = doi_elem.get('href', '') or doi_elem.get_text('')
                    doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_text)
                    if doi_match:
                        doi = doi_match.group()
                
                # Extract authors
                authors = []
                author_elem = article.find('div', class_='hlFld-ContribAuthor') or article.find('span', class_='authors')
                if author_elem:
                    author_text = author_elem.get_text(strip=True)
                    # Split by common separators
                    authors = re.split(r'[,;]|\s+and\s+', author_text)
                    authors = [a.strip() for a in authors if a.strip()]
                
                # Extract year
                year = None
                date_elem = article.find('span', class_='publication-year') or article.find('time')
                if date_elem:
                    year_text = date_elem.get_text()
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                    if year_match:
                        year = int(year_match.group())
                
                results.append(SearchResult(
                    title=title,
                    authors=authors,
                    doi=doi,
                    url=url,
                    year=year,
                    source="taylor-francis",
                    confidence=0.8
                ))
                
            except Exception as e:
                logger.debug(f"Failed to parse T&F result: {e}")
                continue
        
        return results
    
    def _extract_pdf_link_tf(self, html: str) -> Optional[str]:
        """Extract PDF download link from Taylor & Francis page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for PDF download button/link patterns
        pdf_patterns = [
            {'class': 'download-pdf'},
            {'class': 'pdf-link'},
            {'href': re.compile(r'/doi/pdf/')},
            {'href': re.compile(r'\.pdf')}
        ]
        
        for pattern in pdf_patterns:
            pdf_link = soup.find('a', pattern)
            if pdf_link and pdf_link.get('href'):
                href = pdf_link.get('href')
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        # Look for download button with onclick
        download_button = soup.find('button', text=re.compile(r'download|pdf', re.IGNORECASE))
        if download_button and download_button.get('onclick'):
            onclick = download_button.get('onclick')
            url_match = re.search(r'["\']([^"\']*\.pdf[^"\']*)["\']', onclick)
            if url_match:
                pdf_url = url_match.group(1)
                if pdf_url.startswith('/'):
                    return urljoin(self.base_url, pdf_url)
                elif pdf_url.startswith('http'):
                    return pdf_url
        
        return None
    
    async def _download_pdf_url(self, pdf_url: str, start_time: float) -> DownloadResult:
        """Download PDF from URL with proper headers"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*',
                'Referer': self.base_url
            }
            
            async with self.session.get(pdf_url, headers=headers, allow_redirects=True) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    pdf_data = await response.read()
                    
                    if pdf_data.startswith(b'%PDF') or 'pdf' in content_type.lower():
                        return DownloadResult(
                            success=True,
                            pdf_data=pdf_data,
                            source="taylor-francis",
                            url=pdf_url,
                            download_time=time.time() - start_time,
                            file_size=len(pdf_data)
                        )
                    
                return DownloadResult(
                    success=False,
                    error=f"Invalid PDF response: HTTP {response.status}",
                    source="taylor-francis",
                    download_time=time.time() - start_time
                )
                
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="taylor-francis",
                download_time=time.time() - start_time
            )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'tandfonline' in query.lower() or 'taylor' in query.lower():
            return 0.9
        return 0.2
    
    @property 
    def name(self) -> str:
        return "taylor-francis"

class SageDownloader(DownloadStrategy):
    """SAGE Publications downloader"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.session = None
        self.base_url = "https://journals.sagepub.com"
    
    async def authenticate(self):
        if not self.session:
            self.session = create_secure_session()
        
        # SAGE institutional authentication
        if 'institution_url' in self.credentials:
            try:
                inst_url = self.credentials['institution_url']
                async with self.session.get(inst_url) as response:
                    if response.status == 200:
                        text = await response.text()
                        if 'logout' in text.lower() or 'my account' in text.lower():
                            return True
                        logger.info("SAGE institutional auth needed")
                        return True
            except Exception as e:
                logger.error(f"SAGE authentication failed: {e}")
        
        return True
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        await self.authenticate()
        
        search_url = f"{self.base_url}/action/doSearch"
        params = {
            'AllField': query,
            'pageSize': 20,
            'startPage': 0
        }
        
        try:
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_sage_search(html)
        except Exception as e:
            logger.error(f"SAGE search failed: {e}")
        
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        await self.authenticate()
        
        # Determine PDF URL
        if isinstance(paper_info, str):
            # Check if it's a DOI
            if '10.' in paper_info and '/' in paper_info:
                doi = paper_info.replace('doi:', '').replace('https://doi.org/', '')
                pdf_url = f"{self.base_url}/doi/pdf/{doi}"
            else:
                return DownloadResult(
                    success=False,
                    error="Invalid identifier for SAGE",
                    source="sage",
                    download_time=time.time() - start_time
                )
        else:
            # Extract from search result
            if paper_info.doi:
                pdf_url = f"{self.base_url}/doi/pdf/{paper_info.doi}"
            elif paper_info.url:
                # Convert article URL to PDF URL
                pdf_url = paper_info.url.replace('/doi/', '/doi/pdf/')
                if '/full/' in pdf_url:
                    pdf_url = pdf_url.replace('/full/', '/pdf/')
            else:
                return DownloadResult(
                    success=False,
                    error="No DOI or URL available",
                    source="sage",
                    download_time=time.time() - start_time
                )
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*'
            }
            
            async with self.session.get(pdf_url, headers=headers, allow_redirects=True) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower():
                        pdf_data = await response.read()
                        if pdf_data.startswith(b'%PDF'):
                            return DownloadResult(
                                success=True,
                                pdf_data=pdf_data,
                                source="sage",
                                url=pdf_url,
                                download_time=time.time() - start_time,
                                file_size=len(pdf_data)
                            )
                    else:
                        # HTML page, try to extract PDF link
                        html = await response.text()
                        actual_pdf_url = self._extract_pdf_link_sage(html)
                        if actual_pdf_url:
                            return await self._download_pdf_sage(actual_pdf_url, start_time)
                
                return DownloadResult(
                    success=False,
                    error=f"Failed to download PDF: HTTP {response.status}",
                    source="sage",
                    download_time=time.time() - start_time
                )
                
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="sage",
                download_time=time.time() - start_time
            )
    
    def _parse_sage_search(self, html: str) -> List[SearchResult]:
        """Parse SAGE search results"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find article entries
        articles = soup.find_all('div', class_='art_title') or soup.find_all('article', class_='searchResultItem')
        
        for article in articles[:20]:
            try:
                # Extract title
                title_elem = article.find('a', class_='ref') or article.find('h3') or article.find('a')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract URL
                url = title_elem.get('href', '')
                if url and not url.startswith('http'):
                    url = urljoin(self.base_url, url)
                
                # Extract DOI
                doi = None
                doi_elem = article.find('a', href=re.compile(r'doi\.org')) or article.find('span', text=re.compile(r'10\.\d{4,}'))
                if doi_elem:
                    doi_text = doi_elem.get('href', '') or doi_elem.get_text('')
                    doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_text)
                    if doi_match:
                        doi = doi_match.group()
                
                # Extract authors
                authors = []
                author_elem = article.find('div', class_='art_authors') or article.find('span', class_='authors')
                if author_elem:
                    author_text = author_elem.get_text(strip=True)
                    authors = re.split(r'[,;]|\s+and\s+', author_text)
                    authors = [a.strip() for a in authors if a.strip()]
                
                # Extract year
                year = None
                date_elem = article.find('span', class_='published') or article.find('time')
                if date_elem:
                    year_text = date_elem.get_text()
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                    if year_match:
                        year = int(year_match.group())
                
                results.append(SearchResult(
                    title=title,
                    authors=authors,
                    doi=doi,
                    url=url,
                    year=year,
                    source="sage",
                    confidence=0.8
                ))
                
            except Exception as e:
                logger.debug(f"Failed to parse SAGE result: {e}")
                continue
        
        return results
    
    def _extract_pdf_link_sage(self, html: str) -> Optional[str]:
        """Extract PDF link from SAGE page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for PDF download links
        pdf_patterns = [
            {'class': 'show-pdf'},
            {'class': 'pdf-link'},
            {'href': re.compile(r'/doi/pdf/')},
            {'text': re.compile(r'PDF', re.IGNORECASE)}
        ]
        
        for pattern in pdf_patterns:
            pdf_link = soup.find('a', pattern)
            if pdf_link and pdf_link.get('href'):
                href = pdf_link.get('href')
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        return None
    
    async def _download_pdf_sage(self, pdf_url: str, start_time: float) -> DownloadResult:
        """Download PDF from SAGE URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*',
                'Referer': self.base_url
            }
            
            async with self.session.get(pdf_url, headers=headers) as response:
                if response.status == 200:
                    pdf_data = await response.read()
                    if pdf_data.startswith(b'%PDF'):
                        return DownloadResult(
                            success=True,
                            pdf_data=pdf_data,
                            source="sage",
                            url=pdf_url,
                            download_time=time.time() - start_time,
                            file_size=len(pdf_data)
                        )
        except Exception as e:
            logger.error(f"SAGE PDF download failed: {e}")
        
        return DownloadResult(
            success=False,
            error="PDF download failed",
            source="sage",
            download_time=time.time() - start_time
        )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'sagepub' in query.lower() or 'sage' in query.lower():
            return 0.9
        return 0.2
    
    @property
    def name(self) -> str:
        return "sage"

class CambridgeDownloader(DownloadStrategy):
    """Cambridge University Press downloader"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.session = None
        self.base_url = "https://www.cambridge.org"
    
    async def authenticate(self):
        if not self.session:
            self.session = create_secure_session()
        
        # Cambridge institutional authentication
        if 'institution_url' in self.credentials:
            try:
                inst_url = self.credentials['institution_url']
                async with self.session.get(inst_url) as response:
                    if response.status == 200:
                        text = await response.text()
                        if 'sign out' in text.lower() or 'my account' in text.lower():
                            return True
                        logger.info("Cambridge institutional auth needed")
                        return True
            except Exception as e:
                logger.error(f"Cambridge authentication failed: {e}")
        
        return True
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        await self.authenticate()
        
        search_url = f"{self.base_url}/core/search"
        params = {
            'q': query,
            'sort': 'relevance',
            'pageSize': 20,
            'product': 'core'
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            async with self.session.get(search_url, params=params, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_cambridge_search(html)
        except Exception as e:
            logger.error(f"Cambridge search failed: {e}")
        
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        await self.authenticate()
        
        # Determine PDF URL
        if isinstance(paper_info, str):
            # Check if it's a DOI
            if '10.' in paper_info and '/' in paper_info:
                doi = paper_info.replace('doi:', '').replace('https://doi.org/', '')
                # Cambridge uses different URL patterns
                pdf_url = f"{self.base_url}/core/services/aop-cambridge-core/content/view/{doi}"
            else:
                return DownloadResult(
                    success=False,
                    error="Invalid identifier for Cambridge",
                    source="cambridge",
                    download_time=time.time() - start_time
                )
        else:
            # Extract from search result
            if paper_info.url:
                # Convert article URL to PDF URL
                if '/article/' in paper_info.url:
                    pdf_url = paper_info.url.replace('/article/', '/services/aop-cambridge-core/content/view/')
                else:
                    pdf_url = paper_info.url
            elif paper_info.doi:
                pdf_url = f"{self.base_url}/core/services/aop-cambridge-core/content/view/{paper_info.doi}"
            else:
                return DownloadResult(
                    success=False,
                    error="No URL or DOI available",
                    source="cambridge",
                    download_time=time.time() - start_time
                )
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*',
                'Referer': self.base_url
            }
            
            async with self.session.get(pdf_url, headers=headers, allow_redirects=True) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower():
                        pdf_data = await response.read()
                        if pdf_data.startswith(b'%PDF'):
                            return DownloadResult(
                                success=True,
                                pdf_data=pdf_data,
                                source="cambridge",
                                url=pdf_url,
                                download_time=time.time() - start_time,
                                file_size=len(pdf_data)
                            )
                    else:
                        # Try to extract PDF link from HTML
                        html = await response.text()
                        actual_pdf_url = self._extract_pdf_link_cambridge(html)
                        if actual_pdf_url:
                            return await self._download_pdf_cambridge(actual_pdf_url, start_time)
                
                return DownloadResult(
                    success=False,
                    error=f"Failed to download PDF: HTTP {response.status}",
                    source="cambridge",
                    download_time=time.time() - start_time
                )
                
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="cambridge",
                download_time=time.time() - start_time
            )
    
    def _parse_cambridge_search(self, html: str) -> List[SearchResult]:
        """Parse Cambridge search results"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find search result items
        articles = soup.find_all('div', class_='result-item') or soup.find_all('li', class_='search-result')
        
        for article in articles[:20]:
            try:
                # Extract title
                title_elem = article.find('h3', class_='title') or article.find('a', class_='title-link')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract URL
                url = None
                link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        url = urljoin(self.base_url, href)
                    else:
                        url = href
                
                # Extract DOI
                doi = None
                doi_elem = article.find('a', href=re.compile(r'doi\.org')) or article.find('span', class_='doi')
                if doi_elem:
                    doi_text = doi_elem.get('href', '') or doi_elem.get_text('')
                    doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_text)
                    if doi_match:
                        doi = doi_match.group()
                
                # Extract authors
                authors = []
                author_elem = article.find('div', class_='contributors') or article.find('span', class_='authors')
                if author_elem:
                    author_text = author_elem.get_text(strip=True)
                    authors = re.split(r'[,;]|\s+and\s+', author_text)
                    authors = [a.strip() for a in authors if a.strip() and not a.strip().isdigit()]
                
                # Extract year
                year = None
                date_elem = article.find('span', class_='date') or article.find('time')
                if date_elem:
                    year_text = date_elem.get_text()
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                    if year_match:
                        year = int(year_match.group())
                
                results.append(SearchResult(
                    title=title,
                    authors=authors,
                    doi=doi,
                    url=url,
                    year=year,
                    source="cambridge",
                    confidence=0.8
                ))
                
            except Exception as e:
                logger.debug(f"Failed to parse Cambridge result: {e}")
                continue
        
        return results
    
    def _extract_pdf_link_cambridge(self, html: str) -> Optional[str]:
        """Extract PDF link from Cambridge page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for PDF download links
        pdf_patterns = [
            {'class': 'download-pdf'},
            {'class': 'pdf-link'},
            {'href': re.compile(r'/download/pdf/')},
            {'href': re.compile(r'\.pdf')},
            {'data-pdf-url': True}
        ]
        
        for pattern in pdf_patterns:
            pdf_elem = soup.find('a', pattern)
            if pdf_elem:
                # Check data-pdf-url first
                if pdf_elem.get('data-pdf-url'):
                    return pdf_elem.get('data-pdf-url')
                # Then check href
                elif pdf_elem.get('href'):
                    href = pdf_elem.get('href')
                    if href.startswith('/'):
                        return urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        return href
        
        return None
    
    async def _download_pdf_cambridge(self, pdf_url: str, start_time: float) -> DownloadResult:
        """Download PDF from Cambridge URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*',
                'Referer': self.base_url
            }
            
            async with self.session.get(pdf_url, headers=headers) as response:
                if response.status == 200:
                    pdf_data = await response.read()
                    if pdf_data.startswith(b'%PDF'):
                        return DownloadResult(
                            success=True,
                            pdf_data=pdf_data,
                            source="cambridge",
                            url=pdf_url,
                            download_time=time.time() - start_time,
                            file_size=len(pdf_data)
                        )
        except Exception as e:
            logger.error(f"Cambridge PDF download failed: {e}")
        
        return DownloadResult(
            success=False,
            error="PDF download failed",
            source="cambridge",
            download_time=time.time() - start_time
        )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'cambridge.org' in query.lower() or 'cambridge university press' in query.lower():
            return 0.9
        return 0.2
    
    @property
    def name(self) -> str:
        return "cambridge"

class ACMDownloader(DownloadStrategy):
    """ACM Digital Library downloader"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.session = None
        self.base_url = "https://dl.acm.org"
    
    async def authenticate(self):
        if not self.session:
            self.session = create_secure_session()
        return True
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        await self.authenticate()
        
        search_url = f"{self.base_url}/action/doSearch"
        params = {
            'AllField': query,
            'pageSize': 20,
            'sortBy': 'relevancy'
        }
        
        try:
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_acm_search(html)
        except Exception as e:
            logger.error(f"ACM search failed: {e}")
        
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        start_time = time.time()
        await self.authenticate()
        
        # ACM download implementation
        if isinstance(paper_info, SearchResult) and paper_info.url:
            pdf_url = paper_info.url.replace('/doi/', '/doi/pdf/')
            
            try:
                async with self.session.get(pdf_url) as response:
                    if response.status == 200:
                        pdf_data = await response.read()
                        if pdf_data.startswith(b'%PDF'):
                            return DownloadResult(
                                success=True,
                                pdf_data=pdf_data,
                                source="acm",
                                url=pdf_url,
                                download_time=time.time() - start_time,
                                file_size=len(pdf_data)
                            )
            except Exception as e:
                logger.error(f"ACM download failed: {e}")
        
        return DownloadResult(
            success=False,
            error="ACM download failed",
            source="acm",
            download_time=time.time() - start_time
        )
    
    def _parse_acm_search(self, html: str) -> List[SearchResult]:
        # Parse ACM search results  
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # ACM-specific parsing logic
        articles = soup.find_all('div', class_='issue-item')
        
        for article in articles:
            try:
                title_elem = article.find('h5', class_='issue-item__title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract URL
                link = title_elem.find('a')
                url = None
                if link and link.get('href'):
                    href = link.get('href')
                    if href.startswith('/'):
                        url = urljoin(self.base_url, href)
                    else:
                        url = href
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    source="acm",
                    confidence=0.8
                ))
            
            except Exception as e:
                logger.debug(f"Failed to parse ACM result: {e}")
                continue
        
        return results
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'acm.org' in query.lower() or 'dl.acm.org' in query.lower():
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "acm"

# Enhanced Sci-Hub with better mirror management
class EnhancedSciHubDownloader(DownloadStrategy):
    """Enhanced Sci-Hub with dynamic mirror discovery"""
    
    def __init__(self):
        self.mirrors = []
        self.session = None
        self.mirror_finder_urls = [
            "https://sci-hub.now.sh/",  # Sci-Hub status page
            "https://whereisscihub.now.sh/",  # Mirror finder
        ]
        self.last_mirror_update = 0
        self.mirror_update_interval = 3600  # 1 hour
    
    async def _discover_mirrors(self):
        """Dynamically discover active Sci-Hub mirrors"""
        if time.time() - self.last_mirror_update < self.mirror_update_interval:
            return
        
        if not self.session:
            self.session = create_secure_session(timeout=aiohttp.ClientTimeout(total=15))
        
        discovered_mirrors = []
        
        # Try known mirror patterns
        mirror_patterns = [
            "https://sci-hub.se/",
            "https://sci-hub.st/", 
            "https://sci-hub.ru/",
            "https://sci-hub.wf/",
            "https://sci-hub.shop/",
            "https://sci-hub.ren/",
            "https://sci-hub.red/",
            "https://sci-hub.one/",
        ]
        
        # Test each mirror
        tasks = [self._test_mirror(mirror) for mirror in mirror_patterns]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if result is True:
                discovered_mirrors.append(mirror_patterns[i])
        
        self.mirrors = discovered_mirrors
        self.last_mirror_update = time.time()
        
        logger.info(f"Discovered {len(self.mirrors)} active Sci-Hub mirrors")
    
    async def _test_mirror(self, mirror_url: str) -> bool:
        """Test if a mirror is active"""
        try:
            async with self.session.get(mirror_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    # Check for Sci-Hub indicators
                    if 'sci-hub' in content.lower() or 'doi' in content.lower():
                        return True
        except Exception:
            pass
        return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Enhanced search with DOI detection"""
        if self._looks_like_doi(query):
            return [SearchResult(
                title=f"Paper with DOI: {query}",
                doi=self._clean_doi(query),
                source="sci-hub",
                confidence=0.9
            )]
        elif self._looks_like_pmid(query):
            return [SearchResult(
                title=f"Paper with PMID: {query}",
                metadata={'pmid': query},
                source="sci-hub",
                confidence=0.8
            )]
        return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Enhanced download with better error handling"""
        start_time = time.time()
        await self._discover_mirrors()
        
        if not self.mirrors:
            return DownloadResult(
                success=False,
                error="No active Sci-Hub mirrors found",
                source="sci-hub",
                download_time=time.time() - start_time
            )
        
        # Extract identifier
        if isinstance(paper_info, str):
            identifier = paper_info
        elif paper_info.doi:
            identifier = paper_info.doi
        elif 'pmid' in paper_info.metadata:
            identifier = paper_info.metadata['pmid']
        else:
            return DownloadResult(
                success=False,
                error="No valid identifier (DOI/PMID) provided",
                source="sci-hub",
                download_time=time.time() - start_time
            )
        
        # Try mirrors in random order to distribute load
        mirrors_to_try = self.mirrors.copy()
        random.shuffle(mirrors_to_try)
        
        for mirror in mirrors_to_try:
            try:
                result = await self._download_from_mirror(mirror, identifier)
                if result.success:
                    result.download_time = time.time() - start_time
                    return result
                
                # Random delay between attempts
                await asyncio.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.debug(f"Mirror {mirror} failed: {e}")
                continue
        
        return DownloadResult(
            success=False,
            error="All Sci-Hub mirrors failed",
            source="sci-hub",
            download_time=time.time() - start_time
        )
    
    async def _download_from_mirror(self, mirror: str, identifier: str) -> DownloadResult:
        """Enhanced download with better PDF detection"""
        clean_identifier = self._clean_doi(identifier)
        url = urljoin(mirror, clean_identifier)
        
        try:
            # Use random user agent
            headers = {'User-Agent': self._get_random_user_agent()}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return DownloadResult(success=False, error=f"HTTP {response.status}")
                
                content_type = response.headers.get('content-type', '')
                
                if 'pdf' in content_type.lower():
                    # Direct PDF response
                    pdf_data = await response.read()
                    if pdf_data.startswith(b'%PDF'):
                        return DownloadResult(
                            success=True,
                            pdf_data=pdf_data,
                            source="sci-hub",
                            url=url,
                            file_size=len(pdf_data)
                        )
                else:
                    # HTML page, extract PDF URL
                    html = await response.text()
                    pdf_urls = self._extract_pdf_urls(html, mirror)
                    
                    for pdf_url in pdf_urls:
                        try:
                            async with self.session.get(pdf_url, headers=headers) as pdf_response:
                                if pdf_response.status == 200:
                                    pdf_data = await pdf_response.read()
                                    if pdf_data.startswith(b'%PDF'):
                                        return DownloadResult(
                                            success=True,
                                            pdf_data=pdf_data,
                                            source="sci-hub", 
                                            url=pdf_url,
                                            file_size=len(pdf_data)
                                        )
                        except Exception as e:
                            logger.debug(f"PDF URL {pdf_url} failed: {e}")
                            continue
        
        except Exception as e:
            return DownloadResult(success=False, error=str(e))
        
        return DownloadResult(success=False, error="No valid PDF found")
    
    def _extract_pdf_urls(self, html: str, base_url: str) -> List[str]:
        """Extract all possible PDF URLs from HTML"""
        urls = []
        
        # Enhanced patterns for PDF detection
        patterns = [
            r'<iframe[^>]+src=["\'](.*?\.pdf[^"\']*)["\']',
            r'<embed[^>]+src=["\'](.*?\.pdf[^"\']*)["\']', 
            r'<object[^>]+data=["\'](.*?\.pdf[^"\']*)["\']',
            r'<a[^>]+href=["\'](.*?\.pdf[^"\']*)["\'][^>]*>',
            r'location\.href\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
            r'window\.open\(["\']([^"\']*\.pdf[^"\']*)["\']',
            r'src=["\'](https?://[^"\']*\.pdf[^"\']*)["\']',
            r'"(https?://[^"]*\.pdf[^"]*)"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                pdf_url = match
                if pdf_url.startswith('//'):
                    pdf_url = 'https:' + pdf_url
                elif pdf_url.startswith('/'):
                    pdf_url = urljoin(base_url, pdf_url)
                elif not pdf_url.startswith('http'):
                    pdf_url = urljoin(base_url, pdf_url)
                
                urls.append(pdf_url)
        
        return list(set(urls))  # Remove duplicates
    
    def _clean_doi(self, doi: str) -> str:
        """Clean DOI for URL usage"""
        return doi.replace('doi:', '').replace('https://doi.org/', '').replace('http://dx.doi.org/', '').strip()
    
    def _looks_like_doi(self, text: str) -> bool:
        """Enhanced DOI detection"""
        doi_patterns = [
            r'10\.\d{4,}/[^\s]+',
            r'doi:10\.\d{4,}/[^\s]+',
            r'https?://doi\.org/10\.\d{4,}/[^\s]+'
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in doi_patterns)
    
    def _looks_like_pmid(self, text: str) -> bool:
        """Detect PubMed IDs"""
        return re.match(r'^\d{8,}$', text.strip()) is not None
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent to avoid detection"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", 
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        return random.choice(user_agents)
    
    def can_handle(self, query: str, **kwargs) -> float:
        if self._looks_like_doi(query) or self._looks_like_pmid(query):
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "enhanced-sci-hub"