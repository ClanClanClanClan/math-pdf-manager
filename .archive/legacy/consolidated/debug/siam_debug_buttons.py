#!/usr/bin/env python3
"""
SIAM Debug - Find All Institutional Buttons
===========================================

Debug script to find and analyze all institutional access options on SIAM.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def debug_siam_buttons():
    """Find all possible institutional access buttons on SIAM."""
    print("🔍 SIAM Button Debug")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,
            args=['--start-maximized']
        )
        
        page = browser.new_page()
        
        # Try different starting points
        test_urls = [
            ("SIAM Homepage", "https://www.siam.org/"),
            ("SIAM ePubs", "https://epubs.siam.org/"),
            ("Direct SSO", "https://epubs.siam.org/action/ssostart"),
            ("Login Page", "https://epubs.siam.org/action/showLogin"),
            ("Paper Page", "https://epubs.siam.org/doi/10.1137/20M1339829")
        ]
        
        for name, url in test_urls:
            print(f"\n{'='*60}")
            print(f"Testing: {name}")
            print(f"URL: {url}")
            print('='*60)
            
            try:
                # Navigate with longer timeout
                print("🌐 Loading page...")
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(5000)
                
                # Check for Cloudflare
                page_text = page.content()
                if "cloudflare" in page_text.lower():
                    print("🔒 Cloudflare detected - waiting 15 seconds...")
                    page.wait_for_timeout(15000)
                    page_text = page.content()
                
                # Current state
                current_url = page.url
                page_title = page.title()
                print(f"📍 Current URL: {current_url}")
                print(f"📋 Title: {page_title[:80]}...")
                
                # Look for ALL institutional/login related elements
                print("\n🔍 Searching for institutional access elements...")
                
                # Comprehensive selectors
                all_selectors = [
                    # Specific institutional
                    'a.institutional__btn',
                    '.loginBar a.btn',
                    '.user-login-bar a',
                    'a[href*="ssostart"]',
                    'a[href*="institutional"]',
                    'a:has-text("Access via your Institution")',
                    'a:has-text("Institutional")',
                    'button:has-text("Institution")',
                    
                    # General login/access
                    'a:has-text("Sign in")',
                    'a:has-text("Log in")',
                    'a:has-text("Login")',
                    'button:has-text("Sign in")',
                    'button:has-text("Log in")',
                    '.sign-in-label',
                    
                    # Header/nav areas
                    'header a.btn',
                    'nav a.btn',
                    '.navbar a.btn',
                    '.header-login a',
                    
                    # Any button with institution icon
                    'a:has(.icon-institution)',
                    'button:has(.icon-institution)',
                    
                    # Hidden elements
                    '.hidden-xs a.btn',
                    '.hidden-sm a.btn',
                    '.visible-lg a.btn'
                ]
                
                found_elements = []
                
                for selector in all_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        for elem in elements:
                            try:
                                text = elem.text_content() or ""
                                href = elem.get_attribute('href') or ""
                                classes = elem.get_attribute('class') or ""
                                is_visible = elem.is_visible()
                                
                                # Get parent info
                                parent = elem.evaluate('el => el.parentElement.tagName + "." + el.parentElement.className')
                                
                                element_info = {
                                    'selector': selector,
                                    'text': text.strip(),
                                    'href': href,
                                    'classes': classes,
                                    'visible': is_visible,
                                    'parent': parent
                                }
                                
                                # Avoid duplicates
                                if element_info not in found_elements:
                                    found_elements.append(element_info)
                                    
                            except Exception as e:
                                pass
                    except Exception as e:
                        pass
                
                # Display findings
                if found_elements:
                    print(f"\n✅ Found {len(found_elements)} login/institutional elements:")
                    for i, elem in enumerate(found_elements):
                        print(f"\n{i+1}. Selector: {elem['selector']}")
                        print(f"   Text: '{elem['text']}'")
                        print(f"   Href: {elem['href']}")
                        print(f"   Classes: {elem['classes']}")
                        print(f"   Visible: {elem['visible']}")
                        print(f"   Parent: {elem['parent']}")
                else:
                    print("❌ No institutional/login elements found")
                
                # Take screenshot
                screenshot_path = f"siam_debug_{name.replace(' ', '_').lower()}.png"
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"\n📸 Full page screenshot: {screenshot_path}")
                
                # Special check for paper page
                if "doi" in url:
                    print("\n🔍 Special checks for paper page...")
                    
                    # Check if we need to click PDF first
                    pdf_links = page.query_selector_all('a:has-text("PDF"), button:has-text("PDF")')
                    print(f"📄 Found {len(pdf_links)} PDF links")
                    
                    # Check for login state
                    if "guest" in page_text.lower() or "not logged in" in page_text.lower():
                        print("👤 User appears to be guest/not logged in")
                    
                    # Check header area specifically
                    header = page.query_selector('header, .header, .navbar, .top-navigation')
                    if header:
                        header_html = header.inner_html()
                        if "institution" in header_html.lower():
                            print("✅ Found 'institution' in header area")
                        if "sign in" in header_html.lower() or "log in" in header_html.lower():
                            print("✅ Found login option in header")
                
            except Exception as e:
                print(f"❌ Error on {name}: {e}")
            
            input(f"\n⏸️  Press Enter to continue to next URL...")
        
        print("\n🏁 Debug complete. Browser stays open for 30 seconds...")
        page.wait_for_timeout(30000)
        browser.close()


def main():
    """Run SIAM button debug."""
    print("SIAM Institutional Button Debug")
    print("==============================")
    print("This script will help identify the correct institutional access button\n")
    
    debug_siam_buttons()
    
    print("\n" + "="*60)
    print("Debug complete. Check screenshots and output.")


if __name__ == "__main__":
    main()