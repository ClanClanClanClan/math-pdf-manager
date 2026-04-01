#!/usr/bin/env python3
"""
IEEE Keyboard Navigation Test
Uses keyboard to select ETH from dropdown.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_ieee_keyboard():
    """Test using keyboard navigation for ETH selection."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    
    print(f"\n{'='*70}")
    print(f"⌨️  IEEE KEYBOARD NAVIGATION TEST")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print()
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Navigate to paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            print(f"📍 Current URL: {page.url}")
            
            # Accept cookies
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            print(f"\n🔐 AUTHENTICATION FLOW")
            print("-" * 50)
            
            # Step 1: Click institutional sign in
            print("Step 1: Clicking institutional sign in...")
            login_btn = await page.query_selector('a.inst-sign-in')
            await login_btn.click()
            print("✅ Clicked institutional sign in")
            await page.wait_for_timeout(3000)
            
            # Step 2: Click SeamlessAccess
            print("Step 2: Clicking SeamlessAccess...")
            seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            await seamless_btn.click()
            print("✅ Clicked SeamlessAccess")
            await page.wait_for_timeout(3000)
            
            # Step 3: Type ETH Zurich and use keyboard
            print("Step 3: Typing ETH Zurich with keyboard navigation...")
            search_input = await page.query_selector('input.inst-typeahead-input')
            
            # Clear and type
            await search_input.click()
            await search_input.fill("")
            await page.wait_for_timeout(500)
            
            # Type slowly to trigger autocomplete
            for char in "ETH Zurich":
                await search_input.type(char)
                await page.wait_for_timeout(100)
            
            print("✅ Typed ETH Zurich")
            
            # Wait for dropdown to appear
            await page.wait_for_timeout(2000)
            
            # Try keyboard navigation
            print("Using keyboard to select result...")
            
            # Press down arrow to select first result
            await search_input.press('ArrowDown')
            await page.wait_for_timeout(500)
            print("✅ Pressed Down Arrow")
            
            # Press Enter to select
            await search_input.press('Enter')
            await page.wait_for_timeout(500)
            print("✅ Pressed Enter to select")
            
            # Wait for navigation
            await page.wait_for_timeout(8000)
            
            # Check if at ETH login
            if 'ethz.ch' in page.url.lower() or 'aai' in page.url.lower():
                print("✅ SUCCESS! Reached ETH login page")
                print(f"📍 ETH URL: {page.url}")
                
                # Fill credentials
                username_field = await page.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                if username_field:
                    await username_field.fill(username)
                    print("✅ Filled username")
                
                password_field = await page.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                if password_field:
                    await password_field.fill(password)
                    print("✅ Filled password")
                
                # Submit
                submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_btn:
                    await submit_btn.click()
                    print("✅ Submitted credentials")
                    
                    # Wait for redirect
                    await page.wait_for_timeout(15000)
                    
                    if 'ieeexplore.ieee.org' in page.url:
                        print("✅ Redirected back to IEEE")
                        
                        # Check for PDF button
                        pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                        if pdf_button:
                            print("🎉 AUTHENTICATION SUCCESSFUL - PDF button found!")
                        else:
                            print("⚠️  No PDF button after authentication")
            else:
                print(f"⚠️  Not at ETH login. Current URL: {page.url}")
                print("The keyboard navigation might not have worked.")
                print("\nTrying alternative: Tab navigation...")
                
                # Go back to search input
                search_input = await page.query_selector('input.inst-typeahead-input')
                if search_input:
                    await search_input.click()
                    await search_input.fill("")
                    await page.wait_for_timeout(500)
                    
                    # Type again
                    await search_input.type("ETH Zurich")
                    await page.wait_for_timeout(2000)
                    
                    # Try Tab to focus on result
                    await search_input.press('Tab')
                    await page.wait_for_timeout(500)
                    print("✅ Pressed Tab")
                    
                    # Press Enter
                    await page.keyboard.press('Enter')
                    print("✅ Pressed Enter")
                    
                    await page.wait_for_timeout(8000)
                    
                    if 'ethz.ch' in page.url.lower():
                        print("✅ Tab navigation worked!")
                    else:
                        print("❌ Tab navigation also didn't work")
            
            print("\nBrowser staying open for 30 seconds...")
            await page.wait_for_timeout(30000)
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_ieee_keyboard())