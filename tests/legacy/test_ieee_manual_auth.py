#!/usr/bin/env python3
"""
IEEE Manual Authentication Test
This test lets you authenticate manually, then tests PDF download.
"""

import asyncio
import json
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_manual_auth():
    """Test with manual authentication."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    output_path = Path(f"ieee_manual_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🎯 IEEE MANUAL AUTHENTICATION TEST")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Output: {output_path}")
    print()
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
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
        
        print(f"\n{'='*70}")
        print("📋 MANUAL AUTHENTICATION REQUIRED")
        print(f"{'='*70}")
        print()
        print("Please manually authenticate in the browser:")
        print("1. Click 'Institutional Sign In'")
        print("2. Click 'Access through your institution'")
        print("3. Search for and select 'ETH Zurich'")
        print("4. Log in with your credentials")
        print("5. Wait to be redirected back to IEEE")
        print()
        print("The test will automatically detect when you're authenticated")
        print("(checking every 5 seconds for PDF button)")
        print()
        
        # Wait for authentication
        authenticated = False
        check_count = 0
        max_checks = 60  # 5 minutes maximum
        
        while not authenticated and check_count < max_checks:
            check_count += 1
            print(f"Checking for authentication... (attempt {check_count}/{max_checks})")
            
            # Check for PDF button
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            
            if pdf_button:
                print("✅ PDF button found - authentication successful!")
                authenticated = True
                break
            
            # Also check for sign out link
            sign_out = await page.query_selector('*:has-text("Sign Out")')
            if sign_out:
                print("✅ Sign Out link found - authenticated")
                # Wait a bit more for PDF button to appear
                await page.wait_for_timeout(3000)
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    authenticated = True
                    break
            
            await page.wait_for_timeout(5000)
        
        if not authenticated:
            print("❌ Authentication timeout - no PDF button found")
            await browser.close()
            return
        
        # Get PDF button href
        pdf_href = await pdf_button.get_attribute('href')
        if pdf_href.startswith('/'):
            pdf_url = f"https://ieeexplore.ieee.org{pdf_href}"
        else:
            pdf_url = pdf_href
        
        print(f"📄 PDF URL: {pdf_url}")
        
        print(f"\n{'='*70}")
        print("🔬 TESTING PDF ACCESS METHODS")
        print(f"{'='*70}")
        
        # Method 1: Try direct click with JavaScript override
        print("\n📌 Method 1: JavaScript Override + Click")
        print("-" * 40)
        
        await page.evaluate("""
            () => {
                // Remove all event listeners from PDF button
                const pdfButton = document.querySelector('a[href*="/stamp/stamp.jsp"]');
                if (pdfButton) {
                    // Clone to remove listeners
                    const newButton = pdfButton.cloneNode(true);
                    pdfButton.parentNode.replaceChild(newButton, pdfButton);
                    
                    // Remove handlers
                    newButton.onclick = null;
                    newButton.onmousedown = null;
                    newButton.onmouseup = null;
                    
                    // Make sure it's clickable
                    newButton.style.pointerEvents = 'auto';
                    newButton.style.cursor = 'pointer';
                }
                
                // Override preventDefault
                const originalPreventDefault = Event.prototype.preventDefault;
                Event.prototype.preventDefault = function() {
                    if (this.target && this.target.href && this.target.href.includes('/stamp/stamp.jsp')) {
                        console.log('Blocking preventDefault for PDF');
                        return;
                    }
                    return originalPreventDefault.call(this);
                };
            }
        """)
        
        # Try clicking
        pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
        before_url = page.url
        
        await pdf_button.click()
        await page.wait_for_timeout(5000)
        
        after_url = page.url
        
        if after_url != before_url:
            print(f"✅ Navigation occurred: {after_url}")
            if '/stamp/stamp.jsp' in after_url:
                print("🎉 SUCCESS - Reached PDF viewer!")
                
                # Try to download
                download_btn = await page.query_selector('button[title*="Download"], a[title*="Download"]')
                if download_btn:
                    try:
                        async with page.expect_download() as download_info:
                            await download_btn.click()
                            download = await download_info.value
                            await download.save_as(output_path)
                            print(f"✅ PDF downloaded to: {output_path}")
                            await browser.close()
                            return
                    except:
                        print("❌ Download failed")
        else:
            print("❌ No navigation occurred")
        
        # Method 2: Extract cookies and use HTTP
        print("\n📌 Method 2: HTTP with Cookies")
        print("-" * 40)
        
        # Get all cookies
        cookies = await context.cookies()
        print(f"🍪 Total cookies: {len(cookies)}")
        
        # Build cookie jar
        cookie_jar = {}
        for cookie in cookies:
            cookie_jar[cookie['name']] = cookie['value']
        
        # Get user agent
        user_agent = await page.evaluate("() => navigator.userAgent")
        
        print("📡 Making HTTP request with cookies...")
        
        # Close browser - we don't need it anymore
        await browser.close()
        print("🔒 Browser closed")
        
        # Try HTTP download
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': before_url,
            'Cache-Control': 'no-cache'
        }
        
        async with aiohttp.ClientSession(cookies=cookie_jar) as session:
            # Try stamp.jsp URL
            async with session.get(pdf_url, headers=headers, allow_redirects=True) as response:
                print(f"Response status: {response.status}")
                print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                
                if response.status == 200:
                    content = await response.read()
                    
                    # Check if it's a PDF
                    if content[:4] == b'%PDF':
                        output_path.write_bytes(content)
                        print(f"✅ SUCCESS! PDF downloaded via HTTP")
                        print(f"📁 Saved to: {output_path}")
                        print(f"📊 Size: {len(content):,} bytes")
                        return
                    else:
                        print("❌ Response is not a PDF")
                        
                        # Try alternative URLs
                        if arnumber:
                            alt_urls = [
                                f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}&ref=",
                                f"https://ieeexplore.ieee.org/ielx7/5/8600701/{arnumber}.pdf"
                            ]
                            
                            for alt_url in alt_urls:
                                print(f"\nTrying: {alt_url}")
                                async with session.get(alt_url, headers=headers) as alt_response:
                                    if alt_response.status == 200:
                                        alt_content = await alt_response.read()
                                        if alt_content[:4] == b'%PDF':
                                            output_path.write_bytes(alt_content)
                                            print(f"✅ SUCCESS! PDF downloaded")
                                            print(f"📁 Saved to: {output_path}")
                                            return
                
                print("❌ All download methods failed")


if __name__ == "__main__":
    asyncio.run(test_manual_auth())