#!/usr/bin/env python3
"""
Download PDF After Authentication
==================================

Complete the IEEE authentication and actually download the PDF to disk.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager

async def download_pdf_after_auth():
    """Complete IEEE authentication and actually download PDF."""
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return False
    
    print(f"🔑 Using ETH credentials for: {username}")
    
    output_dir = Path("pdf_download_test")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        page = await context.new_page()
        
        try:
            print("🚀 Complete authentication and download PDF...")
            
            # Complete authentication (we know this works)
            print("1️⃣ Complete IEEE authentication")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
            await page.wait_for_timeout(2000)
            
            # Accept cookies
            try:
                await page.click('button:has-text("Accept All")')
            except:
                pass
            
            # Go through full auth flow
            await page.click('a:has-text("Institutional Sign In")')
            await page.wait_for_timeout(2000)
            
            # First modal
            modal = await page.wait_for_selector('ngb-modal-window')
            await page.wait_for_function(
                '''() => {
                    const modal = document.querySelector('ngb-modal-window');
                    const buttons = modal ? modal.querySelectorAll('button') : [];
                    return buttons.length > 2;
                }''',
                timeout=15000
            )
            
            access_button = await modal.wait_for_selector(
                'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', 
                timeout=10000, 
                state='visible'
            )
            await access_button.click()
            await page.wait_for_timeout(3000)
            
            # Second modal
            inst_modal = await page.wait_for_selector('ngb-modal-window:has-text("Search for your Institution")', timeout=15000)
            search_input = await inst_modal.wait_for_selector('input.inst-typeahead-input', timeout=10000)
            await search_input.fill("ETH Zurich")
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)
            
            # Navigate to ETH
            eth_option = await page.wait_for_selector('a:has-text("ETH Zurich - ETH Zurich")', timeout=10000)
            href = await eth_option.get_attribute('href')
            if href.startswith('/'):
                full_url = f"https://ieeexplore.ieee.org{href}"
            else:
                full_url = href
            
            await page.goto(full_url, wait_until='networkidle')
            
            # Fill ETH credentials
            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=10000, state='visible')
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=5000, state='visible')
            
            await username_input.fill(username)
            await password_input.fill(password)
            
            submit_button = await page.query_selector('button[type="submit"]')
            await submit_button.click()
            
            # Wait for redirect back to IEEE
            await page.wait_for_timeout(8000)
            
            current_url = page.url
            print(f"After auth URL: {current_url}")
            
            if 'ieee' in current_url:
                print("✅ Authentication successful, now trying PDF download...")
                
                # Extract document ID from current URL
                if '/document/' in current_url:
                    doc_id = current_url.split('/document/')[1].split('/')[0]
                else:
                    doc_id = "8347162"
                
                print(f"Document ID: {doc_id}")
                
                # Try multiple PDF access methods
                pdf_urls = [
                    f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}",
                    f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={doc_id}",
                    f"https://ieeexplore.ieee.org/document/{doc_id}/download",
                    f"https://ieeexplore.ieee.org/iel7/5/4359136/{doc_id}.pdf"
                ]
                
                for i, pdf_url in enumerate(pdf_urls):
                    print(f"2️⃣ Trying PDF URL {i+1}: {pdf_url}")
                    
                    try:
                        response = await page.goto(pdf_url, wait_until='networkidle', timeout=30000)
                        
                        if response and response.status == 200:
                            content = await response.body()
                            content_type = response.headers.get('content-type', '')
                            
                            print(f"   Response: status={response.status}, content-type={content_type}, size={len(content)}")
                            
                            if content.startswith(b'%PDF'):
                                print(f"🎉 SUCCESS! PDF downloaded from URL {i+1}")
                                pdf_path = output_dir / f"ieee_paper_method_{i+1}.pdf"
                                with open(pdf_path, 'wb') as f:
                                    f.write(content)
                                print(f"📁 PDF saved: {pdf_path} ({len(content)} bytes)")
                                
                                # Verify it's a valid PDF
                                if len(content) > 1000:  # Reasonable size check
                                    print("✅ PDF appears to be valid (size > 1KB)")
                                    return True
                                else:
                                    print("⚠️ PDF seems too small, continuing...")
                            
                            elif 'pdf' in content_type.lower():
                                print(f"📄 Content-type indicates PDF but content doesn't start with %PDF")
                                # Save anyway
                                pdf_path = output_dir / f"ieee_content_method_{i+1}.pdf" 
                                with open(pdf_path, 'wb') as f:
                                    f.write(content)
                                print(f"📁 Content saved: {pdf_path}")
                            
                            else:
                                print(f"📄 HTML response, checking for embedded PDF...")
                                
                                # Look for PDF iframe or embed
                                await page.wait_for_timeout(3000)
                                
                                # Check for iframe with PDF
                                iframes = await page.query_selector_all('iframe')
                                print(f"   Found {len(iframes)} iframes")
                                
                                for j, iframe in enumerate(iframes):
                                    src = await iframe.get_attribute('src')
                                    if src:
                                        print(f"     Iframe {j}: {src}")
                                        
                                        if 'pdf' in src.lower() or 'stamp' in src:
                                            print(f"     🎯 This looks like a PDF iframe")
                                            
                                            if not src.startswith('http'):
                                                src = f"https://ieeexplore.ieee.org{src}"
                                            
                                            iframe_response = await page.goto(src, wait_until='networkidle')
                                            iframe_content = await iframe_response.body()
                                            
                                            if iframe_content.startswith(b'%PDF'):
                                                print(f"🎉 SUCCESS! PDF downloaded from iframe")
                                                pdf_path = output_dir / f"ieee_iframe_{i+1}_{j}.pdf"
                                                with open(pdf_path, 'wb') as f:
                                                    f.write(iframe_content)
                                                print(f"📁 PDF saved: {pdf_path} ({len(iframe_content)} bytes)")
                                                return True
                                
                                # Check for direct PDF links
                                pdf_links = await page.query_selector_all('a[href*="pdf"], a[href*="download"]')
                                print(f"   Found {len(pdf_links)} potential PDF links")
                                
                                for j, link in enumerate(pdf_links[:3]):  # Try first 3
                                    link_href = await link.get_attribute('href')
                                    link_text = await link.text_content()
                                    
                                    if link_href:
                                        print(f"     Link {j}: '{link_text}' -> {link_href}")
                                        
                                        if not link_href.startswith('http'):
                                            link_href = f"https://ieeexplore.ieee.org{link_href}"
                                        
                                        try:
                                            link_response = await page.goto(link_href)
                                            link_content = await link_response.body()
                                            
                                            if link_content.startswith(b'%PDF'):
                                                print(f"🎉 SUCCESS! PDF downloaded from link")
                                                pdf_path = output_dir / f"ieee_link_{i+1}_{j}.pdf"
                                                with open(pdf_path, 'wb') as f:
                                                    f.write(link_content)
                                                print(f"📁 PDF saved: {pdf_path} ({len(link_content)} bytes)")
                                                return True
                                        except:
                                            continue
                                
                                # Take screenshot of what we see
                                screenshot_path = output_dir / f"method_{i+1}_page.png"
                                await page.screenshot(path=screenshot_path)
                                print(f"📸 Screenshot saved: {screenshot_path}")
                        
                        else:
                            print(f"   Failed: HTTP {response.status if response else 'No response'}")
                    
                    except Exception as e:
                        print(f"   Error with URL {i+1}: {e}")
                
                print("❌ All PDF download methods failed")
                return False
            
            else:
                print(f"❌ Authentication did not redirect back to IEEE: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            print("Keeping browser open for inspection...")
            await asyncio.sleep(60)  # Longer time to manually check
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(download_pdf_after_auth())
    
    if success:
        print("\n🎉 PDF DOWNLOAD SUCCESS!")
        print("✅ IEEE authentication completed")
        print("✅ PDF successfully downloaded to disk")
    else:
        print("\n❌ PDF download failed")
        print("Authentication worked but PDF access is still restricted")
    
    exit(0 if success else 1)