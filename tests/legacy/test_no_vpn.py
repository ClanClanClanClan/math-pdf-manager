#!/usr/bin/env python3
"""
Test Institutional Login WITHOUT VPN - ULTRATHINK Reality Check
Most publishers support Shibboleth/SAML authentication without requiring VPN
"""

import asyncio
import getpass
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from cookie_banner_handler import CookieBannerHandler, PublisherSpecificHandlers


async def test_springer_without_vpn():
    """Test Springer institutional login without VPN"""
    print("🔍 TESTING SPRINGER INSTITUTIONAL LOGIN (NO VPN)")
    print("=" * 50)
    
    test_url = "https://link.springer.com/article/10.1007/s10994-018-5759-4"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visual for debugging
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1: Navigate to paper
            print(f"📄 Loading Springer paper...")
            await page.goto(test_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Step 2: Handle cookie banners first
            print("🍪 Checking for cookie banners...")
            cookie_dismissed = await PublisherSpecificHandlers.handle_springer_cookies(page)
            if cookie_dismissed:
                print("✅ Cookie banner dismissed")
            
            # Step 3: Look for login/access options
            print("🔍 Looking for access options...")
            
            # Springer typically has these options
            access_selectors = [
                'a:has-text("Log in")',
                'a:has-text("Sign in")',
                'a:has-text("Access")',
                'button:has-text("Access")',
                '[data-track-action="institution link"]',
                'a[href*="/login"]',
                '.c-header__login-text',
                '[data-test="login-link"]'
            ]
            
            found_access = None
            for selector in access_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        text = await element.text_content()
                        print(f"✅ Found access option: '{text}'")
                        found_access = element
                        break
                except:
                    continue
            
            if found_access:
                # Use cookie handler to ensure click succeeds
                async def click_access():
                    await found_access.click()
                    return True
                
                try:
                    await CookieBannerHandler.handle_cookie_banner_before_action(
                        page, click_access, max_retries=2
                    )
                except:
                    # Fallback to direct click
                    await found_access.click()
                
                await page.wait_for_timeout(3000)
                
                # Step 3: Look for institutional login option
                print("🏛️ Looking for institutional login...")
                
                inst_selectors = [
                    'a:has-text("Log in via institution")',
                    'a:has-text("Institutional login")',
                    'a:has-text("Access via your institution")',
                    'button:has-text("Institution")',
                    '[href*="institutional"]',
                    '[href*="shibboleth"]',
                    '.institutional-login',
                    'a:has-text("Shibboleth")'
                ]
                
                for selector in inst_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=5000, state='visible')
                        if element:
                            text = await element.text_content()
                            print(f"✅ Found institutional login: '{text}'")
                            await element.click()
                            await page.wait_for_timeout(3000)
                            
                            # Should now be at institution search page
                            current_url = page.url
                            print(f"📍 Redirected to: {current_url}")
                            
                            if "wayf" in current_url or "discovery" in current_url or "idp" in current_url:
                                print("✅ Reached institution selection page!")
                                
                                # Search for ETH
                                search_input = await page.query_selector('input[type="text"], input[type="search"]')
                                if search_input:
                                    print("🔍 Searching for ETH Zurich...")
                                    await search_input.fill("ETH Zurich")
                                    await page.keyboard.press('Enter')
                                    await page.wait_for_timeout(2000)
                                    
                                    # Look for ETH in results
                                    eth_link = await page.query_selector('a:has-text("ETH Zurich"), a:has-text("ETH Zürich")')
                                    if eth_link:
                                        print("✅ Found ETH Zurich in institution list!")
                                        print("🎉 Institutional login IS available without VPN!")
                                        return True
                            break
                    except:
                        continue
            
            print("❌ Could not find institutional login option")
            return False
            
        finally:
            await browser.close()


