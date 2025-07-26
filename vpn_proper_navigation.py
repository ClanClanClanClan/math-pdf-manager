#!/usr/bin/env python3
"""
VPN PROPER NAVIGATION TEST
==========================

Actually navigate the page properly when VPN is on.
Look more carefully for PDF access options.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def proper_vpn_test():
    """Properly test VPN access with careful navigation"""
    
    # Load credentials
    from src.secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username:
        print("❌ No credentials")
        return
    
    print(f"✅ Credentials: {username[:3]}***")
    
    downloads_dir = Path("vpn_proper_test")
    downloads_dir.mkdir(exist_ok=True)
    
    # Test Econometrica paper that failed with API
    test_paper = {
        'doi': '10.3982/ECTA20404',
        'url': 'https://onlinelibrary.wiley.com/doi/10.3982/ECTA20404',
        'journal': 'Econometrica'
    }
    
    print(f"\n📄 Testing: {test_paper['journal']}")
    print(f"DOI: {test_paper['doi']}")
    print(f"URL: {test_paper['url']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser to see what happens
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            accept_downloads=True
        )
        
        page = await context.new_page()
        
        try:
            print("\n🔄 Step 1: Navigate to paper...")
            await page.goto(test_paper['url'], wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            try:
                cookie_btn = await page.wait_for_selector('button:has-text("Accept")', timeout=3000)
                if cookie_btn:
                    await cookie_btn.click()
                    print("✅ Accepted cookies")
                    await page.wait_for_timeout(2000)
            except:
                print("ℹ️ No cookie banner")
            
            # Screenshot initial state
            await page.screenshot(path=downloads_dir / "1_initial_state.png")
            
            # Check page content
            page_text = await page.inner_text('body')
            print("\n📋 Page analysis:")
            
            if 'full access' in page_text.lower():
                print("✅ Shows 'Full Access'")
            else:
                print("❌ No 'Full Access' indicator")
            
            if 'eth' in page_text.lower():
                print("✅ ETH mentioned on page")
            
            # Look for ALL possible PDF access points
            print("\n🔍 Looking for PDF access options...")
            
            # Method 1: Look in the article tools section
            try:
                tools_section = await page.wait_for_selector('.article-tools, .content-tools, [class*="tools"]', timeout=3000)
                if tools_section:
                    print("✅ Found tools section")
                    await page.screenshot(path=downloads_dir / "2_tools_section.png")
                    
                    # Look for PDF within tools
                    pdf_in_tools = await tools_section.query_selector('a:has-text("PDF"), button:has-text("PDF")')
                    if pdf_in_tools:
                        print("✅ Found PDF in tools!")
                        
                        # Click it
                        async with page.expect_download() as download_info:
                            await pdf_in_tools.click()
                            print("🖱️ Clicked PDF button")
                            
                            try:
                                download = await download_info.value
                                filename = f"econometrica_{test_paper['doi'].replace('/', '_')}.pdf"
                                save_path = downloads_dir / filename
                                await download.save_as(save_path)
                                
                                size_mb = save_path.stat().st_size / (1024 * 1024)
                                print(f"\n🎉 SUCCESS! Downloaded {size_mb:.2f} MB")
                                print(f"✅ VPN METHOD WORKS!")
                                await browser.close()
                                return
                            except:
                                print("⏳ No immediate download, checking for new tab/page...")
            except:
                print("ℹ️ No obvious tools section")
            
            # Method 2: Look for any PDF links on the page
            print("\n🔍 Searching entire page for PDF links...")
            
            all_links = await page.query_selector_all('a')
            pdf_found = False
            
            for link in all_links:
                href = await link.get_attribute('href') or ''
                text = await link.inner_text() or ''
                
                if 'pdf' in href.lower() or 'pdf' in text.lower():
                    print(f"📎 Found potential PDF link: {text[:30]}... -> {href[:50]}...")
                    pdf_found = True
                    
                    # Try clicking it
                    try:
                        async with page.expect_download() as download_info:
                            await link.click()
                            download = await download_info.value
                            
                            filename = f"econometrica_link_{test_paper['doi'].replace('/', '_')}.pdf"
                            save_path = downloads_dir / filename
                            await download.save_as(save_path)
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"\n🎉 SUCCESS! Downloaded {size_mb:.2f} MB")
                            print(f"✅ VPN METHOD WORKS!")
                            await browser.close()
                            return
                    except:
                        continue
            
            if not pdf_found:
                print("❌ No PDF links found on page")
            
            # Method 3: Check if we need to scroll or expand sections
            print("\n🔍 Checking for expandable sections...")
            
            # Look for expandable/collapsible sections
            expandables = await page.query_selector_all('[aria-expanded="false"], .collapsed, .expandable')
            for exp in expandables:
                try:
                    await exp.click()
                    await page.wait_for_timeout(1000)
                    print("📂 Expanded a section")
                except:
                    pass
            
            # Method 4: Look for the specific toolbar that has PDF
            print("\n🔍 Looking for article toolbar...")
            
            # The screenshot showed PDF in a toolbar at the bottom
            toolbar_selectors = [
                '.article-toolbar',
                '.bottom-toolbar',
                '[role="toolbar"]',
                '.article-actions',
                '.pdf-toolbar',
                'div:has(> a:has-text("PDF"))'
            ]
            
            for selector in toolbar_selectors:
                try:
                    toolbar = await page.wait_for_selector(selector, timeout=2000)
                    if toolbar:
                        print(f"✅ Found toolbar: {selector}")
                        
                        # Look for PDF within
                        pdf_btn = await toolbar.query_selector('a:has-text("PDF"), button:has-text("PDF")')
                        if pdf_btn:
                            print("✅ Found PDF button in toolbar!")
                            
                            # Get more info about the button
                            href = await pdf_btn.get_attribute('href') or 'No href'
                            text = await pdf_btn.inner_text() or 'No text'
                            print(f"  Text: {text}")
                            print(f"  Href: {href[:100]}...")
                            
                            # Click it
                            await pdf_btn.click()
                            print("🖱️ Clicked PDF button")
                            
                            # Wait for something to happen
                            await page.wait_for_timeout(5000)
                            
                            # Check all pages/tabs
                            all_pages = context.pages
                            print(f"\n📑 Open pages: {len(all_pages)}")
                            
                            for i, p in enumerate(all_pages):
                                url = p.url
                                print(f"  Page {i+1}: {url[:80]}...")
                                
                                if 'pdf' in url.lower() or 'epdf' in url.lower():
                                    print(f"  ✅ This is a PDF page!")
                                    
                                    # Try to save it
                                    await p.wait_for_timeout(3000)
                                    pdf_buffer = await p.pdf(format='A4')
                                    
                                    filename = f"econometrica_final_{test_paper['doi'].replace('/', '_')}.pdf"
                                    save_path = downloads_dir / filename
                                    
                                    with open(save_path, 'wb') as f:
                                        f.write(pdf_buffer)
                                    
                                    size_mb = save_path.stat().st_size / (1024 * 1024)
                                    print(f"\n🎉 SUCCESS! Saved {size_mb:.2f} MB")
                                    print(f"✅ VPN METHOD WORKS!")
                                    await browser.close()
                                    return
                except:
                    continue
            
            # Final screenshot
            await page.screenshot(path=downloads_dir / "3_final_state.png")
            
            print("\n❌ Could not find working PDF download")
            print("📸 Check screenshots in:", downloads_dir)
            
            # Wait for user to manually show where PDF is
            print("\n⏸️ Browser still open - please show me where the PDF button is!")
            await asyncio.sleep(30)  # Give time to inspect
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            await page.screenshot(path=downloads_dir / "error_state.png")
        
        finally:
            await browser.close()

async def main():
    print("🔒 VPN PROPER NAVIGATION TEST")
    print("=" * 60)
    print("Testing Econometrica access with careful navigation")
    print("=" * 60)
    
    await proper_vpn_test()
    
    print("\n🔒 TEST COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())