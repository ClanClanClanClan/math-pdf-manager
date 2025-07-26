#!/usr/bin/env python3
"""
Debug IEEE Actual Problem
==========================

Find out what's actually happening after clicking ETH Zurich.
"""

import asyncio
from playwright.async_api import async_playwright
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager


async def debug_ieee_flow():
    """Debug what actually happens."""
    
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials!")
        return
    
    print(f"✅ Have ETH credentials: {username[:3]}***")
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        print(f"\n1️⃣ Going to IEEE: {ieee_url}")
        await page.goto(ieee_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        print(f"   Now at: {page.url}")
        
        # Accept cookies
        try:
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                print("   ✅ Accepted cookies")
                await page.wait_for_timeout(1000)
        except:
            pass
        
        # Click institutional sign in
        print("\n2️⃣ Looking for Institutional Sign In...")
        inst_button = await page.wait_for_selector('a:has-text("Institutional Sign In")')
        await inst_button.click()
        print("   ✅ Clicked Institutional Sign In")
        await page.wait_for_timeout(2000)
        
        # Find modal
        print("\n3️⃣ Looking for modal...")
        modal = await page.wait_for_selector('ngb-modal-window')
        print("   ✅ Found modal")
        
        # Get ALL links in modal and print them
        modal_links = await modal.query_selector_all('a')
        print(f"   Modal has {len(modal_links)} links:")
        
        for i, link in enumerate(modal_links):
            text = await link.text_content()
            href = await link.get_attribute('href')
            print(f"   [{i}] Text: '{text}' | Href: {href}")
        
        # Click the FIRST link (since there are only 2)
        if modal_links:
            print(f"\n4️⃣ Clicking first link in modal...")
            await modal_links[0].click()
            await page.wait_for_load_state('networkidle')
            print(f"   Now at: {page.url}")
            await page.wait_for_timeout(2000)
        
        # Search for ETH
        print("\n5️⃣ Looking for search box...")
        search_input = None
        search_selectors = [
            'input[placeholder*="institution"]',
            'input[placeholder*="organization"]',
            'input[id="search"]',
            'input[type="search"]',
            'input[type="text"]'
        ]
        
        for selector in search_selectors:
            try:
                inputs = await page.query_selector_all(selector)
                for inp in inputs:
                    if await inp.is_visible():
                        placeholder = await inp.get_attribute('placeholder') or ''
                        print(f"   Found input: {selector} (placeholder: '{placeholder}')")
                        if not search_input:
                            search_input = inp
            except:
                pass
        
        if search_input:
            print("   ✅ Using search input")
            await search_input.fill("ETH Zurich")
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(2000)
        
        # Look for ETH 
        print("\n6️⃣ Looking for ETH Zurich...")
        
        # Get ALL clickable elements with ETH
        all_elements = await page.query_selector_all('a, button, div[role="button"], li[role="option"], span')
        eth_elements = []
        
        for elem in all_elements:
            try:
                text = await elem.text_content()
                if text and 'eth' in text.lower():
                    tag = await elem.evaluate('el => el.tagName')
                    eth_elements.append((elem, text.strip(), tag))
                    print(f"   Found ETH element: <{tag}> '{text.strip()}'")
            except:
                pass
        
        # Click the first ETH element
        if eth_elements:
            elem, text, tag = eth_elements[0]
            print(f"\n7️⃣ Clicking: '{text}'")
            await elem.click()
            await page.wait_for_timeout(3000)
            print(f"   Now at: {page.url}")
            
            # Take screenshot
            await page.screenshot(path="after_eth_click.png")
            print("   📸 Screenshot saved: after_eth_click.png")
        
        # Check what's on the page now
        print("\n8️⃣ What's on the page now?")
        
        # Look for ANY input fields
        all_inputs = await page.query_selector_all('input')
        print(f"   Found {len(all_inputs)} input fields:")
        
        for i, inp in enumerate(all_inputs[:10]):  # First 10
            try:
                name = await inp.get_attribute('name') or ''
                id_attr = await inp.get_attribute('id') or ''
                type_attr = await inp.get_attribute('type') or ''
                placeholder = await inp.get_attribute('placeholder') or ''
                visible = await inp.is_visible()
                print(f"   [{i}] name='{name}' id='{id_attr}' type='{type_attr}' placeholder='{placeholder}' visible={visible}")
            except:
                pass
        
        # Check if we're still on IEEE or redirected
        current_url = page.url
        if 'ieee' in current_url:
            print("\n⚠️  Still on IEEE - didn't redirect to ETH login!")
        elif 'eth' in current_url or 'switch' in current_url:
            print("\n✅ Redirected to ETH/Switch login")
        else:
            print(f"\n❓ On unknown page: {current_url}")
        
        print("\n🔍 Keeping browser open for inspection...")
        print("Press Enter to close...")
        input()
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_ieee_flow())