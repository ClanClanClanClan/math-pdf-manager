#!/usr/bin/env python3
"""
Browser-Automated Publisher Downloaders
Full browser automation for all major academic publishers using Playwright.
"""

import asyncio
import logging
import time
import re
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .universal_downloader import DownloadStrategy, DownloadResult, SearchResult

# Browser automation
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = BrowserContext = Page = None

logger = logging.getLogger(__name__)

class BrowserDownloadStrategy(DownloadStrategy):
    """Base class for browser-automated publisher downloaders"""
    
    def __init__(self, credentials: Dict[str, str]):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is required for browser automation. Install with: playwright install")
        
        self.credentials = credentials
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._authenticated = False
    
    async def _launch_browser(self, headless: bool = True):
        """Launch browser with proper configuration"""
        self.playwright = await async_playwright().start()
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ]
        )
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
        )
        
        # Create page
        self.page = await self.context.new_page()
        
        # Set up request/response logging
        self.page.on('response', self._log_response)
    
    async def _log_response(self, response):
        """Log important responses"""
        if response.status >= 400:
            logger.warning(f"HTTP {response.status}: {response.url}")
        elif 'pdf' in response.headers.get('content-type', '').lower():
            logger.info(f"PDF found: {response.url}")
    
    async def _eth_institutional_login(self) -> bool:
        """Perform ETH Zurich institutional authentication"""
        username = self.credentials.get('username')
        password = self.credentials.get('password')
        
        if not username or not password:
            logger.error("ETH credentials not provided")
            return False
        
        try:
            # Look for institutional login button
            login_selectors = [
                'text="Institutional Sign In"',
                'text="Sign in via your institution"',
                'text="Access through your institution"',
                'text="Institutional Login"',
                '[data-testid="institutional-login"]',
                'a[href*="institutional"]',
                'button[data-target*="institutional"]'
            ]
            
            login_clicked = False
            for selector in login_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    await self.page.click(selector)
                    logger.info(f"Clicked institutional login: {selector}")
                    login_clicked = True
                    break
                except:
                    continue
            
            if not login_clicked:
                logger.warning("No institutional login button found")
                return False
            
            # Wait for institution selector or direct redirect
            await self.page.wait_for_timeout(2000)
            
            # Look for ETH Zurich in institution selector
            eth_selectors = [
                'text="ETH Zurich"',
                'text="Swiss Federal Institute of Technology Zurich"',
                '[value*="ethz"]',
                'option:has-text("ETH")'
            ]
            
            for selector in eth_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    await self.page.click(selector)
                    logger.info("Selected ETH Zurich")
                    break
                except:
                    continue
            
            # Wait for ETH login page
            await self.page.wait_for_timeout(3000)
            
            # Fill ETH credentials
            username_selectors = [
                'input[name="j_username"]',
                'input[name="username"]',
                'input[id="username"]',
                'input[type="text"]'
            ]
            
            password_selectors = [
                'input[name="j_password"]',
                'input[name="password"]', 
                'input[id="password"]',
                'input[type="password"]'
            ]
            
            # Fill username
            for selector in username_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=2000)
                    await self.page.fill(selector, username)
                    logger.info("Filled username")
                    break
                except:
                    continue
            
            # Fill password
            for selector in password_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=2000)
                    await self.page.fill(selector, password)
                    logger.info("Filled password")
                    break
                except:
                    continue
            
            # Submit form
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Sign")',
                'button:has-text("Login")',
                'input[value*="Login"]'
            ]
            
            for selector in submit_selectors:
                try:
                    await self.page.click(selector)
                    logger.info("Submitted login form")
                    break
                except:
                    continue
            
            # Wait for authentication to complete
            await self.page.wait_for_timeout(5000)
            
            # Check for successful authentication
            current_url = self.page.url
            if 'login' not in current_url.lower() and 'auth' not in current_url.lower():
                logger.info("ETH authentication successful")
                return True
            else:
                logger.warning("Authentication may have failed")
                return False
                
        except Exception as e:
            logger.error(f"ETH authentication failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

class WileyBrowserDownloader(BrowserDownloadStrategy):
    """Wiley Online Library with browser automation"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = "https://onlinelibrary.wiley.com"
    
    async def authenticate(self) -> bool:
        """Authenticate with Wiley via browser automation"""
        if self._authenticated:
            return True
        
        await self._launch_browser(headless=True)
        
        try:
            # Navigate to Wiley
            await self.page.goto(self.base_url, wait_until='domcontentloaded')
            logger.info("Navigated to Wiley")
            
            # Perform ETH institutional authentication
            self._authenticated = await self._eth_institutional_login()
            return self._authenticated
            
        except Exception as e:
            logger.error(f"Wiley authentication failed: {e}")
            return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Wiley with browser automation"""
        if not await self.authenticate():
            return []
        
        try:
            # Navigate to search
            search_url = f"{self.base_url}/action/doSearch"
            await self.page.goto(f"{search_url}?AllField={query}", wait_until='domcontentloaded')
            
            # Wait for results
            await self.page.wait_for_selector('.item__body, .search-result', timeout=10000)
            
            # Extract results
            results = []
            items = await self.page.query_selector_all('.item__body, .search-result')
            
            for item in items[:20]:
                try:
                    title_elem = await item.query_selector('h2.item__title a, .title-link')
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    url = await title_elem.get_attribute('href')
                    if url and not url.startswith('http'):
                        url = urljoin(self.base_url, url)
                    
                    # Extract DOI
                    doi = None
                    doi_elem = await item.query_selector('a[href*="doi.org"]')
                    if doi_elem:
                        doi_href = await doi_elem.get_attribute('href')
                        doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_href)
                        if doi_match:
                            doi = doi_match.group()
                    
                    results.append(SearchResult(
                        title=title.strip(),
                        doi=doi,
                        url=url,
                        source="wiley-browser",
                        confidence=0.9
                    ))
                    
                except Exception as e:
                    logger.debug(f"Failed to parse Wiley result: {e}")
                    continue
            
            logger.info(f"Found {len(results)} Wiley results")
            return results
            
        except Exception as e:
            logger.error(f"Wiley search failed: {e}")
            return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from Wiley with browser automation"""
        start_time = time.time()
        
        if not await self.authenticate():
            return DownloadResult(
                success=False,
                error="Authentication failed",
                source="wiley-browser",
                download_time=time.time() - start_time
            )
        
        try:
            # Navigate to paper
            if isinstance(paper_info, str):
                # Assume DOI
                paper_url = f"https://doi.org/{paper_info}"
            else:
                paper_url = paper_info.url or f"https://doi.org/{paper_info.doi}"
            
            await self.page.goto(paper_url, wait_until='domcontentloaded')
            
            # Look for PDF download button
            pdf_selectors = [
                'a[href*=".pdf"]',
                'button:has-text("Download PDF")',
                '.pdf-download',
                '[data-testid="pdf-download"]'
            ]
            
            pdf_url = None
            for selector in pdf_selectors:
                try:
                    elem = await self.page.wait_for_selector(selector, timeout=3000)
                    pdf_url = await elem.get_attribute('href')
                    if pdf_url:
                        break
                except:
                    continue
            
            if not pdf_url:
                return DownloadResult(
                    success=False,
                    error="PDF download link not found",
                    source="wiley-browser",
                    download_time=time.time() - start_time
                )
            
            # Download PDF
            async with self.page.expect_download() as download_info:
                await self.page.click(f'a[href="{pdf_url}"]')
            
            download = await download_info.value
            pdf_data = await download.path().read_bytes()
            
            return DownloadResult(
                success=True,
                pdf_data=pdf_data,
                source="wiley-browser",
                url=pdf_url,
                download_time=time.time() - start_time,
                file_size=len(pdf_data)
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="wiley-browser",
                download_time=time.time() - start_time
            )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'wiley' in query.lower() or 'onlinelibrary.wiley.com' in query:
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "wiley-browser"

class TaylorFrancisBrowserDownloader(BrowserDownloadStrategy):
    """Taylor & Francis with browser automation"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = "https://www.tandfonline.com"
    
    async def authenticate(self) -> bool:
        """Authenticate with Taylor & Francis"""
        if self._authenticated:
            return True
        
        await self._launch_browser(headless=True)
        
        try:
            await self.page.goto(self.base_url, wait_until='domcontentloaded')
            logger.info("Navigated to Taylor & Francis")
            
            self._authenticated = await self._eth_institutional_login()
            return self._authenticated
            
        except Exception as e:
            logger.error(f"Taylor & Francis authentication failed: {e}")
            return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Taylor & Francis"""
        if not await self.authenticate():
            return []
        
        try:
            search_url = f"{self.base_url}/action/doSearch?AllField={query}"
            await self.page.goto(search_url, wait_until='domcontentloaded')
            
            await self.page.wait_for_selector('.hlFld-Title, .searchResultItem', timeout=10000)
            
            results = []
            items = await self.page.query_selector_all('.hlFld-Title, .searchResultItem')
            
            for item in items[:20]:
                try:
                    title_elem = await item.query_selector('a')
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    url = await title_elem.get_attribute('href')
                    if url and not url.startswith('http'):
                        url = urljoin(self.base_url, url)
                    
                    results.append(SearchResult(
                        title=title.strip(),
                        url=url,
                        source="taylor-francis-browser",
                        confidence=0.9
                    ))
                    
                except Exception as e:
                    logger.debug(f"Failed to parse T&F result: {e}")
                    continue
            
            logger.info(f"Found {len(results)} Taylor & Francis results")
            return results
            
        except Exception as e:
            logger.error(f"Taylor & Francis search failed: {e}")
            return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from Taylor & Francis"""
        start_time = time.time()
        
        if not await self.authenticate():
            return DownloadResult(
                success=False,
                error="Authentication failed",
                source="taylor-francis-browser",
                download_time=time.time() - start_time
            )
        
        try:
            # Navigate to paper
            if isinstance(paper_info, str):
                paper_url = f"https://doi.org/{paper_info}"
            else:
                paper_url = paper_info.url or f"https://doi.org/{paper_info.doi}"
            
            await self.page.goto(paper_url, wait_until='domcontentloaded')
            
            # Look for PDF download
            pdf_selectors = [
                'a:has-text("Download PDF")',
                '.download-pdf',
                'a[href*=".pdf"]'
            ]
            
            for selector in pdf_selectors:
                try:
                    elem = await self.page.wait_for_selector(selector, timeout=3000)
                    async with self.page.expect_download() as download_info:
                        await elem.click()
                    
                    download = await download_info.value
                    pdf_data = await download.path().read_bytes()
                    
                    return DownloadResult(
                        success=True,
                        pdf_data=pdf_data,
                        source="taylor-francis-browser",
                        url=paper_url,
                        download_time=time.time() - start_time,
                        file_size=len(pdf_data)
                    )
                except:
                    continue
            
            return DownloadResult(
                success=False,
                error="PDF download not found",
                source="taylor-francis-browser",
                download_time=time.time() - start_time
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="taylor-francis-browser",
                download_time=time.time() - start_time
            )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'tandfonline' in query.lower() or 'taylor' in query.lower():
            return 0.9
        return 0.2
    
    @property
    def name(self) -> str:
        return "taylor-francis-browser"

