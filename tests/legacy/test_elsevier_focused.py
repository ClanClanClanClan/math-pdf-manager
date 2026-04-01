#!/usr/bin/env python3
"""
Focused Elsevier Testing with Real ScienceDirect Papers
Test multiple papers that we know work with the current DOI -> Link Hub -> ScienceDirect flow.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.publishers.elsevier_navigator import (
    ELSEVIER_CONFIG,
    ElsevierNavigator,
)
from src.secure_credential_manager import get_credential_manager


class ElsevierFocusedTester:
    """Focused testing for Elsevier with verified working papers."""
    
    def __init__(self):
        # These are real DOIs that follow the Link Hub -> ScienceDirect flow
        self.test_papers = [
            {
                'doi': '10.1016/j.jmb.2021.166861',
                'title': 'DNA mechanics and its biological impact',
                'journal': 'Journal of Molecular Biology',
                'type': 'known_working'
            },
            {
                'doi': '10.1016/j.jcp.2025.114261',
                'title': 'Recent computational physics paper',
                'journal': 'Journal of Computational Physics',
                'type': 'recent_2025'
            },
            {
                'doi': '10.1016/j.jcp.2025.114242',
                'title': 'Another computational physics paper',
                'journal': 'Journal of Computational Physics',
                'type': 'recent_2025'
            },
            {
                'doi': '10.1016/j.cpc.2025.109780',
                'title': 'Computer physics communications',
                'journal': 'Computer Physics Communications',
                'type': 'recent_2025'
            },
            {
                'doi': '10.1016/j.cpc.2025.109755',
                'title': 'Another computer physics paper',
                'journal': 'Computer Physics Communications', 
                'type': 'recent_2025'
            },
            {
                'doi': '10.1016/j.commatsci.2025.114174',
                'title': 'Computational materials science',
                'journal': 'Computational Materials Science',
                'type': 'recent_2025'
            },
            {
                'doi': '10.1016/j.eswa.2024.124167',
                'title': 'Expert systems application',
                'journal': 'Expert Systems with Applications',
                'type': 'expert_systems'
            }
        ]
        
        self.results = []
    
    async def test_single_paper(self, browser, paper: Dict, test_number: int) -> Dict:
        """Test access to a single Elsevier paper."""
        
        doi = paper['doi']
        
        print(f"\n{'='*60}")
        print(f"📄 TEST {test_number}: {paper['journal']}")
        print(f"{'='*60}")
        print(f"DOI: {doi}")
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True
        )
        page = await context.new_page()
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        result = {
            'test_number': test_number,
            'doi': doi,
            'journal': paper['journal'],
            'type': paper['type'],
            'success': False,
            'steps_completed': [],
            'error': None,
            'time_taken': 0,
            'final_url': None
        }
        
        try:
            import time
            start_time = time.time()
            
            # Create navigator
            navigator = ElsevierNavigator(page, ELSEVIER_CONFIG)
            navigator.eth_auth = ETHAuthenticator(page, username, password)
            
            # Step 1: Navigate to paper (Link Hub -> ScienceDirect)
            print(f"🌐 Step 1: Navigate to paper...")
            if await navigator.navigate_to_paper(doi):
                result['steps_completed'].append('navigation')
                result['final_url'] = page.url
                print(f"   ✅ Reached ScienceDirect: {page.url}")
            else:
                print(f"   ❌ Failed to reach ScienceDirect")
                result['error'] = f"Navigation failed - final URL: {page.url}"
                result['final_url'] = page.url
                return result
            
            # Verify we have the right paper
            title = await page.title()
            print(f"   📝 Title: {title[:60]}...")
            
            # Step 2: Navigate to institutional login
            print(f"\n🔐 Step 2: Navigate to institutional login...")
            if await navigator.navigate_to_login():
                result['steps_completed'].append('login_navigation')
                print(f"   ✅ Reached institutional login")
            else:
                print(f"   ❌ Failed to navigate to login")
                result['error'] = "Login navigation failed"
                return result
            
            # Step 3: Select ETH institution
            print(f"\n🏛️  Step 3: Select ETH institution...")
            if await navigator.select_eth_institution():
                result['steps_completed'].append('eth_selection')
                print(f"   ✅ Selected ETH")
            else:
                print(f"   ❌ Failed to select ETH")
                result['error'] = "ETH selection failed"
                return result
            
            # Step 4: ETH authentication
            print(f"\n🔑 Step 4: ETH authentication...")
            if await navigator.eth_auth.perform_login():
                result['steps_completed'].append('authentication')
                print(f"   ✅ Authentication successful")
            else:
                print(f"   ❌ Authentication failed")
                result['error'] = "Authentication failed"
                return result
            
            # Step 5: Post-auth redirect
            print(f"\n🔄 Step 5: Post-auth redirect...")
            if await navigator.navigate_after_auth():
                result['steps_completed'].append('post_auth')
                print(f"   ✅ Post-auth successful")
            else:
                print(f"   ❌ Post-auth failed")
                result['error'] = "Post-auth failed"
                return result
            
            # Step 6: Verify PDF access
            print(f"\n📄 Step 6: PDF access verification...")
            
            # Look for PDF button
            pdf_button = None
            for selector in ELSEVIER_CONFIG.pdf_download_selectors:
                pdf_button = await page.query_selector(selector)
                if pdf_button:
                    print(f"   ✅ Found PDF button: {selector}")
                    result['steps_completed'].append('pdf_found')
                    break
            
            if pdf_button:
                # Try to get PDF URL
                pdf_href = await pdf_button.get_attribute('href')
                if pdf_href:
                    print(f"   ✅ PDF URL available")
                    result['steps_completed'].append('pdf_url')
                    result['success'] = True
                    print(f"   🎉 COMPLETE SUCCESS")
                else:
                    print(f"   ❌ Could not get PDF URL")
                    result['error'] = "PDF URL not available"
            else:
                print(f"   ❌ PDF button not found")
                result['error'] = "PDF button not found"
                
                # Debug: Show what we can find
                all_links = await page.query_selector_all('a')
                pdf_related = []
                for link in all_links[:20]:
                    try:
                        text = await link.inner_text()
                        href = await link.get_attribute('href')
                        if text and any(term in text.lower() for term in ['pdf', 'download', 'view']):
                            pdf_related.append(f"'{text[:30]}' -> {href[:50] if href else 'No href'}")
                    except:
                        continue
                
                if pdf_related:
                    print(f"   🔍 Found PDF-related elements:")
                    for elem in pdf_related[:3]:
                        print(f"      {elem}")
            
            result['time_taken'] = time.time() - start_time
            
        except Exception as e:
            result['error'] = str(e)
            print(f"   ❌ Test error: {e}")
        
        finally:
            await context.close()
        
        return result
    
    async def run_focused_test(self):
        """Run focused test on verified papers."""
        
        print(f"\n{'='*80}")
        print(f"🎯 ELSEVIER FOCUSED TESTING SUITE")
        print(f"{'='*80}")
        print(f"Testing {len(self.test_papers)} verified ScienceDirect papers...")
        
        async with async_playwright() as p:
            browser = await p.firefox.launch(
                headless=True,  # Headless for speed
                firefox_user_prefs={
                    "dom.webdriver.enabled": False,
                    "useAutomationExtension": False,
                }
            )
            
            try:
                # Test each paper
                for i, paper in enumerate(self.test_papers, 1):
                    result = await self.test_single_paper(browser, paper, i)
                    self.results.append(result)
                    
                    if result['success']:
                        steps = len(result['steps_completed'])
                        time_taken = result['time_taken']
                        print(f"✅ TEST {i} PASSED ({steps}/6 steps, {time_taken:.1f}s)")
                    else:
                        print(f"❌ TEST {i} FAILED: {result['error']}")
                    
                    # Delay between tests to avoid rate limiting
                    await asyncio.sleep(3)
                
            finally:
                await browser.close()
        
        # Generate report
        self.generate_focused_report()
    
    def generate_focused_report(self):
        """Generate focused test report."""
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"📊 ELSEVIER FOCUSED TEST REPORT")
        print(f"{'='*80}")
        
        print(f"\n📈 OVERALL RESULTS:")
        print(f"   Total tests: {total_tests}")
        print(f"   ✅ Successful: {successful_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📊 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 85:
            print(f"\n🎉 EXCELLENT: Elsevier navigator is production-ready!")
            print(f"   ✅ Ready to add as third publisher")
        elif success_rate >= 70:
            print(f"\n✅ GOOD: Elsevier navigator is reliable")
            print(f"   ⚠️  Minor improvements recommended")
        elif success_rate >= 50:
            print(f"\n⚠️  MODERATE: Elsevier navigator needs work")
            print(f"   🔧 Significant improvements needed")
        else:
            print(f"\n❌ POOR: Elsevier navigator requires major fixes")
            print(f"   🚫 Not ready for production")
        
        # Step-by-step analysis
        print(f"\n🔍 STEP-BY-STEP ANALYSIS:")
        step_names = ['navigation', 'login_navigation', 'eth_selection', 'authentication', 'post_auth', 'pdf_found', 'pdf_url']
        
        for step in step_names:
            step_successes = sum(1 for r in self.results if step in r['steps_completed'])
            step_rate = (step_successes / total_tests * 100) if total_tests > 0 else 0
            status = "✅" if step_rate >= 85 else "⚠️" if step_rate >= 70 else "❌"
            print(f"   {step.replace('_', ' ').title()}: {status} {step_successes}/{total_tests} ({step_rate:.1f}%)")
        
        # Detailed results
        print(f"\n📋 DETAILED TEST RESULTS:")
        for result in self.results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            steps = len(result['steps_completed'])
            time_taken = result.get('time_taken', 0)
            
            print(f"\n   Test {result['test_number']}: {status}")
            print(f"      DOI: {result['doi']}")
            print(f"      Journal: {result['journal']}")
            print(f"      Steps: {steps}/6")
            print(f"      Time: {time_taken:.1f}s")
            
            if result['final_url']:
                print(f"      Final URL: {result['final_url']}")
            
            if not result['success']:
                print(f"      Error: {result['error']}")
                print(f"      Steps completed: {', '.join(result['steps_completed'])}")
        
        # Failure analysis
        if failed_tests > 0:
            print(f"\n❌ FAILURE ANALYSIS:")
            error_counts = {}
            for result in self.results:
                if not result['success'] and result['error']:
                    error = result['error']
                    error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {error}: {count} occurrence(s)")
        
        # Final recommendation
        print(f"\n💡 FINAL RECOMMENDATION:")
        if success_rate >= 85:
            print(f"   🎉 ELSEVIER NAVIGATOR APPROVED FOR PRODUCTION")
            print(f"   ✅ Add as third publisher to institutional access system")
            print(f"   ✅ Three-publisher system (IEEE + Springer + Elsevier) ready")
        elif success_rate >= 70:
            print(f"   ⚠️  ELSEVIER NAVIGATOR NEEDS MINOR FIXES")
            print(f"   🔧 Address failure points before production")
            print(f"   🧪 Re-test after improvements")
        else:
            print(f"   ❌ ELSEVIER NAVIGATOR NOT READY")
            print(f"   🔧 Major debugging and improvements required")
            print(f"   🚫 Do not deploy until success rate > 85%")


async def main():
    """Run focused Elsevier testing."""
    tester = ElsevierFocusedTester()
    await tester.run_focused_test()


if __name__ == "__main__":
    asyncio.run(main())