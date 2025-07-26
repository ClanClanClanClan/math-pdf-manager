#!/usr/bin/env python3
"""
IEEE Simple Iframe Test
=======================

Simple test focusing just on the iframe search.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("simple_iframe")

nest_asyncio.apply()

async def simple_iframe_test():
    from playwright.async_api import async_playwright
    
    output_dir = Path("simple_iframe")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            logger.info("Navigating to IEEE...")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            
            logger.info("Accept cookies...")
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            logger.info("Click Institutional Sign In...")
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            await page.wait_for_timeout(3000)
            
            logger.info("Click Access Through Your Institution...")
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            await access_btn.click()
            
            logger.info("Waiting for iframe to be ready...")
            await page.wait_for_timeout(8000)  # Wait longer
            
            # Find and interact with iframe
            iframe = await page.query_selector('iframe[src*="seamlessaccess"]')
            if iframe:
                logger.info("Found iframe, getting frame handle...")
                frame = await iframe.content_frame()
                
                if frame:
                    logger.info("Got frame handle, waiting for search input...")
                    
                    # Wait longer for iframe content
                    await frame.wait_for_timeout(5000)
                    
                    # Try to find search input with more patience
                    search_input = None
                    for attempt in range(3):
                        logger.info(f"Search attempt {attempt + 1}/3...")
                        try:
                            search_input = await frame.wait_for_selector('input[type="search"]', timeout=5000)
                            if search_input:
                                logger.info("✅ Found search input!")
                                break
                        except Exception as e:
                            logger.info(f"Attempt {attempt + 1} failed, waiting more...")
                            await frame.wait_for_timeout(3000)
                    
                    if not search_input:
                        # Try alternative selectors
                        alt_selectors = ['input[type="text"]', 'input:not([type="hidden"])']
                        for selector in alt_selectors:
                            try:
                                search_input = await frame.wait_for_selector(selector, timeout=3000)
                                if search_input:
                                    logger.info(f"✅ Found search input with: {selector}")
                                    break
                            except Exception as e:
                                continue
                    
                    if search_input:
                        logger.info("Filling search with 'ETH Zurich'...")
                        await search_input.fill("ETH Zurich")
                        await frame.wait_for_timeout(3000)
                        
                        # Take screenshot
                        await page.screenshot(path=output_dir / "after_search.png")
                        
                        logger.info("Looking for ETH in results...")
                        try:
                            eth_option = await frame.wait_for_selector('text="ETH Zurich"', timeout=5000)
                            if eth_option:
                                logger.info("✅ Found ETH Zurich option!")
                                await eth_option.click()
                                
                                logger.info("Waiting for redirect...")
                                await page.wait_for_timeout(5000)
                                
                                logger.info(f"Current URL: {page.url}")
                                if 'ethz' in page.url or 'aai' in page.url:
                                    logger.info("✅ Successfully redirected to ETH!")
                                    return True
                        except Exception as e:
                            logger.warning("Could not find ETH option")
                            
                            # Debug what's in iframe
                            text_content = await frame.text_content('body')
                            logger.info(f"Iframe content: {text_content[:200]}...")
                    else:
                        logger.warning("Could not find search input")
                        
                        # Debug iframe content
                        content = await frame.content()
                        logger.info(f"Iframe HTML length: {len(content)}")
                        
                        with open(output_dir / "iframe_debug.html", "w") as f:
                            f.write(content)
                        logger.info("Iframe content saved to iframe_debug.html")
                else:
                    logger.warning("Could not get frame handle")
            else:
                logger.warning("SeamlessAccess iframe not found")
            
            await page.screenshot(path=output_dir / "final_state.png")
            logger.info("Browser staying open for 20 seconds...")
            await asyncio.sleep(20)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(simple_iframe_test())