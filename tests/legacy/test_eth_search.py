#!/usr/bin/env python3
"""
Test ETH Search in Institution Lists - ULTRATHINK
Different publishers use different names for ETH
"""

import asyncio
import logging

from playwright.async_api import async_playwright

from cookie_banner_handler import CookieBannerHandler, PublisherSpecificHandlers

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Various ways ETH might appear
ETH_SEARCH_TERMS = [
    "ETH Zurich",
    "ETH Zürich", 
    "Swiss Federal Institute of Technology Zurich",
    "Eidgenössische Technische Hochschule Zürich",
    "ETHZ",
    "ETH",
    "Zurich",
    "Zürich",
    "Switzerland"
]

ETH_IDENTIFIERS = [
    "ETH Zurich",
    "ETH Zürich",
    "Swiss Federal Institute",
    "Eidgenössische",
    "ETHZ",
    "ETH-Bibliothek",
    "library.ethz.ch",
    "ethz.ch"
]


async def test_springer_eth_search():
    """Test finding ETH in Springer's institution list"""
    print("\n🔍 TESTING ETH SEARCH IN SPRINGER")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Go directly to WAYF page
            wayf_url = "https://wayf.springernature.com/?redirect_uri=https://link.springer.com"
            print(f"📄 Loading Springer WAYF page...")
            await page.goto(wayf_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Handle cookies
            await CookieBannerHandler.dismiss_cookie_banner(page)
            
            print("🔍 Testing different search terms for ETH...")
            
            for search_term in ETH_SEARCH_TERMS:
                print(f"\n   Trying: '{search_term}'")
                
                # Find search box
                search_input = page.locator('input[type="search"], input[type="text"]').first
                if await search_input.count() > 0:
                    # Clear and search
                    await search_input.clear()
                    await search_input.fill(search_term)
                    await page.wait_for_timeout(1500)  # Wait for autocomplete
                    
                    # Check results
                    results_found = False
                    for identifier in ETH_IDENTIFIERS:
                        result = page.locator(f'*:has-text("{identifier}")').first
                        if await result.count() > 0:
                            text = await result.text_content()
                            # Filter out the search box itself
                            if text and identifier in text and len(text) < 200:
                                print(f"      ✅ Found: '{text[:100]}'")
                                results_found = True
                                
                                # Check if it's clickable
                                if await result.evaluate('el => el.tagName') in ['A', 'BUTTON', 'LI']:
                                    print(f"      🎯 This looks clickable!")
                                    
                                    # Try clicking
                                    try:
                                        await result.click()
                                        await page.wait_for_timeout(3000)
                                        
                                        # Check if redirected to ETH
                                        if "ethz.ch" in page.url or "switch.ch" in page.url:
                                            print(f"      🎉 SUCCESS! Redirected to ETH login")
                                            print(f"      📍 URL: {page.url}")
                                            return True
                                        else:
                                            print(f"      📍 Redirected to: {page.url[:80]}...")
                                            # Go back for next attempt
                                            await page.go_back()
                                            await page.wait_for_timeout(2000)
                                    except Exception as e:
                                        print(f"      ⚠️ Click failed: {str(e)[:50]}")
                                break
                    
                    if not results_found:
                        print(f"      ❌ No results for '{search_term}'")
            
            # If nothing worked, list all available institutions
            print("\n📋 Listing available institutions...")
            await page.goto(wayf_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Try to find institution list
            inst_links = await page.locator('a[href*="entityID"], a[href*="idp"], li[class*="institution"]').all()
            print(f"   Found {len(inst_links)} institution links")
            
            swiss_institutions = []
            for link in inst_links[:100]:  # Check first 100
                try:
                    text = await link.text_content()
                    if text and any(term in text for term in ["Swiss", "Switzerland", "ETH", "Zurich", "Zürich"]):
                        swiss_institutions.append(text)
                except:
                    continue
            
            if swiss_institutions:
                print("\n   🇨🇭 Swiss institutions found:")
                for inst in swiss_institutions[:10]:
                    print(f"      • {inst}")
            
        finally:
            await browser.close()
    
    return False


async def test_ieee_eth_search():
    """Test finding ETH in IEEE's institution list"""
    print("\n🔍 TESTING ETH SEARCH IN IEEE")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Load IEEE paper
            ieee_url = "https://ieeexplore.ieee.org/document/10534571"
            print(f"📄 Loading IEEE paper...")
            await page.goto(ieee_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Handle cookies
            await PublisherSpecificHandlers.handle_ieee_cookies(page)
            
            # Click institutional sign in
            inst_signin = page.locator('a:has-text("Institutional Sign In")').first
            if await inst_signin.count() > 0:
                print("🏛️ Clicking Institutional Sign In...")
                await inst_signin.click()
                await page.wait_for_timeout(3000)
                
                # Look for modal
                modal = page.locator('ngb-modal-window, .modal, [role="dialog"]').first
                if await modal.count() > 0:
                    print("✅ Modal opened")
                    
                    # Search in modal
                    search_input = modal.locator('input[type="search"], input[type="text"], input[placeholder*="institution"]').first
                    if await search_input.count() > 0:
                        print("🔍 Testing ETH search terms...")
                        
                        for search_term in ["ETH", "Zurich", "Swiss Federal"]:
                            print(f"   Trying: '{search_term}'")
                            await search_input.clear()
                            await search_input.fill(search_term)
                            await page.wait_for_timeout(2000)
                            
                            # Look for results in modal
                            eth_result = modal.locator('*:has-text("ETH"), *:has-text("Zurich")').first
                            if await eth_result.count() > 0:
                                text = await eth_result.text_content()
                                if len(text) < 200:  # Not a large block
                                    print(f"      ✅ Found: '{text}'")
                                    
                                    # Try to click
                                    try:
                                        await eth_result.click()
                                        await page.wait_for_timeout(3000)
                                        
                                        if "ethz.ch" in page.url:
                                            print("      🎉 SUCCESS! Redirected to ETH")
                                            return True
                                    except:
                                        pass
            
        finally:
            await browser.close()
    
    return False


async def main():
    """Test ETH search across publishers"""
    print("🚀 TESTING ETH INSTITUTION SEARCH")
    print("=" * 60)
    print("Finding the right search terms for ETH across publishers")
    print()
    
    results = {}
    
    # Test Springer
    print("Testing Springer institution search:")
    results['Springer'] = await test_springer_eth_search()
    
    # Test IEEE  
    print("\nTesting IEEE institution search:")
    results['IEEE'] = await test_ieee_eth_search()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SEARCH RESULTS")
    print("=" * 60)
    
    for publisher, found in results.items():
        if found:
            print(f"✅ {publisher}: ETH found and accessible")
        else:
            print(f"❌ {publisher}: Could not find/access ETH")
    
    print("\n🎯 RECOMMENDATIONS:")
    print("1. Try variations: 'ETH', 'Zurich', 'Swiss Federal'")
    print("2. Some publishers might list ETH under Switzerland")
    print("3. Look for 'ETHZ' or 'ETH-Bibliothek' as alternatives")
    print("4. Check if alphabetical browsing is available")


if __name__ == "__main__":
    asyncio.run(main())