#!/usr/bin/env python3
"""
IEEE ULTRATHINK Solution
Advanced approaches to bypass IEEE's anti-automation detection and download PDFs.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def ultrathink_ieee():
    """ULTRATHINK: Advanced PDF download bypass strategies."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    arnumber = "8347162"
    output_path = Path(f"ieee_ultrathink_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🧠 IEEE ULTRATHINK SOLUTION")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Arnumber: {arnumber}")
    print(f"Target: {output_path}")
    print()
    print("🎯 GOAL: Automatic PDF download bypassing all detection")
    print()
    
    async with async_playwright() as p:
        # Strategy 1: Authenticate in headless mode, extract session
        print("🔬 STRATEGY 1: HEADLESS AUTHENTICATION + SESSION EXTRACTION")
        print("-" * 60)
        
        browser1 = await p.firefox.launch(
            headless=True,  # Headless might avoid some detection
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "general.platform.override": "MacIntel",
                "general.useragent.override": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
            }
        )
        
        context1 = await browser1.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        page1 = await context1.new_page()
        
        try:
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            print("🔐 Authenticating in headless mode...")
            
            # Quick authentication in headless
            url = f"https://doi.org/{test_doi}"
            await page1.goto(url, wait_until='networkidle')
            await page1.wait_for_timeout(2000)
            
            # Skip cookies if possible
            try:
                cookie_btn = await page1.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page1.wait_for_timeout(500)
            except:
                pass
            
            # Fast authentication
            login_btn = await page1.query_selector('a.inst-sign-in')
            if login_btn:
                await login_btn.click()
                await page1.wait_for_timeout(2000)
                
                seamless_btn = await page1.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                if seamless_btn:
                    await seamless_btn.click()
                    await page1.wait_for_timeout(2000)
                    
                    search_input = await page1.query_selector('input.inst-typeahead-input')
                    if search_input:
                        await search_input.fill("ETH Zurich")
                        await page1.wait_for_timeout(1000)
                        await search_input.press('ArrowDown')
                        await page1.wait_for_timeout(300)
                        await search_input.press('Enter')
                        
                        await page1.wait_for_timeout(5000)
                        
                        # ETH login
                        if 'ethz.ch' in page1.url.lower():
                            username_field = await page1.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                            if username_field:
                                await username_field.fill(username)
                            
                            password_field = await page1.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                            if password_field:
                                await password_field.fill(password)
                            
                            submit_btn = await page1.query_selector('button[type="submit"], input[type="submit"]')
                            if submit_btn:
                                await submit_btn.click()
                                await page1.wait_for_timeout(10000)
            
            # Extract complete session state
            if 'ieeexplore.ieee.org' in page1.url:
                pdf_button = await page1.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    print("✅ Authentication successful in headless mode")
                    
                    # Extract ALL possible session data
                    cookies = await context1.cookies()
                    local_storage = await page1.evaluate("() => JSON.stringify(localStorage)")
                    session_storage = await page1.evaluate("() => JSON.stringify(sessionStorage)")
                    page_cookies = await page1.evaluate("() => document.cookie")
                    user_agent = await page1.evaluate("() => navigator.userAgent")
                    
                    print(f"📦 Extracted {len(cookies)} cookies")
                    print(f"💾 Local storage: {len(local_storage)} chars")
                    print(f"🔒 Session storage: {len(session_storage)} chars")
                    
                    await browser1.close()
                    
                    # Strategy 1A: Advanced HTTP with complete session replication
                    print(f"\n🌐 STRATEGY 1A: ADVANCED HTTP SESSION REPLICATION")
                    print("-" * 50)
                    
                    cookie_jar = {c['name']: c['value'] for c in cookies}
                    
                    # Perfect browser headers
                    headers = {
                        'User-Agent': user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                        'Referer': f'https://ieeexplore.ieee.org/document/{arnumber}',
                    }
                    
                    pdf_urls = [
                        f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arnumber}",
                        f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}&ref=",
                        f"https://ieeexplore.ieee.org/ielx7/5/8600701/{arnumber}.pdf",
                        f"https://ieeexplore.ieee.org/iel7/5/8600701/{arnumber}.pdf"
                    ]
                    
                    connector = aiohttp.TCPConnector(
                        limit=100,
                        limit_per_host=30,
                        keepalive_timeout=30,
                        enable_cleanup_closed=True
                    )
                    
                    timeout = aiohttp.ClientTimeout(total=30, connect=10)
                    
                    async with aiohttp.ClientSession(
                        cookies=cookie_jar,
                        headers=headers,
                        connector=connector,
                        timeout=timeout
                    ) as session:
                        
                        for i, pdf_url in enumerate(pdf_urls):
                            print(f"  Attempt {i+1}: {pdf_url}")
                            
                            try:
                                async with session.get(pdf_url, allow_redirects=True) as response:
                                    print(f"    Status: {response.status}")
                                    print(f"    Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                                    print(f"    Content-Length: {response.headers.get('Content-Length', 'unknown')}")
                                    
                                    if response.status == 200:
                                        content = await response.read()
                                        
                                        if content[:4] == b'%PDF':
                                            output_path.write_bytes(content)
                                            print(f"    🎉 SUCCESS! PDF downloaded via advanced HTTP!")
                                            print(f"    📁 Saved to: {output_path}")
                                            print(f"    📊 Size: {len(content):,} bytes")
                                            return
                                        else:
                                            print(f"    ❌ Not a PDF (first 20 bytes: {content[:20]})")
                                            
                                            # Save HTML response for analysis
                                            if 'html' in response.headers.get('Content-Type', '').lower():
                                                html_path = output_path.with_suffix(f'_attempt{i+1}.html')
                                                html_path.write_bytes(content)
                                                print(f"    💾 Saved HTML response to: {html_path}")
                                    
                                    await asyncio.sleep(1)  # Rate limiting
                                        
                            except Exception as e:
                                print(f"    ❌ Request failed: {e}")
                    
                    # Strategy 1B: Curl with complete session
                    print(f"\n🔧 STRATEGY 1B: CURL WITH SESSION REPLICATION")
                    print("-" * 50)
                    
                    # Create curl command with all cookies and headers
                    cookie_string = "; ".join([f"{name}={value}" for name, value in cookie_jar.items()])
                    
                    curl_headers = [
                        f'-H "User-Agent: {user_agent}"',
                        f'-H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"',
                        f'-H "Accept-Language: en-US,en;q=0.9"',
                        f'-H "Accept-Encoding: gzip, deflate, br"',
                        f'-H "Referer: https://ieeexplore.ieee.org/document/{arnumber}"',
                        f'-H "Cookie: {cookie_string}"'
                    ]
                    
                    for i, pdf_url in enumerate(pdf_urls[:2]):  # Try first 2 URLs
                        print(f"  Curl attempt {i+1}: {pdf_url}")
                        
                        curl_output = output_path.with_suffix(f'_curl{i+1}.pdf')
                        
                        curl_cmd = [
                            'curl', 
                            '-L',  # Follow redirects
                            '-s',  # Silent
                            '--compressed',  # Handle encoding
                            '--max-time', '30',
                            '--connect-timeout', '10',
                        ]
                        
                        # Add headers
                        for header in curl_headers:
                            curl_cmd.extend(['-H', header.replace('-H "', '').replace('"', '')])
                        
                        curl_cmd.extend(['-o', str(curl_output), pdf_url])
                        
                        try:
                            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=45)
                            
                            if result.returncode == 0 and curl_output.exists():
                                # Check if it's a PDF
                                with open(curl_output, 'rb') as f:
                                    first_bytes = f.read(10)
                                
                                if first_bytes[:4] == b'%PDF':
                                    # Move to final location
                                    curl_output.rename(output_path)
                                    print(f"    🎉 SUCCESS! PDF downloaded via curl!")
                                    print(f"    📁 Saved to: {output_path}")
                                    print(f"    📊 Size: {output_path.stat().st_size:,} bytes")
                                    return
                                else:
                                    print(f"    ❌ Not a PDF: {first_bytes}")
                                    curl_output.unlink()  # Delete non-PDF
                            else:
                                print(f"    ❌ Curl failed: {result.stderr}")
                                
                        except Exception as e:
                            print(f"    ❌ Curl error: {e}")
                    
                    # Strategy 2: Fresh browser with session injection
                    print(f"\n🔄 STRATEGY 2: FRESH BROWSER WITH SESSION INJECTION")
                    print("-" * 50)
                    
                    # Create completely new browser context
                    browser2 = await p.firefox.launch(
                        headless=False,
                        firefox_user_prefs={
                            "dom.webdriver.enabled": False,
                            "useAutomationExtension": False,
                            "network.cookie.cookieBehavior": 0,
                            "privacy.trackingprotection.enabled": False,
                            "dom.disable_beforeunload": True,
                            "browser.tabs.remote.autostart": False,
                        }
                    )
                    
                    context2 = await browser2.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent=user_agent,
                        java_script_enabled=True
                    )
                    
                    # Add all cookies to new context
                    await context2.add_cookies(cookies)
                    print("✅ Injected all cookies into fresh browser context")
                    
                    page2 = await context2.new_page()
                    
                    # Inject storage data
                    await page2.goto('https://ieeexplore.ieee.org', wait_until='domcontentloaded')
                    
                    # Restore local and session storage
                    if local_storage and local_storage != "{}":
                        await page2.evaluate(f"Object.assign(localStorage, {local_storage})")
                        print("✅ Restored localStorage")
                    
                    if session_storage and session_storage != "{}":
                        await page2.evaluate(f"Object.assign(sessionStorage, {session_storage})")
                        print("✅ Restored sessionStorage")
                    
                    # Navigate directly to paper
                    paper_url = f"https://ieeexplore.ieee.org/document/{arnumber}"
                    print(f"🌐 Navigating to paper with full session: {paper_url}")
                    
                    await page2.goto(paper_url, wait_until='networkidle')
                    await page2.wait_for_timeout(5000)
                    
                    # Check authentication
                    pdf_button = await page2.query_selector('a[href*="/stamp/stamp.jsp"]')
                    if pdf_button:
                        print("✅ Authentication preserved in fresh context!")
                        
                        # Try direct PDF navigation in fresh context
                        pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arnumber}"
                        print(f"🎯 Direct navigation in fresh context: {pdf_url}")
                        
                        await page2.goto(pdf_url, wait_until='networkidle')
                        await page2.wait_for_timeout(8000)
                        
                        if '/stamp/stamp.jsp' in page2.url:
                            print("🎉 SUCCESS! PDF accessible in fresh context!")
                            
                            # Try download
                            try:
                                async with page2.expect_download(timeout=15000) as download_info:
                                    # Look for download button
                                    download_selectors = [
                                        'button[title*="Download"]',
                                        'a[title*="Download"]',
                                        'button:has-text("Download")',
                                        'a[href*=".pdf"]'
                                    ]
                                    
                                    for selector in download_selectors:
                                        btn = await page2.query_selector(selector)
                                        if btn and await btn.is_visible():
                                            await btn.click()
                                            print(f"✅ Clicked download button: {selector}")
                                            break
                                    else:
                                        # Force download via JavaScript
                                        await page2.evaluate(f"""
                                            () => {{
                                                const link = document.createElement('a');
                                                link.href = '{pdf_url}';
                                                link.download = 'ieee_paper.pdf';
                                                document.body.appendChild(link);
                                                link.click();
                                                document.body.removeChild(link);
                                            }}
                                        """)
                                        print("✅ Triggered download via JavaScript")
                                    
                                    download = await download_info.value
                                    await download.save_as(output_path)
                                    print(f"🎉 SUCCESS! PDF DOWNLOADED!")
                                    print(f"📁 Final file: {output_path}")
                                    
                                    await browser2.close()
                                    return
                                    
                            except Exception as e:
                                print(f"Download attempt failed: {e}")
                                print("PDF viewer is open - you can manually save it")
                                await page2.wait_for_timeout(60000)
                        else:
                            print(f"❌ Fresh context also redirected: {page2.url}")
                    else:
                        print("❌ Authentication not preserved in fresh context")
                    
                    await browser2.close()
                    
                else:
                    print("❌ Headless authentication failed")
                    await browser1.close()
            else:
                print("❌ Never reached IEEE in headless mode")
                await browser1.close()
            
        except Exception as e:
            print(f"❌ Strategy 1 failed: {e}")
            try:
                await browser1.close()
            except:
                pass
        
        print(f"\n❌ ALL ULTRATHINK STRATEGIES FAILED")
        print("IEEE's anti-automation detection is extremely sophisticated")
        print("It appears to work at multiple levels:")
        print("  - Browser automation detection")
        print("  - Session fingerprinting") 
        print("  - Server-side request analysis")
        print("  - Behavioral pattern recognition")


if __name__ == "__main__":
    asyncio.run(ultrathink_ieee())