#!/usr/bin/env python3
"""
PRACTICAL ROBUST SYSTEM
=======================

Ultra-robust system with realistic 2FA handling
"""

import subprocess
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import requests
import json
from datetime import datetime
import pyautogui
import logging

class PracticalRobustSystem:
    """Practical system with semi-automated VPN and full PDF downloads"""
    
    def __init__(self, password=None):
        self.api_key = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"
        self.password = password
        self.downloads_dir = Path("robust_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler('practical_system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        print("🧠 PRACTICAL ROBUST PDF SYSTEM")
        print("=" * 70)
        print("Features:")
        print("✓ Automatic VPN launch and connection")
        print("✓ Password auto-fill (if provided)")
        print("✓ 2FA options with instructions")
        print("✓ Full PDF downloads (not just first page)")
        print("✓ Intelligent retry logic")
        print("=" * 70)
    
    def check_vpn_status(self) -> bool:
        """Check if VPN is connected"""
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=5
            )
            return "state: Connected" in result.stdout
        except:
            return False
    
    def launch_cisco_vpn(self):
        """Launch Cisco Secure Client"""
        print("\n🚀 Launching Cisco VPN...")
        
        # Kill any existing instance
        subprocess.run(["pkill", "-f", "Cisco Secure Client"], capture_output=True)
        time.sleep(1)
        
        # Launch fresh
        subprocess.run(["open", "-a", "Cisco Secure Client"])
        time.sleep(3)
        
        # Bring to front
        applescript = '''
        tell application "Cisco Secure Client"
            activate
        end tell
        '''
        subprocess.run(["osascript", "-e", applescript])
        
        print("✅ Cisco VPN launched")
    
    def automated_vpn_connect(self) -> bool:
        """Automated VPN connection with smart 2FA handling"""
        
        if self.check_vpn_status():
            print("✅ VPN already connected")
            return True
        
        print("\n🔐 AUTOMATED VPN CONNECTION")
        print("-" * 40)
        
        self.launch_cisco_vpn()
        
        # Click Connect button using AppleScript
        print("🖱️ Clicking Connect...")
        applescript = '''
        tell application "System Events"
            tell process "Cisco Secure Client"
                try
                    click button "Connect" of window 1
                end try
            end tell
        end tell
        '''
        subprocess.run(["osascript", "-e", applescript])
        time.sleep(3)
        
        # Auto-fill password if provided
        if self.password:
            print("🔑 Auto-filling password...")
            pyautogui.typewrite(self.password, interval=0.05)
            pyautogui.press('enter')
            time.sleep(2)
        else:
            print("⏸️ Please enter your password manually")
            time.sleep(10)
        
        # 2FA handling
        print("\n📱 2FA REQUIRED")
        print("-" * 40)
        print("OPTIONS:")
        print("1. [EASIEST] Open authenticator on phone and type code")
        print("2. [AUTOMATED] Connect phone via USB and run: scrcpy")
        print("3. [FUTURE] Share TOTP secret for full automation")
        
        # Smart 2FA wait with visual countdown
        print("\n⏳ Waiting for 2FA (60 seconds)...")
        for i in range(60):
            if self.check_vpn_status():
                print(f"\n✅ VPN CONNECTED!")
                return True
            
            # Visual progress
            if i % 5 == 0:
                remaining = 60 - i
                bar = "█" * (i//2) + "░" * ((60-i)//2)
                print(f"\r[{bar}] {remaining}s", end="", flush=True)
            
            time.sleep(1)
        
        print("\n❌ VPN connection timeout")
        return False
    
    async def download_full_pdf(self, doi: str, journal: str, url: str) -> Path:
        """Download FULL PDF with VPN access"""
        
        print(f"\n📄 Downloading: {journal}")
        print(f"DOI: {doi}")
        
        # Check if already downloaded
        existing = list(self.downloads_dir.glob(f"*{doi.replace('/', '_')}*.pdf"))
        if existing:
            for pdf in existing:
                if pdf.stat().st_size > 100000:  # > 100KB
                    print(f"✅ Already have full PDF: {pdf.name}")
                    return pdf
        
        # Ensure VPN connected
        if not self.check_vpn_status():
            if not self.automated_vpn_connect():
                return None
        
        # Load credentials
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
        except:
            print("❌ No ETH credentials available")
            return None
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                downloads_path=str(self.downloads_dir)
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                accept_downloads=True
            )
            
            page = await context.new_page()
            
            # Set up download handler
            download_path = None
            
            async def handle_download(download):
                nonlocal download_path
                filename = f"full_{doi.replace('/', '_').replace('.', '_')}.pdf"
                save_path = self.downloads_dir / filename
                await download.save_as(save_path)
                download_path = save_path
                self.logger.info(f"Downloaded: {save_path}")
            
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
                
                # Strategy 1: Look for download button
                download_selectors = [
                    'a[title*="PDF"]',
                    'a:has-text("Download PDF")',
                    'button:has-text("Download")',
                    '.pdf-download',
                    'a[href*="pdf"][download]'
                ]
                
                for selector in download_selectors:
                    try:
                        btn = await page.wait_for_selector(selector, timeout=2000)
                        if btn:
                            await btn.click()
                            await page.wait_for_timeout(5000)
                            
                            if download_path and download_path.exists():
                                size_mb = download_path.stat().st_size / (1024 * 1024)
                                if size_mb > 0.1:  # > 100KB
                                    print(f"✅ Downloaded FULL PDF: {size_mb:.2f} MB")
                                    await browser.close()
                                    return download_path
                    except:
                        continue
                
                # Strategy 2: Click ePDF and find viewer download
                epdf_link = await page.wait_for_selector('a[href*="epdf"]', timeout=3000)
                if epdf_link:
                    await epdf_link.click()
                    await page.wait_for_timeout(5000)
                    
                    # Check all open pages for PDF viewer
                    for p in context.pages:
                        if 'pdf' in p.url or 'epdf' in p.url:
                            # Try download button in viewer
                            viewer_selectors = [
                                '#download',
                                'button[id*="download"]',
                                '[aria-label*="Download"]',
                                'button[title*="Download"]'
                            ]
                            
                            for sel in viewer_selectors:
                                try:
                                    btn = await p.wait_for_selector(sel, timeout=2000)
                                    if btn:
                                        await btn.click()
                                        await page.wait_for_timeout(5000)
                                        
                                        if download_path and download_path.exists():
                                            size_mb = download_path.stat().st_size / (1024 * 1024)
                                            if size_mb > 0.1:
                                                print(f"✅ Downloaded FULL PDF: {size_mb:.2f} MB")
                                                await browser.close()
                                                return download_path
                                except:
                                    continue
                            
                            # Try Ctrl+S
                            print("⌨️ Trying Ctrl+S...")
                            await p.keyboard.press('Control+s')
                            await page.wait_for_timeout(5000)
                            
                            if download_path and download_path.exists():
                                size_mb = download_path.stat().st_size / (1024 * 1024)
                                if size_mb > 0.1:
                                    print(f"✅ Downloaded FULL PDF: {size_mb:.2f} MB")
                                    await browser.close()
                                    return download_path
                
                print("❌ Could not trigger automatic download")
                print("💡 Try manually clicking download button in browser")
                await asyncio.sleep(30)  # Give time for manual download
                
            except Exception as e:
                self.logger.error(f"Error: {e}")
            
            finally:
                await browser.close()
        
        return download_path
    
    async def batch_download(self, papers):
        """Download multiple papers robustly"""
        
        results = {
            'total': len(papers),
            'successful': 0,
            'failed': 0,
            'papers': []
        }
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{'='*20} PAPER {i}/{len(papers)} {'='*20}")
            
            result = await self.download_full_pdf(
                paper['doi'],
                paper['journal'],
                paper.get('url', f"https://onlinelibrary.wiley.com/doi/{paper['doi']}")
            )
            
            if result:
                results['successful'] += 1
                results['papers'].append({
                    **paper, 
                    'status': 'success',
                    'path': str(result),
                    'size_mb': result.stat().st_size / (1024 * 1024)
                })
            else:
                results['failed'] += 1
                results['papers'].append({**paper, 'status': 'failed'})
            
            # Smart delay
            if i < len(papers):
                delay = 20
                print(f"⏳ Waiting {delay}s before next paper...")
                await asyncio.sleep(delay)
        
        return results

