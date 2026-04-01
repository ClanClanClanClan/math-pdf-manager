#!/usr/bin/env python3
"""
QUICK MATHEMATICAL FINANCE TEST
===============================

Fast test of key journals in Mathematical Finance and Economics
that you actually need for research.
"""

import requests
import time
from pathlib import Path

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

def quick_test():
    """Quick test of math finance journals"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'ETH-Mathematical-Finance-Research/1.0',
        'Accept': 'application/pdf',
        'X-API-Key': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Wiley-TDM-Client-Token': API_KEY,
    })
    
    downloads_dir = Path("quick_mathfin_test")
    downloads_dir.mkdir(exist_ok=True)
    
    # Key journals you mentioned + some that worked before
    test_papers = [
        # Mathematical Finance (if published by Wiley)
        {'doi': '10.1111/mafi.12345', 'journal': 'Mathematical Finance'},
        
        # Economics journals from Wiley
        {'doi': '10.1002/mde.3234', 'journal': 'Managerial and Decision Economics'},  # Known working
        {'doi': '10.1002/bse.2567', 'journal': 'Business Strategy and Environment'},  # Known working
        {'doi': '10.1002/tie.22123', 'journal': 'The International Economy'},         # Known working
        
        # Applied Math from Wiley
        {'doi': '10.1002/mma.6789', 'journal': 'Mathematical Methods in Applied Sciences'},
        {'doi': '10.1002/nla.2167', 'journal': 'Numerical Linear Algebra'},
        
        # Finance/Economics related
        {'doi': '10.1111/jofi.12789', 'journal': 'Journal of Finance'},
        {'doi': '10.1111/ecoj.12456', 'journal': 'The Economic Journal'},
        
        # Check if Econometrica accessible (probably not via Wiley)
        {'doi': '10.3982/ECTA12345', 'journal': 'Econometrica'},
    ]
    
    print("📈 QUICK TEST - MATHEMATICAL FINANCE & ECONOMICS")
    print("=" * 60)
    
    results = {'successful': 0, 'total': len(test_papers), 'size_mb': 0}
    
    for i, paper in enumerate(test_papers, 1):
        doi = paper['doi']
        journal = paper['journal']
        
        print(f"\n{i}. {journal}")
        print(f"   DOI: {doi}")
        
        try:
            url = f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi}"
            response = session.get(url, timeout=15)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' in content_type.lower() and len(response.content) > 1000:
                    size_mb = len(response.content) / (1024 * 1024)
                    
                    filename = f"mathfin_{doi.replace('/', '_').replace('.', '_')}.pdf"
                    save_path = downloads_dir / filename
                    
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    results['successful'] += 1
                    results['size_mb'] += size_mb
                    print(f"   ✅ SUCCESS: {size_mb:.2f} MB")
                else:
                    print(f"   ❌ Not PDF: {content_type}")
            elif response.status_code == 403:
                print(f"   🚫 Forbidden")
            elif response.status_code == 404:
                print(f"   ❌ Not Found")
            elif response.status_code == 500:
                print(f"   🔧 Server Error (rate limited)")
            else:
                print(f"   ❌ HTTP {response.status_code}")
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:30]}")
        
        # Small delay between requests
        if i < len(test_papers):
            time.sleep(3)
    
    # Summary
    print(f"\n{'='*30} RESULTS {'='*30}")
    success_rate = (results['successful'] / results['total']) * 100
    print(f"Success rate: {results['successful']}/{results['total']} ({success_rate:.1f}%)")
    print(f"Total downloaded: {results['size_mb']:.2f} MB")
    
    if results['successful'] > 0:
        print(f"✅ Your API key works on {results['successful']} journals")
        print(f"📂 Files saved in: {downloads_dir}")
        
        pdf_files = list(downloads_dir.glob("*.pdf"))
        for pdf in pdf_files:
            size = pdf.stat().st_size / (1024 * 1024)
            print(f"   📄 {pdf.name} ({size:.2f} MB)")
    else:
        print(f"❌ No successful downloads from your research area")
        print(f"💡 Mathematical Finance journals may not be in Wiley's TDM system")
        print(f"💡 Focus on general Economics journals from Wiley that worked")
    
    return results

if __name__ == "__main__":
    quick_test()