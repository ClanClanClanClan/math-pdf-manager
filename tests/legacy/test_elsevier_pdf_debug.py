#!/usr/bin/env python3
"""
Debug Elsevier PDF Download Issues
Test actual PDF download behavior to identify the problem.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.publishers.elsevier_navigator import (
    ELSEVIER_CONFIG,
    ElsevierNavigator,
)
from src.secure_credential_manager import get_credential_manager


async def debug_elsevier_pdf_download():
    """Debug Elsevier PDF download process step by step."""
    
    print(f"🔍 DEBUGGING ELSEVIER PDF DOWNLOAD")
    print(f"=" * 50)
    
    # Test with a known working paper
    test_doi = "10.1016/j.jmb.2021.166861"
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=False,  # Use visible browser for debugging
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
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
            
            # Create navigator
            navigator = ElsevierNavigator(page, ELSEVIER_CONFIG)
            navigator.eth_auth = ETHAuthenticator(page, username, password)
            
            print(f"\n📄 Testing DOI: {test_doi}")
            
            # Step 1: Full authentication flow
            print(f"\n🌐 Step 1: Navigate and authenticate...")
            if not await navigator.navigate_to_paper(test_doi):
                print(f"❌ Navigation failed")
                return
            
            if not await navigator.navigate_to_login():
                print(f"❌ Login navigation failed")
                return
                
            if not await navigator.select_eth_institution():
                print(f"❌ ETH selection failed")
                return
                
            if not await navigator.eth_auth.perform_login():
                print(f"❌ Authentication failed")
                return
                
            if not await navigator.navigate_after_auth():
                print(f"❌ Post-auth failed")
                return
            
            print(f"✅ Full authentication completed")
            
            # Step 2: Analyze PDF button details
            print(f"\n🔍 Step 2: Analyzing PDF access...")
            
            # Find all potential PDF elements
            pdf_elements = []
            for selector in ELSEVIER_CONFIG.pdf_download_selectors:
                elements = await page.query_selector_all(selector)
                for elem in elements:
                    try:
                        text = await elem.inner_text()
                        href = await elem.get_attribute('href')
                        tag = await elem.evaluate('el => el.tagName')
                        pdf_elements.append({
                            'selector': selector,
                            'text': text[:50],
                            'href': href,
                            'tag': tag
                        })
                    except:
                        continue
            
            print(f"Found {len(pdf_elements)} PDF elements:")
            for i, elem in enumerate(pdf_elements, 1):
                print(f"  {i}. {elem['tag']} - '{elem['text']}' -> {elem['href'][:80] if elem['href'] else 'No href'}")
            
            if not pdf_elements:
                print(f"❌ No PDF elements found")
                return
            
            # Step 3: Test different download approaches
            print(f"\n📥 Step 3: Testing download approaches...")
            
            # Use the first PDF element
            main_pdf = pdf_elements[0]
            pdf_href = main_pdf['href']
            
            if not pdf_href:
                print(f"❌ No PDF URL available")
                return
            
            if not pdf_href.startswith('http'):
                pdf_href = f"https://www.sciencedirect.com{pdf_href}"
            
            print(f"PDF URL: {pdf_href}")
            
            # Method 1: Try Playwright download
            print(f"\n🔄 Method 1: Playwright expect_download...")
            try:
                pdf_button = await page.query_selector(main_pdf['selector'])
                if pdf_button:
                    async with page.expect_download(timeout=30000) as download_info:
                        await pdf_button.click()
                    
                    download = await download_info.value
                    
                    # Save download
                    downloads_dir = Path("elsevier_debug_downloads")
                    downloads_dir.mkdir(exist_ok=True)
                    
                    save_path = downloads_dir / f"elsevier_playwright.pdf"
                    await download.save_as(save_path)
                    
                    if save_path.exists() and save_path.stat().st_size > 1000:
                        print(f"✅ Playwright download success: {save_path} ({save_path.stat().st_size} bytes)")
                        print(f"🎉 SOLUTION FOUND: Use Playwright expect_download()")
                        return save_path
                    else:
                        print(f"❌ Playwright download failed: Invalid file")
            except Exception as e:
                print(f"❌ Playwright download error: {e}")
            
            # Method 2: HTTP request approach (current implementation)
            print(f"\n🔄 Method 2: HTTP request with cookies...")
            try:
                import aiohttp

                # Get cookies from authenticated session
                cookies = await context.cookies()
                cookie_header = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
                
                headers = {
                    'Cookie': cookie_header,
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/pdf,*/*',
                    'Referer': page.url
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(pdf_href, headers=headers, timeout=30) as response:
                        print(f"HTTP Status: {response.status}")
                        print(f"Content-Type: {response.headers.get('content-type', 'Unknown')}")
                        print(f"Content-Length: {response.headers.get('content-length', 'Unknown')}")
                        
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')
                            
                            if 'pdf' in content_type.lower():
                                pdf_content = await response.read()
                                
                                downloads_dir = Path("elsevier_debug_downloads")
                                downloads_dir.mkdir(exist_ok=True)
                                
                                save_path = downloads_dir / f"elsevier_http.pdf"
                                with open(save_path, 'wb') as f:
                                    f.write(pdf_content)
                                
                                if save_path.exists() and save_path.stat().st_size > 1000:
                                    print(f"✅ HTTP download success: {save_path} ({save_path.stat().st_size} bytes)")
                                    return save_path
                                else:
                                    print(f"❌ HTTP download failed: Invalid file")
                            else:
                                print(f"❌ HTTP download failed: Not PDF content")
                                # Show first 200 chars of response
                                content_sample = (await response.read())[:200]
                                print(f"Response sample: {content_sample}")
                        else:
                            print(f"❌ HTTP request failed: {response.status}")
                            
            except Exception as e:
                print(f"❌ HTTP download error: {e}")
            
            # Method 3: Direct page navigation
            print(f"\n🔄 Method 3: Direct PDF navigation...")
            try:
                # Navigate directly to PDF URL
                response = await page.goto(pdf_href, wait_until='domcontentloaded', timeout=30000)
                
                if response and response.status == 200:
                    # Check if it's a PDF
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower():
                        print(f"✅ Direct navigation to PDF successful")
                        print(f"Content-Type: {content_type}")
                        print(f"🎉 SOLUTION: PDF opens directly in browser")
                        return True
                    else:
                        print(f"❌ Direct navigation failed: Not PDF content")
                        print(f"Content-Type: {content_type}")
                else:
                    print(f"❌ Direct navigation failed: {response.status if response else 'No response'}")
                    
            except Exception as e:
                print(f"❌ Direct navigation error: {e}")
            
            print(f"\n❌ All download methods failed")
            return None
            
        finally:
            await browser.close()


async def main():
    """Run Elsevier PDF download debugging."""
    result = await debug_elsevier_pdf_download()
    
    if result:
        print(f"\n✅ SUCCESS: PDF download working")
    else:
        print(f"\n❌ FAILED: Could not download PDF")


if __name__ == "__main__":
    asyncio.run(main())