#!/usr/bin/env python3
"""
Debug IEEE Authentication Flow
==============================

Complete authentication flow for IEEE with detailed debugging.
"""

import os
import asyncio
import nest_asyncio
import logging
from datetime import datetime
from pathlib import Path

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ieee_auth_debug")

# Apply nest_asyncio
nest_asyncio.apply()

# Get ETH credentials from environment
ETH_USERNAME = os.getenv("ETH_USERNAME", "")
ETH_PASSWORD = os.getenv("ETH_PASSWORD", "")

if not ETH_USERNAME or not ETH_PASSWORD:
    logger.error("ETH credentials not found in environment!")
    exit(1)

logger.info(f"ETH Username: {ETH_USERNAME}")

async def debug_ieee_auth():
    """Debug IEEE authentication and download flow."""
    from playwright.async_api import async_playwright
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    debug_dir = Path("ieee_auth_debug")
    debug_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        # Launch browser in visible mode
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: logger.debug(f"Console: {msg.text}"))
        
        try:
            # Step 1: Go to IEEE document
            logger.info("Step 1: Navigating to IEEE document...")
            await page.goto(ieee_url, wait_until='networkidle')
            await page.screenshot(path=debug_dir / "01_initial.png")
            
            doc_id = page.url.split('/document/')[1].split('/')[0] if '/document/' in page.url else None
            logger.info(f"Document ID: {doc_id}")
            
            # Step 2: Click institutional sign in
            logger.info("Step 2: Looking for institutional sign in...")
            inst_button = await page.query_selector('text="Institutional Sign In"')
            if inst_button:
                logger.info("Found institutional sign in button, clicking...")
                await inst_button.click()
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=debug_dir / "02_after_inst_click.png")
            
            # Step 3: Look for institution selection
            logger.info("Step 3: Looking for institution selection...")
            await page.wait_for_timeout(2000)  # Give page time to load
            
            # Check current URL
            current_url = page.url
            logger.info(f"Current URL: {current_url}")
            
            # Look for ETH option
            eth_selectors = [
                'text="ETH Zurich"',
                'text="Swiss Federal Institute"',
                'option:has-text("ETH")',
                '[value*="ethz"]',
                'a:has-text("ETH")'
            ]
            
            eth_found = False
            for selector in eth_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.info(f"Found ETH option with selector: {selector}")
                    await element.click()
                    eth_found = True
                    await page.wait_for_load_state('networkidle')
                    await page.screenshot(path=debug_dir / "03_after_eth_select.png")
                    break
            
            if not eth_found:
                # Try searching for ETH
                search_box = await page.query_selector('input[placeholder*="Search"], input[type="search"]')
                if search_box:
                    logger.info("Found search box, searching for ETH...")
                    await search_box.fill("ETH Zurich")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(2000)
                    
                    # Try clicking ETH again
                    for selector in eth_selectors:
                        element = await page.query_selector(selector)
                        if element:
                            await element.click()
                            eth_found = True
                            break
            
            # Step 4: Fill login form
            logger.info("Step 4: Looking for login form...")
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            logger.info(f"Login page URL: {current_url}")
            
            # Fill username
            username_filled = False
            username_selectors = [
                '[name="j_username"]',
                '[name="username"]', 
                '[id="username"]',
                'input[type="text"]'
            ]
            
            for selector in username_selectors:
                element = await page.query_selector(selector)
                if element:
                    await element.fill(ETH_USERNAME)
                    logger.info(f"Filled username with selector: {selector}")
                    username_filled = True
                    break
            
            # Fill password
            password_filled = False
            password_selectors = [
                '[name="j_password"]',
                '[name="password"]',
                '[id="password"]',
                'input[type="password"]'
            ]
            
            for selector in password_selectors:
                element = await page.query_selector(selector)
                if element:
                    await element.fill(ETH_PASSWORD)
                    logger.info(f"Filled password with selector: {selector}")
                    password_filled = True
                    break
            
            await page.screenshot(path=debug_dir / "04_login_form_filled.png")
            
            # Submit form
            if username_filled and password_filled:
                submit_button = await page.query_selector('[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
                if submit_button:
                    logger.info("Submitting login form...")
                    await submit_button.click()
                    await page.wait_for_load_state('networkidle')
                    await page.screenshot(path=debug_dir / "05_after_login.png")
            
            # Wait for redirect back to IEEE
            logger.info("Waiting for authentication to complete...")
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            logger.info(f"Post-auth URL: {current_url}")
            
            # Step 5: Try to access PDF
            if doc_id and 'ieee' in current_url:
                logger.info("Step 5: Trying to access PDF...")
                
                # Try stamp URL again
                stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                logger.info(f"Navigating to stamp URL: {stamp_url}")
                
                response = await page.goto(stamp_url, wait_until='networkidle')
                await page.screenshot(path=debug_dir / "06_stamp_authenticated.png")
                
                if response:
                    content = await response.body()
                    if content.startswith(b'%PDF'):
                        logger.info("✅ Got PDF from stamp URL!")
                        with open(debug_dir / "downloaded.pdf", 'wb') as f:
                            f.write(content)
                        return True
                    else:
                        logger.info("Stamp URL still returns HTML")
                        
                        # Check for PDF iframe
                        pdf_frame = await page.query_selector('iframe[src*=".pdf"]')
                        if pdf_frame:
                            pdf_src = await pdf_frame.get_attribute('src')
                            logger.info(f"Found PDF iframe: {pdf_src}")
                            
                            if pdf_src and not pdf_src.startswith('http'):
                                pdf_src = f"https://ieeexplore.ieee.org{pdf_src}"
                            
                            pdf_response = await page.goto(pdf_src)
                            if pdf_response:
                                pdf_content = await pdf_response.body()
                                if pdf_content.startswith(b'%PDF'):
                                    logger.info("✅ Got PDF from iframe!")
                                    with open(debug_dir / "downloaded.pdf", 'wb') as f:
                                        f.write(pdf_content)
                                    return True
            
            logger.error("Could not download PDF")
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path=debug_dir / "error_state.png")
            return False
        finally:
            logger.info("Keeping browser open for 30 seconds...")
            await asyncio.sleep(30)
            await browser.close()

async def main():
    """Run debug session."""
    # First source the environment
    os.system("source ~/.zshrc")
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if username and password:
        os.environ["ETH_USERNAME"] = username
        os.environ["ETH_PASSWORD"] = password
        
    success = await debug_ieee_auth()
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)