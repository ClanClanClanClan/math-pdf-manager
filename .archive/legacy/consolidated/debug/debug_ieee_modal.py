#!/usr/bin/env python3
"""
Debug IEEE Modal Interaction
============================

Carefully debug the IEEE modal to understand why institutional login isn't working.
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


def debug_ieee_modal():
    """Debug IEEE modal interaction step by step."""
    print("🔍 IEEE Modal Debug")
    print("Detailed investigation of modal behavior")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        return False
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=2000,
                args=['--start-maximized']
            )
            
            page = browser.new_page()
            
            # Step 1: Load IEEE paper
            print("\n🌐 Step 1: Loading IEEE paper...")
            page.goto("https://ieeexplore.ieee.org/document/8959041", wait_until='networkidle')
            
            # Handle cookies
            page.wait_for_timeout(2000)
            try:
                cookie_btn = page.wait_for_selector('button:has-text("Continue")', timeout=3000)
                if cookie_btn:
                    cookie_btn.click()
                    page.wait_for_timeout(1000)
                    print("🍪 Handled cookies")
            except Exception as e:
                pass
            
            page.screenshot(path="ieee_debug_01_loaded.png")
            
            # Step 2: Click PDF button
            print("📄 Step 2: Clicking PDF button...")
            pdf_button = page.wait_for_selector('a:has-text("PDF")', timeout=10000)
            
            if pdf_button:
                print("✅ Found PDF button")
                pdf_button.click(force=True)
                page.wait_for_timeout(3000)
                
                # Handle any new cookies
                try:
                    cookie_btn = page.wait_for_selector('button:has-text("Continue")', timeout=2000)
                    if cookie_btn:
                        cookie_btn.click()
                        page.wait_for_timeout(1000)
                except Exception as e:
                    pass
            
            page.screenshot(path="ieee_debug_02_modal_open.png")
            
            # Step 3: Examine modal content
            print("🔍 Step 3: Examining modal content...")
            
            # Check if modal is visible
            modal_selectors = [
                '.modal-dialog',
                '.modal-content',
                '[role="dialog"]',
                '.sip-modal'
            ]
            
            modal_found = False
            for selector in modal_selectors:
                try:
                    modal = page.wait_for_selector(selector, timeout=3000)
                    if modal and modal.is_visible():
                        print(f"✅ Found modal: {selector}")
                        modal_found = True
                        break
                except Exception as e:
                    continue
            
            if not modal_found:
                print("❌ No modal found")
                return False
            
            # Look for institutional button
            print("🔍 Step 4: Looking for institutional button...")
            
            institutional_selectors = [
                'button.stats-Doc_Details_sign_in_seamlessaccess_access_through_your_institution_btn',
                'button:has-text("Access Through Your Institution")',
                '.seamless-access-btn',
                'div:has-text("Access Through Your Institution")'
            ]
            
            institutional_button = None
            for selector in institutional_selectors:
                try:
                    institutional_button = page.wait_for_selector(selector, timeout=3000)
                    if institutional_button and institutional_button.is_visible():
                        print(f"✅ Found institutional button: {selector}")
                        break
                except Exception as e:
                    continue
            
            if not institutional_button:
                print("❌ No institutional button found")
                print("🔍 Available buttons in modal:")
                
                buttons = page.query_selector_all('.modal button, .modal a')
                for i, btn in enumerate(buttons):
                    try:
                        text = btn.text_content()
                        classes = btn.get_attribute('class')
                        print(f"  {i+1}. '{text.strip()}' (classes: {classes})")
                    except Exception as e:
                        continue
                
                return False
            
            # Step 5: Debug button click behavior
            print("🖱️ Step 5: Testing button click behavior...")
            
            # Get button properties before click
            button_text = institutional_button.text_content()
            button_classes = institutional_button.get_attribute('class')
            is_clickable = institutional_button.is_enabled()
            
            print(f"📋 Button details:")
            print(f"   Text: '{button_text.strip()}'")
            print(f"   Classes: {button_classes}")
            print(f"   Clickable: {is_clickable}")
            
            current_url_before = page.url
            print(f"📍 URL before click: {current_url_before}")
            
            # Try clicking with different methods
            click_methods = [
                ("click()", lambda: institutional_button.click()),
                ("click(force=True)", lambda: institutional_button.click(force=True)),
                ("click(timeout=10000)", lambda: institutional_button.click(timeout=10000))
            ]
            
            for method_name, click_func in click_methods:
                try:
                    print(f"🖱️ Trying {method_name}...")
                    click_func()
                    page.wait_for_timeout(3000)
                    
                    current_url_after = page.url
                    print(f"📍 URL after {method_name}: {current_url_after}")
                    
                    if current_url_after != current_url_before:
                        print(f"✅ {method_name} caused URL change!")
                        break
                    else:
                        print(f"⚠️ {method_name} - no URL change")
                    
                except Exception as e:
                    print(f"❌ {method_name} failed: {e}")
                    continue
            
            page.screenshot(path="ieee_debug_03_after_click.png")
            
            # Step 6: Check what happened after click
            final_url = page.url
            print(f"📍 Final URL: {final_url}")
            
            if "seamlessaccess" in final_url or final_url != current_url_before:
                print("✅ Click succeeded - navigated away from IEEE")
                
                # Continue with ETH search if we're on SeamlessAccess
                if "seamlessaccess" in final_url:
                    print("🔍 On SeamlessAccess, searching for ETH...")
                    
                    try:
                        search_box = page.wait_for_selector('input[type="search"], input[type="text"]', timeout=5000)
                        if search_box:
                            search_box.fill("ETH Zurich")
                            page.keyboard.press('Enter')
                            page.wait_for_timeout(3000)
                            
                            # Look for ETH
                            eth_link = page.wait_for_selector('a:has-text("ETH Zurich")', timeout=5000)
                            if eth_link:
                                print("✅ Found ETH on SeamlessAccess")
                                eth_link.click()
                                page.wait_for_timeout(5000)
                                
                                final_final_url = page.url
                                if "ethz.ch" in final_final_url:
                                    print("🎉 SUCCESS: Reached ETH login!")
                                    success = True
                                else:
                                    print(f"⚠️ ETH click result: {final_final_url}")
                                    success = False
                            else:
                                print("❌ ETH not found on SeamlessAccess")
                                success = False
                        else:
                            print("❌ No search box on SeamlessAccess")
                            success = False
                    except Exception as e:
                        print(f"❌ SeamlessAccess navigation failed: {e}")
                        success = False
                else:
                    print("⚠️ Not on SeamlessAccess page")
                    success = False
            else:
                print("❌ Click did not navigate away from IEEE")
                print("🔍 Modal might still be open or click was intercepted")
                
                # Check if modal is still visible
                modal_still_visible = page.query_selector('.modal-dialog')
                if modal_still_visible and modal_still_visible.is_visible():
                    print("⚠️ Modal still visible after click")
                else:
                    print("✅ Modal closed after click")
                
                success = False
            
            page.screenshot(path="ieee_debug_04_final_state.png")
            
            print("\n📸 Debug screenshots: ieee_debug_01 through ieee_debug_04")
            print("⏳ Browser stays open 20 seconds for manual inspection...")
            page.wait_for_timeout(20000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run IEEE modal debug."""
    print("IEEE Modal Debug Test")
    print("====================")
    print("🔍 Investigating IEEE modal behavior in detail")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required for testing")
        return False
    
    print(f"✅ ETH credentials available for: {username}")
    
    success = debug_ieee_modal()
    
    print(f"\n{'='*50}")
    print("IEEE MODAL DEBUG RESULTS")
    print(f"{'='*50}")
    
    if success:
        print("🎉 IEEE modal navigation works!")
        print("✅ Institutional button click successful")
        print("✅ SeamlessAccess integration working")
        print("✅ ETH authentication reachable")
    else:
        print("⚠️ IEEE modal needs specific handling")
        print("🔍 Check debug screenshots for details")
        print("💡 Modal click behavior needs refinement")
    
    return success


if __name__ == "__main__":
    main()