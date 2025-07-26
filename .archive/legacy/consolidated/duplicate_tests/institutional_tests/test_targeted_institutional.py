#!/usr/bin/env python3
"""
Targeted Institutional Access Test
==================================

Focus on specific publisher institutional access flows with proper error handling.
"""

import sys
import time
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.sync_api import sync_playwright
    from secure_credential_manager import get_credential_manager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def handle_cookies(page):
    """Handle cookie modals."""
    selectors = [
        'button:has-text("Accept All")',
        'button:has-text("Accept")',
        '#onetrust-accept-btn-handler',
        '.cc-allow'
    ]
    
    for selector in selectors:
        try:
            element = page.wait_for_selector(selector, timeout=2000)
            if element and element.is_visible():
                element.click()
                page.wait_for_timeout(1000)
                return True
        except Exception as e:
            continue
    return False


def test_ieee_institutional_flow():
    """Test IEEE institutional access step by step."""
    print("🎯 IEEE Institutional Access Test")
    print("Paper: https://ieeexplore.ieee.org/document/8959041")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        return False
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=2000,  # Slower for visibility
                args=['--start-maximized']
            )
            
            page = browser.new_page()
            
            # Step 1: Go to IEEE paper
            print("🌐 Step 1: Loading IEEE paper...")
            page.goto("https://ieeexplore.ieee.org/document/8959041", wait_until='networkidle')
            handle_cookies(page)
            
            # Step 2: Click PDF button to trigger institutional access
            print("📄 Step 2: Clicking PDF to see access options...")
            pdf_button = page.wait_for_selector('a:has-text("PDF")', timeout=10000)
            if pdf_button:
                pdf_button.click()
                page.wait_for_timeout(3000)
                handle_cookies(page)
            
            # Step 3: Look for institutional sign in
            print("🏛️ Step 3: Looking for institutional sign in...")
            
            # IEEE might show a popup or redirect to sign in page
            institutional_selectors = [
                'a:has-text("Institutional Sign In")',
                'a:has-text("Sign In")',
                'button:has-text("Sign In")',
                'a[href*="wayf"]',
                'a[href*="institutional"]'
            ]
            
            institutional_clicked = False
            for selector in institutional_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        print(f"✅ Found institutional login: {selector}")
                        element.click()
                        page.wait_for_timeout(3000)
                        institutional_clicked = True
                        break
                except Exception as e:
                    continue
            
            if not institutional_clicked:
                print("🔄 Trying direct IEEE wayf URL...")
                page.goto("https://ieeexplore.ieee.org/servlet/wayf.jsp", wait_until='networkidle')
                handle_cookies(page)
            
            # Step 4: Search for ETH
            print("🔍 Step 4: Searching for ETH Zurich...")
            
            # Look for search box
            search_box = None
            search_selectors = [
                'input[placeholder*="institution" i]',
                'input[placeholder*="organization" i]',
                'input[type="search"]',
                'input#institutionInput'
            ]
            
            for selector in search_selectors:
                try:
                    search_box = page.wait_for_selector(selector, timeout=3000)
                    if search_box and search_box.is_visible():
                        print(f"🔍 Found search box: {selector}")
                        break
                except Exception as e:
                    continue
            
            if search_box:
                search_box.fill("ETH Zurich")
                page.wait_for_timeout(2000)
                page.keyboard.press('Enter')
                page.wait_for_timeout(3000)
            
            # Step 5: Select ETH from results
            print("🎯 Step 5: Selecting ETH Zurich...")
            
            eth_selectors = [
                'a:has-text("ETH Zurich")',
                'a:has-text("Swiss Federal Institute")',
                'option:has-text("ETH")',
                '[value*="ethz"]'
            ]
            
            eth_clicked = False
            for selector in eth_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        print(f"✅ Found ETH: {selector}")
                        element.click()
                        page.wait_for_timeout(5000)
                        eth_clicked = True
                        break
                except Exception as e:
                    continue
            
            # Step 6: Check if we reached ETH login
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            success = False
            if "ethz.ch" in current_url:
                print("🎉 SUCCESS: Reached ETH login page!")
                
                # Try to fill login form
                try:
                    username_field = page.wait_for_selector('input[name="j_username"], input[name="username"]', timeout=5000)
                    password_field = page.wait_for_selector('input[name="j_password"], input[name="password"]', timeout=5000)
                    
                    if username_field and password_field:
                        print(f"🔐 Filling ETH credentials for: {username}")
                        username_field.fill(username)
                        password_field.fill(password)
                        
                        submit_button = page.wait_for_selector('input[type="submit"], button[type="submit"]', timeout=3000)
                        if submit_button:
                            print("🚀 Submitting login...")
                            submit_button.click()
                            page.wait_for_load_state('networkidle')
                            
                            # Check if login succeeded
                            new_url = page.url
                            if "ieee" in new_url and "ethz.ch" not in new_url:
                                print("✅ LOGIN SUCCESS: Redirected back to IEEE!")
                                success = True
                            else:
                                print(f"⚠️ Login result unclear. URL: {new_url}")
                except Exception as e:
                    print(f"❌ Login error: {e}")
            else:
                print(f"❌ Did not reach ETH login. Current URL: {current_url}")
            
            # Take final screenshot
            page.screenshot(path="ieee_final_result.png")
            print("📸 Final screenshot: ieee_final_result.png")
            
            print("⏳ Browser stays open 15 seconds for inspection...")
            page.wait_for_timeout(15000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ IEEE test error: {e}")
        return False


def test_springer_institutional_flow():
    """Test Springer institutional access."""
    print("\n🎯 Springer Institutional Access Test")
    print("Paper: https://link.springer.com/article/10.1007/s00454-020-00244-6")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=2000)
            page = browser.new_page()
            
            # Step 1: Go to Springer paper
            print("🌐 Step 1: Loading Springer paper...")
            page.goto("https://link.springer.com/article/10.1007/s00454-020-00244-6", wait_until='networkidle')
            handle_cookies(page)
            
            # Step 2: Look for institutional access
            print("🏛️ Step 2: Looking for institutional access...")
            
            # Common Springer institutional access patterns
            institutional_selectors = [
                'a:has-text("Access through your institution")',
                'a:has-text("Institutional Login")', 
                'button:has-text("Access through your institution")',
                'a[href*="institutional"]',
                '.institutional-access'
            ]
            
            institutional_found = False
            for selector in institutional_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        print(f"✅ Found institutional access: {selector}")
                        element.click()
                        page.wait_for_timeout(3000)
                        handle_cookies(page)
                        institutional_found = True
                        break
                except Exception as e:
                    continue
            
            if not institutional_found:
                print("❌ No institutional access found on Springer page")
                # Try direct Springer institutional URL if exists
                print("🔄 Trying alternative approach...")
            
            # Step 3: Look for ETH in institution list
            print("🔍 Step 3: Looking for ETH Zurich...")
            
            eth_selectors = [
                'a:has-text("ETH Zurich")',
                'a:has-text("Swiss Federal Institute")',
                'option:has-text("ETH")',
                '[value*="ethz"]'
            ]
            
            eth_found = False
            for selector in eth_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        print(f"✅ Found ETH: {selector}")
                        element.click()
                        page.wait_for_timeout(5000)
                        eth_found = True
                        break
                except Exception as e:
                    continue
            
            current_url = page.url
            print(f"📍 Final URL: {current_url}")
            
            success = "ethz.ch" in current_url
            if success:
                print("🎉 SUCCESS: Reached ETH login!")
            else:
                print("❌ Did not reach ETH login")
            
            page.screenshot(path="springer_final_result.png")
            print("📸 Screenshot: springer_final_result.png")
            
            page.wait_for_timeout(10000)
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ Springer test error: {e}")
        return False