class SageBrowserDownloader(BrowserDownloadStrategy):
    """SAGE Publications with browser automation"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = "https://journals.sagepub.com"
    
    async def authenticate(self) -> bool:
        """Authenticate with SAGE"""
        if self._authenticated:
            return True
        
        await self._launch_browser(headless=True)
        
        try:
            await self.page.goto(self.base_url, wait_until='domcontentloaded')
            logger.info("Navigated to SAGE")
            
            self._authenticated = await self._eth_institutional_login()
            return self._authenticated
            
        except Exception as e:
            logger.error(f"SAGE authentication failed: {e}")
            return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search SAGE"""
        if not await self.authenticate():
            return []
        
        try:
            search_url = f"{self.base_url}/action/doSearch?AllField={query}"
            await self.page.goto(search_url, wait_until='domcontentloaded')
            
            await self.page.wait_for_selector('.art_title, .searchResultItem', timeout=10000)
            
            results = []
            items = await self.page.query_selector_all('.art_title, .searchResultItem')
            
            for item in items[:20]:
                try:
                    title_elem = await item.query_selector('a')
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    url = await title_elem.get_attribute('href')
                    if url and not url.startswith('http'):
                        url = urljoin(self.base_url, url)
                    
                    results.append(SearchResult(
                        title=title.strip(),
                        url=url,
                        source="sage-browser",
                        confidence=0.9
                    ))
                    
                except Exception as e:
                    logger.debug(f"Failed to parse SAGE result: {e}")
                    continue
            
            logger.info(f"Found {len(results)} SAGE results")
            return results
            
        except Exception as e:
            logger.error(f"SAGE search failed: {e}")
            return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from SAGE"""
        start_time = time.time()
        
        if not await self.authenticate():
            return DownloadResult(
                success=False,
                error="Authentication failed",
                source="sage-browser",
                download_time=time.time() - start_time
            )
        
        try:
            # Navigate to paper
            if isinstance(paper_info, str):
                paper_url = f"https://doi.org/{paper_info}"
            else:
                paper_url = paper_info.url or f"https://doi.org/{paper_info.doi}"
            
            await self.page.goto(paper_url, wait_until='domcontentloaded')
            
            # Look for PDF download
            pdf_selectors = [
                '.show-pdf',
                'a:has-text("PDF")',
                'a[href*=".pdf"]'
            ]
            
            for selector in pdf_selectors:
                try:
                    elem = await self.page.wait_for_selector(selector, timeout=3000)
                    async with self.page.expect_download() as download_info:
                        await elem.click()
                    
                    download = await download_info.value
                    pdf_data = await download.path().read_bytes()
                    
                    return DownloadResult(
                        success=True,
                        pdf_data=pdf_data,
                        source="sage-browser",
                        url=paper_url,
                        download_time=time.time() - start_time,
                        file_size=len(pdf_data)
                    )
                except:
                    continue
            
            return DownloadResult(
                success=False,
                error="PDF download not found",
                source="sage-browser",
                download_time=time.time() - start_time
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="sage-browser",
                download_time=time.time() - start_time
            )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'sagepub' in query.lower() or 'sage' in query.lower():
            return 0.9
        return 0.2
    
    @property
    def name(self) -> str:
        return "sage-browser"

class CambridgeBrowserDownloader(BrowserDownloadStrategy):
    """Cambridge University Press with browser automation"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = "https://www.cambridge.org"
    
    async def authenticate(self) -> bool:
        """Authenticate with Cambridge"""
        if self._authenticated:
            return True
        
        await self._launch_browser(headless=True)
        
        try:
            await self.page.goto(self.base_url, wait_until='domcontentloaded')
            logger.info("Navigated to Cambridge")
            
            self._authenticated = await self._eth_institutional_login()
            return self._authenticated
            
        except Exception as e:
            logger.error(f"Cambridge authentication failed: {e}")
            return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Cambridge"""
        if not await self.authenticate():
            return []
        
        try:
            search_url = f"{self.base_url}/core/search?q={query}"
            await self.page.goto(search_url, wait_until='domcontentloaded')
            
            await self.page.wait_for_selector('.result-item, .search-result', timeout=10000)
            
            results = []
            items = await self.page.query_selector_all('.result-item, .search-result')
            
            for item in items[:20]:
                try:
                    title_elem = await item.query_selector('h3 a, .title-link')
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    url = await title_elem.get_attribute('href')
                    if url and not url.startswith('http'):
                        url = urljoin(self.base_url, url)
                    
                    results.append(SearchResult(
                        title=title.strip(),
                        url=url,
                        source="cambridge-browser",
                        confidence=0.9
                    ))
                    
                except Exception as e:
                    logger.debug(f"Failed to parse Cambridge result: {e}")
                    continue
            
            logger.info(f"Found {len(results)} Cambridge results")
            return results
            
        except Exception as e:
            logger.error(f"Cambridge search failed: {e}")
            return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from Cambridge"""
        start_time = time.time()
        
        if not await self.authenticate():
            return DownloadResult(
                success=False,
                error="Authentication failed",
                source="cambridge-browser",
                download_time=time.time() - start_time
            )
        
        try:
            # Navigate to paper
            if isinstance(paper_info, str):
                paper_url = f"https://doi.org/{paper_info}"
            else:
                paper_url = paper_info.url or f"https://doi.org/{paper_info.doi}"
            
            await self.page.goto(paper_url, wait_until='domcontentloaded')
            
            # Look for PDF download
            pdf_selectors = [
                '.download-pdf',
                'a:has-text("Download PDF")',
                'a[href*=".pdf"]'
            ]
            
            for selector in pdf_selectors:
                try:
                    elem = await self.page.wait_for_selector(selector, timeout=3000)
                    async with self.page.expect_download() as download_info:
                        await elem.click()
                    
                    download = await download_info.value
                    pdf_data = await download.path().read_bytes()
                    
                    return DownloadResult(
                        success=True,
                        pdf_data=pdf_data,
                        source="cambridge-browser",
                        url=paper_url,
                        download_time=time.time() - start_time,
                        file_size=len(pdf_data)
                    )
                except:
                    continue
            
            return DownloadResult(
                success=False,
                error="PDF download not found",
                source="cambridge-browser",
                download_time=time.time() - start_time
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="cambridge-browser",
                download_time=time.time() - start_time
            )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'cambridge.org' in query.lower() or 'cambridge university press' in query.lower():
            return 0.9
        return 0.2
    
    @property
    def name(self) -> str:
        return "cambridge-browser"

