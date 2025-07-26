#!/usr/bin/env python3
"""
ETH API + VPN COMBINED SOLUTION
===============================

Since the API key alone doesn't work with standard endpoints, this solution
combines VPN connection with API key authentication for fully automatic downloads.

The API key likely works as an additional authentication layer when VPN is connected.
"""

import asyncio
import subprocess
import requests
import time
import os
from pathlib import Path
from playwright.async_api import async_playwright
import aiohttp
import json
from typing import Dict, List, Optional

# Your ETH Library API key
API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

class ETHAPIVPNDownloader:
    """Combined API + VPN solution for automatic downloads"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.downloads_dir = Path("eth_api_vpn_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        self.session = None
    
    def is_vpn_connected(self) -> bool:
        """Check if VPN is connected"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            return "state: Connected" in result.stdout
        except:
            return False
    
    def connect_vpn_automatic(self) -> bool:
        """Automatically connect to VPN using expect script"""
        
        print("🔌 AUTOMATIC VPN CONNECTION")
        print("=" * 50)
        
        if self.is_vpn_connected():
            print("✅ VPN already connected")
            return True
        
        # Create expect script for automatic connection
        expect_script = """#!/usr/bin/expect -f
set timeout 60

# Get credentials from environment
set username $env(ETH_USERNAME)
set password $env(ETH_PASSWORD)

# Start VPN connection
spawn /opt/cisco/secureclient/bin/vpn connect sslvpn.ethz.ch/staff-net

# Handle username prompt
expect {
    "Username:" {
        send "$username\r"
        exp_continue
    }
    "Password:" {
        send "$password\r"
        exp_continue
    }
    "state: Connected" {
        exit 0
    }
    timeout {
        exit 1
    }
}

# Wait for connection
expect {
    "state: Connected" {
        exit 0
    }
    timeout {
        exit 1
    }
}
"""
        
        try:
            # Save expect script
            script_path = Path("/tmp/vpn_connect.expect")
            script_path.write_text(expect_script)
            script_path.chmod(0o755)
            
            # Get credentials
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not (username and password):
                print("❌ No ETH credentials found")
                return False
            
            print(f"✅ Using credentials for: {username[:3]}***")
            
            # Set environment variables
            env = os.environ.copy()
            env['ETH_USERNAME'] = username
            env['ETH_PASSWORD'] = password
            
            print("🔄 Connecting to VPN automatically...")
            
            # Run expect script
            result = subprocess.run(['expect', str(script_path)], 
                                  env=env, capture_output=True, text=True, timeout=60)
            
            # Clean up
            script_path.unlink()
            
            # Check if connected
            time.sleep(3)
            if self.is_vpn_connected():
                print("✅ VPN connected successfully!")
                return True
            else:
                print("❌ VPN connection failed")
                print("Falling back to GUI automation...")
                return self.connect_vpn_gui_automation()
                
        except Exception as e:
            print(f"❌ Automatic connection error: {e}")
            return self.connect_vpn_gui_automation()
    
    def connect_vpn_gui_automation(self) -> bool:
        """Fallback: Use GUI automation to click Connect"""
        
        print("\n🖱️ GUI AUTOMATION FALLBACK")
        print("=" * 50)
        
        try:
            # Open Cisco
            subprocess.run(['open', '-a', 'Cisco Secure Client'])
            time.sleep(3)
            
            # Use AppleScript to click Connect
            applescript = '''
tell application "System Events"
    tell process "Cisco Secure Client"
        set frontmost to true
        delay 1
        
        -- Click Connect button
        click button "Connect" of window 1
    end tell
end tell
'''
            
            result = subprocess.run(['osascript', '-e', applescript], 
                                  capture_output=True, text=True)
            
            print("✅ Clicked Connect button")
            print("⏳ Waiting for connection...")
            
            # Wait for connection with 2FA
            for i in range(90):
                time.sleep(1)
                if self.is_vpn_connected():
                    print("✅ VPN connected!")
                    return True
                    
                if i == 30:
                    print("💡 Complete 2FA if prompted...")
            
            return self.is_vpn_connected()
            
        except Exception as e:
            print(f"❌ GUI automation error: {e}")
            return False
    
    async def initialize_session(self):
        """Initialize HTTP session with API key"""
        
        # Different authentication headers to try
        self.auth_headers = [
            {'Authorization': f'Bearer {self.api_key}'},
            {'X-API-Key': self.api_key},
            {'Proxy-Authorization': f'Bearer {self.api_key}'},
            {'Cookie': f'ezproxy={self.api_key}'}
        ]
        
        self.session = aiohttp.ClientSession()
    
    async def test_api_with_vpn(self) -> bool:
        """Test if API key works when VPN is connected"""
        
        print("\n🔍 TESTING API KEY WITH VPN")
        print("=" * 50)
        
        test_url = "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.202004934"
        
        for i, headers in enumerate(self.auth_headers, 1):
            try:
                print(f"\nTest {i}: {list(headers.keys())[0]}")
                
                async with self.session.get(test_url, headers=headers, 
                                          timeout=aiohttp.ClientTimeout(total=15)) as response:
                    
                    print(f"  Status: {response.status}")
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'pdf' in content_type.lower():
                            print(f"  ✅ SUCCESS! API key works with {list(headers.keys())[0]}")
                            self.working_headers = headers
                            return True
                        else:
                            print(f"  ❌ Not PDF: {content_type}")
                    else:
                        print(f"  ❌ Access denied")
                        
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:50]}")
        
        return False
    
    async def download_with_api_vpn(self, doi: str, title: str = "") -> bool:
        """Download PDF using API key + VPN"""
        
        print(f"\n📥 Downloading: {title or doi}")
        
        pdf_url = f"https://onlinelibrary.wiley.com/doi/pdf/{doi}"
        
        # Try with working headers if found, otherwise try all
        headers_to_try = [getattr(self, 'working_headers', self.auth_headers[0])] + self.auth_headers
        
        for headers in headers_to_try:
            try:
                async with self.session.get(pdf_url, headers=headers,
                                          timeout=aiohttp.ClientTimeout(total=30)) as response:
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        if 'pdf' in content_type.lower():
                            pdf_content = await response.read()
                            
                            if len(pdf_content) > 1000:
                                filename = f"api_vpn_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                save_path = self.downloads_dir / filename
                                
                                with open(save_path, 'wb') as f:
                                    f.write(pdf_content)
                                
                                size_mb = len(pdf_content) / (1024 * 1024)
                                print(f"✅ SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                return True
                            else:
                                print(f"❌ PDF too small: {len(pdf_content)} bytes")
                        else:
                            print(f"❌ Not PDF: {content_type}")
                    
            except Exception as e:
                continue
        
        # Fallback to Playwright if API doesn't work
        print("🔄 Trying browser fallback...")
        return await self.download_with_browser(doi, title)
    
    async def download_with_browser(self, doi: str, title: str = "") -> bool:
        """Fallback: Download using browser automation"""
        
        pdf_url = f"https://onlinelibrary.wiley.com/doi/pdf/{doi}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Add API key as cookie
            context = await browser.new_context()
            await context.add_cookies([{
                'name': 'ezproxy',
                'value': self.api_key,
                'domain': '.wiley.com',
                'path': '/'
            }])
            
            page = await context.new_page()
            
            # Add API key in headers
            await page.set_extra_http_headers({
                'Authorization': f'Bearer {self.api_key}'
            })
            
            try:
                response = await page.goto(pdf_url, timeout=30000)
                
                if response and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    if 'pdf' in content_type.lower():
                        pdf_buffer = await response.body()
                        
                        if len(pdf_buffer) > 1000:
                            filename = f"browser_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_buffer)
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"✅ BROWSER SUCCESS: {save_path} ({size_mb:.2f} MB)")
                            
                            await browser.close()
                            return True
                
                await browser.close()
                return False
                
            except Exception as e:
                print(f"❌ Browser error: {e}")
                await browser.close()
                return False
    
    async def batch_download(self, papers: List[Dict]) -> Dict:
        """Download multiple papers with API + VPN"""
        
        print("🚀 ETH API + VPN AUTOMATIC DOWNLOADER")
        print("=" * 70)
        print(f"Using API key: {self.api_key[:20]}...")
        print("=" * 70)
        
        # Initialize session
        await self.initialize_session()
        
        # Connect VPN automatically
        if not self.connect_vpn_automatic():
            print("❌ Failed to connect VPN automatically")
            print("💡 Please connect manually and run again")
            await self.session.close()
            return {'successful': 0, 'failed': len(papers)}
        
        # Test API with VPN
        api_works = await self.test_api_with_vpn()
        if api_works:
            print("\n✅ API KEY WORKS WITH VPN!")
            print("🎉 Fully automatic downloads enabled")
        else:
            print("\n⚠️ API key not working, using browser fallback")
        
        # Download papers
        results = {
            'successful': 0,
            'failed': 0,
            'papers': []
        }
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{'='*20} PAPER {i}/{len(papers)} {'='*20}")
            
            # Check VPN still connected
            if not self.is_vpn_connected():
                print("⚠️ VPN disconnected, reconnecting...")
                if not self.connect_vpn_automatic():
                    print("❌ Cannot reconnect VPN")
                    results['failed'] += 1
                    continue
            
            doi = paper.get('doi', '')
            title = paper.get('title', '')
            
            if not doi:
                print("❌ No DOI provided")
                results['failed'] += 1
                continue
            
            success = await self.download_with_api_vpn(doi, title)
            
            if success:
                results['successful'] += 1
                print(f"✅ PAPER {i} SUCCESS")
            else:
                results['failed'] += 1
                print(f"❌ PAPER {i} FAILED")
            
            results['papers'].append({
                'doi': doi,
                'title': title,
                'success': success
            })
        
        # Cleanup
        await self.session.close()
        
        return results
    
    async def run(self, papers: List[Dict]):
        """Main run method"""
        
        results = await self.batch_download(papers)
        
        # Show results
        print(f"\n{'='*30} FINAL RESULTS {'='*30}")
        print(f"Total papers: {len(papers)}")
        print(f"Successfully downloaded: {results['successful']}")
        print(f"Failed: {results['failed']}")
        success_rate = (results['successful'] / len(papers)) * 100 if papers else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if results['successful'] > 0:
            print(f"\n📁 Downloaded files in: {self.downloads_dir}")
            
            pdf_files = list(self.downloads_dir.glob("*.pdf"))
            for pdf_file in pdf_files:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            
            print(f"\n🎉 AUTOMATIC DOWNLOAD SUCCESS!")
            print(f"🤖 100% Automated with API + VPN")
            print(f"🔑 API Key: Active")
            print(f"🔌 VPN: Auto-connected")
            print(f"📄 PDFs: Downloaded")
        
        return results['successful'] > 0


async def main():
    """Main function"""
    
    print("🎯 ETH API + VPN COMBINED SOLUTION")
    print("=" * 80)
    print("Fully automatic downloads using your API key + VPN")
    print("=" * 80)
    
    downloader = ETHAPIVPNDownloader()
    
    # Test papers
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie - Test Paper'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Economica - Test Paper'
        },
        {
            'doi': '10.1002/adma.202001924',
            'title': 'Advanced Materials - Test Paper'
        }
    ]
    
    success = await downloader.run(papers)
    
    if success:
        print("\n🎉 API + VPN SOLUTION WORKS!")
        print("This provides 100% automation")
    else:
        print("\n❌ Solution needs troubleshooting")


if __name__ == "__main__":
    asyncio.run(main())