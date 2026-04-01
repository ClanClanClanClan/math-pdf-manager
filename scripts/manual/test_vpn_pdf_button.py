#!/usr/bin/env python3
"""
TEST VPN PDF BUTTON
===================

The page shows "Full Access" but PDF button is in the toolbar.
Let's click it properly.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def test_pdf_button():
    """Test clicking the PDF button in the toolbar"""
    
    # Load credentials
    from src.secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username:
        print("❌ No credentials")
        return
    
    print(f"✅ Credentials loaded: {username[:3]}***")
    
    downloads_dir = Path("vpn_pdf_button_test")
    downloads_dir.mkdir(exist_ok=True)
    
    test_paper = {
        'doi': '10.3982/ECTA20404',
        'url': 'https://onlinelibrary.wiley.com/doi/10.3982/ECTA20404'
    }
    
    print(f"\n📄 Testing Econometrica paper")
    print(f"DOI: {test_paper['doi']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            accept_downloads=True
        )
        
        page = await context.new_page()
        
        try:
            print("\n🔄 Navigating to paper...")
            await page.goto(test_paper['url'], wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            try:
                cookie_btn = await page.wait_for_selector('button:has-text("Accept")', timeout=3000)
                if cookie_btn:
                    await cookie_btn.click()
                    print("✅ Accepted cookies")
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # Screenshot current state
            await page.screenshot(path=downloads_dir / "1_page_loaded.png")
            
            # Check if we see "Full Access"
            page_text = await page.inner_text('body')
            if 'full access' in page_text.lower():
                print("✅ Page shows 'Full Access'")
            
            # Look for the PDF button in the toolbar
            print("\n🔍 Looking for PDF button...")
            
            # Try multiple selectors for PDF button
            pdf_selectors = [
                'a:has-text("PDF")',
                'button:has-text("PDF")',
                'a[href*="pdf"]',
                'a[href*="epdf"]',
                'div.article-tools a:has-text("PDF")',
                '[aria-label*="PDF"]',
                '.pdf-download',
                'a.pdf-link'
            ]
            
            pdf_button = None
            for selector in pdf_selectors:
                try:
                    pdf_button = await page.wait_for_selector(selector, timeout=2000)
                    if pdf_button:
                        print(f"✅ Found PDF button with selector: {selector}")
                        break
                except:
                    continue
            
            if pdf_button:
                # Take screenshot before clicking
                await page.screenshot(path=downloads_dir / "2_before_pdf_click.png")
                
                # Set up download handler
                download_complete = False
                download_path = None
                
                async def handle_download(download):
                    nonlocal download_complete, download_path
                    filename = f"econometrica_{test_paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                    save_path = downloads_dir / filename
                    await download.save_as(save_path)
                    download_path = save_path
                    download_complete = True
                    print(f"✅ Download started: {filename}")
                
                page.on("download", handle_download)
                
                # Click PDF button
                print("🖱️ Clicking PDF button...")
                await pdf_button.click()
                
                # Wait for download or new page/tab
                await page.wait_for_timeout(5000)
                
                if download_complete and download_path:
                    size_mb = download_path.stat().st_size / (1024 * 1024)
                    print(f"\n🎉 SUCCESS! Downloaded {size_mb:.2f} MB")
                    print(f"📄 File: {download_path}")
                    print("\n✅ VPN METHOD WORKS!")
                    print("You CAN access Econometrica papers with VPN!")
                else:
                    # Check if PDF opened in viewer
                    if 'pdf' in page.url or await page.query_selector('embed[type="application/pdf"]'):
                        print("📄 PDF opened in viewer - printing to file...")
                        
                        pdf_buffer = await page.pdf(format='A4')
                        filename = f"econometrica_print_{test_paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                        save_path = downloads_dir / filename
                        
                        with open(save_path, 'wb') as f:
                            f.write(pdf_buffer)
                        
                        size_mb = save_path.stat().st_size / (1024 * 1024)
                        print(f"\n🎉 SUCCESS! Printed {size_mb:.2f} MB")
                        print(f"📄 File: {save_path}")
                        print("\n✅ VPN METHOD WORKS!")
                    else:
                        # Check all open pages
                        all_pages = context.pages
                        print(f"ℹ️ Open pages: {len(all_pages)}")
                        
                        for i, p in enumerate(all_pages):
                            print(f"  Page {i}: {p.url[:50]}...")
                            if 'pdf' in p.url:
                                print(f"  📄 This is a PDF page!")
                                
                                # Try to download from this page
                                pdf_buffer = await p.pdf(format='A4')
                                filename = f"econometrica_tab_{test_paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                                save_path = downloads_dir / filename
                                
                                with open(save_path, 'wb') as f:
                                    f.write(pdf_buffer)
                                
                                size_mb = save_path.stat().st_size / (1024 * 1024)
                                print(f"\n🎉 SUCCESS! Got PDF from tab: {size_mb:.2f} MB")
                                print(f"📄 File: {save_path}")
                                print("\n✅ VPN METHOD WORKS!")
                                break
            else:
                print("❌ Could not find PDF button")
                await page.screenshot(path=downloads_dir / "3_no_pdf_button.png")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path=downloads_dir / "error.png")
        
        finally:
            await browser.close()

async def main():
    print("🔒 TESTING VPN METHOD - PDF BUTTON CLICK")
    print("=" * 60)
    print("Testing if we can download Econometrica via VPN")
    print("=" * 60)
    
    await test_pdf_button()
    
    print("\n🔒 TEST COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())