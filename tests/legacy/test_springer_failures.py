#!/usr/bin/env python3
"""
Test the Springer papers that failed in the comprehensive test
with improved navigator timing.
"""

import asyncio
import json
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


async def test_springer_failures():
    """Test the papers that failed in comprehensive test."""
    
    # Test with the papers that failed (excluding the one that worked)
    failing_papers = [
        {
            'title': 'Scaled total least squares fundamentals',
            'doi': '10.1007/s002110100314', 
            'journal': 'Numerische Mathematik'
        },
        {
            'title': 'A note on two problems in connexion with graphs',
            'doi': '10.1007/BF01386390',
            'journal': 'Numerische Mathematik'
        },
        {
            'title': 'On the LambertW function',
            'doi': '10.1007/BF02124750',
            'journal': 'Advances in Computational Mathematics'
        }
    ]
    
    success_count = 0
    results = []
    
    print(f"\n{'='*70}")
    print(f"🔧 SPRINGER FAILURE ANALYSIS - Fixed Navigator")
    print(f"{'='*70}")
    print(f"Testing {len(failing_papers)} papers that failed previously")
    print()
    
    async with async_playwright() as p:
        # HEADLESS Firefox
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
        
        for i, paper in enumerate(failing_papers, 1):
            print(f"\n{'='*50}")
            print(f"📄 PAPER {i}: {paper['title'][:35]}...")
            print(f"{'='*50}")
            print(f"DOI: {paper['doi']}")
            
            result = {
                'paper_num': i,
                'title': paper['title'],
                'doi': paper['doi'],
                'success': False,
                'file_size': 0,
                'duration': 0,
                'error': None
            }
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                accept_downloads=True
            )
            page = await context.new_page()
            
            start_time = time.time()
            
            try:
                # Navigate
                print(f"🌐 Navigating...")
                url = f"https://doi.org/{paper['doi']}"
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                
                if 'springer.com' not in page.url:
                    result['error'] = "Not at Springer"
                    results.append(result)
                    continue
                
                # Create navigator with improved timing
                navigator = SpringerNavigator(page, SPRINGER_CONFIG)
                navigator.eth_auth = ETHAuthenticator(page, username, password)
                
                # Test login navigation (this was the failing step)
                print(f"🔐 Testing improved login navigation...")
                if not await navigator.navigate_to_login():
                    result['error'] = "Login nav failed (even with improvements)"
                    results.append(result)
                    continue
                
                print(f"✅ Login navigation SUCCESS!")
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
                    print(f"🎉 SUCCESS! {result['file_size']:,} bytes")
                else:
                    result['error'] = "Download failed"
                    print(f"❌ Download failed")
                
                results.append(result)
                
            except Exception as e:
                print(f"❌ ERROR: {e}")
                result['error'] = str(e)
                results.append(result)
            
            finally:
                result['duration'] = time.time() - start_time
                await context.close()
            
            # Short delay
            if i < len(failing_papers):
                await asyncio.sleep(5)
        
        await browser.close()
    
    # Results
    print(f"\n{'='*70}")
    print(f"📊 FAILURE ANALYSIS RESULTS")
    print(f"{'='*70}")
    print(f"✅ Now successful: {success_count}/{len(failing_papers)}")
    print(f"❌ Still failing: {len(failing_papers) - success_count}")
    print(f"📈 Improvement rate: {(success_count/len(failing_papers)*100):.1f}%")
    print()
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['title'][:50]}...")
        if result['file_size'] > 0:
            print(f"   Size: {result['file_size']:,} bytes")
        if result['error']:
            print(f"   Error: {result['error']}")
        print(f"   Duration: {result['duration']:.1f}s")
    
    if success_count == len(failing_papers):
        print(f"\n🏆 ALL FAILURES FIXED!")
        print(f"✅ Navigator improvements successful")
        print(f"🚀 Ready to re-run comprehensive test")
    elif success_count > 0:
        print(f"\n✅ PARTIAL SUCCESS")
        print(f"🔧 {success_count} papers now working with improved navigator")
    else:
        print(f"\n❌ Still having issues")
        print(f"🔍 Need further investigation")


if __name__ == "__main__":
    asyncio.run(test_springer_failures())