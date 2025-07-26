#!/usr/bin/env python3
"""
IEEE SeamlessAccess Wait
========================

Wait for SeamlessAccess to load properly.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seamless_wait")

nest_asyncio.apply()

async def seamless_wait_test():
    from playwright.async_api import async_playwright
    
    output_dir = Path("seamless_wait")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate
            logger.info("Navigating to IEEE...")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Accept cookies
            logger.info("Accepting cookies...")
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in
            logger.info("Clicking Institutional Sign In...")
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            
            # Wait longer for modal to fully load
            logger.info("Waiting for modal to fully load...")
            await page.wait_for_timeout(5000)
            
            # Try different approach - look for the button and its parent
            logger.info("Looking for Access Through Your Institution button...")
            
            # Method 1: Direct button click in modal
            try:
                button = await page.wait_for_selector(
                    'ngb-modal-window button:has-text("Access Through Your Institution")',
                    timeout=5000
                )
                if button:
                    logger.info("Found button in modal, clicking...")
                    await button.click()
                    
                    # Wait and check for navigation
                    logger.info("Waiting for navigation...")
                    try:
                        await page.wait_for_navigation(timeout=5000)
                        logger.info(f"Navigated to: {page.url}")
                    except Exception as e:
                        logger.info("No navigation occurred, checking for new tabs...")
                        
                        # Check for new tabs
                        all_pages = context.pages
                        if len(all_pages) > 1:
                            new_page = all_pages[-1]
                            logger.info(f"New tab opened: {new_page.url}")
                            
                            # Switch to new tab
                            await new_page.wait_for_load_state('networkidle')
                            
                            # Search for ETH in new tab
                            logger.info("Searching for ETH in new tab...")
                            search_input = await new_page.wait_for_selector(
                                'input[type="search"], input[placeholder*="institution"]',
                                timeout=10000
                            )
                            if search_input:
                                await search_input.fill("ETH Zurich")
                                await new_page.wait_for_timeout(2000)
                                
                                # Click ETH
                                eth_option = await new_page.wait_for_selector('text="ETH Zurich"', timeout=10000)
                                await eth_option.click()
                                
                                logger.info("Selected ETH Zurich")
                                await new_page.wait_for_load_state('networkidle')
                                
                                # Check if we're at login page
                                if 'ethz' in new_page.url or 'aai' in new_page.url:
                                    logger.info("✅ Successfully reached ETH login page!")
                                    logger.info(f"Login URL: {new_page.url}")
                                    return True
                        else:
                            # No new tab, check iframe
                            logger.info("No new tab, checking SeamlessAccess iframe...")
                            
                            # Wait for iframe to load
                            await page.wait_for_timeout(3000)
                            
                            # Find SeamlessAccess iframe
                            sa_iframe = await page.query_selector('iframe[src*="seamlessaccess"]')
                            if sa_iframe:
                                frame = await sa_iframe.content_frame()
                                if frame:
                                    logger.info("Got SeamlessAccess frame, looking for content...")
                                    
                                    # Wait for frame content
                                    await frame.wait_for_timeout(2000)
                                    
                                    # Look for search in frame
                                    search_input = await frame.query_selector('input[type="search"]')
                                    if search_input:
                                        logger.info("Found search in iframe!")
                                        await search_input.fill("ETH Zurich")
                                        await frame.wait_for_timeout(2000)
                                        
                                        eth_option = await frame.query_selector('text="ETH Zurich"')
                                        if eth_option:
                                            await eth_option.click()
                                            logger.info("Clicked ETH in iframe")
            except Exception as e:
                logger.error(f"Button click failed: {e}")
            
            # Take screenshot
            await page.screenshot(path=output_dir / "final_state.png")
            logger.info(f"Screenshot saved to {output_dir}/final_state.png")
            
            # Keep browser open
            logger.info("Browser will stay open for inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(seamless_wait_test())