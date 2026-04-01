#!/usr/bin/env python3
"""
Test Autocomplete Institution Search - ULTRATHINK
Properly handle autocomplete with minimum 3 characters
"""

import asyncio
import logging

from playwright.async_api import async_playwright

from cookie_banner_handler import CookieBannerHandler

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_springer_autocomplete():
    """Test Springer's autocomplete institution search"""
    print("🔍 TESTING SPRINGER AUTOCOMPLETE SEARCH")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Load WAYF page
            wayf_url = "https://wayf.springernature.com/?redirect_uri=https://link.springer.com"
            print(f"📄 Loading Springer WAYF page...")
            await page.goto(wayf_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Handle cookies
            await CookieBannerHandler.dismiss_cookie_banner(page)
            
            # Find search input
            search_input = page.locator('#searchFormTextInput').first
            if await search_input.count() == 0:
                search_input = page.locator('input[name="search"]').first
            
            if await search_input.count() > 0:
                print("✅ Found search input")
                
                # Test different search terms (minimum 3 characters)
                search_terms = [
                    "ETH Zurich",
                    "ETH ",  # With space to get 4 chars
                    "Zurich",
                    "Swiss Federal",
                    "Eidgenössische"
                ]
                
                for term in search_terms:
                    print(f"\n🔍 Searching for: '{term}'")
                    
                    # Clear and type slowly to trigger autocomplete
                    await search_input.clear()
                    await search_input.type(term, delay=100)  # Type with delay
                    await page.wait_for_timeout(2000)  # Wait for autocomplete
                    
                    # Check for autocomplete dropdown/modal
                    autocomplete_selectors = [
                        '[role="listbox"]',
                        '[data-component-autocomplete-results]',
                        '.autocomplete-results',
                        '.dropdown-menu',
                        '[aria-expanded="true"]',
                        '.modal.show',
                        'ngb-modal-window'
                    ]
                    
                    dropdown_found = False
                    for selector in autocomplete_selectors:
                        dropdown = page.locator(selector).first
                        if await dropdown.count() > 0:
                            print(f"   ✅ Autocomplete dropdown appeared: {selector}")
                            dropdown_found = True
                            
                            # Look for ETH in dropdown
                            eth_options = await dropdown.locator('*:has-text("ETH"), *:has-text("Zurich")').all()
                            
                            for option in eth_options:
                                try:
                                    text = await option.text_content()
                                    if text and len(text) < 200:
                                        print(f"   📍 Found option: '{text}'")
                                        
                                        # Try to click it
                                        await option.click()
                                        await page.wait_for_timeout(3000)
                                        
                                        # Check if redirected
                                        if "ethz.ch" in page.url or "switch.ch" in page.url:
                                            print("   🎉 SUCCESS! Redirected to ETH login")
                                            print(f"   📍 URL: {page.url}")
                                            return True
                                        elif page.url != wayf_url:
                                            print(f"   📍 Redirected to: {page.url[:80]}...")
                                except Exception as e:
                                    print(f"   ⚠️ Could not click option: {str(e)[:50]}")
                            break
                    
                    if not dropdown_found:
                        # Try submitting the form
                        print("   No dropdown found, trying form submission...")
                        await page.keyboard.press('Enter')
                        await page.wait_for_timeout(3000)
                        
                        # Check if we got results
                        if page.url != wayf_url:
                            print(f"   📍 Navigated to: {page.url[:80]}...")
                            
                            # Look for ETH on the results page
                            eth_links = await page.locator('a:has-text("ETH"), a:has-text("Zurich")').all()
                            for link in eth_links:
                                try:
                                    text = await link.text_content()
                                    if text and "ETH" in text:
                                        print(f"   ✅ Found ETH link: '{text}'")
                                        await link.click()
                                        await page.wait_for_timeout(3000)
                                        
                                        if "ethz.ch" in page.url:
                                            print("   🎉 SUCCESS! Reached ETH login")
                                            return True
                                except:
                                    continue
                            
                            # Go back for next search
                            await page.go_back()
                            await page.wait_for_timeout(2000)
            else:
                print("❌ Could not find search input")
            
            # If nothing worked, try clicking the search button
            print("\n🔍 Trying with search button click...")
            search_button = page.locator('button[type="submit"]').first
            if await search_button.count() > 0:
                await search_input.fill("ETH Zurich")
                await search_button.click()
                await page.wait_for_timeout(3000)
                
                print(f"   📍 After search: {page.url[:80]}...")
            
        finally:
            print("\n⏸️ Keeping browser open for inspection...")
            await page.wait_for_timeout(20000)
            await browser.close()


async def test_direct_eth_url():
    """Test if ETH has a direct Shibboleth URL"""
    print("\n🔍 TESTING DIRECT ETH SHIBBOLETH URL")
    print("=" * 60)
    
    # Common ETH Shibboleth URLs
    eth_urls = [
        "https://aai-logon.ethz.ch/idp/profile/SAML2/Redirect/SSO",
        "https://login.ethz.ch/",
        "https://www.library.ethz.ch/en/",
        "https://eth.swisscovery.slsp.ch/"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        for url in eth_urls:
            page = await context.new_page()
            try:
                print(f"\n📍 Testing: {url}")
                response = await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                
                if response.status == 200:
                    print(f"   ✅ Accessible (HTTP {response.status})")
                    
                    # Check for login form
                    if "login" in page.url.lower() or "idp" in page.url.lower():
                        print("   🔑 Login page detected")
                        
                        # Look for username field
                        username_field = page.locator('input[type="text"], input[name*="user"], input[id*="user"]').first
                        if await username_field.count() > 0:
                            print("   ✅ Username field found - ETH login page confirmed!")
                else:
                    print(f"   ❌ HTTP {response.status}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}")
            finally:
                await page.close()
        
        await browser.close()


async def main():
    """Test autocomplete institution search"""
    print("🚀 TESTING AUTOCOMPLETE INSTITUTION SEARCH")
    print("=" * 60)
    print("Handling minimum 3 character requirement")
    print()
    
    # Test Springer autocomplete
    springer_found = await test_springer_autocomplete()
    
    # Test direct ETH URLs
    await test_direct_eth_url()
    
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    if springer_found:
        print("✅ Successfully found ETH in Springer autocomplete!")
    else:
        print("⚠️ Could not find ETH via autocomplete")
        print("\n🎯 MANUAL STEPS TO TRY:")
        print("1. Go to: https://wayf.springernature.com/")
        print("2. Type 'ETH Zurich' in search box")
        print("3. Wait for autocomplete dropdown")
        print("4. Click on 'ETH Zurich' if it appears")
        print("5. Or try 'Swiss Federal Institute'")


if __name__ == "__main__":
    asyncio.run(main())