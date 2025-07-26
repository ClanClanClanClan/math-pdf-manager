#!/usr/bin/env python3
"""
SIAM Working Final
==================

Complete working SIAM implementation with the correct flow:
1. Click "GET ACCESS" 
2. Click "Access via your Institution" in the modal
3. Search for ETH in shibboleth
4. Complete authentication and download
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def siam_working_final():
    print("🎯 FINAL WORKING SIAM IMPLEMENTATION")
    print("=" * 50)
    
    # Get credentials
    try:
        from src.secure_credential_manager import get_credential_manager
        
        cm = get_credential_manager()
        username = cm.get_credential("eth_username")
        password = cm.get_credential("eth_password")
        
        if not username or not password:
            print("❌ No ETH credentials for SIAM")
            return False
            
        print(f"✅ Using ETH credentials: {username[:3]}***")
            
    except ImportError as e:
        print(f"❌ Cannot import credentials: {e}")
        return False
    
    # Test paper
    test_doi = "10.1137/S0097539795293172" 
    test_title = "Shor's Quantum Factoring Algorithm"
    
    print(f"\nDownloading: {test_doi}")
    print(f"Title: {test_title}")
    
    try:
        async with async_playwright() as p:
            # Simple browser setup
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            print("\n🔄 STEP 1: Navigate to SIAM paper")
            siam_url = f"https://epubs.siam.org/doi/{test_doi}"
            await page.goto(siam_url, timeout=90000)
            await page.wait_for_timeout(5000)
            print("   ✓ Page loaded")
            
            print("\n🔄 STEP 2: Click GET ACCESS button")
            access_button = await page.wait_for_selector('a:has-text("GET ACCESS")', timeout=15000)
            await access_button.click()
            await page.wait_for_timeout(5000)
            print("   ✓ GET ACCESS clicked - modal should appear")
            
            print("\n🔄 STEP 3: Click 'Access via your Institution' in modal")
            # The key step I was missing!
            inst_link = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=15000)
            await inst_link.click()
            await page.wait_for_timeout(8000)
            print("   ✓ Institutional access clicked")
            
            print("\n🔄 STEP 4: Search for ETH Zurich")
            search_input = await page.wait_for_selector('input#shibboleth_search', timeout=20000)
            await search_input.click()
            await search_input.fill("")
            await page.wait_for_timeout(1000)
            await search_input.type("ETH Zurich", delay=150)
            await page.wait_for_timeout(5000)
            print("   ✓ Typed ETH Zurich")
            
            print("\n🔄 STEP 5: Click ETH Zurich option")
            eth_option = await page.wait_for_selector('.ms-res-item a.sso-institution:has-text("ETH Zurich")', timeout=15000)
            await eth_option.click()
            await page.wait_for_timeout(10000)
            print("   ✓ ETH Zurich selected")
            
            print("\n🔄 STEP 6: ETH Login")
            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=30000)
            await username_input.fill(username)
            
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
            await password_input.fill(password)
            
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
            await submit_button.click()
            await page.wait_for_timeout(20000)
            print("   ✓ ETH credentials submitted")
            
            print("\n🔄 STEP 7: Navigate to PDF")
            pdf_url = siam_url.replace('/doi/', '/doi/epdf/')
            await page.goto(pdf_url, timeout=90000)
            await page.wait_for_timeout(15000)
            print("   ✓ Navigated to PDF URL")
            
            print("\n🔄 STEP 8: Download PDF")
            # Setup download handler
            download_happened = False
            downloaded_file = None
            output_dir = Path("siam_working_final")
            output_dir.mkdir(exist_ok=True)
            
            async def handle_download(download):
                nonlocal download_happened, downloaded_file
                download_happened = True
                filename = f"siam_{test_doi.replace('/', '_').replace('.', '_')}_WORKING.pdf"
                save_path = output_dir / filename
                await download.save_as(str(save_path))
                downloaded_file = save_path
                print(f"   ✓ Download handler triggered: {save_path.name}")
            
            page.on('download', handle_download)
            
            # Click download button
            download_button = await page.wait_for_selector('a[title*="Download"]', timeout=15000)
            await download_button.click()
            await page.wait_for_timeout(15000)
            print("   ✓ Download button clicked")
            
            # Verify download
            if download_happened and downloaded_file and downloaded_file.exists():
                with open(downloaded_file, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'%PDF'):
                        size_kb = downloaded_file.stat().st_size / 1024
                        print(f"\n🎉 SUCCESS! Downloaded: {downloaded_file.name} ({size_kb:.0f} KB)")
                        await browser.close()
                        return True
                    else:
                        print(f"\n❌ Invalid PDF format")
            else:
                print(f"\n❌ No download occurred")
            
            await browser.close()
            return False
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        return False

async def main():
    success = await siam_working_final()
    
    if success:
        print("\n🎉 SIAM FLOW COMPLETED SUCCESSFULLY!")
        print("The complete working flow is now implemented!")
    else:
        print("\n❌ SIAM flow still has issues")

if __name__ == "__main__":
    asyncio.run(main())