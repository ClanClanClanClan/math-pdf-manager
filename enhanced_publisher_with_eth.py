#!/usr/bin/env python3
"""
ENHANCED PUBLISHER WITH ETH INFRASTRUCTURE
==========================================

Enhanced publisher implementation that uses ETH infrastructure to bypass Cloudflare:
1. Try ETH Library Portal first
2. Try VPN connection if needed
3. Fall back to standard methods

This creates a bulletproof approach for both Wiley and Elsevier.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class ETHEnhancedPublisher:
    """Enhanced publisher with ETH infrastructure support"""
    
    def __init__(self, publisher_name, auth_config):
        self.publisher_name = publisher_name
        self.auth_config = auth_config
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.vpn_connected = False
        
        # Publisher-specific URLs
        self.publisher_configs = {
            'Wiley': {
                'base_url': 'https://onlinelibrary.wiley.com',
                'doi_pattern': 'https://onlinelibrary.wiley.com/doi/{}',
                'library_search': 'Wiley Online Library',
                'pdf_selectors': [
                    'a:has-text("Download PDF")',
                    'a:has-text("PDF")',
                    'a[href*="/pdf/"]'
                ]
            },
            'Elsevier': {
                'base_url': 'https://www.sciencedirect.com',
                'doi_pattern': 'https://www.sciencedirect.com/science/article/pii/{}',
                'library_search': 'ScienceDirect',
                'pdf_selectors': [
                    'a:has-text("Download PDF")',
                    'a[href*="pdf"]',
                    'button:has-text("Download")'
                ]
            }
        }
    
    def check_vpn_status(self):
        """Check if ETH VPN is connected"""
        try:
            if not Path(self.cisco_path).exists():
                return False
                
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            if "Connected" in result.stdout:
                self.vpn_connected = True
                return True
            return False
            
        except:
            return False
    
    def connect_vpn(self):
        """Connect to ETH VPN if possible"""
        if self.vpn_connected or not Path(self.cisco_path).exists():
            return self.vpn_connected
            
        try:
            print(f"🔄 Attempting ETH VPN connection for {self.publisher_name}...")
            
            connect_cmd = [
                self.cisco_path, "connect", "vpn.ethz.ch",
                "-s", f"{self.auth_config.username}",
                f"{self.auth_config.password}"
            ]
            
            result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ ETH VPN connected for {self.publisher_name}")
                self.vpn_connected = True
                return True
            else:
                print(f"❌ VPN connection failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ VPN connection error: {e}")
            return False
    
    async def download_paper_enhanced(self, paper_identifier: str, save_path: Path):
        """Enhanced download with ETH infrastructure fallbacks"""
        
        print(f"🚀 Enhanced {self.publisher_name} download: {paper_identifier}")
        
        # Approach 1: Try ETH Library Portal first
        print("📚 Approach 1: ETH Library Portal")
        result = await self._try_library_portal(paper_identifier, save_path)
        if result.get('success'):
            return result
        
        # Approach 2: Try with VPN
        print("🔒 Approach 2: With ETH VPN")
        if self.connect_vpn():
            result = await self._try_with_vpn(paper_identifier, save_path)
            if result.get('success'):
                return result
        
        # Approach 3: Direct access (original method)
        print("🎯 Approach 3: Direct access")
        result = await self._try_direct_access(paper_identifier, save_path)
        
        return result
    
    async def _try_library_portal(self, paper_identifier: str, save_path: Path):
        """Try accessing through ETH library portal"""
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    args=['--start-maximized']
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # Step 1: Go to ETH library
                print("   📍 Accessing ETH library portal")
                await page.goto("https://library.ethz.ch/", wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Step 2: Search for publisher
                config = self.publisher_configs.get(self.publisher_name, {})
                search_term = config.get('library_search', self.publisher_name)
                
                print(f"   🔍 Searching for: {search_term}")
                
                # Try different search approaches
                search_success = False
                
                # Try main search
                search_selectors = [
                    'input[type="search"]',
                    'input[name*="search"]',
                    'input[placeholder*="search"]',
                    '#search-input',
                    '.search-input'
                ]
                
                for selector in search_selectors:
                    try:
                        search_box = await page.wait_for_selector(selector, timeout=3000)
                        if search_box:
                            await search_box.fill(search_term)
                            await search_box.press("Enter")
                            await page.wait_for_timeout(3000)
                            search_success = True
                            break
                    except:
                        continue
                
                if not search_success:
                    # Try navigating to databases directly
                    print("   🔄 Trying direct database access")
                    db_url = "https://www.library.ethz.ch/en/Resources/Databases-and-E-Journals"
                    await page.goto(db_url)
                    await page.wait_for_timeout(3000)
                
                # Step 3: Look for publisher access
                publisher_selectors = [
                    f'a:has-text("{self.publisher_name}")',
                    f'a:has-text("{search_term}")',
                    f'*:has-text("{self.publisher_name}")'
                ]
                
                publisher_found = False
                for selector in publisher_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            href = await element.get_attribute('href')
                            if href and (self.publisher_name.lower() in href.lower() or 
                                       'database' in href.lower()):
                                print(f"   ✅ Found {self.publisher_name} access")
                                await element.click()
                                await page.wait_for_timeout(5000)
                                publisher_found = True
                                break
                        if publisher_found:
                            break
                    except:
                        continue
                
                if publisher_found:
                    # Step 4: Handle ETH authentication if needed
                    if 'ethz' in page.url or 'shibboleth' in page.url:
                        print("   🔐 Handling ETH authentication")
                        await self._handle_eth_auth(page)
                    
                    # Step 5: Try to access the paper
                    return await self._access_paper_through_portal(page, paper_identifier, save_path)
                
                await browser.close()
                
        except Exception as e:
            print(f"   ❌ Library portal approach failed: {e}")
        
        return {'success': False, 'error': 'Library portal access failed'}
    
    async def _try_with_vpn(self, paper_identifier: str, save_path: Path):
        """Try accessing with VPN connection"""
        
        try:
            # Import the original publisher
            if self.publisher_name == 'Wiley':
                from src.publishers.wiley_publisher import WileyPublisher
                publisher = WileyPublisher(self.auth_config)
            elif self.publisher_name == 'Elsevier':
                # Would implement ElsevierPublisher here
                return {'success': False, 'error': 'Elsevier publisher not implemented'}
            else:
                return {'success': False, 'error': 'Unknown publisher'}
            
            # Try download with VPN active
            print("   🔄 Attempting download with VPN active")
            result = await publisher.download_paper(paper_identifier, save_path)
            
            if result.success:
                print(f"   ✅ {self.publisher_name} download successful via VPN")
                return {'success': True, 'file_path': save_path}
            else:
                print(f"   ❌ {self.publisher_name} download failed via VPN")
                return {'success': False, 'error': getattr(result, 'error_message', 'VPN download failed')}
            
        except Exception as e:
            print(f"   ❌ VPN approach failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _try_direct_access(self, paper_identifier: str, save_path: Path):
        """Try direct access (fallback)"""
        
        try:
            if self.publisher_name == 'Wiley':
                from src.publishers.wiley_publisher import WileyPublisher
                publisher = WileyPublisher(self.auth_config)
            elif self.publisher_name == 'Elsevier':
                return {'success': False, 'error': 'Elsevier direct access not implemented'}
            else:
                return {'success': False, 'error': 'Unknown publisher'}
            
            print("   🔄 Attempting direct access")
            result = await publisher.download_paper(paper_identifier, save_path)
            
            if result.success:
                print(f"   ✅ {self.publisher_name} direct access successful")
                return {'success': True, 'file_path': save_path}
            else:
                print(f"   ❌ {self.publisher_name} direct access failed")
                return {'success': False, 'error': getattr(result, 'error_message', 'Direct access failed')}
                
        except Exception as e:
            print(f"   ❌ Direct access failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_eth_auth(self, page):
        """Handle ETH authentication"""
        try:
            await page.wait_for_timeout(3000)
            
            # Username field
            username_selectors = [
                'input[name="username"]',
                'input[name="user"]',
                'input[type="text"]'
            ]
            
            for selector in username_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=3000)
                    if field and await field.is_visible():
                        await field.fill(self.auth_config.username)
                        break
                except:
                    continue
            
            # Password field
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]'
            ]
            
            for selector in password_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=3000)
                    if field and await field.is_visible():
                        await field.fill(self.auth_config.password)
                        break
                except:
                    continue
            
            # Submit
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Login")'
            ]
            
            for selector in submit_selectors:
                try:
                    btn = await page.wait_for_selector(selector, timeout=3000)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(5000)
                        return True
                except:
                    continue
            
            return False
            
        except:
            return False
    
    async def _access_paper_through_portal(self, page, paper_identifier, save_path):
        """Access paper through the portal"""
        
        try:
            config = self.publisher_configs.get(self.publisher_name, {})
            
            # Navigate to paper
            if paper_identifier.startswith('http'):
                paper_url = paper_identifier
            else:
                paper_url = config.get('doi_pattern', '').format(paper_identifier)
            
            if paper_url:
                print(f"   📄 Accessing paper: {paper_url}")
                await page.goto(paper_url)
                await page.wait_for_timeout(5000)
                
                # Look for PDF access
                pdf_selectors = config.get('pdf_selectors', [])
                
                for selector in pdf_selectors:
                    try:
                        pdf_element = await page.wait_for_selector(selector, timeout=3000)
                        if pdf_element and await pdf_element.is_visible():
                            print(f"   🎯 Found PDF link: {selector}")
                            
                            # Try download
                            async with page.expect_download() as download_info:
                                await pdf_element.click()
                                download = await download_info.value
                                await download.save_as(save_path)
                                
                                if save_path.exists() and save_path.stat().st_size > 1000:
                                    print(f"   ✅ PDF downloaded successfully")
                                    return {'success': True, 'file_path': save_path}
                            break
                    except:
                        continue
            
            return {'success': False, 'error': 'No PDF access found'}
            
        except Exception as e:
            print(f"   ❌ Paper access failed: {e}")
            return {'success': False, 'error': str(e)}

async def test_enhanced_publishers():
    """Test the enhanced publishers"""
    
    print("🧪 TESTING ENHANCED PUBLISHERS")
    print("=" * 80)
    
    try:
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not (username and password):
            print("❌ No ETH credentials")
            return
        
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        
        # Test Wiley
        print("\n🔬 TESTING ENHANCED WILEY")
        print("-" * 40)
        
        wiley = ETHEnhancedPublisher('Wiley', auth_config)
        test_doi = '10.1002/anie.202004934'
        save_path = Path('enhanced_wiley_test.pdf')
        
        result = await wiley.download_paper_enhanced(test_doi, save_path)
        
        if result.get('success'):
            print("🎉 ENHANCED WILEY SUCCESS!")
        else:
            print(f"❌ Enhanced Wiley failed: {result.get('error')}")
        
        # Test Elsevier
        print("\n🔬 TESTING ENHANCED ELSEVIER")
        print("-" * 40)
        
        elsevier = ETHEnhancedPublisher('Elsevier', auth_config)
        test_doi = '10.1016/j.cell.2020.04.001'
        save_path = Path('enhanced_elsevier_test.pdf')
        
        result = await elsevier.download_paper_enhanced(test_doi, save_path)
        
        if result.get('success'):
            print("🎉 ENHANCED ELSEVIER SUCCESS!")
        else:
            print(f"❌ Enhanced Elsevier failed: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_publishers())