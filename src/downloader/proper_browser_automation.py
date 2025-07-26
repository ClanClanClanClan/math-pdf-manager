#!/usr/bin/env python3
"""
Proper Browser Automation for Academic Publishers
Following the working patterns from IEEE and SIAM implementations
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

class ProperBrowserDownloader(DownloadStrategy):
    """Base class for PROPER browser automation following IEEE/SIAM patterns"""
    
    def __init__(self, credentials: Dict[str, str]):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is required. Install with: pip install playwright && playwright install")
        
        self.credentials = credentials
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._authenticated = False
    
    async def _launch_browser(self, headless: bool = False):
        """Launch browser with proven settings from IEEE implementation"""
        self.playwright = await async_playwright().start()
        
        # Use exact args from working IEEE implementation
        self.browser = await self.playwright.chromium.launch(
            headless=headless,  # Visual mode for reliability
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        # Create context
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        # Enable download handling
        self.page.set_default_timeout(60000)
    
    async def _handle_eth_authentication(self, modal_window=None) -> bool:
        """Handle ETH authentication following IEEE pattern"""
        username = self.credentials.get('username')
        password = self.credentials.get('password')
        
        if not username or not password:
            logger.error("No ETH credentials provided")
            return False
        
        try:
            # If we're in a modal, work within it
            search_context = modal_window if modal_window else self.page
            
            # Search for ETH in institution list (following IEEE pattern)
            logger.info("Searching for ETH Zurich...")
            
            # Look for search input
            search_input = await search_context.wait_for_selector('input[type="text"]', timeout=10000)
            if search_input:
                await search_input.fill("ETH Zurich")
                await self.page.keyboard.press('Enter')
                await self.page.wait_for_timeout(2000)
            
            # Click on ETH option
            eth_option = await self.page.wait_for_selector('text="ETH Zurich"', timeout=10000)
            await eth_option.click()
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for redirect to ETH login
            logger.info("Waiting for ETH login page...")
            await self.page.wait_for_timeout(3000)
            
            # Fill ETH credentials (exact selectors from IEEE)
            username_input = await self.page.wait_for_selector(
                'input[name="j_username"], input[id="username"], input[name="username"]', 
                timeout=10000
            )
            await username_input.fill(username)
            
            password_input = await self.page.wait_for_selector(
                'input[name="j_password"], input[id="password"], input[name="password"]',
                timeout=10000
            )
            await password_input.fill(password)
            
            # Submit
            submit_button = await self.page.query_selector('[type="submit"]')
            await submit_button.click()
            
            # Wait for authentication to complete
            logger.info("Waiting for authentication...")
            await self.page.wait_for_timeout(5000)
            
            return True
            
        except Exception as e:
            logger.error(f"ETH authentication failed: {e}")
            await self.page.screenshot(path="eth_auth_error.png")
            return False
    
    async def _get_pdf_via_stamp(self, doc_id: str, base_url: str) -> Optional[bytes]:
        """Get PDF using stamp URL pattern (from IEEE implementation)"""
        stamp_url = f"{base_url}/stamp/stamp.jsp?tp=&arnumber={doc_id}"
        logger.info(f"Trying stamp URL: {stamp_url}")
        
        response = await self.page.goto(stamp_url, wait_until='networkidle')
        content = await response.body()
        
        if content.startswith(b'%PDF'):
            logger.info("✅ Got PDF directly from stamp URL")
            return content
        
        # PDF might be in iframe
        logger.info("Checking for PDF iframe...")
        await self.page.wait_for_timeout(5000)
        
        pdf_frame = await self.page.query_selector('iframe#pdf, iframe[src*="pdf"]')
        if pdf_frame:
            src = await pdf_frame.get_attribute('src')
            logger.info(f"Found PDF iframe: {src}")
            
            if src and not src.startswith('http'):
                src = urljoin(base_url, src)
            
            pdf_response = await self.page.goto(src)
            pdf_content = await pdf_response.body()
            
            if pdf_content.startswith(b'%PDF'):
                logger.info("✅ Got PDF from iframe")
                return pdf_content
        
        return None
    
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

class IEEEBrowserDownloader(ProperBrowserDownloader):
    """IEEE with PROPER modal handling"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = "https://ieeexplore.ieee.org"
    
    async def authenticate(self) -> bool:
        """Authenticate following exact IEEE working pattern"""
        if self._authenticated:
            return True
        
        await self._launch_browser(headless=False)  # Visual mode
        
        try:
            # Use a test DOI like in working implementation
            test_doi = "10.1109/JPROC.2018.2820126"
            ieee_url = f"https://doi.org/{test_doi}"
            
            logger.info("Navigating to IEEE document...")
            await self.page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await self.page.wait_for_timeout(5000)
            
            # Handle cookies
            accept_button = await self.page.query_selector('button:has-text("Accept All")')
            if accept_button:
                await accept_button.click()
                await self.page.wait_for_timeout(1000)
            
            # Click institutional sign in
            logger.info("Clicking Institutional Sign In...")
            inst_button = await self.page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
            await inst_button.click()
            await self.page.wait_for_timeout(2000)
            
            # Find the modal window (exact selector from working code)
            logger.info("Looking for modal window...")
            modal = await self.page.wait_for_selector('ngb-modal-window', timeout=5000)
            
            if modal:
                logger.info("Found modal, looking for SeamlessAccess button...")
                
                # Click the SeamlessAccess button (exact selector from working code)
                access_button = await modal.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                if access_button:
                    await access_button.click()
                    await self.page.wait_for_timeout(3000)
                else:
                    logger.error("Could not find SeamlessAccess button")
                    return False
            
            # Wait for institution selector modal
            logger.info("Waiting for institution selector...")
            institution_modal = await self.page.wait_for_selector(
                'ngb-modal-window:has-text("Search for your Institution")', 
                timeout=10000
            )
            
            if institution_modal:
                # Handle ETH authentication within modal
                self._authenticated = await self._handle_eth_authentication(institution_modal)
                
                # Check if we're back at IEEE
                if self._authenticated:
                    current_url = self.page.url
                    if 'ieee' in current_url:
                        logger.info("✅ Successfully authenticated with IEEE")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"IEEE authentication failed: {e}")
            await self.page.screenshot(path="ieee_auth_error.png")
            return False
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from IEEE using stamp URL pattern"""
        start_time = time.time()
        
        if not await self.authenticate():
            return DownloadResult(
                success=False,
                error="Authentication failed",
                source="ieee-browser",
                download_time=time.time() - start_time
            )
        
        try:
            # Navigate to paper
            if isinstance(paper_info, str):
                paper_url = f"https://doi.org/{paper_info}"
            else:
                paper_url = paper_info.url or f"https://doi.org/{paper_info.doi}"
            
            await self.page.goto(paper_url, wait_until='domcontentloaded')
            await self.page.wait_for_timeout(3000)
            
            # Extract document ID from URL
            current_url = self.page.url
            doc_id = None
            if '/document/' in current_url:
                doc_id = current_url.split('/document/')[1].split('/')[0]
            
            if doc_id:
                # Try stamp URL method
                pdf_content = await self._get_pdf_via_stamp(doc_id, self.base_url)
                
                if pdf_content:
                    return DownloadResult(
                        success=True,
                        pdf_data=pdf_content,
                        source="ieee-browser",
                        url=paper_url,
                        download_time=time.time() - start_time,
                        file_size=len(pdf_content)
                    )
            
            return DownloadResult(
                success=False,
                error="Could not extract PDF",
                source="ieee-browser",
                download_time=time.time() - start_time
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="ieee-browser",
                download_time=time.time() - start_time
            )
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search IEEE (implement if needed)"""
        return []
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'ieee' in query.lower() or '10.1109' in query:
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "ieee-browser"

