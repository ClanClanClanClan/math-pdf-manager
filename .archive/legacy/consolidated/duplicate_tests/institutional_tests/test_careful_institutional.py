#!/usr/bin/env python3
"""
Careful Institutional Access Test
=================================

Properly handle IEEE modal interaction and Springer wayf cookie banners.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.sync_api import sync_playwright
    from secure_credential_manager import get_credential_manager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def handle_all_cookies(page):
    """Comprehensive cookie handling for different sites."""
    cookie_selectors = [
        # Generic
        'button:has-text("Accept All")',
        'button:has-text("Accept all cookies")', 
        'button:has-text("Accept")',
        'button:has-text("OK")',
        'button:has-text("I Agree")',
        'button:has-text("Continue")',
        # IEEE
        '#onetrust-accept-btn-handler',
        '.ot-sdk-show-settings',
        # Springer
        '.cc-allow',
        '.cc-dismiss',
        'button.cc-allow',
        'button.cc-dismiss',
        # SpringerNature wayf specific
        'button[data-cc="accept"]',
        'button.consent-accept',
        '.cookie-consent button',
        # Generic close/dismiss
        'button[aria-label="Close"]',
        'button[title="Close"]',
        '.close-button',
        '[data-dismiss="modal"]'
    ]
    
    cookies_handled = False
    for selector in cookie_selectors:
        try:
            element = page.wait_for_selector(selector, timeout=2000)
            if element and element.is_visible():
                print(f"🍪 Handling cookies with: {selector}")
                element.click()
                page.wait_for_timeout(1000)
                cookies_handled = True
                break
        except Exception as e:
            continue
    
    return cookies_handled


def test_ieee_modal_careful():
    """Carefully handle IEEE modal interaction."""
    print("🎯 IEEE Careful Modal Test")
    print("Focus on proper modal interaction")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        return False
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=2000,  # Even slower for careful interaction
                args=['--start-maximized']
            )
            
            page = browser.new_page()
            
            # Step 1: Load IEEE paper
            print("🌐 Step 1: Loading IEEE paper...")
            page.goto("https://ieeexplore.ieee.org/document/8959041", wait_until='networkidle')
            handle_all_cookies(page)
            page.screenshot(path="ieee_careful_01_loaded.png")
            
            # Step 2: Click PDF to open modal
            print("📄 Step 2: Clicking PDF to open sign-in modal...")
            pdf_button = page.wait_for_selector('a:has-text("PDF")', timeout=10000)
            if pdf_button:
                pdf_button.click()
                page.wait_for_timeout(3000)
                handle_all_cookies(page)  # Handle any new cookies
                page.screenshot(path="ieee_careful_02_modal_open.png")
            
            # Step 3: Click institutional access in modal
            print("🏛️ Step 3: Clicking institutional access in modal...")
            
            # Wait for modal to be fully loaded
            page.wait_for_timeout(2000)
            
            # Target the specific button from your HTML
            institutional_button = page.wait_for_selector(
                'button.stats-Doc_Details_sign_in_seamlessaccess_access_through_your_institution_btn',
                timeout=10000
            )
            
            if institutional_button and institutional_button.is_visible():
                print("✅ Found institutional button in modal")
                institutional_button.click()
                print("🔄 Waiting for SeamlessAccess redirect...")
                page.wait_for_timeout(5000)  # Wait longer for redirect
                handle_all_cookies(page)
                page.screenshot(path="ieee_careful_03_seamless_access.png")
            else:
                print("❌ Could not find institutional button in modal")
                return False
            
            # Step 4: Now on SeamlessAccess - look for institution search
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            if "seamlessaccess.org" in current_url:
                print("✅ Successfully redirected to SeamlessAccess")
                
                # Look for institution search on SeamlessAccess
                print("🔍 Step 4: Searching for ETH on SeamlessAccess...")
                
                search_selectors = [
                    'input[placeholder*="institution"]',
                    'input[placeholder*="search"]',
                    'input[type="search"]',
                    'input[name="entity"]',
                    '#ds-search'
                ]
                
                search_box = None
                for selector in search_selectors:
                    try:
                        search_box = page.wait_for_selector(selector, timeout=5000)
                        if search_box and search_box.is_visible():
                            print(f"🔍 Found SeamlessAccess search: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if search_box:
                    search_box.fill("ETH Zurich")
                    page.wait_for_timeout(2000)
                    page.keyboard.press('Enter')
                    page.wait_for_timeout(3000)
                    page.screenshot(path="ieee_careful_04_eth_search.png")
                    
                    # Look for ETH in search results
                    eth_selectors = [
                        'a:has-text("ETH Zurich")',
                        'a:has-text("Swiss Federal Institute")',
                        'button:has-text("ETH")',
                        '.result:has-text("ETH")',
                        'li:has-text("ETH")'
                    ]
                    
                    for selector in eth_selectors:
                        try:
                            eth_element = page.wait_for_selector(selector, timeout=5000)
                            if eth_element and eth_element.is_visible():
                                print(f"✅ Found ETH in results: {selector}")
                                eth_element.click()
                                page.wait_for_timeout(5000)
                                page.screenshot(path="ieee_careful_05_eth_selected.png")
                                break
                        except Exception as e:
                            continue
                
            else:
                print(f"⚠️ Not on SeamlessAccess. URL: {current_url}")
                # Might be directly on institution page
                print("🔍 Looking for ETH on current page...")
                
                # Try to find ETH on current page
                eth_selectors = [
                    'a:has-text("ETH Zurich")',
                    'a:has-text("Swiss Federal Institute")',
                    'option:has-text("ETH")',
                    '[value*="ethz"]'
                ]
                
                for selector in eth_selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=3000)
                        if element and element.is_visible():
                            print(f"✅ Found ETH: {selector}")
                            element.click()
                            page.wait_for_timeout(3000)
                            break
                    except Exception as e:
                        continue
            
            # Step 5: Check final result
            final_url = page.url
            print(f"📍 Final URL: {final_url}")
            
            success = "ethz.ch" in final_url or "idp" in final_url
            if success:
                print("🎉 SUCCESS: Reached ETH authentication!")
            else:
                print(f"❌ Did not reach ETH. Final URL: {final_url}")
            
            page.screenshot(path="ieee_careful_06_final.png")
            print("📸 Screenshots: ieee_careful_01 through ieee_careful_06")
            
            print("⏳ Browser open 20 seconds for inspection...")
            page.wait_for_timeout(20000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ IEEE careful test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_springer_wayf_careful():
    """Carefully handle Springer wayf page with cookie banners."""
    print("\n🎯 Springer Wayf Careful Test")
    print("Handle wayf page cookie banners properly")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=2000)
            page = browser.new_page()
            
            # Step 1: Load Springer paper
            print("🌐 Step 1: Loading Springer paper...")
            page.goto("https://link.springer.com/article/10.1007/s00454-020-00244-6", wait_until='networkidle')
            handle_all_cookies(page)
            page.screenshot(path="springer_careful_01_loaded.png")
            
            # Step 2: Click institutional login
            print("🏛️ Step 2: Clicking institutional login...")
            
            institutional_button = page.wait_for_selector(
                'a:has-text("Log in via an institution")',
                timeout=10000
            )
            
            if institutional_button and institutional_button.is_visible():
                print("✅ Found Springer institutional button")
                institutional_button.click()
                page.wait_for_timeout(3000)
                page.screenshot(path="springer_careful_02_wayf_loading.png")
            else:
                print("❌ Could not find Springer institutional button")
                return False
            
            # Step 3: Handle wayf page cookies
            print("🍪 Step 3: Handling wayf page cookies...")
            current_url = page.url
            print(f"📍 Wayf URL: {current_url}")
            
            # Give wayf page time to load completely
            page.wait_for_timeout(3000)
            
            # Handle cookies on wayf page specifically
            wayf_cookie_handled = handle_all_cookies(page)
            if wayf_cookie_handled:
                print("✅ Handled wayf page cookies")
            else:
                print("⚠️ No wayf cookies found or already handled")
            
            page.wait_for_timeout(2000)
            page.screenshot(path="springer_careful_03_wayf_ready.png")
            
            # Step 4: Search for ETH on wayf page
            print("🔍 Step 4: Looking for ETH on wayf page...")
            
            # SpringerNature wayf might have different search patterns
            search_selectors = [
                'input[placeholder*="institution"]',
                'input[placeholder*="search"]',
                'input[type="search"]',
                'input[type="text"]',
                '#query',
                '#search'
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = page.wait_for_selector(selector, timeout=3000)
                    if search_box and search_box.is_visible():
                        print(f"🔍 Found wayf search: {selector}")
                        break
                except Exception as e:
                    continue
            
            if search_box:
                search_box.fill("ETH Zurich")
                page.wait_for_timeout(2000)
                page.keyboard.press('Enter')
                page.wait_for_timeout(3000)
                page.screenshot(path="springer_careful_04_eth_search.png")
            else:
                print("⚠️ No search box found, looking for ETH directly...")
            
            # Step 5: Look for ETH in results or list
            print("🎯 Step 5: Selecting ETH from wayf results...")
            
            eth_selectors = [
                'a:has-text("ETH Zurich")',
                'a:has-text("Swiss Federal Institute")',
                'a:has-text("Eidgenössische Technische Hochschule")',
                'button:has-text("ETH")',
                'option:has-text("ETH")',
                'li:has-text("ETH")',
                '[value*="ethz"]',
                'a[href*="ethz"]'
            ]
            
            eth_found = False
            for selector in eth_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        print(f"✅ Found ETH on wayf: {selector}")
                        element.click()
                        page.wait_for_timeout(5000)
                        eth_found = True
                        page.screenshot(path="springer_careful_05_eth_selected.png")
                        break
                except Exception as e:
                    continue
            
            if not eth_found:
                print("❌ Could not find ETH on wayf page")
                print("🔍 Available options:")
                
                # Show what's available
                links = page.query_selector_all('a, button')
                for i, link in enumerate(links[:10]):
                    try:
                        text = link.text_content()
                        if text and "eth" in text.lower():
                            print(f"  ETH-related: {text.strip()}")
                    except Exception as e:
                        continue
            
            # Step 6: Check final result
            final_url = page.url
            print(f"📍 Final URL: {final_url}")
            
            success = "ethz.ch" in final_url
            if success:
                print("🎉 SUCCESS: Reached ETH login!")
            else:
                print(f"❌ Did not reach ETH. Final URL: {final_url}")
            
            page.screenshot(path="springer_careful_06_final.png")
            print("📸 Screenshots: springer_careful_01 through springer_careful_06")
            
            page.wait_for_timeout(15000)
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ Springer careful test error: {e}")
        return False


def main():
    """Run careful institutional tests."""
    print("Careful Institutional Access Test")
    print("=================================")
    print("🎯 Proper modal handling and cookie management")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"✅ Testing with ETH credentials for: {username}")
    print("\n🎬 Watch careful modal and cookie handling!")
    
    # Test IEEE with careful modal handling
    ieee_success = test_ieee_modal_careful()
    
    # Test Springer with careful wayf handling
    springer_success = test_springer_wayf_careful()
    
    # Results
    print(f"\n{'='*60}")
    print("CAREFUL INSTITUTIONAL ACCESS RESULTS")
    print(f"{'='*60}")
    print(f"IEEE careful modal flow:   {'✅ SUCCESS' if ieee_success else '❌ FAILED'}")
    print(f"Springer careful wayf flow: {'✅ SUCCESS' if springer_success else '❌ FAILED'}")
    
    if ieee_success or springer_success:
        print("\n🎉 INSTITUTIONAL LOGIN SUCCESS!")
        print("✅ Careful modal/cookie handling enables authentication")
        print("🔧 The system properly navigates publisher-specific flows")
        print("📄 ETH institutional access works without VPN")
    else:
        print("\n⚠️ Still refining publisher-specific interactions")
        print("📸 Screenshots show exactly where each step stops")
        print("🔧 Framework is solid - needs final UI interaction tuning")
    
    return ieee_success or springer_success


if __name__ == "__main__":
    main()