#!/usr/bin/env python3
"""
COMPLETE AUTO VPN + PDF
=======================

Bulletproof VPN connection with automatic PDF downloads
Combines all our solutions into one ultra-robust system
"""

import subprocess
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from bulletproof_vpn_connect import BulletproofVPNConnect
from twofa_automation import TwoFAAutomation
from secure_vpn_credentials import get_vpn_password

class CompleteAutoPDFSystem:
    """Complete automatic VPN + PDF download system"""
    
    def __init__(self):
        print("🚀 COMPLETE AUTOMATIC VPN + PDF SYSTEM")
        print("=" * 70)
        print("Features:")
        print("✓ Bulletproof Connect button clicking")
        print("✓ Automatic password entry")
        print("✓ 2FA automation options")
        print("✓ Full PDF downloads")
        print("=" * 70)
        
        self.vpn_connector = BulletproofVPNConnect()
        self.twofa_handler = TwoFAAutomation()
        self.downloads_dir = Path("automatic_pdfs")
        self.downloads_dir.mkdir(exist_ok=True)
        
    def connect_vpn_automatically(self):
        """Connect VPN with full automation"""
        print("\n🔐 PHASE 1: AUTOMATIC VPN CONNECTION")
        print("=" * 50)
        
        # Check if already connected
        if self.check_vpn_status():
            print("✅ VPN already connected!")
            return True
        
        # Launch Cisco
        self.vpn_connector.launch_cisco_reliably()
        
        # Find and click Connect
        positions = self.vpn_connector.find_connect_button_visually()
        self.vpn_connector.click_connect_bulletproof(positions)
        
        # Auto-enter password
        self.vpn_connector.auto_enter_password()
        
        # Handle 2FA automatically
        print("\n🔑 Attempting automatic 2FA...")
        self.twofa_handler.auto_2fa_with_best_method()
        
        # Monitor connection
        return self.vpn_connector.monitor_connection()
    
    def check_vpn_status(self):
        """Check if VPN is connected"""
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=5
            )
            return "state: Connected" in result.stdout
        except:
            return False
    
    async def download_pdf_automatically(self, doi, journal):
        """Download PDF with full automation"""
        print(f"\n📄 Downloading: {journal}")
        print(f"DOI: {doi}")
        
        url = f"https://onlinelibrary.wiley.com/doi/{doi}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Show browser for debugging
                downloads_path=str(self.downloads_dir)
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                accept_downloads=True
            )
            
            page = await context.new_page()
            
            download_completed = False
            download_path = None
            
            async def handle_download(download):
                nonlocal download_completed, download_path
                filename = f"{doi.replace('/', '_').replace('.', '_')}.pdf"
                save_path = self.downloads_dir / filename
                await download.save_as(save_path)
                download_path = save_path
                download_completed = True
                print(f"✅ Downloaded to: {save_path}")
            
            page.on("download", handle_download)
            
            try:
                # Navigate to paper
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Accept cookies
                try:
                    await page.click('button:has-text("Accept")', timeout=3000)
                except:
                    pass
                
                # Find and click PDF link
                pdf_selectors = [
                    'a[href*="epdf"]',
                    'a[title*="PDF"]',
                    'button:has-text("PDF")',
                    '.pdf-download',
                    'a:has-text("Download PDF")'
                ]
                
                for selector in pdf_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000)
                        if element:
                            await element.click()
                            await page.wait_for_timeout(5000)
                            
                            if download_completed:
                                size_mb = download_path.stat().st_size / (1024 * 1024)
                                print(f"✅ Downloaded: {size_mb:.2f} MB")
                                await browser.close()
                                return download_path
                            
                            # Check for PDF viewer
                            for p in context.pages:
                                if 'pdf' in p.url or 'epdf' in p.url:
                                    # Try Ctrl+S
                                    await p.keyboard.press('Control+s')
                                    await page.wait_for_timeout(3000)
                                    
                                    if download_completed:
                                        size_mb = download_path.stat().st_size / (1024 * 1024)
                                        print(f"✅ Downloaded via viewer: {size_mb:.2f} MB")
                                        await browser.close()
                                        return download_path
                            break
                    except:
                        continue
                
                print("⚠️ Automatic download failed")
                await asyncio.sleep(20)  # Give time for manual download
                
            except Exception as e:
                print(f"❌ Error: {e}")
            
            finally:
                await browser.close()
        
        return download_path
    
    async def run_complete_automation(self):
        """Run the complete automated workflow"""
        
        # Phase 1: Connect VPN
        vpn_connected = self.connect_vpn_automatically()
        
        if not vpn_connected:
            print("\n❌ VPN connection failed")
            return False
        
        print("\n✅ VPN CONNECTED SUCCESSFULLY!")
        
        # Phase 2: Download PDFs
        print("\n📚 PHASE 2: AUTOMATIC PDF DOWNLOADS")
        print("=" * 50)
        
        papers = [
            {'doi': '10.1111/mafi.12456', 'journal': 'Mathematical Finance'},
            {'doi': '10.3982/ECTA20404', 'journal': 'Econometrica'},
            {'doi': '10.3982/ECTA20411', 'journal': 'Econometrica'},
            {'doi': '10.1111/jofi.13412', 'journal': 'Journal of Finance'},
        ]
        
        successful = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{'='*20} Paper {i}/{len(papers)} {'='*20}")
            
            result = await self.download_pdf_automatically(
                paper['doi'], 
                paper['journal']
            )
            
            if result:
                successful += 1
            
            # Delay between downloads
            if i < len(papers):
                print("⏳ Waiting 10s before next download...")
                await asyncio.sleep(10)
        
        # Final summary
        print(f"\n{'='*70}")
        print(f"🏆 COMPLETE AUTOMATION RESULTS")
        print(f"✅ VPN: Connected automatically")
        print(f"✅ Password: Entered from secure storage")
        print(f"✅ PDFs: {successful}/{len(papers)} downloaded")
        print(f"📁 Location: {self.downloads_dir}")
        print("=" * 70)
        
        return successful > 0

async def main():
    """Main execution"""
    
    # Check prerequisites
    print("🔍 Checking prerequisites...")
    
    # Check for stored password
    password = get_vpn_password()
    if not password:
        print("❌ No password stored!")
        print("Run: python secure_vpn_credentials.py")
        return
    else:
        print("✅ Password loaded from secure storage")
    
    # Check for cliclick
    try:
        subprocess.run(["which", "cliclick"], check=True, capture_output=True)
        print("✅ cliclick installed")
    except:
        print("📦 Installing cliclick...")
        subprocess.run(["brew", "install", "cliclick"])
    
    # Run complete automation
    system = CompleteAutoPDFSystem()
    success = await system.run_complete_automation()
    
    if success:
        print("\n🎉 COMPLETE AUTOMATION SUCCESS!")
        print("✅ VPN connected automatically")
        print("✅ PDFs downloaded automatically")
        print("\n🧠 ULTRATHINKING ACHIEVED!")
    else:
        print("\n⚠️ Automation completed with issues")
        print("Check debug screenshots for troubleshooting")

if __name__ == "__main__":
    asyncio.run(main())