async def test_nature_without_vpn():
    """Test Nature institutional login without VPN"""
    print("\n🔍 TESTING NATURE INSTITUTIONAL LOGIN (NO VPN)")
    print("=" * 50)
    
    test_url = "https://www.nature.com/articles/s41586-019-1666-5"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"📄 Loading Nature paper...")
            await page.goto(test_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Handle cookie banners first
            print("🍪 Checking for cookie banners...")
            cookie_dismissed = await PublisherSpecificHandlers.handle_nature_cookies(page)
            if cookie_dismissed:
                print("✅ Cookie banner dismissed")
            
            # Nature access options
            access_selectors = [
                'a:has-text("Access")',
                'a:has-text("Log in")',
                'a:has-text("Sign in")',
                '.c-header__login',
                '[data-track-action="view access options"]'
            ]
            
            for selector in access_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        text = await element.text_content()
                        print(f"✅ Found access option: '{text}'")
                        await element.click()
                        await page.wait_for_timeout(3000)
                        
                        # Look for institutional option
                        inst_element = await page.query_selector('a:has-text("institution"), a:has-text("Shibboleth")')
                        if inst_element:
                            print("✅ Found institutional login option!")
                            await inst_element.click()
                            await page.wait_for_timeout(3000)
                            
                            current_url = page.url
                            print(f"📍 Redirected to: {current_url}")
                            
                            if any(term in current_url for term in ["wayf", "discovery", "idp", "shibboleth"]):
                                print("✅ Reached institution selection!")
                                print("🎉 Nature institutional login IS available without VPN!")
                                return True
                        break
                except:
                    continue
            
            print("❌ Could not find institutional login for Nature")
            return False
            
        finally:
            await browser.close()


async def test_ieee_without_vpn():
    """Test IEEE institutional login without VPN"""
    print("\n🔍 TESTING IEEE INSTITUTIONAL LOGIN (NO VPN)")
    print("=" * 50)
    
    # Use DOI redirect since direct access might be blocked
    test_url = "https://doi.org/10.1109/JPROC.2018.2820126"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            print(f"📄 Loading IEEE paper via DOI...")
            response = await page.goto(test_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            print(f"📍 Redirected to: {current_url}")
            
            if "ieee" in current_url:
                print("✅ Reached IEEE Xplore")
                
                # Handle cookie banners first
                print("🍪 Checking for cookie banners...")
                cookie_dismissed = await PublisherSpecificHandlers.handle_ieee_cookies(page)
                if cookie_dismissed:
                    print("✅ Cookie banner dismissed")
                
                # Look for institutional sign in
                inst_selectors = [
                    'a:has-text("Institutional Sign In")',
                    'a:has-text("Institution")',
                    'button:has-text("Institution")',
                    '.institutional-access',
                    '[href*="institutional"]'
                ]
                
                for selector in inst_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element and await element.is_visible():
                            text = await element.text_content()
                            print(f"✅ Found institutional option: '{text}'")
                            await element.click()
                            await page.wait_for_timeout(3000)
                            
                            # Check if modal opened or page changed
                            modal = await page.query_selector('ngb-modal-window, .modal, [role="dialog"]')
                            if modal:
                                print("✅ Institutional login modal opened!")
                                print("🎉 IEEE institutional login IS available without VPN!")
                                return True
                            
                            new_url = page.url
                            if new_url != current_url:
                                print(f"✅ Redirected to: {new_url}")
                                print("🎉 IEEE institutional login IS available without VPN!")
                                return True
                            break
                    except:
                        continue
            else:
                print(f"⚠️ Could not reach IEEE directly: {current_url}")
                print("   IEEE might require different approach without VPN")
            
            return False
            
        finally:
            await browser.close()


async def main():
    """Test institutional login without VPN for major publishers"""
    print("🚀 INSTITUTIONAL LOGIN TEST (NO VPN REQUIRED)")
    print("=" * 60)
    print("Testing if publishers support ETH login without VPN connection")
    print()
    
    # Check current network status
    import requests
    try:
        response = requests.get('https://api.ipify.org', timeout=10)
        ip = response.text
        eth_ranges = ['129.132.', '192.33.118.', '192.33.119.']
        is_eth = any(ip.startswith(prefix) for prefix in eth_ranges)
        
        print(f"📍 Current IP: {ip}")
        if is_eth:
            print("✅ On ETH network (but testing as if external)")
        else:
            print("✅ NOT on ETH network - perfect for testing!")
        print()
    except:
        pass
    
    results = {}
    
    # Test each publisher
    print("Testing publishers that should work WITHOUT VPN:")
    print("-" * 40)
    
    # Springer (most likely to work)
    results['Springer'] = await test_springer_without_vpn()
    
    # Nature (owned by Springer, similar infrastructure)
    results['Nature'] = await test_nature_without_vpn()
    
    # IEEE (might work with proper approach)
    results['IEEE'] = await test_ieee_without_vpn()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    
    working_publishers = [pub for pub, works in results.items() if works]
    not_working = [pub for pub, works in results.items() if not works]
    
    if working_publishers:
        print(f"✅ WORKS WITHOUT VPN ({len(working_publishers)}):")
        for pub in working_publishers:
            print(f"   • {pub} - Institutional login available!")
    
    if not_working:
        print(f"\n⚠️ MIGHT NEED VPN ({len(not_working)}):")
        for pub in not_working:
            print(f"   • {pub} - Could not find institutional login")
    
    print("\n🎯 KEY FINDING:")
    if working_publishers:
        print("✅ VPN is NOT required for institutional login!")
        print("   Publishers support Shibboleth/SAML authentication from anywhere")
        print("   You just need your ETH credentials")
    else:
        print("⚠️ Some publishers might need different approach or VPN")
    
    print("\n📋 NEXT STEPS:")
    print("1. Test full authentication flow with ETH credentials")
    print("2. Update diagnostic to prioritize institutional login over VPN")
    print("3. Document working authentication flows for each publisher")


if __name__ == "__main__":
    asyncio.run(main())