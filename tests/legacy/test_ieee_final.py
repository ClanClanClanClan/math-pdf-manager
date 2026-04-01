#!/usr/bin/env python3
"""
IEEE Final Test with Search Triggering
This test properly triggers the institution search and waits for results.
"""

import asyncio
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_ieee_final():
    """Final IEEE test with proper search triggering."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    output_path = Path(f"ieee_final_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🎯 IEEE FINAL TEST")
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
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Apply stealth
        await page.add_init_script("""
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
            
            # Step 3: Fill search and trigger it properly
            print("Step 3: Searching for ETH Zurich...")
            search_input = await page.query_selector('input.inst-typeahead-input')
            
            # Clear any existing text first
            await search_input.click()
            await search_input.fill("")  # Clear the field completely
            await page.wait_for_timeout(500)
            await search_input.type("ETH Zurich")
            print("✅ Typed ETH Zurich")
            
            # Wait for results to appear
            await page.wait_for_timeout(2000)
            
            # Try pressing Enter to trigger search
            await search_input.press('Enter')
            print("✅ Pressed Enter")
            await page.wait_for_timeout(2000)
            
            # Look for results that appeared
            print("Looking for ETH results...")
            
            # Check for dropdown/list results
            result_containers = [
                '.typeahead-results',
                '.inst-results',
                '.dropdown-menu',
                '.results',
                'ul[role="listbox"]',
                '[class*="result"]',
                '[class*="dropdown"]'
            ]
            
            results_found = False
            for container_selector in result_containers:
                try:
                    container = await page.query_selector(container_selector)
                    if container and await container.is_visible():
                        print(f"✅ Found results container: {container_selector}")
                        
                        # Look for ETH in this container
                        eth_links = await container.query_selector_all('a, li, div')
                        for link in eth_links:
                            text = await link.text_content()
                            if text and 'ETH' in text and 'Zurich' in text:
                                print(f"✅ Found ETH option: {text.strip()}")
                                await link.click()
                                print("✅ Clicked ETH option")
                                results_found = True
                                break
                        
                        if results_found:
                            break
                except:
                    continue
            
            if not results_found:
                # Try typing more slowly to trigger autocomplete
                print("Trying slower typing...")
                await search_input.click()
                await search_input.fill("")  # Clear the field completely first
                await page.wait_for_timeout(500)
                
                # Type character by character
                for char in "ETH Zurich":
                    await search_input.type(char)
                    await page.wait_for_timeout(200)
                
                await page.wait_for_timeout(3000)
                
                # Look for any clickable elements containing ETH
                all_elements = await page.query_selector_all('*')
                for elem in all_elements:
                    try:
                        if await elem.is_visible():
                            text = await elem.text_content()
                            if text and 'ETH Zurich' in text and len(text.strip()) < 100:
                                tag_name = await elem.evaluate('el => el.tagName')
                                if tag_name in ['A', 'LI', 'DIV', 'BUTTON']:
                                    print(f"✅ Found ETH element: {text.strip()}")
                                    await elem.click()
                                    print("✅ Clicked ETH element")
                                    results_found = True
                                    break
                    except:
                        pass
                    
                    if results_found:
                        break
            
            if not results_found:
                print("❌ Could not find or select ETH Zurich")
                print("⏸️  Browser will stay open for manual completion...")
                print("Please manually:")
                print("1. Select ETH Zurich from the dropdown")
                print("2. Complete the authentication")  
                print("3. Wait for PDF button to appear")
                print("The test will continue automatically...")
                
                # Wait for manual authentication
                authenticated = False
                for i in range(60):  # 5 minutes
                    await page.wait_for_timeout(5000)
                    pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                    if pdf_button:
                        print("🎉 AUTHENTICATION SUCCESSFUL - PDF button detected!")
                        authenticated = True
                        break
                    print(f"Waiting for authentication... ({i+1}/60)")
                
                if not authenticated:
                    print("❌ Authentication timeout")
                    await browser.close()
                    return
            else:
                # Automated flow continued
                await page.wait_for_timeout(8000)
                
                # Check if we're at ETH login
                if 'ethz.ch' in page.url.lower() or 'aai' in page.url.lower():
                    print("✅ Reached ETH login page")
                    
                    # Fill credentials
                    username_field = await page.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                    if username_field:
                        await username_field.fill(username)
                        print("✅ Filled username")
                    
                    password_field = await page.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                    if password_field:
                        await password_field.fill(password)
                        print("✅ Filled password")
                    
                    # Submit
                    submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                    if submit_btn:
                        await submit_btn.click()
                        print("✅ Submitted credentials")
                        
                        # Wait for redirect
                        await page.wait_for_timeout(15000)
                
                # Check for PDF button
                await page.wait_for_timeout(5000)
            
            # Test PDF access
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            if pdf_button:
                print(f"\n🎯 TESTING PDF ACCESS")
                print("-" * 50)
                
                pdf_href = await pdf_button.get_attribute('href')
                if pdf_href.startswith('/'):
                    pdf_url = f"https://ieeexplore.ieee.org{pdf_href}"
                else:
                    pdf_url = pdf_href
                
                print(f"📄 PDF URL: {pdf_url}")
                
                # Method 1: JavaScript override
                print("\nMethod 1: JavaScript override")
                await page.evaluate("""
                    () => {
                        // Ultra-comprehensive override
                        const pdfButton = document.querySelector('a[href*="/stamp/stamp.jsp"]');
                        if (pdfButton) {
                            // Remove all listeners
                            const newButton = pdfButton.cloneNode(true);
                            pdfButton.parentNode.replaceChild(newButton, pdfButton);
                            
                            // Clear handlers
                            newButton.onclick = null;
                            newButton.onmousedown = null;
                            newButton.onmouseup = null;
                            
                            // Override all event prevention
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
                            
                            // Force link behavior
                            newButton.addEventListener('click', function(e) {
                                window.location.href = this.href;
                            });
                        }
                    }
                """)
                
                # Try click
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                before_url = page.url
                await pdf_button.click()
                await page.wait_for_timeout(8000)
                after_url = page.url
                
                if '/stamp/stamp.jsp' in after_url:
                    print("✅ SUCCESS! Reached PDF viewer")
                    
                    # Try download
                    try:
                        async with page.expect_download() as download_info:
                            download_btn = await page.query_selector('button[title*="Download"], a[title*="Download"], button:has-text("Download")')
                            if download_btn:
                                await download_btn.click()
                                download = await download_info.value
                                await download.save_as(output_path)
                                print(f"✅ PDF downloaded to: {output_path}")
                                await browser.close()
                                return
                    except:
                        pass
                
                # Method 2: HTTP download
                print("\nMethod 2: HTTP with authenticated cookies")
                
                cookies = await context.cookies()
                cookie_jar = {c['name']: c['value'] for c in cookies}
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Referer': page.url
                }
                
                print(f"Using {len(cookie_jar)} cookies for HTTP request")
                
                async with aiohttp.ClientSession(cookies=cookie_jar) as session:
                    # Try main PDF URL
                    async with session.get(pdf_url, headers=headers) as response:
                        if response.status == 200:
                            content = await response.read()
                            if content[:4] == b'%PDF':
                                output_path.write_bytes(content)
                                print(f"🎉 SUCCESS! PDF downloaded via HTTP")
                                print(f"📁 File: {output_path}")
                                print(f"📊 Size: {len(content):,} bytes")
                                await browser.close()
                                return
                            else:
                                print(f"Response is HTML, not PDF")
                        else:
                            print(f"HTTP response: {response.status}")
                    
                    # Try alternative URLs if arnumber available
                    if arnumber:
                        alt_urls = [
                            f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}&ref=",
                            f"https://ieeexplore.ieee.org/ielx7/5/8600701/{arnumber}.pdf"
                        ]
                        
                        for alt_url in alt_urls:
                            print(f"Trying: {alt_url}")
                            async with session.get(alt_url, headers=headers) as response:
                                if response.status == 200:
                                    content = await response.read()
                                    if content[:4] == b'%PDF':
                                        output_path.write_bytes(content)
                                        print(f"🎉 SUCCESS! PDF downloaded")
                                        print(f"📁 File: {output_path}")
                                        print(f"📊 Size: {len(content):,} bytes")
                                        await browser.close()
                                        return
                
                print("❌ All download methods failed")
            else:
                print("❌ No PDF button found after authentication")
            
            print(f"\nTest complete. Browser staying open for 30 seconds...")
            await page.wait_for_timeout(30000)
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_ieee_final())