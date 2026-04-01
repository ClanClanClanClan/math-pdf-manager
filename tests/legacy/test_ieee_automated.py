#!/usr/bin/env python3
"""
Automated IEEE Test with Fixed Selectors
This test performs fully automated authentication and PDF download.
"""

import asyncio
import re
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_ieee_automated():
    """Fully automated IEEE test with updated selectors."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    output_path = Path(f"ieee_auto_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🚀 AUTOMATED IEEE TEST")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Output: {output_path}")
    print()
    
    async with async_playwright() as p:
        # Use Firefox with stealth settings
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
        
        # Apply stealth JavaScript
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Navigate to paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
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
                    print("✅ Accepted cookies")
            except:
                pass
            
            # Check if already authenticated
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            
            if not pdf_button:
                print(f"\n🔐 PERFORMING AUTHENTICATION")
                print("-" * 50)
                
                # Step 1: Click institutional sign in
                print("Step 1: Looking for institutional sign in...")
                
                login_selectors = [
                    'a.inst-sign-in',
                    'a:has-text("Institutional Sign In")',
                    'button:has-text("Institutional")',
                    'a[class*="institutional"]',
                    'button[class*="institutional"]'
                ]
                
                login_clicked = False
                for selector in login_selectors:
                    try:
                        login_btn = await page.wait_for_selector(selector, timeout=5000)
                        await login_btn.click()
                        print(f"✅ Clicked login using: {selector}")
                        login_clicked = True
                        break
                    except:
                        continue
                
                if not login_clicked:
                    print("❌ Could not find institutional sign in")
                    await browser.close()
                    return
                
                await page.wait_for_timeout(3000)
                
                # Step 2: Click SeamlessAccess button
                print("Step 2: Looking for SeamlessAccess button...")
                
                seamless_selectors = [
                    'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn',
                    'button:has-text("Access through your institution")',
                    'button:has-text("Access Through Your Institution")',
                    'button[class*="seamless"]',
                    'button[class*="access"]'
                ]
                
                seamless_clicked = False
                for selector in seamless_selectors:
                    try:
                        seamless_btn = await page.wait_for_selector(selector, timeout=5000)
                        await seamless_btn.click()
                        print(f"✅ Clicked SeamlessAccess using: {selector}")
                        seamless_clicked = True
                        break
                    except:
                        continue
                
                if not seamless_clicked:
                    print("❌ Could not find SeamlessAccess button")
                    await browser.close()
                    return
                
                await page.wait_for_timeout(3000)
                
                # Step 3: Search for ETH
                print("Step 3: Searching for ETH Zurich...")
                
                search_selectors = [
                    'input.inst-typeahead-input',
                    'input[placeholder*="institution"]',
                    'input[placeholder*="search"]',
                    'input[type="search"]',
                    'input.typeahead',
                    'input#searchInput'
                ]
                
                search_found = False
                for selector in search_selectors:
                    try:
                        search_input = await page.wait_for_selector(selector, timeout=5000)
                        await search_input.fill("ETH Zurich")
                        print(f"✅ Entered ETH Zurich using: {selector}")
                        search_found = True
                        break
                    except:
                        continue
                
                if not search_found:
                    print("❌ Could not find search input")
                    await browser.close()
                    return
                
                await page.wait_for_timeout(3000)
                
                # Step 4: Select ETH from results
                print("Step 4: Selecting ETH Zurich from results...")
                
                # Try multiple strategies
                eth_selected = False
                
                # Strategy 1: Look for ETH in dropdown/list
                eth_selectors = [
                    'a:has-text("ETH Zurich")',
                    'li:has-text("ETH Zurich")',
                    'div:has-text("ETH Zurich")',
                    '[data-institution*="ETH"]',
                    'button:has-text("ETH Zurich")'
                ]
                
                for selector in eth_selectors:
                    try:
                        # Get all matching elements
                        eth_elements = await page.query_selector_all(selector)
                        print(f"Found {len(eth_elements)} elements matching: {selector}")
                        
                        # Click the first visible one
                        for elem in eth_elements:
                            if await elem.is_visible():
                                await elem.click()
                                print(f"✅ Clicked ETH element")
                                eth_selected = True
                                break
                        
                        if eth_selected:
                            break
                    except:
                        continue
                
                # Strategy 2: If no click yet, try JavaScript click
                if not eth_selected:
                    print("Trying JavaScript click on ETH elements...")
                    
                    await page.evaluate("""
                        () => {
                            const elements = document.querySelectorAll('*');
                            for (let elem of elements) {
                                if (elem.textContent && elem.textContent.includes('ETH Zurich')) {
                                    elem.click();
                                    console.log('Clicked ETH element via JS');
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    
                    eth_selected = True
                    print("✅ Attempted JavaScript click on ETH")
                
                await page.wait_for_timeout(8000)
                
                # Step 5: ETH login
                if 'ethz.ch' in page.url.lower() or 'aai-logon' in page.url.lower():
                    print("✅ Reached ETH login page")
                    print(f"📍 ETH URL: {page.url}")
                    
                    # Fill credentials
                    username_selectors = [
                        'input[name="j_username"]',
                        'input[name="username"]',
                        'input[id="username"]',
                        'input[type="text"]'
                    ]
                    
                    for selector in username_selectors:
                        try:
                            username_field = await page.wait_for_selector(selector, timeout=5000)
                            await username_field.fill(username)
                            print(f"✅ Filled username using: {selector}")
                            break
                        except:
                            continue
                    
                    password_selectors = [
                        'input[name="j_password"]',
                        'input[name="password"]',
                        'input[id="password"]',
                        'input[type="password"]'
                    ]
                    
                    for selector in password_selectors:
                        try:
                            password_field = await page.wait_for_selector(selector, timeout=5000)
                            await password_field.fill(password)
                            print(f"✅ Filled password using: {selector}")
                            break
                        except:
                            continue
                    
                    # Submit
                    submit_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Login")',
                        'button:has-text("Sign in")'
                    ]
                    
                    for selector in submit_selectors:
                        try:
                            submit_btn = await page.wait_for_selector(selector, timeout=5000)
                            await submit_btn.click()
                            print(f"✅ Submitted credentials using: {selector}")
                            break
                        except:
                            continue
                    
                    # Wait for redirect
                    await page.wait_for_timeout(15000)
                    
                    if 'ieeexplore.ieee.org' in page.url:
                        print("✅ Successfully redirected back to IEEE")
                    else:
                        print(f"📍 Current URL after login: {page.url}")
                else:
                    print(f"⚠️  Not at ETH login. Current URL: {page.url}")
                
                # Check for PDF button again
                await page.wait_for_timeout(5000)
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                
                if pdf_button:
                    print("🎉 AUTHENTICATION SUCCESSFUL - PDF button found!")
                else:
                    print("⚠️  No PDF button after authentication")
            else:
                print("✅ PDF button already available")
            
            if pdf_button:
                # Get PDF URL
                pdf_href = await pdf_button.get_attribute('href')
                if pdf_href.startswith('/'):
                    pdf_url = f"https://ieeexplore.ieee.org{pdf_href}"
                else:
                    pdf_url = pdf_href
                
                print(f"📄 PDF URL: {pdf_url}")
                
                print(f"\n🎯 ATTEMPTING PDF DOWNLOAD")
                print("-" * 50)
                
                # Method 1: JavaScript override and click
                print("Method 1: JavaScript override + click")
                
                await page.evaluate("""
                    () => {
                        const pdfButton = document.querySelector('a[href*="/stamp/stamp.jsp"]');
                        if (pdfButton) {
                            // Remove all event listeners
                            const newButton = pdfButton.cloneNode(true);
                            pdfButton.parentNode.replaceChild(newButton, pdfButton);
                            
                            // Clear handlers
                            newButton.onclick = null;
                            newButton.onmousedown = null;
                            
                            // Override preventDefault
                            Event.prototype.preventDefault = function() {
                                if (this.target && this.target.href && this.target.href.includes('stamp.jsp')) {
                                    return;
                                }
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
                    print(f"✅ SUCCESS! Reached PDF viewer: {after_url}")
                    
                    # Try to download
                    download_selectors = [
                        'button[title*="Download"]',
                        'a[title*="Download"]',
                        'button:has-text("Download")',
                        'a:has-text("Download PDF")'
                    ]
                    
                    for selector in download_selectors:
                        try:
                            download_btn = await page.wait_for_selector(selector, timeout=5000)
                            async with page.expect_download() as download_info:
                                await download_btn.click()
                                download = await download_info.value
                                await download.save_as(output_path)
                                print(f"✅ PDF downloaded to: {output_path}")
                                await browser.close()
                                return
                        except:
                            continue
                    
                    print("⚠️  Could not find download button on PDF viewer")
                elif after_url != before_url:
                    print(f"⚠️  Navigation occurred but not to PDF: {after_url}")
                else:
                    print("❌ No navigation occurred")
                
                # Method 2: HTTP with cookies
                print("\nMethod 2: HTTP download with cookies")
                
                cookies = await context.cookies()
                cookie_jar = {}
                for cookie in cookies:
                    cookie_jar[cookie['name']] = cookie['value']
                
                print(f"🍪 Using {len(cookie_jar)} cookies")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Referer': page.url
                }
                
                async with aiohttp.ClientSession(cookies=cookie_jar) as session:
                    async with session.get(pdf_url, headers=headers) as response:
                        if response.status == 200:
                            content = await response.read()
                            if content[:4] == b'%PDF':
                                output_path.write_bytes(content)
                                print(f"✅ PDF downloaded via HTTP to: {output_path}")
                                print(f"📊 Size: {len(content):,} bytes")
                                await browser.close()
                                return
                            else:
                                print("❌ Response is not a PDF")
                
                print("❌ All download methods failed")
            else:
                print("❌ No PDF button available")
            
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_ieee_automated())