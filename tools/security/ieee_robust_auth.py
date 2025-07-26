#!/usr/bin/env python3
"""
IEEE Robust Authentication
==========================

Handles the IEEE modal flow correctly.
"""

import os
import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ieee_robust")

nest_asyncio.apply()

async def ieee_robust_auth():
    """Robust IEEE authentication with proper modal handling."""
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
    
    output_dir = Path("ieee_robust_output")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to IEEE
            logger.info("Step 1: Navigating to IEEE document...")
            await page.goto(ieee_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Handle cookies
            logger.info("Step 2: Accepting cookies...")
            cookie_accept = await page.query_selector('button:has-text("Accept All")')
            if cookie_accept:
                await cookie_accept.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in
            logger.info("Step 3: Clicking Institutional Sign In...")
            inst_link = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
            await inst_link.click()
            await page.wait_for_timeout(3000)  # Wait for modal to appear
            
            # Click the button in the modal (with correct capitalization)
            logger.info("Step 4: Clicking 'Access Through Your Institution' button...")
            # Try the exact button selector from our debug
            access_button = await page.wait_for_selector(
                'button:has-text("Access Through Your Institution")', 
                timeout=10000
            )
            await access_button.click()
            logger.info("Clicked access button, waiting for page load...")
            
            # Wait for navigation to institution selection page
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            logger.info(f"Step 5: Current URL after modal: {current_url}")
            
            # Handle institution search
            if 'seamlessaccess' in current_url or 'wayf' in current_url or 'discovery' in current_url:
                logger.info("Step 6: On institution selection page, searching for ETH...")
                
                # Look for search input
                search_input = None
                search_selectors = [
                    'input[type="search"]',
                    'input[placeholder*="institution"]',
                    'input[placeholder*="organization"]',
                    'input#idpSelectInput',
                    'input.idp-search'
                ]
                
                for selector in search_selectors:
                    try:
                        search_input = await page.wait_for_selector(selector, timeout=3000)
                        if search_input and await search_input.is_visible():
                            logger.info(f"Found search input with selector: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if search_input:
                    await search_input.fill("ETH Zurich")
                    await page.wait_for_timeout(2000)  # Wait for search results
                    
                    # Click on ETH Zurich option
                    logger.info("Step 7: Clicking on ETH Zurich...")
                    eth_option = await page.wait_for_selector('text="ETH Zurich"', timeout=10000)
                    await eth_option.click()
                else:
                    logger.warning("Could not find search input, looking for ETH directly...")
                    eth_option = await page.wait_for_selector('text="ETH Zurich"', timeout=10000)
                    await eth_option.click()
                
                # Wait for redirect to ETH login
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
            
            # Now we should be at ETH login page
            current_url = page.url
            logger.info(f"Step 8: At login page: {current_url}")
            
            if 'ethz' in current_url or 'aai' in current_url:
                logger.info("Step 9: Filling ETH login form...")
                
                # Wait for and fill username
                username_input = await page.wait_for_selector(
                    'input[name="j_username"], input[id="username"], input[name="username"]',
                    timeout=10000
                )
                await username_input.fill(username)
                
                # Fill password
                password_input = await page.wait_for_selector(
                    'input[name="j_password"], input[id="password"], input[name="password"]',
                    timeout=10000
                )
                await password_input.fill(password)
                
                # Submit
                logger.info("Step 10: Submitting login...")
                submit_button = await page.query_selector('[type="submit"]')
                await submit_button.click()
                
                # Wait for authentication to complete
                logger.info("Step 11: Waiting for authentication...")
                await page.wait_for_timeout(5000)
                
                # Check if we're back at IEEE
                current_url = page.url
                logger.info(f"Step 12: Post-auth URL: {current_url}")
                
                if 'ieee' in current_url:
                    logger.info("✅ Successfully authenticated and returned to IEEE!")
                    
                    # Extract document ID and try to download PDF
                    doc_id = None
                    if '/document/' in current_url:
                        doc_id = current_url.split('/document/')[1].split('/')[0]
                    
                    if doc_id:
                        stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                        logger.info(f"Step 13: Trying stamp URL: {stamp_url}")
                        
                        response = await page.goto(stamp_url, wait_until='networkidle')
                        content = await response.body()
                        
                        if content.startswith(b'%PDF'):
                            logger.info("✅ SUCCESS! Downloaded PDF directly")
                            pdf_path = output_dir / "ieee_paper.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            logger.info(f"PDF saved to: {pdf_path}")
                            return True
                        else:
                            logger.info("Stamp page returned HTML, checking for PDF iframe...")
                            await page.wait_for_timeout(3000)
                            
                            # Look for PDF in iframe
                            pdf_frame = await page.query_selector('iframe#pdf, iframe[src*="pdf"]')
                            if pdf_frame:
                                src = await pdf_frame.get_attribute('src')
                                if src and not src.startswith('http'):
                                    src = f"https://ieeexplore.ieee.org{src}"
                                
                                logger.info(f"Found PDF iframe: {src}")
                                pdf_response = await page.goto(src)
                                pdf_content = await pdf_response.body()
                                
                                if pdf_content.startswith(b'%PDF'):
                                    logger.info("✅ SUCCESS! Downloaded PDF from iframe")
                                    pdf_path = output_dir / "ieee_paper.pdf"
                                    with open(pdf_path, 'wb') as f:
                                        f.write(pdf_content)
                                    return True
                            
                            await page.screenshot(path=output_dir / "stamp_page.png")
                            logger.error("Could not extract PDF from stamp page")
                else:
                    logger.error(f"Not redirected back to IEEE, stuck at: {current_url}")
            else:
                logger.error(f"Not at ETH login page, current URL: {current_url}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path=output_dir / f"error_{e.__class__.__name__}.png")
            return False
        finally:
            logger.info("Browser will stay open for 15 seconds for inspection...")
            await asyncio.sleep(15)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(ieee_robust_auth())
    if success:
        logger.info("✅ IEEE authentication and download successful!")
    else:
        logger.error("❌ IEEE authentication or download failed!")
    exit(0 if success else 1)