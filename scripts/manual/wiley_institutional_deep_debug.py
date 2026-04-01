#!/usr/bin/env python3
"""
DEEP DEBUG WILEY INSTITUTIONAL LOGIN
====================================

Let's examine the institutional login flow step by step to find ways around Cloudflare
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def deep_debug_institutional():
    """Deep debug of the institutional login process"""
    
    print("🕵️ DEEP DEBUG: WILEY INSTITUTIONAL LOGIN")
    print("=" * 80)
    
    async with async_playwright() as p:
        # Try different browser approaches
        approaches = [
            {
                "name": "Standard Chrome",
                "headless": False,
                "args": ['--start-maximized']
            },
            {
                "name": "Stealth Chrome", 
                "headless": False,
                "args": [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--start-maximized',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            }
        ]
        
        for approach in approaches[:1]:  # Test first approach
            print(f"\n🔬 TESTING: {approach['name']}")
            print("-" * 60)
            
            browser = await p.chromium.launch(
                headless=approach['headless'],
                args=approach['args']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Add stealth scripts
            await context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Add chrome object
                window.chrome = {
                    runtime: {},
                };
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """)
            
            page = await context.new_page()
            
            # Step 1: Navigate to article
            test_doi = "10.1002/anie.202004934"
            url = f"https://doi.org/{test_doi}"
            print(f"📍 Step 1: Navigate to {url}")
            
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Step 2: Accept cookies
            print("🍪 Step 2: Handle cookies")
            try:
                cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(2000)
                    print("   ✅ Cookies accepted")
            except:
                print("   ❌ No cookie banner")
            
            # Step 3: Open login menu slowly
            print("🔑 Step 3: Open login menu")
            try:
                login_btn = await page.wait_for_selector('button:has-text("Login / Register")', timeout=5000)
                if login_btn:
                    # Hover first (human-like)
                    await login_btn.hover()
                    await page.wait_for_timeout(1000)
                    
                    # Click slowly
                    await login_btn.click()
                    await page.wait_for_timeout(3000)
                    print("   ✅ Login menu opened")
                    
                    # Take screenshot
                    await page.screenshot(path='wiley_login_menu.png')
                    print("   📸 Screenshot: wiley_login_menu.png")
            except Exception as e:
                print(f"   ❌ Failed to open login menu: {e}")
            
            # Step 4: Try different institutional access approaches
            print("🏛️ Step 4: Test institutional access approaches")
            
            # Approach A: Direct click on institutional login
            print("   Approach A: Direct institutional login click")
            try:
                inst_link = await page.wait_for_selector('a:has-text("Institutional login")', timeout=3000)
                if inst_link:
                    print("   🎯 Found institutional login link")
                    
                    # Check the href before clicking
                    href = await inst_link.get_attribute('href')
                    print(f"   🔗 Link points to: {href}")
                    
                    # Wait and click slowly
                    await page.wait_for_timeout(2000)
                    await inst_link.hover()
                    await page.wait_for_timeout(1000)
                    await inst_link.click()
                    
                    # Wait and check result
                    await page.wait_for_timeout(5000)
                    
                    current_url = page.url
                    print(f"   📍 Result URL: {current_url}")
                    
                    # Take screenshot of result
                    await page.screenshot(path='wiley_after_inst_click.png')
                    print("   📸 Screenshot: wiley_after_inst_click.png")
                    
                    # Check if we hit Cloudflare
                    page_content = await page.content()
                    if 'cloudflare' in page_content.lower() or 'verify you are human' in page_content.lower():
                        print("   ❌ Hit Cloudflare protection")
                        
                        # Try to wait it out
                        print("   ⏳ Waiting to see if Cloudflare clears...")
                        await page.wait_for_timeout(10000)
                        
                        new_url = page.url
                        new_content = await page.content()
                        
                        if new_url != current_url:
                            print(f"   🔄 URL changed to: {new_url}")
                            await page.screenshot(path='wiley_after_wait.png')
                            print("   📸 Screenshot: wiley_after_wait.png")
                        
                        if 'cloudflare' not in new_content.lower():
                            print("   ✅ Cloudflare cleared!")
                        else:
                            print("   ❌ Still blocked by Cloudflare")
                    else:
                        print("   ✅ No Cloudflare detected")
                        
                        # Look for institution selection
                        if 'institution' in page_content.lower() or 'eth' in page_content.lower():
                            print("   🎯 Found institution selection page")
                        else:
                            print("   ❓ Unknown page type")
                            
            except Exception as e:
                print(f"   ❌ Approach A failed: {e}")
            
            # Approach B: Try accessing SSO URL directly with delays
            print("\n   Approach B: Direct SSO URL with delays")
            try:
                # Construct SSO URL
                sso_url = f"https://onlinelibrary.wiley.com/action/ssostart?redirectUri=%2Fdoi%2F{test_doi.replace('/', '%2F')}"
                print(f"   🎯 Trying direct access to: {sso_url}")
                
                # Wait longer before accessing
                await page.wait_for_timeout(5000)
                
                # Navigate with different approach
                response = await page.goto(sso_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(5000)
                
                result_url = page.url
                status = response.status if response else "No response"
                
                print(f"   📊 Status: {status}")
                print(f"   📍 Result URL: {result_url}")
                
                # Check content
                content = await page.content()
                if 'cloudflare' in content.lower():
                    print("   ❌ Direct access also hits Cloudflare")
                else:
                    print("   ✅ Direct access bypassed Cloudflare!")
                    
                    # Take screenshot
                    await page.screenshot(path='wiley_direct_sso.png')
                    print("   📸 Screenshot: wiley_direct_sso.png")
                
            except Exception as e:
                print(f"   ❌ Approach B failed: {e}")
            
            print("\n⏸️ Keeping browser open for 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)
            
            await browser.close()
            break  # Only test first approach for now

if __name__ == "__main__":
    asyncio.run(deep_debug_institutional())