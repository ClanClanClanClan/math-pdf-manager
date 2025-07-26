#!/usr/bin/env python3
"""
SIAM Login Test
===============

Test SIAM institutional login flow.
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


def test_siam_login():
    """Test SIAM institutional login."""
    print("🔐 Testing SIAM Institutional Login")
    print("=" * 50)
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return
    
    print(f"✅ ETH credentials loaded for: {username}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=1000,
            args=['--start-maximized']
        )
        
        page = browser.new_page()
        
        # Try different login URLs
        login_urls = [
            "https://epubs.siam.org/action/showLogin",
            "https://epubs.siam.org/action/ssostart",
            "https://www.siam.org/membership/individual/individual-membership-application"
        ]
        
        for url in login_urls:
            print(f"\n🔗 Trying: {url}")
            
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(5000)
                
                current_url = page.url
                page_title = page.title()
                
                print(f"📍 Current URL: {current_url}")
                print(f"📋 Page title: {page_title[:80]}...")
                
                # Check for Cloudflare
                page_text = page.content()
                if "cloudflare" in page_text.lower():
                    print("🔒 Cloudflare challenge - waiting...")
                    page.wait_for_timeout(10000)
                    page_text = page.content()
                
                # Look for institutional login
                inst_selectors = [
                    'a:has-text("institutional")',
                    'button:has-text("institutional")',
                    'a:has-text("Shibboleth")',
                    'a:has-text("Athens")',
                    'a:has-text("access through your institution")',
                    'a[href*="shibboleth"]',
                    'a[href*="institutional"]',
                    'select[name*="institution"]',
                    'input[placeholder*="institution"]'
                ]
                
                found_institutional = False
                for selector in inst_selectors:
                    try:
                        elem = page.wait_for_selector(selector, timeout=3000)
                        if elem and elem.is_visible():
                            print(f"✅ Found institutional option: {selector}")
                            found_institutional = True
                            
                            # Try to interact with it
                            if elem.tag_name == 'select':
                                print("📋 It's a dropdown - looking for ETH...")
                                elem.select_option(label="ETH Zurich")
                            elif elem.tag_name == 'input':
                                print("📋 It's a search box - typing ETH...")
                                elem.fill("ETH Zurich")
                            else:
                                print("📋 Clicking institutional login...")
                                elem.click()
                            
                            page.wait_for_timeout(5000)
                            break
                    except Exception as e:
                        continue
                
                if found_institutional:
                    print("🏛️ Proceeding with institutional login...")
                    
                    # Take screenshot
                    screenshot_path = f"siam_login_{url.split('/')[-1]}.png"
                    page.screenshot(path=screenshot_path)
                    print(f"📸 Screenshot: {screenshot_path}")
                    
                    # Check if we reached ETH
                    if "ethz.ch" in page.url:
                        print("🎉 Reached ETH login!")
                        # Could proceed with login here
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Also try accessing a paper after any successful login attempt
        print("\n📄 Testing paper access after login attempts...")
        paper_url = "https://epubs.siam.org/doi/pdf/10.1137/20M1339829"
        
        try:
            page.goto(paper_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(5000)
            
            if page.url.endswith('.pdf'):
                print("✅ PDF accessible after login!")
            else:
                print(f"📍 Redirected to: {page.url}")
                
        except Exception as e:
            print(f"❌ Error accessing paper: {e}")
        
        print("\n⏳ Browser stays open for 45 seconds...")
        page.wait_for_timeout(45000)
        browser.close()


def main():
    """Run SIAM login test."""
    print("SIAM Login Test")
    print("===============")
    print("Testing SIAM institutional login options\n")
    
    test_siam_login()
    
    print("\n" + "="*60)
    print("SIAM Login Test Complete")


if __name__ == "__main__":
    main()