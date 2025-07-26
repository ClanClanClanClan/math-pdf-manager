#!/usr/bin/env python3
"""
WILEY SUBSCRIPTION TEST WITH ETH VPN
====================================

Test Wiley subscription papers with ETH VPN connection active.
This addresses the user's concern about testing non-open-access papers thoroughly.

The 403 responses suggest we need to be on the ETH network to access subscription content.
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class WileySubscriptionVPNTester:
    """Test Wiley subscription access with VPN"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.credentials = None
        self.vpn_connected = False
    
    async def initialize(self):
        """Initialize credentials and check VPN"""
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
        """Check VPN connection status"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            if "state: Connected" in result.stdout:
                print("✅ ETH VPN already connected")
                self.vpn_connected = True
                return True
            else:
                print("❌ ETH VPN not connected")
                return False
                
        except Exception as e:
            print(f"❌ VPN status check failed: {e}")
            return False
    
    def connect_vpn_interactive(self):
        """Connect VPN with interactive prompt"""
        if self.vpn_connected:
            return True
            
        print("\n🔌 VPN CONNECTION REQUIRED")
        print("=" * 50)
        print("To access Wiley subscription content, ETH VPN connection is needed.")
        print("Please manually connect to ETH VPN using Cisco Secure Client:")
        print("1. Open Cisco Secure Client")
        print("2. Connect to: vpn.ethz.ch")
        print("3. Use your ETH credentials + 2FA")
        print("4. Wait for connection to establish")
        
        input("\nPress Enter when VPN is connected...")
        
        # Check if connected now
        return self.check_vpn_status()
    
    def get_verified_subscription_papers(self):
        """Get papers known to be subscription-based from premium journals"""
        return [
            {
                'doi': '10.1111/1467-9523.00201',  # Economica - definitely subscription
                'title': 'Economics research paper',
                'journal': 'Economica',
                'note': 'Economics journal - subscription required'
            },
            {
                'doi': '10.1002/anie.201906273',  # Angewandte - known subscription
                'title': 'Chemistry research',
                'journal': 'Angewandte Chemie',
                'note': 'Premium chemistry journal'
            },
            {
                'doi': '10.1111/joms.12567',  # Journal of Management Studies
                'title': 'Management research',
                'journal': 'Journal of Management Studies', 
                'note': 'Business journal - institutional access'
            }
        ]
    
    async def test_subscription_access(self):
        """Test access to subscription papers with VPN"""
        
        print("\n🧪 WILEY SUBSCRIPTION ACCESS TEST (WITH VPN)")
        print("=" * 80)
        
        papers = self.get_verified_subscription_papers()
        results = []
        
        async with async_playwright() as p:
            # Enhanced browser settings for ETH access
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            # Test each paper
            for i, paper in enumerate(papers, 1):
                print(f"\n{'='*15} TEST {i}/{len(papers)}: {paper['journal']} {'='*15}")
                print(f"DOI: {paper['doi']}")
                print(f"Title: {paper['title']}")
                
                result = await self._test_single_paper(page, paper)
                results.append(result)
                
                # Brief pause between tests
                await page.wait_for_timeout(3000)
            
            print(f"\n⏸️ Keeping browser open for final inspection...")
            await page.wait_for_timeout(20000)
            
            await browser.close()
        
        # Print summary
        self._print_results_summary(results, papers)
        
        return results
    
    async def _test_single_paper(self, page, paper_info):
        """Test access to a single subscription paper"""
        
        doi = paper_info['doi']
        paper_url = f"https://onlinelibrary.wiley.com/doi/{doi}"
        
        result = {
            'doi': doi,
            'journal': paper_info['journal'],
            'accessible': False,
            'has_paywall': False,
            'pdf_downloadable': False,
            'http_status': None,
            'final_url': None,
            'errors': []
        }
        
        try:
            print(f"   📍 Accessing: {paper_url}")
            
            # Navigate to paper
            response = await page.goto(paper_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(5000)
            
            result['http_status'] = response.status if response else None
            result['final_url'] = page.url
            
            print(f"   Status: {result['http_status']}")
            print(f"   Final URL: {result['final_url']}")
            
            if result['http_status'] == 404:
                print(f"   ❌ Paper not found (404)")
                result['errors'].append("Paper not found")
                return result
            elif result['http_status'] == 403:
                print(f"   ❌ Access forbidden (403) - may need different VPN or auth")
                result['errors'].append("Access forbidden")
                return result
            
            # Handle cookies
            await self._handle_cookies(page)
            
            # Check page content
            page_text = await page.inner_text('body')
            
            # Check for paywall indicators
            paywall_indicators = [
                'purchase this article',
                'subscription required',
                'institutional access required',
                'sign in to access full text',
                'get access',
                'preview only'
            ]
            
            has_paywall = any(indicator in page_text.lower() for indicator in paywall_indicators)
            result['has_paywall'] = has_paywall
            
            if has_paywall:
                print(f"   🔒 Paywall detected - attempting institutional access")
                await self._attempt_institutional_access(page)
                
                # Re-check page after auth attempt
                await page.wait_for_timeout(5000)
                page_text = await page.inner_text('body')
            
            # Check for access indicators
            access_indicators = [
                'download pdf',
                'full text',
                'view full text',
                'read article',
                'open access'
            ]
            
            has_access = any(indicator in page_text.lower() for indicator in access_indicators)
            result['accessible'] = has_access
            
            if has_access:
                print(f"   ✅ Content appears accessible")
                
                # Test PDF download
                pdf_success = await self._test_pdf_download(page, doi)
                result['pdf_downloadable'] = pdf_success
                
                if pdf_success:
                    print(f"   🎉 PDF download successful!")
                else:
                    print(f"   ⚠️ Content accessible but PDF download failed")
            else:
                print(f"   ❌ No access to content detected")
                
                # Check what type of restriction we're seeing
                if 'cloudflare' in page_text.lower():
                    result['errors'].append("Cloudflare protection")
                    print(f"   🚫 Cloudflare protection detected")
                elif any(word in page_text.lower() for word in ['login', 'sign in', 'authentication']):
                    result['errors'].append("Authentication required")
                    print(f"   🔑 Authentication still required")
                else:
                    result['errors'].append("Unknown access restriction")
                    print(f"   ❓ Unknown access restriction")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            result['errors'].append(str(e))
            return result
    
    async def _handle_cookies(self, page):
        """Handle cookie banners"""
        cookie_selectors = [
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            '#onetrust-accept-btn-handler'
        ]
        
        for selector in cookie_selectors:
            try:
                btn = await page.wait_for_selector(selector, timeout=2000)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    return
            except:
                continue
    
    async def _attempt_institutional_access(self, page):
        """Attempt institutional access"""
        institutional_selectors = [
            'a:has-text("Institutional Login")',
            'a[href*="ssostart"]',
            'button:has-text("Login")',
            'a:has-text("Sign in")'
        ]
        
        for selector in institutional_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element and await element.is_visible():
                    print(f"     👆 Clicking: {selector}")
                    await element.click()
                    await page.wait_for_timeout(5000)
                    
                    # Handle ETH auth if redirected
                    if 'ethz' in page.url or 'shibboleth' in page.url:
                        print(f"     🔐 ETH authentication required")
                        await self._handle_eth_auth(page)
                    
                    return True
            except:
                continue
        
        return False
    
    async def _handle_eth_auth(self, page):
        """Handle ETH authentication"""
        try:
            # Check for Cloudflare first
            page_content = await page.content()
            if 'cloudflare' in page_content.lower():
                print(f"     ❌ Cloudflare protection detected")
                return False
            
            # Fill credentials
            await page.wait_for_timeout(2000)
            
            # Username
            try:
                username_field = await page.wait_for_selector('input[name="username"]', timeout=5000)
                if username_field:
                    await username_field.fill(self.credentials['username'])
                    print(f"     ✅ Username filled")
            except:
                print(f"     ❌ Could not find username field")
                return False
            
            # Password
            try:
                password_field = await page.wait_for_selector('input[name="password"]', timeout=5000) 
                if password_field:
                    await password_field.fill(self.credentials['password'])
                    print(f"     ✅ Password filled")
            except:
                print(f"     ❌ Could not find password field")
                return False
            
            # Submit
            try:
                submit_btn = await page.wait_for_selector('input[type="submit"]', timeout=5000)
                if submit_btn:
                    await submit_btn.click()
                    await page.wait_for_timeout(8000)
                    print(f"     ✅ Credentials submitted")
                    return True
            except:
                print(f"     ❌ Could not submit credentials")
                return False
                
        except Exception as e:
            print(f"     ❌ ETH auth failed: {e}")
            return False
    
    async def _test_pdf_download(self, page, doi):
        """Test PDF download"""
        pdf_selectors = [
            'a:has-text("Download PDF")',
            'a:has-text("PDF")',
            'a[href*="pdf"]'
        ]
        
        for selector in pdf_selectors:
            try:
                pdf_element = await page.wait_for_selector(selector, timeout=3000)
                if pdf_element and await pdf_element.is_visible():
                    # Try download
                    save_dir = Path("vpn_subscription_test")
                    save_dir.mkdir(exist_ok=True)
                    save_path = save_dir / f"wiley_{doi.replace('/', '_').replace('.', '_')}.pdf"
                    
                    try:
                        async with page.expect_download(timeout=10000) as download_info:
                            await pdf_element.click()
                            download = await download_info.value
                            await download.save_as(save_path)
                            
                            if save_path.exists() and save_path.stat().st_size > 1000:
                                return True
                    except:
                        pass
            except:
                continue
        
        return False
    
    def _print_results_summary(self, results, papers):
        """Print comprehensive results summary"""
        
        print(f"\n{'='*25} RESULTS SUMMARY {'='*25}")
        
        accessible_count = sum(1 for r in results if r['accessible'])
        paywall_count = sum(1 for r in results if r['has_paywall'])
        pdf_count = sum(1 for r in results if r['pdf_downloadable'])
        
        print(f"\n📊 Overview:")
        print(f"   Papers tested: {len(results)}")
        print(f"   Accessible: {accessible_count}/{len(results)}")
        print(f"   With paywalls: {paywall_count}/{len(results)}")
        print(f"   PDF downloads: {pdf_count}/{len(results)}")
        
        print(f"\n📋 Individual Results:")
        for i, (result, paper) in enumerate(zip(results, papers), 1):
            status = "✅ ACCESSIBLE" if result['accessible'] else "❌ BLOCKED"
            paywall = " (🔒 PAYWALL)" if result['has_paywall'] else ""
            pdf = " + 📄 PDF" if result['pdf_downloadable'] else ""
            
            print(f"   {i}. {result['journal']} - {status}{paywall}{pdf}")
            print(f"      DOI: {result['doi']} | Status: {result['http_status']}")
            
            if result['errors']:
                print(f"      Errors: {', '.join(result['errors'])}")
        
        # Final assessment
        success_rate = accessible_count / len(results) * 100 if results else 0
        
        print(f"\n🎯 FINAL ASSESSMENT:")
        if success_rate >= 80:
            print(f"   🎉 EXCELLENT: {success_rate:.0f}% subscription access rate")
            print(f"   ETH VPN + institutional access working well!")
        elif success_rate >= 50:
            print(f"   ✅ GOOD: {success_rate:.0f}% subscription access rate")
            print(f"   ETH approach mostly working for subscription content")
        elif success_rate > 0:
            print(f"   ⚠️ PARTIAL: {success_rate:.0f}% subscription access rate")
            print(f"   Some subscription access working")
        else:
            print(f"   ❌ FAILED: 0% subscription access rate")
            print(f"   Subscription content access needs improvement")
            print(f"   💡 May need manual VPN connection or different approach")

async def main():
    """Main test function"""
    
    print("🔬 WILEY SUBSCRIPTION ACCESS TEST WITH VPN")
    print("=" * 80)
    print("Testing NON-OPEN-ACCESS papers as requested")
    print("=" * 80)
    
    tester = WileySubscriptionVPNTester()
    
    # Initialize
    if not await tester.initialize():
        return
    
    # Check VPN status
    if not tester.check_vpn_status():
        if not tester.connect_vpn_interactive():
            print("⚠️ Continuing without VPN - access may be limited")
    
    # Run tests
    results = await tester.test_subscription_access()
    
    # Final message
    accessible_count = sum(1 for r in results if r['accessible'])
    if accessible_count > 0:
        print(f"\n🎉 SUCCESS: {accessible_count} subscription papers accessible!")
        print("ETH infrastructure working for subscription content")
    else:
        print(f"\n❌ No subscription papers accessible")
        print("May need VPN connection or additional configuration")

if __name__ == "__main__":
    asyncio.run(main())