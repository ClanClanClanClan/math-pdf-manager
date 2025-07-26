#!/usr/bin/env python3
"""
Complete IEEE Authentication Debug
==================================

Handle cookie consent and complete authentication flow.
"""

import os
import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ieee_complete")

nest_asyncio.apply()

async def complete_ieee_auth():
    """Complete IEEE authentication with cookie handling."""
    from playwright.async_api import async_playwright
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        logger.error("No ETH credentials found!")
        return False
    
    logger.info(f"Using ETH username: {username}")
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    debug_dir = Path("ieee_complete_debug")
    debug_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1: Navigate to IEEE
            logger.info("Step 1: Navigating to IEEE...")
            await page.goto(ieee_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)  # Let page fully load
            
            # Step 2: Handle cookie consent
            logger.info("Step 2: Handling cookie consent...")
            cookie_selectors = [
                'button:has-text("Accept All")',
                'button:has-text("Accept")',
                'button:has-text("OK")',
                '[class*="accept"]',
                '[class*="osano-cm-accept"]',
                '.osano-cm-accept-all'
            ]
            
            for selector in cookie_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        logger.info(f"Found cookie button: {selector}")
                        await button.click()
                        await page.wait_for_timeout(1000)
                        break
                except Exception as e:
                    continue
            
            # Close any other overlays
            close_selectors = [
                '.usabilla__close',
                '[aria-label="Close"]',
                'button[aria-label="Close"]',
                '.modal-close',
                '.close-button'
            ]
            
            for selector in close_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        await page.wait_for_timeout(500)
                except Exception as e:
                    continue
            
            await page.screenshot(path=debug_dir / "01_after_cookie.png")
            
            # Step 3: Click institutional sign in
            logger.info("Step 3: Clicking institutional sign in...")
            inst_button = await page.wait_for_selector('text="Institutional Sign In"', timeout=10000)
            if inst_button:
                await inst_button.click()
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=debug_dir / "02_inst_options.png")
            
            # Step 3.5: Click "Access through your institution" in the popup
            logger.info("Step 3.5: Clicking 'Access through your institution'...")
            await page.wait_for_timeout(2000)
            
            access_button = await page.wait_for_selector('text="Access through your institution"', timeout=10000)
            if access_button:
                logger.info("Found 'Access through your institution' button, clicking...")
                await access_button.click()
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=debug_dir / "02b_after_access_click.png")
            
            # Step 4: Find and click ETH
            logger.info("Step 4: Looking for ETH option...")
            await page.wait_for_timeout(2000)
            
            # First check if we need to search
            search_box = await page.query_selector('input[placeholder*="institution"], input[placeholder*="organization"]')
            if search_box:
                logger.info("Found search box, searching for ETH...")
                await search_box.fill("ETH Zurich")
                await page.wait_for_timeout(1000)
            
            # Click ETH option
            eth_clicked = False
            eth_selectors = [
                'text="ETH Zurich"',
                'text="Swiss Federal Institute of Technology Zurich"',
                'a:has-text("ETH Zurich")',
                'li:has-text("ETH Zurich")',
                '[title*="ETH Zurich"]'
            ]
            
            for selector in eth_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        logger.info(f"Found ETH with selector: {selector}")
                        await element.click()
                        eth_clicked = True
                        break
                except Exception as e:
                    continue
            
            if eth_clicked:
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=debug_dir / "03_after_eth_click.png")
            
            # Step 5: Fill login form
            logger.info("Step 5: Filling login form...")
            await page.wait_for_timeout(3000)
            
            # Fill username
            username_input = await page.wait_for_selector('input[name="j_username"], input[name="username"], input[id="username"]', timeout=10000)
            if username_input:
                await username_input.fill(username)
                logger.info("Filled username")
            
            # Fill password
            password_input = await page.wait_for_selector('input[name="j_password"], input[name="password"], input[id="password"]', timeout=5000)
            if password_input:
                await password_input.fill(password)
                logger.info("Filled password")
            
            await page.screenshot(path=debug_dir / "04_login_filled.png")
            
            # Submit
            submit_button = await page.query_selector('[type="submit"], button:has-text("Login")')
            if submit_button:
                logger.info("Submitting login...")
                await submit_button.click()
                await page.wait_for_load_state('networkidle')
            
            # Wait for redirect
            logger.info("Waiting for authentication to complete...")
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            logger.info(f"Post-auth URL: {current_url}")
            await page.screenshot(path=debug_dir / "05_after_auth.png")
            
            # Step 6: Try to download PDF
            if 'ieee' in current_url:
                logger.info("Step 6: Attempting PDF download...")
                
                # Extract doc ID
                doc_id = current_url.split('/document/')[1].split('/')[0] if '/document/' in current_url else None
                
                if doc_id:
                    # Try stamp URL
                    stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                    logger.info(f"Trying stamp URL: {stamp_url}")
                    
                    response = await page.goto(stamp_url, wait_until='networkidle')
                    await page.screenshot(path=debug_dir / "06_stamp_page.png")
                    
                    if response:
                        content = await response.body()
                        if content.startswith(b'%PDF'):
                            logger.info("✅ SUCCESS! Got PDF directly from stamp URL")
                            with open(debug_dir / "downloaded.pdf", 'wb') as f:
                                f.write(content)
                            return True
                        else:
                            # Look for PDF in page
                            logger.info("Stamp returned HTML, looking for PDF elements...")
                            
                            # Check for PDF viewer iframe
                            pdf_viewers = await page.query_selector_all('iframe[src*="pdf"], embed[src*="pdf"], object[data*="pdf"]')
                            logger.info(f"Found {len(pdf_viewers)} potential PDF viewers")
                            
                            for viewer in pdf_viewers:
                                src = await viewer.get_attribute('src') or await viewer.get_attribute('data')
                                if src:
                                    logger.info(f"Found PDF viewer: {src}")
                                    if not src.startswith('http'):
                                        src = f"https://ieeexplore.ieee.org{src}"
                                    
                                    pdf_response = await page.goto(src)
                                    if pdf_response:
                                        pdf_content = await pdf_response.body()
                                        if pdf_content.startswith(b'%PDF'):
                                            logger.info("✅ SUCCESS! Got PDF from viewer")
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
            logger.info("Keeping browser open for manual inspection...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(complete_ieee_auth())
    if success:
        logger.info("✅ IEEE authentication and download successful!")
    else:
        logger.error("❌ IEEE authentication or download failed!")
    exit(0 if success else 1)