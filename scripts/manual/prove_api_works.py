#!/usr/bin/env python3
"""
PROVE API WORKS - CONCRETE EVIDENCE
===================================

Stop with the analysis - let's PROVE what your API key can actually do.
Real attempts, real downloads, real evidence.
"""

import asyncio
import requests
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

class ProveAPIWorks:
    """Actually prove what the API can do with concrete results"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.downloads_dir = Path("proof_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        
        print("💪 PROVE API WORKS - CONCRETE EVIDENCE")
        print("=" * 60)
        print("NO MORE ANALYSIS - ACTUAL PROOF!")
        print("=" * 60)
    
    def aggressive_wiley_test(self):
        """Aggressively test Wiley with every possible method"""
        
        print("\n🔥 AGGRESSIVE WILEY TEST")
        print("-" * 40)
        
        doi = "10.1002/anie.202004934"
        
        # Every possible Wiley URL pattern
        urls_to_try = [
            f"https://onlinelibrary.wiley.com/doi/pdf/{doi}",
            f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
            f"https://onlinelibrary.wiley.com/doi/epdf/{doi}",
            f"https://onlinelibrary.wiley.com/action/downloadSupplement?doi={doi}&file=pdf",
            f"https://advanced.onlinelibrary.wiley.com/doi/pdf/{doi}",
            f"https://chemistry-europe.onlinelibrary.wiley.com/doi/pdf/{doi}",
            f"https://onlinelibrary.wiley.com/doi/{doi}/pdf",
            f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi}",
        ]
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'X-API-Key': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'apikey': self.api_key,
            'Wiley-TDM-Client-Token': self.api_key,
        })
        
        for i, url in enumerate(urls_to_try, 1):
            print(f"\n🔄 Attempt {i}: {url}")
            
            try:
                response = session.get(url, timeout=20, allow_redirects=True)
                
                print(f"  Status: {response.status_code}")
                print(f"  Size: {len(response.content)} bytes")
                print(f"  Type: {response.headers.get('Content-Type', 'Unknown')}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'pdf' in content_type.lower() or response.content.startswith(b'%PDF'):
                        if len(response.content) > 1000:
                            filename = f"wiley_proof_{i}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(response.content)
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"  🎉 PDF DOWNLOADED: {save_path} ({size_mb:.2f} MB)")
                            return True
                        else:
                            print(f"  ⚠️ PDF too small")
                    
                    elif 'html' in content_type.lower():
                        # Save HTML to inspect
                        html_file = self.downloads_dir / f"wiley_response_{i}.html"
                        with open(html_file, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        print(f"  📄 HTML saved: {html_file}")
                        
                        # Quick check for useful content
                        if 'pdf' in response.text.lower():
                            print(f"  🔗 HTML contains PDF references")
                        if 'institutional' in response.text.lower():
                            print(f"  🔐 Institutional access mentioned")
                        if 'login' in response.text.lower():
                            print(f"  🔑 Login required")
                
                elif response.status_code == 403:
                    print(f"  🚫 Forbidden")
                elif response.status_code == 404:
                    print(f"  ❌ Not found")
                else:
                    print(f"  ❌ HTTP {response.status_code}")
            
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:50]}")
        
        return False
    
    def aggressive_elsevier_test(self):
        """Aggressively test Elsevier"""
        
        print("\n🔥 AGGRESSIVE ELSEVIER TEST")
        print("-" * 40)
        
        # Use a real Elsevier DOI
        doi = "10.1016/j.cell.2020.02.058"
        pii = "S0092867420302270"  # PII extracted from DOI
        
        urls_to_try = [
            f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft",
            f"https://www.sciencedirect.com/science/article/pii/{pii}",
            f"https://linkinghub.elsevier.com/retrieve/pii/{pii}",
            f"https://api.elsevier.com/content/article/doi/{doi}",
            f"https://api.elsevier.com/content/article/pii/{pii}",
            f"https://pdf.sciencedirectassets.com/pdf/{pii}.pdf",
        ]
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/pdf,text/html,application/xhtml+xml',
            'X-API-Key': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'X-ELS-APIKey': self.api_key,
            'apikey': self.api_key,
        })
        
        for i, url in enumerate(urls_to_try, 1):
            print(f"\n🔄 Attempt {i}: {url}")
            
            try:
                response = session.get(url, timeout=20, allow_redirects=True)
                
                print(f"  Status: {response.status_code}")
                print(f"  Size: {len(response.content)} bytes")
                print(f"  Type: {response.headers.get('Content-Type', 'Unknown')}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'pdf' in content_type.lower() or response.content.startswith(b'%PDF'):
                        if len(response.content) > 1000:
                            filename = f"elsevier_proof_{i}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(response.content)
                            
                            size_mb = save_path.stat().st_size / (1024 * 1024)
                            print(f"  🎉 PDF DOWNLOADED: {save_path} ({size_mb:.2f} MB)")
                            return True
                    
                    elif 'html' in content_type.lower():
                        # Save for inspection
                        html_file = self.downloads_dir / f"elsevier_response_{i}.html"
                        with open(html_file, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        print(f"  📄 HTML saved: {html_file}")
                
                elif response.status_code == 403:
                    print(f"  🚫 Forbidden")
                else:
                    print(f"  ❌ HTTP {response.status_code}")
            
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:50]}")
        
        return False
    
    async def browser_force_test(self):
        """Use browser to force access with API key in every possible way"""
        
        print("\n🔥 BROWSER FORCE TEST")
        print("-" * 40)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Show what's happening
                args=[
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--allow-running-insecure-content'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                ignore_https_errors=True
            )
            
            # Add API key everywhere possible
            await context.add_cookies([
                {'name': 'apikey', 'value': self.api_key, 'domain': '.wiley.com', 'path': '/'},
                {'name': 'X-API-Key', 'value': self.api_key, 'domain': '.wiley.com', 'path': '/'},
                {'name': 'authorization', 'value': f'Bearer {self.api_key}', 'domain': '.wiley.com', 'path': '/'},
                {'name': 'eth_api_key', 'value': self.api_key, 'domain': '.wiley.com', 'path': '/'},
            ])
            
            page = await context.new_page()
            
            await page.set_extra_http_headers({
                'X-API-Key': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'apikey': self.api_key,
                'Wiley-TDM-Client-Token': self.api_key,
            })
            
            doi = "10.1002/anie.202004934"
            
            try:
                print(f"🔄 Forcing access to: {doi}")
                
                # Go to PDF URL
                pdf_url = f"https://onlinelibrary.wiley.com/doi/pdf/{doi}"
                await page.goto(pdf_url, timeout=30000)
                
                # Wait and screenshot
                await page.wait_for_timeout(5000)
                screenshot_path = self.downloads_dir / "browser_force_test.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 Screenshot: {screenshot_path}")
                
                # Try to extract PDF
                current_url = page.url
                print(f"Final URL: {current_url}")
                
                # Check if PDF loaded
                page_content = await page.content()
                
                if len(page_content) > 10000:  # Substantial content
                    # Try print to PDF
                    pdf_buffer = await page.pdf(format='A4')
                    
                    if len(pdf_buffer) > 1000:
                        filename = "browser_force_proof.pdf"
                        save_path = self.downloads_dir / filename
                        
                        with open(save_path, 'wb') as f:
                            f.write(pdf_buffer)
                        
                        size_mb = save_path.stat().st_size / (1024 * 1024)
                        print(f"🎉 BROWSER PDF: {save_path} ({size_mb:.2f} MB)")
                        
                        await browser.close()
                        return True
                
                await browser.close()
                return False
                
            except Exception as e:
                print(f"❌ Browser test failed: {e}")
                await browser.close()
                return False
    
    def test_alternative_endpoints(self):
        """Test alternative API endpoints that might work"""
        
        print("\n🔥 ALTERNATIVE ENDPOINTS TEST")
        print("-" * 40)
        
        # Test various academic API endpoints
        endpoints = [
            # CrossRef (should work)
            "https://api.crossref.org/works/10.1002/anie.202004934",
            
            # Unpaywall (open access check)
            "https://api.unpaywall.org/v2/10.1002/anie.202004934?email=test@ethz.ch",
            
            # Semantic Scholar
            "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1002/anie.202004934",
            
            # arXiv (if available)
            "https://export.arxiv.org/api/query?search_query=all:10.1002/anie.202004934",
        ]
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Academic-Downloader/1.0',
            'X-API-Key': self.api_key,
        })
        
        for endpoint in endpoints:
            print(f"\n🔄 Testing: {endpoint}")
            
            try:
                response = session.get(endpoint, timeout=15)
                
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"  ✅ JSON response received")
                        
                        # Save response for inspection
                        json_file = self.downloads_dir / f"api_response_{endpoint.split('//')[-1].split('/')[0]}.json"
                        with open(json_file, 'w') as f:
                            json.dump(data, f, indent=2)
                        print(f"  💾 Response saved: {json_file}")
                        
                        # Look for PDF URLs in response
                        response_str = json.dumps(data).lower()
                        if 'pdf' in response_str:
                            print(f"  🔗 PDF references found in response")
                    
                    except:
                        print(f"  📄 Non-JSON response")
                        
                else:
                    print(f"  ❌ HTTP {response.status_code}")
            
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:50]}")
    
    async def run_proof_tests(self):
        """Run all proof tests"""
        
        print("💪 RUNNING PROOF TESTS - SHOW ME WHAT WORKS!")
        print("=" * 70)
        
        results = {
            'wiley_direct': False,
            'elsevier_direct': False,
            'browser_force': False,
            'alternative_apis': False
        }
        
        # Test 1: Aggressive Wiley
        print(f"\n{'='*20} TEST 1: WILEY DIRECT {'='*20}")
        results['wiley_direct'] = self.aggressive_wiley_test()
        
        # Test 2: Aggressive Elsevier  
        print(f"\n{'='*20} TEST 2: ELSEVIER DIRECT {'='*20}")
        results['elsevier_direct'] = self.aggressive_elsevier_test()
        
        # Test 3: Browser force
        print(f"\n{'='*20} TEST 3: BROWSER FORCE {'='*20}")
        results['browser_force'] = await self.browser_force_test()
        
        # Test 4: Alternative endpoints
        print(f"\n{'='*20} TEST 4: ALTERNATIVE APIS {'='*20}")
        self.test_alternative_endpoints()
        results['alternative_apis'] = True  # Always true for data gathering
        
        return results
    
    def show_concrete_evidence(self, results):
        """Show concrete evidence of what worked"""
        
        print(f"\n{'='*30} CONCRETE EVIDENCE {'='*30}")
        
        # Count actual downloaded files
        pdf_files = list(self.downloads_dir.glob("*.pdf"))
        html_files = list(self.downloads_dir.glob("*.html"))
        json_files = list(self.downloads_dir.glob("*.json"))
        image_files = list(self.downloads_dir.glob("*.png"))
        
        print(f"\n📊 ACTUAL RESULTS:")
        print(f"📄 PDFs downloaded: {len(pdf_files)}")
        print(f"📝 HTML responses: {len(html_files)}")
        print(f"📋 JSON responses: {len(json_files)}")
        print(f"📸 Screenshots: {len(image_files)}")
        
        if pdf_files:
            print(f"\n🎉 PDF DOWNLOADS:")
            total_size = 0
            for pdf in pdf_files:
                size_mb = pdf.stat().st_size / (1024 * 1024)
                total_size += size_mb
                print(f"  ✅ {pdf.name} ({size_mb:.2f} MB)")
            print(f"📊 Total PDF size: {total_size:.2f} MB")
        
        if html_files:
            print(f"\n📝 HTML RESPONSES (inspect these):")
            for html in html_files:
                size_kb = html.stat().st_size / 1024
                print(f"  📄 {html.name} ({size_kb:.1f} KB)")
        
        if json_files:
            print(f"\n📋 API RESPONSES:")
            for json_file in json_files:
                print(f"  📋 {json_file.name}")
        
        success_count = sum(results.values())
        
        print(f"\n🎯 FINAL VERDICT:")
        if pdf_files:
            print(f"🎉 SUCCESS: {len(pdf_files)} PDFs actually downloaded!")
            print(f"✅ Your API key CAN access some content")
        else:
            print(f"❌ NO PDFs downloaded")
            print(f"📊 But we have {len(html_files + json_files)} responses to analyze")
        
        print(f"\n📂 All evidence saved in: {self.downloads_dir}")
        print(f"🔍 Inspect the files to see exactly what your API key can access")

async def main():
    """Main proof function"""
    
    print("💪 PROVE API WORKS - NO MORE SPECULATION!")
    print("=" * 70)
    print("Time to show concrete evidence of what your API key can do")
    print("=" * 70)
    
    prover = ProveAPIWorks()
    
    results = await prover.run_proof_tests()
    
    prover.show_concrete_evidence(results)
    
    print(f"\n💪 PROOF TESTS COMPLETE!")
    print(f"🎯 Check the downloaded files for concrete evidence")
    print(f"📂 Location: {prover.downloads_dir}")

if __name__ == "__main__":
    asyncio.run(main())