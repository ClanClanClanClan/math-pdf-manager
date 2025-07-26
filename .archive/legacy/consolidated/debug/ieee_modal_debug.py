#!/usr/bin/env python3
"""
IEEE Modal Debug
================

Debug what's inside the modal.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("modal_debug")

nest_asyncio.apply()

async def debug_modal():
    from playwright.async_api import async_playwright
    
    output_dir = Path("modal_debug")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
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
            
            # Now examine the modal
            logger.info("\n4️⃣  MODAL CONTENT ANALYSIS:")
            logger.info("=" * 50)
            
            # Find the modal
            modal = await page.query_selector('ngb-modal-window')
            if modal:
                logger.info("✅ Found modal window")
                
                # Get ALL clickable elements in the modal
                all_elements = await modal.query_selector_all('a, button, [role="button"]')
                logger.info(f"\n📋 Found {len(all_elements)} clickable elements in modal:\n")
                
                for i, elem in enumerate(all_elements):
                    tag = await elem.evaluate('el => el.tagName')
                    text = await elem.text_content()
                    href = await elem.get_attribute('href') if tag == 'A' else None
                    classes = await elem.get_attribute('class')
                    
                    logger.info(f"{i+1}. {tag}")
                    logger.info(f"   Text: {text.strip() if text else '(no text)'}")
                    if href:
                        logger.info(f"   Href: {href}")
                    if classes:
                        logger.info(f"   Classes: {classes}")
                    logger.info("")
                
                # Take screenshot
                await page.screenshot(path=output_dir / "modal_content.png")
                logger.info(f"📸 Screenshot saved to {output_dir}/modal_content.png")
                
            else:
                logger.error("❌ No modal found!")
            
            logger.info("\n" + "=" * 50)
            logger.info("👀 Please check the browser to see the modal.")
            logger.info("🔍 Look for a link that says 'Access through your institution'")
            logger.info("📝 Note which element number it is from the list above.")
            logger.info("=" * 50)
            
            # Keep browser open
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_modal())