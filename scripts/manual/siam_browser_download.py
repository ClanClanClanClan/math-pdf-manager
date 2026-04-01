#!/usr/bin/env python3
"""
SIAM Browser Download
=====================

Download SIAM PDFs directly in the browser (like the ultrathink test).
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def download_siam_pdfs():
    print("🎯 SIAM BROWSER DOWNLOAD TEST")
    print("=" * 50)
    
    # Get credentials
    try:
        from src.secure_credential_manager import get_credential_manager
        
        cm = get_credential_manager()
        username = cm.get_credential("eth_username")
        password = cm.get_credential("eth_password")
        
        if not username or not password:
            print("❌ No ETH credentials")
            return 0
            
        print(f"✅ Using ETH credentials: {username[:3]}***")
            
    except ImportError as e:
        print(f"❌ Cannot import credentials: {e}")
        return 0
    
    # Test DOIs
    test_dois = [
        "10.1137/S0097539795293172",  # Shor's algorithm
        "10.1137/S0097539792240406",  # Complexity of permanent
        "10.1137/0210022"  # LP algorithm
    ]
    
    downloaded = 0
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to first paper to authenticate
            print(f"\n🔐 Authenticating with SIAM...")
            base_url = "https://epubs.siam.org"
            sso_url = f"{base_url}/action/ssostart?redirectUri=/doi/{test_dois[0]}"
            
            await page.goto(sso_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Find search input
            search_input = await page.wait_for_selector('input#shibboleth_search', timeout=15000)
            
            # Type ETH Zurich
            await search_input.click()
            await search_input.fill("")
            await page.wait_for_timeout(500)
            await search_input.type("ETH Zurich", delay=100)
            await page.wait_for_timeout(2000)
            
            # Wait for dropdown
            await page.wait_for_selector('.ms-res-ctn.dropdown-menu', timeout=3000)
            
            # Click ETH
            eth_option = await page.wait_for_selector('.ms-res-item a.sso-institution:has-text("ETH Zurich")', timeout=2000)
            await eth_option.click()
            
            # Wait for ETH login
            await page.wait_for_timeout(10000)
            
            # Fill credentials
            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
            await username_input.fill(username)
            
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
            await password_input.fill(password)
            
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
            await submit_button.click()
            
            await page.wait_for_timeout(20000)
            
            print("✅ Authentication successful!")
            
            # Now download PDFs
            output_dir = Path("siam_browser_downloads")
            output_dir.mkdir(exist_ok=True)
            
            for idx, doi in enumerate(test_dois):
                print(f"\n📄 Downloading paper {idx + 1}/3: {doi}")
                
                # Navigate to PDF
                pdf_url = f"{base_url}/doi/epdf/{doi}"
                await page.goto(pdf_url, timeout=90000)
                
                # Wait for PDF to load
                print("   Waiting for PDF to load...")
                await page.wait_for_timeout(10000)
                
                # Setup download handler
                download_happened = False
                
                async def handle_download(download):
                    nonlocal download_happened, downloaded
                    download_happened = True
                    filename = f"siam_{doi.replace('/', '_').replace('.', '_')}.pdf"
                    save_path = output_dir / filename
                    await download.save_as(str(save_path))
                    print(f"   ✅ Downloaded: {filename}")
                    downloaded += 1
                
                page.on('download', handle_download)
                
                # Click download button
                download_button = await page.wait_for_selector('a[title*="Download"]', timeout=15000)
                await download_button.click()
                
                # Wait for download
                await page.wait_for_timeout(10000)
                
                if not download_happened:
                    print("   ❌ Download didn't trigger")
            
            await browser.close()
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
    
    return downloaded

async def main():
    downloaded = await download_siam_pdfs()
    
    print(f"\n" + "=" * 50)
    print(f"Downloaded {downloaded} PDFs")
    
    if downloaded > 0:
        print("\n🎉 SIAM BROWSER DOWNLOAD WORKS!")
        print("The issue is with session transfer to requests")
    else:
        print("\n⚠️ SIAM browser download needs investigation")

if __name__ == "__main__":
    asyncio.run(main())