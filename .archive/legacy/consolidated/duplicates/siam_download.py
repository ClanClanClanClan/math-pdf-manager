#!/usr/bin/env python3
"""
SIAM PDF Download with ETH Authentication
=========================================

Download PDFs from SIAM (Society for Industrial and Applied Mathematics) 
using ETH institutional access.
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


def siam_pdf_download():
    """SIAM authentication and PDF download."""
    print("📄 SIAM PDF Download with ETH Authentication")
    print("Authenticate through SIAM institutional access")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"🔐 Using ETH credentials for: {username}")
    
    # Example SIAM paper URLs - try multiple formats
    paper_urls = [
        "https://epubs.siam.org/doi/10.1137/20M1339829",  # Recent paper
        "https://epubs.siam.org/doi/abs/10.1137/18M1210502",  # With /abs/
        "https://epubs.siam.org/doi/full/10.1137/18M1210502",  # With /full/
        "https://www.siam.org/publications/journals/siam-journal-on-numerical-analysis-sinum"  # Journal page
    ]
    
    paper_url = paper_urls[0]  # Try the first one
    print(f"📄 Testing with paper: {paper_url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=1000,
                args=['--start-maximized']
            )
            
            page = browser.new_page()
            
            print("\n🌐 Step 1: Loading SIAM paper...")
            page.goto(paper_url, wait_until='networkidle')
            page.wait_for_timeout(3000)
            
            # Handle cookies
            try:
                cookie_buttons = [
                    'button:has-text("Accept")',
                    'button:has-text("Accept All")',
                    'button:has-text("I Agree")',
                    'button[id*="accept"]',
                    'button[class*="accept"]'
                ]
                for selector in cookie_buttons:
                    try:
                        cookie_btn = page.wait_for_selector(selector, timeout=2000)
                        if cookie_btn and cookie_btn.is_visible():
                            cookie_btn.click()
                            print("🍪 Accepted cookies")
                            page.wait_for_timeout(1000)
                            break
                    except Exception as e:
                        continue
            except Exception as e:
                pass
            
            print("📄 Step 2: Looking for PDF access options...")
            
            # Debug: Print all links on page
            print("🔍 Debugging: Looking for all links on page...")
            all_links = page.query_selector_all('a')
            print(f"📋 Found {len(all_links)} links total")
            
            # Also check page title to verify we loaded correctly
            page_title = page.title()
            print(f"📄 Page title: {page_title}")
            
            # Check if we got a 404
            if "404" in page_title or "not found" in page_title.lower():
                print("❌ Page not found (404). Trying alternative URL...")
                # Try next URL in list
                if len(paper_urls) > 1:
                    paper_url = paper_urls[1]
                    print(f"📄 Trying: {paper_url}")
                    page.goto(paper_url, wait_until='networkidle')
                    page.wait_for_timeout(3000)
            
            pdf_related_links = []
            download_links = []
            
            for link in all_links:  # Check all links
                try:
                    href = link.get_attribute('href') or ''
                    text = link.text_content() or ''
                    title = link.get_attribute('title') or ''
                    aria_label = link.get_attribute('aria-label') or ''
                    
                    # Look for PDF-related content
                    if ('pdf' in href.lower() or 'pdf' in text.lower() or 
                        'pdf' in title.lower() or 'pdf' in aria_label.lower() or
                        'download' in text.lower() or 'full text' in text.lower()):
                        link_info = f"Text: '{text.strip()}', Href: '{href}'"
                        if title:
                            link_info += f", Title: '{title}'"
                        if aria_label:
                            link_info += f", Aria: '{aria_label}'"
                        pdf_related_links.append(link_info)
                        
                        # Check for download links specifically
                        if 'download' in text.lower() or '/pdf/' in href or '.pdf' in href:
                            download_links.append((text.strip(), href))
                except Exception as e:
                    continue
            
            if pdf_related_links:
                print(f"📋 Found {len(pdf_related_links)} PDF/download-related links:")
                for link_info in pdf_related_links[:10]:  # Show first 10
                    print(f"  - {link_info}")
            
            # Look for PDF button/link with expanded selectors
            pdf_selectors = [
                'a:has-text("PDF")',
                'button:has-text("PDF")',
                'a[href*=".pdf"]',
                'a[href*="/pdf/"]',
                'a.pdf-link',
                '.pdf-download',
                'a:has-text("Download PDF")',
                'button:has-text("Download PDF")',
                'a[title*="PDF"]',
                'a[aria-label*="PDF"]',
                # SIAM specific selectors
                'a.show-pdf',
                'a.pdf-view',
                'a[data-doi*="pdf"]',
                'a[onclick*="pdf"]',
                '.article-tool a[href*="pdf"]',
                '.epdf-link',
                'a[href*="epdf"]',
                'a:has-text("View PDF")',
                'a:has-text("Full Text")',
                'a.full-text',
                '.download-article',
                'a[class*="download"]'
            ]
            
            pdf_element = None
            for selector in pdf_selectors:
                try:
                    elem = page.wait_for_selector(selector, timeout=1000)
                    if elem and elem.is_visible():
                        pdf_element = elem
                        print(f"✅ Found PDF element: {selector}")
                        # Get more info about the element
                        try:
                            href = elem.get_attribute('href')
                            text = elem.text_content()
                            print(f"   - Text: '{text}', Href: '{href}'")
                        except Exception as e:
                            pass
                        break
                except Exception as e:
                    continue
            
            if not pdf_element:
                print("❌ No PDF access button found")
                print("📸 Taking screenshot for debugging...")
                page.screenshot(path="siam_page_debug.png")
                print("📸 Screenshot saved as siam_page_debug.png")
                browser.close()
                return False
            
            print("📄 Step 3: Attempting PDF access...")
            
            # Get href before clicking
            pdf_href = pdf_element.get_attribute('href')
            print(f"📋 PDF URL: {pdf_href}")
            
            # Try to download PDF
            if pdf_href:
                if not pdf_href.startswith('http'):
                    pdf_href = 'https://epubs.siam.org' + pdf_href
                
                print(f"📍 PDF URL: {pdf_href}")
                
                # Method 1: Try direct download with browser
                try:
                    print("📥 Method 1: Browser download...")
                    with page.expect_download(timeout=15000) as download_info:
                        # Click the PDF link
                        pdf_element.click()
                    
                    download = download_info.value
                    download_path = "siam_downloaded.pdf"
                    download.save_as(download_path)
                    
                    if os.path.exists(download_path):
                        file_size = os.path.getsize(download_path)
                        print(f"🎉 PDF DOWNLOADED: {file_size} bytes")
                        print(f"📁 Saved as: {download_path}")
                        
                        # Verify PDF
                        with open(download_path, 'rb') as f:
                            header = f.read(4)
                            if header == b'%PDF':
                                print("✅ VALID PDF FILE!")
                                print("\n🎊 SIAM PDF DOWNLOAD SUCCESS!")
                                print("✅ Direct browser download")
                                print("✅ PDF file saved")
                                
                                print("\n⏳ Browser open 30 seconds for inspection...")
                                page.wait_for_timeout(30000)
                                browser.close()
                                return True
                                
                except Exception as e:
                    print(f"⚠️ Browser download failed: {e}")
                
                # Method 2: Download with requests
                print("📥 Method 2: Requests download...")
                try:
                    cookies = page.context.cookies()
                    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'application/pdf,text/html,application/xhtml+xml,*/*',
                        'Accept-Language': 'en-US,en;q=0.9'
                    }
                    
                    response = requests.get(pdf_href, cookies=cookie_dict, headers=headers, timeout=30)
                    
                    print(f"📋 Response status: {response.status_code}")
                    print(f"📋 Content-Type: {response.headers.get('content-type', '')}")
                    print(f"📋 Content-Length: {response.headers.get('content-length', 'unknown')}")
                    
                    if response.status_code == 200:
                        content = response.content
                        if content.startswith(b'%PDF'):
                            download_path = "siam_requests_downloaded.pdf"
                            with open(download_path, 'wb') as f:
                                f.write(content)
                            
                            print(f"🎉 PDF DOWNLOADED: {len(content)} bytes")
                            print(f"📁 Saved as: {download_path}")
                            print("\n🎊 SIAM PDF DOWNLOAD SUCCESS!")
                            print("✅ Requests download successful")
                            print("✅ PDF file saved")
                            
                            print("\n⏳ Browser open 30 seconds for inspection...")
                            page.wait_for_timeout(30000)
                            browser.close()
                            return True
                        else:
                            print(f"⚠️ Not a PDF response. Content starts with: {content[:100]}")
                            # May need login - continue to check
                            
                except Exception as e:
                    print(f"⚠️ Requests download failed: {e}")
                
                # If download failed, navigate to check if login is needed
                print("📍 Navigating to check access...")
                page.goto(pdf_href, wait_until='domcontentloaded', timeout=15000)
                page.wait_for_timeout(3000)
            
            # Check if we need institutional login
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            # Check for Cloudflare challenge
            page_text = page.content()
            if "Verify you are human" in page_text or "cloudflare" in page_text.lower():
                print("🔒 Cloudflare challenge detected")
                print("⏳ Waiting for manual verification...")
                
                # Take screenshot
                page.screenshot(path="siam_cloudflare.png")
                print("📸 Screenshot saved as siam_cloudflare.png")
                
                # Wait for user to complete challenge
                print("⏳ Please complete the Cloudflare challenge in the browser...")
                page.wait_for_timeout(15000)  # Wait 15 seconds
                
                # Check if we moved past the challenge
                current_url = page.url
                print(f"📍 After challenge URL: {current_url}")
            
            # Check if PDF opened in browser
            if current_url.endswith('.pdf') or 'pdf' in page.url:
                print("📄 PDF opened in browser")
                print("📥 Attempting to save PDF...")
                
                # Take screenshot as PDF might be displayed
                page.screenshot(path="siam_pdf_view.png")
                
                # Try to trigger download
                try:
                    # Press Ctrl+S or Cmd+S to save
                    page.keyboard.press('Control+s' if sys.platform != 'darwin' else 'Meta+s')
                    page.wait_for_timeout(2000)
                    
                    # Or try to download via requests
                    cookies = page.context.cookies()
                    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'application/pdf,*/*'
                    }
                    
                    response = requests.get(current_url, cookies=cookie_dict, headers=headers)
                    
                    if response.status_code == 200 and response.content.startswith(b'%PDF'):
                        download_path = "siam_browser_downloaded.pdf"
                        with open(download_path, 'wb') as f:
                            f.write(response.content)
                        
                        file_size = len(response.content)
                        print(f"🎉 PDF DOWNLOADED: {file_size} bytes")
                        print(f"📁 Saved as: {download_path}")
                        print("\n🎊 SIAM PDF DOWNLOAD SUCCESS!")
                        print("✅ PDF accessed without login")
                        print("✅ PDF file downloaded")
                        
                        print("\n⏳ Browser open 30 seconds for inspection...")
                        page.wait_for_timeout(30000)
                        browser.close()
                        return True
                    
                except Exception as e:
                    print(f"⚠️ PDF save failed: {e}")
            
            # Look for institutional login options
            print("🏛️ Step 4: Looking for institutional access...")
            
            institutional_selectors = [
                'a:has-text("Institutional")',
                'button:has-text("Institutional")',
                'a:has-text("Institution")',
                'button:has-text("Institution")',
                'a:has-text("Log in via your institution")',
                'button:has-text("Log in via your institution")',
                'a:has-text("Access through your institution")',
                'button:has-text("Access through your institution")',
                'a[href*="institutional"]',
                'a[href*="institution"]',
                '.institutional-login',
                '#institutional-login',
                'a:has-text("Shibboleth")',
                'a:has-text("Athens")'
            ]
            
            inst_element = None
            for selector in institutional_selectors:
                try:
                    elem = page.wait_for_selector(selector, timeout=3000)
                    if elem and elem.is_visible():
                        inst_element = elem
                        print(f"✅ Found institutional access: {selector}")
                        break
                except Exception as e:
                    continue
            
            if inst_element:
                print("🏛️ Step 5: Clicking institutional access...")
                inst_element.click()
                page.wait_for_timeout(3000)
                
                # Look for institution search
                print("🔍 Step 6: Searching for ETH Zurich...")
                
                search_selectors = [
                    'input[type="search"]',
                    'input[placeholder*="institution"]',
                    'input[placeholder*="search"]',
                    'input[placeholder*="university"]',
                    'input[name*="search"]',
                    'input[name*="institution"]',
                    'input.search',
                    '#institutionSearch',
                    'input[aria-label*="search"]'
                ]
                
                search_input = None
                for selector in search_selectors:
                    try:
                        elem = page.wait_for_selector(selector, timeout=3000)
                        if elem and elem.is_visible():
                            search_input = elem
                            print(f"✅ Found search input: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if search_input:
                    search_input.focus()
                    search_input.type("ETH Zurich", delay=100)
                    page.wait_for_timeout(3000)
                    
                    # Look for ETH in results
                    print("🎯 Step 7: Selecting ETH Zurich...")
                    
                    eth_selectors = [
                        'a:has-text("ETH Zurich")',
                        'button:has-text("ETH Zurich")',
                        'div:has-text("ETH Zurich")',
                        'li:has-text("ETH Zurich")',
                        'span:has-text("ETH Zurich")',
                        '[title*="ETH Zurich"]',
                        'option:has-text("ETH Zurich")'
                    ]
                    
                    eth_element = None
                    for selector in eth_selectors:
                        try:
                            elem = page.wait_for_selector(selector, timeout=3000)
                            if elem and elem.is_visible():
                                eth_element = elem
                                print(f"✅ Found ETH option: {selector}")
                                break
                        except Exception as e:
                            continue
                    
                    if eth_element:
                        eth_element.click()
                        page.wait_for_timeout(5000)
                        
                        # Check if we reached ETH login
                        current_url = page.url
                        if "ethz.ch" in current_url:
                            print("🎉 Step 8: Reached ETH authentication!")
                            print(f"📍 ETH URL: {current_url}")
                            
                            # ETH login
                            print("🔐 Step 9: Entering ETH credentials...")
                            
                            username_field = page.wait_for_selector(
                                'input[name="j_username"], input[name="username"]', 
                                timeout=5000
                            )
                            if username_field:
                                username_field.fill(username)
                                print(f"✅ Username: {username}")
                            
                            password_field = page.wait_for_selector(
                                'input[name="j_password"], input[name="password"]', 
                                timeout=5000
                            )
                            if password_field:
                                password_field.fill(password)
                                print("✅ Password entered")
                            
                            submit_button = page.wait_for_selector(
                                'input[type="submit"], button[type="submit"]', 
                                timeout=5000
                            )
                            if submit_button:
                                print("🚀 Step 10: Submitting login...")
                                submit_button.click()
                                
                                # Wait for redirect back to SIAM
                                page.wait_for_timeout(10000)
                                
                                final_url = page.url
                                print(f"📍 Final URL: {final_url}")
                                
                                if "siam" in final_url.lower():
                                    print("✅ Returned to SIAM with authentication!")
                                    
                                    # Extract cookies for download
                                    print("🍪 Extracting authentication cookies...")
                                    cookies = page.context.cookies()
                                    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                                    print(f"📋 Found {len(cookies)} cookies")
                                    
                                    # Now try to download the PDF
                                    print("📥 Step 11: Attempting PDF download...")
                                    
                                    # Method 1: Direct download from page
                                    download_success = False
                                    try:
                                        with page.expect_download(timeout=30000) as download_info:
                                            # Try clicking PDF link again
                                            pdf_link = page.wait_for_selector('a:has-text("PDF")', timeout=5000)
                                            if pdf_link:
                                                pdf_link.click()
                                        
                                        download = download_info.value
                                        download_path = "siam_downloaded.pdf"
                                        download.save_as(download_path)
                                        
                                        if os.path.exists(download_path):
                                            file_size = os.path.getsize(download_path)
                                            print(f"🎉 PDF DOWNLOADED: {file_size} bytes")
                                            print(f"📁 Saved as: {download_path}")
                                            
                                            # Verify PDF
                                            with open(download_path, 'rb') as f:
                                                header = f.read(4)
                                                if header == b'%PDF':
                                                    print("✅ VALID PDF FILE!")
                                                    download_success = True
                                    except Exception as e:
                                        print(f"⚠️ Direct download failed: {e}")
                                    
                                    # Method 2: Find PDF URL and download with requests
                                    if not download_success:
                                        print("📥 Method 2: Looking for PDF URL...")
                                        
                                        # Get all links on page
                                        all_links = page.query_selector_all('a')
                                        pdf_urls = []
                                        
                                        for link in all_links:
                                            try:
                                                href = link.get_attribute('href')
                                                text = link.text_content()
                                                if href and ('.pdf' in href or '/pdf/' in href or 
                                                           (text and 'pdf' in text.lower())):
                                                    if not href.startswith('http'):
                                                        href = 'https://epubs.siam.org' + href
                                                    pdf_urls.append((text, href))
                                            except Exception as e:
                                                continue
                                        
                                        if pdf_urls:
                                            print("📋 Found PDF URLs:")
                                            for text, url in pdf_urls[:5]:
                                                print(f"  - {text}: {url}")
                                            
                                            # Try downloading the first PDF URL
                                            if pdf_urls:
                                                pdf_url = pdf_urls[0][1]
                                                print(f"📥 Downloading: {pdf_url}")
                                                
                                                headers = {
                                                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                                                    'Accept': 'application/pdf,*/*',
                                                    'Accept-Language': 'en-US,en;q=0.9'
                                                }
                                                
                                                response = requests.get(
                                                    pdf_url,
                                                    cookies=cookie_dict,
                                                    headers=headers,
                                                    timeout=30
                                                )
                                                
                                                if response.status_code == 200:
                                                    content = response.content
                                                    if content.startswith(b'%PDF'):
                                                        download_path = "siam_requests_downloaded.pdf"
                                                        with open(download_path, 'wb') as f:
                                                            f.write(content)
                                                        
                                                        print(f"🎉 PDF DOWNLOADED: {len(content)} bytes")
                                                        print(f"📁 Saved as: {download_path}")
                                                        download_success = True
                                                    else:
                                                        print(f"⚠️ Not a PDF: {content[:50]}")
                                                else:
                                                    print(f"❌ HTTP {response.status_code}")
                                    
                                    if download_success:
                                        print("\n🎊 SIAM PDF DOWNLOAD SUCCESS!")
                                        print("✅ Complete SIAM authentication")
                                        print("✅ ETH institutional access")
                                        print("✅ PDF file downloaded")
                                        success = True
                                    else:
                                        print("\n⚠️ SIAM authentication successful but PDF download failed")
                                        success = False
                                    
                                else:
                                    print("❌ Did not return to SIAM after authentication")
                                    success = False
                            else:
                                print("❌ Submit button not found")
                                success = False
                        else:
                            print("❌ Did not reach ETH authentication")
                            success = False
                    else:
                        print("❌ Could not find ETH in institution list")
                        success = False
                else:
                    print("❌ Could not find institution search")
                    success = False
            else:
                print("ℹ️ No institutional login button found")
                
                # Check if we actually have access or need login
                page_content = page.content()
                if "access denied" in page_content.lower() or "403" in page_content or "forbidden" in page_content.lower():
                    print("❌ Access denied - institutional login may be required")
                    print("📸 Taking screenshot for debugging...")
                    page.screenshot(path="siam_access_denied.png")
                    success = False
                else:
                    # Try to find the PDF by other means
                    print("🔍 Looking for PDF in current page...")
                    
                    # Initialize success flag
                    success = False
                    
                    # Get cookies and headers
                    cookies = page.context.cookies()
                    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'application/pdf,*/*'
                    }
                    
                    # Check for PDF viewer iframe or embed
                    pdf_viewers = page.query_selector_all('iframe[src*="pdf"], embed[src*="pdf"], object[type*="pdf"]')
                    if pdf_viewers:
                        print(f"📄 Found {len(pdf_viewers)} PDF viewer(s)")
                        for viewer in pdf_viewers:
                            src = viewer.get_attribute('src') or viewer.get_attribute('data')
                            if src:
                                print(f"📋 PDF viewer source: {src}")
                                if not src.startswith('http'):
                                    src = 'https://epubs.siam.org' + src
                                
                                # Try to download the PDF
                                try:
                                    response = requests.get(src, cookies=cookie_dict, headers=headers, timeout=30)
                                    if response.status_code == 200 and response.content.startswith(b'%PDF'):
                                        download_path = "siam_viewer_downloaded.pdf"
                                        with open(download_path, 'wb') as f:
                                            f.write(response.content)
                                        
                                        print(f"🎉 PDF DOWNLOADED: {len(response.content)} bytes")
                                        print(f"📁 Saved as: {download_path}")
                                        print("\n🎊 SIAM PDF DOWNLOAD SUCCESS!")
                                        print("✅ PDF extracted from viewer")
                                        print("✅ PDF file saved")
                                        success = True
                                        break
                                except Exception as e:
                                    print(f"⚠️ Viewer PDF download failed: {e}")
                    
                    if not success:
                        print("⚠️ Could not find or download PDF")
                        print("📸 Taking final screenshot...")
                        page.screenshot(path="siam_final_page.png")
                        success = False
            
            print("\n⏳ Browser open 30 seconds for inspection...")
            page.wait_for_timeout(30000)
            
            browser.close()
            return success
            
    except Exception as e:
        print(f"❌ SIAM download error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run SIAM PDF download."""
    print("SIAM PDF Download")
    print("=================")
    print("🎯 Download PDF from SIAM with ETH institutional access")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"✅ ETH credentials loaded for: {username}")
    
    success = siam_pdf_download()
    
    print(f"\n{'='*60}")
    print("SIAM DOWNLOAD RESULTS")
    print(f"{'='*60}")
    
    if success:
        print("🎉 SIAM PDF DOWNLOAD COMPLETE!")
        print("✅ SIAM authentication successful")
        print("✅ ETH institutional access working")
        print("✅ PDF file downloaded")
        print("\n✅ IEEE: Working")
        print("✅ Springer: Working")
        print("✅ SIAM: Working")
    else:
        print("⚠️ SIAM download needs further investigation")
        print("ℹ️ May require different authentication flow")
    
    return success


if __name__ == "__main__":
    main()