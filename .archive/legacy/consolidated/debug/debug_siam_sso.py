#!/usr/bin/env python3
"""
Debug SIAM SSO
==============

Debug the SIAM SSO page to understand the institution selection.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("debug_siam_sso")

nest_asyncio.apply()

async def debug_siam_sso():
    from playwright.async_api import async_playwright
    
    output_dir = Path("debug_siam_sso")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Go to SIAM paper
            siam_url = "https://epubs.siam.org/doi/10.1137/S0036142997325199"
            logger.info(f"Going to SIAM: {siam_url}")
            
            await page.goto(siam_url, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(3000)
            
            # Click institutional access
            access_link = await page.query_selector('a:has-text("Access via your Institution")')
            await access_link.click()
            await page.wait_for_timeout(5000)
            
            logger.info(f"Current URL: {page.url}")
            logger.info(f"Page title: {await page.title()}")
            
            # Take screenshot
            await page.screenshot(path=output_dir / "sso_page.png")
            logger.info("📸 Screenshot saved: sso_page.png")
            
            # List all input fields
            inputs = await page.query_selector_all('input')
            logger.info(f"\n📝 Found {len(inputs)} input fields:")
            for i, inp in enumerate(inputs):
                tag = await inp.evaluate('el => el.outerHTML')
                logger.info(f"  {i+1}: {tag[:200]}...")
            
            # List all buttons
            buttons = await page.query_selector_all('button')
            logger.info(f"\n🔘 Found {len(buttons)} buttons:")
            for i, btn in enumerate(buttons):
                text = await btn.text_content()
                tag = await btn.evaluate('el => el.outerHTML')
                logger.info(f"  {i+1}: '{text}' -> {tag[:150]}...")
            
            # List all links
            links = await page.query_selector_all('a')
            logger.info(f"\n🔗 Found {len(links)} links:")
            for i, link in enumerate(links[:10]):  # First 10 only
                text = await link.text_content()
                href = await link.get_attribute('href')
                if text and text.strip():
                    logger.info(f"  {i+1}: '{text.strip()}' -> {href}")
            
            # Look for forms
            forms = await page.query_selector_all('form')
            logger.info(f"\n📋 Found {len(forms)} forms:")
            for i, form in enumerate(forms):
                action = await form.get_attribute('action')
                method = await form.get_attribute('method')
                logger.info(f"  {i+1}: action='{action}' method='{method}'")
            
            # Get page source
            content = await page.content()
            with open(output_dir / "sso_page.html", 'w') as f:
                f.write(content)
            logger.info("💾 Page source saved: sso_page.html")
            
            logger.info("\n=== Debug Complete ===")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.info("Browser staying open for inspection...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_siam_sso())