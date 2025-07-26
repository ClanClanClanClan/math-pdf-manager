#!/usr/bin/env python3
"""
TEST ETH SPECIFIC SYSTEMS
=========================

Test specific ETH Library systems that might use this API key.
Focus on proxy-based authentication and SLSP integration.
"""

import requests
import base64
from urllib.parse import quote

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

def test_proxy_authentication():
    """Test if this is a proxy authentication key"""
    
    print("🔍 TESTING PROXY-BASED AUTHENTICATION")
    print("=" * 60)
    
    # Test Wiley through potential proxy with API key
    test_urls = [
        "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.202004934",
        "https://onlinelibrary-wiley-com.ezproxy.ethz.ch/doi/pdf/10.1002/anie.202004934"
    ]
    
    # Different authentication methods for proxies
    auth_methods = [
        # Bearer token
        lambda: {'Authorization': f'Bearer {API_KEY}'},
        # Basic auth with API key as password
        lambda: {'Authorization': f'Basic {base64.b64encode(f":{API_KEY}".encode()).decode()}'},
        # API key in various headers
        lambda: {'X-API-Key': API_KEY},
        lambda: {'Proxy-Authorization': f'Bearer {API_KEY}'},
        # Cookie-based
        lambda: {'Cookie': f'ezproxy={API_KEY}'},
    ]
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        
        for i, auth_func in enumerate(auth_methods):
            try:
                headers = auth_func()
                auth_type = list(headers.keys())[0]
                
                print(f"  Method {i+1}: {auth_type}")
                
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=15,
                    allow_redirects=True
                )
                
                print(f"    Status: {response.status_code}")
                print(f"    Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'pdf' in content_type.lower():
                        print(f"    ✅ SUCCESS! PDF accessible with {auth_type}")
                        print(f"    PDF size: {len(response.content)} bytes")
                        
                        # Save test PDF
                        with open('test_api_download.pdf', 'wb') as f:
                            f.write(response.content)
                        print(f"    📄 Saved test PDF!")
                        
                        return True
                    else:
                        print(f"    ❌ Not a PDF: {content_type}")
                elif response.status_code == 302:
                    print(f"    🔄 Redirect to: {response.headers.get('Location', 'Unknown')}")
                        
            except Exception as e:
                print(f"    ❌ Error: {str(e)[:50]}")
    
    return False

def test_swisscovery_primo():
    """Test SLSP/Primo API used by ETH"""
    
    print("\n\n🔍 TESTING SWISSCOVERY/PRIMO API")
    print("=" * 60)
    
    # Primo/SLSP search API
    search_urls = [
        "https://eth.swisscovery.slsp.ch/primaws/rest/pub/pnxs",
        "https://eth.swisscovery.slsp.ch/primo_library/libweb/webservices/rest/v1/pnxs",
        "https://slsp.ch/primo/v1/search"
    ]
    
    # Search for a test DOI
    test_doi = "10.1002/anie.202004934"
    
    for base_url in search_urls:
        print(f"\nTesting: {base_url}")
        
        # Try different parameter combinations
        param_sets = [
            {'q': f'doi:{test_doi}', 'apikey': API_KEY},
            {'q': f'any,contains,{test_doi}', 'apikey': API_KEY},
            {'query': f'doi:{test_doi}', 'apikey': API_KEY}
        ]
        
        headers_sets = [
            {},
            {'Authorization': f'Bearer {API_KEY}'},
            {'X-API-Key': API_KEY}
        ]
        
        for params in param_sets:
            for headers in headers_sets:
                try:
                    response = requests.get(
                        base_url,
                        params=params,
                        headers=headers,
                        timeout=10
                    )
                    
                    print(f"  Params: {list(params.keys())}")
                    print(f"  Headers: {list(headers.keys()) if headers else 'None'}")
                    print(f"  Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print(f"  ✅ Success!")
                        content = response.text[:200]
                        print(f"  Response preview: {content}...")
                        
                        # Try to parse response
                        try:
                            data = response.json()
                            if 'docs' in data or 'records' in data:
                                print(f"  📚 Found search results!")
                        except:
                            pass
                    
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:30]}")

def test_eth_knowledge_portal():
    """Test ETH Knowledge Portal / Research Collection"""
    
    print("\n\n🔍 TESTING ETH KNOWLEDGE PORTAL")
    print("=" * 60)
    
    portal_urls = [
        "https://www.research-collection.ethz.ch/oai/request",
        "https://www.research-collection.ethz.ch/rest/items",
        "https://doi.library.ethz.ch/api"
    ]
    
    for url in portal_urls:
        print(f"\nTesting: {url}")
        
        try:
            headers = {'X-API-Key': API_KEY}
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"  Status: {response.status_code}")
            if response.status_code in [200, 400, 401]:
                print(f"  ✅ Endpoint exists")
                print(f"  Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

def check_api_key_format():
    """Analyze the API key format"""
    
    print("\n\n🔍 API KEY FORMAT ANALYSIS")
    print("=" * 60)
    
    print(f"Key length: {len(API_KEY)} characters")
    print(f"Key format: Alphanumeric")
    
    # Check if it's base64
    try:
        decoded = base64.b64decode(API_KEY + '==')  # Add padding
        print(f"Base64 decodable: Yes")
        print(f"Decoded length: {len(decoded)} bytes")
    except:
        print(f"Base64 decodable: No")
    
    # Common API key patterns
    if len(API_KEY) == 48:
        print("\n✅ Length matches common API key formats")
    
    print("\n💡 This appears to be a standard API key")
    print("   Likely used for proxy authentication or special access")

def save_working_config(method=None):
    """Save working configuration if found"""
    
    if method:
        config = {
            'api_key': API_KEY,
            'method': method,
            'example': 'See test results above'
        }
        
        with open('eth_api_config.json', 'w') as f:
            import json
            json.dump(config, f, indent=2)
        
        print(f"\n✅ Saved working configuration to eth_api_config.json")

def main():
    """Run all tests"""
    
    print("🧪 ETH API KEY COMPREHENSIVE TEST")
    print("=" * 80)
    print(f"Testing API key: {API_KEY[:20]}...")
    print("=" * 80)
    
    # Check format
    check_api_key_format()
    
    # Test proxy auth
    if test_proxy_authentication():
        print("\n🎉 FOUND WORKING METHOD: Proxy Authentication")
        save_working_config('proxy')
        return
    
    # Test Swisscovery
    test_swisscovery_primo()
    
    # Test other ETH systems
    test_eth_knowledge_portal()
    
    print("\n\n📊 FINAL ASSESSMENT")
    print("=" * 60)
    print("If no method worked, this API key might be for:")
    print("1. A system that requires VPN connection first")
    print("2. A specific service not tested here")
    print("3. Rate-limited or time-restricted access")
    print("\nRecommendation: Contact ETH Library for API documentation")

if __name__ == "__main__":
    main()