class SpringerBrowserDownloader(BrowserDownloadStrategy):
    """Springer with browser automation"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = "https://link.springer.com"
    
    async def authenticate(self) -> bool:
        """Authenticate with Springer"""
        if self._authenticated:
            return True
        
        await self._launch_browser(headless=True)
        
        try:
            await self.page.goto(self.base_url, wait_until='domcontentloaded')
            logger.info("Navigated to Springer")
            
            self._authenticated = await self._eth_institutional_login()
            return self._authenticated
            
        except Exception as e:
            logger.error(f"Springer authentication failed: {e}")
            return False
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Springer"""
        if not await self.authenticate():
            return []
        
        try:
            search_url = f"{self.base_url}/search?query={query}"
            await self.page.goto(search_url, wait_until='domcontentloaded')
            
            await self.page.wait_for_selector('.c-listing__item, .result-item', timeout=10000)
            
            results = []
            items = await self.page.query_selector_all('.c-listing__item, .result-item')
            
            for item in items[:20]:
                try:
                    title_elem = await item.query_selector('h3 a, .c-listing__title a')
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    url = await title_elem.get_attribute('href')
                    if url and not url.startswith('http'):
                        url = urljoin(self.base_url, url)
                    
                    results.append(SearchResult(
                        title=title.strip(),
                        url=url,
                        source="springer-browser",
                        confidence=0.9
                    ))
                    
                except Exception as e:
                    logger.debug(f"Failed to parse Springer result: {e}")
                    continue
            
            logger.info(f"Found {len(results)} Springer results")
            return results
            
        except Exception as e:
            logger.error(f"Springer search failed: {e}")
            return []
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from Springer"""
        start_time = time.time()
        
        if not await self.authenticate():
            return DownloadResult(
                success=False,
                error="Authentication failed",
                source="springer-browser",
                download_time=time.time() - start_time
            )
        
        try:
            # Navigate to paper
            if isinstance(paper_info, str):
                paper_url = f"https://doi.org/{paper_info}"
            else:
                paper_url = paper_info.url or f"https://doi.org/{paper_info.doi}"
            
            await self.page.goto(paper_url, wait_until='domcontentloaded')
            
            # Look for PDF download
            pdf_selectors = [
                'a:has-text("Download PDF")',
                '.c-pdf-download',
                'a[href*=".pdf"]'
            ]
            
            for selector in pdf_selectors:
                try:
                    elem = await self.page.wait_for_selector(selector, timeout=3000)
                    async with self.page.expect_download() as download_info:
                        await elem.click()
                    
                    download = await download_info.value
                    pdf_data = await download.path().read_bytes()
                    
                    return DownloadResult(
                        success=True,
                        pdf_data=pdf_data,
                        source="springer-browser",
                        url=paper_url,
                        download_time=time.time() - start_time,
                        file_size=len(pdf_data)
                    )
                except:
                    continue
            
            return DownloadResult(
                success=False,
                error="PDF download not found",
                source="springer-browser",
                download_time=time.time() - start_time
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="springer-browser",
                download_time=time.time() - start_time
            )
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'springer' in query.lower() or 'link.springer.com' in query:
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "springer-browser"