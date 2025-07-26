#!/usr/bin/env python3
"""
IEEE Debug Steps
================

Debug each step with screenshots.
"""

import os
import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ieee_debug_steps")

nest_asyncio.apply()

async def debug_ieee_steps():
    """Debug IEEE auth step by step."""
    from playwright.async_api import async_playwright
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("ieee_steps")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1
            logger.info("Step 1: Navigate to IEEE")
            await page.goto(ieee_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            await page.screenshot(path=output_dir / "01_ieee_page.png")
            
            # Step 2
            logger.info("Step 2: Handle cookies")
            cookie_buttons = await page.query_selector_all('button')
            for button in cookie_buttons:
                text = await button.text_content()
                if text and 'accept' in text.lower():
                    logger.info(f"Found cookie button: {text}")
                    await button.click()
                    break
            await page.wait_for_timeout(1000)
            await page.screenshot(path=output_dir / "02_after_cookies.png")
            
            # Step 3
            logger.info("Step 3: Find Institutional Sign In")
            inst_buttons = await page.query_selector_all('a, button')
            inst_found = False
            for button in inst_buttons:
                text = await button.text_content()
                if text and 'institutional' in text.lower():
                    logger.info(f"Found institutional button: {text}")
                    await button.click()
                    inst_found = True
                    break
            
            if inst_found:
                await page.wait_for_timeout(3000)
                await page.screenshot(path=output_dir / "03_after_inst_click.png")
                
                # Step 4 - Look for any popup or modal
                logger.info("Step 4: Looking for popup content")
                
                # Get all visible text
                all_links = await page.query_selector_all('a, button')
                logger.info("Visible clickable elements:")
                for link in all_links[:20]:  # First 20
                    text = await link.text_content()
                    if text and text.strip():
                        logger.info(f"  - {text.strip()}")
                
                # Try different selectors
                access_selectors = [
                    'text="Access through your institution"',
                    'text="Access through institution"',
                    'text="Institutional access"',
                    'text="Institution"',
                    'a:has-text("institution")',
                    'button:has-text("institution")'
                ]
                
                access_found = False
                for selector in access_selectors:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        logger.info(f"Found access element: {text}")
                        await element.click()
                        access_found = True
                        break
                
                if access_found:
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=output_dir / "04_after_access_click.png")
                else:
                    logger.warning("Could not find access button, continuing anyway...")
                
                # Step 5 - Search for ETH
                logger.info("Step 5: Search for ETH")
                search_inputs = await page.query_selector_all('input[type="search"], input[type="text"]')
                logger.info(f"Found {len(search_inputs)} search inputs")
                
                if search_inputs:
                    # Use the first visible search input
                    for search_input in search_inputs:
                        if await search_input.is_visible():
                            await search_input.fill("ETH Zurich")
                            await page.keyboard.press('Enter')
                            break
                    
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=output_dir / "05_after_search.png")
                
                # Step 6 - Click ETH
                logger.info("Step 6: Click ETH option")
                eth_links = await page.query_selector_all('a, li, div')
                for link in eth_links:
                    text = await link.text_content()
                    if text and 'ETH' in text and 'Zurich' in text:
                        logger.info(f"Found ETH option: {text}")
                        await link.click()
                        break
                
                await page.wait_for_timeout(3000)
                await page.screenshot(path=output_dir / "06_eth_login_page.png")
                
                # Continue with login...
                logger.info("Stopping here for manual inspection")
                
            logger.info("\nCheck the screenshots in the 'ieee_steps' folder to see what happened.")
            return True
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            logger.info("Browser will stay open for 30 seconds...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_ieee_steps())