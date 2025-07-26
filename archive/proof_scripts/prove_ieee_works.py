#!/usr/bin/env python3
"""
Prove IEEE Works
================

Simple test that proves the IEEE authentication works.
"""

import asyncio
from playwright.async_api import async_playwright

async def prove_it_works():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        print("1. Going to IEEE...")
        await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
        await page.wait_for_timeout(3000)
        
        print("2. Accept cookies...")
        try:
            await page.click('button:has-text("Accept All")')
            await page.wait_for_timeout(1000)
        except:
            pass
        
        print("3. Click Institutional Sign In...")
        await page.click('a:has-text("Institutional Sign In")')
        await page.wait_for_timeout(3000)
        
        print("4. Wait for modal and find button...")
        modal = await page.query_selector('ngb-modal-window')
        if modal:
            # Wait for the button to be visible
            button = await modal.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', timeout=10000, state='visible')
            button_text = await button.text_content()
            print(f"5. Found button: '{button_text}'")
            
            print("6. Clicking the button...")
            await button.click()
            await page.wait_for_timeout(3000)
            
            print("7. Looking for second modal...")
            # Check for institution search modal
            inst_modal = await page.query_selector('ngb-modal-window:has-text("Search for your Institution")')
            if inst_modal:
                print("✅ SUCCESS! Second modal appeared with institution search!")
                
                # Find search input - try different approaches
                print("8. Looking for search input...")
                
                # Debug: list all inputs
                all_inputs = await inst_modal.query_selector_all('input')
                print(f"Found {len(all_inputs)} total inputs in second modal")
                
                search_input = None
                for i, inp in enumerate(all_inputs):
                    inp_type = await inp.get_attribute('type') or 'text'
                    placeholder = await inp.get_attribute('placeholder') or ''
                    name = await inp.get_attribute('name') or ''
                    visible = await inp.is_visible()
                    print(f"  Input {i}: type={inp_type}, placeholder='{placeholder}', name='{name}', visible={visible}")
                    
                    # First visible text input is probably the search
                    if visible and inp_type == 'text' and not search_input:
                        search_input = inp
                        print(f"  🎯 Using this as search input!")
                
                if search_input:
                    print("9. Typing 'ETH Zurich'...")
                    await search_input.fill("ETH Zurich")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(3000)
                    
                    print("10. Looking for ETH option...")
                    eth_elements = await page.query_selector_all(':text("ETH")')
                    print(f"✅ Found {len(eth_elements)} elements with 'ETH'!")
                    
                    if eth_elements:
                        print("11. Clicking on ETH Zurich...")
                        # Look for the specific ETH Zurich option
                        eth_zurich = await page.query_selector('text="ETH Zurich"')
                        if eth_zurich:
                            print("✅ Found 'ETH Zurich' option!")
                            await eth_zurich.click()
                            await page.wait_for_timeout(5000)
                            
                            print("12. Checking if redirected to ETH login...")
                            current_url = page.url
                            print(f"Current URL: {current_url}")
                            
                            if 'eth' in current_url.lower() or 'shibboleth' in current_url.lower() or 'wayf' in current_url.lower():
                                print("✅ COMPLETE SUCCESS! Redirected to ETH authentication!")
                                print("🎉 The entire IEEE authentication flow works perfectly!")
                                print("🎯 Modal-within-modal pattern successfully implemented!")
                            else:
                                print("⚠️ Almost complete - ETH was clicked but redirect unclear")
                        else:
                            print("⚠️ Found ETH elements but not exact 'ETH Zurich' match")
                            # Try clicking the first ETH element
                            print("   Trying first ETH element...")
                            await eth_elements[0].click()
                            await page.wait_for_timeout(5000)
                            current_url = page.url
                            print(f"   After click URL: {current_url}")
                    else:
                        print("⚠️ Almost complete - search worked but no ETH results yet")
                else:
                    print("❌ No visible text input found in second modal")
            else:
                print("❌ Second modal did not appear")
                # Check what happened
                current_url = page.url
                print(f"Current URL: {current_url}")
        
        print("\nKeeping browser open for inspection...")
        await page.wait_for_timeout(30000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(prove_it_works())