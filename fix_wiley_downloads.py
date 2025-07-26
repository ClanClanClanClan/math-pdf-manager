#!/usr/bin/env python3
"""
FIX WILEY DOWNLOADS
===================

Direct approach to fix the PDF download issue.
No fancy infrastructure - just get the download working.

The problem: Downloads are not actually happening despite finding PDF links.
The solution: Debug and fix the download mechanism step by step.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def debug_wiley_download():
    """Debug why Wiley downloads aren't working"""
    
    print("🔧 DEBUGGING WILEY DOWNLOAD MECHANISM")
    print("=" * 60)
    
    # Use a known working Wiley paper
    test_doi = "10.1002/anie.202004934"
    test_url = f"https://onlinelibrary.wiley.com/doi/{test_doi}"
    
    print(f"Test URL: {test_url}")
    
    # Create downloads directory
    downloads_dir = Path("debug_downloads")
    downloads_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        # Launch with downloads enabled
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized'],
            downloads_path=str(downloads_dir)
        )
        
        context = await browser.new_context(
            accept_downloads=True
        )
        
        page = await context.new_page()
        
        # Enable download tracking
        downloads = []
        
        def handle_download(download):
            print(f"📥 Download started: {download.url}")
            downloads.append(download)
        
        page.on("download", handle_download)
        
        try:
            print(f"\n1. Loading page...")
            await page.goto(test_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            print(f"✅ Page loaded: {page.url}")
            
            # Handle cookies
            print(f"\n2. Handling cookies...")
            try:
                cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
                if cookie_btn:
                    await cookie_btn.click()
                    print("✅ Cookies accepted")
                    await page.wait_for_timeout(2000)
            except:
                print("❌ No cookie banner found")
            
            # Check page content
            print(f"\n3. Analyzing page content...")
            page_text = await page.inner_text('body')
            
            has_paywall = any(indicator in page_text.lower() for indicator in [
                'purchase', 'subscription', 'sign in to access', 'institutional access'
            ])
            
            if has_paywall:
                print("🔒 Paywall detected")
            else:
                print("🆓 No obvious paywall")
            
            # Look for ALL possible PDF-related elements
            print(f"\n4. Finding PDF elements...")
            
            # Get all links
            all_links = await page.query_selector_all('a')
            pdf_links = []
            
            for link in all_links:
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    
                    if href and ('pdf' in href.lower() or 'pdf' in text.lower()):
                        pdf_links.append({
                            'text': text.strip(),
                            'href': href,
                            'element': link
                        })
                        print(f"   📎 Found PDF link: '{text.strip()}' -> {href}")
                except:
                    continue
            
            if not pdf_links:
                print("❌ No PDF links found at all")
                
                # Look for any download-related elements
                download_elements = await page.query_selector_all('*:has-text("Download")')
                print(f"Found {len(download_elements)} elements with 'Download' text")
                
                for i, elem in enumerate(download_elements[:5]):  # Check first 5
                    try:
                        tag = await elem.evaluate('el => el.tagName')
                        text = await elem.inner_text()
                        print(f"   {i+1}. {tag}: '{text.strip()}'")
                    except:
                        pass
            else:
                print(f"✅ Found {len(pdf_links)} PDF-related links")
            
            # Try downloading from each PDF link
            print(f"\n5. Attempting downloads...")
            
            for i, link_info in enumerate(pdf_links):
                print(f"\n   Trying link {i+1}: {link_info['text']}")
                
                try:
                    # Method 1: Click and expect download
                    print(f"     Method 1: Click and expect download")
                    
                    download_promise = page.wait_for_event('download', timeout=10000)
                    await link_info['element'].click()
                    
                    try:
                        download = await download_promise
                        print(f"     ✅ Download triggered!")
                        
                        # Save the download
                        save_path = downloads_dir / f"wiley_test_{i+1}.pdf"
                        await download.save_as(save_path)
                        
                        if save_path.exists():
                            size = save_path.stat().st_size
                            print(f"     🎉 DOWNLOAD SUCCESS: {save_path} ({size} bytes)")
                            
                            if size > 1000:
                                print(f"     ✅ File size looks good!")
                                # We got a real download!
                                break
                            else:
                                print(f"     ⚠️ File too small, might be HTML error page")
                        else:
                            print(f"     ❌ File not saved")
                            
                    except:
                        print(f"     ❌ No download triggered")
                        
                        # Method 2: Check if href is direct PDF
                        href = link_info['href']
                        if href and not href.startswith('javascript:'):
                            print(f"     Method 2: Navigate to PDF URL directly")
                            
                            # Open in new page
                            new_page = await context.new_page()
                            
                            try:
                                response = await new_page.goto(href, timeout=15000)
                                
                                if response:
                                    content_type = response.headers.get('content-type', '')
                                    print(f"     Content-Type: {content_type}")
                                    
                                    if 'pdf' in content_type.lower():
                                        print(f"     ✅ Direct PDF found!")
                                        
                                        # Get PDF content
                                        pdf_buffer = await response.body()
                                        
                                        save_path = downloads_dir / f"wiley_direct_{i+1}.pdf"
                                        with open(save_path, 'wb') as f:
                                            f.write(pdf_buffer)
                                        
                                        if save_path.exists() and save_path.stat().st_size > 1000:
                                            print(f"     🎉 DIRECT DOWNLOAD SUCCESS: {save_path}")
                                            await new_page.close()
                                            break
                                    else:
                                        print(f"     ❌ Not a PDF response")
                                else:
                                    print(f"     ❌ No response from PDF URL")
                                    
                            except Exception as e:
                                print(f"     ❌ Direct navigation failed: {e}")
                            
                            await new_page.close()
                
                except Exception as e:
                    print(f"     ❌ Link {i+1} failed: {e}")
            
            # Check final results
            print(f"\n6. Final results...")
            pdf_files = list(downloads_dir.glob("*.pdf"))
            
            if pdf_files:
                print(f"🎉 SUCCESS: Downloaded {len(pdf_files)} files!")
                for pdf_file in pdf_files:
                    size_mb = pdf_file.stat().st_size / (1024 * 1024)
                    print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            else:
                print(f"❌ NO DOWNLOADS SUCCESSFUL")
                print(f"💡 The download mechanism needs fixing")
            
            # Keep browser open for inspection
            print(f"\n⏸️ Keeping browser open for manual inspection...")
            await page.wait_for_timeout(30000)
            
            await browser.close()
            
            return len(pdf_files) > 0
            
        except Exception as e:
            print(f"❌ Debug failed: {e}")
            await browser.close()
            return False

async def test_simple_download():
    """Test the simplest possible download scenario"""
    
    print(f"\n🔬 SIMPLE DOWNLOAD TEST")
    print("=" * 40)
    
    # Try with a completely open access paper first
    test_url = "https://onlinelibrary.wiley.com/doi/10.1002/anie.202004934"
    
    downloads_dir = Path("simple_test")
    downloads_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        print(f"Loading: {test_url}")
        await page.goto(test_url)
        await page.wait_for_timeout(5000)
        
        # Look for any downloadable link
        print("Looking for download links...")
        
        # Try the most common PDF selectors
        selectors = [
            'a:has-text("PDF")',
            'a[href*="pdf"]',
            'a[href*="epdf"]'
        ]
        
        for selector in selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    text = await element.inner_text()
                    href = await element.get_attribute('href')
                    print(f"Found: '{text}' -> {href}")
                    
                    # Try clicking it
                    print("Attempting download...")
                    
                    async with page.expect_download() as download_info:
                        await element.click()
                        download = await download_info.value
                        
                        save_path = downloads_dir / "simple_test.pdf"
                        await download.save_as(save_path)
                        
                        if save_path.exists():
                            print(f"✅ Downloaded: {save_path} ({save_path.stat().st_size} bytes)")
                            await browser.close()
                            return True
                    break
            except:
                continue
        
        print("❌ Simple download failed")
        await page.wait_for_timeout(10000)
        await browser.close()
        return False

async def main():
    """Main debugging function"""
    
    print("🔧 WILEY DOWNLOAD DEBUG SESSION")
    print("=" * 80)
    
    # First try simple download
    simple_success = await test_simple_download()
    
    if simple_success:
        print("✅ Simple download works!")
    else:
        print("❌ Even simple download fails - investigating...")
        
        # Debug the full mechanism
        debug_success = await debug_wiley_download()
        
        if debug_success:
            print("✅ Download mechanism fixed!")
        else:
            print("❌ Download mechanism still broken")

if __name__ == "__main__":
    asyncio.run(main())