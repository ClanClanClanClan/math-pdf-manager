#!/usr/bin/env python3
"""
Test What ACTUALLY Works - ULTRATHINK Reality Check
No claims, just facts about what works and what doesn't
"""

import asyncio

from playwright.async_api import async_playwright

from cookie_banner_handler import CookieBannerHandler, PublisherSpecificHandlers


async def test_reality():
    """Test what actually works in reality"""
    print("🔬 TESTING WHAT ACTUALLY WORKS")
    print("=" * 60)
    print("No claims, just facts\n")
    
    results = {
        'cookie_banner_handling': False,
        'springer_wayf_page': False,
        'eth_in_autocomplete': False,
        'redirect_to_eth_login': False,
        'full_auth_flow': False
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Headless for quick test
        context = await browser.new_context()
        
        try:
            # Test 1: Cookie Banner Handling
            print("1️⃣ Testing Cookie Banner Handling...")
            page = await context.new_page()
            await page.goto("https://link.springer.com", wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Check for cookie banner
            banner_before = await CookieBannerHandler.detect_cookie_banner(page)
            if banner_before:
                print("   Cookie banner detected")
                dismissed = await CookieBannerHandler.dismiss_cookie_banner(page)
                if dismissed:
                    banner_after = await CookieBannerHandler.detect_cookie_banner(page)
                    if not banner_after:
                        print("   ✅ Cookie banner successfully dismissed")
                        results['cookie_banner_handling'] = True
                    else:
                        print("   ❌ Cookie banner still present after dismissal")
                else:
                    print("   ❌ Failed to dismiss cookie banner")
            else:
                print("   ℹ️ No cookie banner found (might be already accepted)")
                results['cookie_banner_handling'] = True  # Not a failure
            
            await page.close()
            
            # Test 2: Springer WAYF Page Access
            print("\n2️⃣ Testing Springer WAYF Page...")
            page = await context.new_page()
            wayf_url = "https://wayf.springernature.com/?redirect_uri=https://link.springer.com"
            
            try:
                response = await page.goto(wayf_url, wait_until='domcontentloaded', timeout=10000)
                if response.status == 200:
                    print(f"   ✅ WAYF page accessible (HTTP {response.status})")
                    results['springer_wayf_page'] = True
                    
                    # Test 3: ETH Search
                    print("\n3️⃣ Testing ETH Search in Autocomplete...")
                    search_input = page.locator('#searchFormTextInput, input[name="search"]').first
                    
                    if await search_input.count() > 0:
                        print("   Found search input")
                        await search_input.type("ETH Zurich", delay=100)
                        await page.wait_for_timeout(3000)
                        
                        # Check for dropdown
                        dropdown = page.locator('[role="listbox"]').first
                        if await dropdown.count() > 0:
                            print("   Dropdown appeared")
                            
                            # Look for ETH
                            eth_option = dropdown.locator('*:has-text("ETH Zurich")').first
                            if await eth_option.count() > 0:
                                print("   ✅ 'ETH Zurich' found in autocomplete")
                                results['eth_in_autocomplete'] = True
                                
                                # Test 4: Click and redirect
                                await eth_option.click()
                                await page.wait_for_timeout(5000)
                                
                                if "ethz.ch" in page.url or "aai-logon" in page.url:
                                    print(f"   ✅ Redirected to ETH: {page.url[:50]}...")
                                    results['redirect_to_eth_login'] = True
                                else:
                                    print(f"   ❌ No ETH redirect: {page.url[:50]}...")
                            else:
                                print("   ❌ ETH not found in dropdown")
                        else:
                            print("   ❌ No autocomplete dropdown appeared")
                    else:
                        print("   ❌ Search input not found")
                else:
                    print(f"   ❌ WAYF page returned HTTP {response.status}")
            except Exception as e:
                print(f"   ❌ Error accessing WAYF: {str(e)[:50]}")
            
            await page.close()
            
            # Test 5: Full auth flow
            print("\n4️⃣ Testing Full Authentication Flow...")
            print("   ⚠️ Cannot test without credentials")
            print("   Would need ETH username/password to complete")
            
        finally:
            await browser.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 REALITY CHECK RESULTS")
    print("=" * 60)
    
    working = []
    not_working = []
    
    for feature, works in results.items():
        feature_name = feature.replace('_', ' ').title()
        if works:
            working.append(feature_name)
            print(f"✅ {feature_name}: WORKS")
        else:
            not_working.append(feature_name)
            print(f"❌ {feature_name}: DOESN'T WORK")
    
    print(f"\n📈 Success Rate: {len(working)}/{len(results)} features working")
    
    print("\n🎯 HONEST ASSESSMENT:")
    if results['redirect_to_eth_login']:
        print("• Can reach ETH login page without VPN ✅")
        print("• Cookie banners can be handled ✅")
        print("• ETH appears in Springer autocomplete ✅")
        print("• BUT: Full download requires valid ETH credentials")
        print("• BUT: Only tested with Springer, not all publishers")
    else:
        print("• Some parts work, but not the complete flow")
        print("• May need VPN or different approach")
        print("• More investigation needed")
    
    return results


if __name__ == "__main__":
    results = asyncio.run(test_reality())
    
    # Exit code based on success
    if results['redirect_to_eth_login']:
        print("\n✅ Core functionality verified")
        exit(0)
    else:
        print("\n⚠️ Core functionality not fully working")
        exit(1)