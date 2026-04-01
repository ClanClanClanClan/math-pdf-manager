#!/usr/bin/env python3
"""
PRACTICAL WILEY DOWNLOADER
==========================

The most practical solution:
1. Checks VPN status automatically
2. Opens VPN client if needed (one click for you)
3. Downloads PDFs automatically once VPN is connected
4. Minimal manual intervention - just one click to connect VPN when prompted

This gives you 95% automation with 5% manual work (just clicking "Connect" in VPN GUI when needed).
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class PracticalWileyDownloader:
    """Practical Wiley downloader with minimal manual VPN work"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.downloads_dir = Path("practical_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize credentials"""
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not (username and password):
                raise Exception("No ETH credentials")
                
            self.credentials = {'username': username, 'password': password}
            print(f"✅ ETH credentials: {username[:3]}***")
            return True
            
        except Exception as e:
            print(f"❌ Credential error: {e}")
            return False
    
    def check_vpn_status(self):
        """Check VPN connection status"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            if "state: Connected" in result.stdout:
                print("✅ VPN connected")
                return True
            else:
                print("❌ VPN not connected")
                return False
                
        except Exception as e:
            print(f"❌ VPN check failed: {e}")
            return False
    
    def smart_vpn_connect(self):
        """Smart VPN connection with minimal manual work"""
        
        if self.check_vpn_status():
            return True
        
        print("\\n🔌 VPN CONNECTION NEEDED")
        print("=" * 50)
        print("Opening Cisco Secure Client for you...")
        
        # Open Cisco Secure Client
        try:
            subprocess.run(['open', '-a', 'Cisco Secure Client'], timeout=10)
            print("✅ Cisco Secure Client opened")
            
            print("\\n📋 Quick Connection Steps:")
            print("1. ✅ App opened for you")
            print("2. 👆 Enter server: vpn.ethz.ch") 
            print("3. 👆 Click Connect")
            print("4. 👆 Enter your ETH credentials + 2FA")
            print("5. ⏳ Wait for connection")
            
            print("\\n⏳ Waiting for VPN connection...")
            print("(Script will continue automatically once connected)")
            
            # Smart waiting with progress
            for i in range(60):  # Wait up to 60 seconds
                time.sleep(1)
                
                if self.check_vpn_status():
                    print("\\n🎉 VPN CONNECTION DETECTED!")
                    return True
                
                # Show progress every 10 seconds
                if (i + 1) % 10 == 0:
                    remaining = 60 - (i + 1)
                    print(f"   ⏳ Still waiting... ({remaining} seconds remaining)")
            
            print("\\n⏰ Connection timeout - please verify VPN status")
            return self.check_vpn_status()
            
        except Exception as e:
            print(f"❌ Could not open Cisco client: {e}")
            print("💡 Please open Cisco Secure Client manually and connect to vpn.ethz.ch")
            return False
    
    async def verify_pdf_access(self):
        """Verify we can access Wiley PDFs"""
        
        print("🔍 Verifying PDF access...")
        
        test_url = "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.202004934"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                response = await page.goto(test_url, timeout=15000)
                
                if response and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower():
                        print("✅ PDF access verified!")
                        await browser.close()
                        return True
                
                print("❌ PDF access blocked")
                await browser.close()
                return False
                
            except Exception as e:
                print(f"❌ Access test failed: {e}")
                await browser.close()
                return False
    
    async def download_wiley_pdf(self, doi, title=""):
        """Download a Wiley PDF"""
        
        print(f"\\n📄 DOWNLOADING: {title or doi}")
        print(f"DOI: {doi}")
        print("-" * 50)
        
        pdf_url = f"https://onlinelibrary.wiley.com/doi/pdf/{doi}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                print("📍 Accessing PDF URL...")
                response = await page.goto(pdf_url, timeout=20000)
                
                if response and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    if 'pdf' in content_type.lower():
                        print("✅ PDF response received")
                        
                        # Get PDF content
                        pdf_buffer = await response.body()
                        
                        if len(pdf_buffer) > 1000:
                            # Save PDF
                            filename = f"wiley_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_buffer)
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"🎉 PDF DOWNLOADED: {save_path} ({size_mb:.2f} MB)")
                            
                            await browser.close()
                            return True
                        else:
                            print(f"❌ PDF too small ({len(pdf_buffer)} bytes)")
                    else:
                        print(f"❌ Not a PDF response: {content_type}")
                        print(f"Status: {response.status}")
                        
                        # Show what we got instead
                        if response.status == 403:
                            print("🔒 Access forbidden - VPN may not be working properly")
                        elif 'html' in content_type.lower():
                            print("📄 Got HTML instead of PDF - may need authentication")
                else:
                    print(f"❌ Bad response: {response.status if response else 'No response'}")
                
                # Keep browser open briefly for inspection if failed
                if response and response.status != 200:
                    print("🔍 Keeping browser open for inspection...")
                    await page.wait_for_timeout(10000)
                
                await browser.close()
                return False
                
            except Exception as e:
                print(f"❌ Download error: {e}")
                await browser.close()
                return False
    
    async def batch_download(self, papers):
        """Download multiple papers"""
        
        print("🚀 PRACTICAL BATCH WILEY DOWNLOADER")
        print("=" * 80)
        print("Minimal manual work - maximum automation!")
        print("=" * 80)
        
        # Ensure VPN connection once at the start
        if not self.smart_vpn_connect():
            print("❌ VPN connection required for downloads")
            return False
        
        # Verify access once
        if not await self.verify_pdf_access():
            print("❌ PDF access verification failed")
            print("💡 VPN may not be working properly")
            return False
        
        print(f"\\n🎯 Starting batch download of {len(papers)} papers...")
        
        successful = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\\n{'='*20} PAPER {i}/{len(papers)} {'='*20}")
            
            # Re-check VPN before each download
            if not self.check_vpn_status():
                print("⚠️ VPN disconnected - reconnecting...")
                if not self.smart_vpn_connect():
                    print("❌ VPN reconnection failed")
                    continue
            
            if isinstance(paper, str):
                doi = paper
                title = ""
            else:
                doi = paper.get('doi', '')
                title = paper.get('title', '')
            
            success = await self.download_wiley_pdf(doi, title)
            
            if success:
                successful += 1
                print(f"✅ PAPER {i} SUCCESS")
            else:
                print(f"❌ PAPER {i} FAILED")
        
        # Final summary
        print(f"\\n{'='*25} FINAL SUMMARY {'='*25}")
        print(f"Papers attempted: {len(papers)}")
        print(f"Successfully downloaded: {successful}")
        print(f"Success rate: {successful/len(papers)*100:.1f}%")
        
        if successful > 0:
            print(f"\\n📁 Downloaded Files:")
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            total_size = 0
            
            for pdf_file in pdf_files:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                total_size += size_mb
                print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            
            print(f"\\n📊 Total: {len(pdf_files)} files, {total_size:.2f} MB")
            print(f"💾 Location: {self.downloads_dir}")
            
            if successful == len(papers):
                print(f"\\n🎉 PERFECT SUCCESS - ALL PAPERS DOWNLOADED!")
            else:
                print(f"\\n✅ PARTIAL SUCCESS - {successful}/{len(papers)} papers downloaded")
        else:
            print(f"\\n❌ NO SUCCESSFUL DOWNLOADS")
            print(f"💡 Check VPN connection and network access")
        
        return successful > 0

async def main():
    """Main function"""
    
    print("🎯 PRACTICAL WILEY DOWNLOADER")
    print("=" * 80)
    print("95% automated - just click Connect in VPN when prompted!")
    print("=" * 80)
    
    downloader = PracticalWileyDownloader()
    
    if not await downloader.initialize():
        return False
    
    # Test with subscription papers
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie - Chemical Synthesis Research'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Economica - Economic Analysis Paper'  
        },
        {
            'doi': '10.1002/adma.202001924',
            'title': 'Advanced Materials - Materials Science Research'
        }
    ]
    
    success = await downloader.batch_download(papers)
    
    if success:
        print(f"\\n🎉 PRACTICAL DOWNLOADER WORKING!")
        print(f"🤖 VPN management: Semi-automatic")
        print(f"📄 PDF downloads: Fully automatic")
        print(f"💪 Manual effort: Minimal (just VPN connect)")
    else:
        print(f"\\n❌ Downloads failed - check VPN and network")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())