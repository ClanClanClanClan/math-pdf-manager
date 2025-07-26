#!/usr/bin/env python3
"""
ULTRATHINK WILEY TEST
====================

Test different approaches to avoid Cloudflare:
1. Try downloading PDFs directly without institutional login
2. Use better anti-detection measures
3. Try different access patterns
"""

import asyncio
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def ultrathink_wiley():
    """Ultrathink approach to Wiley"""
    
    print("🧠 ULTRATHINK WILEY TEST")
    print("=" * 80)
    
    test_doi = "10.1002/anie.202004934"
    pdf_dir = Path("wiley_ultrathink")
    if pdf_dir.exists():
        import shutil
        shutil.rmtree(pdf_dir)
    pdf_dir.mkdir()
    
    async with async_playwright() as p:
        # Launch with maximum anti-detection
        browser = await p.chromium.launch(
            headless=False,  # Keep visible to check
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--start-maximized',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        # Add anti-detection scripts
        await context.add_init_script("""
            // Overwrite the `plugins` property to use a custom getter.
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Overwrite the `languages` property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Overwrite webdriver indicator
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Add chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Modify permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        page = await context.new_page()
        
        # Approach 1: Navigate slowly and naturally
        print("\n📍 APPROACH 1: Natural navigation")
        url = f"https://doi.org/{test_doi}"
        print(f"   Navigating to: {url}")
        await page.goto(url, wait_until='domcontentloaded')
        
        # Wait like a human
        await page.wait_for_timeout(5000)
        
        # Accept cookies slowly
        try:
            cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
            if cookie_btn:
                print("   🍪 Accepting cookies...")
                await page.wait_for_timeout(2000)  # Human delay
                await cookie_btn.click()
                await page.wait_for_timeout(3000)
        except:
            pass
        
        # Approach 2: Check if PDF is directly accessible
        print("\n📍 APPROACH 2: Direct PDF access")
        
        # Look for PDF links
        pdf_links = await page.query_selector_all('a[href*="/pdf/"], a[href*="pdf"], a:has-text("PDF")')
        print(f"   Found {len(pdf_links)} PDF-related links")
        
        if pdf_links:
            # Try the first visible PDF link
            for i, link in enumerate(pdf_links[:3]):
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    visible = await link.is_visible()
                    
                    print(f"   Link {i+1}: '{text.strip()}' visible={visible}")
                    
                    if visible and ('pdf' in text.lower() or (href and 'pdf' in href)):
                        print(f"   🎯 Attempting direct PDF download from link {i+1}")
                        
                        # Set up download handling
                        download_path = pdf_dir / f"wiley_direct_{i+1}.pdf"
                        
                        # Try clicking with download expectation
                        async with page.expect_download() as download_info:
                            await link.click()
                            download = await download_info.value
                            
                            # Save the download
                            await download.save_as(download_path)
                            print(f"   ✅ Downloaded to {download_path}")
                            
                            # Verify it's a PDF
                            if download_path.exists() and download_path.stat().st_size > 1000:
                                with open(download_path, 'rb') as f:
                                    if f.read(4) == b'%PDF':
                                        print(f"   ✅ Valid PDF downloaded!")
                                        await page.wait_for_timeout(30000)
                                        await browser.close()
                                        return True
                        
                except Exception as e:
                    print(f"   ❌ Download attempt {i+1} failed: {str(e)}")
                    
                    # Alternative: Try navigating to PDF URL directly
                    try:
                        href = await link.get_attribute('href')
                        if href:
                            if not href.startswith('http'):
                                href = f"https://onlinelibrary.wiley.com{href}"
                            
                            print(f"   🔄 Trying direct navigation to: {href}")
                            
                            # Navigate in a new page
                            new_page = await context.new_page()
                            
                            # Set up download expectation
                            download_path = pdf_dir / f"wiley_nav_{i+1}.pdf"
                            
                            # Navigate and wait for potential download
                            await new_page.goto(href)
                            await new_page.wait_for_timeout(5000)
                            
                            # Check if PDF loaded in browser
                            if 'pdf' in new_page.url:
                                print(f"   📄 PDF loaded in browser")
                                # Try to trigger download
                                await new_page.keyboard.press('Control+s')
                                await new_page.wait_for_timeout(5000)
                            
                            await new_page.close()
                            
                    except Exception as e2:
                        print(f"   ❌ Navigation attempt failed: {str(e2)}")
        
        # Approach 3: Try without institutional login first
        print("\n📍 APPROACH 3: Check access without login")
        
        # Check page content
        page_content = await page.content()
        
        # Look for signs of full text access
        if any(indicator in page_content.lower() for indicator in [
            'full text', 'download pdf', 'view pdf', 'read online'
        ]):
            print("   ✅ Some form of access appears available")
        else:
            print("   ❌ No obvious access indicators")
        
        # Take screenshot
        await page.screenshot(path='wiley_ultrathink.png')
        print("\n📸 Screenshot saved: wiley_ultrathink.png")
        
        print("\n⏸️ Keeping browser open for 30 seconds...")
        await page.wait_for_timeout(30000)
        
        await browser.close()
        
        # Check results
        pdfs = list(pdf_dir.glob("*.pdf"))
        if pdfs:
            print(f"\n✅ SUCCESS! Downloaded {len(pdfs)} PDFs:")
            for pdf in pdfs:
                print(f"   📄 {pdf.name} ({pdf.stat().st_size / 1024:.1f} KB)")
            return True
        else:
            print("\n❌ No PDFs downloaded")
            return False

if __name__ == "__main__":
    success = asyncio.run(ultrathink_wiley())
    if not success:
        print("\n💡 ULTRATHINK INSIGHTS:")
        print("   - Wiley shows PDF links but they may require session/authentication")
        print("   - Cloudflare only triggers on institutional login path")
        print("   - Direct PDF access might work with proper session handling")
        print("   - May need to investigate cookie/session management")