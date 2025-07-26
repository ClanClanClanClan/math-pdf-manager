#!/usr/bin/env python3
"""
Debug SIAM Dropdown
==================

Debug the dropdown that appears after typing in SIAM institution search.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("debug_dropdown")

nest_asyncio.apply()

async def debug_siam_dropdown():
    from playwright.async_api import async_playwright
    
    output_dir = Path("debug_siam_dropdown")
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
            
            # Find and focus search field
            search_input = await page.wait_for_selector('#shibboleth_search input', timeout=10000)
            
            # Type "ETH" character by character to trigger autocomplete
            await search_input.type("ETH", delay=100)
            logger.info("Typed 'ETH' with delay")
            
            # Wait for dropdown to appear
            await page.wait_for_timeout(2000)
            
            # Screenshot after typing
            await page.screenshot(path=output_dir / "after_typing_eth.png")
            
            # Look for dropdown containers with various selectors
            dropdown_selectors = [
                '.ms-res-ctn',  # Multi-select results container
                '.ms-opt-ctn',  # Multi-select options container
                '.autocomplete-dropdown',
                '.dropdown-menu',
                '.institution-dropdown',
                'ul.ms-list',
                'div[role="listbox"]',
                '.ms-ctn.form-control.ms-no-trigger',
                '#shibboleth_search .ms-opt-ctn'
            ]
            
            for selector in dropdown_selectors:
                try:
                    dropdown = await page.query_selector(selector)
                    if dropdown:
                        logger.info(f"Found dropdown with selector: {selector}")
                        
                        # Check if it's visible
                        is_visible = await dropdown.is_visible()
                        logger.info(f"  Visible: {is_visible}")
                        
                        # Get all items in dropdown
                        items = await dropdown.query_selector_all('li, a, div')
                        logger.info(f"  Found {len(items)} items")
                        
                        for i, item in enumerate(items[:10]):  # First 10 only
                            text = await item.text_content()
                            if text and 'ETH' in text:
                                logger.info(f"    Item {i+1}: '{text.strip()}'")
                                
                                # Try clicking the ETH option
                                if 'zurich' in text.lower() or text.strip() == 'ETH Zurich':
                                    logger.info(f"🎯 Clicking ETH option: '{text.strip()}'")
                                    await item.click()
                                    await page.wait_for_timeout(3000)
                                    
                                    logger.info(f"After click URL: {page.url}")
                                    await page.screenshot(path=output_dir / "after_eth_click.png")
                                    
                                    # Check if we're now at ETH or another page
                                    if page.url != "https://epubs.siam.org/action/ssostart?redirectUri=%2F":
                                        logger.info("🎉 URL changed after clicking!")
                                        return True
                                    else:
                                        logger.info("URL didn't change after clicking")
                except Exception as e:
                    logger.debug(f"Dropdown selector {selector} failed: {e}")
                    continue
            
            # If no dropdown found, try alternative approach
            logger.info("No dropdown found, trying alternative...")
            
            # Clear and type full name
            await search_input.fill("")
            await search_input.type("ETH Zurich", delay=100)
            await page.wait_for_timeout(2000)
            
            # Try pressing Arrow Down to select from dropdown
            await search_input.press('ArrowDown')
            await page.wait_for_timeout(1000)
            await search_input.press('Enter')
            await page.wait_for_timeout(3000)
            
            logger.info(f"After ArrowDown+Enter: {page.url}")
            
            if page.url != "https://epubs.siam.org/action/ssostart?redirectUri=%2F":
                logger.info("🎉 ArrowDown+Enter worked!")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Browser staying open for inspection...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(debug_siam_dropdown())
    if success:
        logger.info("🎉 Found working dropdown interaction!")
    else:
        logger.error("💥 Dropdown interaction failed")