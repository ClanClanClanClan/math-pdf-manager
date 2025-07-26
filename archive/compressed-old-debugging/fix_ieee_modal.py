#!/usr/bin/env python3
"""
Fix IEEE Modal Click
=====================

Find and click the RIGHT button in the IEEE modal.
"""

import asyncio
from playwright.async_api import async_playwright
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager


async def fix_ieee_modal():
    """Fix the modal click issue."""
    
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        print("1️⃣ Going to IEEE paper...")
        await page.goto(ieee_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        
        # Accept cookies
        try:
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                print("   ✅ Accepted cookies")
                await page.wait_for_timeout(1000)
        except:
            pass
        
        # Click Institutional Sign In
        print("\n2️⃣ Clicking Institutional Sign In...")
        inst_button = await page.wait_for_selector('a:has-text("Institutional Sign In")')
        await inst_button.click()
        print("   ✅ Clicked")
        await page.wait_for_timeout(2000)
        
        # CAREFULLY examine the modal
        print("\n3️⃣ EXAMINING MODAL CONTENTS...")
        modal = await page.wait_for_selector('ngb-modal-window')
        
        # Get ALL elements in the modal
        all_modal_elements = await modal.query_selector_all('*')
        print(f"   Modal has {len(all_modal_elements)} total elements")
        
        # Look for clickable elements (not just links)
        clickable_elements = await modal.query_selector_all('a, button, div[role="button"], span[role="button"], [onclick]')
        print(f"   Modal has {len(clickable_elements)} clickable elements:")
        
        for i, elem in enumerate(clickable_elements):
            tag = await elem.evaluate('el => el.tagName')
            text = await elem.text_content()
            classes = await elem.get_attribute('class') or ''
            href = await elem.get_attribute('href') if tag == 'A' else None
            role = await elem.get_attribute('role') or ''
            onclick = await elem.get_attribute('onclick') or ''
            
            print(f"\n   [{i}] <{tag}>")
            print(f"       Text: '{text.strip() if text else 'NO TEXT'}'")
            print(f"       Classes: {classes}")
            print(f"       Href: {href}")
            print(f"       Role: {role}")
            print(f"       Onclick: {onclick}")
            
            # Check if visible
            is_visible = await elem.is_visible()
            print(f"       Visible: {is_visible}")
        
        # Also check for any text that mentions "institution"
        print("\n4️⃣ Looking for ANY text mentioning institution/access...")
        modal_text = await modal.text_content()
        lines = modal_text.split('\n')
        for line in lines:
            if line.strip() and ('institution' in line.lower() or 'access' in line.lower() or 
                                'sign' in line.lower() or 'athens' in line.lower()):
                print(f"   • {line.strip()}")
        
        # Look for the modal body specifically
        print("\n5️⃣ Looking for modal body content...")
        modal_body = await modal.query_selector('.modal-body, [class*="modal-body"]')
        if modal_body:
            body_html = await modal_body.inner_html()
            print("   Modal body HTML (first 500 chars):")
            print(f"   {body_html[:500]}...")
        
        # Take screenshot of modal
        await modal.screenshot(path="ieee_modal_content.png")
        print("\n📸 Modal screenshot saved: ieee_modal_content.png")
        
        print("\n🔍 Browser staying open. Check the modal manually!")
        print("What should we click on?")
        print("Press Enter to close...")
        input()
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(fix_ieee_modal())