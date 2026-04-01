#!/usr/bin/env python3
"""
Springer Headless Mode Test - Fast Version

Quick test of Springer institutional access in headless mode.
"""

import asyncio
import json
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


async def test_springer_headless_fast():
    """Fast test of Springer with 3 papers in headless mode."""
    
    # Test with 3 verified papers
    test_papers = [
        {
            'title': 'Discontinuous Galerkin Algorithms',
            'doi': '10.1007/s00211-021-01234-3',
            'field': 'Numerische Mathematik'
        },
        {
            'title': 'Scaled Total Least Squares', 
            'doi': '10.1007/s002110100314',
            'field': 'Numerische Mathematik'
        },
        {
            'title': 'LambertW Function',
            'doi': '10.1007/BF02124750',
            'field': 'Computational Mathematics'
        }
    ]
    
    success_count = 0
    results = []
    
    print(f"\n{'='*70}")
    print(f"🤖 SPRINGER HEADLESS TEST (Fast)")
    print(f"{'='*70}")
    print(f"Testing {len(test_papers)} papers in headless mode")
    print()
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=True,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "general.useragent.override": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
            }
        )
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        for i, paper in enumerate(test_papers, 1):
            print(f"\n{'='*50}")
            print(f"📄 PAPER {i}: {paper['title'][:30]}...")
            print(f"{'='*50}")
            print(f"DOI: {paper['doi']}")
            
            result = {
                'paper_num': i,
                'title': paper['title'],
                'doi': paper['doi'],
                'success': False,
                'file_size': 0,
                'error': None
            }
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                accept_downloads=True
            )
            page = await context.new_page()
            
            try:
                # Navigate
                print(f"🌐 Navigating...")
                url = f"https://doi.org/{paper['doi']}"
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(1)
                
                if 'springer.com' not in page.url:
                    result['error'] = "Not at Springer"
                    results.append(result)
                    continue
                
                # Create navigator
                navigator = SpringerNavigator(page, SPRINGER_CONFIG)
                navigator.eth_auth = ETHAuthenticator(page, username, password)
                
                # Login flow
                print(f"🔐 Login...")
                if not await navigator.navigate_to_login():
                    result['error'] = "Login nav failed"
                    results.append(result)
                    continue
                
                print(f"🏛️  ETH selection...")
                if not await navigator.select_eth_institution():
                    result['error'] = "ETH selection failed"
                    results.append(result)
                    continue
                
                print(f"🔑 ETH auth...")
                if not await navigator.eth_auth.perform_login():
                    result['error'] = "ETH auth failed"
                    results.append(result)
                    continue
                
                print(f"🔄 Post-auth...")
                if not await navigator.navigate_after_auth():
                    result['error'] = "Post-auth failed"
                    results.append(result)
                    continue
                
                # Download
                print(f"📄 Download...")
                downloads_dir = Path("downloads")
                downloads_dir.mkdir(exist_ok=True)
                
                pdf_path = await navigator.download_pdf(downloads_dir)
                
                if pdf_path and pdf_path.exists():
                    result['success'] = True
                    result['file_size'] = pdf_path.stat().st_size
                    success_count += 1
                    print(f"✅ SUCCESS! {result['file_size']:,} bytes")
                else:
                    result['error'] = "Download failed"
                    print(f"❌ Download failed")
                
                results.append(result)
                
            except Exception as e:
                print(f"❌ ERROR: {e}")
                result['error'] = str(e)
                results.append(result)
            
            finally:
                await context.close()
            
            # Short delay
            if i < len(test_papers):
                await asyncio.sleep(random.uniform(3, 5))
        
        await browser.close()
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SPRINGER HEADLESS RESULTS")
    print(f"{'='*70}")
    print(f"✅ Successful: {success_count}/{len(test_papers)}")
    print(f"📈 Success rate: {(success_count/len(test_papers)*100):.1f}%")
    print()
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['title'][:40]}...")
        if result['file_size'] > 0:
            print(f"   Size: {result['file_size']:,} bytes")
        if result['error']:
            print(f"   Error: {result['error']}")
    
    # Save results
    results_file = Path('springer_headless_fast_results.json')
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'total_papers': len(test_papers),
            'success_count': success_count,
            'success_rate': success_count / len(test_papers) * 100,
            'results': results
        }, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")
    
    if success_count == len(test_papers):
        print("\n🏆 PERFECT SUCCESS IN HEADLESS MODE!")
        print("Springer is production-ready!")
    elif success_count >= 2:
        print(f"\n✅ GOOD SUCCESS RATE!")
        print("Springer implementation is robust!")
    else:
        print(f"\n⚠️  Needs improvement")


if __name__ == "__main__":
    asyncio.run(test_springer_headless_fast())