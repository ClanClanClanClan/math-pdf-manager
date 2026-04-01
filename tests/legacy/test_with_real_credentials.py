#!/usr/bin/env python3
"""
Test with REAL ETH Credentials - ULTRATHINK Reality Check
Using actual credentials from environment to test complete flow
"""

import asyncio
import logging
import os

from playwright.async_api import async_playwright

from cookie_banner_handler import CookieBannerHandler, PublisherSpecificHandlers

logging.basicConfig(level=logging.WARNING)  # Reduce noise

# Get credentials from environment
ETH_USERNAME = os.getenv('ETH_USERNAME')
ETH_PASSWORD = os.getenv('ETH_PASSWORD')

if not ETH_USERNAME or not ETH_PASSWORD:
    print("❌ ETH credentials not found in environment")
    print("   Set ETH_USERNAME and ETH_PASSWORD environment variables")
    exit(1)

print(f"✅ Found ETH credentials for user: {ETH_USERNAME}")


async def test_complete_flow_with_credentials():
    """Test the complete flow with real ETH credentials"""
    print("\n🔐 TESTING COMPLETE FLOW WITH REAL CREDENTIALS")
    print("=" * 60)
    
    # Use a confirmed paywalled paper
    paper_url = "https://link.springer.com/article/10.1007/s00453-024-01221-8"
    
    async with async_playwright() as p:
        # Use visible browser to see what's happening
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1: Load paper
            print("\n📄 Step 1: Loading paywalled paper...")
            await page.goto(paper_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Step 2: Handle cookies
            print("🍪 Step 2: Handling cookies...")
            dismissed = await PublisherSpecificHandlers.handle_springer_cookies(page)
            if dismissed:
                print("   ✅ Cookies handled")
            
            # Step 3: Go directly to institutional login
            print("🏛️ Step 3: Going to institutional login...")
            inst_url = f"https://link.springer.com/athens-shibboleth-login?previousUrl={paper_url}"
            await page.goto(inst_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            print(f"   📍 Current URL: {current_url[:80]}...")
            
            # Step 4: Search for ETH
            print("🔍 Step 4: Searching for ETH Zurich...")
            
            if "wayf" in current_url.lower():
                print("   ✅ Reached WAYF page")
                
                # Find search input
                search_input = page.locator('#searchFormTextInput, input[name="search"]').first
                if await search_input.count() > 0:
                    print("   Found search input")
                    
                    # Type slowly to trigger autocomplete
                    await search_input.type("ETH Zurich", delay=150)
                    await page.wait_for_timeout(3000)
                    
                    # Look for dropdown
                    dropdown = page.locator('[role="listbox"]').first
                    if await dropdown.count() > 0:
                        print("   ✅ Autocomplete dropdown appeared")
                        
                        # Click ETH option
                        eth_option = dropdown.locator('*:has-text("ETH Zurich")').first
                        if await eth_option.count() > 0:
                            print("   ✅ Found 'ETH Zurich' in dropdown")
                            await eth_option.click()
                            await page.wait_for_timeout(5000)
                        else:
                            # Try without dropdown
                            print("   Trying form submission...")
                            await page.keyboard.press('Enter')
                            await page.wait_for_timeout(5000)
                    else:
                        # No dropdown, try submitting
                        print("   No dropdown, submitting form...")
                        await page.keyboard.press('Enter')
                        await page.wait_for_timeout(5000)
                    
                    # Step 5: Check if at ETH login
                    current_url = page.url
                    print(f"\n📍 Step 5: After institution selection...")
                    print(f"   Current URL: {current_url[:80]}...")
                    
                    if "ethz.ch" in current_url or "aai-logon" in current_url:
                        print("   ✅ Reached ETH login page!")
                        
                        # Step 6: Login with credentials
                        print("\n🔐 Step 6: Logging in with ETH credentials...")
                        
                        # Common username field selectors
                        username_selectors = [
                            'input[name="j_username"]',
                            'input[name="username"]',
                            'input[id="username"]',
                            'input[type="text"]'
                        ]
                        
                        username_field = None
                        for selector in username_selectors:
                            field = page.locator(selector).first
                            if await field.count() > 0:
                                username_field = field
                                print(f"   Found username field: {selector}")
                                break
                        
                        if username_field:
                            await username_field.fill(ETH_USERNAME)
                            print(f"   ✅ Entered username: {ETH_USERNAME}")
                            
                            # Find password field
                            password_field = page.locator('input[type="password"]').first
                            if await password_field.count() > 0:
                                await password_field.fill(ETH_PASSWORD)
                                print("   ✅ Entered password")
                                
                                # Submit
                                submit_button = page.locator('button[type="submit"], input[type="submit"]').first
                                if await submit_button.count() > 0:
                                    print("   🔄 Submitting login...")
                                    await submit_button.click()
                                    await page.wait_for_timeout(10000)  # Wait for redirect
                                    
                                    # Step 7: Check if authenticated
                                    current_url = page.url
                                    print(f"\n📍 Step 7: After authentication...")
                                    print(f"   Current URL: {current_url[:80]}...")
                                    
                                    if "springer.com" in current_url:
                                        print("   ✅ Redirected back to Springer!")
                                        
                                        # Check for PDF access
                                        pdf_selectors = [
                                            'a[href*=".pdf"]',
                                            'button:has-text("Download PDF")',
                                            'a:has-text("Download PDF")',
                                            'a:has-text("PDF")'
                                        ]
                                        
                                        pdf_found = False
                                        for selector in pdf_selectors:
                                            pdf_link = page.locator(selector).first
                                            if await pdf_link.count() > 0:
                                                print("   ✅ PDF DOWNLOAD AVAILABLE!")
                                                pdf_found = True
                                                
                                                # Try to get PDF URL
                                                href = await pdf_link.get_attribute('href')
                                                if href:
                                                    print(f"   📥 PDF URL: {href[:80]}...")
                                                break
                                        
                                        if pdf_found:
                                            print("\n🎉 SUCCESS! Complete flow works!")
                                            print("   ✅ Accessed paywalled paper")
                                            print("   ✅ Found ETH in institution list")
                                            print("   ✅ Authenticated with ETH credentials")
                                            print("   ✅ Can download PDF")
                                            return True
                                        else:
                                            print("   ⚠️ Back at paper but no PDF access")
                                            
                                            # Check if still paywalled
                                            if "Buy this article" in await page.content():
                                                print("   ❌ Paper still paywalled after login")
                                            else:
                                                print("   ℹ️ May have partial access")
                                    
                                    elif "ethz.ch" in current_url:
                                        print("   ⚠️ Still at ETH login - authentication may have failed")
                                        
                                        # Check for error messages
                                        error_selectors = [
                                            '.error',
                                            '.alert',
                                            '[role="alert"]',
                                            '*:has-text("incorrect")',
                                            '*:has-text("failed")'
                                        ]
                                        
                                        for selector in error_selectors:
                                            error = page.locator(selector).first
                                            if await error.count() > 0:
                                                error_text = await error.text_content()
                                                print(f"   ❌ Error: {error_text}")
                                                break
                                else:
                                    print("   ❌ No submit button found")
                            else:
                                print("   ❌ No password field found")
                        else:
                            print("   ❌ No username field found")
                    else:
                        print("   ❌ Did not reach ETH login page")
                        print(f"   Current URL: {current_url}")
                else:
                    print("   ❌ No search input found on WAYF page")
            else:
                print(f"   ❌ Not at WAYF page: {current_url}")
            
            # Keep browser open to see final state
            print("\n⏸️ Keeping browser open for 30 seconds to inspect...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"\n❌ Error during test: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()
    
    return False


async def main():
    """Main test runner"""
    print("🚀 TESTING WITH REAL ETH CREDENTIALS")
    print("=" * 60)
    
    # Check network
    import requests
    try:
        response = requests.get('https://api.ipify.org', timeout=10)
        ip = response.text
        print(f"📍 Current IP: {ip}")
        
        eth_ranges = ['129.132.', '192.33.118.', '192.33.119.']
        if any(ip.startswith(prefix) for prefix in eth_ranges):
            print("✅ On ETH network")
        else:
            print("ℹ️ Not on ETH network - testing remote access")
    except:
        pass
    
    # Run test
    success = await test_complete_flow_with_credentials()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ COMPLETE FLOW VERIFIED WITH REAL CREDENTIALS!")
        print("The system can:")
        print("• Access paywalled papers")
        print("• Navigate institutional login")
        print("• Authenticate with ETH")
        print("• Download PDFs")
    else:
        print("❌ Complete flow did not succeed")
        print("Check the browser window for details")


if __name__ == "__main__":
    asyncio.run(main())