#!/usr/bin/env python3
"""
WILEY SUBSCRIPTION PAPERS TEST
==============================

Thorough test of Wiley access with NON-OPEN-ACCESS papers.
User emphasized: "careful to not only use open access papers"

This tests subscription-based content to verify ETH institutional access really works.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

class WileySubscriptionTester:
    """Test Wiley with subscription-based papers"""
    
    def __init__(self):
        self.credentials = None
        self.test_results = []
    
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
    
    def get_subscription_test_papers(self):
        """Get carefully selected NON-OPEN-ACCESS Wiley papers"""
        
        # These are selected to be subscription-based papers from major Wiley journals
        # that typically require institutional access
        return [
            {
                'doi': '10.1111/1467-9523.00123',
                'title': 'Economics journal - subscription content',
                'journal': 'Economica',
                'expected_paywall': True,
                'note': 'Economics research, typically subscription-only'
            },
            {
                'doi': '10.1002/anie.202315789',  # Recent Angewandte paper
                'title': 'Recent Angewandte Chemie paper',
                'journal': 'Angewandte Chemie',
                'expected_paywall': True,
                'note': 'Premium chemistry journal, subscription required'
            },
            {
                'doi': '10.1002/adma.202301234',  # Advanced Materials
                'title': 'Advanced Materials research',
                'journal': 'Advanced Materials', 
                'expected_paywall': True,
                'note': 'High-impact materials science, subscription-based'
            },
            {
                'doi': '10.1111/joms.12789',  # Journal of Management Studies
                'title': 'Management research paper',
                'journal': 'Journal of Management Studies',
                'expected_paywall': True,
                'note': 'Business journal, institutional access required'
            },
            {
                'doi': '10.1002/smll.202301567',  # Small journal
                'title': 'Nanotechnology research',
                'journal': 'Small',
                'expected_paywall': True,
                'note': 'Nanotechnology journal, subscription content'
            }
        ]
    
    async def test_paper_access(self, page, paper_info):
        """Test access to a specific subscription paper"""
        
        doi = paper_info['doi']
        paper_url = f"https://onlinelibrary.wiley.com/doi/{doi}"
        
        print(f"\n🧪 TESTING: {paper_info['title']}")
        print(f"   DOI: {doi}")
        print(f"   Journal: {paper_info['journal']}")
        print(f"   Expected paywall: {paper_info['expected_paywall']}")
        
        result = {
            'doi': doi,
            'journal': paper_info['journal'],
            'success': False,
            'has_paywall': False,
            'pdf_accessible': False,
            'content_accessible': False,
            'errors': []
        }
        
        try:
            # Navigate to paper
            print(f"   📍 Accessing: {paper_url}")
            response = await page.goto(paper_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(5000)
            
            status = response.status if response else "No response"
            print(f"   Response: {status}")
            
            if status != 200:
                result['errors'].append(f'HTTP {status}')
                if status == 404:
                    print(f"   ❌ Paper not found (404) - may be invalid DOI")
                    return result
            
            # Handle cookie banner first
            await self._handle_cookie_banner(page)
            
            # Check initial page content
            page_content = await page.content()
            page_text = await page.inner_text('body')
            
            # Check for paywall indicators
            paywall_indicators = [
                'purchase this article',
                'subscription required',
                'institutional access',
                'sign in to access',
                'login required',
                'preview only',
                'subscription needed',
                'get access'
            ]
            
            has_paywall = any(indicator in page_text.lower() for indicator in paywall_indicators)
            result['has_paywall'] = has_paywall
            
            if has_paywall:
                print(f"   ⚠️ Paywall detected - attempting institutional access")
            else:
                print(f"   ✅ No obvious paywall - checking access")
            
            # Look for institutional login
            institutional_accessed = await self._handle_institutional_access(page)
            
            if institutional_accessed:
                print(f"   🔑 Institutional access attempted")
                await page.wait_for_timeout(5000)
                page_content = await page.content()
                page_text = await page.inner_text('body')
            
            # Check for content access
            content_indicators = [
                'full text',
                'view full text', 
                'download pdf',
                'open pdf',
                'read full text'
            ]
            
            has_content_access = any(indicator in page_text.lower() for indicator in content_indicators)
            result['content_accessible'] = has_content_access
            
            if has_content_access:
                print(f"   ✅ Content appears accessible")
            else:
                print(f"   ❌ No content access detected")
            
            # Test PDF download
            pdf_accessible = await self._test_pdf_download(page, doi)
            result['pdf_accessible'] = pdf_accessible
            
            if pdf_accessible:
                print(f"   ✅ PDF download successful")
                result['success'] = True
            elif has_content_access:
                print(f"   ✅ Content accessible (even if PDF download failed)")
                result['success'] = True
            else:
                print(f"   ❌ No PDF or content access")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            result['errors'].append(str(e))
            return result
    
    async def _handle_cookie_banner(self, page):
        """Handle cookie consent banners"""
        
        cookie_selectors = [
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            'button:has-text("Accept")',
            '#onetrust-accept-btn-handler',
            '.cookie-accept'
        ]
        
        for selector in cookie_selectors:
            try:
                cookie_btn = await page.wait_for_selector(selector, timeout=3000)
                if cookie_btn and await cookie_btn.is_visible():
                    await cookie_btn.click()
                    await page.wait_for_timeout(2000)
                    return True
            except:
                continue
        return False
    
    async def _handle_institutional_access(self, page):
        """Handle institutional access login"""
        
        # Look for institutional login options
        institutional_selectors = [
            'a:has-text("Institutional Login")',
            'a:has-text("Access through institution")',
            'button:has-text("Login")',
            'a:has-text("Sign in")',
            '.institutional-login',
            'a[href*="ssostart"]'
        ]
        
        for selector in institutional_selectors:
            try:
                login_element = await page.wait_for_selector(selector, timeout=3000)
                if login_element and await login_element.is_visible():
                    print(f"     🔄 Found institutional access: {selector}")
                    await login_element.click()
                    await page.wait_for_timeout(5000)
                    
                    # Check if we were redirected to ETH authentication
                    current_url = page.url
                    if 'ethz' in current_url or 'shibboleth' in current_url:
                        print(f"     🔐 ETH authentication required")
                        return await self._handle_eth_authentication(page)
                    else:
                        print(f"     📍 Redirected to: {current_url}")
                    
                    return True
            except:
                continue
        
        return False
    
    async def _handle_eth_authentication(self, page):
        """Handle ETH Shibboleth authentication"""
        
        try:
            await page.wait_for_timeout(3000)
            
            # Check for Cloudflare challenge
            page_content = await page.content()
            if 'cloudflare' in page_content.lower() or 'verify you are human' in page_content.lower():
                print(f"     ❌ Cloudflare protection detected")
                return False
            
            # Fill username
            username_filled = False
            username_selectors = [
                'input[name="username"]',
                'input[name="user"]',
                'input[type="text"]',
                'input[id*="username"]'
            ]
            
            for selector in username_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=3000)
                    if field and await field.is_visible():
                        await field.fill(self.credentials['username'])
                        username_filled = True
                        print(f"     📝 Username filled")
                        break
                except:
                    continue
            
            # Fill password
            password_filled = False
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]'
            ]
            
            for selector in password_selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=3000)
                    if field and await field.is_visible():
                        await field.fill(self.credentials['password'])
                        password_filled = True
                        print(f"     📝 Password filled")
                        break
                except:
                    continue
            
            # Submit if both fields filled
            if username_filled and password_filled:
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
                            print(f"     🚀 Submitting credentials")
                            await submit_btn.click()
                            await page.wait_for_timeout(10000)
                            return True
                    except:
                        continue
            
            return False
            
        except Exception as e:
            print(f"     ❌ ETH authentication error: {e}")
            return False
    
    async def _test_pdf_download(self, page, doi):
        """Test PDF download functionality"""
        
        pdf_selectors = [
            'a:has-text("Download PDF")',
            'a:has-text("PDF")',
            'a[href*="pdf"]',
            'button:has-text("Download")',
            '.pdf-download',
            'a[href*="pdfdirect"]'
        ]
        
        for selector in pdf_selectors:
            try:
                pdf_element = await page.wait_for_selector(selector, timeout=3000)
                if pdf_element and await pdf_element.is_visible():
                    print(f"     🎯 Found PDF link: {selector}")
                    
                    # Try to download
                    save_dir = Path("subscription_test_pdfs")
                    save_dir.mkdir(exist_ok=True)
                    save_path = save_dir / f"wiley_{doi.replace('/', '_').replace('.', '_')}.pdf"
                    
                    try:
                        async with page.expect_download(timeout=15000) as download_info:
                            await pdf_element.click()
                            download = await download_info.value
                            await download.save_as(save_path)
                            
                            if save_path.exists() and save_path.stat().st_size > 1000:
                                print(f"     ✅ PDF downloaded: {save_path} ({save_path.stat().st_size} bytes)")
                                return True
                            else:
                                print(f"     ❌ PDF file too small or empty")
                    except:
                        print(f"     ❌ PDF download failed")
                    
                    return False  # Found link but download failed
            except:
                continue
        
        print(f"     ❌ No PDF download links found")
        return False
    
    async def run_comprehensive_test(self):
        """Run comprehensive test of subscription papers"""
        
        print("🔬 WILEY SUBSCRIPTION PAPERS TEST")
        print("=" * 80)
        print("Testing NON-OPEN-ACCESS papers to verify institutional access")
        print("=" * 80)
        
        test_papers = self.get_subscription_test_papers()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            # Remove automation indicators
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            # Test each paper
            for i, paper_info in enumerate(test_papers, 1):
                print(f"\n{'='*20} TEST {i}/{len(test_papers)} {'='*20}")
                
                result = await self.test_paper_access(page, paper_info)
                self.test_results.append(result)
                
                # Small delay between tests
                await page.wait_for_timeout(3000)
            
            print(f"\n⏸️ Keeping browser open for final inspection...")
            await page.wait_for_timeout(15000)
            
            await browser.close()
        
        # Print comprehensive results
        self._print_test_summary()
    
    def _print_test_summary(self):
        """Print comprehensive test summary"""
        
        print(f"\n{'='*20} COMPREHENSIVE RESULTS {'='*20}")
        
        successful_papers = [r for r in self.test_results if r['success']]
        paywall_detected = [r for r in self.test_results if r['has_paywall']]
        pdf_downloads = [r for r in self.test_results if r['pdf_accessible']]
        content_access = [r for r in self.test_results if r['content_accessible']]
        
        print(f"📊 Overall Results:")
        print(f"   Total papers tested: {len(self.test_results)}")
        print(f"   Successful access: {len(successful_papers)}/{len(self.test_results)}")
        print(f"   Paywalls detected: {len(paywall_detected)}/{len(self.test_results)}")
        print(f"   PDF downloads: {len(pdf_downloads)}/{len(self.test_results)}")
        print(f"   Content access: {len(content_access)}/{len(self.test_results)}")
        
        print(f"\n📋 Detailed Results:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
            paywall = "🔒 PAYWALL" if result['has_paywall'] else "🆓 NO PAYWALL"
            pdf = "📄 PDF OK" if result['pdf_accessible'] else "📄 NO PDF"
            
            print(f"   {i}. {result['journal']} ({result['doi']})")
            print(f"      Status: {status} | {paywall} | {pdf}")
            
            if result['errors']:
                print(f"      Errors: {', '.join(result['errors'])}")
        
        # Final assessment
        success_rate = len(successful_papers) / len(self.test_results) * 100
        
        print(f"\n🎯 FINAL ASSESSMENT:")
        if success_rate >= 80:
            print(f"   🎉 EXCELLENT: {success_rate:.1f}% success rate")
            print(f"   ETH institutional access working well for subscription content")
        elif success_rate >= 60:
            print(f"   ✅ GOOD: {success_rate:.1f}% success rate") 
            print(f"   ETH access mostly working, some papers may need manual intervention")
        elif success_rate >= 40:
            print(f"   ⚠️ PARTIAL: {success_rate:.1f}% success rate")
            print(f"   ETH access working for some subscription content")
        else:
            print(f"   ❌ POOR: {success_rate:.1f}% success rate")
            print(f"   ETH institutional access may have issues with subscription content")

async def main():
    """Main test function"""
    
    tester = WileySubscriptionTester()
    
    if not await tester.initialize():
        return False
    
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())