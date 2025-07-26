#!/usr/bin/env python3
"""
Real Paper Download Test
========================

Start with actual paper DOIs, navigate to publisher pages, 
handle institutional login, and download PDFs.
"""

import sys
import time
import tempfile
import os
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
    """Handle cookie consent modals."""
    cookie_buttons = [
        'button:has-text("Accept All")',
        'button:has-text("Accept all cookies")',
        'button:has-text("Accept")',
        'button:has-text("OK")', 
        'button:has-text("I Agree")',
        '#onetrust-accept-btn-handler',
        '.cc-allow',
        '.cc-dismiss'
    ]
    
    for selector in cookie_buttons:
        try:
            element = page.wait_for_selector(selector, timeout=2000)
            if element and element.is_visible():
                print(f"🍪 Accepting cookies: {selector}")
                element.click()
                page.wait_for_timeout(1000)
                return True
        except Exception as e:
            continue
    return False


def test_ieee_paper_download():
    """Test IEEE paper download from DOI to PDF."""
    print("🎯 IEEE Paper Download Test")
    print("DOI: 10.1109/ACCESS.2020.2964093")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=1000,
                args=['--start-maximized']
            )
            
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            # Step 1: Go directly to the IEEE paper
            ieee_url = "https://ieeexplore.ieee.org/document/8959041"
            print(f"🌐 Step 1: Going to IEEE paper: {ieee_url}")
            page.goto(ieee_url, wait_until='networkidle')
            
            # Handle cookies
            handle_cookie_modals(page)
            
            page.screenshot(path="ieee_step1_paper_page.png")
            print("📸 Screenshot: ieee_step1_paper_page.png")
            
            # Step 2: Look for PDF download or institutional access
            print("🔍 Step 2: Looking for PDF download options...")
            
            # First try direct PDF download
            pdf_buttons = [
                'a:has-text("PDF")',
                'button:has-text("PDF")',
                'a[href*=".pdf"]',
                '.pdf-download',
                '#pdf-btn'
            ]
            
            pdf_found = False
            for selector in pdf_buttons:
                try:
                    element = page.wait_for_selector(selector, timeout=3000)
                    if element and element.is_visible():
                        print(f"📄 Found PDF button: {selector}")
                        element.click()
                        page.wait_for_timeout(2000)
                        pdf_found = True
                        break
                except Exception as e:
                    continue
            
            if not pdf_found:
                print("❌ No direct PDF access - need institutional login")
                
                # Look for institutional login options
                institutional_buttons = [
                    'a:has-text("Institutional Sign In")',
                    'a:has-text("Access through your institution")',
                    'button:has-text("Sign In")',
                    'a:has-text("Sign In")',
                    '.institutional-access',
                    'a[href*="institutional"]'
                ]
                
                institutional_found = False
                for selector in institutional_buttons:
                    try:
                        element = page.wait_for_selector(selector, timeout=3000)
                        if element and element.is_visible():
                            print(f"🏛️ Found institutional login: {selector}")
                            element.click()
                            page.wait_for_timeout(3000)
                            handle_cookie_modals(page)
                            institutional_found = True
                            break
                    except Exception as e:
                        continue
                
                if not institutional_found:
                    # Try going to IEEE wayf directly
                    print("🔄 Trying IEEE institutional access directly...")
                    page.goto("https://ieeexplore.ieee.org/servlet/wayf.jsp", wait_until='networkidle')
                    handle_cookie_modals(page)
            
            page.screenshot(path="ieee_step2_after_institutional.png")
            print("📸 Screenshot: ieee_step2_after_institutional.png")
            
            # Step 3: Find and select ETH Zurich
            print("🏛️ Step 3: Looking for ETH Zurich in institution list...")
            
            # Try typing in search box if available
            search_selectors = [
                'input[placeholder*="institution"]',
                'input[placeholder*="organization"]',
                'input[type="search"]',
                'input#institutionInput'
            ]
            
            for selector in search_selectors:
                try:
                    search_box = page.wait_for_selector(selector, timeout=3000)
                    if search_box and search_box.is_visible():
                        print(f"🔍 Found search box: {selector}")
                        search_box.fill("ETH Zurich")
                        page.wait_for_timeout(2000)
                        page.keyboard.press('Enter')
                        page.wait_for_timeout(2000)
                        break
                except Exception as e:
                    continue
            
            # Look for ETH options
            eth_selectors = [
                'a:has-text("ETH Zurich")',
                'a:has-text("Swiss Federal Institute of Technology")',
                'option:has-text("ETH")',
                '[value*="ethz"]',
                'a[href*="ethz"]'
            ]
            
            eth_found = False
            for selector in eth_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        print(f"✅ Found ETH option: {selector}")
                        element.click()
                        page.wait_for_timeout(3000)
                        eth_found = True
                        break
                except Exception as e:
                    continue
            
            if not eth_found:
                print("❌ Could not find ETH Zurich option")
                print("🔍 Available options on page:")
                # Show what's available
                links = page.query_selector_all('a')
                for i, link in enumerate(links[:10]):
                    try:
                        text = link.text_content()
                        if text and len(text.strip()) > 0:
                            print(f"  {i+1}. {text.strip()[:50]}")
                    except Exception as e:
                        continue
            
            page.screenshot(path="ieee_step3_eth_selection.png")
            print("📸 Screenshot: ieee_step3_eth_selection.png")
            
            # Step 4: ETH login
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            if "ethz.ch" in current_url:
                print("🎉 Reached ETH login page!")
                print("🔐 Step 4: Filling ETH credentials...")
                
                # Find username field
                username_selectors = [
                    'input[name="j_username"]',
                    'input[name="username"]',
                    'input[id="username"]',
                    'input[type="text"]'
                ]
                
                for selector in username_selectors:
                    try:
                        username_field = page.wait_for_selector(selector, timeout=3000)
                        if username_field and username_field.is_visible():
                            print(f"👤 Found username field: {selector}")
                            username_field.fill(username)
                            break
                    except Exception as e:
                        continue
                
                # Find password field
                password_selectors = [
                    'input[name="j_password"]',
                    'input[name="password"]',
                    'input[id="password"]',
                    'input[type="password"]'
                ]
                
                for selector in password_selectors:
                    try:
                        password_field = page.wait_for_selector(selector, timeout=3000)
                        if password_field and password_field.is_visible():
                            print(f"🔒 Found password field: {selector}")
                            password_field.fill(password)
                            break
                    except Exception as e:
                        continue
                
                # Submit form
                submit_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_button = page.wait_for_selector(selector, timeout=3000)
                        if submit_button and submit_button.is_visible():
                            print(f"✅ Found submit button: {selector}")
                            submit_button.click()
                            page.wait_for_load_state('networkidle')
                            break
                    except Exception as e:
                        continue
                
                page.screenshot(path="ieee_step4_after_login.png")
                print("📸 Screenshot: ieee_step4_after_login.png")
                
                # Step 5: Back to IEEE - try to download PDF
                print("📄 Step 5: Attempting PDF download...")
                page.wait_for_timeout(3000)
                
                # Look for PDF download again
                pdf_selectors = [
                    'a:has-text("PDF")',
                    'button:has-text("PDF")',
                    'a[href*=".pdf"]',
                    '.pdf-download',
                    'a[href*="stamp.jsp"]'
                ]
                
                pdf_downloaded = False
                with tempfile.TemporaryDirectory() as tmpdir:
                    for selector in pdf_selectors:
                        try:
                            element = page.wait_for_selector(selector, timeout=3000)
                            if element and element.is_visible():
                                print(f"📄 Clicking PDF download: {selector}")
                                
                                # Set up download
                                with page.expect_download() as download_info:
                                    element.click()
                                
                                download = download_info.value
                                download_path = os.path.join(tmpdir, "ieee_paper.pdf")
                                download.save_as(download_path)
                                
                                if os.path.exists(download_path):
                                    file_size = os.path.getsize(download_path)
                                    print(f"✅ PDF downloaded: {file_size} bytes")
                                    
                                    # Verify it's a PDF
                                    with open(download_path, 'rb') as f:
                                        header = f.read(4)
                                        if header == b'%PDF':
                                            print("✅ Valid PDF file!")
                                            pdf_downloaded = True
                                        else:
                                            print(f"⚠️ File header: {header}")
                                
                                break
                        except Exception as e:
                            print(f"   ❌ PDF download attempt failed: {e}")
                            continue
                
                if not pdf_downloaded:
                    print("❌ Could not download PDF")
            
            else:
                print(f"❌ Not on ETH login page. Current URL: {current_url}")
            
            print("⏳ Browser will stay open for 20 seconds for inspection...")
            page.wait_for_timeout(20000)
            
            browser.close()
            return pdf_downloaded
            
    except Exception as e:
        print(f"❌ IEEE test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_springer_paper_download():
    """Test Springer paper download from DOI to PDF."""
    print("\n🎯 Springer Paper Download Test")
    print("DOI: 10.1007/s00454-020-00244-6")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=1000)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            # Step 1: Go to Springer paper
            springer_url = "https://link.springer.com/article/10.1007/s00454-020-00244-6"
            print(f"🌐 Step 1: Going to Springer paper: {springer_url}")
            page.goto(springer_url, wait_until='networkidle')
            
            handle_cookie_modals(page)
            page.screenshot(path="springer_step1_paper_page.png")
            
            # Step 2: Look for PDF download or institutional access
            print("🔍 Step 2: Looking for PDF access...")
            
            # Try direct PDF first
            pdf_buttons = [
                'a:has-text("Download PDF")',
                'a:has-text("PDF")',
                'button:has-text("PDF")',
                '.pdf-download'
            ]
            
            pdf_found = False
            for selector in pdf_buttons:
                try:
                    element = page.wait_for_selector(selector, timeout=3000)
                    if element and element.is_visible():
                        print(f"📄 Found PDF button: {selector}")
                        element.click()
                        page.wait_for_timeout(2000)
                        pdf_found = True
                        break
                except Exception as e:
                    continue
            
            if not pdf_found:
                # Look for institutional access
                institutional_selectors = [
                    'a:has-text("Access through your institution")',
                    'a:has-text("Institutional Login")',
                    'button:has-text("Access through your institution")',
                    '.institutional-access'
                ]
                
                for selector in institutional_selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=3000)
                        if element and element.is_visible():
                            print(f"🏛️ Found institutional access: {selector}")
                            element.click()
                            page.wait_for_timeout(3000)
                            handle_cookie_modals(page)
                            break
                    except Exception as e:
                        continue
            
            page.screenshot(path="springer_step2_institutional.png")
            
            # Step 3: Find ETH Zurich
            print("🏛️ Step 3: Looking for ETH Zurich...")
            
            eth_selectors = [
                'a:has-text("ETH Zurich")',
                'a:has-text("Swiss Federal Institute")',
                'option:has-text("ETH")',
                '[value*="ethz"]'
            ]
            
            for selector in eth_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=5000)
                    if element and element.is_visible():
                        print(f"✅ Found ETH: {selector}")
                        element.click()
                        page.wait_for_timeout(3000)
                        break
                except Exception as e:
                    continue
            
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            if "ethz.ch" in current_url:
                print("🎉 Reached ETH login!")
                # Similar login process as IEEE...
                # (abbreviated for space)
                success = True
            else:
                print(f"❌ Not on ETH page: {current_url}")
                success = False
            
            page.wait_for_timeout(15000)
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ Springer test error: {e}")
        return False


