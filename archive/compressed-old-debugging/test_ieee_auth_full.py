#!/usr/bin/env python3
"""
Full IEEE Authentication Test
=============================

Complete test with credentials.
"""

import asyncio
import logging
import os
from pathlib import Path
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ieee_full")

async def test_full_auth():
    """Test full IEEE authentication flow."""
    
    # Get credentials from environment
    username = os.getenv('ETH_USERNAME')
    password = os.getenv('ETH_PASSWORD')
    
    if not username or not password:
        logger.error("Please set ETH_USERNAME and ETH_PASSWORD environment variables")
        return False
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("ieee_auth_test")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to IEEE
            logger.info("Navigating to IEEE document...")
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Handle cookies
            logger.info("Accepting cookies...")
            accept_button = await page.query_selector('button:has-text("Accept All")')
            if accept_button:
                await accept_button.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in (this opens a modal)
            logger.info("Clicking Institutional Sign In...")
            inst_button = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
            await inst_button.click()
            await page.wait_for_timeout(2000)
            
            # Find the first modal window
            modal = await page.wait_for_selector('ngb-modal-window', timeout=5000)
            
            if modal:
                logger.info("Found modal window, looking for SeamlessAccess button...")
                
                # Click the SeamlessAccess button
                access_button = await modal.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                if access_button:
                    logger.info("Clicking 'Access Through Your Institution' button...")
                    await access_button.click()
                    await page.wait_for_timeout(3000)
                else:
                    logger.error("Could not find the SeamlessAccess button!")
                    return False
            
            # Wait for the SECOND modal (institution selector) to appear
            logger.info("Waiting for institution selector modal...")
            
            try:
                # The modal should contain "Search for your Institution" text
                institution_modal = await page.wait_for_selector('ngb-modal-window:has-text("Search for your Institution")', timeout=10000)
                
                if institution_modal:
                    logger.info("Found institution search modal")
                    
                    # Find the search input INSIDE this modal - it's the first text input
                    all_inputs = await institution_modal.query_selector_all('input')
                    search_input = None
                    
                    for inp in all_inputs:
                        inp_type = await inp.get_attribute('type') or 'text'
                        if inp_type == 'text':
                            search_input = inp
                            break
                    
                    if search_input:
                        logger.info("Found institution search input")
                        await search_input.fill("ETH Zurich")
                        await page.keyboard.press('Enter')
                        await page.wait_for_timeout(2000)
                        logger.info("Searched for ETH Zurich")
                    else:
                        logger.error("Could not find search input in institution modal")
                        return False
                else:
                    logger.error("Institution search modal did not appear")
                    return False
                    
            except Exception as e:
                logger.error(f"Error finding institution modal: {e}")
                return False
            
            await page.wait_for_timeout(2000)
            
            # Click ETH option
            logger.info("Looking for ETH Zurich option...")
            eth_option = await page.wait_for_selector('text="ETH Zurich"', timeout=10000)
            await eth_option.click()
            await page.wait_for_load_state('networkidle')
            
            # Wait for redirect to ETH login
            logger.info("Waiting for redirect to ETH login...")
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            logger.info(f"After clicking ETH, URL is: {current_url}")
            
            # Fill login form
            logger.info("Looking for ETH login form...")
            try:
                username_input = await page.wait_for_selector('input[name="j_username"], input[id="username"], input[name="username"]', timeout=10000)
                logger.info("Found username input field")
                await username_input.fill(username)
                
                password_input = await page.wait_for_selector('input[name="j_password"], input[id="password"], input[type="password"]', timeout=5000)
                await password_input.fill(password)
                logger.info("Filled credentials")
            except Exception as e:
                logger.error(f"Could not find or fill login form: {e}")
                await page.screenshot(path=output_dir / "login_error.png")
                return False
            
            # Submit
            submit_button = await page.query_selector('[type="submit"]')
            await submit_button.click()
            
            # Wait for authentication
            logger.info("Waiting for authentication to complete...")
            await page.wait_for_timeout(5000)
            
            # Check if we're back at IEEE
            current_url = page.url
            logger.info(f"Post-auth URL: {current_url}")
            
            if 'ieee' in current_url:
                doc_id = current_url.split('/document/')[1].split('/')[0] if '/document/' in current_url else None
                
                if doc_id:
                    # Try stamp URL
                    stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                    logger.info(f"Navigating to stamp URL: {stamp_url}")
                    
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
                        logger.info("Stamp page returned HTML, waiting for PDF to load...")
                        await page.wait_for_timeout(5000)
                        
                        # The PDF might be in an iframe
                        pdf_frame = await page.query_selector('iframe#pdf, iframe[src*="pdf"]')
                        if pdf_frame:
                            src = await pdf_frame.get_attribute('src')
                            logger.info(f"Found PDF iframe: {src}")
                            
                            if src and not src.startswith('http'):
                                src = f"https://ieeexplore.ieee.org{src}"
                            
                            pdf_response = await page.goto(src)
                            pdf_content = await pdf_response.body()
                            
                            if pdf_content.startswith(b'%PDF'):
                                logger.info("✅ SUCCESS! Downloaded PDF from iframe")
                                pdf_path = output_dir / "ieee_paper.pdf"
                                with open(pdf_path, 'wb') as f:
                                    f.write(pdf_content)
                                return True
                        
                        # Last resort - take screenshot of what we see
                        await page.screenshot(path=output_dir / "stamp_page.png")
                        logger.error("Could not extract PDF, see stamp_page.png")
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            logger.info("Browser will close in 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_full_auth())
    if success:
        logger.info("✅ IEEE authentication and download successful!")
    else:
        logger.error("❌ IEEE authentication or download failed!")
    exit(0 if success else 1)