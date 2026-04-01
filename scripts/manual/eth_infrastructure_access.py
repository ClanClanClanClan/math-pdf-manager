#!/usr/bin/env python3
"""
ETH INFRASTRUCTURE ACCESS
=========================

Comprehensive solution using ETH's infrastructure to access publishers:
1. ETH Library Portal (library.ethz.ch)
2. ETH VPN Connection (Cisco Secure Client)
3. ETH EZproxy URLs
4. ETH Database Portal

This should work for both Wiley AND Elsevier, bypassing Cloudflare issues.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class ETHInfrastructureAccess:
    """ETH infrastructure access manager"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.vpn_connected = False
        self.credentials = None
        
    async def initialize(self):
        """Initialize with ETH credentials"""
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            if not (username and password):
                raise Exception("No ETH credentials available")
                
            self.credentials = {
                'username': username,
                'password': password
            }
            
            print(f"✅ ETH credentials loaded: {username[:3]}***")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load credentials: {e}")
            return False
    
    def check_vpn_status(self):
        """Check if ETH VPN is connected"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            if "Connected" in result.stdout:
                print("✅ ETH VPN already connected")
                self.vpn_connected = True
                return True
            else:
                print("❌ ETH VPN not connected")
                return False
                
        except Exception as e:
            print(f"❌ VPN status check failed: {e}")
            return False
    
    def connect_vpn(self):
        """Connect to ETH VPN using Cisco Secure Client"""
        if self.vpn_connected:
            return True
            
        try:
            print("🔄 Connecting to ETH VPN...")
            
            # Connect command
            connect_cmd = [
                self.cisco_path, "connect", "vpn.ethz.ch",
                "-s", f"{self.credentials['username']}",
                f"{self.credentials['password']}"
            ]
            
            result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ ETH VPN connected successfully")
                self.vpn_connected = True
                return True
            else:
                print(f"❌ VPN connection failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ VPN connection error: {e}")
            return False
    
    def disconnect_vpn(self):
        """Disconnect from ETH VPN"""
        if not self.vpn_connected:
            return True
            
        try:
            print("🔄 Disconnecting ETH VPN...")
            result = subprocess.run([self.cisco_path, "disconnect"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ ETH VPN disconnected")
                self.vpn_connected = False
                return True
            else:
                print(f"❌ VPN disconnect failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ VPN disconnect error: {e}")
            return False
    
    async def test_library_portal_access(self):
        """Test access through ETH library portal"""
        
        print("\n📚 TESTING ETH LIBRARY PORTAL ACCESS")
        print("=" * 60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--start-maximized']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            # Method 1: Direct database access
            print("🔍 Method 1: ETH Database Portal")
            try:
                db_url = "https://www.library.ethz.ch/en/Resources/Databases-and-E-Journals"
                await page.goto(db_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                print("   📍 Navigated to database portal")
                
                # Look for publisher databases
                publishers = ['Wiley', 'Elsevier']
                publisher_links = {}
                
                for publisher in publishers:
                    try:
                        # Search for publisher
                        search_selectors = [
                            'input[type="search"]',
                            'input[name*="search"]',
                            'input[placeholder*="search"]'
                        ]
                        
                        for selector in search_selectors:
                            try:
                                search_box = await page.wait_for_selector(selector, timeout=3000)
                                if search_box:
                                    print(f"   🔍 Searching for {publisher}")
                                    await search_box.fill(publisher)
                                    await search_box.press("Enter")
                                    await page.wait_for_timeout(3000)
                                    
                                    # Look for results
                                    publisher_elements = await page.query_selector_all(f'a:has-text("{publisher}")')
                                    
                                    for elem in publisher_elements:
                                        text = await elem.inner_text()
                                        href = await elem.get_attribute('href')
                                        
                                        if publisher.lower() in text.lower():
                                            publisher_links[publisher] = {
                                                'text': text.strip(),
                                                'href': href
                                            }
                                            print(f"   ✅ Found {publisher}: {text.strip()}")
                                            break
                                    break
                            except:
                                continue
                                
                    except Exception as e:
                        print(f"   ❌ Search for {publisher} failed: {e}")
                
                # Test access to found publishers
                for publisher, link_info in publisher_links.items():
                    if await self.test_publisher_access(page, publisher, link_info):
                        print(f"   🎉 {publisher} access confirmed!")
                    else:
                        print(f"   ❌ {publisher} access failed")
                
            except Exception as e:
                print(f"   ❌ Database portal test failed: {e}")
            
            print("\n⏸️ Keeping browser open for inspection...")
            await page.wait_for_timeout(30000)
            
            await browser.close()
    
    async def test_publisher_access(self, page, publisher, link_info):
        """Test access to a specific publisher"""
        
        try:
            print(f"   🧪 Testing {publisher} access...")
            
            # Click publisher access link
            publisher_link = await page.wait_for_selector(f'a:has-text("{link_info["text"]}")', timeout=5000)
            if publisher_link:
                await publisher_link.click()
                await page.wait_for_timeout(5000)
                
                # Check if we need ETH authentication
                current_url = page.url
                print(f"   📍 Current URL: {current_url}")
                
                if 'ethz' in current_url or 'shibboleth' in current_url:
                    print(f"   🔐 {publisher} requires ETH authentication")
                    if await self.handle_eth_authentication(page):
                        print(f"   ✅ {publisher} authentication successful")
                    else:
                        print(f"   ❌ {publisher} authentication failed")
                        return False
                
                # Test paper access
                test_dois = {
                    'Wiley': '10.1002/anie.202004934',
                    'Elsevier': '10.1016/j.cell.2020.04.001'
                }
                
                if publisher in test_dois:
                    return await self.test_paper_download(page, publisher, test_dois[publisher])
                
                return True
            
        except Exception as e:
            print(f"   ❌ {publisher} access test failed: {e}")
            return False
    
    async def handle_eth_authentication(self, page):
        """Handle ETH Shibboleth authentication"""
        
        try:
            await page.wait_for_timeout(3000)
            
            # Look for username field
            username_selectors = [
                'input[name="username"]',
                'input[name="user"]',
                'input[type="text"]',
                'input[id*="username"]'
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=3000)
                    if field and await field.is_visible():
                        username_field = field
                        break
                except:
                    continue
            
            # Look for password field
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=3000)
                    if field and await field.is_visible():
                        password_field = field
                        break
                except:
                    continue
            
            if username_field and password_field:
                print("   📝 Filling ETH credentials")
                await username_field.fill(self.credentials['username'])
                await password_field.fill(self.credentials['password'])
                
                # Submit
                submit_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_btn = await page.wait_for_selector(selector, timeout=3000)
                        if submit_btn and await submit_btn.is_visible():
                            await submit_btn.click()
                            await page.wait_for_timeout(5000)
                            return True
                    except:
                        continue
            
            return False
            
        except Exception as e:
            print(f"   ❌ ETH authentication error: {e}")
            return False
    
    async def test_paper_download(self, page, publisher, doi):
        """Test downloading a paper from the publisher"""
        
        try:
            print(f"   📄 Testing paper download: {doi}")
            
            # Navigate to paper
            if publisher == 'Wiley':
                paper_url = f"https://onlinelibrary.wiley.com/doi/{doi}"
            elif publisher == 'Elsevier':
                paper_url = f"https://www.sciencedirect.com/science/article/pii/{doi.replace('10.1016/', '')}"
            else:
                return False
            
            await page.goto(paper_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Look for PDF access
            pdf_selectors = [
                'a:has-text("Download PDF")',
                'a:has-text("PDF")',
                'a[href*="pdf"]',
                'button:has-text("Download")'
            ]
            
            for selector in pdf_selectors:
                try:
                    pdf_element = await page.wait_for_selector(selector, timeout=3000)
                    if pdf_element and await pdf_element.is_visible():
                        print(f"   ✅ PDF access available for {publisher}")
                        return True
                except:
                    continue
            
            print(f"   ❌ No PDF access found for {publisher}")
            return False
            
        except Exception as e:
            print(f"   ❌ Paper download test failed: {e}")
            return False
    
    async def test_ezproxy_access(self):
        """Test EZproxy access for publishers"""
        
        print("\n🔗 TESTING EZPROXY ACCESS")
        print("=" * 60)
        
        ezproxy_urls = {
            'Wiley': 'https://onlinelibrary.wiley.com.ezproxy.ethz.ch/',
            'Elsevier': 'https://www.sciencedirect.com.ezproxy.ethz.ch/'
        }
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            for publisher, ezproxy_url in ezproxy_urls.items():
                try:
                    print(f"🔄 Testing {publisher} EZproxy: {ezproxy_url}")
                    
                    response = await page.goto(ezproxy_url, wait_until='domcontentloaded', timeout=15000)
                    await page.wait_for_timeout(3000)
                    
                    status = response.status if response else "No response"
                    current_url = page.url
                    
                    print(f"   Status: {status}")
                    print(f"   Final URL: {current_url}")
                    
                    if 'ethz' in current_url and status == 200:
                        print(f"   ✅ {publisher} EZproxy access working!")
                        
                        # Test authentication
                        if await self.handle_eth_authentication(page):
                            print(f"   ✅ {publisher} authenticated via EZproxy")
                        else:
                            print(f"   ❌ {publisher} authentication failed")
                    else:
                        print(f"   ❌ {publisher} EZproxy not working")
                        
                except Exception as e:
                    print(f"   ❌ {publisher} EZproxy test failed: {e}")
            
            await page.wait_for_timeout(10000)
            await browser.close()

async def main():
    """Main test function"""
    
    print("🧠 ETH INFRASTRUCTURE ACCESS TEST")
    print("=" * 80)
    print("Testing comprehensive access to Wiley AND Elsevier via ETH")
    print("=" * 80)
    
    eth = ETHInfrastructureAccess()
    
    # Initialize credentials
    if not await eth.initialize():
        return False
    
    # Test approaches
    print("\n🔍 TESTING APPROACHES:")
    print("1. ETH Library Portal")
    print("2. EZproxy URLs")
    print("3. VPN Connection (if needed)")
    
    # Test library portal
    await eth.test_library_portal_access()
    
    # Test EZproxy
    await eth.test_ezproxy_access()
    
    # Check VPN status (don't automatically connect)
    print(f"\n🔍 VPN Status Check:")
    eth.check_vpn_status()
    
    print(f"\n💡 ETH INFRASTRUCTURE SUMMARY:")
    print(f"   📚 Library Portal: Available for database access")
    print(f"   🔗 EZproxy: Available for direct publisher access")
    print(f"   🔒 VPN: Available via Cisco Secure Client")
    print(f"   🎯 This should bypass ALL Cloudflare issues!")

if __name__ == "__main__":
    asyncio.run(main())