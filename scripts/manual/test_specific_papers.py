#!/usr/bin/env python3
"""
TEST SPECIFIC ECONOMETRICA PAPERS
=================================

Testing the exact papers you provided to understand why success isn't 100%.
"""

import requests
import time
from pathlib import Path

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

def test_specific_papers():
    """Test the specific papers you provided"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'ETH-Research/1.0',
        'Accept': 'application/pdf',
        'X-API-Key': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Wiley-TDM-Client-Token': API_KEY,
    })
    
    downloads_dir = Path("specific_papers_test")
    downloads_dir.mkdir(exist_ok=True)
    
    # The exact papers you provided
    papers = [
        {
            'url': 'https://onlinelibrary.wiley.com/doi/10.3982/ECTA20404',
            'doi': '10.3982/ECTA20404',
            'journal': 'Econometrica'
        },
        {
            'url': 'https://onlinelibrary.wiley.com/doi/10.3982/ECTA20411', 
            'doi': '10.3982/ECTA20411',
            'journal': 'Econometrica'
        }
    ]
    
    # Also test the ones that worked before to see if they still work
    previous_working = [
        {
            'doi': '10.1111/mafi.12453',
            'journal': 'Mathematical Finance',
            'description': 'Previously worked'
        },
        {
            'doi': '10.1111/jofi.13412',
            'journal': 'Journal of Finance', 
            'description': 'Previously worked'
        },
        {
            'doi': '10.1111/jofi.13404',
            'journal': 'Journal of Finance',
            'description': 'Previously worked'
        }
    ]
    
    print("🎯 TESTING SPECIFIC PAPERS YOU PROVIDED")
    print("=" * 60)
    print("Understanding why success rate isn't 100%")
    print("=" * 60)
    
    all_results = []
    
    # Test your specific Econometrica papers
    print("\n📊 TESTING YOUR ECONOMETRICA PAPERS:")
    for i, paper in enumerate(papers, 1):
        doi = paper['doi']
        journal = paper['journal']
        
        print(f"\n{i}. {journal}")
        print(f"   DOI: {doi}")
        print(f"   URL: {paper['url']}")
        
        result = test_single_paper(session, doi, journal, downloads_dir)
        all_results.append(result)
        
        time.sleep(5)  # Respectful delay
    
    # Test previously working papers to see current status
    print(f"\n📊 RETESTING PREVIOUSLY WORKING PAPERS:")
    for i, paper in enumerate(previous_working, 1):
        doi = paper['doi']
        journal = paper['journal']
        
        print(f"\n{i}. {journal} ({paper['description']})")
        print(f"   DOI: {doi}")
        
        result = test_single_paper(session, doi, journal, downloads_dir)
        all_results.append(result)
        
        time.sleep(5)  # Respectful delay
    
    # Analysis
    print(f"\n{'='*30} ANALYSIS {'='*30}")
    
    successful = sum(1 for r in all_results if r['success'])
    total = len(all_results)
    success_rate = (successful / total * 100) if total > 0 else 0
    
    print(f"Overall success rate: {successful}/{total} ({success_rate:.1f}%)")
    
    # Group by status code
    status_codes = {}
    for result in all_results:
        code = result['status_code']
        if code not in status_codes:
            status_codes[code] = []
        status_codes[code].append(result)
    
    print(f"\n📊 BREAKDOWN BY STATUS CODE:")
    for code, results in status_codes.items():
        count = len(results)
        if code == 200:
            size = sum(r['size_mb'] for r in results if r['success'])
            print(f"  ✅ HTTP 200 (Success): {count} papers ({size:.2f} MB total)")
        elif code == 403:
            print(f"  🚫 HTTP 403 (Forbidden): {count} papers")
            print(f"     Reason: Access denied - may require institutional authentication")
        elif code == 404:
            print(f"  ❌ HTTP 404 (Not Found): {count} papers")
            print(f"     Reason: Paper not in Wiley's TDM system")
        elif code == 500:
            print(f"  🔧 HTTP 500 (Server Error): {count} papers")
            print(f"     Reason: API rate limiting or system issues")
        else:
            print(f"  ❓ HTTP {code}: {count} papers")
    
    # Specific analysis for why not 100%
    print(f"\n🔍 WHY NOT 100% SUCCESS?")
    
    forbidden_count = len(status_codes.get(403, []))
    not_found_count = len(status_codes.get(404, []))
    server_error_count = len(status_codes.get(500, []))
    
    if forbidden_count > 0:
        print(f"1. 🚫 {forbidden_count} papers returned 403 Forbidden")
        print(f"   - Some papers require additional institutional authentication")
        print(f"   - API key may not have access to all content")
        print(f"   - Publisher restrictions on specific articles")
    
    if not_found_count > 0:
        print(f"2. ❌ {not_found_count} papers returned 404 Not Found")
        print(f"   - Papers may not be in Wiley's TDM database yet")
        print(f"   - Recent papers may have delayed API availability")
    
    if server_error_count > 0:
        print(f"3. 🔧 {server_error_count} papers returned 500 Server Error")
        print(f"   - API rate limiting (too many requests)")
        print(f"   - Temporary system issues")
    
    # Recommendations
    print(f"\n💡 ACHIEVING HIGHER SUCCESS RATES:")
    print(f"1. 🕐 Longer delays between requests (30-60 seconds)")
    print(f"2. 🔄 Retry 403/500 errors after waiting")
    print(f"3. 🎯 Focus on papers that consistently work")
    print(f"4. 🔀 Combine TDM API + VPN method for comprehensive coverage")
    print(f"5. ⏰ Try different times of day (off-peak hours)")
    
    if successful > 0:
        print(f"\n📁 DOWNLOADED FILES:")
        pdf_files = list(downloads_dir.glob("*.pdf"))
        total_size = sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)
        print(f"Location: {downloads_dir}")
        print(f"Total size: {total_size:.2f} MB")
        
        for pdf in pdf_files:
            size = pdf.stat().st_size / (1024 * 1024)
            print(f"  📄 {pdf.name} ({size:.2f} MB)")
    
    return all_results

def test_single_paper(session, doi, journal, downloads_dir):
    """Test a single paper"""
    
    result = {
        'doi': doi,
        'journal': journal,
        'success': False,
        'status_code': 0,
        'size_mb': 0,
        'error': None
    }
    
    try:
        url = f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi}"
        response = session.get(url, timeout=20)
        
        result['status_code'] = response.status_code
        
        print(f"   Status: {response.status_code}")
        print(f"   Size: {len(response.content)} bytes")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            
            if 'pdf' in content_type.lower() and len(response.content) > 1000:
                size_mb = len(response.content) / (1024 * 1024)
                result['size_mb'] = size_mb
                result['success'] = True
                
                # Save PDF
                filename = f"specific_{doi.replace('/', '_').replace('.', '_')}.pdf"
                save_path = downloads_dir / filename
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"   ✅ SUCCESS: {size_mb:.2f} MB")
            else:
                result['error'] = f"Not PDF: {content_type}"
                print(f"   ❌ Not PDF")
        
        elif response.status_code == 403:
            result['error'] = "HTTP 403 - Forbidden"
            print(f"   🚫 Forbidden - Access denied")
        
        elif response.status_code == 404:
            result['error'] = "HTTP 404 - Not found"
            print(f"   ❌ Not found in system")
        
        elif response.status_code == 500:
            result['error'] = "HTTP 500 - Server error"
            print(f"   🔧 Server error")
        
        else:
            result['error'] = f"HTTP {response.status_code}"
            print(f"   ❌ HTTP {response.status_code}")
    
    except Exception as e:
        result['error'] = str(e)[:50]
        print(f"   ❌ Error: {str(e)[:30]}")
    
    return result

if __name__ == "__main__":
    test_specific_papers()