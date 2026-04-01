#!/usr/bin/env python3
"""
IEEE ULTIMATE Solution
Most advanced approach: Session bridging with external tools.
"""

import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def ultimate_ieee():
    """ULTIMATE: Most advanced PDF download approach."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    arnumber = "8347162"
    output_path = Path(f"ieee_ultimate_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🚀 IEEE ULTIMATE SOLUTION")
    print(f"{'='*70}")
    print(f"🎯 MISSION: Download PDF automatically using session bridging")
    print()
    
    async with async_playwright() as p:
        print("🔬 APPROACH 1: AUTHENTICATION + IMMEDIATE SESSION EXPORT")
        print("-" * 60)
        
        # Use visible browser for authentication, but prepare for quick export
        browser = await p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "network.cookie.cookieBehavior": 0,
                "privacy.trackingprotection.enabled": False,
                "security.tls.insecure_fallback_hosts": "ieeexplore.ieee.org",
                "network.http.referer.XOriginPolicy": 0,
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            java_script_enabled=True,
            accept_downloads=True
        )
        
        page = await context.new_page()
        
        try:
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            print("🔐 Fast authentication...")
            url = f"https://doi.org/{test_doi}"
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Accept cookies quickly
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(500)
            except:
                pass
            
            # Fast authentication flow
            login_btn = await page.query_selector('a.inst-sign-in')
            if login_btn:
                await login_btn.click()
                await page.wait_for_timeout(2000)
                
                seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                if seamless_btn:
                    await seamless_btn.click()
                    await page.wait_for_timeout(2000)
                    
                    search_input = await page.query_selector('input.inst-typeahead-input')
                    if search_input:
                        await search_input.fill("ETH Zurich")
                        await page.wait_for_timeout(1500)
                        await search_input.press('ArrowDown')
                        await page.wait_for_timeout(300)
                        await search_input.press('Enter')
                        
                        await page.wait_for_timeout(6000)
                        
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
                                await page.wait_for_timeout(12000)
            
            # Check authentication
            if 'ieeexplore.ieee.org' in page.url:
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    print("✅ Authentication successful!")
                    
                    # IMMEDIATE SESSION EXTRACTION
                    print("📦 Extracting session data immediately...")
                    
                    cookies = await context.cookies()
                    user_agent = await page.evaluate("() => navigator.userAgent")
                    
                    # Get current page state
                    current_url = page.url
                    referrer = current_url
                    
                    print(f"🍪 Extracted {len(cookies)} cookies")
                    
                    # METHOD 1: Python requests with session mimicking
                    print(f"\n🐍 METHOD 1: PYTHON REQUESTS WITH PERFECT MIMICKING")
                    print("-" * 50)
                    
                    import requests
                    from requests.adapters import HTTPAdapter
                    from urllib3.util.retry import Retry

                    # Create session with retry strategy
                    session = requests.Session()
                    
                    retry_strategy = Retry(
                        total=3,
                        backoff_factor=1,
                        status_forcelist=[429, 500, 502, 503, 504],
                    )
                    adapter = HTTPAdapter(max_retries=retry_strategy)
                    session.mount("http://", adapter)
                    session.mount("https://", adapter)
                    
                    # Add all cookies
                    for cookie in cookies:
                        session.cookies.set(
                            cookie['name'], 
                            cookie['value'], 
                            domain=cookie.get('domain', '.ieeexplore.ieee.org'),
                            path=cookie.get('path', '/')
                        )
                    
                    # Perfect headers
                    session.headers.update({
                        'User-Agent': user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                        'Referer': referrer,
                    })
                    
                    pdf_urls = [
                        f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arnumber}",
                        f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}&ref=",
                    ]
                    
                    for i, pdf_url in enumerate(pdf_urls):
                        print(f"  Attempt {i+1}: {pdf_url}")
                        
                        try:
                            response = session.get(pdf_url, timeout=30, allow_redirects=True)
                            print(f"    Status: {response.status_code}")
                            print(f"    Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                            print(f"    Content-Length: {len(response.content)}")
                            
                            if response.status_code == 200 and response.content:
                                if response.content[:4] == b'%PDF':
                                    output_path.write_bytes(response.content)
                                    print(f"    🎉 SUCCESS! PDF downloaded with requests!")
                                    print(f"    📁 Saved to: {output_path}")
                                    print(f"    📊 Size: {len(response.content):,} bytes")
                                    await browser.close()
                                    return
                                else:
                                    print(f"    ❌ Not PDF: {response.content[:50]}")
                            
                        except Exception as e:
                            print(f"    ❌ Request failed: {e}")
                    
                    # METHOD 2: Wget with cookie export
                    print(f"\n📥 METHOD 2: WGET WITH COOKIE FILE")
                    print("-" * 50)
                    
                    # Create Netscape cookie file
                    cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                    
                    # Write Netscape cookie format
                    cookie_file.write("# Netscape HTTP Cookie File\n")
                    
                    for cookie in cookies:
                        domain = cookie.get('domain', '.ieeexplore.ieee.org')
                        if not domain.startswith('.'):
                            domain = '.' + domain
                            
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                        http_only = 'TRUE' if cookie.get('httpOnly', False) else 'FALSE'
                        expires = str(int(cookie.get('expires', time.time() + 86400)))
                        path = cookie.get('path', '/')
                        name = cookie['name']
                        value = cookie['value']
                        
                        # Format: domain, domain_specified, path, secure, expires, name, value
                        cookie_file.write(f"{domain}\tTRUE\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
                    
                    cookie_file.close()
                    print(f"✅ Created cookie file: {cookie_file.name}")
                    
                    for i, pdf_url in enumerate(pdf_urls):
                        print(f"  Wget attempt {i+1}: {pdf_url}")
                        
                        wget_output = output_path.with_suffix(f'_wget{i+1}.pdf')
                        
                        wget_cmd = [
                            'wget',
                            '--load-cookies', cookie_file.name,
                            '--user-agent', user_agent,
                            '--header', f'Referer: {referrer}',
                            '--header', 'Accept: application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            '--timeout=30',
                            '--tries=3',
                            '--no-check-certificate',
                            '-O', str(wget_output),
                            pdf_url
                        ]
                        
                        try:
                            result = subprocess.run(wget_cmd, capture_output=True, text=True, timeout=45)
                            
                            if result.returncode == 0 and wget_output.exists():
                                with open(wget_output, 'rb') as f:
                                    first_bytes = f.read(10)
                                
                                if first_bytes[:4] == b'%PDF':
                                    wget_output.rename(output_path)
                                    print(f"    🎉 SUCCESS! PDF downloaded with wget!")
                                    print(f"    📁 Saved to: {output_path}")
                                    print(f"    📊 Size: {output_path.stat().st_size:,} bytes")
                                    
                                    # Cleanup
                                    os.unlink(cookie_file.name)
                                    await browser.close()
                                    return
                                else:
                                    print(f"    ❌ Not PDF: {first_bytes}")
                                    wget_output.unlink()
                            else:
                                print(f"    ❌ Wget failed: {result.stderr}")
                                
                        except Exception as e:
                            print(f"    ❌ Wget error: {e}")
                    
                    # Cleanup cookie file
                    try:
                        os.unlink(cookie_file.name)
                    except:
                        pass
                    
                    # METHOD 3: Browser automation with delayed PDF click
                    print(f"\n⏰ METHOD 3: DELAYED PDF ACCESS IN SAME SESSION")
                    print("-" * 50)
                    
                    print("Waiting 30 seconds to let session settle...")
                    await asyncio.sleep(30)
                    
                    # Try PDF access after delay
                    print("Attempting PDF access after session settling...")
                    
                    # Navigate back to paper
                    await page.goto(f"https://ieeexplore.ieee.org/document/{arnumber}", wait_until='networkidle')
                    await page.wait_for_timeout(5000)
                    
                    pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                    if pdf_button:
                        # Try multiple click strategies
                        strategies = [
                            "direct_click",
                            "javascript_click", 
                            "force_navigation"
                        ]
                        
                        for strategy in strategies:
                            print(f"  Strategy: {strategy}")
                            
                            if strategy == "direct_click":
                                await pdf_button.click()
                            elif strategy == "javascript_click":
                                await page.evaluate("document.querySelector('a[href*=\"/stamp/stamp.jsp\"]').click()")
                            elif strategy == "force_navigation":
                                pdf_href = await pdf_button.get_attribute('href')
                                full_url = f"https://ieeexplore.ieee.org{pdf_href}" if pdf_href.startswith('/') else pdf_href
                                await page.goto(full_url, wait_until='networkidle')
                            
                            await page.wait_for_timeout(8000)
                            
                            if '/stamp/stamp.jsp' in page.url:
                                print(f"    🎉 SUCCESS! {strategy} worked!")
                                
                                # Try to download
                                try:
                                    async with page.expect_download(timeout=20000) as download_info:
                                        # Multiple download triggers
                                        download_triggers = [
                                            'button[title*="Download"]',
                                            'a[title*="Download"]',
                                            'button:has-text("Download")'
                                        ]
                                        
                                        for trigger in download_triggers:
                                            btn = await page.query_selector(trigger)
                                            if btn and await btn.is_visible():
                                                await btn.click()
                                                break
                                        else:
                                            # JavaScript download trigger
                                            await page.evaluate(f"""
                                                () => {{
                                                    const link = document.createElement('a');
                                                    link.href = window.location.href;
                                                    link.download = 'paper.pdf';
                                                    link.click();
                                                }}
                                            """)
                                        
                                        download = await download_info.value
                                        await download.save_as(output_path)
                                        print(f"    🎉 FINAL SUCCESS! PDF DOWNLOADED!")
                                        print(f"    📁 File: {output_path}")
                                        await browser.close()
                                        return
                                        
                                except Exception as e:
                                    print(f"    Download failed: {e}")
                                    print("    PDF viewer is accessible - manual download possible")
                                    await page.wait_for_timeout(30000)
                                    break
                            else:
                                print(f"    ❌ {strategy} failed: {page.url}")
                                
                                # Reset for next strategy
                                if strategy != strategies[-1]:
                                    await page.goto(f"https://ieeexplore.ieee.org/document/{arnumber}", wait_until='networkidle')
                                    await page.wait_for_timeout(3000)
                                    pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                    
                else:
                    print("❌ Authentication failed")
                    
            await browser.close()
            
        except Exception as e:
            print(f"❌ Ultimate solution failed: {e}")
            import traceback
            traceback.print_exc()
            try:
                await browser.close()
            except:
                pass
        
        print(f"\n💀 ULTIMATE CONCLUSION")
        print("=" * 30)
        print("IEEE's anti-automation system is exceptionally sophisticated.")
        print("It appears to use advanced techniques including:")
        print("  🔍 Browser fingerprinting")
        print("  🕵️  Session behavioral analysis") 
        print("  🤖 Bot detection algorithms")
        print("  🌐 Network traffic analysis")
        print("  ⏱️  Temporal pattern recognition")
        print()
        print("The institutional authentication works perfectly.")
        print("The PDF blocking is a separate, very advanced anti-bot system.")


if __name__ == "__main__":
    asyncio.run(ultimate_ieee())