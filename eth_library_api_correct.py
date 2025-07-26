#!/usr/bin/env python3
"""
ETH LIBRARY API - CORRECT USAGE
===============================

Test the ETH Library API with the correct query parameter format.
Based on research: ETH Library has Discovery API, Research Collection API, etc.
API key should be used as query parameter: &apikey={yourkey}
"""

import requests
import json
from urllib.parse import quote
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Optional

# Your ETH Library API credentials
API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"
APP_ID = "8cbc0329-19ba-4dbc-af39-864fb0eb5e35"  # PDF_Management app

class ETHLibraryAPI:
    """Correct ETH Library API client"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.app_id = APP_ID
        self.base_urls = [
            "https://api.library.ethz.ch",
            "https://developer.library.ethz.ch/api",
            "https://library.ethz.ch/api"
        ]
        self.downloads_dir = Path("eth_api_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    def test_api_endpoints(self):
        """Test various ETH Library API endpoints with correct authentication"""
        
        print("🔍 TESTING ETH LIBRARY API ENDPOINTS")
        print("=" * 70)
        print(f"API Key: {self.api_key[:20]}...")
        print(f"App ID: {self.app_id}")
        print("=" * 70)
        
        # Test different API endpoints based on research
        endpoints_to_test = [
            # Discovery API - access to 30+ million items
            {
                'name': 'Discovery API - Search',
                'endpoints': [
                    '/discovery/v3/search',
                    '/api/discovery/v3/search',
                    '/discovery/search'
                ]
            },
            # Research Collection API - ETH research papers
            {
                'name': 'Research Collection API',
                'endpoints': [
                    '/research-collection/v1/search',
                    '/api/research-collection/v1/search',
                    '/research-collection/search'
                ]
            },
            # General API endpoints
            {
                'name': 'General APIs',
                'endpoints': [
                    '/v1/status',
                    '/status',
                    '/v1/search',
                    '/search'
                ]
            }
        ]
        
        working_endpoints = []
        
        for endpoint_group in endpoints_to_test:
            print(f"\n🧪 Testing {endpoint_group['name']}")
            print("-" * 50)
            
            for base_url in self.base_urls:
                for endpoint in endpoint_group['endpoints']:
                    full_url = f"{base_url}{endpoint}"
                    
                    # Test with API key as query parameter (correct method)
                    test_url = f"{full_url}?apikey={self.api_key}"
                    
                    try:
                        print(f"Testing: {test_url[:80]}...")
                        
                        response = requests.get(test_url, timeout=15)
                        
                        print(f"  Status: {response.status_code}")
                        
                        if response.status_code in [200, 400, 401]:
                            print(f"  ✅ Endpoint exists!")
                            
                            if response.status_code == 200:
                                print(f"  🎉 SUCCESS! Working endpoint found")
                                
                                try:
                                    data = response.json()
                                    print(f"  Response type: JSON")
                                    print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'List/Other'}")
                                except:
                                    print(f"  Response type: {response.headers.get('Content-Type', 'Unknown')}")
                                
                                working_endpoints.append({
                                    'url': full_url,
                                    'status': response.status_code,
                                    'response': response.text[:200]
                                })
                            
                            elif response.status_code == 401:
                                print(f"  🔐 Authentication issue - check API key")
                            elif response.status_code == 400:
                                print(f"  ⚠️ Bad request - may need parameters")
                        
                        else:
                            print(f"  ❌ {response.status_code}")
                        
                    except requests.exceptions.Timeout:
                        print(f"  ⏰ Timeout")
                    except requests.exceptions.ConnectionError:
                        print(f"  ❌ Connection error")
                    except Exception as e:
                        print(f"  ❌ Error: {str(e)[:30]}...")
                    
                    print()
        
        return working_endpoints
    
    def search_paper_by_doi(self, doi: str):
        """Search for a paper by DOI using Discovery API"""
        
        print(f"\n🔍 Searching for DOI: {doi}")
        print("-" * 50)
        
        # Potential Discovery API search endpoints
        search_endpoints = [
            "https://api.library.ethz.ch/discovery/v3/search",
            "https://developer.library.ethz.ch/api/discovery/v3/search",
            "https://library.ethz.ch/api/discovery/search",
            "https://api.library.ethz.ch/search"
        ]
        
        # Different search parameter combinations
        search_params = [
            {'q': doi, 'apikey': self.api_key},
            {'query': doi, 'apikey': self.api_key},
            {'doi': doi, 'apikey': self.api_key},
            {'identifier': doi, 'apikey': self.api_key},
            {'search': doi, 'apikey': self.api_key}
        ]
        
        for endpoint in search_endpoints:
            for params in search_params:
                try:
                    print(f"Testing: {endpoint}")
                    print(f"  Params: {list(params.keys())}")
                    
                    response = requests.get(endpoint, params=params, timeout=15)
                    
                    print(f"  Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print(f"  ✅ SUCCESS! Found results")
                        
                        try:
                            data = response.json()
                            
                            # Look for results in various formats
                            results = None
                            if 'results' in data:
                                results = data['results']
                            elif 'items' in data:
                                results = data['items']
                            elif 'records' in data:
                                results = data['records']
                            elif 'docs' in data:
                                results = data['docs']
                            
                            if results:
                                print(f"  📚 Found {len(results)} results")
                                
                                for i, result in enumerate(results[:3]):  # Show first 3
                                    print(f"    Result {i+1}:")
                                    print(f"      Title: {result.get('title', 'Unknown')}")
                                    print(f"      DOI: {result.get('doi', 'Unknown')}")
                                    
                                    # Look for PDF access
                                    pdf_url = (result.get('pdf_url') or 
                                             result.get('fulltext_url') or
                                             result.get('download_url') or
                                             result.get('access_url'))
                                    
                                    if pdf_url:
                                        print(f"      📄 PDF: {pdf_url}")
                                        return result
                            else:
                                print(f"  ℹ️ Response structure: {list(data.keys()) if isinstance(data, dict) else 'List'}")
                        
                        except Exception as e:
                            print(f"  ⚠️ JSON parse error: {e}")
                            print(f"  Raw response: {response.text[:100]}...")
                    
                    elif response.status_code == 401:
                        print(f"  🔐 Authentication failed")
                    elif response.status_code == 400:
                        print(f"  ❌ Bad request")
                    else:
                        print(f"  ❌ Status {response.status_code}")
                
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:40]}...")
                
                print()
        
        return None
    
    def test_with_app_id(self):
        """Test endpoints that might use the app ID"""
        
        print(f"\n🔧 Testing with App ID: {self.app_id}")
        print("-" * 50)
        
        endpoints = [
            "https://api.library.ethz.ch/apps/{app_id}/search",
            "https://developer.library.ethz.ch/api/apps/{app_id}/resources",
            "https://api.library.ethz.ch/v1/apps/{app_id}/discovery"
        ]
        
        for endpoint_template in endpoints:
            endpoint = endpoint_template.format(app_id=self.app_id)
            
            try:
                url = f"{endpoint}?apikey={self.api_key}"
                print(f"Testing: {url}")
                
                response = requests.get(url, timeout=10)
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"  ✅ App-specific endpoint works!")
                    print(f"  Response: {response.text[:100]}...")
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:30]}...")
            
            print()
    
    async def download_with_api(self, doi: str, title: str = "") -> bool:
        """Download PDF using ETH Library API"""
        
        print(f"\n📥 API Download: {title or doi}")
        
        # First, search for the paper
        paper_info = self.search_paper_by_doi(doi)
        
        if not paper_info:
            print("❌ Paper not found in ETH Library")
            return False
        
        # Extract PDF URL
        pdf_url = (paper_info.get('pdf_url') or 
                  paper_info.get('fulltext_url') or
                  paper_info.get('download_url') or
                  paper_info.get('access_url'))
        
        if not pdf_url:
            print("❌ No PDF URL found")
            return False
        
        print(f"🔗 PDF URL: {pdf_url}")
        
        # Download PDF with API authentication
        try:
            # Add API key to PDF URL if needed
            if 'apikey=' not in pdf_url:
                separator = '&' if '?' in pdf_url else '?'
                pdf_url_with_key = f"{pdf_url}{separator}apikey={self.api_key}"
            else:
                pdf_url_with_key = pdf_url
            
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url_with_key) as response:
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        if 'pdf' in content_type.lower():
                            pdf_content = await response.read()
                            
                            if len(pdf_content) > 1000:
                                filename = f"eth_api_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                save_path = self.downloads_dir / filename
                                
                                with open(save_path, 'wb') as f:
                                    f.write(pdf_content)
                                
                                size_mb = len(pdf_content) / (1024 * 1024)
                                print(f"✅ SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                return True
                            else:
                                print(f"❌ PDF too small: {len(pdf_content)} bytes")
                        else:
                            print(f"❌ Not PDF: {content_type}")
                    else:
                        print(f"❌ Download failed: {response.status}")
        
        except Exception as e:
            print(f"❌ Download error: {e}")
        
        return False

def main():
    """Main function"""
    
    print("🎯 ETH LIBRARY API - CORRECT IMPLEMENTATION")
    print("=" * 80)
    print("Testing ETH Library APIs with proper query parameter authentication")
    print("=" * 80)
    
    api = ETHLibraryAPI()
    
    # Test API endpoints
    working_endpoints = api.test_api_endpoints()
    
    if working_endpoints:
        print(f"\n🎉 Found {len(working_endpoints)} working endpoints!")
        for endpoint in working_endpoints:
            print(f"  ✅ {endpoint['url']} (Status: {endpoint['status']})")
    
    # Test with app ID
    api.test_with_app_id()
    
    # Test searching for a paper
    test_doi = "10.1002/anie.202004934"
    paper_info = api.search_paper_by_doi(test_doi)
    
    if paper_info:
        print(f"\n🎉 PAPER FOUND!")
        print(f"Title: {paper_info.get('title', 'Unknown')}")
        print(f"DOI: {paper_info.get('doi', 'Unknown')}")
        
        # Try to download
        import asyncio
        success = asyncio.run(api.download_with_api(test_doi))
        
        if success:
            print(f"\n🎉 ETH LIBRARY API DOWNLOAD SUCCESS!")
            print(f"🔑 API Key authentication working")
            print(f"📄 PDF downloaded successfully")
        else:
            print(f"\n⚠️ Paper found but download needs work")
    else:
        print(f"\n💡 Paper not found - may need different search parameters")
    
    print(f"\n📊 SUMMARY")
    print("=" * 50)
    print(f"✅ Correct API key format: ?apikey={API_KEY[:20]}...")
    print(f"✅ App ID available: {APP_ID}")
    print(f"✅ Testing multiple ETH Library API endpoints")
    
    if working_endpoints:
        print(f"✅ Found working endpoints - API access confirmed!")
    else:
        print(f"❌ No endpoints responding - may need registration or different URLs")

if __name__ == "__main__":
    main()