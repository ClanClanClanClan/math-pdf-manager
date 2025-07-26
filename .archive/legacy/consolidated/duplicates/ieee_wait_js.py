#!/usr/bin/env python3
"""
IEEE Wait for JavaScript
========================

Wait for JavaScript to load in the iframe.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wait_js")

nest_asyncio.apply()

async def wait_for_js():
    from playwright.async_api import async_playwright
    
    output_dir = Path("wait_js")
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
            logger.info("Clicked access button, waiting for iframe to fully load...")
            
            # Wait longer for iframe
            await page.wait_for_timeout(8000)
            
            # Find iframe
            iframe = await page.query_selector('iframe[src*="seamlessaccess"]')
            if iframe:
                frame = await iframe.content_frame()
                if frame:
                    logger.info("Got frame, waiting for JavaScript to load...")
                    
                    # Wait for the JavaScript to load and populate the interface
                    # We'll wait for either the search input to appear or timeout
                    search_input = None
                    
                    for attempt in range(12):  # Try for up to 2 minutes
                        logger.info(f"Attempt {attempt + 1}/12 - waiting for search input...")
                        await frame.wait_for_timeout(5000)
                        
                        # Check all possible selectors
                        selectors = [
                            'input[aria-label="Search for your Institution"]',
                            'input.inst-typeahead-input',
                            'input[role="search"]',
                            'input[type="search"]',
                            'input[type="text"]',
                            'input:not([type="hidden"])'
                        ]
                        
                        for selector in selectors:
                            try:
                                search_input = await frame.query_selector(selector)
                                if search_input and await search_input.is_visible():
                                    logger.info(f"✅ Found search input with: {selector}")
                                    break
                            except Exception as e:
                                continue
                        
                        if search_input:
                            break
                        
                        # Debug current content
                        content = await frame.content()
                        logger.info(f"Iframe content length: {len(content)}")
                        
                        # Check if there's meaningful content
                        text_content = await frame.text_content('body')
                        if text_content and len(text_content.strip()) > 10:
                            logger.info(f"Iframe has text: {text_content[:100]}...")
                    
                    if search_input:
                        logger.info("✅ Search input found! Filling with 'ETH Zurich'...")
                        await search_input.fill("ETH Zurich")
                        await frame.wait_for_timeout(3000)
                        
                        await page.screenshot(path=output_dir / "after_search.png")
                        
                        # Wait for search results
                        logger.info("Waiting for search results...")
                        await frame.wait_for_timeout(3000)
                        
                        # Look for ETH in results
                        eth_selectors = [
                            'text="ETH Zurich"',
                            'li:has-text("ETH Zurich")',
                            'div:has-text("ETH Zurich")',
                            'a:has-text("ETH Zurich")',
                            'button:has-text("ETH Zurich")',
                            'text=/ETH.*Zurich/i'
                        ]
                        
                        eth_option = None
                        for selector in eth_selectors:
                            try:
                                eth_option = await frame.wait_for_selector(selector, timeout=3000)
                                if eth_option:
                                    logger.info(f"✅ Found ETH with: {selector}")
                                    break
                            except Exception as e:
                                continue
                        
                        if eth_option:
                            logger.info("✅ Clicking ETH Zurich...")
                            await eth_option.click()
                            
                            # Wait for redirect
                            logger.info("Waiting for redirect...")
                            await page.wait_for_timeout(8000)
                            
                            final_url = page.url
                            logger.info(f"Final URL: {final_url}")
                            
                            if 'ethz' in final_url or 'aai' in final_url:
                                logger.info("✅ SUCCESS! Redirected to ETH login!")
                                await page.screenshot(path=output_dir / "eth_login.png")
                                return True
                            else:
                                logger.warning(f"Not redirected to ETH: {final_url}")
                        else:
                            logger.warning("ETH option not found in results")
                            
                            # Debug what's there
                            text_content = await frame.text_content('body')
                            logger.info(f"Search results: {text_content}")
                    else:
                        logger.warning("Search input never appeared")
                        
                        # Save final iframe content
                        final_content = await frame.content()
                        with open(output_dir / "final_iframe.html", "w") as f:
                            f.write(final_content)
                        logger.info("Final iframe content saved")
            
            logger.info("Keeping browser open for inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(wait_for_js())