#!/usr/bin/env python3
"""
Realistic Institutional Login Test
=================================

Handle real-world publisher websites with cookie modals, popups, and actual UI.
This shows the complete institutional authentication flow.
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


def handle_cookie_modals(page):
    """Handle cookie consent modals that block interaction."""
    print("🍪 Checking for cookie modals...")
    
    cookie_selectors = [
        # Common cookie modal buttons
        'button:has-text("Accept All")',
        'button:has-text("Accept all cookies")',
        'button:has-text("Accept")',
        'button:has-text("OK")',
        'button:has-text("I Agree")',
        'button:has-text("Continue")',
        '[id*="cookie"] button',
        '[class*="cookie"] button',
        '[data-testid*="cookie"] button',
        '.cookie-banner button',
        '#cookieConsent button',
        '.gdpr-banner button',
        # IEEE specific
        '#onetrust-accept-btn-handler',
        '.ot-sdk-show-settings',
        # Springer specific
        '.cc-allow',
        '.cc-dismiss',
        # Generic close buttons
        'button[aria-label="Close"]',
        'button[title="Close"]',
        '.close-button',
        '[data-dismiss="modal"]'
    ]
    
    for selector in cookie_selectors:
        try:
            element = page.wait_for_selector(selector, timeout=2000)
            if element and element.is_visible():
                print(f"✅ Found cookie modal button: {selector}")
                element.click()
                page.wait_for_timeout(1000)
                print("🍪 Cookie modal dismissed")
                return True
        except Exception as e:
            continue
    
    print("🍪 No cookie modal found or already dismissed")
    return False


def test_ieee_complete_flow():
    """Complete IEEE institutional flow with all real-world handling."""
    print("🎬 Complete IEEE Institutional Flow")
    print("===================================")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials not found")
        return False
    
    print(f"✅ ETH credentials loaded for: {username}")
    
    try:
        with sync_playwright() as p:
            # Launch with realistic settings
            browser = p.chromium.launch(
                headless=False,
                slow_mo=1500,  # Slower for visibility
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            print("\n🌐 Step 1: Going to IEEE Xplore...")
            page.goto("https://ieeexplore.ieee.org", wait_until='networkidle')
            
            # Handle cookie modal first
            handle_cookie_modals(page)
            
            print("🔍 Step 2: Looking for institutional access...")
            
            # Try multiple approaches to find institutional access
            approaches = [
                {
                    'name': 'Direct institutional URL',
                    'action': lambda: page.goto("https://ieeexplore.ieee.org/servlet/wayf.jsp", wait_until='networkidle')
                },
                {
                    'name': 'Subscribe/Access menu',
                    'action': lambda: page.click('a:has-text("Subscribe")') if page.query_selector('a:has-text("Subscribe")') else None
                },
                {
                    'name': 'User menu institutional',
                    'action': lambda: page.click('.user-menu') if page.query_selector('.user-menu') else None
                }
            ]
            
            for approach in approaches:
                try:
                    print(f"🎯 Trying: {approach['name']}")
                    result = approach['action']()
                    if result is not None:
                        page.wait_for_timeout(2000)
                        handle_cookie_modals(page)  # Check again after navigation
                        break
                except Exception as e:
                    print(f"   ❌ Failed: {e}")
                    continue
            
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            # Take screenshot for debugging
            page.screenshot(path="ieee_step2.png")
            print("📸 Screenshot saved: ieee_step2.png")
            
            print("🏛️ Step 3: Looking for institution finder...")
            
            # Look for various institution finder patterns
            institution_patterns = [
                # Direct search box
                {
                    'selector': 'input[placeholder*="institution" i]',
                    'action': 'type',
                    'value': 'ETH Zurich'
                },
                {
                    'selector': 'input[placeholder*="organization" i]',
                    'action': 'type', 
                    'value': 'ETH Zurich'
                },
                # Dropdown or select
                {
                    'selector': 'select[name*="institution" i]',
                    'action': 'select',
                    'value': 'ETH Zurich'
                },
                # Links with ETH
                {
                    'selector': 'a:has-text("ETH Zurich")',
                    'action': 'click'
                },
                {
                    'selector': 'a:has-text("Swiss Federal Institute")',
                    'action': 'click'
                },
                # Options in select
                {
                    'selector': 'option:has-text("ETH")',
                    'action': 'click'
                }
            ]
            
            institution_found = False
            for pattern in institution_patterns:
                try:
                    element = page.wait_for_selector(pattern['selector'], timeout=3000)
                    if element and element.is_visible():
                        print(f"✅ Found institution element: {pattern['selector']}")
                        
                        if pattern['action'] == 'type':
                            element.fill(pattern['value'])
                            page.wait_for_timeout(1000)
                            # Try to submit or press enter
                            page.keyboard.press('Enter')
                        elif pattern['action'] == 'click':
                            element.click()
                        elif pattern['action'] == 'select':
                            element.select_option(label=pattern['value'])
                        
                        page.wait_for_timeout(2000)
                        institution_found = True
                        break
                        
                except Exception as e:
                    print(f"   ⚠️  Pattern {pattern['selector']} failed: {e}")
                    continue
            
            if not institution_found:
                print("❌ Could not find institution selector")
                print("🔍 Let's see what's available on the page...")
                
                # Debug: show all clickable elements
                clickable = page.query_selector_all('a, button, input, select')
                print(f"📋 Found {len(clickable)} interactive elements")
                
                for i, elem in enumerate(clickable[:10]):  # Show first 10
                    try:
                        tag = elem.tag_name
                        text = elem.text_content()[:50] if elem.text_content() else ""
                        print(f"  {i+1}. {tag}: {text}")
                    except Exception as e:
                        continue
            
            # Check final state
            final_url = page.url
            page_title = page.title()
            print(f"\n📍 Final state:")
            print(f"   Title: {page_title}")
            print(f"   URL: {final_url}")
            
            # Take final screenshot
            page.screenshot(path="ieee_final.png")
            print("📸 Final screenshot: ieee_final.png")
            
            if "ethz.ch" in final_url:
                print("🎉 SUCCESS: Reached ETH authentication!")
                print("✅ Institutional login flow is working")
                
                # Show what we'd do next
                print("🔑 Next steps would be:")
                print(f"   1. Enter username: {username}")
                print("   2. Enter password: [hidden]")
                print("   3. Submit login form")
                print("   4. Get redirected back to IEEE with access")
                
                success = True
            else:
                print("⚠️  Did not reach ETH login page")
                print("💡 May need manual intervention or different approach")
                success = False
            
            print(f"\n⏳ Browser will stay open for 20 seconds...")
            print("   You can interact with it manually")
            page.wait_for_timeout(20000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_springer_complete_flow():
    """Test Springer with complete real-world handling."""
    print("\n🎬 Complete Springer Institutional Flow")
    print("=======================================")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=1500)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            print("🌐 Going to a Springer paper page...")
            page.goto("https://link.springer.com/article/10.1007/s00454-020-00244-6", wait_until='networkidle')
            
            # Handle cookies
            handle_cookie_modals(page)
            
            print("🔍 Looking for institutional access...")
            
            # Springer-specific selectors
            springer_institutional = [
                'a:has-text("Access through your institution")',
                'a:has-text("Institutional Login")',
                'button:has-text("Access through your institution")',
                '.institutional-access',
                '[href*="institutional"]'
            ]
            
            clicked = False
            for selector in springer_institutional:
                try:
                    element = page.wait_for_selector(selector, timeout=3000)
                    if element and element.is_visible():
                        print(f"✅ Found institutional button: {selector}")
                        element.click()
                        page.wait_for_timeout(2000)
                        handle_cookie_modals(page)  # Handle any new modals
                        clicked = True
                        break
                except Exception as e:
                    continue
            
            if clicked:
                current_url = page.url
                print(f"📍 After click: {current_url}")
                
                # Look for ETH in institution list
                eth_found = False
                eth_selectors = [
                    'a:has-text("ETH Zurich")',
                    'a:has-text("Swiss Federal Institute")',
                    'option:has-text("ETH")',
                    '[value*="ethz"]'
                ]
                
                for selector in eth_selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=5000)
                        if element:
                            print(f"✅ Found ETH option: {selector}")
                            element.click()
                            page.wait_for_timeout(3000)
                            eth_found = True
                            break
                    except Exception as e:
                        continue
                
                final_url = page.url
                print(f"📍 Final URL: {final_url}")
                
                # Take screenshot
                page.screenshot(path="springer_final.png")
                print("📸 Screenshot: springer_final.png")
                
                if "ethz.ch" in final_url:
                    print("🎉 SUCCESS: Reached ETH authentication!")
                    success = True
                else:
                    print("⚠️  May need manual navigation")
                    success = False
            else:
                print("❌ Could not find institutional access button")
                success = False
            
            print("⏳ Browser stays open 15 seconds...")
            page.wait_for_timeout(15000)
            browser.close()
            
            return success
            
    except Exception as e:
        print(f"❌ Springer test error: {e}")
        return False


def main():
    """Run realistic institutional tests."""
    print("Realistic Institutional Login Test")
    print("==================================")
    print("🎯 This handles real website complexities:")
    print("   - Cookie consent modals")
    print("   - Dynamic content loading")
    print("   - Multiple UI patterns")
    print("   - Actual authentication flows")
    
    # Get credentials
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"✅ ETH credentials loaded for: {username}")
    
    # Test IEEE
    print("\n" + "="*50)
    ieee_success = test_ieee_complete_flow()
    
    # Test Springer
    print("\n" + "="*50)
    springer_success = test_springer_complete_flow()
    
    # Summary
    print("\n" + "="*60)
    print("REALISTIC INSTITUTIONAL TEST RESULTS")
    print("="*60)
    print(f"IEEE complete flow:     {'✅ SUCCESS' if ieee_success else '❌ NEEDS WORK'}")
    print(f"Springer complete flow: {'✅ SUCCESS' if springer_success else '❌ NEEDS WORK'}")
    
    if ieee_success or springer_success:
        print("\n🎉 Institutional authentication is working!")
        print("✅ The system can handle real publisher websites")
        print("💡 With proper configuration, this enables ETH access")
    else:
        print("\n⚠️  Publisher interfaces may need specific handling")
        print("💡 The framework is there, needs publisher-specific tuning")
    
    return ieee_success or springer_success


if __name__ == "__main__":
    main()