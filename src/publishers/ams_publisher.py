#!/usr/bin/env python3
"""
AMS (American Mathematical Society) Publisher
=============================================

Implementation for downloading papers from AMS journals with institutional access.
Covers AMS journals like Journal of the AMS, Transactions, Proceedings, etc.
"""

import asyncio
import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, BrowserContext, Page

from . import DownloadResult, AuthenticationConfig

logger = logging.getLogger(__name__)

class AMSPublisher:
    """AMS (American Mathematical Society) publisher with browser automation for institutional access"""
    
    def __init__(self, auth_config: AuthenticationConfig):
        self.auth_config = auth_config
        self.base_urls = [
            "https://www.ams.org/",
            "https://mathscinet.ams.org/",
        ]
        self.session_data = {}
        
    def can_handle_url(self, url: str) -> bool:
        """Check if this publisher can handle the given URL"""
        return any(domain in url.lower() for domain in [
            'ams.org',
            'mathscinet.ams.org',
            'doi.org'
        ])
    
    def can_handle_doi(self, doi: str) -> bool:
        """Check if this publisher can handle the given DOI"""
        return any(prefix in doi.lower() for prefix in [
            '10.1090/',  # Main AMS DOI prefix
            '10.1112/',  # Some AMS-related journals
        ])
    
    async def download_paper(self, paper_identifier: str, save_path: Path) -> DownloadResult:
        """Download paper using browser automation with ETH institutional access"""
        
        start_time = time.time()
        
        try:
            # Determine if input is DOI or URL
            if paper_identifier.startswith('http'):
                target_url = paper_identifier
            elif paper_identifier.startswith('10.'):
                target_url = f"https://doi.org/{paper_identifier}"
            else:
                # Assume it's an AMS article identifier
                target_url = f"https://www.ams.org/journals/jams/articles/{paper_identifier}"
            
            logger.info(f"AMS: Starting download for {target_url}")
            
            # Use browser automation for institutional access
            result = await self._browser_institutional_download(target_url, save_path)
            
            if result.success:
                logger.info(f"AMS: Successfully downloaded")
            else:
                logger.warning(f"AMS: Download failed - {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"AMS: Download error - {e}")
            return DownloadResult(
                success=False,
                error_message=f"AMS download failed: {str(e)}"
            )
    
    async def _browser_institutional_download(self, target_url: str, save_path: Path) -> DownloadResult:
        """Download using browser automation with ETH institutional authentication"""
        
        async with async_playwright() as p:
            # Launch browser with anti-detection settings
            browser = await p.chromium.launch(
                headless=False,  # Keep visible for debugging institutional access
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--start-maximized',
                    '--no-sandbox'
                ]
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                
                # Add anti-detection scripts
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() { return {}; },
                        csi: function() { return {}; }
                    };
                """)
                
                page = await context.new_page()
                
                # Navigate to the target article
                logger.info(f"AMS: Navigating to {target_url}")
                await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Check if we need institutional access
                page_content = await page.content()
                current_url = page.url
                
                if any(indicator in page_content.lower() for indicator in [
                    'institutional access', 'subscribe', 'purchase', 'paywall',
                    'login', 'sign in', 'access through your institution',
                    'get access', 'member access', 'subscription required',
                    'mathscinet access', 'ams member'
                ]):
                    logger.info("AMS: Institutional access required")
                    
                    # Look for institutional access options
                    access_selectors = [
                        'a:has-text("Institutional Access")',
                        'a:has-text("Access through your institution")',
                        'a:has-text("Sign in through your institution")',
                        'a:has-text("Login through your institution")',
                        'a:has-text("MathSciNet access")',
                        'a[href*="institutional"]',
                        'a[href*="shibboleth"]', 
                        'button:has-text("Institution")',
                        '.institutional-access a',
                        '#institution-login',
                        '.inst-login',
                        'a[href*="mathscinet"]'
                    ]
                    
                    institutional_link = None
                    for selector in access_selectors:
                        try:
                            element = await page.wait_for_selector(selector, timeout=5000)
                            if element:
                                institutional_link = element
                                logger.info(f"AMS: Found institutional access with: {selector}")
                                break
                        except:
                            continue
                    
                    if institutional_link:
                        logger.info("AMS: Clicking institutional access")
                        await institutional_link.click()
                        await page.wait_for_timeout(3000)
                        
                        # Handle institutional authentication flow
                        if await self._handle_institutional_authentication(page):
                            logger.info("AMS: Institutional authentication successful")
                        else:
                            logger.warning("AMS: Institutional authentication may have failed")
                    else:
                        logger.warning("AMS: No institutional access link found")
                
                # Wait for page to load after potential authentication
                await page.wait_for_timeout(5000)
                
                # Look for PDF download options
                pdf_downloaded = await self._find_and_download_pdf(page, save_path)
                
                if pdf_downloaded:
                    # Verify the PDF was downloaded correctly
                    if save_path.exists() and save_path.stat().st_size > 1000:
                        # Quick PDF validation
                        with open(save_path, 'rb') as f:
                            if f.read(4) == b'%PDF':
                                logger.info(f"AMS: PDF successfully downloaded to {save_path}")
                                return DownloadResult(
                                    success=True,
                                    file_path=save_path
                                )
                
                return DownloadResult(
                    success=False,
                    error_message="Could not download PDF from AMS"
                )
                
            finally:
                await browser.close()
    
    async def _handle_institutional_authentication(self, page: Page) -> bool:
        """Handle institutional authentication flow"""
        
        try:
            await page.wait_for_timeout(3000)
            current_url = page.url
            page_content = await page.content()
            
            logger.info(f"AMS auth: Current URL is {current_url}")
            
            # Check if we're on AMS's institutional selection page
            if 'ams.org' in current_url and ('wayf' in current_url or 'institution' in current_url or 'shibboleth' in current_url):
                logger.info("AMS: On institutional selection page")
                
                # Look for ETH in the institution dropdown/search
                eth_selectors = [
                    'option:has-text("ETH Zurich")',
                    'option:has-text("Swiss Federal Institute")',
                    'a:has-text("ETH Zurich")',
                    'text="ETH Zurich"',
                    'text="Swiss Federal Institute of Technology"',
                    'text="Eidgenössische Technische Hochschule"',
                    'li:has-text("ETH")',
                    'div:has-text("ETH Zurich")',
                    'button:has-text("ETH Zurich")'
                ]
                
                eth_found = False
                for selector in eth_selectors:
                    try:
                        eth_element = await page.wait_for_selector(selector, timeout=3000)
                        if eth_element:
                            logger.info(f"AMS: Found ETH option with: {selector}")
                            await eth_element.click()
                            await page.wait_for_timeout(3000)
                            eth_found = True
                            break
                    except:
                        continue
                
                if not eth_found:
                    # Try searching for ETH in a search box
                    search_selectors = [
                        'input[type="search"]',
                        'input[placeholder*="institution"]',
                        'input[placeholder*="search"]',
                        'input.institution-search',
                        'input[name="query"]',
                        'input[id*="search"]'
                    ]
                    
                    for selector in search_selectors:
                        try:
                            search_box = await page.wait_for_selector(selector, timeout=3000)
                            if search_box:
                                logger.info("AMS: Found institution search box")
                                await search_box.fill("ETH Zurich")
                                await page.wait_for_timeout(2000)
                                
                                # Press Enter or look for search button
                                await search_box.press("Enter")
                                await page.wait_for_timeout(2000)
                                
                                # Look for ETH in search results
                                eth_result_selectors = [
                                    'text="ETH Zurich"',
                                    'a:has-text("ETH Zurich")',
                                    'button:has-text("ETH Zurich")',
                                    'li:has-text("ETH Zurich")'
                                ]
                                
                                for result_selector in eth_result_selectors:
                                    try:
                                        eth_result = await page.wait_for_selector(result_selector, timeout=5000)
                                        if eth_result:
                                            await eth_result.click()
                                            await page.wait_for_timeout(3000)
                                            eth_found = True
                                            break
                                    except:
                                        continue
                                
                                if eth_found:
                                    break
                        except:
                            continue
                
                # After selecting institution, might need to click "Continue" or "Go"
                if eth_found:
                    continue_selectors = [
                        'button:has-text("Continue")',
                        'button:has-text("Go")',
                        'button:has-text("Proceed")',
                        'button:has-text("Select")',
                        'input[type="submit"]',
                        'button[type="submit"]'
                    ]
                    
                    for selector in continue_selectors:
                        try:
                            continue_button = await page.wait_for_selector(selector, timeout=3000)
                            if continue_button:
                                await continue_button.click()
                                await page.wait_for_timeout(3000)
                                break
                        except:
                            continue
            
            # Handle ETH-specific authentication
            current_url = page.url
            if 'eth' in current_url.lower() or 'ethz' in current_url.lower():
                return await self._handle_eth_login(page)
            
            # Handle generic Shibboleth authentication
            elif 'shibboleth' in current_url.lower():
                return await self._handle_shibboleth_auth(page)
            
            return True  # Assume success if we get here
            
        except Exception as e:
            logger.warning(f"AMS: Institutional authentication error - {e}")
            return False
    
    async def _handle_eth_login(self, page: Page) -> bool:
        """Handle ETH Zurich login page"""
        
        try:
            logger.info("AMS: Handling ETH login")
            
            # Look for username/password fields
            username_selectors = [
                'input[name="username"]',
                'input[name="user"]', 
                'input[type="text"]',
                'input[id*="username"]',
                'input[id*="user"]'
            ]
            
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[id*="password"]'
            ]
            
            username_field = None
            password_field = None
            
            for selector in username_selectors:
                try:
                    username_field = await page.wait_for_selector(selector, timeout=3000)
                    if username_field:
                        break
                except:
                    continue
            
            for selector in password_selectors:
                try:
                    password_field = await page.wait_for_selector(selector, timeout=3000)
                    if password_field:
                        break
                except:
                    continue
            
            if username_field and password_field:
                logger.info("AMS: Found ETH login fields")
                
                # Fill credentials
                await username_field.fill(self.auth_config.username)
                await page.wait_for_timeout(1000)
                await password_field.fill(self.auth_config.password)
                await page.wait_for_timeout(1000)
                
                # Submit form
                submit_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    'input[value*="Login"]'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_button = await page.wait_for_selector(selector, timeout=3000)
                        if submit_button:
                            await submit_button.click()
                            break
                    except:
                        continue
                
                # Wait for authentication to complete
                await page.wait_for_timeout(5000)
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"AMS: ETH login error - {e}")
            return False
    
    async def _handle_shibboleth_auth(self, page: Page) -> bool:
        """Handle generic Shibboleth authentication"""
        
        try:
            logger.info("AMS: Handling Shibboleth authentication")
            return await self._handle_eth_login(page)
            
        except Exception as e:
            logger.warning(f"AMS: Shibboleth auth error - {e}")
            return False
    
    async def _find_and_download_pdf(self, page: Page, save_path: Path) -> bool:
        """Find and download PDF from AMS article page"""
        
        try:
            # AMS PDF download patterns
            pdf_selectors = [
                'a[href$=".pdf"]',
                'a[href*="/pdf/"]',
                'a:has-text("PDF")',
                'a:has-text("Download PDF")',
                'a:has-text("View PDF")',
                'a:has-text("Full Text PDF")',
                'a:has-text("Download")',
                'button:has-text("PDF")',
                'button:has-text("Download")',
                '.pdf-download a',
                '.download-pdf',
                '[data-item="pdf"]',
                'a[title*="PDF"]',
                '.article-tools a[href*="pdf"]',
                'a.pdf-link',
                'a[aria-label*="PDF"]',
                '.article-download a'
            ]
            
            pdf_link = None
            for selector in pdf_selectors:
                try:
                    pdf_element = await page.wait_for_selector(selector, timeout=5000)
                    if pdf_element:
                        # Check if this is actually a PDF link
                        href = await pdf_element.get_attribute('href')
                        text = await pdf_element.inner_text()
                        if (href and ('pdf' in href.lower() or href.endswith('.pdf'))) or 'pdf' in text.lower():
                            pdf_link = pdf_element
                            logger.info(f"AMS: Found PDF link with selector: {selector}")
                            break
                except:
                    continue
            
            if not pdf_link:
                logger.warning("AMS: No PDF download link found")
                # Try alternative approach - look for iframe with PDF
                try:
                    pdf_iframe = await page.wait_for_selector('iframe[src*="pdf"]', timeout=5000)
                    if pdf_iframe:
                        pdf_url = await pdf_iframe.get_attribute('src')
                        if pdf_url:
                            logger.info("AMS: Found PDF in iframe")
                            return await self._download_pdf_from_url(page, pdf_url, save_path)
                except:
                    pass
                
                return False
            
            # Setup download handling
            download_completed = False
            
            async def handle_download(download):
                nonlocal download_completed
                try:
                    await download.save_as(save_path)
                    download_completed = True
                    logger.info(f"AMS: PDF saved to {save_path}")
                except Exception as e:
                    logger.error(f"AMS: Download save failed - {e}")
            
            page.on('download', handle_download)
            
            # Click the PDF download link
            await pdf_link.click()
            
            # Wait for download to complete
            max_wait = 30  # 30 seconds max
            waited = 0
            while waited < max_wait and not download_completed:
                await page.wait_for_timeout(1000)
                waited += 1
            
            return download_completed
            
        except Exception as e:
            logger.error(f"AMS: PDF download failed - {e}")
            return False
    
    async def _download_pdf_from_url(self, page: Page, pdf_url: str, save_path: Path) -> bool:
        """Download PDF directly from URL"""
        
        try:
            # Make sure URL is absolute
            if not pdf_url.startswith('http'):
                base_url = page.url
                from urllib.parse import urljoin
                pdf_url = urljoin(base_url, pdf_url)
            
            # Navigate to PDF URL
            await page.goto(pdf_url, wait_until='domcontentloaded')
            
            # Setup download handling
            download_completed = False
            
            async def handle_download(download):
                nonlocal download_completed
                try:
                    await download.save_as(save_path)
                    download_completed = True
                    logger.info(f"AMS: PDF saved from URL to {save_path}")
                except Exception as e:
                    logger.error(f"AMS: URL download save failed - {e}")
            
            page.on('download', handle_download)
            
            # Wait for download to trigger
            await page.wait_for_timeout(10000)
            
            return download_completed
            
        except Exception as e:
            logger.error(f"AMS: PDF URL download failed - {e}")
            return False
    
    async def search_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for papers on AMS (optional functionality)"""
        
        results = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # AMS search URL (via MathSciNet when available)
                search_url = f"https://mathscinet.ams.org/mathscinet/search/publications.html?pg1=INDI&s1={query}"
                await page.goto(search_url, wait_until='domcontentloaded')
                
                # Parse search results
                article_elements = await page.query_selector_all('.headline')
                
                for element in article_elements[:max_results]:
                    try:
                        title_elem = await element.query_selector('a')
                        
                        if title_elem:
                            title = await title_elem.inner_text()
                            link = await title_elem.get_attribute('href')
                            
                            if link and not link.startswith('http'):
                                link = urljoin('https://mathscinet.ams.org/', link)
                            
                            results.append({
                                'title': title.strip(),
                                'url': link,
                                'source': 'AMS'
                            })
                            
                    except Exception as e:
                        logger.debug(f"AMS: Error parsing search result - {e}")
                        continue
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"AMS: Search failed - {e}")
        
        return results

    def __str__(self):
        return f"AMSPublisher(auth={self.auth_config.institutional_login})"