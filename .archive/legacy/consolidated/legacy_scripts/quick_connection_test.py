#!/usr/bin/env python3
"""
Quick Connection Test
====================

Test if we can even connect to IEEE.
"""

import asyncio
import nest_asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quick_test")

nest_asyncio.apply()

async def quick_test():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Test different IEEE URLs
            test_urls = [
                "https://ieeexplore.ieee.org",
                "https://ieeexplore.ieee.org/document/8347162",
                "https://doi.org/10.1109/JPROC.2018.2820126"
            ]
            
            for url in test_urls:
                logger.info(f"Testing: {url}")
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    logger.info(f"✅ Success: {response.status} - {page.title()}")
                    
                    # Check if we see institutional sign in
                    inst_signin = await page.query_selector('a:has-text("Institutional Sign In")')
                    if inst_signin:
                        logger.info("✅ Found Institutional Sign In button")
                        return True
                    else:
                        logger.info("No Institutional Sign In button found")
                    
                except Exception as e:
                    logger.error(f"❌ Failed: {e}")
                
                await page.wait_for_timeout(2000)
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        finally:
            await asyncio.sleep(5)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    if success:
        logger.info("✅ Connection test passed")
    else:
        logger.error("❌ Connection test failed")