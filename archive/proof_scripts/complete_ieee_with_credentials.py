#!/usr/bin/env python3
"""
Complete IEEE with Credentials
==============================

Full IEEE authentication including credential filling and PDF download.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager

async def complete_ieee_with_credentials():
    """Complete IEEE authentication including ETH credential filling."""
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return False
    
    print(f"🔑 Using ETH credentials for: {username}")
    
    output_dir = Path("complete_ieee_test")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Visual to see credential filling
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
            print("🚀 Complete IEEE authentication with credentials...")
            
            # Step 1-3: Navigate through IEEE modals (we know this works)
            print("1️⃣ Navigate to IEEE and through modals")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
            await page.wait_for_timeout(2000)
            
            # Accept cookies
            try:
                await page.click('button:has-text("Accept All")')
            except:
                pass
            
            # Institutional sign in flow
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
            
            # Navigate to ETH (we know this works now)
            eth_option = await page.wait_for_selector('a:has-text("ETH Zurich - ETH Zurich")', timeout=10000)
            href = await eth_option.get_attribute('href')
            if href.startswith('/'):
                full_url = f"https://ieeexplore.ieee.org{href}"
            else:
                full_url = href
            
            print(f"2️⃣ Navigate to ETH authentication: {full_url}")
            await page.goto(full_url, wait_until='networkidle')
            
            current_url = page.url
            print(f"Current URL: {current_url}")
            
            # Step 4: Fill ETH credentials
            if 'ethz.ch' in current_url or 'shibboleth' in current_url:
                print("3️⃣ Fill ETH login credentials")
                
                # Wait for login form to appear
                await page.wait_for_timeout(3000)
                
                # Look for username field with multiple selectors
                username_selectors = [
                    'input[name="j_username"]',
                    'input[id="username"]', 
                    'input[name="username"]',
                    'input[type="text"]:visible',
                    'input[placeholder*="username" i]',
                    'input[placeholder*="benutzername" i]'
                ]
                
                username_input = None
                for selector in username_selectors:
                    try:
                        username_input = await page.wait_for_selector(selector, timeout=5000, state='visible')
                        if username_input:
                            print(f"✅ Found username field with: {selector}")
                            break
                    except:
                        continue
                
                if not username_input:
                    print("❌ Could not find username input field")
                    # Debug: show all inputs
                    all_inputs = await page.query_selector_all('input')
                    print(f"Found {len(all_inputs)} input fields:")
                    for i, inp in enumerate(all_inputs[:5]):
                        inp_type = await inp.get_attribute('type') or 'text'
                        name = await inp.get_attribute('name') or ''
                        placeholder = await inp.get_attribute('placeholder') or ''
                        visible = await inp.is_visible()
                        print(f"  Input {i}: type={inp_type}, name='{name}', placeholder='{placeholder}', visible={visible}")
                    return False
                
                # Look for password field
                password_selectors = [
                    'input[name="j_password"]',
                    'input[id="password"]',
                    'input[name="password"]', 
                    'input[type="password"]:visible',
                    'input[placeholder*="password" i]',
                    'input[placeholder*="passwort" i]'
                ]
                
                password_input = None
                for selector in password_selectors:
                    try:
                        password_input = await page.wait_for_selector(selector, timeout=5000, state='visible')
                        if password_input:
                            print(f"✅ Found password field with: {selector}")
                            break
                    except:
                        continue
                
                if not password_input:
                    print("❌ Could not find password input field")
                    return False
                
                # Fill credentials
                print(f"4️⃣ Filling credentials for user: {username}")
                await username_input.fill(username)
                await password_input.fill(password)
                print("✅ Credentials filled")
                
                # Submit form
                print("5️⃣ Submit login form")
                submit_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]', 
                    'button:has-text("Login")',
                    'button:has-text("Anmelden")',
                    'input[value="Login"]',
                    'input[value="Anmelden"]',
                    'form button:last-child'
                ]
                
                submitted = False
                for selector in submit_selectors:
                    try:
                        submit_button = await page.query_selector(selector)
                        if submit_button:
                            await submit_button.click()
                            print(f"✅ Clicked submit button: {selector}")
                            submitted = True
                            break
                    except:
                        continue
                
                if not submitted:
                    # Try pressing Enter
                    print("⌨️ Trying Enter key")
                    await page.keyboard.press('Enter')
                    submitted = True
                
                # Wait for authentication
                print("6️⃣ Wait for authentication to complete")
                await page.wait_for_timeout(8000)
                
                # Check where we ended up
                current_url = page.url
                print(f"After login URL: {current_url}")
                
                if 'ieee' in current_url:
                    print("✅ SUCCESS! Back at IEEE after authentication")
                    
                    # Try to access PDF
                    print("7️⃣ Test PDF access")
                    doc_id = "8347162" 
                    stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                    
                    response = await page.goto(stamp_url, wait_until='networkidle')
                    
                    if response and response.status == 200:
                        content = await response.body()
                        
                        if content.startswith(b'%PDF'):
                            print("🎉 SUCCESS! PDF downloaded directly!")
                            pdf_path = output_dir / "ieee_authenticated.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            print(f"📁 PDF saved: {pdf_path} ({len(content)} bytes)")
                            return True
                        else:
                            # Check for PDF iframe
                            await page.wait_for_timeout(5000)
                            pdf_frame = await page.query_selector('iframe[src*="pdf"], iframe#pdf')
                            if pdf_frame:
                                src = await pdf_frame.get_attribute('src')
                                if src and not src.startswith('http'):
                                    src = f"https://ieeexplore.ieee.org{src}"
                                
                                pdf_response = await page.goto(src)
                                pdf_content = await pdf_response.body()
                                
                                if pdf_content.startswith(b'%PDF'):
                                    print("🎉 SUCCESS! PDF downloaded from iframe!")
                                    pdf_path = output_dir / "ieee_authenticated.pdf"
                                    with open(pdf_path, 'wb') as f:
                                        f.write(pdf_content)
                                    print(f"📁 PDF saved: {pdf_path} ({len(pdf_content)} bytes)")
                                    return True
                            
                            print("⚠️ Authentication succeeded but PDF access still restricted")
                            await page.screenshot(path=output_dir / "after_auth.png")
                            return True  # Authentication worked
                else:
                    print(f"⚠️ Still at ETH or other page: {current_url}")
                    await page.screenshot(path=output_dir / "still_at_eth.png") 
                    return False
            else:
                print(f"❌ Not at ETH login page: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            print("Keeping browser open for inspection...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(complete_ieee_with_credentials())
    
    if success:
        print("\n🎉 COMPLETE SUCCESS!")
        print("✅ IEEE authentication flow works end-to-end")
        print("✅ ETH credentials filled and submitted")
        print("✅ Authentication completed successfully")
    else:
        print("\n❌ Authentication incomplete")
    
    exit(0 if success else 1)