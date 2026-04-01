#!/usr/bin/env python3
"""
IEEE DOI Fixed
==============

Properly resolve IEEE DOIs to document URLs.
"""

import requests
from pathlib import Path

def resolve_ieee_dois():
    print("🔍 RESOLVING IEEE DOI FORMATS")
    print("=" * 50)
    
    # The failing DOIs
    failing_dois = [
        "10.1109/MC.2006.5",
        "10.1109/JPROC.2016.2515118", 
        "10.1109/JPROC.2015.2460651",
        "10.1109/5.869037",
        "10.1109/JPROC.2016.2571690"
    ]
    
    # Working DOIs
    working_dois = [
        "10.1109/5.726791",
        "10.1109/JPROC.2018.2820126",
        "10.1109/5.771073",
        "10.1109/5.726787",
        "10.1109/JPROC.2017.2761740"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    def test_doi_resolution(doi, status="unknown"):
        print(f"\n📄 Testing {status}: {doi}")
        
        doi_url = f"https://doi.org/{doi}"
        print(f"   DOI URL: {doi_url}")
        
        try:
            response = session.get(doi_url, allow_redirects=True, timeout=15)
            final_url = response.url
            status_code = response.status_code
            
            print(f"   Status: {status_code}")
            print(f"   Final URL: {final_url}")
            
            if status_code == 200 and 'ieeexplore.ieee.org' in final_url:
                # Extract document ID from IEEE URL
                import re
                doc_id_match = re.search(r'/document/(\d+)', final_url)
                if doc_id_match:
                    doc_id = doc_id_match.group(1)
                    print(f"   ✅ Document ID: {doc_id}")
                    return doc_id, final_url
                else:
                    print(f"   ❌ Could not extract document ID from: {final_url}")
            elif status_code != 200:
                print(f"   ❌ HTTP error: {status_code}")
            else:
                print(f"   ❌ Does not redirect to IEEE")
                
        except Exception as e:
            print(f"   ❌ Resolution failed: {e}")
        
        return None, None
    
    print("WORKING DOIs:")
    working_results = {}
    for doi in working_dois:
        doc_id, url = test_doi_resolution(doi, "WORKING")
        if doc_id:
            working_results[doi] = (doc_id, url)
    
    print("\n" + "=" * 50)
    print("FAILING DOIs:")
    failing_results = {}
    for doi in failing_dois:
        doc_id, url = test_doi_resolution(doi, "FAILING")
        if doc_id:
            failing_results[doi] = (doc_id, url)
    
    print(f"\n📊 ANALYSIS")
    print(f"Working DOIs resolved: {len(working_results)}/{len(working_dois)}")
    print(f"Failing DOIs resolved: {len(failing_results)}/{len(failing_dois)}")
    
    if working_results:
        print("\n✅ Successfully resolved working DOIs:")
        for doi, (doc_id, url) in working_results.items():
            print(f"   {doi} -> {doc_id}")
    
    if failing_results:
        print("\n🎯 Successfully resolved 'failing' DOIs:")
        for doi, (doc_id, url) in failing_results.items():
            print(f"   {doi} -> {doc_id}")
        print("\n🔍 This suggests the DOIs are valid and the issue is in authentication!")
    
    if not failing_results:
        print("\n❌ Could not resolve 'failing' DOIs")
        print("This suggests these DOIs might be:")
        print("  1. Invalid/malformed")
        print("  2. Very old papers with different URL structure")
        print("  3. Papers that require special access")
    
    return working_results, failing_results

if __name__ == "__main__":
    working, failing = resolve_ieee_dois()
    
    if failing:
        print(f"\n🎉 GREAT NEWS: The 'failing' DOIs actually resolve!")
        print(f"This means the authentication issue is NOT about invalid DOIs.")
        print(f"The problem is in how the IEEE publisher handles authentication.")
    else:
        print(f"\n❌ The 'failing' DOIs don't resolve - they may be malformed or invalid.")