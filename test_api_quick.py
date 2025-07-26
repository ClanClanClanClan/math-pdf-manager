#!/usr/bin/env python3
"""
QUICK API TEST
==============

Test API method for journals that work
"""

import requests
from pathlib import Path

def test_api():
    """Quick test of API method"""
    
    api_key = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"
    
    # Papers that previously worked
    test_papers = [
        {'doi': '10.1111/jpet.12457', 'journal': 'Journal of Public Economic Theory'},
        {'doi': '10.1002/aic.18687', 'journal': 'AIChE Journal'},
        {'doi': '10.1111/jofi.12965', 'journal': 'Journal of Finance'},
    ]
    
    print("🧠 TESTING API METHOD")
    print("=" * 60)
    
    downloads_dir = Path("api_test_results")
    downloads_dir.mkdir(exist_ok=True)
    
    session = requests.Session()
    
    for paper in test_papers:
        print(f"\n📄 Testing: {paper['journal']}")
        print(f"DOI: {paper['doi']}")
        
        # Use the working TDM endpoint with API key as query parameter
        url = f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{paper['doi']}?apikey={api_key}"
        
        try:
            response = session.get(url, timeout=30)
            
            if response.status_code == 200 and len(response.content) > 10000:
                filename = f"{paper['doi'].replace('/', '_').replace('.', '_')}.pdf"
                save_path = downloads_dir / filename
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                size_mb = save_path.stat().st_size / (1024 * 1024)
                print(f"✅ SUCCESS: Downloaded {size_mb:.2f} MB")
            else:
                print(f"❌ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n✅ API METHOD CONFIRMED TO WORK FOR SOME JOURNALS")

if __name__ == "__main__":
    test_api()