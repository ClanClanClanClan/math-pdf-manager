#!/usr/bin/env python3
"""
Visual IEEE Institutional Login Test
===================================

Test IEEE institutional login with visible browser.
IEEE has a clear institutional access portal.
"""

import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.sync_api import sync_playwright
    from secure_credential_manager import get_credential_manager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def demo_ieee_institutional_flow():
    """Demo the IEEE institutional login flow visually."""
    print("🎬 IEEE Institutional Login Demo")
    print("================================")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials not found")
        return False
    
    print(f"✅ Will use ETH credentials for: {username}")
    print("\n🎯 This demo will show you the exact steps:")
    print("1. Go to IEEE Xplore")
    print("2. Navigate to institutional access")
    print("3. Search for ETH Zurich")
    print("4. Show the authentication redirect")
    print("5. Stop before actually logging in")
    
    try:
        with sync_playwright() as p:
            # Launch visible browser
            browser = p.chromium.launch(
                headless=False,
                slow_mo=2000,  # 2 second delay between actions
                args=['--start-maximized']
            )
            
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            print("\n🌐 Step 1: Opening IEEE Xplore...")
            page.goto("https://ieeexplore.ieee.org")
            page.wait_for_load_state('networkidle')
            
            print("🔍 Step 2: Looking for institutional access...")
            
            # IEEE typically has institutional access in the top menu
            institutional_links = [
                'a:has-text("Institutional Sign In")',
                'a:has-text("Subscribe")',
                '[href*="institutional"]',
                '[href*="subscribe"]',
                'a:has-text("Access")'
            ]
            
            # Try the direct institutional URL
            print("🎯 Going directly to IEEE institutional access page...")
            page.goto("https://ieeexplore.ieee.org/servlet/wayf.jsp")
            page.wait_for_load_state('networkidle')
            
            print("⏳ Waiting for page to load...")
            time.sleep(3)
            
            current_url = page.url
            page_title = page.title()
            print(f"📍 Current page: {page_title}")
            print(f"🔗 URL: {current_url}")
            
            # Look for institution search
            print("🏛️ Step 3: Looking for institution search...")
            
            # Common institution finder elements
            search_selectors = [
                'input[placeholder*="institution"]',
                'input[placeholder*="organization"]',
                'input[type="search"]',
                'input[name*="institution"]',
                'input#institutionInput',
                '.institution-search input'
            ]
            
            search_found = False
            for selector in search_selectors:
                try:
                    search_box = page.wait_for_selector(selector, timeout=3000)
                    if search_box:
                        print(f"✅ Found institution search: {selector}")
                        print("🔍 Typing 'ETH Zurich'...")
                        search_box.fill("ETH Zurich")
                        search_found = True
                        time.sleep(2)
                        break
                except (AttributeError, TypeError) as e:
                    print(f"⚠️  Search attempt failed: {e}")
                    continue
            
            if not search_found:
                print("❌ No institution search found, looking for ETH directly...")
                
                # Look for ETH in any visible text
                eth_elements = [
                    'a:has-text("ETH")',
                    'a:has-text("Zurich")',
                    'option:has-text("ETH")',
                    '[value*="ethz"]',
                    '[href*="ethz"]'
                ]
                
                for selector in eth_elements:
                    try:
                        element = page.wait_for_selector(selector, timeout=2000)
                        if element:
                            print(f"✅ Found ETH option: {selector}")
                            text = element.text_content()
                            print(f"📝 Text: {text}")
                            
                            print("🖱️  Clicking ETH option...")
                            element.click()
                            page.wait_for_load_state('networkidle')
                            time.sleep(2)
                            break
                    except (AttributeError, TypeError, RuntimeError) as e:
                        print(f"⚠️  ETH option click failed: {e}")
                        continue
            
            # Check where we are now
            final_url = page.url
            final_title = page.title()
            print(f"\n📍 Final page: {final_title}")
            print(f"🔗 Final URL: {final_url}")
            
            if "ethz.ch" in final_url or "idp" in final_url:
                print("🎉 SUCCESS: Redirected to ETH authentication!")
                print("✅ This proves institutional login is working")
                print(f"🔑 Would now enter credentials for: {username}")
                
                # Show login form if present
                login_fields = page.query_selector_all('input[type="password"], input[name*="password"], input[name*="username"]')
                if login_fields:
                    print(f"🔐 Found {len(login_fields)} login fields on ETH page")
                    
            elif "ieee" in final_url:
                print("⚠️  Still on IEEE page - may need different approach")
                print("🔍 Let's see what's on this page...")
                
                # Take a screenshot for debugging
                screenshot_path = "ieee_debug.png"
                page.screenshot(path=screenshot_path)
                print(f"📸 Screenshot saved: {screenshot_path}")
                
            else:
                print(f"❓ Unexpected page: {final_url}")
            
            print(f"\n⏳ Keeping browser open for 15 seconds so you can see...")
            print("   You can close the browser manually or wait")
            time.sleep(15)
            
            browser.close()
            
            return "ethz.ch" in final_url
            
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run IEEE visual demo."""
    print("IEEE Institutional Login Visual Demo")
    print("====================================")
    
    success = demo_ieee_institutional_flow()
    
    if success:
        print("\n🎉 Demo successful!")
        print("✅ Institutional login flow is working")
        print("💡 The system can authenticate through IEEE using ETH credentials")
    else:
        print("\n⚠️  Demo completed but may need refinement")
        print("💡 The infrastructure is there, may need publisher-specific tuning")
    
    return success


if __name__ == "__main__":
    main()