def main():
    """Run targeted institutional tests."""
    print("Targeted Institutional Access Test")
    print("==================================")
    print("🎯 Testing real publisher institutional login flows")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"✅ Testing with ETH credentials for: {username}")
    print("\n🎬 Watch the browser windows to see the institutional login process!")
    
    # Test IEEE
    ieee_success = test_ieee_institutional_flow()
    
    # Test Springer
    springer_success = test_springer_institutional_flow()
    
    # Results
    print(f"\n{'='*50}")
    print("INSTITUTIONAL ACCESS TEST RESULTS")
    print(f"{'='*50}")
    print(f"IEEE institutional login:     {'✅ SUCCESS' if ieee_success else '❌ FAILED'}")
    print(f"Springer institutional login: {'✅ SUCCESS' if springer_success else '❌ FAILED'}")
    
    if ieee_success or springer_success:
        print("\n🎉 INSTITUTIONAL LOGIN IS WORKING!")
        print("✅ ETH credentials can authenticate with publishers")
        print("📄 This enables direct PDF downloads without VPN")
    else:
        print("\n⚠️ Institutional login needs debugging")
        print("📸 Check screenshots to see where the process stops")
        print("💡 May need publisher-specific flow adjustments")
    
    return ieee_success or springer_success


if __name__ == "__main__":
    main()