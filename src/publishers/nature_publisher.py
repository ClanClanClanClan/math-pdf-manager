#!/usr/bin/env python3
"""
Nature Publishing Group Publisher
=================================

Implementation for downloading papers from Nature journals with institutional access.
Covers Nature, Nature Materials, Nature Physics, etc.
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

class NaturePublisher:
    """Nature Publishing Group publisher with browser automation"""
    
    def __init__(self, auth_config: AuthenticationConfig):
        self.auth_config = auth_config
        self.base_urls = [
            "https://www.nature.com/",
            "https://link.springer.com/",  # Nature articles often redirect here
        ]
        self.session_data = {}
        
    def can_handle_url(self, url: str) -> bool:
        """Check if this publisher can handle the given URL"""
        return any(domain in url.lower() for domain in [
            'nature.com',
            'link.springer.com/article/',
            'doi.org'
        ]) and any(journal in url.lower() for journal in [
            'nature',
            'npg',
            'nmat',  # Nature Materials
            'nphys', # Nature Physics
            'nchembio', # Nature Chemical Biology
        ])
    
    def can_handle_doi(self, doi: str) -> bool:
        """Check if this publisher can handle the given DOI - IMPROVED VERSION"""
        import re
        
        # Clean the DOI
        clean_doi = doi.strip().lower()
        
        # Check basic format
        if not re.match(r'^10\.\d{4,}\/.*', clean_doi):
            return False
        
        # Nature-specific sophisticated patterns
        patterns = [
            r"10\.1038\/nature\d{5}",                          # Nature main journal
            r"10\.1038\/s\d{5}-\d{3}-\d{4}-\d",                # Nature Scientific Reports format
            r"10\.1038\/[a-z]{2,8}\.\d{4}\.\d{1,4}",          # Nature subject journals
            r"10\.1038\/[a-z]{2,8}\d{4}",                      # Compact nature format
            r"10\.1038\/[a-z]{3,10}[0-9]{2,4}",               # Mixed alpha-numeric
        ]
        
        for pattern in patterns:
            if re.match(pattern, clean_doi, re.IGNORECASE):
                return True
        
        return False
    
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
                target_url = f"https://www.nature.com/articles/{paper_identifier}"
            
            logger.info(f"Nature: Starting download for {target_url}")
            
            # Use browser automation for institutional access
            result = await self._browser_institutional_download(target_url, save_path)
            
            if result.success:
                result.download_time = time.time() - start_time
                logger.info(f"Nature: Successfully downloaded in {result.download_time:.1f}s")
            else:
                logger.warning(f"Nature: Download failed - {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Nature: Download error - {e}")
            return DownloadResult(
                success=False,
                error_message=f"Nature download failed: {str(e)}"
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
                logger.info(f"Nature: Navigating to {target_url}")
                await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Check if we need institutional access
                page_content = await page.content()
                current_url = page.url
                
                if any(indicator in page_content.lower() for indicator in [
                    'institutional access', 'subscribe', 'purchase', 'paywall',
                    'login', 'sign in', 'access through'
                ]):
                    logger.info("Nature: Institutional access required")
                    
                    # Look for institutional access link
                    access_selectors = [
                        'a[href*="institutional"]',
                        'a[href*="shibboleth"]', 
                        'a[href*="institution"]',
                        'text="Access through your institution"',
                        'text="Institutional access"'
                    ]
                    
                    institutional_link = None
                    for selector in access_selectors:
                        try:
                            element = await page.wait_for_selector(selector, timeout=5000)
                            if element:
                                institutional_link = element
                                break
                        except:
                            continue
                    
                    if institutional_link:
                        logger.info("Nature: Found institutional access link")
                        await institutional_link.click()
                        await page.wait_for_timeout(3000)
                        
                        # Handle ETH institutional authentication 
                        if await self._handle_eth_authentication(page):
                            logger.info("Nature: ETH authentication successful")
                        else:
                            logger.warning("Nature: ETH authentication may have failed")
                    else:
                        logger.warning("Nature: No institutional access link found")
                
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
                                logger.info(f"Nature: PDF successfully downloaded to {save_path}")
                                return DownloadResult(
                                    success=True,
                                    file_path=save_path
                                )
                
                return DownloadResult(
                    success=False,
                    error_message="Could not download PDF from Nature"
                )
                
            finally:
                await browser.close()
    
    async def _handle_eth_authentication(self, page: Page) -> bool:
        """Handle ETH Zurich institutional authentication"""
        
        try:
            # Wait for ETH login page or similar
            await page.wait_for_timeout(3000)
            current_url = page.url
            page_content = await page.content()
            
            logger.info(f"Nature ETH auth: Current URL is {current_url}")
            
            # Look for ETH-specific authentication
            if 'eth' in current_url.lower() or 'ethz' in current_url.lower():
                logger.info("Nature: On ETH authentication page")
                
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
                    'input[name="pass"]',
                    'input[type="password"]',
                    'input[id*="password"]',
                    'input[id*="pass"]'
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
                    logger.info("Nature: Found ETH login fields")
                    
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
                    
                    # Check if we're back to the article or still on auth page
                    new_url = page.url
                    if new_url != current_url and 'nature.com' in new_url:
                        logger.info("Nature: ETH authentication appears successful")
                        return True
            
            # Alternative: Look for Shibboleth-style authentication
            elif 'shibboleth' in current_url.lower() or 'wayf' in current_url.lower():
                logger.info("Nature: On Shibboleth authentication page")
                
                # Look for ETH in the institution list
                eth_selectors = [
                    'text="ETH Zurich"',
                    'text="Swiss Federal Institute"',
                    'text="Eidgenössische Technische Hochschule"',
                    'option:has-text("ETH")',
                    'a:has-text("ETH")'
                ]
                
                for selector in eth_selectors:
                    try:
                        eth_option = await page.wait_for_selector(selector, timeout=3000)
                        if eth_option:
                            await eth_option.click()
                            await page.wait_for_timeout(3000)
                            return await self._handle_eth_authentication(page)  # Recursive call
                    except:
                        continue
            
            return False
            
        except Exception as e:
            logger.warning(f"Nature: ETH authentication error - {e}")
            return False
    
    async def _find_and_download_pdf(self, page: Page, save_path: Path) -> bool:
        """Find and download PDF from Nature article page"""
        
        try:
            # Nature PDF download patterns
            pdf_selectors = [
                'a[href$=".pdf"]',
                'a[href*="/pdf/"]',
                'a:has-text("Download PDF")',
                'a:has-text("PDF")',
                'button:has-text("Download PDF")',
                '.pdf-download a',
                '.c-pdf-download a',
                '[data-track-action="download pdf"]'
            ]
            
            pdf_link = None
            for selector in pdf_selectors:
                try:
                    pdf_element = await page.wait_for_selector(selector, timeout=5000)
                    if pdf_element:
                        pdf_link = pdf_element
                        logger.info(f"Nature: Found PDF link with selector: {selector}")
                        break
                except:
                    continue
            
            if not pdf_link:
                logger.warning("Nature: No PDF download link found")
                return False
            
            # Setup download handling
            download_completed = False
            
            async def handle_download(download):
                nonlocal download_completed
                try:
                    await download.save_as(save_path)
                    download_completed = True
                    logger.info(f"Nature: PDF saved to {save_path}")
                except Exception as e:
                    logger.error(f"Nature: Download save failed - {e}")
            
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
            logger.error(f"Nature: PDF download failed - {e}")
            return False
    
    async def search_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for papers on Nature (optional functionality)"""
        
        results = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Nature search URL
                search_url = f"https://www.nature.com/search?q={query}"
                await page.goto(search_url, wait_until='domcontentloaded')
                
                # Parse search results (basic implementation)
                article_elements = await page.query_selector_all('article')
                
                for element in article_elements[:max_results]:
                    try:
                        title_elem = await element.query_selector('h3 a, h2 a, .title a')
                        link_elem = await element.query_selector('a[href*="/articles/"]')
                        
                        if title_elem and link_elem:
                            title = await title_elem.inner_text()
                            link = await link_elem.get_attribute('href')
                            
                            if link and not link.startswith('http'):
                                link = urljoin('https://www.nature.com/', link)
                            
                            results.append({
                                'title': title.strip(),
                                'url': link,
                                'source': 'Nature'
                            })
                            
                    except Exception as e:
                        logger.debug(f"Nature: Error parsing search result - {e}")
                        continue
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Nature: Search failed - {e}")
        
        return results

    def __str__(self):
        return f"NaturePublisher(auth={self.auth_config.institutional_login})"