#!/usr/bin/env python3
"""
ROBUST PDF DOWNLOAD SYSTEM
==========================

ULTRATHINKING: A truly robust system that handles everything
"""

import subprocess
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

class RobustPDFSystem:
    """Robust system combining all methods intelligently"""
    
    def __init__(self):
        self.api_key = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"
        self.tdm_base_url = "https://api.wiley.com/onlinelibrary/tdm/v1/articles/"
        self.downloads_dir = Path("robust_pdfs")
        self.downloads_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('robust_pdf_system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Track success rates
        self.journal_stats = self.load_journal_stats()
        
        print("🧠 ROBUST PDF SYSTEM - ULTRATHINKING APPROACH")
        print("=" * 60)
        
    def load_journal_stats(self) -> Dict:
        """Load historical success rates"""
        stats_file = Path("journal_stats.json")
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                return json.load(f)
        return {}
        
    def save_journal_stats(self):
        """Save journal statistics"""
        with open("journal_stats.json", 'w') as f:
            json.dump(self.journal_stats, f, indent=2)
    
    def try_api_method(self, doi: str, journal: str) -> Optional[Path]:
        """Try API method first (fastest)"""
        
        self.logger.info(f"Trying API for {doi}")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'ETH-Research/1.0',
            'Accept': 'application/pdf',
            'X-API-Key': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Wiley-TDM-Client-Token': self.api_key,
        })
        
        try:
            url = f"{self.tdm_base_url}{doi}"
            response = session.get(url, timeout=30)
            
            if response.status_code == 200 and len(response.content) > 1000:
                filename = f"api_{doi.replace('/', '_').replace('.', '_')}.pdf"
                save_path = self.downloads_dir / filename
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                self.logger.info(f"✅ API SUCCESS: {save_path}")
                self.update_stats(journal, 'api', True)
                return save_path
            
            else:
                self.logger.warning(f"API failed: HTTP {response.status_code}")
                self.update_stats(journal, 'api', False)
                return None
                
        except Exception as e:
            self.logger.error(f"API error: {e}")
            self.update_stats(journal, 'api', False)
            return None
    
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
    
    def semi_automated_vpn_connect(self) -> bool:
        """Semi-automated VPN connection with user interaction for 2FA"""
        
        print("\n🔐 VPN CONNECTION REQUIRED")
        print("-" * 40)
        
        if self.check_vpn_status():
            print("✅ VPN already connected")
            return True
        
        print("📱 SETUP REQUIRED (one-time):")
        print("1. Install 'scrcpy' for phone mirroring: brew install scrcpy")
        print("2. Or use 'Pushbullet' for notification mirroring")
        print("3. Or position phone under webcam")
        
        print("\n🔄 Starting VPN connection...")
        
        # Launch Cisco GUI
        subprocess.run(["open", "-a", "Cisco Secure Client"])
        time.sleep(2)
        
        # Try AppleScript for basic automation
        applescript = '''
        tell application "Cisco Secure Client"
            activate
        end tell
        
        tell application "System Events"
            tell process "Cisco Secure Client"
                -- Click Connect if visible
                try
                    click button "Connect" of window 1
                end try
            end tell
        end tell
        '''
        
        subprocess.run(["osascript", "-e", applescript])
        
        print("\n⏳ Waiting for 2FA prompt...")
        print("📱 Options for 2FA:")
        print("1. [MANUAL] Enter code when prompted")
        print("2. [SEMI-AUTO] Run: scrcpy --window-title Phone")
        print("3. [FUTURE] Set up TOTP secret sharing")
        
        # Wait for user to complete 2FA
        for i in range(60):  # 60 second timeout
            if self.check_vpn_status():
                print("\n✅ VPN connected successfully!")
                return True
            time.sleep(1)
            if i % 10 == 0:
                print(f"⏳ Waiting... {60-i}s remaining")
        
        print("❌ VPN connection timeout")
        return False
    
    async def try_vpn_method(self, doi: str, journal: str, url: str) -> Optional[Path]:
        """Try VPN + browser method"""
        
        self.logger.info(f"Trying VPN method for {doi}")
        
        # Ensure VPN is connected
        if not self.check_vpn_status():
            if not self.semi_automated_vpn_connect():
                return None
        
        # Load credentials
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
        except:
            self.logger.error("No credentials available")
            return None
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Show browser for debugging
                downloads_path=str(self.downloads_dir)
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            try:
                # Navigate to paper
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Accept cookies
                try:
                    await page.click('button:has-text("Accept")', timeout=3000)
                except:
                    pass
                
                # Click ePDF link
                epdf_link = await page.wait_for_selector('a[href*="epdf"]', timeout=5000)
                if epdf_link:
                    await epdf_link.click()
                    await page.wait_for_timeout(5000)
                    
                    # Handle Cloudflare if needed
                    if "Verify you are human" in await page.content():
                        print("⚠️ Cloudflare protection - manual intervention needed")
                        print("Please complete the captcha...")
                        await page.wait_for_timeout(20000)  # 20s for manual captcha
                    
                    # Now try to get PDF
                    all_pages = context.pages
                    for p in all_pages:
                        if 'pdf' in p.url:
                            # Save PDF
                            pdf_buffer = await p.pdf(format='A4')
                            filename = f"vpn_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_buffer)
                            
                            if save_path.stat().st_size > 50000:  # > 50KB
                                self.logger.info(f"✅ VPN SUCCESS: {save_path}")
                                self.update_stats(journal, 'vpn', True)
                                await browser.close()
                                return save_path
                
                await browser.close()
                self.update_stats(journal, 'vpn', False)
                return None
                
            except Exception as e:
                self.logger.error(f"VPN method error: {e}")
                await browser.close()
                self.update_stats(journal, 'vpn', False)
                return None
    
    def update_stats(self, journal: str, method: str, success: bool):
        """Update journal statistics"""
        if journal not in self.journal_stats:
            self.journal_stats[journal] = {
                'api': {'attempts': 0, 'successes': 0},
                'vpn': {'attempts': 0, 'successes': 0}
            }
        
        self.journal_stats[journal][method]['attempts'] += 1
        if success:
            self.journal_stats[journal][method]['successes'] += 1
        
        self.save_journal_stats()
    
    def get_best_method(self, journal: str) -> str:
        """Determine best method based on historical data"""
        if journal not in self.journal_stats:
            return 'api'  # Default to API
        
        stats = self.journal_stats[journal]
        
        # Calculate success rates
        api_rate = 0
        if stats['api']['attempts'] > 0:
            api_rate = stats['api']['successes'] / stats['api']['attempts']
        
        vpn_rate = 0
        if stats['vpn']['attempts'] > 0:
            vpn_rate = stats['vpn']['successes'] / stats['vpn']['attempts']
        
        # Prefer API if success rate > 50%
        if api_rate > 0.5:
            return 'api'
        # Use VPN if it has better success rate
        elif vpn_rate > api_rate:
            return 'vpn'
        else:
            return 'api'  # Default
    
    async def download_paper(self, doi: str, journal: str, url: str) -> Optional[Path]:
        """Download paper using best method"""
        
        print(f"\n📄 Downloading: {journal}")
        print(f"DOI: {doi}")
        
        # Check existing downloads
        existing = list(self.downloads_dir.glob(f"*{doi.replace('/', '_').replace('.', '_')}*.pdf"))
        if existing:
            print(f"✅ Already downloaded: {existing[0]}")
            return existing[0]
        
        # Determine best method
        best_method = self.get_best_method(journal)
        print(f"📊 Best method based on history: {best_method}")
        
        # Try best method first
        if best_method == 'api':
            result = self.try_api_method(doi, journal)
            if result:
                return result
            # Fallback to VPN
            result = await self.try_vpn_method(doi, journal, url)
            if result:
                return result
        else:
            result = await self.try_vpn_method(doi, journal, url)
            if result:
                return result
            # Fallback to API
            result = self.try_api_method(doi, journal)
            if result:
                return result
        
        print(f"❌ Failed to download {doi}")
        return None
    
    async def batch_download(self, papers: List[Dict]) -> Dict:
        """Download multiple papers intelligently"""
        
        results = {
            'total': len(papers),
            'successful': 0,
            'failed': 0,
            'papers': []
        }
        
        # Sort papers by predicted success rate
        sorted_papers = sorted(papers, 
                             key=lambda p: self.get_success_probability(p['journal']), 
                             reverse=True)
        
        for i, paper in enumerate(sorted_papers, 1):
            print(f"\n{'='*20} PAPER {i}/{len(papers)} {'='*20}")
            
            result = await self.download_paper(
                paper['doi'],
                paper['journal'],
                paper.get('url', f"https://onlinelibrary.wiley.com/doi/{paper['doi']}")
            )
            
            if result:
                results['successful'] += 1
                results['papers'].append({**paper, 'status': 'success', 'path': str(result)})
            else:
                results['failed'] += 1
                results['papers'].append({**paper, 'status': 'failed'})
            
            # Intelligent delay
            if i < len(papers):
                delay = 10 if results['successful'] / i > 0.8 else 30
                print(f"⏳ Waiting {delay}s before next paper...")
                await asyncio.sleep(delay)
        
        return results
    
    def get_success_probability(self, journal: str) -> float:
        """Get predicted success probability for a journal"""
        if journal not in self.journal_stats:
            return 0.5  # Unknown journal
        
        stats = self.journal_stats[journal]
        total_attempts = stats['api']['attempts'] + stats['vpn']['attempts']
        total_successes = stats['api']['successes'] + stats['vpn']['successes']
        
        if total_attempts == 0:
            return 0.5
        
        return total_successes / total_attempts