class SpringerBrowserDownloader(ProperBrowserDownloader):
    """Springer with PROPER authentication handling"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = "https://link.springer.com"
    
    async def authenticate(self) -> bool:
        """Authenticate with Springer using proper flow"""
        if self._authenticated:
            return True
        
        await self._launch_browser(headless=False)
        
        try:
            # Navigate to a paper that requires authentication
            test_doi = "10.1007/s10994-021-05946-3"
            springer_url = f"https://doi.org/{test_doi}"
            
            logger.info("Navigating to Springer paper...")
            await self.page.goto(springer_url, wait_until='domcontentloaded', timeout=60000)
            await self.page.wait_for_timeout(5000)
            
            # Check if we need to authenticate (look for login/access buttons)
            login_button = await self.page.query_selector('a:has-text("Log in"), a:has-text("Access")')
            
            if login_button:
                logger.info("Need authentication, clicking login...")
                await login_button.click()
                await self.page.wait_for_timeout(3000)
                
                # Look for institutional access
                inst_button = await self.page.wait_for_selector(
                    'text="Log in via your institution", text="Institutional access"',
                    timeout=10000
                )
                
                if inst_button:
                    await inst_button.click()
                    await self.page.wait_for_timeout(3000)
                    
                    # Handle ETH authentication
                    self._authenticated = await self._handle_eth_authentication()
                    
                    if self._authenticated:
                        # Check if we're back at Springer with access
                        current_url = self.page.url
                        if 'springer' in current_url:
                            logger.info("✅ Successfully authenticated with Springer")
                            return True
            else:
                # Already have access
                logger.info("Already have access to Springer")
                self._authenticated = True
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Springer authentication failed: {e}")
            await self.page.screenshot(path="springer_auth_error.png")
            return False
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from Springer with proper authentication"""
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
            await self.page.wait_for_timeout(3000)
            
            # Look for download button
            download_button = await self.page.wait_for_selector(
                'a:has-text("Download PDF"), button:has-text("Download PDF")',
                timeout=10000
            )
            
            if download_button:
                # Get the href
                href = await download_button.get_attribute('href')
                
                if href:
                    # Navigate to PDF URL
                    if not href.startswith('http'):
                        href = urljoin(self.base_url, href)
                    
                    response = await self.page.goto(href, wait_until='networkidle')
                    content = await response.body()
                    
                    if content.startswith(b'%PDF'):
                        return DownloadResult(
                            success=True,
                            pdf_data=content,
                            source="springer-browser",
                            url=paper_url,
                            download_time=time.time() - start_time,
                            file_size=len(content)
                        )
            
            return DownloadResult(
                success=False,
                error="Could not find download button",
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
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Springer (implement if needed)"""
        return []
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'springer' in query.lower() or '10.1007' in query:
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "springer-browser"

class WileyBrowserDownloader(ProperBrowserDownloader):
    """Wiley with PROPER authentication flow"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.base_url = "https://onlinelibrary.wiley.com"
    
    async def authenticate(self) -> bool:
        """Authenticate with Wiley properly"""
        if self._authenticated:
            return True
        
        await self._launch_browser(headless=False)
        
        try:
            # Navigate to a Wiley paper
            test_doi = "10.1002/anie.201506954"
            wiley_url = f"https://doi.org/{test_doi}"
            
            logger.info("Navigating to Wiley paper...")
            await self.page.goto(wiley_url, wait_until='domcontentloaded', timeout=60000)
            await self.page.wait_for_timeout(5000)
            
            # Handle cookies
            try:
                cookie_button = await self.page.wait_for_selector('button:has-text("Accept All")', timeout=3000)
                if cookie_button:
                    await cookie_button.click()
                    await self.page.wait_for_timeout(1000)
            except:
                pass
            
            # Click Login
            login_button = await self.page.wait_for_selector('text="Login / Register"', timeout=10000)
            await login_button.click()
            await self.page.wait_for_timeout(3000)
            
            # Click institutional access
            inst_button = await self.page.wait_for_selector('a:has-text("Institution")', timeout=10000)
            await inst_button.click()
            await self.page.wait_for_timeout(3000)
            
            # Handle ETH authentication
            self._authenticated = await self._handle_eth_authentication()
            
            if self._authenticated:
                current_url = self.page.url
                if 'wiley' in current_url:
                    logger.info("✅ Successfully authenticated with Wiley")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Wiley authentication failed: {e}")
            await self.page.screenshot(path="wiley_auth_error.png")
            return False
    
    async def download(self, paper_info: Union[str, SearchResult], **kwargs) -> DownloadResult:
        """Download from Wiley"""
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
                paper_url = f"https://doi.org/{paper_info}"
            else:
                paper_url = paper_info.url or f"https://doi.org/{paper_info.doi}"
            
            await self.page.goto(paper_url, wait_until='domcontentloaded')
            await self.page.wait_for_timeout(3000)
            
            # Look for PDF link
            pdf_link = await self.page.wait_for_selector('a:has-text("PDF")', timeout=10000)
            
            if pdf_link:
                href = await pdf_link.get_attribute('href')
                
                if href:
                    if not href.startswith('http'):
                        href = urljoin(self.base_url, href)
                    
                    response = await self.page.goto(href, wait_until='networkidle')
                    content = await response.body()
                    
                    if content.startswith(b'%PDF'):
                        return DownloadResult(
                            success=True,
                            pdf_data=content,
                            source="wiley-browser",
                            url=paper_url,
                            download_time=time.time() - start_time,
                            file_size=len(content)
                        )
            
            return DownloadResult(
                success=False,
                error="Could not find PDF link",
                source="wiley-browser",
                download_time=time.time() - start_time
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                source="wiley-browser",
                download_time=time.time() - start_time
            )
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Wiley (implement if needed)"""
        return []
    
    def can_handle(self, query: str, **kwargs) -> float:
        if 'wiley' in query.lower() or '10.1002' in query:
            return 0.9
        return 0.3
    
    @property
    def name(self) -> str:
        return "wiley-browser"

# Similar implementations for Taylor & Francis, SAGE, Cambridge...
# Following the same pattern: proper modal handling, ETH auth, direct PDF download