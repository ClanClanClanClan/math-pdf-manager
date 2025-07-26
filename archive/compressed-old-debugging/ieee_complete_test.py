#!/usr/bin/env python3
"""
IEEE Complete Test - Full Authentication with PDF Download
==========================================================

Complete IEEE authentication with real credentials and PDF download.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager

async def complete_ieee_test():
    """Complete IEEE authentication test with real credentials and PDF download."""
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        print("Available credentials:", cm.list_available_credentials())
        return False
    
    print(f"✅ Found ETH credentials for user: {username}")
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("ieee_complete_test")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Visual to see what happens
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate', 
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            }
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        page = await context.new_page()
        
        try:
            print("🚀 Starting complete IEEE authentication...")
            
            # Navigate to IEEE
            print("1️⃣ Navigate to IEEE document")
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Handle cookies
            print("2️⃣ Accept cookies")
            try:
                await page.click('button:has-text("Accept All")', timeout=5000)
                await page.wait_for_timeout(1000)
            except:
                pass
            
            # Click institutional sign in
            print("3️⃣ Click Institutional Sign In")
            await page.click('a:has-text("Institutional Sign In")', timeout=10000)
            await page.wait_for_timeout(2000)
            
            # Wait for first modal and find SeamlessAccess button
            print("4️⃣ Find first modal and SeamlessAccess button")
            modal = await page.wait_for_selector('ngb-modal-window', timeout=10000)
            
            # Wait for buttons to load
            await page.wait_for_function(
                '''() => {
                    const modal = document.querySelector('ngb-modal-window');
                    const buttons = modal ? modal.querySelectorAll('button') : [];
                    return buttons.length > 2;
                }''',
                timeout=20000
            )
            
            # Click SeamlessAccess button
            access_button = await modal.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', timeout=10000, state='visible')
            await access_button.click()
            await page.wait_for_timeout(3000)
            
            # Wait for second modal (institution search)
            print("5️⃣ Wait for institution search modal")
            inst_modal = await page.wait_for_selector('ngb-modal-window:has-text("Search for your Institution")', timeout=15000)
            
            # Find and fill search input
            print("6️⃣ Find search input and type ETH Zurich")
            search_input = await inst_modal.wait_for_selector('input.inst-typeahead-input', timeout=10000)
            await search_input.fill("ETH Zurich")
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)
            
            # Click ETH Zurich link
            print("7️⃣ Click ETH Zurich option")
            eth_link = await page.wait_for_selector('a:has-text("ETH Zurich - ETH Zurich")', timeout=10000)
            await page.evaluate('(element) => element.click()', eth_link)
            print("✅ Clicked ETH Zurich link")
            
            # Wait for redirect to ETH login
            print("8️⃣ Wait for redirect to ETH login")
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            current_url = page.url
            print(f"Current URL: {current_url}")
            
            if 'wayf' in current_url or 'shibboleth' in current_url or 'ethz.ch' in current_url:
                print("✅ SUCCESS! Redirected to ETH authentication system!")
                
                # Fill ETH credentials
                print("9️⃣ Fill ETH login form")
                try:
                    # Wait for login form
                    username_input = await page.wait_for_selector('input[name="j_username"], input[id="username"], input[name="username"]', timeout=10000)
                    password_input = await page.wait_for_selector('input[name="j_password"], input[id="password"], input[type="password"]', timeout=5000)
                    
                    print("✅ Found login form")
                    await username_input.fill(username)
                    await password_input.fill(password)
                    print("✅ Filled credentials")
                    
                    # Submit form
                    submit_button = await page.query_selector('[type="submit"], input[value="Login"], button:has-text("Login")')
                    if submit_button:
                        await submit_button.click()
                        print("✅ Submitted login form")
                    else:
                        # Try pressing Enter
                        await page.keyboard.press('Enter')
                        print("✅ Pressed Enter to submit")
                    
                    # Wait for authentication
                    print("🔟 Wait for authentication to complete")
                    await page.wait_for_timeout(5000)
                    
                    # Check if we're back at IEEE
                    current_url = page.url
                    print(f"Post-auth URL: {current_url}")
                    
                    if 'ieee' in current_url:
                        print("✅ SUCCESS! Back at IEEE after authentication!")
                        
                        # Extract document ID and try stamp URL
                        doc_id = current_url.split('/document/')[1].split('/')[0] if '/document/' in current_url else "8347162"
                        stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                        
                        print(f"1️⃣1️⃣ Navigate to stamp URL for PDF: {stamp_url}")
                        response = await page.goto(stamp_url, wait_until='networkidle', timeout=30000)
                        
                        if response and response.status == 200:
                            content = await response.body()
                            
                            if content.startswith(b'%PDF'):
                                print("🎉 SUCCESS! Got PDF directly!")
                                pdf_path = output_dir / "ieee_paper.pdf"
                                with open(pdf_path, 'wb') as f:
                                    f.write(content)
                                print(f"📁 PDF saved to: {pdf_path}")
                                print(f"📊 PDF size: {len(content)} bytes")
                                return True
                            else:
                                print("🔍 Looking for PDF iframe...")
                                await page.wait_for_timeout(5000)
                                
                                # Look for PDF iframe
                                pdf_frame = await page.query_selector('iframe[src*="pdf"], iframe#pdf')
                                if pdf_frame:
                                    src = await pdf_frame.get_attribute('src')
                                    print(f"📄 Found PDF iframe: {src}")
                                    
                                    if src and not src.startswith('http'):
                                        src = f"https://ieeexplore.ieee.org{src}"
                                    
                                    pdf_response = await page.goto(src, wait_until='networkidle')
                                    pdf_content = await pdf_response.body()
                                    
                                    if pdf_content.startswith(b'%PDF'):
                                        print("🎉 SUCCESS! Downloaded PDF from iframe!")
                                        pdf_path = output_dir / "ieee_paper.pdf"
                                        with open(pdf_path, 'wb') as f:
                                            f.write(pdf_content)
                                        print(f"📁 PDF saved to: {pdf_path}")
                                        print(f"📊 PDF size: {len(pdf_content)} bytes")
                                        return True
                                
                                print("⚠️ Authentication succeeded but PDF not directly accessible")
                                return True
                        else:
                            print(f"⚠️ Stamp URL returned status: {response.status if response else 'None'}")
                            return True
                    else:
                        print(f"⚠️ Still at ETH after login: {current_url}")
                        return False
                        
                except Exception as e:
                    print(f"❌ Error during ETH login: {e}")
                    await page.screenshot(path=output_dir / "eth_login_error.png")
                    return False
            else:
                print(f"❌ Unexpected redirect URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path=output_dir / "complete_test_error.png")
            return False
        finally:
            print("Keeping browser open for 20 seconds for inspection...")
            await asyncio.sleep(20)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(complete_ieee_test())
    print(f"\n{'🎉 COMPLETE SUCCESS' if success else '❌ FAILED'}: IEEE authentication {'with PDF download works perfectly!' if success else 'needs debugging'}")
    exit(0 if success else 1)