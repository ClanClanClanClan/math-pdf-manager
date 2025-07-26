#!/usr/bin/env python3
"""
SIAM Focused Solution
====================

Direct approach targeting the exact institutional login flow.
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


def siam_focused_approach():
    """Focused approach using direct SSO URL."""
    print("🎯 SIAM Focused Solution")
    print("=" * 60)
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"✅ ETH credentials ready for: {username}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=1000,
                args=['--start-maximized']
            )
            
            page = browser.new_page()
            
            # APPROACH 1: Direct SSO URL
            print("\n📍 APPROACH 1: Direct SSO URL")
            print("Going directly to: https://epubs.siam.org/action/ssostart")
            
            page.goto("https://epubs.siam.org/action/ssostart", wait_until='domcontentloaded')
            page.wait_for_timeout(10000)  # Give Cloudflare time
            
            # Check where we are
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            # If Cloudflare, wait for manual solve
            if "cloudflare" in page.content().lower():
                print("\n⚠️  CLOUDFLARE DETECTED")
                print("Please solve the Cloudflare challenge manually")
                print("Press Enter when done...")
                input()
            
            # Now check if we're on the institution search page
            if "shibboleth" in page.url or "discovery" in page.url or "wayf" in page.url:
                print("✅ Reached institution search!")
                
                # Look for search field
                search_input = page.wait_for_selector(
                    '#shibboleth_search, input[type="search"], input[placeholder*="institution"]',
                    timeout=10000
                )
                
                if search_input:
                    print("✅ Found search field")
                    search_input.click()
                    search_input.fill("ETH Zurich")
                    page.wait_for_timeout(3000)
                    
                    # Look for ETH in results
                    eth_option = page.wait_for_selector(
                        'li:has-text("ETH Zurich"), div:has-text("ETH Zurich")',
                        timeout=5000
                    )
                    if eth_option:
                        eth_option.click()
                        print("✅ Selected ETH Zurich")
            
            # APPROACH 2: Try from a paper page but look in header
            if not "ethz.ch" in page.url:
                print("\n📍 APPROACH 2: Paper page header check")
                
                paper_url = "https://epubs.siam.org/doi/10.1137/20M1339829"
                page.goto(paper_url, wait_until='domcontentloaded')
                page.wait_for_timeout(10000)
                
                # Look specifically in header/top area
                print("🔍 Checking header area for institutional button...")
                
                # Try to find the loginBar
                login_bar = page.wait_for_selector('.loginBar, .user-login-bar', timeout=5000)
                if login_bar:
                    print("✅ Found login bar")
                    
                    # Look for institutional button within it
                    inst_button = login_bar.query_selector('a.institutional__btn, a[href*="ssostart"]')
                    if inst_button:
                        print("✅ Found institutional button in login bar")
                        inst_button.click()
                        page.wait_for_timeout(5000)
                
                # Also check header
                header = page.query_selector('header, .header, #header')
                if header:
                    inst_in_header = header.query_selector('a:has-text("Institution"), a[href*="ssostart"]')
                    if inst_in_header:
                        print("✅ Found institutional in header")
                        inst_in_header.click()
                        page.wait_for_timeout(5000)
            
            # APPROACH 3: Clear cookies and try to access PDF
            if not "ethz.ch" in page.url:
                print("\n📍 APPROACH 3: Force authentication prompt")
                
                # Clear cookies
                page.context.clear_cookies()
                
                # Go directly to PDF URL
                pdf_url = "https://epubs.siam.org/doi/pdf/10.1137/20M1339829"
                page.goto(pdf_url, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)
                
                # Should be redirected to login - look for institutional
                print("🔍 Looking for institutional option after PDF access attempt...")
                
                # Check everywhere
                inst_button = page.wait_for_selector(
                    'a:has-text("Access via your Institution"), ' +
                    'a.institutional__btn, ' +
                    'a[href*="ssostart"]',
                    timeout=10000
                )
                
                if inst_button:
                    print("✅ Found institutional button after PDF attempt")
                    inst_button.click()
            
            # Final check
            page.wait_for_timeout(5000)
            if "ethz.ch" in page.url:
                print("\n🎉 SUCCESS! Reached ETH login")
                # Continue with ETH login...
                success = True
            else:
                print(f"\n❌ Could not reach ETH. Current URL: {page.url}")
                success = False
            
            # Debug info
            print("\n📋 Page Analysis:")
            print(f"URL: {page.url}")
            print(f"Title: {page.title()}")
            
            # Take screenshot
            page.screenshot(path="siam_focused_debug.png", full_page=True)
            print("📸 Screenshot: siam_focused_debug.png")
            
            print("\n⏳ Browser stays open for 60 seconds...")
            page.wait_for_timeout(60000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run focused SIAM solution."""
    print("SIAM Focused Solution")
    print("====================")
    print("Multiple approaches to find the institutional login\n")
    
    success = siam_focused_approach()
    
    print("\n" + "="*60)
    if success:
        print("✅ Successfully reached ETH login!")
    else:
        print("❌ Could not complete institutional flow")
        print("\n💡 The main issue appears to be:")
        print("   - Cloudflare protection on all SIAM pages")
        print("   - This blocks automated browser detection")
        print("\n✅ Solution: Use the semi-automated script (siam_manual_assist.py)")
        print("   which pauses for manual Cloudflare solving")


if __name__ == "__main__":
    main()