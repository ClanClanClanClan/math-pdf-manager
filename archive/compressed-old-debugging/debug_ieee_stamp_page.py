#!/usr/bin/env python3
"""
Debug IEEE Stamp Page
====================

Debug what's on the IEEE stamp page after authentication to find the download button.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from secure_credential_manager import get_credential_manager

async def debug_ieee_stamp_page():
    """Debug IEEE stamp page to find download elements."""
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return False
    
    print("🔍 DEBUGGING IEEE STAMP PAGE")
    print("=" * 40)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visual for debugging
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        page = await context.new_page()
        
        try:
            # Fast authentication (same as IEEE publisher)
            print("1️⃣ Quick authentication...")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            try:
                await page.click('button:has-text("Accept All")', timeout=5000)
            except:
                pass
            
            # Quick auth flow
            await page.click('a:has-text("Institutional Sign In")')
            await page.wait_for_timeout(3000)
            
            modal = await page.wait_for_selector('ngb-modal-window')
            
            # Wait for modal content
            await page.wait_for_function(
                '''() => {
                    const modal = document.querySelector('ngb-modal-window');
                    if (!modal) return false;
                    const buttons = modal.querySelectorAll('button');
                    const visibleButtons = Array.from(buttons).filter(btn => {
                        const style = window.getComputedStyle(btn);
                        return style.display !== 'none' && style.visibility !== 'hidden' && btn.offsetParent !== null;
                    });
                    return visibleButtons.length >= 2;
                }''',
                timeout=30000
            )
            
            await page.wait_for_timeout(2000)
            
            access_button = await modal.wait_for_selector(
                'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', 
                timeout=15000, 
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
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000, state='visible')
            
            await username_input.fill(username)
            await password_input.fill(password)
            
            submit_button = await page.query_selector('button[type="submit"]')
            await submit_button.click()
            await page.wait_for_timeout(10000)
            
            print("✅ Authentication completed")
            
            # Now debug the stamp page
            print("\n2️⃣ Navigating to stamp page...")
            
            # Click PDF button
            pdf_button = await page.wait_for_selector('a[href*="stamp.jsp"]', timeout=10000, state='visible')
            if pdf_button:
                href = await pdf_button.get_attribute('href')
                print(f"Found PDF button: {href}")
                
                await pdf_button.click()
                await page.wait_for_timeout(5000)
                await page.wait_for_load_state('networkidle')
                
                print(f"📍 Stamp page URL: {page.url}")
                
                # Debug: Show all elements that might be download buttons
                print("\n3️⃣ Analyzing stamp page elements...")
                
                # Look for iframes
                iframes = await page.query_selector_all('iframe')
                print(f"Found {len(iframes)} iframes:")
                for i, iframe in enumerate(iframes):
                    src = await iframe.get_attribute('src')
                    print(f"  Iframe {i}: {src}")
                
                # Look for divs with specific IDs
                print("\n🔍 Looking for download-related elements...")
                
                elements_to_check = [
                    '#icon',
                    '#maskedImage', 
                    'cr-icon',
                    '[id="icon"]',
                    '[id="maskedImage"]',
                    'div:has(#maskedImage)',
                    '.download',
                    '.pdf-download',
                    'button:has-text("Download")',
                    'a:has-text("Download")'
                ]
                
                for selector in elements_to_check:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            print(f"✅ Found {len(elements)} elements with selector: {selector}")
                            for j, elem in enumerate(elements):
                                visible = await elem.is_visible()
                                text = await elem.text_content()
                                print(f"    Element {j}: visible={visible}, text='{text}'")
                        else:
                            print(f"❌ No elements found for: {selector}")
                    except Exception as e:
                        print(f"❌ Error with selector {selector}: {e}")
                
                # Show page content snippet
                print("\n📄 Page content analysis...")
                content = await page.content()
                
                if 'maskedImage' in content:
                    print("✅ Found 'maskedImage' in page content")
                if 'cr-icon' in content:
                    print("✅ Found 'cr-icon' in page content")
                if 'download' in content.lower():
                    print("✅ Found 'download' in page content")
                
                # Look for any clickable elements
                clickable_elements = await page.query_selector_all('button, a, div[onclick], span[onclick]')
                print(f"\n🖱️ Found {len(clickable_elements)} potentially clickable elements")
                
                download_related = []
                for elem in clickable_elements[:20]:  # Check first 20
                    try:
                        text = await elem.text_content()
                        onclick = await elem.get_attribute('onclick')
                        classes = await elem.get_attribute('class')
                        elem_id = await elem.get_attribute('id')
                        
                        if any(keyword in (text or '').lower() for keyword in ['download', 'pdf', 'save']):
                            download_related.append(f"Text: '{text}', ID: {elem_id}, Class: {classes}")
                        elif onclick and 'download' in onclick.lower():
                            download_related.append(f"OnClick: '{onclick}', ID: {elem_id}")
                    except:
                        continue
                
                if download_related:
                    print("📥 Download-related elements:")
                    for elem_info in download_related:
                        print(f"  - {elem_info}")
                
                print("\n⏱️ Waiting 60 seconds for manual inspection...")
                await page.wait_for_timeout(60000)
            else:
                print("❌ Could not find PDF button")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_ieee_stamp_page())