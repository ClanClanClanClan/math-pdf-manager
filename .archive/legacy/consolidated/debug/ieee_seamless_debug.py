#!/usr/bin/env python3
"""
IEEE SeamlessAccess Debug
=========================

Debug the SeamlessAccess integration.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seamless_debug")

nest_asyncio.apply()

async def debug_seamless():
    from playwright.async_api import async_playwright
    
    output_dir = Path("seamless_debug")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Monitor network activity
        page.on("framenavigated", lambda frame: logger.info(f"🔄 Frame navigated: {frame.url}"))
        
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
            
            # Now check for iframe
            logger.info("\n4️⃣  CHECKING FOR IFRAMES:")
            logger.info("=" * 50)
            
            iframes = await page.query_selector_all('iframe')
            logger.info(f"Found {len(iframes)} iframes")
            
            for i, iframe in enumerate(iframes):
                src = await iframe.get_attribute('src')
                name = await iframe.get_attribute('name')
                id_attr = await iframe.get_attribute('id')
                logger.info(f"\nIframe {i}:")
                logger.info(f"  ID: {id_attr}")
                logger.info(f"  Name: {name}")
                logger.info(f"  Src: {src}")
            
            # Check if SeamlessAccess is in an iframe
            if iframes:
                # Try to interact with the iframe
                for iframe in iframes:
                    src = await iframe.get_attribute('src')
                    if src and 'seamlessaccess' in src:
                        logger.info("\n5️⃣  FOUND SEAMLESSACCESS IFRAME!")
                        
                        # Get frame handle
                        frame = await iframe.content_frame()
                        if frame:
                            logger.info("Got frame handle, looking for button inside...")
                            
                            # Wait for content to load in frame
                            await frame.wait_for_timeout(2000)
                            
                            # Try to find button in frame
                            buttons = await frame.query_selector_all('button')
                            logger.info(f"Found {len(buttons)} buttons in iframe")
                            
                            for button in buttons:
                                text = await button.text_content()
                                if text:
                                    logger.info(f"  Button: {text.strip()}")
                        break
            
            # Also check the main page buttons again
            logger.info("\n6️⃣  MAIN PAGE BUTTONS:")
            main_buttons = await page.query_selector_all('button')
            for button in main_buttons[:10]:  # First 10
                text = await button.text_content()
                if text and text.strip():
                    logger.info(f"  - {text.strip()}")
            
            # Try a different approach - look for the modal dialog
            logger.info("\n7️⃣  MODAL ANALYSIS:")
            modal = await page.query_selector('ngb-modal-window')
            if modal:
                # Check if the button triggers JavaScript
                buttons = await modal.query_selector_all('button')
                for button in buttons:
                    text = await button.text_content()
                    if text and "Access Through Your Institution" in text:
                        logger.info(f"Found button: {text}")
                        
                        # Get onclick handler
                        onclick = await button.evaluate('el => el.onclick ? el.onclick.toString() : null')
                        logger.info(f"OnClick handler: {onclick}")
                        
                        # Check for event listeners
                        has_listeners = await button.evaluate('''el => {
                            const listeners = getEventListeners ? getEventListeners(el) : null;
                            return listeners ? Object.keys(listeners).length > 0 : 'unknown';
                        }''')
                        logger.info(f"Has event listeners: {has_listeners}")
                        
                        # Try clicking with JavaScript
                        logger.info("\n8️⃣  Clicking button with JavaScript...")
                        await button.evaluate('el => el.click()')
                        await page.wait_for_timeout(3000)
                        
                        # Check URL
                        new_url = page.url
                        logger.info(f"URL after JS click: {new_url}")
                        
                        # Check for new windows/tabs
                        all_pages = context.pages
                        logger.info(f"Number of pages/tabs: {len(all_pages)}")
                        
                        if len(all_pages) > 1:
                            logger.info("New tab/window opened!")
                            new_page = all_pages[-1]
                            logger.info(f"New page URL: {new_page.url}")
            
            logger.info("\n" + "=" * 50)
            await page.screenshot(path=output_dir / "seamless_state.png")
            logger.info("Screenshot saved. Check browser state.")
            logger.info("=" * 50)
            
            # Keep browser open
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_seamless())