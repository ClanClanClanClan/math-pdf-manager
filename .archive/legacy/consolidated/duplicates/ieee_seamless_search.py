#!/usr/bin/env python3
"""
IEEE SeamlessAccess Search
==========================

Properly handle the SeamlessAccess iframe search.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seamless_search")

nest_asyncio.apply()

async def seamless_search_test():
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
    
    output_dir = Path("seamless_search")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info("Step 1: Navigate and setup...")
            await page.goto(ieee_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            await page.wait_for_timeout(3000)
            
            logger.info("Step 2: Click Access Through Your Institution...")
            access_button = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            await access_button.click()
            
            logger.info("Step 3: Wait for SeamlessAccess iframe to load...")
            # Give more time for iframe to fully load
            await page.wait_for_timeout(5000)
            
            # Find SeamlessAccess iframe
            sa_iframe = await page.wait_for_selector('iframe[src*="seamlessaccess"]', timeout=10000)
            if sa_iframe:
                logger.info("Found SeamlessAccess iframe")
                frame = await sa_iframe.content_frame()
                
                if frame:
                    logger.info("Got frame handle, waiting for content to load...")
                    
                    # Wait longer for iframe content to fully load
                    await frame.wait_for_timeout(5000)
                    
                    # Check content
                    content = await frame.content()
                    logger.info(f"Iframe content length: {len(content)}")
                    
                    # Save content for debugging
                    with open(output_dir / "iframe_content.html", "w") as f:
                        f.write(content)
                    
                    if len(content) > 100:
                        logger.info("Step 4: Iframe has content, looking for search input...")
                        
                        # Try multiple search input selectors
                        search_selectors = [
                            'input[type="search"]',
                            'input[placeholder*="institution"]',
                            'input[placeholder*="search"]',
                            'input[placeholder*="organization"]',
                            'input[id*="search"]',
                            'input[class*="search"]',
                            'input[type="text"]',
                            'input:not([type="hidden"])'
                        ]
                        
                        search_input = None
                        for selector in search_selectors:
                            try:
                                search_input = await frame.wait_for_selector(selector, timeout=2000)
                                if search_input and await search_input.is_visible():
                                    logger.info(f"✅ Found search input with selector: {selector}")
                                    break
                            except Exception as e:
                                logger.debug(f"Selector '{selector}' not found")
                                continue
                        
                        if search_input:
                            logger.info("Step 5: Entering 'ETH Zurich' in search...")
                            await search_input.fill("ETH Zurich")
                            await frame.wait_for_timeout(3000)  # Wait for search results
                            
                            # Take screenshot of iframe after search
                            await page.screenshot(path=output_dir / "after_search.png")
                            
                            logger.info("Step 6: Looking for ETH Zurich in results...")
                            
                            # Try different selectors for ETH option
                            eth_selectors = [
                                'text="ETH Zurich"',
                                'li:has-text("ETH Zurich")',
                                'div:has-text("ETH Zurich")',
                                'a:has-text("ETH Zurich")',
                                'button:has-text("ETH Zurich")',
                                '[title*="ETH Zurich"]',
                                'text=/ETH.*Zurich/i',
                                'li:has-text("ETH")',
                                'div:has-text("ETH")'
                            ]
                            
                            eth_option = None
                            for selector in eth_selectors:
                                try:
                                    eth_option = await frame.wait_for_selector(selector, timeout=2000)
                                    if eth_option:
                                        logger.info(f"✅ Found ETH option with selector: {selector}")
                                        break
                                except Exception as e:
                                    logger.debug(f"ETH selector '{selector}' not found")
                                    continue
                            
                            if eth_option:
                                logger.info("Step 7: Clicking ETH Zurich...")
                                await eth_option.click()
                                
                                # Wait for redirect
                                logger.info("Waiting for redirect to ETH login...")
                                await page.wait_for_timeout(5000)
                                
                                # Check if we're redirected to ETH
                                current_url = page.url
                                logger.info(f"Current URL: {current_url}")
                                
                                if 'ethz' in current_url or 'aai' in current_url:
                                    logger.info("✅ Step 8: Redirected to ETH login!")
                                    
                                    # Fill login form
                                    await page.fill('[name="j_username"], [id="username"]', username)
                                    await page.fill('[name="j_password"], [id="password"]', password)
                                    
                                    # Submit
                                    submit = await page.query_selector('[type="submit"]')
                                    await submit.click()
                                    
                                    logger.info("Step 9: Authenticating...")
                                    await page.wait_for_timeout(5000)
                                    
                                    # Check final result
                                    final_url = page.url
                                    logger.info(f"Final URL: {final_url}")
                                    
                                    if 'ieee' in final_url:
                                        logger.info("✅ SUCCESS! Authenticated and returned to IEEE!")
                                        
                                        # Try PDF download
                                        doc_id = final_url.split('/document/')[1].split('/')[0] if '/document/' in final_url else None
                                        if doc_id:
                                            stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                                            logger.info(f"Trying PDF download: {stamp_url}")
                                            
                                            response = await page.goto(stamp_url, wait_until='networkidle')
                                            content = await response.body()
                                            
                                            if content.startswith(b'%PDF'):
                                                pdf_path = output_dir / "ieee_paper.pdf"
                                                with open(pdf_path, 'wb') as f:
                                                    f.write(content)
                                                logger.info(f"✅ PDF downloaded: {pdf_path}")
                                                return True
                                        
                                        return True
                                    else:
                                        logger.warning(f"Not returned to IEEE: {final_url}")
                                else:
                                    logger.warning(f"Not redirected to ETH: {current_url}")
                                    
                                    # Check for other windows
                                    all_pages = context.pages
                                    if len(all_pages) > 1:
                                        for other_page in all_pages[1:]:
                                            other_url = other_page.url
                                            logger.info(f"Other window: {other_url}")
                                            if 'ethz' in other_url or 'aai' in other_url:
                                                logger.info("Found ETH login in other window!")
                                                # Continue with other_page...
                            else:
                                logger.warning("Could not find ETH option in search results")
                                
                                # Debug what's in the iframe
                                iframe_text = await frame.text_content('body')
                                logger.debug(f"Iframe text content: {iframe_text[:500]}...")
                        else:
                            logger.warning("Could not find search input in iframe")
                            
                            # Debug what's in the iframe
                            iframe_text = await frame.text_content('body')
                            logger.debug(f"Iframe text content: {iframe_text[:500]}...")
                    else:
                        logger.warning("Iframe content is empty or too small")
                else:
                    logger.warning("Could not get frame handle")
            else:
                logger.warning("SeamlessAccess iframe not found")
            
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
    success = asyncio.run(seamless_search_test())
    if success:
        logger.info("✅ IEEE authentication and download successful!")
    else:
        logger.error("❌ IEEE authentication failed!")