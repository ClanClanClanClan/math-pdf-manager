#!/usr/bin/env python3
"""
FOCUSED PUBLISHER TEST - NO VPN
==============================

Quick focused test of key publishers without VPN:
- 2-3 Wiley papers
- 2 Elsevier papers  
- Fast execution with detailed results
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent))

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

class FocusedPublisherTest:
    """Focused test of key publishers"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.downloads_dir = Path("focused_test_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        
        print("🎯 FOCUSED PUBLISHER TEST - NO VPN")
        print("=" * 60)
        print("✅ Quick test of Wiley + Elsevier without VPN")
        print("✅ Testing true API-only access")
        print("=" * 60)
    
    def check_vpn_status(self) -> bool:
        """Check VPN status"""
        try:
            cisco_path = "/opt/cisco/secureclient/bin/vpn"
            result = subprocess.run([cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=5)
            connected = "state: Connected" in result.stdout
            
            status = "🔌 CONNECTED" if connected else "🔌 DISCONNECTED"
            print(f"VPN Status: {status}")
            
            return connected
        except:
            print("VPN Status: ❓ Cannot determine")
            return False
    
    async def quick_test_paper(self, paper: dict) -> dict:
        """Quick test of a single paper"""
        
        doi = paper['doi']
        title = paper['title']
        publisher = paper['publisher']
        
        print(f"\n📄 TESTING: {publisher} - {doi}")
        print("-" * 40)
        
        result = {
            'doi': doi,
            'title': title,
            'publisher': publisher,
            'success': False,
            'access_method': None,
            'file_size': 0,
            'status': 'Failed'
        }
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            # Add API key
            await page.set_extra_http_headers({
                'X-API-Key': self.api_key,
                'Authorization': f'Bearer {self.api_key}'
            })
            
            try:
                # Test main URL patterns for each publisher
                if 'wiley' in publisher.lower():
                    test_urls = [
                        f"https://onlinelibrary.wiley.com/doi/pdf/{doi}",
                        f"https://onlinelibrary.wiley.com/doi/{doi}"
                    ]
                elif 'elsevier' in publisher.lower():
                    # Extract PII from DOI for Elsevier
                    pii = doi.split('/')[-1] if '/' in doi else doi
                    test_urls = [
                        f"https://www.sciencedirect.com/science/article/pii/{pii}",
                        f"https://linkinghub.elsevier.com/retrieve/pii/{pii}"
                    ]
                else:
                    test_urls = [f"https://doi.org/{doi}"]
                
                for i, url in enumerate(test_urls, 1):
                    print(f"🔄 Attempt {i}: {url[:50]}...")
                    
                    try:
                        response = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                        
                        if response:
                            status = response.status
                            content_type = response.headers.get('content-type', '')
                            
                            print(f"  Status: {status}, Type: {content_type[:30]}...")
                            
                            if status == 200:
                                # Direct PDF
                                if 'pdf' in content_type.lower():
                                    pdf_buffer = await response.body()
                                    
                                    if len(pdf_buffer) > 1000:
                                        filename = f"{publisher.lower()}_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                        save_path = self.downloads_dir / filename
                                        
                                        with open(save_path, 'wb') as f:
                                            f.write(pdf_buffer)
                                        
                                        size_mb = save_path.stat().st_size / (1024 * 1024)
                                        print(f"  🎉 SUCCESS: Direct PDF ({size_mb:.2f} MB)")
                                        
                                        result.update({
                                            'success': True,
                                            'access_method': 'Direct PDF',
                                            'file_size': size_mb,
                                            'status': 'Downloaded'
                                        })
                                        
                                        await browser.close()
                                        return result
                                
                                # HTML page - check for access info
                                elif 'html' in content_type.lower():
                                    # Handle cookies
                                    try:
                                        cookie_btn = await page.wait_for_selector('button:has-text("Accept")', timeout=3000)
                                        if cookie_btn:
                                            await cookie_btn.click()
                                            await page.wait_for_timeout(1000)
                                    except:
                                        pass
                                    
                                    page_text = await page.inner_text('body')
                                    
                                    # Check access status
                                    if 'access denied' in page_text.lower() or 'forbidden' in page_text.lower():
                                        result['status'] = 'Access Denied'
                                        print("  🚫 Access denied")
                                    elif 'subscription' in page_text.lower() or 'paywall' in page_text.lower():
                                        result['status'] = 'Paywall'
                                        print("  💰 Paywall")
                                    elif 'institutional' in page_text.lower() or 'login' in page_text.lower():
                                        result['status'] = 'Needs Institutional Login'
                                        print("  🔐 Institutional login required")
                                    else:
                                        result['status'] = 'HTML Page Loaded'
                                        print("  📄 HTML page accessible")
                                        
                                        # Quick check for PDF links
                                        pdf_links = await page.query_selector_all('a[href*="pdf"]')
                                        if pdf_links:
                                            print(f"  🔗 Found {len(pdf_links)} PDF links")
                                            result['status'] += f' ({len(pdf_links)} PDF links)'
                            
                            elif status == 403:
                                result['status'] = 'HTTP 403 Forbidden'
                                print("  🚫 HTTP 403")
                            elif status == 404:
                                result['status'] = 'HTTP 404 Not Found'
                                print("  ❌ HTTP 404")
                            else:
                                result['status'] = f'HTTP {status}'
                                print(f"  ❌ HTTP {status}")
                        
                        else:
                            result['status'] = 'No Response'
                            print("  ❌ No response")
                    
                    except Exception as e:
                        print(f"  ❌ Error: {str(e)[:40]}")
                        result['status'] = f'Error: {str(e)[:40]}'
                
                await browser.close()
                return result
                
            except Exception as e:
                print(f"❌ Test error: {e}")
                result['status'] = f'Test error: {str(e)[:40]}'
                await browser.close()
                return result
    
    async def run_focused_test(self) -> dict:
        """Run focused test"""
        
        print("🧪 FOCUSED PUBLISHER TEST")
        print("=" * 60)
        
        # Check VPN status
        vpn_connected = self.check_vpn_status()
        
        # Test papers - focused selection
        test_papers = [
            # Wiley papers
            {
                'doi': '10.1002/anie.202004934',
                'title': 'Template-Directed Copying of RNA',
                'publisher': 'Wiley'
            },
            {
                'doi': '10.1002/adma.202001924',
                'title': 'Nanoparticle-Based Electrodes',
                'publisher': 'Wiley'
            },
            
            # Elsevier papers
            {
                'doi': '10.1016/j.cell.2020.02.058',
                'title': 'Cell Biology Research',
                'publisher': 'Elsevier'
            },
            {
                'doi': '10.1016/j.jmb.2020.04.012',
                'title': 'Molecular Biology Research',
                'publisher': 'Elsevier'
            }
        ]
        
        results = {
            'total': len(test_papers),
            'successful': 0,
            'failed': 0,
            'papers': []
        }
        
        for i, paper in enumerate(test_papers, 1):
            print(f"\n{'='*10} PAPER {i}/{len(test_papers)} {'='*10}")
            
            result = await self.quick_test_paper(paper)
            results['papers'].append(result)
            
            if result['success']:
                results['successful'] += 1
                print(f"✅ SUCCESS")
            else:
                results['failed'] += 1
                print(f"❌ FAILED - {result['status']}")
        
        return results

async def main():
    """Main function"""
    
    print("🎯 FOCUSED PUBLISHER TEST - NO VPN")
    print("=" * 70)
    print("Quick test of your API key with major publishers")
    print("=" * 70)
    
    tester = FocusedPublisherTest()
    
    results = await tester.run_focused_test()
    
    # Results summary
    print(f"\n{'='*20} FINAL RESULTS {'='*20}")
    print(f"Total papers tested: {results['total']}")
    print(f"Successfully downloaded: {results['successful']}")
    print(f"Failed: {results['failed']}")
    success_rate = (results['successful'] / results['total']) * 100 if results['total'] else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    print(f"\n📊 DETAILED RESULTS:")
    wiley_results = []
    elsevier_results = []
    
    for result in results['papers']:
        status_line = f"  {result['publisher']}: {result['status']}"
        if result['success']:
            status_line += f" ({result['file_size']:.2f} MB)"
        print(status_line)
        
        if 'wiley' in result['publisher'].lower():
            wiley_results.append(result)
        elif 'elsevier' in result['publisher'].lower():
            elsevier_results.append(result)
    
    # Publisher-specific analysis
    print(f"\n🔍 PUBLISHER ANALYSIS:")
    
    wiley_success = sum(1 for r in wiley_results if r['success'])
    print(f"  Wiley: {wiley_success}/{len(wiley_results)} successful")
    
    elsevier_success = sum(1 for r in elsevier_results if r['success'])
    print(f"  Elsevier: {elsevier_success}/{len(elsevier_results)} successful")
    
    # Show downloaded files
    if results['successful'] > 0:
        print(f"\n📁 DOWNLOADED FILES:")
        pdf_files = list(tester.downloads_dir.glob("*.pdf"))
        total_size = 0
        
        for pdf_file in pdf_files:
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            total_size += size_mb
            print(f"  📄 {pdf_file.name} ({size_mb:.2f} MB)")
        
        print(f"\n✅ Total downloaded: {total_size:.2f} MB")
        print(f"📂 Location: {tester.downloads_dir}")
    
    print(f"\n💡 API KEY ANALYSIS:")
    print(f"✅ Your API key: {API_KEY[:20]}...")
    
    if results['successful'] > 0:
        print(f"✅ API provides direct access to some content")
        print(f"✅ No VPN required for accessible papers")
    else:
        print(f"ℹ️ API key may require institutional authentication")
        print(f"ℹ️ Most content behind institutional access controls")
    
    print(f"\n🏆 FOCUSED TEST COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())