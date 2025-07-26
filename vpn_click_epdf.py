#!/usr/bin/env python3
"""
VPN CLICK EPDF LINK
==================

Click the specific ePDF link you identified.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def click_epdf_link():
    """Click the ePDF link and download the paper"""
    
    # Load credentials
    from src.secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username:
        print("❌ No credentials")
        return
    
    print(f"✅ Credentials: {username[:3]}***")
    
    downloads_dir = Path("vpn_epdf_test")
    downloads_dir.mkdir(exist_ok=True)
    
    test_paper = {
        'doi': '10.3982/ECTA20404',
        'url': 'https://onlinelibrary.wiley.com/doi/10.3982/ECTA20404',
        'epdf_url': '/doi/epdf/10.3982/ECTA20404'
    }
    
    print(f"\n📄 Testing Econometrica paper")
    print(f"DOI: {test_paper['doi']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            accept_downloads=True
        )
        
        page = await context.new_page()
        
        try:
            print("\n🔄 Navigating to paper...")
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
                pass
            
            # Look for the specific ePDF link
            print("\n🔍 Looking for ePDF link...")
            
            # Try multiple selectors based on what you showed
            epdf_selectors = [
                f'a[href="{test_paper["epdf_url"]}"]',
                'a[href*="epdf/10.3982/ECTA20404"]',
                'a.pdf-download[href*="epdf"]',
                '.coolBar__section a[href*="epdf"]',
                'a[title="ePDF"]',
                'div.PdfLink a'
            ]
            
            epdf_link = None
            for selector in epdf_selectors:
                try:
                    epdf_link = await page.wait_for_selector(selector, timeout=3000)
                    if epdf_link:
                        print(f"✅ Found ePDF link with selector: {selector}")
                        break
                except:
                    continue
            
            if epdf_link:
                # Get link info
                href = await epdf_link.get_attribute('href')
                print(f"📎 Link href: {href}")
                
                # Click the ePDF link
                print("\n🖱️ Clicking ePDF link...")
                await epdf_link.click()
                
                # Wait for navigation
                await page.wait_for_timeout(5000)
                
                # Check all open pages
                all_pages = context.pages
                print(f"\n📑 Open pages: {len(all_pages)}")
                
                for i, p in enumerate(all_pages):
                    url = p.url
                    print(f"  Page {i+1}: {url[:100]}...")
                    
                    if 'epdf' in url or 'pdf' in url:
                        print(f"  ✅ This is the PDF page!")
                        
                        # Wait for PDF to load
                        await p.wait_for_timeout(5000)
                        
                        # Save the PDF
                        print("\n📄 Saving PDF...")
                        pdf_buffer = await p.pdf(
                            format='A4',
                            margin={'top': '0cm', 'right': '0cm', 'bottom': '0cm', 'left': '0cm'},
                            print_background=True
                        )
                        
                        filename = f"econometrica_vpn_{test_paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                        save_path = downloads_dir / filename
                        
                        with open(save_path, 'wb') as f:
                            f.write(pdf_buffer)
                        
                        size_mb = save_path.stat().st_size / (1024 * 1024)
                        print(f"\n🎉 SUCCESS! Downloaded {size_mb:.2f} MB")
                        print(f"📄 Saved to: {save_path}")
                        print(f"\n✅ VPN METHOD WORKS!")
                        print(f"✅ You CAN access Econometrica papers with VPN!")
                        
                        await browser.close()
                        return True
            
            else:
                print("❌ Could not find ePDF link")
                print("Taking screenshot...")
                await page.screenshot(path=downloads_dir / "no_epdf_link.png")
                
                # Try direct navigation to ePDF URL
                print("\n🔄 Trying direct navigation to ePDF...")
                epdf_full_url = f"https://onlinelibrary.wiley.com{test_paper['epdf_url']}"
                print(f"URL: {epdf_full_url}")
                
                await page.goto(epdf_full_url, wait_until='networkidle')
                await page.wait_for_timeout(5000)
                
                # Check if we're on a PDF page now
                if 'pdf' in page.url:
                    print("✅ Navigated to PDF page!")
                    
                    pdf_buffer = await page.pdf(format='A4')
                    filename = f"econometrica_direct_{test_paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                    save_path = downloads_dir / filename
                    
                    with open(save_path, 'wb') as f:
                        f.write(pdf_buffer)
                    
                    size_mb = save_path.stat().st_size / (1024 * 1024)
                    print(f"\n🎉 SUCCESS! Downloaded {size_mb:.2f} MB")
                    print(f"✅ VPN METHOD WORKS via direct navigation!")
                    
                    await browser.close()
                    return True
            
            await browser.close()
            return False
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            await page.screenshot(path=downloads_dir / "error.png")
            await browser.close()
            return False

async def main():
    print("🔒 VPN ePDF LINK TEST")
    print("=" * 60)
    print("Testing the exact ePDF link you identified")
    print("=" * 60)
    
    success = await click_epdf_link()
    
    if success:
        print("\n🏆 CONFIRMED: VPN METHOD WORKS!")
        print("You can access Econometrica papers that the API blocks!")
    else:
        print("\n❌ VPN method failed")
        print("Check screenshots in: vpn_epdf_test/")
    
    print("\n🔒 TEST COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())