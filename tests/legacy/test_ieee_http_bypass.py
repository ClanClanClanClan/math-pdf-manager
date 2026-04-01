#!/usr/bin/env python3
"""
IEEE HTTP Bypass Test
This bypasses the browser environment entirely by using direct HTTP requests
with authenticated session cookies.
"""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

import aiohttp

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ieee_http_bypass():
    """
    Ultimate bypass: Get authenticated cookies via browser,
    then use direct HTTP to download PDF.
    """
    
    test_doi = "10.1109/JPROC.2018.2820126"
    output_path = Path(f"ieee_http_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🎯 IEEE HTTP BYPASS TEST")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Output: {output_path}")
    print()
    print("Strategy:")
    print("1. Authenticate normally in browser")
    print("2. Extract all cookies and session data")
    print("3. Close browser completely") 
    print("4. Use aiohttp with cookies to download PDF")
    print("5. This bypasses ALL browser detection!")
    print()
    
    async with async_playwright() as p:
        # Use standard browser for authentication only
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
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
            
            # Extract arnumber from URL
            arnumber = None
            if '/document/' in page.url:
                arnumber = page.url.split('/document/')[-1].strip('/')
                print(f"📄 Extracted arnumber: {arnumber}")
            
            # Accept cookies
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # Check if already authenticated
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            
            if not pdf_button:
                print(f"\n🔐 PERFORMING AUTHENTICATION")
                print("-" * 50)
                
                # Click institutional sign in
                login_btn = await page.wait_for_selector('a.inst-sign-in', timeout=10000)
                await login_btn.click()
                print("✅ Clicked institutional sign in")
                await page.wait_for_timeout(3000)
                
                # Click SeamlessAccess
                seamless_btn = await page.wait_for_selector(
                    'button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn',
                    timeout=10000
                )
                await seamless_btn.click()
                print("✅ Clicked SeamlessAccess")
                await page.wait_for_timeout(3000)
                
                # Search for ETH
                search_input = await page.wait_for_selector('input.inst-typeahead-input', timeout=10000)
                await search_input.fill("ETH Zurich")
                print("✅ Entered ETH Zurich")
                await page.wait_for_timeout(3000)
                
                # Try to select ETH
                eth_selected = False
                selectors = [
                    'a[id="ETH Zurich - ETH Zurich"]',
                    'a:has-text("ETH Zurich")',
                    'li.inst-result:first-child a'
                ]
                
                for selector in selectors:
                    try:
                        eth_option = await page.wait_for_selector(selector, timeout=5000)
                        await eth_option.click()
                        print(f"✅ Selected ETH using: {selector}")
                        eth_selected = True
                        break
                    except:
                        continue
                
                if not eth_selected:
                    print("❌ Could not select ETH")
                    return
                
                await page.wait_for_timeout(8000)
                
                # ETH login
                if 'ethz.ch' in page.url.lower():
                    print("📍 At ETH login page")
                    
                    username_field = await page.wait_for_selector('input[name="j_username"]', timeout=10000)
                    await username_field.fill(username)
                    
                    password_field = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                    await password_field.fill(password)
                    
                    submit_btn = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                    await submit_btn.click()
                    print("✅ Submitted ETH credentials")
                    
                    await page.wait_for_timeout(15000)
                    
                    if 'ieeexplore.ieee.org' in page.url:
                        print("✅ Redirected back to IEEE")
                    else:
                        print(f"❌ Unexpected URL: {page.url}")
                        return
                else:
                    print(f"❌ Not at ETH login. URL: {page.url}")
                    return
                
                # Verify authentication
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    print("🎉 AUTHENTICATION SUCCESSFUL - PDF button found")
                else:
                    print("❌ Authentication may have failed - no PDF button")
                    return
            else:
                print("✅ Already authenticated - PDF button found")
            
            # Extract PDF URL from button
            pdf_href = await pdf_button.get_attribute('href')
            if pdf_href.startswith('/'):
                pdf_url = f"https://ieeexplore.ieee.org{pdf_href}"
            else:
                pdf_url = pdf_href
            
            print(f"📄 PDF URL: {pdf_url}")
            
            print(f"\n🍪 EXTRACTING SESSION DATA")
            print("-" * 50)
            
            # Get all cookies
            cookies = await context.cookies()
            ieee_cookies = [c for c in cookies if 'ieee' in c.get('domain', '').lower()]
            
            print(f"Total cookies: {len(cookies)}")
            print(f"IEEE cookies: {len(ieee_cookies)}")
            
            # Build cookie dict for aiohttp
            cookie_jar = {}
            for cookie in cookies:
                # Include all cookies, not just IEEE ones
                cookie_jar[cookie['name']] = cookie['value']
            
            # Get additional session info
            session_info = await page.evaluate("""
                () => {
                    return {
                        localStorage: JSON.stringify(localStorage),
                        sessionStorage: JSON.stringify(sessionStorage),
                        referrer: document.referrer,
                        userAgent: navigator.userAgent
                    };
                }
            """)
            
            # Get the current page URL as referrer
            referrer_url = page.url
            
            print(f"✅ Session data extracted")
            print(f"   Cookies: {len(cookie_jar)}")
            print(f"   Referrer: {referrer_url}")
            
            # Close browser - we don't need it anymore
            await browser.close()
            print("🔒 Browser closed")
            
            print(f"\n🌐 ATTEMPTING DIRECT HTTP DOWNLOAD")
            print("-" * 50)
            
            # Method 1: Direct stamp.jsp access
            print("Method 1: Direct stamp.jsp URL")
            
            headers = {
                'User-Agent': session_info['userAgent'] or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': referrer_url,
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1'
            }
            
            async with aiohttp.ClientSession(cookies=cookie_jar) as session:
                # Try stamp.jsp URL
                async with session.get(pdf_url, headers=headers, allow_redirects=True) as response:
                    print(f"Response status: {response.status}")
                    print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                    print(f"Content-Length: {response.headers.get('Content-Length', 'unknown')}")
                    
                    if response.status == 200:
                        content = await response.read()
                        
                        # Check if it's a PDF
                        if content[:4] == b'%PDF':
                            output_path.write_bytes(content)
                            print(f"✅ SUCCESS! PDF downloaded via stamp.jsp")
                            print(f"📁 Saved to: {output_path}")
                            print(f"📊 Size: {len(content):,} bytes")
                            return
                        else:
                            # It might be HTML with PDF embedded
                            print("Got HTML response, parsing for PDF URL...")
                            
                            # Try to find PDF URL in response
                            text = content.decode('utf-8', errors='ignore')
                            
                            # Look for PDF URL patterns
                            pdf_patterns = [
                                r'src="([^"]*\.pdf[^"]*)"',
                                r'href="([^"]*\.pdf[^"]*)"',
                                r'url\(([^)]*\.pdf[^)]*)\)',
                                r'getPDF\.jsp[^"\']*arnumber=\d+[^"\']*',
                                r'/stampPDF/getPDF\.jsp[^"\']*'
                            ]
                            
                            for pattern in pdf_patterns:
                                matches = re.findall(pattern, text)
                                if matches:
                                    print(f"Found PDF URL in HTML: {matches[0][:100]}")
                                    # Try to download the found PDF URL
                                    found_url = matches[0]
                                    if found_url.startswith('/'):
                                        found_url = f"https://ieeexplore.ieee.org{found_url}"
                                    
                                    async with session.get(found_url, headers=headers) as pdf_response:
                                        if pdf_response.status == 200:
                                            pdf_content = await pdf_response.read()
                                            if pdf_content[:4] == b'%PDF':
                                                output_path.write_bytes(pdf_content)
                                                print(f"✅ SUCCESS! PDF downloaded from embedded URL")
                                                print(f"📁 Saved to: {output_path}")
                                                print(f"📊 Size: {len(pdf_content):,} bytes")
                                                return
                
                # Method 2: Try getPDF.jsp endpoint
                if arnumber:
                    print(f"\nMethod 2: getPDF.jsp endpoint")
                    
                    get_pdf_urls = [
                        f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}&ref=",
                        f"https://ieeexplore.ieee.org/ielx7/5/8600701/{arnumber}.pdf",
                        f"https://ieeexplore.ieee.org/iel7/5/8600701/{arnumber}.pdf"
                    ]
                    
                    for get_pdf_url in get_pdf_urls:
                        print(f"Trying: {get_pdf_url}")
                        
                        async with session.get(get_pdf_url, headers=headers, allow_redirects=True) as response:
                            print(f"Response status: {response.status}")
                            
                            if response.status == 200:
                                content = await response.read()
                                if content[:4] == b'%PDF':
                                    output_path.write_bytes(content)
                                    print(f"✅ SUCCESS! PDF downloaded via getPDF")
                                    print(f"📁 Saved to: {output_path}")
                                    print(f"📊 Size: {len(content):,} bytes")
                                    return
                
                # Method 3: Try REST API
                print(f"\nMethod 3: REST API endpoint")
                
                api_url = f"https://ieeexplore.ieee.org/rest/document/{arnumber}/pdf"
                
                async with session.get(api_url, headers={**headers, 'Accept': 'application/pdf'}) as response:
                    print(f"Response status: {response.status}")
                    
                    if response.status == 200:
                        content = await response.read()
                        if content[:4] == b'%PDF':
                            output_path.write_bytes(content)
                            print(f"✅ SUCCESS! PDF downloaded via REST API")
                            print(f"📁 Saved to: {output_path}")
                            print(f"📊 Size: {len(content):,} bytes")
                            return
            
            print(f"\n❌ All HTTP methods failed")
            print(f"IEEE's protection is very sophisticated")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Make sure browser is closed
            try:
                await browser.close()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(test_ieee_http_bypass())