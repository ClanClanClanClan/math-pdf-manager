#!/usr/bin/env python3
"""
Test IEEE Subscription Access Patterns
Test multiple IEEE papers to understand ETH's subscription coverage.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.publishers.institutional import download_with_institutional_access

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise

async def test_ieee_subscription_patterns():
    """Test different types of IEEE papers to understand subscription access."""
    
    # Different types of IEEE papers to test
    test_papers = [
        {
            "doi": "10.1109/JPROC.2018.2820126", 
            "description": "Signal Processing (FAILED before)",
            "type": "Proceedings"
        },
        {
            "doi": "10.1109/ACCESS.2020.2982225",
            "description": "IEEE Access (Open Access)",
            "type": "Open Access"
        },
        {
            "doi": "10.1109/TIT.2019.2915312",
            "description": "Information Theory",
            "type": "Transactions"
        },
        {
            "doi": "10.1109/TPAMI.2020.2988574", 
            "description": "Pattern Analysis",
            "type": "Transactions"
        },
        {
            "doi": "10.1109/ICCV.2019.00010",
            "description": "Computer Vision Conference",
            "type": "Conference"
        }
    ]
    
    print(f"\n🧪 TESTING IEEE SUBSCRIPTION PATTERNS")
    print(f"Testing {len(test_papers)} different IEEE papers")
    print("=" * 70)
    
    results = {}
    
    for i, paper in enumerate(test_papers, 1):
        print(f"\n📄 Test {i}/{len(test_papers)}: {paper['description']}")
        print(f"   DOI: {paper['doi']}")
        print(f"   Type: {paper['type']}")
        print("-" * 50)
        
        try:
            # Quick test - just check if we can access PDF
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)  # Run quickly
                context = await browser.new_context()
                page = await context.new_page()
                
                try:
                    from src.secure_credential_manager import get_credential_manager
                    cm = get_credential_manager()
                    username, password = cm.get_eth_credentials()
                    
                    # Get the IEEE URL
                    ieee_url = f"https://doi.org/{paper['doi']}"
                    print(f"   🌐 Navigating to: {ieee_url}")
                    
                    # Navigate and check basic access
                    await page.goto(ieee_url, wait_until='domcontentloaded', timeout=30000)
                    
                    # Quick auth check - look for institutional login
                    login_button = await page.query_selector('a.inst-sign-in')
                    if login_button:
                        print("   🔐 Institutional login available")
                        
                        # Quick auth test (abbreviated)
                        await login_button.click()
                        await page.wait_for_timeout(2000)
                        
                        # Look for SeamlessAccess
                        seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                        if seamless_btn:
                            await seamless_btn.click()
                            await page.wait_for_timeout(2000)
                            
                            # Quick ETH selection
                            search_input = await page.query_selector('input.inst-typeahead-input')
                            if search_input:
                                await search_input.fill("ETH Zurich")
                                await page.wait_for_timeout(2000)
                                
                                eth_option = await page.query_selector('a#ETH\\\\ Zurich\\\\ -\\\\ ETH\\\\ Zurich')
                                if eth_option:
                                    await eth_option.click()
                                    await page.wait_for_timeout(5000)
                                    
                                    # Quick ETH login
                                    if 'ethz.ch' in page.url.lower():
                                        username_field = await page.query_selector('input[name="j_username"]')
                                        password_field = await page.query_selector('input[name="j_password"]')
                                        
                                        if username_field and password_field:
                                            await username_field.fill(username)
                                            await password_field.fill(password)
                                            
                                            submit_btn = await page.query_selector('button[type="submit"]')
                                            if submit_btn:
                                                await submit_btn.click()
                                                await page.wait_for_timeout(10000)
                                                
                                                print("   ✅ Authentication completed")
                                                
                                                # Now test PDF access
                                                if 'ieeexplore.ieee.org' in page.url:
                                                    pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                                                    if pdf_button:
                                                        pdf_href = await pdf_button.get_attribute('href')
                                                        print(f"   📄 PDF button found: {pdf_href}")
                                                        
                                                        # Test direct PDF access
                                                        pdf_url = f"https://ieeexplore.ieee.org{pdf_href}"
                                                        response = await page.goto(pdf_url, timeout=10000)
                                                        
                                                        final_url = page.url
                                                        status = response.status
                                                        
                                                        if '/stamp/stamp.jsp' in final_url:
                                                            print("   🎉 PDF ACCESS GRANTED!")
                                                            results[paper['doi']] = "SUCCESS - PDF accessible"
                                                        elif final_url != pdf_url:
                                                            print(f"   ❌ PDF BLOCKED - Redirected to: {final_url}")
                                                            results[paper['doi']] = "BLOCKED - Subscription issue"
                                                        else:
                                                            print(f"   ⚠️  PDF UNKNOWN - Status: {status}")
                                                            results[paper['doi']] = f"UNKNOWN - Status {status}"
                                                    else:
                                                        print("   ❌ No PDF button found")
                                                        results[paper['doi']] = "NO PDF - Paper may not have full text"
                                                else:
                                                    print("   ❌ Not redirected back to IEEE")
                                                    results[paper['doi']] = "AUTH FAILED - No redirect"
                    else:
                        print("   ⚠️  No institutional login found")
                        results[paper['doi']] = "NO LOGIN - May be open access or restricted"
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    results[paper['doi']] = f"ERROR - {str(e)[:50]}"
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            print(f"   ❌ Critical error: {e}")
            results[paper['doi']] = f"CRITICAL - {str(e)[:50]}"
            
        # Brief pause between tests
        await asyncio.sleep(2)
    
    # Summary
    print(f"\n" + "=" * 70)
    print(f"📊 IEEE SUBSCRIPTION ACCESS SUMMARY")
    print("=" * 70)
    
    success_count = 0
    for paper in test_papers:
        doi = paper['doi']
        result = results.get(doi, "NOT TESTED")
        status = "🎉" if "SUCCESS" in result else "❌" if "BLOCK" in result else "⚠️"
        
        if "SUCCESS" in result:
            success_count += 1
            
        print(f"{status} {paper['type']:15} | {paper['description']:30} | {result}")
    
    print(f"\n📈 Overall Success Rate: {success_count}/{len(test_papers)} ({success_count/len(test_papers)*100:.1f}%)")
    
    if success_count > 0:
        print(f"\n✅ GOOD NEWS: ETH has access to some IEEE papers!")
        print(f"   The institutional access system IS working correctly.")
        print(f"   The issue is subscription coverage for specific papers.")
    else:
        print(f"\n⚠️  CONCERN: No IEEE papers accessible.")
        print(f"   This suggests a broader institutional access issue.")
        
    return results

if __name__ == "__main__":
    results = asyncio.run(test_ieee_subscription_patterns())