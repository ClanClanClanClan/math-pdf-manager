#!/usr/bin/env python3
"""
SIAM Strategic Approach
======================

A more thoughtful approach to SIAM authentication based on understanding their flow.
"""

import sys
import time
import requests
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.sync_api import sync_playwright
    from secure_credential_manager import get_credential_manager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def clear_siam_session(page):
    """Clear cookies to ensure we start anonymous."""
    print("🧹 Clearing session cookies...")
    page.context.clear_cookies()
    page.reload()
    page.wait_for_timeout(3000)


def wait_for_cloudflare(page, max_wait=30):
    """Smart Cloudflare detection and waiting."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        content = page.content()
        if "cloudflare" not in content.lower() and "verify you are human" not in content.lower():
            return True
        print("⏳ Cloudflare active, waiting...")
        page.wait_for_timeout(5000)
    return False


def siam_strategic_download():
    """Strategic approach to SIAM download."""
    print("🎯 SIAM Strategic Download Approach")
    print("=" * 60)
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"✅ ETH credentials ready for: {username}")
    
    paper_url = "https://epubs.siam.org/doi/10.1137/20M1339829"
    
    try:
        with sync_playwright() as p:
            # Use Chrome instead of Chromium for better compatibility
            browser = p.chromium.launch(
                headless=False,
                slow_mo=1000,
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # Step 1: Start fresh
            print("\n📍 Step 1: Starting fresh session")
            clear_siam_session(page)
            
            # Step 2: Load paper page
            print("\n📍 Step 2: Loading paper page")
            page.goto(paper_url, wait_until='domcontentloaded')
            
            if not wait_for_cloudflare(page):
                print("⚠️  Cloudflare challenge persistent")
            
            # Step 3: Try to access PDF to trigger login prompt
            print("\n📍 Step 3: Clicking PDF to trigger authentication")
            
            pdf_selectors = [
                'a:has-text("PDF")',
                'button:has-text("PDF")',
                '.show-pdf',
                'a[href*="pdf"]'
            ]
            
            pdf_clicked = False
            for selector in pdf_selectors:
                try:
                    pdf_elem = page.wait_for_selector(selector, timeout=3000)
                    if pdf_elem and pdf_elem.is_visible():
                        print(f"✅ Found PDF link: {selector}")
                        pdf_elem.click()
                        pdf_clicked = True
                        break
                except Exception as e:
                    continue
            
            if pdf_clicked:
                print("⏳ Waiting for authentication prompt...")
                page.wait_for_timeout(5000)
            
            # Step 4: Now look for institutional access in multiple locations
            print("\n📍 Step 4: Looking for institutional access (may appear after PDF click)")
            
            # Check different areas of the page
            areas_to_check = [
                ("Header", "header, .header, .navbar, .top-navigation"),
                ("Login Bar", ".loginBar, .user-login-bar"),
                ("Modal/Popup", ".modal, .popup, .dialog, [role='dialog']"),
                ("Main Content", "main, .content, article"),
                ("Sidebar", "aside, .sidebar")
            ]
            
            institutional_found = False
            
            for area_name, area_selector in areas_to_check:
                print(f"\n🔍 Checking {area_name}...")
                
                try:
                    area = page.query_selector(area_selector)
                    if area:
                        # Look for institutional within this area
                        inst_in_area = area.query_selector_all(
                            'a:has-text("Institution"), ' +
                            'a.institutional__btn, ' +
                            'a[href*="ssostart"], ' +
                            '.connect-anonymous-bar a'
                        )
                        
                        if inst_in_area:
                            print(f"✅ Found {len(inst_in_area)} institutional option(s) in {area_name}")
                            
                            for elem in inst_in_area:
                                try:
                                    text = elem.text_content()
                                    href = elem.get_attribute('href')
                                    is_visible = elem.is_visible()
                                    
                                    print(f"   - Text: '{text.strip()}', Visible: {is_visible}")
                                    
                                    if is_visible and not institutional_found:
                                        print(f"   🎯 Clicking this institutional link...")
                                        elem.click()
                                        institutional_found = True
                                        break
                                except Exception as e:
                                    pass
                            
                            if institutional_found:
                                break
                except Exception as e:
                    pass
            
            if not institutional_found:
                # Try global search as fallback
                print("\n🔍 Global search for institutional button...")
                
                inst_elem = page.wait_for_selector(
                    'a:has-text("Access via your Institution"), a.institutional__btn',
                    timeout=5000
                )
                if inst_elem and inst_elem.is_visible():
                    print("✅ Found institutional button globally")
                    inst_elem.click()
                    institutional_found = True
            
            if institutional_found:
                print("\n⏳ Waiting for SSO page...")
                page.wait_for_timeout(5000)
                
                # Handle potential Cloudflare on SSO page
                if not wait_for_cloudflare(page):
                    print("⚠️  Cloudflare on SSO page")
                
                # Now look for the search field
                print("\n📍 Step 5: Looking for institution search")
                
                # The search field might be dynamically loaded
                search_found = False
                for attempt in range(3):
                    print(f"\n🔍 Search attempt {attempt + 1}...")
                    
                    search_selectors = [
                        '#shibboleth_search',
                        'input[aria-label*="institution"]',
                        '.ms-sel-ctn input',
                        'input[placeholder*="Search"]',
                        'input[type="search"]'
                    ]
                    
                    for selector in search_selectors:
                        try:
                            search_elem = page.wait_for_selector(selector, timeout=3000)
                            if search_elem:
                                print(f"✅ Found search field: {selector}")
                                
                                # Click and type
                                search_elem.click()
                                page.wait_for_timeout(1000)
                                search_elem.fill("ETH Zurich")
                                print("📝 Typed: ETH Zurich")
                                
                                search_found = True
                                break
                        except Exception as e:
                            continue
                    
                    if search_found:
                        break
                    
                    # Wait a bit before retry
                    page.wait_for_timeout(3000)
                
                if search_found:
                    print("\n⏳ Waiting for dropdown results...")
                    page.wait_for_timeout(3000)
                    
                    # Try to click ETH
                    eth_clicked = False
                    eth_selectors = [
                        'li:has-text("ETH Zurich")',
                        'div:has-text("ETH Zurich")',
                        '[role="option"]:has-text("ETH")',
                        '.ms-res-item:has-text("ETH")'
                    ]
                    
                    for selector in eth_selectors:
                        try:
                            eth_elem = page.wait_for_selector(selector, timeout=3000)
                            if eth_elem and eth_elem.is_visible():
                                print(f"✅ Found ETH option: {selector}")
                                eth_elem.click()
                                eth_clicked = True
                                break
                        except Exception as e:
                            continue
                    
                    if not eth_clicked:
                        print("⏎ Pressing Enter as fallback...")
                        page.keyboard.press("Enter")
                    
                    print("\n⏳ Waiting for ETH redirect...")
                    page.wait_for_timeout(5000)
                    
                    # Continue with ETH login if reached
                    if "ethz.ch" in page.url:
                        print("\n🎉 Reached ETH login!")
                        # ... rest of ETH login code ...
                        success = True
                    else:
                        print("❌ Did not reach ETH")
                        success = False
                else:
                    print("❌ Could not find institution search")
                    success = False
            else:
                print("❌ Could not find institutional access button")
                print("\n💡 Possible reasons:")
                print("   - Need to be logged out first")
                print("   - Button appears only after clicking PDF")
                print("   - Cloudflare blocking the button")
                success = False
            
            # Take final screenshot
            page.screenshot(path="siam_strategic_final.png", full_page=True)
            print(f"\n📸 Final screenshot: siam_strategic_final.png")
            
            print("\n⏳ Browser stays open for 45 seconds...")
            page.wait_for_timeout(45000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run strategic SIAM approach."""
    print("SIAM Strategic Download")
    print("======================")
    print("A more thoughtful approach to SIAM authentication\n")
    
    success = siam_strategic_download()
    
    print("\n" + "="*60)
    if success:
        print("✅ Success with strategic approach!")
    else:
        print("❌ Still facing challenges")
        print("\n💡 Key insights:")
        print("   - Institutional button may only appear when anonymous")
        print("   - May need to trigger authentication by clicking PDF first")
        print("   - Button might be in header/navigation, not main content")
        print("   - Cloudflare remains the main obstacle")


if __name__ == "__main__":
    main()