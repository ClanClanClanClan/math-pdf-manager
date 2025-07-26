#!/usr/bin/env python3
"""
DEBUG WILEY INSTITUTIONAL PAGE
==============================

See what happens after clicking institutional login
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def debug_wiley_institution():
    """Debug Wiley institutional authentication"""
    
    print("🔍 WILEY INSTITUTIONAL AUTH DEBUG")
    print("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Navigate to test DOI
        test_doi = "10.1002/anie.202004934"
        url = f"https://doi.org/{test_doi}"
        print(f"📍 Navigating to: {url}")
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Accept cookies
        try:
            cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
            if cookie_btn:
                print("🍪 Accepting cookies...")
                await cookie_btn.click()
                await page.wait_for_timeout(2000)
        except:
            pass
        
        # Click Login/Register
        try:
            login_btn = await page.wait_for_selector('button:has-text("Login / Register")', timeout=5000)
            if login_btn:
                print("🔑 Clicking Login/Register...")
                await login_btn.click()
                await page.wait_for_timeout(2000)
        except:
            print("❌ No Login/Register button found")
        
        # Click Institutional login
        try:
            inst_link = await page.wait_for_selector('a:has-text("Institutional login")', timeout=5000)
            if inst_link:
                print("🏛️ Clicking Institutional login...")
                await inst_link.click()
                await page.wait_for_timeout(5000)
                
                new_url = page.url
                print(f"📍 New URL: {new_url}")
                
                # Take screenshot
                await page.screenshot(path='wiley_institution_page.png')
                print("📸 Screenshot: wiley_institution_page.png")
                
                # Check what's on the page
                print("\n🔍 Page analysis:")
                
                # Look for any search boxes
                search_inputs = await page.query_selector_all('input[type="search"], input[type="text"]')
                print(f"   Found {len(search_inputs)} search/text inputs")
                
                for i, inp in enumerate(search_inputs[:5]):
                    try:
                        placeholder = await inp.get_attribute('placeholder')
                        name = await inp.get_attribute('name')
                        visible = await inp.is_visible()
                        print(f"   Input {i+1}: placeholder='{placeholder}', name='{name}', visible={visible}")
                    except:
                        pass
                
                # Look for any dropdowns
                selects = await page.query_selector_all('select')
                print(f"\n   Found {len(selects)} select dropdowns")
                
                # Look for ETH text anywhere
                eth_elements = await page.query_selector_all('*:has-text("ETH"), *:has-text("Swiss")')
                print(f"\n   Found {len(eth_elements)} elements mentioning ETH/Swiss")
                
                # Check for iframes
                iframes = await page.query_selector_all('iframe')
                print(f"\n   Found {len(iframes)} iframes")
                
                if iframes:
                    for i, iframe in enumerate(iframes):
                        try:
                            src = await iframe.get_attribute('src')
                            print(f"   Iframe {i+1} src: {src}")
                        except:
                            pass
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("\n⏸️ Keeping browser open for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_wiley_institution())