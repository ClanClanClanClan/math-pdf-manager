#!/usr/bin/env python3
"""
Final Test: All Four Publishers
===============================

Test IEEE, SIAM, Sci-Hub, and ArXiv with clean slate.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("FINAL TEST: ALL FOUR PUBLISHERS")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

def test_ieee():
    """Test IEEE"""
    print("\n1. IEEE TEST")
    print("-" * 40)
    
    try:
        from src.publishers.ieee_publisher import IEEEPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        print(f"Using ETH credentials: {username[:3]}***")
        
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        ieee = IEEEPublisher(auth_config)
        
        test_doi = "10.1109/5.726791"
        output_path = Path("FINAL_ALL_FOUR") / f"ieee_{test_doi.replace('/', '_')}.pdf"
        output_path.parent.mkdir(exist_ok=True)
        
        print(f"Downloading: {test_doi}")
        result = ieee.download_paper(test_doi, output_path)
        
        if result.success and output_path.exists():
            size_kb = output_path.stat().st_size / 1024
            print(f"✅ SUCCESS: IEEE downloaded {size_kb:.0f} KB")
            return True
        else:
            print(f"❌ FAILED: {result.error_message if hasattr(result, 'error_message') else 'Unknown'}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    return False

async def test_siam():
    """Test SIAM with direct browser automation"""
    print("\n2. SIAM TEST")
    print("-" * 40)
    
    try:
        from playwright.async_api import async_playwright
        from src.secure_credential_manager import get_credential_manager
        
        cm = get_credential_manager()
        username = cm.get_credential("eth_username")
        password = cm.get_credential("eth_password")
        
        print(f"Using ETH credentials: {username[:3]}***")
        
        test_doi = "10.1137/S0097539795293172"
        siam_url = f"https://epubs.siam.org/doi/{test_doi}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate and authenticate (simplified)
            await page.goto(siam_url, timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Click institutional access
            inst_button = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=10000)
            await inst_button.click()
            await page.wait_for_timeout(3000)
            
            # Search ETH
            search_input = await page.wait_for_selector('input#shibboleth_search', timeout=10000)
            await search_input.fill("ETH Zurich")
            await page.wait_for_timeout(2000)
            
            # Click ETH
            eth_option = await page.wait_for_selector('.ms-res-item a:has-text("ETH Zurich")', timeout=5000)
            await eth_option.click()
            await page.wait_for_timeout(5000)
            
            # ETH login
            username_input = await page.wait_for_selector('input[name="j_username"]', timeout=15000)
            await username_input.fill(username)
            
            password_input = await page.wait_for_selector('input[name="j_password"]', timeout=5000)
            await password_input.fill(password)
            
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
            await submit_button.click()
            await page.wait_for_timeout(10000)
            
            # Navigate to PDF
            pdf_url = siam_url.replace('/doi/', '/doi/epdf/')
            await page.goto(pdf_url, timeout=60000)
            await page.wait_for_timeout(8000)
            
            # Set up download
            output_path = Path("FINAL_ALL_FOUR")
            output_path.mkdir(exist_ok=True)
            
            download_happened = False
            downloaded_file = None
            
            async def handle_download(download):
                nonlocal download_happened, downloaded_file
                download_happened = True
                save_path = output_path / download.suggested_filename
                await download.save_as(str(save_path))
                downloaded_file = save_path
            
            page.on('download', handle_download)
            
            # Click download
            download_button = await page.wait_for_selector('a[aria-label*="Download"]', timeout=10000)
            await download_button.click()
            await page.wait_for_timeout(8000)
            
            await browser.close()
            
            if download_happened and downloaded_file and downloaded_file.exists():
                size_kb = downloaded_file.stat().st_size / 1024
                print(f"✅ SUCCESS: SIAM downloaded {size_kb:.0f} KB")
                return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    return False

async def test_scihub():
    """Test Sci-Hub"""
    print("\n3. SCI-HUB TEST")
    print("-" * 40)
    
    try:
        from src.downloader.universal_downloader import SciHubDownloader
        
        sci_hub = SciHubDownloader()
        
        test_doi = "10.1126/science.1102896"
        print(f"Downloading: {test_doi}")
        
        result = await sci_hub.download(test_doi)
        
        if result.success:
            output_path = Path("FINAL_ALL_FOUR") / f"scihub_{test_doi.replace('/', '_')}.pdf"
            
            with open(output_path, 'wb') as f:
                f.write(result.pdf_data)
            
            size_kb = len(result.pdf_data) / 1024
            print(f"✅ SUCCESS: Sci-Hub downloaded {size_kb:.0f} KB")
            
            if hasattr(sci_hub, 'session') and sci_hub.session:
                await sci_hub.session.close()
            
            return True
        else:
            print(f"❌ FAILED: {result.error}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    return False

def test_arxiv():
    """Test ArXiv"""
    print("\n4. ARXIV TEST")
    print("-" * 40)
    
    try:
        import requests
        
        arxiv_id = "1706.03762"  # Transformer paper
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        print(f"Downloading: {arxiv_id}")
        response = requests.get(pdf_url, timeout=30)
        
        if response.status_code == 200 and len(response.content) > 100000:
            output_path = Path("FINAL_ALL_FOUR") / f"arxiv_{arxiv_id}.pdf"
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            size_kb = len(response.content) / 1024
            print(f"✅ SUCCESS: ArXiv downloaded {size_kb:.0f} KB")
            return True
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    return False

async def main():
    """Test all publishers"""
    results = []
    
    # Test each
    results.append(("IEEE", test_ieee()))
    results.append(("SIAM", await test_siam()))
    results.append(("Sci-Hub", await test_scihub()))
    results.append(("ArXiv", test_arxiv()))
    
    # Final summary
    print("\n" + "="*70)
    print("🎯 FINAL ANSWER: ALL FOUR PUBLISHERS STATUS")
    print("="*70)
    
    working_count = sum(1 for _, success in results if success)
    
    print(f"\nRESULT: {working_count}/4 publishers working\n")
    
    for name, success in results:
        status = "✅ WORKING" if success else "❌ FAILED"
        print(f"{status:12} | {name}")
    
    # Verify files
    output_dir = Path("FINAL_ALL_FOUR")
    if output_dir.exists():
        pdfs = list(output_dir.glob("*.pdf"))
        total_size = sum(pdf.stat().st_size for pdf in pdfs)
        
        print(f"\n📊 Downloaded {len(pdfs)} PDFs totaling {total_size/1024:.0f} KB")
        
        for pdf in pdfs:
            size_kb = pdf.stat().st_size / 1024
            print(f"   • {pdf.name} ({size_kb:.0f} KB)")
    
    # Answer the user's question directly
    print(f"\n🎯 ANSWER TO: 'Ok, so arXiv, SIAM, IEEE and sci-hub all work?'")
    if working_count == 4:
        print("✅ YES! All 4 publishers work perfectly!")
    else:
        failed_publishers = [name for name, success in results if not success]
        print(f"❌ {working_count}/4 work. Not working: {', '.join(failed_publishers)}")

if __name__ == "__main__":
    asyncio.run(main())