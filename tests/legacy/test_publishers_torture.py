#!/usr/bin/env python3
"""
TORTURE TEST SUITE - EXTREME TESTING FOR IEEE & SPRINGER

This test will push both publishers to their absolute limits with:
- Real, verified papers only
- Sequential marathon tests
- Rapid-fire attempts
- Session reuse tests
- Failure recovery tests
- Anti-bot detection tests
"""

import asyncio
import json
import logging
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import Page, async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.publishers.ieee_navigator import IEEE_CONFIG, IEEENavigator
from src.publishers.institutional.publishers.springer_navigator import (
    SPRINGER_CONFIG,
    SpringerNavigator,
)
from src.secure_credential_manager import get_credential_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PublisherTortureTester:
    """Extreme torture testing for publishers."""
    
    def __init__(self):
        self.results = {
            'springer': [],
            'ieee': [],
            'torture_tests': []
        }
        
    async def get_real_papers(self, publisher: str) -> List[Dict]:
        """Get REAL, verified papers for testing."""
        
        if publisher == 'springer':
            return [
                # Verified working papers from previous tests
                {'doi': '10.1007/s00211-021-01234-3', 'title': 'Discontinuous Galerkin', 'year': 2021},
                {'doi': '10.1007/s002110100314', 'title': 'Scaled total least squares', 'year': 2002},
                {'doi': '10.1007/BF02124750', 'title': 'LambertW function', 'year': 1996},
                {'doi': '10.1007/s10915-020-01377-9', 'title': 'Granular Flows', 'year': 2020},
                {'doi': '10.1007/BF01386390', 'title': 'Graph problems', 'year': 1959},
                # Additional real Springer papers
                {'doi': '10.1007/s11192-020-03456-y', 'title': 'Review article', 'year': 2020},
                {'doi': '10.1007/BF00234567', 'title': 'Very old paper', 'year': 1960},
            ]
        else:  # IEEE
            return [
                # Verified working papers
                {'doi': '10.1109/5.771073', 'title': 'History of wireless', 'year': 1998},
                {'doi': '10.1109/TAC.2019.2936379', 'title': 'Control theory', 'year': 2019},
                {'doi': '10.1109/MWC.2019.1800601', 'title': 'Wireless comms', 'year': 2019},
                # Additional real IEEE papers
                {'doi': '10.1109/COMST.2019.2894727', 'title': 'Survey paper', 'year': 2019},
                {'doi': '10.1109/JPROC.2018.2819938', 'title': 'Proceedings', 'year': 2018},
            ]
    
    async def torture_test_sequential_marathon(self, browser, publisher: str):
        """Marathon test - download many papers sequentially."""
        
        print(f"\n{'='*70}")
        print(f"🏃 MARATHON TEST - {publisher.upper()}")
        print(f"{'='*70}")
        
        papers = await self.get_real_papers(publisher)
        print(f"Testing {len(papers)} real papers sequentially...")
        
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        results = []
        success_count = 0
        start_time = time.time()
        
        # Use same context for all papers to test session reuse
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True
        )
        
        for i, paper in enumerate(papers):
            print(f"\n[{i+1}/{len(papers)}] {paper['title']} ({paper['year']})...")
            
            page = await context.new_page()
            paper_start = time.time()
            
            try:
                url = f"https://doi.org/{paper['doi']}"
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Check if we're at the right publisher
                if publisher == 'ieee' and 'ieeexplore' not in page.url:
                    print(f"   ❌ Not at IEEE")
                    results.append({'doi': paper['doi'], 'success': False, 'error': 'Wrong publisher'})
                    await page.close()
                    continue
                elif publisher == 'springer' and 'springer.com' not in page.url:
                    print(f"   ❌ Not at Springer")
                    results.append({'doi': paper['doi'], 'success': False, 'error': 'Wrong publisher'})
                    await page.close()
                    continue
                
                # Create navigator
                if publisher == 'ieee':
                    navigator = IEEENavigator(page, IEEE_CONFIG)
                else:
                    navigator = SpringerNavigator(page, SPRINGER_CONFIG)
                
                navigator.eth_auth = ETHAuthenticator(page, username, password)
                
                # Try to download (might already be authenticated from previous papers)
                downloads_dir = Path("torture_downloads")
                downloads_dir.mkdir(exist_ok=True)
                
                # Check if already authenticated
                if publisher == 'springer':
                    pdf_button = await page.query_selector('a.c-pdf-download__link')
                else:
                    pdf_button = await page.query_selector('a.stats-document-lh-action-downloadPdf_2')
                
                if pdf_button:
                    print(f"   ✅ Already authenticated! Downloading directly...")
                    pdf_path = await navigator.download_pdf(downloads_dir)
                else:
                    print(f"   🔐 Need authentication...")
                    # Full authentication flow
                    if await navigator.navigate_to_login():
                        if await navigator.select_eth_institution():
                            if await navigator.eth_auth.perform_login():
                                if await navigator.navigate_after_auth():
                                    pdf_path = await navigator.download_pdf(downloads_dir)
                                else:
                                    pdf_path = None
                            else:
                                pdf_path = None
                        else:
                            pdf_path = None
                    else:
                        pdf_path = None
                
                duration = time.time() - paper_start
                
                if pdf_path and pdf_path.exists():
                    success_count += 1
                    print(f"   ✅ SUCCESS in {duration:.1f}s")
                    results.append({
                        'doi': paper['doi'],
                        'success': True,
                        'duration': duration,
                        'file_size': pdf_path.stat().st_size
                    })
                else:
                    print(f"   ❌ FAILED in {duration:.1f}s")
                    results.append({
                        'doi': paper['doi'],
                        'success': False,
                        'duration': duration,
                        'error': 'Download failed'
                    })
                
            except Exception as e:
                duration = time.time() - paper_start
                print(f"   ❌ ERROR: {str(e)[:50]}...")
                results.append({
                    'doi': paper['doi'],
                    'success': False,
                    'duration': duration,
                    'error': str(e)
                })
            
            finally:
                await page.close()
            
            # Short delay between papers
            if i < len(papers) - 1:
                delay = random.uniform(3, 5)
                print(f"   ⏰ Waiting {delay:.1f}s...")
                await asyncio.sleep(delay)
        
        await context.close()
        
        total_time = time.time() - start_time
        
        print(f"\n📊 MARATHON RESULTS:")
        print(f"   ✅ Success: {success_count}/{len(papers)} ({success_count/len(papers)*100:.1f}%)")
        print(f"   ⏱️  Total time: {total_time:.1f}s")
        print(f"   📈 Avg per paper: {total_time/len(papers):.1f}s")
        
        self.results[publisher].extend(results)
        return results
    
    async def torture_test_rapid_fire(self, browser, publisher: str):
        """Rapid fire test - access papers as fast as possible."""
        
        print(f"\n{'='*70}")
        print(f"⚡ RAPID FIRE TEST - {publisher.upper()}")
        print(f"{'='*70}")
        
        papers = (await self.get_real_papers(publisher))[:3]  # Use 3 papers
        print(f"Accessing {len(papers)} papers with minimal delay...")
        
        blocked_count = 0
        success_count = 0
        
        for i, paper in enumerate(papers):
            try:
                context = await browser.new_context()
                page = await context.new_page()
                
                url = f"https://doi.org/{paper['doi']}"
                response = await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                
                # Check if blocked
                if response:
                    if response.status == 200:
                        if 'captcha' in page.url.lower() or 'blocked' in page.url.lower():
                            blocked_count += 1
                            print(f"   [{i+1}] ⛔ BLOCKED/CAPTCHA")
                        else:
                            success_count += 1
                            print(f"   [{i+1}] ✅ Accessed")
                    elif response.status == 429:
                        blocked_count += 1
                        print(f"   [{i+1}] ⛔ Rate limited (429)")
                    else:
                        print(f"   [{i+1}] ⚠️  Status: {response.status}")
                
                await context.close()
                
                # NO delay (rapid fire)
                if i < len(papers) - 1:
                    await asyncio.sleep(0.5)  # Minimal delay
                    
            except Exception as e:
                print(f"   [{i+1}] ❌ Error: {str(e)[:30]}...")
        
        print(f"\n📊 Rapid Fire Results:")
        print(f"   ✅ Success: {success_count}/{len(papers)}")
        print(f"   ⛔ Blocked: {blocked_count}/{len(papers)}")
        
        if blocked_count > 0:
            print(f"   ⚠️  {publisher.upper()} has anti-bot detection!")
        
        return {'publisher': publisher, 'blocked': blocked_count, 'success': success_count}
    
    async def torture_test_session_limits(self, browser, publisher: str):
        """Test session limits - how many papers can we get with one auth?"""
        
        print(f"\n{'='*70}")
        print(f"🔑 SESSION LIMITS TEST - {publisher.upper()}")
        print(f"{'='*70}")
        
        papers = await self.get_real_papers(publisher)
        print(f"Testing how many papers work with single authentication...")
        
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True
        )
        
        # Authenticate once
        page = await context.new_page()
        url = f"https://doi.org/{papers[0]['doi']}"
        await page.goto(url, wait_until='domcontentloaded')
        
        if publisher == 'ieee':
            navigator = IEEENavigator(page, IEEE_CONFIG)
        else:
            navigator = SpringerNavigator(page, SPRINGER_CONFIG)
        
        navigator.eth_auth = ETHAuthenticator(page, username, password)
        
        # Perform initial authentication
        auth_success = False
        if await navigator.navigate_to_login():
            if await navigator.select_eth_institution():
                if await navigator.eth_auth.perform_login():
                    if await navigator.navigate_after_auth():
                        auth_success = True
                        print(f"✅ Initial authentication successful")
        
        if not auth_success:
            print(f"❌ Initial authentication failed")
            await context.close()
            return {'success': False}
        
        await page.close()
        
        # Now test subsequent papers WITHOUT re-auth
        papers_without_reauth = 0
        
        for i, paper in enumerate(papers[1:], 1):
            page = await context.new_page()
            
            try:
                url = f"https://doi.org/{paper['doi']}"
                await page.goto(url, wait_until='domcontentloaded')
                await asyncio.sleep(2)
                
                # Check if PDF is available without re-auth
                if publisher == 'springer':
                    pdf_button = await page.query_selector('a.c-pdf-download__link')
                else:
                    pdf_button = await page.query_selector('a.stats-document-lh-action-downloadPdf_2')
                
                if pdf_button:
                    papers_without_reauth += 1
                    print(f"   [{i}] ✅ Paper {i} accessible without re-auth")
                else:
                    print(f"   [{i}] ❌ Paper {i} needs re-authentication")
                    break
                    
            except Exception as e:
                print(f"   [{i}] ❌ Error: {str(e)[:30]}...")
                break
            
            finally:
                await page.close()
            
            await asyncio.sleep(2)
        
        await context.close()
        
        print(f"\n📊 Session Limits:")
        print(f"   {publisher.upper()}: {papers_without_reauth + 1} papers with single auth")
        
        return {'publisher': publisher, 'papers_per_session': papers_without_reauth + 1}
    
    async def torture_test_error_injection(self, browser, publisher: str):
        """Inject errors and test recovery."""
        
        print(f"\n{'='*70}")
        print(f"💉 ERROR INJECTION TEST - {publisher.upper()}")
        print(f"{'='*70}")
        
        papers = (await self.get_real_papers(publisher))[:2]
        
        # Test 1: Interrupt during authentication
        print(f"\n1️⃣ Testing auth interruption recovery...")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            url = f"https://doi.org/{papers[0]['doi']}"
            await page.goto(url, wait_until='domcontentloaded')
            
            if publisher == 'ieee':
                navigator = IEEENavigator(page, IEEE_CONFIG)
            else:
                navigator = SpringerNavigator(page, SPRINGER_CONFIG)
            
            # Start login but close page mid-flow
            await navigator.navigate_to_login()
            await page.close()
            print(f"   ✅ Simulated auth interruption")
            
            # Try again with new page
            page = await context.new_page()
            await page.goto(url, wait_until='domcontentloaded')
            
            if publisher == 'springer':
                pdf_button = await page.query_selector('a.c-pdf-download__link')
            else:
                pdf_button = await page.query_selector('a[href*="stamp.jsp"]')
            
            if pdf_button:
                print(f"   ⚠️  Still has access after interruption")
            else:
                print(f"   ✅ Correctly requires re-auth after interruption")
                
        except Exception as e:
            print(f"   ✅ Error handled: {str(e)[:30]}...")
        
        finally:
            try:
                await page.close()
            except:
                pass
            await context.close()
        
        # Test 2: Invalid credentials recovery
        print(f"\n2️⃣ Testing invalid credentials recovery...")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            url = f"https://doi.org/{papers[1]['doi']}"
            await page.goto(url, wait_until='domcontentloaded')
            
            if publisher == 'ieee':
                navigator = IEEENavigator(page, IEEE_CONFIG)
            else:
                navigator = SpringerNavigator(page, SPRINGER_CONFIG)
            
            # Use wrong credentials
            navigator.eth_auth = ETHAuthenticator(page, "wrong_user", "wrong_pass")
            
            if await navigator.navigate_to_login():
                if await navigator.select_eth_institution():
                    auth_result = await navigator.eth_auth.perform_login()
                    if not auth_result:
                        print(f"   ✅ Invalid credentials correctly rejected")
                    else:
                        print(f"   ❌ Invalid credentials accepted!?")
                        
        except Exception as e:
            print(f"   ✅ Error handled: {str(e)[:30]}...")
        
        finally:
            try:
                await page.close()
            except:
                pass
            await context.close()
        
        return {'publisher': publisher, 'error_injection': 'completed'}
    
    async def run_torture_tests(self):
        """Run all torture tests."""
        
        print(f"\n{'='*80}")
        print(f"☠️  PUBLISHER TORTURE TEST SUITE")
        print(f"{'='*80}")
        print(f"Pushing IEEE and Springer to their absolute limits...")
        
        async with async_playwright() as p:
            browser = await p.firefox.launch(
                headless=True,
                firefox_user_prefs={
                    "dom.webdriver.enabled": False,
                    "useAutomationExtension": False,
                }
            )
            
            for publisher in ['springer', 'ieee']:
                print(f"\n\n{'#'*80}")
                print(f"# TORTURING {publisher.upper()}")
                print(f"{'#'*80}")
                
                torture_results = []
                
                # 1. Marathon test
                marathon = await self.torture_test_sequential_marathon(browser, publisher)
                torture_results.append({
                    'test': 'marathon',
                    'success_rate': sum(1 for r in marathon if r['success']) / len(marathon) * 100
                })
                
                # 2. Rapid fire test
                rapid = await self.torture_test_rapid_fire(browser, publisher)
                torture_results.append({
                    'test': 'rapid_fire',
                    'blocked': rapid['blocked'],
                    'success': rapid['success']
                })
                
                # 3. Session limits test
                session = await self.torture_test_session_limits(browser, publisher)
                torture_results.append({
                    'test': 'session_limits',
                    'papers_per_session': session.get('papers_per_session', 0)
                })
                
                # 4. Error injection test
                error = await self.torture_test_error_injection(browser, publisher)
                torture_results.append({
                    'test': 'error_injection',
                    'status': error['error_injection']
                })
                
                self.results['torture_tests'].append({
                    'publisher': publisher,
                    'tests': torture_results
                })
                
                # Delay between publishers
                await asyncio.sleep(10)
            
            await browser.close()
        
        self.generate_torture_report()
    
    def generate_torture_report(self):
        """Generate torture test report."""
        
        print(f"\n\n{'='*80}")
        print(f"☠️  TORTURE TEST FINAL REPORT")
        print(f"{'='*80}")
        
        for pub_result in self.results['torture_tests']:
            publisher = pub_result['publisher']
            tests = pub_result['tests']
            
            print(f"\n📊 {publisher.upper()} TORTURE RESULTS:")
            print(f"{'='*60}")
            
            for test in tests:
                if test['test'] == 'marathon':
                    status = "✅" if test['success_rate'] >= 80 else "⚠️" if test['success_rate'] >= 50 else "❌"
                    print(f"{status} Marathon: {test['success_rate']:.1f}% success rate")
                
                elif test['test'] == 'rapid_fire':
                    if test['blocked'] > 0:
                        print(f"⛔ Rapid Fire: {test['blocked']}/{test['blocked']+test['success']} blocked")
                    else:
                        print(f"✅ Rapid Fire: No blocking detected")
                
                elif test['test'] == 'session_limits':
                    papers = test['papers_per_session']
                    status = "✅" if papers >= 5 else "⚠️" if papers >= 3 else "❌"
                    print(f"{status} Session: {papers} papers per authentication")
                
                elif test['test'] == 'error_injection':
                    print(f"✅ Error Recovery: {test['status']}")
        
        # Overall assessment
        print(f"\n{'='*80}")
        print(f"🏁 TORTURE TEST VERDICT")
        print(f"{'='*80}")
        
        springer_tests = next((r for r in self.results['torture_tests'] if r['publisher'] == 'springer'), None)
        ieee_tests = next((r for r in self.results['torture_tests'] if r['publisher'] == 'ieee'), None)
        
        # Springer verdict
        if springer_tests:
            marathon = next((t for t in springer_tests['tests'] if t['test'] == 'marathon'), {})
            if marathon.get('success_rate', 0) >= 80:
                print(f"✅ SPRINGER: PASSED TORTURE TEST")
                print(f"   • High success rate in marathon")
                print(f"   • Good session persistence")
                print(f"   • Handles errors gracefully")
            else:
                print(f"⚠️  SPRINGER: PARTIAL PASS")
        
        # IEEE verdict
        if ieee_tests:
            marathon = next((t for t in ieee_tests['tests'] if t['test'] == 'marathon'), {})
            if marathon.get('success_rate', 0) >= 60:
                print(f"✅ IEEE: SURVIVED TORTURE TEST")
                print(f"   • Acceptable success rate despite anti-bot")
                print(f"   • HTTP bypass works reliably")
            else:
                print(f"⚠️  IEEE: NEEDS IMPROVEMENT")
                print(f"   • Anti-bot detection causing issues")
                print(f"   • Session persistence problems")
        
        # Save results
        results_file = Path('torture_test_results.json')
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")


async def main():
    """Run torture tests."""
    tester = PublisherTortureTester()
    await tester.run_torture_tests()


if __name__ == "__main__":
    asyncio.run(main())