async def main():
    """Main robust system"""
    
    print("🧠 ROBUST PDF DOWNLOAD SYSTEM")
    print("=" * 80)
    print("Combining API + VPN methods intelligently")
    print("=" * 80)
    
    system = RobustPDFSystem()
    
    # Test papers
    test_papers = [
        {'doi': '10.1111/mafi.12456', 'journal': 'Mathematical Finance'},
        {'doi': '10.1111/jofi.13412', 'journal': 'Journal of Finance'},
        {'doi': '10.3982/ECTA20404', 'journal': 'Econometrica'},
        {'doi': '10.3982/ECTA20411', 'journal': 'Econometrica'},
    ]
    
    results = await system.batch_download(test_papers)
    
    # Summary
    print(f"\n{'='*30} RESULTS {'='*30}")
    print(f"Success rate: {results['successful']}/{results['total']} ({results['successful']/results['total']*100:.1f}%)")
    
    # Show journal statistics
    print(f"\n📊 JOURNAL STATISTICS:")
    for journal, stats in system.journal_stats.items():
        api_rate = stats['api']['successes'] / stats['api']['attempts'] if stats['api']['attempts'] > 0 else 0
        vpn_rate = stats['vpn']['successes'] / stats['vpn']['attempts'] if stats['vpn']['attempts'] > 0 else 0
        
        print(f"\n{journal}:")
        print(f"  API: {api_rate*100:.1f}% ({stats['api']['successes']}/{stats['api']['attempts']})")
        print(f"  VPN: {vpn_rate*100:.1f}% ({stats['vpn']['successes']}/{stats['vpn']['attempts']})")
    
    print(f"\n🧠 ROBUST SYSTEM COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())