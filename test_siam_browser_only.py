#!/usr/bin/env python3
"""
Test SIAM Browser Download Only
===============================

Focus on just the browser download part.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import time

async def test_siam_browser_download():
    """Test SIAM browser download directly"""
    print("\n" + "="*60)
    print("TESTING SIAM BROWSER DOWNLOAD DIRECTLY")
    print("="*60)
    
    # Get credentials
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from src.secure_credential_manager import get_credential_manager
    
    cm = get_credential_manager()
    username = cm.get_credential("eth_username")
    password = cm.get_credential("eth_password")
    
    if not username or not password:
        print("❌ No ETH credentials found")
        return False
    
    print(f"✓ Using ETH credentials: {username[:3]}***")
    
    test_doi = "10.1137/S0097539795293172"
    siam_url = f"https://epubs.siam.org/doi/{test_doi}"
    
    async with async_playwright() as p:
        print("\nLaunching browser...")
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"Navigating to: {siam_url}")
            await page.goto(siam_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Click institutional access
            print("Looking for institutional access...")
            inst_button = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=10000)
            print("✓ Found institutional access button")
            
            await inst_button.click()
            await page.wait_for_timeout(3000)
            
            # Search for ETH
            print("Searching for ETH Zurich...")
            search_input = await page.wait_for_selector('input#shibboleth_search', timeout=10000)
            await search_input.click()
            await search_input.fill("")  # Clear first
            await page.wait_for_timeout(500)
            await search_input.type("ETH Zurich", delay=100)  # Type slowly to trigger dropdown
            await page.wait_for_timeout(2000)
            
            # Try multiple selectors for ETH
            eth_selectors = [
                '.ms-res-item a:has-text("ETH Zurich")',
                'a.sso-institution:has-text("ETH Zurich")',
                'text="ETH Zurich"',
                '.ms-res-item:has-text("ETH Zurich")',
                'a[data-entityid*="ethz.ch"]'
            ]
            
            eth_option = None
            for selector in eth_selectors:
                try:
                    eth_option = await page.wait_for_selector(selector, timeout=3000)
                    if eth_option:
                        print(f"✓ Found ETH Zurich with selector: {selector}")
                        break
                except:
                    continue
            
            if eth_option:
                await eth_option.click()
            else:
                print("❌ Could not find ETH Zurich option")
                # Take screenshot
                await page.screenshot(path="siam_search_issue.png")
                print("Screenshot saved: siam_search_issue.png")
                return False
            
            # Wait for ETH login
            await page.wait_for_timeout(5000)
            print("At ETH login page")
            
            # Fill credentials
            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=10000)
            await username_input.fill(username)
            
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
            await password_input.fill(password)
            
            # Submit
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
            print("✓ Submitting credentials...")
            await submit_button.click()
            
            # Wait for redirect back to SIAM
            print("Waiting for authentication...")
            await page.wait_for_timeout(10000)
            
            current_url = page.url
            if 'siam' in current_url:
                print("✓ Back at SIAM!")
                
                # Navigate to PDF URL
                pdf_url = siam_url.replace('/doi/', '/doi/epdf/')
                print(f"\nNavigating to PDF: {pdf_url}")
                await page.goto(pdf_url, wait_until='domcontentloaded')
                
                # Wait for PDF to load
                print("Waiting for PDF to load...")
                await page.wait_for_timeout(10000)
                
                # Set up download handling
                download_path = Path("SIAM_BROWSER_TEST")
                download_path.mkdir(exist_ok=True)
                
                # Handle download event
                download_happened = False
                downloaded_file = None
                
                async def handle_download(download):
                    nonlocal download_happened, downloaded_file
                    download_happened = True
                    suggested_name = download.suggested_filename
                    print(f"\n✅ DOWNLOAD STARTED: {suggested_name}")
                    
                    # Save the download
                    save_path = download_path / suggested_name
                    await download.save_as(str(save_path))
                    downloaded_file = save_path
                    print(f"✅ SAVED TO: {save_path}")
                
                page.on('download', handle_download)
                
                # Look for download button
                print("\nLooking for download button...")
                download_selectors = [
                    'a[aria-label*="Download"]',
                    'button[aria-label*="Download"]',
                    'a[title*="Download"]',
                    'button[title*="Download"]',
                    'a:has-text("Download")',
                    'button:has-text("Download")',
                    '.download-btn',
                    'a.get_app',  # Material icon
                ]
                
                download_button = None
                for selector in download_selectors:
                    try:
                        download_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                        if download_button:
                            text = await download_button.text_content() or ''
                            print(f"✓ Found download button: '{text.strip()}' with {selector}")
                            break
                    except:
                        continue
                
                if download_button:
                    print("Clicking download button...")
                    await download_button.click()
                    
                    # Wait for download
                    await page.wait_for_timeout(10000)
                    
                    if download_happened and downloaded_file and downloaded_file.exists():
                        file_size = downloaded_file.stat().st_size
                        print(f"\n✅ SUCCESS! PDF DOWNLOADED!")
                        print(f"File: {downloaded_file}")
                        print(f"Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                        
                        # Verify it's a PDF
                        with open(downloaded_file, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                print("✅ Valid PDF file!")
                                return True
                    else:
                        print("❌ Download did not complete")
                else:
                    print("❌ No download button found")
                    
                    # Take screenshot
                    await page.screenshot(path="siam_pdf_page.png")
                    print("Screenshot saved: siam_pdf_page.png")
            else:
                print(f"❌ Not back at SIAM: {current_url}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_siam_browser_download())
    
    if success:
        print("\n" + "="*60)
        print("✅ SIAM BROWSER DOWNLOAD WORKS!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ SIAM browser download failed")
        print("="*60)