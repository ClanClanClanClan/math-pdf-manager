#!/usr/bin/env python3
"""
Springer Headless Mode Test

Test Springer institutional access in headless mode with multiple papers
to verify reliability and robustness.
"""

import asyncio
import json
import logging
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.publishers.springer_navigator import (
    SPRINGER_CONFIG,
    SpringerNavigator,
)
from src.secure_credential_manager import get_credential_manager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


async def test_springer_headless():
    """Test Springer with multiple papers in headless mode."""
    
    # Test papers - verified existing Springer papers
    test_papers = [
        {
            'title': 'Discontinuous Galerkin Algorithms',
            'doi': '10.1007/s00211-021-01234-3',  # Our proven working paper
            'field': 'Numerische Mathematik'
        },
        {
            'title': 'Scaled Total Least Squares',
            'doi': '10.1007/s002110100314',  # Verified valid
            'field': 'Numerische Mathematik'
        },
        {
            'title': 'LambertW Function',
            'doi': '10.1007/BF02124750',  # Verified valid
            'field': 'Advances in Computational Mathematics'
        },
        {
            'title': 'Dry Granular Flows',
            'doi': '10.1007/s10915-020-01377-9',  # Verified valid
            'field': 'Journal of Scientific Computing'
        },
        {
            'title': 'Test with Original Again',
            'doi': '10.1007/s00211-021-01234-3',  # Use our proven paper twice to test reliability
            'field': 'Numerische Mathematik (Duplicate Test)'
        }
    ]
    
    success_count = 0
    results = []
    
    print(f"\n{'='*80}")
    print(f"🤖 SPRINGER HEADLESS MODE TEST")
    print(f"{'='*80}")
    print(f"Testing {len(test_papers)} papers in HEADLESS mode")
    print()
    
    async with async_playwright() as p:
        # HEADLESS Firefox with stealth configuration
        browser = await p.firefox.launch(
            headless=True,  # ← HEADLESS MODE
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "marionette.enabled": False,
                "remote.enabled": False,
                "general.useragent.override": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
                "general.platform.override": "MacIntel",
                "general.oscpu.override": "Intel Mac OS X 10.15",
                "intl.accept_languages": "en-US,en",
                "intl.locale.requested": "en-US",
                # Additional stealth for headless
                "media.peerconnection.enabled": False,
                "media.navigator.enabled": False,
                "permissions.default.microphone": 2,
                "permissions.default.camera": 2,
                "permissions.default.geo": 2,
                "permissions.default.desktop-notification": 2,
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            screen={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0',
            locale='en-US',
            timezone_id='America/New_York',
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            accept_downloads=True,
            bypass_csp=True,
            ignore_https_errors=False,
            java_script_enabled=True,
        )
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        for i, paper in enumerate(test_papers, 1):
            print(f"\n{'='*70}")
            print(f"📄 PAPER {i}/{len(test_papers)}: {paper['title']}")
            print(f"{'='*70}")
            print(f"DOI: {paper['doi']}")
            print(f"Field: {paper['field']}")
            
            result = {
                'paper_num': i,
                'title': paper['title'],
                'doi': paper['doi'],
                'field': paper['field'],
                'success': False,
                'mode': 'headless',
                'file_size': 0,
                'error': None,
                'steps': {
                    'navigation': False,
                    'login_nav': False,
                    'eth_selection': False,
                    'eth_auth': False,
                    'post_auth': False,
                    'pdf_download': False
                }
            }
            
            page = await context.new_page()
            
            try:
                # Step 1: Navigate to paper
                print(f"🌐 HEADLESS: Navigating to DOI...")
                url = f"https://doi.org/{paper['doi']}"
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(random.uniform(2, 3))
                
                print(f"📍 HEADLESS: Current URL: {page.url}")
                
                if 'springer.com' not in page.url:
                    # DOI might not exist or be invalid, try one more check
                    print(f"⚠️  HEADLESS: Not at Springer, at: {page.url}")
                    
                    # If it's a 404 or error page, mark as invalid DOI
                    if '404' in page.url or 'error' in page.url.lower():
                        result['error'] = "Invalid DOI - paper not found"
                    else:
                        result['error'] = f"Not redirected to Springer: {page.url}"
                    
                    results.append(result)
                    await page.close()
                    continue
                
                result['steps']['navigation'] = True
                
                # Create navigator
                navigator = SpringerNavigator(page, SPRINGER_CONFIG)
                navigator.eth_auth = ETHAuthenticator(page, username, password)
                
                # Step 2: Navigate to login
                print(f"🔐 HEADLESS: Navigate to institutional login...")
                login_success = await navigator.navigate_to_login()
                
                if not login_success:
                    result['error'] = "Failed to navigate to login"
                    results.append(result)
                    await page.close()
                    continue
                
                result['steps']['login_nav'] = True
                print(f"✅ HEADLESS: At WAYF page")
                
                # Step 3: Select ETH
                print(f"🏛️  HEADLESS: Select ETH Zurich...")
                eth_success = await navigator.select_eth_institution()
                
                if not eth_success:
                    result['error'] = "Failed to select ETH"
                    results.append(result)
                    await page.close()
                    continue
                
                result['steps']['eth_selection'] = True
                print(f"✅ HEADLESS: ETH selected, at login page")
                
                # Step 4: ETH authentication
                print(f"🔑 HEADLESS: ETH authentication...")
                auth_success = await navigator.eth_auth.perform_login()
                
                if not auth_success:
                    result['error'] = "ETH authentication failed"
                    results.append(result)
                    await page.close()
                    continue
                
                result['steps']['eth_auth'] = True
                print(f"✅ HEADLESS: ETH auth successful")
                
                # Step 5: Post-auth redirect
                print(f"🔄 HEADLESS: Post-auth handling...")
                redirect_success = await navigator.navigate_after_auth()
                
                if not redirect_success:
                    result['error'] = "Post-auth redirect failed"
                    results.append(result)
                    await page.close()
                    continue
                
                result['steps']['post_auth'] = True
                print(f"✅ HEADLESS: Back at Springer with access")
                
                # Step 6: PDF download
                print(f"📄 HEADLESS: PDF download...")
                downloads_dir = Path("downloads")
                downloads_dir.mkdir(exist_ok=True)
                
                pdf_path = await navigator.download_pdf(downloads_dir)
                
                if pdf_path and pdf_path.exists():
                    result['steps']['pdf_download'] = True
                    result['success'] = True
                    result['file_size'] = pdf_path.stat().st_size
                    success_count += 1
                    
                    print(f"🎉 HEADLESS SUCCESS! PDF downloaded!")
                    print(f"📁 File: {pdf_path}")
                    print(f"📊 Size: {result['file_size']:,} bytes")
                else:
                    result['error'] = "PDF download failed"
                    print(f"❌ HEADLESS: PDF download failed")
                
                results.append(result)
                
            except Exception as e:
                print(f"❌ HEADLESS ERROR: {e}")
                result['error'] = str(e)
                results.append(result)
            
            finally:
                await page.close()
            
            # Delay between papers
            if i < len(test_papers):
                delay = random.uniform(10, 15)
                print(f"⏰ Waiting {delay:.1f}s before next paper...")
                await asyncio.sleep(delay)
        
        await browser.close()
    
    # Print comprehensive summary
    print(f"\n{'='*80}")
    print(f"📊 SPRINGER HEADLESS TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Mode: HEADLESS (invisible browser)")
    print(f"✅ Successful downloads: {success_count}/{len(test_papers)}")
    print(f"❌ Failed downloads: {len(test_papers) - success_count}")
    print(f"📈 Success rate: {(success_count / len(test_papers) * 100):.1f}%")
    print()
    
    # Step-by-step analysis
    step_counts = {
        'navigation': sum(1 for r in results if r['steps']['navigation']),
        'login_nav': sum(1 for r in results if r['steps']['login_nav']),
        'eth_selection': sum(1 for r in results if r['steps']['eth_selection']),
        'eth_auth': sum(1 for r in results if r['steps']['eth_auth']),
        'post_auth': sum(1 for r in results if r['steps']['post_auth']),
        'pdf_download': sum(1 for r in results if r['steps']['pdf_download'])
    }
    
    print("📋 STEP-BY-STEP SUCCESS RATES:")
    print("-" * 50)
    for step, count in step_counts.items():
        rate = (count / len(test_papers)) * 100
        status = "✅" if rate == 100 else "⚠️" if rate >= 80 else "❌"
        print(f"{status} {step.replace('_', ' ').title()}: {count}/{len(test_papers)} ({rate:.1f}%)")
    
    print(f"\n📋 DETAILED RESULTS:")
    print("-" * 80)
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} Paper {result['paper_num']}: {result['title']}")
        print(f"   DOI: {result['doi']}")
        print(f"   Field: {result['field']}")
        if result['file_size'] > 0:
            print(f"   Size: {result['file_size']:,} bytes")
        if result['error']:
            print(f"   Error: {result['error']}")
        
        # Show which step failed
        failed_step = None
        for step, success in result['steps'].items():
            if not success:
                failed_step = step
                break
        if failed_step:
            print(f"   Failed at: {failed_step.replace('_', ' ')}")
        print()
    
    # Save detailed results
    results_file = Path('springer_headless_results.json')
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'mode': 'headless',
            'total_papers': len(test_papers),
            'success_count': success_count,
            'success_rate': success_count / len(test_papers) * 100,
            'step_success_rates': {k: (v / len(test_papers)) * 100 for k, v in step_counts.items()},
            'results': results
        }, f, indent=2, default=str)
    
    print(f"📄 Results saved to: {results_file}")
    
    if success_count == len(test_papers):
        print("\n🏆 PERFECT SUCCESS IN HEADLESS MODE!")
        print("Springer institutional access is production-ready!")
    elif success_count >= len(test_papers) * 0.8:  # 80% success
        print(f"\n✅ GOOD SUCCESS RATE ({(success_count/len(test_papers)*100):.1f}%)")
        print("Springer implementation is robust!")
    else:
        print(f"\n⚠️  LOW SUCCESS RATE ({(success_count/len(test_papers)*100):.1f}%)")
        print("Springer implementation needs improvement")


if __name__ == "__main__":
    asyncio.run(test_springer_headless())