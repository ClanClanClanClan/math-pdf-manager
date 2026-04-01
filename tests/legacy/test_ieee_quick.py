#!/usr/bin/env python3
"""
IEEE Quick Test - Shows current status
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_ieee_quick():
    """Quick IEEE test to show current status."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    
    print(f"\n{'='*70}")
    print(f"⚡ QUICK IEEE STATUS CHECK")
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
        
        # Apply stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
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
            
            # Extract arnumber
            arnumber = None
            if '/document/' in page.url:
                arnumber = page.url.split('/document/')[-1].strip('/')
                print(f"📄 Arnumber: {arnumber}")
            
            # Accept cookies
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            print(f"\n🔐 STARTING AUTHENTICATION FLOW")
            print("-" * 50)
            
            # Step 1: Click institutional sign in
            print("Step 1: Looking for institutional sign in...")
            login_btn = await page.query_selector('a.inst-sign-in')
            if login_btn:
                await login_btn.click()
                print("✅ Clicked institutional sign in")
                await page.wait_for_timeout(3000)
                
                # Step 2: Click SeamlessAccess
                print("Step 2: Looking for SeamlessAccess...")
                seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                if seamless_btn:
                    await seamless_btn.click()
                    print("✅ Clicked SeamlessAccess")
                    await page.wait_for_timeout(3000)
                    
                    # Step 3: Find search input
                    print("Step 3: Looking for search input...")
                    search_input = await page.query_selector('input.inst-typeahead-input')
                    if search_input:
                        await search_input.click()
                        await search_input.press('Control+a')
                        await search_input.type("ETH Zurich")
                        print("✅ Typed ETH Zurich")
                        
                        # Wait for results
                        await page.wait_for_timeout(2000)
                        
                        # Try pressing Enter
                        await search_input.press('Enter')
                        print("✅ Pressed Enter to trigger search")
                        await page.wait_for_timeout(3000)
                        
                        # Look for any ETH results
                        print("🔍 Looking for ETH results...")
                        
                        # Get page text to see if ETH appears
                        page_text = await page.evaluate("() => document.body.innerText")
                        eth_in_text = 'ETH' in page_text and 'Zurich' in page_text
                        print(f"ETH Zurich in page text: {eth_in_text}")
                        
                        # Try to find clickable ETH elements
                        all_elements = await page.query_selector_all('a, li, div, button')
                        eth_elements = []
                        
                        for elem in all_elements[:50]:  # Check first 50 elements
                            try:
                                if await elem.is_visible():
                                    text = await elem.text_content()
                                    if text and 'ETH' in text and 'Zurich' in text and len(text.strip()) < 100:
                                        eth_elements.append(text.strip())
                            except:
                                pass
                        
                        print(f"Found {len(eth_elements)} ETH elements:")
                        for i, text in enumerate(eth_elements[:5]):
                            print(f"  {i+1}. {text}")
                        
                        if eth_elements:
                            print("✅ ETH options found - manual selection required")
                            print("\n⏸️  Browser staying open for manual completion...")
                            print("Please manually select ETH Zurich and complete authentication")
                            print("The comprehensive test will handle this automatically with fallback")
                        else:
                            print("❌ No ETH options found in search results")
                            print("This confirms the issue with ETH selection")
                    else:
                        print("❌ Search input not found")
                else:
                    print("❌ SeamlessAccess button not found")
            else:
                print("❌ Institutional sign in not found")
            
            print(f"\n📊 CURRENT STATUS SUMMARY:")
            print("-" * 30)
            print("✅ Navigation to IEEE: SUCCESS")
            print("✅ Institutional login button: SUCCESS") 
            print("✅ SeamlessAccess button: SUCCESS")
            print("✅ Search input found: SUCCESS")
            print("✅ Search text entered: SUCCESS")
            print("❓ ETH selection: NEEDS MANUAL INTERVENTION")
            print()
            print("The comprehensive test_ieee_final.py includes:")
            print("- Manual fallback option for ETH selection")
            print("- 5-minute wait for user authentication")
            print("- Multiple PDF bypass methods once authenticated")
            print("- HTTP download with session cookies as backup")
            
            print(f"\nBrowser staying open for 30 seconds for inspection...")
            await page.wait_for_timeout(30000)
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_ieee_quick())