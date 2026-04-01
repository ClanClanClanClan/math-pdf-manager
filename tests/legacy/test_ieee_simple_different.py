#!/usr/bin/env python3
"""
Simple IEEE Different Paper Test
Test with one different paper to check if blocking is paper-specific.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_simple_different():
    """Simple test with a different paper."""
    
    # Try a different well-known IEEE DOI
    test_doi = "10.1109/MCOM.2020.1900659"  # Different paper
    
    print(f"\n{'='*70}")
    print(f"🔬 IEEE SIMPLE DIFFERENT PAPER TEST")
    print(f"{'='*70}")
    print(f"Testing DOI: {test_doi}")
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
            
            # Navigate to different paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            print(f"📍 Current URL: {page.url}")
            
            # Check if we're at IEEE
            if 'ieeexplore.ieee.org' not in page.url:
                print("❌ DOI didn't resolve to IEEE - trying different approach")
                
                # Try direct search
                await page.goto("https://ieeexplore.ieee.org", wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                
                search_box = await page.query_selector('input[name="queryText"], input.search-input, input[placeholder*="Search"]')
                if search_box:
                    await search_box.fill(test_doi)
                    await search_box.press('Enter')
                    await page.wait_for_timeout(5000)
                    
                    # Click first result
                    first_result = await page.query_selector('a[href*="/document/"]')
                    if first_result:
                        await first_result.click()
                        await page.wait_for_timeout(3000)
                        print(f"📍 Found paper at: {page.url}")
                    else:
                        print("❌ Could not find paper")
                        await browser.close()
                        return
            
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
            
            # Check if PDF button exists (not authenticated)
            pdf_button_unauth = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            if pdf_button_unauth:
                print("✅ PDF button visible without authentication")
                print("🎯 Testing PDF click WITHOUT authentication first...")
                
                # Test click without auth
                await pdf_button_unauth.click()
                await page.wait_for_timeout(5000)
                
                if '/stamp/stamp.jsp' in page.url:
                    print("🎉 SUCCESS! PDF accessible WITHOUT authentication!")
                    print("This paper might be open access")
                    print("Browser staying open...")
                    await page.wait_for_timeout(60000)
                    await browser.close()
                    return
                else:
                    print("❌ PDF click failed without auth (expected)")
                    # Go back to paper
                    await page.go_back()
                    await page.wait_for_timeout(2000)
            
            print(f"\n🔐 PERFORMING AUTHENTICATION")
            print("-" * 50)
            
            # Authentication
            login_btn = await page.query_selector('a.inst-sign-in')
            if login_btn:
                await login_btn.click()
                print("✅ Clicked institutional sign in")
                await page.wait_for_timeout(3000)
                
                seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                if seamless_btn:
                    await seamless_btn.click()
                    print("✅ Clicked SeamlessAccess")
                    await page.wait_for_timeout(3000)
                    
                    search_input = await page.query_selector('input.inst-typeahead-input')
                    if search_input:
                        await search_input.click()
                        await search_input.fill("")
                        await page.wait_for_timeout(500)
                        
                        for char in "ETH Zurich":
                            await search_input.type(char)
                            await page.wait_for_timeout(100)
                        
                        await page.wait_for_timeout(2000)
                        await search_input.press('ArrowDown')
                        await page.wait_for_timeout(500)
                        await search_input.press('Enter')
                        print("✅ Selected ETH Zurich")
                        
                        await page.wait_for_timeout(8000)
                        
                        # ETH login
                        if 'ethz.ch' in page.url.lower():
                            print("✅ At ETH login page")
                            
                            username_field = await page.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                            if username_field:
                                await username_field.fill(username)
                            
                            password_field = await page.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                            if password_field:
                                await password_field.fill(password)
                            
                            submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                            if submit_btn:
                                await submit_btn.click()
                                await page.wait_for_timeout(15000)
                                print("✅ Authentication completed")
            
            # Check authentication success
            if 'ieeexplore.ieee.org' in page.url:
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    print("🎉 AUTHENTICATION SUCCESSFUL for this paper!")
                    
                    print(f"\n📄 TESTING PDF ACCESS")
                    print("-" * 50)
                    
                    # Test PDF click
                    print("Test 1: Clicking PDF button...")
                    before_url = page.url
                    await pdf_button.click()
                    await page.wait_for_timeout(8000)
                    after_url = page.url
                    
                    if '/stamp/stamp.jsp' in after_url:
                        print("🎉 SUCCESS! PDF click worked for this paper!")
                        print(f"📄 PDF URL: {after_url}")
                        
                        download_btn = await page.query_selector('button[title*="Download"], a[title*="Download"]')
                        if download_btn:
                            print("✅ Download button available!")
                        
                        print("🎉 THIS PAPER WORKS! PDF is accessible after authentication!")
                        print("Browser staying open for manual download...")
                        await page.wait_for_timeout(120000)
                        await browser.close()
                        return
                    
                    elif after_url != before_url:
                        print(f"❌ Redirected to: {after_url}")
                    else:
                        print("❌ No navigation occurred")
                    
                    # Test direct navigation
                    if arnumber:
                        print("Test 2: Direct navigation...")
                        pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arnumber}"
                        await page.goto(pdf_url, wait_until='domcontentloaded')
                        await page.wait_for_timeout(8000)
                        
                        if '/stamp/stamp.jsp' in page.url:
                            print("🎉 SUCCESS! Direct navigation worked!")
                            print(f"📄 PDF URL: {page.url}")
                            print("🎉 THIS PAPER WORKS via direct navigation!")
                            print("Browser staying open...")
                            await page.wait_for_timeout(120000)
                            await browser.close()
                            return
                        else:
                            print(f"❌ Direct navigation blocked: {page.url}")
                    
                    print("❌ Both methods failed for this paper too")
                    print("🔍 Confirms system-wide blocking across different papers")
                else:
                    print("❌ No PDF button after authentication")
            
            print(f"\n📊 RESULT: Same blocking behavior as original paper")
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_simple_different())