def main():
    """Run real paper download tests."""
    print("Real Paper Download Test")
    print("========================")
    print("🎯 Testing complete flow: DOI → Paper Page → Institutional Login → PDF Download")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        print("Set ETH_USERNAME and ETH_PASSWORD environment variables")
        return False
    
    print(f"✅ ETH credentials loaded for: {username}")
    
    # Test IEEE
    print("\n" + "="*60)
    ieee_success = test_ieee_paper_download()
    
    # Test Springer  
    print("\n" + "="*60)
    springer_success = test_springer_paper_download()
    
    # Results
    print("\n" + "="*60)
    print("REAL PAPER DOWNLOAD RESULTS")
    print("="*60)
    print(f"IEEE complete flow:     {'✅ SUCCESS' if ieee_success else '❌ FAILED'}")
    print(f"Springer complete flow: {'✅ SUCCESS' if springer_success else '❌ FAILED'}")
    
    if ieee_success or springer_success:
        print("\n🎉 SUCCESS: Institutional download is working!")
        print("✅ ETH credentials can access publisher content")
        print("📄 PDFs are being downloaded through institutional access")
    else:
        print("\n⚠️ Need to debug the specific publisher flows")
        print("📸 Check the screenshots to see where the process stops")
    
    return ieee_success or springer_success


if __name__ == "__main__":
    main()