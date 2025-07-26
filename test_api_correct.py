#!/usr/bin/env python3
"""
CORRECT API TEST
================

Using the correct API pattern discovered earlier
"""

import requests
from pathlib import Path
import time

def test_api_correct():
    """Test with correct API usage"""
    
    api_key = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"
    
    # Test papers from different journals
    test_papers = [
        # Papers that worked before
        {'doi': '10.1111/jpet.12457', 'journal': 'Journal of Public Economic Theory'},
        {'doi': '10.1002/aic.17888', 'journal': 'AIChE Journal'},
        {'doi': '10.1111/jofi.12875', 'journal': 'Journal of Finance'},
        # Mathematical Finance papers
        {'doi': '10.1111/mafi.12301', 'journal': 'Mathematical Finance'},
        {'doi': '10.1111/mafi.12456', 'journal': 'Mathematical Finance'},
        # Econometrica papers
        {'doi': '10.3982/ECTA20404', 'journal': 'Econometrica'},
        {'doi': '10.3982/ECTA20411', 'journal': 'Econometrica'},
    ]
    
    print("🧠 TESTING CORRECT API USAGE")
    print("=" * 60)
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print("=" * 60)
    
    downloads_dir = Path("api_correct_results")
    downloads_dir.mkdir(exist_ok=True)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'ETH-Research/1.0',
        'Accept': 'application/pdf',
    })
    
    successes = 0
    
    for i, paper in enumerate(test_papers, 1):
        print(f"\n📄 [{i}/{len(test_papers)}] {paper['journal']}")
        print(f"DOI: {paper['doi']}")
        
        # Correct endpoint with apikey as query parameter
        url = f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{paper['doi']}"
        params = {'apikey': api_key}
        
        try:
            response = session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                if len(response.content) > 10000:
                    filename = f"{paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                    save_path = downloads_dir / filename
                    
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    size_mb = save_path.stat().st_size / (1024 * 1024)
                    print(f"✅ SUCCESS: Downloaded {size_mb:.2f} MB")
                    successes += 1
                else:
                    print(f"❌ Empty response: {len(response.content)} bytes")
            else:
                print(f"❌ Failed: HTTP {response.status_code}")
                if response.status_code == 403:
                    print("   → Access denied (subscription content?)")
                elif response.status_code == 500:
                    print("   → Server error (rate limiting?)")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Small delay to avoid rate limiting
        if i < len(test_papers):
            time.sleep(5)
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {successes}/{len(test_papers)} successful downloads")
    print(f"Success rate: {successes/len(test_papers)*100:.1f}%")
    
    if successes > 0:
        print("\n✅ API METHOD WORKS FOR SOME CONTENT!")
        print("Note: Econometrica and Mathematical Finance may require VPN")
    else:
        print("\n⚠️ API not working - may need to wait or use VPN")

if __name__ == "__main__":
    test_api_correct()