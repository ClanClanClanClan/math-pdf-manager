#!/usr/bin/env python3
"""
IEEE Fresh Context Test
This test authenticates, then creates a fresh browser context with the cookies
to bypass detection.
"""

import asyncio
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_ieee_fresh_context():
    """Test with fresh context after authentication."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    output_path = Path(f"ieee_fresh_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🔄 IEEE FRESH CONTEXT TEST")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Output: {output_path}")
    print()
    
    async with async_playwright() as p:
        # First browser for authentication
        browser1 = await p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
            }
        )
        
        context1 = await browser1.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page1 = await context1.new_page()
        
        # Apply stealth
        await page1.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Navigate to paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page1.goto(url, wait_until='domcontentloaded')
            await page1.wait_for_timeout(3000)
            
            print(f"📍 Current URL: {page1.url}")
            
            # Extract arnumber
            arnumber = None
            if '/document/' in page1.url:
                arnumber = page1.url.split('/document/')[-1].strip('/')
                print(f"📄 Arnumber: {arnumber}")
            
            # Accept cookies
            try:
                cookie_btn = await page1.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page1.wait_for_timeout(1000)
            except:
                pass
            
            print(f"\n🔐 PERFORMING AUTHENTICATION")
            print("-" * 50)
            
            # Step 1: Click institutional sign in
            print("Step 1: Clicking institutional sign in...")
            login_btn = await page1.query_selector('a.inst-sign-in')
            await login_btn.click()
            print("✅ Clicked institutional sign in")
            await page1.wait_for_timeout(3000)
            
            # Step 2: Click SeamlessAccess
            print("Step 2: Clicking SeamlessAccess...")
            seamless_btn = await page1.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            await seamless_btn.click()
            print("✅ Clicked SeamlessAccess")
            await page1.wait_for_timeout(3000)
            
            # Step 3: Search for ETH
            print("Step 3: Searching for ETH Zurich...")
            search_input = await page1.query_selector('input.inst-typeahead-input')
            await search_input.click()
            await search_input.fill("")
            await page1.wait_for_timeout(500)
            await search_input.type("ETH Zurich")
            print("✅ Typed ETH Zurich")
            await page1.wait_for_timeout(2000)
            
            # Press Enter and wait
            await search_input.press('Enter')
            await page1.wait_for_timeout(3000)
            
            # Try to find and click ETH
            eth_clicked = False
            all_elements = await page1.query_selector_all('*')
            for elem in all_elements:
                try:
                    if await elem.is_visible():
                        text = await elem.text_content()
                        if text and 'ETH Zurich' in text and len(text.strip()) < 200:
                            tag_name = await elem.evaluate('el => el.tagName')
                            if tag_name in ['A', 'LI', 'DIV', 'BUTTON']:
                                await elem.click()
                                print(f"✅ Clicked ETH element")
                                eth_clicked = True
                                break
                except:
                    pass
            
            if not eth_clicked:
                print("❌ Could not click ETH - please do it manually")
                print("Waiting 30 seconds for manual selection...")
                await page1.wait_for_timeout(30000)
            else:
                await page1.wait_for_timeout(8000)
            
            # Check if at ETH login
            if 'ethz.ch' in page1.url.lower() or 'aai' in page1.url.lower():
                print("✅ Reached ETH login page")
                
                # Fill credentials
                username_field = await page1.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                if username_field:
                    await username_field.fill(username)
                    print("✅ Filled username")
                
                password_field = await page1.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                if password_field:
                    await password_field.fill(password)
                    print("✅ Filled password")
                
                # Submit
                submit_btn = await page1.query_selector('button[type="submit"], input[type="submit"]')
                if submit_btn:
                    await submit_btn.click()
                    print("✅ Submitted credentials")
                    
                    # Wait for redirect back to IEEE
                    await page1.wait_for_timeout(15000)
            
            # Check authentication success
            pdf_button = await page1.query_selector('a[href*="/stamp/stamp.jsp"]')
            if pdf_button:
                print("🎉 AUTHENTICATION SUCCESSFUL - PDF button found!")
                
                # Get cookies from authenticated session
                cookies = await context1.cookies()
                print(f"📦 Extracted {len(cookies)} cookies from authenticated session")
                
                # Close first browser
                await browser1.close()
                print("🔒 Closed authentication browser")
                
                # Create fresh browser with cookies
                print(f"\n🔄 CREATING FRESH BROWSER CONTEXT")
                print("-" * 50)
                
                browser2 = await p.firefox.launch(
                    headless=False,
                    firefox_user_prefs={
                        "dom.webdriver.enabled": False,
                        "useAutomationExtension": False,
                        "network.cookie.cookieBehavior": 0,
                    }
                )
                
                context2 = await browser2.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                
                # Add cookies to new context
                await context2.add_cookies(cookies)
                print("✅ Added cookies to new context")
                
                page2 = await context2.new_page()
                
                # Navigate directly to paper
                paper_url = f"https://ieeexplore.ieee.org/document/{arnumber}"
                print(f"🌐 Navigating to paper in fresh context: {paper_url}")
                await page2.goto(paper_url, wait_until='domcontentloaded')
                await page2.wait_for_timeout(5000)
                
                # Check for PDF button in fresh context
                pdf_button2 = await page2.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button2:
                    print("✅ PDF button available in fresh context!")
                    
                    # Try clicking it
                    pdf_href = await pdf_button2.get_attribute('href')
                    pdf_url = f"https://ieeexplore.ieee.org{pdf_href}" if pdf_href.startswith('/') else pdf_href
                    print(f"📄 PDF URL: {pdf_url}")
                    
                    # Method 1: Direct click
                    print("\nMethod 1: Direct click in fresh context")
                    before_url = page2.url
                    await pdf_button2.click()
                    await page2.wait_for_timeout(8000)
                    after_url = page2.url
                    
                    if '/stamp/stamp.jsp' in after_url:
                        print("✅ SUCCESS! Reached PDF viewer in fresh context")
                        
                        # Try download
                        try:
                            async with page2.expect_download() as download_info:
                                download_btn = await page2.query_selector('button[title*="Download"], a[title*="Download"]')
                                if download_btn:
                                    await download_btn.click()
                                    download = await download_info.value
                                    await download.save_as(output_path)
                                    print(f"✅ PDF downloaded to: {output_path}")
                                    await browser2.close()
                                    return
                        except:
                            pass
                    
                    # Method 2: Navigate directly to PDF URL
                    print("\nMethod 2: Direct navigation to PDF URL")
                    await page2.goto(pdf_url, wait_until='domcontentloaded')
                    await page2.wait_for_timeout(8000)
                    
                    if '/stamp/stamp.jsp' in page2.url:
                        print("✅ Reached PDF viewer via direct navigation")
                        
                        # Try download
                        try:
                            async with page2.expect_download() as download_info:
                                download_btn = await page2.query_selector('button[title*="Download"], a[title*="Download"]')
                                if download_btn:
                                    await download_btn.click()
                                    download = await download_info.value
                                    await download.save_as(output_path)
                                    print(f"✅ PDF downloaded to: {output_path}")
                                    await browser2.close()
                                    return
                        except:
                            pass
                    
                    # Method 3: HTTP with cookies
                    print("\nMethod 3: HTTP download with cookies")
                    cookie_jar = {c['name']: c['value'] for c in cookies}
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Referer': paper_url
                    }
                    
                    async with aiohttp.ClientSession(cookies=cookie_jar) as session:
                        async with session.get(pdf_url, headers=headers) as response:
                            if response.status == 200:
                                content = await response.read()
                                if content[:4] == b'%PDF':
                                    output_path.write_bytes(content)
                                    print(f"✅ SUCCESS! PDF downloaded via HTTP")
                                    print(f"📁 File: {output_path}")
                                    print(f"📊 Size: {len(content):,} bytes")
                                    await browser2.close()
                                    return
                                else:
                                    print("Response is not a PDF")
                    
                    print("❌ All methods failed in fresh context")
                else:
                    print("❌ No PDF button in fresh context - authentication not transferred")
                
                print("\nBrowser staying open for 30 seconds...")
                await page2.wait_for_timeout(30000)
                await browser2.close()
            else:
                print("❌ Authentication failed - no PDF button")
                await browser1.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await browser1.close()
            except:
                pass
            try:
                await browser2.close()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(test_ieee_fresh_context())