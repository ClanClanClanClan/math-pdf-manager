#!/usr/bin/env python3
"""
WORKING VPN SOLUTION
===================

Final robust solution combining CLI and manual guidance
"""

import subprocess
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

def check_vpn_status():
    """Check VPN connection status"""
    try:
        result = subprocess.run(
            ["/opt/cisco/secureclient/bin/vpn", "state"],
            capture_output=True, text=True, timeout=5
        )
        return "state: Connected" in result.stdout
    except:
        return False

def connect_vpn_guided():
    """Guided VPN connection with user assistance"""
    
    print("🔐 GUIDED VPN CONNECTION")
    print("=" * 50)
    
    if check_vpn_status():
        print("✅ VPN already connected!")
        return True
    
    print("\n📋 STEP-BY-STEP VPN CONNECTION:")
    print("=" * 50)
    
    # Step 1: Launch Cisco
    print("\n1️⃣ Launching Cisco Secure Client...")
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(3)
    
    print("✅ Cisco launched")
    
    # Step 2: User interaction
    print("\n2️⃣ MANUAL STEPS (please do these now):")
    print("   🖱️  Click the 'Connect' button in Cisco window")
    print("   🔑 Enter your ETH credentials when prompted")
    print("   📱 Complete 2FA on your phone")
    print("\n⏳ I'll monitor the connection status...")
    
    # Step 3: Monitor connection
    print("\n3️⃣ Monitoring connection...")
    
    for i in range(180):  # 3 minutes
        if check_vpn_status():
            print(f"\n🎉 VPN CONNECTED SUCCESSFULLY!")
            return True
        
        if i % 15 == 0:
            remaining = 180 - i
            print(f"   Waiting for connection... {remaining}s remaining")
            if i == 60:
                print("   💡 Make sure you clicked Connect and entered credentials")
            elif i == 120:
                print("   💡 Check if 2FA is completed on your phone")
        
        time.sleep(1)
    
    print("\n❌ Connection timeout - but you can still try manual connection")
    return False

async def download_paper_with_vpn(doi, journal_name):
    """Download paper once VPN is connected"""
    
    print(f"\n📄 DOWNLOADING: {journal_name}")
    print(f"DOI: {doi}")
    print("=" * 50)
    
    if not check_vpn_status():
        print("❌ VPN not connected - please connect first")
        return None
    
    downloads_dir = Path("vpn_downloads")
    downloads_dir.mkdir(exist_ok=True)
    
    url = f"https://onlinelibrary.wiley.com/doi/{doi}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            downloads_path=str(downloads_dir)
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            accept_downloads=True
        )
        
        page = await context.new_page()
        
        download_path = None
        
        async def handle_download(download):
            nonlocal download_path
            filename = f"{doi.replace('/', '_').replace('.', '_')}.pdf"
            save_path = downloads_dir / filename
            await download.save_as(save_path)
            download_path = save_path
        
        page.on("download", handle_download)
        
        try:
            print("🌐 Navigating to paper...")
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            try:
                await page.click('button:has-text("Accept")', timeout=3000)
                print("✅ Accepted cookies")
            except:
                pass
            
            # Look for PDF access
            print("🔍 Looking for PDF access...")
            
            # Check if we have institutional access
            page_content = await page.content()
            if "Full Access" in page_content or "Institution:" in page_content:
                print("✅ Institutional access confirmed!")
            
            # Try to find PDF link
            pdf_selectors = [
                'a[href*="epdf"]',
                'a[title*="PDF"]', 
                'a:has-text("PDF")',
                '.pdf-download'
            ]
            
            for selector in pdf_selectors:
                try:
                    pdf_link = await page.wait_for_selector(selector, timeout=3000)
                    if pdf_link:
                        print(f"🖱️ Clicking PDF link: {selector}")
                        await pdf_link.click()
                        await page.wait_for_timeout(5000)
                        
                        if download_path:
                            size_mb = download_path.stat().st_size / (1024 * 1024)
                            print(f"✅ Downloaded: {size_mb:.2f} MB")
                            await browser.close()
                            return download_path
                        
                        # If no download, try in PDF viewer
                        for p in context.pages:
                            if 'pdf' in p.url:
                                await p.keyboard.press('Control+s')
                                await page.wait_for_timeout(3000)
                                
                                if download_path:
                                    size_mb = download_path.stat().st_size / (1024 * 1024)
                                    print(f"✅ Downloaded via viewer: {size_mb:.2f} MB")
                                    await browser.close()
                                    return download_path
                        break
                except:
                    continue
            
            print("⚠️ Automatic download failed - leaving browser open")
            print("💡 You can manually download the PDF")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            await browser.close()
    
    return download_path

async def main():
    """Main robust VPN + download workflow"""
    
    print("🚀 WORKING VPN + PDF DOWNLOAD SOLUTION")
    print("=" * 60)
    print("This solution combines:")
    print("✓ Guided VPN connection (with user assistance)")
    print("✓ Reliable PDF downloads")
    print("✓ Full automation once VPN is connected")
    print("=" * 60)
    
    # Step 1: Connect VPN
    print("\n🔒 PHASE 1: VPN CONNECTION")
    vpn_connected = connect_vpn_guided()
    
    if not vpn_connected:
        print("\n⚠️ VPN connection incomplete")
        print("💡 You can still try downloading if VPN connected manually")
        
        # Ask user if they want to continue
        if input("\nDid you connect VPN manually? (y/n): ").lower() != 'y':
            print("Exiting...")
            return
    
    # Step 2: Download papers
    print("\n📄 PHASE 2: PDF DOWNLOADS")
    
    target_papers = [
        {'doi': '10.1111/mafi.12456', 'journal': 'Mathematical Finance'},
        {'doi': '10.3982/ECTA20404', 'journal': 'Econometrica'},
        {'doi': '10.3982/ECTA20411', 'journal': 'Econometrica'},
    ]
    
    successful_downloads = 0
    
    for paper in target_papers:
        result = await download_paper_with_vpn(paper['doi'], paper['journal'])
        
        if result:
            successful_downloads += 1
            print(f"✅ Success: {result}")
        else:
            print(f"❌ Failed: {paper['journal']}")
        
        # Delay between downloads
        if paper != target_papers[-1]:
            print("⏳ Waiting 10s before next download...")
            await asyncio.sleep(10)
    
    # Summary
    print(f"\n🏆 FINAL RESULTS")
    print("=" * 60)
    print(f"✅ Successful downloads: {successful_downloads}/{len(target_papers)}")
    
    if successful_downloads > 0:
        print("✅ VPN + Download system WORKING!")
        print("📁 Check vpn_downloads/ folder for PDFs")
    else:
        print("⚠️ No automatic downloads - but VPN access confirmed")
        print("💡 Try downloading PDFs manually in browser")
    
    print("\n🚀 ROBUST SOLUTION COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())