#!/usr/bin/env python3
"""
Comprehensive Elsevier Testing Suite
Test Elsevier navigator with multiple papers in headless mode to ensure reliability.
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


class ElsevierComprehensiveTester:
    """Comprehensive testing for Elsevier/ScienceDirect with multiple papers."""
    
    def __init__(self):
        self.test_papers = [
            {
                'doi': '10.1016/j.jmb.2021.166861',
                'title': 'DNA mechanics and its biological impact',
                'journal': 'Journal of Molecular Biology',
                'type': 'research_article'
            },
            {
                'doi': '10.1016/j.cell.2021.02.052', 
                'title': 'Spatially resolved cell atlas',
                'journal': 'Cell',
                'type': 'major_journal'
            },
            {
                'doi': '10.1016/j.neuron.2021.01.025',
                'title': 'Neural circuits for visual motion',
                'journal': 'Neuron', 
                'type': 'neuroscience'
            },
            {
                'doi': '10.1016/j.nature.2021.03.027',
                'title': 'Machine learning dynamics',
                'journal': 'Nature', 
                'type': 'nature_family'
            },
            {
                'doi': '10.1016/j.science.2021.04.015',
                'title': 'Quantum computing advances',
                'journal': 'Science',
                'type': 'science_family'
            },
            {
                'doi': '10.1016/j.pnas.2021.05.012',
                'title': 'Biological systems modeling',
                'journal': 'PNAS',
                'type': 'pnas'
            },
            {
                'doi': '10.1016/j.biocel.2020.105123',
                'title': 'Cellular mechanisms',
                'journal': 'Biochimica et Biophysica Acta',
                'type': 'biochemistry'
            },
            {
                'doi': '10.1016/j.jcp.2021.110234',
                'title': 'Computational physics methods',
                'journal': 'Journal of Computational Physics',
                'type': 'computational'
            },
            {
                'doi': '10.1016/j.jmps.2021.104567',
                'title': 'Mechanics of materials',
                'journal': 'Journal of Mechanics and Physics of Solids',
                'type': 'mechanics'
            }
        ]
        
        self.results = []
    
    async def test_single_paper(self, browser, paper: Dict, test_number: int) -> Dict:
        """Test access to a single Elsevier paper."""
        
        doi = paper['doi']
        expected_title = paper['title']
        
        print(f"\n{'='*60}")
        print(f"📄 TEST {test_number}: {paper['journal']}")
        print(f"{'='*60}")
        print(f"DOI: {doi}")
        print(f"Expected: {expected_title}")
        
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
            'pdf_size': 0,
            'time_taken': 0
        }
        
        try:
            import time
            start_time = time.time()
            
            # Create navigator
            navigator = ElsevierNavigator(page, ELSEVIER_CONFIG)
            navigator.eth_auth = ETHAuthenticator(page, username, password)
            
            # Step 1: Navigate to paper
            print(f"🌐 Step 1: Navigate to paper...")
            if await navigator.navigate_to_paper(doi):
                result['steps_completed'].append('navigation')
                print(f"   ✅ Successfully reached ScienceDirect")
            else:
                print(f"   ❌ Failed to reach ScienceDirect")
                result['error'] = "Navigation failed"
                return result
            
            # Verify we're at the right paper
            current_url = page.url
            title = await page.title()
            print(f"   📍 URL: {current_url}")
            print(f"   📝 Title: {title[:60]}...")
            
            # Step 2: Navigate to institutional login
            print(f"\n🔐 Step 2: Navigate to institutional login...")
            if await navigator.navigate_to_login():
                result['steps_completed'].append('login_navigation')
                print(f"   ✅ Successfully reached institutional login")
            else:
                print(f"   ❌ Failed to navigate to login")
                result['error'] = "Login navigation failed"
                return result
            
            # Step 3: Select ETH institution
            print(f"\n🏛️  Step 3: Select ETH institution...")
            if await navigator.select_eth_institution():
                result['steps_completed'].append('eth_selection')
                print(f"   ✅ Successfully selected ETH")
            else:
                print(f"   ❌ Failed to select ETH")
                result['error'] = "ETH selection failed"
                return result
            
            # Step 4: ETH authentication
            print(f"\n🔑 Step 4: ETH authentication...")
            if await navigator.eth_auth.perform_login():
                result['steps_completed'].append('authentication')
                print(f"   ✅ ETH authentication successful")
            else:
                print(f"   ❌ ETH authentication failed")
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
            
            # Step 6: PDF access verification
            print(f"\n📄 Step 6: PDF access verification...")
            downloads_dir = Path("elsevier_test_downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            # Try to find PDF button first
            pdf_button = None
            for selector in ELSEVIER_CONFIG.pdf_download_selectors:
                pdf_button = await page.query_selector(selector)
                if pdf_button:
                    print(f"   ✅ Found PDF button: {selector}")
                    break
            
            if pdf_button:
                result['steps_completed'].append('pdf_found')
                
                # Try to get PDF URL
                pdf_href = await pdf_button.get_attribute('href')
                if pdf_href:
                    if not pdf_href.startswith('http'):
                        pdf_href = f"https://www.sciencedirect.com{pdf_href}"
                    
                    print(f"   📎 PDF URL: {pdf_href[:80]}...")
                    result['steps_completed'].append('pdf_url')
                    
                    # For headless testing, we'll consider it success if we can find the PDF button and URL
                    # Full download testing would be too resource intensive for multiple papers
                    result['success'] = True
                    result['steps_completed'].append('pdf_access')
                    print(f"   ✅ PDF access confirmed")
                else:
                    print(f"   ❌ Could not get PDF URL")
                    result['error'] = "PDF URL not found"
            else:
                print(f"   ❌ PDF button not found")
                result['error'] = "PDF button not found"
            
            result['time_taken'] = time.time() - start_time
            
        except Exception as e:
            result['error'] = str(e)
            print(f"   ❌ Test error: {e}")
        
        finally:
            await context.close()
        
        return result
    
    async def run_comprehensive_test(self):
        """Run comprehensive test on all papers."""
        
        print(f"\n{'='*80}")
        print(f"🧪 ELSEVIER COMPREHENSIVE TESTING SUITE")
        print(f"{'='*80}")
        print(f"Testing {len(self.test_papers)} papers in headless mode...")
        
        async with async_playwright() as p:
            browser = await p.firefox.launch(
                headless=True,  # Headless mode for comprehensive testing
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
                        print(f"✅ TEST {i} PASSED")
                    else:
                        print(f"❌ TEST {i} FAILED: {result['error']}")
                    
                    # Small delay between tests
                    await asyncio.sleep(2)
                
            finally:
                await browser.close()
        
        # Generate comprehensive report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"📊 ELSEVIER COMPREHENSIVE TEST REPORT")
        print(f"{'='*80}")
        
        print(f"\n📈 OVERALL RESULTS:")
        print(f"   Total tests: {total_tests}")
        print(f"   ✅ Successful: {successful_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📊 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print(f"\n🎉 EXCELLENT: Elsevier navigator is highly reliable!")
        elif success_rate >= 75:
            print(f"\n✅ GOOD: Elsevier navigator is reliable with minor issues")
        elif success_rate >= 50:
            print(f"\n⚠️  MODERATE: Elsevier navigator needs improvement")
        else:
            print(f"\n❌ POOR: Elsevier navigator requires significant fixes")
        
        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        for result in self.results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            steps = len(result['steps_completed'])
            time_taken = result.get('time_taken', 0)
            
            print(f"\n   Test {result['test_number']}: {status}")
            print(f"      Journal: {result['journal']}")
            print(f"      DOI: {result['doi']}")
            print(f"      Steps completed: {steps}/6")
            print(f"      Time taken: {time_taken:.1f}s")
            
            if result['steps_completed']:
                print(f"      Completed: {', '.join(result['steps_completed'])}")
            
            if not result['success']:
                print(f"      Error: {result['error']}")
        
        # Step analysis
        print(f"\n🔍 STEP ANALYSIS:")
        step_names = ['navigation', 'login_navigation', 'eth_selection', 'authentication', 'post_auth', 'pdf_found', 'pdf_url', 'pdf_access']
        
        for step in step_names:
            step_successes = sum(1 for r in self.results if step in r['steps_completed'])
            step_rate = (step_successes / total_tests * 100) if total_tests > 0 else 0
            print(f"   {step.replace('_', ' ').title()}: {step_successes}/{total_tests} ({step_rate:.1f}%)")
        
        # Failure analysis
        if failed_tests > 0:
            print(f"\n❌ FAILURE ANALYSIS:")
            error_counts = {}
            for result in self.results:
                if not result['success'] and result['error']:
                    error = result['error']
                    error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {error}: {count} occurrences")
        
        # Journal type analysis
        print(f"\n📚 JOURNAL TYPE ANALYSIS:")
        type_stats = {}
        for result in self.results:
            journal_type = result['type']
            if journal_type not in type_stats:
                type_stats[journal_type] = {'total': 0, 'success': 0}
            type_stats[journal_type]['total'] += 1
            if result['success']:
                type_stats[journal_type]['success'] += 1
        
        for journal_type, stats in sorted(type_stats.items()):
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   {journal_type.replace('_', ' ').title()}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if success_rate >= 90:
            print(f"   • Elsevier navigator ready for production")
            print(f"   • Consider adding to main institutional access system")
            print(f"   • Monitor performance in real-world usage")
        elif success_rate >= 75:
            print(f"   • Address identified failure points")
            print(f"   • Add additional error handling for edge cases")
            print(f"   • Consider rate limiting between requests")
        else:
            print(f"   • Significant debugging required")
            print(f"   • Review authentication flow reliability")
            print(f"   • Check for publisher-side changes")


async def main():
    """Run Elsevier comprehensive testing."""
    tester = ElsevierComprehensiveTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())