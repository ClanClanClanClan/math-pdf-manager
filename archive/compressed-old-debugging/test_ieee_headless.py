#!/usr/bin/env python3
"""
Test IEEE Headless Mode
=======================

Test the enhanced IEEE publisher with headless mode support.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager

async def test_ieee_headless():
    """Test IEEE authentication in headless mode with enhanced reliability."""
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return False
    
    print("🧪 TESTING IEEE HEADLESS MODE")
    print("=" * 40)
    print(f"🔑 ETH User: {username}")
    print(f"🖥️ Mode: Headless (with visual fallback)")
    print("=" * 40)
    
    output_dir = Path("ieee_headless_test")
    output_dir.mkdir(exist_ok=True)
    
    # Test with headless first, fallback to visual if needed
    for mode_attempt, (headless, mode_name) in enumerate([(True, "headless"), (False, "visual")]):
        
        if mode_attempt > 0:
            print(f"\n🔄 Fallback to {mode_name} mode...")
        else:
            print(f"\n🚀 Attempt 1: {mode_name} mode")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security', 
                    '--disable-features=VizDisplayCompositor',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-dev-shm-usage',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
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
                print(f"1️⃣ Navigate to IEEE document ({mode_name} mode)")
                await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Accept cookies
                try:
                    await page.click('button:has-text("Accept All")', timeout=5000)
                    print("✅ Accepted cookies")
                except:
                    print("- No cookies to accept")
                
                print(f"2️⃣ Click Institutional Sign In ({mode_name} mode)")
                await page.click('a:has-text("Institutional Sign In")')
                await page.wait_for_timeout(3000)
                
                print(f"3️⃣ Enhanced modal handling ({mode_name} mode)")
                modal = await page.wait_for_selector('ngb-modal-window', timeout=10000)
                
                if modal:
                    print("   Found modal, waiting for content to fully load...")
                    
                    # Enhanced waiting
                    await page.wait_for_function(
                        '''() => {
                            const modal = document.querySelector('ngb-modal-window');
                            if (!modal) return false;
                            
                            const hasLoading = modal.textContent.includes('Loading institutional login options...');
                            if (hasLoading) return false;
                            
                            const buttons = modal.querySelectorAll('button');
                            const visibleButtons = Array.from(buttons).filter(btn => {
                                const rect = btn.getBoundingClientRect();
                                const style = window.getComputedStyle(btn);
                                return (
                                    style.display !== 'none' && 
                                    style.visibility !== 'hidden' && 
                                    style.opacity !== '0' &&
                                    btn.offsetParent !== null &&
                                    rect.width > 0 && 
                                    rect.height > 0
                                );
                            });
                            
                            return visibleButtons.length >= 2;
                        }''',
                        timeout=30000
                    )
                    
                    # Mode-specific wait
                    wait_time = 5000 if headless else 2000
                    await page.wait_for_timeout(wait_time)
                    print(f"   Content loaded (waited {wait_time}ms for {mode_name})")
                    
                    # Find access button with enhanced reliability
                    access_button = None
                    selectors = [
                        'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn',
                        'button:has-text("Access through your institution")',
                        'button:has-text("Access Through Your Institution")'
                    ]
                    
                    for selector in selectors:
                        try:
                            access_button = await modal.wait_for_selector(selector, timeout=5000, state='visible')
                            if access_button and await access_button.is_visible():
                                button_text = await access_button.text_content()
                                print(f"   Found button: '{button_text}'")
                                break
                            access_button = None
                        except:
                            continue
                    
                    if access_button:
                        print(f"4️⃣ Click access button ({mode_name} mode)")
                        await access_button.click()
                        
                        # Longer wait for second modal in headless
                        wait_time = 8000 if headless else 3000
                        await page.wait_for_timeout(wait_time)
                        
                        print(f"5️⃣ Handle institution search ({mode_name} mode)")
                        inst_modal = await page.wait_for_selector('ngb-modal-window:has-text("Search for your Institution")', timeout=15000)
                        
                        if inst_modal:
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
                            
                            print(f"6️⃣ Fill ETH credentials ({mode_name} mode)")
                            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=10000, state='visible')
                            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000, state='visible')
                            
                            await username_input.fill(username)
                            await password_input.fill(password)
                            
                            submit_button = await page.query_selector('button[type="submit"]')
                            await submit_button.click()
                            await page.wait_for_timeout(10000)
                            
                            current_url = page.url
                            if 'ieee' in current_url:
                                print(f"🎉 SUCCESS! IEEE authentication completed in {mode_name} mode")
                                
                                # Quick test download
                                print("7️⃣ Test quick download")
                                import requests
                                
                                cookies = await context.cookies()
                                session = requests.Session()
                                for cookie in cookies:
                                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
                                
                                pdf_url = "https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber=8347162&ref="
                                response = session.get(pdf_url, stream=True, timeout=10)
                                
                                if response.status_code == 200 and len(response.content) > 100000:
                                    test_pdf = output_dir / f"test_{mode_name}.pdf"
                                    with open(test_pdf, 'wb') as f:
                                        f.write(response.content)
                                    
                                    file_size = test_pdf.stat().st_size
                                    print(f"✅ Test PDF downloaded: {file_size:,} bytes")
                                    
                                    await browser.close()
                                    return True, mode_name
                                else:
                                    print(f"⚠️ Authentication successful but download failed in {mode_name}")
                            else:
                                print(f"❌ Authentication failed in {mode_name} mode")
                        else:
                            print(f"❌ Institution modal not found in {mode_name} mode")
                    else:
                        print(f"❌ Access button not found in {mode_name} mode")
                        
                        # Debug: show available buttons
                        all_buttons = await modal.query_selector_all('button')
                        print(f"   Debug: Found {len(all_buttons)} buttons:")
                        for i, btn in enumerate(all_buttons):
                            try:
                                text = await btn.text_content()
                                visible = await btn.is_visible()
                                print(f"     {i}: '{text}' (visible: {visible})")
                            except:
                                print(f"     {i}: [error getting button info]")
                else:
                    print(f"❌ No modal found in {mode_name} mode")
            
            except Exception as e:
                print(f"❌ Error in {mode_name} mode: {e}")
            finally:
                await browser.close()
    
    return False, "failed"

if __name__ == "__main__":
    success, mode_used = asyncio.run(test_ieee_headless())
    
    if success:
        print(f"\n{'🎉' * 20}")
        print(f"IEEE HEADLESS MODE WORKING!")
        print(f"Final mode used: {mode_used}")
        print(f"{'🎉' * 20}")
    else:
        print(f"\n❌ IEEE headless mode test failed")
    
    exit(0 if success else 1)