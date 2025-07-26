#!/usr/bin/env python3
"""
Focused SIAM Test
================

Quick focused SIAM download test.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("focused_siam")

nest_asyncio.apply()

async def focused_siam_test():
    from playwright.async_api import async_playwright
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    output_dir = Path("focused_siam")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Direct SIAM URL (DOI redirect times out)
            siam_url = "https://epubs.siam.org/doi/10.1137/S0036142997325199"
            logger.info(f"Going to SIAM DOI: {siam_url}")
            
            await page.goto(siam_url, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(3000)
            
            logger.info("✅ Connected to SIAM page")
            
            # Look for authentication options
            auth_selectors = [
                'a:has-text("Access via your Institution")',
                'a:has-text("Institutional Access")',
                'a[href*="ssostart"]',
                'a:has-text("Sign In")'
            ]
            
            auth_found = False
            for selector in auth_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        href = await element.get_attribute('href')
                        logger.info(f"Found auth option: '{text}' -> {href}")
                        
                        # Click it
                        await element.click()
                        await page.wait_for_timeout(3000)
                        auth_found = True
                        break
                except Exception as e:
                    continue
            
            if not auth_found:
                logger.error("No authentication options found")
                return False
            
            logger.info("✅ Clicked institutional access")
            
            # Wait for institution selector page
            await page.wait_for_timeout(5000)
            current_url = page.url
            logger.info(f"Current URL: {current_url}")
            
            # Look for institution search/selector
            if 'ssostart' in current_url or 'discovery' in current_url or 'wayf' in current_url:
                logger.info("At institution selection page")
                
                # Look for the Shibboleth institution search field (input inside the container)
                try:
                    search_input = await page.wait_for_selector('#shibboleth_search input', timeout=10000)
                    logger.info("Found Shibboleth search input field")
                    
                    # Type ETH Zurich
                    await search_input.fill("ETH Zurich")
                    logger.info("Filled ETH Zurich")
                    await page.wait_for_timeout(2000)
                    
                    # Press Enter to search (skip dropdown search for now)
                    await search_input.press('Enter')
                    logger.info("Pressed Enter on institution search")
                    
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.error(f"Failed to find/use institution search: {e}")
                
                # Check if we're now at ETH login
                await page.wait_for_timeout(3000)
                current_url = page.url
                logger.info(f"After institution selection: {current_url}")
            
            if 'ethz' in current_url or 'aai' in current_url:
                logger.info("At ETH login page")
                
                await page.fill('[name="j_username"], [id="username"]', username)
                await page.fill('[name="j_password"], [id="password"]', password)
                
                submit = await page.query_selector('[type="submit"]')
                await submit.click()
                
                logger.info("Submitted login, waiting for redirect...")
                await page.wait_for_timeout(8000)
                
                current_url = page.url
                logger.info(f"After login URL: {current_url}")
                
                if 'siam' in current_url:
                    logger.info("🎉 SIAM AUTHENTICATION SUCCESSFUL!")
                    
                    # Look for PDF download
                    pdf_selectors = [
                        'a:has-text("PDF")',
                        'button:has-text("PDF")',
                        'a[href*=".pdf"]',
                        '[href*="pdf"]'
                    ]
                    
                    for selector in pdf_selectors:
                        try:
                            pdf_element = await page.query_selector(selector)
                            if pdf_element:
                                text = await pdf_element.text_content()
                                href = await pdf_element.get_attribute('href')
                                logger.info(f"Found PDF option: '{text}' -> {href}")
                                
                                # Try to download
                                if href:
                                    if not href.startswith('http'):
                                        href = f"https://epubs.siam.org{href}"
                                    
                                    logger.info(f"Attempting PDF download: {href}")
                                    pdf_response = await page.goto(href, timeout=30000)
                                    content = await pdf_response.body()
                                    
                                    if content.startswith(b'%PDF'):
                                        pdf_path = output_dir / "SIAM_PAPER.pdf"
                                        with open(pdf_path, 'wb') as f:
                                            f.write(content)
                                        
                                        if pdf_path.exists():
                                            file_size = pdf_path.stat().st_size
                                            logger.info(f"🏆 SIAM PDF SAVED: {pdf_path}")
                                            logger.info(f"📊 Size: {file_size} bytes")
                                            return True
                                
                                break
                        except Exception as e:
                            continue
                    
                    logger.info("No direct PDF links found, trying alternative approach")
                    return False
                else:
                    logger.error(f"Auth failed, at: {current_url}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Browser open for 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(focused_siam_test())
    if success:
        logger.info("🏆 SIAM DOWNLOAD SUCCESSFUL!")
    else:
        logger.error("💥 SIAM download failed")