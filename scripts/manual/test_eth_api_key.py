#!/usr/bin/env python3
"""
TEST ETH API KEY
================

Test the provided API key and discover the actual ETH Library API endpoints.
"""

import requests
import json
from urllib.parse import quote

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

def test_api_endpoints():
    """Test various possible ETH Library API endpoints"""
    
    print("🔍 TESTING ETH LIBRARY API KEY")
    print("=" * 60)
    print(f"API Key: {API_KEY[:20]}...")
    print()
    
    # Common API authentication methods
    headers_variations = [
        {'Authorization': f'Bearer {API_KEY}'},
        {'Authorization': f'Token {API_KEY}'},
        {'X-API-Key': API_KEY},
        {'api-key': API_KEY},
        {'apikey': API_KEY}
    ]
    
    # Possible ETH Library API endpoints
    base_urls = [
        "https://api.library.ethz.ch",
        "https://library.ethz.ch/api",
        "https://www.library.ethz.ch/api",
        "https://slsp.ch/api",
        "https://eth.swisscovery.slsp.ch/api",
        "https://api.ethz.ch/library"
    ]
    
    endpoints = [
        "/v1/status",
        "/v1/search",
        "/status",
        "/health",
        "/",
        "/v1/resources",
        "/search",
        "/holdings"
    ]
    
    # Test each combination
    working_endpoints = []
    
    for base_url in base_urls:
        for endpoint in endpoints:
            for headers in headers_variations:
                url = f"{base_url}{endpoint}"
                
                try:
                    print(f"Testing: {url}")
                    print(f"  Auth method: {list(headers.keys())[0]}")
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    print(f"  Status: {response.status_code}")
                    
                    if response.status_code in [200, 201, 401, 403]:
                        # These status codes suggest the endpoint exists
                        working_endpoints.append({
                            'url': url,
                            'status': response.status_code,
                            'headers': headers,
                            'response': response.text[:200]
                        })
                        
                        if response.status_code == 200:
                            print(f"  ✅ SUCCESS! Working endpoint found")
                            print(f"  Response preview: {response.text[:100]}...")
                        elif response.status_code == 401:
                            print(f"  🔐 Authentication required (good sign)")
                        elif response.status_code == 403:
                            print(f"  🚫 Forbidden (API exists but access denied)")
                    
                    print()
                    
                except requests.exceptions.Timeout:
                    print(f"  ⏰ Timeout")
                except requests.exceptions.ConnectionError:
                    print(f"  ❌ Connection error")
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:50]}")
                
                print()
    
    # Check SLSP/Swisscovery (ETH uses this system)
    print("\n🔍 TESTING SLSP/SWISSCOVERY ENDPOINTS")
    print("=" * 60)
    
    slsp_endpoints = [
        "https://slsp.ch/primo/v1/search",
        "https://eth.swisscovery.slsp.ch/discovery/search",
        "https://eth.swisscovery.slsp.ch/primaws/rest/pub/pnxs"
    ]
    
    for url in slsp_endpoints:
        try:
            print(f"Testing: {url}")
            
            # Try with API key as parameter
            params = {'apikey': API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ Endpoint accessible")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
        
        print()
    
    # Test if this is an EZproxy key
    print("\n🔍 TESTING EZPROXY AUTHENTICATION")
    print("=" * 60)
    
    ezproxy_test = "https://onlinelibrary.wiley.com.ezproxy.ethz.ch/doi/10.1002/anie.202004934"
    
    try:
        print(f"Testing EZproxy with API key...")
        headers = {'Authorization': f'Bearer {API_KEY}'}
        response = requests.get(ezproxy_test, headers=headers, timeout=10, allow_redirects=False)
        
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 302]:
            print("✅ EZproxy key might work!")
        
    except Exception as e:
        print(f"❌ EZproxy test failed: {e}")
    
    # Summary
    print("\n📊 SUMMARY")
    print("=" * 60)
    
    if working_endpoints:
        print(f"Found {len(working_endpoints)} potentially working endpoints:")
        for ep in working_endpoints:
            print(f"  - {ep['url']} (Status: {ep['status']})")
    else:
        print("❌ No standard API endpoints found")
        print("This API key might be for:")
        print("  1. A proxy service (not REST API)")
        print("  2. A different authentication system")
        print("  3. Requires specific documentation")
    
    print("\n💡 NEXT STEPS:")
    print("1. Check ETH Library documentation for API usage")
    print("2. The key might be for a proxy-based system")
    print("3. Contact library for API documentation")

def test_doi_search():
    """Test searching for a DOI using various methods"""
    
    print("\n🔍 TESTING DOI SEARCH")
    print("=" * 60)
    
    test_doi = "10.1002/anie.202004934"
    
    # Test Crossref as baseline
    print(f"Testing Crossref for DOI: {test_doi}")
    crossref_url = f"https://api.crossref.org/works/{test_doi}"
    
    try:
        response = requests.get(crossref_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            title = data.get('message', {}).get('title', ['Unknown'])[0]
            print(f"✅ Crossref found: {title}")
    except Exception as e:
        print(f"❌ Crossref error: {e}")

if __name__ == "__main__":
    test_api_endpoints()
    test_doi_search()