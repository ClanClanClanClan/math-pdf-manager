#!/usr/bin/env python3
"""
IEEE Button Debug
=================

Debug what happens after clicking the modal button.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("button_debug")

nest_asyncio.apply()

async def debug_button_click():
    from playwright.async_api import async_playwright
    
    output_dir = Path("button_debug")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: logger.info(f"🖥️  Console: {msg.text}"))
        
        # Enable request logging
        page.on("request", lambda req: logger.info(f"➡️  Request: {req.method} {req.url}"))
        
        try:
            # Navigate
            logger.info("1️⃣  Navigating to IEEE...")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Accept cookies
            logger.info("2️⃣  Accepting cookies...")
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in
            logger.info("3️⃣  Clicking Institutional Sign In...")
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            await page.wait_for_timeout(3000)
            
            # Take screenshot before clicking
            await page.screenshot(path=output_dir / "01_before_click.png")
            
            # Find and analyze the button
            logger.info("\n4️⃣  ANALYZING BUTTON:")
            logger.info("=" * 50)
            
            buttons = await page.query_selector_all('button:has-text("Access Through Your Institution")')
            logger.info(f"Found {len(buttons)} matching buttons")
            
            if buttons:
                button = buttons[0]  # Use first button
                
                # Get button properties
                properties = await button.evaluate('''el => {
                    return {
                        text: el.textContent,
                        className: el.className,
                        onclick: el.onclick ? el.onclick.toString() : null,
                        href: el.getAttribute('href'),
                        type: el.getAttribute('type'),
                        disabled: el.disabled,
                        visible: el.offsetParent !== null
                    }
                }''')
                
                logger.info(f"Button properties: {properties}")
                
                # Click with different methods
                logger.info("\n5️⃣  CLICKING BUTTON...")
                
                # Method 1: Regular click
                await button.click()
                logger.info("Clicked button, waiting 3 seconds...")
                await page.wait_for_timeout(3000)
                
                # Check URL change
                new_url = page.url
                logger.info(f"\n6️⃣  URL after click: {new_url}")
                
                # Take screenshot after clicking
                await page.screenshot(path=output_dir / "02_after_click.png")
                
                # Check if we're still on the same page
                if new_url == "https://ieeexplore.ieee.org/document/8347162":
                    logger.info("\n⚠️  Still on same page!")
                    
                    # Check if modal is still open
                    modal = await page.query_selector('ngb-modal-window')
                    if modal:
                        logger.info("Modal is still open")
                    else:
                        logger.info("Modal is closed")
                    
                    # Try clicking button again with force
                    logger.info("\n7️⃣  Trying force click...")
                    await button.click(force=True)
                    await page.wait_for_timeout(3000)
                    
                    new_url2 = page.url
                    logger.info(f"URL after force click: {new_url2}")
                else:
                    logger.info("✅ Navigated to new page!")
            
            logger.info("\n" + "=" * 50)
            logger.info("Check the screenshots in 'button_debug' folder")
            logger.info("=" * 50)
            
            # Keep browser open
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=output_dir / "error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_button_click())