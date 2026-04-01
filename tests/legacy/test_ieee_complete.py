#!/usr/bin/env python3
"""
IEEE Complete Test - Authentication + PDF Download
Uses keyboard navigation for authentication and multiple methods for PDF download.
"""

import asyncio
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_ieee_complete():
    """Complete IEEE test with working authentication and PDF download attempts."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    output_path = Path(f"ieee_complete_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🎯 IEEE COMPLETE TEST - AUTHENTICATION + PDF DOWNLOAD")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Output: {output_path}")
    print()
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "pdfjs.disabled": True,  # Disable PDF viewer
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True
        )
        
        page = await context.new_page()
        
        # Maximum stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Navigate to paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            print(f"📍 Current URL: {page.url}")
            
            # Extract arnumber
            arnumber = None
            if '/document/' in page.url:
                arnumber = page.url.split('/document/')[-1].strip('/')
                print(f"📄 Arnumber: {arnumber}")
            
            # Accept cookies
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            print(f"\n🔐 PERFORMING AUTHENTICATION")
            print("-" * 50)
            
            # Step 1: Click institutional sign in
            print("Step 1: Clicking institutional sign in...")
            login_btn = await page.query_selector('a.inst-sign-in')
            await login_btn.click()
            print("✅ Clicked institutional sign in")
            await page.wait_for_timeout(3000)
            
            # Step 2: Click SeamlessAccess
            print("Step 2: Clicking SeamlessAccess...")
            seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            await seamless_btn.click()
            print("✅ Clicked SeamlessAccess")
            await page.wait_for_timeout(3000)
            
            # Step 3: Type ETH Zurich with keyboard navigation
            print("Step 3: Searching for ETH Zurich...")
            search_input = await page.query_selector('input.inst-typeahead-input')
            
            # Clear and type
            await search_input.click()
            await search_input.fill("")
            await page.wait_for_timeout(500)
            
            # Type slowly
            for char in "ETH Zurich":
                await search_input.type(char)
                await page.wait_for_timeout(100)
            
            print("✅ Typed ETH Zurich")
            await page.wait_for_timeout(2000)
            
            # Use keyboard to select
            print("Step 4: Using keyboard to select ETH...")
            await search_input.press('ArrowDown')
            await page.wait_for_timeout(500)
            await search_input.press('Enter')
            print("✅ Selected ETH Zurich")
            
            await page.wait_for_timeout(8000)
            
            # Step 5: ETH authentication
            if 'ethz.ch' in page.url.lower() or 'aai' in page.url.lower():
                print("Step 5: Authenticating at ETH...")
                print(f"📍 ETH URL: {page.url}")
                
                username_field = await page.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                if username_field:
                    await username_field.fill(username)
                    print("✅ Filled username")
                
                password_field = await page.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                if password_field:
                    await password_field.fill(password)
                    print("✅ Filled password")
                
                submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_btn:
                    await submit_btn.click()
                    print("✅ Submitted credentials")
                    
                    await page.wait_for_timeout(15000)
                    
                    if 'ieeexplore.ieee.org' in page.url:
                        print("✅ Successfully authenticated and returned to IEEE")
            
            # Check for PDF button
            await page.wait_for_timeout(5000)
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            
            if not pdf_button:
                print("❌ No PDF button found after authentication")
                await browser.close()
                return
            
            print("🎉 AUTHENTICATION SUCCESSFUL - PDF button available!")
            
            # Get PDF URL
            pdf_href = await pdf_button.get_attribute('href')
            if pdf_href.startswith('/'):
                pdf_url = f"https://ieeexplore.ieee.org{pdf_href}"
            else:
                pdf_url = pdf_href
            
            print(f"📄 PDF URL: {pdf_url}")
            
            print(f"\n📥 ATTEMPTING PDF DOWNLOAD")
            print("-" * 50)
            
            # Method 1: JavaScript injection + click
            print("\nMethod 1: JavaScript injection to override blocks")
            await page.evaluate("""
                () => {
                    // Ultra-comprehensive override
                    const pdfButton = document.querySelector('a[href*="/stamp/stamp.jsp"]');
                    if (pdfButton) {
                        // Remove all listeners
                        const newButton = pdfButton.cloneNode(true);
                        pdfButton.parentNode.replaceChild(newButton, pdfButton);
                        
                        // Clear all handlers
                        newButton.onclick = null;
                        newButton.onmousedown = null;
                        newButton.onmouseup = null;
                        
                        // Override preventDefault and stopPropagation
                        const originalPreventDefault = Event.prototype.preventDefault;
                        const originalStopPropagation = Event.prototype.stopPropagation;
                        
                        Event.prototype.preventDefault = function() {
                            if (this.target && this.target.href && this.target.href.includes('stamp')) {
                                console.log('Blocked preventDefault for PDF');
                                return;
                            }
                            return originalPreventDefault.call(this);
                        };
                        
                        Event.prototype.stopPropagation = function() {
                            if (this.target && this.target.href && this.target.href.includes('stamp')) {
                                console.log('Blocked stopPropagation for PDF');
                                return;
                            }
                            return originalStopPropagation.call(this);
                        };
                    }
                }
            """)
            
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            before_url = page.url
            
            await pdf_button.click()
            await page.wait_for_timeout(8000)
            
            after_url = page.url
            
            if '/stamp/stamp.jsp' in after_url:
                print("✅ SUCCESS! Reached PDF viewer")
                
                # Try to download from viewer
                try:
                    async with page.expect_download(timeout=10000) as download_info:
                        download_btn = await page.query_selector('button[title*="Download"], a[title*="Download"], button:has-text("Download")')
                        if download_btn:
                            await download_btn.click()
                            download = await download_info.value
                            await download.save_as(output_path)
                            print(f"✅ PDF DOWNLOADED SUCCESSFULLY!")
                            print(f"📁 Saved to: {output_path}")
                            await browser.close()
                            return
                except:
                    print("Download button not working")
            else:
                print(f"Navigation occurred but not to PDF: {after_url}")
            
            # Method 2: Direct navigation
            print("\nMethod 2: Direct navigation to PDF URL")
            await page.goto(pdf_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(8000)
            
            if '/stamp/stamp.jsp' in page.url:
                print("✅ Reached PDF viewer via direct navigation")
                
                try:
                    async with page.expect_download(timeout=10000) as download_info:
                        download_btn = await page.query_selector('button[title*="Download"], a[title*="Download"]')
                        if download_btn:
                            await download_btn.click()
                            download = await download_info.value
                            await download.save_as(output_path)
                            print(f"✅ PDF DOWNLOADED SUCCESSFULLY!")
                            print(f"📁 Saved to: {output_path}")
                            await browser.close()
                            return
                except:
                    pass
            
            # Method 3: HTTP download with cookies
            print("\nMethod 3: HTTP download with authenticated cookies")
            
            cookies = await context.cookies()
            cookie_jar = {c['name']: c['value'] for c in cookies}
            
            print(f"🍪 Using {len(cookie_jar)} cookies")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': page.url
            }
            
            async with aiohttp.ClientSession(cookies=cookie_jar) as session:
                # Try stamp.jsp URL
                async with session.get(pdf_url, headers=headers, allow_redirects=True) as response:
                    print(f"Response status: {response.status}")
                    
                    if response.status == 200:
                        content = await response.read()
                        
                        if content[:4] == b'%PDF':
                            output_path.write_bytes(content)
                            print(f"✅ PDF DOWNLOADED VIA HTTP!")
                            print(f"📁 Saved to: {output_path}")
                            print(f"📊 Size: {len(content):,} bytes")
                            await browser.close()
                            return
                        else:
                            print("Response is HTML, not PDF")
                            
                            # Try direct PDF URLs
                            if arnumber:
                                alt_urls = [
                                    f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}&ref=",
                                    f"https://ieeexplore.ieee.org/ielx7/5/8600701/{arnumber}.pdf",
                                    f"https://ieeexplore.ieee.org/iel7/5/8600701/{arnumber}.pdf"
                                ]
                                
                                for alt_url in alt_urls:
                                    print(f"Trying: {alt_url}")
                                    async with session.get(alt_url, headers=headers) as alt_response:
                                        if alt_response.status == 200:
                                            alt_content = await alt_response.read()
                                            if alt_content[:4] == b'%PDF':
                                                output_path.write_bytes(alt_content)
                                                print(f"✅ PDF DOWNLOADED VIA DIRECT URL!")
                                                print(f"📁 Saved to: {output_path}")
                                                print(f"📊 Size: {len(alt_content):,} bytes")
                                                await browser.close()
                                                return
                                            else:
                                                print(f"Status {alt_response.status}: Not a PDF")
            
            # Method 4: Force download via JavaScript
            print("\nMethod 4: Force download via JavaScript")
            await page.evaluate(f"""
                () => {{
                    const link = document.createElement('a');
                    link.href = '{pdf_url}';
                    link.download = 'ieee_paper.pdf';
                    link.click();
                }}
            """)
            
            await page.wait_for_timeout(5000)
            
            # Check if download started
            if output_path.exists():
                print(f"✅ PDF downloaded!")
                print(f"📁 File: {output_path}")
            else:
                print("❌ JavaScript download didn't work")
            
            print("\n❌ All download methods failed")
            print("IEEE appears to be blocking PDF access in automated browsers")
            print("\nBrowser staying open for manual download...")
            print("You can manually click the PDF button and download")
            await page.wait_for_timeout(60000)
            
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_ieee_complete())