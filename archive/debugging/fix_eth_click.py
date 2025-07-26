#!/usr/bin/env python3
"""
Fix ETH Click Issue
==================

Debug and fix the ETH Zurich link clicking issue.
"""

import asyncio
from playwright.async_api import async_playwright

async def fix_eth_click():
    """Fix the ETH Zurich link clicking issue."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print("🔧 Debugging ETH link click issue...")
            
            # Navigate to IEEE
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
            await page.wait_for_timeout(2000)
            
            # Accept cookies
            try:
                await page.click('button:has-text("Accept All")')
            except:
                pass
            
            # Go through authentication flow up to ETH selection
            print("1️⃣ Click Institutional Sign In")
            await page.click('a:has-text("Institutional Sign In")')
            await page.wait_for_timeout(2000)
            
            print("2️⃣ Click SeamlessAccess button")
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
            
            print("3️⃣ Search for ETH Zurich")
            inst_modal = await page.wait_for_selector('ngb-modal-window:has-text("Search for your Institution")', timeout=15000)
            search_input = await inst_modal.wait_for_selector('input.inst-typeahead-input', timeout=10000)
            await search_input.fill("ETH Zurich")
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)
            
            print("4️⃣ Debug ETH Zurich link")
            
            # Find all links that contain ETH
            eth_links = await page.query_selector_all('a:has-text("ETH")')
            print(f"Found {len(eth_links)} links with 'ETH'")
            
            for i, link in enumerate(eth_links):
                text = await link.text_content()
                href = await link.get_attribute('href') or ''
                visible = await link.is_visible()
                id_attr = await link.get_attribute('id') or ''
                
                print(f"  Link {i}: '{text}' href='{href[:50]}...' visible={visible} id='{id_attr}'")
                
                if 'ETH Zurich - ETH Zurich' in text:
                    print(f"  🎯 This is the target link!")
                    
                    # Try multiple click methods
                    print("  🔄 Method 1: Regular click")
                    try:
                        await link.click(timeout=5000)
                        await page.wait_for_timeout(2000)
                        current_url = page.url
                        print(f"      After regular click: {current_url}")
                        
                        if 'wayf' in current_url or 'shibboleth' in current_url:
                            print("  ✅ SUCCESS with regular click!")
                            return True
                    except Exception as e:
                        print(f"      Regular click failed: {e}")
                    
                    print("  🔄 Method 2: Force click")
                    try:
                        await link.click(force=True, timeout=5000)
                        await page.wait_for_timeout(2000)
                        current_url = page.url
                        print(f"      After force click: {current_url}")
                        
                        if 'wayf' in current_url or 'shibboleth' in current_url:
                            print("  ✅ SUCCESS with force click!")
                            return True
                    except Exception as e:
                        print(f"      Force click failed: {e}")
                    
                    print("  🔄 Method 3: Navigate to href directly")
                    try:
                        if href and href.startswith('/'):
                            full_href = f"https://ieeexplore.ieee.org{href}"
                            print(f"      Navigating to: {full_href}")
                            await page.goto(full_href)
                            await page.wait_for_timeout(2000)
                            current_url = page.url
                            print(f"      After direct navigation: {current_url}")
                            
                            if 'wayf' in current_url or 'shibboleth' in current_url or 'ethz' in current_url:
                                print("  ✅ SUCCESS with direct navigation!")
                                return True
                    except Exception as e:
                        print(f"      Direct navigation failed: {e}")
                    
                    print("  🔄 Method 4: Hover and click")
                    try:
                        await link.hover()
                        await page.wait_for_timeout(500)
                        await link.click()
                        await page.wait_for_timeout(2000)
                        current_url = page.url
                        print(f"      After hover+click: {current_url}")
                        
                        if 'wayf' in current_url or 'shibboleth' in current_url:
                            print("  ✅ SUCCESS with hover+click!")
                            return True
                    except Exception as e:
                        print(f"      Hover+click failed: {e}")
                    
                    break
            
            print("❌ All click methods failed")
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        finally:
            print("Keeping browser open for inspection...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(fix_eth_click())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: ETH link click test")