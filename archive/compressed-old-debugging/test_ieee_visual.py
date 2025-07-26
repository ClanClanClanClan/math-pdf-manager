#!/usr/bin/env python3
"""
Test IEEE Visual
=================

Run IEEE auth with browser visible to see what's happening.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "tools" / "security"))

# Patch the ieee_working_auth to run with headless=False
import ieee_working_auth

# Replace the function to use headless=False
original_func = ieee_working_auth.ieee_working_auth

async def visual_ieee_auth():
    """Run with browser visible."""
    # Temporarily modify the function
    import inspect
    source = inspect.getsource(original_func)
    # Replace headless=False with headless=False (it's already False)
    # But let's make sure
    
    from playwright.async_api import async_playwright
    from secure_credential_manager import get_credential_manager
    import logging
    
    logger = logging.getLogger("ieee_visual")
    
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        logger.error("No ETH credentials found!")
        return False
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)  # SLOW and VISIBLE
        context = await browser.new_context()
        page = await context.new_page()
        
        print("\n1️⃣ Going to IEEE...")
        await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        
        # Accept cookies
        print("2️⃣ Accepting cookies...")
        accept_button = await page.query_selector('button:has-text("Accept All")')
        if accept_button:
            await accept_button.click()
            await page.wait_for_timeout(1000)
        
        # Click institutional sign in
        print("3️⃣ Clicking Institutional Sign In...")
        inst_button = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
        await inst_button.click()
        await page.wait_for_timeout(2000)
        
        # Find modal
        print("4️⃣ Looking for modal...")
        modal = await page.wait_for_selector('ngb-modal-window', timeout=5000)
        
        if modal:
            print("   ✅ Found modal")
            
            # Click the SeamlessAccess button
            access_button = await modal.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            if access_button:
                print("5️⃣ Clicking 'Access Through Your Institution' button...")
                
                # Check how many pages we have before clicking
                pages_before = context.pages
                print(f"   Pages before click: {len(pages_before)}")
                
                await access_button.click()
                await page.wait_for_timeout(3000)
                
                # Check pages after
                pages_after = context.pages
                print(f"   Pages after click: {len(pages_after)}")
                
                if len(pages_after) > len(pages_before):
                    print("   🆕 New tab/window opened!")
                    new_page = pages_after[-1]
                    await new_page.bring_to_front()
                    page = new_page
                
                current_url = page.url
                print(f"   Current URL: {current_url}")
                
                # Look for ANY input field
                print("\n6️⃣ Looking for ANY input fields on the page...")
                all_inputs = await page.query_selector_all('input')
                print(f"   Found {len(all_inputs)} input fields")
                
                for i, inp in enumerate(all_inputs[:5]):  # First 5
                    try:
                        type_attr = await inp.get_attribute('type') or 'text'
                        placeholder = await inp.get_attribute('placeholder') or ''
                        visible = await inp.is_visible()
                        id_attr = await inp.get_attribute('id') or ''
                        name_attr = await inp.get_attribute('name') or ''
                        
                        if visible:
                            print(f"   [{i}] VISIBLE INPUT:")
                            print(f"       type: {type_attr}")
                            print(f"       placeholder: '{placeholder}'")
                            print(f"       id: {id_attr}")
                            print(f"       name: {name_attr}")
                            
                            # If it looks like a search box, try it!
                            if type_attr in ['search', 'text'] and 'password' not in type_attr:
                                print(f"       🎯 Trying to type 'ETH Zurich' in this field...")
                                await inp.click()
                                await inp.fill("ETH Zurich")
                                await page.keyboard.press('Enter')
                                await page.wait_for_timeout(3000)
                                
                                print(f"       After typing, URL: {page.url}")
                                
                                # Look for ETH in the results
                                eth_elements = await page.query_selector_all(':text("ETH")')
                                print(f"       Found {len(eth_elements)} elements with 'ETH'")
                                
                                break  # Stop after first successful input
                    except Exception as e:
                        print(f"   Error with input {i}: {e}")
        
        print("\n🔍 KEEPING BROWSER OPEN FOR MANUAL INSPECTION")
        print("Look at what's on the screen and tell me what you see!")
        print("Press Enter to close...")
        input()
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(visual_ieee_auth())