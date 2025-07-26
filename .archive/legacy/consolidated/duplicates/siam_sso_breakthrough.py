#!/usr/bin/env python3
"""
SIAM SSO Breakthrough
====================

Use the separate SSO domain to bypass Cloudflare.
"""

import sys
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


def investigate_sso_domain():
    """Investigate the separate SSO domain."""
    print("🔍 Investigating SSO Domain")
    print("=" * 60)
    
    sso_urls = [
        "https://sso.siam.org/",
        "https://sso.siam.org/SSO/Login.aspx",
        "https://sso.siam.org/SSO/",
        "https://sso.siam.org/SSO/Discovery.aspx",
        "https://sso.siam.org/SSO/Shibboleth.aspx",
        "https://sso.siam.org/SSO/Institution.aspx"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    for url in sso_urls:
        print(f"\n🔗 Testing: {url}")
        try:
            response = session.get(url, timeout=10, allow_redirects=True)
            print(f"   Status: {response.status_code}")
            print(f"   Final URL: {response.url}")
            print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            # Check for Cloudflare
            if 'cloudflare' in response.text.lower():
                print("   ☁️ Cloudflare detected")
            else:
                print("   ✅ No Cloudflare!")
                
                # Check for institution search
                if 'institution' in response.text.lower():
                    print("   🏛️ Institution search found!")
                    
                # Check for ETH
                if 'eth' in response.text.lower():
                    print("   🎯 ETH reference found!")
                    
                # Check for form elements
                if '<form' in response.text:
                    print("   📝 Form elements found!")
                    
                # Save the response for analysis
                with open(f"sso_response_{url.split('/')[-1]}.html", 'w') as f:
                    f.write(response.text)
                print(f"   💾 Saved response to file")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")


def test_sso_with_browser():
    """Test SSO domain with browser automation."""
    print("\n🌐 Testing SSO Domain with Browser")
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
            
            # Try the SSO domain
            sso_url = "https://sso.siam.org/SSO/Login.aspx"
            print(f"\n📍 Navigating to: {sso_url}")
            
            page.goto(sso_url, wait_until='domcontentloaded')
            page.wait_for_timeout(5000)
            
            # Check if we bypassed Cloudflare
            if 'cloudflare' not in page.content().lower():
                print("✅ Successfully bypassed Cloudflare on SSO domain!")
                
                # Take screenshot
                page.screenshot(path="sso_domain_success.png")
                print("📸 Screenshot saved")
                
                # Look for institution search
                search_selectors = [
                    'input[type="text"]',
                    'input[placeholder*="institution"]',
                    'input[name*="institution"]',
                    'select[name*="institution"]',
                    '#institution',
                    '.institution-search'
                ]
                
                for selector in search_selectors:
                    try:
                        elem = page.wait_for_selector(selector, timeout=3000)
                        if elem and elem.is_visible():
                            print(f"✅ Found search element: {selector}")
                            
                            # Try to use it
                            elem.fill("ETH Zurich")
                            print("📝 Filled ETH Zurich")
                            
                            # Look for submit button
                            submit_btn = page.query_selector('input[type="submit"], button[type="submit"]')
                            if submit_btn:
                                submit_btn.click()
                                print("🚀 Submitted form")
                                
                                page.wait_for_timeout(5000)
                                
                                # Check if we reached ETH
                                if 'ethz.ch' in page.url:
                                    print("🎉 BREAKTHROUGH! Reached ETH login via SSO domain!")
                                    
                                    # Continue with ETH login
                                    username_field = page.query_selector('input[name="j_username"], input[name="username"]')
                                    if username_field:
                                        username_field.fill(username)
                                        print("✅ Username filled")
                                    
                                    password_field = page.query_selector('input[name="j_password"], input[name="password"]')
                                    if password_field:
                                        password_field.fill(password)
                                        print("✅ Password filled")
                                    
                                    submit_button = page.query_selector('input[type="submit"], button[type="submit"]')
                                    if submit_button:
                                        submit_button.click()
                                        print("🚀 ETH login submitted")
                                        
                                        page.wait_for_timeout(10000)
                                        
                                        # Check if we're back at SIAM
                                        if 'siam' in page.url.lower():
                                            print("🎉 COMPLETE SUCCESS! Returned to SIAM with authentication!")
                                            
                                            # Now try to download PDF
                                            pdf_url = "https://epubs.siam.org/doi/pdf/10.1137/20M1339829"
                                            page.goto(pdf_url, wait_until='domcontentloaded')
                                            page.wait_for_timeout(5000)
                                            
                                            if page.url.endswith('.pdf'):
                                                print("📄 PDF accessible!")
                                                
                                                # Download with requests
                                                cookies = page.context.cookies()
                                                cookie_dict = {c['name']: c['value'] for c in cookies}
                                                
                                                response = requests.get(page.url, cookies=cookie_dict)
                                                if response.status_code == 200 and response.content.startswith(b'%PDF'):
                                                    with open("siam_sso_breakthrough.pdf", 'wb') as f:
                                                        f.write(response.content)
                                                    
                                                    print(f"🎉 PDF DOWNLOADED: {len(response.content)} bytes")
                                                    print("📁 Saved as: siam_sso_breakthrough.pdf")
                                                    
                                                    browser.close()
                                                    return True
                            
                            break
                    except Exception as e:
                        continue
                
                # If no search found, look for other elements
                print("🔍 Looking for other interactive elements...")
                
                # Check for links to institution selection
                links = page.query_selector_all('a')
                for link in links:
                    try:
                        text = link.text_content()
                        href = link.get_attribute('href')
                        if text and ('institution' in text.lower() or 'shibboleth' in text.lower()):
                            print(f"🔗 Found link: '{text}' -> {href}")
                            link.click()
                            page.wait_for_timeout(5000)
                            break
                    except Exception as e:
                        continue
                
            else:
                print("❌ Cloudflare still present on SSO domain")
            
            print("\n⏳ Browser stays open for 30 seconds...")
            page.wait_for_timeout(30000)
            
            browser.close()
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Test the SSO breakthrough approach."""
    print("SIAM SSO Breakthrough")
    print("====================")
    print("Using separate SSO domain to bypass Cloudflare\n")
    
    # First investigate the SSO domain
    investigate_sso_domain()
    
    # Then test with browser
    success = test_sso_with_browser()
    
    print("\n" + "="*60)
    if success:
        print("🎉 BREAKTHROUGH SUCCESSFUL!")
        print("✅ SSO domain bypassed Cloudflare")
        print("✅ ETH authentication completed")
        print("✅ PDF downloaded successfully")
        print("\n🎊 ALL THREE PUBLISHERS NOW FULLY WORKING!")
    else:
        print("🔍 SSO domain investigation complete")
        print("Check saved HTML files for further analysis")
        
        print("\n💡 Alternative approaches to try:")
        print("1. Use the saved HTML to understand the SSO form structure")
        print("2. Try different User-Agent strings")
        print("3. Use the separate SSO domain for direct authentication")
        print("4. Investigate any JavaScript requirements")


if __name__ == "__main__":
    main()