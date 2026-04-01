#!/usr/bin/env python3
"""
IEEE Direct PDF Test
Authenticate first, then navigate directly to stamp.jsp URL instead of clicking button.
"""

import asyncio
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_ieee_direct_pdf():
    """Test direct navigation to PDF after authentication."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    arnumber = "8347162"
    output_path = Path(f"ieee_direct_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🎯 IEEE DIRECT PDF ACCESS TEST")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Arnumber: {arnumber}")
    print(f"Output: {output_path}")
    print()
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "pdfjs.disabled": True,
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True
        )
        
        page = await context.new_page()
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Navigate to paper first for authentication
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Step 1: Navigating to paper for authentication: {url}")
            
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            print(f"📍 Current URL: {page.url}")
            
            # Accept cookies
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            print(f"\n🔐 STEP 2: PERFORMING AUTHENTICATION")
            print("-" * 50)
            
            # Authentication flow
            print("Clicking institutional sign in...")
            login_btn = await page.query_selector('a.inst-sign-in')
            await login_btn.click()
            await page.wait_for_timeout(3000)
            
            print("Clicking SeamlessAccess...")
            seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            await seamless_btn.click()
            await page.wait_for_timeout(3000)
            
            print("Searching for ETH Zurich...")
            search_input = await page.query_selector('input.inst-typeahead-input')
            await search_input.click()
            await search_input.fill("")
            await page.wait_for_timeout(500)
            
            for char in "ETH Zurich":
                await search_input.type(char)
                await page.wait_for_timeout(100)
            
            await page.wait_for_timeout(2000)
            
            # Use keyboard navigation
            await search_input.press('ArrowDown')
            await page.wait_for_timeout(500)
            await search_input.press('Enter')
            print("✅ Selected ETH Zurich")
            
            await page.wait_for_timeout(8000)
            
            # ETH login
            if 'ethz.ch' in page.url.lower() or 'aai' in page.url.lower():
                print("At ETH login page...")
                
                username_field = await page.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                if username_field:
                    await username_field.fill(username)
                
                password_field = await page.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                if password_field:
                    await password_field.fill(password)
                
                submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_btn:
                    await submit_btn.click()
                    await page.wait_for_timeout(15000)
                    print("✅ Authentication submitted")
            
            # Verify we're back at IEEE and authenticated
            if 'ieeexplore.ieee.org' in page.url:
                print("✅ Back at IEEE after authentication")
                
                # Check for PDF button to confirm authentication worked
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    print("✅ PDF button found - authentication successful!")
                else:
                    print("❌ No PDF button - authentication may have failed")
                    await browser.close()
                    return
            
            print(f"\n📄 STEP 3: DIRECT PDF ACCESS")
            print("-" * 50)
            
            # Direct navigation to PDF URL
            pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arnumber}"
            print(f"🎯 Navigating directly to PDF URL: {pdf_url}")
            
            await page.goto(pdf_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(8000)
            
            print(f"📍 Current URL after navigation: {page.url}")
            
            if '/stamp/stamp.jsp' in page.url:
                print("🎉 SUCCESS! Reached PDF viewer via direct navigation!")
                
                # Method 1: Try to download via download button
                print("\nMethod 1: Looking for download button...")
                download_selectors = [
                    'button[title*="Download"]',
                    'a[title*="Download"]', 
                    'button:has-text("Download")',
                    'a:has-text("Download")',
                    'button[aria-label*="download"]',
                    '.pdf-download-btn'
                ]
                
                download_success = False
                for selector in download_selectors:
                    try:
                        download_btn = await page.query_selector(selector)
                        if download_btn and await download_btn.is_visible():
                            print(f"Found download button: {selector}")
                            
                            async with page.expect_download(timeout=15000) as download_info:
                                await download_btn.click()
                                download = await download_info.value
                                await download.save_as(output_path)
                                print(f"✅ PDF DOWNLOADED SUCCESSFULLY!")
                                print(f"📁 Saved to: {output_path}")
                                download_success = True
                                break
                    except Exception as e:
                        print(f"Download attempt failed with {selector}: {e}")
                        continue
                
                if not download_success:
                    # Method 2: HTTP download from the stamp.jsp page
                    print("\nMethod 2: HTTP download of PDF content...")
                    
                    cookies = await context.cookies()
                    cookie_jar = {c['name']: c['value'] for c in cookies}
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'application/pdf,text/html,application/xhtml+xml,*/*',
                        'Referer': f"https://ieeexplore.ieee.org/document/{arnumber}"
                    }
                    
                    print(f"Making HTTP request to: {pdf_url}")
                    
                    async with aiohttp.ClientSession(cookies=cookie_jar) as session:
                        async with session.get(pdf_url, headers=headers) as response:
                            print(f"Response status: {response.status}")
                            print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                            
                            if response.status == 200:
                                content = await response.read()
                                
                                # Check if it's a PDF
                                if content[:4] == b'%PDF':
                                    output_path.write_bytes(content)
                                    print(f"✅ PDF DOWNLOADED VIA HTTP!")
                                    print(f"📁 Saved to: {output_path}")
                                    print(f"📊 Size: {len(content):,} bytes")
                                    download_success = True
                                else:
                                    print("Response is HTML, not PDF")
                                    # Save HTML to see what we got
                                    html_path = output_path.with_suffix('.html')
                                    html_path.write_bytes(content)
                                    print(f"Saved HTML response to: {html_path}")
                
                if not download_success:
                    # Method 3: Try to extract PDF from page content
                    print("\nMethod 3: Looking for PDF embed or iframe...")
                    
                    # Check for PDF embeds
                    pdf_embeds = await page.query_selector_all('embed[src*=".pdf"], iframe[src*=".pdf"], object[data*=".pdf"]')
                    for embed in pdf_embeds:
                        src = await embed.get_attribute('src') or await embed.get_attribute('data')
                        if src:
                            print(f"Found PDF embed: {src}")
                            if src.startswith('/'):
                                src = f"https://ieeexplore.ieee.org{src}"
                            
                            # Try to download the embedded PDF
                            async with aiohttp.ClientSession(cookies=cookie_jar) as session:
                                async with session.get(src, headers=headers) as response:
                                    if response.status == 200:
                                        content = await response.read()
                                        if content[:4] == b'%PDF':
                                            output_path.write_bytes(content)
                                            print(f"✅ PDF downloaded from embed!")
                                            download_success = True
                                            break
                
                if not download_success:
                    print("\n❌ Could not download PDF automatically")
                    print("The PDF viewer is open - you can manually save it")
                    print("Browser staying open for manual download...")
                    await page.wait_for_timeout(60000)
                
            else:
                print(f"❌ Did not reach PDF viewer. Current URL: {page.url}")
                print("Direct navigation to stamp.jsp was blocked or redirected")
            
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_ieee_direct_pdf())