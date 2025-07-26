#!/usr/bin/env python3
"""
IEEE Final Test
===============

Comprehensive test with all fixes applied.
"""

import os
import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ieee_final")

nest_asyncio.apply()

async def final_ieee_test():
    """Final comprehensive IEEE test."""
    from playwright.async_api import async_playwright
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        logger.error("No ETH credentials found!")
        return False
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("ieee_final_output")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        # Use headless=False to see what's happening
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to IEEE
            logger.info("Navigating to IEEE document...")
            await page.goto(ieee_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Handle cookies
            logger.info("Handling cookie consent...")
            accept_button = await page.query_selector('button:has-text("Accept All")')
            if accept_button:
                await accept_button.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in
            logger.info("Clicking Institutional Sign In...")
            inst_button = await page.wait_for_selector('text="Institutional Sign In"', timeout=10000)
            await inst_button.click()
            await page.wait_for_timeout(2000)
            
            # Click "Access through your institution"
            logger.info("Looking for 'Access through your institution'...")
            access_button = await page.wait_for_selector('text="Access through your institution"', timeout=10000)
            await access_button.click()
            await page.wait_for_load_state('networkidle')
            
            # Search for ETH
            logger.info("Searching for ETH Zurich...")
            search_input = await page.wait_for_selector('input[type="search"], input[placeholder*="institution"]', timeout=10000)
            await search_input.fill("ETH Zurich")
            await page.wait_for_timeout(1000)
            
            # Click ETH result
            eth_option = await page.wait_for_selector('text="ETH Zurich"', timeout=10000)
            await eth_option.click()
            await page.wait_for_load_state('networkidle')
            
            # Fill login form
            logger.info("Filling ETH login form...")
            await page.wait_for_selector('input[name="j_username"], input[id="username"]', timeout=10000)
            await page.fill('input[name="j_username"], input[id="username"]', username)
            await page.fill('input[name="j_password"], input[id="password"]', password)
            
            # Submit
            submit_button = await page.query_selector('[type="submit"]')
            await submit_button.click()
            
            # Wait for authentication
            logger.info("Waiting for authentication to complete...")
            await page.wait_for_timeout(5000)
            
            # Check if we're back at IEEE
            current_url = page.url
            logger.info(f"Current URL: {current_url}")
            
            if 'ieee' in current_url:
                doc_id = current_url.split('/document/')[1].split('/')[0] if '/document/' in current_url else None
                
                if doc_id:
                    # Try direct PDF access
                    stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                    logger.info(f"Trying stamp URL: {stamp_url}")
                    
                    response = await page.goto(stamp_url, wait_until='networkidle')
                    content = await response.body()
                    
                    if content.startswith(b'%PDF'):
                        logger.info("✅ SUCCESS! Got PDF")
                        pdf_path = output_dir / "ieee_paper.pdf"
                        with open(pdf_path, 'wb') as f:
                            f.write(content)
                        logger.info(f"Saved to: {pdf_path}")
                        return True
                    else:
                        logger.info("Stamp page returned HTML, checking for PDF viewer...")
                        
                        # Wait a bit for PDF to load
                        await page.wait_for_timeout(5000)
                        
                        # Check all iframes
                        iframes = await page.query_selector_all('iframe')
                        logger.info(f"Found {len(iframes)} iframes")
                        
                        for i, iframe in enumerate(iframes):
                            src = await iframe.get_attribute('src')
                            logger.debug(f"Iframe {i}: {src}")
                            
                            if src and ('pdf' in src.lower() or 'getPDF' in src):
                                if not src.startswith('http'):
                                    src = f"https://ieeexplore.ieee.org{src}"
                                
                                logger.info(f"Trying PDF URL: {src}")
                                pdf_response = await page.goto(src)
                                pdf_content = await pdf_response.body()
                                
                                if pdf_content.startswith(b'%PDF'):
                                    logger.info("✅ SUCCESS! Got PDF from iframe")
                                    pdf_path = output_dir / "ieee_paper.pdf"
                                    with open(pdf_path, 'wb') as f:
                                        f.write(pdf_content)
                                    return True
            
            logger.error("Failed to download PDF")
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            logger.info("Test complete. Browser closing in 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(final_ieee_test())
    if success:
        logger.info("✅ IEEE test PASSED!")
    else:
        logger.error("❌ IEEE test FAILED!")
    exit(0 if success else 1)