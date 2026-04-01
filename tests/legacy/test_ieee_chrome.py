#!/usr/bin/env python3
"""
IEEE Chrome Test
Try with Chromium engine instead of Firefox to see if detection is browser-specific.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_ieee_chrome():
    """Test with Chrome instead of Firefox."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    arnumber = "8347162"
    
    print(f"\n{'='*70}")
    print(f"🌐 IEEE CHROME ENGINE TEST")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Testing direct PDF access with Chromium...")
    print()
    
    async with async_playwright() as p:
        # Use Chromium instead of Firefox
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-plugins-discovery',
                '--disable-web-security',
                '--no-first-run',
                '--no-service-autorun',
                '--password-store=basic',
                '--use-mock-keychain',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Maximum stealth for Chrome
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override the automation property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Remove automation indicators
            delete window.chrome;
            window.chrome = {
                runtime: {}
            };
        """)
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Quick authentication
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Authenticating at: {url}")
            
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Accept cookies
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # Quick auth flow
            login_btn = await page.query_selector('a.inst-sign-in')
            await login_btn.click()
            await page.wait_for_timeout(2000)
            
            seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            await seamless_btn.click()
            await page.wait_for_timeout(2000)
            
            search_input = await page.query_selector('input.inst-typeahead-input')
            await search_input.click()
            await search_input.fill("")
            await page.wait_for_timeout(300)
            await search_input.type("ETH Zurich", delay=50)
            await page.wait_for_timeout(1500)
            await search_input.press('ArrowDown')
            await page.wait_for_timeout(300)
            await search_input.press('Enter')
            
            await page.wait_for_timeout(5000)
            
            # ETH login
            if 'ethz.ch' in page.url.lower():
                username_field = await page.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                if username_field:
                    await username_field.fill(username)
                
                password_field = await page.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                if password_field:
                    await password_field.fill(password)
                
                submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_btn:
                    await submit_btn.click()
                    await page.wait_for_timeout(10000)
            
            # Check authentication
            if 'ieeexplore.ieee.org' in page.url:
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    print("✅ Authentication successful in Chrome!")
                    
                    # Test 1: Direct navigation
                    pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arnumber}"
                    print(f"\n🎯 Test 1: Direct navigation to: {pdf_url}")
                    
                    await page.goto(pdf_url, wait_until='domcontentloaded')
                    await page.wait_for_timeout(5000)
                    
                    print(f"Result URL: {page.url}")
                    
                    if '/stamp/stamp.jsp' in page.url:
                        print("🎉 SUCCESS! Chrome reached PDF viewer!")
                        
                        # Try to get the actual PDF content
                        page_content = await page.content()
                        if 'PDF' in page_content or 'pdf' in page_content:
                            print("✅ PDF content detected in page!")
                        
                        # Look for PDF download link
                        download_links = await page.query_selector_all('a[href*=".pdf"], button[title*="Download"]')
                        if download_links:
                            print(f"Found {len(download_links)} potential download links")
                        
                        print("Browser staying open - you can manually save the PDF!")
                        await page.wait_for_timeout(60000)
                        
                    else:
                        print("❌ Chrome also redirected away from PDF")
                        
                        # Test 2: Click PDF button instead
                        print(f"\n🎯 Test 2: Clicking PDF button in Chrome")
                        
                        # Go back to paper page
                        paper_url = f"https://ieeexplore.ieee.org/document/{arnumber}"
                        await page.goto(paper_url, wait_until='domcontentloaded')
                        await page.wait_for_timeout(3000)
                        
                        pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                        if pdf_button:
                            before_url = page.url
                            await pdf_button.click()
                            await page.wait_for_timeout(5000)
                            after_url = page.url
                            
                            print(f"Before: {before_url}")
                            print(f"After: {after_url}")
                            
                            if after_url != before_url:
                                if '/stamp/stamp.jsp' in after_url:
                                    print("🎉 SUCCESS! PDF button click worked in Chrome!")
                                else:
                                    print(f"❌ Redirected to: {after_url}")
                            else:
                                print("❌ No navigation occurred")
                
                else:
                    print("❌ No PDF button - auth failed in Chrome too")
            
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_ieee_chrome())