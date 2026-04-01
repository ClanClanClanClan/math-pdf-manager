#!/usr/bin/env python3
"""
IEEE Download Debug Test

The torture tests show IEEE HTTP access is working (200 responses) but PDFs aren't downloading.
This test will diagnose exactly what's happening with IEEE downloads.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.publishers.ieee_navigator import IEEE_CONFIG, IEEENavigator
from src.secure_credential_manager import get_credential_manager


async def debug_ieee_download():
    """Debug IEEE download process in detail."""
    
    print(f"\n{'='*70}")
    print(f"🔍 IEEE DOWNLOAD DEBUG")
    print(f"{'='*70}")
    
    # Use a known working paper
    doi = '10.1109/5.771073'
    
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
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        try:
            print(f"🌐 Navigating to: {doi}")
            url = f"https://doi.org/{doi}"
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            navigator = IEEENavigator(page, IEEE_CONFIG)
            navigator.eth_auth = ETHAuthenticator(page, username, password)
            
            # Perform authentication
            print(f"🔐 Authenticating...")
            if await navigator.navigate_to_login():
                if await navigator.select_eth_institution():
                    if await navigator.eth_auth.perform_login():
                        if await navigator.navigate_after_auth():
                            print(f"✅ Authentication successful")
                            
                            # Now debug the download process step by step
                            print(f"\n🔍 DEBUGGING PDF DOWNLOAD PROCESS:")
                            
                            # Check current page
                            current_url = page.url
                            print(f"Current URL: {current_url}")
                            
                            # Look for PDF button
                            pdf_buttons = await page.query_selector_all('a[href*="stamp.jsp"]')
                            print(f"Found {len(pdf_buttons)} PDF buttons")
                            
                            if pdf_buttons:
                                for i, button in enumerate(pdf_buttons):
                                    href = await button.get_attribute('href')
                                    text = await button.inner_text()
                                    print(f"  Button {i}: '{text}' → {href}")
                                
                                # Try to click the first PDF button
                                print(f"\n📄 Attempting PDF download...")
                                
                                try:
                                    # Set up download expectation
                                    async with page.expect_download(timeout=30000) as download_info:
                                        await pdf_buttons[0].click()
                                        print(f"   ✅ Clicked PDF button")
                                    
                                    download = await download_info.value
                                    print(f"   ✅ Download initiated")
                                    
                                    # Save the file
                                    downloads_dir = Path("debug_downloads")
                                    downloads_dir.mkdir(exist_ok=True)
                                    
                                    filename = download.suggested_filename or f"ieee_{doi.replace('/', '_')}.pdf"
                                    filepath = downloads_dir / filename
                                    
                                    await download.save_as(filepath)
                                    print(f"   ✅ File saved: {filepath}")
                                    
                                    if filepath.exists():
                                        size = filepath.stat().st_size
                                        print(f"   📊 File size: {size:,} bytes")
                                        
                                        if size > 1000:
                                            print(f"   🎉 SUCCESS! PDF downloaded successfully")
                                        else:
                                            print(f"   ⚠️  File too small, might be error page")
                                            # Read first few bytes to check
                                            with open(filepath, 'rb') as f:
                                                first_bytes = f.read(100)
                                                print(f"   First bytes: {first_bytes[:50]}...")
                                    
                                except Exception as e:
                                    print(f"   ❌ Download failed: {e}")
                                    
                                    # Try alternative method - navigate directly to PDF URL
                                    print(f"\n🔄 Trying direct PDF URL access...")
                                    
                                    pdf_href = await pdf_buttons[0].get_attribute('href')
                                    if pdf_href:
                                        if not pdf_href.startswith('http'):
                                            pdf_href = f"https://ieeexplore.ieee.org{pdf_href}"
                                        
                                        print(f"   Direct URL: {pdf_href}")
                                        
                                        # Navigate to PDF URL
                                        response = await page.goto(pdf_href, wait_until='domcontentloaded')
                                        print(f"   Response status: {response.status}")
                                        print(f"   Content type: {response.headers.get('content-type', 'unknown')}")
                                        
                                        # Check if it's actually a PDF
                                        content_type = response.headers.get('content-type', '')
                                        if 'pdf' in content_type.lower():
                                            print(f"   ✅ Got PDF content type")
                                        else:
                                            print(f"   ⚠️  Not PDF content type: {content_type}")
                                            
                                            # Check page content
                                            page_content = await page.content()
                                            if 'PDF' in page_content:
                                                print(f"   📄 Page contains PDF viewer")
                                            else:
                                                print(f"   ❌ Page doesn't seem to contain PDF")
                                                print(f"   Page title: {await page.title()}")
                                
                            else:
                                print(f"❌ No PDF buttons found")
                                
                                # Check what buttons are available
                                all_buttons = await page.query_selector_all('a, button')
                                print(f"\nAll clickable elements:")
                                for i, btn in enumerate(all_buttons[:10]):
                                    try:
                                        text = await btn.inner_text()
                                        href = await btn.get_attribute('href')
                                        if text and ('pdf' in text.lower() or 'download' in text.lower()):
                                            print(f"  Element {i}: '{text}' → {href}")
                                    except:
                                        pass
                        else:
                            print(f"❌ Post-auth navigation failed")
                    else:
                        print(f"❌ ETH authentication failed")
                else:
                    print(f"❌ ETH selection failed")
            else:
                print(f"❌ Login navigation failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            # Keep browser open for manual inspection
            print(f"\n⏸️  Browser kept open for manual inspection...")
            print(f"Press Enter to close...")
            input()
            
            await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_ieee_download())