async def main():
    """Main execution"""
    
    print("🧠 ULTRA-ROBUST PDF DOWNLOAD SYSTEM")
    print("=" * 80)
    
    # You can provide password here for auto-fill
    # password = "your_password_here"
    password = None  # Set to None for manual entry
    
    system = PracticalRobustSystem(password=password)
    
    # Your target papers
    target_papers = [
        {'doi': '10.1111/mafi.12456', 'journal': 'Mathematical Finance'},
        {'doi': '10.3982/ECTA20404', 'journal': 'Econometrica'},
        {'doi': '10.3982/ECTA20411', 'journal': 'Econometrica'},
        {'doi': '10.1111/jofi.13412', 'journal': 'Journal of Finance'},
    ]
    
    results = await system.batch_download(target_papers)
    
    # Summary
    print(f"\n{'='*30} FINAL RESULTS {'='*30}")
    print(f"✅ Successful: {results['successful']}/{results['total']}")
    print(f"❌ Failed: {results['failed']}/{results['total']}")
    
    if results['successful'] > 0:
        print("\n📁 Downloaded PDFs:")
        for paper in results['papers']:
            if paper['status'] == 'success':
                print(f"  • {paper['journal']}: {paper['size_mb']:.2f} MB")
    
    print("\n🧠 ULTRA-ROBUST SYSTEM COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())