#!/usr/bin/env python3
"""
Wiley Publisher
===============

Implementation for downloading papers from Wiley journals with institutional access.
Covers Wiley Online Library, journals like Science, Advanced Materials, etc.
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

class WileyPublisher:
    """Wiley publisher with browser automation for institutional access"""
    
    def __init__(self, auth_config: AuthenticationConfig):
        self.auth_config = auth_config
        self.base_urls = [
            "https://onlinelibrary.wiley.com/",
            "https://www.wiley.com/",
        ]
        self.session_data = {}
        
    def can_handle_url(self, url: str) -> bool:
        """Check if this publisher can handle the given URL"""
        return any(domain in url.lower() for domain in [
            'onlinelibrary.wiley.com',
            'wiley.com',
            'doi.org'
        ])
    
    def can_handle_doi(self, doi: str) -> bool:
        """Check if this publisher can handle the given DOI"""
        return any(prefix in doi.lower() for prefix in [
            '10.1002/',  # Main Wiley DOI prefix
            '10.1111/',  # Another Wiley prefix
            '10.1046/',  # Older Wiley prefix
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
                # Assume it's a Wiley article ID
                target_url = f"https://onlinelibrary.wiley.com/doi/{paper_identifier}"
            
            logger.info(f"Wiley: Starting download for {target_url}")
            
            # Use browser automation for institutional access
            result = await self._browser_institutional_download(target_url, save_path)
            
            if result.success:
                result.download_time = time.time() - start_time
                logger.info(f"Wiley: Successfully downloaded in {result.download_time:.1f}s")
            else:
                logger.warning(f"Wiley: Download failed - {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Wiley: Download error - {e}")
            return DownloadResult(
                success=False,
                error_message=f"Wiley download failed: {str(e)}"
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
                logger.info(f"Wiley: Navigating to {target_url}")
                await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Handle cookie banner if present
                try:
                    cookie_banner = await page.wait_for_selector('button:has-text("Accept All"), button:has-text("Accept Cookies")', timeout=5000)
                    if cookie_banner:
                        logger.info("Wiley: Accepting cookies")
                        await cookie_banner.click()
                        await page.wait_for_timeout(2000)
                except:
                    pass
                
                # Check if we need institutional access
                page_content = await page.content()
                current_url = page.url
                
                if any(indicator in page_content.lower() for indicator in [
                    'institutional access', 'subscribe', 'purchase', 'paywall',
                    'login', 'sign in', 'access through your institution',
                    'get access', 'rent or buy'
                ]):
                    logger.info("Wiley: Institutional access required")
                    
                    # First check if we need to click Login/Register button to reveal options
                    try:
                        login_button = await page.wait_for_selector('button:has-text("Login / Register")', timeout=5000)
                        if login_button and await login_button.is_visible():
                            logger.info("Wiley: Clicking Login/Register button to reveal options")
                            await login_button.click()
                            await page.wait_for_timeout(2000)
                    except:
                        pass
                    
                    # Try INDIVIDUAL login first (avoids Cloudflare)
                    individual_selectors = [
                        'a:has-text("Individual login")',
                        'a[href*="showLogin"]'
                    ]
                    
                    individual_link = None
                    for selector in individual_selectors:
                        try:
                            element = await page.wait_for_selector(selector, timeout=3000)
                            if element and await element.is_visible():
                                individual_link = element
                                logger.info(f"Wiley: Found individual login with: {selector}")
                                break
                        except:
                            continue
                    
                    if individual_link:
                        logger.info("Wiley: Trying individual login first")
                        await individual_link.click()
                        await page.wait_for_timeout(3000)
                        
                        # Try to use ETH credentials for individual login
                        if await self._handle_individual_login(page):
                            logger.info("Wiley: Individual login successful")
                        else:
                            logger.warning("Wiley: Individual login failed, falling back to institutional")
                            # Go back and try institutional
                            await page.go_back()
                            await page.wait_for_timeout(2000)
                    
                    # If individual login failed, try institutional access options
                    access_selectors = [
                        'a:has-text("Institutional login")',  # Note lowercase 'login'
                        'a:has-text("Login / Register")',
                        'a:has-text("Access through your institution")',
                        'a:has-text("Institutional Login")',
                        'a[href*="institutional"]',
                        'a[href*="shibboleth"]',
                        'a[href*="ssostart"]',  # SSO start URL
                        'button:has-text("Institution")',
                        '.institutional-access a',
                        '[data-access-type="institutional"]'
                    ]
                    
                    institutional_link = None
                    for selector in access_selectors:
                        try:
                            element = await page.wait_for_selector(selector, timeout=5000)
                            if element and await element.is_visible():
                                institutional_link = element
                                logger.info(f"Wiley: Found institutional access with: {selector}")
                                break
                        except:
                            continue
                    
                    if institutional_link:
                        logger.info("Wiley: Clicking institutional access")
                        await institutional_link.click()
                        await page.wait_for_timeout(3000)
                        
                        # Handle institutional authentication flow
                        if await self._handle_institutional_authentication(page):
                            logger.info("Wiley: Institutional authentication successful")
                        else:
                            logger.warning("Wiley: Institutional authentication may have failed")
                    else:
                        logger.warning("Wiley: No institutional access link found")
                
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
                                logger.info(f"Wiley: PDF successfully downloaded to {save_path}")
                                return DownloadResult(
                                    success=True,
                                    file_path=save_path
                                )
                
                return DownloadResult(
                    success=False,
                    error_message="Could not download PDF from Wiley"
                )
                
            finally:
                await browser.close()
    
    async def _handle_institutional_authentication(self, page: Page) -> bool:
        """Handle institutional authentication (ETH Zurich or generic)"""
        
        try:
            await page.wait_for_timeout(3000)
            current_url = page.url
            page_content = await page.content()
            
            logger.info(f"Wiley auth: Current URL is {current_url}")
            
            # Check if we're on a Wiley institutional selection page
            if 'wiley.com' in current_url and ('wayf' in current_url or 'institution' in current_url or 'ssostart' in current_url):
                logger.info("Wiley: On institutional selection page")
                
                # First try to find a search box for institutions
                search_found = False
                search_selectors = [
                    'input[type="search"]',
                    'input[placeholder*="institution"]',
                    'input[placeholder*="search"]',
                    'input[name*="search"]',
                    'input[id*="search"]',
                    'input.institution-search'
                ]
                
                for selector in search_selectors:
                    try:
                        search_box = await page.wait_for_selector(selector, timeout=3000)
                        if search_box:
                            logger.info(f"Wiley: Found institution search box")
                            await search_box.fill("ETH Zurich")
                            await page.wait_for_timeout(2000)
                            
                            # Try to press Enter or find search button
                            await search_box.press("Enter")
                            await page.wait_for_timeout(3000)
                            search_found = True
                            break
                    except:
                        continue
                
                # Look for ETH in the institution dropdown/list
                eth_selectors = [
                    'option:has-text("ETH Zurich")',
                    'option:has-text("Swiss Federal Institute")',
                    'a:has-text("ETH Zurich")',
                    'text="ETH Zurich"',
                    'text="Swiss Federal Institute of Technology"',
                    'button:has-text("ETH")',
                    'li:has-text("ETH Zurich")',
                    'div:has-text("ETH Zurich"):not(:has-text("Search"))'
                ]
                
                eth_found = False
                for selector in eth_selectors:
                    try:
                        eth_element = await page.wait_for_selector(selector, timeout=5000)
                        if eth_element and await eth_element.is_visible():
                            logger.info(f"Wiley: Found ETH option with: {selector}")
                            await eth_element.click()
                            await page.wait_for_timeout(3000)
                            eth_found = True
                            break
                    except:
                        continue
                
                if not eth_found:
                    logger.warning("Wiley: Could not find ETH in institution list")
                
                # After selecting institution, might need to click "Go" or "Continue"
                continue_selectors = [
                    'button:has-text("Go")',
                    'button:has-text("Continue")',
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
            logger.warning(f"Wiley: Institutional authentication error - {e}")
            return False
    
    async def _handle_individual_login(self, page: Page) -> bool:
        """Handle Wiley individual login (avoids Cloudflare)"""
        
        try:
            logger.info("Wiley: Handling individual login")
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            logger.info(f"Wiley individual login URL: {current_url}")
            
            # Look for username/password fields on individual login page
            username_selectors = [
                'input[name="loginId"]',
                'input[name="username"]',
                'input[name="email"]',
                'input[type="email"]',
                'input[type="text"]',
                'input[id*="username"]',
                'input[id*="login"]'
            ]
            
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[id*="password"]'
            ]
            
            username_field = None
            password_field = None
            
            # Find username field
            for selector in username_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=3000)
                    if field and await field.is_visible():
                        username_field = field
                        logger.info(f"Wiley: Found username field with: {selector}")
                        break
                except:
                    continue
            
            # Find password field
            for selector in password_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=3000)
                    if field and await field.is_visible():
                        password_field = field
                        logger.info(f"Wiley: Found password field with: {selector}")
                        break
                except:
                    continue
            
            if username_field and password_field:
                logger.info("Wiley: Attempting individual login with ETH credentials")
                
                # Try using ETH email format
                eth_email = f"{self.auth_config.username}@student.ethz.ch"
                
                await username_field.fill(eth_email)
                await page.wait_for_timeout(1000)
                await password_field.fill(self.auth_config.password)
                await page.wait_for_timeout(1000)
                
                # Find and click submit button
                submit_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'button:has-text("Sign in")',
                    'button:has-text("Login")',
                    'button:has-text("Log in")',
                    'input[value*="Login"]',
                    'input[value*="Sign"]'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_btn = await page.wait_for_selector(selector, timeout=3000)
                        if submit_btn and await submit_btn.is_visible():
                            logger.info(f"Wiley: Clicking submit with: {selector}")
                            await submit_btn.click()
                            await page.wait_for_timeout(5000)
                            break
                    except:
                        continue
                
                # Check if login was successful
                new_url = page.url
                if current_url != new_url or 'error' not in page.url.lower():
                    logger.info("Wiley: Individual login appears successful")
                    return True
                else:
                    logger.warning("Wiley: Individual login appears to have failed")
                    return False
            else:
                logger.warning("Wiley: Could not find username/password fields for individual login")
                return False
                
        except Exception as e:
            logger.error(f"Wiley: Individual login error - {e}")
            return False
    
    async def _handle_eth_login(self, page: Page) -> bool:
        """Handle ETH Zurich login page"""
        
        try:
            logger.info("Wiley: Handling ETH login")
            
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
                logger.info("Wiley: Found ETH login fields")
                
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
            logger.warning(f"Wiley: ETH login error - {e}")
            return False
    
    async def _handle_shibboleth_auth(self, page: Page) -> bool:
        """Handle generic Shibboleth authentication"""
        
        try:
            logger.info("Wiley: Handling Shibboleth authentication")
            
            # Similar to ETH login but more generic
            # This would handle other institutional logins
            return await self._handle_eth_login(page)
            
        except Exception as e:
            logger.warning(f"Wiley: Shibboleth auth error - {e}")
            return False
    
    async def _find_and_download_pdf(self, page: Page, save_path: Path) -> bool:
        """Find and download PDF from Wiley article page"""
        
        try:
            # Wiley PDF download patterns
            pdf_selectors = [
                'a[href$=".pdf"]',
                'a[href*="/pdf/"]',
                'a:has-text("PDF")',
                'a:has-text("Download PDF")',
                'a:has-text("View PDF")',
                'button:has-text("PDF")',
                '.pdf-download a',
                '.article-download-pdf-link',
                '[data-item="pdf"]',
                'a[title*="PDF"]'
            ]
            
            pdf_link = None
            for selector in pdf_selectors:
                try:
                    pdf_element = await page.wait_for_selector(selector, timeout=5000)
                    if pdf_element:
                        # Check if this is actually a PDF link
                        href = await pdf_element.get_attribute('href')
                        if href and ('pdf' in href.lower() or href.endswith('.pdf')):
                            pdf_link = pdf_element
                            logger.info(f"Wiley: Found PDF link with selector: {selector}")
                            break
                except:
                    continue
            
            if not pdf_link:
                logger.warning("Wiley: No PDF download link found")
                # Try alternative approach - look for iframe with PDF
                try:
                    pdf_iframe = await page.wait_for_selector('iframe[src*="pdf"]', timeout=5000)
                    if pdf_iframe:
                        pdf_url = await pdf_iframe.get_attribute('src')
                        if pdf_url:
                            logger.info("Wiley: Found PDF in iframe")
                            # Download directly from iframe src
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
                    logger.info(f"Wiley: PDF saved to {save_path}")
                except Exception as e:
                    logger.error(f"Wiley: Download save failed - {e}")
            
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
            logger.error(f"Wiley: PDF download failed - {e}")
            return False
    
    async def _download_pdf_from_url(self, page: Page, pdf_url: str, save_path: Path) -> bool:
        """Download PDF directly from URL"""
        
        try:
            # Navigate to PDF URL and download
            await page.goto(pdf_url, wait_until='domcontentloaded')
            
            # The PDF should trigger a download
            download_completed = False
            
            async def handle_download(download):
                nonlocal download_completed
                try:
                    await download.save_as(save_path)
                    download_completed = True
                    logger.info(f"Wiley: PDF saved from URL to {save_path}")
                except Exception as e:
                    logger.error(f"Wiley: URL download save failed - {e}")
            
            page.on('download', handle_download)
            
            # Wait for download
            await page.wait_for_timeout(10000)
            
            return download_completed
            
        except Exception as e:
            logger.error(f"Wiley: PDF URL download failed - {e}")
            return False
    
    async def search_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for papers on Wiley (optional functionality)"""
        
        results = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Wiley search URL
                search_url = f"https://onlinelibrary.wiley.com/action/doSearch?AllField={query}"
                await page.goto(search_url, wait_until='domcontentloaded')
                
                # Parse search results
                article_elements = await page.query_selector_all('.item__body')
                
                for element in article_elements[:max_results]:
                    try:
                        title_elem = await element.query_selector('.visitable')
                        link_elem = await element.query_selector('a[href*="/doi/"]')
                        
                        if title_elem and link_elem:
                            title = await title_elem.inner_text()
                            link = await link_elem.get_attribute('href')
                            
                            if link and not link.startswith('http'):
                                link = urljoin('https://onlinelibrary.wiley.com/', link)
                            
                            results.append({
                                'title': title.strip(),
                                'url': link,
                                'source': 'Wiley'
                            })
                            
                    except Exception as e:
                        logger.debug(f"Wiley: Error parsing search result - {e}")
                        continue
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Wiley: Search failed - {e}")
        
        return results

    def __str__(self):
        return f"WileyPublisher(auth={self.auth_config.institutional_login})"