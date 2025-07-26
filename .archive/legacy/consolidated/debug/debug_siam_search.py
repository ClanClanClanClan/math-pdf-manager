#!/usr/bin/env python3
"""
Debug SIAM Search
================

Debug what happens when we search for ETH in the institution selector.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("debug_search")

nest_asyncio.apply()

async def debug_siam_search():
    from playwright.async_api import async_playwright
    
    output_dir = Path("debug_siam_search")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Go to SIAM and start SSO
            siam_url = "https://epubs.siam.org/doi/10.1137/S0036142997325199"
            await page.goto(siam_url, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(3000)
            
            # Click institutional access
            access_link = await page.query_selector('a:has-text("Access via your Institution")')
            await access_link.click()
            await page.wait_for_timeout(5000)
            
            logger.info("=== Before searching ===")
            await page.screenshot(path=output_dir / "before_search.png")
            
            # Find and fill search
            search_input = await page.wait_for_selector('#shibboleth_search input', timeout=10000)
            await search_input.fill("ETH")
            logger.info("Filled 'ETH'")
            
            # Wait a bit for any autocomplete
            await page.wait_for_timeout(3000)
            
            logger.info("=== After typing 'ETH' ===")
            await page.screenshot(path=output_dir / "after_typing.png")
            
            # Look for any dropdown/results
            results_selectors = [
                '.ms-res-ctn',  # Common multi-select results container
                '.autocomplete-results',
                '.dropdown-results',
                '.institution-list',
                'ul li',
                'div[role="listbox"]',
                '[aria-expanded="true"]'
            ]
            
            found_results = False
            for selector in results_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        for i, elem in enumerate(elements[:3]):  # First 3 only
                            text = await elem.text_content()
                            if text and 'ETH' in text:
                                logger.info(f"  {i+1}: '{text.strip()}'")
                                found_results = True
                except Exception as e:
                    continue
            
            if not found_results:
                logger.info("No dropdown results found after typing")
            
            # Try typing full name
            await search_input.fill("ETH Zurich")
            logger.info("Filled 'ETH Zurich'")
            await page.wait_for_timeout(3000)
            
            logger.info("=== After typing 'ETH Zurich' ===")
            await page.screenshot(path=output_dir / "after_full_name.png")
            
            # Try pressing various keys
            logger.info("Trying Enter...")
            await search_input.press('Enter')
            await page.wait_for_timeout(3000)
            
            logger.info("=== After Enter ===")
            await page.screenshot(path=output_dir / "after_enter.png")
            logger.info(f"URL: {page.url}")
            
            # Try pressing Tab to see if it selects
            await search_input.press('Tab')
            await page.wait_for_timeout(2000)
            
            logger.info("=== After Tab ===")
            await page.screenshot(path=output_dir / "after_tab.png")
            logger.info(f"URL: {page.url}")
            
            # Look for any clickable ETH options
            eth_options = await page.query_selector_all('*:has-text("ETH")')
            logger.info(f"Found {len(eth_options)} elements containing 'ETH'")
            
            for i, option in enumerate(eth_options[:5]):  # First 5
                try:
                    text = await option.text_content()
                    tag = await option.evaluate('el => el.tagName')
                    if text and 'ETH' in text and len(text.strip()) < 100:
                        logger.info(f"  Option {i+1}: {tag} '{text.strip()}'")
                        
                        # Try clicking it
                        if 'zurich' in text.lower() or text.strip() == 'ETH Zurich':
                            logger.info(f"Trying to click: '{text.strip()}'")
                            await option.click()
                            await page.wait_for_timeout(3000)
                            
                            logger.info("=== After clicking ETH option ===")
                            await page.screenshot(path=output_dir / "after_click.png")
                            logger.info(f"URL: {page.url}")
                            break
                except Exception as e:
                    continue
            
            logger.info("=== Debug Complete ===")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.info("Browser staying open for inspection...")
            await asyncio.sleep(20)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_siam_search())