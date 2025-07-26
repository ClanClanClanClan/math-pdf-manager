#!/usr/bin/env python3
"""
IEEE Correct Input Test
=======================

Test with the correct input selector.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("correct_input")

nest_asyncio.apply()

async def test_correct_input():
    from playwright.async_api import async_playwright
    
    output_dir = Path("correct_input")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            logger.info("Navigate and setup...")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded', timeout=60000)
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
            
            # Click access button
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            await access_btn.click()
            await page.wait_for_timeout(5000)
            
            # Find iframe and search input
            iframe = await page.query_selector('iframe[src*="seamlessaccess"]')
            if iframe:
                frame = await iframe.content_frame()
                if frame:
                    await frame.wait_for_timeout(3000)
                    
                    # Try the correct selectors
                    selectors = [
                        'input[aria-label="Search for your Institution"]',
                        'input.inst-typeahead-input',
                        'input[role="search"]'
                    ]
                    
                    search_input = None
                    for selector in selectors:
                        try:
                            search_input = await frame.wait_for_selector(selector, timeout=3000)
                            if search_input:
                                logger.info(f"✅ Found input with: {selector}")
                                break
                        except Exception as e:
                            logger.info(f"❌ Failed: {selector}")
                    
                    if search_input:
                        logger.info("✅ Filling search with 'ETH Zurich'...")
                        await search_input.fill("ETH Zurich")
                        await frame.wait_for_timeout(3000)
                        
                        await page.screenshot(path=output_dir / "after_search.png")
                        
                        # Look for ETH in results
                        try:
                            eth_option = await frame.wait_for_selector('text="ETH Zurich"', timeout=5000)
                            if eth_option:
                                logger.info("✅ Found ETH Zurich, clicking...")
                                await eth_option.click()
                                
                                await page.wait_for_timeout(5000)
                                logger.info(f"Final URL: {page.url}")
                                
                                if 'ethz' in page.url or 'aai' in page.url:
                                    logger.info("✅ SUCCESS! Redirected to ETH login!")
                                    return True
                        except Exception as e:
                            logger.warning("ETH option not found")
                            
                            # Debug results
                            content = await frame.text_content('body')
                            logger.info(f"Frame content: {content[:300]}...")
                    else:
                        logger.warning("Search input not found")
                        content = await frame.content()
                        with open(output_dir / "iframe.html", "w") as f:
                            f.write(content)
                        logger.info("Iframe content saved for debugging")
            
            logger.info("Keeping browser open...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_correct_input())