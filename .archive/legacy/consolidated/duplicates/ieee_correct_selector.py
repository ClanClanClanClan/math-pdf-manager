#!/usr/bin/env python3
"""
IEEE Correct Selector
=====================

Use the exact button selector from the HTML.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("correct_selector")

nest_asyncio.apply()

async def correct_selector_test():
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
    
    output_dir = Path("correct_selector")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to IEEE
            logger.info("Step 1: Navigating to IEEE...")
            await page.goto(ieee_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            logger.info("Step 2: Accepting cookies...")
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in
            logger.info("Step 3: Clicking Institutional Sign In...")
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            await page.wait_for_timeout(3000)
            
            # Now use the EXACT selector from the HTML
            logger.info("Step 4: Using exact button selector...")
            
            # The button has class "stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn"
            exact_button = await page.wait_for_selector(
                'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn',
                timeout=10000
            )
            
            if exact_button:
                logger.info("Found button with exact class, clicking...")
                
                # Try different click methods
                # Method 1: Regular click
                await exact_button.click()
                logger.info("Clicked button, waiting for response...")
                
                # Wait for any navigation or new window
                await page.wait_for_timeout(3000)
                
                # Check for navigation
                current_url = page.url
                logger.info(f"Current URL after click: {current_url}")
                
                # Check for new windows/tabs
                all_pages = context.pages
                logger.info(f"Number of pages: {len(all_pages)}")
                
                if len(all_pages) > 1:
                    # New window opened
                    new_page = all_pages[-1]
                    await new_page.wait_for_load_state('networkidle')
                    logger.info(f"New window URL: {new_page.url}")
                    
                    # Continue with the new window
                    target_page = new_page
                elif 'seamless' in current_url or 'wayf' in current_url or 'discovery' in current_url:
                    # Navigation occurred in same window
                    logger.info("Navigation in same window")
                    target_page = page
                else:
                    # Check for iframe changes
                    logger.info("No navigation, checking iframe content...")
                    sa_iframe = await page.query_selector('iframe[src*="seamlessaccess"]')
                    if sa_iframe:
                        frame = await sa_iframe.content_frame()
                        if frame:
                            await frame.wait_for_timeout(2000)
                            
                            # Check if iframe now has content
                            frame_content = await frame.content()
                            if 'search' in frame_content.lower() or 'institution' in frame_content.lower():
                                logger.info("Iframe now has content!")
                                target_page = frame
                            else:
                                logger.warning("Iframe still empty")
                                target_page = None
                    else:
                        logger.warning("No iframe found")
                        target_page = None
                
                # If we have a target page/frame, continue with authentication
                if target_page:
                    logger.info("Step 5: Searching for ETH...")
                    
                    # Look for search input
                    search_selectors = [
                        'input[type="search"]',
                        'input[placeholder*="institution"]',
                        'input[placeholder*="organization"]',
                        'input[type="text"]'
                    ]
                    
                    search_input = None
                    for selector in search_selectors:
                        try:
                            search_input = await target_page.wait_for_selector(selector, timeout=3000)
                            if search_input:
                                logger.info(f"Found search input: {selector}")
                                break
                        except Exception as e:
                            continue
                    
                    if search_input:
                        await search_input.fill("ETH Zurich")
                        await target_page.wait_for_timeout(2000)
                        
                        # Click ETH option
                        logger.info("Step 6: Clicking ETH Zurich...")
                        eth_option = await target_page.wait_for_selector('text="ETH Zurich"', timeout=10000)
                        await eth_option.click()
                        
                        # Wait for redirect to ETH
                        if hasattr(target_page, 'wait_for_load_state'):
                            await target_page.wait_for_load_state('networkidle')
                        else:
                            # It's a frame, wait for navigation in main page
                            await page.wait_for_timeout(5000)
                        
                        # Check if we're at ETH login
                        current_url = page.url if hasattr(target_page, 'url') else page.url
                        logger.info(f"Current URL: {current_url}")
                        
                        if 'ethz' in current_url or 'aai' in current_url:
                            logger.info("Step 7: At ETH login page!")
                            
                            # Fill credentials
                            await page.fill('input[name="j_username"], input[id="username"]', username)
                            await page.fill('input[name="j_password"], input[id="password"]', password)
                            
                            # Submit
                            submit = await page.query_selector('[type="submit"]')
                            await submit.click()
                            
                            # Wait for authentication
                            logger.info("Step 8: Authenticating...")
                            await page.wait_for_timeout(5000)
                            
                            # Check if back at IEEE
                            if 'ieee' in page.url:
                                logger.info("✅ Successfully authenticated!")
                                
                                # Try PDF download
                                doc_id = page.url.split('/document/')[1].split('/')[0] if '/document/' in page.url else None
                                if doc_id:
                                    stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                                    logger.info(f"Step 9: Downloading PDF from: {stamp_url}")
                                    
                                    response = await page.goto(stamp_url, wait_until='networkidle')
                                    content = await response.body()
                                    
                                    if content.startswith(b'%PDF'):
                                        pdf_path = output_dir / "ieee_paper.pdf"
                                        with open(pdf_path, 'wb') as f:
                                            f.write(content)
                                        logger.info(f"✅ PDF saved to: {pdf_path}")
                                        return True
                                    else:
                                        logger.info("Not a PDF, checking for iframe...")
                                        # Look for PDF in iframe
                                        iframe = await page.query_selector('iframe[src*="pdf"]')
                                        if iframe:
                                            src = await iframe.get_attribute('src')
                                            if not src.startswith('http'):
                                                src = f"https://ieeexplore.ieee.org{src}"
                                            
                                            pdf_response = await page.goto(src)
                                            pdf_content = await pdf_response.body()
                                            
                                            if pdf_content.startswith(b'%PDF'):
                                                pdf_path = output_dir / "ieee_paper.pdf"
                                                with open(pdf_path, 'wb') as f:
                                                    f.write(pdf_content)
                                                logger.info(f"✅ PDF saved from iframe: {pdf_path}")
                                                return True
            
            # Take screenshot for debugging
            await page.screenshot(path=output_dir / "final_state.png")
            logger.info("Browser will stay open for inspection...")
            await asyncio.sleep(30)
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(correct_selector_test())
    if success:
        logger.info("✅ IEEE authentication and download successful!")
    else:
        logger.error("❌ IEEE authentication or download failed!")