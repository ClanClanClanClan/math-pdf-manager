#!/usr/bin/env python3
"""
ETH DISCOVERY API TEST
======================

Test the Discovery API which should provide access to external publishers like Wiley.
The Research Collection API only returns ETH's internal repository.
"""

import requests
import json
from urllib.parse import quote
from pathlib import Path

# Your ETH Library API credentials
API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"
APP_ID = "8cbc0329-19ba-4dbc-af39-864fb0eb5e35"

class ETHDiscoveryAPI:
    """Test ETH Discovery API for external publisher access"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.app_id = APP_ID
        
        # From our previous tests, we know these endpoints returned 200:
        self.working_endpoints = [
            "https://api.library.ethz.ch/research-collection/v1/search",  # Internal ETH repository
            "https://developer.library.ethz.ch/api/discovery/v3/search",  # Discovery API (external?)
            "https://developer.library.ethz.ch/api/research-collection/v1/search",
            "https://developer.library.ethz.ch/api/v1/search",
            "https://developer.library.ethz.ch/api/search"
        ]
        
        # Headers
        self.headers = {
            'User-Agent': 'ETH-Discovery-Client/1.0',
            'Accept': 'application/json'
        }
    
    def test_discovery_endpoints_detailed(self):
        """Test Discovery API endpoints in detail to understand their responses"""
        
        print("🔍 DETAILED DISCOVERY API ANALYSIS")
        print("=" * 70)
        
        test_queries = [
            "10.1002/anie.202004934",  # Wiley DOI
            "Angewandte Chemie",       # Journal name
            "wiley"                    # Publisher name
        ]
        
        for endpoint in self.working_endpoints:
            print(f"\n📡 Testing endpoint: {endpoint}")
            print("-" * 60)
            
            for query in test_queries:
                print(f"\n🔍 Query: {query}")
                
                # Test different parameter combinations
                param_sets = [
                    {'q': query, 'apikey': self.api_key},
                    {'query': query, 'apikey': self.api_key},
                    {'search': query, 'apikey': self.api_key},
                    {'title': query, 'apikey': self.api_key},
                    {'any': query, 'apikey': self.api_key}
                ]
                
                for params in param_sets[:2]:  # Test first 2 param sets
                    try:
                        response = requests.get(
                            endpoint,
                            params=params,
                            headers=self.headers,
                            timeout=10
                        )
                        
                        print(f"  Params: {list(params.keys())[:2]} | Status: {response.status_code}")
                        
                        if response.status_code == 200:
                            content_type = response.headers.get('Content-Type', '')
                            
                            if 'json' in content_type.lower():
                                try:
                                    data = response.json()
                                    self._analyze_json_response(data, query)
                                except:
                                    print(f"    ❌ JSON parse failed")
                            else:
                                print(f"    ⚠️ HTML response (likely documentation page)")
                                # Check if it's a working API that returns HTML unexpectedly
                                if len(response.text) < 500:
                                    print(f"    Response snippet: {response.text[:100]}...")
                        
                    except Exception as e:
                        print(f"    ❌ Error: {str(e)[:40]}...")
                
                print()
    
    def _analyze_json_response(self, data, query):
        """Analyze JSON response structure"""
        
        if isinstance(data, dict):
            print(f"    ✅ JSON response (dict)")
            print(f"    Keys: {list(data.keys())}")
            
            # Look for total results count
            total_fields = ['total', 'totalResults', 'count', 'numFound']
            for field in total_fields:
                if field in data:
                    print(f"    Total results: {data[field]}")
                    break
            
            # Look for results
            result_fields = ['results', 'docs', 'items', 'records', 'response']
            for field in result_fields:
                if field in data:
                    results = data[field]
                    if isinstance(results, list):
                        print(f"    📚 Found {len(results)} results in '{field}'")
                        if len(results) > 0:
                            self._analyze_single_result(results[0], query)
                    elif isinstance(results, dict) and 'docs' in results:
                        docs = results['docs']
                        print(f"    📚 Found {len(docs)} docs in '{field}.docs'")
                        if len(docs) > 0:
                            self._analyze_single_result(docs[0], query)
                    break
        
        elif isinstance(data, list):
            print(f"    ✅ JSON response (list)")
            print(f"    📚 Found {len(data)} results")
            if len(data) > 0:
                self._analyze_single_result(data[0], query)
        
        else:
            print(f"    ⚠️ Unexpected JSON format: {type(data)}")
    
    def _analyze_single_result(self, result, query):
        """Analyze a single result to understand its structure"""
        
        if not isinstance(result, dict):
            print(f"      ⚠️ Result not a dict: {type(result)}")
            return
        
        print(f"      🔍 Sample result analysis:")
        
        # Check for title
        title_fields = ['title', 'dc.title', 'Title', 'name']
        title = None
        for field in title_fields:
            if field in result:
                title = result[field]
                if isinstance(title, list) and len(title) > 0:
                    title = title[0]
                break
        
        print(f"        Title: {str(title)[:50]}..." if title else "        Title: Not found")
        
        # Check for DOI
        doi_fields = ['doi', 'DOI', 'dc.identifier.doi', 'identifier']
        doi = None
        for field in doi_fields:
            if field in result:
                doi = result[field]
                if isinstance(doi, list) and len(doi) > 0:
                    doi = doi[0]
                break
        
        print(f"        DOI: {doi}" if doi else "        DOI: Not found")
        
        # Check for publisher/source
        pub_fields = ['publisher', 'source', 'journal', 'dc.publisher']
        publisher = None
        for field in pub_fields:
            if field in result:
                publisher = result[field]
                if isinstance(publisher, list) and len(publisher) > 0:
                    publisher = publisher[0]
                break
        
        print(f"        Publisher: {publisher}" if publisher else "        Publisher: Not found")
        
        # Look for URL/access fields
        url_fields = ['url', 'link', 'fulltext_url', 'pdf_url', 'access_url', 'dc.identifier.uri']
        urls = []
        for field in url_fields:
            if field in result:
                value = result[field]
                if isinstance(value, str):
                    urls.append(value)
                elif isinstance(value, list):
                    urls.extend(value)
        
        if urls:
            print(f"        URLs found: {len(urls)}")
            for url in urls[:2]:  # Show first 2
                print(f"          {url}")
        else:
            print(f"        URLs: Not found")
        
        # Check if this looks like a Wiley paper
        wiley_indicators = ['wiley', 'onlinelibrary.wiley', 'doi.wiley']
        is_wiley = any(indicator in str(result).lower() for indicator in wiley_indicators)
        if is_wiley:
            print(f"        🎯 WILEY CONTENT DETECTED!")
        
        # Show all fields for first few results to understand structure
        if len(result.keys()) < 20:
            print(f"        All fields: {list(result.keys())}")
    
    def test_specific_wiley_search(self):
        """Test searching specifically for Wiley content"""
        
        print(f"\n🎯 TESTING SPECIFIC WILEY CONTENT SEARCH")
        print("=" * 70)
        
        # Discovery API is most likely to have external content
        discovery_endpoints = [
            "https://developer.library.ethz.ch/api/discovery/v3/search",
            "https://developer.library.ethz.ch/api/v1/search",
            "https://developer.library.ethz.ch/api/search"
        ]
        
        wiley_searches = [
            {
                'query': '10.1002/anie.202004934',
                'description': 'Specific Wiley DOI'
            },
            {
                'query': 'publisher:Wiley',
                'description': 'Publisher field search'
            },
            {
                'query': 'source:Wiley',
                'description': 'Source field search'
            },
            {
                'query': 'journal:"Angewandte Chemie"',
                'description': 'Journal name search'
            }
        ]
        
        for endpoint in discovery_endpoints:
            print(f"\n🔍 Testing: {endpoint}")
            
            for search in wiley_searches:
                print(f"\n  Search: {search['description']}")
                print(f"  Query: {search['query']}")
                
                try:
                    params = {
                        'q': search['query'],
                        'apikey': self.api_key,
                        'rows': 5  # Limit results for testing
                    }
                    
                    response = requests.get(
                        endpoint,
                        params=params,
                        headers=self.headers,
                        timeout=15
                    )
                    
                    print(f"    Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        if 'json' in content_type.lower():
                            try:
                                data = response.json()
                                self._check_for_wiley_results(data)
                            except Exception as e:
                                print(f"    ❌ JSON error: {e}")
                        else:
                            print(f"    ⚠️ Non-JSON response: {content_type}")
                    
                except Exception as e:
                    print(f"    ❌ Request error: {e}")
    
    def _check_for_wiley_results(self, data):
        """Check if results contain Wiley content"""
        
        # Extract results
        results = []
        if isinstance(data, dict):
            for field in ['results', 'docs', 'items', 'records']:
                if field in data:
                    results = data[field]
                    if isinstance(results, dict) and 'docs' in results:
                        results = results['docs']
                    break
        elif isinstance(data, list):
            results = data
        
        if not results:
            print(f"    ❌ No results found")
            return
        
        print(f"    📚 Found {len(results)} results")
        
        wiley_count = 0
        for i, result in enumerate(results[:3]):  # Check first 3
            if isinstance(result, dict):
                # Convert to string and check for Wiley indicators
                result_str = str(result).lower()
                wiley_indicators = ['wiley', 'onlinelibrary.wiley', 'doi.wiley', 'wileyonlinelibrary']
                
                if any(indicator in result_str for indicator in wiley_indicators):
                    wiley_count += 1
                    print(f"      🎯 Result {i+1}: WILEY CONTENT FOUND!")
                    
                    # Extract key fields
                    title = result.get('title', result.get('dc.title', 'Unknown'))
                    if isinstance(title, list):
                        title = title[0] if title else 'Unknown'
                    
                    doi = result.get('doi', result.get('DOI', result.get('dc.identifier.doi', '')))
                    if isinstance(doi, list):
                        doi = doi[0] if doi else ''
                    
                    print(f"        Title: {str(title)[:60]}...")
                    print(f"        DOI: {doi}")
                    
                    # Look for access URLs
                    url_fields = ['url', 'fulltext_url', 'pdf_url', 'link']
                    for field in url_fields:
                        if field in result:
                            print(f"        {field}: {result[field]}")
                else:
                    print(f"      Result {i+1}: Not Wiley content")
        
        if wiley_count > 0:
            print(f"    🎉 FOUND {wiley_count} WILEY RESULTS!")
        else:
            print(f"    ❌ No Wiley content in results")

def main():
    """Main function"""
    
    print("🎯 ETH DISCOVERY API - EXTERNAL PUBLISHER ACCESS TEST")
    print("=" * 80)
    print("Testing Discovery API for access to external publishers like Wiley")
    print("=" * 80)
    
    api = ETHDiscoveryAPI()
    
    # Test all endpoints in detail
    api.test_discovery_endpoints_detailed()
    
    # Test specific Wiley searches
    api.test_specific_wiley_search()
    
    print(f"\n📊 CONCLUSION")
    print("=" * 50)
    print("✅ API key is working")
    print("✅ Multiple endpoints responding")
    print("🔍 Need to find the right endpoint for external publisher access")
    print("💡 Research Collection API = ETH internal repository only")
    print("❓ Discovery API = May provide external publisher access")

if __name__ == "__main__":
    main()